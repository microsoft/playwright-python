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

"""Port of tests/library/emulation-focus.spec.ts."""

import asyncio
from typing import Awaitable, Callable, Dict

import pytest

from playwright.async_api import BrowserContext, BrowserType, Page
from tests.server import Server

from ..utils import Utils

CLICK_COUNTER = """() => {
    document.onclick = () => window['clickCount'] = (window['clickCount'] || 0) + 1;
}"""

LOGGER = """() => {
    self['_events'] = [];
    const element = document.querySelector('input');
    element.onfocus = element.onblur = e => self['_events'].push(e.type);
}"""


async def test_EM_013_should_think_that_it_is_focused_by_default(page: Page) -> None:
    assert await page.evaluate("document.hasFocus()") is True


async def test_EM_014_should_think_that_all_pages_are_focused_smoke(
    page: Page,
) -> None:
    page2 = await page.context.new_page()
    assert await page.evaluate("document.hasFocus()") is True
    assert await page2.evaluate("document.hasFocus()") is True
    await page2.close()


async def test_EM_015_should_focus_popups_by_default(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_popup() as popup_info:
        await page.evaluate("url => { window.open(url); }", server.EMPTY_PAGE)
    popup = await popup_info.value
    assert await popup.evaluate("document.hasFocus()") is True
    assert await page.evaluate("document.hasFocus()") is True


async def test_EM_016_should_provide_target_for_keyboard_events(
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


async def test_EM_017_should_not_affect_mouse_event_target_page(
    page: Page, server: Server
) -> None:
    page2 = await page.context.new_page()
    await asyncio.gather(
        page.evaluate(CLICK_COUNTER),
        page2.evaluate(CLICK_COUNTER),
        page.focus("body"),
        page2.focus("body"),
    )
    await asyncio.gather(
        page.mouse.click(1, 1),
        page2.mouse.click(1, 1),
    )
    counters = await asyncio.gather(
        page.evaluate("window.clickCount"),
        page2.evaluate("window.clickCount"),
    )
    assert counters == [1, 1]


async def test_EM_018_should_change_document_active_element(
    page: Page, server: Server
) -> None:
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


async def test_EM_019_should_not_affect_screenshots(
    page: Page,
    server: Server,
    browser_name: str,
    headless: bool,
    is_win: bool,
    is_linux: bool,
    assert_to_be_golden: Callable[[bytes, str], None],
) -> None:
    if browser_name == "webkit" and is_win and not headless:
        pytest.skip(
            "WebKit/Windows/headed has a larger minimal viewport. See https://github.com/microsoft/playwright/issues/22616"
        )
    if browser_name == "webkit" and is_linux and not headless:
        pytest.skip("WebKit headed has a larger minimal viewport on gtk4.")
    if browser_name == "firefox" and not headless:
        pytest.skip("Firefox headed produces a different image")

    page2 = await page.context.new_page()
    await asyncio.gather(
        page.set_viewport_size({"width": 500, "height": 500}),
        page.goto(server.PREFIX + "/grid.html"),
        page2.set_viewport_size({"width": 50, "height": 50}),
        page2.goto(server.PREFIX + "/grid.html"),
    )
    await asyncio.gather(
        page.focus("body"),
        page2.focus("body"),
    )
    screenshots = await asyncio.gather(
        page.screenshot(),
        page2.screenshot(),
    )
    assert_to_be_golden(screenshots[0], "screenshot-sanity.png")
    assert_to_be_golden(screenshots[1], "grid-cell-0.png")


async def test_EM_020_should_change_focused_iframe(
    page: Page, server: Server, utils: Utils, browser_name: str, headless: bool
) -> None:
    if browser_name == "firefox" and not headless:
        pytest.skip("Headed FF might lose focus")
    await page.goto(server.EMPTY_PAGE)
    frame1, frame2 = await asyncio.gather(
        utils.attach_frame(page, "frame1", server.PREFIX + "/input/textarea.html"),
        utils.attach_frame(page, "frame2", server.PREFIX + "/input/textarea.html"),
    )
    await asyncio.gather(
        frame1.evaluate(LOGGER),
        frame2.evaluate(LOGGER),
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


# @see https://github.com/microsoft/playwright/issues/3476
async def test_EM_021_should_focus_with_more_than_one_page_context(
    context_factory: Callable[..., Awaitable[BrowserContext]],
) -> None:
    page1 = await (await context_factory()).new_page()
    page2 = await (await context_factory()).new_page()
    await page1.set_content(
        '<button id="foo" onfocus="window.gotFocus=true">foo</button>'
    )
    await page2.set_content(
        '<button id="foo" onfocus="window.gotFocus=true">foo</button>'
    )
    await page1.focus("#foo")
    await page2.focus("#foo")
    assert await page1.evaluate("() => !!window['gotFocus']") is True
    assert await page2.evaluate("() => !!window['gotFocus']") is True


async def test_EM_022_should_not_fire_blur_events_when_interacting_with_more_than_one_page_context(
    context_factory: Callable[..., Awaitable[BrowserContext]],
) -> None:
    page1 = await (await context_factory()).new_page()
    page2 = await (await context_factory()).new_page()
    await page1.set_content(
        '<button id="foo" onblur="window.gotBlur=true">foo</button>'
    )
    await page2.set_content(
        '<button id="foo" onblur="window.gotBlur=true">foo</button>'
    )
    await page1.click("#foo")
    await page2.click("#foo")
    assert await page1.evaluate("() => !!window['gotBlur']") is False
    assert await page2.evaluate("() => !!window['gotBlur']") is False


async def test_EM_023_should_not_blur_iframe_when_interacting_with_another_page_context(
    context_factory: Callable[..., Awaitable[BrowserContext]], browser_name: str
) -> None:
    if browser_name == "firefox":
        pytest.skip("fixme: https://github.com/microsoft/playwright/issues/43280")

    page1 = await (await context_factory()).new_page()
    page2 = await (await context_factory()).new_page()
    srcdoc = "<button id=foo>foo</button><script>window.addEventListener('blur', () => window.gotBlur = true)</script>"
    await page1.set_content(
        f'<iframe srcdoc="{srcdoc}"></iframe><iframe srcdoc="{srcdoc}"></iframe>'
    )
    _, frame1, frame2 = page1.frames
    await frame1.click("#foo")
    await page2.set_content("<p>other page</p>")
    await page2.mouse.click(10, 10)
    assert await frame1.evaluate("() => !!window['gotBlur']") is False
    assert await frame1.evaluate("() => document.hasFocus()") is True
    assert await frame2.evaluate("() => document.hasFocus()") is False


async def test_EM_024_should_trigger_hover_state_concurrently(
    browser_type: BrowserType, launch_arguments: Dict, headless: bool
) -> None:
    if not headless:
        pytest.skip("headed messes up with hover")

    browser1 = await browser_type.launch(**launch_arguments)
    context1 = await browser1.new_context()
    page1 = await context1.new_page()
    page2 = await context1.new_page()
    browser2 = await browser_type.launch(**launch_arguments)
    page3 = await browser2.new_page()

    for page in [page1, page2, page3]:
        await page.set_content(
            """
      <style>
        button { display: none; }
        div:hover button { display: inline };
      </style>
      <div><span>hover me</span><button onclick="window.clicked=1+(window.clicked || 0)">click me</button></div>
    """
        )

    for page in [page1, page2, page3]:
        await page.hover("span")
    for page in [page1, page2, page3]:
        await page.click("button")
    for page in [page1, page2, page3]:
        assert await page.evaluate("window.clicked") == 1
    for page in [page1, page2, page3]:
        await page.click("button")
    for page in [page1, page2, page3]:
        assert await page.evaluate("window.clicked") == 2

    await browser1.close()
    await browser2.close()
