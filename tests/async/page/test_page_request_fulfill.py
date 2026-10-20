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
from typing import Any, Awaitable, Callable, Dict, List, Optional

import pytest

from playwright.async_api import Error, Page, Playwright, Request, Route, expect
from tests.server import Server, TestServerRequest
from tests.utils import must


async def ignore_error(awaitable: Awaitable[Any]) -> None:
    """Port of `promise.catch(() => {})`."""
    try:
        await awaitable
    except Error:
        pass


async def test_RO_096_should_work(page: Page, server: Server) -> None:
    async def handler(route: Route) -> None:
        await route.fulfill(
            status=201,
            headers={"foo": "bar"},
            content_type="text/html",
            body="Yo, page!",
        )

    await page.route("**/*", handler)
    response = must(await page.goto(server.EMPTY_PAGE))
    assert response.status == 201
    assert response.headers["foo"] == "bar"
    assert await page.evaluate("() => document.body.textContent") == "Yo, page!"


async def test_RO_097_should_work_with_buffer_as_body(
    page: Page, server: Server
) -> None:
    async def handler(route: Route) -> None:
        await route.fulfill(status=200, content_type="text/plain", body=b"Yo, page!")

    await page.route("**/*", handler)
    response = must(await page.goto(server.EMPTY_PAGE))
    assert response.status == 200
    assert await page.evaluate("() => document.body.textContent") == "Yo, page!"


async def test_RO_098_should_work_with_status_code_422(
    page: Page, server: Server
) -> None:
    async def handler(route: Route) -> None:
        await route.fulfill(status=422, body="Yo, page!")

    await page.route("**/*", handler)
    response = must(await page.goto(server.EMPTY_PAGE))
    assert response.status == 422
    assert response.status_text == "Unprocessable Entity"
    assert await page.evaluate("() => document.body.textContent") == "Yo, page!"


async def test_RO_099_should_fulfill_with_unuassigned_status_codes(
    page: Page, server: Server
) -> None:
    fulfill_future: "asyncio.Future[Optional[Error]]" = asyncio.Future()

    async def handler(route: Route) -> None:
        try:
            await route.fulfill(status=430, body="Yo, page!")
            fulfill_future.set_result(None)
        except Error as e:
            fulfill_future.set_result(e)

    await page.route("**/data.json", handler)
    await page.goto(server.EMPTY_PAGE)
    response = await page.evaluate(
        """async url => {
            const { status, statusText } = await fetch(url);
            return { status, statusText };
        }""",
        server.PREFIX + "/data.json",
    )
    error = await fulfill_future
    assert error is None
    assert response["status"] == 430
    assert response["statusText"] == "Unknown"


async def test_RO_100_should_not_throw_if_request_was_cancelled_by_the_page(
    page: Page, server: Server
) -> None:
    intercept_future: "asyncio.Future[Route]" = asyncio.Future()
    await page.route("**/data.json", lambda route: intercept_future.set_result(route))
    await page.goto(server.EMPTY_PAGE)
    evaluate_task = asyncio.create_task(
        ignore_error(
            page.evaluate(
                """url => {
                    globalThis.controller = new AbortController();
                    return fetch(url, { signal: globalThis.controller.signal });
                }""",
                server.PREFIX + "/data.json",
            )
        )
    )
    route = await intercept_future
    async with page.expect_event("requestfailed") as failure_info:
        await page.evaluate("() => globalThis.controller.abort()")
    cancelled_request: Request = await failure_info.value
    assert cancelled_request.failure
    assert re.search(r"cancelled|aborted", cancelled_request.failure, re.I)
    await route.fulfill(status=200)  # Should not throw.
    await evaluate_task


async def test_RO_101_should_allow_mocking_binary_responses(
    page: Page,
    server: Server,
    browser_name: str,
    headless: bool,
    assetdir: Path,
    assert_to_be_golden: Callable[[bytes, str], None],
) -> None:
    if browser_name == "firefox" and not headless:
        pytest.skip("Firefox headed produces a different image.")

    async def handler(route: Route) -> None:
        image_buffer = (assetdir / "pptr.png").read_bytes()
        await route.fulfill(content_type="image/png", body=image_buffer)

    await page.route("**/*", handler)
    await page.evaluate(
        """PREFIX => {
            const img = document.createElement('img');
            img.src = PREFIX + '/does-not-exist.png';
            document.body.appendChild(img);
            return new Promise(fulfill => img.onload = fulfill);
        }""",
        server.PREFIX,
    )
    img = must(await page.query_selector("img"))
    assert_to_be_golden(await img.screenshot(), "mock-binary-response.png")


async def test_RO_102_should_allow_mocking_svg_with_charset(
    page: Page,
    server: Server,
    browser_name: str,
    headless: bool,
    assert_to_be_golden: Callable[[bytes, str], None],
) -> None:
    if browser_name == "firefox" and not headless:
        pytest.skip("Firefox headed produces a different image.")

    async def handler(route: Route) -> None:
        await route.fulfill(
            content_type="image/svg+xml ; charset=utf-8",
            body='<svg width="50" height="50" version="1.1" xmlns="http://www.w3.org/2000/svg"><rect x="10" y="10" width="30" height="30" stroke="black" fill="transparent" stroke-width="5"/></svg>',
        )

    await page.route("**/*", handler)
    await page.evaluate(
        """PREFIX => {
            const img = document.createElement('img');
            img.src = PREFIX + '/does-not-exist.svg';
            document.body.appendChild(img);
            return new Promise((f, r) => { img.onload = f; img.onerror = r; });
        }""",
        server.PREFIX,
    )
    img = must(await page.query_selector("img"))
    assert_to_be_golden(await img.screenshot(), "mock-svg.png")


async def test_RO_103_should_work_with_file_path(
    page: Page,
    server: Server,
    assetdir: Path,
    assert_to_be_golden: Callable[[bytes, str], None],
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
    img = must(await page.query_selector("img"))
    assert_to_be_golden(await img.screenshot(), "mock-binary-response.png")


async def test_RO_104_should_stringify_intercepted_request_response_headers(
    page: Page, server: Server
) -> None:
    async def handler(route: Route) -> None:
        await route.fulfill(status=200, headers={"foo": "true"}, body="Yo, page!")

    await page.route("**/*", handler)
    response = must(await page.goto(server.EMPTY_PAGE))
    assert response.status == 200
    headers = response.headers
    assert headers["foo"] == "true"
    assert await page.evaluate("() => document.body.textContent") == "Yo, page!"


async def test_RO_105_should_not_modify_the_headers_sent_to_the_server(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/empty.html")
    intercepted_requests: List[TestServerRequest] = []

    # this is just to enable request interception, which disables caching in chromium
    await page.route(server.PREFIX + "/unused", lambda route: None)

    def handle(request: TestServerRequest) -> None:
        intercepted_requests.append(request)
        request.setResponseCode(200)
        request.setHeader("Access-Control-Allow-Origin", "*")
        request.write(b"done")
        request.finish()

    server.set_route("/something", handle)

    text = await page.evaluate(
        """async url => {
            const data = await fetch(url);
            return data.text();
        }""",
        server.CROSS_PROCESS_PREFIX + "/something",
    )
    assert text == "done"

    async def handler(route: Route, request: Request) -> None:
        await route.continue_(headers={**request.headers})

    await page.route(server.CROSS_PROCESS_PREFIX + "/something", handler)

    text_after_route = await page.evaluate(
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


async def test_RO_106_should_include_the_origin_header(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/empty.html")
    intercepted_requests: List[Request] = []

    async def handler(route: Route, request: Request) -> None:
        intercepted_requests.append(request)
        await route.fulfill(
            headers={"Access-Control-Allow-Origin": "*"},
            content_type="text/plain",
            body="done",
        )

    await page.route(server.CROSS_PROCESS_PREFIX + "/something", handler)

    text = await page.evaluate(
        """async url => {
            const data = await fetch(url);
            return data.text();
        }""",
        server.CROSS_PROCESS_PREFIX + "/something",
    )
    assert text == "done"
    assert intercepted_requests[-1].headers["origin"] == server.PREFIX


async def test_RO_107_should_fulfill_with_global_fetch_result(
    playwright: Playwright, page: Page, server: Server
) -> None:
    async def handler(route: Route) -> None:
        request = await playwright.request.new_context()
        response = await request.get(server.PREFIX + "/simple.json")
        await route.fulfill(response=response)

    await page.route("**/*", handler)
    response = must(await page.goto(server.EMPTY_PAGE))
    assert response.status == 200
    assert await response.json() == {"foo": "bar"}


async def test_RO_108_should_fulfill_with_fetch_result(
    page: Page, server: Server
) -> None:
    async def handler(route: Route) -> None:
        response = await page.request.get(server.PREFIX + "/simple.json")
        await route.fulfill(response=response)

    await page.route("**/*", handler)
    response = must(await page.goto(server.EMPTY_PAGE))
    assert response.status == 200
    assert await response.json() == {"foo": "bar"}


async def test_RO_109_should_fulfill_with_fetch_result_and_overrides(
    page: Page, server: Server
) -> None:
    async def handler(route: Route) -> None:
        response = await page.request.get(server.PREFIX + "/simple.json")
        await route.fulfill(
            response=response,
            status=201,
            headers={
                "Content-Type": "application/json",  # Case matters for the tested behavior
                "foo": "bar",
            },
        )

    await page.route("**/*", handler)
    response = must(await page.goto(server.EMPTY_PAGE))
    assert response.status == 201
    assert (await response.all_headers())["foo"] == "bar"
    assert await response.json() == {"foo": "bar"}


async def test_RO_110_should_fetch_original_request_and_fulfill(
    page: Page, server: Server
) -> None:
    async def handler(route: Route) -> None:
        response = await page.request.fetch(route.request)
        await route.fulfill(response=response)

    await page.route("**/*", handler)
    response = must(await page.goto(server.PREFIX + "/title.html"))
    assert response.status == 200
    assert await page.title() == "Woof-Woof"


async def test_RO_111_should_fulfill_with_multiple_set_cookie(
    page: Page, server: Server
) -> None:
    cookies = ["a=b", "c=d"]

    async def handler(route: Route) -> None:
        await route.fulfill(
            status=200,
            headers={
                "X-Header-1": "v1",
                "Set-Cookie": "\n".join(cookies),
                "X-Header-2": "v2",
            },
            body="",
        )

    await page.route("**/multiple-set-cookie.html", handler)
    response = must(await page.goto(server.PREFIX + "/multiple-set-cookie.html"))
    assert (
        sorted(
            s.strip() for s in (await page.evaluate("() => document.cookie")).split(";")
        )
        == cookies
    )
    assert await response.header_value("X-Header-1") == "v1"
    assert await response.header_value("X-Header-2") == "v2"


async def test_RO_112_should_fulfill_with_fetch_response_that_has_multiple_set_cookie(
    playwright: Playwright, page: Page, server: Server
) -> None:
    def handle(request: TestServerRequest) -> None:
        request.responseHeaders.setRawHeaders("Set-Cookie", ["a=b", "c=d"])
        request.setHeader("Content-Type", "text/html")
        request.finish()

    server.set_route("/empty.html", handle)

    async def handler(route: Route) -> None:
        request = await playwright.request.new_context()
        response = await request.fetch(route.request)
        await route.fulfill(response=response)

    await page.route("**/empty.html", handler)
    await page.goto(server.EMPTY_PAGE)
    cookie = await page.evaluate("() => document.cookie")
    assert sorted(s.strip() for s in cookie.split(";")) == ["a=b", "c=d"]


async def test_RO_113_header_value_should_return_set_cookie_from_intercepted_response(
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

    async def handler(route: Route) -> None:
        await route.fulfill(status=200, headers={"Set-Cookie": "a=b"}, body="")

    await page.route("**/empty.html", handler)
    response = must(await page.goto(server.EMPTY_PAGE))
    assert await response.header_value("Set-Cookie") == "a=b"


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


async def test_RO_114_should_fulfill_with_har_response(
    page: Page, assetdir: Path
) -> None:
    har_path = assetdir / "har-fulfill.har"
    har = json.loads(har_path.read_text(encoding="utf-8"))

    async def handler(route: Route) -> None:
        response = find_response(har, route.request.url)
        headers = {}
        for header in response["headers"]:
            headers[header["name"]] = header["value"]
        text = response["content"].get("text") or ""
        if response["content"].get("encoding") == "base64":
            body = base64.b64decode(text)
        else:
            body = text.encode("utf-8")
        await route.fulfill(status=response["status"], headers=headers, body=body)

    await page.route("**/*", handler)
    await page.goto("http://no.playwright/")
    # HAR contains a redirect for the script.
    assert await page.evaluate("window.value") == "foo"
    # HAR contains a POST for the css file but we match ignoring the method, so the file should be served.
    await expect(page.locator("body")).to_have_css(
        "background-color", "rgb(0, 255, 255)"
    )


async def test_RO_115_should_fulfill_preload_link_requests(
    page: Page, server: Server
) -> None:
    intercepted = False

    async def handler(route: Route) -> None:
        nonlocal intercepted
        intercepted = True
        await route.fulfill(
            status=200,
            headers={
                "content-type": "text/css; charset=utf-8",
                "cache-control": "no-cache, no-store",
                "custom": "value",
            },
            body="body { background-color: green; }",
        )

    await page.route("**/one-style.css", handler)
    async with page.expect_response("**/one-style.css") as response_info:
        await page.goto(server.PREFIX + "/preload.html")
    response = await response_info.value
    assert await response.header_value("custom") == "value"
    await page.wait_for_function("() => window.preloadedStyles")
    assert intercepted is True
    color = await page.evaluate(
        "() => window.getComputedStyle(document.body).backgroundColor"
    )
    assert color == "rgb(0, 128, 0)"


async def test_RO_116_should_fulfill_json(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)

    async def handler(route: Route) -> None:
        await route.fulfill(status=201, headers={"foo": "bar"}, json={"bar": "baz"})

    await page.route("**/data.json", handler)
    async with page.expect_response("**/*") as response_info:
        body = await page.evaluate("() => fetch('./data.json').then(r => r.text())")
    response = await response_info.value
    assert response.status == 201
    assert response.headers["content-type"] == "application/json"
    assert body == '{"bar":"baz"}'


async def test_RO_117_should_fulfill_with_gzip_and_readback(
    page: Page, server: Server
) -> None:
    server.enable_gzip("/one-style.html")

    async def handler(route: Route) -> None:
        response = await route.fetch()
        assert response.headers["content-encoding"] == "gzip"
        await route.fulfill(response=response)

    await page.route("**/one-style.html", handler)

    response = must(await page.goto(server.PREFIX + "/one-style.html"))
    await expect(page.locator("div")).to_have_text("hello, world!")
    await expect(page.locator("body")).to_have_css(
        "background-color", "rgb(255, 192, 203)"
    )
    assert "<div>hello, world!</div>" in await response.text()


async def test_RO_118_should_not_go_to_the_network_for_fulfilled_requests_body(
    page: Page, server: Server
) -> None:
    async def handler(route: Route) -> None:
        await route.fulfill(
            status=404, content_type="text/plain", body="Not Found! (mocked)"
        )

    await page.route("**/one-style.css", handler)

    server_hit = False

    def handle(request: TestServerRequest) -> None:
        nonlocal server_hit
        server_hit = True
        request.setHeader("Content-Type", "text/css")
        request.write(b"body { background-color: green; }")
        request.finish()

    server.set_route("/one-style.css", handle)

    async with page.expect_response("**/one-style.css") as response_info:
        await page.goto(server.PREFIX + "/one-style.html")
    response = await response_info.value
    body = await response.body()
    assert body.decode() == "Not Found! (mocked)"
    assert server_hit is False


async def test_RO_119_should_return_body_for_fulfilled_responses(
    page: Page, server: Server
) -> None:
    for status in [100, 200, 404, 500]:
        body_override = f"Custom body {status}"

        async def handler(route: Route) -> None:
            await route.fulfill(
                status=status, content_type="text/plain", body=body_override
            )

        await page.route("**/one-style.css", handler)

        async with page.expect_response("**/one-style.css") as response_info:
            await page.goto(server.PREFIX + "/one-style.html")
        response = await response_info.value
        body = await response.body()
        assert body.decode() == body_override
        await page.unroute_all()
