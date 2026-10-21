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

"""Port of tests/page/page-network-request.spec.ts."""

import asyncio
import json
import re
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, TypeVar

import pytest
from greenlet import greenlet

from playwright._impl._greenlets import wait_for_future
from playwright.sync_api import Error, Page, Request, Route
from tests.helpers.raw_request_headers import raw_headers, record_raw_headers
from tests.server import Server, TestServerRequest, reactor

from ..utils import Utils

T = TypeVar("T")


def wait_for(page: Page, awaitable: "Awaitable[T]") -> T:
    """Port of `await promise`: runs the event loop until the awaitable settles."""
    future = asyncio.ensure_future(awaitable, loop=page._loop)
    wait_for_future(page._loop, page._dispatcher_fiber, future)
    return future.result()


def run_in_background(page: Page, action: Callable[[], Any]) -> "asyncio.Future[Any]":
    """Like calling an async function without await: starts the action and goes on.

    The action runs in a greenlet of its own. The future settles with the result or the
    error of the action; wait_for(page, future) waits for it.
    """
    result: "asyncio.Future[Any]" = page._loop.create_future()

    def run() -> None:
        try:
            result.set_result(action())
        except Exception as error:
            result.set_result(error)

    async def start() -> None:
        greenlet(run).switch()

    # start() returns once the action waits for the driver, after it sent its message.
    wait_for(page, start())
    return result


def adjust_server_headers(headers: Dict[str, str], browser_name: str) -> Dict[str, str]:
    if browser_name == "firefox":
        headers.pop("priority", None)
    return headers


def node_headers(request: TestServerRequest) -> Dict[str, str]:
    """Like `req.headers` in Node.js: lower-case names, repeated values joined."""
    headers: Dict[str, str] = {}
    for name, values in request.requestHeaders.getAllRawHeaders():
        key = name.decode().lower()
        separator = "; " if key == "cookie" else ", "
        headers[key] = separator.join(value.decode() for value in values)
    return headers


def expect_failure(request: pytest.FixtureRequest, reason: str) -> None:
    """Like `it.fail()`: the test must fail."""
    request.applymarker(pytest.mark.xfail(reason=f"upstream: {reason}", strict=True))


def test_NE_001_should_work_for_main_frame_navigation_request(
    page: Page, server: Server
) -> None:
    requests: List[Request] = []
    page.on("request", lambda request: requests.append(request))
    page.goto(server.EMPTY_PAGE)
    assert len(requests) == 1
    assert requests[0].frame == page.main_frame


def test_NE_002_should_work_for_subframe_navigation_request(
    page: Page, server: Server, utils: Utils
) -> None:
    page.goto(server.EMPTY_PAGE)
    requests: List[Request] = []
    page.on("request", lambda request: requests.append(request))
    utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    assert len(requests) == 1
    assert requests[0].frame == page.frames[1]


def test_NE_003_should_work_for_fetch_requests_smoke(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    requests: List[Request] = []
    page.on("request", lambda request: requests.append(request))
    page.evaluate("() => fetch('/digits/1.png')")
    assert len(requests) == 1
    assert requests[0].frame == page.main_frame


def test_NE_004_should_work_for_a_redirect(page: Page, server: Server) -> None:
    server.set_redirect("/foo.html", "/empty.html")
    requests: List[Request] = []
    page.on("request", lambda request: requests.append(request))
    page.goto(server.PREFIX + "/foo.html")

    assert len(requests) == 2
    assert requests[0].url == server.PREFIX + "/foo.html"
    assert requests[1].url == server.PREFIX + "/empty.html"


# https://github.com/microsoft/playwright/issues/3993
def test_NE_005_should_not_work_for_a_redirect_and_interception(
    page: Page, server: Server
) -> None:
    server.set_redirect("/foo.html", "/empty.html")
    requests: List[Request] = []

    def handle(route: Route) -> None:
        requests.append(route.request)
        route.continue_()

    page.route("**", handle)
    page.goto(server.PREFIX + "/foo.html")

    assert page.url == server.PREFIX + "/empty.html"

    assert len(requests) == 1
    assert requests[0].url == server.PREFIX + "/foo.html"


def test_NE_006_should_return_headers(
    page: Page, server: Server, browser_name: str
) -> None:
    response = page.goto(server.EMPTY_PAGE)
    assert response
    if browser_name == "chromium":
        assert "Chrome" in response.request.headers["user-agent"]
    elif browser_name == "firefox":
        assert "Firefox" in response.request.headers["user-agent"]
    elif browser_name == "webkit":
        assert "WebKit" in response.request.headers["user-agent"]


def test_NE_007_should_get_the_same_headers_as_the_server(
    page: Page,
    server: Server,
    browser_name: str,
    platform: str,
    browser_channel: Optional[str],
    request: pytest.FixtureRequest,
) -> None:
    if (
        browser_name == "webkit"
        and platform == "win32"
        and browser_channel != "webkit-wsl"
    ):
        expect_failure(
            request, "Curl does not show accept-encoding and accept-language"
        )
    server_requests: List[TestServerRequest] = []

    def handle(server_request: TestServerRequest) -> None:
        server_requests.append(server_request)
        server_request.write(b"done")
        server_request.finish()

    server.set_route("/empty.html", handle)
    response = page.goto(server.PREFIX + "/empty.html")
    assert response
    headers = response.request.all_headers()
    assert headers == adjust_server_headers(
        node_headers(server_requests[0]), browser_name
    )


def test_NE_008_should_not_return_all_headers_until_they_are_available(
    page: Page,
    server: Server,
    browser_name: str,
    platform: str,
    browser_channel: Optional[str],
    request: pytest.FixtureRequest,
) -> None:
    if (
        browser_name == "webkit"
        and platform == "win32"
        and browser_channel != "webkit-wsl"
    ):
        expect_failure(
            request, "Curl does not show accept-encoding and accept-language"
        )

    # The handlers call all_headers() at once, as upstream does; it waits for the headers.
    request_headers_promises: List[Any] = []
    page.on("request", lambda r: request_headers_promises.append(r.all_headers()))
    response_headers_promises: List[Any] = []
    page.on("response", lambda r: response_headers_promises.append(r.all_headers()))

    server_requests: List[TestServerRequest] = []

    def handle(server_request: TestServerRequest) -> None:
        server_requests.append(server_request)
        server_request.setResponseCode(200)
        server_request.setHeader("foo", "bar")
        # Send the status line and the headers now, like response.writeHead().
        server_request.write(b"")

        def end() -> None:
            server_request.write(b"done")
            server_request.finish()

        reactor.callLater(3, end)

    server.set_route("/empty.html", handle)

    page.goto(server.PREFIX + "/empty.html")
    request_headers = request_headers_promises[-1]
    assert request_headers == adjust_server_headers(
        node_headers(server_requests[0]), browser_name
    )

    response_headers = response_headers_promises[-1]
    assert response_headers["foo"] == "bar"


def test_NE_009_should_get_the_same_headers_as_the_server_cors(
    page: Page,
    server: Server,
    browser_name: str,
    platform: str,
    browser_channel: Optional[str],
    request: pytest.FixtureRequest,
) -> None:
    if (
        browser_name == "webkit"
        and platform == "win32"
        and browser_channel != "webkit-wsl"
    ):
        expect_failure(
            request, "Curl does not show accept-encoding and accept-language"
        )

    page.goto(server.PREFIX + "/empty.html")
    server_requests: List[TestServerRequest] = []

    def handle(server_request: TestServerRequest) -> None:
        server_requests.append(server_request)
        server_request.setResponseCode(200)
        server_request.setHeader("Access-Control-Allow-Origin", "*")
        server_request.write(b"done")
        server_request.finish()

    server.set_route("/something", handle)
    with page.expect_event("response") as response_info:
        text = page.evaluate(
            """async url => {
                const data = await fetch(url);
                return data.text();
            }""",
            server.CROSS_PROCESS_PREFIX + "/something",
        )
    assert text == "done"
    response = response_info.value
    headers = response.request.all_headers()
    assert headers == adjust_server_headers(
        node_headers(server_requests[0]), browser_name
    )


def test_NE_010_should_not_get_preflight_cors_requests_when_intercepting(
    page: Page, server: Server, browser_name: str
) -> None:
    page.goto(server.PREFIX + "/empty.html")

    requests: List[str] = []

    def handle(server_request: TestServerRequest) -> None:
        requests.append(server_request.method.decode())
        if server_request.method == b"OPTIONS":
            server_request.setResponseCode(204)
            server_request.setHeader("Access-Control-Allow-Origin", "*")
            server_request.setHeader(
                "Access-Control-Allow-Methods", "POST, GET, OPTIONS, DELETE"
            )
            server_request.setHeader("Access-Control-Allow-Headers", "*")
            server_request.setHeader("Cache-Control", "no-cache")
            server_request.finish()
            return
        server_request.setResponseCode(200)
        server_request.setHeader("Access-Control-Allow-Origin", "*")
        server_request.write(b"done")
        server_request.finish()

    server.set_route("/something", handle)
    # First check the browser will send preflight request when interception is OFF.
    text = page.evaluate(
        """async url => {
            const data = await fetch(url, {
                method: 'DELETE',
                headers: { 'X-PINGOTHER': 'pingpong' }
            });
            return data.text();
        }""",
        server.CROSS_PROCESS_PREFIX + "/something",
    )
    assert text == "done"
    assert requests == ["OPTIONS", "DELETE"]

    # Now check the browser will NOT send preflight request when interception is ON.
    requests.clear()
    routed: List[str] = []

    def handle_route(route: Route) -> None:
        routed.append(route.request.method)
        route.continue_()

    page.route("**/something", handle_route)

    text = page.evaluate(
        """async url => {
            const data = await fetch(url, {
                method: 'DELETE',
                headers: { 'X-PINGOTHER': 'pingpong' }
            });
            return data.text();
        }""",
        server.CROSS_PROCESS_PREFIX + "/something",
    )
    assert text == "done"
    # Check that there was no preflight (OPTIONS) request.
    assert routed == ["DELETE"]
    if browser_name == "firefox":
        assert requests == ["OPTIONS", "DELETE"]
    else:
        assert requests == ["DELETE"]


def test_NE_011_should_return_post_data(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    server.set_route("/post", lambda server_request: server_request.finish())
    requests: List[Request] = []
    page.on("request", lambda r: requests.append(r))
    page.evaluate(
        "() => fetch('./post', { method: 'POST', body: JSON.stringify({ foo: 'bar' }) })"
    )
    assert requests
    assert requests[-1].post_data == '{"foo":"bar"}'


def test_NE_012_should_work_with_binary_post_data(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    server.set_route("/post", lambda server_request: server_request.finish())
    requests: List[Request] = []
    page.on("request", lambda r: requests.append(r))
    page.evaluate(
        """async () => {
            await fetch('./post', { method: 'POST', body: new Uint8Array(Array.from(Array(256).keys())) });
        }"""
    )
    assert requests
    buffer = requests[-1].post_data_buffer
    assert buffer
    assert len(buffer) == 256
    for i in range(256):
        assert buffer[i] == i


def test_NE_013_should_work_with_binary_post_data_and_interception(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    server.set_route("/post", lambda server_request: server_request.finish())
    requests: List[Request] = []
    page.route("/post", lambda route: route.continue_())
    page.on("request", lambda r: requests.append(r))
    page.evaluate(
        """async () => {
            await fetch('./post', { method: 'POST', body: new Uint8Array(Array.from(Array(256).keys())) });
        }"""
    )
    assert requests
    buffer = requests[-1].post_data_buffer
    assert buffer
    assert len(buffer) == 256
    for i in range(256):
        assert buffer[i] == i


def test_NE_014_should_override_post_data_content_type(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    server_requests: List[TestServerRequest] = []

    def handle(server_request: TestServerRequest) -> None:
        server_requests.append(server_request)
        server_request.finish()

    server.set_route("/post", handle)

    def handle_route(route: Route, request: Request) -> None:
        headers = request.headers
        headers["content-type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        route.continue_(headers=headers, post_data=request.post_data)

    page.route("**/post", handle_route)
    page.evaluate(
        """async () => {
            await fetch('./post', { method: 'POST', body: 'foo=bar' });
        }"""
    )
    assert server_requests
    assert (
        server_requests[0].getHeader("content-type")
        == "application/x-www-form-urlencoded; charset=UTF-8"
    )


def test_NE_015_should_get_undefined_with_post_data_when_there_is_no_post_data(
    page: Page, server: Server
) -> None:
    response = page.goto(server.EMPTY_PAGE)
    assert response
    assert response.request.post_data is None


def test_NE_016_should_parse_the_json_post_data(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    server.set_route("/post", lambda server_request: server_request.finish())
    requests: List[Request] = []
    page.on("request", lambda r: requests.append(r))
    page.evaluate(
        "() => fetch('./post', { method: 'POST', body: JSON.stringify({ foo: 'bar' }) })"
    )
    assert requests
    assert requests[-1].post_data_json == {"foo": "bar"}


def test_NE_017_should_parse_the_data_if_content_type_is_application_x_www_form_urlencoded(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    server.set_route("/post", lambda server_request: server_request.finish())
    requests: List[Request] = []
    page.on("request", lambda r: requests.append(r))
    page.set_content(
        "<form method='POST' action='/post'><input type='text' name='foo' value='bar'><input type='number' name='baz' value='123'><input type='submit'></form>"
    )
    page.click("input[type=submit]")
    assert requests
    assert requests[-1].post_data_json == {"foo": "bar", "baz": "123"}


def test_NE_018_should_parse_the_data_if_content_type_is_application_x_www_form_urlencoded_charset_utf_8(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    with page.expect_request("**/post") as request_info:
        page.evaluate(
            """() => fetch('./post', {
                method: 'POST',
                headers: {
                    'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                },
                body: 'foo=bar&baz=123'
            })"""
        )
    assert (request_info.value).post_data_json == {"foo": "bar", "baz": "123"}


def test_NE_019_should_get_undefined_with_post_data_json_when_there_is_no_post_data(
    page: Page, server: Server
) -> None:
    response = page.goto(server.EMPTY_PAGE)
    assert response
    assert response.request.post_data_json is None


def test_NE_020_should_return_multipart_form_data(
    page: Page, server: Server, browser_name: str, browser_major_version: int
) -> None:
    if browser_name == "webkit":
        pytest.skip("fixme: File content is missing in WebKit")
    if browser_name == "chromium" and browser_major_version < 126:
        pytest.skip("Requires a recent enough protocol")

    page.goto(server.EMPTY_PAGE)
    server.set_route("/post", lambda server_request: server_request.finish())
    page.route("**/*", lambda route: route.continue_())
    with page.expect_request("**/post") as request_info:
        page.evaluate(
            """async () => {
                const body = new FormData();
                body.set('name1', 'value1');
                body.set('file', new File(['file-value'], 'foo.txt'));
                body.set('name2', 'value2');
                body.append('name2', 'another-value2');
                await fetch('/post', { method: 'POST', body });
            }"""
        )
    request = request_info.value
    content_type = request.header_value("Content-Type")
    assert content_type
    match = re.match(r"^multipart\/form-data; boundary=(.*)$", content_type)
    assert match
    b = match.group(1)
    expected = (
        f'--{b}\r\nContent-Disposition: form-data; name="name1"\r\n\r\nvalue1\r\n'
        f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="foo.txt"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\nfile-value\r\n"
        f'--{b}\r\nContent-Disposition: form-data; name="name2"\r\n\r\nvalue2\r\n'
        f'--{b}\r\nContent-Disposition: form-data; name="name2"\r\n\r\nanother-value2\r\n'
        f"--{b}--\r\n"
    )
    post_data_buffer = request.post_data_buffer
    assert post_data_buffer
    assert post_data_buffer.decode("utf-8") == expected


def test_NE_021_should_return_event_source(page: Page, server: Server) -> None:
    SSE_MESSAGE = {"foo": "bar"}

    # 1. Setup server-sent events on server that immediately sends a message to the client.
    def handle(server_request: TestServerRequest) -> None:
        server_request.setResponseCode(200)
        server_request.setHeader("Content-Type", "text/event-stream")
        server_request.setHeader("Connection", "keep-alive")
        server_request.setHeader("Cache-Control", "no-cache")
        server_request.write(
            f"data: {json.dumps(SSE_MESSAGE, separators=(',', ':'))}\n\n".encode()
        )

    server.set_route("/sse", handle)
    # 2. Subscribe to page request events.
    page.goto(server.EMPTY_PAGE)
    requests: List[Request] = []
    page.on("request", lambda request: requests.append(request))
    # 3. Connect to EventSource in browser and return first message.
    assert (
        page.evaluate(
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


def test_NE_022_should_return_navigation_bit(page: Page, server: Server) -> None:
    requests: Dict[str, Request] = {}
    page.on(
        "request",
        lambda request: requests.__setitem__(request.url.split("/")[-1], request),
    )
    server.set_redirect("/rrredirect", "/frames/one-frame.html")
    page.goto(server.PREFIX + "/rrredirect")
    assert requests["rrredirect"].is_navigation_request() is True
    assert requests["one-frame.html"].is_navigation_request() is True
    assert requests["frame.html"].is_navigation_request() is True
    assert requests["script.js"].is_navigation_request() is False
    assert requests["style.css"].is_navigation_request() is False


def test_NE_023_should_return_navigation_bit_when_navigating_to_image(
    page: Page, server: Server
) -> None:
    requests: List[Request] = []
    page.on("request", lambda request: requests.append(request))
    page.goto(server.PREFIX + "/pptr.png")
    assert requests[0].is_navigation_request() is True


def test_NE_024_should_report_raw_headers(
    page: Page,
    server: Server,
    browser_name: str,
    platform: str,
    browser_channel: Optional[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_raw_headers(monkeypatch)
    expected_headers: List[Dict[str, str]] = []

    def handle(server_request: TestServerRequest) -> None:
        nonlocal expected_headers
        expected_headers = [
            {"name": name, "value": value}
            for name, value in raw_headers(server_request)
        ]
        if (
            browser_name == "webkit"
            and platform == "win32"
            and browser_channel != "webkit-wsl"
        ):
            expected_headers = [
                header
                for header in expected_headers
                if header["name"].lower() != "accept-encoding"
            ]

            # Convert "value": "en-US, en-US" => "en-US"
            def dedupe(header: Dict[str, str]) -> Dict[str, str]:
                if header["name"].lower() != "accept-language":
                    return header
                values = [v.strip() for v in header["value"].split(",")]
                if len(values) == 1:
                    return header
                if values[0] != values[1]:
                    return header
                return {"name": header["name"], "value": values[0]}

            expected_headers = [dedupe(header) for header in expected_headers]
        if browser_name == "firefox":
            expected_headers = [
                header
                for header in expected_headers
                if header["name"].lower() != "priority"
            ]

        server_request.finish()

    server.set_route("/headers", handle)
    page.goto(server.EMPTY_PAGE)
    with page.expect_request("**/*") as request_info:
        page.evaluate(
            """() => fetch('/headers', {
                headers: [
                    ['header-a', 'value-a'],
                    ['header-b', 'value-b'],
                    ['header-a', 'value-a-1'],
                    ['header-a', 'value-a-2'],
                ]
            })"""
        )
    request = request_info.value
    headers = request.headers_array()
    assert sorted(headers, key=lambda header: header["name"].lower()) == sorted(
        expected_headers, key=lambda header: header["name"].lower()
    )
    assert request.header_value("header-a") == "value-a, value-a-1, value-a-2"
    assert request.header_value("not-there") is None


@pytest.mark.skip_browser("webkit")
def test_NE_025_should_report_raw_response_headers_in_redirects(
    page: Page, server: Server
) -> None:
    # WebKit won't give us raw headers for redirects.
    server.set_extra_headers("/redirect/1.html", {"sec-test-header": "1.html"})
    server.set_extra_headers("/redirect/2.html", {"sec-test-header": "2.html"})
    server.set_extra_headers("/empty.html", {"sec-test-header": "empty.html"})
    server.set_redirect("/redirect/1.html", "/redirect/2.html")
    server.set_redirect("/redirect/2.html", "/empty.html")

    expected_urls = [
        server.PREFIX + s
        for s in ["/redirect/1.html", "/redirect/2.html", "/empty.html"]
    ]
    expected_headers = ["1.html", "2.html", "empty.html"]

    response = page.goto(server.PREFIX + "/redirect/1.html")
    assert response
    redirect_chain: List[str] = []
    headers_chain: List[Optional[str]] = []
    req: Optional[Request] = response.request
    while req:
        redirect_chain.insert(0, req.url)
        res = req.response()
        assert res
        headers = res.all_headers()
        headers_chain.insert(0, headers.get("sec-test-header"))
        req = req.redirected_from

    assert redirect_chain == expected_urls
    assert headers_chain == expected_headers


def test_NE_026_should_report_all_cookies_in_one_header(
    page: Page, server: Server
) -> None:
    expected_headers: Dict[str, str] = {}

    def handle(server_request: TestServerRequest) -> None:
        for name, values in server_request.requestHeaders.getAllRawHeaders():
            for value in values:
                expected_headers[name.decode()] = value.decode()
        server_request.finish()

    server.set_route("/headers", handle)

    page.goto(server.EMPTY_PAGE)
    page.evaluate(
        """() => {
            document.cookie = 'myCookie=myValue';
            document.cookie = 'myOtherCookie=myOtherValue';
        }"""
    )
    response = page.goto(server.EMPTY_PAGE)
    assert response
    cookie = (response.request.all_headers())["cookie"]
    assert cookie == "myCookie=myValue; myOtherCookie=myOtherValue"


def test_NE_027_should_not_allow_to_access_frame_on_popup_main_request(
    page: Page, server: Server
) -> None:
    page.set_content(f'<a target=_blank href="{server.EMPTY_PAGE}">click me</a>')
    with page.context.expect_page() as popup_info:
        with page.context.expect_event("request") as request_info:
            # Python: the click is not awaited, as upstream: the frame is checked
            # as soon as the request arrives, before the popup page exists.
            clicked = run_in_background(
                page, lambda: page.get_by_text("click me").click()
            )
        request = request_info.value

        assert request.is_navigation_request() is True

        with pytest.raises(Error) as exc_info:
            request.frame
        assert (
            "Frame for this navigation request is not available"
            in exc_info.value.message
        )

        response = request.response()
        assert response
        response.finished()
    popup_info.value
    wait_for(page, clicked)


def test_NE_028_page_reload_return_304_status_code(
    page: Page, server: Server, browser_name: str
) -> None:
    if browser_name == "firefox":
        pytest.skip("fixme: Does not send second request")
    request_number = 0

    def handle(server_request: TestServerRequest) -> None:
        nonlocal request_number
        request_number += 1
        if request_number == 1:
            server_request.setResponseCode(200)
        else:
            server_request.setResponseCode(304, b"Not Modified")
        server_request.setHeader("cf-cache-status", "DYNAMIC")
        server_request.setHeader("Content-Type", "text/html;charset=UTF-8")
        server_request.setHeader("Last-Modified", "Fri, 05 Jan 2024 01:56:20 GMT")
        server_request.setHeader("Vary", "Access-Control-Request-Headers")
        server_request.write(b"<div>Test</div>")
        server_request.finish()

    server.set_route("/test.html", handle)
    response1 = page.goto(server.PREFIX + "/test.html")
    assert response1
    assert response1.status == 200
    response2 = page.reload()
    assert response2
    assert request_number == 2
    if browser_name == "chromium":
        assert response2.status == 200
        assert response2.status_text == "OK"
        assert response2.text() == "<div>Test</div>"
    else:
        assert response2.status == 304
        assert response2.status_text == "Not Modified"


@pytest.mark.only_browser("chromium")
def test_NE_029_should_handle_mixed_content_blocked_requests(
    page: Page, assetdir: Path
) -> None:
    # FF and WK actually succeed with the request, and block afterwards.
    page.route(
        "**/mixedcontent.html",
        lambda route: route.fulfill(
            status=200,
            content_type="text/html",
            body="""
        <!doctype html>
        <meta charset="utf-8">
        <style>
        @font-face {
          font-family: 'pwtest-iconfont';
          src: url('http://another.com/iconfont.woff2') format('woff2');
        }
        body {
          font-family: 'pwtest-iconfont';
        }
        </style>
        <span>+-</span>
    """,
        ),
    )

    def handle_font(route: Route) -> None:
        body = (assetdir / "webfont" / "iconfont2.woff").read_bytes()
        route.fulfill(body=body)

    page.route("**/iconfont.woff2", handle_font)

    with page.expect_event(
        "requestfailed", lambda r: "iconfont.woff2" in r.url
    ) as request_info:
        page.goto("https://example.com/mixedcontent.html")
    request = request_info.value
    headers = request.all_headers()
    assert headers["origin"]
    assert request.failure == "mixed-content"
