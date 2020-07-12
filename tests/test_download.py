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
from asyncio.futures import Future
from typing import Optional
from playwright.browser import Browser
from playwright.page import Page
from playwright import Error as PlaywrightError
import pytest
import asyncio
import os


def assert_file_content(path, content):
    with open(path, "r") as fd:
        assert fd.read() == content


@pytest.fixture(autouse=True)
def after_each_hook(server):
    def handle_download(request):
        request.setHeader("Content-Type", "application/octet-stream")
        request.setHeader("Content-Disposition", "attachment")
        request.write(b"Hello world")
        request.finish()

    def handle_download_with_file_name(request):
        request.setHeader("Content-Type", "application/octet-stream")
        request.setHeader("Content-Disposition", "attachment; filename=file.txt")
        request.write(b"Hello world")
        request.finish()

    server.set_route("/download", handle_download)
    server.set_route("/downloadWithFilename", handle_download_with_file_name)
    yield


async def test_should_report_downloads_with_acceptDownloads_false(page: Page, server):
    await page.setContent(
        f'<a href="{server.PREFIX}/downloadWithFilename">download</a>'
    )
    download = (await asyncio.gather(page.waitForEvent("download"), page.click("a")))[0]
    assert download.url == f"{server.PREFIX}/downloadWithFilename"
    assert download.suggestedFilename == "file.txt"
    error: Optional[PlaywrightError] = None
    try:
        await download.path()
    except PlaywrightError as exc:
        error = exc
    assert "acceptDownloads" in await download.failure()
    assert error
    assert "acceptDownloads: true" in error.message


async def test_should_report_downloads_with_acceptDownloads_true(browser, server):
    page = await browser.newPage(acceptDownloads=True)
    await page.setContent(f'<a href="{server.PREFIX}/download">download</a>')
    download = (await asyncio.gather(page.waitForEvent("download"), page.click("a")))[0]
    path = await download.path()
    assert os.path.isfile(path)
    assert_file_content(path, "Hello world")
    await page.close()


async def test_should_report_non_navigation_downloads(browser, server):
    # Mac WebKit embedder does not download in this case, although Safari does.
    def handle_download(request):
        request.setHeader("Content-Type", "application/octet-stream")
        request.write(b"Hello world")
        request.finish()

    server.set_route("/download", handle_download)

    page = await browser.newPage(acceptDownloads=True)
    await page.goto(server.EMPTY_PAGE)
    await page.setContent(
        f'<a download="file.txt" href="{server.PREFIX}/download">download</a>'
    )
    download = (await asyncio.gather(page.waitForEvent("download"), page.click("a")))[0]
    assert download.suggestedFilename == "file.txt"
    path = await download.path()
    assert os.path.exists(path)
    assert_file_content(path, "Hello world")
    await page.close()


async def test_report_download_path_within_page_on_download_handler_for_files(
    browser: Browser, server
):
    page = await browser.newPage(acceptDownloads=True)
    on_download_path: Future[str] = asyncio.Future()

    async def on_download(download):
        on_download_path.set_result(await download.path())

    page.once(
        "download", lambda res: asyncio.ensure_future(on_download(res)),
    )
    await page.setContent(f'<a href="{server.PREFIX}/download">download</a>')
    await page.click("a")
    path = await on_download_path
    assert_file_content(path, "Hello world")
    await page.close()


async def test_download_report_download_path_within_page_on_handle_for_blobs(
    browser, server
):
    page = await browser.newPage(acceptDownloads=True)
    on_download_path = asyncio.Future()

    async def on_download(download):
        on_download_path.set_result(await download.path())

    page.once(
        "download", lambda res: asyncio.ensure_future(on_download(res)),
    )

    await page.goto(server.PREFIX + "/download-blob.html")
    await page.click("a")
    path = await on_download_path
    assert_file_content(path, "Hello world")
    await page.close()


@pytest.mark.only_browser("chromium")
async def test_should_report_alt_click_downloads(browser, server):
    # Firefox does not download on alt-click by default.
    # Our WebKit embedder does not download on alt-click, although Safari does.
    def handle_download(request):
        request.setHeader("Content-Type", "application/octet-stream")
        request.write(b"Hello world")
        request.finish()

    server.set_route("/download", handle_download)

    page = await browser.newPage(acceptDownloads=True)
    await page.goto(server.EMPTY_PAGE)
    await page.setContent(f'<a href="{server.PREFIX}/download">download</a>')
    download = (
        await asyncio.gather(
            page.waitForEvent("download"), page.click("a", modifiers=["Alt"])
        )
    )[0]
    path = await download.path()
    assert os.path.exists(path)
    assert_file_content(path, "Hello world")
    await page.close()


async def test_should_report_new_window_downloads(browser, server):
    # TODO: - the test fails in headful Chromium as the popup page gets closed along
    # with the session before download completed event arrives.
    # - WebKit doesn't close the popup page
    page = await browser.newPage(acceptDownloads=True)
    await page.setContent(
        f'<a target=_blank href="{server.PREFIX}/download">download</a>'
    )
    download = (await asyncio.gather(page.waitForEvent("download"), page.click("a")))[0]
    path = await download.path()
    assert os.path.exists(path)
    await page.close()


async def test_should_delete_file(browser, server):
    page = await browser.newPage(acceptDownloads=True)
    await page.setContent(f'<a href="{server.PREFIX}/download">download</a>')
    download = (await asyncio.gather(page.waitForEvent("download"), page.click("a")))[0]
    path = await download.path()
    assert os.path.exists(path)
    await download.delete()
    assert os.path.exists(path) is False
    await page.close()


async def test_should_delete_downloads_on_context_destruction(browser, server):
    page = await browser.newPage(acceptDownloads=True)
    await page.setContent(f'<a href="{server.PREFIX}/download">download</a>')
    download1 = (await asyncio.gather(page.waitForEvent("download"), page.click("a")))[
        0
    ]
    download2 = (await asyncio.gather(page.waitForEvent("download"), page.click("a")))[
        0
    ]
    path1 = await download1.path()
    path2 = await download2.path()
    assert os.path.exists(path1)
    assert os.path.exists(path2)
    await page.context.close()
    assert os.path.exists(path1) is False
    assert os.path.exists(path2) is False


async def test_should_delete_downloads_on_browser_gone(browser_factory, server):
    browser = await browser_factory()
    page = await browser.newPage(acceptDownloads=True)
    await page.setContent(f'<a href="{server.PREFIX}/download">download</a>')
    download1 = (await asyncio.gather(page.waitForEvent("download"), page.click("a")))[
        0
    ]
    download2 = (await asyncio.gather(page.waitForEvent("download"), page.click("a")))[
        0
    ]
    path1 = await download1.path()
    path2 = await download2.path()
    assert os.path.exists(path1)
    assert os.path.exists(path2)
    await browser.close()
    assert os.path.exists(path1) is False
    assert os.path.exists(path2) is False
    assert os.path.exists(os.path.join(path1, "..")) is False
