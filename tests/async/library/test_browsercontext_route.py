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

"""Port of tests/library/browsercontext-route.spec.ts."""

import asyncio
import re
from typing import Awaitable, Callable, List

import pytest

from playwright.async_api import (
    Browser,
    BrowserContext,
    Error,
    Page,
    Request,
    Route,
    expect,
)
from tests.server import Server, TestServerRequest
from tests.utils import must


async def test_RO_165_should_intercept(browser: Browser, server: Server) -> None:
    context = await browser.new_context()
    intercepted = False

    async def handler(route: Route) -> None:
        nonlocal intercepted
        intercepted = True
        request = route.request
        assert "empty.html" in request.url
        assert request.headers["user-agent"]
        assert request.method == "GET"
        assert request.post_data is None
        assert request.is_navigation_request() is True
        assert request.resource_type == "document"
        assert request.frame == page.main_frame
        assert request.frame.url == "about:blank"
        await route.continue_()

    await context.route("**/empty.html", handler)
    page = await context.new_page()
    response = must(await page.goto(server.EMPTY_PAGE))
    assert response.ok is True
    assert intercepted is True
    await context.close()


async def test_RO_166_should_unroute(browser: Browser, server: Server) -> None:
    context = await browser.new_context()
    page = await context.new_page()

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

    await context.route("**/*", handler1)
    await context.route("**/empty.html", handler2)
    await context.route("**/empty.html", handler3)
    await context.route(re.compile("empty.html"), handler4)
    await page.goto(server.EMPTY_PAGE)
    assert intercepted == [4, 3, 2, 1]

    intercepted = []
    await context.unroute(re.compile("empty.html"), handler4)
    await page.goto(server.EMPTY_PAGE)
    assert intercepted == [3, 2, 1]

    intercepted = []
    await context.unroute("**/empty.html")
    await page.goto(server.EMPTY_PAGE)
    assert intercepted == [1]

    await context.close()


async def test_RO_167_should_yield_to_page_route(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()

    async def context_handler(route: Route) -> None:
        await route.fulfill(status=200, body="context")

    await context.route("**/empty.html", context_handler)
    page = await context.new_page()

    async def page_handler(route: Route) -> None:
        await route.fulfill(status=200, body="page")

    await page.route("**/empty.html", page_handler)
    response = must(await page.goto(server.EMPTY_PAGE))
    assert response.ok is True
    assert await response.text() == "page"
    await context.close()


async def test_RO_168_should_fall_back_to_context_route(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()

    async def context_handler(route: Route) -> None:
        await route.fulfill(status=200, body="context")

    await context.route("**/empty.html", context_handler)
    page = await context.new_page()

    async def page_handler(route: Route) -> None:
        await route.fulfill(status=200, body="page")

    await page.route("**/non-empty.html", page_handler)
    response = must(await page.goto(server.EMPTY_PAGE))
    assert response.ok is True
    assert await response.text() == "context"
    await context.close()


async def test_RO_169_should_support_set_cookie_header(
    context_factory: "Callable[..., Awaitable[BrowserContext]]",
    default_same_site_cookie_value: str,
) -> None:
    context = await context_factory()
    page = await context.new_page()

    async def handler(route: Route, request: Request) -> None:
        await route.fulfill(
            headers={"Set-Cookie": "name=value; domain=.example.com; Path=/"},
            content_type="text/html",
            body="done",
        )

    await page.route("https://example.com/", handler)
    await page.goto("https://example.com")
    assert await context.cookies() == [
        {
            "sameSite": default_same_site_cookie_value,
            "name": "name",
            "value": "value",
            "domain": ".example.com",
            "path": "/",
            "expires": -1,
            "httpOnly": False,
            "secure": False,
        }
    ]


async def test_RO_170_should_ignore_secure_set_cookie_header_for_insecure_requests(
    context_factory: "Callable[..., Awaitable[BrowserContext]]",
    server: Server,
    browser_name: str,
    is_mac: bool,
) -> None:
    if browser_name == "webkit" and not is_mac:
        pytest.skip("fixme: upstream fixme for WebKit on non-Mac")

    context = await context_factory()
    page = await context.new_page()

    async def handler(route: Route, request: Request) -> None:
        await route.fulfill(
            headers={"Set-Cookie": "name=value; domain=.example.com; Path=/; Secure"},
            content_type="text/html",
            body="done",
        )

    await page.route("http://example.com/", handler)
    await page.goto("http://example.com")
    assert await context.cookies() == []


async def test_RO_171_should_use_set_cookie_header_in_future_requests(
    context_factory: "Callable[..., Awaitable[BrowserContext]]",
    server: Server,
    default_same_site_cookie_value: str,
) -> None:
    context = await context_factory()
    page = await context.new_page()

    async def handler(route: Route, request: Request) -> None:
        await route.fulfill(
            headers={"Set-Cookie": "name=value"},
            content_type="text/html",
            body="done",
        )

    await page.route(server.EMPTY_PAGE, handler)
    await page.goto(server.EMPTY_PAGE)
    assert await context.cookies() == [
        {
            "sameSite": default_same_site_cookie_value,
            "name": "name",
            "value": "value",
            "domain": server.HOSTNAME,
            "path": "/",
            "expires": -1,
            "httpOnly": False,
            "secure": False,
        }
    ]

    cookie = ""

    def handle(request: TestServerRequest) -> None:
        nonlocal cookie
        cookie = must(request.getHeader("cookie"))
        request.finish()

    server.set_route("/foo.html", handle)
    await page.goto(server.PREFIX + "/foo.html")
    assert cookie == "name=value"


async def test_RO_172_should_work_with_ignore_https_errors(
    browser: Browser, https_server: Server
) -> None:
    context = await browser.new_context(ignore_https_errors=True)
    page = await context.new_page()

    await page.route("**/*", lambda route: route.continue_())
    response = must(await page.goto(https_server.EMPTY_PAGE))
    assert response.status == 200
    await context.close()


async def test_RO_173_should_support_the_times_parameter_with_route_matching(
    context: BrowserContext, page: Page, server: Server
) -> None:
    intercepted: List[int] = []

    async def handler(route: Route) -> None:
        intercepted.append(1)
        await route.continue_()

    await context.route("**/empty.html", handler, times=1)
    await page.goto(server.EMPTY_PAGE)
    await page.goto(server.EMPTY_PAGE)
    await page.goto(server.EMPTY_PAGE)
    assert len(intercepted) == 1


async def test_RO_174_should_work_if_handler_with_times_parameter_was_removed_from_another_handler(
    context: BrowserContext, page: Page, server: Server
) -> None:
    intercepted: List[str] = []

    async def handler(route: Route) -> None:
        intercepted.append("first")
        await route.continue_()

    await context.route("**/*", handler, times=1)

    async def handler2(route: Route) -> None:
        intercepted.append("second")
        await context.unroute("**/*", handler)
        await route.fallback()

    await context.route("**/*", handler2)
    await page.goto(server.EMPTY_PAGE)
    assert intercepted == ["second"]
    intercepted.clear()
    await page.goto(server.EMPTY_PAGE)
    assert intercepted == ["second"]


async def test_RO_175_should_support_async_handler_w_times(
    context: BrowserContext, page: Page, server: Server
) -> None:
    async def handler(route: Route) -> None:
        await asyncio.sleep(0.1)
        await route.fulfill(
            body="<html>intercepted</html>",
            content_type="text/html",
        )

    await context.route("**/empty.html", handler, times=1)
    await page.goto(server.EMPTY_PAGE)
    await expect(page.locator("body")).to_have_text("intercepted")
    await page.goto(server.EMPTY_PAGE)
    await expect(page.locator("body")).not_to_have_text("intercepted")


async def test_RO_176_should_overwrite_post_body_with_empty_string(
    context: BrowserContext, server: Server, page: Page
) -> None:
    async def handler(route: Route) -> None:
        await route.continue_(post_data="")

    await context.route("**/empty.html", handler)

    req_task = asyncio.create_task(server.wait_for_request("/empty.html"))
    await page.set_content(
        f"""
      <script>
        (async () => {{
            await fetch('{server.EMPTY_PAGE}', {{
              method: 'POST',
              body: 'original',
            }});
        }})()
      </script>
    """
    )
    req = await req_task

    body = (req.post_body or b"").decode()
    assert body == ""


async def test_RO_177_should_chain_fallback(
    context: BrowserContext, page: Page, server: Server
) -> None:
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

    await context.route("**/empty.html", handler1)
    await context.route("**/empty.html", handler2)
    await context.route("**/empty.html", handler3)
    await page.goto(server.EMPTY_PAGE)
    assert intercepted == [3, 2, 1]


async def test_RO_178_should_chain_fallback_w_dynamic_url(
    context: BrowserContext, page: Page, server: Server
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

    await context.route("**/bar", handler1)
    await context.route("**/foo", handler2)
    await context.route("**/empty.html", handler3)

    await page.goto(server.EMPTY_PAGE)
    assert intercepted == [3, 2, 1]


async def test_RO_179_should_not_chain_fulfill(
    context: BrowserContext, page: Page, server: Server
) -> None:
    failed = False

    def handler1(route: Route) -> None:
        nonlocal failed
        failed = True

    async def handler2(route: Route) -> None:
        await route.fulfill(status=200, body="fulfilled")

    async def handler3(route: Route) -> None:
        await route.fallback()

    await context.route("**/empty.html", handler1)
    await context.route("**/empty.html", handler2)
    await context.route("**/empty.html", handler3)
    response = must(await page.goto(server.EMPTY_PAGE))
    body = await response.body()
    assert body.decode() == "fulfilled"
    assert not failed


async def test_RO_180_should_not_chain_abort(
    context: BrowserContext, page: Page, server: Server
) -> None:
    failed = False

    def handler1(route: Route) -> None:
        nonlocal failed
        failed = True

    async def handler2(route: Route) -> None:
        await route.abort()

    async def handler3(route: Route) -> None:
        await route.fallback()

    await context.route("**/empty.html", handler1)
    await context.route("**/empty.html", handler2)
    await context.route("**/empty.html", handler3)
    with pytest.raises(Error) as exc_info:
        await page.goto(server.EMPTY_PAGE)
    assert exc_info.value
    assert not failed


async def test_RO_181_should_chain_fallback_into_page(
    context: BrowserContext, page: Page, server: Server
) -> None:
    intercepted: List[int] = []

    def make_handler(value: int) -> Callable[[Route], Awaitable[None]]:
        async def handler(route: Route) -> None:
            intercepted.append(value)
            await route.fallback()

        return handler

    await context.route("**/empty.html", make_handler(1))
    await context.route("**/empty.html", make_handler(2))
    await context.route("**/empty.html", make_handler(3))
    await page.route("**/empty.html", make_handler(4))
    await page.route("**/empty.html", make_handler(5))
    await page.route("**/empty.html", make_handler(6))
    await page.goto(server.EMPTY_PAGE)
    assert intercepted == [6, 5, 4, 3, 2, 1]


async def test_RO_182_should_fall_back_async(
    page: Page, context: BrowserContext, server: Server
) -> None:
    intercepted: List[int] = []

    async def handler1(route: Route) -> None:
        intercepted.append(1)
        await asyncio.sleep(0.1)
        await route.fallback()

    async def handler2(route: Route) -> None:
        intercepted.append(2)
        await asyncio.sleep(0.1)
        await route.fallback()

    async def handler3(route: Route) -> None:
        intercepted.append(3)
        await asyncio.sleep(0.1)
        await route.fallback()

    await context.route("**/empty.html", handler1)
    await context.route("**/empty.html", handler2)
    await context.route("**/empty.html", handler3)
    await page.goto(server.EMPTY_PAGE)
    assert intercepted == [3, 2, 1]


async def test_RO_183_should_bypass_disk_cache_when_context_interception_is_enabled(
    page: Page, server: Server
) -> None:
    await page.context.route("**/api*", lambda route: route.continue_())
    await page.goto(server.PREFIX + "/frames/one-frame.html")
    requests: List[TestServerRequest] = []

    def handle(request: TestServerRequest) -> None:
        requests.append(request)
        request.setResponseCode(200)
        request.setHeader("content-type", "text/plain")
        request.setHeader("cache-control", "public, max-age=31536000")
        request.write(b"Hello")
        request.finish()

    server.set_route("/api", handle)
    for i in range(3):
        async with page.expect_response("**/api") as response_info:
            await page.evaluate(
                """async () => {
                    const response = await fetch('/api');
                    return response.status;
                }"""
            )
        response = await response_info.value
        assert response.status == 200
        assert len(requests) == i + 1


async def test_RO_184_should_fulfill_popup_main_request_using_alias(
    page: Page, server: Server
) -> None:
    async def handler(route: Route) -> None:
        response = await route.fetch()
        await route.fulfill(response=response, body="hello")

    await page.context.route("**/*", handler)
    await page.set_content(f'<a target=_blank href="{server.EMPTY_PAGE}">click me</a>')
    async with page.expect_popup() as popup_info:
        await page.get_by_text("click me").click()
    popup = await popup_info.value
    await expect(popup.locator("body")).to_have_text("hello")
