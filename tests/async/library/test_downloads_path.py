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

"""Port of tests/library/downloads-path.spec.ts."""

import os
from pathlib import Path
from typing import Awaitable, Callable, Dict, Tuple

import pytest

from playwright.async_api import BrowserContext, BrowserType, Error, Page
from tests.server import Server, TestServerRequest

LaunchPersistent = Callable[..., Awaitable[Tuple[BrowserContext, Page]]]


@pytest.fixture(autouse=True)
def before_each(server: Server) -> None:
    def handler(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "application/octet-stream")
        request.setHeader("Content-Disposition", "attachment; filename=file.txt")
        request.write(b"Hello world")
        request.finish()

    server.set_route("/download", handler)


async def test_DO_039_downloads_path_should_keep_downloads_path_folder(
    browser_type: BrowserType, launch_arguments: Dict, server: Server, tmp_path: Path
) -> None:
    downloads_browser = await browser_type.launch(
        **launch_arguments, downloads_path=tmp_path
    )
    page = await downloads_browser.new_page()
    await page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    assert download.url == f"{server.PREFIX}/download"
    assert download.suggested_filename == "file.txt"
    try:
        await download.path()
    except Error:
        pass
    await page.close()
    await downloads_browser.close()
    assert tmp_path.exists()


async def test_DO_040_downloads_path_should_delete_downloads_when_context_closes(
    browser_type: BrowserType, launch_arguments: Dict, server: Server, tmp_path: Path
) -> None:
    downloads_browser = await browser_type.launch(
        **launch_arguments, downloads_path=tmp_path
    )
    page = await downloads_browser.new_page()
    await page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    path = await download.path()
    assert path.exists()
    await page.close()
    assert not path.exists()
    await downloads_browser.close()


async def test_DO_041_downloads_path_should_report_downloads_in_downloads_path_folder(
    browser_type: BrowserType, launch_arguments: Dict, server: Server, tmp_path: Path
) -> None:
    downloads_browser = await browser_type.launch(
        **launch_arguments, downloads_path=tmp_path
    )
    page = await downloads_browser.new_page()
    await page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    path = await download.path()
    assert str(path).startswith(str(tmp_path))
    await page.close()
    await downloads_browser.close()


async def test_DO_042_downloads_path_should_report_downloads_in_downloads_path_folder_with_a_relative_path(
    browser_type: BrowserType, launch_arguments: Dict, server: Server, tmp_path: Path
) -> None:
    downloads_browser = await browser_type.launch(
        **launch_arguments, downloads_path=os.path.relpath(tmp_path, os.getcwd())
    )
    page = await downloads_browser.new_page()
    await page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    download_path = await download.path()
    assert str(download_path).startswith(str(tmp_path))
    await page.close()
    await downloads_browser.close()


async def test_DO_043_downloads_path_should_accept_downloads_in_persistent_context(
    launch_persistent: LaunchPersistent, server: Server, tmp_path: Path
) -> None:
    context, page = await launch_persistent(downloads_path=tmp_path)
    await page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    assert download.url == f"{server.PREFIX}/download"
    assert download.suggested_filename == "file.txt"
    path = await download.path()
    assert str(path).startswith(str(tmp_path))
    await context.close()


async def test_DO_044_downloads_path_should_delete_downloads_when_persistent_context_closes(
    launch_persistent: LaunchPersistent, server: Server, tmp_path: Path
) -> None:
    context, page = await launch_persistent(downloads_path=tmp_path)
    await page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    path = await download.path()
    assert path.exists()
    await context.close()
    assert not path.exists()
