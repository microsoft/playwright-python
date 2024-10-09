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
import re
from pathlib import Path
from typing import Callable, List, Optional

import pytest

from playwright._impl._glob import glob_to_regex
from playwright.async_api import (
    Browser,
    BrowserContext,
    Error,
    Page,
    Playwright,
    Request,
    Route,
)
from tests.server import Server, TestServerRequest
from tests.utils import must


async def test_page_route_should_intercept(page: Page, server: Server) -> None:
    intercepted = []

    async def handle_request(route: Route, request: Request) -> None:
        assert route.request == request
        assert "empty.html" in request.url
        assert request.headers["user-agent"]
        assert request.method == "GET"
        assert request.post_data is None
        assert request.is_navigation_request()
        assert request.resource_type == "document"
        assert request.frame == page.main_frame
        assert request.frame.url == "about:blank"
        await route.continue_()
        intercepted.append(True)

    await page.route("**/empty.html", handle_request)

    response = await page.goto(server.EMPTY_PAGE)
    assert response
    assert response.ok
    assert len(intercepted) == 1


async def test_page_route_should_unroute(page: Page, server: Server) -> None:
    intercepted = []

    def _handle1(route: Route) -> None:
        intercepted.append(1)
        asyncio.create_task(route.continue_())

    await page.route("**/*", _handle1)

    def _handle2(route: Route, request: Request) -> None:
        intercepted.append(2)
        asyncio.create_task(route.continue_())

    await page.route("**/empty.html", _handle2)

    def _handle3(route: Route, request: Request) -> None:
        intercepted.append(3)
        asyncio.create_task(route.continue_())

    await page.route(
        "**/empty.html",
        _handle3,
    )

    def handler4(route: Route) -> None:
        intercepted.append(4)
        asyncio.create_task(route.continue_())

    await page.route(re.compile("empty.html"), handler4)

    await page.goto(server.EMPTY_PAGE)
    assert intercepted == [4]

    intercepted = []
    await page.unroute(re.compile("empty.html"), handler4)
    await page.goto(server.EMPTY_PAGE)
    assert intercepted == [3]

    intercepted = []
    await page.unroute("**/empty.html")
    await page.goto(server.EMPTY_PAGE)
    assert intercepted == [1]


async def test_page_route_should_work_when_POST_is_redirected_with_302(
    page: Page, server: Server
) -> None:
    server.set_redirect("/rredirect", "/empty.html")
    await page.goto(server.EMPTY_PAGE)
    await page.route("**/*", lambda route: route.continue_())
    await page.set_content(
        """
      <form action='/rredirect' method='post'>
        <input type="hidden" id="foo" name="foo" value="FOOBAR">
      </form>
    """
    )
    async with page.expect_navigation():
        await page.eval_on_selector("form", "form => form.submit()")


# @see https://github.com/GoogleChrome/puppeteer/issues/3973
async def test_page_route_should_work_when_header_manipulation_headers_with_redirect(
    page: Page, server: Server
) -> None:
    server.set_redirect("/rrredirect", "/empty.html")
    await page.route(
        "**/*",
        lambda route: route.continue_(headers={**route.request.headers, "foo": "bar"}),
    )

    await page.goto(server.PREFIX + "/rrredirect")


# @see https://github.com/GoogleChrome/puppeteer/issues/4743
async def test_page_route_should_be_able_to_remove_headers(
    page: Page, server: Server
) -> None:
    async def handle_request(route: Route) -> None:
        headers = route.request.headers
        if "origin" in headers:
            del headers["origin"]
        await route.continue_(headers=headers)

    await page.route(
        "**/*",  # remove "origin" header
        handle_request,
    )

    [serverRequest, _] = await asyncio.gather(
        server.wait_for_request("/empty.html"), page.goto(server.PREFIX + "/empty.html")
    )
    assert serverRequest.getHeader("origin") is None


async def test_page_route_should_contain_referer_header(
    page: Page, server: Server
) -> None:
    requests = []

    def _handle(route: Route, request: Request) -> None:
        requests.append(route.request)
        asyncio.create_task(route.continue_())

    await page.route(
        "**/*",
        _handle,
    )

    await page.goto(server.PREFIX + "/one-style.html")
    assert "/one-style.css" in requests[1].url
    assert "/one-style.html" in requests[1].headers["referer"]


async def test_page_route_should_properly_return_navigation_response_when_URL_has_cookies(
    context: BrowserContext, page: Page, server: Server
) -> None:
    # Setup cookie.
    await page.goto(server.EMPTY_PAGE)
    await context.add_cookies(
        [{"url": server.EMPTY_PAGE, "name": "foo", "value": "bar"}]
    )

    # Setup request interception.
    await page.route("**/*", lambda route: route.continue_())
    response = await page.reload()
    assert response
    assert response.status == 200


async def test_page_route_should_show_custom_HTTP_headers(
    page: Page, server: Server
) -> None:
    await page.set_extra_http_headers({"foo": "bar"})

    def assert_headers(request: Request) -> None:
        assert request.headers["foo"] == "bar"

    def _handle(route: Route) -> None:
        assert_headers(route.request)
        asyncio.create_task(route.continue_())

    await page.route(
        "**/*",
        _handle,
    )

    response = await page.goto(server.EMPTY_PAGE)
    assert response
    assert response.ok


# @see https://github.com/GoogleChrome/puppeteer/issues/4337
async def test_page_route_should_work_with_redirect_inside_sync_XHR(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    server.set_redirect("/logo.png", "/pptr.png")
    await page.route("**/*", lambda route: route.continue_())
    status = await page.evaluate(
        """async() => {
      const request = new XMLHttpRequest();
      request.open('GET', '/logo.png', false);  // `false` makes the request synchronous
      request.send(null);
      return request.status;
    }"""
    )

    assert status == 200


async def test_page_route_should_work_with_custom_referer_headers(
    page: Page, server: Server
) -> None:
    await page.set_extra_http_headers({"referer": server.EMPTY_PAGE})

    def assert_headers(route: Route) -> None:
        assert route.request.headers["referer"] == server.EMPTY_PAGE

    def _handle(route: Route, request: Request) -> None:
        assert_headers(route)
        asyncio.create_task(route.continue_())

    await page.route(
        "**/*",
        _handle,
    )

    response = await page.goto(server.EMPTY_PAGE)
    assert response
    assert response.ok


async def test_page_route_should_be_abortable(page: Page, server: Server) -> None:
    await page.route(r"/\.css$/", lambda route: asyncio.create_task(route.abort()))
    failed = []

    def handle_request(request: Request) -> None:
        if ".css" in request.url:
            failed.append(True)

    page.on("requestfailed", handle_request)

    response = await page.goto(server.PREFIX + "/one-style.html")
    assert response
    assert response.ok
    assert response.request.failure is None
    assert len(failed) == 0


async def test_page_route_should_be_abortable_with_custom_error_codes(
    page: Page, server: Server, is_webkit: bool, is_firefox: bool
) -> None:
    await page.route(
        "**/*",
        lambda route: route.abort("internetdisconnected"),
    )
    failed_requests = []
    page.on("requestfailed", lambda request: failed_requests.append(request))
    with pytest.raises(Error):
        await page.goto(server.EMPTY_PAGE)
    assert len(failed_requests) == 1
    failed_request = failed_requests[0]
    if is_webkit:
        assert failed_request.failure == "Blocked by Web Inspector"
    elif is_firefox:
        assert failed_request.failure == "NS_ERROR_OFFLINE"
    else:
        assert failed_request.failure == "net::ERR_INTERNET_DISCONNECTED"


async def test_page_route_should_send_referer(page: Page, server: Server) -> None:
    await page.set_extra_http_headers({"referer": "http://google.com/"})

    await page.route("**/*", lambda route: route.continue_())
    [request, _] = await asyncio.gather(
        server.wait_for_request("/grid.html"),
        page.goto(server.PREFIX + "/grid.html"),
    )
    assert request.getHeader("referer") == "http://google.com/"


async def test_page_route_should_fail_navigation_when_aborting_main_resource(
    page: Page, server: Server, is_webkit: bool, is_firefox: bool
) -> None:
    await page.route("**/*", lambda route: route.abort())
    with pytest.raises(Error) as exc:
        await page.goto(server.EMPTY_PAGE)
    assert exc
    if is_webkit:
        assert "Blocked by Web Inspector" in exc.value.message
    elif is_firefox:
        assert "NS_ERROR_FAILURE" in exc.value.message
    else:
        assert "net::ERR_FAILED" in exc.value.message


async def test_page_route_should_not_work_with_redirects(
    page: Page, server: Server
) -> None:
    intercepted = []

    def _handle(route: Route, request: Request) -> None:
        asyncio.create_task(route.continue_())
        intercepted.append(route.request)

    await page.route(
        "**/*",
        _handle,
    )

    server.set_redirect("/non-existing-page.html", "/non-existing-page-2.html")
    server.set_redirect("/non-existing-page-2.html", "/non-existing-page-3.html")
    server.set_redirect("/non-existing-page-3.html", "/non-existing-page-4.html")
    server.set_redirect("/non-existing-page-4.html", "/empty.html")

    response = await page.goto(server.PREFIX + "/non-existing-page.html")
    assert response
    assert response.status == 200
    assert "empty.html" in response.url

    assert len(intercepted) == 1
    assert intercepted[0].resource_type == "document"
    assert intercepted[0].is_navigation_request()
    assert "/non-existing-page.html" in intercepted[0].url

    chain = []
    r: Optional[Request] = response.request
    while r:
        chain.append(r)
        assert r.is_navigation_request()
        r = r.redirected_from

    assert len(chain) == 5
    assert "/empty.html" in chain[0].url
    assert "/non-existing-page-4.html" in chain[1].url
    assert "/non-existing-page-3.html" in chain[2].url
    assert "/non-existing-page-2.html" in chain[3].url
    assert "/non-existing-page.html" in chain[4].url
    for idx, _ in enumerate(chain):
        assert chain[idx].redirected_to == (chain[idx - 1] if idx > 0 else None)


async def test_page_route_should_work_with_redirects_for_subresources(
    page: Page, server: Server
) -> None:
    intercepted: List[Request] = []

    def _handle(route: Route) -> None:
        asyncio.create_task(route.continue_())
        intercepted.append(route.request)

    await page.route(
        "**/*",
        _handle,
    )

    server.set_redirect("/one-style.css", "/two-style.css")
    server.set_redirect("/two-style.css", "/three-style.css")
    server.set_redirect("/three-style.css", "/four-style.css")
    server.set_route(
        "/four-style.css",
        lambda req: (req.write(b"body {box-sizing: border-box; }"), req.finish()),
    )

    response = await page.goto(server.PREFIX + "/one-style.html")
    assert response
    assert response.status == 200
    assert "one-style.html" in response.url

    # TODO: https://github.com/microsoft/playwright/issues/12789
    assert len(intercepted) >= 2
    assert intercepted[0].resource_type == "document"
    assert "one-style.html" in intercepted[0].url

    r: Optional[Request] = intercepted[1]
    for url in [
        "/one-style.css",
        "/two-style.css",
        "/three-style.css",
        "/four-style.css",
    ]:
        assert r
        assert r.resource_type == "stylesheet"
        assert url in r.url
        r = r.redirected_to
    assert r is None


async def test_page_route_should_work_with_equal_requests(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    hits = [True]

    def handle_request(request: TestServerRequest, hits: List[bool]) -> None:
        request.write(str(len(hits) * 11).encode())
        request.finish()
        hits.append(True)

    server.set_route("/zzz", lambda r: handle_request(r, hits))

    spinner: List[bool] = []

    async def handle_route(route: Route) -> None:
        if len(spinner) == 1:
            await route.abort()
            spinner.pop(0)
        else:
            await route.continue_()
            spinner.append(True)

    # Cancel 2nd request.
    await page.route("**/*", handle_route)

    results = []
    for idx in range(3):
        results.append(
            await page.evaluate(
                """() => fetch('/zzz').then(response => response.text()).catch(e => 'FAILED')"""
            )
        )
    assert results == ["11", "FAILED", "22"]


async def test_page_route_should_navigate_to_dataURL_and_not_fire_dataURL_requests(
    page: Page, server: Server
) -> None:
    requests = []

    def _handle(route: Route) -> None:
        requests.append(route.request)
        asyncio.create_task(route.continue_())

    await page.route(
        "**/*",
        _handle,
    )

    data_URL = "data:text/html,<div>yo</div>"
    response = await page.goto(data_URL)
    assert response is None
    assert len(requests) == 0


async def test_page_route_should_be_able_to_fetch_dataURL_and_not_fire_dataURL_requests(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    requests = []

    def _handle(route: Route) -> None:
        requests.append(route.request)
        asyncio.create_task(route.continue_())

    await page.route("**/*", _handle)

    data_URL = "data:text/html,<div>yo</div>"
    text = await page.evaluate("url => fetch(url).then(r => r.text())", data_URL)
    assert text == "<div>yo</div>"
    assert len(requests) == 0


async def test_page_route_should_navigate_to_URL_with_hash_and_and_fire_requests_without_hash(
    page: Page, server: Server
) -> None:
    requests = []

    def _handle(route: Route) -> None:
        requests.append(route.request)
        asyncio.create_task(route.continue_())

    await page.route(
        "**/*",
        _handle,
    )

    response = await page.goto(server.EMPTY_PAGE + "#hash")
    assert response
    assert response.status == 200
    assert response.url == server.EMPTY_PAGE
    assert len(requests) == 1
    assert requests[0].url == server.EMPTY_PAGE


async def test_page_route_should_work_with_encoded_server(
    page: Page, server: Server
) -> None:
    # The requestWillBeSent will report encoded URL, whereas interception will
    # report URL as-is. @see crbug.com/759388
    await page.route("**/*", lambda route: route.continue_())
    response = await page.goto(server.PREFIX + "/some nonexisting page")
    assert response
    assert response.status == 404


async def test_page_route_should_work_with_encoded_server___2(
    page: Page, server: Server
) -> None:
    # The requestWillBeSent will report URL as-is, whereas interception will
    # report encoded URL for stylesheet. @see crbug.com/759388
    requests: List[Request] = []

    def _handle(route: Route) -> None:
        asyncio.create_task(route.continue_())
        requests.append(route.request)

    await page.route("**/*", _handle)

    response = await page.goto(
        f"""data:text/html,<link rel="stylesheet" href="{server.PREFIX}/fonts?helvetica|arial"/>"""
    )
    assert response is None
    # TODO: https://github.com/microsoft/playwright/issues/12789
    assert len(requests) >= 1
    assert (must(await requests[0].response())).status == 404


async def test_page_route_should_not_throw_Invalid_Interception_Id_if_the_request_was_cancelled(
    page: Page, server: Server
) -> None:
    await page.set_content("<iframe></iframe>")
    route_future: "asyncio.Future[Route]" = asyncio.Future()
    await page.route("**/*", lambda r, _: route_future.set_result(r))

    async with page.expect_request("**/*"):
        await page.eval_on_selector(
            "iframe", """(frame, url) => frame.src = url""", server.EMPTY_PAGE
        )
    # Delete frame to cause request to be canceled.
    await page.eval_on_selector("iframe", "frame => frame.remove()")
    route = await route_future
    await route.continue_()


async def test_page_route_should_intercept_main_resource_during_cross_process_navigation(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    intercepted = []

    def _handle(route: Route) -> None:
        intercepted.append(True)
        asyncio.create_task(route.continue_())

    await page.route(
        server.CROSS_PROCESS_PREFIX + "/empty.html",
        _handle,
    )

    response = await page.goto(server.CROSS_PROCESS_PREFIX + "/empty.html")
    assert response
    assert response.ok
    assert len(intercepted) == 1


@pytest.mark.skip_browser("webkit")
async def test_page_route_should_create_a_redirect(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/empty.html")

    async def handle_route(route: Route, request: Request) -> None:
        if request.url != (server.PREFIX + "/redirect_this"):
            return await route.continue_()
        await route.fulfill(status=301, headers={"location": "/empty.html"})

    await page.route(
        "**/*",
        handle_route,
    )

    text = await page.evaluate(
        """async url => {
      const data = await fetch(url);
      return data.text();
    }""",
        server.PREFIX + "/redirect_this",
    )
    assert text == ""


async def test_page_route_should_support_cors_with_GET(
    page: Page, server: Server, browser_name: str
) -> None:
    await page.goto(server.EMPTY_PAGE)

    async def handle_route(route: Route, request: Request) -> None:
        headers = {
            "access-control-allow-origin": (
                "*" if request.url.endswith("allow") else "none"
            )
        }
        await route.fulfill(
            content_type="application/json",
            headers=headers,
            status=200,
            body=json.dumps(["electric", "gas"]),
        )

    await page.route(
        "**/cars*",
        handle_route,
    )
    # Should succeed
    resp = await page.evaluate(
        """async () => {
        const response = await fetch('https://example.com/cars?allow', { mode: 'cors' });
        return response.json();
      }"""
    )

    assert resp == ["electric", "gas"]

    # Should be rejected
    with pytest.raises(Error) as exc:
        await page.evaluate(
            """async () => {
            const response = await fetch('https://example.com/cars?reject', { mode: 'cors' });
            return response.json();
        }"""
        )
    if browser_name == "chromium":
        assert "Failed" in exc.value.message
    elif browser_name == "webkit":
        assert "TypeError" in exc.value.message
    elif browser_name == "firefox":
        assert "NetworkError" in exc.value.message


async def test_page_route_should_support_cors_with_POST(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.route(
        "**/cars",
        lambda route: route.fulfill(
            content_type="application/json",
            headers={"Access-Control-Allow-Origin": "*"},
            status=200,
            body=json.dumps(["electric", "gas"]),
        ),
    )

    resp = await page.evaluate(
        """async () => {
      const response = await fetch('https://example.com/cars', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        mode: 'cors',
        body: JSON.stringify({ 'number': 1 })
      });
      return response.json();
    }"""
    )

    assert resp == ["electric", "gas"]


async def test_page_route_should_support_cors_for_different_methods(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.route(
        "**/cars",
        lambda route, request: route.fulfill(
            content_type="application/json",
            headers={"Access-Control-Allow-Origin": "*"},
            status=200,
            body=json.dumps([request.method, "electric", "gas"]),
        ),
    )

    # First POST
    resp = await page.evaluate(
        """async () => {
        const response = await fetch('https://example.com/cars', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          mode: 'cors',
          body: JSON.stringify({ 'number': 1 })
        });
        return response.json();
      }"""
    )

    assert resp == ["POST", "electric", "gas"]
    # Then DELETE
    resp = await page.evaluate(
        """async () => {
        const response = await fetch('https://example.com/cars', {
          method: 'DELETE',
          headers: {},
          mode: 'cors',
          body: ''
        });
        return response.json();
      }"""
    )

    assert resp == ["DELETE", "electric", "gas"]


async def test_request_fulfill_should_work_a(page: Page, server: Server) -> None:
    await page.route(
        "**/*",
        lambda route: route.fulfill(
            status=201,
            headers={"foo": "bar"},
            content_type="text/html",
            body="Yo, page!",
        ),
    )

    response = await page.goto(server.EMPTY_PAGE)
    assert response
    assert response.status == 201
    assert response.headers["foo"] == "bar"
    assert await page.evaluate("() => document.body.textContent") == "Yo, page!"


async def test_request_fulfill_should_work_with_status_code_422(
    page: Page, server: Server
) -> None:
    await page.route(
        "**/*",
        lambda route: route.fulfill(status=422, body="Yo, page!"),
    )

    response = await page.goto(server.EMPTY_PAGE)
    assert response
    assert response.status == 422
    assert response.status_text == "Unprocessable Entity"
    assert await page.evaluate("() => document.body.textContent") == "Yo, page!"


async def test_request_fulfill_should_allow_mocking_binary_responses(
    page: Page,
    server: Server,
    assert_to_be_golden: Callable[[bytes, str], None],
    assetdir: Path,
) -> None:
    await page.route(
        "**/*",
        lambda route: route.fulfill(
            content_type="image/png",
            body=(assetdir / "pptr.png").read_bytes(),
        ),
    )

    await page.evaluate(
        """PREFIX => {
      const img = document.createElement('img');
      img.src = PREFIX + '/does-not-exist.png';
      document.body.appendChild(img);
      return new Promise(fulfill => img.onload = fulfill);
    }""",
        server.PREFIX,
    )
    img = await page.query_selector("img")
    assert img
    assert_to_be_golden(await img.screenshot(), "mock-binary-response.png")


async def test_request_fulfill_should_allow_mocking_svg_with_charset(
    page: Page, server: Server, assert_to_be_golden: Callable[[bytes, str], None]
) -> None:
    await page.route(
        "**/*",
        lambda route: route.fulfill(
            content_type="image/svg+xml ; charset=utf-8",
            body='<svg width="50" height="50" version="1.1" xmlns="http://www.w3.org/2000/svg"><rect x="10" y="10" width="30" height="30" stroke="black" fill="transparent" stroke-width="5"/></svg>',
        ),
    )

    await page.evaluate(
        """PREFIX => {
      const img = document.createElement('img');
      img.src = PREFIX + '/does-not-exist.svg';
      document.body.appendChild(img);
      return new Promise((f, r) => { img.onload = f; img.onerror = r; });
    }""",
        server.PREFIX,
    )
    img = await page.query_selector("img")
    assert img
    assert_to_be_golden(await img.screenshot(), "mock-svg.png")


async def test_request_fulfill_should_work_with_file_path(
    page: Page,
    server: Server,
    assert_to_be_golden: Callable[[bytes, str], None],
    assetdir: Path,
) -> None:
    await page.route(
        "**/*",
        lambda route: route.fulfill(
            content_type="shouldBeIgnored", path=assetdir / "pptr.png"
        ),
    )
    await page.evaluate(
        """PREFIX => {
      const img = document.createElement('img');
      img.src = PREFIX + '/does-not-exist.png';
      document.body.appendChild(img);
      return new Promise(fulfill => img.onload = fulfill);
    }""",
        server.PREFIX,
    )
    img = await page.query_selector("img")
    assert img
    assert_to_be_golden(await img.screenshot(), "mock-binary-response.png")


async def test_request_fulfill_should_stringify_intercepted_request_response_headers(
    page: Page, server: Server
) -> None:
    await page.route(
        "**/*",
        lambda route: route.fulfill(
            status=200, headers={"foo": True}, body="Yo, page!"  # type: ignore
        ),
    )

    response = await page.goto(server.EMPTY_PAGE)
    assert response
    assert response.status == 200
    headers = response.headers
    assert headers["foo"] == "True"
    assert await page.evaluate("() => document.body.textContent") == "Yo, page!"


async def test_request_fulfill_should_not_modify_the_headers_sent_to_the_server(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/empty.html")
    interceptedRequests = []

    # this is just to enable request interception, which disables caching in chromium
    await page.route(server.PREFIX + "/unused", lambda route, req: None)

    def _handler1(response: TestServerRequest) -> None:
        interceptedRequests.append(response)
        response.setHeader("Access-Control-Allow-Origin", "*")
        response.write(b"done")
        response.finish()

    server.set_route("/something", _handler1)

    text = await page.evaluate(
        """async url => {
      const data = await fetch(url);
      return data.text();
    }""",
        server.CROSS_PROCESS_PREFIX + "/something",
    )
    assert text == "done"

    playwrightRequest: "asyncio.Future[Request]" = asyncio.Future()

    def _handler2(route: Route, request: Request) -> None:
        playwrightRequest.set_result(request)
        asyncio.create_task(route.continue_(headers={**request.headers}))

    await page.route(
        server.CROSS_PROCESS_PREFIX + "/something",
        _handler2,
    )

    textAfterRoute = await page.evaluate(
        """async url => {
      const data = await fetch(url);
      return data.text();
    }""",
        server.CROSS_PROCESS_PREFIX + "/something",
    )
    assert textAfterRoute == "done"

    assert len(interceptedRequests) == 2
    assert (
        interceptedRequests[0].requestHeaders == interceptedRequests[1].requestHeaders
    )


async def test_request_fulfill_should_include_the_origin_header(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/empty.html")
    interceptedRequest = []

    def _handle(route: Route, request: Request) -> None:
        interceptedRequest.append(request)
        asyncio.create_task(
            route.fulfill(
                headers={"Access-Control-Allow-Origin": "*"},
                content_type="text/plain",
                body="done",
            )
        )

    await page.route(server.CROSS_PROCESS_PREFIX + "/something", _handle)

    text = await page.evaluate(
        """async url => {
      const data = await fetch(url);
      return data.text();
    }""",
        server.CROSS_PROCESS_PREFIX + "/something",
    )
    assert text == "done"
    assert len(interceptedRequest) == 1
    assert interceptedRequest[0].headers["origin"] == server.PREFIX


async def test_request_fulfill_should_work_with_request_interception(
    page: Page, server: Server
) -> None:
    requests = {}

    async def _handle_route(route: Route) -> None:
        requests[route.request.url.split("/").pop()] = route.request
        await route.continue_()

    await page.route("**/*", _handle_route)

    server.set_redirect("/rrredirect", "/frames/one-frame.html")
    await page.goto(server.PREFIX + "/rrredirect")
    assert requests["rrredirect"].is_navigation_request()
    assert requests["frame.html"].is_navigation_request()
    assert requests["script.js"].is_navigation_request() is False
    assert requests["style.css"].is_navigation_request() is False


async def test_Interception_should_work_with_request_interception(
    browser: Browser, https_server: Server
) -> None:
    context = await browser.new_context(ignore_https_errors=True)
    page = await context.new_page()

    await page.route("**/*", lambda route: asyncio.ensure_future(route.continue_()))
    response = await page.goto(https_server.EMPTY_PAGE)
    assert response
    assert response.status == 200
    await context.close()


async def test_ignore_http_errors_service_worker_should_intercept_after_a_service_worker(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/serviceworkers/fetchdummy/sw.html")
    await page.evaluate("() => window.activationPromise")

    # Sanity check.
    sw_response = await page.evaluate('() => fetchDummy("foo")')
    assert sw_response == "responseFromServiceWorker:foo"

    def _handle_route(route: Route) -> None:
        asyncio.ensure_future(
            route.fulfill(
                status=200,
                content_type="text/css",
                body="responseFromInterception:" + route.request.url.split("/")[-1],
            )
        )

    await page.route("**/foo", _handle_route)

    # Page route is applied after service worker fetch event.
    sw_response2 = await page.evaluate('() => fetchDummy("foo")')
    assert sw_response2 == "responseFromServiceWorker:foo"

    # Page route is not applied to service worker initiated fetch.
    non_intercepted_response = await page.evaluate('() => fetchDummy("passthrough")')
    assert non_intercepted_response == "FAILURE: Not Found"


async def test_page_route_should_support_times_parameter(
    page: Page, server: Server
) -> None:
    intercepted = []

    async def handle_request(route: Route) -> None:
        await route.continue_()
        intercepted.append(True)

    await page.route("**/empty.html", handle_request, times=1)

    await page.goto(server.EMPTY_PAGE)
    await page.goto(server.EMPTY_PAGE)
    await page.goto(server.EMPTY_PAGE)
    assert len(intercepted) == 1


async def test_should_work_if_handler_with_times_parameter_was_removed_from_another_handler(
    context: BrowserContext, page: Page, server: Server
) -> None:
    intercepted = []

    async def handler(route: Route) -> None:
        intercepted.append("first")
        await route.continue_()

    await page.route("**/*", handler, times=1)

    async def handler2(route: Route) -> None:
        intercepted.append("second")
        await page.unroute("**/*", handler)
        await route.fallback()

    await page.route("**/*", handler2)
    await page.goto(server.EMPTY_PAGE)
    assert intercepted == ["second"]
    intercepted.clear()
    await page.goto(server.EMPTY_PAGE)
    assert intercepted == ["second"]


async def test_should_fulfill_with_global_fetch_result(
    page: Page, playwright: Playwright, server: Server
) -> None:
    async def handle_request(route: Route) -> None:
        request = await playwright.request.new_context()
        response = await request.get(server.PREFIX + "/simple.json")
        await route.fulfill(response=response)
        await request.dispose()

    await page.route("**/*", handle_request)

    response = await page.goto(server.EMPTY_PAGE)
    assert response
    assert response.status == 200
    assert await response.json() == {"foo": "bar"}


async def test_glob_to_regex() -> None:
    assert glob_to_regex("**/*.js").match("https://localhost:8080/foo.js")
    assert not glob_to_regex("**/*.css").match("https://localhost:8080/foo.js")
    assert not glob_to_regex("*.js").match("https://localhost:8080/foo.js")
    assert glob_to_regex("https://**/*.js").match("https://localhost:8080/foo.js")
    assert glob_to_regex("http://localhost:8080/simple/path.js").match(
        "http://localhost:8080/simple/path.js"
    )
    assert glob_to_regex("http://localhost:8080/?imple/path.js").match(
        "http://localhost:8080/Simple/path.js"
    )
    assert glob_to_regex("**/{a,b}.js").match("https://localhost:8080/a.js")
    assert glob_to_regex("**/{a,b}.js").match("https://localhost:8080/b.js")
    assert not glob_to_regex("**/{a,b}.js").match("https://localhost:8080/c.js")

    assert glob_to_regex("**/*.{png,jpg,jpeg}").match("https://localhost:8080/c.jpg")
    assert glob_to_regex("**/*.{png,jpg,jpeg}").match("https://localhost:8080/c.jpeg")
    assert glob_to_regex("**/*.{png,jpg,jpeg}").match("https://localhost:8080/c.png")
    assert not glob_to_regex("**/*.{png,jpg,jpeg}").match(
        "https://localhost:8080/c.css"
    )
    assert glob_to_regex("foo*").match("foo.js")
    assert not glob_to_regex("foo*").match("foo/bar.js")
    assert not glob_to_regex("http://localhost:3000/signin-oidc*").match(
        "http://localhost:3000/signin-oidc/foo"
    )
    assert glob_to_regex("http://localhost:3000/signin-oidc*").match(
        "http://localhost:3000/signin-oidcnice"
    )

    assert glob_to_regex("**/three-columns/settings.html?**id=[a-z]**").match(
        "http://mydomain:8080/blah/blah/three-columns/settings.html?id=settings-e3c58efe-02e9-44b0-97ac-dd138100cf7c&blah"
    )

    assert glob_to_regex("\\?") == re.compile(r"^\?$")
    assert glob_to_regex("\\") == re.compile(r"^\\$")
    assert glob_to_regex("\\\\") == re.compile(r"^\\$")
    assert glob_to_regex("\\[") == re.compile(r"^\[$")
    assert glob_to_regex("[a-z]") == re.compile(r"^[a-z]$")
    assert glob_to_regex("$^+.\\*()|\\?\\{\\}\\[\\]") == re.compile(
        r"^\$\^\+\.\*\(\)\|\?\{\}\[\]$"
    )
