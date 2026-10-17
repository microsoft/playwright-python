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

"""Port of tests/library/browsercontext-add-cookies.spec.ts."""

import datetime
import time
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence, cast
from urllib.parse import urlparse

import pytest

from playwright.async_api import (
    Browser,
    BrowserContext,
    BrowserType,
    Error,
    Page,
    Route,
)
from tests.server import Server, TestServerRequest, WebSocketProtocol


def by_name(cookies: Sequence[Any]) -> List[Dict[str, Any]]:
    """The cookies sorted by name, to compare them like a Set upstream."""
    return sorted((dict(cookie) for cookie in cookies), key=lambda c: c["name"])


def is_webkit_on_windows(
    browser_name: str, is_win: bool, browser_channel: Optional[str]
) -> bool:
    return browser_name == "webkit" and is_win and browser_channel != "webkit-wsl"


async def test_CO_019_should_work_smoke(
    context: BrowserContext, page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await context.add_cookies(
        [{"url": server.EMPTY_PAGE, "name": "password", "value": "123456"}]
    )
    assert await page.evaluate("() => document.cookie") == "password=123456"


async def fulfill_with_empty_html(route: Route) -> None:
    try:
        await route.fulfill(body="<html></html>")
    except Error:
        pass


async def test_CO_020_should_work_with_expires_1(
    context: BrowserContext, page: Page
) -> None:
    await context.add_cookies(
        [
            {
                "name": "username",
                "value": "John Doe",
                "domain": "www.example.com",
                "path": "/",
                "expires": -1,
                "httpOnly": False,
                "secure": False,
                "sameSite": "Lax",
            }
        ]
    )
    await page.route("**/*", fulfill_with_empty_html)
    await page.goto("https://www.example.com")
    assert await page.evaluate("() => document.cookie") == "username=John Doe"


async def test_CO_021_should_add_cookies_with_empty_value(
    context: BrowserContext, page: Page, server: Server
) -> None:
    await context.add_cookies(
        [
            {
                "name": "marker",
                "value": "",
                "domain": "www.example.com",
                "path": "/",
                "expires": -1,
                "httpOnly": False,
                "secure": False,
                "sameSite": "Lax",
            }
        ]
    )
    await page.route("**/*", fulfill_with_empty_html)
    await page.goto("https://www.example.com")
    assert await page.evaluate("() => document.cookie") == "marker="


async def test_CO_022_should_set_cookies_with_same_site_attribute_and_no_secure_attribute(
    context: BrowserContext,
    browser_name: str,
    is_win: bool,
    is_linux: bool,
    default_same_site_cookie_value: str,
    browser_channel: Optional[str],
) -> None:
    # Use domain instead of URL to ensure that the `secure` attribute is not set.
    await context.add_cookies(
        [
            {"domain": "foo.com", "path": "/", "name": "same-site-unset", "value": "1"},
            {
                "domain": "foo.com",
                "path": "/",
                "name": "same-site-none",
                "value": "1",
                "sameSite": "None",
            },
            {
                "domain": "foo.com",
                "path": "/",
                "name": "same-site-lax",
                "value": "1",
                "sameSite": "Lax",
            },
            {
                "domain": "foo.com",
                "path": "/",
                "name": "same-site-strict",
                "value": "1",
                "sameSite": "Strict",
            },
        ]
    )
    cookies = by_name(await context.cookies(["https://foo.com"]))
    webkit_on_windows = is_webkit_on_windows(browser_name, is_win, browser_channel)
    expected: List[Dict[str, Any]] = [
        {
            "name": "same-site-unset",
            "value": "1",
            "domain": "foo.com",
            "path": "/",
            "expires": -1,
            "httpOnly": False,
            "secure": False,
            "sameSite": default_same_site_cookie_value,
        },
        *(
            []
            if browser_name == "chromium"
            or (
                browser_name == "webkit"
                and (is_linux or browser_channel == "webkit-wsl")
            )
            else [
                {
                    "name": "same-site-none",
                    "value": "1",
                    "domain": "foo.com",
                    "path": "/",
                    "expires": -1,
                    "httpOnly": False,
                    "secure": False,
                    "sameSite": "None",
                }
            ]
        ),
        {
            "name": "same-site-lax",
            "value": "1",
            "domain": "foo.com",
            "path": "/",
            "expires": -1,
            "httpOnly": False,
            "secure": False,
            "sameSite": "None" if webkit_on_windows else "Lax",
        },
        {
            "name": "same-site-strict",
            "value": "1",
            "domain": "foo.com",
            "path": "/",
            "expires": -1,
            "httpOnly": False,
            "secure": False,
            "sameSite": "None" if webkit_on_windows else "Strict",
        },
    ]
    assert cookies == by_name(expected)


async def test_CO_023_should_roundtrip_cookie(
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
    await context.add_cookies(cast(Any, cookies))

    # Slightly different rounding on chromium win.
    def normalized_expires(cookies: Sequence[Any]) -> List[Dict[str, Any]]:
        return [
            {**cookie, "expires": int(cookie["expires"] // 1)} for cookie in cookies
        ]

    assert normalized_expires(await context.cookies()) == normalized_expires(cookies)


async def test_CO_024_should_send_cookie_header(
    server: Server, context: BrowserContext
) -> None:
    cookie: List[Optional[str]] = []

    def handler(request: TestServerRequest) -> None:
        cookie.append(request.getHeader("cookie"))
        request.finish()

    server.set_route("/empty.html", handler)
    await context.add_cookies(
        [{"url": server.EMPTY_PAGE, "name": "cookie", "value": "value"}]
    )
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    assert cookie == ["cookie=value"]


async def test_CO_025_should_isolate_cookies_in_browser_contexts(
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


async def test_CO_026_should_isolate_session_cookies(
    context: BrowserContext, server: Server, browser: Browser
) -> None:
    def handler(request: TestServerRequest) -> None:
        request.setHeader("Set-Cookie", "session=value")
        request.finish()

    server.set_route("/setcookie.html", handler)
    page = await context.new_page()
    await page.goto(server.PREFIX + "/setcookie.html")

    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    cookies = await context.cookies()
    assert len(cookies) == 1
    assert ",".join(cookie["value"] for cookie in cookies) == "value"

    context_2 = await browser.new_context()
    page = await context_2.new_page()
    await page.goto(server.EMPTY_PAGE)
    cookies = await context_2.cookies()
    assert (cookies[0]["name"] if cookies else None) is None
    await context_2.close()


async def test_CO_027_should_isolate_persistent_cookies(
    context: BrowserContext, server: Server, browser: Browser
) -> None:
    def handler(request: TestServerRequest) -> None:
        request.setHeader("Set-Cookie", "persistent=persistent-value; max-age=3600")
        request.finish()

    server.set_route("/setcookie.html", handler)
    page = await context.new_page()
    await page.goto(server.PREFIX + "/setcookie.html")

    context_1 = context
    context_2 = await browser.new_context()
    page_1 = await context_1.new_page()
    page_2 = await context_2.new_page()
    await page_1.goto(server.EMPTY_PAGE)
    await page_2.goto(server.EMPTY_PAGE)
    cookies_1 = await context_1.cookies()
    cookies_2 = await context_2.cookies()
    assert len(cookies_1) == 1
    assert cookies_1[0]["name"] == "persistent"
    assert cookies_1[0]["value"] == "persistent-value"
    assert len(cookies_2) == 0
    await context_2.close()


async def test_CO_028_should_isolate_send_cookie_header(
    server: Server, context: BrowserContext, browser: Browser
) -> None:
    cookie: List[str] = [""]

    def handler(request: TestServerRequest) -> None:
        cookie[0] = request.getHeader("cookie") or ""
        request.finish()

    server.set_route("/empty.html", handler)
    await context.add_cookies(
        [{"url": server.EMPTY_PAGE, "name": "sendcookie", "value": "value"}]
    )
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    assert cookie[0] == "sendcookie=value"

    context_2 = await browser.new_context()
    page = await context_2.new_page()
    await page.goto(server.EMPTY_PAGE)
    assert cookie[0] == ""
    await context_2.close()


async def test_CO_029_should_isolate_cookies_between_launches(
    browser_type: BrowserType, server: Server, launch_arguments: Dict
) -> None:
    browser_1 = await browser_type.launch(**launch_arguments)
    context_1 = await browser_1.new_context()
    await context_1.add_cookies(
        [
            {
                "url": server.EMPTY_PAGE,
                "name": "cookie-in-context-1",
                "value": "value",
                "expires": time.time() + 10000,
            }
        ]
    )
    await browser_1.close()

    browser_2 = await browser_type.launch(**launch_arguments)
    context_2 = await browser_2.new_context()
    cookies = await context_2.cookies()
    assert len(cookies) == 0
    await browser_2.close()


async def test_CO_030_should_set_multiple_cookies(
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


async def test_CO_031_should_have_expires_set_to_1_for_session_cookies(
    context: BrowserContext, server: Server
) -> None:
    await context.add_cookies(
        [{"url": server.EMPTY_PAGE, "name": "expires", "value": "123456"}]
    )
    cookies = await context.cookies()
    assert cookies[0]["expires"] == -1


async def test_CO_032_should_set_cookie_with_reasonable_defaults(
    context: BrowserContext, server: Server, default_same_site_cookie_value: str
) -> None:
    await context.add_cookies(
        [{"url": server.EMPTY_PAGE, "name": "defaults", "value": "123456"}]
    )
    cookies = await context.cookies()
    assert by_name(cookies) == [
        {
            "name": "defaults",
            "value": "123456",
            "domain": server.HOSTNAME,
            "path": "/",
            "expires": -1,
            "httpOnly": False,
            "secure": False,
            "sameSite": default_same_site_cookie_value,
        }
    ]


async def test_CO_033_should_set_a_cookie_with_a_path(
    context: BrowserContext,
    page: Page,
    server: Server,
    browser_name: str,
    is_win: bool,
    browser_channel: Optional[str],
) -> None:
    await page.goto(server.PREFIX + "/grid.html")
    await context.add_cookies(
        [
            {
                "domain": server.HOSTNAME,
                "path": "/grid.html",
                "name": "gridcookie",
                "value": "GRID",
                "sameSite": "Lax",
            }
        ]
    )
    assert await context.cookies() == [
        {
            "name": "gridcookie",
            "value": "GRID",
            "domain": server.HOSTNAME,
            "path": "/grid.html",
            "expires": -1,
            "httpOnly": False,
            "secure": False,
            "sameSite": (
                "None"
                if is_webkit_on_windows(browser_name, is_win, browser_channel)
                else "Lax"
            ),
        }
    ]
    assert await page.evaluate("document.cookie") == "gridcookie=GRID"
    await page.goto(server.EMPTY_PAGE)
    assert await page.evaluate("document.cookie") == ""
    await page.goto(server.PREFIX + "/grid.html")
    assert await page.evaluate("document.cookie") == "gridcookie=GRID"


async def test_CO_034_should_not_set_a_cookie_with_blank_page_url(
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


async def test_CO_035_should_not_set_a_cookie_on_a_data_url_page(
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


async def test_CO_036_should_default_to_setting_secure_cookie_for_https_websites(
    context: BrowserContext, page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    secure_url = "https://example.com"
    await context.add_cookies([{"url": secure_url, "name": "foo", "value": "bar"}])
    [cookie] = await context.cookies(secure_url)
    assert cookie["secure"] is True


async def test_CO_037_should_be_able_to_set_unsecure_cookie_for_http_website(
    context: BrowserContext, page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    http_url = "http://example.com"
    await context.add_cookies([{"url": http_url, "name": "foo", "value": "bar"}])
    [cookie] = await context.cookies(http_url)
    assert cookie["secure"] is False


async def test_CO_038_should_set_a_cookie_on_a_different_domain(
    context: BrowserContext,
    page: Page,
    server: Server,
    browser_name: str,
    is_win: bool,
    browser_channel: Optional[str],
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await context.add_cookies(
        [
            {
                "url": "https://www.example.com",
                "name": "example-cookie",
                "value": "best",
                "sameSite": "Lax",
            }
        ]
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
            "sameSite": (
                "None"
                if is_webkit_on_windows(browser_name, is_win, browser_channel)
                else "Lax"
            ),
        }
    ]


async def test_CO_039_should_set_cookies_for_a_frame(
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


async def test_CO_040_should_allow_unnamed_cookies(
    page: Page,
    context: BrowserContext,
    server: Server,
    browser_name: str,
    platform: str,
) -> None:
    def handler(request: TestServerRequest) -> None:
        request.write((request.getHeader("cookie") or "undefined-on-server").encode())
        request.finish()

    server.set_route("/cookies", handler)
    await context.add_cookies(
        [{"url": server.EMPTY_PAGE, "name": "", "value": "unnamed-via-add-cookies"}]
    )
    # Round-trip behavior
    resp = await page.goto(server.PREFIX + "/cookies")
    assert resp
    if browser_name == "webkit" and platform == "darwin":
        assert await resp.text() == "undefined-on-server"
        assert await page.evaluate("document.cookie") == ""
    else:
        assert await resp.text() == "unnamed-via-add-cookies"
        assert await page.evaluate("document.cookie") == "unnamed-via-add-cookies"
    # Within PW behavior
    await page.goto(server.EMPTY_PAGE)
    await page.evaluate("() => document.cookie = '=unnamed-via-js;'")
    await context.add_cookies(cast(Any, await context.cookies()))
    if browser_name == "webkit" and platform == "darwin":
        assert await page.evaluate("document.cookie") == ""
    else:
        assert await page.evaluate("document.cookie") == "unnamed-via-js"


async def test_CO_041_should_set_secure_cookies_on_secure_web_socket(
    context_factory: Callable[..., Awaitable[BrowserContext]],
    https_server: Server,
) -> None:
    received_web_socket_headers: List[Dict[str, str]] = []

    def on_connection(ws: WebSocketProtocol) -> None:
        received_web_socket_headers.append(ws.http_headers)

    https_server.once_web_socket_connection(on_connection)
    context = await context_factory(ignore_https_errors=True)
    page = await context.new_page()
    await page.goto(https_server.EMPTY_PAGE)
    await context.add_cookies(
        [
            {
                "domain": urlparse(https_server.PREFIX).hostname,
                "path": "/",
                "name": "foo",
                "value": "bar",
                "secure": True,
            }
        ]
    )
    await page.evaluate(
        "hostname => new WebSocket(`wss://${hostname}/ws`)", https_server.HOST
    )
    while not received_web_socket_headers:
        await page.wait_for_timeout(50)
    headers = received_web_socket_headers[0]
    assert headers.get("cookie") == "foo=bar"
