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

from typing import Generator

import pytest

from playwright.async_api import Page
from tests.server import Server, TestServerRequest


@pytest.fixture(autouse=True)
def after_each_hook(server: Server) -> Generator[None, None, None]:
    def handle_download(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "application/octet-stream")
        request.setHeader("Content-Disposition", "attachment")
        request.write(b"Hello world")
        request.finish()

    def handle_download_with_file_name(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "application/octet-stream")
        request.setHeader("Content-Disposition", "attachment; filename=file.txt")
        request.write(b"Hello world")
        request.finish()

    server.set_route("/download", handle_download)
    server.set_route("/downloadWithFilename", handle_download_with_file_name)
    yield


async def test_should_report_downloads_with_accept_downloads_false(
    page: Page, server: Server
) -> None:
    await page.set_content(
        f'<a href="{server.PREFIX}/downloadWithFilename">download</a>'
    )
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    assert download.page is page
    assert download.url == f"{server.PREFIX}/downloadWithFilename"
    assert download.suggested_filename == "file.txt"
    assert (
        repr(download)
        == f"<Download url={download.url!r} suggested_filename={download.suggested_filename!r}>"
    )
    assert await download.path()
    assert await download.failure() is None
