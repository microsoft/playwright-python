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

"""Port of tests/page/page-request-fulfill.spec.ts."""

import asyncio
import base64
import json
import re
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, TypeVar

import pytest

from playwright._impl._greenlets import wait_for_future
from playwright.sync_api import Error, Page, Playwright, Request, Route, expect
from tests.server import Server, TestServerRequest
from tests.utils import must

T = TypeVar("T")


def wait_for(page: Page, awaitable: "Awaitable[T]") -> T:
    """Port of `await promise`: runs the event loop until the awaitable settles."""
    future = asyncio.ensure_future(awaitable)
    wait_for_future(page._loop, page._dispatcher_fiber, future)
    return future.result()


def ignore_error(action: Callable[[], Any]) -> Callable[[], None]:
    """Port of `promise.catch(() => {})`."""

    def run() -> None:
        try:
            action()
        except Error:
            pass

    return run


def test_RO_096_should_work(page: Page, server: Server) -> None:
    def handler(route: Route) -> None:
        route.fulfill(
            status=201,
            headers={"foo": "bar"},
            content_type="text/html",
            body="Yo, page!",
        )

    page.route("**/*", handler)
    response = must(page.goto(server.EMPTY_PAGE))
    assert response.status == 201
    assert response.headers["foo"] == "bar"
    assert page.evaluate("() => document.body.textContent") == "Yo, page!"


def test_RO_097_should_work_with_buffer_as_body(page: Page, server: Server) -> None:
    def handler(route: Route) -> None:
        route.fulfill(status=200, content_type="text/plain", body=b"Yo, page!")

    page.route("**/*", handler)
    response = must(page.goto(server.EMPTY_PAGE))
    assert response.status == 200
    assert page.evaluate("() => document.body.textContent") == "Yo, page!"


def test_RO_098_should_work_with_status_code_422(page: Page, server: Server) -> None:
    def handler(route: Route) -> None:
        route.fulfill(status=422, body="Yo, page!")

    page.route("**/*", handler)
    response = must(page.goto(server.EMPTY_PAGE))
    assert response.status == 422
    assert response.status_text == "Unprocessable Entity"
    assert page.evaluate("() => document.body.textContent") == "Yo, page!"


def test_RO_099_should_fulfill_with_unuassigned_status_codes(
    page: Page, server: Server
) -> None:
    fulfill_future: "asyncio.Future[Optional[Error]]" = asyncio.Future()

    def handler(route: Route) -> None:
        try:
            route.fulfill(status=430, body="Yo, page!")
            fulfill_future.set_result(None)
        except Error as e:
            fulfill_future.set_result(e)

    page.route("**/data.json", handler)
    page.goto(server.EMPTY_PAGE)
    response = page.evaluate(
        """async url => {
            const { status, statusText } = await fetch(url);
            return { status, statusText };
        }""",
        server.PREFIX + "/data.json",
    )
    error = wait_for(page, fulfill_future)
    assert error is None
    assert response["status"] == 430
    assert response["statusText"] == "Unknown"


def test_RO_100_should_not_throw_if_request_was_cancelled_by_the_page(
    page: Page, server: Server
) -> None:
    intercept_future: "asyncio.Future[Route]" = asyncio.Future()
    page.route("**/data.json", lambda route: intercept_future.set_result(route))
    page.goto(server.EMPTY_PAGE)

    page.evaluate(
        """url => {
            globalThis.controller = new AbortController();
            fetch(url, { signal: globalThis.controller.signal }).catch(() => {});
        }""",
        server.PREFIX + "/data.json",
    )
    route = wait_for(page, intercept_future)
    with page.expect_event("requestfailed") as failure_info:
        page.evaluate("() => globalThis.controller.abort()")
    cancelled_request: Request = failure_info.value
    assert cancelled_request.failure
    assert re.search(r"cancelled|aborted", cancelled_request.failure, re.I)
    route.fulfill(status=200)  # Should not throw.


def test_RO_101_should_allow_mocking_binary_responses(
    page: Page,
    server: Server,
    browser_name: str,
    headless: bool,
    assetdir: Path,
    assert_to_be_golden: Callable[[bytes, str], None],
) -> None:
    if browser_name == "firefox" and not headless:
        pytest.skip("Firefox headed produces a different image.")

    def handler(route: Route) -> None:
        image_buffer = (assetdir / "pptr.png").read_bytes()
        route.fulfill(content_type="image/png", body=image_buffer)

    page.route("**/*", handler)
    page.evaluate(
        """PREFIX => {
            const img = document.createElement('img');
            img.src = PREFIX + '/does-not-exist.png';
            document.body.appendChild(img);
            return new Promise(fulfill => img.onload = fulfill);
        }""",
        server.PREFIX,
    )
    img = must(page.query_selector("img"))
    assert_to_be_golden(img.screenshot(), "mock-binary-response.png")


def test_RO_102_should_allow_mocking_svg_with_charset(
    page: Page,
    server: Server,
    browser_name: str,
    headless: bool,
    assert_to_be_golden: Callable[[bytes, str], None],
) -> None:
    if browser_name == "firefox" and not headless:
        pytest.skip("Firefox headed produces a different image.")

    def handler(route: Route) -> None:
        route.fulfill(
            content_type="image/svg+xml ; charset=utf-8",
            body='<svg width="50" height="50" version="1.1" xmlns="http://www.w3.org/2000/svg"><rect x="10" y="10" width="30" height="30" stroke="black" fill="transparent" stroke-width="5"/></svg>',
        )

    page.route("**/*", handler)
    page.evaluate(
        """PREFIX => {
            const img = document.createElement('img');
            img.src = PREFIX + '/does-not-exist.svg';
            document.body.appendChild(img);
            return new Promise((f, r) => { img.onload = f; img.onerror = r; });
        }""",
        server.PREFIX,
    )
    img = must(page.query_selector("img"))
    assert_to_be_golden(img.screenshot(), "mock-svg.png")


def test_RO_103_should_work_with_file_path(
    page: Page,
    server: Server,
    assetdir: Path,
    assert_to_be_golden: Callable[[bytes, str], None],
) -> None:
    page.route(
        "**/*",
        lambda route: route.fulfill(
            content_type="shouldBeIgnored", path=assetdir / "pptr.png"
        ),
    )
    page.evaluate(
        """PREFIX => {
            const img = document.createElement('img');
            img.src = PREFIX + '/does-not-exist.png';
            document.body.appendChild(img);
            return new Promise(fulfill => img.onload = fulfill);
        }""",
        server.PREFIX,
    )
    img = must(page.query_selector("img"))
    assert_to_be_golden(img.screenshot(), "mock-binary-response.png")


def test_RO_104_should_stringify_intercepted_request_response_headers(
    page: Page, server: Server
) -> None:
    def handler(route: Route) -> None:
        route.fulfill(status=200, headers={"foo": "true"}, body="Yo, page!")

    page.route("**/*", handler)
    response = must(page.goto(server.EMPTY_PAGE))
    assert response.status == 200
    headers = response.headers
    assert headers["foo"] == "true"
    assert page.evaluate("() => document.body.textContent") == "Yo, page!"


def test_RO_105_should_not_modify_the_headers_sent_to_the_server(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/empty.html")
    intercepted_requests: List[TestServerRequest] = []

    # this is just to enable request interception, which disables caching in chromium
    page.route(server.PREFIX + "/unused", lambda route: None)

    def handle(request: TestServerRequest) -> None:
        intercepted_requests.append(request)
        request.setResponseCode(200)
        request.setHeader("Access-Control-Allow-Origin", "*")
        request.write(b"done")
        request.finish()

    server.set_route("/something", handle)

    text = page.evaluate(
        """async url => {
            const data = await fetch(url);
            return data.text();
        }""",
        server.CROSS_PROCESS_PREFIX + "/something",
    )
    assert text == "done"

    def handler(route: Route, request: Request) -> None:
        route.continue_(headers={**request.headers})

    page.route(server.CROSS_PROCESS_PREFIX + "/something", handler)

    text_after_route = page.evaluate(
        """async url => {
            const data = await fetch(url);
            return data.text();
        }""",
        server.CROSS_PROCESS_PREFIX + "/something",
    )
    assert text_after_route == "done"

    assert len(intercepted_requests) == 2
    assert dict(intercepted_requests[1].requestHeaders.getAllRawHeaders()) == dict(
        intercepted_requests[0].requestHeaders.getAllRawHeaders()
    )


def test_RO_106_should_include_the_origin_header(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/empty.html")
    intercepted_requests: List[Request] = []

    def handler(route: Route, request: Request) -> None:
        intercepted_requests.append(request)
        route.fulfill(
            headers={"Access-Control-Allow-Origin": "*"},
            content_type="text/plain",
            body="done",
        )

    page.route(server.CROSS_PROCESS_PREFIX + "/something", handler)

    text = page.evaluate(
        """async url => {
            const data = await fetch(url);
            return data.text();
        }""",
        server.CROSS_PROCESS_PREFIX + "/something",
    )
    assert text == "done"
    assert intercepted_requests[-1].headers["origin"] == server.PREFIX


def test_RO_107_should_fulfill_with_global_fetch_result(
    playwright: Playwright, page: Page, server: Server
) -> None:
    def handler(route: Route) -> None:
        request = playwright.request.new_context()
        response = request.get(server.PREFIX + "/simple.json")
        route.fulfill(response=response)

    page.route("**/*", handler)
    response = must(page.goto(server.EMPTY_PAGE))
    assert response.status == 200
    assert response.json() == {"foo": "bar"}


def test_RO_108_should_fulfill_with_fetch_result(page: Page, server: Server) -> None:
    def handler(route: Route) -> None:
        response = page.request.get(server.PREFIX + "/simple.json")
        route.fulfill(response=response)

    page.route("**/*", handler)
    response = must(page.goto(server.EMPTY_PAGE))
    assert response.status == 200
    assert response.json() == {"foo": "bar"}


def test_RO_109_should_fulfill_with_fetch_result_and_overrides(
    page: Page, server: Server
) -> None:
    def handler(route: Route) -> None:
        response = page.request.get(server.PREFIX + "/simple.json")
        route.fulfill(
            response=response,
            status=201,
            headers={
                "Content-Type": "application/json",  # Case matters for the tested behavior
                "foo": "bar",
            },
        )

    page.route("**/*", handler)
    response = must(page.goto(server.EMPTY_PAGE))
    assert response.status == 201
    assert (response.all_headers())["foo"] == "bar"
    assert response.json() == {"foo": "bar"}


def test_RO_110_should_fetch_original_request_and_fulfill(
    page: Page, server: Server
) -> None:
    def handler(route: Route) -> None:
        response = page.request.fetch(route.request)
        route.fulfill(response=response)

    page.route("**/*", handler)
    response = must(page.goto(server.PREFIX + "/title.html"))
    assert response.status == 200
    assert page.title() == "Woof-Woof"


def test_RO_111_should_fulfill_with_multiple_set_cookie(
    page: Page, server: Server
) -> None:
    cookies = ["a=b", "c=d"]

    def handler(route: Route) -> None:
        route.fulfill(
            status=200,
            headers={
                "X-Header-1": "v1",
                "Set-Cookie": "\n".join(cookies),
                "X-Header-2": "v2",
            },
            body="",
        )

    page.route("**/multiple-set-cookie.html", handler)
    response = must(page.goto(server.PREFIX + "/multiple-set-cookie.html"))
    assert (
        sorted(s.strip() for s in (page.evaluate("() => document.cookie")).split(";"))
        == cookies
    )
    assert response.header_value("X-Header-1") == "v1"
    assert response.header_value("X-Header-2") == "v2"


def test_RO_112_should_fulfill_with_fetch_response_that_has_multiple_set_cookie(
    playwright: Playwright, page: Page, server: Server
) -> None:
    def handle(request: TestServerRequest) -> None:
        request.responseHeaders.setRawHeaders("Set-Cookie", ["a=b", "c=d"])
        request.setHeader("Content-Type", "text/html")
        request.finish()

    server.set_route("/empty.html", handle)

    def handler(route: Route) -> None:
        request = playwright.request.new_context()
        response = request.fetch(route.request)
        route.fulfill(response=response)

    page.route("**/empty.html", handler)
    page.goto(server.EMPTY_PAGE)
    cookie = page.evaluate("() => document.cookie")
    assert sorted(s.strip() for s in cookie.split(";")) == ["a=b", "c=d"]


def test_RO_113_header_value_should_return_set_cookie_from_intercepted_response(
    page: Page, server: Server, browser_name: str, request: pytest.FixtureRequest
) -> None:
    if browser_name == "chromium":
        request.applymarker(
            pytest.mark.xfail(
                reason="upstream: Set-Cookie is missing in response after interception",
                strict=True,
            )
        )
    if browser_name == "webkit":
        pytest.skip(
            "Set-Cookie with \\n in intercepted response does not pass validation in WebCore, see also https://github.com/microsoft/playwright/pull/9273"
        )

    def handler(route: Route) -> None:
        route.fulfill(status=200, headers={"Set-Cookie": "a=b"}, body="")

    page.route("**/empty.html", handler)
    response = must(page.goto(server.EMPTY_PAGE))
    assert response.header_value("Set-Cookie") == "a=b"


def find_response(har: Dict[str, Any], url: str) -> Dict[str, Any]:
    entry: Optional[Dict[str, Any]] = None
    original_url = url
    while url.strip():
        entry = next(
            (e for e in har["log"]["entries"] if e["request"]["url"] == url), None
        )
        url = entry["response"]["redirectURL"] if entry else ""
    assert entry, original_url
    return entry["response"]


def test_RO_114_should_fulfill_with_har_response(page: Page, assetdir: Path) -> None:
    har_path = assetdir / "har-fulfill.har"
    har = json.loads(har_path.read_text(encoding="utf-8"))

    def handler(route: Route) -> None:
        response = find_response(har, route.request.url)
        headers = {}
        for header in response["headers"]:
            headers[header["name"]] = header["value"]
        text = response["content"].get("text") or ""
        if response["content"].get("encoding") == "base64":
            body = base64.b64decode(text)
        else:
            body = text.encode("utf-8")
        route.fulfill(status=response["status"], headers=headers, body=body)

    page.route("**/*", handler)
    page.goto("http://no.playwright/")
    # HAR contains a redirect for the script.
    assert page.evaluate("window.value") == "foo"
    # HAR contains a POST for the css file but we match ignoring the method, so the file should be served.
    expect(page.locator("body")).to_have_css("background-color", "rgb(0, 255, 255)")


def test_RO_115_should_fulfill_preload_link_requests(
    page: Page, server: Server
) -> None:
    intercepted = False

    def handler(route: Route) -> None:
        nonlocal intercepted
        intercepted = True
        route.fulfill(
            status=200,
            headers={
                "content-type": "text/css; charset=utf-8",
                "cache-control": "no-cache, no-store",
                "custom": "value",
            },
            body="body { background-color: green; }",
        )

    page.route("**/one-style.css", handler)
    with page.expect_response("**/one-style.css") as response_info:
        page.goto(server.PREFIX + "/preload.html")
    response = response_info.value
    assert response.header_value("custom") == "value"
    page.wait_for_function("() => window.preloadedStyles")
    assert intercepted is True
    color = page.evaluate(
        "() => window.getComputedStyle(document.body).backgroundColor"
    )
    assert color == "rgb(0, 128, 0)"


def test_RO_116_should_fulfill_json(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)

    def handler(route: Route) -> None:
        route.fulfill(status=201, headers={"foo": "bar"}, json={"bar": "baz"})

    page.route("**/data.json", handler)
    with page.expect_response("**/*") as response_info:
        body = page.evaluate("() => fetch('./data.json').then(r => r.text())")
    response = response_info.value
    assert response.status == 201
    assert response.headers["content-type"] == "application/json"
    assert body == '{"bar":"baz"}'


def test_RO_117_should_fulfill_with_gzip_and_readback(
    page: Page, server: Server
) -> None:
    server.enable_gzip("/one-style.html")

    def handler(route: Route) -> None:
        response = route.fetch()
        assert response.headers["content-encoding"] == "gzip"
        route.fulfill(response=response)

    page.route("**/one-style.html", handler)

    response = must(page.goto(server.PREFIX + "/one-style.html"))
    expect(page.locator("div")).to_have_text("hello, world!")
    expect(page.locator("body")).to_have_css("background-color", "rgb(255, 192, 203)")
    assert "<div>hello, world!</div>" in response.text()


def test_RO_118_should_not_go_to_the_network_for_fulfilled_requests_body(
    page: Page, server: Server
) -> None:
    def handler(route: Route) -> None:
        route.fulfill(status=404, content_type="text/plain", body="Not Found! (mocked)")

    page.route("**/one-style.css", handler)

    server_hit = False

    def handle(request: TestServerRequest) -> None:
        nonlocal server_hit
        server_hit = True
        request.setHeader("Content-Type", "text/css")
        request.write(b"body { background-color: green; }")
        request.finish()

    server.set_route("/one-style.css", handle)

    with page.expect_response("**/one-style.css") as response_info:
        page.goto(server.PREFIX + "/one-style.html")
    response = response_info.value
    body = response.body()
    assert body.decode() == "Not Found! (mocked)"
    assert server_hit is False


def test_RO_119_should_return_body_for_fulfilled_responses(
    page: Page, server: Server
) -> None:
    for status in [100, 200, 404, 500]:
        body_override = f"Custom body {status}"

        def handler(route: Route) -> None:
            route.fulfill(status=status, content_type="text/plain", body=body_override)

        page.route("**/one-style.css", handler)

        with page.expect_response("**/one-style.css") as response_info:
            page.goto(server.PREFIX + "/one-style.html")
        response = response_info.value
        body = response.body()
        assert body.decode() == body_override
        page.unroute_all()
