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
import datetime
from typing import Callable, List

import pytest

from playwright.async_api import Browser, BrowserContext, Error, Page
from tests.server import Server, TestServerRequest
from tests.utils import must


async def test_should_work(context: BrowserContext, page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await context.add_cookies(
        [{"url": server.EMPTY_PAGE, "name": "password", "value": "123456"}]
    )
    assert await page.evaluate("() => document.cookie") == "password=123456"


async def test_should_roundtrip_cookie(
    context: BrowserContext, page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    # @see https://en.wikipedia.org/wiki/Year_2038_problem
    date = int(datetime.datetime(2038, 1, 1).timestamp() * 1000)
    document_cookie = await page.evaluate(
        """timestamp => {
    const date = new Date(timestamp);
    document.cookie = `username=John Doe;expires=${date.toUTCString()}`;
    return document.cookie;
  }""",
        date,
    )
    assert document_cookie == "username=John Doe"
    cookies = await context.cookies()
    await context.clear_cookies()
    assert await context.cookies() == []
    # TODO: We are waiting for PEP705 so SetCookieParam can be readonly and matches the Cookie type.
    await context.add_cookies(cookies)  # type: ignore
    assert await context.cookies() == cookies


async def test_should_send_cookie_header(
    server: Server, context: BrowserContext
) -> None:
    cookie: List[str] = []

    def handler(request: TestServerRequest) -> None:
        cookie.extend(must(request.requestHeaders.getRawHeaders("cookie")))
        request.finish()

    server.set_route("/empty.html", handler)
    await context.add_cookies(
        [{"url": server.EMPTY_PAGE, "name": "cookie", "value": "value"}]
    )
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    assert cookie == ["cookie=value"]


async def test_should_isolate_cookies_in_browser_contexts(
    context: BrowserContext, server: Server, browser: Browser
) -> None:
    another_context = await browser.new_context()
    await context.add_cookies(
        [{"url": server.EMPTY_PAGE, "name": "isolatecookie", "value": "page1value"}]
    )
    await another_context.add_cookies(
        [{"url": server.EMPTY_PAGE, "name": "isolatecookie", "value": "page2value"}]
    )

    cookies_1 = await context.cookies()
    cookies_2 = await another_context.cookies()
    assert len(cookies_1) == 1
    assert len(cookies_2) == 1
    assert cookies_1[0]["name"] == "isolatecookie"
    assert cookies_1[0]["value"] == "page1value"
    assert cookies_2[0]["name"] == "isolatecookie"
    assert cookies_2[0]["value"] == "page2value"
    await another_context.close()


async def test_should_isolate_session_cookies(
    context: BrowserContext, server: Server, browser: Browser
) -> None:
    server.set_route(
        "/setcookie.html",
        lambda r: (
            r.setHeader("Set-Cookie", "session=value"),
            r.finish(),
        ),
    )

    page_1 = await context.new_page()
    await page_1.goto(server.PREFIX + "/setcookie.html")
    ##
    page_2 = await context.new_page()
    await page_2.goto(server.EMPTY_PAGE)
    cookies_2 = await context.cookies()
    assert len(cookies_2) == 1
    assert ",".join(list(map(lambda c: c["value"], cookies_2))) == "value"
    ##
    context_b = await browser.new_context()
    page_3 = await context_b.new_page()
    await page_3.goto(server.EMPTY_PAGE)
    cookies_3 = await context_b.cookies()
    assert cookies_3 == []
    await context_b.close()


async def test_should_isolate_persistent_cookies(
    context: BrowserContext, server: Server, browser: Browser
) -> None:
    server.set_route(
        "/setcookie.html",
        lambda r: (
            r.setHeader("Set-Cookie", "persistent=persistent-value; max-age=3600"),
            r.finish(),
        ),
    )

    page = await context.new_page()
    await page.goto(server.PREFIX + "/setcookie.html")

    context_1 = context
    context_2 = await browser.new_context()
    [page_1, page_2] = await asyncio.gather(context_1.new_page(), context_2.new_page())
    await asyncio.gather(page_1.goto(server.EMPTY_PAGE), page_2.goto(server.EMPTY_PAGE))
    [cookies_1, cookies_2] = await asyncio.gather(
        context_1.cookies(), context_2.cookies()
    )
    assert len(cookies_1) == 1
    assert cookies_1[0]["name"] == "persistent"
    assert cookies_1[0]["value"] == "persistent-value"
    assert len(cookies_2) == 0
    await context_2.close()


async def test_should_isolate_send_cookie_header(
    server: Server, context: BrowserContext, browser: Browser
) -> None:
    cookie: List[str] = []

    def handler(request: TestServerRequest) -> None:
        cookie.extend(request.requestHeaders.getRawHeaders("cookie") or [])
        request.finish()

    server.set_route("/empty.html", handler)

    await context.add_cookies(
        [{"url": server.EMPTY_PAGE, "name": "sendcookie", "value": "value"}]
    )

    page_1 = await context.new_page()
    await page_1.goto(server.EMPTY_PAGE)
    assert cookie == ["sendcookie=value"]
    cookie.clear()
    ##
    context_2 = await browser.new_context()
    page_2 = await context_2.new_page()
    await page_2.goto(server.EMPTY_PAGE)
    assert cookie == []
    await context_2.close()


async def test_should_isolate_cookies_between_launches(
    browser_factory: Callable[..., "asyncio.Future[Browser]"], server: Server
) -> None:
    browser_1 = await browser_factory()
    context_1 = await browser_1.new_context()
    await context_1.add_cookies(
        [
            {
                "url": server.EMPTY_PAGE,
                "name": "cookie-in-context-1",
                "value": "value",
                "expires": int(datetime.datetime.now().timestamp() + 10000),
            }
        ]
    )
    await browser_1.close()

    browser_2 = await browser_factory()
    context_2 = await browser_2.new_context()
    cookies = await context_2.cookies()
    assert cookies == []
    await browser_2.close()


async def test_should_set_multiple_cookies(
    context: BrowserContext, page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await context.add_cookies(
        [
            {"url": server.EMPTY_PAGE, "name": "multiple-1", "value": "123456"},
            {"url": server.EMPTY_PAGE, "name": "multiple-2", "value": "bar"},
        ]
    )
    assert (
        await page.evaluate(
            """() => {
    const cookies = document.cookie.split(';');
    return cookies.map(cookie => cookie.trim()).sort();
  }"""
        )
        == ["multiple-1=123456", "multiple-2=bar"]
    )


async def test_should_have_expires_set_to_neg_1_for_session_cookies(
    context: BrowserContext, server: Server
) -> None:
    await context.add_cookies(
        [{"url": server.EMPTY_PAGE, "name": "expires", "value": "123456"}]
    )
    cookies = await context.cookies()
    assert cookies[0]["expires"] == -1


async def test_should_set_cookie_with_reasonable_defaults(
    context: BrowserContext,
    server: Server,
    default_same_site_cookie_value: str,
) -> None:
    await context.add_cookies(
        [{"url": server.EMPTY_PAGE, "name": "defaults", "value": "123456"}]
    )
    cookies = await context.cookies()
    cookies.sort(key=lambda r: r["name"])
    assert cookies == [
        {
            "name": "defaults",
            "value": "123456",
            "domain": "localhost",
            "path": "/",
            "expires": -1,
            "httpOnly": False,
            "secure": False,
            "sameSite": default_same_site_cookie_value,
        }
    ]


async def test_should_set_a_cookie_with_a_path(
    context: BrowserContext,
    page: Page,
    server: Server,
    default_same_site_cookie_value: str,
) -> None:
    await page.goto(server.PREFIX + "/grid.html")
    await context.add_cookies(
        [
            {
                "domain": "localhost",
                "path": "/grid.html",
                "name": "gridcookie",
                "value": "GRID",
            }
        ]
    )
    assert await context.cookies() == [
        {
            "name": "gridcookie",
            "value": "GRID",
            "domain": "localhost",
            "path": "/grid.html",
            "expires": -1,
            "httpOnly": False,
            "secure": False,
            "sameSite": default_same_site_cookie_value,
        }
    ]
    assert await page.evaluate("document.cookie") == "gridcookie=GRID"
    await page.goto(server.EMPTY_PAGE)
    assert await page.evaluate("document.cookie") == ""
    await page.goto(server.PREFIX + "/grid.html")
    assert await page.evaluate("document.cookie") == "gridcookie=GRID"


async def test_should_not_set_a_cookie_with_blank_page_url(
    context: BrowserContext, server: Server
) -> None:
    with pytest.raises(Error) as exc_info:
        await context.add_cookies(
            [
                {"url": server.EMPTY_PAGE, "name": "example-cookie", "value": "best"},
                {"url": "about:blank", "name": "example-cookie-blank", "value": "best"},
            ]
        )
    assert (
        'Blank page can not have cookie "example-cookie-blank"'
        in exc_info.value.message
    )


async def test_should_not_set_a_cookie_on_a_data_url_page(
    context: BrowserContext,
) -> None:
    with pytest.raises(Error) as exc_info:
        await context.add_cookies(
            [
                {
                    "url": "data:,Hello%2C%20World!",
                    "name": "example-cookie",
                    "value": "best",
                }
            ]
        )
    assert (
        'Data URL page can not have cookie "example-cookie"' in exc_info.value.message
    )


async def test_should_default_to_setting_secure_cookie_for_https_websites(
    context: BrowserContext, page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    SECURE_URL = "https://example.com"
    await context.add_cookies([{"url": SECURE_URL, "name": "foo", "value": "bar"}])
    [cookie] = await context.cookies(SECURE_URL)
    assert cookie["secure"]


async def test_should_be_able_to_set_unsecure_cookie_for_http_website(
    context: BrowserContext, page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    HTTP_URL = "http://example.com"
    await context.add_cookies([{"url": HTTP_URL, "name": "foo", "value": "bar"}])
    [cookie] = await context.cookies(HTTP_URL)
    assert not cookie["secure"]


async def test_should_set_a_cookie_on_a_different_domain(
    context: BrowserContext,
    page: Page,
    server: Server,
    default_same_site_cookie_value: str,
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await context.add_cookies(
        [{"url": "https://www.example.com", "name": "example-cookie", "value": "best"}]
    )
    assert await page.evaluate("document.cookie") == ""
    assert await context.cookies("https://www.example.com") == [
        {
            "name": "example-cookie",
            "value": "best",
            "domain": "www.example.com",
            "path": "/",
            "expires": -1,
            "httpOnly": False,
            "secure": True,
            "sameSite": default_same_site_cookie_value,
        }
    ]


async def test_should_set_cookies_for_a_frame(
    context: BrowserContext, page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await context.add_cookies(
        [{"url": server.PREFIX, "name": "frame-cookie", "value": "value"}]
    )
    await page.evaluate(
        """src => {
    let fulfill;
    const promise = new Promise(x => fulfill = x);
    const iframe = document.createElement('iframe');
    document.body.appendChild(iframe);
    iframe.onload = fulfill;
    iframe.src = src;
    return promise;
  }""",
        server.PREFIX + "/grid.html",
    )

    assert await page.frames[1].evaluate("document.cookie") == "frame-cookie=value"


async def test_should_not_block_third_party_cookies(
    context: BrowserContext,
    page: Page,
    server: Server,
    is_chromium: bool,
    is_firefox: bool,
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.evaluate(
        """src => {
    let fulfill;
    const promise = new Promise(x => fulfill = x);
    const iframe = document.createElement('iframe');
    document.body.appendChild(iframe);
    iframe.onload = fulfill;
    iframe.src = src;
    return promise;
  }""",
        server.CROSS_PROCESS_PREFIX + "/grid.html",
    )
    await page.frames[1].evaluate("document.cookie = 'username=John Doe'")
    await page.wait_for_timeout(2000)
    allows_third_party = is_firefox
    cookies = await context.cookies(server.CROSS_PROCESS_PREFIX + "/grid.html")

    if allows_third_party:
        assert cookies == [
            {
                "domain": "127.0.0.1",
                "expires": -1,
                "httpOnly": False,
                "name": "username",
                "path": "/",
                "sameSite": "Lax" if is_chromium else "None",
                "secure": False,
                "value": "John Doe",
            }
        ]
    else:
        assert cookies == []
