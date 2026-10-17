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

"""Port of tests/page/page-route.spec.ts."""

import asyncio
import json
import re
import time
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse

import pytest

from playwright.async_api import Error, Page, Request, Route, expect
from tests.server import Server, TestServerRequest


def end(body: str) -> Callable[[TestServerRequest], None]:
    """A server route that answers with body, like upstream's res.end(body)."""

    def handler(request: TestServerRequest) -> None:
        request.write(body.encode())
        request.finish()

    return handler


async def wait_for_list(page: Page, values: List[Any]) -> None:
    """Waits until a route handler adds to values.

    Port of awaiting the promise that upstream's route handler resolves.
    """
    deadline = time.monotonic() + 10
    while not values:
        assert time.monotonic() < deadline, "the route handler did not run"
        await page.wait_for_timeout(20)


async def test_RO_001_should_intercept_smoke(page: Page, server: Server) -> None:
    intercepted = False

    async def handler(route: Route, request: Request) -> None:
        nonlocal intercepted
        assert route.request == request
        assert "empty.html" in request.url
        assert request.headers["user-agent"]
        assert request.method == "GET"
        assert request.post_data is None
        assert request.is_navigation_request() is True
        assert request.resource_type == "document"
        assert request.frame == page.main_frame
        assert request.frame.url == "about:blank"
        intercepted = True
        await route.continue_()

    await page.route("**/empty.html", handler)
    response = await page.goto(server.EMPTY_PAGE)
    assert response
    assert response.ok is True
    assert intercepted is True


async def test_RO_002_should_unroute(page: Page, server: Server) -> None:
    intercepted: List[int] = []

    async def handler1(route: Route) -> None:
        intercepted.append(1)
        await route.fallback()

    async def handler2(route: Route) -> None:
        intercepted.append(2)
        await route.fallback()

    async def handler3(route: Route) -> None:
        intercepted.append(3)
        await route.fallback()

    async def handler4(route: Route) -> None:
        intercepted.append(4)
        await route.fallback()

    await page.route("**/*", handler1)
    await page.route("**/empty.html", handler2)
    await page.route("**/empty.html", handler3)
    await page.route(re.compile("empty.html"), handler4)
    await page.goto(server.EMPTY_PAGE)
    assert intercepted == [4, 3, 2, 1]

    intercepted.clear()
    await page.unroute(re.compile("empty.html"), handler4)
    await page.goto(server.EMPTY_PAGE)
    assert intercepted == [3, 2, 1]

    intercepted.clear()
    await page.unroute("**/empty.html")
    await page.goto(server.EMPTY_PAGE)
    assert intercepted == [1]


async def test_RO_003_should_not_support_in_glob_pattern(
    page: Page, server: Server
) -> None:
    server.set_route("/index", end("index-no-hello"))
    server.set_route("/index123hello", end("index123hello"))
    server.set_route("/index?hello", end("index?hello"))
    server.set_route("/index1hello", end("index1hello"))

    await page.route(
        "**/index?hello",
        lambda route: route.fulfill(body="intercepted any character"),
    )
    await page.route(
        "**/index\\?hello",
        lambda route: route.fulfill(body="intercepted question mark"),
    )

    await page.goto(server.PREFIX + "/index?hello")
    assert "intercepted question mark" in await page.content()

    await page.goto(server.PREFIX + "/index")
    assert "index-no-hello" in await page.content()

    await page.goto(server.PREFIX + "/index1hello")
    assert "index1hello" in await page.content()

    await page.goto(server.PREFIX + "/index123hello")
    assert "index123hello" in await page.content()


async def test_RO_004_should_work_when_post_is_redirected_with_302(
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
async def test_RO_005_should_work_when_header_manipulation_headers_with_redirect(
    page: Page, server: Server
) -> None:
    server.set_redirect("/rrredirect", "/empty.html")

    async def handler(route: Route) -> None:
        headers = {**route.request.headers, "foo": "bar"}
        await route.continue_(headers=headers)

    await page.route("**/*", handler)
    await page.goto(server.PREFIX + "/rrredirect")


# @see https://github.com/GoogleChrome/puppeteer/issues/4743
async def test_RO_006_should_be_able_to_remove_headers(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)

    async def handler(route: Route) -> None:
        headers = {**route.request.headers}
        headers.pop("foo", None)
        await route.continue_(headers=headers)

    await page.route("**/*", handler)

    with server.expect_request("/title.html") as server_request_info:
        await page.evaluate(
            "url => fetch(url, { headers: { foo: 'bar' } })",
            server.PREFIX + "/title.html",
        )
    server_request = server_request_info.value
    assert server_request.getHeader("foo") is None


async def test_RO_007_should_contain_referer_header(page: Page, server: Server) -> None:
    requests: List[Request] = []

    async def handler(route: Route) -> None:
        requests.append(route.request)
        await route.continue_()

    await page.route("**/*", handler)
    await page.goto(server.PREFIX + "/one-style.html")
    assert "/one-style.css" in requests[1].url
    assert "/one-style.html" in requests[1].headers["referer"]


async def test_RO_008_should_properly_return_navigation_response_when_url_has_cookies(
    page: Page, server: Server
) -> None:
    # Setup cookie.
    await page.goto(server.EMPTY_PAGE)
    await page.context.add_cookies(
        [{"url": server.EMPTY_PAGE, "name": "foo", "value": "bar"}]
    )

    # Setup request interception.
    await page.route("**/*", lambda route: route.continue_())
    response = await page.reload()
    assert response
    assert response.status == 200


async def test_RO_009_should_not_override_cookie_header(
    page: Page, server: Server, browser_name: str
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.evaluate("() => document.cookie = 'original=value'")
    cookie_value_in_route: Optional[str] = None

    async def handler(route: Route) -> None:
        nonlocal cookie_value_in_route
        headers = await route.request.all_headers()
        cookie_value_in_route = headers.get("cookie")
        headers["cookie"] = "overridden=value"
        await route.continue_(headers=headers)

    await page.route("**", handler)
    with server.expect_request("/empty.html") as server_request_info:
        await page.goto(server.EMPTY_PAGE)
    server_request = server_request_info.value

    if browser_name != "webkit":
        assert cookie_value_in_route == "original=value"
    assert server_request.getHeader("cookie") == "original=value"


async def test_RO_010_should_show_custom_http_headers(
    page: Page, server: Server
) -> None:
    await page.set_extra_http_headers({"foo": "bar"})
    foo_headers: List[Optional[str]] = []

    async def handler(route: Route) -> None:
        foo_headers.append(route.request.headers.get("foo"))
        await route.continue_()

    await page.route("**/*", handler)
    response = await page.goto(server.EMPTY_PAGE)
    assert response
    assert response.ok is True
    assert foo_headers
    assert all(header == "bar" for header in foo_headers)


# @see https://github.com/GoogleChrome/puppeteer/issues/4337
async def test_RO_011_should_work_with_redirect_inside_sync_xhr(
    page: Page, server: Server, browser_name: str
) -> None:
    if browser_name == "webkit":
        pytest.skip("fixme: No Network.requestIntercepted for the request")
    await page.goto(server.EMPTY_PAGE)
    server.set_redirect("/logo.png", "/pptr.png")
    continue_results: List[Optional[Error]] = []

    async def handler(route: Route) -> None:
        try:
            await route.continue_()
            continue_results.append(None)
        except Error as error:
            continue_results.append(error)

    await page.route("**/*", handler)
    status = await page.evaluate(
        """async () => {
    const request = new XMLHttpRequest();
    request.open('GET', '/logo.png', false);  // `false` makes the request synchronous
    request.send(null);
    return request.status;
  }"""
    )
    assert status == 200
    await wait_for_list(page, continue_results)
    assert all(result is None for result in continue_results)


async def test_RO_012_should_pause_intercepted_xhr_until_continue(
    page: Page, server: Server, browser_name: str
) -> None:
    if browser_name == "webkit":
        pytest.skip("fixme: Redirected request is not paused in WebKit")

    await page.goto(server.EMPTY_PAGE)
    xhr_finished = False
    xhr_finished_while_paused: List[bool] = []

    async def handler(route: Route) -> None:
        # Check that intercepted request is actually paused.
        await page.wait_for_timeout(500)
        xhr_finished_while_paused.append(xhr_finished)
        await route.continue_()

    await page.route("**/global-var.html", handler)
    status = await page.evaluate(
        """async () => {
    const request = new XMLHttpRequest();
    request.open('GET', '/global-var.html', false);  // `false` makes the request synchronous
    request.send(null);
    return request.status;
  }"""
    )
    xhr_finished = True
    assert xhr_finished_while_paused == [False]
    assert status == 200


async def test_RO_013_should_pause_intercepted_fetch_request_until_continue(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    fetch_finished = False
    fetch_finished_while_paused: List[bool] = []

    async def handler(route: Route) -> None:
        # Check that intercepted request is actually paused.
        await page.wait_for_timeout(500)
        fetch_finished_while_paused.append(fetch_finished)
        await route.continue_()

    await page.route("**/global-var.html", handler)
    status = await page.evaluate(
        """async () => {
    const response = await fetch('/global-var.html');
    return response.status;
  }"""
    )
    fetch_finished = True
    assert fetch_finished_while_paused == [False]
    assert status == 200


async def test_RO_014_should_work_with_custom_referer_headers(
    page: Page, server: Server, browser_name: str, browser_major_version: int
) -> None:
    await page.set_extra_http_headers({"referer": server.EMPTY_PAGE})
    referers: List[Optional[str]] = []

    async def handler(route: Route) -> None:
        referers.append(route.request.headers.get("referer"))
        await route.continue_()

    await page.route("**/*", handler)
    response = await page.goto(server.EMPTY_PAGE)
    assert response
    assert response.ok is True
    assert referers
    for referer in referers:
        # See https://github.com/microsoft/playwright/issues/8999
        if browser_name == "chromium" and browser_major_version < 154:
            assert referer == server.EMPTY_PAGE + ", " + server.EMPTY_PAGE
        else:
            assert referer == server.EMPTY_PAGE


async def test_RO_015_should_be_abortable(page: Page, server: Server) -> None:
    await page.route(re.compile(r"\.css$"), lambda route: route.abort())
    failed = False

    def on_request_failed(request: Request) -> None:
        nonlocal failed
        if ".css" in request.url:
            failed = True

    page.on("requestfailed", on_request_failed)
    response = await page.goto(server.PREFIX + "/one-style.html")
    assert response
    assert response.ok is True
    assert response.request.failure is None
    assert failed is True


async def test_RO_016_should_be_abortable_with_custom_error_codes(
    page: Page, server: Server, browser_name: str, is_mac: bool, mac_version: int
) -> None:
    await page.route("**/*", lambda route: route.abort("internetdisconnected"))
    failed_requests: List[Request] = []
    page.on("requestfailed", lambda request: failed_requests.append(request))
    try:
        await page.goto(server.EMPTY_PAGE)
    except Error:
        pass
    assert failed_requests
    failed_request = failed_requests[-1]
    if browser_name == "webkit":
        assert failed_request.failure == (
            "Request intercepted"
            if is_mac and mac_version < 11
            else "Blocked by Web Inspector"
        )
    elif browser_name == "firefox":
        assert failed_request.failure == "NS_ERROR_OFFLINE"
    else:
        assert failed_request.failure == "net::ERR_INTERNET_DISCONNECTED"


async def test_RO_017_should_not_throw_if_request_was_cancelled_by_the_page(
    page: Page, server: Server
) -> None:
    routes: List[Route] = []
    await page.route("**/data.json", lambda route: routes.append(route))
    await page.goto(server.EMPTY_PAGE)
    await page.evaluate(
        """url => {
    globalThis.controller = new AbortController();
    fetch(url, { signal: globalThis.controller.signal }).catch(() => {});
  }""",
        server.PREFIX + "/data.json",
    )
    await wait_for_list(page, routes)
    route = routes[0]
    async with page.expect_event("requestfailed") as failure_info:
        await page.evaluate("() => globalThis.controller.abort()")
    cancelled_request = await failure_info.value
    assert cancelled_request.failure
    assert re.search(r"cancelled|aborted", cancelled_request.failure, re.IGNORECASE)
    await route.abort()  # Should not throw.


async def test_RO_018_should_send_referer(page: Page, server: Server) -> None:
    await page.set_extra_http_headers({"referer": "http://google.com/"})
    await page.route("**/*", lambda route: route.continue_())
    with server.expect_request("/grid.html") as request_info:
        await page.goto(server.PREFIX + "/grid.html")
    assert request_info.value.getHeader("referer") == "http://google.com/"


async def test_RO_019_should_fail_navigation_when_aborting_main_resource(
    page: Page, server: Server, browser_name: str, is_mac: bool, mac_version: int
) -> None:
    await page.route("**/*", lambda route: route.abort())
    with pytest.raises(Error) as exc_info:
        await page.goto(server.EMPTY_PAGE)
    error = exc_info.value
    assert error
    if browser_name == "webkit":
        assert (
            "Request intercepted"
            if is_mac and mac_version < 11
            else "Blocked by Web Inspector"
        ) in error.message
    elif browser_name == "firefox":
        assert "NS_ERROR_FAILURE" in error.message
    else:
        assert "net::ERR_FAILED" in error.message


async def test_RO_020_should_not_work_with_redirects(
    page: Page, server: Server
) -> None:
    intercepted: List[Request] = []

    async def handler(route: Route) -> None:
        intercepted.append(route.request)
        await route.continue_()

    await page.route("**/*", handler)
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
    assert intercepted[0].is_navigation_request() is True
    assert "/non-existing-page.html" in intercepted[0].url

    chain: List[Request] = []
    r: Optional[Request] = response.request
    while r:
        chain.append(r)
        assert r.is_navigation_request() is True
        r = r.redirected_from
    assert len(chain) == 5
    assert "/empty.html" in chain[0].url
    assert "/non-existing-page-4.html" in chain[1].url
    assert "/non-existing-page-3.html" in chain[2].url
    assert "/non-existing-page-2.html" in chain[3].url
    assert "/non-existing-page.html" in chain[4].url
    for i in range(len(chain)):
        assert chain[i].redirected_to == (chain[i - 1] if i else None)


async def test_RO_021_should_chain_fallback_w_dynamic_url(
    page: Page, server: Server
) -> None:
    intercepted: List[int] = []

    async def handler1(route: Route) -> None:
        intercepted.append(1)
        await route.fallback(url=server.EMPTY_PAGE)

    async def handler2(route: Route) -> None:
        intercepted.append(2)
        await route.fallback(url="http://localhost/bar")

    async def handler3(route: Route) -> None:
        intercepted.append(3)
        await route.fallback(url="http://localhost/foo")

    await page.route("**/bar", handler1)
    await page.route("**/foo", handler2)
    await page.route("**/empty.html", handler3)

    await page.goto(server.EMPTY_PAGE)
    assert intercepted == [3, 2, 1]


async def test_RO_022_should_work_with_redirects_for_subresources(
    page: Page, server: Server
) -> None:
    intercepted: List[Request] = []

    async def handler(route: Route) -> None:
        intercepted.append(route.request)
        await route.continue_()

    await page.route("**/*", handler)
    server.set_redirect("/one-style.css", "/two-style.css")
    server.set_redirect("/two-style.css", "/three-style.css")
    server.set_redirect("/three-style.css", "/four-style.css")
    server.set_route("/four-style.css", end("body {box-sizing: border-box; }"))

    response = await page.goto(server.PREFIX + "/one-style.html")
    assert response
    assert response.status == 200
    assert "one-style.html" in response.url

    assert len(intercepted) == 2
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


async def test_RO_023_should_work_with_equal_requests(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    response_count = 1

    def handle_zzz(request: TestServerRequest) -> None:
        nonlocal response_count
        request.write(str(response_count * 11).encode())
        response_count += 1
        request.finish()

    server.set_route("/zzz", handle_zzz)

    spinner = False

    # Cancel 2nd request.
    async def handler(route: Route) -> None:
        nonlocal spinner
        abort = spinner
        spinner = not spinner
        if abort:
            await route.abort()
        else:
            await route.continue_()

    await page.route("**/*", handler)
    results = []
    for _ in range(3):
        results.append(
            await page.evaluate(
                "() => fetch('/zzz').then(response => response.text()).catch(e => 'FAILED')"
            )
        )
    assert results == ["11", "FAILED", "22"]


async def test_RO_024_should_navigate_to_data_url_and_not_fire_data_url_requests(
    page: Page, server: Server
) -> None:
    requests: List[Request] = []

    async def handler(route: Route) -> None:
        requests.append(route.request)
        await route.continue_()

    await page.route("**/*", handler)
    data_url = "data:text/html,<div>yo</div>"
    response = await page.goto(data_url)
    assert response is None
    assert len(requests) == 0


async def test_RO_025_should_be_able_to_fetch_data_url_and_not_fire_data_url_requests(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    requests: List[Request] = []

    async def handler(route: Route) -> None:
        requests.append(route.request)
        await route.continue_()

    await page.route("**/*", handler)
    data_url = "data:text/html,<div>yo</div>"
    text = await page.evaluate("url => fetch(url).then(r => r.text())", data_url)
    assert text == "<div>yo</div>"
    assert len(requests) == 0


async def test_RO_026_should_navigate_to_url_with_hash_and_and_fire_requests_without_hash(
    page: Page, server: Server
) -> None:
    requests: List[Request] = []

    async def handler(route: Route) -> None:
        requests.append(route.request)
        await route.continue_()

    await page.route("**/*", handler)
    response = await page.goto(server.EMPTY_PAGE + "#hash")
    assert response
    assert response.status == 200
    assert response.url == server.EMPTY_PAGE
    assert len(requests) == 1
    assert requests[0].url == server.EMPTY_PAGE


async def test_RO_027_should_work_with_encoded_server(
    page: Page, server: Server
) -> None:
    # The requestWillBeSent will report encoded URL, whereas interception will
    # report URL as-is. @see crbug.com/759388
    await page.route("**/*", lambda route: route.continue_())
    response = await page.goto(server.PREFIX + "/some nonexisting page")
    assert response
    assert response.status == 404


async def test_RO_028_should_work_with_badly_encoded_server(
    page: Page, server: Server
) -> None:
    server.set_route("/malformed?rnd=%911", end(""))
    await page.route("**/*", lambda route: route.continue_())
    response = await page.goto(server.PREFIX + "/malformed?rnd=%911")
    assert response
    assert response.status == 200


async def test_RO_029_should_work_with_encoded_server_2(
    page: Page, server: Server
) -> None:
    # The requestWillBeSent will report URL as-is, whereas interception will
    # report encoded URL for stylesheet. @see crbug.com/759388
    await page.goto(server.EMPTY_PAGE)
    requests: List[Request] = []

    async def handler(route: Route) -> None:
        requests.append(route.request)
        await route.continue_()

    await page.route("**/*", handler)
    await page.set_content(
        f'<link rel="stylesheet" href="{server.PREFIX}/fonts?helvetica|arial"/>'
    )
    assert len(requests) == 1
    response = await requests[0].response()
    assert response
    assert response.status == 404


async def test_RO_030_should_not_throw_invalid_interception_id_if_the_request_was_cancelled(
    page: Page, server: Server
) -> None:
    await page.set_content("<iframe></iframe>")
    routes: List[Route] = []
    await page.route("**/*", lambda route: routes.append(route))
    # Wait for request interception.
    async with page.expect_event("request"):
        await page.eval_on_selector(
            "iframe", "(frame, url) => frame.src = url", server.EMPTY_PAGE
        )
    # Delete frame to cause request to be canceled.
    await page.eval_on_selector("iframe", "frame => frame.remove()")
    await wait_for_list(page, routes)
    await routes[0].continue_()


async def test_RO_031_should_intercept_main_resource_during_cross_process_navigation(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    intercepted = False

    async def handler(route: Route) -> None:
        nonlocal intercepted
        intercepted = True
        await route.continue_()

    await page.route(server.CROSS_PROCESS_PREFIX + "/empty.html", handler)
    response = await page.goto(server.CROSS_PROCESS_PREFIX + "/empty.html")
    assert response
    assert response.ok is True
    assert intercepted is True


async def test_RO_032_should_fulfill_with_redirect_status(
    page: Page, server: Server, browser_name: str
) -> None:
    if browser_name == "webkit":
        pytest.skip(
            "fixme: in WebKit the redirects are handled by the network stack and we intercept before"
        )

    await page.goto(server.PREFIX + "/title.html")
    server.set_route("/final", end("foo"))

    async def handler(route: Route, request: Request) -> None:
        if request.url != server.PREFIX + "/redirect_this":
            await route.continue_()
            return
        await route.fulfill(status=301, headers={"location": "/final"})

    await page.route("**/*", handler)

    text = await page.evaluate(
        """async url => {
    const data = await fetch(url);
    return data.text();
  }""",
        server.PREFIX + "/redirect_this",
    )
    assert text == "foo"


async def test_RO_033_should_not_fulfill_with_redirect_status(
    page: Page, server: Server, browser_name: str
) -> None:
    if browser_name != "webkit":
        pytest.skip(
            "we should support fulfill with redirect in webkit and delete this test"
        )

    await page.goto(server.PREFIX + "/empty.html")

    status = 0
    exceptions: List[Optional[Error]] = []

    async def handler(route: Route, request: Request) -> None:
        if request.url != server.PREFIX + "/redirect_this":
            await route.continue_()
            return
        try:
            await route.fulfill(status=status, headers={"location": "/empty.html"})
            exceptions.append(None)  # fulfill didn't throw
        except Error as e:
            exceptions.append(e)

    await page.route("**/*", handler)

    for status in range(300, 310):
        exceptions.clear()
        await page.evaluate(
            "url => location.href = url", server.PREFIX + "/redirect_this"
        )
        await wait_for_list(page, exceptions)
        exception = exceptions[0]
        assert exception
        assert "Cannot fulfill with redirect status" in exception.message


async def test_RO_034_should_support_cors_with_get(
    page: Page, server: Server, browser_name: str
) -> None:
    await page.goto(server.EMPTY_PAGE)

    async def handler(route: Route, request: Request) -> None:
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

    await page.route("**/cars*", handler)
    # Should succeed
    resp = await page.evaluate(
        """async () => {
    const response = await fetch('https://example.com/cars?allow', { mode: 'cors' });
    return response.json();
  }"""
    )
    assert resp == ["electric", "gas"]

    # Should be rejected
    with pytest.raises(Error) as exc_info:
        await page.evaluate(
            """async () => {
      const response = await fetch('https://example.com/cars?reject', { mode: 'cors' });
      return response.json();
    }"""
        )
    if browser_name == "chromium":
        assert "Failed" in exc_info.value.message
    if browser_name == "webkit":
        assert "TypeError" in exc_info.value.message
    if browser_name == "firefox":
        assert "NetworkError" in exc_info.value.message


async def test_RO_035_should_add_access_control_allow_origin_by_default_when_fulfill(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.route(
        "**/cars",
        lambda route: route.fulfill(
            content_type="application/json",
            status=200,
            body=json.dumps(["electric", "gas"]),
        ),
    )

    async with page.expect_response("https://example.com/cars") as response_info:
        result = await page.evaluate(
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
    response = await response_info.value
    assert result == ["electric", "gas"]
    assert await response.header_value("Access-Control-Allow-Origin") == server.PREFIX


async def test_RO_036_should_allow_null_origin_for_about_blank(
    page: Page, server: Server
) -> None:
    await page.route(
        "**/something",
        lambda route: route.fulfill(
            content_type="text/plain",
            status=200,
            body="done",
        ),
    )

    async with page.expect_response(
        server.CROSS_PROCESS_PREFIX + "/something"
    ) as response_info:
        text = await page.evaluate(
            """async url => {
      const data = await fetch(url, {
        method: 'GET',
        headers: { 'X-PINGOTHER': 'pingpong' }
      });
      return data.text();
    }""",
            server.CROSS_PROCESS_PREFIX + "/something",
        )
    response = await response_info.value
    assert text == "done"
    assert await response.header_value("Access-Control-Allow-Origin") == "null"


async def test_RO_037_should_respect_cors_overrides(
    page: Page, server: Server, browser_name: str
) -> None:
    await page.goto(server.EMPTY_PAGE)

    def handle_something(request: TestServerRequest) -> None:
        if request.method == b"OPTIONS":
            request.setResponseCode(204)
            request.setHeader("Access-Control-Allow-Origin", "*")
            request.setHeader(
                "Access-Control-Allow-Methods", "POST, GET, OPTIONS, DELETE"
            )
            request.setHeader("Access-Control-Allow-Headers", "*")
            request.setHeader("Cache-Control", "no-cache")
            request.finish()
            return
        request.setResponseCode(404)
        request.setHeader("Access-Control-Allow-Origin", "*")
        request.write(b"NOT FOUND")
        request.finish()

    server.set_route("/something", handle_something)
    # Fetch request should fail when CORS header doesn't include the origin.
    await page.route(
        "**/something",
        lambda route: route.fulfill(
            content_type="text/plain",
            status=200,
            headers={"Access-Control-Allow-Origin": "http://non-existent"},
            body="done",
        ),
    )

    with pytest.raises(Error) as exc_info:
        await page.evaluate(
            """async url => {
      const data = await fetch(url, {
        method: 'GET',
        headers: { 'X-PINGOTHER': 'pingpong' }
      });
      return data.text();
    }""",
            server.CROSS_PROCESS_PREFIX + "/something",
        )
    if browser_name == "chromium":
        assert "Failed to fetch" in exc_info.value.message
    elif browser_name == "webkit":
        assert "Load failed" in exc_info.value.message
    elif browser_name == "firefox":
        assert (
            "NetworkError when attempting to fetch resource." in exc_info.value.message
        )


def options_server_route(requests: List[str]) -> Callable[[TestServerRequest], None]:
    """The /something route of RO-038 and RO-039."""

    def handler(request: TestServerRequest) -> None:
        requests.append(request.method.decode() + ":" + request.uri.decode())
        if request.method == b"OPTIONS":
            request.setResponseCode(200)
            request.setHeader("Access-Control-Allow-Origin", "*")
            request.setHeader(
                "Access-Control-Allow-Methods", "POST, GET, OPTIONS, DELETE"
            )
            request.setHeader("Access-Control-Allow-Headers", "*")
            request.setHeader("Cache-Control", "no-cache")
            request.write(b"Hello")
            request.finish()
            return
        request.setResponseCode(200)
        request.setHeader("Access-Control-Allow-Origin", "*")
        request.write(b"World")
        request.finish()

    return handler


async def test_RO_038_should_not_auto_intercept_non_preflight_options_without_network_interception(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)

    requests: List[str] = []
    server.set_route("/something", options_server_route(requests))

    # Without interception.
    requests.clear()
    [text1, text2] = await page.evaluate(
        """async url => {
      const response1 = await fetch(url, { method: 'OPTIONS' });
      const text1 = await response1.text();
      const response2 = await fetch(url, { method: 'GET' });
      const text2 = await response2.text();
      return [text1, text2];
    }""",
        server.CROSS_PROCESS_PREFIX + "/something",
    )
    assert text1 == "Hello"
    assert text2 == "World"
    # Preflight for OPTIONS, then OPTIONS, then GET without preflight.
    assert requests == ["OPTIONS:/something", "OPTIONS:/something", "GET:/something"]


# Make sure this runs in a new context as preflight results could be cached.
async def test_RO_039_should_not_auto_intercept_non_preflight_options_with_network_interception(
    page: Page, server: Server, browser_name: str
) -> None:
    await page.goto(server.EMPTY_PAGE)

    requests: List[str] = []
    server.set_route("/something", options_server_route(requests))

    # With interception.
    await page.route("**/something", lambda route: route.continue_())

    requests.clear()
    [text1, text2] = await page.evaluate(
        """async url => {
      const response1 = await fetch(url, { method: 'OPTIONS' });
      const text1 = await response1.text();
      const response2 = await fetch(url, { method: 'GET' });
      const text2 = await response2.text();
      return [text1, text2];
    }""",
        server.CROSS_PROCESS_PREFIX + "/something",
    )
    assert text1 == "Hello"
    assert text2 == "World"
    # Preflight for OPTIONS is auto-fulfilled, then OPTIONS, then GET without preflight.
    if browser_name == "chromium":
        assert requests == ["OPTIONS:/something", "GET:/something"]
    else:
        assert requests == [
            "OPTIONS:/something",
            "OPTIONS:/something",
            "GET:/something",
        ]


async def test_RO_040_should_support_cors_with_post(page: Page, server: Server) -> None:
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


async def test_RO_041_should_support_cors_with_credentials(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.route(
        "**/cars",
        lambda route: route.fulfill(
            content_type="application/json",
            headers={
                "Access-Control-Allow-Origin": server.PREFIX,
                "Access-Control-Allow-Credentials": "true",
            },
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
      body: JSON.stringify({ 'number': 1 }),
      credentials: 'include'
    });
    return response.json();
  }"""
    )
    assert resp == ["electric", "gas"]


async def test_RO_042_should_not_abort_preflighted_cross_origin_redirect_when_a_route_is_registered(
    page: Page, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/43242
    def allow_cors(request: TestServerRequest) -> bool:
        request.setHeader(
            "Access-Control-Allow-Origin", request.getHeader("origin") or "*"
        )
        request.setHeader("Access-Control-Allow-Credentials", "true")
        request.setHeader("Access-Control-Allow-Headers", "x-app-version")
        if request.method != b"OPTIONS":
            return False
        request.setResponseCode(204)
        request.finish()
        return True

    def handle_download(request: TestServerRequest) -> None:
        if allow_cors(request):
            return
        request.setResponseCode(302)
        request.setHeader("location", f"{server.PREFIX}/file")
        request.finish()

    def handle_file(request: TestServerRequest) -> None:
        if allow_cors(request):
            return
        request.write(b"file contents")
        request.finish()

    server.set_route("/download", handle_download)
    server.set_route("/file", handle_file)

    await page.goto(server.EMPTY_PAGE)
    await page.route("**/never-matches", lambda route: route.continue_())
    result = await page.evaluate(
        """async url => {
    const response = await fetch(url, { credentials: 'include', headers: { 'X-App-Version': '1.2.3' } });
    return `${response.status} ${await response.text()}`;
  }""",
        server.CROSS_PROCESS_PREFIX + "/download",
    )
    assert result == "200 file contents"


async def test_RO_043_should_reject_cors_with_disallowed_credentials(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.route(
        "**/cars",
        lambda route: route.fulfill(
            content_type="application/json",
            headers={
                "Access-Control-Allow-Origin": server.PREFIX,
                # Should fail without this line below!
                # "Access-Control-Allow-Credentials": "true"
            },
            status=200,
            body=json.dumps(["electric", "gas"]),
        ),
    )
    with pytest.raises(Error) as exc_info:
        await page.evaluate(
            """async () => {
      const response = await fetch('https://example.com/cars', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        mode: 'cors',
        body: JSON.stringify({ 'number': 1 }),
        credentials: 'include'
      });
      return response.json();
    }"""
        )
    assert exc_info.value


async def test_RO_044_should_support_cors_for_different_methods(
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


async def test_RO_045_should_support_the_times_parameter_with_route_matching(
    page: Page, server: Server
) -> None:
    intercepted: List[int] = []

    async def handler(route: Route) -> None:
        intercepted.append(1)
        await route.continue_()

    await page.route("**/empty.html", handler, times=1)
    await page.goto(server.EMPTY_PAGE)
    await page.goto(server.EMPTY_PAGE)
    await page.goto(server.EMPTY_PAGE)
    assert len(intercepted) == 1


async def test_RO_046_should_work_if_handler_with_times_parameter_was_removed_from_another_handler(
    page: Page, server: Server
) -> None:
    intercepted: List[str] = []

    async def handler(route: Route) -> None:
        intercepted.append("first")
        await route.continue_()

    async def handler2(route: Route) -> None:
        intercepted.append("second")
        await page.unroute("**/*", handler)
        await route.fallback()

    await page.route("**/*", handler, times=1)
    await page.route("**/*", handler2)
    await page.goto(server.EMPTY_PAGE)
    assert intercepted == ["second"]
    intercepted.clear()
    await page.goto(server.EMPTY_PAGE)
    assert intercepted == ["second"]


async def test_RO_047_should_support_async_handler_w_times(
    page: Page, server: Server
) -> None:
    async def handler(route: Route) -> None:
        await page.wait_for_timeout(100)
        await route.fulfill(
            body="<html>intercepted</html>",
            content_type="text/html",
        )

    await page.route("**/empty.html", handler, times=1)
    await page.goto(server.EMPTY_PAGE)
    await expect(page.locator("body")).to_have_text("intercepted")
    await page.goto(server.EMPTY_PAGE)
    await expect(page.locator("body")).not_to_have_text("intercepted")


async def test_RO_048_route_abort_with_times_1_should_not_affect_second_sequential_fetch(
    page: Page, server: Server, browser_name: str, browser_major_version: int
) -> None:
    # https://github.com/microsoft/playwright/issues/41802
    if browser_name == "chromium" and browser_major_version < 155:
        pytest.skip(
            "Chromium drops a request that is intercepted while Fetch.disable is being processed; fix is not rolled yet"
        )

    def handle_data(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("Content-Type", "text/plain")
        request.write(b"ok")
        request.finish()

    server.set_route("/data", handle_data)

    await page.goto(server.EMPTY_PAGE)
    await page.route("**/data", lambda route: route.abort("timedout"), times=1)

    results = await page.evaluate(
        """async () => {
    async function fetchOrHung(url) {
      const timeout = new Promise(resolve => setTimeout(() => resolve('hung'), 3000));
      const request = fetch(url).then(r => String(r.status)).catch(() => 'aborted');
      return Promise.race([request, timeout]);
    }
    const first = await fetchOrHung('/data');
    const second = await fetchOrHung('/data');
    return [first, second];
  }"""
    )

    assert results == ["aborted", "200"]


async def test_RO_049_should_contain_raw_request_header(
    page: Page, server: Server
) -> None:
    headers: Dict[str, str] = {}

    async def handler(route: Route) -> None:
        nonlocal headers
        headers = await route.request.all_headers()
        await route.continue_()

    await page.route("**/*", handler)
    await page.goto(server.PREFIX + "/empty.html")
    assert headers.get("accept")


def sec_fetch(headers: Dict[str, str]) -> Dict[str, str]:
    return {
        name: value
        for name, value in headers.items()
        if name.lower().startswith("sec-fetch-")
    }


async def test_RO_050_should_contain_sec_fetch_headers_in_route(
    page: Page, server: Server, browser_name: str, request: pytest.FixtureRequest
) -> None:
    # https://github.com/microsoft/playwright/issues/42620
    if browser_name == "chromium":
        request.applymarker(
            pytest.mark.xfail(
                reason="upstream: Fetch.requestPaused fires before Chromium attaches Fetch Metadata headers",
                strict=True,
            )
        )

    modes = ["cors", "no-cors", "same-origin"]

    await page.goto(server.EMPTY_PAGE)

    routed: Dict[str, Dict[str, Dict[str, str]]] = {}

    async def handler(route: Route) -> None:
        path = urlparse(route.request.url).path
        routed[path] = {
            "headers": sec_fetch(route.request.headers),
            "allHeaders": sec_fetch(await route.request.all_headers()),
        }
        await route.continue_()

    await page.route("**/probe-*", handler)

    with (
        server.expect_request("/probe-cors") as cors_info,
        server.expect_request("/probe-no-cors") as no_cors_info,
        server.expect_request("/probe-same-origin") as same_origin_info,
    ):
        await page.evaluate(
            """async modes => {
      for (const mode of modes)
        await (await fetch(`/probe-${mode}`, { mode })).text();
    }""",
            modes,
        )
    server_requests = [cors_info.value, no_cors_info.value, same_origin_info.value]

    for i, mode in enumerate(modes):
        path = f"/probe-{mode}"
        on_server = sec_fetch(
            {
                name.decode().lower(): values[0].decode()
                for name, values in server_requests[i].requestHeaders.getAllRawHeaders()
            }
        )
        # The server does receive the browser-computed Fetch Metadata.
        assert on_server == {
            "sec-fetch-site": "same-origin",
            "sec-fetch-mode": mode,
            "sec-fetch-dest": "empty",
        }, f"{path} on server"
        # The route handler should see the same headers.
        assert routed[path]["headers"] == on_server, f"{path} route.request().headers()"
        assert (
            routed[path]["allHeaders"] == on_server
        ), f"{path} route.request().allHeaders()"


async def test_RO_051_should_contain_raw_response_header(
    page: Page, server: Server
) -> None:
    requests: List[Request] = []

    async def handler(route: Route) -> None:
        requests.append(route.request)
        await route.continue_()

    await page.route("**/*", handler)
    await page.goto(server.PREFIX + "/empty.html")
    response = await requests[-1].response()
    assert response
    headers = await response.all_headers()
    assert headers.get("content-type")


async def test_RO_052_should_contain_raw_response_header_after_fulfill(
    page: Page, server: Server
) -> None:
    requests: List[Request] = []

    async def handler(route: Route) -> None:
        requests.append(route.request)
        await route.fulfill(
            status=200,
            body="Hello",
            content_type="text/html",
        )

    await page.route("**/*", handler)
    await page.goto(server.PREFIX + "/empty.html")
    response = await requests[-1].response()
    assert response
    headers = await response.all_headers()
    assert headers.get("content-type")


@pytest.mark.parametrize("method", ["fulfill", "continue_", "fallback", "abort"])
async def test_RO_053_should_throw_if_called_twice(
    page: Page, server: Server, method: str
) -> None:
    routes: List[Route] = []
    await page.route("**/*", lambda route: routes.append(route))

    async def navigate() -> None:
        try:
            await page.goto(server.PREFIX + "/empty.html")
        except Error:
            pass

    async def call_twice() -> str:
        await wait_for_list(page, routes)
        route = routes[0]
        await getattr(route, method)()
        with pytest.raises(Error) as exc_info:
            await getattr(route, method)()
        return exc_info.value.message

    _, message = await asyncio.gather(navigate(), call_twice())
    assert "Route is already handled!" in message


async def test_RO_054_should_intercept_when_post_data_is_more_than_1_mb(
    page: Page, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/22753
    await page.goto(server.EMPTY_PAGE)
    post_data: List[Optional[str]] = []
    POST_BODY = "0" * (2 * 1024 * 1024)  # 2MB

    async def handler(route: Route) -> None:
        await route.abort()
        post_data.append(route.request.post_data)

    await page.route("**/404.html", handler)
    await page.evaluate(
        """POST_BODY => fetch('/404.html', {
    method: 'POST',
    body: POST_BODY,
  }).catch(e => {})""",
        POST_BODY,
    )
    await wait_for_list(page, post_data)
    assert post_data[0] == POST_BODY


async def test_RO_055_should_be_able_to_intercept_every_navigation_to_a_page_controlled_by_service_worker(
    page: Page, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/33561
    interceptions = 0
    url = server.PREFIX + "/serviceworkers/bug-33561/index.html"

    async def handler(route: Route) -> None:
        nonlocal interceptions
        interceptions += 1
        await route.continue_()

    await page.route(url, handler)

    await page.goto(url)
    await page.evaluate("() => window['activationPromise']")
    await page.goto(url)
    assert interceptions == 2
