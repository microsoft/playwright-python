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

"""Port of tests/library/browsercontext-events.spec.ts."""

import asyncio
import time
from typing import Any, Awaitable, Callable

import pytest

from playwright.async_api import BrowserContext, Page
from tests.server import Server, TestServerRequest
from tests.utils import must


async def poll_until_equal(
    actual: Callable[[], Awaitable[Any]], expected: Any, timeout: float = 5000
) -> None:
    """Port of `await expect.poll(actual).toBe(expected)`."""
    deadline = time.monotonic() + timeout / 1000
    value = await actual()
    while value != expected and time.monotonic() < deadline:
        await asyncio.sleep(0.1)
        value = await actual()
    assert value == expected


async def test_BC_032_console_event_should_work_smoke(page: Page) -> None:
    async with page.context.expect_event("console") as message_info:
        await page.evaluate("() => console.log('hello')")
    message = await message_info.value

    assert message.text == "hello"
    assert message.page == page


async def test_BC_033_console_event_should_work_with_element_handles(
    page: Page,
) -> None:
    await page.set_content("<body>hello</body>")
    async with page.context.expect_event("console") as message_info:
        await page.evaluate("() => console.log(document.body)")
    message = await message_info.value
    body = message.args[0]
    assert await body.evaluate("x => x.nodeName") == "BODY"
    await must(body.as_element()).click()


async def test_BC_034_console_event_should_work_in_popup(page: Page) -> None:
    async with page.context.expect_event("console") as message_info:
        async with page.expect_popup() as popup_info:
            await page.evaluate(
                """() => {
                  const win = window.open('');
                  win.console.log('hello');
                }"""
            )
    message = await message_info.value
    popup = await popup_info.value

    assert message.text == "hello"
    assert message.page == popup


async def test_BC_035_console_event_should_work_in_popup_2(
    page: Page, browser_name: str
) -> None:
    if browser_name == "firefox":
        pytest.skip(
            "fixme: console message from javascript: url is not reported at all"
        )

    async with page.context.expect_event(
        "console", lambda msg: msg.type == "log"
    ) as message_info:
        async with page.context.expect_event("page") as popup_info:
            await page.evaluate(
                """async () => {
                  const win = window.open('javascript:console.log("hello")');
                  await new Promise(f => window.builtins.setTimeout(f, 0));
                  win.close();
                }"""
            )
    message = await message_info.value
    popup = await popup_info.value

    assert message.text == "hello"
    assert message.page == popup


async def test_BC_036_console_event_should_work_in_immediately_closed_popup(
    page: Page, browser_name: str
) -> None:
    if browser_name == "firefox":
        pytest.skip("fixme: console message is not reported at all")

    async with page.context.expect_event("console") as message_info:
        async with page.expect_popup() as popup_info:
            await page.evaluate(
                """async () => {
                  const win = window.open();
                  win.console.log('hello');
                  win.close();
                }"""
            )
    message = await message_info.value
    popup = await popup_info.value

    assert message.text == "hello"
    assert message.page == popup


async def test_BC_037_dialog_event_should_work_smoke(page: Page) -> None:
    async def run_prompt() -> Any:
        return await page.evaluate("() => prompt('hey?')")

    async def handle_dialog() -> None:
        async with page.context.expect_event("dialog") as dialog1_info:
            async with page.expect_event("dialog") as dialog2_info:
                pass
        dialog1 = await dialog1_info.value
        dialog2 = await dialog2_info.value

        assert dialog1 == dialog2
        assert dialog1.message == "hey?"
        assert dialog1.page == page
        await dialog1.accept("hello")

    # Listen first: the driver dismisses a dialog that nobody listens for yet.
    [_, result] = await asyncio.gather(handle_dialog(), run_prompt())
    assert result == "hello"


async def test_BC_038_dialogclosed_event_should_work(page: Page) -> None:
    async def run_prompt() -> Any:
        return await page.evaluate("() => prompt('hey?')")

    async def handle_dialog() -> None:
        dialog = await page.context.wait_for_event("dialog")
        async with page.context.expect_event("dialogclosed") as closed1_info:
            async with page.expect_event("dialogclosed") as closed2_info:
                await dialog.accept("hello")
        assert await closed1_info.value == dialog
        assert await closed2_info.value == dialog

    # Listen first: the driver dismisses a dialog that nobody listens for yet.
    [_, result] = await asyncio.gather(handle_dialog(), run_prompt())
    assert result == "hello"


async def test_BC_039_dialog_event_should_work_in_popup(page: Page) -> None:
    async def run_prompt() -> Any:
        return await page.evaluate(
            """() => {
              const win = window.open('');
              return win.prompt('hey?');
            }"""
        )

    async def handle_dialog() -> None:
        async with page.context.expect_event("dialog") as dialog_info:
            async with page.expect_popup() as popup_info:
                pass
        dialog = await dialog_info.value
        popup = await popup_info.value

        assert dialog.message == "hey?"
        assert dialog.page == popup
        await dialog.accept("hello")

    # Listen first: the driver dismisses a dialog that nobody listens for yet.
    [_, result] = await asyncio.gather(handle_dialog(), run_prompt())
    assert result == "hello"


async def test_BC_040_dialog_event_should_work_in_popup_2(
    page: Page, browser_name: str
) -> None:
    if browser_name == "firefox":
        pytest.skip("fixme: dialog from javascript: url is not reported at all")

    async def open_popup() -> None:
        await page.evaluate(
            """async () => {
              window.open('javascript:prompt("hey?")');
            }"""
        )

    async def handle_dialog() -> None:
        dialog = await page.context.wait_for_event("dialog")

        assert dialog.message == "hey?"
        assert dialog.page is None
        await dialog.accept("hello")

    await asyncio.gather(open_popup(), handle_dialog())


async def test_BC_041_dialog_event_should_work_in_immediately_closed_popup(
    page: Page,
) -> None:
    async def run_prompt() -> Any:
        return await page.evaluate(
            """async () => {
              const win = window.open();
              const result = win.prompt('hey?');
              win.close();
              return result;
            }"""
        )

    async def handle_dialog() -> None:
        async with page.context.expect_event("dialog") as dialog_info:
            async with page.expect_popup() as popup_info:
                pass
        dialog = await dialog_info.value
        popup = await popup_info.value

        assert dialog.message == "hey?"
        assert dialog.page == popup
        await dialog.accept("hello")

    # Listen first: the driver dismisses a dialog that nobody listens for yet.
    [_, result] = await asyncio.gather(handle_dialog(), run_prompt())
    assert result == "hello"


async def test_BC_042_dialog_event_should_work_with_inline_script_tag(
    page: Page, server: Server
) -> None:
    def handler(request: TestServerRequest) -> None:
        request.setHeader("content-type", "text/html")
        request.write(b"<script>window.result = prompt('hey?')</script>")
        request.finish()

    server.set_route("/popup.html", handler)

    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<a href='popup.html' target=_blank>Click me</a>")

    async def click() -> None:
        await page.click("a")

    async def handle_dialog() -> Page:
        async with page.context.expect_event("dialog") as dialog_info:
            async with page.context.expect_event("page") as popup_info:
                pass
        dialog = await dialog_info.value
        popup = await popup_info.value

        assert dialog.message == "hey?"
        assert dialog.page == popup
        await dialog.accept("hello")
        return popup

    # Listen first: the driver dismisses a dialog that nobody listens for yet.
    [popup, _] = await asyncio.gather(handle_dialog(), click())
    await poll_until_equal(lambda: popup.evaluate("window.result"), "hello")


async def test_BC_043_weberror_event_should_work(page: Page) -> None:
    async with page.context.expect_event("weberror") as web_error_info:
        await page.set_content('<script>throw new Error("boom")</script>')
    web_error = await web_error_info.value
    assert web_error.page == page
    assert "boom" in must(web_error.error.stack)


async def test_BC_044_weberror_event_should_include_location(
    page: Page, server: Server
) -> None:
    def handle_error_js(request: TestServerRequest) -> None:
        request.setHeader("content-type", "application/javascript")
        request.write(
            b"""
      function foo() {
        throw new Error('boom');
      }
      foo();
    """
        )
        request.finish()

    server.set_route("/error.js", handle_error_js)

    def handle_error_html(request: TestServerRequest) -> None:
        request.setHeader("content-type", "text/html")
        request.write(b'<script src="/error.js"></script>')
        request.finish()

    server.set_route("/error.html", handle_error_html)

    async with page.context.expect_event("weberror") as web_error_info:
        await page.goto(server.PREFIX + "/error.html")
    web_error = await web_error_info.value

    location = web_error.location
    assert location["url"] == f"{server.PREFIX}/error.js"
    assert location["line"] == 2
    # column is not consistent across browsers
    assert location["column"] > 0


async def test_BC_045_pageload_event_should_work_smoke(
    page: Page, server: Server
) -> None:
    async with page.context.expect_event("pageload") as event_page_info:
        await page.goto(server.EMPTY_PAGE)
    event_page = await event_page_info.value
    assert event_page == page


async def test_BC_046_framenavigated_event_should_work_smoke(
    page: Page, server: Server
) -> None:
    async with page.context.expect_event("framenavigated") as frame_info:
        await page.goto(server.EMPTY_PAGE)
    frame = await frame_info.value
    assert frame == page.main_frame
    assert frame.url == server.EMPTY_PAGE


async def test_BC_047_pageclose_event_should_work_smoke(
    context: BrowserContext,
) -> None:
    page = await context.new_page()
    async with context.expect_event("pageclose") as closed_info:
        await page.close()
    closed = await closed_info.value
    assert closed == page


async def test_BC_048_frameattached_event_should_work_smoke(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    async with page.context.expect_event("frameattached") as frame_info:
        await page.evaluate(
            """() => {
              const iframe = document.createElement('iframe');
              iframe.src = 'about:blank';
              document.body.appendChild(iframe);
            }"""
        )
    frame = await frame_info.value
    assert frame.parent_frame == page.main_frame


async def test_BC_049_framedetached_event_should_work_smoke(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.evaluate(
        """() => {
          const iframe = document.createElement('iframe');
          iframe.id = 'x';
          iframe.src = 'about:blank';
          document.body.appendChild(iframe);
        }"""
    )
    await page.wait_for_selector("iframe")
    async with page.context.expect_event("framedetached") as frame_info:
        await page.evaluate("() => document.getElementById('x').remove()")
    frame = await frame_info.value
    assert frame.parent_frame == page.main_frame


async def test_BC_050_download_event_should_work_smoke(
    page: Page, server: Server
) -> None:
    def handler(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "application/octet-stream")
        request.setHeader("Content-Disposition", "attachment; filename=file.txt")
        request.write(b"Hello world")
        request.finish()

    server.set_route("/download", handler)
    await page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    async with page.context.expect_event("download") as download_info:
        await page.click("a")
    download = await download_info.value
    assert download.suggested_filename == "file.txt"
    assert download.page == page
