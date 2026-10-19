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

"""Port of tests/library/browsercontext-viewport.spec.ts."""

from typing import Any, Callable, Dict

import pytest

from playwright.sync_api import Browser, BrowserContext, Error, Page, Playwright
from tests.server import Server

from ..utils import Utils

ContextFactory = Callable[..., BrowserContext]


def test_VP_001_should_get_the_proper_default_viewport_size(
    page: Page, utils: Utils
) -> None:
    utils.verify_viewport(page, 1280, 720)


def test_VP_002_should_set_the_proper_viewport_size(page: Page, utils: Utils) -> None:
    utils.verify_viewport(page, 1280, 720)
    page.set_viewport_size({"width": 345, "height": 456})
    utils.verify_viewport(page, 345, 456)


def test_VP_003_should_return_correct_outer_width_and_outer_height(
    page: Page,
) -> None:
    page.set_viewport_size({"width": 410, "height": 420})
    size = page.evaluate(
        """() => {
            return {
                innerWidth: window.innerWidth,
                innerHeight: window.innerHeight,
                outerWidth: window.outerWidth,
                outerHeight: window.outerHeight,
            };
        }"""
    )
    assert size["innerWidth"] == 410
    assert size["innerHeight"] == 420
    assert size["outerWidth"] >= size["innerWidth"]
    assert size["outerHeight"] >= size["innerHeight"]


def test_VP_004_landscape_viewport_should_have_width_larger_than_height(
    playwright: Playwright,
) -> None:
    for device, configuration in playwright.devices.items():
        if "landscape" in device or "Landscape" in device:
            assert (
                configuration["viewport"]["width"] > configuration["viewport"]["height"]
            )


def test_VP_005_should_emulate_device_width(page: Page) -> None:
    assert page.viewport_size == {"width": 1280, "height": 720}
    page.set_viewport_size({"width": 300, "height": 300})
    assert page.evaluate("() => window.screen.width") == 300
    assert (
        page.evaluate("() => matchMedia('(min-device-width: 200px)').matches") is True
    )
    assert (
        page.evaluate("() => matchMedia('(min-device-width: 400px)').matches") is False
    )
    assert (
        page.evaluate("() => matchMedia('(max-device-width: 200px)').matches") is False
    )
    assert (
        page.evaluate("() => matchMedia('(max-device-width: 400px)').matches") is True
    )
    assert page.evaluate("() => matchMedia('(device-width: 600px)').matches") is False
    assert page.evaluate("() => matchMedia('(device-width: 300px)').matches") is True
    page.set_viewport_size({"width": 500, "height": 500})
    assert page.evaluate("() => window.screen.width") == 500
    assert (
        page.evaluate("() => matchMedia('(min-device-width: 400px)').matches") is True
    )
    assert (
        page.evaluate("() => matchMedia('(min-device-width: 600px)').matches") is False
    )
    assert (
        page.evaluate("() => matchMedia('(max-device-width: 400px)').matches") is False
    )
    assert (
        page.evaluate("() => matchMedia('(max-device-width: 600px)').matches") is True
    )
    assert page.evaluate("() => matchMedia('(device-width: 200px)').matches") is False
    assert page.evaluate("() => matchMedia('(device-width: 500px)').matches") is True


def test_VP_006_should_emulate_device_height(page: Page) -> None:
    assert page.viewport_size == {"width": 1280, "height": 720}
    page.set_viewport_size({"width": 300, "height": 300})
    assert page.evaluate("() => window.screen.height") == 300
    assert (
        page.evaluate("() => matchMedia('(min-device-height: 200px)').matches") is True
    )
    assert (
        page.evaluate("() => matchMedia('(min-device-height: 400px)').matches") is False
    )
    assert (
        page.evaluate("() => matchMedia('(max-device-height: 200px)').matches") is False
    )
    assert (
        page.evaluate("() => matchMedia('(max-device-height: 400px)').matches") is True
    )
    assert page.evaluate("() => matchMedia('(device-height: 600px)').matches") is False
    assert page.evaluate("() => matchMedia('(device-height: 300px)').matches") is True
    page.set_viewport_size({"width": 500, "height": 500})
    assert page.evaluate("() => window.screen.height") == 500
    assert (
        page.evaluate("() => matchMedia('(min-device-height: 400px)').matches") is True
    )
    assert (
        page.evaluate("() => matchMedia('(min-device-height: 600px)').matches") is False
    )
    assert (
        page.evaluate("() => matchMedia('(max-device-height: 400px)').matches") is False
    )
    assert (
        page.evaluate("() => matchMedia('(max-device-height: 600px)').matches") is True
    )
    assert page.evaluate("() => matchMedia('(device-height: 200px)').matches") is False
    assert page.evaluate("() => matchMedia('(device-height: 500px)').matches") is True


def test_VP_007_should_emulate_avail_width_and_avail_height(page: Page) -> None:
    page.set_viewport_size({"width": 500, "height": 600})
    assert page.evaluate("() => window.screen.availWidth") == 500
    assert page.evaluate("() => window.screen.availHeight") == 600


def test_VP_008_should_not_have_touch_by_default(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/mobile.html")
    assert page.evaluate("() => 'ontouchstart' in window") is False


def test_VP_009_should_throw_on_tap_if_has_touch_is_not_enabled(
    page: Page,
) -> None:
    page.set_content("<div>a</div>")
    with pytest.raises(Error) as exc_info:
        page.tap("div")
    assert exc_info.value
    assert "The page does not support tap" in exc_info.value.message

    with pytest.raises(Error) as exc_info:
        page.locator("div").tap()
    assert exc_info.value
    assert "The page does not support tap" in exc_info.value.message


def test_VP_010_should_support_touch_with_null_viewport(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context(no_viewport=True, has_touch=True)
    page = context.new_page()
    page.goto(server.PREFIX + "/mobile.html")
    assert page.evaluate("() => 'ontouchstart' in window") is True
    context.close()


def test_VP_011_should_keep_touch_emulation_after_screenshot_beyond_viewport(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context(
        viewport={"width": 393, "height": 727}, has_touch=True
    )
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)
    page.set_content('<div id="tall" style="height:3000px">tall</div>')

    def probe() -> Dict[str, Any]:
        return page.evaluate(
            """() => ({
                ontouchstart: 'ontouchstart' in window,
                maxTouchPoints: navigator.maxTouchPoints,
                coarse: matchMedia('(pointer: coarse)').matches,
            })"""
        )

    expected = probe()
    assert expected["ontouchstart"] is True
    page.screenshot(full_page=True)
    assert probe() == expected
    page.locator("#tall").screenshot()
    assert probe() == expected
    page.goto(server.EMPTY_PAGE)
    assert probe() == expected
    context.close()


def test_VP_012_should_set_both_screen_and_viewport_options(
    context_factory: ContextFactory,
) -> None:
    context = context_factory(
        screen={"width": 1280, "height": 720},
        viewport={"width": 1000, "height": 600},
    )
    page = context.new_page()
    screen = page.evaluate("() => ({ w: screen.width, h: screen.height })")
    assert screen == {"w": 1280, "h": 720}
    inner = page.evaluate("() => ({ w: window.innerWidth, h: window.innerHeight })")
    assert inner == {"w": 1000, "h": 600}


def test_VP_013_should_report_null_viewport_size_when_given_null_viewport(
    browser: Browser,
) -> None:
    context = browser.new_context(no_viewport=True)
    page = context.new_page()
    assert page.viewport_size is None
    context.close()


def test_VP_014_should_drag_with_high_dpi(
    browser: Browser, server: Server, headless: bool
) -> None:
    if not headless:
        pytest.skip("Stray mouse events mess up the test")

    page = browser.new_page(device_scale_factor=2)
    page.goto(server.PREFIX + "/drag-n-drop.html")
    page.hover("#source")
    page.mouse.down()
    page.hover("#target")
    page.mouse.up()
    # could not find source in target
    assert (
        page.eval_on_selector(
            "#target", "target => target.contains(document.querySelector('#source'))"
        )
        is True
    )
    page.close()


def test_VP_015_web_kit_windows_headed_should_have_a_minimal_viewport(
    context_factory: ContextFactory, browser_name: str, headless: bool, is_win: bool
) -> None:
    if browser_name != "webkit" or headless or not is_win:
        pytest.skip("Not relevant for this browser")

    with pytest.raises(Error) as exc_info:
        context_factory(viewport={"width": 100, "height": 100})
    assert (
        "WebKit on Windows has a minimal viewport of 250x240." in exc_info.value.message
    )

    context = context_factory()
    page = context.new_page()
    with pytest.raises(Error) as exc_info:
        page.set_viewport_size({"width": 100, "height": 100})
    assert (
        "WebKit on Windows has a minimal viewport of 250x240." in exc_info.value.message
    )
    context.close()


def test_VP_016_should_be_able_to_get_correct_orientation_angle_on_non_mobile_devices(
    browser: Browser, browser_name: str, server: Server
) -> None:
    if browser_name == "webkit":
        pytest.skip("Desktop webkit dont support orientation API")

    context = browser.new_context(
        viewport={"width": 300, "height": 400}, is_mobile=False
    )
    page = context.new_page()
    page.goto(server.PREFIX + "/index.html")
    assert page.evaluate("() => window.screen.orientation.angle") == 0
    page.set_viewport_size({"width": 400, "height": 300})
    assert page.evaluate("() => window.screen.orientation.angle") == 0
    context.close()


def test_VP_017_should_set_window_screen_orientation_type_for_mobile_devices(
    context_factory: ContextFactory,
    playwright: Playwright,
    server: Server,
) -> None:
    context = context_factory(**playwright.devices["iPhone 14"])
    page = context.new_page()
    page.goto(server.PREFIX + "/index.html")
    assert page.evaluate("() => window.screen.orientation.type") == "portrait-primary"
    context.close()
