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

from typing import Callable, Dict

import pytest

from playwright.sync_api import BrowserContext, BrowserType, Page
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


def test_EM_013_should_think_that_it_is_focused_by_default(page: Page) -> None:
    assert page.evaluate("document.hasFocus()") is True


def test_EM_014_should_think_that_all_pages_are_focused_smoke(
    page: Page,
) -> None:
    page2 = page.context.new_page()
    assert page.evaluate("document.hasFocus()") is True
    assert page2.evaluate("document.hasFocus()") is True
    page2.close()


def test_EM_015_should_focus_popups_by_default(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    with page.expect_popup() as popup_info:
        page.evaluate("url => { window.open(url); }", server.EMPTY_PAGE)
    popup = popup_info.value
    assert popup.evaluate("document.hasFocus()") is True
    assert page.evaluate("document.hasFocus()") is True


def test_EM_016_should_provide_target_for_keyboard_events(
    page: Page, server: Server, sync_gather: Callable
) -> None:
    page2 = page.context.new_page()
    sync_gather(
        lambda: page.goto(server.PREFIX + "/input/textarea.html"),
        lambda: page2.goto(server.PREFIX + "/input/textarea.html"),
    )
    sync_gather(
        lambda: page.focus("input"),
        lambda: page2.focus("input"),
    )
    text = "first"
    text2 = "second"
    sync_gather(
        lambda: page.keyboard.type(text),
        lambda: page2.keyboard.type(text2),
    )
    results = sync_gather(
        lambda: page.evaluate("result"),
        lambda: page2.evaluate("result"),
    )
    assert results == [text, text2]


def test_EM_017_should_not_affect_mouse_event_target_page(
    page: Page, server: Server, sync_gather: Callable
) -> None:
    page2 = page.context.new_page()
    sync_gather(
        lambda: page.evaluate(CLICK_COUNTER),
        lambda: page2.evaluate(CLICK_COUNTER),
        lambda: page.focus("body"),
        lambda: page2.focus("body"),
    )
    sync_gather(
        lambda: page.mouse.click(1, 1),
        lambda: page2.mouse.click(1, 1),
    )
    counters = sync_gather(
        lambda: page.evaluate("window.clickCount"),
        lambda: page2.evaluate("window.clickCount"),
    )
    assert counters == [1, 1]


def test_EM_018_should_change_document_active_element(
    page: Page, server: Server, sync_gather: Callable
) -> None:
    page2 = page.context.new_page()
    sync_gather(
        lambda: page.goto(server.PREFIX + "/input/textarea.html"),
        lambda: page2.goto(server.PREFIX + "/input/textarea.html"),
    )
    sync_gather(
        lambda: page.focus("input"),
        lambda: page2.focus("textarea"),
    )
    active = sync_gather(
        lambda: page.evaluate("document.activeElement.tagName"),
        lambda: page2.evaluate("document.activeElement.tagName"),
    )
    assert active == ["INPUT", "TEXTAREA"]


def test_EM_019_should_not_affect_screenshots(
    page: Page,
    server: Server,
    browser_name: str,
    headless: bool,
    is_win: bool,
    is_linux: bool,
    assert_to_be_golden: Callable[[bytes, str], None],
    sync_gather: Callable,
) -> None:
    if browser_name == "webkit" and is_win and not headless:
        pytest.skip(
            "WebKit/Windows/headed has a larger minimal viewport. See https://github.com/microsoft/playwright/issues/22616"
        )
    if browser_name == "webkit" and is_linux and not headless:
        pytest.skip("WebKit headed has a larger minimal viewport on gtk4.")
    if browser_name == "firefox" and not headless:
        pytest.skip("Firefox headed produces a different image")

    page2 = page.context.new_page()
    sync_gather(
        lambda: page.set_viewport_size({"width": 500, "height": 500}),
        lambda: page.goto(server.PREFIX + "/grid.html"),
        lambda: page2.set_viewport_size({"width": 50, "height": 50}),
        lambda: page2.goto(server.PREFIX + "/grid.html"),
    )
    sync_gather(
        lambda: page.focus("body"),
        lambda: page2.focus("body"),
    )
    screenshots = sync_gather(
        lambda: page.screenshot(),
        lambda: page2.screenshot(),
    )
    assert_to_be_golden(screenshots[0], "screenshot-sanity.png")
    assert_to_be_golden(screenshots[1], "grid-cell-0.png")


def test_EM_020_should_change_focused_iframe(
    page: Page,
    server: Server,
    utils: Utils,
    browser_name: str,
    headless: bool,
    sync_gather: Callable,
) -> None:
    if browser_name == "firefox" and not headless:
        pytest.skip("Headed FF might lose focus")
    page.goto(server.EMPTY_PAGE)
    frame1, frame2 = sync_gather(
        lambda: utils.attach_frame(
            page, "frame1", server.PREFIX + "/input/textarea.html"
        ),
        lambda: utils.attach_frame(
            page, "frame2", server.PREFIX + "/input/textarea.html"
        ),
    )
    sync_gather(
        lambda: frame1.evaluate(LOGGER),
        lambda: frame2.evaluate(LOGGER),
    )
    focused = sync_gather(
        lambda: frame1.evaluate("document.hasFocus()"),
        lambda: frame2.evaluate("document.hasFocus()"),
    )
    assert focused == [False, False]

    frame1.focus("input")
    events = sync_gather(
        lambda: frame1.evaluate("self._events"),
        lambda: frame2.evaluate("self._events"),
    )
    assert events == [["focus"], []]
    focused = sync_gather(
        lambda: frame1.evaluate("document.hasFocus()"),
        lambda: frame2.evaluate("document.hasFocus()"),
    )
    assert focused == [True, False]

    frame2.focus("input")
    events = sync_gather(
        lambda: frame1.evaluate("self._events"),
        lambda: frame2.evaluate("self._events"),
    )
    assert events == [["focus", "blur"], ["focus"]]
    focused = sync_gather(
        lambda: frame1.evaluate("document.hasFocus()"),
        lambda: frame2.evaluate("document.hasFocus()"),
    )
    assert focused == [False, True]


# @see https://github.com/microsoft/playwright/issues/3476
def test_EM_021_should_focus_with_more_than_one_page_context(
    context_factory: Callable[..., BrowserContext],
) -> None:
    page1 = (context_factory()).new_page()
    page2 = (context_factory()).new_page()
    page1.set_content('<button id="foo" onfocus="window.gotFocus=true">foo</button>')
    page2.set_content('<button id="foo" onfocus="window.gotFocus=true">foo</button>')
    page1.focus("#foo")
    page2.focus("#foo")
    assert page1.evaluate("() => !!window['gotFocus']") is True
    assert page2.evaluate("() => !!window['gotFocus']") is True


def test_EM_022_should_not_fire_blur_events_when_interacting_with_more_than_one_page_context(
    context_factory: Callable[..., BrowserContext],
) -> None:
    page1 = (context_factory()).new_page()
    page2 = (context_factory()).new_page()
    page1.set_content('<button id="foo" onblur="window.gotBlur=true">foo</button>')
    page2.set_content('<button id="foo" onblur="window.gotBlur=true">foo</button>')
    page1.click("#foo")
    page2.click("#foo")
    assert page1.evaluate("() => !!window['gotBlur']") is False
    assert page2.evaluate("() => !!window['gotBlur']") is False


def test_EM_023_should_not_blur_iframe_when_interacting_with_another_page_context(
    context_factory: Callable[..., BrowserContext], browser_name: str
) -> None:
    if browser_name == "firefox":
        pytest.skip("fixme: https://github.com/microsoft/playwright/issues/43280")

    page1 = (context_factory()).new_page()
    page2 = (context_factory()).new_page()
    srcdoc = "<button id=foo>foo</button><script>window.addEventListener('blur', () => window.gotBlur = true)</script>"
    page1.set_content(
        f'<iframe srcdoc="{srcdoc}"></iframe><iframe srcdoc="{srcdoc}"></iframe>'
    )
    _, frame1, frame2 = page1.frames
    frame1.click("#foo")
    page2.set_content("<p>other page</p>")
    page2.mouse.click(10, 10)
    assert frame1.evaluate("() => !!window['gotBlur']") is False
    assert frame1.evaluate("() => document.hasFocus()") is True
    assert frame2.evaluate("() => document.hasFocus()") is False


def test_EM_024_should_trigger_hover_state_concurrently(
    browser_type: BrowserType, launch_arguments: Dict, headless: bool
) -> None:
    if not headless:
        pytest.skip("headed messes up with hover")

    browser1 = browser_type.launch(**launch_arguments)
    context1 = browser1.new_context()
    page1 = context1.new_page()
    page2 = context1.new_page()
    browser2 = browser_type.launch(**launch_arguments)
    page3 = browser2.new_page()

    for page in [page1, page2, page3]:
        page.set_content(
            """
      <style>
        button { display: none; }
        div:hover button { display: inline };
      </style>
      <div><span>hover me</span><button onclick="window.clicked=1+(window.clicked || 0)">click me</button></div>
    """
        )

    for page in [page1, page2, page3]:
        page.hover("span")
    for page in [page1, page2, page3]:
        page.click("button")
    for page in [page1, page2, page3]:
        assert page.evaluate("window.clicked") == 1
    for page in [page1, page2, page3]:
        page.click("button")
    for page in [page1, page2, page3]:
        assert page.evaluate("window.clicked") == 2

    browser1.close()
    browser2.close()
