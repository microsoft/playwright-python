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

import re
from urllib.parse import urlparse

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


async def test_should_remove_cookies_by_name(
    context: BrowserContext, page: Page, server: Server
) -> None:
    await context.add_cookies(
        [
            {
                "name": "cookie1",
                "value": "1",
                "domain": urlparse(server.PREFIX).hostname,
                "path": "/",
            },
            {
                "name": "cookie2",
                "value": "2",
                "domain": urlparse(server.PREFIX).hostname,
                "path": "/",
            },
        ]
    )
    await page.goto(server.PREFIX)
    assert await page.evaluate("document.cookie") == "cookie1=1; cookie2=2"
    await context.clear_cookies(name="cookie1")
    assert await page.evaluate("document.cookie") == "cookie2=2"


async def test_should_remove_cookies_by_name_regex(
    context: BrowserContext, page: Page, server: Server
) -> None:
    await context.add_cookies(
        [
            {
                "name": "cookie1",
                "value": "1",
                "domain": urlparse(server.PREFIX).hostname,
                "path": "/",
            },
            {
                "name": "cookie2",
                "value": "2",
                "domain": urlparse(server.PREFIX).hostname,
                "path": "/",
            },
        ]
    )
    await page.goto(server.PREFIX)
    assert await page.evaluate("document.cookie") == "cookie1=1; cookie2=2"
    await context.clear_cookies(name=re.compile("coo.*1"))
    assert await page.evaluate("document.cookie") == "cookie2=2"


async def test_should_remove_cookies_by_domain(
    context: BrowserContext, page: Page, server: Server
) -> None:
    await context.add_cookies(
        [
            {
                "name": "cookie1",
                "value": "1",
                "domain": urlparse(server.PREFIX).hostname,
                "path": "/",
            },
            {
                "name": "cookie2",
                "value": "2",
                "domain": urlparse(server.CROSS_PROCESS_PREFIX).hostname,
                "path": "/",
            },
        ]
    )
    await page.goto(server.PREFIX)
    assert await page.evaluate("document.cookie") == "cookie1=1"
    await page.goto(server.CROSS_PROCESS_PREFIX)
    assert await page.evaluate("document.cookie") == "cookie2=2"
    await context.clear_cookies(domain=urlparse(server.CROSS_PROCESS_PREFIX).hostname)
    assert await page.evaluate("document.cookie") == ""
    await page.goto(server.PREFIX)
    assert await page.evaluate("document.cookie") == "cookie1=1"


async def test_should_remove_cookies_by_path(
    context: BrowserContext, page: Page, server: Server
) -> None:
    await context.add_cookies(
        [
            {
                "name": "cookie1",
                "value": "1",
                "domain": urlparse(server.PREFIX).hostname,
                "path": "/api/v1",
            },
            {
                "name": "cookie2",
                "value": "2",
                "domain": urlparse(server.PREFIX).hostname,
                "path": "/api/v2",
            },
            {
                "name": "cookie3",
                "value": "3",
                "domain": urlparse(server.PREFIX).hostname,
                "path": "/",
            },
        ]
    )
    await page.goto(server.PREFIX + "/api/v1")
    assert await page.evaluate("document.cookie") == "cookie1=1; cookie3=3"
    await context.clear_cookies(path="/api/v1")
    assert await page.evaluate("document.cookie") == "cookie3=3"
    await page.goto(server.PREFIX + "/api/v2")
    assert await page.evaluate("document.cookie") == "cookie2=2; cookie3=3"
    await page.goto(server.PREFIX + "/")
    assert await page.evaluate("document.cookie") == "cookie3=3"


async def test_should_remove_cookies_by_name_and_domain(
    context: BrowserContext, page: Page, server: Server
) -> None:
    await context.add_cookies(
        [
            {
                "name": "cookie1",
                "value": "1",
                "domain": urlparse(server.PREFIX).hostname,
                "path": "/",
            },
            {
                "name": "cookie1",
                "value": "1",
                "domain": urlparse(server.CROSS_PROCESS_PREFIX).hostname,
                "path": "/",
            },
        ]
    )
    await page.goto(server.PREFIX)
    assert await page.evaluate("document.cookie") == "cookie1=1"
    await context.clear_cookies(name="cookie1", domain=urlparse(server.PREFIX).hostname)
    assert await page.evaluate("document.cookie") == ""
    await page.goto(server.CROSS_PROCESS_PREFIX)
    assert await page.evaluate("document.cookie") == "cookie1=1"
