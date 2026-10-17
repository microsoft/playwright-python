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

"""Port of tests/page/page-request-fallback.spec.ts."""

import asyncio
import json
from typing import Any, Awaitable, Dict, List, Optional, TypeVar, cast

import pytest

from playwright._impl._greenlets import wait_for_future
from playwright.sync_api import APIResponse, Error, Page, Request, Route
from tests.server import Server, TestServerRequest
from tests.utils import must

T = TypeVar("T")


def wait_for(page: Page, awaitable: "Awaitable[T]") -> T:
    """Port of `await promise`: runs the event loop until the awaitable settles."""
    future = asyncio.ensure_future(awaitable)
    wait_for_future(page._loop, page._dispatcher_fiber, future)
    return future.result()


def test_RO_120_should_work(page: Page, server: Server) -> None:
    page.route("**/*", lambda route: route.fallback())
    page.goto(server.EMPTY_PAGE)


def test_RO_121_should_fall_back(page: Page, server: Server) -> None:
    intercepted: List[int] = []

    def handler1(route: Route) -> None:
        intercepted.append(1)
        route.fallback()

    def handler2(route: Route) -> None:
        intercepted.append(2)
        route.fallback()

    def handler3(route: Route) -> None:
        intercepted.append(3)
        route.fallback()

    page.route("**/empty.html", handler1)
    page.route("**/empty.html", handler2)
    page.route("**/empty.html", handler3)
    page.goto(server.EMPTY_PAGE)
    assert intercepted == [3, 2, 1]


def test_RO_122_should_fall_back_async(page: Page, server: Server) -> None:
    intercepted: List[int] = []

    def handler1(route: Route) -> None:
        intercepted.append(1)
        page.wait_for_timeout(100)
        route.fallback()

    def handler2(route: Route) -> None:
        intercepted.append(2)
        page.wait_for_timeout(100)
        route.fallback()

    def handler3(route: Route) -> None:
        intercepted.append(3)
        page.wait_for_timeout(100)
        route.fallback()

    page.route("**/empty.html", handler1)
    page.route("**/empty.html", handler2)
    page.route("**/empty.html", handler3)
    page.goto(server.EMPTY_PAGE)
    assert intercepted == [3, 2, 1]


def test_RO_123_should_not_chain_fulfill(page: Page, server: Server) -> None:
    failed = False

    def handler1(route: Route) -> None:
        nonlocal failed
        failed = True

    def handler2(route: Route) -> None:
        route.fulfill(status=200, body="fulfilled")

    def handler3(route: Route) -> None:
        route.fallback()

    page.route("**/empty.html", handler1)
    page.route("**/empty.html", handler2)
    page.route("**/empty.html", handler3)
    response = must(page.goto(server.EMPTY_PAGE))
    body = response.body()
    assert body.decode() == "fulfilled"
    assert not failed


def test_RO_124_should_not_chain_abort(page: Page, server: Server) -> None:
    failed = False

    def handler1(route: Route) -> None:
        nonlocal failed
        failed = True

    def handler2(route: Route) -> None:
        route.abort()

    def handler3(route: Route) -> None:
        route.fallback()

    page.route("**/empty.html", handler1)
    page.route("**/empty.html", handler2)
    page.route("**/empty.html", handler3)
    with pytest.raises(Error) as exc_info:
        page.goto(server.EMPTY_PAGE)
    assert exc_info.value
    assert not failed


def test_RO_125_should_fall_back_after_exception(page: Page, server: Server) -> None:
    def handler1(route: Route) -> None:
        route.continue_()

    def handler2(route: Route) -> None:
        try:
            # An invalid response, like upstream's `{}`.
            route.fulfill(response=cast(APIResponse, object()))
        except Exception:
            route.fallback()

    page.route("**/empty.html", handler1)
    page.route("**/empty.html", handler2)
    page.goto(server.EMPTY_PAGE)


def test_RO_126_should_chain_once(page: Page, server: Server) -> None:
    def handler1(route: Route) -> None:
        route.fulfill(status=200, body="fulfilled one")

    def handler2(route: Route) -> None:
        route.fallback()

    page.route("**/empty.html", handler1, times=1)
    page.route("**/empty.html", handler2, times=1)
    response = must(page.goto(server.EMPTY_PAGE))
    body = response.body()
    assert body.decode() == "fulfilled one"


def test_RO_127_should_amend_http_headers(page: Page, server: Server) -> None:
    values: List[Optional[str]] = []

    def handler1(route: Route) -> None:
        values.append(route.request.headers.get("foo"))
        values.append(route.request.header_value("FOO"))
        route.continue_()

    def handler2(route: Route) -> None:
        route.fallback(headers={**route.request.headers, "FOO": "bar"})

    page.route("**/sleep.zzz", handler1)
    page.route("**/*", handler2)
    page.goto(server.EMPTY_PAGE)
    with server.expect_request("/sleep.zzz") as request_info:
        page.evaluate("() => fetch('/sleep.zzz')")
    values.append(request_info.value.getHeader("foo"))
    assert values == ["bar", "bar", "bar"]


def test_RO_128_should_delete_header_with_undefined_value(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/empty.html")

    def handle(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("Access-Control-Allow-Origin", "*")
        request.write(b"done")
        request.finish()

    server.set_route("/something", handle)
    intercepted_requests: List[Request] = []

    def handler1(route: Route, request: Request) -> None:
        intercepted_requests.append(request)
        route.continue_()

    def handler2(route: Route, request: Request) -> None:
        headers: Dict[str, Any] = {**(request.all_headers()), "foo": None}
        route.fallback(headers=headers)

    page.route("**/*", handler1)
    page.route(server.PREFIX + "/something", handler2)
    with server.expect_request("/something") as server_request_info:
        text = page.evaluate(
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
    assert intercepted_requests[-1].headers.get("foo") is None
    assert intercepted_requests[-1].headers["bar"] == "b"
    assert not server_request.getHeader("foo")
    assert server_request.getHeader("bar") == "b"


def test_RO_129_should_amend_method(page: Page, server: Server) -> None:
    s_request = asyncio.create_task(server.wait_for_request("/sleep.zzz"))
    page.goto(server.EMPTY_PAGE)

    method: Optional[str] = None

    def handler1(route: Route) -> None:
        nonlocal method
        method = route.request.method
        route.continue_()

    page.route("**/*", handler1)
    page.route("**/*", lambda route: route.fallback(method="POST"))

    with page.expect_request("**/sleep.zzz") as request_info:
        page.evaluate("() => fetch('/sleep.zzz')")
    request = request_info.value
    assert method == "POST"
    assert request.method == "POST"
    assert wait_for(page, s_request).method == b"POST"


def test_RO_130_should_override_request_url(page: Page, server: Server) -> None:
    server_request = asyncio.create_task(server.wait_for_request("/global-var.html"))

    url: Optional[str] = None

    def handler1(route: Route) -> None:
        nonlocal url
        url = route.request.url
        route.continue_()

    page.route("**/global-var.html", handler1)

    page.route(
        "**/foo",
        lambda route: route.fallback(url=server.PREFIX + "/global-var.html"),
    )

    response = must(page.goto(server.PREFIX + "/foo"))
    assert url == server.PREFIX + "/global-var.html"
    assert response.request.url == server.PREFIX + "/global-var.html"
    assert response.url == server.PREFIX + "/global-var.html"
    assert page.evaluate("() => window['globalVar']") == 123
    assert wait_for(page, server_request).method == b"GET"


def test_RO_131_post_data_should_amend_post_data(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    post_data: Optional[str] = None

    def handler1(route: Route) -> None:
        nonlocal post_data
        post_data = route.request.post_data
        route.continue_()

    def handler2(route: Route) -> None:
        route.fallback(post_data="doggo")

    page.route("**/*", handler1)
    page.route("**/*", handler2)
    with server.expect_request("/sleep.zzz") as server_request_info:
        page.evaluate("() => fetch('/sleep.zzz', { method: 'POST', body: 'birdy' })")
    assert post_data == "doggo"
    assert must(server_request_info.value.post_body).decode("utf8") == "doggo"


def test_RO_132_post_data_should_amend_binary_post_data(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    arr = list(range(256))
    post_data_buffer: Optional[bytes] = None

    def handler1(route: Route) -> None:
        nonlocal post_data_buffer
        post_data_buffer = route.request.post_data_buffer
        route.continue_()

    def handler2(route: Route) -> None:
        route.fallback(post_data=bytes(arr))

    page.route("**/*", handler1)
    page.route("**/*", handler2)
    with server.expect_request("/sleep.zzz") as server_request_info:
        page.evaluate("() => fetch('/sleep.zzz', { method: 'POST', body: 'birdy' })")
    buffer = must(server_request_info.value.post_body)
    assert post_data_buffer is not None
    assert len(post_data_buffer) == len(arr)
    assert len(buffer) == len(arr)
    for i in range(len(arr)):
        assert buffer[i] == arr[i]
        assert post_data_buffer[i] == arr[i]


def test_RO_133_post_data_should_amend_json_post_data(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    post_data: Any = None

    def handler1(route: Route) -> None:
        nonlocal post_data
        post_data = route.request.post_data_json
        route.continue_()

    def handler2(route: Route) -> None:
        route.fallback(post_data={"foo": "bar"})

    page.route("**/*", handler1)
    page.route("**/*", handler2)
    with server.expect_request("/sleep.zzz") as server_request_info:
        page.evaluate("() => fetch('/sleep.zzz', { method: 'POST', body: 'birdy' })")
    assert post_data == {"foo": "bar"}
    assert must(server_request_info.value.post_body).decode("utf8") == json.dumps(
        {"foo": "bar"}
    )
