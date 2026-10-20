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

"""Python only: tests of behaviors that no upstream test covers."""

import asyncio
from typing import List

from playwright.async_api import Page, Request, Route
from tests.server import Server


async def test_request_fulfill(page: Page, server: Server) -> None:
    async def handle_request(route: Route, request: Request) -> None:
        headers = await route.request.all_headers()
        assert headers["accept"]
        assert route.request == request
        assert repr(route) == f"<Route request={route.request}>"
        assert "empty.html" in request.url
        assert request.headers["user-agent"]
        assert request.method == "GET"
        assert request.post_data is None
        assert request.is_navigation_request()
        assert request.resource_type == "document"
        assert request.frame == page.main_frame
        assert request.frame.url == "about:blank"
        assert (
            repr(request) == f"<Request url={request.url!r} method={request.method!r}>"
        )
        await route.fulfill(body="Text")

    await page.route(
        "**/empty.html",
        lambda route, request: asyncio.create_task(handle_request(route, request)),
    )

    response = await page.goto(server.EMPTY_PAGE)
    assert response

    assert response.ok
    assert (
        repr(response) == f"<Response url={response.url!r} request={response.request}>"
    )
    assert await response.text() == "Text"


async def test_page_events_request_should_accept_method(
    page: Page, server: Server
) -> None:
    class Log:
        def __init__(self) -> None:
            self.requests: List[Request] = []

        def handle(self, request: Request) -> None:
            self.requests.append(request)

    log = Log()
    page.on("request", log.handle)
    await page.goto(server.EMPTY_PAGE)
    assert len(log.requests) == 1


async def test_response_headers_should_work(page: Page, server: Server) -> None:
    server.set_route("/empty.html", lambda r: (r.setHeader("foo", "bar"), r.finish()))

    response = await page.goto(server.EMPTY_PAGE)
    assert response
    assert response.headers["foo"] == "bar"
    assert (await response.all_headers())["foo"] == "bar"
    # Looking up a missing header must not add it.
    assert await response.header_value("x-missing") is None
    assert "x-missing" not in await response.all_headers()


async def test_should_parse_the_json_post_data_when_content_type_header_is_missing(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_request("**/*") as request_info:
        await page.evaluate(
            """({url}) => {
            const request = new Request(url, {
                method: 'POST',
                body: JSON.stringify({ value: 42 }),
            });
            request.headers.delete('content-type');
            return fetch(request);
        }""",
            {"url": server.PREFIX + "/title.html"},
        )
    request = await request_info.value
    assert "content-type" not in request.headers
    assert request.post_data_json == {"value": 42}


async def test_response_security_details_none_without_https(
    page: Page, server: Server
) -> None:
    response = await page.goto(server.EMPTY_PAGE)
    assert response
    security_details = await response.security_details()
    assert security_details is None
