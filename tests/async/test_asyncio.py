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
import asyncio
import gc
import os
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Dict

import pytest

from playwright.async_api import Page, async_playwright
from tests.server import Server
from tests.utils import TARGET_CLOSED_ERROR_MESSAGE


async def test_should_cancel_underlying_protocol_calls(
    browser_name: str,
    launch_arguments: Dict,
) -> None:
    handler_exception = None

    def exception_handlerdler(loop: asyncio.AbstractEventLoop, context: Dict) -> None:
        nonlocal handler_exception
        handler_exception = context["exception"]

    asyncio.get_running_loop().set_exception_handler(exception_handlerdler)

    async with async_playwright() as p:
        browser = await p[browser_name].launch(**launch_arguments)
        page = await browser.new_page()
        await page.set_content(
            """
            <button disabled onclick="window.clicked = true">click me</button>
            <script>window.clicked = false</script>
            """
        )
        task = asyncio.create_task(page.locator("button").click(timeout=0))
        await page.wait_for_timeout(100)
        assert not task.done()

        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        await page.locator("button").evaluate("button => button.disabled = false")
        await page.wait_for_timeout(700)
        assert not await page.evaluate("window.clicked")
        await browser.close()

    # The actual 'Future exception was never retrieved' is logged inside the Future destructor (__del__).
    gc.collect()

    assert handler_exception is None

    asyncio.get_running_loop().set_exception_handler(None)


async def test_async_playwright_stop_multiple_times() -> None:
    playwright = await async_playwright().start()
    await playwright.stop()
    await playwright.stop()


async def test_cancel_pending_protocol_call_on_playwright_stop(server: Server) -> None:
    server.set_route("/hang", lambda _: None)
    playwright = await async_playwright().start()
    api_request_context = await playwright.request.new_context()
    pending_task = asyncio.create_task(api_request_context.get(server.PREFIX + "/hang"))
    await playwright.stop()
    with pytest.raises(Exception) as exc_info:
        await pending_task
    assert TARGET_CLOSED_ERROR_MESSAGE in str(exc_info.value)


async def test_should_not_throw_with_taskgroup(page: Page) -> None:
    if sys.version_info < (3, 11):
        pytest.skip("TaskGroup is only available in Python 3.11+")

    from builtins import ExceptionGroup  # type: ignore

    async def raise_exception() -> None:
        raise ValueError("Something went wrong")

    with pytest.raises(ExceptionGroup) as exc_info:
        async with asyncio.TaskGroup() as group:  # type: ignore
            group.create_task(page.locator(".this-element-does-not-exist").inner_text())
            group.create_task(raise_exception())
    assert len(exc_info.value.exceptions) == 1
    assert "Something went wrong" in str(exc_info.value.exceptions[0])
    assert isinstance(exc_info.value.exceptions[0], ValueError)
    assert await page.evaluate("() => 11 * 11") == 121


def test_stop_does_not_deadlock_with_asyncio_atexit(tmp_path: Path) -> None:
    # Regression test for https://github.com/microsoft/playwright-python/issues/3004.
    # asyncio.run() cancels all remaining tasks (including transport.run()) before
    # calling loop.close(). asyncio-atexit hooks loop.close() to run async cleanup,
    # so awaiting playwright.stop() at that point used to deadlock on a future that
    # the (already cancelled) run task would never set.
    script = tmp_path / "atexit_stop.py"
    script.write_text(
        textwrap.dedent(
            """
            import asyncio

            import asyncio_atexit
            from playwright.async_api import async_playwright


            async def main():
                pw = await async_playwright().start()
                asyncio_atexit.register(lambda: stop(pw))


            async def stop(pw):
                await pw.stop()
                print("STOPPED", flush=True)


            asyncio.run(main())
            """
        )
    )
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "STOPPED" in result.stdout


async def test_should_return_proper_api_name_on_error(page: Page) -> None:
    try:
        await page.evaluate("does_not_exist")

        assert (
            False
        ), "Accessing undefined JavaScript variable should have thrown exception"
    except Exception as error:
        # Each browser returns slightly different error messages, but they should all start with "Page.evaluate:", because that was the Playwright method where the error originated
        assert str(error).startswith("Page.evaluate:")


async def test_no_orphaned_future_on_serialization_error(
    browser_name: str,
    launch_arguments: Dict,
) -> None:
    # When transport.send fails (e.g. non-JSON-serializable params), the protocol
    # callback must not be left for cleanup() to reject — that yields
    # "Future exception was never retrieved". See issue #3165.
    handler_exception = None

    def exception_handler(loop: asyncio.AbstractEventLoop, context: Dict) -> None:
        nonlocal handler_exception
        handler_exception = context.get("exception")

    asyncio.get_running_loop().set_exception_handler(exception_handler)
    try:
        async with async_playwright() as p:
            browser = await p[browser_name].launch(**launch_arguments)
            page = await browser.new_page()
            with pytest.raises(TypeError, match="JSON serializable"):
                await page.locator("asdf").highlight(style=object())  # type: ignore[arg-type]
            await browser.close()
        gc.collect()
        assert handler_exception is None
    finally:
        asyncio.get_running_loop().set_exception_handler(None)


async def test_no_orphaned_future_on_send_may_fail_teardown(
    browser_name: str,
    launch_arguments: Dict,
    tmp_path: Path,
) -> None:
    # Mirrors pytest-playwright session teardown: background send_may_fail work,
    # then browser.close() + playwright.stop(). Also covers unexpected driver death
    # before stop (transport EOF → connection.cleanup). See issue #3165.
    script = tmp_path / "repro_may_fail.py"
    script.write_text(
        textwrap.dedent(
            f"""
            import asyncio
            import gc
            import os
            import signal

            from playwright.async_api import async_playwright

            async def session(kill_driver: bool) -> None:
                p = await async_playwright().start()
                browser = await p["{browser_name}"].launch(**{launch_arguments!r})
                page = await browser.new_page()
                channel = page._impl_obj._channel
                for _ in range(20):
                    channel.send_may_fail("bringToFront", None, {{}})
                await asyncio.sleep(0)
                if kill_driver:
                    os.kill(
                        page._impl_obj._connection._transport._proc.pid,
                        signal.SIGKILL,
                    )
                    await asyncio.sleep(0.01)
                else:
                    await browser.close()
                try:
                    await p.stop()
                except Exception:
                    pass

            async def main() -> None:
                for i in range(40):
                    await session(kill_driver=(i % 2 == 0))
                    gc.collect()
                await asyncio.sleep(0.1)
                gc.collect()

            asyncio.run(main())
            """
        )
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2])
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        timeout=180,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert "Future exception was never retrieved" not in result.stderr
