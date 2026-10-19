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

from typing import Any, Callable, List

import pytest

from playwright.sync_api import BrowserContext, Error, Page, Request, Route
from tests.server import Server


def _append_with_return_value(values: List, value: Any) -> Any:
    values.append(value)


def test_should_work(page: Page, context: BrowserContext, server: Server) -> None:
    context.route("**/*", lambda route: route.fallback())
    page.goto(server.EMPTY_PAGE)


def test_should_fall_back(page: Page, context: BrowserContext, server: Server) -> None:
    intercepted: List[int] = []
    context.route(
        "**/empty.html",
        lambda route: (
            _append_with_return_value(intercepted, 1),
            route.fallback(),
        ),
    )
    context.route(
        "**/empty.html",
        lambda route: (
            _append_with_return_value(intercepted, 2),
            route.fallback(),
        ),
    )
    context.route(
        "**/empty.html",
        lambda route: (
            _append_with_return_value(intercepted, 3),
            route.fallback(),
        ),
    )

    page.goto(server.EMPTY_PAGE)
    assert intercepted == [3, 2, 1]


def test_should_fall_back_async_delayed(
    page: Page, context: BrowserContext, server: Server
) -> None:
    intercepted = []

    def create_handler(i: int) -> Callable[[Route], None]:
        def handler(route: Route) -> None:
            intercepted.append(i)
            page.wait_for_timeout(500)
            route.fallback()

        return handler

    context.route("**/empty.html", create_handler(1))
    context.route("**/empty.html", create_handler(2))
    context.route("**/empty.html", create_handler(3))
    page.goto(server.EMPTY_PAGE)
    assert intercepted == [3, 2, 1]


def test_should_chain_once(page: Page, context: BrowserContext, server: Server) -> None:
    context.route(
        "**/madeup.txt",
        lambda route: route.fulfill(status=200, body="fulfilled one"),
        times=1,
    )
    context.route("**/madeup.txt", lambda route: route.fallback(), times=1)

    resp = page.goto(server.PREFIX + "/madeup.txt")
    assert resp
    body = resp.body()
    assert body == b"fulfilled one"


def test_should_not_chain_fulfill(
    page: Page, context: BrowserContext, server: Server
) -> None:
    failed = [False]

    def handler(route: Route) -> None:
        failed[0] = True

    context.route("**/empty.html", handler)
    context.route(
        "**/empty.html",
        lambda route: route.fulfill(status=200, body="fulfilled"),
    )
    context.route("**/empty.html", lambda route: route.fallback())

    response = page.goto(server.EMPTY_PAGE)
    assert response
    body = response.body()
    assert body == b"fulfilled"
    assert not failed[0]


def test_should_not_chain_abort(
    page: Page,
    context: BrowserContext,
    server: Server,
    is_webkit: bool,
    is_firefox: bool,
) -> None:
    failed = [False]

    def handler(route: Route) -> None:
        failed[0] = True

    context.route("**/empty.html", handler)
    context.route("**/empty.html", lambda route: route.abort())
    context.route("**/empty.html", lambda route: route.fallback())

    with pytest.raises(Error) as excinfo:
        page.goto(server.EMPTY_PAGE)
    if is_webkit:
        assert "Blocked by Web Inspector" in excinfo.value.message
    elif is_firefox:
        assert "NS_ERROR_FAILURE" in excinfo.value.message
    else:
        assert "net::ERR_FAILED" in excinfo.value.message
    assert not failed[0]


def test_should_fall_back_after_exception(
    page: Page, context: BrowserContext, server: Server
) -> None:
    context.route("**/empty.html", lambda route: route.continue_())

    def handler(route: Route) -> None:
        try:
            route.fulfill(response=47)  # type: ignore
        except Exception:
            route.fallback()

    context.route("**/empty.html", handler)

    page.goto(server.EMPTY_PAGE)


def test_should_amend_http_headers(
    page: Page, context: BrowserContext, server: Server
) -> None:
    values = []

    def handler(route: Route) -> None:
        values.append(route.request.headers.get("foo"))
        values.append(route.request.header_value("FOO"))
        route.continue_()

    context.route("**/sleep.zzz", handler)

    def handler_with_header_mods(route: Route) -> None:
        route.fallback(headers={**route.request.headers, "FOO": "bar"})

    context.route("**/*", handler_with_header_mods)

    page.goto(server.EMPTY_PAGE)
    with server.expect_request("/sleep.zzz") as server_request_info:
        page.evaluate("() => fetch('/sleep.zzz')")
    values.append(server_request_info.value.getHeader("foo"))
    assert values == ["bar", "bar", "bar"]


def test_should_delete_header_with_undefined_value(
    page: Page, context: BrowserContext, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    server.set_route(
        "/something",
        lambda r: (
            r.setHeader("Acces-Control-Allow-Origin", "*"),
            r.write(b"done"),
            r.finish(),
        ),
    )

    intercepted_request = []

    def capture_and_continue(route: Route, request: Request) -> None:
        intercepted_request.append(request)
        route.continue_()

    context.route("**/*", capture_and_continue)

    def delete_foo_header(route: Route, request: Request) -> None:
        headers = request.all_headers()
        del headers["foo"]
        route.fallback(headers=headers)

    context.route(server.PREFIX + "/something", delete_foo_header)
    with server.expect_request("/something") as server_req_info:
        text = page.evaluate(
            """
            async url => {
                const data = await fetch(url, {
                    headers: {
                    foo: 'a',
                    bar: 'b',
                    }
                });
                return data.text();
                }
            """,
            server.PREFIX + "/something",
        )
    server_req = server_req_info.value
    assert text == "done"
    assert not intercepted_request[0].headers.get("foo")
    assert intercepted_request[0].headers.get("bar") == "b"
    assert not server_req.getHeader("foo")
    assert server_req.getHeader("bar") == "b"


def test_should_amend_method(
    page: Page, context: BrowserContext, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    method: List[str] = []
    context.route(
        "**/*",
        lambda route: (
            _append_with_return_value(method, route.request.method),
            route.continue_(),
        ),
    )
    context.route("**/*", lambda route: route.fallback(method="POST"))

    with server.expect_request("/sleep.zzz") as request_info:
        page.evaluate("() => fetch('/sleep.zzz')")
    request = request_info.value
    assert method == ["POST"]
    assert request.method == b"POST"


def test_should_override_request_url(
    page: Page, context: BrowserContext, server: Server
) -> None:
    url: List[str] = []
    context.route(
        "**/global-var.html",
        lambda route: (
            _append_with_return_value(url, route.request.url),
            route.continue_(),
        ),
    )
    context.route(
        "**/foo",
        lambda route: route.fallback(url=server.PREFIX + "/global-var.html"),
    )

    with server.expect_request("/global-var.html") as server_request_info:
        with page.expect_event("response") as response_info:
            page.goto(server.PREFIX + "/foo")
    server_request = server_request_info.value
    response = response_info.value
    assert url == [server.PREFIX + "/global-var.html"]
    assert response.url == server.PREFIX + "/global-var.html"
    assert response.request.url == server.PREFIX + "/global-var.html"
    assert page.evaluate("() => window['globalVar']") == 123
    assert server_request.uri == b"/global-var.html"
    assert server_request.method == b"GET"


def test_should_amend_post_data(
    page: Page, context: BrowserContext, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    post_data: List[str] = []
    context.route(
        "**/*",
        lambda route: (
            _append_with_return_value(post_data, route.request.post_data),
            route.continue_(),
        ),
    )
    context.route("**/*", lambda route: route.fallback(post_data="doggo"))

    with server.expect_request("/sleep.zzz") as server_request_info:
        page.evaluate("() => fetch('/sleep.zzz', { method: 'POST', body: 'birdy' })")
    server_request = server_request_info.value
    assert post_data == ["doggo"]
    assert server_request.post_body == b"doggo"


def test_should_amend_binary_post_data(
    page: Page, context: BrowserContext, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    post_data_buffer: List[str] = []
    context.route(
        "**/*",
        lambda route: (
            _append_with_return_value(post_data_buffer, route.request.post_data),
            route.continue_(),
        ),
    )
    context.route(
        "**/*", lambda route: route.fallback(post_data=b"\x00\x01\x02\x03\x04")
    )

    with server.expect_request("/sleep.zzz") as server_request_info:
        page.evaluate("() => fetch('/sleep.zzz', { method: 'POST', body: 'birdy' })")
    server_request = server_request_info.value
    # FIXME: should this be bytes?
    assert post_data_buffer == ["\x00\x01\x02\x03\x04"]
    assert server_request.method == b"POST"
    assert server_request.post_body == b"\x00\x01\x02\x03\x04"


def test_should_chain_fallback_into_page(
    context: BrowserContext, page: Page, server: Server
) -> None:
    intercepted: List[int] = []
    context.route(
        "**/empty.html",
        lambda route: (_append_with_return_value(intercepted, 1), route.fallback()),
    )
    context.route(
        "**/empty.html",
        lambda route: (_append_with_return_value(intercepted, 2), route.fallback()),
    )
    context.route(
        "**/empty.html",
        lambda route: (_append_with_return_value(intercepted, 3), route.fallback()),
    )
    page.route(
        "**/empty.html",
        lambda route: (_append_with_return_value(intercepted, 4), route.fallback()),
    )
    page.route(
        "**/empty.html",
        lambda route: (_append_with_return_value(intercepted, 5), route.fallback()),
    )
    page.route(
        "**/empty.html",
        lambda route: (_append_with_return_value(intercepted, 6), route.fallback()),
    )

    page.goto(server.EMPTY_PAGE)
    assert intercepted == [6, 5, 4, 3, 2, 1]
