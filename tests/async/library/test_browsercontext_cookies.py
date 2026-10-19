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

"""Port of tests/library/browsercontext-cookies.spec.ts."""

import datetime
import re
import time
from typing import Any, Dict, List, Optional, Sequence

import pytest

from playwright.async_api import BrowserContext, Error, Page, Route, expect
from tests.server import Server, TestServerRequest


def expect_failure(request: pytest.FixtureRequest, reason: str) -> None:
    """Like `it.fail()`: the test must fail."""
    request.applymarker(pytest.mark.xfail(reason=f"upstream: {reason}", strict=True))


def by_name(cookies: Sequence[Any]) -> List[Dict[str, Any]]:
    """The cookies sorted by name, to compare them like a Set upstream."""
    return sorted((dict(cookie) for cookie in cookies), key=lambda c: c["name"])


def is_webkit_on_windows(
    browser_name: str, is_win: bool, browser_channel: Optional[str]
) -> bool:
    return browser_name == "webkit" and is_win and browser_channel != "webkit-wsl"


async def test_CO_001_should_return_no_cookies_in_pristine_browser_context(
    context: BrowserContext, page: Page, server: Server
) -> None:
    assert await context.cookies() == []


async def test_CO_002_should_get_a_cookie_smoke(
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
            "domain": server.HOSTNAME,
            "path": "/",
            "expires": -1,
            "httpOnly": False,
            "secure": False,
            "sameSite": default_same_site_cookie_value,
        }
    ]


async def test_CO_003_should_get_a_non_session_cookie(
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
    assert len(cookies) == 1
    # We will check expires separately.
    assert isinstance(cookies[0]["expires"], (int, float))
    assert {**cookies[0], "expires": None} == {
        "name": "username",
        "value": "John Doe",
        "domain": server.HOSTNAME,
        "path": "/",
        "expires": None,
        "httpOnly": False,
        "secure": False,
        "sameSite": default_same_site_cookie_value,
    }
    # Browsers start to cap cookies with 400 days max expires value.
    # See https://github.com/httpwg/http-extensions/pull/1732
    # Chromium patch: https://chromium.googlesource.com/chromium/src/+/aaa5d2b55478eac2ee642653dcd77a50ac3faff6
    # We want to make sure that expires date is at least 400 days in future.
    four_hundred_days = 1000 * 60 * 60 * 24 * 400
    # Relax condition a bit to make sure test is not flaky.
    five_minutes = 1000 * 60 * 5
    assert (
        cookies[0]["expires"]
        > (time.time() * 1000 + four_hundred_days - five_minutes) / 1000
    )


async def test_CO_004_should_allow_adding_cookies_with_400_days_expiration(
    context: BrowserContext, server: Server
) -> None:
    # Browsers start to cap cookies with 400 days max expires value.
    # See https://github.com/httpwg/http-extensions/pull/1732
    # Chromium patch: https://chromium.googlesource.com/chromium/src/+/aaa5d2b55478eac2ee642653dcd77a50ac3faff6
    expire = time.time() + 401 * 24 * 3600
    await context.add_cookies(
        [
            {
                "name": "username",
                "value": "John Doe",
                "domain": server.HOSTNAME,
                "path": "/",
                "expires": expire,
                "httpOnly": False,
                "secure": False,
                "sameSite": "Lax",
            }
        ]
    )

    cookies = await context.cookies()
    assert len(cookies) == 1
    assert cookies[0]["name"] == "username"
    assert cookies[0]["value"] == "John Doe"
    assert cookies[0]["domain"] == server.HOSTNAME
    assert cookies[0]["path"] == "/"
    assert cookies[0]["expires"] > 0
    assert cookies[0]["expires"] <= expire


async def test_CO_005_should_properly_report_http_only_cookie(
    context: BrowserContext, page: Page, server: Server
) -> None:
    def handler(request: TestServerRequest) -> None:
        request.setHeader("Set-Cookie", "name=value;HttpOnly; Path=/")
        request.finish()

    server.set_route("/empty.html", handler)
    await page.goto(server.EMPTY_PAGE)
    cookies = await context.cookies()
    assert len(cookies) == 1
    assert cookies[0]["httpOnly"] is True


async def test_CO_006_should_properly_report_strict_same_site_cookie(
    context: BrowserContext,
    page: Page,
    server: Server,
    browser_name: str,
    platform: str,
    browser_channel: Optional[str],
    request: pytest.FixtureRequest,
) -> None:
    if (
        browser_name == "webkit"
        and platform == "win32"
        and browser_channel != "webkit-wsl"
    ):
        expect_failure(request, "webkit on win32")

    def handler(request: TestServerRequest) -> None:
        request.setHeader("Set-Cookie", "name=value;SameSite=Strict")
        request.finish()

    server.set_route("/empty.html", handler)
    await page.goto(server.EMPTY_PAGE)
    cookies = await context.cookies()
    assert len(cookies) == 1
    assert cookies[0]["sameSite"] == "Strict"


async def test_CO_007_should_properly_report_lax_same_site_cookie(
    context: BrowserContext,
    page: Page,
    server: Server,
    browser_name: str,
    platform: str,
    browser_channel: Optional[str],
    request: pytest.FixtureRequest,
) -> None:
    if (
        browser_name == "webkit"
        and platform == "win32"
        and browser_channel != "webkit-wsl"
    ):
        expect_failure(request, "webkit on win32")

    def handler(request: TestServerRequest) -> None:
        request.setHeader("Set-Cookie", "name=value;SameSite=Lax")
        request.finish()

    server.set_route("/empty.html", handler)
    await page.goto(server.EMPTY_PAGE)
    cookies = await context.cookies()
    assert len(cookies) == 1
    assert cookies[0]["sameSite"] == "Lax"


async def test_CO_008_should_get_multiple_cookies(
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
    cookies = by_name(await context.cookies())
    assert document_cookie == "password=1234; username=John Doe"
    assert cookies == [
        {
            "name": "password",
            "value": "1234",
            "domain": server.HOSTNAME,
            "path": "/",
            "expires": -1,
            "httpOnly": False,
            "secure": False,
            "sameSite": default_same_site_cookie_value,
        },
        {
            "name": "username",
            "value": "John Doe",
            "domain": server.HOSTNAME,
            "path": "/",
            "expires": -1,
            "httpOnly": False,
            "secure": False,
            "sameSite": default_same_site_cookie_value,
        },
    ]


async def test_CO_009_should_get_cookies_from_multiple_urls(
    context: BrowserContext,
    browser_name: str,
    is_win: bool,
    browser_channel: Optional[str],
) -> None:
    await context.add_cookies(
        [
            {
                "url": "https://foo.com",
                "name": "doggo",
                "value": "woofs",
                "sameSite": "None",
            },
            {
                "url": "https://bar.com",
                "name": "catto",
                "value": "purrs",
                "sameSite": "Lax",
            },
            {
                "url": "https://baz.com",
                "name": "birdo",
                "value": "tweets",
                "sameSite": "Lax",
            },
        ]
    )
    cookies = by_name(await context.cookies(["https://foo.com", "https://baz.com"]))
    assert cookies == [
        {
            "name": "birdo",
            "value": "tweets",
            "domain": "baz.com",
            "path": "/",
            "expires": -1,
            "httpOnly": False,
            "secure": True,
            "sameSite": (
                "None"
                if is_webkit_on_windows(browser_name, is_win, browser_channel)
                else "Lax"
            ),
        },
        {
            "name": "doggo",
            "value": "woofs",
            "domain": "foo.com",
            "path": "/",
            "expires": -1,
            "httpOnly": False,
            "secure": True,
            "sameSite": "None",
        },
    ]


async def test_CO_010_should_work_with_subdomain_cookie(
    context: BrowserContext,
    browser_name: str,
    is_win: bool,
    browser_channel: Optional[str],
) -> None:
    await context.add_cookies(
        [
            {
                "domain": ".foo.com",
                "path": "/",
                "name": "doggo",
                "value": "woofs",
                "sameSite": "Lax",
                "secure": True,
            }
        ]
    )
    same_site = (
        "None" if is_webkit_on_windows(browser_name, is_win, browser_channel) else "Lax"
    )
    assert await context.cookies("https://foo.com") == [
        {
            "name": "doggo",
            "value": "woofs",
            "domain": ".foo.com",
            "path": "/",
            "expires": -1,
            "httpOnly": False,
            "secure": True,
            "sameSite": same_site,
        }
    ]
    assert await context.cookies("https://sub.foo.com") == [
        {
            "name": "doggo",
            "value": "woofs",
            "domain": ".foo.com",
            "path": "/",
            "expires": -1,
            "httpOnly": False,
            "secure": True,
            "sameSite": same_site,
        }
    ]


async def test_CO_011_should_only_return_cookies_that_apply_to_the_url(
    context: BrowserContext,
) -> None:
    await context.add_cookies(
        [
            {"name": "hostonly", "value": "v", "domain": "foo.com", "path": "/api"},
            {"name": "subdomains", "value": "v", "domain": ".foo.com", "path": "/api"},
            {"name": "slash", "value": "v", "domain": "foo.com", "path": "/foo/"},
        ]
    )

    async def names(url: str) -> List[str]:
        return sorted(cookie["name"] for cookie in await context.cookies(url))

    assert await names("http://foo.com/api") == ["hostonly", "subdomains"]
    assert await names("http://foo.com/api/x") == ["hostonly", "subdomains"]
    assert await names("http://foo.com/apiv2") == []
    assert await names("http://sub.foo.com/api") == ["subdomains"]
    assert await names("http://notfoo.com/api") == []
    assert await names("http://foo.com/foo") == []
    assert await names("http://foo.com/foo/") == ["slash"]
    assert await names("http://foo.com/foo/bar") == ["slash"]


async def test_CO_012_should_return_cookies_with_empty_value(
    context: BrowserContext, page: Page, server: Server
) -> None:
    def handler(request: TestServerRequest) -> None:
        request.setHeader("Set-Cookie", "name=;Path=/")
        request.finish()

    server.set_route("/empty.html", handler)
    await page.goto(server.EMPTY_PAGE)
    cookies = await context.cookies()
    assert len(cookies) == 1
    assert cookies[0]["name"] == "name"
    assert cookies[0]["value"] == ""


async def test_CO_013_should_return_secure_cookies_based_on_http_s_protocol(
    context: BrowserContext,
    browser_name: str,
    is_win: bool,
    browser_channel: Optional[str],
) -> None:
    await context.add_cookies(
        [
            {
                "url": "https://foo.com",
                "name": "doggo",
                "value": "woofs",
                "sameSite": "Lax",
                "secure": True,
            },
            {
                "url": "http://foo.com",
                "name": "catto",
                "value": "purrs",
                "sameSite": "Lax",
                "secure": False,
            },
        ]
    )
    same_site = (
        "None" if is_webkit_on_windows(browser_name, is_win, browser_channel) else "Lax"
    )
    cookies = by_name(await context.cookies("https://foo.com"))
    assert cookies == [
        {
            "name": "catto",
            "value": "purrs",
            "domain": "foo.com",
            "path": "/",
            "expires": -1,
            "httpOnly": False,
            "secure": False,
            "sameSite": same_site,
        },
        {
            "name": "doggo",
            "value": "woofs",
            "domain": "foo.com",
            "path": "/",
            "expires": -1,
            "httpOnly": False,
            "secure": True,
            "sameSite": same_site,
        },
    ]
    assert await context.cookies("http://foo.com/") == [
        {
            "name": "catto",
            "value": "purrs",
            "domain": "foo.com",
            "path": "/",
            "expires": -1,
            "httpOnly": False,
            "secure": False,
            "sameSite": same_site,
        }
    ]


@pytest.mark.parametrize("host", ["127.0.0.1", "[::1]"])
async def test_CO_014_should_return_secure_cookies_for_http(
    context: BrowserContext, host: str
) -> None:
    await context.add_cookies(
        [{"name": "a", "value": "v", "domain": host, "path": "/", "secure": True}]
    )
    assert [cookie["name"] for cookie in await context.cookies(f"http://{host}/")] == [
        "a"
    ]


async def test_CO_015_should_add_cookies_with_an_expiration(
    context: BrowserContext,
) -> None:
    expires = int(time.time()) + 3600
    await context.add_cookies(
        [
            {
                "url": "https://foo.com",
                "name": "doggo",
                "value": "woofs",
                "sameSite": "None",
                "expires": expires,
            }
        ]
    )
    cookies = await context.cookies(["https://foo.com"])
    assert len(cookies) == 1
    assert cookies == [
        {
            "name": "doggo",
            "value": "woofs",
            "domain": "foo.com",
            "path": "/",
            "expires": expires,
            "httpOnly": False,
            "secure": True,
            "sameSite": "None",
        }
    ]
    # Rollover to 5-digit year
    await context.add_cookies(
        [
            {
                "url": "https://foo.com",
                "name": "doggo",
                "value": "woofs",
                "sameSite": "None",
                # Fri, 31 Dec 9999 23:59:59 +0000 (UTC)
                "expires": 253402300799,
            }
        ]
    )
    with pytest.raises(Error, match=re.compile("Cookie should have a valid expires")):
        await context.add_cookies(
            [
                {
                    "url": "https://foo.com",
                    "name": "doggo",
                    "value": "woofs",
                    "sameSite": "None",
                    # Sat,  1 Jan 1000 00:00:00 +0000 (UTC)
                    "expires": 253402300800,
                }
            ]
        )

    with pytest.raises(Error, match=re.compile("Cookie should have a valid expires")):
        await context.add_cookies(
            [
                {
                    "url": "https://foo.com",
                    "name": "doggo",
                    "value": "woofs",
                    "sameSite": "None",
                    "expires": -42,
                }
            ]
        )


async def test_CO_016_should_support_request_storage_access(
    page: Page,
    server: Server,
    browser_channel: Optional[str],
    browser_name: str,
    is_mac: bool,
    is_linux: bool,
    is_win: bool,
    mac_version: int,
) -> None:
    if browser_name == "chromium":
        pytest.skip("requestStorageAccess API is not available in Chromium")

    def handler(request: TestServerRequest) -> None:
        request.setHeader("Set-Cookie", "name=value; Path=/")
        request.finish()

    server.set_route("/set-cookie.html", handler)
    # Navigate once to the domain as top level.
    await page.goto(server.CROSS_PROCESS_PREFIX + "/set-cookie.html")
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        f'<iframe src="{server.CROSS_PROCESS_PREFIX + "/empty.html"}"></iframe>'
    )

    frame = page.frames[1]
    if browser_name == "firefox":
        assert await frame.evaluate("() => document.hasStorageAccess()")
        with server.expect_request("/title.html") as server_request_info:
            await frame.evaluate("() => fetch('/title.html')")
        assert server_request_info.value.getHeader("cookie") == "name=value"
    else:
        if browser_name == "webkit" and (is_linux or browser_channel == "webkit-wsl"):
            assert await frame.evaluate("() => document.hasStorageAccess()")
        else:
            assert not await frame.evaluate("() => document.hasStorageAccess()")
        with server.expect_request("/title.html") as server_request_info:
            await frame.evaluate("() => fetch('/title.html')")
        if is_win and browser_name == "webkit" and browser_channel != "webkit-wsl":
            assert server_request_info.value.getHeader("cookie") == "name=value"
        else:
            assert not server_request_info.value.getHeader("cookie")
        assert await frame.evaluate(
            "() => document.requestStorageAccess().then(() => true, e => false)"
        )
        assert await frame.evaluate("() => document.hasStorageAccess()")
        with server.expect_request("/title.html") as server_request_info:
            await frame.evaluate("() => fetch('/title.html')")
        if browser_name == "webkit" and (is_linux or browser_channel == "webkit-wsl"):
            assert server_request_info.value.getHeader("cookie") is None
        else:
            assert server_request_info.value.getHeader("cookie") == "name=value"


async def test_CO_017_should_parse_cookie_with_large_max_age_correctly(
    server: Server,
    page: Page,
    default_same_site_cookie_value: str,
    browser_name: str,
    platform: str,
) -> None:
    def handler(request: TestServerRequest) -> None:
        request.setHeader(
            "set-cookie",
            "cookie1=value1; Path=/; Expires=Thu, 08 Sep 2270 15:06:12 GMT; "
            "Max-Age=7776000000",
        )
        request.setResponseCode(200)
        request.finish()

    server.set_route("/foobar", handler)
    await page.goto(server.PREFIX + "/foobar")
    assert await page.evaluate("() => document.cookie") == "cookie1=value1"
    cookies = await page.context.cookies()
    assert len(cookies) == 1
    assert isinstance(cookies[0]["expires"], (int, float))
    assert {**cookies[0], "expires": None} == {
        "name": "cookie1",
        "value": "value1",
        "domain": server.HOSTNAME,
        "path": "/",
        "expires": None,
        "httpOnly": False,
        "secure": False,
        "sameSite": default_same_site_cookie_value,
    }


async def test_CO_018_iframe_should_inherit_cookies_from_parent(
    page: Page, is_linux: bool, browser_name: str
) -> None:
    async def handle(route: Route) -> None:
        if "sub.example.test" in route.request.url:
            await route.fulfill(
                body="""
                    <p id="result"></p>
                    <script>document.getElementById('result').textContent = document.cookie || 'no cookies';</script>
                """,
                content_type="text/html",
            )
            return
        await route.fulfill(
            headers={
                "set-cookie": "testCookie=value; SameSite=Lax; Domain=example.test"
            },
            content_type="text/html",
            body="""
                <p id="result"></p>
                <script>document.getElementById('result').textContent = document.cookie || 'no cookies';</script>
                <iframe src="http://sub.example.test"></iframe>
            """,
        )

    await page.route("**/*", handle)

    await page.goto("http://example.test")

    await expect(page.locator("body")).to_contain_text("testCookie=value")
    await expect(page.frame_locator("iframe").locator("body")).to_contain_text(
        "testCookie=value"
    )
