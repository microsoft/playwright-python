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

"""Python only: tests of behaviors that no upstream test covers."""

import os
from pathlib import Path
from typing import Dict

import pytest

from playwright.async_api import Browser, BrowserType, Error
from tests.server import Server


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
