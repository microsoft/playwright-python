# Copyright (c) Microsoft Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Python only: tests of behaviors that no upstream test covers."""

import contextlib
import multiprocessing
import signal
import subprocess
import sys
import textwrap
import time
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, Generator, List

import pytest
from greenlet import greenlet

from playwright.sync_api import (
    Browser,
    BrowserContext,
    ConsoleMessage,
    Dialog,
    Error,
    Page,
    Playwright,
    TimeoutError,
    sync_playwright,
)
from tests.server import Server


def test_page_repr(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    assert repr(page) == f"<Page url={page.url!r}>"


def test_frame_repr(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    assert (
        repr(page.main_frame)
        == f"<Frame name={page.main_frame.name} url={page.main_frame.url!r}>"
    )


def test_browser_context_repr(context: BrowserContext) -> None:
    assert repr(context) == f"<BrowserContext browser={context.browser}>"


def test_browser_repr(browser: Browser) -> None:
    assert (
        repr(browser)
        == f"<Browser type={browser.browser_type} version={browser.version}>"
    )


def test_browser_type_repr(browser: Browser) -> None:
    browser_type = browser.browser_type
    assert (
        repr(browser_type)
        == f"<BrowserType name={browser_type.name} executable_path={browser_type.executable_path}>"
    )


def test_dialog_repr(page: Page) -> None:
    def on_dialog(dialog: Dialog) -> None:
        dialog.accept()
        assert (
            repr(dialog)
            == f"<Dialog type={dialog.type} message={dialog.message} default_value={dialog.default_value}>"
        )

    page.on("dialog", on_dialog)
    page.evaluate("alert('yo')")


def test_console_repr(page: Page) -> None:
    messages = []
    page.on("console", lambda m: messages.append(m))
    page.evaluate('() => console.log("Hello world")')
    message = messages[0]
    assert repr(message) == f"<ConsoleMessage type={message.type} text={message.text}>"


def test_sync_wait_for_event_raise(page: Page) -> None:
    with pytest.raises(AssertionError):
        with page.expect_event("popup", timeout=500):
            assert False

    with pytest.raises(Error) as exc_info:
        with page.expect_event("popup", timeout=500):
            page.wait_for_timeout(1_000)
    assert "Timeout 500ms exceeded" in exc_info.value.message


def test_sync_playwright_multiple_times(playwright: Playwright) -> None:
    # The playwright fixture runs the first instance: its event loop is the one
    # that the second sync_playwright() finds.
    with pytest.raises(Error) as exc:
        with sync_playwright() as pw:
            assert pw.chromium
    assert (
        "It looks like you are using Playwright Sync API inside the asyncio loop."
        in exc.value.message
    )


def test_expect_response_should_not_hang_when_predicate_throws(page: Page) -> None:
    with pytest.raises(Exception, match="Oops!"):
        with page.expect_response("**/*"):
            raise Exception("Oops!")


def test_expect_response_should_not_switch_to_stale_greenlet_when_cancelled(
    page: Page, server: Server
) -> None:
    # Mimics frameworks like pytest-twisted that run the test body in a separate
    # greenlet which stays alive (suspended) after handing control back.
    main = greenlet.getcurrent()
    resumed: List[bool] = []

    def body() -> None:
        with pytest.raises(Exception, match="Oops!"):
            with page.expect_response("**/*"):
                raise Exception("Oops!")
        main.switch()
        resumed.append(True)
        main.switch()

    greenlet(body).switch()
    # Pumps the dispatcher, which runs the cancelled future's done callbacks.
    page.goto(server.EMPTY_PAGE)
    assert resumed == []


def test_expect_response_should_use_context_timeout(
    page: Page, context: BrowserContext, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)

    context.set_default_timeout(1_000)
    with pytest.raises(Error) as exc_info:
        with page.expect_response("https://playwright.dev"):
            pass
    assert exc_info.type is TimeoutError
    assert "Timeout 1000ms exceeded" in exc_info.value.message


def _test_sync_playwright_stop_multiple_times() -> None:
    playwright = sync_playwright().start()
    playwright.stop()
    playwright.stop()


@pytest.mark.slow
def test_sync_playwright_stop_multiple_times() -> None:
    # spawn: a fork of this multi-threaded process is unsafe, and Python 3.12 to
    # 3.13 warn about it; 3.14 and the other platforms do not fork by default.
    p = multiprocessing.get_context("spawn").Process(
        target=_test_sync_playwright_stop_multiple_times
    )
    p.start()
    p.join()
    assert p.exitcode == 0


def _test_call_sync_method_after_playwright_close_with_own_loop(
    browser_name: str,
    launch_arguments: Dict[str, Any],
    empty_page: str,
) -> None:
    playwright = sync_playwright().start()
    browser = playwright[browser_name].launch(**launch_arguments)
    context = browser.new_context()
    page = context.new_page()
    page.goto(empty_page)
    playwright.stop()
    with pytest.raises(Error) as exc:
        page.evaluate("1+1")
    assert "Event loop is closed! Is Playwright already stopped?" in str(exc.value)


@pytest.mark.slow
def test_call_sync_method_after_playwright_close_with_own_loop(
    server: Server, browser_name: str, launch_arguments: Dict[str, Any]
) -> None:
    p = multiprocessing.get_context("spawn").Process(
        target=_test_call_sync_method_after_playwright_close_with_own_loop,
        args=[browser_name, launch_arguments, server.EMPTY_PAGE],
    )
    p.start()
    p.join()
    assert p.exitcode == 0


@pytest.mark.slow
def test_should_not_orphan_callback_on_non_serializable_params(
    browser_name: str,
    launch_arguments: Dict[str, Any],
    tmp_path: Path,
) -> None:
    # Regression test for https://github.com/microsoft/playwright-python/issues/3165.
    # Run in a subprocess so "Future exception was never retrieved" on exit is visible on stderr.
    script = tmp_path / "orphan_callback.py"
    script.write_text(
        textwrap.dedent(
            f"""
            from playwright.sync_api import Error, sync_playwright

            with sync_playwright() as p:
                browser = p[{browser_name!r}].launch(**{launch_arguments!r})
                page = browser.new_page()
                # v1 raises the TypeError of the JSON serialization, v2 the Error
                # of the protocol validation.
                try:
                    page.locator("asdf").highlight(style=object())
                except (TypeError, Error):
                    pass
                browser.close()
            """
        )
    )
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert "Future exception was never retrieved" not in result.stderr


@pytest.mark.slow
def test_sync_calls_should_raise_after_driver_exit(
    browser_name: str,
    launch_arguments: Dict[str, Any],
    tmp_path: Path,
) -> None:
    # Regression test for https://github.com/microsoft/playwright-python/pull/3187.
    # Run in a subprocess with a timeout, the calls used to spin forever instead of raising.
    script = tmp_path / "driver_exit.py"
    script.write_text(
        textwrap.dedent(
            f"""
            from playwright.sync_api import sync_playwright


            def error_of(callback):
                try:
                    callback()
                except Exception as e:
                    return str(e)
                return ""


            with sync_playwright() as p:
                browser = p[{browser_name!r}].launch(**{launch_arguments!r})
                page = browser.new_page()
                route = page.route("**/*", lambda route: route.continue_())

                # The driver process: p.stop is bound to the context manager, whose
                # client owns the transport.
                transport = p.stop.__self__._client._transport

                def expect_event():
                    with page.expect_event("console", timeout=0):
                        transport._proc.kill()

                def dispose_route():
                    with route:
                        pass

                for callback in [expect_event, page.title, dispose_route, browser.close]:
                    assert "Playwright connection closed" in error_of(callback), callback
            """
        )
    )
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr


class Interrupted(BaseException):
    """Raised from a signal handler, like pytest-timeout's Failed."""


@contextlib.contextmanager
def interrupt_after(seconds: float) -> Generator[None, None, None]:
    # Python runs the handler in whatever code executes when the alarm fires.
    # During a blocking sync call that is the dispatcher's event loop, not the
    # test. The previous handler and timer belong to pytest-timeout.
    def handler(signum: int, frame: Any) -> None:
        raise Interrupted()

    previous_handler = signal.signal(signal.SIGALRM, handler)
    previous_timer = signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, *previous_timer)
        signal.signal(signal.SIGALRM, previous_handler)


@pytest.mark.skipif(sys.platform == "win32", reason="SIGALRM is not available")
def test_sync_should_survive_exception_raised_by_signal_handler(page: Page) -> None:
    with interrupt_after(0.2):
        with pytest.raises(Interrupted):
            page.wait_for_timeout(10_000)
    # The connection is still usable, and the next call does not wait for the
    # abandoned one to finish.
    start = time.monotonic()
    assert page.evaluate("1 + 1") == 2
    assert time.monotonic() - start < 5
    assert page.title() == ""


@pytest.mark.skipif(sys.platform == "win32", reason="SIGALRM is not available")
def test_sync_expect_event_should_survive_exception_raised_by_signal_handler(
    page: Page,
) -> None:
    with interrupt_after(0.2):
        with pytest.raises(Interrupted):
            with page.expect_event("console"):
                pass
    with page.expect_console_message() as console_info:
        page.evaluate("console.log('hello')")
    assert console_info.value.text == "hello"


@pytest.mark.skipif(sys.platform == "win32", reason="SIGALRM is not available")
def test_sync_should_survive_exception_raised_by_signal_handler_while_event_handler_blocks(
    page: Page,
) -> None:
    handled: List[str] = []

    def handler(message: ConsoleMessage) -> None:
        page.wait_for_timeout(500)
        handled.append(message.text)

    page.on("console", handler)
    with interrupt_after(0.2):
        with pytest.raises(Interrupted):
            page.evaluate("console.log('hello')")
            page.wait_for_timeout(10_000)
    assert page.evaluate("1 + 1") == 2
    # The handler was suspended in its own sync call. It finishes once the
    # dispatcher runs the event loop again.
    deadline = time.monotonic() + 10
    while not handled and time.monotonic() < deadline:
        page.wait_for_timeout(100)
    assert handled == ["hello"]


def test_click_should_accept_timedelta_for_timeout(page: Page) -> None:
    with pytest.raises(TimeoutError, match="Timeout 1ms exceeded"):
        page.click("does-not-exist", timeout=timedelta(milliseconds=1))
