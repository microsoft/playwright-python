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

import re
import threading
from typing import Callable, Dict, List, Optional, Union

import pytest

from playwright.sync_api import Error, Page, Request, Response
from tests.server import Server, TestServerRequest, reactor


def test_NE_084_page_events_request_smoke(page: Page, server: Server) -> None:
    requests: List[Request] = []
    page.on("request", lambda request: requests.append(request))
    page.goto(server.EMPTY_PAGE)
    assert len(requests) == 1
    assert requests[0].url == server.EMPTY_PAGE
    assert requests[0].resource_type == "document"
    assert requests[0].method == "GET"
    assert requests[0].response()
    assert (requests[0].frame == page.main_frame) is True
    assert requests[0].frame.url == server.EMPTY_PAGE


def test_NE_085_page_events_response_smoke(page: Page, server: Server) -> None:
    responses: List[Response] = []
    page.on("response", lambda response: responses.append(response))
    page.goto(server.EMPTY_PAGE)
    assert len(responses) == 1
    assert responses[0].url == server.EMPTY_PAGE
    assert responses[0].status == 200
    assert responses[0].ok is True
    assert responses[0].request


def test_NE_086_page_events_request_failed_smoke(
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
    page.goto(server.PREFIX + "/one-style.html")
    assert len(failed_requests) == 1
    assert "one-style.css" in failed_requests[0].url
    assert failed_requests[0].response() is None
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


def test_NE_087_page_events_request_finished_smoke(page: Page, server: Server) -> None:
    with page.expect_event("requestfinished"):
        response = page.goto(server.EMPTY_PAGE)
    assert response
    request = response.request
    assert request.url == server.EMPTY_PAGE
    assert request.response()
    assert (request.frame == page.main_frame) is True
    assert request.frame.url == server.EMPTY_PAGE
    assert request.failure is None


def test_NE_088_should_fire_events_in_proper_order(page: Page, server: Server) -> None:
    events: List[str] = []
    page.on("request", lambda request: events.append("request"))
    page.on("response", lambda response: events.append("response"))
    response = page.goto(server.EMPTY_PAGE)
    assert response
    # Resolves with null (None in Python) once the request finished.
    response.finished()
    events.append("requestfinished")
    assert events == ["request", "response", "requestfinished"]


def test_NE_089_should_support_redirects(page: Page, server: Server) -> None:
    FOO_URL = server.PREFIX + "/foo.html"
    events: Dict[str, List[Union[str, int]]] = {}
    events[server.EMPTY_PAGE] = []
    events[FOO_URL] = []
    page.on("request", lambda request: events[request.url].append(request.method))
    page.on("response", lambda response: events[response.url].append(response.status))
    page.on("requestfinished", lambda request: events[request.url].append("DONE"))
    page.on("requestfailed", lambda request: events[request.url].append("FAIL"))

    server.set_redirect("/foo.html", "/empty.html")
    response = page.goto(FOO_URL)
    assert response
    response.finished()

    expected: Dict[str, List[Union[str, int]]] = {}
    expected[FOO_URL] = ["GET", 302, "DONE"]
    expected[server.EMPTY_PAGE] = ["GET", 200, "DONE"]
    assert events == expected
    redirected_from = response.request.redirected_from
    assert redirected_from
    assert "/foo.html" in redirected_from.url
    assert redirected_from.redirected_from is None
    assert redirected_from.redirected_to == response.request


def test_NE_090_should_resolve_responses_after_a_cross_process_navigation(
    page: Page, server: Server, browser_name: str, sync_gather: Callable
) -> None:
    responses_from_server: List[TestServerRequest] = []
    server_got_request = threading.Event()

    def handle(server_request: TestServerRequest) -> None:
        responses_from_server.append(server_request)
        server_got_request.set()

    server.set_route("/foo", handle)
    page.goto(server.EMPTY_PAGE)
    with page.expect_request(lambda _: True) as request_info:
        # start a long running request and wait until it hits the server
        page.evaluate("url => void fetch(url)", server.PREFIX + "/foo")
    while not server_got_request.is_set():
        page.wait_for_timeout(10)
    response_from_server = responses_from_server[0]
    request = request_info.value

    def end() -> None:
        try:
            response_from_server.write(b"done")
            response_from_server.finish()
        except RuntimeError:
            # The browser has dropped the request. Like res.end() in Node.js, do nothing.
            pass

    def navigate() -> None:
        # navigate, which should cancel the request
        page.goto(server.CROSS_PROCESS_PREFIX)
        # make sure we aren't stalling this request on the server
        reactor.callFromThread(end)

    # Ask for the response first, then navigate.
    with page.expect_event("requestfailed") as failed_info:
        response, _ = sync_gather(lambda: request.response(), navigate)
    # the response should resolve to null, because the page navigated.
    assert response is None
    # the request should fail with the browser's "canceled" error.
    assert failed_info.value == request
    assert {
        "chromium": "net::ERR_ABORTED",
        "firefox": "NS_BINDING_ABORTED",
        "webkit": "cancelled",
    }[browser_name] in (request.failure or "")


def test_NE_143_should_resolve_responses_after_a_same_process_navigation(
    page: Page, server: Server, browser_name: str, sync_gather: Callable
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
    page.goto(server.EMPTY_PAGE)
    with page.expect_request(server.PREFIX + "/foo") as request_info:
        with page.expect_response(
            server.PREFIX + "/streaming"
        ) as streaming_response_info:
            # start a long running request and wait until it hits the server
            page.evaluate("url => void fetch(url)", server.PREFIX + "/foo")
            # start a request that never finishes streaming its body
            page.evaluate("url => void fetch(url)", server.PREFIX + "/streaming")
    while not server_got_request.is_set():
        page.wait_for_timeout(10)
    response_from_server = responses_from_server[0]
    request = request_info.value
    streaming_response = streaming_response_info.value

    def streaming_text_error() -> Error:
        with pytest.raises(Error) as exc_info:
            streaming_response.text()
        return exc_info.value

    failed_requests: List[Request] = []

    def end() -> None:
        try:
            response_from_server.write(b"done")
            response_from_server.finish()
        except RuntimeError:
            # Python: Node's res.end() also accepts an already dropped request.
            pass

    def navigate() -> None:
        page.on("requestfailed", lambda request: failed_requests.append(request))
        # navigate within the same process, which should cancel the requests
        page.goto(server.PREFIX + "/title.html")
        # make sure we aren't stalling this request on the server
        reactor.callFromThread(end)

    # Python: start the response and body waits before the navigation.
    response, streaming_error, _ = sync_gather(
        lambda: request.response(), streaming_text_error, navigate
    )
    # the response should resolve to null, because the page navigated.
    assert response is None
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
    assert "navigated away" in streaming_error.message
