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

"""Port of tests/library/download.spec.ts."""

import asyncio
import os
import re
from pathlib import Path
from typing import Callable, Dict, Optional

import pytest

from playwright.async_api import Browser, BrowserType, Download, Error, Page, Route
from tests.server import Server, TestServerRequest
from tests.utils import TARGET_CLOSED_ERROR_MESSAGE


def _download_route(
    headers: Dict[str, str], finish: bool = True
) -> Callable[[TestServerRequest], None]:
    def handler(request: TestServerRequest) -> None:
        for name, value in headers.items():
            request.setHeader(name, value)
        request.write(b"Hello world")
        if finish:
            request.finish()

    return handler


@pytest.fixture(autouse=True)
def download_routes(server: Server) -> None:
    """The beforeEach of the 'download event' describe.

    The tests outside the describe set their own routes or do not use these.
    """
    server.set_route(
        "/download",
        _download_route(
            {
                "Content-Type": "application/octet-stream",
                "Content-Disposition": "attachment",
            }
        ),
    )
    server.set_route(
        "/downloadWithFilename",
        _download_route(
            {
                "Content-Type": "application/octet-stream",
                "Content-Disposition": "attachment; filename=file.txt",
            }
        ),
    )

    def download_with_delay(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "application/octet-stream")
        request.setHeader("Content-Disposition", "attachment; filename=file.txt")
        # Chromium requires a large enough payload to trigger the download event soon enough
        request.write(b"a" * 4096)
        request.write(b"foo")

    server.set_route("/downloadWithDelay", download_with_delay)
    server.set_route(
        "/downloadWithCOOP",
        _download_route(
            {
                "Content-Type": "application/octet-stream",
                "Content-Disposition": "attachment",
                "Cross-Origin-Opener-Policy": "same-origin",
            }
        ),
    )


def _set_download_stall_route(server: Server) -> None:
    def handler(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "application/octet-stream")
        request.setHeader("Content-Disposition", "attachment; filename=file.txt")
        request.setResponseCode(200)
        request.write(b"Hello world")

    server.set_route("/downloadStall", handler)


async def test_DO_001_download_event_should_report_download_when_navigation_turns_into_download_smoke(
    browser: Browser, server: Server, browser_name: str, browser_major_version: int
) -> None:
    if browser_name == "chromium" and browser_major_version < 140:
        pytest.skip(
            "old chromium throws net::ERR_ABORTED, depends on https://chromium-review.googlesource.com/c/chromium/src/+/6696011"
        )
    page = await browser.new_page()
    async with page.expect_download() as download_info:
        with pytest.raises(Error) as exc_info:
            await page.goto(server.PREFIX + "/download")
    download = await download_info.value
    assert download.page is page
    assert download.url == f"{server.PREFIX}/download"
    path = await download.path()
    assert path.exists()
    assert path.read_text() == "Hello world"

    assert "Download is starting" in exc_info.value.message

    if browser_name != "firefox":
        assert page.url == "about:blank"
    await page.close()


async def test_DO_002_download_event_should_work_with_cross_origin_opener_policy(
    browser: Browser, server: Server, browser_name: str, browser_major_version: int
) -> None:
    if browser_name == "chromium" and browser_major_version < 140:
        pytest.skip(
            "old chromium throws net::ERR_ABORTED, depends on https://chromium-review.googlesource.com/c/chromium/src/+/6696011"
        )
    page = await browser.new_page()
    async with page.expect_download() as download_info:
        with pytest.raises(Error) as exc_info:
            await page.goto(server.PREFIX + "/downloadWithCOOP")
    download = await download_info.value
    assert download.page is page
    assert download.url == f"{server.PREFIX}/downloadWithCOOP"
    path = await download.path()
    assert path.exists()
    assert path.read_text() == "Hello world"
    assert "Download is starting" in exc_info.value.message
    if browser_name != "firefox":
        assert page.url == "about:blank"
    await page.close()


async def test_DO_003_download_event_should_report_downloads_with_accept_downloads_false(
    browser: Browser, server: Server
) -> None:
    page = await browser.new_page(accept_downloads=False)
    await page.set_content(
        f'<a href="{server.PREFIX}/downloadWithFilename">download</a>'
    )
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    assert download.page is page
    assert download.url == f"{server.PREFIX}/downloadWithFilename"
    assert download.suggested_filename == "file.txt"
    with pytest.raises(Error) as exc_info:
        await download.path()
    assert "accept_downloads" in (await download.failure() or "")
    assert "accept_downloads=True" in exc_info.value.message
    await page.close()


async def test_DO_004_download_event_should_report_downloads_with_accept_downloads_true(
    browser: Browser, server: Server
) -> None:
    page = await browser.new_page()
    await page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    path = await download.path()
    assert path.exists()
    assert path.read_text() == "Hello world"
    await page.close()


async def test_DO_005_download_event_should_report_proper_download_url_when_download_is_from_download_attribute(
    browser: Browser, server: Server, browser_name: str
) -> None:
    page = await browser.new_page()
    await page.goto(server.PREFIX + "/empty.html")
    await page.set_content(
        f'<a href="{server.PREFIX}/chromium-linux.zip" download="foo.zip">download</a>'
    )
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    assert download.url == f"{server.PREFIX}/chromium-linux.zip"
    await page.close()


async def test_DO_006_download_event_should_report_downloads_for_download_attribute(
    browser: Browser, server: Server
) -> None:
    page = await browser.new_page()
    await page.goto(server.PREFIX + "/empty.html")
    await page.set_content(
        f'<a href="{server.PREFIX}/chromium-linux.zip" download="foo.zip">download</a>'
    )
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    assert download.suggested_filename == "foo.zip"
    path = await download.path()
    assert path.exists()
    await page.close()


async def test_DO_007_download_event_should_save_to_user_specified_path_without_updating_original_path(
    browser: Browser, server: Server, tmp_path: Path
) -> None:
    page = await browser.new_page()
    await page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    user_path = tmp_path / "download.txt"
    await download.save_as(user_path)
    assert user_path.exists()
    assert user_path.read_text() == "Hello world"

    original_path = await download.path()
    assert original_path.exists()
    assert original_path.read_text() == "Hello world"
    await page.close()


async def test_DO_008_download_event_should_save_to_two_different_paths_with_multiple_save_as_calls(
    browser: Browser, server: Server, tmp_path: Path
) -> None:
    page = await browser.new_page()
    await page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    user_path = tmp_path / "download.txt"
    await download.save_as(user_path)
    assert user_path.exists()
    assert user_path.read_text() == "Hello world"

    another_user_path = tmp_path / "download (2).txt"
    await download.save_as(another_user_path)
    assert another_user_path.exists()
    assert another_user_path.read_text() == "Hello world"
    await page.close()


async def test_DO_009_download_event_should_save_to_overwritten_filepath(
    browser: Browser, server: Server, tmp_path: Path
) -> None:
    page = await browser.new_page()
    await page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    directory = tmp_path / "downloads"
    user_path = directory / "download.txt"
    await download.save_as(user_path)
    assert len(os.listdir(directory)) == 1
    await download.save_as(user_path)
    assert len(os.listdir(directory)) == 1
    assert user_path.exists()
    assert user_path.read_text() == "Hello world"
    await page.close()


async def test_DO_010_download_event_should_create_subdirectories_when_saving_to_non_existent_user_specified_path(
    browser: Browser, server: Server, tmp_path: Path
) -> None:
    page = await browser.new_page()
    await page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    nested_path = tmp_path / "these" / "are" / "directories" / "download.txt"
    await download.save_as(nested_path)
    assert nested_path.exists()
    assert nested_path.read_text() == "Hello world"
    await page.close()


async def test_DO_011_download_event_should_error_when_saving_with_downloads_disabled(
    browser: Browser, server: Server, tmp_path: Path
) -> None:
    page = await browser.new_page(accept_downloads=False)
    await page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    user_path = tmp_path / "download.txt"
    with pytest.raises(Error) as exc_info:
        await download.save_as(user_path)
    assert (
        "Pass 'accept_downloads=True' when you are creating your browser context"
        in exc_info.value.message
    )
    await page.close()


async def test_DO_012_download_event_should_error_when_saving_after_deletion(
    browser: Browser, server: Server, tmp_path: Path
) -> None:
    page = await browser.new_page()
    await page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    user_path = tmp_path / "download.txt"
    await download.delete()
    with pytest.raises(Error) as exc_info:
        await download.save_as(user_path)
    assert TARGET_CLOSED_ERROR_MESSAGE in exc_info.value.message
    await page.close()


async def test_DO_013_download_event_should_report_non_navigation_downloads(
    browser: Browser, server: Server
) -> None:
    # Mac WebKit embedder does not download in this case, although Safari does.
    server.set_route(
        "/download", _download_route({"Content-Type": "application/octet-stream"})
    )

    page = await browser.new_page()
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        f'<a download="file.txt" href="{server.PREFIX}/download">download</a>'
    )
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    assert download.suggested_filename == "file.txt"
    path = await download.path()
    assert path.exists()
    assert path.read_text() == "Hello world"
    await page.close()


async def test_DO_014_download_event_should_report_download_path_within_page_on_download_handler_for_files(
    browser: Browser, server: Server
) -> None:
    page = await browser.new_page()
    on_download_path: "asyncio.Future[Path]" = asyncio.Future()

    async def handle_download(download: Download) -> None:
        on_download_path.set_result(await download.path())

    page.on("download", handle_download)
    await page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    await page.click("a")
    path = await on_download_path
    assert path.read_text() == "Hello world"
    await page.close()


async def test_DO_015_download_event_should_report_download_path_within_page_on_download_handler_for_blobs(
    browser: Browser, server: Server
) -> None:
    page = await browser.new_page()
    on_download_path: "asyncio.Future[Path]" = asyncio.Future()

    async def handle_download(download: Download) -> None:
        on_download_path.set_result(await download.path())

    page.on("download", handle_download)
    await page.goto(server.PREFIX + "/download-blob.html")
    await page.click("a")
    path = await on_download_path
    assert path.read_text() == "Hello world"
    await page.close()


async def test_DO_016_download_event_should_report_alt_click_downloads(
    browser: Browser, server: Server, browser_name: str
) -> None:
    if browser_name == "firefox":
        pytest.skip("Firefox does not download on alt-click.")

    server.set_route(
        "/download", _download_route({"Content-Type": "application/octet-stream"})
    )

    page = await browser.new_page()
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    async with page.expect_download() as download_info:
        await page.click("a", modifiers=["Alt"])
    download = await download_info.value
    path = await download.path()
    assert path.exists()
    assert path.read_text() == "Hello world"
    await page.close()


async def test_DO_017_download_event_should_report_new_window_downloads(
    browser: Browser, server: Server
) -> None:
    page = await browser.new_page()
    await page.set_content(
        f'<a target=_blank href="{server.PREFIX}/download">download</a>'
    )
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    path = await download.path()
    assert path.exists()
    await page.close()


async def test_DO_018_download_event_should_delete_file(
    browser: Browser, server: Server
) -> None:
    page = await browser.new_page()
    await page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    path = await download.path()
    assert path.exists()
    await download.delete()
    assert not path.exists()
    await page.close()


async def test_DO_020_download_event_should_delete_downloads_on_context_destruction(
    browser: Browser, server: Server
) -> None:
    page = await browser.new_page()
    await page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    async with page.expect_download() as download_info:
        await page.click("a")
    download1 = await download_info.value
    async with page.expect_download() as download_info:
        await page.click("a")
    download2 = await download_info.value
    path1 = await download1.path()
    path2 = await download2.path()
    assert path1.exists()
    assert path2.exists()
    await page.context.close()
    assert not path1.exists()
    assert not path2.exists()


async def test_DO_021_download_event_should_delete_downloads_on_browser_gone(
    server: Server, browser_type: BrowserType, launch_arguments: Dict
) -> None:
    browser = await browser_type.launch(**launch_arguments)
    page = await browser.new_page()
    await page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    async with page.expect_download() as download_info:
        await page.click("a")
    download1 = await download_info.value
    async with page.expect_download() as download_info:
        await page.click("a")
    download2 = await download_info.value
    path1 = await download1.path()
    path2 = await download2.path()
    assert path1.exists()
    assert path2.exists()
    await browser.close()
    assert not path1.exists()
    assert not path2.exists()
    assert not (path1 / "..").exists()


async def test_DO_022_download_event_should_save_downloads_to_artifacts_dir(
    server: Server,
    browser_type: BrowserType,
    launch_arguments: Dict,
    is_frozen_webkit: bool,
    tmp_path: Path,
) -> None:
    if is_frozen_webkit:
        pytest.skip("needs recent webkit")
    artifacts_dir = tmp_path / "artifacts"
    browser = await browser_type.launch(**launch_arguments, artifacts_dir=artifacts_dir)
    page = await browser.new_page()
    await page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    download_path = await download.path()
    assert str(download_path).startswith(str(artifacts_dir))
    assert download_path.exists()
    await browser.close()
    # User-provided artifactsDir should not be cleaned up.
    assert artifacts_dir.exists()


async def test_DO_023_download_event_should_close_the_context_without_awaiting_the_failed_download(
    browser: Browser,
    server: Server,
    https_server: Server,
    browser_name: str,
    headless: bool,
    tmp_path: Path,
) -> None:
    if browser_name != "chromium":
        pytest.skip("Only Chromium downloads on alt-click")

    page = await browser.new_page()
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        f'<a href="{https_server.PREFIX}/downloadWithFilename" download="file.txt">click me</a>'
    )
    async with page.expect_download() as download_info:
        # Use alt-click to force the download. Otherwise browsers might try to navigate first,
        # probably because of http -> https link.
        await page.click("a", modifiers=["Alt"])
    download = await download_info.value
    download_error, save_error, _ = await asyncio.gather(
        download.path(),
        download.save_as(tmp_path / "download.txt"),
        page.context.close(),
        return_exceptions=True,
    )
    assert isinstance(download_error, Error)
    assert download_error.message == "Download.path: canceled"
    assert isinstance(save_error, Error)
    assert save_error.message in [
        "Download.save_as: File not found on disk. Check download.failure() for details.",
        "Download.save_as: canceled",
    ]


async def test_DO_024_download_event_should_close_the_context_without_awaiting_the_download(
    browser: Browser,
    server: Server,
    browser_name: str,
    platform: str,
    browser_channel: Optional[str],
    tmp_path: Path,
) -> None:
    if browser_name == "webkit" and (
        platform == "linux" or browser_channel == "webkit-wsl"
    ):
        pytest.skip(
            "WebKit on linux does not convert to the download immediately upon receiving headers"
        )

    _set_download_stall_route(server)

    page = await browser.new_page()
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        f'<a href="{server.PREFIX}/downloadStall" download="file.txt">click me</a>'
    )
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    download_error, save_error, _ = await asyncio.gather(
        download.path(),
        download.save_as(tmp_path / "download.txt"),
        page.context.close(),
        return_exceptions=True,
    )
    # The exact error message is racy, because sometimes browser is fast enough
    # to cancel the download.
    assert isinstance(download_error, Error)
    assert download_error.message in [
        "Download.path: canceled",
        "Download.path: " + TARGET_CLOSED_ERROR_MESSAGE,
    ]
    assert isinstance(save_error, Error)
    assert save_error.message in [
        "Download.save_as: canceled",
        "Download.save_as: " + TARGET_CLOSED_ERROR_MESSAGE,
    ]


async def test_DO_025_download_event_should_throw_if_browser_dies(
    server: Server,
    browser_type: BrowserType,
    launch_arguments: Dict,
    browser_name: str,
    platform: str,
    browser_channel: Optional[str],
    tmp_path: Path,
) -> None:
    if browser_name == "webkit" and (
        platform == "linux" or browser_channel == "webkit-wsl"
    ):
        pytest.skip(
            "WebKit on linux does not convert to the download immediately upon receiving headers"
        )
    _set_download_stall_route(server)

    browser = await browser_type.launch(**launch_arguments)
    page = await browser.new_page()
    await page.set_content(f'<a href="{server.PREFIX}/downloadStall">click me</a>')
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    download_error, save_error, _ = await asyncio.gather(
        download.path(),
        download.save_as(tmp_path / "download.txt"),
        browser._impl_obj._channel.killForTests(),
        return_exceptions=True,
    )
    assert isinstance(download_error, Error)
    assert download_error.message == "Download.path: " + TARGET_CLOSED_ERROR_MESSAGE
    assert isinstance(save_error, Error)
    assert "Download.save_as: " + TARGET_CLOSED_ERROR_MESSAGE in save_error.message
    await browser.close()


async def test_DO_026_download_event_should_download_large_binary_zip(
    browser: Browser, server: Server, browser_name: str, tmp_path: Path
) -> None:
    zip_file = tmp_path / "binary.zip"
    content = os.urandom(1 << 20)
    zip_file.write_bytes(content)
    server.set_route("/binary.zip", lambda request: request.serve_file(zip_file))

    page = await browser.new_page()
    await page.goto(server.PREFIX + "/empty.html")
    await page.set_content(
        f'<a href="{server.PREFIX}/binary.zip" download="binary.zip">download</a>'
    )
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    download_path = await download.path()
    file_content = download_path.read_bytes()
    assert len(file_content) == len(content)
    assert file_content == content
    # Upstream also reads download.createReadStream(), which the Python API does not have.
    await page.close()


async def test_DO_027_download_event_should_be_able_to_cancel_pending_downloads(
    browser: Browser, server: Server, browser_name: str, browser_version: str
) -> None:
    page = await browser.new_page()
    await page.set_content(f'<a href="{server.PREFIX}/downloadWithDelay">download</a>')
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    await download.cancel()
    failure = await download.failure()
    assert failure == "canceled"
    await page.close()


async def test_DO_028_download_event_should_not_fail_explicitly_to_cancel_a_download_even_if_that_is_already_finished(
    browser: Browser, server: Server, browser_name: str, browser_version: str
) -> None:
    page = await browser.new_page()
    await page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    path = await download.path()
    assert path.exists()
    assert path.read_text() == "Hello world"
    await download.cancel()
    failure = await download.failure()
    assert failure is None
    await page.close()


async def test_DO_029_download_event_should_report_downloads_with_interception(
    browser: Browser, server: Server
) -> None:
    page = await browser.new_page()
    await page.route(re.compile(r".*"), lambda r: r.continue_())
    await page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    path = await download.path()
    assert path.exists()
    assert path.read_text() == "Hello world"
    await page.close()


async def test_DO_030_download_event_should_emit_download_event_from_nested_iframes(
    server: Server, browser: Browser, browser_name: str, tmp_path: Path
) -> None:
    page = await browser.new_page()

    def html_route(body: str) -> Callable[[TestServerRequest], None]:
        def handler(request: TestServerRequest) -> None:
            request.setHeader("Content-Type", "text/html")
            request.write(body.encode())
            request.finish()

        return handler

    server.set_route("/1", html_route(f'<iframe src="{server.PREFIX}/2"></iframe>'))
    server.set_route("/2", html_route(f'<iframe src="{server.PREFIX}/3"></iframe>'))
    server.set_route(
        "/3", html_route(f' <a href="{server.PREFIX}/download">download</a>')
    )
    await page.goto(server.PREFIX + "/1")

    frame = page.frame(url=server.PREFIX + "/3")
    assert frame
    async with page.expect_download() as download_info:
        await frame.click("text=download")
    download = await download_info.value
    user_path = tmp_path / "download.txt"
    await download.save_as(user_path)
    assert user_path.exists()
    assert user_path.read_text() == "Hello world"
    await page.close()


async def test_DO_031_should_be_able_to_download_a_pdf_file(
    browser: Browser, server: Server, assetdir: Path
) -> None:
    page = await browser.new_page()
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        """
    <a href="/empty.pdf" download>download</a>
  """
    )
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    await assert_download_to_pdf(download, assetdir / "empty.pdf")
    await page.close()


async def test_DO_032_should_be_able_to_download_a_inline_pdf_file_via_response_interception(
    browser: Browser, server: Server, assetdir: Path, browser_name: str
) -> None:
    if browser_name == "webkit":
        pytest.skip("fixme: webkit")
    page = await browser.new_page()
    await page.goto(server.EMPTY_PAGE)

    async def handle_route(route: Route) -> None:
        response = await page.context.request.fetch(route.request)
        await route.fulfill(
            response=response,
            headers={**response.headers, "Content-Disposition": "attachment"},
        )

    await page.route("**/empty.pdf", handle_route)
    await page.set_content(
        """
    <a href="/empty.pdf">open</a>
  """
    )
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    await assert_download_to_pdf(download, assetdir / "empty.pdf")
    await page.close()


async def test_DO_033_should_be_able_to_download_a_inline_pdf_file_via_navigation(
    browser: Browser,
    server: Server,
    assetdir: Path,
    browser_name: str,
    is_headless_shell: bool,
) -> None:
    if browser_name == "chromium" and not is_headless_shell:
        pytest.skip("We expect PDF Viewer to open up in headed Chromium")

    page = await browser.new_page()
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        """
    <a href="/empty.pdf">open</a>
  """
    )
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    await assert_download_to_pdf(download, assetdir / "empty.pdf")
    await page.close()


async def test_DO_034_should_save_to_user_specified_path(
    browser: Browser, server: Server, tmp_path: Path
) -> None:
    server.set_route(
        "/download",
        _download_route(
            {
                "Content-Type": "application/octet-stream",
                "Content-Disposition": "attachment",
            }
        ),
    )

    page = await browser.new_page()
    await page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    user_path = tmp_path / "download.txt"
    await download.save_as(user_path)
    assert user_path.exists()
    assert user_path.read_text() == "Hello world"
    await page.close()


async def test_DO_035_should_download_even_if_there_is_no_attachment_value(
    browser: Browser, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/19939
    server.set_route(
        "/download",
        _download_route(
            {
                "Content-Type": "application/octet-stream",
                # Do not set the "attachment" value.
                "Content-Disposition": "filename=foo.txt",
            }
        ),
    )

    page = await browser.new_page()
    await page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    async with page.expect_download():
        await page.click("a")
    await page.close()


async def test_DO_036_should_convert_navigation_to_a_resource_with_unsupported_mime_type_into_download(
    browser: Browser, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/19939
    server.set_route(
        "/download", _download_route({"Content-Type": "application/octet-stream"})
    )
    page = await browser.new_page()
    async with page.expect_download():
        try:
            await page.goto(f"{server.PREFIX}/download")
        except Error:
            pass
    await page.close()


async def test_DO_037_should_download_links_with_data_url(page: Page) -> None:
    # https://github.com/microsoft/playwright/issues/21892
    await page.set_content(
        '<a download="SomeFile.txt" href="data:text/plain;charset=utf8;,hello world">Download!</a>'
    )
    async with page.expect_download() as download_info:
        await page.get_by_text("Download").click()
    download = await download_info.value
    assert download.suggested_filename == "SomeFile.txt"


async def test_DO_038_should_download_successfully_when_routing(
    browser: Browser, server: Server
) -> None:
    page = await browser.new_page()
    await page.context.route("**/*", lambda route: route.continue_())
    await page.goto(server.PREFIX + "/empty.html")
    await page.set_content(
        f'<a href="{server.PREFIX}/chromium-linux.zip" download="foo.zip">download</a>'
    )
    async with page.expect_download() as download_info:
        await page.click("a")
    download = await download_info.value
    assert download.suggested_filename == "foo.zip"
    assert download.url == f"{server.PREFIX}/chromium-linux.zip"
    assert await download.failure() is None
    await page.close()


async def assert_download_to_pdf(download: Download, file_path: Path) -> None:
    assert download.suggested_filename == file_path.name
    # Upstream reads download.createReadStream(), which the Python API does not have.
    data = (await download.path()).read_bytes()
    assert download.url.endswith("/" + file_path.name)
    expected_prefix = b"%PDF"
    for i in range(len(expected_prefix)):
        assert data[i] == expected_prefix[i]
    assert_buffer(data, file_path.read_bytes())


def assert_buffer(expected: bytes, actual: bytes) -> None:
    assert len(expected) == len(actual)
    for i in range(len(expected)):
        assert expected[i] == actual[i]
