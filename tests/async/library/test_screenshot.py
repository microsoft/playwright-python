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

"""Port of tests/library/screenshot.spec.ts."""

import asyncio
from typing import Any, Awaitable, Callable

import pytest

from playwright.async_api import Browser, BrowserContext, Error, Page
from tests.helpers.image_compare import decode_image, pixel
from tests.server import Server, TestServerRequest

from ..utils import Utils

GoldenAssert = Callable[[bytes, str], None]
ContextFactory = Callable[..., Awaitable[BrowserContext]]


@pytest.fixture
def skip_firefox_headed(browser_name: str, headless: bool) -> None:
    """The skip of the upstream describes 'page screenshot' and 'element screenshot'."""
    if browser_name == "firefox" and not headless:
        pytest.skip("Firefox headed produces a different image.")


LARGER_THAN_VIEWPORT_CONTENT = """
      <div style="height: 14px">oooo</div>
      <style>
      div.to-screenshot {
        border: 4px solid red;
        box-sizing: border-box;
        width: 600px;
        height: 600px;
        margin-left: 50px;
        background: rgb(0, 100, 200);
      }
      ::-webkit-scrollbar{
        display: none;
      }
      </style>
      <div class="to-screenshot"></div>
    """


@pytest.mark.usefixtures("skip_firefox_headed")
async def test_SS_068_page_screenshot_should_run_in_parallel_in_multiple_pages(
    server: Server,
    context_factory: ContextFactory,
    assert_to_be_golden: GoldenAssert,
) -> None:
    context = await context_factory()
    n = 5

    async def new_page() -> Page:
        page = await context.new_page()
        await page.goto(server.PREFIX + "/grid.html")
        return page

    pages = await asyncio.gather(*[new_page() for _ in range(n)])
    screenshots = await asyncio.gather(
        *[
            pages[i].screenshot(
                clip={"x": 50 * (i % 2), "y": 0, "width": 50, "height": 50}
            )
            for i in range(n)
        ]
    )
    for i in range(n):
        assert_to_be_golden(
            screenshots[i],
            "grid-cell-0-upstream.png" if i % 2 == 0 else "grid-cell-1.png",
        )
    await asyncio.gather(*[page.close() for page in pages])


@pytest.mark.usefixtures("skip_firefox_headed")
async def test_SS_069_page_screenshot_should_work_with_a_mobile_viewport(
    browser: Browser,
    server: Server,
    browser_name: str,
    assert_to_be_golden: GoldenAssert,
) -> None:
    if browser_name == "firefox":
        pytest.skip("skipped upstream for firefox")

    context = await browser.new_context(
        viewport={"width": 320, "height": 480}, is_mobile=True
    )
    page = await context.new_page()
    await page.goto(server.PREFIX + "/overflow.html")
    screenshot = await page.screenshot()
    assert_to_be_golden(screenshot, "screenshot-mobile.png")
    await context.close()


@pytest.mark.usefixtures("skip_firefox_headed")
async def test_SS_070_page_screenshot_should_work_with_a_mobile_viewport_and_clip(
    browser: Browser,
    server: Server,
    browser_name: str,
    assert_to_be_golden: GoldenAssert,
) -> None:
    if browser_name == "firefox":
        pytest.skip("skipped upstream for firefox")

    context = await browser.new_context(
        viewport={"width": 320, "height": 480}, is_mobile=True
    )
    page = await context.new_page()
    await page.goto(server.PREFIX + "/overflow.html")
    screenshot = await page.screenshot(
        clip={"x": 10, "y": 10, "width": 100, "height": 150}
    )
    assert_to_be_golden(screenshot, "screenshot-mobile-clip.png")
    await context.close()


@pytest.mark.usefixtures("skip_firefox_headed")
async def test_SS_071_page_screenshot_should_work_with_a_mobile_viewport_and_full_page(
    browser: Browser,
    server: Server,
    browser_name: str,
    assert_to_be_golden: GoldenAssert,
) -> None:
    if browser_name == "firefox":
        pytest.skip("skipped upstream for firefox")

    context = await browser.new_context(
        viewport={"width": 320, "height": 480}, is_mobile=True
    )
    page = await context.new_page()
    await page.goto(server.PREFIX + "/overflow-large.html")
    screenshot = await page.screenshot(full_page=True)
    assert_to_be_golden(screenshot, "screenshot-mobile-fullpage.png")
    await context.close()


@pytest.mark.usefixtures("skip_firefox_headed")
async def test_SS_072_page_screenshot_should_work_with_device_scale_factor(
    browser: Browser, server: Server, assert_to_be_golden: GoldenAssert
) -> None:
    context = await browser.new_context(
        viewport={"width": 320, "height": 480}, device_scale_factor=2
    )
    page = await context.new_page()
    await page.goto(server.PREFIX + "/grid.html")
    screenshot = await page.screenshot()
    assert_to_be_golden(screenshot, "screenshot-device-scale-factor.png")
    await context.close()


@pytest.mark.usefixtures("skip_firefox_headed")
async def test_SS_073_page_screenshot_should_work_with_device_scale_factor_and_clip(
    browser: Browser, server: Server, assert_to_be_golden: GoldenAssert
) -> None:
    context = await browser.new_context(
        viewport={"width": 500, "height": 500}, device_scale_factor=3
    )
    page = await context.new_page()
    await page.goto(server.PREFIX + "/grid.html")
    screenshot = await page.screenshot(
        clip={"x": 50, "y": 100, "width": 150, "height": 100}
    )
    assert_to_be_golden(screenshot, "screenshot-device-scale-factor-clip.png")
    await context.close()


@pytest.mark.usefixtures("skip_firefox_headed")
async def test_SS_074_page_screenshot_should_work_with_device_scale_factor_and_scale_css(
    browser: Browser, server: Server, assert_to_be_golden: GoldenAssert
) -> None:
    context = await browser.new_context(
        viewport={"width": 320, "height": 480}, device_scale_factor=2
    )
    page = await context.new_page()
    await page.goto(server.PREFIX + "/grid.html")
    screenshot = await page.screenshot(scale="css")
    assert_to_be_golden(screenshot, "screenshot-device-scale-factor-css-size.png")
    await context.close()


@pytest.mark.usefixtures("skip_firefox_headed")
async def test_SS_075_page_screenshot_should_produce_screenshot_of_correct_size_with_scale_css_and_null_viewport(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context(no_viewport=True)
    page = await context.new_page()
    await page.goto(server.PREFIX + "/grid.html")
    [inner_width, inner_height] = await page.evaluate(
        "() => [window.innerWidth, window.innerHeight]"
    )
    screenshot = await page.screenshot(scale="css")
    decoded = decode_image(screenshot)
    assert decoded.width == inner_width
    assert decoded.height == inner_height
    await context.close()


@pytest.mark.usefixtures("skip_firefox_headed")
async def test_SS_076_page_screenshot_should_work_with_device_scale_factor_clip_and_scale_css(
    browser: Browser, server: Server, assert_to_be_golden: GoldenAssert
) -> None:
    context = await browser.new_context(
        viewport={"width": 500, "height": 500}, device_scale_factor=3
    )
    page = await context.new_page()
    await page.goto(server.PREFIX + "/grid.html")
    screenshot = await page.screenshot(
        clip={"x": 50, "y": 100, "width": 150, "height": 100}, scale="css"
    )
    assert_to_be_golden(screenshot, "screenshot-device-scale-factor-clip-css-size.png")
    await context.close()


@pytest.mark.usefixtures("skip_firefox_headed")
async def test_SS_077_page_screenshot_should_throw_if_screenshot_size_is_too_large_with_device_scale_factor(
    browser: Browser, browser_name: str, is_mac: bool
) -> None:
    context = await browser.new_context(
        viewport={"width": 500, "height": 500}, device_scale_factor=2
    )
    page = await context.new_page()

    await page.set_content(
        "<style>body {margin: 0; padding: 0;}</style><div style='min-height: 16383px; background: red;'></div>"
    )
    result = await page.screenshot(full_page=True)
    assert result

    await page.set_content(
        "<style>body {margin: 0; padding: 0;}</style><div style='min-height: 16384px; background: red;'></div>"
    )
    exception_message = ""
    try:
        await page.screenshot(full_page=True)
    except Error as e:
        exception_message = e.message
    if browser_name == "firefox" or (browser_name == "webkit" and not is_mac):
        assert "Cannot take screenshot larger than 32767" in exception_message

    image = await page.screenshot(full_page=True, scale="css")
    assert image
    await context.close()


@pytest.mark.usefixtures("skip_firefox_headed")
async def test_SS_078_page_screenshot_should_work_with_large_size(
    browser_name: str,
    headless: bool,
    platform: str,
    context_factory: ContextFactory,
) -> None:
    if browser_name == "chromium" and not headless and platform == "linux":
        pytest.skip("fixme: Chromium has gpu problems on linux with large screenshots")

    context = await context_factory()
    page = await context.new_page()

    await page.set_viewport_size({"width": 1280, "height": 800})
    await page.evaluate(
        """() => {
            document.body.style.margin = '0';
            document.body.style.padding = '0';
            document.documentElement.style.margin = '0';
            document.documentElement.style.padding = '0';
            const div = document.createElement('div');
            div.style.width = '1250px';
            div.style.height = '8440px';
            div.style.background = 'linear-gradient(red, blue)';
            document.body.appendChild(div);
        }"""
    )
    buffer = await page.screenshot(full_page=True)
    decoded = decode_image(buffer)

    assert pixel(decoded, 0, 0)[0] > 128
    assert pixel(decoded, 0, 0)[2] < 128
    assert pixel(decoded, 0, 8339)[0] < 128
    assert pixel(decoded, 0, 8339)[2] > 128


@pytest.mark.usefixtures("skip_firefox_headed")
async def test_SS_079_page_screenshot_should_handle_vh_units(
    context_factory: ContextFactory,
) -> None:
    context = await context_factory()
    page = await context.new_page()

    await page.set_viewport_size({"width": 800, "height": 500})
    await page.evaluate(
        """() => {
            document.body.style.margin = '0';
            document.body.style.padding = '0';
            document.documentElement.style.margin = '0';
            document.documentElement.style.padding = '0';
            const div = document.createElement('div');
            div.style.width = '100%';
            div.style.borderTop = '100vh solid red';
            div.style.borderBottom = '100vh solid blue';
            document.body.appendChild(div);
        }"""
    )
    buffer = await page.screenshot(full_page=True)
    decoded = decode_image(buffer)

    assert pixel(decoded, 0, 0)[0] > 128
    assert pixel(decoded, 0, 0)[2] < 128
    assert pixel(decoded, 0, 999)[0] < 128
    assert pixel(decoded, 0, 999)[2] > 128


@pytest.mark.usefixtures("skip_firefox_headed")
async def test_SS_081_element_screenshot_element_screenshot_should_work_with_a_mobile_viewport(
    browser: Browser,
    server: Server,
    browser_name: str,
    assert_to_be_golden: GoldenAssert,
) -> None:
    if browser_name == "firefox":
        pytest.skip("skipped upstream for firefox")

    context = await browser.new_context(
        viewport={"width": 320, "height": 480}, is_mobile=True
    )
    page = await context.new_page()
    await page.goto(server.PREFIX + "/grid.html")
    await page.evaluate("() => window.scrollBy(50, 100)")
    element_handle = await page.query_selector(".box:nth-of-type(3)")
    assert element_handle
    screenshot = await element_handle.screenshot()
    assert_to_be_golden(screenshot, "screenshot-element-mobile.png")
    await context.close()


@pytest.mark.usefixtures("skip_firefox_headed")
async def test_SS_082_element_screenshot_element_screenshot_should_work_with_device_scale_factor(
    browser: Browser,
    server: Server,
    browser_name: str,
    assert_to_be_golden: GoldenAssert,
) -> None:
    if browser_name == "firefox":
        pytest.skip("skipped upstream for firefox")

    context = await browser.new_context(
        viewport={"width": 320, "height": 480}, device_scale_factor=2
    )
    page = await context.new_page()
    await page.goto(server.PREFIX + "/grid.html")
    await page.evaluate("() => window.scrollBy(50, 100)")
    element_handle = await page.query_selector(".box:nth-of-type(3)")
    assert element_handle
    screenshot = await element_handle.screenshot()
    assert_to_be_golden(screenshot, "screenshot-element-mobile-dsf.png")
    await context.close()


@pytest.mark.usefixtures("skip_firefox_headed")
async def test_SS_083_element_screenshot_should_take_screenshots_when_default_viewport_is_null(
    browser: Browser,
) -> None:
    context = await browser.new_context(no_viewport=True)
    page = await context.new_page()
    await page.set_content("<div style='height: 10000px; background: red'></div>")
    window_size = await page.evaluate(
        "() => ({ width: window.innerWidth * window.devicePixelRatio, height: window.innerHeight * window.devicePixelRatio })"
    )
    size_before = await page.evaluate(
        "() => ({ width: document.body.offsetWidth, height: document.body.offsetHeight })"
    )

    screenshot = await page.screenshot()
    assert isinstance(screenshot, bytes)
    decoded = decode_image(screenshot)
    assert decoded.width == window_size["width"]
    assert decoded.height == window_size["height"]

    size_after = await page.evaluate(
        "() => ({ width: document.body.offsetWidth, height: document.body.offsetHeight })"
    )
    assert size_before["width"] == size_after["width"]
    assert size_before["height"] == size_after["height"]
    await context.close()


@pytest.mark.usefixtures("skip_firefox_headed")
async def test_SS_084_element_screenshot_should_take_full_page_screenshots_when_default_viewport_is_null(
    server: Server, browser: Browser
) -> None:
    context = await browser.new_context(no_viewport=True)
    page = await context.new_page()
    await page.goto(server.PREFIX + "/grid.html")
    size_before = await page.evaluate(
        "() => ({ width: document.body.offsetWidth, height: document.body.offsetHeight })"
    )
    screenshot = await page.screenshot(full_page=True)
    assert isinstance(screenshot, bytes)

    size_after = await page.evaluate(
        "() => ({ width: document.body.offsetWidth, height: document.body.offsetHeight })"
    )
    assert size_before["width"] == size_after["width"]
    assert size_before["height"] == size_after["height"]
    await context.close()


@pytest.mark.usefixtures("skip_firefox_headed")
async def test_SS_085_element_screenshot_should_restore_default_viewport_after_full_page_screenshot(
    browser: Browser, utils: Utils
) -> None:
    context = await browser.new_context(viewport={"width": 456, "height": 789})
    page = await context.new_page()
    await utils.verify_viewport(page, 456, 789)
    screenshot = await page.screenshot(full_page=True)
    assert isinstance(screenshot, bytes)
    await utils.verify_viewport(page, 456, 789)
    await context.close()


@pytest.mark.usefixtures("skip_firefox_headed")
async def test_SS_088_element_screenshot_should_take_element_screenshot_when_default_viewport_is_null_and_restore_back(
    browser: Browser,
) -> None:
    context = await browser.new_context(no_viewport=True)
    page = await context.new_page()
    await page.set_content(
        """
      <div style="height: 14px">oooo</div>
      <style>
      div.to-screenshot {
        border: 1px solid blue;
        width: 600px;
        height: 600px;
        margin-left: 50px;
      }
      ::-webkit-scrollbar{
        display: none;
      }
      </style>
      <div class="to-screenshot"></div>
      <div class="to-screenshot"></div>
      <div class="to-screenshot"></div>
    """
    )
    size_before = await page.evaluate(
        "() => ({ width: document.body.offsetWidth, height: document.body.offsetHeight })"
    )
    element_handle = await page.query_selector("div.to-screenshot")
    assert element_handle
    screenshot = await element_handle.screenshot()
    assert isinstance(screenshot, bytes)
    size_after = await page.evaluate(
        "() => ({ width: document.body.offsetWidth, height: document.body.offsetHeight })"
    )
    assert size_before["width"] == size_after["width"]
    assert size_before["height"] == size_after["height"]
    await context.close()


@pytest.mark.usefixtures("skip_firefox_headed")
async def test_SS_090_element_screenshot_element_screenshots_should_handle_vh_units(
    context_factory: ContextFactory,
) -> None:
    context = await context_factory()
    page = await context.new_page()

    await page.set_viewport_size({"width": 800, "height": 500})
    await page.evaluate(
        """() => {
            const div = document.createElement('div');
            div.style.width = '100%';
            div.style.borderTop = '100vh solid red';
            div.style.borderBottom = '100vh solid blue';
            document.body.appendChild(div);
        }"""
    )
    element_handle = await page.query_selector("div")
    assert element_handle
    buffer = await element_handle.screenshot()
    decoded = decode_image(buffer)

    assert pixel(decoded, 0, 0)[0] > 128
    assert pixel(decoded, 0, 0)[2] < 128
    assert pixel(decoded, 0, 999)[0] < 128
    assert pixel(decoded, 0, 999)[2] > 128


@pytest.mark.usefixtures("skip_firefox_headed")
async def test_SS_091_element_screenshot_should_work_if_the_main_resource_hangs(
    browser: Browser,
    browser_name: str,
    server: Server,
    assert_to_be_golden: GoldenAssert,
) -> None:
    if browser_name == "chromium":
        pytest.skip("https://github.com/microsoft/playwright/issues/9757")

    page = await browser.new_page()

    def handle_slow(request: TestServerRequest) -> Any:
        # Like res.writeHead() in Node.js: the headers are not sent, and the
        # response never ends.
        request.setResponseCode(200)
        request.setHeader("content-length", "4096")
        request.setHeader("content-type", "text/html")

    server.set_route("/slow", handle_slow)
    try:
        try:
            await page.goto(server.PREFIX + "/slow", timeout=1000)
        except Error:
            pass
        screenshot = await page.screenshot()
        assert_to_be_golden(screenshot, "hanging-main-resource.png")
    finally:
        await page.close()


@pytest.mark.usefixtures("skip_firefox_headed")
async def test_SS_092_element_screenshot_should_capture_full_element_when_larger_than_viewport_with_device_scale_factor(
    browser: Browser, assert_to_be_golden: GoldenAssert
) -> None:
    context = await browser.new_context(
        viewport={"width": 501, "height": 501}, device_scale_factor=2.5
    )
    page = await context.new_page()
    await page.set_content(LARGER_THAN_VIEWPORT_CONTENT)
    screenshot = await page.locator("div.to-screenshot").screenshot()
    assert_to_be_golden(screenshot, "element-larger-than-viewport-dsf.png")
    await context.close()


@pytest.mark.usefixtures("skip_firefox_headed")
async def test_SS_093_element_screenshot_should_capture_full_element_when_larger_than_viewport_with_device_scale_factor_and_scale_css(
    browser: Browser, assert_to_be_golden: GoldenAssert
) -> None:
    context = await browser.new_context(
        viewport={"width": 501, "height": 501}, device_scale_factor=2.5
    )
    page = await context.new_page()
    await page.set_content(LARGER_THAN_VIEWPORT_CONTENT)
    screenshot = await page.locator("div.to-screenshot").screenshot(scale="css")
    assert_to_be_golden(screenshot, "element-larger-than-viewport-dsf-css-size.png")
    await context.close()


@pytest.mark.usefixtures("skip_firefox_headed")
async def test_SS_094_element_screenshot_page_screenshot_should_capture_css_transform_with_device_pixels(
    browser: Browser, browser_name: str, assert_to_be_golden: GoldenAssert
) -> None:
    if browser_name == "webkit":
        pytest.skip("fixme: browserName === 'webkit'")
    context = await browser.new_context(
        viewport={"width": 500, "height": 500},
        device_scale_factor=3,
    )
    page = await context.new_page()
    await page.set_content(
        """
      <style>
      .container {
        width: 150px;
        height: 150px;
        margin: 75px 0 0 75px;
        border: none;
      }

      .cube {
        width: 100%;
        height: 100%;
        perspective: 550px;
        perspective-origin: 150% 150%;
      }

      .face {
        display: block;
        position: absolute;
        width: 100px;
        height: 100px;
        border: none;
      }

      .right {
        background: rgba(196, 0, 0, 0.7);
        transform: rotateY(70deg);
      }

      </style>
      <div class="container">
        <div class="cube showbf">
          <div class="face right"></div>
        </div>
      </div>
    """
    )

    # expect(page).toHaveScreenshot({ scale: 'device' }) takes the screenshot
    # with these options.
    screenshot = await page.screenshot(
        animations="disabled", caret="hide", scale="device"
    )
    assert_to_be_golden(
        screenshot,
        "element-screenshot-SS-094-page-screenshot-should-capture-css-transform-with-device-pixels-1.png",
    )
    await context.close()
