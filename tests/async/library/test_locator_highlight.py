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

"""Port of tests/library/locator-highlight.spec.ts."""

import pytest

from playwright.async_api import Browser, Playwright, expect
from tests.server import Server

from ..utils import Utils


async def test_LO_193_highlight_should_accept_a_css_string_style(
    browser: Browser, server: Server, browser_name: str, is_frozen_webkit: bool
) -> None:
    if is_frozen_webkit:
        pytest.skip("frozen WebKit")

    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(server.PREFIX + "/input/button.html")

    await page.get_by_role("button").highlight(
        style="outline: 3px solid rgb(255, 0, 0); background-color: rgba(0, 255, 0, 0.25)"
    )

    highlight = page.locator("x-pw-highlight")
    await expect(highlight).to_be_visible()
    style = await highlight.evaluate(
        """el => ({
    outline: el.style.outline,
    backgroundColor: el.style.backgroundColor,
  })"""
    )
    if browser_name == "chromium" or browser_name == "firefox":
        assert style["outline"] == "rgb(255, 0, 0) solid 3px"
    else:
        assert style["outline"] == "3px solid rgb(255, 0, 0)"
    assert style["backgroundColor"] == "rgba(0, 255, 0, 0.25)"

    await context.close()


async def test_LO_195_hide_highlight_removes_a_styled_highlight(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(server.PREFIX + "/input/button.html")

    button = page.get_by_role("button")
    await button.highlight(style="outline: 2px solid red")
    await expect(page.locator("x-pw-highlight")).to_be_visible()

    await button.hide_highlight()
    await expect(page.locator("x-pw-highlight")).to_have_count(0)

    await context.close()


async def test_LO_196_highlight_should_survive_navigation(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    await page.set_content('<button onclick="console.log(1)">Clicker</button>')

    await page.get_by_role("button").highlight()
    await expect(page.locator("x-pw-highlight")).to_have_count(1)

    # Highlights are resolved again after the navigation.
    await page.goto(server.PREFIX + "/input/button.html")
    await expect(page.locator("x-pw-highlight")).to_have_count(1)

    await page.hide_highlight()
    await expect(page.locator("x-pw-highlight")).to_have_count(0)

    await context.close()


async def test_LO_197_page_hide_highlight_clears_all_locator_highlights(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    await page.set_content("<button>One</button><button>Two</button>")

    await page.get_by_role("button", name="One").highlight()
    await page.get_by_role("button", name="Two").highlight()
    await expect(page.locator("x-pw-highlight")).to_have_count(2)

    await page.hide_highlight()
    await expect(page.locator("x-pw-highlight")).to_have_count(0)

    await context.close()


async def test_LO_198_highlight_should_work_with_a_custom_selector_engine_that_runs_in_the_main_world(
    playwright: Playwright, browser: Browser, utils: Utils
) -> None:
    # Engines registered without "contentScript" run in the main world and can see page globals.
    create_engine = """({
    query(root, selector) {
      return window['__engineEnabled'] ? root.querySelector(selector) : null;
    },
    queryAll(root, selector) {
      return window['__engineEnabled'] ? Array.from(root.querySelectorAll(selector)) : [];
    },
  })"""
    await utils.register_selector_engine(
        playwright.selectors, "highlight-tag", create_engine
    )

    context = await browser.new_context()
    page = await context.new_page()
    await page.set_content("<button>Button</button>")
    await page.evaluate("() => window['__engineEnabled'] = true")

    button = page.locator("highlight-tag=button")
    await button.highlight()
    await expect(page.locator("x-pw-highlight")).to_have_count(1)

    await button.hide_highlight()
    await expect(page.locator("x-pw-highlight")).to_have_count(0)

    await button.highlight()
    await expect(page.locator("x-pw-highlight")).to_have_count(1)

    await page.hide_highlight()
    await expect(page.locator("x-pw-highlight")).to_have_count(0)

    await context.close()


async def test_LO_199_highlight_should_resolve_relative_to_the_frame_of_the_locator(
    browser: Browser,
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    await page.set_content(
        '<iframe name="frame" srcdoc="<button>foo</button>"></iframe><button>bar</button>'
    )
    frame = page.frame(name="frame")
    assert frame

    await page.locator("button").highlight()
    await frame.locator("button").highlight()
    await expect(page.locator("x-pw-highlight")).to_have_count(1)
    await expect(frame.locator("x-pw-highlight")).to_have_count(1)

    await page.locator("button").hide_highlight()
    await expect(page.locator("x-pw-highlight")).to_have_count(0)
    await expect(frame.locator("x-pw-highlight")).to_have_count(1)

    await frame.locator("button").hide_highlight()
    await expect(frame.locator("x-pw-highlight")).to_have_count(0)

    await context.close()
