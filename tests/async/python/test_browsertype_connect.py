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


"""Python only: tests of v2 (playwright/_impl_v2) that no upstream test covers.

The v1 tests of the same behaviors are in tests/async/legacy, marked @only_v1.
"""

from pathlib import Path
from typing import Callable

import pytest

from playwright.async_api import BrowserType, Error
from tests.conftest import RemoteServer
from tests.server import Server, TestServerRequest


async def test_should_not_allow_getting_the_path(
    browser_type: BrowserType, launch_server: Callable[[], RemoteServer], server: Server
) -> None:
    def handle_download(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "application/octet-stream")
        request.setHeader("Content-Disposition", "attachment")
        request.write(b"Hello world")
        request.finish()

    server.set_route("/download", handle_download)

    remote_server = launch_server()
    browser = await browser_type.connect(remote_server.ws_endpoint)
    page = await browser.new_page(accept_downloads=True)
    await page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    with pytest.raises(Error) as exc:
        await download.path()
    assert (
        exc.value.message
        == "Path is not available when connecting remotely. Use save_as() to save a local copy."
    )
    remote_server.kill()


async def test_prevent_getting_video_path(
    browser_type: BrowserType,
    launch_server: Callable[[], RemoteServer],
    tmp_path: Path,
    server: Server,
) -> None:
    remote_server = launch_server()
    browser = await browser_type.connect(remote_server.ws_endpoint)
    page = await browser.new_page(record_video_dir=tmp_path)
    await page.goto(server.PREFIX + "/grid.html")
    await browser.close()
    assert page.video
    with pytest.raises(Error) as exc:
        await page.video.path()
    assert (
        exc.value.message
        == "Path is not available when connecting remotely. Use save_as() to save a local copy."
    )
    remote_server.kill()
