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
import asyncio
import os
from asyncio.futures import Future
from pathlib import Path
from typing import Callable, Generator

import pytest

from playwright.async_api import Browser, Download, Error, Page
from tests.server import Server, TestServerRequest
from tests.utils import TARGET_CLOSED_ERROR_MESSAGE


def assert_file_content(path: Path, content: str) -> None:
    with open(path, "r") as fd:
        assert fd.read() == content


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


async def test_should_report_downloads_with_accept_downloads_true(
    browser: Browser, server: Server
) -> None:
    page = await browser.new_page(accept_downloads=True)
    await page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    path = await download.path()
    assert os.path.isfile(path)
    assert_file_content(path, "Hello world")
    await page.close()


async def test_should_save_to_user_specified_path(
    tmp_path: Path, browser: Browser, server: Server
) -> None:
    page = await browser.new_page(accept_downloads=True)
    await page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    user_path = tmp_path / "download.txt"
    await download.save_as(user_path)
    assert user_path.exists()
    assert user_path.read_text("utf-8") == "Hello world"
    await page.close()


async def test_should_save_to_user_specified_path_without_updating_original_path(
    tmp_path: Path, browser: Browser, server: Server
) -> None:
    page = await browser.new_page(accept_downloads=True)
    await page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    user_path = tmp_path / "download.txt"
    await download.save_as(user_path)
    assert user_path.exists()
    assert user_path.read_text("utf-8") == "Hello world"

    originalPath = Path(await download.path())
    assert originalPath.exists()
    assert originalPath.read_text("utf-8") == "Hello world"
    await page.close()


async def test_should_save_to_two_different_paths_with_multiple_save_as_calls(
    tmp_path: Path, browser: Browser, server: Server
) -> None:
    page = await browser.new_page(accept_downloads=True)
    await page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    user_path = tmp_path / "download.txt"
    await download.save_as(user_path)
    assert user_path.exists()
    assert user_path.read_text("utf-8") == "Hello world"

    anotheruser_path = tmp_path / "download (2).txt"
    await download.save_as(anotheruser_path)
    assert anotheruser_path.exists()
    assert anotheruser_path.read_text("utf-8") == "Hello world"
    await page.close()


async def test_should_save_to_overwritten_filepath(
    tmp_path: Path, browser: Browser, server: Server
) -> None:
    page = await browser.new_page(accept_downloads=True)
    await page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    user_path = tmp_path / "download.txt"
    await download.save_as(user_path)
    assert len(list(tmp_path.glob("*.*"))) == 1
    await download.save_as(user_path)
    assert len(list(tmp_path.glob("*.*"))) == 1
    assert user_path.exists()
    assert user_path.read_text("utf-8") == "Hello world"
    await page.close()


async def test_should_create_subdirectories_when_saving_to_non_existent_user_specified_path(
    tmp_path: Path, browser: Browser, server: Server
) -> None:
    page = await browser.new_page(accept_downloads=True)
    await page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    nested_path = tmp_path / "these" / "are" / "directories" / "download.txt"
    await download.save_as(nested_path)
    assert nested_path.exists()
    assert nested_path.read_text("utf-8") == "Hello world"
    await page.close()


async def test_should_error_when_saving_with_downloads_disabled(
    tmp_path: Path, browser: Browser, server: Server
) -> None:
    page = await browser.new_page(accept_downloads=False)
    await page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    user_path = tmp_path / "download.txt"
    with pytest.raises(Error) as exc:
        await download.save_as(user_path)
    assert (
        "Pass 'accept_downloads=True' when you are creating your browser context"
        in exc.value.message
    )
    assert (
        "Pass 'accept_downloads=True' when you are creating your browser context."
        == await download.failure()
    )
    await page.close()


async def test_should_error_when_saving_after_deletion(
    tmp_path: Path, browser: Browser, server: Server
) -> None:
    page = await browser.new_page(accept_downloads=True)
    await page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    user_path = tmp_path / "download.txt"
    await download.delete()
    with pytest.raises(Error) as exc:
        await download.save_as(user_path)
    assert TARGET_CLOSED_ERROR_MESSAGE in exc.value.message
    await page.close()


async def test_should_report_non_navigation_downloads(
    browser: Browser, server: Server
) -> None:
    # Mac WebKit embedder does not download in this case, although Safari does.
    def handle_download(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "application/octet-stream")
        request.write(b"Hello world")
        request.finish()

    server.set_route("/download", handle_download)

    page = await browser.new_page(accept_downloads=True)
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        f'<a download="file.txt" href="{server.PREFIX}/download">download</a>'
    )
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    assert download.suggested_filename == "file.txt"
    path = await download.path()
    assert os.path.exists(path)
    assert_file_content(path, "Hello world")
    await page.close()


async def test_report_download_path_within_page_on_download_handler_for_files(
    browser: Browser, server: Server
) -> None:
    page = await browser.new_page(accept_downloads=True)
    on_download_path: Future[Path] = asyncio.Future()

    async def on_download(download: Download) -> None:
        on_download_path.set_result(await download.path())

    page.once(
        "download",
        lambda res: asyncio.create_task(on_download(res)),
    )
    await page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    await page.click("a")
    path = await on_download_path
    assert_file_content(path, "Hello world")
    await page.close()


async def test_download_report_download_path_within_page_on_handle_for_blobs(
    browser: Browser, server: Server
) -> None:
    page = await browser.new_page(accept_downloads=True)
    on_download_path: "asyncio.Future[Path]" = asyncio.Future()

    async def on_download(download: Download) -> None:
        on_download_path.set_result(await download.path())

    page.once(
        "download",
        lambda res: asyncio.create_task(on_download(res)),
    )

    await page.goto(server.PREFIX + "/download-blob.html")
    await page.click("a")
    path = await on_download_path
    assert_file_content(path, "Hello world")
    await page.close()


@pytest.mark.only_browser("chromium")
async def test_should_report_alt_click_downloads(
    browser: Browser, server: Server
) -> None:
    # Firefox does not download on alt-click by default.
    # Our WebKit embedder does not download on alt-click, although Safari does.
    def handle_download(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "application/octet-stream")
        request.write(b"Hello world")
        request.finish()

    server.set_route("/download", handle_download)

    page = await browser.new_page(accept_downloads=True)
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    async with page.expect_download() as download_info:
        await page.click("a", modifiers=["Alt"])
    download = await download_info.value
    path = await download.path()
    assert os.path.exists(path)
    assert_file_content(path, "Hello world")
    await page.close()


async def test_should_report_new_window_downloads(
    browser: Browser, server: Server
) -> None:
    page = await browser.new_page(accept_downloads=True)
    await page.set_content(
        f'<a target=_blank href="{server.PREFIX}/download">download</a>'
    )
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    path = await download.path()
    assert os.path.exists(path)
    await page.close()


async def test_should_delete_file(browser: Browser, server: Server) -> None:
    page = await browser.new_page(accept_downloads=True)
    await page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    path = await download.path()
    assert os.path.exists(path)
    await download.delete()
    assert os.path.exists(path) is False
    await page.close()


async def test_should_delete_downloads_on_context_destruction(
    browser: Browser, server: Server
) -> None:
    page = await browser.new_page(accept_downloads=True)
    await page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    async with page.expect_download() as download_info:
        await page.click("a")
    download1 = await download_info.value
    async with page.expect_download() as download_info:
        await page.click("a")
    download2 = await download_info.value
    path1 = await download1.path()
    path2 = await download2.path()
    assert os.path.exists(path1)
    assert os.path.exists(path2)
    await page.context.close()
    assert os.path.exists(path1) is False
    assert os.path.exists(path2) is False


async def test_should_delete_downloads_on_browser_gone(
    browser_factory: "Callable[..., asyncio.Future[Browser]]", server: Server
) -> None:
    browser = await browser_factory()
    page = await browser.new_page(accept_downloads=True)
    await page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    async with page.expect_download() as download_info:
        await page.click("a")
    download1 = await download_info.value
    async with page.expect_download() as download_info:
        await page.click("a")
    download2 = await download_info.value
    path1 = await download1.path()
    path2 = await download2.path()
    assert os.path.exists(path1)
    assert os.path.exists(path2)
    await browser.close()
    assert os.path.exists(path1) is False
    assert os.path.exists(path2) is False
    assert os.path.exists(os.path.join(path1, "..")) is False


async def test_download_cancel_should_work(browser: Browser, server: Server) -> None:
    def handle_download(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "application/octet-stream")
        request.setHeader("Content-Disposition", "attachment")
        # Chromium requires a large enough payload to trigger the download event soon enough
        request.write(b"a" * 4096)
        request.write(b"foo")

    server.set_route("/downloadWithDelay", handle_download)
    page = await browser.new_page(accept_downloads=True)
    await page.set_content(f'<a href="{server.PREFIX}/downloadWithDelay">download</a>')
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    await download.cancel()
    assert await download.failure() == "canceled"
    await page.close()
