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
    assert await page.evaluate("11 * 11") == 121
    await page.goto(server.EMPTY_PAGE)
    await browser.close()

    browser = await browser_type.connect(remote_server.ws_endpoint)
    browser_context = await browser.new_context()
    page = await browser_context.new_page()
    await page.goto(server.EMPTY_PAGE)
    await browser.close()


async def test_browser_type_connect_should_be_able_to_connect_two_browsers_at_the_same_time(
    server: Server, browser_type: BrowserType, launch_server
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
    server: Server, browser_type: BrowserType, launch_server
):
    # Launch another server to not affect other tests.
    remote = launch_server()

    browser1 = await browser_type.connect(remote.ws_endpoint)
    browser2 = await browser_type.connect(remote.ws_endpoint)

    disconnected1 = []
    disconnected2_event_future: asyncio.Future[bool] = asyncio.Future()
    browser1.on("disconnected", lambda: disconnected1.append(True))
    browser2.on("disconnected", lambda: disconnected2_event_future.set_result(True))

    page2 = await browser2.new_page()

    await browser1.close()
    assert len(disconnected1) == 1
    assert disconnected2_event_future.done() is False

    remote.kill()
    assert len(disconnected1) == 1

    with pytest.raises(Error):
        # Tickle connection so that it gets a chance to dispatch disconnect event.
        await page2.title()
    await disconnected2_event_future


async def test_browser_type_disconnected_event_should_have_browser_as_argument(
    server: Server, browser_type: BrowserType, launch_server
):
    remote_server = launch_server()
    browser = await browser_type.connect(remote_server.ws_endpoint)
    event_payloads = []
    browser.on("disconnected", lambda b: event_payloads.append(b))
    await browser.close()
    assert event_payloads[0] == browser


async def test_browser_type_connect_set_browser_connected_state(
    server: Server, browser_type: BrowserType, launch_server
):
    remote_server = launch_server()
    browser = await browser_type.connect(remote_server.ws_endpoint)
    assert browser.is_connected()
    await browser.close()
    assert browser.is_connected() is False


async def test_browser_type_connect_should_throw_when_used_after_is_connected_returns_false(
    server: Server, browser_type: BrowserType, launch_server
):
    remote_server = launch_server()
    browser = await browser_type.connect(remote_server.ws_endpoint)
    page = await browser.new_page()

    disconnected_event_future: asyncio.Future[bool] = asyncio.Future()
    browser.on("disconnected", lambda: disconnected_event_future.set_result(True))

    remote_server.kill()

    # Wait until the process and its WS connection is closed
    await disconnected_event_future

    with pytest.raises(Error) as exc_info:
        await page.evaluate("1 + 1")
    assert "Protocol error (Runtime.evaluate): Target closed." in exc_info.value.message
    on_disconnected: asyncio.Future[None] = asyncio.Future()
    browser.on("disconnected", lambda: on_disconnected.set_result(None))
    await on_disconnected
    assert browser.is_connected() is False


async def test_browser_type_connect_should_reject_navigation_when_browser_closes(
    server: Server, browser_type: BrowserType, launch_server
):
    remote_server = launch_server()
    browser = await browser_type.connect(remote_server.ws_endpoint)
    page = await browser.new_page()
    server.set_route("/one-style.css", lambda: None)
    page.on("request", lambda: asyncio.create_task(browser.close()))

    with pytest.raises(Error) as exc_info:
        await page.goto(server.PREFIX + "/one-style.html")
    assert "Playwright connection closed" in exc_info.value.message
