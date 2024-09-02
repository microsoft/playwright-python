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
import re
from pathlib import Path
from typing import Callable

import pytest
from flaky import flaky

from playwright.async_api import BrowserType, Error, Playwright, Route
from tests.conftest import RemoteServer
from tests.server import Server, TestServerRequest, WebSocketProtocol
from tests.utils import chromium_version_less_than, parse_trace


async def test_should_print_custom_ws_close_error(
    server: Server, browser_type: BrowserType
) -> None:
    def _handle_ws(ws: WebSocketProtocol) -> None:
        def _onMessage(payload: bytes, isBinary: bool) -> None:
            ws.sendClose(code=4123, reason="Oh my!")

        setattr(ws, "onMessage", _onMessage)

    server.once_web_socket_connection(_handle_ws)
    with pytest.raises(Error, match="Oh my!"):
        await browser_type.connect(f"ws://localhost:{server.PORT}/ws")


async def test_browser_type_connect_should_be_able_to_reconnect_to_a_browser(
    server: Server, browser_type: BrowserType, launch_server: Callable[[], RemoteServer]
) -> None:
    remote_server = launch_server()
    browser = await browser_type.connect(remote_server.ws_endpoint)
    browser_context = await browser.new_context()
    assert len(browser_context.pages) == 0
    page = await browser_context.new_page()
    assert len(browser_context.pages) == 1
    assert await page.evaluate("11 * 11") == 121
    await page.goto(server.EMPTY_PAGE)
    await browser.close()

    browser = await browser_type.connect(remote_server.ws_endpoint)
    browser_context = await browser.new_context()
    page = await browser_context.new_page()
    await page.goto(server.EMPTY_PAGE)
    await browser.close()


async def test_browser_type_connect_should_be_able_to_connect_two_browsers_at_the_same_time(
    browser_type: BrowserType, launch_server: Callable[[], RemoteServer]
) -> None:
    remote_server = launch_server()
    browser1 = await browser_type.connect(remote_server.ws_endpoint)
    assert len(browser1.contexts) == 0
    await browser1.new_context()
    assert len(browser1.contexts) == 1

    browser2 = await browser_type.connect(remote_server.ws_endpoint)
    assert len(browser2.contexts) == 0
    await browser2.new_context()
    assert len(browser2.contexts) == 1
    assert len(browser1.contexts) == 1

    await browser1.close()
    page2 = await browser2.new_page()
    # original browser should still work
    assert await page2.evaluate("7 * 6") == 42

    await browser2.close()


async def test_browser_type_connect_disconnected_event_should_be_emitted_when_browser_is_closed_or_server_is_closed(
    browser_type: BrowserType, launch_server: Callable[[], RemoteServer]
) -> None:
    # Launch another server to not affect other tests.
    remote = launch_server()

    browser1 = await browser_type.connect(remote.ws_endpoint)
    browser2 = await browser_type.connect(remote.ws_endpoint)

    disconnected1 = []
    disconnected2 = []
    browser1.on("disconnected", lambda _: disconnected1.append(True))
    browser2.on("disconnected", lambda _: disconnected2.append(True))

    page2 = await browser2.new_page()

    await browser1.close()
    assert len(disconnected1) == 1
    assert len(disconnected2) == 0

    remote.kill()
    assert len(disconnected1) == 1

    with pytest.raises(Error):
        # Tickle connection so that it gets a chance to dispatch disconnect event.
        await page2.title()
    assert len(disconnected2) == 1


async def test_browser_type_connect_disconnected_event_should_be_emitted_when_remote_killed_connection(
    browser_type: BrowserType, launch_server: Callable[[], RemoteServer]
) -> None:
    # Launch another server to not affect other tests.
    remote = launch_server()

    browser = await browser_type.connect(remote.ws_endpoint)

    disconnected = []
    browser.on("disconnected", lambda _: disconnected.append(True))
    page = await browser.new_page()
    remote.kill()
    with pytest.raises(Error):
        await page.title()
    assert len(disconnected) == 1


async def test_browser_type_disconnected_event_should_have_browser_as_argument(
    browser_type: BrowserType, launch_server: Callable[[], RemoteServer]
) -> None:
    remote_server = launch_server()
    browser = await browser_type.connect(remote_server.ws_endpoint)
    event_payloads = []
    browser.on("disconnected", lambda b: event_payloads.append(b))
    await browser.close()
    assert event_payloads[0] == browser


async def test_browser_type_connect_set_browser_connected_state(
    browser_type: BrowserType, launch_server: Callable[[], RemoteServer]
) -> None:
    remote_server = launch_server()
    browser = await browser_type.connect(remote_server.ws_endpoint)
    assert browser.is_connected()
    await browser.close()
    assert browser.is_connected() is False


async def test_browser_type_connect_should_throw_when_used_after_is_connected_returns_false(
    browser_type: BrowserType, launch_server: Callable[[], RemoteServer]
) -> None:
    remote_server = launch_server()
    browser = await browser_type.connect(remote_server.ws_endpoint)
    page = await browser.new_page()

    remote_server.kill()

    with pytest.raises(Error) as exc_info:
        await page.evaluate("1 + 1")
    assert "has been closed" in exc_info.value.message
    assert browser.is_connected() is False


async def test_browser_type_connect_should_reject_navigation_when_browser_closes(
    server: Server, browser_type: BrowserType, launch_server: Callable[[], RemoteServer]
) -> None:
    remote_server = launch_server()
    browser = await browser_type.connect(remote_server.ws_endpoint)
    page = await browser.new_page()
    await browser.close()

    with pytest.raises(Error) as exc_info:
        await page.goto(server.PREFIX + "/one-style.html")
    assert "has been closed" in exc_info.value.message


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
        == "Path is not available when using browser_type.connect(). Use save_as() to save a local copy."
    )
    remote_server.kill()


async def test_prevent_getting_video_path(
    browser_type: BrowserType,
    launch_server: Callable[[], RemoteServer],
    tmpdir: Path,
    server: Server,
) -> None:
    remote_server = launch_server()
    browser = await browser_type.connect(remote_server.ws_endpoint)
    page = await browser.new_page(record_video_dir=tmpdir)
    await page.goto(server.PREFIX + "/grid.html")
    await browser.close()
    assert page.video
    with pytest.raises(Error) as exc:
        await page.video.path()
    assert (
        exc.value.message
        == "Path is not available when using browserType.connect(). Use save_as() to save a local copy."
    )
    remote_server.kill()


async def test_connect_to_closed_server_without_hangs(
    browser_type: BrowserType, launch_server: Callable[[], RemoteServer]
) -> None:
    remote_server = launch_server()
    remote_server.kill()
    with pytest.raises(Error) as exc:
        await browser_type.connect(remote_server.ws_endpoint)
    assert "WebSocket error: " in exc.value.message


async def test_should_fulfill_with_global_fetch_result(
    browser_type: BrowserType,
    launch_server: Callable[[], RemoteServer],
    playwright: Playwright,
    server: Server,
) -> None:
    # Launch another server to not affect other tests.
    remote = launch_server()

    browser = await browser_type.connect(remote.ws_endpoint)
    context = await browser.new_context()
    page = await context.new_page()

    async def handle_request(route: Route) -> None:
        request = await playwright.request.new_context()
        response = await request.get(server.PREFIX + "/simple.json")
        await route.fulfill(response=response)
        await request.dispose()

    await page.route("**/*", handle_request)

    response = await page.goto(server.EMPTY_PAGE)
    assert response
    assert response.status == 200
    assert await response.json() == {"foo": "bar"}

    remote.kill()


@flaky
async def test_should_upload_large_file(
    browser_type: BrowserType,
    launch_server: Callable[[], RemoteServer],
    server: Server,
    tmp_path: Path,
) -> None:
    remote = launch_server()

    browser = await browser_type.connect(remote.ws_endpoint)
    context = await browser.new_context()
    page = await context.new_page()

    await page.goto(server.PREFIX + "/input/fileupload.html")
    large_file_path = tmp_path / "200MB.zip"
    data = b"A" * 1024
    with large_file_path.open("wb") as f:
        for i in range(0, 200 * 1024 * 1024, len(data)):
            f.write(data)
    input = page.locator('input[type="file"]')
    events = await input.evaluate_handle(
        """
        e => {
            const events = [];
            e.addEventListener('input', () => events.push('input'));
            e.addEventListener('change', () => events.push('change'));
            return events;
        }
    """
    )

    await input.set_input_files(large_file_path)
    assert await input.evaluate("e => e.files[0].name") == "200MB.zip"
    assert await events.evaluate("e => e") == ["input", "change"]

    [request, _] = await asyncio.gather(
        server.wait_for_request("/upload"),
        page.click("input[type=submit]", timeout=60_000),
    )

    contents = request.args[b"file1"][0]
    assert len(contents) == 200 * 1024 * 1024
    assert contents[:1024] == data
    # flake8: noqa: E203
    assert contents[len(contents) - 1024 :] == data
    assert request.post_body
    match = re.search(
        rb'^.*Content-Disposition: form-data; name="(?P<name>.*)"; filename="(?P<filename>.*)".*$',
        request.post_body,
        re.MULTILINE,
    )
    assert match
    assert match.group("name") == b"file1"
    assert match.group("filename") == b"200MB.zip"


async def test_should_record_trace_with_source(
    launch_server: Callable[[], RemoteServer],
    server: Server,
    tmp_path: Path,
    browser_type: BrowserType,
) -> None:
    remote = launch_server()
    browser = await browser_type.connect(remote.ws_endpoint)
    context = await browser.new_context()
    page = await context.new_page()

    await context.tracing.start(sources=True)
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<button>Click</button>")
    await page.click("'Click'")
    path = tmp_path / "trace1.zip"
    await context.tracing.stop(path=path)

    await context.close()
    await browser.close()

    (resources, events) = parse_trace(path)
    current_file_content = Path(__file__).read_bytes()
    found_current_file = False
    for name, resource in resources.items():
        if resource == current_file_content:
            found_current_file = True
            break
    assert found_current_file


async def test_should_record_trace_with_relative_trace_path(
    launch_server: Callable[[], RemoteServer],
    server: Server,
    browser_type: BrowserType,
) -> None:
    remote = launch_server()
    browser = await browser_type.connect(remote.ws_endpoint)
    context = await browser.new_context()
    page = await context.new_page()

    await context.tracing.start(sources=True)
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<button>Click</button>")
    await page.click("'Click'")
    try:
        await context.tracing.stop(path="trace1.zip")

        await context.close()
        await browser.close()

        # make sure trace1.zip exists
        assert Path("trace1.zip").exists()
    finally:
        Path("trace1.zip").unlink()


async def test_set_input_files_should_preserve_last_modified_timestamp(
    browser_type: BrowserType,
    launch_server: Callable[[], RemoteServer],
    assetdir: Path,
) -> None:
    # Launch another server to not affect other tests.
    remote = launch_server()

    browser = await browser_type.connect(remote.ws_endpoint)
    context = await browser.new_context()
    page = await context.new_page()

    await page.set_content("<input type=file multiple=true/>")
    input = page.locator("input")
    files = ["file-to-upload.txt", "file-to-upload-2.txt"]
    await input.set_input_files([assetdir / file for file in files])
    assert await input.evaluate("input => [...input.files].map(f => f.name)") == files
    timestamps = await input.evaluate(
        "input => [...input.files].map(f => f.lastModified)"
    )
    expected_timestamps = [os.path.getmtime(assetdir / file) * 1000 for file in files]

    # On Linux browser sometimes reduces the timestamp by 1ms: 1696272058110.0715  -> 1696272058109 or even
    # rounds it to seconds in WebKit: 1696272058110 -> 1696272058000.
    for i in range(len(timestamps)):
        assert abs(timestamps[i] - expected_timestamps[i]) < 1000


async def test_should_upload_a_folder(
    browser_type: BrowserType,
    launch_server: Callable[[], RemoteServer],
    server: Server,
    tmp_path: Path,
    browser_name: str,
    browser_version: str,
    headless: bool,
) -> None:
    remote = launch_server()

    browser = await browser_type.connect(remote.ws_endpoint)
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(server.PREFIX + "/input/folderupload.html")
    input = await page.query_selector("input")
    assert input
    dir = tmp_path / "file-upload-test"
    dir.mkdir()
    (dir / "file1.txt").write_text("file1 content")
    (dir / "file2").write_text("file2 content")
    (dir / "sub-dir").mkdir()
    (dir / "sub-dir" / "really.txt").write_text("sub-dir file content")
    await input.set_input_files(dir)
    assert set(
        await input.evaluate("e => [...e.files].map(f => f.webkitRelativePath)")
    ) == set(
        [
            "file-upload-test/file1.txt",
            "file-upload-test/file2",
            # https://issues.chromium.org/issues/345393164
            *(
                []
                if browser_name == "chromium"
                and headless
                and chromium_version_less_than(browser_version, "127.0.6533.0")
                else ["file-upload-test/sub-dir/really.txt"]
            ),
        ]
    )
    webkit_relative_paths = await input.evaluate(
        "e => [...e.files].map(f => f.webkitRelativePath)"
    )
    for i, webkit_relative_path in enumerate(webkit_relative_paths):
        content = await input.evaluate(
            """(e, i) => {
            const reader = new FileReader();
            const promise = new Promise(fulfill => reader.onload = fulfill);
            reader.readAsText(e.files[i]);
            return promise.then(() => reader.result);
        }""",
            i,
        )
        assert content == (dir / ".." / webkit_relative_path).read_text()
