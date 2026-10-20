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

"""Port of tests/library/video.spec.ts."""

import asyncio
import io
import os
import platform as os_platform
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Tuple, TypeVar

import pytest
from greenlet import greenlet
from PIL import Image

from playwright._impl._greenlets import wait_for_future
from playwright.sync_api import (
    Browser,
    BrowserContext,
    BrowserType,
    Error,
    Page,
    Playwright,
    ViewportSize,
)
from tests.helpers.trace_parser import parse_trace_raw
from tests.helpers.video_player import (
    VideoPlayer,
    every_pixel,
    expect_all,
    expect_red_frames,
    find_videos,
    is_almost_black,
    is_almost_gray,
    is_almost_red,
)
from tests.server import Server, TestServerRequest
from tests.utils import relative_path

from ..utils import utils

T = TypeVar("T")


def ensure_some_frames(page: Page) -> None:
    """Port of ensureSomeFrames() in tests/config/utils.ts."""
    utils.rafraf(page, 100)
    page.screenshot()


def wait_for(page: Page, awaitable: "Awaitable[T]") -> T:
    """Port of `await promise`: runs the event loop until the awaitable settles."""
    future = asyncio.ensure_future(awaitable, loop=page._loop)
    wait_for_future(page._loop, page._dispatcher_fiber, future)
    return future.result()


def run_in_background(page: Page, action: Callable[[], Any]) -> "asyncio.Future[Any]":
    """Like calling an async function without await: starts the action and goes on.

    The action runs in a greenlet of its own. The future settles with the result or the
    error of the action; wait_for(page, future) waits for it.
    """
    result: "asyncio.Future[Any]" = page._loop.create_future()

    def run() -> None:
        try:
            result.set_result(action())
        except Exception as error:
            result.set_result(error)

    async def start() -> None:
        greenlet(run).switch()

    # start() returns once the action waits for the driver, after it sent its message.
    wait_for(page, start())
    return result


def test_VI_001_screencast_should_not_have_video_by_default(page: Page) -> None:
    assert page.video is None


def test_VI_003_screencast_should_capture_static_page(
    browser: Browser, browser_name: str, tmp_path: Path
) -> None:
    # Firefox does not have a mobile variant and has a large minimum size (500 on windows and 450 elsewhere).
    size: ViewportSize = (
        {"width": 500, "height": 400}
        if browser_name == "firefox"
        else {"width": 320, "height": 240}
    )
    context = browser.new_context(
        record_video_dir=tmp_path,
        record_video_size=size,
        viewport=size,
    )
    page = context.new_page()

    page.evaluate("() => document.body.style.backgroundColor = 'red'")
    ensure_some_frames(page)
    context.close()

    assert page.video
    video_file = page.video.path()
    expect_red_frames(video_file, size)


def test_VI_004_screencast_should_pad_a_short_frame_to_the_video_size(
    browser: Browser, tmp_path: Path
) -> None:
    video_size: ViewportSize = {"width": 800, "height": 600}
    context = browser.new_context(
        record_video_dir=tmp_path,
        record_video_size=video_size,
        viewport={"width": 800, "height": 396},
    )
    page = context.new_page()
    ensure_some_frames(page)
    context.close()

    assert page.video
    video_file = page.video.path()
    video_player = VideoPlayer(video_file)
    assert video_player.video_width == video_size["width"]
    assert video_player.video_height == video_size["height"]


def test_VI_005_screencast_should_continue_recording_main_page_after_popup_closes(
    browser: Browser, browser_name: str, tmp_path: Path
) -> None:
    # Firefox does not have a mobile variant and has a large minimum size (500 on windows and 450 elsewhere).
    size: ViewportSize = (
        {"width": 500, "height": 400}
        if browser_name == "firefox"
        else {"width": 320, "height": 240}
    )
    context = browser.new_context(
        record_video_dir=tmp_path,
        record_video_size=size,
        viewport=size,
    )
    page = context.new_page()
    page.set_content('<a target=_blank href="about:blank">clickme</a>')
    with page.expect_popup() as popup_info:
        page.click("a")
    popup = popup_info.value
    popup.close()

    page.evaluate(
        """() => {
      document.body.textContent = ''; // remove link
      document.body.style.backgroundColor = 'red';
    }"""
    )
    ensure_some_frames(page)
    context.close()

    assert page.video
    video_file = page.video.path()
    expect_red_frames(video_file, size)


def test_VI_006_screencast_should_expose_video_path(
    browser: Browser, tmp_path: Path
) -> None:
    videos_path = tmp_path
    size: ViewportSize = {"width": 320, "height": 240}
    context = browser.new_context(
        record_video_dir=videos_path,
        record_video_size=size,
        viewport=size,
    )
    page = context.new_page()
    page.evaluate("() => document.body.style.backgroundColor = 'red'")
    assert page.video
    path = page.video.path()
    assert str(videos_path) in str(path)
    context.close()
    assert path.exists()


def test_VI_007_screencast_should_delete_video(
    browser: Browser, tmp_path: Path
) -> None:
    videos_path = tmp_path
    size: ViewportSize = {"width": 320, "height": 240}
    context = browser.new_context(
        record_video_dir=videos_path,
        record_video_size=size,
        viewport=size,
    )
    page = context.new_page()
    video = page.video
    assert video
    delete_promise = run_in_background(page, lambda: video.delete())
    page.evaluate("() => document.body.style.backgroundColor = 'red'")
    ensure_some_frames(page)
    context.close()

    video_path = video.path()
    assert wait_for(page, delete_promise) is None
    assert not video_path.exists()


def test_VI_008_screencast_should_expose_video_path_blank_page(
    browser: Browser, tmp_path: Path
) -> None:
    videos_path = tmp_path
    size: ViewportSize = {"width": 320, "height": 240}
    context = browser.new_context(
        record_video_dir=videos_path,
        record_video_size=size,
        viewport=size,
    )
    page = context.new_page()
    assert page.video
    path = page.video.path()
    assert str(videos_path) in str(path)
    context.close()
    assert path.exists()


def test_VI_009_screencast_should_work_with_weird_screen_resolution(
    browser: Browser, tmp_path: Path
) -> None:
    videos_path = tmp_path
    size: ViewportSize = {"width": 1904, "height": 609}
    context = browser.new_context(
        record_video_dir=videos_path,
        record_video_size=size,
        viewport=size,
    )
    page = context.new_page()
    assert page.video
    path = page.video.path()
    assert str(videos_path) in str(path)
    context.close()
    assert path.exists()


def test_VI_010_screencast_should_work_with_relative_path_for_record_video_dir(
    browser: Browser, tmp_path: Path
) -> None:
    videos_path = relative_path(tmp_path)
    size: ViewportSize = {"width": 320, "height": 240}
    context = browser.new_context(
        record_video_dir=videos_path,
        record_video_size=size,
        viewport=size,
    )
    page = context.new_page()
    assert page.video
    video_path = page.video.path()
    context.close()
    assert video_path.exists()


def test_VI_011_screencast_should_expose_video_path_blank_popup(
    browser: Browser, tmp_path: Path
) -> None:
    videos_path = tmp_path
    size: ViewportSize = {"width": 320, "height": 240}
    context = browser.new_context(
        record_video_dir=videos_path,
        record_video_size=size,
        viewport=size,
    )
    page = context.new_page()
    with page.expect_popup() as popup_info:
        page.evaluate('window.open("about:blank")')
    popup = popup_info.value
    assert popup.video
    path = popup.video.path()
    assert str(videos_path) in str(path)
    context.close()
    assert path.exists()


def test_VI_012_screencast_should_capture_navigation(
    browser: Browser, server: Server, tmp_path: Path
) -> None:
    context = browser.new_context(
        record_video_dir=tmp_path,
        record_video_size={"width": 1280, "height": 720},
    )
    page = context.new_page()

    page.goto(server.PREFIX + "/background-color.html#rgb(0,0,0)")
    ensure_some_frames(page)
    page.goto(server.CROSS_PROCESS_PREFIX + "/background-color.html#rgb(100,100,100)")
    ensure_some_frames(page)
    context.close()

    assert page.video
    video_file = page.video.path()
    video_player = VideoPlayer(video_file)
    duration = video_player.duration
    assert duration > 0

    # Find a frame with all almost-black pixels.
    frame = video_player.find_frame(lambda pixels: every_pixel(pixels, is_almost_black))
    assert frame is not None

    pixels = video_player.seek_last_frame()
    expect_all(pixels, is_almost_gray)


def test_VI_013_screencast_should_capture_css_transformation(
    browser: Browser,
    server: Server,
    headless: bool,
    browser_name: str,
    platform: str,
    tmp_path: Path,
) -> None:
    if not headless:
        pytest.skip("fixme: Fails on headed")
    if browser_name == "webkit" and platform == "win32":
        pytest.skip("fixme")

    size: ViewportSize = {"width": 600, "height": 400}
    # Set viewport equal to screencast frame size to avoid scaling.
    context = browser.new_context(
        record_video_dir=tmp_path,
        record_video_size=size,
        viewport=size,
    )
    page = context.new_page()

    page.goto(server.PREFIX + "/rotate-z.html")
    ensure_some_frames(page)
    context.close()

    assert page.video
    video_file = page.video.path()
    video_player = VideoPlayer(video_file)
    duration = video_player.duration
    assert duration > 0

    pixels = video_player.seek_last_frame((95, 45))
    expect_all(pixels, is_almost_red)


def test_VI_014_screencast_should_work_for_popups(
    browser: Browser,
    server: Server,
    browser_name: str,
    tmp_path: Path,
    sync_gather: Callable[..., List[Any]],
) -> None:
    if browser_name == "firefox":
        pytest.skip("fixme: https://github.com/microsoft/playwright/issues/14557")
    videos_path = tmp_path
    size: ViewportSize = {"width": 600, "height": 400}
    context = browser.new_context(
        record_video_dir=videos_path,
        record_video_size=size,
        viewport=size,
    )

    page = context.new_page()
    page.goto(server.EMPTY_PAGE)
    with page.expect_popup() as popup_info:
        page.evaluate("() => { window.open('about:blank'); }")
    popup = popup_info.value
    popup.evaluate("() => document.body.style.backgroundColor = 'red'")
    sync_gather(lambda: ensure_some_frames(page), lambda: ensure_some_frames(popup))
    context.close()

    assert page.video
    assert popup.video
    page_video_file = page.video.path()
    popup_video_file = popup.video.path()
    assert page_video_file != popup_video_file
    expect_red_frames(popup_video_file, size)

    video_files = find_videos(videos_path)
    assert len(video_files) == 2


def test_VI_015_screencast_should_scale_frames_down_to_the_requested_size(
    browser: Browser,
    browser_name: str,
    server: Server,
    headless: bool,
    is_headless_shell: bool,
    tmp_path: Path,
) -> None:
    if not headless:
        pytest.skip("fixme: Fails on headed")
    if browser_name == "chromium" and not is_headless_shell:
        pytest.skip("fixme: Chromium (but not headless shell) has a min width issue")

    context = browser.new_context(
        record_video_dir=tmp_path,
        # Set size to 1/2 of the viewport.
        record_video_size={"width": 320, "height": 240},
        viewport={"width": 640, "height": 480},
    )
    page = context.new_page()

    page.goto(server.PREFIX + "/checkerboard.html")
    # Update the picture to ensure enough frames are generated.
    page.eval_on_selector(
        ".container",
        """container => {
      container.firstElementChild.classList.remove('red');
    }""",
    )
    ensure_some_frames(page)
    page.eval_on_selector(
        ".container",
        """container => {
      container.firstElementChild.classList.add('red');
    }""",
    )
    ensure_some_frames(page)
    context.close()

    assert page.video
    video_file = page.video.path()
    video_player = VideoPlayer(video_file)
    duration = video_player.duration
    assert duration > 0

    expect_all(video_player.seek_last_frame((10, 10)), is_almost_red)
    expect_all(video_player.seek_last_frame((300, 10)), is_almost_gray)
    expect_all(video_player.seek_last_frame((10, 200)), is_almost_gray)
    expect_all(video_player.seek_last_frame((300, 200)), is_almost_red)


def test_VI_016_screencast_should_use_viewport_scaled_down_to_fit_into_800x800_as_default_size(
    browser: Browser, tmp_path: Path
) -> None:
    size: ViewportSize = {"width": 1600, "height": 1200}
    context = browser.new_context(record_video_dir=tmp_path, viewport=size)

    page = context.new_page()
    ensure_some_frames(page)
    context.close()

    assert page.video
    video_file = page.video.path()
    video_player = VideoPlayer(video_file)
    assert video_player.video_width == 800
    assert video_player.video_height == 600


def test_VI_017_screencast_should_be_800x450_by_default(
    browser: Browser, tmp_path: Path
) -> None:
    context = browser.new_context(record_video_dir=tmp_path)

    page = context.new_page()
    ensure_some_frames(page)
    context.close()

    assert page.video
    video_file = page.video.path()
    video_player = VideoPlayer(video_file)
    assert video_player.video_width == 800
    assert video_player.video_height == 450


def test_VI_018_screencast_should_record_video_with_the_requested_fps(
    browser: Browser, tmp_path: Path
) -> None:
    context = browser.new_context(record_video_dir=tmp_path, record_video_fps=60)

    page = context.new_page()
    ensure_some_frames(page)
    context.close()

    assert page.video
    video_player = VideoPlayer(page.video.path())
    assert video_player.fps == 60


def test_VI_019_screencast_should_throw_on_invalid_fps(
    browser: Browser, tmp_path: Path
) -> None:
    with pytest.raises(Error) as exc_info:
        browser.new_context(record_video_dir=tmp_path, record_video_fps=0)
    assert (
        '"recordVideo.fps" must be a positive number, got 0' in exc_info.value.message
    )


def test_VI_020_screencast_should_be_800x600_with_null_viewport(
    browser: Browser, headless: bool, browser_name: str, tmp_path: Path
) -> None:
    if browser_name == "firefox" and headless:
        pytest.skip("fixme: Fails in headless on bots")

    context = browser.new_context(record_video_dir=tmp_path, no_viewport=True)

    page = context.new_page()
    ensure_some_frames(page)
    context.close()

    assert page.video
    video_file = page.video.path()
    video_player = VideoPlayer(video_file)
    assert video_player.video_width == 800
    assert video_player.video_height == 600


def test_VI_021_screencast_should_capture_static_page_in_persistent_context_smoke(
    launch_persistent: Callable[..., Tuple[BrowserContext, Page]],
    browser_name: str,
    is_mac: bool,
    tmp_path: Path,
) -> None:
    if browser_name == "webkit" and is_mac and os_platform.machine() == "arm64":
        pytest.skip(
            "Is only failing on self-hosted github actions runner on M1 mac; not reproducible locally"
        )
    size: ViewportSize = {"width": 600, "height": 400}
    context, page = launch_persistent(
        record_video_dir=tmp_path,
        record_video_size=size,
        viewport=size,
    )

    page.evaluate("() => document.body.style.backgroundColor = 'red'")
    ensure_some_frames(page)
    context.close()

    assert page.video
    video_file = page.video.path()
    video_player = VideoPlayer(video_file)
    duration = video_player.duration
    assert duration > 0

    assert video_player.video_width == 600
    assert video_player.video_height == 400

    expect_all(video_player.seek_last_frame(), is_almost_red)


def test_VI_022_screencast_should_emulate_an_iphone(
    context_factory: Callable[..., BrowserContext],
    playwright: Playwright,
    tmp_path: Path,
) -> None:
    device = playwright.devices["iPhone 6"]
    context = context_factory(**device, record_video_dir=tmp_path)

    page = context.new_page()
    ensure_some_frames(page)
    context.close()

    assert page.video
    video_file = page.video.path()
    video_player = VideoPlayer(video_file)
    assert video_player.video_width == 374
    assert video_player.video_height == 666


def test_VI_023_screencast_should_throw_on_browser_close(
    browser_type: BrowserType, launch_arguments: Dict, tmp_path: Path
) -> None:
    size: ViewportSize = {"width": 320, "height": 240}
    browser = browser_type.launch(**launch_arguments)
    context = browser.new_context(
        record_video_dir=tmp_path,
        record_video_size=size,
        viewport=size,
    )

    page = context.new_page()
    ensure_some_frames(page)
    browser.close()

    file = tmp_path / "saved-video-"
    assert page.video
    with pytest.raises(Error) as exc_info:
        page.video.save_as(file)
    assert "browser has been closed" in exc_info.value.message


def test_VI_024_screencast_should_throw_if_browser_dies(
    browser_type: BrowserType, launch_arguments: Dict, tmp_path: Path
) -> None:
    size: ViewportSize = {"width": 320, "height": 240}
    browser = browser_type.launch(**launch_arguments)

    context = browser.new_context(
        record_video_dir=tmp_path,
        record_video_size=size,
        viewport=size,
    )

    page = context.new_page()
    ensure_some_frames(page)
    wait_for(page, browser._impl_obj._channel.killForTests())

    file = tmp_path / "saved-video-"
    assert page.video
    with pytest.raises(Error) as exc_info:
        page.video.save_as(file)
    assert "rowser has been closed" in exc_info.value.message


def test_VI_025_screencast_should_wait_for_video_to_finish_if_page_was_closed(
    browser_type: BrowserType, launch_arguments: Dict, tmp_path: Path
) -> None:
    size: ViewportSize = {"width": 320, "height": 240}
    browser = browser_type.launch(**launch_arguments)

    video_dir = tmp_path
    context = browser.new_context(
        record_video_dir=video_dir,
        record_video_size=size,
        viewport=size,
    )

    page = context.new_page()
    ensure_some_frames(page)
    page.close()
    context.close()
    browser.close()

    video_files = find_videos(video_dir)
    assert len(video_files) == 1
    video_player = VideoPlayer(video_files[0])
    assert video_player.video_width == 320
    assert video_player.video_height == 240


def test_VI_026_screencast_should_close_ffmpeg_even_if_there_were_no_frames(
    browser_type: BrowserType, launch_arguments: Dict, tmp_path: Path
) -> None:
    size: ViewportSize = {"width": 320, "height": 240}
    browser = browser_type.launch(**launch_arguments)

    video_dir = tmp_path
    context = browser.new_context(
        record_video_dir=video_dir,
        record_video_size=size,
        viewport=size,
    )

    page1 = context.new_page()
    page1.close()

    page2 = context.new_page()
    page2.close()

    context.close()
    browser.close()

    video_files = find_videos(video_dir)
    assert len(video_files) == 2


def test_VI_027_screencast_should_not_create_video_for_internal_pages(
    browser: Browser, server: Server, tmp_path: Path
) -> None:
    def handler(request: TestServerRequest) -> None:
        request.setHeader("Set-Cookie", "name=value")
        request.finish()

    server.set_route("/empty.html", handler)

    video_dir = tmp_path
    context = browser.new_context(record_video_dir=video_dir)

    page = context.new_page()
    page.goto(server.EMPTY_PAGE)
    ensure_some_frames(page)

    cookies = context.cookies()
    assert len(cookies) == 1
    context.storage_state()
    context.close()

    files = os.listdir(video_dir)
    assert len(files) == 1


def test_VI_028_screencast_should_capture_full_viewport(
    browser_type: BrowserType,
    launch_arguments: Dict,
    browser_name: str,
    is_win: bool,
    is_headless_shell: bool,
    tmp_path: Path,
) -> None:
    if browser_name == "chromium" and not is_headless_shell:
        pytest.skip("fixme: The square is not on the video")
    if browser_name == "firefox" and is_win:
        pytest.skip("fixme: https://github.com/microsoft/playwright/issues/14405")
    size: ViewportSize = {"width": 600, "height": 400}
    browser = browser_type.launch(**launch_arguments)

    video_dir = tmp_path
    context = browser.new_context(
        viewport=size,
        record_video_dir=video_dir,
        record_video_size=size,
    )

    page = context.new_page()
    page.set_content(
        "<div style='margin: 0; background: red; position: fixed; right:0; bottom:0; width: 30; height: 30;'></div>"
    )
    ensure_some_frames(page)
    page.close()
    context.close()
    browser.close()

    video_files = find_videos(video_dir)
    assert len(video_files) == 1
    video_player = VideoPlayer(video_files[0])
    assert video_player.video_width == size["width"]
    assert video_player.video_height == size["height"]

    # Bottom right corner should be part of the red border.
    # However, headed browsers on mac have rounded corners, so offset by 10.
    pixels = video_player.seek_last_frame((size["width"] - 20, size["height"] - 20))
    expect_all(pixels, is_almost_red)


def test_VI_029_screencast_should_capture_full_viewport_on_hidpi(
    browser_type: BrowserType,
    launch_arguments: Dict,
    browser_name: str,
    headless: bool,
    is_win: bool,
    is_linux: bool,
    is_headless_shell: bool,
    browser_channel: str,
    tmp_path: Path,
) -> None:
    if browser_name == "chromium" and not is_headless_shell:
        pytest.skip("fixme: The square is not on the video")
    if browser_name == "firefox" and is_win:
        pytest.skip("fixme: https://github.com/microsoft/playwright/issues/14405")
    if (
        browser_name == "webkit"
        and not headless
        and (is_linux or (is_win and browser_channel == "webkit-wsl"))
    ):
        pytest.skip("fixme: https://github.com/microsoft/playwright/issues/22617")
    size: ViewportSize = {"width": 600, "height": 400}
    browser = browser_type.launch(**launch_arguments)

    video_dir = tmp_path
    context = browser.new_context(
        viewport=size,
        device_scale_factor=3,
        record_video_dir=video_dir,
        record_video_size=size,
    )

    page = context.new_page()
    page.set_content(
        "<div style='margin: 0; background: red; position: fixed; right:0; bottom:0; width: 30; height: 30;'></div>"
    )
    ensure_some_frames(page)
    page.close()
    context.close()
    browser.close()

    video_files = find_videos(video_dir)
    assert len(video_files) == 1
    video_player = VideoPlayer(video_files[0])
    assert video_player.video_width == size["width"]
    assert video_player.video_height == size["height"]

    # Bottom right corner should be part of the red border.
    # However, headed browsers on mac have rounded corners, so offset by 10.
    pixels = video_player.seek_last_frame((size["width"] - 20, size["height"] - 20))
    expect_all(pixels, is_almost_red)


def test_VI_030_screencast_should_work_with_video_trace(
    browser: Browser,
    headless: bool,
    browser_name: str,
    is_headless_shell: bool,
    tmp_path: Path,
) -> None:
    if not headless:
        pytest.skip("fixme: different trace screencast image size on all browsers")
    if browser_name == "chromium" and not is_headless_shell:
        pytest.skip("fixme: different trace screencast image size")

    size: ViewportSize = {"width": 500, "height": 400}
    trace_file = tmp_path / "trace.zip"

    context = browser.new_context(
        record_video_dir=tmp_path,
        record_video_size=size,
        viewport=size,
    )
    context.tracing.start(screenshots=True)
    page = context.new_page()

    page.evaluate("() => document.body.style.backgroundColor = 'red'")
    ensure_some_frames(page)
    context.tracing.stop(path=trace_file)
    context.close()

    assert page.video
    video_file = page.video.path()
    expect_red_frames(video_file, size)

    trace = parse_trace_raw(trace_file)
    frame = [e for e in trace.events if e["type"] == "screencast-frame"][-1]
    with Image.open(io.BytesIO(trace.resources[frame["file"]])) as decoded:
        image = decoded.convert("RGBA")
    assert image.width == size["width"]
    assert image.height == size["height"]
    data = image.tobytes()
    # Center should be red.
    offset = size["width"] * size["height"] // 2 * 4 + size["width"] * 4 // 2
    pixel = (data[offset], data[offset + 1], data[offset + 2], data[offset + 3])
    assert is_almost_red(pixel) is True


def test_VI_031_should_save_as_video(browser: Browser, tmp_path: Path) -> None:
    videos_path = tmp_path
    size: ViewportSize = {"width": 320, "height": 240}
    context = browser.new_context(
        record_video_dir=videos_path,
        record_video_size=size,
        viewport=size,
    )
    page = context.new_page()
    page.evaluate("() => document.body.style.backgroundColor = 'red'")
    ensure_some_frames(page)
    context.close()

    save_as_path = tmp_path / "my-video.webm"
    assert page.video
    page.video.save_as(save_as_path)
    assert save_as_path.exists()
