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
from typing import Any, Callable, Coroutine, cast

from playwright.async_api import BrowserContext, Page, Request, Route
from tests.server import Server


async def test_should_work(page: Page, context: BrowserContext, server: Server) -> None:
    await context.route("**/*", lambda route: asyncio.create_task(route.fallback()))
    await page.goto(server.EMPTY_PAGE)


async def test_should_fall_back(
    page: Page, context: BrowserContext, server: Server
) -> None:
    intercepted = []

    def _handler1(route: Route) -> None:
        intercepted.append(1)
        asyncio.create_task(route.fallback())

    await context.route("**/empty.html", _handler1)

    def _handler2(route: Route) -> None:
        intercepted.append(2)
        asyncio.create_task(route.fallback())

    await context.route(
        "**/empty.html",
        _handler2,
    )

    def _handler3(route: Route) -> None:
        intercepted.append(3)
        asyncio.create_task(route.fallback())

    await context.route("**/empty.html", _handler3)

    await page.goto(server.EMPTY_PAGE)
    assert intercepted == [3, 2, 1]


async def test_should_fall_back_async_delayed(
    page: Page, context: BrowserContext, server: Server
) -> None:
    intercepted = []

    def create_handler(i: int) -> Callable[[Route], Coroutine]:
        async def handler(route: Route) -> None:
            intercepted.append(i)
            await asyncio.sleep(0.1)
            await route.fallback()

        return handler

    await context.route("**/empty.html", create_handler(1))
    await context.route("**/empty.html", create_handler(2))
    await context.route("**/empty.html", create_handler(3))
    await page.goto(server.EMPTY_PAGE)
    assert intercepted == [3, 2, 1]


async def test_should_chain_once(
    page: Page, context: BrowserContext, server: Server
) -> None:
    await context.route(
        "**/madeup.txt",
        lambda route: asyncio.create_task(
            route.fulfill(status=200, body="fulfilled one")
        ),
        times=1,
    )
    await context.route(
        "**/madeup.txt", lambda route: asyncio.create_task(route.fallback()), times=1
    )

    resp = await page.goto(server.PREFIX + "/madeup.txt")
    assert resp
    body = await resp.body()
    assert body == b"fulfilled one"


async def test_should_fall_back_after_exception(
    page: Page, context: BrowserContext, server: Server
) -> None:
    await context.route("**/empty.html", lambda route: route.continue_())

    async def handler(route: Route) -> None:
        try:
            await route.fulfill(response=cast(Any, {}))
        except Exception:
            await route.fallback()

    await context.route("**/empty.html", handler)

    await page.goto(server.EMPTY_PAGE)


async def test_should_amend_http_headers(
    page: Page, context: BrowserContext, server: Server
) -> None:
    values = []

    async def handler(route: Route) -> None:
        values.append(route.request.headers.get("foo"))
        values.append(await route.request.header_value("FOO"))
        await route.continue_()

    await context.route("**/sleep.zzz", handler)

    async def handler_with_header_mods(route: Route) -> None:
        await route.fallback(headers={**route.request.headers, "FOO": "bar"})

    await context.route("**/*", handler_with_header_mods)

    await page.goto(server.EMPTY_PAGE)
    with server.expect_request("/sleep.zzz") as server_request_info:
        await page.evaluate("() => fetch('/sleep.zzz')")
    values.append(server_request_info.value.getHeader("foo"))
    assert values == ["bar", "bar", "bar"]


async def test_should_delete_header_with_undefined_value(
    page: Page, context: BrowserContext, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    server.set_route(
        "/something",
        lambda r: (
            r.setHeader("Acces-Control-Allow-Origin", "*"),
            r.write(b"done"),
            r.finish(),
        ),
    )

    intercepted_request = []

    async def capture_and_continue(route: Route, request: Request) -> None:
        intercepted_request.append(request)
        await route.continue_()

    await context.route("**/*", capture_and_continue)

    async def delete_foo_header(route: Route, request: Request) -> None:
        headers = await request.all_headers()
        del headers["foo"]
        await route.fallback(headers=headers)

    await context.route(server.PREFIX + "/something", delete_foo_header)

    [server_req, text] = await asyncio.gather(
        server.wait_for_request("/something"),
        page.evaluate(
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
        ),
    )

    assert text == "done"
    assert not intercepted_request[0].headers.get("foo")
    assert intercepted_request[0].headers.get("bar") == "b"
    assert not server_req.getHeader("foo")
    assert server_req.getHeader("bar") == "b"


async def test_should_amend_method(
    page: Page, context: BrowserContext, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)

    method = []

    def _handler1(route: Route) -> None:
        method.append(route.request.method)
        asyncio.create_task(route.continue_())

    await context.route("**/*", _handler1)
    await context.route(
        "**/*", lambda route: asyncio.create_task(route.fallback(method="POST"))
    )

    [request, _] = await asyncio.gather(
        server.wait_for_request("/sleep.zzz"),
        page.evaluate("() => fetch('/sleep.zzz')"),
    )

    assert method == ["POST"]
    assert request.method == b"POST"


async def test_should_override_request_url(
    page: Page, context: BrowserContext, server: Server
) -> None:
    url = []

    def _handler1(route: Route) -> None:
        url.append(route.request.url)
        asyncio.create_task(route.continue_())

    await context.route(
        "**/global-var.html",
        _handler1,
    )

    def _handler2(route: Route) -> None:
        asyncio.create_task(route.fallback(url=server.PREFIX + "/global-var.html"))

    await context.route(
        "**/foo",
        _handler2,
    )

    [server_request, response, _] = await asyncio.gather(
        server.wait_for_request("/global-var.html"),
        page.wait_for_event("response"),
        page.goto(server.PREFIX + "/foo"),
    )

    assert url == [server.PREFIX + "/global-var.html"]
    assert response.url == server.PREFIX + "/global-var.html"
    assert response.request.url == server.PREFIX + "/global-var.html"
    assert await page.evaluate("() => window['globalVar']") == 123
    assert server_request.uri == b"/global-var.html"
    assert server_request.method == b"GET"


async def test_should_amend_post_data(
    page: Page, context: BrowserContext, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    post_data = []

    def _handler1(route: Route) -> None:
        post_data.append(route.request.post_data)
        asyncio.create_task(route.continue_())

    await context.route("**/*", _handler1)
    await context.route(
        "**/*", lambda route: asyncio.create_task(route.fallback(post_data="doggo"))
    )
    [server_request, _] = await asyncio.gather(
        server.wait_for_request("/sleep.zzz"),
        page.evaluate("() => fetch('/sleep.zzz', { method: 'POST', body: 'birdy' })"),
    )
    assert post_data == ["doggo"]
    assert server_request.post_body == b"doggo"


async def test_should_amend_binary_post_data(
    page: Page, context: BrowserContext, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    post_data_buffer = []

    def _handler1(route: Route) -> None:
        post_data_buffer.append(route.request.post_data)
        asyncio.create_task(route.continue_())

    await context.route("**/*", _handler1)

    def _handler2(route: Route) -> None:
        asyncio.create_task(route.fallback(post_data=b"\x00\x01\x02\x03\x04"))

    await context.route("**/*", _handler2)

    [server_request, result] = await asyncio.gather(
        server.wait_for_request("/sleep.zzz"),
        page.evaluate("fetch('/sleep.zzz', { method: 'POST', body: 'birdy' })"),
    )
    # FIXME: should this be bytes?
    assert post_data_buffer == ["\x00\x01\x02\x03\x04"]
    assert server_request.method == b"POST"
    assert server_request.post_body == b"\x00\x01\x02\x03\x04"
