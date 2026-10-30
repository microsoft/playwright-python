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

"""Port of tests/page/page-event-network.spec.ts."""

import asyncio
import re
import threading
from typing import Dict, List, Optional, Union

import pytest

from playwright.async_api import Error, Page, Request, Response
from tests.server import Server, TestServerRequest, reactor


async def test_NE_084_page_events_request_smoke(page: Page, server: Server) -> None:
    requests: List[Request] = []
    page.on("request", lambda request: requests.append(request))
    await page.goto(server.EMPTY_PAGE)
    assert len(requests) == 1
    assert requests[0].url == server.EMPTY_PAGE
    assert requests[0].resource_type == "document"
    assert requests[0].method == "GET"
    assert await requests[0].response()
    assert (requests[0].frame == page.main_frame) is True
    assert requests[0].frame.url == server.EMPTY_PAGE


async def test_NE_085_page_events_response_smoke(page: Page, server: Server) -> None:
    responses: List[Response] = []
    page.on("response", lambda response: responses.append(response))
    await page.goto(server.EMPTY_PAGE)
    assert len(responses) == 1
    assert responses[0].url == server.EMPTY_PAGE
    assert responses[0].status == 200
    assert responses[0].ok is True
    assert responses[0].request


async def test_NE_086_page_events_request_failed_smoke(
    page: Page,
    server: Server,
    browser_name: str,
    platform: str,
    browser_channel: Optional[str],
) -> None:
    def handle(server_request: TestServerRequest) -> None:
        server_request.setHeader("Content-Type", "text/css")
        assert server_request.transport
        server_request.transport.loseConnection()

    server.set_route("/one-style.css", handle)
    failed_requests: List[Request] = []
    page.on("requestfailed", lambda request: failed_requests.append(request))
    await page.goto(server.PREFIX + "/one-style.html")
    assert len(failed_requests) == 1
    assert "one-style.css" in failed_requests[0].url
    assert await failed_requests[0].response() is None
    assert failed_requests[0].resource_type == "stylesheet"
    failure = failed_requests[0].failure
    if browser_name == "chromium":
        assert failure == "net::ERR_EMPTY_RESPONSE"
    elif browser_name == "webkit":
        if platform == "linux" or browser_channel == "webkit-wsl":
            assert failure
            assert re.search(
                r"(Message Corrupt)|(Connection terminated unexpectedly)",
                failure,
                re.IGNORECASE,
            )
        elif platform == "darwin":
            assert failure == "The network connection was lost."
        elif platform == "win32":
            assert failure == "Server returned nothing (no headers, no data)"
    else:
        assert failure == "NS_ERROR_NET_RESET"
    assert failed_requests[0].frame


async def test_NE_087_page_events_request_finished_smoke(
    page: Page, server: Server
) -> None:
    async with page.expect_event("requestfinished"):
        response = await page.goto(server.EMPTY_PAGE)
    assert response
    request = response.request
    assert request.url == server.EMPTY_PAGE
    assert await request.response()
    assert (request.frame == page.main_frame) is True
    assert request.frame.url == server.EMPTY_PAGE
    assert request.failure is None


async def test_NE_088_should_fire_events_in_proper_order(
    page: Page, server: Server
) -> None:
    events: List[str] = []
    page.on("request", lambda request: events.append("request"))
    page.on("response", lambda response: events.append("response"))
    response = await page.goto(server.EMPTY_PAGE)
    assert response
    # Resolves with null (None in Python) once the request finished.
    await response.finished()
    events.append("requestfinished")
    assert events == ["request", "response", "requestfinished"]


async def test_NE_089_should_support_redirects(page: Page, server: Server) -> None:
    FOO_URL = server.PREFIX + "/foo.html"
    events: Dict[str, List[Union[str, int]]] = {}
    events[server.EMPTY_PAGE] = []
    events[FOO_URL] = []
    page.on("request", lambda request: events[request.url].append(request.method))
    page.on("response", lambda response: events[response.url].append(response.status))
    page.on("requestfinished", lambda request: events[request.url].append("DONE"))
    page.on("requestfailed", lambda request: events[request.url].append("FAIL"))

    server.set_redirect("/foo.html", "/empty.html")
    response = await page.goto(FOO_URL)
    assert response
    await response.finished()

    expected: Dict[str, List[Union[str, int]]] = {}
    expected[FOO_URL] = ["GET", 302, "DONE"]
    expected[server.EMPTY_PAGE] = ["GET", 200, "DONE"]
    assert events == expected
    redirected_from = response.request.redirected_from
    assert redirected_from
    assert "/foo.html" in redirected_from.url
    assert redirected_from.redirected_from is None
    assert redirected_from.redirected_to == response.request


async def test_NE_090_should_resolve_responses_after_a_cross_process_navigation(
    page: Page, server: Server, browser_name: str
) -> None:
    responses_from_server: List[TestServerRequest] = []
    server_got_request = threading.Event()

    def handle(server_request: TestServerRequest) -> None:
        responses_from_server.append(server_request)
        server_got_request.set()

    server.set_route("/foo", handle)
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_request(lambda _: True) as request_info:
        # start a long running request and wait until it hits the server
        await page.evaluate("url => void fetch(url)", server.PREFIX + "/foo")
    while not server_got_request.is_set():
        await page.wait_for_timeout(10)
    response_from_server = responses_from_server[0]
    request = await request_info.value
    response_promise = asyncio.create_task(request.response())
    async with page.expect_event("requestfailed") as failed_info:
        # navigate, which should cancel the request
        await page.goto(server.CROSS_PROCESS_PREFIX)

    # make sure we aren't stalling this request on the server
    def end() -> None:
        try:
            response_from_server.write(b"done")
            response_from_server.finish()
        except RuntimeError:
            # The browser has dropped the request. Like res.end() in Node.js, do nothing.
            pass

    reactor.callFromThread(end)
    # the response should resolve to null, because the page navigated.
    assert await response_promise is None
    # the request should fail with the browser's "canceled" error.
    assert await failed_info.value == request
    assert {
        "chromium": "net::ERR_ABORTED",
        "firefox": "NS_BINDING_ABORTED",
        "webkit": "cancelled",
    }[browser_name] in (request.failure or "")


async def test_NE_143_should_resolve_responses_after_a_same_process_navigation(
    page: Page, server: Server, browser_name: str
) -> None:
    responses_from_server: List[TestServerRequest] = []
    server_got_request = threading.Event()

    def handle(server_request: TestServerRequest) -> None:
        responses_from_server.append(server_request)
        server_got_request.set()

    server.set_route("/foo", handle)

    def stream(server_request: TestServerRequest) -> None:
        server_request.setResponseCode(200)
        server_request.setHeader("Content-Type", "text/plain")
        server_request.write(b"partial body")

    server.set_route("/streaming", stream)
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_request(server.PREFIX + "/foo") as request_info:
        async with page.expect_response(
            server.PREFIX + "/streaming"
        ) as streaming_response_info:
            # start a long running request and wait until it hits the server
            await page.evaluate("url => void fetch(url)", server.PREFIX + "/foo")
            # start a request that never finishes streaming its body
            await page.evaluate("url => void fetch(url)", server.PREFIX + "/streaming")
    while not server_got_request.is_set():
        await page.wait_for_timeout(10)
    response_from_server = responses_from_server[0]
    request = await request_info.value
    response_promise = asyncio.create_task(request.response())
    streaming_response = await streaming_response_info.value
    streaming_text_promise = asyncio.create_task(streaming_response.text())
    failed_requests: List[Request] = []
    page.on("requestfailed", lambda request: failed_requests.append(request))
    # navigate within the same process, which should cancel the requests
    await page.goto(server.PREFIX + "/title.html")

    # make sure we aren't stalling this request on the server
    def end() -> None:
        try:
            response_from_server.write(b"done")
            response_from_server.finish()
        except RuntimeError:
            # Python: Node's res.end() also accepts an already dropped request.
            pass

    reactor.callFromThread(end)
    # the response should resolve to null, because the page navigated.
    assert await response_promise is None
    # both requests should fail with the browser's "canceled" error.
    error_text = {
        "chromium": "net::ERR_ABORTED",
        "firefox": "NS_BINDING_ABORTED",
        "webkit": "cancelled",
    }[browser_name]
    assert sorted(request.url for request in failed_requests) == [
        server.PREFIX + "/foo",
        server.PREFIX + "/streaming",
    ]
    assert error_text in (request.failure or "")
    assert error_text in (streaming_response.request.failure or "")
    # the partial body should not be available anymore.
    with pytest.raises(Error) as exc_info:
        await streaming_text_promise
    assert "navigated away" in exc_info.value.message
