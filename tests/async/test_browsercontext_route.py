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


async def test_route_should_intercept(context: BrowserContext, server: Server) -> None:
    intercepted = []

    def handle(route: Route, request: Request) -> None:
        intercepted.append(True)
        assert "empty.html" in request.url
        assert request.headers["user-agent"]
        assert request.method == "GET"
        assert request.post_data is None
        assert request.is_navigation_request()
        assert request.resource_type == "document"
        assert request.frame == page.main_frame
        assert request.frame.url == "about:blank"
        asyncio.create_task(route.continue_())

    await context.route("**/empty.html", lambda route, request: handle(route, request))
    page = await context.new_page()
    response = await page.goto(server.EMPTY_PAGE)
    assert response
    assert response.ok
    assert intercepted == [True]
    await context.close()


async def test_route_should_unroute(context: BrowserContext, server: Server) -> None:
    page = await context.new_page()

    intercepted: List[int] = []

    def handler(route: Route, request: Request, ordinal: int) -> None:
        intercepted.append(ordinal)
        asyncio.create_task(route.continue_())

    await context.route("**/*", lambda route, request: handler(route, request, 1))
    await context.route(
        "**/empty.html", lambda route, request: handler(route, request, 2)
    )
    await context.route(
        "**/empty.html", lambda route, request: handler(route, request, 3)
    )

    def handler4(route: Route, request: Request) -> None:
        handler(route, request, 4)

    await context.route(re.compile("empty.html"), handler4)

    await page.goto(server.EMPTY_PAGE)
    assert intercepted == [4]

    intercepted = []
    await context.unroute(re.compile("empty.html"), handler4)
    await page.goto(server.EMPTY_PAGE)
    assert intercepted == [3]

    intercepted = []
    await context.unroute("**/empty.html")
    await page.goto(server.EMPTY_PAGE)
    assert intercepted == [1]


async def test_route_should_yield_to_page_route(
    context: BrowserContext, server: Server
) -> None:
    await context.route(
        "**/empty.html",
        lambda route, request: asyncio.create_task(
            route.fulfill(status=200, body="context")
        ),
    )

    page = await context.new_page()
    await page.route(
        "**/empty.html",
        lambda route, request: asyncio.create_task(
            route.fulfill(status=200, body="page")
        ),
    )

    response = await page.goto(server.EMPTY_PAGE)
    assert response
    assert response.ok
    assert await response.text() == "page"


async def test_route_should_fall_back_to_context_route(
    context: BrowserContext, server: Server
) -> None:
    await context.route(
        "**/empty.html",
        lambda route, request: asyncio.create_task(
            route.fulfill(status=200, body="context")
        ),
    )

    page = await context.new_page()
    await page.route(
        "**/non-empty.html",
        lambda route, request: asyncio.create_task(
            route.fulfill(status=200, body="page")
        ),
    )

    response = await page.goto(server.EMPTY_PAGE)
    assert response
    assert response.ok
    assert await response.text() == "context"


async def test_should_support_set_cookie_header(
    context_factory: "Callable[..., Awaitable[BrowserContext]]",
    default_same_site_cookie_value: str,
) -> None:
    context = await context_factory()
    page = await context.new_page()
    await page.route(
        "https://example.com/",
        lambda route: route.fulfill(
            headers={
                "Set-Cookie": "name=value; domain=.example.com; Path=/",
            },
            content_type="text/html",
            body="done",
        ),
    )
    await page.goto("https://example.com")
    cookies = await context.cookies()
    assert len(cookies) == 1
    assert cookies[0] == {
        "sameSite": default_same_site_cookie_value,
        "name": "name",
        "value": "value",
        "domain": ".example.com",
        "path": "/",
        "expires": -1,
        "httpOnly": False,
        "secure": False,
    }


@pytest.mark.skip_browser("webkit")
async def test_should_ignore_secure_set_cookie_header_for_insecure_request(
    context_factory: "Callable[..., Awaitable[BrowserContext]]",
) -> None:
    context = await context_factory()
    page = await context.new_page()
    await page.route(
        "http://example.com/",
        lambda route: route.fulfill(
            headers={
                "Set-Cookie": "name=value; domain=.example.com; Path=/; Secure",
            },
            content_type="text/html",
            body="done",
        ),
    )
    await page.goto("http://example.com")
    cookies = await context.cookies()
    assert len(cookies) == 0


async def test_should_use_set_cookie_header_in_future_requests(
    context_factory: "Callable[..., Awaitable[BrowserContext]]",
    server: Server,
    default_same_site_cookie_value: str,
) -> None:
    context = await context_factory()
    page = await context.new_page()

    await page.route(
        server.EMPTY_PAGE,
        lambda route: route.fulfill(
            headers={
                "Set-Cookie": "name=value",
            },
            content_type="text/html",
            body="done",
        ),
    )
    await page.goto(server.EMPTY_PAGE)
    assert await context.cookies() == [
        {
            "sameSite": default_same_site_cookie_value,
            "name": "name",
            "value": "value",
            "domain": "localhost",
            "path": "/",
            "expires": -1,
            "httpOnly": False,
            "secure": False,
        }
    ]

    cookie = ""

    def _handle_request(request: TestServerRequest) -> None:
        nonlocal cookie
        cookie = must(request.getHeader("cookie"))
        request.finish()

    server.set_route("/foo.html", _handle_request)
    await page.goto(server.PREFIX + "/foo.html")
    assert cookie == "name=value"


async def test_should_work_with_ignore_https_errors(
    browser: Browser, https_server: Server
) -> None:
    context = await browser.new_context(ignore_https_errors=True)
    page = await context.new_page()

    await page.route("**/*", lambda route: route.continue_())
    response = await page.goto(https_server.EMPTY_PAGE)
    assert must(response).status == 200
    await context.close()


async def test_should_support_the_times_parameter_with_route_matching(
    context: BrowserContext, page: Page, server: Server
) -> None:
    intercepted: List[int] = []

    async def _handle_request(route: Route) -> None:
        intercepted.append(1)
        await route.continue_()

    await context.route("**/empty.html", _handle_request, times=1)
    await page.goto(server.EMPTY_PAGE)
    await page.goto(server.EMPTY_PAGE)
    await page.goto(server.EMPTY_PAGE)
    assert len(intercepted) == 1


async def test_should_work_if_handler_with_times_parameter_was_removed_from_another_handler(
    context: BrowserContext, page: Page, server: Server
) -> None:
    intercepted = []

    async def _handler(route: Route) -> None:
        intercepted.append("first")
        await route.continue_()

    await context.route("**/*", _handler, times=1)

    async def _handler2(route: Route) -> None:
        intercepted.append("second")
        await context.unroute("**/*", _handler)
        await route.fallback()

    await context.route("**/*", _handler2)
    await page.goto(server.EMPTY_PAGE)
    assert intercepted == ["second"]
    intercepted.clear()
    await page.goto(server.EMPTY_PAGE)
    assert intercepted == ["second"]


async def test_should_support_async_handler_with_times(
    context: BrowserContext, page: Page, server: Server
) -> None:
    async def _handler(route: Route) -> None:
        await asyncio.sleep(0.1)
        await route.fulfill(
            body="<html>intercepted</html>",
            content_type="text/html",
        )

    await context.route("**/empty.html", _handler, times=1)
    await page.goto(server.EMPTY_PAGE)
    await expect(page.locator("body")).to_have_text("intercepted")
    await page.goto(server.EMPTY_PAGE)
    await expect(page.locator("body")).not_to_have_text("intercepted")


async def test_should_override_post_body_with_empty_string(
    context: BrowserContext, server: Server, page: Page
) -> None:
    await context.route(
        "**/empty.html",
        lambda route: route.continue_(
            post_data="",
        ),
    )

    req = await asyncio.gather(
        server.wait_for_request("/empty.html"),
        page.set_content(
            """
            <script>
            (async () => {
                await fetch('%s', {
                    method: 'POST',
                    body: 'original',
                });
            })()
            </script>
            """
            % server.EMPTY_PAGE
        ),
    )

    assert req[0].post_body == b""


async def test_should_chain_fallback(
    context: BrowserContext, page: Page, server: Server
) -> None:
    intercepted: List[int] = []

    async def _handler1(route: Route) -> None:
        intercepted.append(1)
        await route.fallback()

    await context.route("**/empty.html", _handler1)

    async def _handler2(route: Route) -> None:
        intercepted.append(2)
        await route.fallback()

    await context.route("**/empty.html", _handler2)

    async def _handler3(route: Route) -> None:
        intercepted.append(3)
        await route.fallback()

    await context.route("**/empty.html", _handler3)
    await page.goto(server.EMPTY_PAGE)
    assert intercepted == [3, 2, 1]


async def test_should_chain_fallback_with_dynamic_url(
    context: BrowserContext, page: Page, server: Server
) -> None:
    intercepted: List[int] = []

    async def _handler1(route: Route) -> None:
        intercepted.append(1)
        await route.fallback(url=server.EMPTY_PAGE)

    await context.route("**/bar", _handler1)

    async def _handler2(route: Route) -> None:
        intercepted.append(2)
        await route.fallback(url="http://localhost/bar")

    await context.route("**/foo", _handler2)

    async def _handler3(route: Route) -> None:
        intercepted.append(3)
        await route.fallback(url="http://localhost/foo")

    await context.route("**/empty.html", _handler3)
    await page.goto(server.EMPTY_PAGE)
    assert intercepted == [3, 2, 1]


async def test_should_not_chain_fulfill(
    page: Page, context: BrowserContext, server: Server
) -> None:
    failed = [False]

    def handler(route: Route) -> None:
        failed[0] = True

    await context.route("**/empty.html", handler)
    await context.route(
        "**/empty.html",
        lambda route: asyncio.create_task(route.fulfill(status=200, body="fulfilled")),
    )
    await context.route(
        "**/empty.html", lambda route: asyncio.create_task(route.fallback())
    )

    response = await page.goto(server.EMPTY_PAGE)
    assert response
    body = await response.body()
    assert body == b"fulfilled"
    assert not failed[0]


async def test_should_not_chain_abort(
    page: Page,
    context: BrowserContext,
    server: Server,
    is_webkit: bool,
    is_firefox: bool,
) -> None:
    failed = [False]

    def handler(route: Route) -> None:
        failed[0] = True

    await context.route("**/empty.html", handler)
    await context.route(
        "**/empty.html", lambda route: asyncio.create_task(route.abort())
    )
    await context.route(
        "**/empty.html", lambda route: asyncio.create_task(route.fallback())
    )

    with pytest.raises(Error) as excinfo:
        await page.goto(server.EMPTY_PAGE)
    if is_webkit:
        assert "Blocked by Web Inspector" in excinfo.value.message
    elif is_firefox:
        assert "NS_ERROR_FAILURE" in excinfo.value.message
    else:
        assert "net::ERR_FAILED" in excinfo.value.message
    assert not failed[0]


async def test_should_chain_fallback_into_page(
    context: BrowserContext, page: Page, server: Server
) -> None:
    intercepted = []

    def _handler1(route: Route) -> None:
        intercepted.append(1)
        asyncio.create_task(route.fallback())

    await context.route("**/empty.html", _handler1)

    def _handler2(route: Route) -> None:
        intercepted.append(2)
        asyncio.create_task(route.fallback())

    await context.route("**/empty.html", _handler2)

    def _handler3(route: Route) -> None:
        intercepted.append(3)
        asyncio.create_task(route.fallback())

    await context.route("**/empty.html", _handler3)

    def _handler4(route: Route) -> None:
        intercepted.append(4)
        asyncio.create_task(route.fallback())

    await page.route("**/empty.html", _handler4)

    def _handler5(route: Route) -> None:
        intercepted.append(5)
        asyncio.create_task(route.fallback())

    await page.route("**/empty.html", _handler5)

    def _handler6(route: Route) -> None:
        intercepted.append(6)
        asyncio.create_task(route.fallback())

    await page.route("**/empty.html", _handler6)

    await page.goto(server.EMPTY_PAGE)
    assert intercepted == [6, 5, 4, 3, 2, 1]


async def test_should_fall_back_async(
    page: Page, context: BrowserContext, server: Server
) -> None:
    intercepted = []

    async def _handler1(route: Route) -> None:
        intercepted.append(1)
        await asyncio.sleep(0.1)
        await route.fallback()

    await context.route("**/empty.html", _handler1)

    async def _handler2(route: Route) -> None:
        intercepted.append(2)
        await asyncio.sleep(0.1)
        await route.fallback()

    await context.route("**/empty.html", _handler2)

    async def _handler3(route: Route) -> None:
        intercepted.append(3)
        await asyncio.sleep(0.1)
        await route.fallback()

    await context.route("**/empty.html", _handler3)

    await page.goto(server.EMPTY_PAGE)
    assert intercepted == [3, 2, 1]
