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


async def test_connect_to_closed_server_without_hangs(
    browser_type: BrowserType, launch_server
):
    remote_server = launch_server()
    remote_server.kill()
    with pytest.raises(Error) as exc:
        await browser_type.connect(remote_server.ws_endpoint)
    assert "playwright's websocket endpoint connection error" in exc.value.message
