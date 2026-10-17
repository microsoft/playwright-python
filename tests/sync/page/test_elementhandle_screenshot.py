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

"""Port of tests/page/elementhandle-screenshot.spec.ts."""

import io
import subprocess
from pathlib import Path
from typing import Any, Callable, List

import pytest
from PIL import Image

from playwright.sync_api import Error, Page
from tests.server import Server

from ..utils import Utils


@pytest.fixture(autouse=True)
def skip_headed_firefox(browser_name: str, headless: bool) -> None:
    if browser_name == "firefox" and not headless:
        pytest.skip("upstream skips element screenshots in headed Firefox")


def fontconfig_serif_family() -> str:
    """The font family that fontconfig picks for "serif", or "" without fontconfig."""
    try:
        return subprocess.run(
            ["fc-match", "--format=%{family}", "serif"],
            capture_output=True,
            text=True,
        ).stdout
    except OSError:
        return ""


def test_EH_074_element_screenshot_should_work(
    page: Page, server: Server, assert_to_be_golden: Callable[[bytes, str], None]
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.goto(server.PREFIX + "/grid.html")
    page.evaluate("() => window.scrollBy(50, 100)")
    element_handle = page.query_selector(".box:nth-of-type(3)")
    assert element_handle
    screenshot = element_handle.screenshot()
    assert_to_be_golden(screenshot, "screenshot-element-bounding-box.png")


def test_EH_075_element_screenshot_should_work_with_webp(
    page: Page, server: Server
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.goto(server.PREFIX + "/grid.html")
    element_handle = page.query_selector(".box:nth-of-type(3)")
    assert element_handle
    webp_image = Image.open(io.BytesIO(element_handle.screenshot(type="webp")))
    assert webp_image.format == "WEBP"
    # The default webp screenshot is lossless, so it must decode to the exact same pixels as png.
    png_image = Image.open(io.BytesIO(element_handle.screenshot(type="png")))
    assert webp_image.width == png_image.width
    assert webp_image.height == png_image.height
    assert webp_image.convert("RGBA").tobytes() == png_image.convert("RGBA").tobytes()


def test_EH_076_element_screenshot_should_work_when_main_world_busts_json_stringify(
    page: Page, server: Server, assert_to_be_golden: Callable[[bytes, str], None]
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.goto(server.PREFIX + "/grid.html")
    page.evaluate(
        """() => {
      window.scrollBy(50, 100);
      JSON.stringify = () => undefined;
    }"""
    )
    element_handle = page.query_selector(".box:nth-of-type(3)")
    assert element_handle
    screenshot = element_handle.screenshot()
    assert_to_be_golden(screenshot, "screenshot-element-bounding-box.png")


def test_EH_077_element_screenshot_should_take_into_account_padding_and_border(
    page: Page,
    browser_name: str,
    is_linux: bool,
    assert_to_be_golden: Callable[[bytes, str], None],
) -> None:
    if (
        browser_name in ("firefox", "webkit")
        and is_linux
        and fontconfig_serif_family() != "DejaVu Serif"
    ):
        # The text "oooo" above the element overflows into its border with other fonts.
        pytest.skip("the golden needs DejaVu Serif as the default serif font")
    page.set_viewport_size({"width": 500, "height": 500})
    page.set_content(
        """
      <div style="height: 14px">oooo</div>
      <style>div {
        border: 2px solid blue;
        background: green;
        width: 50px;
        height: 50px;
      }
      </style>
      <div id="d"></div>
    """
    )
    element_handle = page.query_selector("div#d")
    assert element_handle
    screenshot = element_handle.screenshot()
    assert_to_be_golden(screenshot, "screenshot-element-padding-border.png")


def test_EH_078_element_screenshot_should_capture_full_element_when_larger_than_viewport_in_parallel(
    page: Page,
    utils: Utils,
    assert_to_be_golden: Callable[[bytes, str], None],
    sync_gather: Callable[..., List[Any]],
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})

    page.set_content(
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
    element_handles = page.query_selector_all("div.to-screenshot")
    screenshots = sync_gather(*[handle.screenshot for handle in element_handles])
    assert_to_be_golden(screenshots[2], "screenshot-element-larger-than-viewport.png")

    utils.verify_viewport(page, 500, 500)


def test_EH_079_element_screenshot_should_capture_full_element_when_larger_than_viewport(
    page: Page, utils: Utils, assert_to_be_golden: Callable[[bytes, str], None]
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})

    page.set_content(
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
    element_handle = page.query_selector("div.to-screenshot")
    assert element_handle
    screenshot = element_handle.screenshot()
    assert_to_be_golden(screenshot, "screenshot-element-larger-than-viewport.png")

    utils.verify_viewport(page, 500, 500)


def test_EH_080_element_screenshot_should_scroll_element_into_view(
    page: Page, assert_to_be_golden: Callable[[bytes, str], None]
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.set_content(
        """
      <div style="height: 14px">oooo</div>
      <style>div.above {
        border: 2px solid blue;
        background: red;
        height: 1500px;
      }
      div.to-screenshot {
        border: 2px solid blue;
        background: green;
        width: 50px;
        height: 50px;
      }
      </style>
      <div class="above"></div>
      <div class="to-screenshot"></div>
    """
    )
    element_handle = page.query_selector("div.to-screenshot")
    assert element_handle
    screenshot = element_handle.screenshot()
    assert_to_be_golden(screenshot, "screenshot-element-scrolled-into-view.png")


def test_EH_081_element_screenshot_should_scroll_15000px_into_view(
    page: Page, assert_to_be_golden: Callable[[bytes, str], None]
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.set_content(
        """
      <div style="height: 14px">oooo</div>
      <style>div.above {
        border: 2px solid blue;
        background: red;
        height: 15000px;
      }
      div.to-screenshot {
        border: 2px solid blue;
        background: green;
        width: 50px;
        height: 50px;
      }
      </style>
      <div class="above"></div>
      <div class="to-screenshot"></div>
    """
    )
    element_handle = page.query_selector("div.to-screenshot")
    assert element_handle
    screenshot = element_handle.screenshot()
    assert_to_be_golden(screenshot, "screenshot-element-scrolled-into-view.png")


def test_EH_082_element_screenshot_should_work_with_a_rotated_element(
    page: Page, assert_to_be_golden: Callable[[bytes, str], None]
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.set_content(
        """<div style="position:absolute;
                                      top: 100px;
                                      left: 100px;
                                      width: 100px;
                                      height: 100px;
                                      background: green;
                                      transform: rotateZ(200deg);">&nbsp;</div>"""
    )
    element_handle = page.query_selector("div")
    assert element_handle
    screenshot = element_handle.screenshot()
    assert_to_be_golden(screenshot, "screenshot-element-rotate.png")


def test_EH_083_element_screenshot_should_fail_to_screenshot_a_detached_element(
    page: Page,
) -> None:
    page.set_content("<h1>remove this</h1>")
    element_handle = page.query_selector("h1")
    assert element_handle
    page.evaluate("element => element.remove()", element_handle)
    with pytest.raises(Error) as exc_info:
        element_handle.screenshot()
    assert "Element is not attached to the DOM" in exc_info.value.message


def test_EH_084_element_screenshot_should_timeout_waiting_for_visible(
    page: Page,
) -> None:
    page.set_content('<div style="width: 50px; height: 0"></div>')
    div = page.query_selector("div")
    assert div
    with pytest.raises(Error) as exc_info:
        div.screenshot(timeout=3000)
    assert "ElementHandle.screenshot: Timeout 3000ms exceeded" in exc_info.value.message
    assert "element is not visible" in exc_info.value.message


def test_EH_085_element_screenshot_should_wait_for_visible(
    page: Page,
    server: Server,
    utils: Utils,
    assert_to_be_golden: Callable[[bytes, str], None],
    sync_gather: Callable[..., List[Any]],
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.goto(server.PREFIX + "/grid.html")
    page.evaluate("() => window.scrollBy(50, 100)")
    element_handle = page.query_selector(".box:nth-of-type(3)")
    assert element_handle
    element_handle.evaluate("e => e.style.visibility = 'hidden'")
    done = False

    def take_screenshot() -> bytes:
        nonlocal done
        buffer = element_handle.screenshot()
        done = True
        return buffer

    def show() -> None:
        utils.rafraf(page, 10)
        assert done is False
        element_handle.evaluate("e => e.style.visibility = 'visible'")

    screenshot, _ = sync_gather(take_screenshot, show)
    assert_to_be_golden(screenshot, "screenshot-element-bounding-box.png")


def test_EH_086_element_screenshot_should_work_for_an_element_with_fractional_dimensions(
    page: Page, assert_to_be_golden: Callable[[bytes, str], None]
) -> None:
    page.set_content(
        '<div style="width:48.51px;height:19.8px;border:1px solid black;"></div>'
    )
    element_handle = page.query_selector("div")
    assert element_handle
    screenshot = element_handle.screenshot()
    assert_to_be_golden(screenshot, "screenshot-element-fractional.png")


def test_EH_087_element_screenshot_should_work_for_an_element_with_an_offset(
    page: Page, assert_to_be_golden: Callable[[bytes, str], None]
) -> None:
    page.set_content(
        '<div style="position:absolute; top: 10.3px; left: 20.4px;width:50.3px;height:20.2px;border:1px solid black;"></div>'
    )
    element_handle = page.query_selector("div")
    assert element_handle
    screenshot = element_handle.screenshot()
    assert_to_be_golden(screenshot, "screenshot-element-fractional-offset.png")


def test_EH_088_element_screenshot_should_wait_for_element_to_stop_moving(
    page: Page,
    server: Server,
    utils: Utils,
    assert_to_be_golden: Callable[[bytes, str], None],
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.goto(server.PREFIX + "/grid.html")
    element_handle = page.query_selector(".box:nth-of-type(3)")
    assert element_handle
    element_handle.evaluate("e => e.classList.add('animation')")
    utils.rafraf(page)
    screenshot = element_handle.screenshot()
    assert_to_be_golden(screenshot, "screenshot-element-bounding-box.png")


def test_EH_089_element_screenshot_should_take_screenshot_of_disabled_button(
    page: Page,
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.set_content("<button disabled>Click me</button>")
    button = page.query_selector("button")
    assert button
    screenshot = button.screenshot()
    assert isinstance(screenshot, bytes)


def test_EH_090_element_screenshot_path_option_should_create_subdirectories(
    page: Page,
    server: Server,
    tmp_path: Path,
    assert_to_be_golden: Callable[[bytes, str], None],
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.goto(server.PREFIX + "/grid.html")
    page.evaluate("() => window.scrollBy(50, 100)")
    element_handle = page.query_selector(".box:nth-of-type(3)")
    assert element_handle
    output_path = tmp_path / "these" / "are" / "directories" / "screenshot.png"
    element_handle.screenshot(path=output_path)
    assert_to_be_golden(output_path.read_bytes(), "screenshot-element-bounding-box.png")


def test_EH_091_element_screenshot_should_prefer_type_over_extension(
    page: Page, server: Server, tmp_path: Path
) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.goto(server.PREFIX + "/grid.html")
    page.evaluate("() => window.scrollBy(50, 100)")
    element_handle = page.query_selector(".box:nth-of-type(3)")
    assert element_handle
    output_path = tmp_path / "file.png"
    buffer = element_handle.screenshot(path=output_path, type="jpeg")
    assert [buffer[0], buffer[1], buffer[2]] == [0xFF, 0xD8, 0xFF]


def test_EH_092_element_screenshot_should_not_issue_resize_event(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/grid.html")
    resize_triggered = False

    def resize() -> None:
        nonlocal resize_triggered
        resize_triggered = True

    page.expose_function("resize", resize)
    page.evaluate("() => { window.addEventListener('resize', () => window.resize()); }")
    element_handle = page.query_selector(".box:nth-of-type(3)")
    assert element_handle
    element_handle.screenshot()
    assert not resize_triggered
