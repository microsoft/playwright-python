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
from asyncio import Future
from pathlib import Path
from typing import Dict, List, Optional, Union

import pytest
from flaky import flaky
from twisted.web import http

from playwright.async_api import Browser, Error, Page, Request, Response, Route
from tests.server import Server, TestServerRequest

from .utils import Utils


def adjust_server_headers(headers: Dict[str, str], browser_name: str) -> Dict[str, str]:
    if browser_name != "firefox":
        return headers
    headers = headers.copy()
    headers.pop("priority", None)
    return headers


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


async def test_request_continue(page: Page, server: Server) -> None:
    async def handle_request(
        route: Route, request: Request, intercepted: List[bool]
    ) -> None:
        intercepted.append(True)
        await route.continue_()

    intercepted: List[bool] = []
    await page.route(
        "**/*",
        lambda route, request: asyncio.create_task(
            handle_request(route, request, intercepted)
        ),
    )

    response = await page.goto(server.EMPTY_PAGE)
    assert response
    assert response.ok
    assert intercepted == [True]
    assert await page.title() == ""


async def test_page_events_request_should_fire_for_navigation_requests(
    page: Page, server: Server
) -> None:
    requests = []
    page.on("request", lambda r: requests.append(r))
    await page.goto(server.EMPTY_PAGE)
    assert len(requests) == 1


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


async def test_page_events_request_should_fire_for_iframes(
    page: Page, server: Server, utils: Utils
) -> None:
    requests = []
    page.on("request", lambda r: requests.append(r))
    await page.goto(server.EMPTY_PAGE)
    await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    assert len(requests) == 2


async def test_page_events_request_should_fire_for_fetches(
    page: Page, server: Server
) -> None:
    requests = []
    page.on("request", lambda r: requests.append(r))
    await page.goto(server.EMPTY_PAGE)
    await page.evaluate('() => fetch("/empty.html")')
    assert len(requests) == 2


async def test_page_events_request_should_report_requests_and_responses_handled_by_service_worker(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/serviceworkers/fetchdummy/sw.html")
    await page.evaluate("() => window.activationPromise")
    sw_response = None
    async with page.expect_request("**/*") as request_info:
        sw_response = await page.evaluate('() => fetchDummy("foo")')
    request = await request_info.value
    assert sw_response == "responseFromServiceWorker:foo"
    assert request.url == server.PREFIX + "/serviceworkers/fetchdummy/foo"
    response = await request.response()
    assert response
    assert response.url == server.PREFIX + "/serviceworkers/fetchdummy/foo"
    assert await response.text() == "responseFromServiceWorker:foo"


async def test_request_frame_should_work_for_main_frame_navigation_request(
    page: Page, server: Server
) -> None:
    requests = []
    page.on("request", lambda r: requests.append(r))
    await page.goto(server.EMPTY_PAGE)
    assert len(requests) == 1
    assert requests[0].frame == page.main_frame


async def test_request_frame_should_work_for_subframe_navigation_request(
    page: Page, server: Server, utils: Utils
) -> None:
    await page.goto(server.EMPTY_PAGE)
    requests = []
    page.on("request", lambda r: requests.append(r))
    await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    assert len(requests) == 1
    assert requests[0].frame == page.frames[1]


async def test_request_frame_should_work_for_fetch_requests(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    requests: List[Request] = []
    page.on("request", lambda r: requests.append(r))
    await page.evaluate('() => fetch("/digits/1.png")')
    requests = [r for r in requests if "favicon" not in r.url]
    assert len(requests) == 1
    assert requests[0].frame == page.main_frame


async def test_request_headers_should_work(
    page: Page, server: Server, is_chromium: bool, is_firefox: bool, is_webkit: bool
) -> None:
    response = await page.goto(server.EMPTY_PAGE)
    assert response
    if is_chromium:
        assert "Chrome" in response.request.headers["user-agent"]
    elif is_firefox:
        assert "Firefox" in response.request.headers["user-agent"]
    elif is_webkit:
        assert "WebKit" in response.request.headers["user-agent"]


async def test_request_headers_should_get_the_same_headers_as_the_server(
    page: Page,
    server: Server,
    is_webkit: bool,
    is_win: bool,
    browser_name: str,
) -> None:
    if is_webkit and is_win:
        pytest.xfail("Curl does not show accept-encoding and accept-language")
    server_request_headers_future: Future[Dict[str, str]] = asyncio.Future()

    def handle(request: http.Request) -> None:
        normalized_headers = {
            key.decode().lower(): value[0].decode()
            for key, value in request.requestHeaders.getAllRawHeaders()
        }
        server_request_headers_future.set_result(normalized_headers)
        request.write(b"done")
        request.finish()

    server.set_route("/empty.html", handle)
    response = await page.goto(server.EMPTY_PAGE)
    assert response
    server_headers = adjust_server_headers(
        await server_request_headers_future, browser_name
    )
    assert await response.request.all_headers() == server_headers


async def test_request_headers_should_get_the_same_headers_as_the_server_cors(
    page: Page, server: Server, is_webkit: bool, is_win: bool, browser_name: str
) -> None:
    if is_webkit and is_win:
        pytest.xfail("Curl does not show accept-encoding and accept-language")
    await page.goto(server.PREFIX + "/empty.html")
    server_request_headers_future: Future[Dict[str, str]] = asyncio.Future()

    def handle_something(request: http.Request) -> None:
        normalized_headers = {
            key.decode().lower(): value[0].decode()
            for key, value in request.requestHeaders.getAllRawHeaders()
        }
        server_request_headers_future.set_result(normalized_headers)
        request.setHeader("Access-Control-Allow-Origin", "*")
        request.write(b"done")
        request.finish()

    server.set_route("/something", handle_something)

    text = None
    async with page.expect_request("**/*") as request_info:
        text = await page.evaluate(
            """async url => {
                const data = await fetch(url);
                return data.text();
            }""",
            server.CROSS_PROCESS_PREFIX + "/something",
        )
    request = await request_info.value
    assert text == "done"
    server_headers = adjust_server_headers(
        await server_request_headers_future, browser_name
    )
    assert await request.all_headers() == server_headers


async def test_should_report_request_headers_array(
    page: Page, server: Server, is_win: bool, browser_name: str
) -> None:
    if is_win and browser_name == "webkit":
        pytest.skip("libcurl does not support non-set-cookie multivalue headers")
    expected_headers = []

    def handle(request: http.Request) -> None:
        for name, values in request.requestHeaders.getAllRawHeaders():
            for value in values:
                if browser_name == "firefox" and name.decode().lower() == "priority":
                    continue
                expected_headers.append(
                    {"name": name.decode().lower(), "value": value.decode()}
                )
        request.finish()

    server.set_route("/headers", handle)
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_request("*/**") as request_info:
        await page.evaluate(
            """() => fetch('/headers', {
            headers: [
                ['header-a', 'value-a'],
                ['header-b', 'value-b'],
                ['header-a', 'value-a-1'],
                ['header-a', 'value-a-2'],
            ]
            })
        """
        )
    request = await request_info.value
    sorted_pw_request_headers = sorted(
        list(
            map(
                lambda header: {
                    "name": header["name"].lower(),
                    "value": header["value"],
                },
                await request.headers_array(),
            )
        ),
        key=lambda header: header["name"],
    )
    sorted_expected_headers = sorted(
        expected_headers, key=lambda header: header["name"]
    )
    assert sorted_pw_request_headers == sorted_expected_headers
    assert await request.header_value("Header-A") == "value-a, value-a-1, value-a-2"
    assert await request.header_value("not-there") is None


async def test_should_report_response_headers_array(
    page: Page, server: Server, is_win: bool, browser_name: str
) -> None:
    if is_win and browser_name == "webkit":
        pytest.skip("libcurl does not support non-set-cookie multivalue headers")
    expected_headers = {
        "header-a": ["value-a", "value-a-1", "value-a-2"],
        "header-b": ["value-b"],
        "set-cookie": ["a=b", "c=d"],
    }

    def handle(request: http.Request) -> None:
        for key in expected_headers:
            for value in expected_headers[key]:
                request.responseHeaders.addRawHeader(key, value)
        request.finish()

    server.set_route("/headers", handle)
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_response("*/**") as response_info:
        await page.evaluate(
            """() => fetch('/headers')
        """
        )
    response = await response_info.value
    actual_headers: Dict[str, List[str]] = {}
    for header in await response.headers_array():
        name = header["name"].lower()
        value = header["value"]
        if not actual_headers.get(name):
            actual_headers[name] = []
        actual_headers[name].append(value)

    for key in ["Keep-Alive", "Connection", "Date", "Transfer-Encoding"]:
        if key in actual_headers:
            actual_headers.pop(key)
        if key.lower() in actual_headers:
            actual_headers.pop(key.lower())
    assert actual_headers == expected_headers
    assert await response.header_value("not-there") is None
    assert await response.header_value("set-cookie") == "a=b\nc=d"
    assert await response.header_value("header-a") == "value-a, value-a-1, value-a-2"
    assert await response.header_values("set-cookie") == ["a=b", "c=d"]


async def test_response_headers_should_work(page: Page, server: Server) -> None:
    server.set_route("/empty.html", lambda r: (r.setHeader("foo", "bar"), r.finish()))

    response = await page.goto(server.EMPTY_PAGE)
    assert response
    assert response.headers["foo"] == "bar"
    assert (await response.all_headers())["foo"] == "bar"


async def test_request_post_data_should_work(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    server.set_route("/post", lambda r: r.finish())
    requests = []
    page.on("request", lambda r: requests.append(r))
    await page.evaluate(
        '() => fetch("./post", { method: "POST", body: JSON.stringify({foo: "bar"})})'
    )
    assert len(requests) == 1
    assert requests[0].post_data == '{"foo":"bar"}'


async def test_request_post_data__should_be_undefined_when_there_is_no_post_data(
    page: Page, server: Server
) -> None:
    response = await page.goto(server.EMPTY_PAGE)
    assert response
    assert response.request.post_data is None


async def test_should_parse_the_json_post_data(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    server.set_route("/post", lambda req: req.finish())
    requests = []
    page.on("request", lambda r: requests.append(r))
    await page.evaluate(
        """() => fetch('./post', { method: 'POST', body: JSON.stringify({ foo: 'bar' }) })"""
    )
    assert len(requests) == 1
    assert requests[0].post_data_json == {"foo": "bar"}


async def test_should_parse_the_data_if_content_type_is_form_urlencoded(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    server.set_route("/post", lambda req: req.finish())
    requests = []
    page.on("request", lambda r: requests.append(r))
    await page.set_content(
        """<form method='POST' action='/post'><input type='text' name='foo' value='bar'><input type='number' name='baz' value='123'><input type='submit'></form>"""
    )
    await page.click("input[type=submit]")
    assert len(requests) == 1
    assert requests[0].post_data_json == {"foo": "bar", "baz": "123"}


async def test_should_be_undefined_when_there_is_no_post_data(
    page: Page, server: Server
) -> None:
    response = await page.goto(server.EMPTY_PAGE)
    assert response
    assert response.request.post_data_json is None


async def test_should_return_post_data_without_content_type(
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
            request.headers.set('content-type', '');
            return fetch(request);
        }""",
            {"url": server.PREFIX + "/title.html"},
        )
    request = await request_info.value
    assert request.post_data_json == {"value": 42}


async def test_should_throw_on_invalid_json_in_post_data(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_request("**/*") as request_info:
        await page.evaluate(
            """({url}) => {
            const request = new Request(url, {
                method: 'POST',
                body: '<not a json>',
            });
            request.headers.set('content-type', '');
            return fetch(request);
        }""",
            {"url": server.PREFIX + "/title.html"},
        )
    request = await request_info.value
    with pytest.raises(Error) as exc_info:
        print(request.post_data_json)
    assert "POST data is not a valid JSON object: <not a json>" in str(exc_info.value)


async def test_should_work_with_binary_post_data(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    server.set_route("/post", lambda req: req.finish())
    requests = []
    page.on("request", lambda r: requests.append(r))
    await page.evaluate(
        """async () => {
        await fetch('./post', { method: 'POST', body: new Uint8Array(Array.from(Array(256).keys())) })
    }"""
    )
    assert len(requests) == 1
    buffer = requests[0].post_data_buffer
    assert len(buffer) == 256
    for i in range(256):
        assert buffer[i] == i


async def test_should_work_with_binary_post_data_and_interception(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    server.set_route("/post", lambda req: req.finish())
    requests = []
    await page.route("/post", lambda route: asyncio.ensure_future(route.continue_()))
    page.on("request", lambda r: requests.append(r))
    await page.evaluate(
        """async () => {
        await fetch('./post', { method: 'POST', body: new Uint8Array(Array.from(Array(256).keys())) })
    }"""
    )
    assert len(requests) == 1
    buffer = requests[0].post_data_buffer
    assert len(buffer) == 256
    for i in range(256):
        assert buffer[i] == i


async def test_response_text_should_work(page: Page, server: Server) -> None:
    response = await page.goto(server.PREFIX + "/simple.json")
    assert response
    assert await response.text() == '{"foo": "bar"}\n'


async def test_response_text_should_return_uncompressed_text(
    page: Page, server: Server
) -> None:
    server.enable_gzip("/simple.json")
    response = await page.goto(server.PREFIX + "/simple.json")
    assert response
    assert response.headers["content-encoding"] == "gzip"
    assert await response.text() == '{"foo": "bar"}\n'


async def test_response_text_should_throw_when_requesting_body_of_redirected_response(
    page: Page, server: Server
) -> None:
    server.set_redirect("/foo.html", "/empty.html")
    response = await page.goto(server.PREFIX + "/foo.html")
    assert response
    redirected_from = response.request.redirected_from
    assert redirected_from
    redirected = await redirected_from.response()
    assert redirected
    assert redirected.status == 302
    error: Optional[Error] = None
    try:
        await redirected.text()
    except Error as exc:
        error = exc
    assert error
    assert "Response body is unavailable for redirect responses" in error.message


async def test_response_json_should_work(page: Page, server: Server) -> None:
    response = await page.goto(server.PREFIX + "/simple.json")
    assert response
    assert await response.json() == {"foo": "bar"}


async def test_response_body_should_work(
    page: Page, server: Server, assetdir: Path
) -> None:
    response = await page.goto(server.PREFIX + "/pptr.png")
    assert response
    with open(
        assetdir / "pptr.png",
        "rb",
    ) as fd:
        assert fd.read() == await response.body()


async def test_response_body_should_work_with_compression(
    page: Page, server: Server, assetdir: Path
) -> None:
    server.enable_gzip("/pptr.png")
    response = await page.goto(server.PREFIX + "/pptr.png")
    assert response
    with open(
        assetdir / "pptr.png",
        "rb",
    ) as fd:
        assert fd.read() == await response.body()


async def test_response_status_text_should_work(page: Page, server: Server) -> None:
    server.set_route("/cool", lambda r: (r.setResponseCode(200, b"cool!"), r.finish()))

    response = await page.goto(server.PREFIX + "/cool")
    assert response
    assert response.status_text == "cool!"


async def test_request_resource_type_should_return_event_source(
    page: Page, server: Server
) -> None:
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
    assert requests[0].resource_type == "eventsource"


async def test_network_events_request(page: Page, server: Server) -> None:
    requests = []
    page.on("request", lambda r: requests.append(r))
    await page.goto(server.EMPTY_PAGE)
    assert len(requests) == 1
    assert requests[0].url == server.EMPTY_PAGE
    assert requests[0].resource_type == "document"
    assert requests[0].method == "GET"
    assert await requests[0].response()
    assert requests[0].frame == page.main_frame
    assert requests[0].frame.url == server.EMPTY_PAGE


async def test_network_events_response(page: Page, server: Server) -> None:
    responses = []
    page.on("response", lambda r: responses.append(r))
    await page.goto(server.EMPTY_PAGE)
    assert len(responses) == 1
    assert responses[0].url == server.EMPTY_PAGE
    assert responses[0].status == 200
    assert responses[0].ok
    assert responses[0].request


async def test_network_events_request_failed(
    page: Page,
    server: Server,
    is_chromium: bool,
    is_webkit: bool,
    is_mac: bool,
    is_win: bool,
) -> None:
    def handle_request(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "text/css")
        request.loseConnection()

    server.set_route("/one-style.css", handle_request)

    failed_requests = []
    page.on("requestfailed", lambda request: failed_requests.append(request))
    await page.goto(server.PREFIX + "/one-style.html")
    # TODO: https://github.com/microsoft/playwright/issues/12789
    assert len(failed_requests) >= 1
    assert "one-style.css" in failed_requests[0].url
    assert await failed_requests[0].response() is None
    assert failed_requests[0].resource_type == "stylesheet"
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
            assert failed_requests[0].failure in [
                "Message Corrupt",
                "Connection terminated unexpectedly",
            ]
    else:
        assert failed_requests[0].failure == "NS_ERROR_NET_RESET"
    assert failed_requests[0].frame


async def test_network_events_request_finished(page: Page, server: Server) -> None:
    async with page.expect_event("requestfinished") as event_info:
        await page.goto(server.EMPTY_PAGE)
    request = await event_info.value
    assert request.url == server.EMPTY_PAGE
    assert await request.response()
    assert request.frame == page.main_frame
    assert request.frame.url == server.EMPTY_PAGE


async def test_network_events_should_fire_events_in_proper_order(
    page: Page, server: Server
) -> None:
    events = []
    page.on("request", lambda request: events.append("request"))
    page.on("response", lambda response: events.append("response"))
    response = await page.goto(server.EMPTY_PAGE)
    assert response
    await response.finished()
    events.append("requestfinished")
    assert events == ["request", "response", "requestfinished"]


async def test_network_events_should_support_redirects(
    page: Page, server: Server
) -> None:
    FOO_URL = server.PREFIX + "/foo.html"
    events: Dict[str, List[Union[str, int]]] = {}
    events[FOO_URL] = []
    events[server.EMPTY_PAGE] = []

    def _handle_on_request(request: Request) -> None:
        events[request.url].append(request.method)

    page.on("request", _handle_on_request)

    def _handle_on_response(response: Response) -> None:
        events[response.url].append(response.status)

    page.on("response", _handle_on_response)

    def _handle_on_requestfinished(request: Request) -> None:
        events[request.url].append("DONE")

    page.on("requestfinished", _handle_on_requestfinished)

    def _handle_on_requestfailed(request: Request) -> None:
        events[request.url].append("FAIL")

    page.on("requestfailed", _handle_on_requestfailed)
    server.set_redirect("/foo.html", "/empty.html")
    response = await page.goto(FOO_URL)
    assert response
    await response.finished()
    expected = {}
    expected[FOO_URL] = ["GET", 302, "DONE"]
    expected[server.EMPTY_PAGE] = ["GET", 200, "DONE"]
    assert events == expected
    redirected_from = response.request.redirected_from
    assert redirected_from
    assert "/foo.html" in redirected_from.url
    assert redirected_from.redirected_from is None
    assert redirected_from.redirected_to == response.request


async def test_request_is_navigation_request_should_work(
    page: Page, server: Server
) -> None:
    requests: Dict[str, Request] = {}

    def handle_request(request: Request) -> None:
        requests[request.url.split("/").pop()] = request

    page.on("request", handle_request)
    server.set_redirect("/rrredirect", "/frames/one-frame.html")
    await page.goto(server.PREFIX + "/rrredirect")
    assert requests["rrredirect"].is_navigation_request()
    assert requests["one-frame.html"].is_navigation_request()
    assert requests["frame.html"].is_navigation_request()
    assert requests["script.js"].is_navigation_request() is False
    assert requests["style.css"].is_navigation_request() is False


async def test_request_is_navigation_request_should_work_when_navigating_to_image(
    page: Page, server: Server
) -> None:
    requests = []
    page.on("request", lambda r: requests.append(r))
    await page.goto(server.PREFIX + "/pptr.png")
    assert requests[0].is_navigation_request()


async def test_set_extra_http_headers_should_work(page: Page, server: Server) -> None:
    await page.set_extra_http_headers({"foo": "bar"})

    request = (
        await asyncio.gather(
            server.wait_for_request("/empty.html"),
            page.goto(server.EMPTY_PAGE),
        )
    )[0]
    assert request.getHeader("foo") == "bar"


async def test_set_extra_http_headers_should_work_with_redirects(
    page: Page, server: Server
) -> None:
    server.set_redirect("/foo.html", "/empty.html")
    await page.set_extra_http_headers({"foo": "bar"})

    request = (
        await asyncio.gather(
            server.wait_for_request("/empty.html"),
            page.goto(server.PREFIX + "/foo.html"),
        )
    )[0]
    assert request.getHeader("foo") == "bar"


async def test_set_extra_http_headers_should_work_with_extra_headers_from_browser_context(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()
    await context.set_extra_http_headers({"foo": "bar"})

    page = await context.new_page()
    request = (
        await asyncio.gather(
            server.wait_for_request("/empty.html"),
            page.goto(server.EMPTY_PAGE),
        )
    )[0]
    await context.close()
    assert request.getHeader("foo") == "bar"


@flaky  # Flaky upstream https://devops.aslushnikov.com/flakiness2.html#filter_spec=should+override+extra+headers+from+browser+context&test_parameter_filters=%5B%5B%22browserName%22%2C%5B%5B%22webkit%22%2C%22include%22%5D%5D%5D%2C%5B%22video%22%2C%5B%5Btrue%2C%22exclude%22%5D%5D%5D%2C%5B%22platform%22%2C%5B%5B%22Windows%22%2C%22include%22%5D%5D%5D%5D
async def test_set_extra_http_headers_should_override_extra_headers_from_browser_context(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context(extra_http_headers={"fOo": "bAr", "baR": "foO"})

    page = await context.new_page()
    await page.set_extra_http_headers({"Foo": "Bar"})

    request = (
        await asyncio.gather(
            server.wait_for_request("/empty.html"),
            page.goto(server.EMPTY_PAGE),
        )
    )[0]
    await context.close()
    assert request.getHeader("foo") == "Bar"
    assert request.getHeader("bar") == "foO"


async def test_set_extra_http_headers_should_throw_for_non_string_header_values(
    page: Page,
) -> None:
    error: Optional[Error] = None
    try:
        await page.set_extra_http_headers({"foo": 1})  # type: ignore
    except Error as exc:
        error = exc
    assert error
    assert (
        error.message
        == "Page.set_extra_http_headers: headers[0].value: expected string, got number"
    )


async def test_response_server_addr(page: Page, server: Server) -> None:
    response = await page.goto(server.EMPTY_PAGE)
    assert response
    server_addr = await response.server_addr()
    assert server_addr
    assert server_addr["port"] == server.PORT
    assert server_addr["ipAddress"] in ["127.0.0.1", "[::1]"]


async def test_response_security_details(
    browser: Browser,
    https_server: Server,
    browser_name: str,
    is_win: bool,
    is_linux: bool,
) -> None:
    if (browser_name == "webkit" and is_linux) or (browser_name == "webkit" and is_win):
        pytest.skip("https://github.com/microsoft/playwright/issues/6759")
    page = await browser.new_page(ignore_https_errors=True)
    response = await page.goto(https_server.EMPTY_PAGE)
    assert response
    await response.finished()
    security_details = await response.security_details()
    assert security_details
    if browser_name == "webkit" and is_win:
        assert security_details == {
            "subjectName": "puppeteer-tests",
            "validFrom": 1550084863,
            "validTo": -1,
        }
    elif browser_name == "webkit":
        assert security_details == {
            "protocol": "TLS 1.3",
            "subjectName": "puppeteer-tests",
            "validFrom": 1550084863,
            "validTo": 33086084863,
        }
    else:
        assert security_details == {
            "issuer": "puppeteer-tests",
            "protocol": "TLS 1.3",
            "subjectName": "puppeteer-tests",
            "validFrom": 1550084863,
            "validTo": 33086084863,
        }
    await page.close()


async def test_response_security_details_none_without_https(
    page: Page, server: Server
) -> None:
    response = await page.goto(server.EMPTY_PAGE)
    assert response
    security_details = await response.security_details()
    assert security_details is None


async def test_should_report_if_request_was_from_service_worker(
    page: Page, server: Server
) -> None:
    response = await page.goto(server.PREFIX + "/serviceworkers/fetch/sw.html")
    assert response
    assert not response.from_service_worker
    await page.evaluate("() => window.activationPromise")
    async with page.expect_response("**/example.txt") as response_info:
        await page.evaluate("() => fetch('/example.txt')")
    response = await response_info.value
    assert response.from_service_worker
