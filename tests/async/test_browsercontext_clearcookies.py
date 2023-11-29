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

from playwright.async_api import Browser, BrowserContext, Page
from tests.server import Server


async def test_should_clear_cookies(
    context: BrowserContext, page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await context.add_cookies(
        [{"url": server.EMPTY_PAGE, "name": "cookie1", "value": "1"}]
    )
    assert await page.evaluate("document.cookie") == "cookie1=1"
    await context.clear_cookies()
    assert await context.cookies() == []
    await page.reload()
    assert await page.evaluate("document.cookie") == ""


async def test_should_isolate_cookies_when_clearing(
    context: BrowserContext, server: Server, browser: Browser
) -> None:
    another_context = await browser.new_context()
    await context.add_cookies(
        [{"url": server.EMPTY_PAGE, "name": "page1cookie", "value": "page1value"}]
    )
    await another_context.add_cookies(
        [{"url": server.EMPTY_PAGE, "name": "page2cookie", "value": "page2value"}]
    )

    assert len(await context.cookies()) == 1
    assert len(await another_context.cookies()) == 1

    await context.clear_cookies()
    assert len(await context.cookies()) == 0
    assert len(await another_context.cookies()) == 1

    await another_context.clear_cookies()
    assert len(await context.cookies()) == 0
    assert len(await another_context.cookies()) == 0
    await another_context.close()
