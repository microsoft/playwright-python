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
from typing import Optional

import pytest

from playwright.async_api import Page
from tests.utils import must

from ..server import Server, TestServerRequest


async def test_console_event_should_work(page: Page) -> None:
    [message, _] = await asyncio.gather(
        page.context.wait_for_event("console"),
        page.evaluate("() => console.log('hello')"),
    )
    assert message.text == "hello"
    assert message.page == page


async def test_console_event_should_work_in_popup(page: Page) -> None:
    [message, popup, _] = await asyncio.gather(
        page.context.wait_for_event("console"),
        page.wait_for_event("popup"),
        page.evaluate(
            """() => {
            const win = window.open('');
            win.console.log('hello');
        }"""
        ),
    )
    assert message.text == "hello"
    assert message.page == popup


# console message from javascript: url is not reported at all
@pytest.mark.skip_browser("firefox")
async def test_console_event_should_work_in_popup_2(
    page: Page, browser_name: str
) -> None:
    [message, popup, _] = await asyncio.gather(
        page.context.wait_for_event("console", lambda msg: msg.type == "log"),
        page.context.wait_for_event("page"),
        page.evaluate(
            """async () => {
            const win = window.open('javascript:console.log("hello")');
            await new Promise(f => setTimeout(f, 0));
            win.close();
        }"""
        ),
    )
    assert message.text == "hello"
    assert message.page == popup


# console message from javascript: url is not reported at all
@pytest.mark.skip_browser("firefox")
async def test_console_event_should_work_in_immediately_closed_popup(
    page: Page, browser_name: str
) -> None:
    [message, popup, _] = await asyncio.gather(
        page.context.wait_for_event("console"),
        page.wait_for_event("popup"),
        page.evaluate(
            """async () => {
            const win = window.open();
            win.console.log('hello');
            win.close();
        }"""
        ),
    )
    assert message.text == "hello"
    assert message.page == popup


async def test_dialog_event_should_work1(page: Page) -> None:
    prompt_task: Optional[asyncio.Future[str]] = None

    async def open_dialog() -> None:
        nonlocal prompt_task
        prompt_task = asyncio.create_task(page.evaluate("() => prompt('hey?')"))

    [dialog1, dialog2, _] = await asyncio.gather(
        page.context.wait_for_event("dialog"),
        page.wait_for_event("dialog"),
        open_dialog(),
    )
    assert dialog1 == dialog2
    assert dialog1.message == "hey?"
    assert dialog1.page == page
    await dialog1.accept("hello")
    assert await must(prompt_task) == "hello"


async def test_dialog_event_should_work_in_popup(page: Page) -> None:
    prompt_task: Optional[asyncio.Future[str]] = None

    async def open_dialog() -> None:
        nonlocal prompt_task
        prompt_task = asyncio.create_task(
            page.evaluate("() => window.open('').prompt('hey?')")
        )

    [dialog, popup, _] = await asyncio.gather(
        page.context.wait_for_event("dialog"),
        page.wait_for_event("popup"),
        open_dialog(),
    )
    assert dialog.message == "hey?"
    assert dialog.page == popup
    await dialog.accept("hello")
    assert await must(prompt_task) == "hello"


# console message from javascript: url is not reported at all
@pytest.mark.skip_browser("firefox")
async def test_dialog_event_should_work_in_popup_2(
    page: Page, browser_name: str
) -> None:
    promise = asyncio.create_task(
        page.evaluate("() => window.open('javascript:prompt(\"hey?\")')")
    )
    dialog = await page.context.wait_for_event("dialog")
    assert dialog.message == "hey?"
    assert dialog.page is None
    await dialog.accept("hello")
    await promise


# console message from javascript: url is not reported at all
@pytest.mark.skip_browser("firefox")
async def test_dialog_event_should_work_in_immdiately_closed_popup(page: Page) -> None:
    [message, popup, _] = await asyncio.gather(
        page.context.wait_for_event("console"),
        page.wait_for_event("popup"),
        page.evaluate(
            """() => {
            const win = window.open();
            win.console.log('hello');
            win.close();
        }"""
        ),
    )
    assert message.text == "hello"
    assert message.page == popup


async def test_dialog_event_should_work_with_inline_script_tag(
    page: Page, server: Server
) -> None:
    def handle_route(request: TestServerRequest) -> None:
        request.setHeader("content-type", "text/html")
        request.write(b"""<script>window.result = prompt('hey?')</script>""")
        request.finish()

    server.set_route("/popup.html", handle_route)
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<a href='popup.html' target=_blank>Click me</a>")

    promise = asyncio.create_task(page.click("a"))
    [dialog, popup] = await asyncio.gather(
        page.context.wait_for_event("dialog"),
        page.wait_for_event("popup"),
    )

    assert dialog.message == "hey?"
    assert dialog.page == popup
    await dialog.accept("hello")
    await promise
    assert await popup.evaluate("window.result") == "hello"


async def test_console_event_should_work_with_context_manager(page: Page) -> None:
    async with page.context.expect_console_message() as cm_info:
        await page.evaluate("() => console.log('hello')")
    message = await cm_info.value
    assert message.text == "hello"
    assert message.page == page


async def test_page_error_event_should_work(page: Page) -> None:
    async with page.context.expect_event("weberror") as page_error_info:
        await page.set_content('<script>throw new Error("boom")</script>')
    page_error = await page_error_info.value
    assert page_error.page == page
    assert "boom" in page_error.error.stack
