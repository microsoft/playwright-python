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

"""Port of tests/page/page-request-continue.spec.ts."""

import asyncio
import re
from typing import Any, Awaitable, Dict, List, Optional, Set, TypeVar
from urllib.parse import urlparse

import pytest

from playwright.async_api import Error, Page, Request, Response, Route, expect
from tests.server import Server, TestServerRequest
from tests.utils import must

T = TypeVar("T")


async def ignore_error(awaitable: Awaitable[Any]) -> None:
    """Port of `promise.catch(() => {})`."""
    try:
        await awaitable
    except Error:
        pass


def resolve(future: "asyncio.Future[T]", value: T) -> None:
    """Port of a promise's resolve(): only the first call settles the promise."""
    if not future.done():
        future.set_result(value)


def respond_done_with_cors(request: TestServerRequest) -> None:
    request.setResponseCode(200)
    request.setHeader("Access-Control-Allow-Origin", "*")
    request.write(b"done")
    request.finish()


async def test_RO_057_should_work(page: Page, server: Server) -> None:
    await page.route("**/*", lambda route: route.continue_())
    await page.goto(server.EMPTY_PAGE)


async def test_RO_058_should_amend_http_headers(page: Page, server: Server) -> None:
    async def handler(route: Route) -> None:
        headers = {**route.request.headers, "FOO": "bar"}
        await route.continue_(headers=headers)

    await page.route("**/*", handler)
    await page.goto(server.EMPTY_PAGE)
    with server.expect_request("/sleep.zzz") as request_info:
        await page.evaluate("() => fetch('/sleep.zzz')")
    assert request_info.value.getHeader("foo") == "bar"


async def test_RO_059_should_not_allow_to_override_unsafe_http_headers(
    page: Page, server: Server
) -> None:
    route_future: "asyncio.Future[Route]" = asyncio.Future()
    await page.route("**/*", lambda route: resolve(route_future, route))
    server_request_task = asyncio.create_task(server.wait_for_request("/empty.html"))
    goto_task = asyncio.create_task(ignore_error(page.goto(server.EMPTY_PAGE)))
    route = await route_future
    await route.continue_(
        headers={
            **route.request.headers,
            "host": "bar",
            "trailer": "baz",
        }
    )
    server_request = await server_request_task
    assert server_request.getHeader("trailer") is None
    assert server_request.getHeader("host") == urlparse(server.EMPTY_PAGE).netloc
    await goto_task


async def test_RO_060_should_delete_header_with_undefined_value(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/empty.html")
    server.set_route("/something", respond_done_with_cors)
    intercepted_requests: List[Request] = []

    async def handler(route: Route, request: Request) -> None:
        intercepted_requests.append(request)
        headers: Dict[str, Any] = {**(await request.all_headers()), "foo": None}
        await route.continue_(headers=headers)

    await page.route(server.PREFIX + "/something", handler)

    with server.expect_request("/something") as server_request_info:
        text = await page.evaluate(
            """async url => {
                const data = await fetch(url, {
                    headers: {
                        foo: 'a',
                        bar: 'b',
                    }
                });
                return data.text();
            }""",
            server.PREFIX + "/something",
        )
    server_request = server_request_info.value
    assert text == "done"
    assert intercepted_requests[0].headers.get("foo") is None
    assert not server_request.getHeader("foo")
    assert server_request.getHeader("bar") == "b"


async def test_RO_061_should_amend_method(page: Page, server: Server) -> None:
    s_request = asyncio.create_task(server.wait_for_request("/sleep.zzz"))
    await page.goto(server.EMPTY_PAGE)
    await page.route("**/*", lambda route: route.continue_(method="POST"))
    with server.expect_request("/sleep.zzz") as request_info:
        await page.evaluate("() => fetch('/sleep.zzz')")
    assert request_info.value.method == b"POST"
    assert (await s_request).method == b"POST"


async def test_RO_062_should_override_request_url(page: Page, server: Server) -> None:
    server_request = asyncio.create_task(server.wait_for_request("/global-var.html"))

    async def handler(route: Route) -> None:
        await route.continue_(url=server.PREFIX + "/global-var.html")

    await page.route("**/foo", handler)
    response = must(await page.goto(server.PREFIX + "/foo"))
    assert response.request.url == server.PREFIX + "/global-var.html"
    assert response.url == server.PREFIX + "/global-var.html"
    assert await page.evaluate("() => window['globalVar']") == 123
    assert (await server_request).method == b"GET"


async def test_RO_063_should_not_allow_changing_protocol_when_overriding_url(
    page: Page, server: Server
) -> None:
    error_future: "asyncio.Future[Optional[Error]]" = asyncio.Future()

    async def handler(route: Route) -> None:
        try:
            await route.continue_(url="file:///tmp/foo")
            error_future.set_result(None)
        except Error as e:
            error_future.set_result(e)

    await page.route("**/*", handler)
    asyncio.create_task(ignore_error(page.goto(server.EMPTY_PAGE)))
    error = await error_future
    assert error
    assert "New URL must have same protocol as overridden URL" in error.message


async def test_RO_064_should_not_throw_if_request_was_cancelled_by_the_page(
    page: Page, server: Server
) -> None:
    intercept_future: "asyncio.Future[Route]" = asyncio.Future()
    await page.route("**/data.json", lambda route: intercept_future.set_result(route))
    await page.goto(server.EMPTY_PAGE)
    evaluate_task = asyncio.create_task(
        ignore_error(
            page.evaluate(
                """url => {
                    globalThis.controller = new AbortController();
                    return fetch(url, { signal: globalThis.controller.signal });
                }""",
                server.PREFIX + "/data.json",
            )
        )
    )
    route = await intercept_future
    async with page.expect_event("requestfailed") as failure_info:
        await page.evaluate("() => globalThis.controller.abort()")
    cancelled_request: Request = await failure_info.value
    assert re.search(r"cancelled|aborted", must(cancelled_request.failure), re.I)
    await route.continue_()  # Should not throw.
    await evaluate_task


async def test_RO_065_should_override_method_along_with_url(
    page: Page, server: Server
) -> None:
    request = asyncio.create_task(server.wait_for_request("/empty.html"))

    async def handler(route: Route) -> None:
        await route.continue_(url=server.EMPTY_PAGE, method="POST")

    await page.route("**/foo", handler)
    await page.goto(server.PREFIX + "/foo")
    assert (await request).method == b"POST"


async def test_RO_066_should_amend_method_on_main_request(
    page: Page, server: Server
) -> None:
    request = asyncio.create_task(server.wait_for_request("/empty.html"))
    await page.route("**/*", lambda route: route.continue_(method="POST"))
    await page.goto(server.EMPTY_PAGE)
    assert (await request).method == b"POST"


async def test_RO_067_post_data_should_amend_post_data(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)

    async def handler(route: Route) -> None:
        await route.continue_(post_data="doggo")

    await page.route("**/*", handler)
    with server.expect_request("/sleep.zzz") as server_request_info:
        await page.evaluate(
            "() => fetch('/sleep.zzz', { method: 'POST', body: 'birdy' })"
        )
    assert must(server_request_info.value.post_body).decode("utf8") == "doggo"


async def test_RO_068_post_data_should_compute_content_length_from_post_data(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    data = "a" * 7500

    async def handler(route: Route) -> None:
        headers = route.request.headers
        headers["content-type"] = "application/json"
        await route.continue_(post_data=data, headers=headers)

    await page.route("**/*", handler)
    with server.expect_request("/sleep.zzz") as server_request_info:
        await page.evaluate(
            "() => fetch('/sleep.zzz', { method: 'PATCH', body: 'birdy' })"
        )
    server_request = server_request_info.value
    assert must(server_request.post_body).decode("utf8") == data
    assert server_request.getHeader("content-length") == str(len(data))
    assert server_request.getHeader("content-type") == "application/json"


async def test_RO_069_post_data_should_amend_method_and_post_data(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)

    async def handler(route: Route) -> None:
        await route.continue_(method="POST", post_data="doggo")

    await page.route("**/*", handler)
    with server.expect_request("/sleep.zzz") as server_request_info:
        await page.evaluate("() => fetch('/sleep.zzz', { method: 'GET' })")
    server_request = server_request_info.value
    assert server_request.method == b"POST"
    assert must(server_request.post_body).decode("utf8") == "doggo"


async def test_RO_070_post_data_should_amend_utf8_post_data(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)

    async def handler(route: Route) -> None:
        await route.continue_(post_data="пушкин")

    await page.route("**/*", handler)
    with server.expect_request("/sleep.zzz") as server_request_info:
        await page.evaluate(
            "() => fetch('/sleep.zzz', { method: 'POST', body: 'birdy' })"
        )
    server_request = server_request_info.value
    assert server_request.method == b"POST"
    assert must(server_request.post_body).decode("utf8") == "пушкин"


async def test_RO_071_post_data_should_amend_longer_post_data(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)

    async def handler(route: Route) -> None:
        await route.continue_(post_data="doggo-is-longer-than-birdy")

    await page.route("**/*", handler)
    with server.expect_request("/sleep.zzz") as server_request_info:
        await page.evaluate(
            "() => fetch('/sleep.zzz', { method: 'POST', body: 'birdy' })"
        )
    server_request = server_request_info.value
    assert server_request.method == b"POST"
    assert must(server_request.post_body).decode("utf8") == "doggo-is-longer-than-birdy"


async def test_RO_072_post_data_should_amend_binary_post_data(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    arr = list(range(256))

    async def handler(route: Route) -> None:
        await route.continue_(post_data=bytes(arr))

    await page.route("**/*", handler)
    with server.expect_request("/sleep.zzz") as server_request_info:
        await page.evaluate(
            "() => fetch('/sleep.zzz', { method: 'POST', body: 'birdy' })"
        )
    server_request = server_request_info.value
    assert server_request.method == b"POST"
    buffer = must(server_request.post_body)
    assert len(buffer) == len(arr)
    for i in range(len(arr)):
        assert arr[i] == buffer[i]


async def test_RO_073_post_data_should_use_content_type_from_original_request(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.route(
        f"{server.PREFIX}/title.html",
        lambda route: route.continue_(post_data='{"b":2}'),
    )
    with server.expect_request("/title.html") as request_info:
        await page.evaluate(
            """async url => {
                await fetch(url, {
                    method: 'POST',
                    body: '{"a":1}',
                    headers: { 'content-type': 'application/json' },
                });
            }""",
            f"{server.PREFIX}/title.html",
        )
    request = request_info.value
    assert request.getHeader("content-type") == "application/json"
    assert must(request.post_body).decode("utf-8") == '{"b":2}'


async def test_RO_074_should_work_with_cross_origin_opener_policy(
    page: Page, server: Server, browser_name: str, request: pytest.FixtureRequest
) -> None:
    if browser_name == "webkit":
        request.applymarker(
            pytest.mark.xfail(
                reason="upstream: https://github.com/microsoft/playwright/issues/8796",
                strict=True,
            )
        )
    server_headers: List[TestServerRequest] = []
    server_requests: List[str] = []

    def handle(req: TestServerRequest) -> None:
        server_requests.append(req.uri.decode())
        if not server_headers:
            server_headers.append(req)
        req.setHeader("Cross-Origin-Opener-Policy", "same-origin")
        # Note: without 'onload', Firefox sometimes does not fire the load event
        # over the protocol. The reason is unclear.
        req.write(
            b"""
      <div>Hello there!</div>
      <script>window.onload = () => console.log('onload')</script>
    """
        )
        req.finish()

    server.set_route("/empty.html", handle)

    intercepted: List[str] = []

    async def handler(route: Route, req: Request) -> None:
        intercepted.append(req.url)
        await route.continue_(headers={"foo": "bar"})

    await page.route("**/*", handler)
    requests: Set[Request] = set()
    events: List[str] = []

    def on_request(r: Request) -> None:
        events.append("request")
        requests.add(r)

    def on_request_failed(r: Request) -> None:
        events.append("requestfailed")
        requests.add(r)

    def on_request_finished(r: Request) -> None:
        events.append("requestfinished")
        requests.add(r)

    def on_response(r: Response) -> None:
        events.append("response")
        requests.add(r.request)

    page.on("request", on_request)
    page.on("requestfailed", on_request_failed)
    page.on("requestfinished", on_request_finished)
    page.on("response", on_response)
    response = must(await page.goto(server.EMPTY_PAGE))
    assert intercepted == [server.EMPTY_PAGE]
    # There should be only one request to the server.
    if browser_name == "webkit":
        assert server_requests == ["/empty.html", "/empty.html"]
    else:
        assert server_requests == ["/empty.html"]
    assert server_headers[0].getHeader("foo") == "bar"
    assert page.url == server.EMPTY_PAGE
    await response.finished()
    assert events == ["request", "response", "requestfinished"]
    assert len(requests) == 1
    assert response.request.failure is None


async def test_RO_075_should_not_delete_the_origin_header(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/empty.html")
    server.set_route("/something", respond_done_with_cors)
    intercepted_origin: List[Optional[str]] = []

    async def handler(route: Route, request: Request) -> None:
        headers = await request.all_headers()
        intercepted_origin.append(headers.get("origin"))
        del headers["origin"]
        await route.continue_(headers=headers)

    await page.route(server.CROSS_PROCESS_PREFIX + "/something", handler)

    with server.expect_request("/something") as server_request_info:
        text = await page.evaluate(
            """async url => {
                const data = await fetch(url);
                return data.text();
            }""",
            server.CROSS_PROCESS_PREFIX + "/something",
        )
    assert text == "done"
    assert intercepted_origin == [server.PREFIX]
    assert server_request_info.value.getHeader("origin") == server.PREFIX


async def test_RO_076_should_continue_preload_link_requests(
    page: Page, server: Server
) -> None:
    intercepted = False

    async def handler(route: Route) -> None:
        nonlocal intercepted
        intercepted = True
        await route.continue_(headers={**route.request.headers, "custom": "value"})

    await page.route("**/one-style.css", handler)
    server_request_task = asyncio.create_task(server.wait_for_request("/one-style.css"))
    await page.goto(server.PREFIX + "/preload.html")
    server_request = await server_request_task
    assert server_request.getHeader("custom") == "value"
    await page.wait_for_function("() => window.preloadedStyles")
    assert intercepted is True
    color = await page.evaluate(
        "() => window.getComputedStyle(document.body).backgroundColor"
    )
    assert color == "rgb(255, 192, 203)"


async def test_RO_077_should_respect_set_cookie_in_redirect_response(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content('<a href="/set-cookie-redirect">Set cookie</a>')

    def handle(request: TestServerRequest) -> None:
        request.setResponseCode(302)
        request.setHeader("set-cookie", "foo=bar;  max-age=36000")
        request.setHeader("location", "/empty.html")
        request.finish()

    server.set_route("/set-cookie-redirect", handle)
    await page.route(
        "**/set-cookie-redirect",
        lambda route: route.continue_(headers={**route.request.headers}),
    )
    server_request_task = asyncio.create_task(server.wait_for_request("/empty.html"))
    await page.goto(server.PREFIX + "/set-cookie-redirect")
    server_request = await server_request_task
    assert server_request.getHeader("cookie") == "foo=bar"
    assert await page.evaluate("() => document.cookie") == "foo=bar"


def set_cookie_route(server: Server, path: str, cookie: str) -> None:
    def handle(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("Set-Cookie", cookie)
        request.finish()

    server.set_route(path, handle)


async def test_RO_078_continue_should_not_propagate_cookie_override_to_redirects(
    page: Page, server: Server
) -> None:
    set_cookie_route(server, "/set-cookie", "foo=bar;")
    await page.goto(server.PREFIX + "/set-cookie")
    assert await page.evaluate("() => document.cookie") == "foo=bar"
    server.set_redirect("/redirect", server.PREFIX + "/empty.html")
    await page.route(
        "**/redirect",
        lambda route: route.continue_(
            headers={**route.request.headers, "cookie": "override"}
        ),
    )
    with server.expect_request("/empty.html") as server_request_info:
        await page.goto(server.PREFIX + "/redirect")
    assert server_request_info.value.getHeader("cookie") == "foo=bar"


async def test_RO_079_continue_should_not_override_cookie(
    page: Page, server: Server
) -> None:
    set_cookie_route(server, "/set-cookie", "foo=bar;")
    await page.goto(server.PREFIX + "/set-cookie")
    assert await page.evaluate("() => document.cookie") == "foo=bar"
    await page.route(
        "**",
        lambda route: route.continue_(
            headers={
                **route.request.headers,
                "cookie": "override",
                "custom": "value",
            }
        ),
    )
    with server.expect_request("/empty.html") as server_request_info:
        await page.goto(server.EMPTY_PAGE)
    server_request = server_request_info.value
    # Original cookie from the browser's cookie jar should be sent.
    assert server_request.getHeader("cookie") == "foo=bar"
    assert server_request.getHeader("custom") == "value"


async def test_RO_080_continue_with_headers_should_send_fresh_cookie_from_the_browser_cookie_store(
    page: Page, server: Server
) -> None:
    set_cookie_route(server, "/set-cookie", "foo=v1;")
    await page.goto(server.PREFIX + "/set-cookie")
    assert await page.evaluate("() => document.cookie") == "foo=v1"

    async def handler(route: Route) -> None:
        # Cookie store changes between interception and continuation.
        await page.context.add_cookies(
            [{"name": "foo", "value": "v2", "url": server.PREFIX}]
        )
        await route.continue_(headers=route.request.headers)

    await page.route("**/empty.html", handler)

    with server.expect_request("/empty.html") as server_request_info:
        await page.goto(server.EMPTY_PAGE)
    # The fresh cookie from the browser cookie store should be sent, not the stale captured value.
    assert server_request_info.value.getHeader("cookie") == "foo=v2"


async def test_RO_081_continue_with_headers_should_send_fresh_cookie_after_a_redirect(
    page: Page, server: Server
) -> None:
    set_cookie_route(server, "/set-cookie", "foo=v1;")
    await page.goto(server.PREFIX + "/set-cookie")
    assert await page.evaluate("() => document.cookie") == "foo=v1"

    # The redirect updates the cookie before bouncing to the final destination.
    def handle_redirect(request: TestServerRequest) -> None:
        request.setResponseCode(302)
        request.setHeader("Set-Cookie", "foo=v2;")
        request.setHeader("location", server.PREFIX + "/empty.html")
        request.finish()

    server.set_route("/redirect", handle_redirect)

    await page.route(
        "**/redirect",
        lambda route: route.continue_(headers=route.request.headers),
    )

    with server.expect_request("/empty.html") as server_request_info:
        await page.goto(server.PREFIX + "/redirect")
    # The redirected request should carry the cookie updated by the redirect, not the stale captured value.
    assert server_request_info.value.getHeader("cookie") == "foo=v2"


async def test_RO_082_redirect_after_continue_should_be_able_to_delete_cookie(
    page: Page, server: Server
) -> None:
    set_cookie_route(server, "/set-cookie", "foo=bar;")
    await page.goto(server.PREFIX + "/set-cookie")
    assert await page.evaluate("() => document.cookie") == "foo=bar"

    set_cookie_route(
        server, "/delete-cookie", "foo=bar; expires=Thu, 01 Jan 1970 00:00:00 GMT"
    )
    server.set_redirect("/redirect", "/delete-cookie")
    await page.route(
        "**/redirect",
        lambda route: route.continue_(headers={**route.request.headers}),
    )
    await page.goto(server.PREFIX + "/redirect")
    with server.expect_request("/empty.html") as server_request_info:
        await page.goto(server.EMPTY_PAGE)
    assert not server_request_info.value.getHeader("cookie")


async def test_RO_083_continue_should_propagate_headers_to_redirects(
    page: Page, server: Server
) -> None:
    server.set_redirect("/redirect", "/empty.html")
    await page.route(
        "**/redirect",
        lambda route: route.continue_(
            headers={**route.request.headers, "custom": "value"}
        ),
    )
    with server.expect_request("/empty.html") as server_request_info:
        await page.goto(server.PREFIX + "/redirect")
    assert server_request_info.value.getHeader("custom") == "value"


async def test_RO_084_continue_should_drop_content_length_on_redirects(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)

    server.set_redirect("/redirect", "/empty.html")
    await page.route(
        "**/redirect",
        lambda route: route.continue_(
            headers={**route.request.headers, "custom": "value"}
        ),
    )
    with server.expect_request("/empty.html") as server_request_info:
        await page.evaluate(
            "url => fetch(url, { method: 'POST', body: 'foo' })",
            server.PREFIX + "/redirect",
        )
    server_request = server_request_info.value
    assert server_request.method == b"GET"
    assert server_request.getHeader("content-length") is None
    assert server_request.getHeader("content-type") is None
    assert server_request.getHeader("custom") == "value"


async def test_RO_085_redirected_requests_should_report_overridden_headers(
    page: Page, server: Server
) -> None:
    server.set_redirect("/redirect", "/empty.html")

    async def handler(route: Route) -> None:
        headers = route.request.headers
        headers["custom"] = "value"
        await route.fallback(headers=headers)

    await page.route("**/redirect", handler)

    with server.expect_request("/empty.html") as server_request_info:
        response = must(await page.goto(server.PREFIX + "/redirect"))
    assert server_request_info.value.getHeader("custom") == "value"
    assert response.request.url == server.EMPTY_PAGE
    assert response.request.headers["custom"] == "value"
    assert (await response.request.all_headers())["custom"] == "value"


async def test_RO_086_continue_should_delete_headers_on_redirects(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/empty.html")
    server.set_route("/something", respond_done_with_cors)
    server.set_redirect("/redirect", "/something")

    async def handler(route: Route) -> None:
        headers: Dict[str, Any] = {**route.request.headers, "foo": None}
        await route.continue_(headers=headers)

    await page.route("**/redirect", handler)
    with server.expect_request("/something") as server_request_info:
        text = await page.evaluate(
            """async url => {
                const data = await fetch(url, {
                    headers: {
                        foo: 'a',
                    }
                });
                return data.text();
            }""",
            server.PREFIX + "/redirect",
        )
    assert text == "done"
    assert not server_request_info.value.getHeader("foo")


def cors_route(
    server: Server,
    allow_headers: str,
    allow_origin_on_response: bool,
    server_requests: List[TestServerRequest],
) -> None:
    def handle(request: TestServerRequest) -> None:
        if request.method == b"OPTIONS":
            request.setResponseCode(204)
            request.setHeader("Access-Control-Allow-Origin", server.PREFIX)
            request.setHeader("Access-Control-Allow-Credentials", "true")
            request.setHeader(
                "Access-Control-Allow-Methods", "POST, GET, OPTIONS, DELETE"
            )
            request.setHeader("Access-Control-Allow-Headers", allow_headers)
            request.finish()
            return
        server_requests.append(request)
        request.setResponseCode(200)
        if allow_origin_on_response:
            request.setHeader("Access-Control-Allow-Origin", server.PREFIX)
            request.setHeader("Access-Control-Allow-Credentials", "true")
        request.write(b"done")
        request.finish()

    server.set_route("/something", handle)


def redirect_301_route(server: Server, path: str, location: str) -> None:
    def handle(request: TestServerRequest) -> None:
        request.setResponseCode(301)
        request.setHeader("location", location)
        request.finish()

    server.set_route(path, handle)


async def test_RO_087_propagate_headers_same_origin_redirect(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/empty.html")
    server_requests: List[TestServerRequest] = []
    cors_route(server, "authorization,cookie,custom", False, server_requests)
    server.set_redirect("/redirect", "/something")
    await page.evaluate("() => document.cookie = 'a=b'")
    text = await page.evaluate(
        """async url => {
            const data = await fetch(url, {
                headers: {
                    authorization: 'credentials',
                    custom: 'foo'
                },
                credentials: 'include',
            });
            return data.text();
        }""",
        server.PREFIX + "/redirect",
    )
    assert text == "done"
    server_request = server_requests[0]
    assert server_request.getHeader("authorization") == "credentials"
    assert server_request.getHeader("cookie") == "a=b"
    assert server_request.getHeader("custom") == "foo"


async def test_RO_088_propagate_headers_cross_origin(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/empty.html")
    server_requests: List[TestServerRequest] = []
    cors_route(server, "authorization,custom", True, server_requests)
    text = await page.evaluate(
        """async url => {
            const data = await fetch(url, {
                headers: {
                    authorization: 'credentials',
                    custom: 'foo'
                },
                credentials: 'include',
            });
            return data.text();
        }""",
        server.CROSS_PROCESS_PREFIX + "/something",
    )
    assert text == "done"
    server_request = server_requests[0]
    assert server_request.getHeader("authorization") == "credentials"
    assert server_request.getHeader("custom") == "foo"


async def test_RO_089_propagate_headers_cross_origin_redirect(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/empty.html")
    server_requests: List[TestServerRequest] = []
    cors_route(server, "authorization,cookie,custom", True, server_requests)
    redirect_301_route(server, "/redirect", f"{server.CROSS_PROCESS_PREFIX}/something")
    await page.evaluate("() => document.cookie = 'a=b'")
    text = await page.evaluate(
        """async url => {
            const data = await fetch(url, {
                headers: {
                    authorization: 'credentials',
                    custom: 'foo'
                },
                credentials: 'include',
            });
            return data.text();
        }""",
        server.PREFIX + "/redirect",
    )
    assert text == "done"
    server_request = server_requests[0]
    # Authorization header not propagated to cross-origin redirect.
    assert not server_request.getHeader("authorization")
    assert not server_request.getHeader("cookie")
    assert server_request.getHeader("custom") == "foo"


async def test_RO_090_propagate_headers_cross_origin_redirect_after_interception(
    page: Page, server: Server, browser_name: str
) -> None:
    await page.goto(server.PREFIX + "/empty.html")
    server_requests: List[TestServerRequest] = []
    cors_route(server, "authorization,cookie,custom", True, server_requests)
    redirect_301_route(server, "/redirect", f"{server.CROSS_PROCESS_PREFIX}/something")
    await page.evaluate("() => document.cookie = 'a=b'")

    async def handler(route: Route) -> None:
        await route.continue_(
            headers={
                **route.request.headers,
                "authorization": "credentials",
                "custom": "foo",
            }
        )

    await page.route("**/redirect", handler)
    text = await page.evaluate(
        """async url => {
            const data = await fetch(url, {
                headers: {
                    authorization: 'none',
                },
                credentials: 'include',
            });
            return data.text();
        }""",
        server.PREFIX + "/redirect",
    )
    assert text == "done"
    server_request = server_requests[0]
    if browser_name == "webkit":
        assert not server_request.getHeader("authorization")
    else:
        assert server_request.getHeader("authorization") == "credentials"
    assert not server_request.getHeader("cookie")
    assert server_request.getHeader("custom") == "foo"


async def test_RO_091_continue_should_pass_on_307_cross_origin_redirect(
    page: Page, server: Server
) -> None:
    def handle_final(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("content-type", "text/html")
        request.write(b"<!doctype html><title>final</title><p>ok</p>")
        request.finish()

    server.set_route("/final", handle_final)

    # Cross-origin 307 redirect that preserves the POST method.
    def handle_redirect(request: TestServerRequest) -> None:
        request.setResponseCode(307)
        request.setHeader("location", f"{server.PREFIX}/final")
        request.finish()

    server.set_route("/redirect307", handle_redirect)

    await page.goto(server.PREFIX + "/empty.html")
    await page.set_content(
        f"""
    <form id="f" method="POST" action="{server.CROSS_PROCESS_PREFIX}/redirect307">
      <input type="submit">
    </form>"""
    )

    await page.route("**/*", lambda route: route.continue_())
    await asyncio.gather(
        page.wait_for_url(f"{server.PREFIX}/final"),
        page.locator("input").click(),
    )
    await expect(page.locator("p")).to_have_text("ok")


async def test_RO_092_should_intercept_css_variable_with_background_url(
    page: Page, server: Server
) -> None:
    def handle(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "text/html")
        request.write(
            b"""
    <style>
      @keyframes JNDzq {
        0% { background-position: 0 0 }
        to { background-position: 100 0 }
      }
      div {
        --background: url(/pptr.png);
        background-image: var(--background);
        animation: JNDzq 1s linear infinite;
      }
    </style>
    <div>Yo!</div>"""
        )
        request.finish()

    server.set_route("/test.html", handle)
    intercept_future: "asyncio.Future[None]" = asyncio.Future()
    intercepted_requests = 0

    async def handler(route: Route, request: Request) -> None:
        nonlocal intercepted_requests
        intercepted_requests += 1
        if not intercept_future.done():
            intercept_future.set_result(None)
        await route.continue_()

    await page.route(server.PREFIX + "/pptr.png", handler)
    await page.goto(server.PREFIX + "/test.html")
    assert await page.locator("div").text_content() == "Yo!"
    await intercept_future
    await page.wait_for_timeout(1000)
    assert intercepted_requests == 1


async def test_RO_093_continue_should_not_change_multipart_form_data_body(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)

    def handle(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("Content-Type", "text/plain")
        request.write(b"done")
        request.finish()

    server.set_route("/upload", handle)

    async def send_form_data() -> TestServerRequest:
        with server.expect_request("/upload") as req_info:
            status = await page.evaluate(
                """async () => {
                    const newFile = new File(['file content'], 'file.txt');
                    const formData = new FormData();
                    formData.append('file', newFile);
                    const response = await fetch('/upload', {
                        method: 'POST',
                        credentials: 'include',
                        body: formData,
                    });
                    return response.status;
                }"""
            )
        req = req_info.value
        assert status == 200
        return req

    req_before = await send_form_data()

    async def handler(route: Route) -> None:
        await route.continue_()

    await page.route("**/*", handler)
    req_after = await send_form_data()
    file_content = "\r\n".join(
        [
            'Content-Disposition: form-data; name="file"; filename="file.txt"',
            "Content-Type: application/octet-stream",
            "",
            "file content",
            "------",
        ]
    )
    assert file_content in must(req_before.post_body).decode("utf8")
    assert file_content in must(req_after.post_body).decode("utf8")


async def test_RO_094_should_not_forward_host_header_on_cross_origin_redirect(
    page: Page, server: Server, browser_name: str
) -> None:
    redirect_target_path = "/final"
    redirect_source_path = "/redirect"

    redirected_host: List[Optional[str]] = []

    def handle_target(req: TestServerRequest) -> None:
        redirected_host.append(req.getHeader("host"))
        req.write(b"OK")
        req.finish()

    server.set_route(redirect_target_path, handle_target)

    first_host: List[Optional[str]] = []

    def handle_source(req: TestServerRequest) -> None:
        first_host.append(req.getHeader("host"))
        req.setResponseCode(302)
        req.setHeader(
            "location", f"{server.CROSS_PROCESS_PREFIX}{redirect_target_path}"
        )
        req.finish()

    server.set_route(redirect_source_path, handle_source)

    async def handler(route: Route) -> None:
        headers = route.request.headers
        if browser_name == "firefox":
            assert "host" in headers
        else:
            assert "host" not in headers
        await route.continue_(headers=headers)

    await page.route("**/*", handler)

    response = must(await page.goto(server.PREFIX + redirect_source_path))
    assert response.status == 200
    assert first_host[-1] == urlparse(server.PREFIX).netloc
    assert redirected_host[-1] == urlparse(server.CROSS_PROCESS_PREFIX).netloc


async def test_RO_095_post_data_should_return_empty_string_when_overriding_body_with_empty_string(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)

    async def handler(route: Route) -> None:
        await route.continue_(post_data="")

    await page.route("**/*", handler)
    async with page.expect_request("**") as request_info:
        await page.evaluate(
            "({ url }) => fetch(url, { method: 'POST', body: 'original' })",
            {"url": server.PREFIX + "/sleep.zzz"},
        )
    request = await request_info.value
    assert request.post_data == ""
