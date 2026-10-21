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

"""Port of tests/page/page-screenshot.spec.ts."""

import os
from pathlib import Path
from typing import Any, Callable, List

import pytest

from playwright.sync_api import Error, Page, Route, expect
from tests.helpers.image_compare import (
    assert_to_match_golden,
    compare_images,
    decode_image,
    is_lossless_webp,
    pixel,
)
from tests.server import Server, TestServerRequest, reactor

from ..utils import Utils

GoldenAssert = Callable[[bytes, str], None]


def expect_failure(request: pytest.FixtureRequest, reason: str) -> None:
    """Like `it.fail()`: the test must fail."""
    request.applymarker(pytest.mark.xfail(reason=f"upstream: {reason}", strict=True))


@pytest.fixture
def skip_firefox_headed(browser_name: str, headless: bool) -> None:
    """The skip of the upstream describe 'page screenshot'."""
    if browser_name == "firefox" and not headless:
        pytest.skip("Firefox headed produces a different image.")


CARET_CONTENT = """
      <!-- Refer to stylesheet from other origin. Accessing this
           stylesheet rules will throw.
      -->
      <link rel=stylesheet href="{}">
      <!-- make life harder: define caret color in stylesheet -->
      <style>
        div {{
          caret-color: #000 !important;
        }}
      </style>
      <div contenteditable="true"></div>
    """

TRANSPARENT_CONTENT = """
      <style>
        body { margin: 0 }
        div { width: 300px; height: 100px; }
      </style>
      <div style="background:black"></div>
      <div style="background:white"></div>
      <div style="background:transparent"></div>
    """

CSS_TRANSFORM_CONTENT = """
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


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_001_page_screenshot_should_work_smoke(
    page: Page, server: Server, assert_to_be_golden: GoldenAssert
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.goto(server.PREFIX + "/grid.html")
    screenshot = page.screenshot()
    assert_to_be_golden(screenshot, "screenshot-sanity.png")


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_002_page_screenshot_should_not_capture_blinking_caret_by_default(
    page: Page, server: Server
) -> None:
    page.set_content(
        CARET_CONTENT.format(server.CROSS_PROCESS_PREFIX + "/injectedstyle.css")
    )
    div = page.locator("div")
    div.type("foo bar")
    screenshot = div.screenshot()
    for _ in range(10):
        # Caret blinking time is set to 500ms.
        # Try to capture variety of screenshots to make
        # sure we don't capture blinking caret.
        page.wait_for_timeout(150)
        new_screenshot = div.screenshot()
        assert new_screenshot == screenshot


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_003_page_screenshot_should_capture_blinking_caret_if_explicitly_asked_for(
    page: Page, server: Server, browser_name: str
) -> None:
    if browser_name == "firefox":
        pytest.skip("browser-level screenshot API in firefox does not capture caret")

    page.set_content(
        CARET_CONTENT.format(server.CROSS_PROCESS_PREFIX + "/injectedstyle.css")
    )
    div = page.locator("div")
    div.type("foo bar")
    screenshot = div.screenshot()
    has_different_screenshots = False
    for _ in range(10):
        if has_different_screenshots:
            break
        # Caret blinking time is set to 500ms.
        # Try to capture variety of screenshots to make
        # sure we capture blinking caret.
        page.wait_for_timeout(150)
        new_screenshot = div.screenshot(caret="initial")
        has_different_screenshots = new_screenshot != screenshot
    assert has_different_screenshots is True


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_004_page_screenshot_should_capture_blinking_caret_in_shadow_dom(
    page: Page,
) -> None:
    page.add_script_tag(
        content="""
      class CustomElementContainer extends HTMLElement {
        #shadowRoot;
        constructor() {
          super();
          this.#shadowRoot = this.attachShadow({ mode: 'open' });
          this.#shadowRoot.innerHTML = '<custom-element-input-wrapper><input type="text"/></custom-element-input-wrapper>';
        }
      }
      class CustomElementInputWrapper extends HTMLElement {
        #shadowRoot;
        constructor() {
          super();
          this.#shadowRoot = this.attachShadow({ mode: 'open' });
          this.#shadowRoot.innerHTML = '<style>:host { all: initial; }</style><slot/>';
        }
      }
      customElements.define('custom-element-input-wrapper', CustomElementInputWrapper);
      customElements.define('custom-element-container', CustomElementContainer);

      const container = document.createElement('custom-element-container');
      document.body.appendChild(container);""",
    )

    input = page.locator("input")
    # TODO: click fails in webkit
    input.focus()

    screenshot = input.screenshot()
    has_different_screenshots = False
    for _ in range(10):
        if has_different_screenshots:
            break
        # Caret blinking time is set to 500ms.
        # Try to capture variety of screenshots to make
        # sure we capture blinking caret.
        page.wait_for_timeout(150)
        new_screenshot = input.screenshot(caret="hide")
        has_different_screenshots = new_screenshot != screenshot
    assert has_different_screenshots is False


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_005_page_screenshot_should_clip_rect(
    page: Page, server: Server, assert_to_be_golden: GoldenAssert
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.goto(server.PREFIX + "/grid.html")
    screenshot = page.screenshot(clip={"x": 50, "y": 100, "width": 150, "height": 100})
    assert_to_be_golden(screenshot, "screenshot-clip-rect.png")


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_006_page_screenshot_should_clip_rect_with_full_page(
    page: Page, server: Server, assert_to_be_golden: GoldenAssert
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.goto(server.PREFIX + "/grid.html")
    page.evaluate("() => window.scrollBy(150, 200)")
    screenshot = page.screenshot(
        full_page=True,
        clip={"x": 50, "y": 100, "width": 150, "height": 100},
    )
    assert_to_be_golden(screenshot, "screenshot-clip-rect.png")


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_007_page_screenshot_should_clip_elements_to_the_viewport(
    page: Page, server: Server, assert_to_be_golden: GoldenAssert
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.goto(server.PREFIX + "/grid.html")
    screenshot = page.screenshot(clip={"x": 50, "y": 450, "width": 1000, "height": 100})
    assert_to_be_golden(screenshot, "screenshot-offscreen-clip.png")


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_008_page_screenshot_should_throw_on_clip_outside_the_viewport(
    page: Page, server: Server
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.goto(server.PREFIX + "/grid.html")
    with pytest.raises(Error) as exc_info:
        page.screenshot(clip={"x": 50, "y": 650, "width": 100, "height": 100})
    assert (
        "Clipped area is either empty or outside the resulting image"
        in exc_info.value.message
    )


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_009_page_screenshot_should_throw_on_a_negative_clip_size(
    page: Page, server: Server
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.goto(server.PREFIX + "/grid.html")
    with pytest.raises(Error) as exc_info:
        page.screenshot(clip={"x": 50, "y": 50, "width": -100, "height": 100})
    assert "Expected options.clip.width to be greater than 0" in exc_info.value.message


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_010_page_screenshot_should_run_in_parallel(
    page: Page,
    server: Server,
    assert_to_be_golden: GoldenAssert,
    sync_gather: Callable[..., List[Any]],
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.goto(server.PREFIX + "/grid.html")
    screenshots = sync_gather(
        *[
            lambda i=i: page.screenshot(
                clip={"x": 50 * i, "y": 0, "width": 50, "height": 50}
            )
            for i in range(3)
        ]
    )
    assert_to_be_golden(screenshots[1], "grid-cell-1.png")


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_011_page_screenshot_should_take_full_page_screenshots(
    page: Page, server: Server, assert_to_be_golden: GoldenAssert
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.goto(server.PREFIX + "/grid.html")
    screenshot = page.screenshot(full_page=True)
    assert_to_be_golden(screenshot, "screenshot-grid-fullpage.png")


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_012_page_screenshot_should_take_full_page_screenshots_and_mask_elements_outside_of_it(
    page: Page, server: Server, assert_to_be_golden: GoldenAssert
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.goto(server.PREFIX + "/grid.html")
    screenshot = page.screenshot(
        full_page=True,
        mask=[page.locator(".box").nth(144)],
    )
    assert_to_be_golden(
        screenshot, "screenshot-grid-fullpage-mask-outside-viewport.png"
    )


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_013_page_screenshot_should_restore_viewport_after_full_page_screenshot(
    page: Page, server: Server, utils: Utils
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.goto(server.PREFIX + "/grid.html")
    screenshot = page.screenshot(full_page=True)
    assert isinstance(screenshot, bytes)
    utils.verify_viewport(page, 500, 500)


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_014_page_screenshot_should_allow_transparency(
    page: Page,
    browser_name: str,
    request: pytest.FixtureRequest,
    assert_to_be_golden: GoldenAssert,
) -> None:
    if browser_name == "firefox":
        expect_failure(request, "it.fail(browserName === 'firefox')")

    page.set_viewport_size({"width": 300, "height": 300})
    page.set_content(TRANSPARENT_CONTENT)
    screenshot = page.screenshot(omit_background=True)
    assert_to_be_golden(screenshot, "transparent.png")


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_015_page_screenshot_should_render_white_background_on_jpeg_file(
    page: Page, server: Server, assert_to_be_golden: GoldenAssert
) -> None:
    page.set_viewport_size({"width": 300, "height": 300})
    page.goto(server.EMPTY_PAGE)
    screenshot = page.screenshot(omit_background=True, type="jpeg")
    assert_to_be_golden(screenshot, "white.jpg")


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_016_page_screenshot_should_produce_a_valid_webp_screenshot(
    page: Page, server: Server, assert_to_be_golden: GoldenAssert
) -> None:
    page.set_viewport_size({"width": 300, "height": 300})
    page.goto(server.EMPTY_PAGE)
    page.evaluate("() => (document.body.style.background = 'rgb(255, 0, 0)')")
    screenshot = page.screenshot(type="webp")
    assert_to_be_golden(screenshot, "red.webp")


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_017_page_screenshot_path_option_should_detect_webp(
    page: Page, server: Server, tmp_path: Path, assert_to_be_golden: GoldenAssert
) -> None:
    page.set_viewport_size({"width": 300, "height": 300})
    page.goto(server.EMPTY_PAGE)
    page.evaluate("() => (document.body.style.background = 'rgb(255, 0, 0)')")
    output_path = tmp_path / "screenshot.webp"
    screenshot = page.screenshot(path=output_path)
    assert_to_be_golden(output_path.read_bytes(), "red.webp")
    assert_to_be_golden(screenshot, "red.webp")


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_018_page_screenshot_quality_option_should_work_for_webp(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/grid.html")
    low_quality = page.screenshot(type="webp", quality=0)
    high_quality = page.screenshot(type="webp", quality=100)
    assert len(low_quality) < len(high_quality)


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_019_page_screenshot_webp_screenshots_should_be_lossless_by_default(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/grid.html")
    assert is_lossless_webp(page.screenshot(type="webp")) is True
    assert is_lossless_webp(page.screenshot(type="webp", quality=80)) is False


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_020_page_screenshot_should_allow_transparency_with_webp(
    page: Page, browser_name: str, request: pytest.FixtureRequest
) -> None:
    if browser_name == "firefox":
        expect_failure(request, "it.fail(browserName === 'firefox')")

    page.set_viewport_size({"width": 300, "height": 300})
    page.set_content(TRANSPARENT_CONTENT)
    screenshot = page.screenshot(omit_background=True, type="webp")
    image = decode_image(screenshot)
    width, height = image.size
    assert width == 300
    assert height == 300
    assert pixel(image, 150, 50) == (0, 0, 0, 255)
    assert pixel(image, 150, 150) == (255, 255, 255, 255)
    assert pixel(image, 150, 250)[3] == 0


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_021_page_screenshot_quality_option_should_throw_for_webp_when_out_of_range(
    page: Page,
) -> None:
    with pytest.raises(Error) as exc_info:
        page.screenshot(type="webp", quality=101)
    assert "Expected options.quality to be between 0 and 100" in exc_info.value.message


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_022_page_screenshot_should_work_with_odd_clip_size_on_retina_displays(
    page: Page, assert_to_be_golden: GoldenAssert
) -> None:
    screenshot = page.screenshot(clip={"x": 0, "y": 0, "width": 11, "height": 11})
    assert_to_be_golden(screenshot, "screenshot-clip-odd-size.png")


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_023_page_screenshot_should_work_for_canvas(
    page: Page,
    server: Server,
    browser_name: str,
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.goto(server.PREFIX + "/screenshots/canvas.html")
    screenshot = page.screenshot()
    # Allow 4 corners to be rendered differently on various platforms/browsers.
    assert_to_match_golden(
        browser_name, screenshot, "screenshot-canvas.png", max_diff_pixels=4
    )


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_024_page_screenshot_should_capture_canvas_changes(
    page: Page,
    assert_to_be_golden: GoldenAssert,
) -> None:
    page.goto("data:text/html,<canvas></canvas>")
    page.evaluate(
        """() => {
            const canvas = document.querySelector('canvas');
            canvas.width = 600;
            canvas.height = 600;
        }"""
    )

    def add_line(step: int) -> None:
        page.evaluate(
            """n => {
                const canvas = document.querySelector('canvas');
                const ctx = canvas.getContext('2d');
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.moveTo(0, n * 100);
                ctx.lineTo(300, n * 100);
                ctx.stroke();
            }""",
            step,
        )

    for i in range(3):
        add_line(i)
        # With the slight delay WebKit stops reflecting changes in the screenshots on macOS.
        page.wait_for_timeout(100)
        screenshot = page.screenshot()
        assert_to_be_golden(screenshot, f"canvas-changes-{i}.png")


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_025_page_screenshot_should_work_for_webgl(
    page: Page,
    server: Server,
    browser_name: str,
    platform: str,
    assert_to_be_golden: GoldenAssert,
) -> None:
    if (
        browser_name == "webkit"
        and platform == "darwin"
        and os.uname().machine == "x86_64"
    ):
        pytest.skip(
            "WebGL is not available on Intel macOS - https://bugs.webkit.org/show_bug.cgi?id=278277"
        )

    page.set_viewport_size({"width": 640, "height": 480})
    page.goto(server.PREFIX + "/screenshots/webgl.html")
    screenshot = page.screenshot()
    assert_to_be_golden(screenshot, "screenshot-webgl.png")


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_026_page_screenshot_should_work_for_translate_z(
    page: Page, server: Server, assert_to_be_golden: GoldenAssert
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.goto(server.PREFIX + "/screenshots/translateZ.html")
    screenshot = page.screenshot()
    assert_to_be_golden(screenshot, "screenshot-translateZ.png")


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_027_page_screenshot_should_work_while_navigating(
    page: Page, server: Server
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.goto(server.PREFIX + "/redirectloop1.html")
    for _ in range(10):
        try:
            screenshot = page.screenshot(full_page=True)
        except Error as e:
            if "Cannot take a screenshot while page is navigating" not in e.message:
                raise
            screenshot = b""
        assert isinstance(screenshot, bytes)


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_028_page_screenshot_should_work_with_iframe_in_shadow(
    page: Page, server: Server, assert_to_be_golden: GoldenAssert
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.goto(server.PREFIX + "/grid-iframe-in-shadow.html")
    assert_to_be_golden(page.screenshot(), "screenshot-iframe.png")


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_029_page_screenshot_path_option_should_work(
    page: Page, server: Server, tmp_path: Path, assert_to_be_golden: GoldenAssert
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.goto(server.PREFIX + "/grid.html")
    output_path = tmp_path / "screenshot.png"
    page.screenshot(path=output_path)
    assert_to_be_golden(output_path.read_bytes(), "screenshot-sanity.png")


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_030_page_screenshot_path_option_should_create_subdirectories(
    page: Page, server: Server, tmp_path: Path, assert_to_be_golden: GoldenAssert
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.goto(server.PREFIX + "/grid.html")
    output_path = tmp_path / "these" / "are" / "directories" / "screenshot.png"
    page.screenshot(path=output_path)
    assert_to_be_golden(output_path.read_bytes(), "screenshot-sanity.png")


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_031_page_screenshot_path_option_should_detect_jpeg(
    page: Page, server: Server, tmp_path: Path, assert_to_be_golden: GoldenAssert
) -> None:
    page.set_viewport_size({"width": 300, "height": 300})
    page.goto(server.EMPTY_PAGE)
    output_path = tmp_path / "screenshot.jpg"
    screenshot = page.screenshot(omit_background=True, path=output_path)
    assert_to_be_golden(output_path.read_bytes(), "white.jpg")
    assert_to_be_golden(screenshot, "white.jpg")
    upper_case_path = tmp_path / "screenshot.JPG"
    page.screenshot(omit_background=True, path=upper_case_path)
    assert_to_be_golden(upper_case_path.read_bytes(), "white.jpg")


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_032_page_screenshot_path_option_should_throw_for_unsupported_mime_type(
    page: Page,
) -> None:
    with pytest.raises(Error) as exc_info:
        page.screenshot(path="file.txt")
    assert 'path: unsupported mime type "text/plain"' in exc_info.value.message


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_033_page_screenshot_quality_option_should_throw_for_png(
    page: Page,
) -> None:
    with pytest.raises(Error) as exc_info:
        page.screenshot(quality=10)
    assert "options.quality is unsupported for the png" in exc_info.value.message


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_034_page_screenshot_zero_quality_option_should_throw_for_png(
    page: Page,
) -> None:
    with pytest.raises(Error) as exc_info:
        page.screenshot(quality=0, type="png")
    assert "options.quality is unsupported for the png" in exc_info.value.message


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_035_page_screenshot_quality_option_should_work_for_jpeg(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/grid.html")
    zero_quality = page.screenshot(type="jpeg", quality=0)
    high_quality = page.screenshot(type="jpeg", quality=100)
    assert len(zero_quality) < len(high_quality)


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_036_page_screenshot_should_prefer_type_over_extension(
    page: Page, tmp_path: Path
) -> None:
    output_path = tmp_path / "file.png"
    buffer = page.screenshot(path=output_path, type="jpeg")
    assert [buffer[0], buffer[1], buffer[2]] == [0xFF, 0xD8, 0xFF]


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_037_page_screenshot_should_not_issue_resize_event(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/grid.html")
    resize_triggered = False

    def resize() -> None:
        nonlocal resize_triggered
        resize_triggered = True

    page.expose_function("resize", resize)
    page.evaluate("() => { window.addEventListener('resize', () => window.resize()); }")
    page.screenshot()
    assert not resize_triggered


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_038_page_screenshot_should_work_with_array_deleted(
    page: Page, server: Server, assert_to_be_golden: GoldenAssert
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.goto(server.PREFIX + "/grid.html")
    page.evaluate("() => delete window.Array")
    screenshot = page.screenshot(full_page=True)
    assert_to_be_golden(screenshot, "screenshot-grid-fullpage.png")


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_039_page_screenshot_should_take_full_page_screenshots_during_navigation(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.goto(server.PREFIX + "/grid.html")

    def reload_several_times() -> None:
        for _ in range(5):
            page.reload()

    def screenshot_several_times() -> None:
        for _ in range(5):
            page.screenshot(full_page=True)

    sync_gather(reload_several_times, screenshot_several_times)


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_040_page_screenshot_mask_option_should_work(
    page: Page, server: Server, assert_to_be_golden: GoldenAssert
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.goto(server.PREFIX + "/grid.html")
    assert_to_be_golden(
        page.screenshot(mask=[page.locator("div").nth(5)]),
        "mask-should-work.png",
    )


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_041_page_screenshot_mask_option_should_work_with_locator(
    page: Page, server: Server, assert_to_be_golden: GoldenAssert
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.goto(server.PREFIX + "/grid.html")
    body_locator = page.locator("body")
    assert_to_be_golden(
        body_locator.screenshot(mask=[page.locator("div").nth(5)]),
        "mask-should-work-with-locator.png",
    )


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_042_page_screenshot_mask_option_should_work_with_elementhandle(
    page: Page, server: Server, assert_to_be_golden: GoldenAssert
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.goto(server.PREFIX + "/grid.html")
    body_handle = page.query_selector("body")
    assert body_handle
    assert_to_be_golden(
        body_handle.screenshot(mask=[page.locator("div").nth(5)]),
        "mask-should-work-with-elementhandle.png",
    )


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_043_page_screenshot_mask_option_should_mask_multiple_elements(
    page: Page, server: Server, assert_to_be_golden: GoldenAssert
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.goto(server.PREFIX + "/grid.html")
    assert_to_be_golden(
        page.screenshot(
            mask=[
                page.locator("div").nth(5),
                page.locator("div").nth(12),
            ],
        ),
        "should-mask-multiple-elements.png",
    )


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_044_page_screenshot_mask_option_should_mask_inside_iframe(
    page: Page, server: Server, utils: Utils, assert_to_be_golden: GoldenAssert
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.goto(server.PREFIX + "/grid.html")
    utils.attach_frame(page, "frame1", server.PREFIX + "/grid.html")
    page.add_style_tag(content="iframe { border: none; }")
    assert_to_be_golden(
        page.screenshot(
            mask=[
                page.locator("div").nth(5),
                page.frame_locator("#frame1").locator("div").nth(12),
            ],
        ),
        "should-mask-inside-iframe.png",
    )


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_045_page_screenshot_mask_option_should_mask_in_parallel(
    page: Page,
    server: Server,
    utils: Utils,
    assert_to_be_golden: GoldenAssert,
    sync_gather: Callable[..., List[Any]],
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    utils.attach_frame(page, "frame1", server.PREFIX + "/grid.html")
    utils.attach_frame(page, "frame2", server.PREFIX + "/grid.html")
    page.add_style_tag(content="iframe { border: none; }")
    screenshots = sync_gather(
        lambda: page.screenshot(
            mask=[page.frame_locator("#frame1").locator("div").nth(1)]
        ),
        lambda: page.screenshot(
            mask=[page.frame_locator("#frame2").locator("div").nth(3)]
        ),
    )
    assert_to_be_golden(screenshots[0], "should-mask-in-parallel-1.png")
    assert_to_be_golden(screenshots[1], "should-mask-in-parallel-2.png")


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_046_page_screenshot_mask_option_should_remove_mask_after_screenshot(
    page: Page, server: Server
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.goto(server.PREFIX + "/grid.html")
    screenshot1 = page.screenshot()
    page.screenshot(mask=[page.locator("div").nth(1)])
    screenshot2 = page.screenshot()
    assert screenshot1 == screenshot2


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_047_page_screenshot_mask_option_should_work_when_subframe_has_stalled_navigation(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    routes: List[Route] = []
    # Stalling subframe.
    page.route("**/subframe.html", lambda route: routes.append(route))

    page.goto(server.EMPTY_PAGE)

    def screenshot_and_fulfill() -> None:
        # The route is ready.
        while not routes:
            page.wait_for_timeout(10)
        route = routes[0]

        page.screenshot(mask=[page.locator("non-existent")])
        route.fulfill(body="")

    # set_content() is done when the subframe is fulfilled.
    sync_gather(
        lambda: page.set_content("<iframe src='/subframe.html'></iframe>"),
        screenshot_and_fulfill,
    )


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_048_page_screenshot_mask_option_should_work_when_subframe_used_document_open_after_a_weird_url(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    page.evaluate(
        """() => {
            const iframe = document.createElement('iframe');
            iframe.src = 'javascript:hi';
            document.body.appendChild(iframe);
            iframe.contentDocument.open();
            iframe.contentDocument.write('Hello');
            iframe.contentDocument.close();
        }"""
    )
    page.screenshot(mask=[page.locator("non-existent")])


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_049_page_screenshot_mask_option_should_work_when_mask_color_is_not_pink_f0_f(
    page: Page, server: Server, assert_to_be_golden: GoldenAssert
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.goto(server.PREFIX + "/grid.html")
    assert_to_be_golden(
        page.screenshot(
            mask=[page.locator("div").nth(5)],
            mask_color="#00FF00",
        ),
        "mask-color-should-work.png",
    )


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_050_page_screenshot_mask_option_should_hide_elements_based_on_attr(
    page: Page, server: Server, assert_to_be_golden: GoldenAssert
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.goto(server.PREFIX + "/grid.html")
    page.locator("div").nth(5).evaluate(
        "element => { element.setAttribute('data-test-screenshot', 'hide'); }"
    )
    assert_to_be_golden(
        page.screenshot(
            style="""[data-test-screenshot="hide"] {
          visibility: hidden;
        }"""
        ),
        "hide-should-work.png",
    )
    visibility = (
        page.locator("div").nth(5).evaluate("element => element.style.visibility")
    )
    assert visibility == ""


@pytest.mark.usefixtures("skip_firefox_headed")
def test_SS_051_page_screenshot_mask_option_should_remove_elements_based_on_attr(
    page: Page, server: Server, assert_to_be_golden: GoldenAssert
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.goto(server.PREFIX + "/grid.html")
    page.locator("div").nth(5).evaluate(
        "element => { element.setAttribute('data-test-screenshot', 'remove'); }"
    )
    assert_to_be_golden(
        page.screenshot(
            style="""[data-test-screenshot="remove"] {
          display: none;
        }"""
        ),
        "remove-should-work.png",
    )
    display = page.locator("div").nth(5).evaluate("element => element.style.display")
    assert display == ""


def test_SS_052_page_screenshot_animations_should_not_capture_infinite_css_animation(
    page: Page, server: Server, utils: Utils
) -> None:
    page.goto(server.PREFIX + "/rotate-z.html")
    div = page.locator("div")
    screenshot = div.screenshot(animations="disabled")
    for _ in range(10):
        utils.rafraf(page)
        new_screenshot = div.screenshot(animations="disabled")
        assert new_screenshot == screenshot


def test_SS_053_page_screenshot_animations_should_not_capture_pseudo_element_css_animation(
    page: Page, server: Server, utils: Utils
) -> None:
    page.goto(server.PREFIX + "/rotate-pseudo.html")
    div = page.locator("div")
    screenshot = div.screenshot(animations="disabled")
    for _ in range(10):
        utils.rafraf(page)
        new_screenshot = div.screenshot(animations="disabled")
        assert new_screenshot == screenshot


def test_SS_054_page_screenshot_animations_should_not_capture_css_animations_in_shadow_dom(
    page: Page, server: Server, utils: Utils
) -> None:
    page.goto(server.PREFIX + "/rotate-z-shadow-dom.html")
    screenshot = page.screenshot(animations="disabled")
    for _ in range(4):
        utils.rafraf(page)
        new_screenshot = page.screenshot(animations="disabled")
        assert new_screenshot == screenshot


def test_SS_056_page_screenshot_animations_should_resume_infinite_animations(
    page: Page, server: Server, utils: Utils
) -> None:
    page.goto(server.PREFIX + "/rotate-z.html")
    page.screenshot(animations="disabled")
    buffer1 = page.screenshot()
    utils.rafraf(page)
    buffer2 = page.screenshot()
    assert compare_images(buffer1, buffer2, max_diff_pixels=50) is not None


def test_SS_057_page_screenshot_animations_should_not_capture_infinite_web_animations(
    page: Page, server: Server, utils: Utils
) -> None:
    page.goto(server.PREFIX + "/web-animation.html")
    div = page.locator("div")
    screenshot = div.screenshot(animations="disabled")
    for _ in range(10):
        utils.rafraf(page)
        new_screenshot = div.screenshot(animations="disabled")
        assert new_screenshot == screenshot
    # Should resume infinite web animation.
    buffer1 = page.screenshot()
    utils.rafraf(page)
    buffer2 = page.screenshot()
    assert compare_images(buffer1, buffer2, max_diff_pixels=50) is not None


def test_SS_058_page_screenshot_animations_should_fire_transitionend_for_finite_transitions(
    page: Page, server: Server, utils: Utils
) -> None:
    page.goto(server.PREFIX + "/css-transition.html")
    div = page.locator("div")
    div.evaluate(
        """el => {
            el.addEventListener('transitionend', () => window['__TRANSITION_END'] = true, false);
        }"""
    )

    # make sure transition is actually running
    screenshot1 = page.screenshot()
    utils.rafraf(page)
    screenshot2 = page.screenshot()
    assert screenshot1 != screenshot2

    # Make a screenshot that finishes all finite animations.
    screenshot1 = div.screenshot(animations="disabled")
    utils.rafraf(page)
    # Make sure finite transition is not restarted.
    screenshot2 = div.screenshot(animations="allow")
    assert screenshot1 == screenshot2

    assert page.evaluate("() => window['__TRANSITION_END']") is True


def test_SS_059_page_screenshot_animations_should_capture_screenshots_after_layoutchanges_in_transitionend_event(
    page: Page, server: Server, utils: Utils
) -> None:
    page.goto(server.PREFIX + "/css-transition.html")
    div = page.locator("div")
    div.evaluate(
        """el => {
            el.addEventListener('transitionend', () => {
                const time = window.builtins.Date.now();
                // Block main thread for 200ms, emulating heavy layout.
                while (window.builtins.Date.now() - time < 200) {}
                const h1 = document.createElement('h1');
                h1.textContent = 'woof-woof';
                document.body.append(h1);
            }, false);
        }"""
    )

    # make sure transition is actually running
    screenshot1 = page.screenshot()
    utils.rafraf(page)
    screenshot2 = page.screenshot()
    assert screenshot1 != screenshot2

    # 1. Make a screenshot that finishes all finite animations
    #    and triggers layout.
    screenshot1 = page.screenshot(animations="disabled")

    # 2. Make a second screenshot after h1 is on screen.
    expect(page.locator("h1")).to_be_visible()
    expect(page.locator("h1")).to_have_text("woof-woof")
    screenshot2 = page.screenshot()

    # 3. Make sure both screenshots are equal, meaning that
    #    first screenshot actually was taken after transitionend
    #    changed layout.
    assert screenshot1 == screenshot2


def test_SS_060_page_screenshot_animations_should_not_change_animation_with_playback_rate_equal_to_0(
    page: Page, server: Server, utils: Utils
) -> None:
    page.goto(server.PREFIX + "/rotate-z.html")
    page.evaluate(
        """async () => {
            window.animation = document.getAnimations()[0];
            await window.animation.ready;
            window.animation.updatePlaybackRate(0);
            await window.animation.ready;
            window.animation.currentTime = 500;
        }"""
    )
    screenshot1 = page.screenshot(animations="disabled")
    utils.rafraf(page)
    screenshot2 = page.screenshot(animations="disabled")
    assert screenshot1 == screenshot2
    assert (
        page.evaluate(
            """() => ({
            playbackRate: window.animation.playbackRate,
            currentTime: window.animation.currentTime,
        })"""
        )
        == {"playbackRate": 0, "currentTime": 500}
    )


def test_SS_061_page_screenshot_animations_should_trigger_particular_events_for_css_transitions(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/css-transition.html")
    div = page.locator("div")
    div.evaluate(
        """async el => {
            window._EVENTS = [];
            el.addEventListener('transitionend', () => {
                window._EVENTS.push('transitionend');
                console.log('transitionend');
            }, false);
            const animation = el.getAnimations()[0];
            animation.oncancel = () => window._EVENTS.push('oncancel');
            animation.onfinish = () => window._EVENTS.push('onfinish');
            animation.onremove = () => window._EVENTS.push('onremove');
            await animation.ready;
        }"""
    )
    with page.expect_console_message(lambda msg: msg.text == "transitionend"):
        page.screenshot(animations="disabled")
    assert page.evaluate("() => window._EVENTS") == [
        "onfinish",
        "transitionend",
    ]


def test_SS_062_page_screenshot_animations_should_trigger_particular_events_for_i_nfinite_css_animation(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/rotate-z.html")
    div = page.locator("div")
    div.evaluate(
        """async el => {
            window._EVENTS = [];
            el.addEventListener('animationcancel', () => {
                window._EVENTS.push('animationcancel');
                console.log('animationcancel');
            }, false);
            const animation = el.getAnimations()[0];
            animation.oncancel = () => window._EVENTS.push('oncancel');
            animation.onfinish = () => window._EVENTS.push('onfinish');
            animation.onremove = () => window._EVENTS.push('onremove');
            await animation.ready;
        }"""
    )
    with page.expect_console_message(lambda msg: msg.text == "animationcancel"):
        page.screenshot(animations="disabled")
    assert page.evaluate("() => window._EVENTS") == [
        "oncancel",
        "animationcancel",
    ]


def test_SS_063_page_screenshot_animations_should_trigger_particular_events_for_finite_css_animation(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/rotate-z.html")
    div = page.locator("div")
    div.evaluate(
        """async el => {
            window._EVENTS = [];
            // Make CSS animation to be finite.
            el.style.setProperty('animation-iteration-count', '1000');
            el.addEventListener('animationend', () => {
                window._EVENTS.push('animationend');
                console.log('animationend');
            }, false);
            const animation = el.getAnimations()[0];
            animation.oncancel = () => window._EVENTS.push('oncancel');
            animation.onfinish = () => window._EVENTS.push('onfinish');
            animation.onremove = () => window._EVENTS.push('onremove');
            await animation.ready;
        }"""
    )
    # Ensure CSS animation is finite.
    assert (
        div.evaluate(
            "async el => Number.isFinite(el.getAnimations()[0].effect.getComputedTiming().endTime)"
        )
        is True
    )
    with page.expect_console_message(lambda msg: msg.text == "animationend"):
        page.screenshot(animations="disabled")
    assert page.evaluate("() => window._EVENTS") == [
        "onfinish",
        "animationend",
    ]


def test_SS_064_page_screenshot_animations_should_wait_for_fonts_to_load(
    page: Page, server: Server, browser_name: str, is_win: bool
) -> None:
    if is_win:
        pytest.skip(
            "fixme: This requires a windows-specific test expectations. https://github.com/microsoft/playwright/issues/12707"
        )
    page.set_viewport_size({"width": 500, "height": 500})
    font_requests: List[TestServerRequest] = []
    # Stall font loading.
    server.set_route("/webfont/iconfont.woff2", font_requests.append)
    page.goto(
        server.PREFIX + "/webfont/webfont.html",
        wait_until="domcontentloaded",  # 'load' will not happen if webfont is pending
    )

    # Make sure screenshot times out while webfont is stalled.
    with pytest.raises(Error) as exc_info:
        page.screenshot(timeout=200)
    assert "waiting for fonts to load..." in exc_info.value.message
    assert "Timeout 200ms exceeded" in exc_info.value.message

    while not font_requests:
        page.wait_for_timeout(10)
    font_request = font_requests[0]
    reactor.callFromThread(
        font_request.serve_file, server.static_path / "webfont" / "iconfont.woff2"
    )
    icons_screenshot = page.screenshot()
    assert_to_match_golden(
        browser_name, icons_screenshot, "screenshot-web-font.png", max_diff_pixels=50
    )


def test_SS_065_should_throw_if_screenshot_size_is_too_large(
    page: Page, browser_name: str, is_mac: bool
) -> None:
    max_size = 32767
    page.set_content(
        f"<style>body {{margin: 0; padding: 0;}}</style><div style='min-height: {max_size}px; background: red;'></div>"
    )
    result = page.screenshot(full_page=True)
    assert result

    page.set_content(
        f"<style>body {{margin: 0; padding: 0;}}</style><div style='min-height: {max_size + 1}px; background: red;'></div>"
    )
    exception_message = ""
    try:
        page.screenshot(full_page=True)
    except Error as e:
        exception_message = e.message
    if browser_name == "firefox" or (browser_name == "webkit" and not is_mac):
        assert "Cannot take screenshot larger than 32767" in exception_message


def test_SS_066_page_screenshot_should_capture_css_transform(
    page: Page, browser_name: str, assert_to_be_golden: GoldenAssert
) -> None:
    if browser_name == "webkit":
        pytest.skip("fixme: browserName === 'webkit'")
    page.set_content(CSS_TRANSFORM_CONTENT)

    # expect(page).toHaveScreenshot() takes the screenshot with these options.
    screenshot = page.screenshot(animations="disabled", caret="hide", scale="css")
    assert_to_be_golden(
        screenshot, "SS-066-page-screenshot-should-capture-css-transform-1.png"
    )


def test_SS_067_should_capture_css_box_shadow(
    page: Page, assert_to_be_golden: GoldenAssert
) -> None:
    page.set_content(
        '<div style="box-shadow: red 10px 10px 10px; width: 50px; height: 50px;"></div>'
    )
    # expect(page).toHaveScreenshot() takes the screenshot with these options.
    screenshot = page.screenshot(animations="disabled", caret="hide", scale="css")
    assert_to_be_golden(screenshot, "SS-067-should-capture-css-box-shadow-1.png")
