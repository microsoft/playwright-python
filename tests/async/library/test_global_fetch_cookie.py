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

"""Port of tests/library/global-fetch-cookie.spec.ts.

Upstream passes { __testHookLookup } to some requests, so that host names such as
a.b.one.com resolve to 127.0.0.1. Those tests use the lookup_request_context fixture
instead: its requests go through tests/helpers/lookup_proxy.py, which resolves the
host names in the same way.
"""

import json
import re
import time
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Callable, Generator, List, Optional

import pytest

from playwright.async_api import (
    APIRequestContext,
    Error,
    Playwright,
    StorageState,
    expect,
)
from tests.helpers.lookup_proxy import LookupProxy
from tests.server import Server, TestServerRequest


@pytest.fixture
async def request_context(
    playwright: Playwright,
) -> AsyncGenerator[APIRequestContext, None]:
    """Port of the `request` fixture (pytest reserves the name `request`)."""
    request = await playwright.request.new_context(ignore_https_errors=True)
    yield request
    await request.dispose()


@pytest.fixture
def lookup_proxy() -> Generator[LookupProxy, None, None]:
    proxy = LookupProxy()
    yield proxy
    proxy.close()


@pytest.fixture
async def lookup_request_context(
    playwright: Playwright, lookup_proxy: LookupProxy
) -> AsyncGenerator[APIRequestContext, None]:
    """The `request` fixture, for tests whose requests pass { __testHookLookup }."""
    request = await playwright.request.new_context(
        ignore_https_errors=True, proxy=lookup_proxy.settings
    )
    yield request
    await request.dispose()


def set_cookie_route(
    server: Server, path: str, cookies: Callable[[], List[str]]
) -> None:
    """Port of a route that does res.setHeader('Set-Cookie', cookies); res.end()."""

    def handler(request: TestServerRequest) -> None:
        request.responseHeaders.setRawHeaders("Set-Cookie", cookies())
        request.finish()

    server.set_route(path, handler)


def utc_string(date: datetime) -> str:
    """Port of Date.prototype.toUTCString()."""
    return format_datetime(date.astimezone(timezone.utc), usegmt=True)


async def test_FE_054_should_store_cookie_from_set_cookie_header(
    lookup_request_context: APIRequestContext, server: Server
) -> None:
    request = lookup_request_context
    set_cookie_route(
        server,
        "/setcookie.html",
        lambda: [
            "a=b",
            "c=d; max-age=3600; domain=b.one.com; path=/input",
            "e=f; domain=b.one.com; path=/input/subfolder",
        ],
    )
    await request.get(f"http://a.b.one.com:{server.PORT}/setcookie.html")
    with server.expect_request("/input/button.html") as server_request_info:
        await request.get(f"http://b.one.com:{server.PORT}/input/button.html")
    assert server_request_info.value.getHeader("cookie") == "c=d"


async def test_FE_055_add_cookies_should_add_cookies_to_the_cookie_jar(
    request_context: APIRequestContext, server: Server
) -> None:
    request = request_context
    await request.add_cookies(
        [
            {"name": "a", "value": "b", "url": server.EMPTY_PAGE},
            {
                "name": "c",
                "value": "d",
                "domain": "localhost",
                "path": "/input",
                "httpOnly": True,
                "sameSite": "Strict",
            },
            {"name": "e", "value": "f", "domain": "other.com", "path": "/"},
        ]
    )
    with server.expect_request("/input/button.html") as server_request_info:
        await request.get(f"{server.PREFIX}/input/button.html")
    assert server_request_info.value.getHeader("cookie") == "a=b; c=d"
    state = await request.storage_state()
    assert state["cookies"] == [
        {
            "name": "a",
            "value": "b",
            "domain": "localhost",
            "path": "/",
            "expires": -1,
            "httpOnly": False,
            "secure": False,
            "sameSite": "Lax",
        },
        {
            "name": "c",
            "value": "d",
            "domain": "localhost",
            "path": "/input",
            "expires": -1,
            "httpOnly": True,
            "secure": False,
            "sameSite": "Strict",
        },
        {
            "name": "e",
            "value": "f",
            "domain": "other.com",
            "path": "/",
            "expires": -1,
            "httpOnly": False,
            "secure": False,
            "sameSite": "Lax",
        },
    ]


async def test_FE_056_add_cookies_should_validate_cookies(
    request_context: APIRequestContext,
) -> None:
    request = request_context
    with pytest.raises(Error) as exc_info:
        await request.add_cookies([{"name": "a", "value": "b"}])
    assert "Cookie should have a url or a domain/path pair" in exc_info.value.message


async def test_FE_057_cookies_should_return_cookies_filtered_by_urls(
    request_context: APIRequestContext, server: Server
) -> None:
    request = request_context
    await request.add_cookies(
        [
            {"name": "a", "value": "b", "domain": "localhost", "path": "/"},
            {"name": "c", "value": "d", "domain": "localhost", "path": "/input"},
            {"name": "e", "value": "f", "domain": ".one.com", "path": "/"},
            {
                "name": "g",
                "value": "h",
                "domain": "two.com",
                "path": "/",
                "secure": True,
            },
        ]
    )
    assert [c["name"] for c in await request.cookies()] == ["a", "c", "e", "g"]
    assert [c["name"] for c in await request.cookies(server.EMPTY_PAGE)] == ["a"]
    assert [
        c["name"] for c in await request.cookies(f"{server.PREFIX}/input/button.html")
    ] == ["a", "c"]
    assert [
        c["name"]
        for c in await request.cookies(["http://sub.one.com/", "http://two.com/"])
    ] == ["e"]
    assert [
        c["name"]
        for c in await request.cookies(["http://sub.one.com/", "https://two.com/"])
    ] == ["e", "g"]
    assert await request.cookies("http://other.com/") == []


async def test_FE_058_cookies_should_only_return_cookies_that_apply_to_the_url(
    request_context: APIRequestContext,
) -> None:
    # https://github.com/microsoft/playwright/issues/43078
    request = request_context
    await request.add_cookies(
        [
            {"name": "hostonly", "value": "v", "domain": "one.com", "path": "/api"},
            {"name": "subdomains", "value": "v", "domain": ".one.com", "path": "/api"},
            {"name": "slash", "value": "v", "domain": "one.com", "path": "/foo/"},
        ]
    )

    async def names(url: str) -> List[str]:
        return [c["name"] for c in await request.cookies(url)]

    assert await names("http://one.com/api") == ["hostonly", "subdomains"]
    assert await names("http://one.com/api/x") == ["hostonly", "subdomains"]
    assert await names("http://one.com/apiv2") == []
    assert await names("http://sub.one.com/api") == ["subdomains"]
    assert await names("http://notone.com/api") == []
    assert await names("http://one.com/foo") == []
    assert await names("http://one.com/foo/") == ["slash"]
    assert await names("http://one.com/foo/bar") == ["slash"]


async def test_FE_059_should_only_send_cookies_that_apply_to_the_url(
    lookup_request_context: APIRequestContext, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/43078
    request = lookup_request_context
    set_cookie_route(
        server,
        "/setcookie.html",
        lambda: [
            "hostonly=v; path=/api",
            "subdomains=v; domain=one.com; path=/api",
            "slash=v; path=/foo/",
        ],
    )
    await request.get(f"http://one.com:{server.PORT}/setcookie.html")

    async def sent(host: str, path: str) -> Optional[str]:
        with server.expect_request(path) as server_request_info:
            await request.get(f"http://{host}:{server.PORT}{path}")
        return server_request_info.value.getHeader("cookie")

    assert await sent("one.com", "/api") == "hostonly=v; subdomains=v"
    assert await sent("one.com", "/api/x") == "hostonly=v; subdomains=v"
    assert await sent("one.com", "/apiv2") is None
    assert await sent("sub.one.com", "/api") == "subdomains=v"
    assert await sent("one.com", "/foo") is None
    assert await sent("one.com", "/foo/") == "slash=v"
    assert await sent("one.com", "/foo/bar") == "slash=v"


async def test_FE_060_cookies_should_include_cookies_from_set_cookie_header(
    request_context: APIRequestContext, server: Server
) -> None:
    request = request_context
    set_cookie_route(
        server,
        "/setcookie.html",
        lambda: ["a=b; HttpOnly; SameSite=Strict", "c=d; path=/input"],
    )
    await request.get(f"{server.PREFIX}/setcookie.html")
    assert await request.cookies() == [
        {
            "name": "a",
            "value": "b",
            "domain": "localhost",
            "path": "/",
            "expires": -1,
            "httpOnly": True,
            "secure": False,
            "sameSite": "Strict",
        },
        {
            "name": "c",
            "value": "d",
            "domain": "localhost",
            "path": "/input",
            "expires": -1,
            "httpOnly": False,
            "secure": False,
            "sameSite": "Lax",
        },
    ]


async def test_FE_061_clear_cookies_should_remove_all_cookies(
    request_context: APIRequestContext, server: Server
) -> None:
    request = request_context
    await request.add_cookies(
        [
            {"name": "a", "value": "b", "url": server.EMPTY_PAGE},
            {"name": "c", "value": "d", "domain": "one.com", "path": "/"},
        ]
    )
    await request.clear_cookies()
    assert await request.cookies() == []
    with server.expect_request("/empty.html") as server_request_info:
        await request.get(server.EMPTY_PAGE)
    assert server_request_info.value.getHeader("cookie") is None


async def test_FE_062_clear_cookies_should_filter_by_name_domain_and_path(
    request_context: APIRequestContext,
) -> None:
    request = request_context
    await request.add_cookies(
        [
            {"name": "session", "value": "1", "domain": "one.com", "path": "/"},
            {"name": "session", "value": "2", "domain": "two.com", "path": "/"},
            {"name": "session", "value": "3", "domain": "two.com", "path": "/api"},
            {"name": "other", "value": "4", "domain": "one.com", "path": "/"},
        ]
    )

    async def values() -> List[str]:
        return sorted(c["value"] for c in await request.cookies())

    await request.clear_cookies(name="session", domain="two.com", path="/api")
    assert await values() == ["1", "2", "4"]

    await request.clear_cookies(domain=re.compile(r"one\.com$"))
    assert await values() == ["2"]

    await request.clear_cookies(name=re.compile(r"^sess"))
    assert await values() == []


async def test_FE_063_clear_cookies_should_remove_nameless_cookies_by_empty_name(
    request_context: APIRequestContext,
) -> None:
    # https://github.com/microsoft/playwright/issues/43112
    request = request_context
    await request.add_cookies(
        [
            {"name": "", "value": "nameless", "domain": "one.com", "path": "/"},
            {"name": "session", "value": "secret", "domain": "one.com", "path": "/"},
        ]
    )
    await request.clear_cookies(name="")
    assert [c["name"] for c in await request.cookies()] == ["session"]


async def test_FE_064_should_send_nameless_cookies_as_value_only(
    request_context: APIRequestContext, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/43155
    request = request_context
    await request.add_cookies(
        [
            {"name": "", "value": "nameless", "url": server.EMPTY_PAGE},
            {"name": "a", "value": "b", "url": server.EMPTY_PAGE},
        ]
    )
    with server.expect_request("/empty.html") as server_request_info:
        await request.get(server.EMPTY_PAGE)
    assert server_request_info.value.getHeader("cookie") == "nameless; a=b"


async def test_FE_065_should_store_set_cookie_without_equals_sign_as_nameless_cookie(
    request_context: APIRequestContext, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/43155
    request = request_context
    set_cookie_route(server, "/setcookie.html", lambda: ["token; path=/", "a=; path=/"])
    await request.get(f"{server.PREFIX}/setcookie.html")
    assert [
        {"name": c["name"], "value": c["value"]} for c in await request.cookies()
    ] == [
        {"name": "", "value": "token"},
        {"name": "a", "value": ""},
    ]
    with server.expect_request("/empty.html") as server_request_info:
        await request.get(server.EMPTY_PAGE)
    assert server_request_info.value.getHeader("cookie") == "token; a="


async def test_FE_066_should_filter_outgoing_cookies_by_path(
    request_context: APIRequestContext, server: Server
) -> None:
    request = request_context
    set_cookie_route(
        server,
        "/setcookie.html",
        lambda: ["a=v; path=/input/subfolder", "b=v; path=/input", "c=v;"],
    )
    await request.get(f"{server.PREFIX}/setcookie.html")
    with server.expect_request("/input/button.html") as server_request_info:
        await request.get(f"{server.PREFIX}/input/button.html")
    assert server_request_info.value.getHeader("cookie") == "b=v; c=v"


async def test_FE_067_should_filter_outgoing_cookies_by_domain(
    lookup_request_context: APIRequestContext, server: Server
) -> None:
    request = lookup_request_context
    set_cookie_route(
        server,
        "/setcookie.html",
        lambda: [
            "a=v; domain=one.com",
            "b=v; domain=.b.one.com",
            "c=v; domain=other.com",
        ],
    )
    await request.get(f"http://a.b.one.com:{server.PORT}/setcookie.html")
    with server.expect_request("/empty.html") as server_request_info:
        await request.get(f"http://www.b.one.com:{server.PORT}/empty.html")
    assert server_request_info.value.getHeader("cookie") == "a=v; b=v"

    with server.expect_request("/empty.html") as server_request2_info:
        await request.get(f"http://two.com:{server.PORT}/empty.html")
    assert not server_request2_info.value.getHeader("cookie")


async def test_FE_068_should_do_case_insensitive_match_of_cookie_domain(
    lookup_request_context: APIRequestContext, server: Server
) -> None:
    request = lookup_request_context
    set_cookie_route(
        server,
        "/setcookie.html",
        lambda: ["a=v; domain=One.com", "b=v; domain=.B.oNe.com"],
    )
    await request.get(f"http://a.b.one.com:{server.PORT}/setcookie.html")
    with server.expect_request("/empty.html") as server_request_info:
        await request.get(f"http://www.b.one.com:{server.PORT}/empty.html")
    assert server_request_info.value.getHeader("cookie") == "a=v; b=v"


async def test_FE_069_should_do_case_insensitive_match_of_request_domain(
    lookup_request_context: APIRequestContext, server: Server
) -> None:
    request = lookup_request_context
    set_cookie_route(
        server,
        "/setcookie.html",
        lambda: ["a=v; domain=one.com", "b=v; domain=.b.one.com"],
    )
    await request.get(f"http://a.b.one.com:{server.PORT}/setcookie.html")
    with server.expect_request("/empty.html") as server_request_info:
        await request.get(f"http://WWW.B.ONE.COM:{server.PORT}/empty.html")
    assert server_request_info.value.getHeader("cookie") == "a=v; b=v"


async def test_FE_070_should_send_secure_cookie_over_https(
    request_context: APIRequestContext, server: Server, https_server: Server
) -> None:
    request = request_context
    set_cookie_route(server, "/setcookie.html", lambda: ["a=v; secure", "b=v"])
    await request.get(f"{server.PREFIX}/setcookie.html")
    with https_server.expect_request("/empty.html") as server_request_info:
        await request.get(https_server.EMPTY_PAGE)
    assert server_request_info.value.getHeader("cookie") == "a=v; b=v"


async def test_FE_071_should_send_secure_cookie_over_http_for_localhost(
    request_context: APIRequestContext, server: Server
) -> None:
    request = request_context
    set_cookie_route(server, "/setcookie.html", lambda: ["a=v; secure", "b=v"])
    await request.get(f"{server.PREFIX}/setcookie.html")
    with server.expect_request("/empty.html") as server_request_info:
        await request.get(server.EMPTY_PAGE)
    assert server_request_info.value.getHeader("cookie") == "a=v; b=v"


async def test_FE_072_should_send_secure_cookie_over_http_for_subdomains_of_localhost(
    lookup_request_context: APIRequestContext, server: Server
) -> None:
    request = lookup_request_context
    set_cookie_route(server, "/setcookie.html", lambda: ["a=v; secure", "b=v"])
    prefix = f"http://a.b.localhost:{server.PORT}"
    await request.get(f"{prefix}/setcookie.html")
    with server.expect_request("/empty.html") as server_request_info:
        await request.get(f"{prefix}/empty.html")
    assert server_request_info.value.getHeader("cookie") == "a=v; b=v"


@pytest.mark.parametrize("host", ["127.0.0.1", "[::1]"])
async def test_FE_073_should_send_secure_cookie_over_http_for(
    request_context: APIRequestContext, server: Server, host: str
) -> None:
    # https://github.com/microsoft/playwright/issues/43115
    request = request_context
    set_cookie_route(server, "/setcookie.html", lambda: ["a=v; secure", "b=v"])
    prefix = f"http://{host}:{server.PORT}"
    await request.get(f"{prefix}/setcookie.html")
    with server.expect_request("/empty.html") as server_request_info:
        await request.get(f"{prefix}/empty.html")
    assert server_request_info.value.getHeader("cookie") == "a=v; b=v"
    assert [c["name"] for c in await request.cookies(f"{prefix}/")] == ["a", "b"]


async def test_FE_074_should_send_not_expired_cookies(
    request_context: APIRequestContext, server: Server
) -> None:
    request = request_context

    def cookies() -> List[str]:
        tomorrow = datetime.now() + timedelta(days=1)
        return ["a=v", f"b=v; expires={utc_string(tomorrow)}"]

    set_cookie_route(server, "/setcookie.html", cookies)
    await request.get(f"{server.PREFIX}/setcookie.html")
    with server.expect_request("/empty.html") as server_request_info:
        await request.get(server.EMPTY_PAGE)
    assert server_request_info.value.getHeader("cookie") == "a=v; b=v"


async def test_FE_075_should_remove_expired_cookies(
    request_context: APIRequestContext, server: Server
) -> None:
    request = request_context
    set_cookie_route(
        server,
        "/setcookie.html",
        lambda: ["a=v", f"b=v; expires={utc_string(datetime.now())}"],
    )
    await request.get(f"{server.PREFIX}/setcookie.html")
    with server.expect_request("/empty.html") as server_request_info:
        await request.get(server.EMPTY_PAGE)
    assert server_request_info.value.getHeader("cookie") == "a=v"


async def test_FE_076_should_remove_cookie_with_negative_max_age(
    request_context: APIRequestContext, server: Server
) -> None:
    request = request_context
    set_cookie_route(
        server,
        "/setcookie.html",
        lambda: ["a=v; max-age=100000", "b=v; max-age=100000", "c=v"],
    )

    def remove_cookies() -> List[str]:
        max_age = -2 * int(time.time() * 1000)
        return [f"a=v; max-age={max_age}", "b=v; max-age=-1"]

    set_cookie_route(server, "/removecookie.html", remove_cookies)
    await request.get(f"{server.PREFIX}/setcookie.html")
    await request.get(f"{server.PREFIX}/removecookie.html")
    with server.expect_request("/empty.html") as server_request_info:
        await request.get(server.EMPTY_PAGE)
    assert server_request_info.value.getHeader("cookie") == "c=v"


async def test_FE_077_should_prefer_max_age_over_expires_regardless_of_the_order(
    request_context: APIRequestContext, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/43077
    request = request_context
    past = "Thu, 01 Jan 1970 00:00:00 GMT"
    future = utc_string(datetime.now() + timedelta(seconds=3600))
    set_cookie_route(
        server,
        "/setcookie.html",
        lambda: [
            f"a=v; max-age=3600; expires={past}",
            f"b=v; expires={past}; max-age=3600",
            f"c=v; max-age=-1; expires={future}",
            f"d=v; expires={future}; max-age=-1",
        ],
    )
    await request.get(f"{server.PREFIX}/setcookie.html")
    with server.expect_request("/empty.html") as server_request_info:
        await request.get(server.EMPTY_PAGE)
    assert server_request_info.value.getHeader("cookie") == "a=v; b=v"


async def test_FE_078_should_ignore_max_age_that_is_not_a_number(
    request_context: APIRequestContext, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/43077
    request = request_context
    set_cookie_route(
        server,
        "/setcookie.html",
        lambda: ["a=v; max-age=-1abc", "b=v; max-age=3600abc", "c=v; max-age="],
    )
    await request.get(f"{server.PREFIX}/setcookie.html")
    with server.expect_request("/empty.html") as server_request_info:
        await request.get(server.EMPTY_PAGE)
    assert server_request_info.value.getHeader("cookie") == "a=v; b=v; c=v"
    cookies = (await request.storage_state())["cookies"]
    assert [c["expires"] for c in cookies] == [-1, -1, -1]


async def test_FE_079_should_remove_cookie_with_expires_far_in_the_past(
    request_context: APIRequestContext, server: Server
) -> None:
    request = request_context
    set_cookie_route(server, "/setcookie.html", lambda: ["a=v; max-age=1000000"])
    set_cookie_route(
        server,
        "/removecookie.html",
        lambda: ["a=v; expires=1 Jan 1000 00:00:00 +0000 (UTC)"],
    )
    await request.get(f"{server.PREFIX}/setcookie.html")
    await request.get(f"{server.PREFIX}/removecookie.html")
    with server.expect_request("/empty.html") as server_request_info:
        await request.get(server.EMPTY_PAGE)
    assert not server_request_info.value.getHeader("cookie")


async def test_FE_080_should_store_cookie_from_set_cookie_header_even_if_it_contains_equal_signs(
    lookup_request_context: APIRequestContext, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/11612
    request = lookup_request_context
    set_cookie_route(
        server,
        "/setcookie.html",
        lambda: ["f=value == value=; secure; httpOnly; path=/some=value"],
    )

    await request.get(f"http://a.b.one.com:{server.PORT}/setcookie.html")
    state = await request.storage_state()
    assert state == {
        "cookies": [
            {
                "domain": "a.b.one.com",
                "expires": -1,
                "name": "f",
                "path": "/some=value",
                "sameSite": "Lax",
                "httpOnly": True,
                "secure": True,
                "value": "value == value=",
            }
        ],
        "origins": [],
    }


async def test_FE_081_should_override_cookie_from_set_cookie_header(
    request_context: APIRequestContext, server: Server
) -> None:
    request = request_context
    tomorrow = datetime.now() + timedelta(days=1)
    set_cookie_route(
        server,
        "/setcookie.html",
        lambda: [f"a=old; expires={utc_string(tomorrow)}"],
    )

    day_after_tomorrow = tomorrow + timedelta(days=1)
    day_after_tomorrow_in_seconds = int(day_after_tomorrow.timestamp())
    set_cookie_route(
        server,
        "/updatecookie.html",
        lambda: [f"a=new; expires={utc_string(day_after_tomorrow)}"],
    )

    await request.get(f"{server.PREFIX}/setcookie.html")
    await request.get(f"{server.PREFIX}/updatecookie.html")

    state = await request.storage_state()

    assert len(state["cookies"]) == 1
    assert state["cookies"][0]["name"] == "a"
    assert state["cookies"][0]["value"] == "new"
    assert state["cookies"][0]["expires"] == day_after_tomorrow_in_seconds


async def test_FE_082_should_override_cookie_from_set_cookie_header_even_if_it_expired(
    request_context: APIRequestContext, server: Server
) -> None:
    request = request_context
    tomorrow = datetime.now() + timedelta(days=1)
    set_cookie_route(
        server,
        "/setcookie.html",
        lambda: ["a=ok", f"b=ok; expires={utc_string(tomorrow)}"],
    )

    def unset_cookies() -> List[str]:
        # Port of new Date(1970, 0, 1, 0, 0, 0, 0): midnight in the local time zone.
        past_date_string = utc_string(datetime(1970, 1, 1).astimezone())
        return [f"a=; expires={past_date_string}", f"b=; expires={past_date_string}"]

    set_cookie_route(server, "/unsetsetcookie.html", unset_cookies)

    await request.get(f"{server.PREFIX}/setcookie.html")
    await request.get(f"{server.PREFIX}/unsetsetcookie.html")

    with server.expect_request("/empty.html") as server_request_info:
        await request.get(server.EMPTY_PAGE)

    assert not server_request_info.value.getHeader("cookie")


async def test_FE_083_should_export_cookies_to_storage_state(
    lookup_request_context: APIRequestContext, server: Server
) -> None:
    request = lookup_request_context
    # Port of new Date('12/31/2100 PST').
    expires = datetime(2100, 12, 31, 8, 0, 0, tzinfo=timezone.utc)
    set_cookie_route(
        server,
        "/setcookie.html",
        lambda: [
            "a=b",
            f"c=d; expires={utc_string(expires)}; domain=b.one.com; path=/input",
            "e=f; domain=b.one.com; path=/input/subfolder",
        ],
    )
    await request.get(f"http://a.b.one.com:{server.PORT}/setcookie.html")
    state = await request.storage_state()
    assert state == {
        "cookies": [
            {
                "name": "a",
                "value": "b",
                "domain": "a.b.one.com",
                "path": "/",
                "expires": -1,
                "httpOnly": False,
                "secure": False,
                "sameSite": "Lax",
            },
            {
                "name": "c",
                "value": "d",
                "domain": ".b.one.com",
                "path": "/input",
                "expires": expires.timestamp(),
                "httpOnly": False,
                "secure": False,
                "sameSite": "Lax",
            },
            {
                "name": "e",
                "value": "f",
                "domain": ".b.one.com",
                "path": "/input/subfolder",
                "expires": -1,
                "httpOnly": False,
                "secure": False,
                "sameSite": "Lax",
            },
        ],
        "origins": [],
    }


async def test_FE_084_should_preserve_origin_storage_on_import_export_of_storage_state(
    playwright: Playwright, server: Server
) -> None:
    # The StorageState type has no opfs and indexedDB fields (like upstream's type),
    # so this state is typed Any.
    storage_state: Any = {
        "cookies": [
            {
                "name": "a",
                "value": "b",
                "domain": "a.b.one.com",
                "path": "/",
                "expires": -1,
                "httpOnly": False,
                "secure": False,
                "sameSite": "Lax",
            }
        ],
        "origins": [
            {
                "origin": "https://www.example.com",
                "localStorage": [{"name": "name1", "value": "value1"}],
                "opfs": [
                    {
                        "path": "hello.txt",
                        "type": "file",
                        "base64": "SGVsbG8sIHdvcmxkIQ==",
                    },
                    {
                        "path": "empty",
                        "type": "directory",
                    },
                ],
                "indexedDB": [
                    {
                        "name": "db",
                        "version": 5,
                        "stores": [
                            {
                                "name": "store",
                                "keyPath": "id",
                                "autoIncrement": False,
                                "indexes": [],
                                "records": [
                                    {"value": {"id": "foo", "name": "John Doe"}}
                                ],
                            }
                        ],
                    }
                ],
            }
        ],
    }
    request = await playwright.request.new_context(storage_state=storage_state)
    await request.get(server.EMPTY_PAGE)
    exported_state = await request.storage_state(indexed_db=True, opfs=True)
    assert exported_state == storage_state
    await request.dispose()


async def test_FE_085_should_send_cookies_from_storage_state(
    playwright: Playwright, server: Server, lookup_proxy: LookupProxy
) -> None:
    # Port of new Date('12/31/2099 PST').
    expires = datetime(2099, 12, 31, 8, 0, 0, tzinfo=timezone.utc)
    storage_state: StorageState = {
        "cookies": [
            {
                "name": "a",
                "value": "b",
                "domain": "a.b.one.com",
                "path": "/",
                "expires": -1,
                "httpOnly": False,
                "secure": False,
                "sameSite": "Lax",
            },
            {
                "name": "c",
                "value": "d",
                "domain": ".b.one.com",
                "path": "/first/",
                "expires": expires.timestamp(),
                "httpOnly": False,
                "secure": False,
                "sameSite": "Lax",
            },
            {
                "name": "e",
                "value": "f",
                "domain": ".b.one.com",
                "path": "/first/second",
                "expires": -1,
                "httpOnly": False,
                "secure": False,
                "sameSite": "Lax",
            },
        ],
        "origins": [],
    }
    # The proxy resolves the host name, as { __testHookLookup } does upstream.
    request = await playwright.request.new_context(
        storage_state=storage_state, proxy=lookup_proxy.settings
    )
    with server.expect_request(
        "/first/second/third/not_found.html"
    ) as server_request_info:
        await request.get(
            f"http://www.a.b.one.com:{server.PORT}/first/second/third/not_found.html"
        )
    assert server_request_info.value.getHeader("cookie") == "c=d; e=f"
    await request.dispose()


async def test_FE_086_storage_state_should_round_trip_through_file(
    playwright: Playwright, server: Server, tmp_path: Path
) -> None:
    storage_state: StorageState = {
        "cookies": [
            {
                "name": "a",
                "value": "b",
                "domain": "a.b.one.com",
                "path": "/",
                "expires": -1,
                "httpOnly": False,
                "secure": False,
                "sameSite": "Lax",
            }
        ],
        "origins": [],
    }

    request1 = await playwright.request.new_context(storage_state=storage_state)
    path = tmp_path / "storage-state.json"
    state1 = await request1.storage_state(path=path)
    assert state1 == storage_state

    written = path.read_text("utf8")
    # The Python client writes json.dumps(state); the JavaScript client writes
    # JSON.stringify(state, undefined, 2).
    assert json.dumps(state1) == written

    request2 = await playwright.request.new_context(storage_state=path)
    state2 = await request2.storage_state()
    assert state2 == storage_state
    await request1.dispose()
    await request2.dispose()


async def test_FE_087_should_work_with_empty_storage_state(
    playwright: Playwright, server: Server, tmp_path: Path
) -> None:
    storage_state = tmp_path / "storage-state.json"
    storage_state.write_text("{}")
    request1 = await playwright.request.new_context(storage_state=storage_state)

    state1 = await request1.storage_state()
    assert state1 == {"cookies": [], "origins": []}
    await expect(await request1.get(server.EMPTY_PAGE)).to_be_ok()
    await request1.dispose()
