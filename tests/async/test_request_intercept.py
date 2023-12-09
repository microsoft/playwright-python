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
from pathlib import Path

from twisted.web import http

from playwright.async_api import Page, Route
from tests.server import Server


async def test_should_fulfill_intercepted_response(page: Page, server: Server) -> None:
    async def handle(route: Route) -> None:
        response = await page.request.fetch(route.request)
        await route.fulfill(
            response=response,
            status=201,
            headers={"foo": "bar"},
            content_type="text/plain",
            body="Yo, page!",
        )

    await page.route("**/*", handle)
    response = await page.goto(server.PREFIX + "/empty.html")
    assert response
    assert response.status == 201
    assert response.headers["foo"] == "bar"
    assert response.headers["content-type"] == "text/plain"
    assert await page.evaluate("() => document.body.textContent") == "Yo, page!"


async def test_should_fulfill_response_with_empty_body(
    page: Page, server: Server
) -> None:
    async def handle(route: Route) -> None:
        response = await page.request.fetch(route.request)
        await route.fulfill(
            response=response, status=201, body="", headers={"content-length": "0"}
        )

    await page.route("**/*", handle)
    response = await page.goto(server.PREFIX + "/title.html")
    assert response
    assert response.status == 201
    assert await response.text() == ""


async def test_should_override_with_defaults_when_intercepted_response_not_provided(
    page: Page, server: Server, browser_name: str
) -> None:
    def server_handler(request: http.Request) -> None:
        request.setHeader("foo", "bar")
        request.write("my content".encode())
        request.finish()

    server.set_route("/empty.html", server_handler)

    async def handle(route: Route) -> None:
        await page.request.fetch(route.request)
        await route.fulfill(status=201)

    await page.route("**/*", handle)
    response = await page.goto(server.EMPTY_PAGE)
    assert response
    assert response.status == 201
    assert await response.text() == ""
    if browser_name == "webkit":
        assert response.headers == {"content-type": "text/plain"}
    else:
        assert response.headers == {}


async def test_should_fulfill_with_any_response(page: Page, server: Server) -> None:
    def server_handler(request: http.Request) -> None:
        request.setHeader("foo", "bar")
        request.write("Woo-hoo".encode())
        request.finish()

    server.set_route("/sample", server_handler)
    sample_response = await page.request.get(server.PREFIX + "/sample")
    await page.route(
        "**/*",
        lambda route: route.fulfill(
            response=sample_response, status=201, content_type="text/plain"
        ),
    )
    response = await page.goto(server.EMPTY_PAGE)
    assert response
    assert response.status == 201
    assert await response.text() == "Woo-hoo"
    assert response.headers["foo"] == "bar"


async def test_should_support_fulfill_after_intercept(
    page: Page, server: Server, assetdir: Path
) -> None:
    request_future = asyncio.create_task(server.wait_for_request("/title.html"))

    async def handle_route(route: Route) -> None:
        response = await page.request.fetch(route.request)
        await route.fulfill(response=response)

    await page.route("**", handle_route)
    response = await page.goto(server.PREFIX + "/title.html")
    assert response
    request = await request_future
    assert request.uri.decode() == "/title.html"
    original = (assetdir / "title.html").read_text()
    assert await response.text() == original


async def test_should_give_access_to_the_intercepted_response(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)

    route_task: "asyncio.Future[Route]" = asyncio.Future()
    await page.route("**/title.html", lambda route: route_task.set_result(route))

    eval_task = asyncio.create_task(
        page.evaluate("url => fetch(url)", server.PREFIX + "/title.html")
    )

    route = await route_task
    response = await page.request.fetch(route.request)

    assert response.status == 200
    assert response.status_text == "OK"
    assert response.ok is True
    assert response.url.endswith("/title.html") is True
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert list(
        filter(
            lambda header: header["name"].lower() == "content-type",
            response.headers_array,
        )
    ) == [{"name": "Content-Type", "value": "text/html; charset=utf-8"}]

    await asyncio.gather(
        route.fulfill(response=response),
        eval_task,
    )


async def test_should_give_access_to_the_intercepted_response_body(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)

    route_task: "asyncio.Future[Route]" = asyncio.Future()
    await page.route("**/simple.json", lambda route: route_task.set_result(route))

    eval_task = asyncio.create_task(
        page.evaluate("url => fetch(url)", server.PREFIX + "/simple.json")
    )

    route = await route_task
    response = await page.request.fetch(route.request)

    assert await response.text() == '{"foo": "bar"}\n'

    await asyncio.gather(
        route.fulfill(response=response),
        eval_task,
    )
