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

from playwright.sync_api import Browser, BrowserType
from tests.server import Server


def test_should_expose_video_path(
    browser: Browser, tmpdir: Path, server: Server
) -> None:
    page = browser.new_page(
        record_video_dir=tmpdir, record_video_size={"width": 100, "height": 200}
    )
    page.goto(server.PREFIX + "/grid.html")
    video = page.video
    assert video
    path = video.path()
    assert repr(page.video) == f"<Video page={page}>"
    assert str(tmpdir) in str(path)
    page.wait_for_timeout(1000)
    page.context.close()


def test_video_should_exist(browser: Browser, tmpdir: Path, server: Server) -> None:
    page = browser.new_page(record_video_dir=tmpdir)
    page.goto(server.PREFIX + "/grid.html")
    video = page.video
    assert video
    path = video.path()
    assert str(tmpdir) in str(path)
    page.wait_for_timeout(1000)
    page.context.close()
    assert os.path.exists(path)


def test_record_video_to_path(browser: Browser, tmpdir: Path, server: Server) -> None:
    page = browser.new_page(record_video_dir=tmpdir)
    page.goto(server.PREFIX + "/grid.html")
    video = page.video
    assert video
    path = video.path()
    assert str(tmpdir) in str(path)
    page.wait_for_timeout(1000)
    page.context.close()
    assert os.path.exists(path)


def test_record_video_to_path_persistent(
    browser_type: BrowserType, tmpdir: Path, server: Server, launch_arguments: Dict
) -> None:
    context = browser_type.launch_persistent_context(
        tmpdir, **launch_arguments, record_video_dir=tmpdir
    )
    page = context.pages[0]
    page.goto(server.PREFIX + "/grid.html")
    video = page.video
    assert video
    path = video.path()
    assert str(tmpdir) in str(path)
    page.wait_for_timeout(1000)
    context.close()
    assert os.path.exists(path)


def test_record_video_can_get_video_path_immediately(
    browser_type: BrowserType, tmpdir: Path, launch_arguments: Dict
) -> None:
    context = browser_type.launch_persistent_context(
        tmpdir, **launch_arguments, record_video_dir=tmpdir
    )
    page = context.pages[0]
    video = page.video
    assert video
    path = video.path()
    assert str(tmpdir) in str(path)
    page.wait_for_timeout(1000)
    context.close()
    assert os.path.exists(path)
