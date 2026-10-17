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
from typing import Awaitable, Callable, List, TypeVar

import pytest

from playwright._impl._greenlets import wait_for_future
from playwright.sync_api import (
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

T = TypeVar("T")


def wait_for(page: Page, awaitable: "Awaitable[T]") -> T:
    """Port of `await promise`: runs the event loop until the awaitable settles."""
    future = asyncio.ensure_future(awaitable)
    wait_for_future(page._loop, page._dispatcher_fiber, future)
    return future.result()


def test_RO_165_should_intercept(browser: Browser, server: Server) -> None:
    context = browser.new_context()
    intercepted = False

    def handler(route: Route) -> None:
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
        route.continue_()

    context.route("**/empty.html", handler)
    page = context.new_page()
    response = must(page.goto(server.EMPTY_PAGE))
    assert response.ok is True
    assert intercepted is True
    context.close()


def test_RO_166_should_unroute(browser: Browser, server: Server) -> None:
    context = browser.new_context()
    page = context.new_page()

    intercepted: List[int] = []

    def handler1(route: Route) -> None:
        intercepted.append(1)
        route.fallback()

    def handler2(route: Route) -> None:
        intercepted.append(2)
        route.fallback()

    def handler3(route: Route) -> None:
        intercepted.append(3)
        route.fallback()

    def handler4(route: Route) -> None:
        intercepted.append(4)
        route.fallback()

    context.route("**/*", handler1)
    context.route("**/empty.html", handler2)
    context.route("**/empty.html", handler3)
    context.route(re.compile("empty.html"), handler4)
    page.goto(server.EMPTY_PAGE)
    assert intercepted == [4, 3, 2, 1]

    intercepted = []
    context.unroute(re.compile("empty.html"), handler4)
    page.goto(server.EMPTY_PAGE)
    assert intercepted == [3, 2, 1]

    intercepted = []
    context.unroute("**/empty.html")
    page.goto(server.EMPTY_PAGE)
    assert intercepted == [1]

    context.close()


def test_RO_167_should_yield_to_page_route(browser: Browser, server: Server) -> None:
    context = browser.new_context()

    def context_handler(route: Route) -> None:
        route.fulfill(status=200, body="context")

    context.route("**/empty.html", context_handler)
    page = context.new_page()

    def page_handler(route: Route) -> None:
        route.fulfill(status=200, body="page")

    page.route("**/empty.html", page_handler)
    response = must(page.goto(server.EMPTY_PAGE))
    assert response.ok is True
    assert response.text() == "page"
    context.close()


def test_RO_168_should_fall_back_to_context_route(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context()

    def context_handler(route: Route) -> None:
        route.fulfill(status=200, body="context")

    context.route("**/empty.html", context_handler)
    page = context.new_page()

    def page_handler(route: Route) -> None:
        route.fulfill(status=200, body="page")

    page.route("**/non-empty.html", page_handler)
    response = must(page.goto(server.EMPTY_PAGE))
    assert response.ok is True
    assert response.text() == "context"
    context.close()


def test_RO_169_should_support_set_cookie_header(
    context_factory: "Callable[..., BrowserContext]",
    default_same_site_cookie_value: str,
) -> None:
    context = context_factory()
    page = context.new_page()

    def handler(route: Route, request: Request) -> None:
        route.fulfill(
            headers={"Set-Cookie": "name=value; domain=.example.com; Path=/"},
            content_type="text/html",
            body="done",
        )

    page.route("https://example.com/", handler)
    page.goto("https://example.com")
    assert context.cookies() == [
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


def test_RO_170_should_ignore_secure_set_cookie_header_for_insecure_requests(
    context_factory: "Callable[..., BrowserContext]",
    server: Server,
    browser_name: str,
    is_mac: bool,
) -> None:
    if browser_name == "webkit" and not is_mac:
        pytest.skip("fixme: upstream fixme for WebKit on non-Mac")

    context = context_factory()
    page = context.new_page()

    def handler(route: Route, request: Request) -> None:
        route.fulfill(
            headers={"Set-Cookie": "name=value; domain=.example.com; Path=/; Secure"},
            content_type="text/html",
            body="done",
        )

    page.route("http://example.com/", handler)
    page.goto("http://example.com")
    assert context.cookies() == []


def test_RO_171_should_use_set_cookie_header_in_future_requests(
    context_factory: "Callable[..., BrowserContext]",
    server: Server,
    default_same_site_cookie_value: str,
) -> None:
    context = context_factory()
    page = context.new_page()

    def handler(route: Route, request: Request) -> None:
        route.fulfill(
            headers={"Set-Cookie": "name=value"},
            content_type="text/html",
            body="done",
        )

    page.route(server.EMPTY_PAGE, handler)
    page.goto(server.EMPTY_PAGE)
    assert context.cookies() == [
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
    page.goto(server.PREFIX + "/foo.html")
    assert cookie == "name=value"


def test_RO_172_should_work_with_ignore_https_errors(
    browser: Browser, https_server: Server
) -> None:
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()

    page.route("**/*", lambda route: route.continue_())
    response = must(page.goto(https_server.EMPTY_PAGE))
    assert response.status == 200
    context.close()


def test_RO_173_should_support_the_times_parameter_with_route_matching(
    context: BrowserContext, page: Page, server: Server
) -> None:
    intercepted: List[int] = []

    def handler(route: Route) -> None:
        intercepted.append(1)
        route.continue_()

    context.route("**/empty.html", handler, times=1)
    page.goto(server.EMPTY_PAGE)
    page.goto(server.EMPTY_PAGE)
    page.goto(server.EMPTY_PAGE)
    assert len(intercepted) == 1


def test_RO_174_should_work_if_handler_with_times_parameter_was_removed_from_another_handler(
    context: BrowserContext, page: Page, server: Server
) -> None:
    intercepted: List[str] = []

    def handler(route: Route) -> None:
        intercepted.append("first")
        route.continue_()

    context.route("**/*", handler, times=1)

    def handler2(route: Route) -> None:
        intercepted.append("second")
        context.unroute("**/*", handler)
        route.fallback()

    context.route("**/*", handler2)
    page.goto(server.EMPTY_PAGE)
    assert intercepted == ["second"]
    intercepted.clear()
    page.goto(server.EMPTY_PAGE)
    assert intercepted == ["second"]


def test_RO_175_should_support_async_handler_w_times(
    context: BrowserContext, page: Page, server: Server
) -> None:
    def handler(route: Route) -> None:
        page.wait_for_timeout(100)
        route.fulfill(
            body="<html>intercepted</html>",
            content_type="text/html",
        )

    context.route("**/empty.html", handler, times=1)
    page.goto(server.EMPTY_PAGE)
    expect(page.locator("body")).to_have_text("intercepted")
    page.goto(server.EMPTY_PAGE)
    expect(page.locator("body")).not_to_have_text("intercepted")


def test_RO_176_should_overwrite_post_body_with_empty_string(
    context: BrowserContext, server: Server, page: Page
) -> None:
    def handler(route: Route) -> None:
        route.continue_(post_data="")

    context.route("**/empty.html", handler)

    req_task = asyncio.create_task(server.wait_for_request("/empty.html"))
    page.set_content(
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
    req = wait_for(page, req_task)

    body = (req.post_body or b"").decode()
    assert body == ""


def test_RO_177_should_chain_fallback(
    context: BrowserContext, page: Page, server: Server
) -> None:
    intercepted: List[int] = []

    def handler1(route: Route) -> None:
        intercepted.append(1)
        route.fallback()

    def handler2(route: Route) -> None:
        intercepted.append(2)
        route.fallback()

    def handler3(route: Route) -> None:
        intercepted.append(3)
        route.fallback()

    context.route("**/empty.html", handler1)
    context.route("**/empty.html", handler2)
    context.route("**/empty.html", handler3)
    page.goto(server.EMPTY_PAGE)
    assert intercepted == [3, 2, 1]


def test_RO_178_should_chain_fallback_w_dynamic_url(
    context: BrowserContext, page: Page, server: Server
) -> None:
    intercepted: List[int] = []

    def handler1(route: Route) -> None:
        intercepted.append(1)
        route.fallback(url=server.EMPTY_PAGE)

    def handler2(route: Route) -> None:
        intercepted.append(2)
        route.fallback(url="http://localhost/bar")

    def handler3(route: Route) -> None:
        intercepted.append(3)
        route.fallback(url="http://localhost/foo")

    context.route("**/bar", handler1)
    context.route("**/foo", handler2)
    context.route("**/empty.html", handler3)

    page.goto(server.EMPTY_PAGE)
    assert intercepted == [3, 2, 1]


def test_RO_179_should_not_chain_fulfill(
    context: BrowserContext, page: Page, server: Server
) -> None:
    failed = False

    def handler1(route: Route) -> None:
        nonlocal failed
        failed = True

    def handler2(route: Route) -> None:
        route.fulfill(status=200, body="fulfilled")

    def handler3(route: Route) -> None:
        route.fallback()

    context.route("**/empty.html", handler1)
    context.route("**/empty.html", handler2)
    context.route("**/empty.html", handler3)
    response = must(page.goto(server.EMPTY_PAGE))
    body = response.body()
    assert body.decode() == "fulfilled"
    assert not failed


def test_RO_180_should_not_chain_abort(
    context: BrowserContext, page: Page, server: Server
) -> None:
    failed = False

    def handler1(route: Route) -> None:
        nonlocal failed
        failed = True

    def handler2(route: Route) -> None:
        route.abort()

    def handler3(route: Route) -> None:
        route.fallback()

    context.route("**/empty.html", handler1)
    context.route("**/empty.html", handler2)
    context.route("**/empty.html", handler3)
    with pytest.raises(Error) as exc_info:
        page.goto(server.EMPTY_PAGE)
    assert exc_info.value
    assert not failed


def test_RO_181_should_chain_fallback_into_page(
    context: BrowserContext, page: Page, server: Server
) -> None:
    intercepted: List[int] = []

    def make_handler(value: int) -> Callable[[Route], None]:
        def handler(route: Route) -> None:
            intercepted.append(value)
            route.fallback()

        return handler

    context.route("**/empty.html", make_handler(1))
    context.route("**/empty.html", make_handler(2))
    context.route("**/empty.html", make_handler(3))
    page.route("**/empty.html", make_handler(4))
    page.route("**/empty.html", make_handler(5))
    page.route("**/empty.html", make_handler(6))
    page.goto(server.EMPTY_PAGE)
    assert intercepted == [6, 5, 4, 3, 2, 1]


def test_RO_182_should_fall_back_async(
    page: Page, context: BrowserContext, server: Server
) -> None:
    intercepted: List[int] = []

    def handler1(route: Route) -> None:
        intercepted.append(1)
        page.wait_for_timeout(100)
        route.fallback()

    def handler2(route: Route) -> None:
        intercepted.append(2)
        page.wait_for_timeout(100)
        route.fallback()

    def handler3(route: Route) -> None:
        intercepted.append(3)
        page.wait_for_timeout(100)
        route.fallback()

    context.route("**/empty.html", handler1)
    context.route("**/empty.html", handler2)
    context.route("**/empty.html", handler3)
    page.goto(server.EMPTY_PAGE)
    assert intercepted == [3, 2, 1]


def test_RO_183_should_bypass_disk_cache_when_context_interception_is_enabled(
    page: Page, server: Server
) -> None:
    page.context.route("**/api*", lambda route: route.continue_())
    page.goto(server.PREFIX + "/frames/one-frame.html")
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
        with page.expect_response("**/api") as response_info:
            page.evaluate(
                """async () => {
                    const response = await fetch('/api');
                    return response.status;
                }"""
            )
        response = response_info.value
        assert response.status == 200
        assert len(requests) == i + 1


def test_RO_184_should_fulfill_popup_main_request_using_alias(
    page: Page, server: Server
) -> None:
    def handler(route: Route) -> None:
        response = route.fetch()
        route.fulfill(response=response, body="hello")

    page.context.route("**/*", handler)
    page.set_content(f'<a target=_blank href="{server.EMPTY_PAGE}">click me</a>')
    with page.expect_popup() as popup_info:
        page.get_by_text("click me").click()
    popup = popup_info.value
    expect(popup.locator("body")).to_have_text("hello")
