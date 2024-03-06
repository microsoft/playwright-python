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

import multiprocessing
import os
from typing import Any, Callable, Dict

import pytest

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Dialog,
    Error,
    Page,
    TimeoutError,
    sync_playwright,
)
from tests.server import Server
from tests.utils import TARGET_CLOSED_ERROR_MESSAGE


def test_sync_query_selector(page: Page) -> None:
    page.set_content(
        """
    <h1 id="foo">Bar</h1>
    """
    )
    e1 = page.query_selector("#foo")
    assert e1
    e2 = page.query_selector("h1")
    assert e2
    assert e1.inner_text() == e2.inner_text()


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
        == f"<Browser type={browser._impl_obj._browser_type} version={browser.version}>"
    )


def test_browser_type_repr(browser: Browser) -> None:
    browser_type = browser._impl_obj._browser_type
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


def test_sync_click(page: Page) -> None:
    page.set_content(
        """
    <button onclick="window.clicked=true">Bar</button>
    """
    )
    page.click("text=Bar")
    assert page.evaluate("()=>window.clicked")


def test_sync_nested_query_selector(page: Page) -> None:
    page.set_content(
        """
    <div id="one">
        <span class="two">
            <label>
                MyValue
            </label>
        </span>
    </div>
    """
    )
    e1 = page.query_selector("#one")
    assert e1
    e2 = e1.query_selector(".two")
    assert e2
    e3 = e2.query_selector("label")
    assert e3
    assert e3.inner_text() == "MyValue"


def test_sync_handle_multiple_pages(context: BrowserContext) -> None:
    page1 = context.new_page()
    page2 = context.new_page()
    assert len(context.pages) == 2
    page1.set_content("one")
    page2.set_content("two")
    assert "one" in page1.content()
    assert "two" in page2.content()
    page1.close()
    assert len(context.pages) == 1
    page2.close()
    assert len(context.pages) == 0
    for page in [page1, page2]:
        with pytest.raises(Error):
            page.content()


def test_sync_wait_for_event(page: Page, server: Server) -> None:
    with page.expect_event("popup", timeout=10000) as popup:
        page.evaluate("(url) => window.open(url)", server.EMPTY_PAGE)
    assert popup.value


def test_sync_wait_for_event_raise(page: Page) -> None:
    with pytest.raises(AssertionError):
        with page.expect_event("popup", timeout=500):
            assert False

    with pytest.raises(Error) as exc_info:
        with page.expect_event("popup", timeout=500):
            page.wait_for_timeout(1_000)
    assert "Timeout 500ms exceeded" in exc_info.value.message


def test_sync_make_existing_page_sync(page: Page) -> None:
    page = page
    assert page.evaluate("() => ({'playwright': true})") == {"playwright": True}
    page.set_content("<h1>myElement</h1>")
    page.wait_for_selector("text=myElement")


def test_sync_network_events(page: Page, server: Server) -> None:
    server.set_route(
        "/hello-world",
        lambda request: (
            request.setHeader("Content-Type", "text/plain"),
            request.write(b"Hello world"),
            request.finish(),
        ),
    )
    page.goto(server.EMPTY_PAGE)
    messages = []
    page.on(
        "request", lambda request: messages.append(f">>{request.method}{request.url}")
    )
    page.on(
        "response",
        lambda response: messages.append(f"<<{response.status}{response.url}"),
    )
    response = page.evaluate("""async ()=> (await fetch("/hello-world")).text()""")
    assert response == "Hello world"
    assert messages == [
        f">>GET{server.PREFIX}/hello-world",
        f"<<200{server.PREFIX}/hello-world",
    ]


def test_console_should_work(page: Page, browser_name: str) -> None:
    messages = []
    page.once("console", lambda m: messages.append(m))
    page.evaluate('() => console.log("hello", 5, {foo: "bar"})')
    assert len(messages) == 1
    message = messages[0]
    if browser_name != "firefox":
        assert message.text == "hello 5 {foo: bar}"
        assert str(message) == "hello 5 {foo: bar}"
    else:
        assert message.text == "hello 5 JSHandle@object"
        assert str(message) == "hello 5 JSHandle@object"
    assert message.type == "log"
    assert message.args[0].json_value() == "hello"
    assert message.args[1].json_value() == 5
    assert message.args[2].json_value() == {"foo": "bar"}


def test_sync_download(browser: Browser, server: Server) -> None:
    server.set_route(
        "/downloadWithFilename",
        lambda request: (
            request.setHeader("Content-Type", "application/octet-stream"),
            request.setHeader("Content-Disposition", "attachment; filename=file.txt"),
            request.write(b"Hello world"),
            request.finish(),
        ),
    )
    page = browser.new_page(accept_downloads=True)
    page.set_content(f'<a href="{server.PREFIX}/downloadWithFilename">download</a>')

    with page.expect_event("download") as download:
        page.click("a")
    assert download.value
    assert download.value.suggested_filename == "file.txt"
    path = download.value.path()
    assert os.path.isfile(path)
    with open(path, "r") as fd:
        assert fd.read() == "Hello world"
    page.close()


def test_sync_workers_page_workers(page: Page, server: Server) -> None:
    with page.expect_event("worker") as event_worker:
        page.goto(server.PREFIX + "/worker/worker.html")
    assert event_worker.value
    worker = page.workers[0]
    assert "worker.js" in worker.url

    assert worker.evaluate('() => self["workerFunction"]()') == "worker function result"

    page.goto(server.EMPTY_PAGE)
    assert len(page.workers) == 0


def test_sync_playwright_multiple_times() -> None:
    with pytest.raises(Error) as exc:
        with sync_playwright() as pw:
            assert pw.chromium
    assert (
        "It looks like you are using Playwright Sync API inside the asyncio loop."
        in exc.value.message
    )


def test_sync_set_default_timeout(page: Page) -> None:
    page.set_default_timeout(1)
    with pytest.raises(TimeoutError) as exc:
        page.wait_for_function("false")
    assert "Timeout 1ms exceeded." in exc.value.message


def test_close_should_reject_all_promises(
    context: BrowserContext, sync_gather: Callable
) -> None:
    new_page = context.new_page()
    with pytest.raises(Error) as exc_info:
        sync_gather(
            lambda: new_page.evaluate("() => new Promise(r => {})"),
            lambda: new_page.close(),
        )
    assert TARGET_CLOSED_ERROR_MESSAGE in exc_info.value.message


def test_expect_response_should_work(page: Page, server: Server) -> None:
    with page.expect_response("**/*") as resp:
        page.goto(server.EMPTY_PAGE)
    assert resp.value
    assert resp.value.url == server.EMPTY_PAGE
    assert resp.value.status == 200
    assert resp.value.ok
    assert resp.value.request


def test_expect_response_should_not_hang_when_predicate_throws(page: Page) -> None:
    with pytest.raises(Exception, match="Oops!"):
        with page.expect_response("**/*"):
            raise Exception("Oops!")


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


def test_sync_playwright_stop_multiple_times() -> None:
    p = multiprocessing.Process(target=_test_sync_playwright_stop_multiple_times)
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


def test_call_sync_method_after_playwright_close_with_own_loop(
    server: Server, browser_name: str, launch_arguments: Dict[str, Any]
) -> None:
    p = multiprocessing.Process(
        target=_test_call_sync_method_after_playwright_close_with_own_loop,
        args=[browser_name, launch_arguments, server.EMPTY_PAGE],
    )
    p.start()
    p.join()
    assert p.exitcode == 0
