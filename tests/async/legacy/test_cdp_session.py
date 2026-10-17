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

from playwright.async_api import Browser, Error, Page
from tests.server import Server
from tests.utils import TARGET_CLOSED_ERROR_MESSAGE


@pytest.mark.only_browser("chromium")
async def test_should_work(page: Page) -> None:
    client = await page.context.new_cdp_session(page)
    events = []
    client.on("Runtime.consoleAPICalled", lambda params: events.append(params))
    await client.send("Runtime.enable")
    result = await client.send(
        "Runtime.evaluate",
        {"expression": "window.foo = 'bar'; console.log('log'); 'result'"},
    )
    assert result == {"result": {"type": "string", "value": "result"}}
    foo = await page.evaluate("() => window.foo")
    assert foo == "bar"
    assert events[0]["args"][0]["value"] == "log"


@pytest.mark.only_browser("chromium")
async def test_should_receive_events(page: Page, server: Server) -> None:
    client = await page.context.new_cdp_session(page)
    await client.send("Network.enable")
    events = []
    client.on("Network.requestWillBeSent", lambda event: events.append(event))
    await page.goto(server.EMPTY_PAGE)
    assert len(events) == 1


@pytest.mark.only_browser("chromium")
async def test_should_be_able_to_detach_session(page: Page) -> None:
    client = await page.context.new_cdp_session(page)
    await client.send("Runtime.enable")
    eval_response = await client.send(
        "Runtime.evaluate", {"expression": "1 + 2", "returnByValue": True}
    )
    assert eval_response["result"]["value"] == 3
    await client.detach()
    with pytest.raises(Error) as exc_info:
        await client.send(
            "Runtime.evaluate", {"expression": "3 + 1", "returnByValue": True}
        )
    assert TARGET_CLOSED_ERROR_MESSAGE in exc_info.value.message


@pytest.mark.only_browser("chromium")
async def test_should_not_break_page_close(browser: Browser) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    session = await page.context.new_cdp_session(page)
    await session.detach()
    await page.close()
    await context.close()


@pytest.mark.only_browser("chromium")
async def test_should_detach_when_page_closes(browser: Browser) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    session = await context.new_cdp_session(page)
    await page.close()
    with pytest.raises(Error):
        await session.detach()
    await context.close()


@pytest.mark.only_browser("chromium")
async def test_should_work_with_main_frame(browser: Browser) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    client = await context.new_cdp_session(page.main_frame)
    await client.send("Runtime.enable")
    await client.send(
        "Runtime.evaluate",
        {"expression": "window.foo = 'bar'"},
    )
    assert await page.evaluate("() => window.foo") == "bar"
