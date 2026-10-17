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

import datetime

import pytest

from playwright.async_api import BrowserContext, Page
from tests.server import Server


async def test_should_return_no_cookies_in_pristine_browser_context(
    context: BrowserContext,
) -> None:
    assert await context.cookies() == []


async def test_should_get_a_cookie(
    context: BrowserContext,
    page: Page,
    server: Server,
    default_same_site_cookie_value: str,
) -> None:
    await page.goto(server.EMPTY_PAGE)
    document_cookie = await page.evaluate(
        """() => {
    document.cookie = 'username=John Doe';
    return document.cookie;
  }"""
    )
    assert document_cookie == "username=John Doe"
    assert await context.cookies() == [
        {
            "name": "username",
            "value": "John Doe",
            "domain": "localhost",
            "path": "/",
            "expires": -1,
            "httpOnly": False,
            "secure": False,
            "sameSite": default_same_site_cookie_value,
        }
    ]


async def test_should_get_a_non_session_cookie(
    context: BrowserContext,
    page: Page,
    server: Server,
    default_same_site_cookie_value: str,
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
    expires = cookies[0]["expires"]
    del cookies[0]["expires"]
    # Browsers start to cap cookies with 400 days max expires value.
    # See https://github.com/httpwg/http-extensions/pull/1732
    # Chromium patch: https://chromium.googlesource.com/chromium/src/+/aaa5d2b55478eac2ee642653dcd77a50ac3faff6
    # We want to make sure that expires date is at least 400 days in future.
    # We use 355 to prevent flakes and not think about timezones!
    assert datetime.datetime.fromtimestamp(
        expires
    ) - datetime.datetime.now() > datetime.timedelta(days=355)
    assert cookies == [
        {
            "name": "username",
            "value": "John Doe",
            "domain": "localhost",
            "path": "/",
            "httpOnly": False,
            "secure": False,
            "sameSite": default_same_site_cookie_value,
        }
    ]


async def test_should_properly_report_httpOnly_cookie(
    context: BrowserContext, page: Page, server: Server
) -> None:
    server.set_route(
        "/empty.html",
        lambda r: (
            r.setHeader("Set-Cookie", "name=value;httpOnly; Path=/"),
            r.finish(),
        ),
    )

    await page.goto(server.EMPTY_PAGE)
    cookies = await context.cookies()
    assert len(cookies) == 1
    assert cookies[0]["httpOnly"] is True


async def test_should_properly_report_strict_sameSite_cookie(
    context: BrowserContext, page: Page, server: Server, is_webkit: bool, is_win: bool
) -> None:
    if is_webkit and is_win:
        pytest.skip()

    server.set_route(
        "/empty.html",
        lambda r: (
            r.setHeader("Set-Cookie", "name=value;sameSite=Strict"),
            r.finish(),
        ),
    )
    await page.goto(server.EMPTY_PAGE)
    cookies = await context.cookies()
    assert len(cookies) == 1
    assert cookies[0]["sameSite"] == "Strict"


async def test_should_properly_report_lax_sameSite_cookie(
    context: BrowserContext, page: Page, server: Server, is_webkit: bool, is_win: bool
) -> None:
    if is_webkit and is_win:
        pytest.skip()

    server.set_route(
        "/empty.html",
        lambda r: (
            r.setHeader("Set-Cookie", "name=value;sameSite=Lax"),
            r.finish(),
        ),
    )
    await page.goto(server.EMPTY_PAGE)
    cookies = await context.cookies()
    assert len(cookies) == 1
    assert cookies[0]["sameSite"] == "Lax"


async def test_should_get_multiple_cookies(
    context: BrowserContext,
    page: Page,
    server: Server,
    default_same_site_cookie_value: str,
) -> None:
    await page.goto(server.EMPTY_PAGE)
    document_cookie = await page.evaluate(
        """() => {
    document.cookie = 'username=John Doe';
    document.cookie = 'password=1234';
    return document.cookie.split('; ').sort().join('; ');
  }"""
    )
    cookies = await context.cookies()
    cookies.sort(key=lambda r: r["name"])
    assert document_cookie == "password=1234; username=John Doe"
    assert cookies == [
        {
            "name": "password",
            "value": "1234",
            "domain": "localhost",
            "path": "/",
            "expires": -1,
            "httpOnly": False,
            "secure": False,
            "sameSite": default_same_site_cookie_value,
        },
        {
            "name": "username",
            "value": "John Doe",
            "domain": "localhost",
            "path": "/",
            "expires": -1,
            "httpOnly": False,
            "secure": False,
            "sameSite": default_same_site_cookie_value,
        },
    ]


async def test_should_get_cookies_from_multiple_urls(
    context: BrowserContext, default_same_site_cookie_value: str
) -> None:
    await context.add_cookies(
        [
            {"url": "https://foo.com", "name": "doggo", "value": "woofs"},
            {"url": "https://bar.com", "name": "catto", "value": "purrs"},
            {"url": "https://baz.com", "name": "birdo", "value": "tweets"},
        ]
    )
    cookies = await context.cookies(["https://foo.com", "https://baz.com"])
    cookies.sort(key=lambda r: r["name"])

    assert cookies == [
        {
            "name": "birdo",
            "value": "tweets",
            "domain": "baz.com",
            "path": "/",
            "expires": -1,
            "httpOnly": False,
            "secure": True,
            "sameSite": default_same_site_cookie_value,
        },
        {
            "name": "doggo",
            "value": "woofs",
            "domain": "foo.com",
            "path": "/",
            "expires": -1,
            "httpOnly": False,
            "secure": True,
            "sameSite": default_same_site_cookie_value,
        },
    ]
