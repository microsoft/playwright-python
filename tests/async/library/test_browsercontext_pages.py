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

"""Port of tests/library/browsercontext-pages.spec.ts."""

import asyncio
import re
import warnings
from typing import Awaitable, Callable

import pytest

from playwright.async_api import Browser, BrowserContext, Error, Playwright
from tests.server import Server
from tests.utils import must

from ..utils import Utils


async def test_BC_051_should_not_be_visible_in_context_pages(
    context_factory: Callable[..., Awaitable[BrowserContext]],
) -> None:
    context = await context_factory()
    page = await context.new_page()
    assert page in context.pages
    await page.close()
    assert page not in context.pages


async def test_BC_052_page_context_should_return_the_correct_instance(
    context_factory: Callable[..., Awaitable[BrowserContext]],
) -> None:
    context = await context_factory()
    page = await context.new_page()
    assert page.context == context


async def test_BC_053_frame_focus_should_work_multiple_times(
    context_factory: Callable[..., Awaitable[BrowserContext]],
) -> None:
    context = await context_factory()
    page1 = await context.new_page()
    page2 = await context.new_page()
    for page in [page1, page2]:
        await page.set_content(
            '<button id="foo" onfocus="window.gotFocus=true"></button>'
        )
        await page.focus("#foo")
        assert await page.evaluate("() => !!window['gotFocus']") is True


async def test_BC_054_should_click_with_disabled_javascript(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context(java_script_enabled=False)
    page = await context.new_page()
    await page.goto(server.PREFIX + "/wrappedlink.html")
    async with page.expect_navigation():
        await page.click("a")
    assert page.url == server.PREFIX + "/wrappedlink.html#clicked"
    await context.close()


async def test_BC_055_should_not_hang_with_touch_enabled_viewports(
    browser: Browser, playwright: Playwright
) -> None:
    # @see https://github.com/GoogleChrome/puppeteer/issues/161
    device = playwright.devices["iPhone 6"]
    context = await browser.new_context(
        viewport=device["viewport"], has_touch=device["has_touch"]
    )
    page = await context.new_page()
    await page.mouse.down()
    await page.mouse.move(100, 10)
    await page.mouse.up()
    await context.close()


async def test_BC_056_should_click_the_button_with_device_scale_factor_set(
    browser: Browser, server: Server, utils: Utils
) -> None:
    context = await browser.new_context(
        viewport={"width": 400, "height": 400}, device_scale_factor=5
    )
    page = await context.new_page()
    assert await page.evaluate("() => window.devicePixelRatio") == 5
    await page.set_content('<div style="width:100px;height:100px">spacer</div>')
    await utils.attach_frame(page, "button-test", server.PREFIX + "/input/button.html")
    frame = page.frames[1]
    button = await frame.query_selector("button")
    await must(button).click()
    assert await frame.evaluate("() => window['result']") == "Clicked"
    await context.close()


async def test_BC_057_should_click_the_button_with_offset_with_page_scale(
    browser: Browser, server: Server, browser_name: str
) -> None:
    if browser_name == "firefox":
        pytest.skip()

    context = await browser.new_context(
        viewport={"width": 400, "height": 400}, is_mobile=True
    )
    page = await context.new_page()
    await page.goto(server.PREFIX + "/input/button.html")
    await page.eval_on_selector(
        "button",
        """button => {
          button.style.borderWidth = '8px';
          document.body.style.margin = '0';
        }""",
    )
    await page.click("button", position={"x": 20, "y": 10})
    assert await page.evaluate("result") == "Clicked"

    def expect_close_to(expected: float, actual: float) -> None:
        if abs(expected - actual) > 2:
            raise Exception(f"Expected: {expected}, received: {actual}")

    # Expect 20;10 + 8px of border in each direction. Allow some delta as different
    # browsers round up or down differently during css -> dip -> css conversion.
    expect_close_to(28, await page.evaluate("pageX"))
    expect_close_to(18, await page.evaluate("pageY"))
    await context.close()


async def test_BC_058_should_return_bounding_box_with_page_scale(
    browser: Browser, server: Server, browser_name: str
) -> None:
    if browser_name == "firefox":
        pytest.skip()

    context = await browser.new_context(
        viewport={"width": 400, "height": 400}, is_mobile=True
    )
    page = await context.new_page()
    await page.goto(server.PREFIX + "/input/button.html")
    button = must(await page.query_selector("button"))
    await button.evaluate(
        """button => {
          document.body.style.margin = '0';
          button.style.borderWidth = '0';
          button.style.width = '200px';
          button.style.height = '20px';
          button.style.marginLeft = '17px';
          button.style.marginTop = '23px';
        }"""
    )
    box = must(await button.bounding_box())
    assert round(box["x"] * 100) == 17 * 100
    assert round(box["y"] * 100) == 23 * 100
    assert round(box["width"] * 100) == 200 * 100
    assert round(box["height"] * 100) == 20 * 100
    await context.close()


@pytest.mark.slow
async def test_BC_059_should_not_leak_listeners_during_navigation_of_20_pages(
    context_factory: Callable[..., Awaitable[BrowserContext]], server: Server
) -> None:
    context = await context_factory()
    # Upstream listens to Node.js process warnings (a listener leak warns there);
    # the Python counterpart is the warnings module.
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        pages = await asyncio.gather(*[context.new_page() for _ in range(20)])
        await asyncio.gather(*[page.goto(server.EMPTY_PAGE) for page in pages])
        await asyncio.gather(*[page.close() for page in pages])
    assert [str(warning.message) for warning in recorded] == []


async def test_BC_060_should_close_page_while_a_reload_is_committing(
    context: BrowserContext, browser_name: str
) -> None:
    if browser_name == "chromium":
        pytest.skip(
            "fixme: Chromium loses the close when the reload commits into a new RenderFrameHost; fix is not rolled yet"
        )
    # The evaluate never settles on its own, so it only rejects once the reload
    # commits. Closing right after that races the commit. Repeat a few times,
    # since whether the close or the commit wins is timing-dependent.
    for _ in range(10):
        page = await context.new_page()
        with pytest.raises(Error) as exc_info:
            await page.evaluate(
                """() => {
                  location.reload();
                  return new Promise(() => {});
                }"""
            )
        assert re.search(r"navigation", exc_info.value.message)
        await page.close()


async def test_BC_061_should_keep_selection_in_multiple_pages(
    context: BrowserContext,
) -> None:
    page1 = await context.new_page()
    page2 = await context.new_page()
    for page in [page1, page2]:
        await page.set_content('<div id="container">lorem ipsum dolor sit amet</div>')
        await page.evaluate(
            """() => {
              const element = document.getElementById('container');
              const textNode = element.firstChild;

              const range = document.createRange();
              range.setStart(textNode, 6);
              range.setEnd(textNode, 11);

              const selection = document.getSelection();
              selection?.removeAllRanges();
              selection?.addRange(range);
            }"""
        )
    # In WebKit, selection is updated via IPC, give it enough time to take effect.
    await asyncio.sleep(1)
    for page in [page1, page2]:
        range = await page.evaluate(
            """() => {
              const selection = document.getSelection();
              const range = selection?.getRangeAt(0);
              return {
                rangeCount: selection?.rangeCount,
                startOffset: range?.startOffset,
                endOffset: range?.endOffset,
              };
            }"""
        )
        assert range == {"rangeCount": 1, "startOffset": 6, "endOffset": 11}
