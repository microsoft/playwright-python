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

from playwright.async_api import Page
from tests.server import Server

from .utils import Utils


async def test_should_think_that_it_is_focused_by_default(page: Page) -> None:
    assert await page.evaluate("document.hasFocus()")


async def test_should_think_that_all_pages_are_focused(page: Page) -> None:
    page2 = await page.context.new_page()
    assert await page.evaluate("document.hasFocus()")
    assert await page2.evaluate("document.hasFocus()")
    await page2.close()


async def test_should_focus_popups_by_default(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_popup() as popup_info:
        await page.evaluate("url => { window.open(url); }", server.EMPTY_PAGE)
    popup = await popup_info.value
    assert await popup.evaluate("document.hasFocus()")
    assert await page.evaluate("document.hasFocus()")


async def test_should_provide_target_for_keyboard_events(
    page: Page, server: Server
) -> None:
    page2 = await page.context.new_page()
    await asyncio.gather(
        page.goto(server.PREFIX + "/input/textarea.html"),
        page2.goto(server.PREFIX + "/input/textarea.html"),
    )
    await asyncio.gather(
        page.focus("input"),
        page2.focus("input"),
    )
    text = "first"
    text2 = "second"
    await asyncio.gather(
        page.keyboard.type(text),
        page2.keyboard.type(text2),
    )
    results = await asyncio.gather(
        page.evaluate("result"),
        page2.evaluate("result"),
    )
    assert results == [text, text2]


async def test_should_not_affect_mouse_event_target_page(
    page: Page, server: Server
) -> None:
    page2 = await page.context.new_page()
    click_counter = """() => {
      document.onclick = () => window.click_count = (window.click_count || 0) + 1;
    }"""
    await asyncio.gather(
        page.evaluate(click_counter),
        page2.evaluate(click_counter),
        page.focus("body"),
        page2.focus("body"),
    )
    await asyncio.gather(
        page.mouse.click(1, 1),
        page2.mouse.click(1, 1),
    )
    counters = await asyncio.gather(
        page.evaluate("window.click_count"),
        page2.evaluate("window.click_count"),
    )
    assert counters == [1, 1]


async def test_should_change_document_activeElement(page: Page, server: Server) -> None:
    page2 = await page.context.new_page()
    await asyncio.gather(
        page.goto(server.PREFIX + "/input/textarea.html"),
        page2.goto(server.PREFIX + "/input/textarea.html"),
    )
    await asyncio.gather(
        page.focus("input"),
        page2.focus("textarea"),
    )
    active = await asyncio.gather(
        page.evaluate("document.activeElement.tagName"),
        page2.evaluate("document.activeElement.tagName"),
    )
    assert active == ["INPUT", "TEXTAREA"]


async def test_should_change_focused_iframe(
    page: Page, server: Server, utils: Utils
) -> None:
    await page.goto(server.EMPTY_PAGE)
    [frame1, frame2] = await asyncio.gather(
        utils.attach_frame(page, "frame1", server.PREFIX + "/input/textarea.html"),
        utils.attach_frame(page, "frame2", server.PREFIX + "/input/textarea.html"),
    )
    logger = """() => {
        self._events = [];
        const element = document.querySelector('input');
        element.onfocus = element.onblur = (e) => self._events.push(e.type);
    }"""
    await asyncio.gather(
        frame1.evaluate(logger),
        frame2.evaluate(logger),
    )
    focused = await asyncio.gather(
        frame1.evaluate("document.hasFocus()"),
        frame2.evaluate("document.hasFocus()"),
    )
    assert focused == [False, False]
    await frame1.focus("input")
    events = await asyncio.gather(
        frame1.evaluate("self._events"),
        frame2.evaluate("self._events"),
    )
    assert events == [["focus"], []]
    focused = await asyncio.gather(
        frame1.evaluate("document.hasFocus()"),
        frame2.evaluate("document.hasFocus()"),
    )
    assert focused == [True, False]
    await frame2.focus("input")
    events = await asyncio.gather(
        frame1.evaluate("self._events"),
        frame2.evaluate("self._events"),
    )
    assert events == [["focus", "blur"], ["focus"]]
    focused = await asyncio.gather(
        frame1.evaluate("document.hasFocus()"),
        frame2.evaluate("document.hasFocus()"),
    )
    assert focused == [False, True]
