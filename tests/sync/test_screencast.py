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

from pathlib import Path
from typing import List

import pytest

from playwright._impl._api_structures import ScreencastFrame
from playwright.sync_api import Page
from tests.server import Server


def _noop_frame(f: ScreencastFrame) -> None:
    pass


def test_screencast_start_should_deliver_frames_via_on_frame(
    page: Page, server: Server
) -> None:
    frames: List[ScreencastFrame] = []

    def collect_frame(f: ScreencastFrame) -> None:
        frames.append(f)

    page.screencast.start(on_frame=collect_frame)
    page.goto(server.EMPTY_PAGE)
    page.evaluate("() => document.body.style.backgroundColor = 'red'")
    page.wait_for_timeout(500)
    page.screencast.stop()
    assert len(frames) > 0, "expected at least one frame"
    for frame in frames:
        assert frame["data"][:2] == b"\xff\xd8", "expected JPEG frame"


def test_screencast_start_should_throw_if_already_started(
    page: Page,
) -> None:
    page.screencast.start(on_frame=_noop_frame)
    with pytest.raises(Exception, match="already started"):
        page.screencast.start(on_frame=_noop_frame)
    page.screencast.stop()


def test_screencast_start_should_record_video_to_path(
    page: Page, server: Server, tmp_path: Path
) -> None:
    video_path = tmp_path / "video.webm"
    page.screencast.start(path=video_path)
    page.goto(server.EMPTY_PAGE)
    page.evaluate("() => document.body.style.backgroundColor = 'red'")
    page.wait_for_timeout(500)
    page.screencast.stop()
    assert video_path.exists(), f"video file should exist: {video_path}"
    assert video_path.stat().st_size > 0


def test_screencast_start_returns_disposable(page: Page) -> None:
    disposable = page.screencast.start(on_frame=_noop_frame)
    with disposable:
        pass
    # After dispose, starting again should succeed.
    page.screencast.start(on_frame=_noop_frame)
    page.screencast.stop()


def test_screencast_show_overlay(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    disposable = page.screencast.show_overlay("<div>Hello Overlay</div>")
    assert disposable
    with disposable:
        pass


def test_screencast_show_chapter(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    page.screencast.show_chapter("Chapter Title")
    page.screencast.show_chapter(
        "With Description", description="Some details", duration=100
    )


def test_screencast_hide_show_overlays(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    page.screencast.show_overlay("<div>visible</div>")
    page.screencast.hide_overlays()
    page.screencast.show_overlays()


def test_screencast_show_and_hide_actions(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    with page.screencast.show_actions():
        pass
    page.screencast.hide_actions()
