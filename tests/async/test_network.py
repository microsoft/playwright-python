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
from typing import Dict, List, cast

import pytest

from playwright.async_api import Browser, Error, Page, Request, Response, Route
from tests.server import Server


async def test_request_fulfill(page, server):
    async def handle_request(route: Route, request: Request):
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

    assert response.ok
    assert (
        repr(response) == f"<Response url={response.url!r} request={response.request}>"
    )
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


async def test_page_events_request_should_accept_method(page: Page, server):
    class Log:
        def __init__(self):
            self.requests = []

        def handle(self, request):
            self.requests.append(request)

    log = Log()
    page.on("request", log.handle)
    await page.goto(server.EMPTY_PAGE)
    assert len(log.requests) == 1


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


async def test_page_events_request_should_report_requests_and_responses_handled_by_service_worker(
    page: Page, server
):
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
    page, server
):
    requests = []
    page.on("request", lambda r: requests.append(r))
    await page.goto(server.EMPTY_PAGE)
    assert len(requests) == 1
    assert requests[0].frame == page.main_frame


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
    assert requests[0].frame == page.main_frame


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


# TODO: update once fixed https://github.com/microsoft/playwright/issues/6690
@pytest.mark.xfail
async def test_request_headers_should_get_the_same_headers_as_the_server(
    page: Page, server, is_webkit, is_win
):
    server_request_headers_future: Future[Dict[str, str]] = asyncio.Future()

    def handle(request):
        normalized_headers = {
            key.decode().lower(): value[0].decode()
            for key, value in request.requestHeaders.getAllRawHeaders()
        }
        server_request_headers_future.set_result(normalized_headers)
        request.write(b"done")
        request.finish()

    server.set_route("/empty.html", handle)
    response = await page.goto(server.EMPTY_PAGE)
    server_headers = await server_request_headers_future
    if is_webkit and is_win:
        # Curl does not show accept-encoding and accept-language
        server_headers.pop("accept-encoding")
        server_headers.pop("accept-language")
    assert cast(Response, response).request.headers == server_headers


async def test_request_headers_should_get_the_same_headers_as_the_server_cors(
    page: Page, server, is_webkit, is_win
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
    server_headers = await server_request_headers_future
    if is_webkit and is_win:
        # Curl does not show accept-encoding and accept-language
        server_headers.pop("accept-encoding")
        server_headers.pop("accept-language")
    assert request.headers == server_headers


async def test_response_headers_should_work(page, server):
    server.set_route("/empty.html", lambda r: (r.setHeader("foo", "bar"), r.finish()))

    response = await page.goto(server.EMPTY_PAGE)
    assert response.headers["foo"] == "bar"


async def test_request_post_data_should_work(page, server):
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
    page, server
):
    response = await page.goto(server.EMPTY_PAGE)
    assert response.request.post_data is None


async def test_should_parse_the_json_post_data(page, server):
    await page.goto(server.EMPTY_PAGE)
    server.set_route("/post", lambda req: req.finish())
    requests = []
    page.on("request", lambda r: requests.append(r))
    await page.evaluate(
        """() => fetch('./post', { method: 'POST', body: JSON.stringify({ foo: 'bar' }) })"""
    )
    assert len(requests) == 1
    assert requests[0].post_data_json == {"foo": "bar"}


async def test_should_parse_the_data_if_content_type_is_form_urlencoded(page, server):
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


async def test_should_be_undefined_when_there_is_no_post_data(page, server):
    response = await page.goto(server.EMPTY_PAGE)
    assert response.request.post_data_json is None


async def test_should_return_post_data_without_content_type(page, server):
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


async def test_should_throw_on_invalid_json_in_post_data(page, server):
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


async def test_should_work_with_binary_post_data(page, server):
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


async def test_should_work_with_binary_post_data_and_interception(page, server):
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
    redirected_from = response.request.redirected_from
    assert redirected_from
    redirected = await redirected_from.response()
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


async def test_response_body_should_work(page, server, assetdir):
    response = await page.goto(server.PREFIX + "/pptr.png")
    with open(
        assetdir / "pptr.png",
        "rb",
    ) as fd:
        assert fd.read() == await response.body()


async def test_response_body_should_work_with_compression(page, server, assetdir):
    server.enable_gzip("/pptr.png")
    response = await page.goto(server.PREFIX + "/pptr.png")
    with open(
        assetdir / "pptr.png",
        "rb",
    ) as fd:
        assert fd.read() == await response.body()


async def test_response_status_text_should_work(page, server):
    server.set_route("/cool", lambda r: (r.setResponseCode(200, b"cool!"), r.finish()))

    response = await page.goto(server.PREFIX + "/cool")
    assert response.status_text == "cool!"


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
    assert requests[0].resource_type == "eventsource"


async def test_network_events_request(page, server):
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
    page, server, is_chromium, is_webkit, is_mac, is_win
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
            assert failed_requests[0].failure == "Message Corrupt"
    else:
        assert failed_requests[0].failure == "NS_ERROR_NET_RESET"
    assert failed_requests[0].frame


async def test_network_events_request_finished(page, server):
    async with page.expect_event("requestfinished") as event_info:
        await page.goto(server.EMPTY_PAGE)
    request = await event_info.value
    assert request.url == server.EMPTY_PAGE
    assert await request.response()
    assert request.frame == page.main_frame
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
    redirected_from = response.request.redirected_from
    assert "/foo.html" in redirected_from.url
    assert redirected_from.redirected_from is None
    assert redirected_from.redirected_to == response.request


async def test_request_is_navigation_request_should_work(page, server):
    pytest.skip(msg="test")
    requests = {}

    def handle_request(request):
        requests[request.url().split("/").pop()] = request

    page.on("request", handle_request)
    server.set_redirect("/rrredirect", "/frames/one-frame.html")
    await page.goto(server.PREFIX + "/rrredirect")
    assert requests.get("rrredirect").is_navigation_request()
    assert requests.get("one-frame.html").is_navigation_request()
    assert requests.get("frame.html").is_navigation_request()
    assert requests.get("script.js").is_navigation_request() is False
    assert requests.get("style.css").is_navigation_request() is False


async def test_request_is_navigation_request_should_work_when_navigating_to_image(
    page, server
):
    requests = []
    page.on("request", lambda r: requests.append(r))
    await page.goto(server.PREFIX + "/pptr.png")
    assert requests[0].is_navigation_request()


async def test_set_extra_http_headers_should_work(page, server):
    await page.set_extra_http_headers({"foo": "bar"})

    request = (
        await asyncio.gather(
            server.wait_for_request("/empty.html"),
            page.goto(server.EMPTY_PAGE),
        )
    )[0]
    assert request.getHeader("foo") == "bar"


async def test_set_extra_http_headers_should_work_with_redirects(page, server):
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
    browser, server
):
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


async def test_set_extra_http_headers_should_override_extra_headers_from_browser_context(
    browser, server
):
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
    page, server
):
    error = None
    try:
        await page.set_extra_http_headers({"foo": 1})
    except Error as exc:
        error = exc
    assert error.message == "headers[0].value: expected string, got number"


async def test_response_server_addr(page: Page, server: Server):
    response = await page.goto(server.EMPTY_PAGE)
    server_addr = await response.server_addr()
    assert server_addr
    assert server_addr["port"] == server.PORT
    assert server_addr["ipAddress"] in ["127.0.0.1", "::1"]


async def test_response_security_details(
    browser: Browser, https_server: Server, browser_name, is_win, is_linux
):
    if browser_name == "webkit" and is_linux:
        pytest.skip("https://github.com/microsoft/playwright/issues/6759")
    page = await browser.new_page(ignore_https_errors=True)
    response = await page.goto(https_server.EMPTY_PAGE)
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


async def test_response_security_details_none_without_https(page: Page, server: Server):
    response = await page.goto(server.EMPTY_PAGE)
    security_details = await response.security_details()
    assert security_details is None
