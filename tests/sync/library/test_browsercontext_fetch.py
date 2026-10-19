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

"""Port of tests/library/browsercontext-fetch.spec.ts."""

import base64
import concurrent.futures
import gzip
import json
import threading
import time
import zlib
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional
from urllib.parse import parse_qs, parse_qsl, quote, urlencode, urlparse

import pytest

from playwright.sync_api import (
    Browser,
    BrowserContext,
    BrowserType,
    Error,
    FilePayload,
    FormData,
    Page,
    expect,
    sync_playwright,
)
from tests.helpers.multipart import MultipartPart, parse_multipart
from tests.helpers.resolving_proxy import ResolvingProxy
from tests.server import (
    HTTPServer,
    HTTPSServer,
    Server,
    TestServerRequest,
    find_free_port,
    reactor,
)
from tests.utils import TARGET_CLOSED_ERROR_MESSAGE, must

ContextFactory = Callable[..., BrowserContext]

METHODS = ["fetch", "delete", "get", "head", "patch", "post", "put"]

# zlib.brotliCompressSync() of the bodies: Python has no brotli encoder.
BROTLI_HELLO_WORLD = bytes.fromhex("0b068048656c6c6f2c20776f726c642103")
BROTLI_A = bytes.fromhex("0b00804103")


def lookup(hostname: str) -> str:
    """Port of __testHookLookup: what the requests resolve host names to."""
    if hostname == "localhost" or hostname.endswith("playwright.dev"):
        return "127.0.0.1"
    raise Exception(f"Failed to resolve hostname: {hostname}")


@pytest.fixture
def resolving_proxy() -> Generator[ResolvingProxy, None, None]:
    """Replaces { __testHookLookup } in the request options, see ResolvingProxy."""
    proxy = ResolvingProxy(lookup)
    yield proxy
    proxy.close()


def end(request: TestServerRequest, body: bytes = b"") -> None:
    """Like res.end(body) in Node.js."""
    if body:
        request.write(body)
    request.finish()


def set_cookie_route(server: Server, path: str, cookies: List[str]) -> None:
    def handler(request: TestServerRequest) -> None:
        request.responseHeaders.setRawHeaders("Set-Cookie", cookies)
        end(request)

    server.set_route(path, handler)


def sorted_cookie_header(header: Optional[str]) -> List[str]:
    return sorted(s.strip() for s in must(header).split(";"))


def query_params(url: str) -> Dict[str, List[str]]:
    return parse_qs(urlparse(url).query)


def multipart_fields(parts: List[MultipartPart]) -> Dict[str, str]:
    """The fields that formidable returns: the parts that are not files."""
    return {part.name: part.text for part in parts if part.filename is None}


def multipart_files(parts: List[MultipartPart]) -> Dict[str, MultipartPart]:
    """The files that formidable returns."""
    return {part.name: part for part in parts if part.filename is not None}


def test_FE_088_get_should_work_smoke(context: BrowserContext, server: Server) -> None:
    response = context.request.get(server.PREFIX + "/simple.json")
    assert response.url == server.PREFIX + "/simple.json"
    assert response.status == 200
    assert response.status_text == "OK"
    assert response.ok
    assert response.headers["content-type"] == "application/json; charset=utf-8"
    assert {
        "name": "Content-Type",
        "value": "application/json; charset=utf-8",
    } in response.headers_array
    assert response.text() == '{"foo": "bar"}\n'


def test_FE_089_fetch_should_work(context: BrowserContext, server: Server) -> None:
    response = context.request.fetch(server.PREFIX + "/simple.json")
    assert response.url == server.PREFIX + "/simple.json"
    assert response.status == 200
    assert response.status_text == "OK"
    assert response.ok
    assert response.headers["content-type"] == "application/json; charset=utf-8"
    assert {
        "name": "Content-Type",
        "value": "application/json; charset=utf-8",
    } in response.headers_array
    assert response.text() == '{"foo": "bar"}\n'


def test_FE_090_should_return_timing(context: BrowserContext) -> None:
    # Create a fresh server to guarantee a new connection, because keep-alive
    # sockets from other tests do not have dns/connect timings.
    http_server = HTTPServer()
    http_server.start()
    reactor.wakeUp()
    http_server.set_route("/", lambda request: end(request, b"Hello"))
    try:
        response = context.request.get(f"http://localhost:{http_server.PORT}/")
        assert response.ok
        timing = response.timing
        assert abs(timing["startTime"] - time.time() * 1000) < 5000
        assert timing["domainLookupStart"] == 0
        assert timing["domainLookupEnd"] >= timing["domainLookupStart"]
        assert timing["connectStart"] == timing["domainLookupEnd"]
        assert timing["secureConnectionStart"] == -1
        assert timing["connectEnd"] >= timing["connectStart"]
        assert timing["requestStart"] == timing["connectEnd"]
        assert timing["responseStart"] >= timing["requestStart"]
        assert timing["responseEnd"] >= timing["responseStart"]
        assert timing["responseEnd"] < 60_000
    finally:
        http_server.stop()


def test_FE_091_should_return_timing_for_https(context: BrowserContext) -> None:
    # Create a fresh server to guarantee a new connection, because keep-alive
    # sockets from other tests do not have dns/connect timings.
    https_server = HTTPSServer()
    https_server.start()
    reactor.wakeUp()
    https_server.set_route("/", lambda request: end(request, b"Hello"))
    try:
        response = context.request.get(
            f"https://localhost:{https_server.PORT}/", ignore_https_errors=True
        )
        assert response.ok
        timing = response.timing
        assert abs(timing["startTime"] - time.time() * 1000) < 5000
        assert timing["domainLookupStart"] == 0
        assert timing["domainLookupEnd"] >= timing["domainLookupStart"]
        assert timing["connectStart"] == timing["domainLookupEnd"]
        assert timing["secureConnectionStart"] >= timing["connectStart"]
        assert timing["connectEnd"] >= timing["secureConnectionStart"]
        assert timing["requestStart"] == timing["connectEnd"]
        assert timing["responseStart"] >= timing["requestStart"]
        assert timing["responseEnd"] >= timing["responseStart"]
    finally:
        https_server.stop()


def destroy_socket(request: TestServerRequest) -> None:
    """Like req.socket.destroy() in Node.js: closes the connection after what was written.

    abortConnection() would reset the connection and drop what was written.
    """
    must(request.transport).loseConnection()


def send_partial_body_and_destroy_socket(request: TestServerRequest) -> None:
    request.setHeader("content-length", "4096")
    request.setHeader("content-type", "text/html")
    request.write(b"<title>A")
    destroy_socket(request)


def test_FE_092_should_throw_on_network_error(
    context: BrowserContext, server: Server
) -> None:
    server.set_route("/test", destroy_socket)
    with pytest.raises(Error) as exc_info:
        context.request.get(server.PREFIX + "/test")
    assert "APIRequestContext.get: socket hang up" in exc_info.value.message


def test_FE_093_should_throw_on_network_error_after_redirect(
    context: BrowserContext, server: Server
) -> None:
    server.set_redirect("/redirect", "/test")
    server.set_route("/test", destroy_socket)
    with pytest.raises(Error) as exc_info:
        context.request.get(server.PREFIX + "/redirect")
    assert "APIRequestContext.get: socket hang up" in exc_info.value.message


def test_FE_094_should_throw_on_network_error_when_sending_body(
    context: BrowserContext, server: Server
) -> None:
    server.set_route("/test", send_partial_body_and_destroy_socket)
    with pytest.raises(Error) as exc_info:
        context.request.get(server.PREFIX + "/test")
    assert "APIRequestContext.get: aborted" in exc_info.value.message


def test_FE_095_should_throw_on_network_error_when_sending_body_after_redirect(
    context: BrowserContext, server: Server
) -> None:
    server.set_redirect("/redirect", "/test")
    server.set_route("/test", send_partial_body_and_destroy_socket)
    with pytest.raises(Error) as exc_info:
        context.request.get(server.PREFIX + "/redirect")
    assert "APIRequestContext.get: aborted" in exc_info.value.message


def test_FE_096_should_add_session_cookies_to_request(
    context_factory: ContextFactory, server: Server, resolving_proxy: ResolvingProxy
) -> None:
    context = context_factory(proxy={"server": resolving_proxy.server})
    context.add_cookies(
        [
            {
                "name": "username",
                "value": "John Doe",
                "domain": ".my.playwright.dev",
                "path": "/",
                "expires": -1,
                "httpOnly": False,
                "secure": False,
                "sameSite": "Lax",
            }
        ]
    )
    with server.expect_request("/simple.json") as request_info:
        context.request.get(f"http://www.my.playwright.dev:{server.PORT}/simple.json")
    assert request_info.value.getHeader("cookie") == "username=John Doe"


def test_FE_097_should_filter_cookies_by_domain(
    context_factory: ContextFactory, server: Server, resolving_proxy: ResolvingProxy
) -> None:
    # https://github.com/microsoft/playwright/issues/36069
    context = context_factory(proxy={"server": resolving_proxy.server})
    context.add_cookies(
        [
            {
                "name": "first",
                "value": "1",
                "domain": "playwright.dev",
                "path": "/",
                "expires": -1,
                "httpOnly": False,
                "secure": False,
                "sameSite": "Lax",
            },
            {
                "name": "second",
                "value": "2",
                "domain": ".playwright.dev",
                "path": "/",
                "expires": -1,
                "httpOnly": False,
                "secure": False,
                "sameSite": "Lax",
            },
        ]
    )
    with server.expect_request("/simple.json") as request_info:
        context.request.get(f"http://my.playwright.dev:{server.PORT}/simple.json")
    assert request_info.value.getHeader("cookie") == "second=2"


@pytest.mark.parametrize("method", METHODS)
def test_FE_098_should_support_params_passed_as_object(
    context: BrowserContext, server: Server, method: str
) -> None:
    url = urlparse(server.EMPTY_PAGE)
    search = urlencode({"param1": "value1", "парам2": "знач2"})

    with server.expect_request(f"{url.path}?{search}") as request_info:
        response = getattr(context.request, method)(
            server.EMPTY_PAGE,
            params={
                "param1": "value1",
                "парам2": "знач2",
            },
        )

    request_params = query_params(request_info.value.uri.decode())
    assert request_params["param1"][0] == "value1"
    assert request_params["парам2"][0] == "знач2"

    response_params = query_params(response.url)
    assert response_params["param1"][0] == "value1"
    assert response_params["парам2"][0] == "знач2"


@pytest.mark.parametrize("method", METHODS)
def test_FE_099_should_support_params_passed_as_url_search_params(
    context: BrowserContext, server: Server, method: str
) -> None:
    url = urlparse(server.EMPTY_PAGE)
    # Python has no URLSearchParams: the JS client sends URLSearchParams.toString(),
    # which is urlencode() of the pairs.
    search_params = urlencode(
        [("param1", "value1"), ("param1", "value2"), ("парам2", "знач2")]
    )

    with server.expect_request(f"{url.path}?{search_params}") as request_info:
        response = getattr(context.request, method)(
            server.EMPTY_PAGE, params=search_params
        )

    request_params = query_params(request_info.value.uri.decode())
    assert request_params["param1"] == ["value1", "value2"]
    assert request_params["парам2"][0] == "знач2"

    response_params = query_params(response.url)
    assert response_params["param1"] == ["value1", "value2"]
    assert response_params["парам2"][0] == "знач2"


@pytest.mark.parametrize("method", METHODS)
def test_FE_100_should_support_params_passed_as_string(
    context: BrowserContext, server: Server, method: str
) -> None:
    url = urlparse(server.EMPTY_PAGE)
    params = "?param1=value1&param1=value2&парам2=знач2"

    # quote() with these safe characters is encodeURI() for this string.
    with server.expect_request(url.path + quote(params, safe="?&=")) as request_info:
        response = getattr(context.request, method)(server.EMPTY_PAGE, params=params)

    request_params = query_params(request_info.value.uri.decode())
    assert request_params["param1"] == ["value1", "value2"]
    assert request_params["парам2"][0] == "знач2"

    response_params = query_params(response.url)
    assert response_params["param1"] == ["value1", "value2"]
    assert response_params["парам2"][0] == "знач2"


@pytest.mark.parametrize("method", METHODS)
def test_FE_101_should_append_string_and_url_search_params_params_to_the_url_query(
    context: BrowserContext, server: Server, method: str
) -> None:
    # https://github.com/microsoft/playwright/issues/43210
    # The last one stands for new URLSearchParams({ q: 'cat' }), see FE-099.
    for params in ["q=cat", "?q=cat", urlencode({"q": "cat"})]:
        with server.expect_request("/empty.html?page=2&q=cat") as request_info:
            getattr(context.request, method)(
                server.EMPTY_PAGE + "?page=2", params=params
            )
        assert request_info.value.uri.decode() == "/empty.html?page=2&q=cat"


@pytest.mark.parametrize("method", METHODS)
def test_FE_102_should_support_fail_on_status_code(
    context: BrowserContext, server: Server, method: str
) -> None:
    with pytest.raises(Error) as exc_info:
        getattr(context.request, method)(
            server.PREFIX + "/does-not-exist.html", fail_on_status_code=True
        )
    assert "404 Not Found" in exc_info.value.message
    if method != "head":
        assert "Response text:\nFile not found:" in exc_info.value.message


@pytest.mark.parametrize("method", METHODS)
def test_FE_103_support_ignore_https_errors_option(
    context: BrowserContext, https_server: Server, method: str
) -> None:
    response = getattr(context.request, method)(
        https_server.EMPTY_PAGE, ignore_https_errors=True
    )
    assert response.status == 200


def test_FE_104_should_not_add_context_cookie_if_cookie_header_passed_as_a_parameter(
    context_factory: ContextFactory, server: Server, resolving_proxy: ResolvingProxy
) -> None:
    context = context_factory(proxy={"server": resolving_proxy.server})
    context.add_cookies(
        [
            {
                "name": "username",
                "value": "John Doe",
                "domain": ".my.playwright.dev",
                "path": "/",
                "expires": -1,
                "httpOnly": False,
                "secure": False,
                "sameSite": "Lax",
            }
        ]
    )
    with server.expect_request("/empty.html") as request_info:
        context.request.get(
            f"http://www.my.playwright.dev:{server.PORT}/empty.html",
            headers={"Cookie": "foo=bar"},
        )
    assert request_info.value.getHeader("cookie") == "foo=bar"


def test_FE_105_should_follow_redirects(
    context_factory: ContextFactory, server: Server, resolving_proxy: ResolvingProxy
) -> None:
    context = context_factory(proxy={"server": resolving_proxy.server})
    server.set_redirect("/redirect1", "/redirect2")
    server.set_redirect("/redirect2", "/simple.json")
    context.add_cookies(
        [
            {
                "name": "username",
                "value": "John Doe",
                "domain": ".my.playwright.dev",
                "path": "/",
                "expires": -1,
                "httpOnly": False,
                "secure": False,
                "sameSite": "Lax",
            }
        ]
    )
    with server.expect_request("/simple.json") as request_info:
        response = context.request.get(
            f"http://www.my.playwright.dev:{server.PORT}/redirect1"
        )
    assert request_info.value.getHeader("cookie") == "username=John Doe"
    assert response.url == f"http://www.my.playwright.dev:{server.PORT}/simple.json"
    assert response.json() == {"foo": "bar"}


def test_FE_106_should_follow_redirects_correctly_when_location_header_contains_utf_8_characters(
    context: BrowserContext, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/30903
    def handler(request: TestServerRequest) -> None:
        # Send the non-ASCII header as a raw response.
        transport = must(request.transport)
        transport.write(b"HTTP/1.1 301 Moved Permanently\r\n")
        transport.write(
            f"Location: {server.PREFIX}/empty.html?message=マスクПривет\r\n".encode()
        )
        transport.write(b"\r\n")
        transport.loseConnection()

    server.set_route("/redirect", handler)
    response = context.request.get(server.PREFIX + "/redirect")
    assert response.url == server.PREFIX + "/empty.html?" + urlencode(
        {"message": "マスクПривет"}
    )


def test_FE_107_should_add_cookies_from_set_cookie_header(
    context: BrowserContext, page: Page, server: Server
) -> None:
    set_cookie_route(
        server, "/setcookie.html", ["session=value", "foo=bar; max-age=3600"]
    )
    context.request.get(server.PREFIX + "/setcookie.html")
    cookies = context.cookies()
    assert {(c["name"], c["value"]) for c in cookies} == {
        ("session", "value"),
        ("foo", "bar"),
    }
    page.goto(server.EMPTY_PAGE)
    assert sorted(
        s.strip() for s in (page.evaluate("() => document.cookie")).split(";")
    ) == ["foo=bar", "session=value"]


def test_FE_108_page_request_add_cookies_should_add_cookies_to_the_browser_context(
    context: BrowserContext, page: Page, server: Server
) -> None:
    page.request.add_cookies(
        [
            {"name": "a", "value": "b", "url": server.EMPTY_PAGE},
            {
                "name": "c",
                "value": "d",
                "domain": "localhost",
                "path": "/",
                "expires": time.time() + 3600,
            },
        ]
    )
    assert sorted(
        ({"name": c["name"], "value": c["value"]} for c in context.cookies()),
        key=lambda c: c["name"],
    ) == [
        {"name": "a", "value": "b"},
        {"name": "c", "value": "d"},
    ]
    with server.expect_request("/empty.html") as request_info:
        context.request.get(server.EMPTY_PAGE)
    assert sorted_cookie_header(request_info.value.getHeader("cookie")) == [
        "a=b",
        "c=d",
    ]
    page.goto(server.EMPTY_PAGE)
    assert sorted_cookie_header(page.evaluate("() => document.cookie")) == [
        "a=b",
        "c=d",
    ]


def test_FE_109_page_request_cookies_should_return_browser_context_cookies(
    context: BrowserContext, page: Page, server: Server
) -> None:
    context.add_cookies(
        [
            {"name": "a", "value": "b", "url": server.EMPTY_PAGE},
            {"name": "c", "value": "d", "domain": "example.com", "path": "/"},
        ]
    )
    assert sorted(c["name"] for c in page.request.cookies()) == ["a", "c"]
    assert [c["name"] for c in page.request.cookies(server.EMPTY_PAGE)] == ["a"]
    assert page.request.cookies(server.EMPTY_PAGE) == context.cookies(server.EMPTY_PAGE)


def test_FE_110_page_request_clear_cookies_should_clear_browser_context_cookies(
    context: BrowserContext, page: Page, server: Server
) -> None:
    context.add_cookies(
        [
            {"name": "a", "value": "b", "url": server.EMPTY_PAGE},
            {"name": "c", "value": "d", "url": server.EMPTY_PAGE},
        ]
    )
    page.request.clear_cookies(name="a")
    assert [c["name"] for c in context.cookies()] == ["c"]
    page.request.clear_cookies()
    assert context.cookies() == []
    with server.expect_request("/empty.html") as request_info:
        page.request.get(server.EMPTY_PAGE)
    assert request_info.value.getHeader("cookie") is None


def test_FE_111_should_preserve_cookie_order_from_set_cookie_header(
    context: BrowserContext, page: Page, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/23390
    set_cookie_route(server, "/setcookie.html", ["cookie.0=foo", "cookie.1=bar"])
    page.request.get(server.PREFIX + "/setcookie.html")
    cookies = context.cookies()
    assert [{"name": c["name"], "value": c["value"]} for c in cookies] == [
        {"name": "cookie.0", "value": "foo"},
        {"name": "cookie.1", "value": "bar"},
    ]
    page.goto(server.EMPTY_PAGE)
    assert page.evaluate("() => document.cookie") == "cookie.0=foo; cookie.1=bar"
    with server.expect_request("/empty.html") as request_info:
        page.request.get(server.EMPTY_PAGE)
    assert request_info.value.getHeader("cookie") == "cookie.0=foo; cookie.1=bar"


def test_FE_112_should_support_cookie_with_empty_value(
    context: BrowserContext, page: Page, server: Server
) -> None:
    set_cookie_route(server, "/setcookie.html", ["first="])
    context.request.get(server.PREFIX + "/setcookie.html")
    page.goto(server.EMPTY_PAGE)
    assert page.evaluate("() => document.cookie") == "first="
    cookies = context.cookies()
    assert [{"name": c["name"], "value": c["value"]} for c in cookies] == [
        {"name": "first", "value": ""},
    ]


def test_FE_113_should_not_lose_body_while_handling_set_cookie_header(
    context: BrowserContext, server: Server
) -> None:
    def handler(request: TestServerRequest) -> None:
        request.responseHeaders.setRawHeaders(
            "Set-Cookie", ["session=value", "foo=bar; max-age=3600"]
        )
        end(request, b"text content")

    server.set_route("/setcookie.html", handler)
    response = context.request.get(server.PREFIX + "/setcookie.html")
    assert response.text() == "text content"


def test_FE_114_should_remove_cookie_with_negative_max_age(
    page: Page, server: Server
) -> None:
    set_cookie_route(
        server,
        "/setcookie.html",
        ["a=v; max-age=100000", "b=v; max-age=100000", "c=v"],
    )
    max_age = -2 * int(time.time() * 1000)
    set_cookie_route(
        server, "/removecookie.html", [f"a=v; max-age={max_age}", "b=v; max-age=-1"]
    )
    page.request.get(f"{server.PREFIX}/setcookie.html")
    page.request.get(f"{server.PREFIX}/removecookie.html")
    with server.expect_request("/empty.html") as request_info:
        page.request.get(server.EMPTY_PAGE)
    assert request_info.value.getHeader("cookie") == "c=v"


def test_FE_115_should_remove_cookie_with_expires_far_in_the_past(
    page: Page, server: Server
) -> None:
    set_cookie_route(server, "/setcookie.html", ["a=v; max-age=1000000"])
    set_cookie_route(
        server, "/removecookie.html", ["a=v; expires=Wed, 01 Jan 1000 00:00:00 GMT"]
    )
    page.request.get(f"{server.PREFIX}/setcookie.html")
    page.request.get(f"{server.PREFIX}/removecookie.html")
    with server.expect_request("/empty.html") as request_info:
        page.request.get(server.EMPTY_PAGE)
    assert not request_info.value.getHeader("cookie")


def test_FE_116_should_handle_cookies_on_redirects(
    context: BrowserContext,
    server: Server,
    browser_name: str,
    is_win: bool,
    browser_channel: Optional[str],
) -> None:
    def redirect1(request: TestServerRequest) -> None:
        request.setHeader("Set-Cookie", "r1=v1;SameSite=Lax")
        request.setResponseCode(301)
        request.setHeader("location", "/a/b/redirect2")
        end(request)

    def redirect2(request: TestServerRequest) -> None:
        request.setHeader("Set-Cookie", "r2=v2;SameSite=Lax")
        request.setResponseCode(302)
        request.setHeader("location", "/title.html")
        end(request)

    server.set_route("/redirect1", redirect1)
    server.set_route("/a/b/redirect2", redirect2)
    with (
        server.expect_request("/redirect1") as req1_info,
        server.expect_request("/a/b/redirect2") as req2_info,
        server.expect_request("/title.html") as req3_info,
    ):
        context.request.get(f"{server.PREFIX}/redirect1")
    assert not req1_info.value.getHeader("cookie")
    assert req2_info.value.getHeader("cookie") == "r1=v1"
    assert req3_info.value.getHeader("cookie") == "r1=v1"

    with (
        server.expect_request("/redirect1") as req1_info,
        server.expect_request("/a/b/redirect2") as req2_info,
        server.expect_request("/title.html") as req3_info,
    ):
        context.request.get(f"{server.PREFIX}/redirect1")
    assert req1_info.value.getHeader("cookie") == "r1=v1"
    assert sorted_cookie_header(req2_info.value.getHeader("cookie")) == [
        "r1=v1",
        "r2=v2",
    ]
    assert req3_info.value.getHeader("cookie") == "r1=v1"

    same_site = (
        "None"
        if browser_name == "webkit" and is_win and browser_channel != "webkit-wsl"
        else "Lax"
    )
    cookies = context.cookies()
    assert sorted(cookies, key=lambda c: c["name"]) == [
        {
            "sameSite": same_site,
            "name": "r1",
            "value": "v1",
            "domain": server.HOSTNAME,
            "path": "/",
            "expires": -1,
            "httpOnly": False,
            "secure": False,
        },
        {
            "sameSite": same_site,
            "name": "r2",
            "value": "v2",
            "domain": server.HOSTNAME,
            "path": "/a/b",
            "expires": -1,
            "httpOnly": False,
            "secure": False,
        },
    ]


def test_FE_117_should_return_raw_headers(
    context: BrowserContext, page: Page, server: Server
) -> None:
    def handler(request: TestServerRequest) -> None:
        # Write directly to the socket, to send the same header name more than once.
        transport = must(request.transport)
        transport.write(b"HTTP/1.1 200 OK\r\n")
        transport.write(b"Name-A: v1\r\n")
        transport.write(b"name-b: v4\r\n")
        transport.write(b"Name-a: v2\r\n")
        transport.write(b"name-A: v3\r\n")
        transport.write(b"\r\n")
        transport.loseConnection()

    server.set_route("/headers", handler)
    response = context.request.get(f"{server.PREFIX}/headers")
    assert response.status == 200
    headers = [h for h in response.headers_array if "name-" in h["name"].lower()]
    assert headers == [
        {"name": "Name-A", "value": "v1"},
        {"name": "name-b", "value": "v4"},
        {"name": "Name-a", "value": "v2"},
        {"name": "name-A", "value": "v3"},
    ]
    # Comma separated values, this matches Response.headers()
    assert response.headers["name-a"] == "v1, v2, v3"
    assert response.headers["name-b"] == "v4"


def test_FE_118_should_work_with_http_credentials(
    context: BrowserContext, server: Server
) -> None:
    server.set_auth("/empty.html", "user", "pass")

    with server.expect_request("/empty.html") as request_info:
        response = context.request.get(
            server.EMPTY_PAGE,
            headers={
                "authorization": "Basic " + base64.b64encode(b"user:pass").decode()
            },
        )
    assert response.status == 200
    assert request_info.value.uri == b"/empty.html"


def test_FE_121_should_support_multiple_http_credentials(
    context_factory: ContextFactory, server: Server
) -> None:
    server.set_auth("/empty.html", "user1", "pass1")
    context = context_factory(
        http_credentials=[
            {"username": "user1", "password": "pass1", "origin": server.PREFIX},
            {
                "username": "user2",
                "password": "pass2",
                "origin": server.CROSS_PROCESS_PREFIX,
            },
        ]
    )
    response1 = context.request.get(server.EMPTY_PAGE)
    assert response1.status == 200
    # Wrong credentials are picked for the other origin.
    response2 = context.request.get(server.CROSS_PROCESS_PREFIX + "/empty.html")
    assert response2.status == 401


def test_FE_122_should_support_http_credentials_send_for_new_context(
    context_factory: ContextFactory, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/30534
    context = context_factory(
        http_credentials={
            "username": "user",
            "password": "pass",
            "origin": server.PREFIX.upper(),
            "send": "always",
        }
    )
    with server.expect_request("/empty.html") as request_info:
        response = context.request.get(server.EMPTY_PAGE)
    assert (
        request_info.value.getHeader("authorization")
        == "Basic " + base64.b64encode(b"user:pass").decode()
    )
    assert response.status == 200

    with server.expect_request("/empty.html") as request_info:
        response = context.request.get(server.CROSS_PROCESS_PREFIX + "/empty.html")
    # Not sent to another origin.
    assert request_info.value.getHeader("authorization") is None
    assert response.status == 200


def test_FE_123_should_support_http_credentials_send_for_browser_new_page(
    server: Server, browser: Browser
) -> None:
    # https://github.com/microsoft/playwright/issues/30534
    page = browser.new_page(
        http_credentials={
            "username": "user",
            "password": "pass",
            "origin": server.PREFIX.upper(),
            "send": "always",
        }
    )
    with server.expect_request("/empty.html") as request_info:
        response = page.request.get(server.EMPTY_PAGE)
    assert (
        request_info.value.getHeader("authorization")
        == "Basic " + base64.b64encode(b"user:pass").decode()
    )
    assert response.status == 200

    with server.expect_request("/empty.html") as request_info:
        response = page.request.get(server.CROSS_PROCESS_PREFIX + "/empty.html")
    # Not sent to another origin.
    assert request_info.value.getHeader("authorization") is None
    assert response.status == 200
    page.close()


def test_FE_124_delete_should_support_post_data(
    context: BrowserContext, server: Server
) -> None:
    with server.expect_request("/simple.json") as request_info:
        response = context.request.delete(
            f"{server.PREFIX}/simple.json", data="My request"
        )
    request = request_info.value
    assert request.method == b"DELETE"
    assert request.post_body == b"My request"
    assert response.status == 200
    assert request.uri == b"/simple.json"


def test_FE_125_get_should_support_post_data(
    context: BrowserContext, server: Server
) -> None:
    with server.expect_request("/simple.json") as request_info:
        response = context.request.get(
            f"{server.PREFIX}/simple.json", data="My request"
        )
    request = request_info.value
    assert request.method == b"GET"
    assert request.post_body == b"My request"
    assert response.status == 200
    assert request.uri == b"/simple.json"


def test_FE_126_head_should_support_post_data(
    context: BrowserContext, server: Server
) -> None:
    with server.expect_request("/simple.json") as request_info:
        response = context.request.head(
            f"{server.PREFIX}/simple.json", data="My request"
        )
    request = request_info.value
    assert request.method == b"HEAD"
    assert request.post_body == b"My request"
    assert response.status == 200
    assert request.uri == b"/simple.json"


def test_FE_127_patch_should_support_post_data(
    context: BrowserContext, server: Server
) -> None:
    with server.expect_request("/simple.json") as request_info:
        response = context.request.patch(
            f"{server.PREFIX}/simple.json", data="My request"
        )
    request = request_info.value
    assert request.method == b"PATCH"
    assert request.post_body == b"My request"
    assert response.status == 200
    assert request.uri == b"/simple.json"


def test_FE_128_post_should_support_post_data(
    context: BrowserContext, server: Server
) -> None:
    with server.expect_request("/simple.json") as request_info:
        response = context.request.post(
            f"{server.PREFIX}/simple.json", data="My request"
        )
    request = request_info.value
    assert request.method == b"POST"
    assert request.post_body == b"My request"
    assert response.status == 200
    assert request.uri == b"/simple.json"


def test_FE_129_put_should_support_post_data(
    context: BrowserContext, server: Server
) -> None:
    with server.expect_request("/simple.json") as request_info:
        response = context.request.put(
            f"{server.PREFIX}/simple.json", data="My request"
        )
    request = request_info.value
    assert request.method == b"PUT"
    assert request.post_body == b"My request"
    assert response.status == 200
    assert request.uri == b"/simple.json"


def test_FE_130_should_add_default_headers(
    context: BrowserContext, server: Server, page: Page
) -> None:
    with server.expect_request("/empty.html") as request_info:
        context.request.get(server.EMPTY_PAGE)
    request = request_info.value
    assert request.getHeader("accept") == "*/*"
    user_agent = page.evaluate("() => navigator.userAgent")
    assert request.getHeader("user-agent") == user_agent
    assert request.getHeader("accept-encoding") == "gzip,deflate,br"


def test_FE_131_should_send_content_length(
    context: BrowserContext, server: Server
) -> None:
    with server.expect_request("/empty.html") as request_info:
        context.request.post(server.EMPTY_PAGE, data=bytes(range(256)))
    request = request_info.value
    assert request.getHeader("content-length") == "256"
    assert request.getHeader("content-type") == "application/octet-stream"


def test_FE_132_should_add_default_headers_to_redirects(
    context: BrowserContext, server: Server, page: Page
) -> None:
    server.set_redirect("/redirect", "/empty.html")
    with server.expect_request("/empty.html") as request_info:
        context.request.get(f"{server.PREFIX}/redirect")
    request = request_info.value
    assert request.getHeader("accept") == "*/*"
    user_agent = page.evaluate("() => navigator.userAgent")
    assert request.getHeader("user-agent") == user_agent
    assert request.getHeader("accept-encoding") == "gzip,deflate,br"


def test_FE_133_should_allow_to_override_default_headers(
    context: BrowserContext, server: Server, page: Page
) -> None:
    with server.expect_request("/empty.html") as request_info:
        context.request.get(
            server.EMPTY_PAGE,
            headers={
                "User-Agent": "Playwright",
                "Accept": "text/html",
                "Accept-Encoding": "br",
            },
        )
    request = request_info.value
    assert request.getHeader("accept") == "text/html"
    assert request.getHeader("user-agent") == "Playwright"
    assert request.getHeader("accept-encoding") == "br"


def test_FE_134_should_propagate_custom_headers_with_redirects(
    context: BrowserContext, server: Server
) -> None:
    server.set_redirect("/a/redirect1", "/b/c/redirect2")
    server.set_redirect("/b/c/redirect2", "/simple.json")
    with (
        server.expect_request("/a/redirect1") as req1_info,
        server.expect_request("/b/c/redirect2") as req2_info,
        server.expect_request("/simple.json") as req3_info,
    ):
        context.request.get(f"{server.PREFIX}/a/redirect1", headers={"foo": "bar"})
    assert req1_info.value.getHeader("foo") == "bar"
    assert req2_info.value.getHeader("foo") == "bar"
    assert req3_info.value.getHeader("foo") == "bar"


def test_FE_135_should_propagate_extra_http_headers_with_redirects(
    context: BrowserContext, server: Server
) -> None:
    server.set_redirect("/a/redirect1", "/b/c/redirect2")
    server.set_redirect("/b/c/redirect2", "/simple.json")
    context.set_extra_http_headers({"My-Secret": "Value"})
    with (
        server.expect_request("/a/redirect1") as req1_info,
        server.expect_request("/b/c/redirect2") as req2_info,
        server.expect_request("/simple.json") as req3_info,
    ):
        context.request.get(f"{server.PREFIX}/a/redirect1")
    assert req1_info.value.getHeader("my-secret") == "Value"
    assert req2_info.value.getHeader("my-secret") == "Value"
    assert req3_info.value.getHeader("my-secret") == "Value"


def test_FE_136_should_throw_on_invalid_header_value(
    context: BrowserContext, server: Server
) -> None:
    with pytest.raises(Error) as exc_info:
        context.request.get(
            f"{server.PREFIX}/a/redirect1",
            headers={
                "foo": "недопустимое значение",
            },
        )
    assert "Invalid character in header content" in exc_info.value.message


def test_FE_137_should_throw_on_non_http_s_protocol(
    context: BrowserContext,
) -> None:
    with pytest.raises(Error) as exc_info1:
        context.request.get("data:text/plain,test")
    assert 'Protocol "data:" not supported' in exc_info1.value.message
    with pytest.raises(Error) as exc_info2:
        context.request.get("file:///tmp/foo")
    assert 'Protocol "file:" not supported' in exc_info2.value.message


def test_FE_138_should_support_https(
    browser_name: str,
    launch_arguments: Dict,
    https_server: Server,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Upstream sets NODE_TLS_REJECT_UNAUTHORIZED=0 in the test process, which runs the
    # Playwright server. The Python driver is another process, and it reads the
    # environment when it starts: start one with the variable set. A thread can run
    # only one sync Playwright, so the new one runs in a thread of its own.
    def run() -> int:
        with sync_playwright() as playwright:
            browser = playwright[browser_name].launch(**launch_arguments)
            context = browser.new_context()
            response = context.request.get(https_server.EMPTY_PAGE)
            status = response.status
            browser.close()
            return status

    with monkeypatch.context() as patch:
        patch.setenv("NODE_TLS_REJECT_UNAUTHORIZED", "0")
        # suppressCertificateWarning()
        patch.setenv("NODE_NO_WARNINGS", "1")
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            status = executor.submit(run).result()
    assert status == 200


def test_FE_139_should_inherit_ignore_https_errors_from_context(
    context_factory: ContextFactory, https_server: Server
) -> None:
    context = context_factory(ignore_https_errors=True)
    response = context.request.get(https_server.EMPTY_PAGE)
    assert response.status == 200


def test_FE_140_should_resolve_url_relative_to_base_url(
    server: Server, context_factory: ContextFactory
) -> None:
    context = context_factory(base_url=server.PREFIX)
    response = context.request.get("/empty.html")
    assert response.url == server.EMPTY_PAGE


def compressed_route(encoding: str, body: bytes) -> Callable[[TestServerRequest], None]:
    def handler(request: TestServerRequest) -> None:
        request.setHeader("Content-Encoding", encoding)
        request.setHeader("Content-Type", "text/plain")
        end(request, body)

    return handler


def test_FE_141_should_support_gzip_compression(
    context: BrowserContext, server: Server
) -> None:
    server.set_route(
        "/compressed", compressed_route("gzip", gzip.compress(b"Hello, world!"))
    )
    response = context.request.get(server.PREFIX + "/compressed")
    assert response.text() == "Hello, world!"


def test_FE_142_should_support_case_insensitive_content_encoding(
    context: BrowserContext, server: Server
) -> None:
    server.set_route(
        "/compressed-uppercase",
        compressed_route("GZIP", gzip.compress(b"Hello, world!")),
    )
    response = context.request.get(server.PREFIX + "/compressed-uppercase")
    assert response.text() == "Hello, world!"


def test_FE_143_should_throw_informative_error_on_corrupted_gzip_body(
    context: BrowserContext, server: Server
) -> None:
    server.set_route("/corrupted", compressed_route("gzip", b"Hello, world!"))
    with pytest.raises(Error) as exc_info:
        context.request.get(server.PREFIX + "/corrupted")
    assert "failed to decompress 'gzip' encoding" in exc_info.value.message


def test_FE_144_should_support_brotli_compression(
    context: BrowserContext, server: Server
) -> None:
    server.set_route("/compressed", compressed_route("br", BROTLI_HELLO_WORLD))
    response = context.request.get(server.PREFIX + "/compressed")
    assert response.text() == "Hello, world!"


def test_FE_145_should_throw_informative_error_on_corrupted_brotli_body(
    context: BrowserContext, server: Server
) -> None:
    server.set_route("/corrupted", compressed_route("br", b"Hello, world!"))
    with pytest.raises(Error) as exc_info:
        context.request.get(server.PREFIX + "/corrupted")
    assert "failed to decompress 'br' encoding" in exc_info.value.message


def test_FE_146_should_support_deflate_compression(
    context: BrowserContext, server: Server
) -> None:
    server.set_route(
        "/compressed", compressed_route("deflate", zlib.compress(b"Hello, world!"))
    )
    response = context.request.get(server.PREFIX + "/compressed")
    assert response.text() == "Hello, world!"


def test_FE_147_should_throw_informative_error_on_corrupted_deflate_body(
    context: BrowserContext, server: Server
) -> None:
    server.set_route("/corrupted", compressed_route("deflate", b"Hello, world!"))
    with pytest.raises(Error) as exc_info:
        context.request.get(server.PREFIX + "/corrupted")
    assert "failed to decompress 'deflate' encoding" in exc_info.value.message


def never_ending_route(request: TestServerRequest) -> None:
    request.setHeader("content-length", "4096")
    request.setHeader("content-type", "text/html")


def test_FE_148_should_support_timeout_option(
    context: BrowserContext, server: Server
) -> None:
    server.set_route("/slow", never_ending_route)

    with pytest.raises(Error) as exc_info:
        context.request.get(server.PREFIX + "/slow", timeout=10)
    assert "APIRequestContext.get: Timeout 10ms exceeded" in exc_info.value.message


def test_FE_149_should_support_a_timeout_of_0(
    context: BrowserContext, server: Server
) -> None:
    def handler(request: TestServerRequest) -> None:
        request.setHeader("content-length", "4")
        request.setHeader("content-type", "text/html")
        reactor.callLater(0.05, lambda: end(request, b"done"))

    server.set_route("/slow", handler)

    response = context.request.get(server.PREFIX + "/slow", timeout=0)
    assert response.text() == "done"


def test_FE_150_should_respect_timeout_after_redirects(
    context: BrowserContext, server: Server
) -> None:
    server.set_redirect("/redirect", "/slow")
    server.set_route("/slow", never_ending_route)

    context.set_default_timeout(100)
    with pytest.raises(Error) as exc_info:
        context.request.get(server.PREFIX + "/redirect")
    assert "APIRequestContext.get: Timeout 100ms exceeded" in exc_info.value.message


def test_FE_151_should_not_hang_on_a_brotli_encoded_range_request(
    context: BrowserContext, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/18190
    encoded_request_payload = BROTLI_A

    def handler(request: TestServerRequest) -> None:
        request.setResponseCode(206)
        request.setHeader("Content-Type", "text/plain")
        request.setHeader("content-length", "1")
        request.setHeader("Content-Encoding", "br")
        request.setHeader("content-range", f"bytes 0-2/{len(encoded_request_payload)}")
        request.setHeader("Accept-Ranges", "bytes")
        request.write(encoded_request_payload[:2])

    server.set_route("/brotli", handler)

    with pytest.raises(Error, match=r"Parse Error: Expected HTTP/"):
        context.request.get(
            server.PREFIX + "/brotli",
            headers={
                "range": "bytes=0-2",
            },
        )


def test_FE_152_should_dispose(context: BrowserContext, server: Server) -> None:
    response = context.request.get(server.PREFIX + "/simple.json")
    assert response.json() == {"foo": "bar"}
    response.dispose()
    with pytest.raises(Error) as exc_info:
        response.body()
    assert "Response has been disposed" in exc_info.value.message


def test_FE_153_should_dispose_when_context_closes(
    context: BrowserContext, server: Server
) -> None:
    response = context.request.get(server.PREFIX + "/simple.json")
    assert response.json() == {"foo": "bar"}
    context.close()
    with pytest.raises(Error) as exc_info:
        response.body()
    assert "Response has been disposed" in exc_info.value.message


def test_FE_154_should_override_request_parameters(
    context: BrowserContext, page: Page, server: Server
) -> None:
    with page.expect_request("**/*") as page_request_info:
        page.goto(server.EMPTY_PAGE)
    page_request = page_request_info.value
    with server.expect_request("/empty.html") as request_info:
        context.request.fetch(
            page_request,
            method="POST",
            headers={
                "foo": "bar",
            },
            data="data",
        )
    request = request_info.value
    assert request.method == b"POST"
    assert request.getHeader("foo") == "bar"
    assert must(request.post_body).decode() == "data"


def test_FE_155_should_support_application_x_www_form_urlencoded(
    context: BrowserContext, page: Page, server: Server
) -> None:
    with server.expect_request("/empty.html") as request_info:
        context.request.post(
            server.EMPTY_PAGE,
            form={
                "firstName": "John",
                "lastName": "Doe",
                "file": "f.js",
            },
        )
    request = request_info.value
    assert request.method == b"POST"
    assert request.getHeader("content-type") == "application/x-www-form-urlencoded"
    body = must(request.post_body).decode()
    params = parse_qsl(body)
    assert request.getHeader("content-length") == str(len(urlencode(params)))
    assert dict(params) == {"firstName": "John", "lastName": "Doe", "file": "f.js"}


def test_FE_156_should_support_application_x_www_form_urlencoded_with_param_lists(
    context: BrowserContext, page: Page, server: Server
) -> None:
    form = FormData()
    form.append("foo", "1")
    form.append("foo", "2")
    with server.expect_request("/empty.html") as request_info:
        context.request.post(server.EMPTY_PAGE, form=form)
    request = request_info.value
    assert request.method == b"POST"
    assert request.getHeader("content-type") == "application/x-www-form-urlencoded"
    body = must(request.post_body).decode()
    params = parse_qsl(body)
    assert request.getHeader("content-length") == str(len(urlencode(params)))
    assert parse_qs(body)["foo"] == ["1", "2"]


def test_FE_157_should_encode_to_application_json_by_default(
    context: BrowserContext, page: Page, server: Server
) -> None:
    data = {
        "firstName": "John",
        "lastName": "Doe",
        "file": {
            "name": "f.js",
        },
    }
    with server.expect_request("/empty.html") as request_info:
        context.request.post(server.EMPTY_PAGE, data=data)
    request = request_info.value
    assert request.method == b"POST"
    assert request.getHeader("content-type") == "application/json"
    body = must(request.post_body).decode()
    assert json.loads(body) == data


def multipart_route(
    assetdir: Path, received: Dict[str, Any]
) -> Callable[[TestServerRequest], None]:
    """Parses the posted form, then serves the file, like the formidable routes."""

    def handler(request: TestServerRequest) -> None:
        received["request"] = request
        try:
            received["parts"] = parse_multipart(
                must(request.getHeader("content-type")), must(request.post_body)
            )
        except Exception as error:
            received["error"] = error
        request.serve_file(assetdir / "empty.html")

    return handler


def test_FE_158_should_support_multipart_form_data(
    context: BrowserContext, server: Server, assetdir: Path
) -> None:
    received: Dict[str, Any] = {}
    server.set_route("/empty.html", multipart_route(assetdir, received))

    file: FilePayload = {
        "name": "f.js",
        "mimeType": "text/javascript",
        "buffer": b"var x = 10;\r\n;console.log(x);",
    }
    response = context.request.post(
        server.EMPTY_PAGE,
        multipart={
            "firstName": "John",
            "middleName": "",
            "lastName": "Doe",
            "file": file,
        },
    )
    assert not received.get("error")
    server_request: TestServerRequest = received["request"]
    assert server_request.method == b"POST"
    assert "multipart/form-data" in must(server_request.getHeader("content-type"))
    fields = multipart_fields(received["parts"])
    files = multipart_files(received["parts"])
    assert fields["firstName"] == "John"
    assert fields["middleName"] == ""
    assert fields["lastName"] == "Doe"
    assert files["file"].filename == file["name"]
    assert files["file"].content_type == file["mimeType"]
    assert files["file"].data == file["buffer"]
    assert response.status == 200


def test_FE_159_should_escape_quotes_and_newlines_in_multipart_field_and_file_names(
    context: BrowserContext, server: Server, assetdir: Path
) -> None:
    # https://github.com/microsoft/playwright/issues/43422
    received: Dict[str, Any] = {}

    def handler(request: TestServerRequest) -> None:
        received["content_type"] = request.getHeader("content-type")
        received["body"] = request.post_body
        request.serve_file(assetdir / "empty.html")

    server.set_route("/empty.html", handler)
    context.request.post(
        server.EMPTY_PAGE,
        multipart={
            'say"hi\nthere': "v1",
            "file": {
                "name": 'report "final"\r\n.txt',
                "mimeType": "text/plain",
                "buffer": b"hello",
            },
        },
    )
    content_type: str = must(received["content_type"])
    body: bytes = must(received["body"])
    headers = [
        line
        for line in body.decode().split("\r\n")
        if line.startswith("content-disposition")
    ]
    assert headers == [
        'content-disposition: form-data; name="say%22hi%0D%0Athere"',
        'content-disposition: form-data; name="file"; filename="report %22final%22%0D%0A.txt"',
    ]
    # A standard multipart parser expects that escaping.
    form = {part.name: part for part in reversed(parse_multipart(content_type, body))}
    assert form['say"hi\r\nthere'].text == "v1"
    assert form["file"].text == "hello"


def test_FE_160_should_support_multipart_form_data_with_read_stream_values(
    context: BrowserContext, page: Page, assetdir: Path, server: Server
) -> None:
    received: Dict[str, Any] = {}
    server.set_route("/empty.html", multipart_route(assetdir, received))
    # Python has no ReadStream: a Path value in FormData is a file read from the disk.
    form = FormData()
    form.set("firstName", "John")
    form.set("lastName", "Doe")
    form.set("readStream", assetdir / "simplezip.json")
    response = context.request.post(server.EMPTY_PAGE, multipart=form)
    assert not received.get("error")
    server_request: TestServerRequest = received["request"]
    assert server_request.method == b"POST"
    assert "multipart/form-data" in must(server_request.getHeader("content-type"))
    assert "5498" in must(server_request.getHeader("content-length"))
    fields = multipart_fields(received["parts"])
    files = multipart_files(received["parts"])
    assert fields["firstName"] == "John"
    assert fields["lastName"] == "Doe"
    assert files["readStream"].filename == "simplezip.json"
    assert files["readStream"].content_type == "application/json"
    assert files["readStream"].data == (assetdir / "simplezip.json").read_bytes()
    assert response.status == 200


def test_FE_161_should_support_multipart_form_data_and_keep_the_order(
    context: BrowserContext, page: Page, assetdir: Path, server: Server
) -> None:
    given: Dict[str, Any] = {
        "firstName": "John",
        "lastName": "Doe",
        "age": 27,
    }
    given["foo"] = "bar"
    given_keys = list(given.keys())
    received: Dict[str, Any] = {}
    server.set_route("/empty.html", multipart_route(assetdir, received))
    response = context.request.post(server.EMPTY_PAGE, multipart=given)
    assert not received.get("error")
    actual_keys = list(multipart_fields(received["parts"]).keys())
    assert actual_keys == given_keys
    assert response.status == 200


def test_FE_162_should_support_repeating_names_in_multipart_form_data(
    context: BrowserContext, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/28070
    received: Dict[str, Any] = {}

    def handler(request: TestServerRequest) -> None:
        received["post_body"] = must(request.post_body).decode()
        request.setHeader("content-type", "text/plain")
        end(request, b"OK.")

    server.set_route("/empty.html", handler)
    form_data = FormData()
    form_data.set("name", "John")
    form_data.append("name", "Doe")
    # Python has no File or Blob: a file is a FilePayload with its file name. A Blob
    # gets the file name "blob".
    form_data.append(
        "file",
        {
            "name": "f1.js",
            "mimeType": "text/javascript",
            "buffer": b"var x = 10;\r\n;console.log(x);",
        },
    )
    form_data.append(
        "file", {"name": "custom_f2.txt", "mimeType": "text/plain", "buffer": b"hello"}
    )
    form_data.append(
        "file", {"name": "blob", "mimeType": "text/plain", "buffer": b"boo"}
    )
    response = context.request.post(server.EMPTY_PAGE, multipart=form_data)
    post_body: str = received["post_body"]
    assert 'content-disposition: form-data; name="name"\r\n\r\nJohn' in post_body
    assert 'content-disposition: form-data; name="name"\r\n\r\nDoe' in post_body
    assert (
        'content-disposition: form-data; name="file"; filename="f1.js"\r\ncontent-type: text/javascript\r\n\r\nvar x = 10;\r\n;console.log(x);'
        in post_body
    )
    assert (
        'content-disposition: form-data; name="file"; filename="custom_f2.txt"\r\ncontent-type: text/plain\r\n\r\nhello'
        in post_body
    )
    assert (
        'content-disposition: form-data; name="file"; filename="blob"\r\ncontent-type: text/plain\r\n\r\nboo'
        in post_body
    )
    assert response.status == 200


def test_FE_163_should_serialize_data_to_json_regardless_of_content_type(
    context: BrowserContext, server: Server
) -> None:
    data = {
        "firstName": "John",
        "lastName": "Doe",
    }
    with server.expect_request("/empty.html") as request_info:
        context.request.post(
            server.EMPTY_PAGE,
            headers={
                "content-type": "unknown",
            },
            data=data,
        )
    request = request_info.value
    assert request.method == b"POST"
    assert request.getHeader("content-type") == "unknown"
    body = must(request.post_body).decode()
    assert body == json.dumps(data, separators=(",", ":"))


def test_FE_164_should_throw_nice_error_on_unsupported_data_type(
    context: BrowserContext, server: Server
) -> None:
    with pytest.raises(Error) as exc_info:
        context.request.post(
            server.EMPTY_PAGE,
            headers={
                "content-type": "application/json",
            },
            data=lambda: True,
        )
    assert "Unexpected 'data' type" in exc_info.value.message


def test_FE_165_context_request_should_export_same_storage_state_as_context(
    context: BrowserContext, page: Page, server: Server
) -> None:
    set_cookie_route(server, "/setcookie.html", ["a=b", "c=d"])
    context.request.get(server.PREFIX + "/setcookie.html")
    context_state = context.storage_state()
    assert len(context_state["cookies"]) == 2
    request_state = context.request.storage_state()
    assert request_state == context_state
    page_state = page.request.storage_state()
    assert page_state == context_state


def test_FE_166_should_send_secure_cookie_over_http_for_localhost(
    page: Page, server: Server, browser_channel: Optional[str]
) -> None:
    if browser_channel == "webkit-wsl":
        pytest.skip()
    set_cookie_route(server, "/setcookie.html", ["a=v; secure"])
    page.request.get(f"{server.PREFIX}/setcookie.html")
    with server.expect_request("/empty.html") as request_info:
        page.request.get(server.EMPTY_PAGE)
    assert request_info.value.getHeader("cookie") == "a=v"


def test_FE_167_should_accept_bool_and_numeric_params_and_filter_out_undefined(
    page: Page, server: Server
) -> None:
    received: List[TestServerRequest] = []
    url = urlparse(server.EMPTY_PAGE)
    search = urlencode({"str": "s", "num": "10", "bool": "true", "bool2": "false"})

    def handler(request: TestServerRequest) -> None:
        received.append(request)
        request.serve_file(server.static_path / "empty.html")

    server.set_route(f"{url.path}?{search}", handler)
    # None is Python's undefined.
    params: Dict[str, Any] = {
        "str": "s",
        "num": 10,
        "bool": True,
        "bool2": False,
        "none": None,
    }
    page.request.get(server.EMPTY_PAGE, params=params)
    assert received
    request_params = query_params(received[0].uri.decode())
    assert request_params["str"][0] == "s"
    assert request_params["num"][0] == "10"
    assert request_params["bool"][0] == "true"
    assert request_params["bool2"][0] == "false"
    assert "none" not in request_params


def test_FE_168_should_abort_requests_when_browser_context_closes(
    context_factory: ContextFactory,
    server: Server,
    page: Page,
    sync_gather: Callable,
) -> None:
    request_received = threading.Event()
    connection_closed: "concurrent.futures.Future[None]" = concurrent.futures.Future()

    def handler(request: TestServerRequest) -> None:
        def on_close(_: Any) -> None:
            if not connection_closed.done():
                connection_closed.set_result(None)

        request.notifyFinish().addErrback(on_close)
        request_received.set()

    server.set_route("/empty.html", handler)
    context = context_factory()

    def get() -> Any:
        try:
            return context.request.get(server.EMPTY_PAGE)
        except Error as error:
            return error

    def post() -> Any:
        try:
            return context.request.post(server.EMPTY_PAGE)
        except Error as error:
            return error

    def close_on_request() -> None:
        # server.wait_for_request() is async only: poll, and let the requests run
        # while the page of another context waits.
        while not request_received.is_set():
            page.wait_for_timeout(10)
        context.close()

    [error, _, _] = sync_gather(get, post, close_on_request)
    assert isinstance(error, Error)
    assert (
        "Request context disposed" in error.message
        or "Target page, context or browser has been closed" in error.message
    )
    connection_closed.result(timeout=30)


@pytest.mark.only_browser("chromium")
def test_FE_169_should_work_with_connect_over_cdp(
    browser_type: BrowserType, launch_arguments: Dict, server: Server
) -> None:
    port = find_free_port()
    browser_server = browser_type.launch(
        **launch_arguments, args=[f"--remote-debugging-port={port}"]
    )
    try:
        cdp_browser = browser_type.connect_over_cdp(f"http://127.0.0.1:{port}/")
        [context] = cdp_browser.contexts
        response = context.request.get(server.PREFIX + "/simple.json")
        assert response.url == server.PREFIX + "/simple.json"
        assert response.status == 200
        assert response.text() == '{"foo": "bar"}\n'
    finally:
        browser_server.close()


def test_FE_170_should_support_same_site_cookie_attribute_over_https(
    context_factory: ContextFactory,
    https_server: Server,
    browser_name: str,
    is_win: bool,
    browser_channel: Optional[str],
) -> None:
    # Cookies with SameSite=None must also specify the Secure attribute. WebKit navigation
    # to HTTP url will fail if the response contains a cookie with Secure attribute, so
    # we do HTTPS navigation.
    context = context_factory(ignore_https_errors=True)
    page = context.new_page()
    for value in ["None", "Lax", "Strict"]:
        set_cookie_route(
            https_server,
            "/empty.html",
            [f"SID=2022; Path=/; Secure; SameSite={value}"],
        )
        page.request.get(https_server.EMPTY_PAGE)
        [cookie] = page.context.cookies()
        if browser_name == "webkit" and is_win and browser_channel != "webkit-wsl":
            assert cookie["sameSite"] == "None"
        else:
            assert cookie["sameSite"] == value


def test_FE_171_should_set_domain_localhost_cookie(
    context: BrowserContext, server: Server
) -> None:
    set_cookie_route(
        server, "/empty.html", [f"name=val; Domain={server.HOSTNAME}; Path=/;"]
    )
    context.request.get(server.EMPTY_PAGE)
    [cookie] = context.cookies()
    assert cookie
    assert cookie["name"] == "name"
    assert cookie["value"] == "val"


def test_FE_172_fetch_should_not_throw_on_long_set_cookie_value(
    context: BrowserContext, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/27165
    set_cookie_route(server, "/empty.html", [f"foo={'a' * 4100}; path=/;", "bar=val"])
    context.request.get(server.EMPTY_PAGE, timeout=5000)
    cookies = context.cookies()
    assert "bar" in [c["name"] for c in cookies]


def test_FE_173_should_support_set_cookie_with_same_site_and_without_secure_attribute_over_http(
    page: Page,
    server: Server,
    browser_name: str,
    is_win: bool,
    is_linux: bool,
    browser_channel: Optional[str],
) -> None:
    for value in ["None", "Lax", "Strict"]:
        set_cookie_route(server, "/empty.html", [f"SID=2022; Path=/; SameSite={value}"])
        page.request.get(server.EMPTY_PAGE)
        cookies = page.context.cookies()
        if browser_name == "chromium" and value == "None":
            assert not cookies
        elif (
            browser_name == "webkit"
            and (is_linux or browser_channel == "webkit-wsl")
            and value == "None"
        ):
            assert not cookies
        elif browser_name == "webkit" and is_win and browser_channel != "webkit-wsl":
            assert cookies[0]["sameSite"] == "None"
        else:
            assert cookies[0]["sameSite"] == value


def test_FE_174_should_update_host_header_on_redirect(
    context: BrowserContext, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/26743
    redirect_count = 0
    prefix_host = urlparse(server.PREFIX).netloc
    cross_process_host = urlparse(server.CROSS_PROCESS_PREFIX).netloc

    def redirect(request: TestServerRequest) -> None:
        nonlocal redirect_count
        redirect_count += 1
        path = "/redirect" if request.getHeader("host") == prefix_host else "/test"
        request.setResponseCode(302)
        request.setHeader("host", cross_process_host)
        request.setHeader("location", server.CROSS_PROCESS_PREFIX + path)
        end(request)

    def test(request: TestServerRequest) -> None:
        request.setHeader("content-type", "text/plain")
        end(request, b"Hello!")

    server.set_route("/redirect", redirect)
    server.set_route("/test", test)
    with server.expect_request("/test") as request_info:
        response = context.request.get(
            server.PREFIX + "/redirect", headers={"HosT": prefix_host}
        )
    assert redirect_count == 2
    expect(response).to_be_ok()
    assert response.text() == "Hello!"

    assert request_info.value.getHeader("host") == cross_process_host


def test_FE_175_should_not_work_after_dispose(
    context: BrowserContext, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/27822
    context.request.dispose()
    with pytest.raises(Error) as exc_info:
        context.request.get(server.EMPTY_PAGE)
    assert TARGET_CLOSED_ERROR_MESSAGE in exc_info.value.message


def test_FE_176_should_not_work_after_context_dispose(
    context: BrowserContext, server: Server
) -> None:
    context.close(reason="Test ended.")
    with pytest.raises(Error) as exc_info:
        context.request.get(server.EMPTY_PAGE)
    assert "Test ended." in exc_info.value.message


def test_FE_177_should_retry_on_econnreset(
    context: BrowserContext, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/30978
    request_count = 0

    def handler(request: TestServerRequest) -> None:
        nonlocal request_count
        request_count += 1
        if request_count <= 3:
            destroy_socket(request)
            return
        request.setHeader("content-type", "text/plain")
        end(request, b"Hello!")

    server.set_route("/test", handler)
    response = context.request.get(server.PREFIX + "/test", max_retries=3)
    assert response.status == 200
    assert response.text() == "Hello!"
    assert request_count == 4


def test_FE_178_should_retry_econnreset_on_compressed_response(
    context: BrowserContext, server: Server
) -> None:
    request_count = 0

    def handler(request: TestServerRequest) -> None:
        nonlocal request_count
        request_count += 1
        if request_count <= 2:
            destroy_socket(request)
            return
        request.setHeader("Content-Encoding", "gzip")
        request.setHeader("Content-Type", "text/plain")
        end(request, gzip.compress(b"compressed-retry-ok"))

    server.set_route("/test-gzip", handler)
    response = context.request.get(server.PREFIX + "/test-gzip", max_retries=3)
    assert response.status == 200
    assert response.text() == "compressed-retry-ok"
    assert request_count == 3


def test_FE_179_should_retry_econnreset_mid_stream_during_gzip_decompression(
    context: BrowserContext, server: Server
) -> None:
    request_count = 0

    def handler(request: TestServerRequest) -> None:
        nonlocal request_count
        request_count += 1
        if request_count <= 2:
            # Send response headers to make client enter the decompression pipeline,
            # then destroy the socket. This exercises the fix: without it, the
            # pipeline error callback wraps the error, stripping .code for retry.
            request.setHeader("Content-Encoding", "gzip")
            request.setHeader("Content-Type", "text/plain")
            request.write(b"")
            destroy_socket(request)
            return
        request.setHeader("Content-Encoding", "gzip")
        request.setHeader("Content-Type", "text/plain")
        end(request, gzip.compress(b"midstream-retry-ok"))

    server.set_route("/test-gzip-midstream", handler)
    response = context.request.get(
        server.PREFIX + "/test-gzip-midstream", max_retries=3
    )
    assert response.status == 200
    assert response.text() == "midstream-retry-ok"
    assert request_count == 3
