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

"""Port of tests/library/screencast.spec.ts."""

import asyncio
import io
import os
import time
from pathlib import Path
from typing import Any, Awaitable, Dict, List, TypeVar

import pytest
from PIL import Image

from playwright._impl._greenlets import wait_for_future
from playwright.sync_api import (
    Browser,
    BrowserType,
    Error,
    Page,
    ScreencastFrame,
    ViewportSize,
)
from tests.helpers.video_player import (
    VideoPlayer,
    expect_frames,
    expect_red_frames,
    is_almost_white,
)
from tests.server import Server
from tests.utils import TARGET_CLOSED_ERROR_MESSAGE

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


def sleep(page: Page, ms: float) -> None:
    """Like `await new Promise(f => setTimeout(f, ms))`: no message to the driver."""
    wait_for(page, asyncio.sleep(ms / 1000))


def jpeg_dimensions(buffer: bytes) -> Dict[str, int]:
    with Image.open(io.BytesIO(buffer)) as image:
        assert image.format == "JPEG"
        return {"width": image.width, "height": image.height}


def test_SC_001_screencast_start_delivers_frames_via_on_frame_callback(
    browser: Browser, server: Server, browser_name: str, is_mac: bool, headless: bool
) -> None:
    if browser_name == "firefox" and is_mac and not headless:
        pytest.skip("fixme: wrong frame size in headed Firefox on Mac")

    context = browser.new_context(viewport={"width": 1000, "height": 400})
    page = context.new_page()

    frames: List[bytes] = []
    size: ViewportSize = {"width": 500, "height": 400}
    page.screencast.start(
        on_frame=lambda frame: frames.append(frame["data"]), size=size
    )
    page.goto(server.EMPTY_PAGE)
    page.evaluate("() => document.body.style.backgroundColor = 'red'")
    ensure_some_frames(page)
    page.screencast.stop()

    assert len(frames) > 0
    for frame in frames:
        # Each frame must be a valid JPEG (starts with FF D8)
        assert frame[0] == 0xFF
        assert frame[1] == 0xD8
        dimensions = jpeg_dimensions(frame)
        # Frame should be scaled down to fit the maximum size.
        assert dimensions["width"] == 500
        assert dimensions["height"] == 200

    context.close()


def test_SC_002_applies_backpressure_while_async_on_frame_callback_is_pending(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context(viewport={"width": 500, "height": 400})
    page = context.new_page()

    loop = page._loop
    callback_done: "asyncio.Future[None]" = loop.create_future()
    first_frame_received: "asyncio.Future[None]" = loop.create_future()
    frame_count = 0
    last_frame_timestamp = 0.0

    def on_frame(frame: ScreencastFrame) -> None:
        nonlocal frame_count, last_frame_timestamp
        frame_count += 1
        last_frame_timestamp = time.monotonic()
        if not first_frame_received.done():
            first_frame_received.set_result(None)
        # The sync callback blocks until released, like the pending async callback.
        wait_for(page, callback_done)

    page.screencast.start(on_frame=on_frame)
    page.goto(server.EMPTY_PAGE)
    page.evaluate(
        """() => {
    const animate = () => {
      document.body.style.backgroundColor = document.body.style.backgroundColor === 'red' ? 'blue' : 'red';
      requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }"""
    )
    wait_for(page, first_frame_received)
    deadline = time.monotonic() + 30
    while (time.monotonic() - last_frame_timestamp) * 1000 <= 1000:
        assert time.monotonic() < deadline
        sleep(page, 100)

    frames_while_blocked = frame_count
    ensure_some_frames(page)
    assert frame_count == frames_while_blocked

    callback_done.set_result(None)
    deadline = time.monotonic() + 30
    while True:
        page.evaluate(
            """() => {
      document.body.style.backgroundColor = document.body.style.backgroundColor === 'red' ? 'blue' : 'red';
    }"""
        )
        ensure_some_frames(page)
        if frame_count > frames_while_blocked:
            break
        assert time.monotonic() < deadline

    page.screencast.stop()
    context.close()


def test_SC_003_on_frame_receives_viewport_size(
    browser: Browser, server: Server, browser_name: str, is_mac: bool, headless: bool
) -> None:
    if browser_name == "firefox" and is_mac and not headless:
        pytest.skip("fixme: wrong frame size in headed Firefox on Mac")

    context = browser.new_context(viewport={"width": 1000, "height": 400})
    page = context.new_page()

    frames: List[Dict[str, Any]] = []
    page.screencast.start(
        on_frame=lambda frame: frames.append(
            {
                "timestamp": frame["timestamp"],
                "viewportWidth": frame["viewportWidth"],
                "viewportHeight": frame["viewportHeight"],
            }
        ),
        size={"width": 500, "height": 400},
    )
    page.goto(server.EMPTY_PAGE)
    ensure_some_frames(page)
    page.screencast.stop()

    assert len(frames) > 0
    for frame in frames:
        assert frame["viewportWidth"] == 1000
        assert frame["viewportHeight"] == 400
        assert isinstance(frame["timestamp"], (int, float))

    context.close()


def test_SC_004_start_throws_if_screencast_is_already_started(
    browser: Browser,
) -> None:
    context = browser.new_context(viewport={"width": 500, "height": 400})
    page = context.new_page()

    page.screencast.start(on_frame=lambda frame: None)
    with pytest.raises(Error, match="Screencast is already started"):
        page.screencast.start(on_frame=lambda frame: None)

    page.screencast.stop()
    context.close()


def test_SC_005_start_allows_restart_with_different_options_after_stop(
    browser: Browser,
) -> None:
    context = browser.new_context(viewport={"width": 500, "height": 400})
    page = context.new_page()

    page.screencast.start(
        on_frame=lambda frame: None, size={"width": 500, "height": 400}
    )
    page.screencast.stop()
    # Different options should succeed once the previous screencast is stopped.
    page.screencast.start(
        on_frame=lambda frame: None, size={"width": 320, "height": 240}
    )
    page.screencast.stop()
    context.close()


def test_SC_006_start_returns_a_disposable_that_stops_screencast(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context(viewport={"width": 500, "height": 400})
    page = context.new_page()

    frames: List[bytes] = []
    page.screencast.start(
        on_frame=lambda frame: frames.append(frame["data"]),
        size={"width": 500, "height": 400},
    )
    page.goto(server.EMPTY_PAGE)
    page.evaluate("() => document.body.style.backgroundColor = 'red'")
    ensure_some_frames(page)
    page.screencast.stop()

    frame_count_after_dispose = len(frames)
    assert frame_count_after_dispose > 0

    # No more frames should arrive after dispose.
    page.evaluate("() => document.body.style.backgroundColor = 'blue'")
    ensure_some_frames(page)
    assert len(frames) == frame_count_after_dispose

    context.close()


def test_SC_007_start_stop_twice_without_path_creates_two_files_in_artifacts_dir(
    browser_type: BrowserType, launch_arguments: Dict, tmp_path: Path
) -> None:
    artifacts_dir = tmp_path / "artifacts"
    browser = browser_type.launch(**launch_arguments, artifacts_dir=artifacts_dir)
    size: ViewportSize = {"width": 800, "height": 800}
    context = browser.new_context(viewport=size)
    page = context.new_page()

    page.screencast.start(path=tmp_path / "video1.webm", size=size)
    page.evaluate("() => document.body.style.backgroundColor = 'red'")
    ensure_some_frames(page)
    page.screencast.stop()

    page.screencast.start(path=tmp_path / "video2.webm", size=size)
    page.evaluate("() => document.body.style.backgroundColor = 'blue'")
    ensure_some_frames(page)
    page.screencast.stop()

    video_files = [f for f in os.listdir(artifacts_dir) if f.endswith(".webm")]
    assert len(video_files) == 2

    context.close()
    browser.close()


def test_SC_008_start_should_work_when_record_video_is_set(
    browser: Browser, tmp_path: Path
) -> None:
    auto_dir = tmp_path / "auto"
    manual_dir = tmp_path / "manual"
    context = browser.new_context(record_video_dir=auto_dir)
    page = context.new_page()

    page.screencast.start(path=manual_dir / "video.webm")
    page.evaluate("() => document.body.style.backgroundColor = 'blue'")
    ensure_some_frames(page)
    page.screencast.stop()
    video_files1 = [f for f in os.listdir(manual_dir) if f.endswith(".webm")]
    assert len(video_files1) == 1

    context.close()
    video_files2 = [f for f in os.listdir(auto_dir) if f.endswith(".webm")]
    assert len(video_files2) == 1


def test_SC_009_start_should_record_video_with_the_requested_fps(
    browser: Browser, tmp_path: Path
) -> None:
    context = browser.new_context()
    page = context.new_page()
    video_path = tmp_path / "video.webm"
    page.screencast.start(path=video_path, fps=60)
    ensure_some_frames(page)
    page.screencast.stop()
    assert VideoPlayer(video_path).fps == 60
    context.close()


def test_SC_010_start_should_throw_on_invalid_fps(page: Page, tmp_path: Path) -> None:
    with pytest.raises(Error) as exc_info:
        page.screencast.start(path=tmp_path / "video.webm", fps=-1)
    assert '"fps" must be a positive number, got -1' in exc_info.value.message


def test_SC_011_start_should_fail_when_another_recording_is_in_progress(
    page: Page, tmp_path: Path
) -> None:
    page.screencast.start(path=tmp_path / "video.webm")
    with pytest.raises(Error) as exc_info:
        page.screencast.start(path=tmp_path / "video2.webm")
    assert "Screencast is already started" in exc_info.value.message


def test_SC_012_stop_should_not_fail_when_no_recording_is_in_progress(
    browser: Browser,
) -> None:
    context = browser.new_context()
    page = context.new_page()
    # stop() is a no-op when screencast is not started.
    page.screencast.stop()
    context.close()


def test_SC_013_start_should_finish_when_page_is_closed(
    browser: Browser, tmp_path: Path
) -> None:
    context = browser.new_context()
    page = context.new_page()
    video_path = tmp_path / "video.webm"
    page.screencast.start(path=video_path, size={"width": 800, "height": 800})
    page.evaluate("() => document.body.style.backgroundColor = 'red'")
    ensure_some_frames(page)
    page.close()
    with pytest.raises(Error) as exc_info:
        page.screencast.stop()
    assert TARGET_CLOSED_ERROR_MESSAGE in exc_info.value.message
    context.close()


def test_SC_014_empty_video(browser: Browser, tmp_path: Path) -> None:
    size: ViewportSize = {"width": 800, "height": 800}
    context = browser.new_context(viewport=size)
    page = context.new_page()
    video_path = tmp_path / "empty-video.webm"
    page.screencast.start(path=video_path, size=size)
    page.screencast.stop()
    context.close()
    expect_frames(video_path, size, is_almost_white)


def test_SC_015_start_dispose_stops_recording(browser: Browser, tmp_path: Path) -> None:
    size: ViewportSize = {"width": 800, "height": 800}
    context = browser.new_context(viewport=size)
    page = context.new_page()
    video_path = tmp_path / "dispose-video.webm"
    with page.screencast.start(path=video_path, size=size):
        page.evaluate("() => document.body.style.backgroundColor = 'red'")
        ensure_some_frames(page)
    expect_red_frames(video_path, size)
    context.close()
