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

"""Port of tests/library/browsercontext-viewport-mobile.spec.ts."""

import pytest

from playwright.sync_api import Browser, Error, Playwright, Route
from tests.server import Server

# The upstream describe 'mobile viewport' skips firefox (but not firefox over BiDi).
pytestmark = pytest.mark.skip_browser("firefox")


def test_DV_011_mobile_viewport_should_support_mobile_emulation(
    playwright: Playwright, browser: Browser, server: Server
) -> None:
    iphone = playwright.devices["iPhone 6"]
    context = browser.new_context(**iphone)
    page = context.new_page()
    page.goto(server.PREFIX + "/mobile.html")
    assert page.evaluate("() => window.innerWidth") == 375
    page.set_viewport_size({"width": 400, "height": 300})
    assert page.evaluate("() => window.innerWidth") == 400
    context.close()


def test_DV_012_mobile_viewport_should_support_touch_emulation(
    playwright: Playwright, browser: Browser, server: Server
) -> None:
    iphone = playwright.devices["iPhone 6"]
    context = browser.new_context(**iphone)
    page = context.new_page()
    page.goto(server.PREFIX + "/mobile.html")
    assert page.evaluate("() => 'ontouchstart' in window") is True
    assert (
        page.evaluate(
            """function dispatchTouch() {
                let fulfill;
                const promise = new Promise(x => fulfill = x);
                window.ontouchstart = function(e) {
                    fulfill('Received touch');
                };
                window.dispatchEvent(new Event('touchstart'));

                fulfill('Did not receive touch');

                return promise;
            }"""
        )
        == "Received touch"
    )
    context.close()


def test_DV_013_mobile_viewport_should_be_detectable(
    playwright: Playwright, browser: Browser
) -> None:
    iphone = playwright.devices["iPhone 6"]
    context = browser.new_context(**iphone)
    page = context.new_page()
    assert (
        page.evaluate("() => 'ontouchstart' in window || !!window.TouchEvent") is True
    )
    context.close()


def test_DV_014_mobile_viewport_should_detect_touch_when_applying_viewport_with_touches(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context(
        viewport={"width": 800, "height": 600}, has_touch=True
    )
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)
    assert (
        page.evaluate("() => 'ontouchstart' in window || !!window.TouchEvent") is True
    )
    context.close()


def test_DV_015_mobile_viewport_should_support_landscape_emulation(
    playwright: Playwright, browser: Browser, server: Server
) -> None:
    iphone = playwright.devices["iPhone 6"]
    iphone_landscape = playwright.devices["iPhone 6 landscape"]
    context1 = browser.new_context(**iphone)
    page1 = context1.new_page()
    page1.goto(server.PREFIX + "/mobile.html")
    assert (
        page1.evaluate("() => matchMedia('(orientation: landscape)').matches") is False
    )
    context2 = browser.new_context(**iphone_landscape)
    page2 = context2.new_page()
    assert (
        page2.evaluate("() => matchMedia('(orientation: landscape)').matches") is True
    )
    context1.close()
    context2.close()


def test_DV_016_mobile_viewport_should_support_window_orientation_emulation(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context(
        viewport={"width": 300, "height": 400}, is_mobile=True
    )
    page = context.new_page()
    page.goto(server.PREFIX + "/mobile.html")
    assert page.evaluate("() => window.orientation") == 0
    page.set_viewport_size({"width": 400, "height": 300})
    assert page.evaluate("() => window.orientation") == 90
    context.close()


def test_DV_017_mobile_viewport_should_preserve_window_orientation_override_after_navigation(
    browser: Browser, server: Server, is_frozen_webkit: bool
) -> None:
    if is_frozen_webkit:
        pytest.skip("skipped upstream for frozen webkit")

    context = browser.new_context(
        viewport={"width": 400, "height": 300}, is_mobile=True
    )
    page = context.new_page()
    page.goto(server.PREFIX + "/mobile.html")
    assert page.evaluate("() => window.orientation") == 90
    page.goto(server.CROSS_PROCESS_PREFIX + "/mobile.html")
    assert page.evaluate("() => window.orientation") == 90
    context.close()


def test_DV_018_mobile_viewport_should_preserve_screen_orientation_type_override_after_navigation(
    browser: Browser, server: Server, is_frozen_webkit: bool
) -> None:
    if is_frozen_webkit:
        pytest.skip("skipped upstream for frozen webkit")

    context = browser.new_context(
        viewport={"width": 300, "height": 400}, is_mobile=True
    )
    page = context.new_page()
    page.goto(server.PREFIX + "/mobile.html")
    assert page.evaluate("() => window.screen.orientation.type") == "portrait-primary"
    page.goto(server.CROSS_PROCESS_PREFIX + "/mobile.html")
    assert page.evaluate("() => window.screen.orientation.type") == "portrait-primary"
    context.close()


def test_DV_019_mobile_viewport_should_fire_orientationchange_event(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context(
        viewport={"width": 300, "height": 400}, is_mobile=True
    )
    page = context.new_page()
    page.goto(server.PREFIX + "/mobile.html")
    page.evaluate(
        """() => {
            let counter = 0;
            window.addEventListener('orientationchange', () => console.log(++counter));
        }"""
    )

    with page.expect_console_message() as event1_info:
        page.set_viewport_size({"width": 400, "height": 300})
    assert (event1_info.value).text == "1"

    with page.expect_console_message() as event2_info:
        page.set_viewport_size({"width": 300, "height": 400})
    assert (event2_info.value).text == "2"
    context.close()


def test_DV_020_mobile_viewport_default_mobile_viewports_to_980_width(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context(
        viewport={"width": 320, "height": 480}, is_mobile=True
    )
    page = context.new_page()
    page.goto(server.PREFIX + "/empty.html")
    assert page.evaluate("() => window.innerWidth") == 980
    context.close()


def test_DV_021_mobile_viewport_respect_meta_viewport_tag(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context(
        viewport={"width": 320, "height": 480}, is_mobile=True
    )
    page = context.new_page()
    page.goto(server.PREFIX + "/mobile.html")
    assert page.evaluate("() => window.innerWidth") == 320
    context.close()


def test_DV_022_mobile_viewport_should_emulate_the_hover_media_feature(
    playwright: Playwright, browser: Browser
) -> None:
    iphone = playwright.devices["iPhone 6"]
    mobilepage = browser.new_page(**iphone)
    assert mobilepage.evaluate("() => matchMedia('(hover: hover)').matches") is False
    assert mobilepage.evaluate("() => matchMedia('(hover: none)').matches") is True
    assert (
        mobilepage.evaluate("() => matchMedia('(any-hover: hover)').matches") is False
    )
    assert mobilepage.evaluate("() => matchMedia('(any-hover: none)').matches") is True
    assert mobilepage.evaluate("() => matchMedia('(pointer: coarse)').matches") is True
    assert mobilepage.evaluate("() => matchMedia('(pointer: fine)').matches") is False
    assert (
        mobilepage.evaluate("() => matchMedia('(any-pointer: coarse)').matches") is True
    )
    assert (
        mobilepage.evaluate("() => matchMedia('(any-pointer: fine)').matches") is False
    )
    mobilepage.close()

    desktop_page = browser.new_page()
    assert desktop_page.evaluate("() => matchMedia('(hover: none)').matches") is False
    assert desktop_page.evaluate("() => matchMedia('(hover: hover)').matches") is True
    assert (
        desktop_page.evaluate("() => matchMedia('(any-hover: none)').matches") is False
    )
    assert (
        desktop_page.evaluate("() => matchMedia('(any-hover: hover)').matches") is True
    )
    assert (
        desktop_page.evaluate("() => matchMedia('(pointer: coarse)').matches") is False
    )
    assert desktop_page.evaluate("() => matchMedia('(pointer: fine)').matches") is True
    assert (
        desktop_page.evaluate("() => matchMedia('(any-pointer: coarse)').matches")
        is False
    )
    assert (
        desktop_page.evaluate("() => matchMedia('(any-pointer: fine)').matches") is True
    )
    desktop_page.close()


def test_DV_023_mobile_viewport_mouse_should_work_with_mobile_viewports_and_cross_process_navigations(
    browser: Browser, server: Server
) -> None:
    # @see https://crbug.com/929806
    context = browser.new_context(
        viewport={"width": 360, "height": 640}, is_mobile=True
    )
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)
    page.goto(server.CROSS_PROCESS_PREFIX + "/mobile.html")
    page.evaluate(
        """() => {
            document.addEventListener('click', event => {
                window['result'] = { x: event.clientX, y: event.clientY };
            });
        }"""
    )

    page.mouse.click(30, 40)

    assert page.evaluate("result") == {"x": 30, "y": 40}
    context.close()


def test_DV_024_mobile_viewport_should_scroll_when_emulating_a_mobile_viewport(
    browser: Browser, server: Server, browser_name: str
) -> None:
    context = browser.new_context(
        viewport={"width": 1000, "height": 600},
        is_mobile=True,
    )
    page = context.new_page()
    page.goto(server.PREFIX + "/input/scrollable.html")
    page.mouse.move(50, 60)
    if browser_name == "webkit":
        with pytest.raises(Error) as exc_info:
            page.mouse.wheel(0, 100)
        assert "Mouse wheel is not supported in mobile WebKit" in exc_info.value.message
    else:
        page.mouse.wheel(0, 100)
        page.wait_for_function("window.scrollY === 100")
    context.close()


def test_DV_025_mobile_viewport_should_scroll_mobile_page_with_background_attachment_fixed(
    playwright: Playwright, browser: Browser, server: Server
) -> None:
    iphone = playwright.devices["iPhone 12"]
    context = browser.new_context(**iphone)
    page = context.new_page()
    page.goto(server.PREFIX + "/input/background-fixed.html")
    page.get_by_role("button").click()
    assert page.evaluate("() => window.scrollY") > 1000
    context.close()


def test_DV_026_mobile_viewport_view_scale_should_reset_after_navigation(
    browser: Browser,
) -> None:
    context = browser.new_context(
        viewport={"width": 390, "height": 664},
        is_mobile=True,
    )
    page = context.new_page()
    page.goto(
        "data:text/html,<meta name='viewport' content='device-width, initial-scale=1'><button>Mobile Viewport</button>"
    )

    def handle_route(route: Route) -> None:
        route.fulfill(
            body="""<body>
          <button>Click me</button>
          <script>
            window.clicks = [];
            document.addEventListener('click', e => {
              const dot = document.createElement('div');
              dot.style.position = 'absolute';
              dot.style.width = '10px';
              dot.style.height = '10px';
              dot.style.borderRadius = '5px';
              dot.style.backgroundColor = 'red';
              dot.style.left = e.pageX + 'px';
              dot.style.top = e.pageY + 'px';
              dot.textContent = 'x: ' + e.pageX + ' y: ' + e.pageY;
              document.body.appendChild(dot);
              window.clicks.push({ x: e.pageX, y: e.pageY });
            });
          </script>
        </body>""",
            content_type="text/html",
        )

    page.route("**/button.html", handle_route)
    page.goto("http://localhost/button.html")
    page.get_by_text("Click me").click(force=True)
    box = page.locator("button").bounding_box()
    assert box
    clicks = page.evaluate("() => window.clicks")
    assert len(clicks) == 1
    x, y = clicks[0]["x"], clicks[0]["y"]
    is_click_inside_button = (
        box["x"] <= x <= box["x"] + box["width"]
        and box["y"] <= y <= box["y"] + box["height"]
    )
    assert is_click_inside_button is True
    context.close()
