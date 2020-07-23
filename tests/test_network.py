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
import json
import os
from asyncio.futures import Future
from typing import Dict, List

import pytest

from playwright.helper import Error
from playwright.network import Request
from playwright.page import Page


async def test_request_fulfill(page):
    async def handle_request(route, request):
        assert route.request == request
        assert "empty.html" in request.url
        assert request.headers["user-agent"]
        assert request.method == "GET"
        assert request.postData is None
        assert request.isNavigationRequest
        assert request.resourceType == "document"
        assert request.frame == page.mainFrame
        assert request.frame.url == "about:blank"
        await route.fulfill(body="Text")

    await page.route(
        "**/empty.html",
        lambda route, request: asyncio.create_task(handle_request(route, request)),
    )

    response = await page.goto("http://www.non-existent.com/empty.html")
    assert response.ok
    assert await response.text() == "Text"


async def test_request_continue(page, server):
    async def handle_request(route, request, intercepted):
        intercepted.append(True)
        await route.continue_()

    intercepted = list()
    await page.route(
        "**/*",
        lambda route, request: asyncio.create_task(
            handle_request(route, request, intercepted)
        ),
    )

    response = await page.goto(server.EMPTY_PAGE)
    assert response.ok
    assert intercepted == [True]
    assert await page.title() == ""


async def test_page_events_request_should_fire_for_navigation_requests(
    page: Page, server
):
    requests = []
    page.on("request", lambda r: requests.append(r))
    await page.goto(server.EMPTY_PAGE)
    assert len(requests) == 1


async def test_page_events_request_should_fire_for_iframes(page, server, utils):
    requests = []
    page.on("request", lambda r: requests.append(r))
    await page.goto(server.EMPTY_PAGE)
    await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    assert len(requests) == 2


async def test_page_events_request_should_fire_for_fetches(page, server):
    requests = []
    page.on("request", lambda r: requests.append(r))
    await page.goto(server.EMPTY_PAGE)
    await page.evaluate('() => fetch("/empty.html")')
    assert len(requests) == 2


@pytest.mark.skip("sometimes hanging")  # TODO: needs to be investigated
async def test_page_events_request_should_report_requests_and_responses_handled_by_service_worker(
    page: Page, server
):
    await page.goto(server.PREFIX + "/serviceworkers/fetchdummy/sw.html")
    await page.evaluate("() => window.activationPromise")
    [request, sw_response] = await asyncio.gather(
        page.waitForEvent("request"), page.evaluate('() => fetchDummy("foo")')
    )
    assert sw_response == "responseFromServiceWorker:foo"
    assert request.url == server.PREFIX + "/serviceworkers/fetchdummy/foo"
    response = await request.response()
    assert response.url == server.PREFIX + "/serviceworkers/fetchdummy/foo"
    assert await response.text() == "responseFromServiceWorker:foo"


async def test_request_frame_should_work_for_main_frame_navigation_request(
    page, server
):
    requests = []
    page.on("request", lambda r: requests.append(r))
    await page.goto(server.EMPTY_PAGE)
    assert len(requests) == 1
    assert requests[0].frame == page.mainFrame


async def test_request_frame_should_work_for_subframe_navigation_request(
    page, server, utils
):
    await page.goto(server.EMPTY_PAGE)
    requests = []
    page.on("request", lambda r: requests.append(r))
    await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    assert len(requests) == 1
    assert requests[0].frame == page.frames[1]


async def test_request_frame_should_work_for_fetch_requests(page, server):
    await page.goto(server.EMPTY_PAGE)
    requests: List[Request] = []
    page.on("request", lambda r: requests.append(r))
    await page.evaluate('() => fetch("/digits/1.png")')
    requests = [r for r in requests if "favicon" not in r.url]
    assert len(requests) == 1
    assert requests[0].frame == page.mainFrame


async def test_request_headers_should_work(
    page, server, is_chromium, is_firefox, is_webkit
):
    response = await page.goto(server.EMPTY_PAGE)
    if is_chromium:
        assert "Chrome" in response.request.headers["user-agent"]
    elif is_firefox:
        assert "Firefox" in response.request.headers["user-agent"]
    elif is_webkit:
        assert "WebKit" in response.request.headers["user-agent"]


@pytest.mark.only_browser("firefox")
async def test_request_headers_should_get_the_same_headers_as_the_server(
    page: Page, server
):
    await page.goto(server.PREFIX + "/empty.html")
    server_request_headers_future: Future[Dict[str, str]] = asyncio.Future()

    def handle_something(request):
        normalized_headers = {
            key.decode().lower(): value[0].decode()
            for key, value in request.requestHeaders.getAllRawHeaders()
        }
        server_request_headers_future.set_result(normalized_headers)
        request.setHeader("Access-Control-Allow-Origin", "*")
        request.write(b"done")
        request.finish()

    server.set_route("/something", handle_something)

    requestPromise = asyncio.create_task(page.waitForEvent("request"))
    text = await page.evaluate(
        """async url => {
      const data = await fetch(url);
      return data.text();
    }""",
        server.CROSS_PROCESS_PREFIX + "/something",
    )
    request: Request = await requestPromise
    assert text == "done"
    server_headers = await server_request_headers_future
    assert request.headers == server_headers


async def test_response_headers_should_work(page, server):
    server.set_route("/empty.html", lambda r: (r.setHeader("foo", "bar"), r.finish()))

    response = await page.goto(server.EMPTY_PAGE)
    assert response.headers["foo"] == "bar"


async def test_request_postdata_should_work(page, server):
    await page.goto(server.EMPTY_PAGE)
    server.set_route("/post", lambda r: r.finish())
    requests = []
    page.on("request", lambda r: requests.append(r))
    await page.evaluate(
        '() => fetch("./post", { method: "POST", body: JSON.stringify({foo: "bar"})})'
    )
    assert len(requests) == 1
    assert requests[0].postData == '{"foo":"bar"}'


async def test_request_postdata_should_be_undefined_when_there_is_no_post_data(
    page, server
):
    response = await page.goto(server.EMPTY_PAGE)
    assert response.request.postData is None


async def test_response_text_should_work(page, server):
    response = await page.goto(server.PREFIX + "/simple.json")
    assert await response.text() == '{"foo": "bar"}\n'


async def test_response_text_should_return_uncompressed_text(page, server):
    server.enable_gzip("/simple.json")
    response = await page.goto(server.PREFIX + "/simple.json")
    assert response.headers["content-encoding"] == "gzip"
    assert await response.text() == '{"foo": "bar"}\n'


async def test_response_text_should_throw_when_requesting_body_of_redirected_response(
    page, server
):
    server.set_redirect("/foo.html", "/empty.html")
    response = await page.goto(server.PREFIX + "/foo.html")
    redirectedFrom = response.request.redirectedFrom
    assert redirectedFrom
    redirected = await redirectedFrom.response()
    assert redirected.status == 302
    error = None
    try:
        await redirected.text()
    except Error as exc:
        error = exc
    assert "Response body is unavailable for redirect responses" in error.message


async def test_response_json_should_work(page, server):
    response = await page.goto(server.PREFIX + "/simple.json")
    assert await response.json() == {"foo": "bar"}


async def test_response_body_should_work(page, server):
    response = await page.goto(server.PREFIX + "/pptr.png")
    with open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets/pptr.png"),
        "rb",
    ) as fd:
        assert fd.read() == await response.body()


async def test_response_body_should_work_with_compression(page, server):
    server.enable_gzip("/pptr.png")
    response = await page.goto(server.PREFIX + "/pptr.png")
    with open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets/pptr.png"),
        "rb",
    ) as fd:
        assert fd.read() == await response.body()


async def test_response_status_text_should_work(page, server):
    server.set_route("/cool", lambda r: (r.setResponseCode(200, b"cool!"), r.finish()))

    response = await page.goto(server.PREFIX + "/cool")
    assert response.statusText == "cool!"


async def test_request_resource_type_should_return_event_source(page, server):
    SSE_MESSAGE = {"foo": "bar"}
    # 1. Setup server-sent events on server that immediately sends a message to the client.
    server.set_route(
        "/sse",
        lambda r: (
            r.setHeader("Content-Type", "text/event-stream"),
            r.setHeader("Connection", "keep-alive"),
            r.setHeader("Cache-Control", "no-cache"),
            r.setResponseCode(200),
            r.write(f"data: {json.dumps(SSE_MESSAGE)}\n\n".encode()),
            r.finish(),
        ),
    )

    # 2. Subscribe to page request events.
    await page.goto(server.EMPTY_PAGE)
    requests = []
    page.on("request", lambda r: requests.append(r))
    # 3. Connect to EventSource in browser and return first message.
    assert (
        await page.evaluate(
            """() => {
      const eventSource = new EventSource('/sse');
      return new Promise(resolve => {
        eventSource.onmessage = e => resolve(JSON.parse(e.data));
      });
    }"""
        )
        == SSE_MESSAGE
    )
    assert requests[0].resourceType == "eventsource"


async def test_network_events_request(page, server):
    requests = []
    page.on("request", lambda r: requests.append(r))
    await page.goto(server.EMPTY_PAGE)
    assert len(requests) == 1
    assert requests[0].url == server.EMPTY_PAGE
    assert requests[0].resourceType == "document"
    assert requests[0].method == "GET"
    assert await requests[0].response()
    assert requests[0].frame == page.mainFrame
    assert requests[0].frame.url == server.EMPTY_PAGE


async def test_network_events_response(page, server):
    responses = []
    page.on("response", lambda r: responses.append(r))
    await page.goto(server.EMPTY_PAGE)
    assert len(responses) == 1
    assert responses[0].url == server.EMPTY_PAGE
    assert responses[0].status == 200
    assert responses[0].ok
    assert responses[0].request


async def test_network_events_request_failed(
    page, server, is_chromium, is_webkit, is_firefox, is_mac, is_win
):
    def handle_request(request):
        request.setHeader("Content-Type", "text/css")
        request.transport.loseConnection()

    server.set_route("/one-style.css", handle_request)

    failed_requests = []
    page.on("requestfailed", lambda request: failed_requests.append(request))
    await page.goto(server.PREFIX + "/one-style.html")
    assert len(failed_requests) == 1
    assert "one-style.css" in failed_requests[0].url
    assert await failed_requests[0].response() is None
    assert failed_requests[0].resourceType == "stylesheet"
    if is_chromium:
        assert failed_requests[0].failure == "net::ERR_EMPTY_RESPONSE"
    elif is_webkit:
        if is_mac:
            assert failed_requests[0].failure == "The network connection was lost."
        elif is_win:
            assert (
                failed_requests[0].failure
                == "Server returned nothing (no headers, no data)"
            )
        else:
            assert failed_requests[0].failure == "Message Corrupt"
    else:
        assert failed_requests[0].failure == "NS_ERROR_NET_RESET"
    assert failed_requests[0].frame


async def test_network_events_request_finished(page, server):
    response = (
        await asyncio.gather(
            page.goto(server.EMPTY_PAGE), page.waitForEvent("requestfinished")
        )
    )[0]
    request = response.request
    assert request.url == server.EMPTY_PAGE
    assert await request.response()
    assert request.frame == page.mainFrame
    assert request.frame.url == server.EMPTY_PAGE


async def test_network_events_should_fire_events_in_proper_order(page, server):
    events = []
    page.on("request", lambda request: events.append("request"))
    page.on("response", lambda response: events.append("response"))
    response = await page.goto(server.EMPTY_PAGE)
    await response.finished()
    events.append("requestfinished")
    assert events == ["request", "response", "requestfinished"]


async def test_network_events_should_support_redirects(page, server):
    events = []
    page.on("request", lambda request: events.append(f"{request.method} {request.url}"))
    page.on(
        "response", lambda response: events.append(f"{response.status} {response.url}")
    )
    page.on("requestfinished", lambda request: events.append(f"DONE {request.url}"))
    page.on("requestfailed", lambda request: events.append(f"FAIL {request.url}"))
    server.set_redirect("/foo.html", "/empty.html")
    FOO_URL = server.PREFIX + "/foo.html"
    response = await page.goto(FOO_URL)
    await response.finished()
    assert events == [
        f"GET {FOO_URL}",
        f"302 {FOO_URL}",
        f"DONE {FOO_URL}",
        f"GET {server.EMPTY_PAGE}",
        f"200 {server.EMPTY_PAGE}",
        f"DONE {server.EMPTY_PAGE}",
    ]
    redirectedFrom = response.request.redirectedFrom
    assert "/foo.html" in redirectedFrom.url
    assert redirectedFrom.redirectedFrom is None
    assert redirectedFrom.redirectedTo == response.request


async def test_request_is_navigation_request_should_work(page, server):
    pytest.skip(msg="test")
    requests = {}

    def handle_request(request):
        requests[request.url().split("/").pop()] = request

    page.on("request", handle_request)
    server.set_redirect("/rrredirect", "/frames/one-frame.html")
    await page.goto(server.PREFIX + "/rrredirect")
    print("kek")
    assert requests.get("rrredirect").isNavigationRequest
    assert requests.get("one-frame.html").isNavigationRequest
    assert requests.get("frame.html").isNavigationRequest
    assert requests.get("script.js").isNavigationRequest is False
    assert requests.get("style.css").isNavigationRequest is False


async def test_request_is_navigation_request_should_work_when_navigating_to_image(
    page, server
):
    requests = []
    page.on("request", lambda r: requests.append(r))
    await page.goto(server.PREFIX + "/pptr.png")
    assert requests[0].isNavigationRequest()


async def test_set_extra_http_headers_should_work(page, server):
    await page.setExtraHTTPHeaders({"foo": "bar"})

    request = (
        await asyncio.gather(
            server.wait_for_request("/empty.html"), page.goto(server.EMPTY_PAGE),
        )
    )[0]
    assert request.getHeader("foo") == "bar"


async def test_set_extra_http_headers_should_work_with_redirects(page, server):
    server.set_redirect("/foo.html", "/empty.html")
    await page.setExtraHTTPHeaders({"foo": "bar"})

    request = (
        await asyncio.gather(
            server.wait_for_request("/empty.html"),
            page.goto(server.PREFIX + "/foo.html"),
        )
    )[0]
    assert request.getHeader("foo") == "bar"


async def test_set_extra_http_headers_should_work_with_extra_headers_from_browser_context(
    browser, server
):
    context = await browser.newContext()
    await context.setExtraHTTPHeaders({"foo": "bar"})

    page = await context.newPage()
    request = (
        await asyncio.gather(
            server.wait_for_request("/empty.html"), page.goto(server.EMPTY_PAGE),
        )
    )[0]
    await context.close()
    assert request.getHeader("foo") == "bar"


async def test_set_extra_http_headers_should_override_extra_headers_from_browser_context(
    browser, server
):
    context = await browser.newContext(extraHTTPHeaders={"fOo": "bAr", "baR": "foO"})

    page = await context.newPage()
    await page.setExtraHTTPHeaders({"Foo": "Bar"})

    request = (
        await asyncio.gather(
            server.wait_for_request("/empty.html"), page.goto(server.EMPTY_PAGE),
        )
    )[0]
    await context.close()
    assert request.getHeader("foo") == "Bar"
    assert request.getHeader("bar") == "foO"


async def test_set_extra_http_headers_should_throw_for_non_string_header_values(
    page, server
):
    error = None
    try:
        await page.setExtraHTTPHeaders({"foo": 1})
    except Error as exc:
        error = exc
    assert (
        error.message
        == 'Expected value of header "foo" to be String, but "number" is found.'
    )
