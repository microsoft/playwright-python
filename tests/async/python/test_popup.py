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

import asyncio

from playwright.async_api import Browser
from tests.server import Server


async def test_window_open_inherit_user_agent_from_browser_context(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context(user_agent="hey")

    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    request_promise = asyncio.create_task(server.wait_for_request("/dummy.html"))
    await asyncio.sleep(0)  # execute scheduled tasks, but don't await them
    user_agent = await page.evaluate(
        """url => {
            win = window.open(url)
            return win.navigator.userAgent
        }""",
        server.PREFIX + "/dummy.html",
    )
    request = await request_promise
    assert user_agent == "hey"
    assert request.requestHeaders.getRawHeaders("user-agent") == ["hey"]
    await context.close()
