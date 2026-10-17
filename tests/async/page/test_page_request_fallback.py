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
from typing import Any, Dict, List, Optional, cast

import pytest

from playwright.async_api import APIResponse, Error, Page, Request, Route
from tests.server import Server, TestServerRequest
from tests.utils import must


async def test_RO_120_should_work(page: Page, server: Server) -> None:
    await page.route("**/*", lambda route: route.fallback())
    await page.goto(server.EMPTY_PAGE)


async def test_RO_121_should_fall_back(page: Page, server: Server) -> None:
    intercepted: List[int] = []

    async def handler1(route: Route) -> None:
        intercepted.append(1)
        await route.fallback()

    async def handler2(route: Route) -> None:
        intercepted.append(2)
        await route.fallback()

    async def handler3(route: Route) -> None:
        intercepted.append(3)
        await route.fallback()

    await page.route("**/empty.html", handler1)
    await page.route("**/empty.html", handler2)
    await page.route("**/empty.html", handler3)
    await page.goto(server.EMPTY_PAGE)
    assert intercepted == [3, 2, 1]


async def test_RO_122_should_fall_back_async(page: Page, server: Server) -> None:
    intercepted: List[int] = []

    async def handler1(route: Route) -> None:
        intercepted.append(1)
        await asyncio.sleep(0.1)
        await route.fallback()

    async def handler2(route: Route) -> None:
        intercepted.append(2)
        await asyncio.sleep(0.1)
        await route.fallback()

    async def handler3(route: Route) -> None:
        intercepted.append(3)
        await asyncio.sleep(0.1)
        await route.fallback()

    await page.route("**/empty.html", handler1)
    await page.route("**/empty.html", handler2)
    await page.route("**/empty.html", handler3)
    await page.goto(server.EMPTY_PAGE)
    assert intercepted == [3, 2, 1]


async def test_RO_123_should_not_chain_fulfill(page: Page, server: Server) -> None:
    failed = False

    def handler1(route: Route) -> None:
        nonlocal failed
        failed = True

    async def handler2(route: Route) -> None:
        await route.fulfill(status=200, body="fulfilled")

    async def handler3(route: Route) -> None:
        await route.fallback()

    await page.route("**/empty.html", handler1)
    await page.route("**/empty.html", handler2)
    await page.route("**/empty.html", handler3)
    response = must(await page.goto(server.EMPTY_PAGE))
    body = await response.body()
    assert body.decode() == "fulfilled"
    assert not failed


async def test_RO_124_should_not_chain_abort(page: Page, server: Server) -> None:
    failed = False

    def handler1(route: Route) -> None:
        nonlocal failed
        failed = True

    async def handler2(route: Route) -> None:
        await route.abort()

    async def handler3(route: Route) -> None:
        await route.fallback()

    await page.route("**/empty.html", handler1)
    await page.route("**/empty.html", handler2)
    await page.route("**/empty.html", handler3)
    with pytest.raises(Error) as exc_info:
        await page.goto(server.EMPTY_PAGE)
    assert exc_info.value
    assert not failed


async def test_RO_125_should_fall_back_after_exception(
    page: Page, server: Server
) -> None:
    async def handler1(route: Route) -> None:
        await route.continue_()

    async def handler2(route: Route) -> None:
        try:
            # An invalid response, like upstream's `{}`.
            await route.fulfill(response=cast(APIResponse, object()))
        except Exception:
            await route.fallback()

    await page.route("**/empty.html", handler1)
    await page.route("**/empty.html", handler2)
    await page.goto(server.EMPTY_PAGE)


async def test_RO_126_should_chain_once(page: Page, server: Server) -> None:
    async def handler1(route: Route) -> None:
        await route.fulfill(status=200, body="fulfilled one")

    async def handler2(route: Route) -> None:
        await route.fallback()

    await page.route("**/empty.html", handler1, times=1)
    await page.route("**/empty.html", handler2, times=1)
    response = must(await page.goto(server.EMPTY_PAGE))
    body = await response.body()
    assert body.decode() == "fulfilled one"


async def test_RO_127_should_amend_http_headers(page: Page, server: Server) -> None:
    values: List[Optional[str]] = []

    async def handler1(route: Route) -> None:
        values.append(route.request.headers.get("foo"))
        values.append(await route.request.header_value("FOO"))
        await route.continue_()

    async def handler2(route: Route) -> None:
        await route.fallback(headers={**route.request.headers, "FOO": "bar"})

    await page.route("**/sleep.zzz", handler1)
    await page.route("**/*", handler2)
    await page.goto(server.EMPTY_PAGE)
    with server.expect_request("/sleep.zzz") as request_info:
        await page.evaluate("() => fetch('/sleep.zzz')")
    values.append(request_info.value.getHeader("foo"))
    assert values == ["bar", "bar", "bar"]


async def test_RO_128_should_delete_header_with_undefined_value(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/empty.html")

    def handle(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("Access-Control-Allow-Origin", "*")
        request.write(b"done")
        request.finish()

    server.set_route("/something", handle)
    intercepted_requests: List[Request] = []

    async def handler1(route: Route, request: Request) -> None:
        intercepted_requests.append(request)
        await route.continue_()

    async def handler2(route: Route, request: Request) -> None:
        headers: Dict[str, Any] = {**(await request.all_headers()), "foo": None}
        await route.fallback(headers=headers)

    await page.route("**/*", handler1)
    await page.route(server.PREFIX + "/something", handler2)
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
    assert intercepted_requests[-1].headers.get("foo") is None
    assert intercepted_requests[-1].headers["bar"] == "b"
    assert not server_request.getHeader("foo")
    assert server_request.getHeader("bar") == "b"


async def test_RO_129_should_amend_method(page: Page, server: Server) -> None:
    s_request = asyncio.create_task(server.wait_for_request("/sleep.zzz"))
    await page.goto(server.EMPTY_PAGE)

    method: Optional[str] = None

    async def handler1(route: Route) -> None:
        nonlocal method
        method = route.request.method
        await route.continue_()

    await page.route("**/*", handler1)
    await page.route("**/*", lambda route: route.fallback(method="POST"))

    async with page.expect_request("**/sleep.zzz") as request_info:
        await page.evaluate("() => fetch('/sleep.zzz')")
    request = await request_info.value
    assert method == "POST"
    assert request.method == "POST"
    assert (await s_request).method == b"POST"


async def test_RO_130_should_override_request_url(page: Page, server: Server) -> None:
    server_request = asyncio.create_task(server.wait_for_request("/global-var.html"))

    url: Optional[str] = None

    async def handler1(route: Route) -> None:
        nonlocal url
        url = route.request.url
        await route.continue_()

    await page.route("**/global-var.html", handler1)

    await page.route(
        "**/foo",
        lambda route: route.fallback(url=server.PREFIX + "/global-var.html"),
    )

    response = must(await page.goto(server.PREFIX + "/foo"))
    assert url == server.PREFIX + "/global-var.html"
    assert response.request.url == server.PREFIX + "/global-var.html"
    assert response.url == server.PREFIX + "/global-var.html"
    assert await page.evaluate("() => window['globalVar']") == 123
    assert (await server_request).method == b"GET"


async def test_RO_131_post_data_should_amend_post_data(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    post_data: Optional[str] = None

    async def handler1(route: Route) -> None:
        nonlocal post_data
        post_data = route.request.post_data
        await route.continue_()

    async def handler2(route: Route) -> None:
        await route.fallback(post_data="doggo")

    await page.route("**/*", handler1)
    await page.route("**/*", handler2)
    with server.expect_request("/sleep.zzz") as server_request_info:
        await page.evaluate(
            "() => fetch('/sleep.zzz', { method: 'POST', body: 'birdy' })"
        )
    assert post_data == "doggo"
    assert must(server_request_info.value.post_body).decode("utf8") == "doggo"


async def test_RO_132_post_data_should_amend_binary_post_data(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    arr = list(range(256))
    post_data_buffer: Optional[bytes] = None

    async def handler1(route: Route) -> None:
        nonlocal post_data_buffer
        post_data_buffer = route.request.post_data_buffer
        await route.continue_()

    async def handler2(route: Route) -> None:
        await route.fallback(post_data=bytes(arr))

    await page.route("**/*", handler1)
    await page.route("**/*", handler2)
    with server.expect_request("/sleep.zzz") as server_request_info:
        await page.evaluate(
            "() => fetch('/sleep.zzz', { method: 'POST', body: 'birdy' })"
        )
    buffer = must(server_request_info.value.post_body)
    assert post_data_buffer is not None
    assert len(post_data_buffer) == len(arr)
    assert len(buffer) == len(arr)
    for i in range(len(arr)):
        assert buffer[i] == arr[i]
        assert post_data_buffer[i] == arr[i]


async def test_RO_133_post_data_should_amend_json_post_data(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    post_data: Any = None

    async def handler1(route: Route) -> None:
        nonlocal post_data
        post_data = route.request.post_data_json
        await route.continue_()

    async def handler2(route: Route) -> None:
        await route.fallback(post_data={"foo": "bar"})

    await page.route("**/*", handler1)
    await page.route("**/*", handler2)
    with server.expect_request("/sleep.zzz") as server_request_info:
        await page.evaluate(
            "() => fetch('/sleep.zzz', { method: 'POST', body: 'birdy' })"
        )
    assert post_data == {"foo": "bar"}
    assert must(server_request_info.value.post_body).decode("utf8") == json.dumps(
        {"foo": "bar"}
    )
