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

import os
from pathlib import Path
from typing import Dict

import pytest

from playwright.async_api import Browser, BrowserType, Error
from tests.server import Server


async def test_should_expose_video_path(
    browser: Browser, tmp_path: Path, server: Server
) -> None:
    page = await browser.new_page(record_video_dir=tmp_path)
    await page.goto(server.PREFIX + "/grid.html")
    assert page.video
    path = await page.video.path()
    assert isinstance(path, Path)
    assert str(tmp_path) in str(path)
    await page.context.close()


async def test_short_video_should_throw(
    browser: Browser, tmp_path: Path, server: Server
) -> None:
    page = await browser.new_page(record_video_dir=tmp_path)
    await page.goto(server.PREFIX + "/grid.html")
    assert page.video
    path = await page.video.path()
    assert str(tmp_path) in str(path)
    await page.wait_for_timeout(1000)
    await page.context.close()
    assert os.path.exists(path)


async def test_short_video_should_throw_persistent_context(
    browser_type: BrowserType, tmp_path: Path, launch_arguments: Dict, server: Server
) -> None:
    context = await browser_type.launch_persistent_context(
        str(tmp_path),
        **launch_arguments,
        viewport={"width": 320, "height": 240},
        record_video_dir=str(tmp_path) + "1",
    )
    page = context.pages[0]
    await page.goto(server.PREFIX + "/grid.html")
    await page.wait_for_timeout(1000)
    await context.close()

    assert page.video
    path = await page.video.path()
    assert str(tmp_path) in str(path)


async def test_should_not_error_if_page_not_closed_before_save_as(
    browser: Browser, tmp_path: Path, server: Server
) -> None:
    page = await browser.new_page(record_video_dir=tmp_path)
    await page.goto(server.PREFIX + "/grid.html")
    await page.wait_for_timeout(1000)  # make sure video has some data
    out_path = tmp_path / "some-video.webm"
    assert page.video
    saved = page.video.save_as(out_path)
    await page.close()
    await saved
    await page.context.close()
    assert os.path.exists(out_path)


async def test_should_be_None_if_not_recording(
    browser: Browser, tmp_path: Path, server: Server
) -> None:
    page = await browser.new_page()
    assert page.video is None
    await page.close()


async def test_should_record_video_with_fps(
    browser: Browser, tmp_path: Path, server: Server
) -> None:
    context = await browser.new_context(record_video_dir=tmp_path, record_video_fps=60)
    page = await context.new_page()
    await page.goto(server.PREFIX + "/grid.html")
    await page.wait_for_timeout(500)
    await context.close()
    assert page.video
    assert os.path.exists(await page.video.path())


async def test_should_throw_on_invalid_record_video_fps(
    browser: Browser, browser_type: BrowserType, tmp_path: Path, launch_arguments: Dict
) -> None:
    with pytest.raises(
        Error, match='"recordVideo.fps" must be a positive number, got 0'
    ):
        await browser.new_context(record_video_dir=tmp_path, record_video_fps=0)
    with pytest.raises(
        Error, match='"recordVideo.fps" must be a positive number, got 0'
    ):
        await browser_type.launch_persistent_context(
            tmp_path / "user-data-dir",
            **launch_arguments,
            record_video_dir=tmp_path,
            record_video_fps=0,
        )
