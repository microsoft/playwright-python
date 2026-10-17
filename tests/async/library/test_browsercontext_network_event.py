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

"""Port of tests/library/browsercontext-network-event.spec.ts."""

import asyncio
from typing import List

import pytest

from playwright.async_api import BrowserContext, Error, Page, Request, Response
from tests.server import Server, TestServerRequest


async def test_NE_121_browser_context_events_request(
    context: BrowserContext, server: Server
) -> None:
    page = await context.new_page()
    requests: List[Request] = []
    context.on("request", lambda request: requests.append(request))
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        '<a target=_blank rel=noopener href="/one-style.html">yo</a>'
    )
    async with context.expect_page() as page_info:
        await page.click("a")
    page1 = await page_info.value
    await page1.wait_for_load_state()
    urls = [r.url for r in requests]
    assert urls == [
        server.EMPTY_PAGE,
        f"{server.PREFIX}/one-style.html",
        f"{server.PREFIX}/one-style.css",
    ]


async def test_NE_122_browser_context_events_response(
    context: BrowserContext, server: Server
) -> None:
    page = await context.new_page()
    responses: List[Response] = []
    context.on("response", lambda response: responses.append(response))
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        '<a target=_blank rel=noopener href="/one-style.html">yo</a>'
    )
    async with context.expect_page() as page_info:
        await page.click("a")
    page1 = await page_info.value
    await page1.wait_for_load_state()
    urls = [r.url for r in responses]
    assert urls == [
        server.EMPTY_PAGE,
        f"{server.PREFIX}/one-style.html",
        f"{server.PREFIX}/one-style.css",
    ]


async def test_NE_123_browser_context_events_request_failed(
    context: BrowserContext, server: Server
) -> None:
    def handle(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "text/css")
        assert request.transport
        request.transport.abortConnection()

    server.set_route("/one-style.css", handle)
    page = await context.new_page()
    failed_requests: List[Request] = []
    context.on("requestfailed", lambda request: failed_requests.append(request))
    await page.goto(server.PREFIX + "/one-style.html")
    assert len(failed_requests) == 1
    assert "one-style.css" in failed_requests[0].url
    assert await failed_requests[0].response() is None
    assert failed_requests[0].resource_type == "stylesheet"
    assert failed_requests[0].frame


async def test_NE_124_browser_context_events_request_finished(
    context: BrowserContext, server: Server
) -> None:
    page = await context.new_page()
    async with context.expect_event("requestfinished"):
        response = await page.goto(server.EMPTY_PAGE)
    assert response
    request = response.request
    assert request.url == server.EMPTY_PAGE
    assert await request.response()
    assert request.frame == page.main_frame
    assert request.frame.url == server.EMPTY_PAGE
    assert request.failure is None


async def test_NE_125_should_fire_events_in_proper_order(
    context: BrowserContext, server: Server
) -> None:
    page = await context.new_page()
    events: List[str] = []
    context.on("request", lambda _: events.append("request"))
    context.on("response", lambda _: events.append("response"))
    context.on("requestfinished", lambda _: events.append("requestfinished"))
    async with context.expect_event("requestfinished"):
        await page.goto(server.EMPTY_PAGE)
    assert events == [
        "request",
        "response",
        "requestfinished",
    ]


async def test_NE_126_should_not_fire_events_for_favicon_or_favicon_redirects(
    context: BrowserContext,
    page: Page,
    server: Server,
    browser_name: str,
    headless: bool,
) -> None:
    if headless and browser_name != "firefox":
        pytest.skip("headless browsers, except firefox, do not request favicons")
    if not headless and browser_name == "webkit":
        pytest.skip("headed webkit does not have a favicon feature")
    favicon = "/no-cache/favicon.ico"
    hashed_favicon_url = "/favicon-hashed.ico"
    image_path = "/fakeimage.png"
    page_path = "/page.html"
    server.set_redirect(favicon, hashed_favicon_url)

    def handle_page(request: TestServerRequest) -> None:
        request.write(
            f"""
      <!DOCTYPE html>
      <html>
        <head>
          <meta charset="utf-8">
          <link rel="icon" type="image/svg+xml" href="{favicon}">
          <title>SVG Favicon Test</title>
        </head>
        <body>
          <img src="{image_path}" alt="my fake image">
        </body>
      </html>
""".encode()
        )
        request.finish()

    server.set_route(page_path, handle_page)

    events: List[str] = []
    context.on("request", lambda req: events.append(req.url))
    context.on("response", lambda res: events.append(res.url))
    context.on("requestfinished", lambda req: events.append(req.url))

    await asyncio.gather(
        server.wait_for_request(favicon),
        server.wait_for_request(hashed_favicon_url),
        page.goto(server.PREFIX + "/page.html"),
    )

    assert any(page_path in event for event in events)
    assert any(image_path in event for event in events)
    assert not any(favicon in event for event in events)
    assert not any(hashed_favicon_url in event for event in events)


async def test_NE_127_should_reject_response_finished_if_context_closes(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)

    def handle(request: TestServerRequest) -> None:
        # In Firefox, |fetch| will be hanging until it receives |Content-Type| header
        # from server.
        request.setHeader("Content-Type", "text/plain; charset=utf-8")
        request.write(b"hello ")

    server.set_route("/get", handle)
    # send request and wait for server response
    async with page.expect_event("response") as response_info:
        await page.evaluate("() => fetch('./get', { method: 'GET' })")
    page_response = await response_info.value

    finish_task = asyncio.create_task(page_response.finished())
    await page.context.close()
    with pytest.raises(Error) as exc_info:
        await finish_task
    assert "closed" in exc_info.value.message
