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

import pytest

from playwright.async_api import BrowserType, Error
from tests.server import Server


async def test_browser_type_connect_should_be_able_to_reconnect_to_a_browser(
    server: Server, browser_type: BrowserType, launch_server
):
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
    browser_type: BrowserType, launch_server
):
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
    browser_type: BrowserType, launch_server
):
    # Launch another server to not affect other tests.
    remote = launch_server()

    browser1 = await browser_type.connect(remote.ws_endpoint)
    browser2 = await browser_type.connect(remote.ws_endpoint)

    disconnected1 = []
    disconnected2 = []
    browser1.on("disconnected", lambda: disconnected1.append(True))
    browser2.on("disconnected", lambda: disconnected2.append(True))

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
    browser_type: BrowserType, launch_server
):
    # Launch another server to not affect other tests.
    remote = launch_server()

    browser = await browser_type.connect(remote.ws_endpoint)

    disconnected = []
    browser.on("disconnected", lambda: disconnected.append(True))
    page = await browser.new_page()
    remote.kill()
    with pytest.raises(Error):
        await page.title()
    assert len(disconnected) == 1


async def test_browser_type_disconnected_event_should_have_browser_as_argument(
    browser_type: BrowserType, launch_server
):
    remote_server = launch_server()
    browser = await browser_type.connect(remote_server.ws_endpoint)
    event_payloads = []
    browser.on("disconnected", lambda b: event_payloads.append(b))
    await browser.close()
    assert event_payloads[0] == browser


async def test_browser_type_connect_set_browser_connected_state(
    browser_type: BrowserType, launch_server
):
    remote_server = launch_server()
    browser = await browser_type.connect(remote_server.ws_endpoint)
    assert browser.is_connected()
    await browser.close()
    assert browser.is_connected() is False


async def test_browser_type_connect_should_throw_when_used_after_is_connected_returns_false(
    browser_type: BrowserType, launch_server
):
    remote_server = launch_server()
    browser = await browser_type.connect(remote_server.ws_endpoint)
    page = await browser.new_page()

    remote_server.kill()

    with pytest.raises(Error) as exc_info:
        await page.evaluate("1 + 1")
    assert "Playwright connection closed" == exc_info.value.message
    assert browser.is_connected() is False


async def test_browser_type_connect_should_reject_navigation_when_browser_closes(
    server: Server, browser_type: BrowserType, launch_server
):
    remote_server = launch_server()
    browser = await browser_type.connect(remote_server.ws_endpoint)
    page = await browser.new_page()
    await browser.close()

    with pytest.raises(Error) as exc_info:
        await page.goto(server.PREFIX + "/one-style.html")
    assert "Playwright connection closed" in exc_info.value.message


async def test_should_not_allow_getting_the_path(
    browser_type: BrowserType, launch_server, server: Server
):
    def handle_download(request):
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
    browser_type: BrowserType, launch_server, tmpdir, server
):
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
    browser_type: BrowserType, launch_server
):
    remote_server = launch_server()
    remote_server.kill()
    with pytest.raises(Error) as exc:
        await browser_type.connect(remote_server.ws_endpoint)
    assert "websocket.connect: " in exc.value.message
