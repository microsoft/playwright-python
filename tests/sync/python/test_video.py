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

import pytest

from playwright.sync_api import Browser, Error
from tests.server import Server


def test_should_expose_video_path(
    browser: Browser, tmp_path: Path, server: Server
) -> None:
    page = browser.new_page(
        record_video_dir=tmp_path, record_video_size={"width": 100, "height": 200}
    )
    page.goto(server.PREFIX + "/grid.html")
    video = page.video
    assert video
    path = video.path()
    assert isinstance(path, Path)
    assert repr(page.video) == f"<Video page={page}>"
    assert str(tmp_path) in str(path)
    page.wait_for_timeout(1000)
    page.context.close()


def test_should_error_if_page_not_closed_before_save_as(
    browser: Browser, tmp_path: Path, server: Server
) -> None:
    page = browser.new_page(record_video_dir=tmp_path)
    page.goto(server.PREFIX + "/grid.html")
    page.wait_for_timeout(1000)  # Give it some time to record.
    out_path = tmp_path / "some-video.webm"
    with pytest.raises(Error) as err:
        video = page.video
        assert video
        video.save_as(out_path)
    assert video
    assert "Page is not yet closed. Close the page prior to calling save_as" in str(err)
    assert not os.path.exists(out_path)
    page.close()

    video.save_as(out_path)
    assert os.path.exists(out_path)
