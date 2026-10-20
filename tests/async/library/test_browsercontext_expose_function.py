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

"""Port of tests/library/browsercontext-expose-function.spec.ts."""

import time
from typing import Any, Callable, Dict, List

import pytest

from playwright.async_api import BrowserContext, Error, JSHandle, Page
from tests.server import Server, TestServerRequest


async def poll_until_equal(
    page: Page, actual: Callable[[], Any], expected: Any, timeout: float = 5000
) -> None:
    """Port of `await expect.poll(actual).toEqual(expected)`."""
    deadline = time.monotonic() + timeout / 1000
    while actual() != expected and time.monotonic() < deadline:
        await page.wait_for_timeout(100)
    assert actual() == expected


async def test_EF_022_expose_binding_should_work(context: BrowserContext) -> None:
    binding_sources: List[Dict] = []

    def add(source: Dict, a: int, b: int) -> int:
        binding_sources.append(source)
        return a + b

    await context.expose_binding("add", add)
    page = await context.new_page()
    result = await page.evaluate("add(5, 6)")
    assert binding_sources[0]["context"] is context
    assert binding_sources[0]["page"] is page
    assert binding_sources[0]["frame"] is page.main_frame
    assert result == 11


async def test_EF_023_should_work(context: BrowserContext, server: Server) -> None:
    await context.expose_function("add", lambda a, b: a + b)
    page = await context.new_page()
    await page.expose_function("mul", lambda a, b: a * b)
    await context.expose_function("sub", lambda a, b: a - b)

    async def add_handle(source: Dict, a: int, b: int) -> JSHandle:
        handle = await source["frame"].evaluate_handle("([a, b]) => a + b", [a, b])
        return handle

    await context.expose_binding("addHandle", add_handle)
    result = await page.evaluate(
        "(async () => ({ mul: await mul(9, 4), add: await add(9, 4), sub: await sub(9, 4), addHandle: await addHandle(5, 6) }))()"
    )
    assert result == {"mul": 36, "add": 13, "sub": 5, "addHandle": 11}


async def test_EF_024_should_dispose(context: BrowserContext, server: Server) -> None:
    binding = await context.expose_function("compute", lambda a, b: a * b)
    page = await context.new_page()
    result = await page.evaluate(
        """async function() {
            return await window['compute'](9, 4);
        }"""
    )
    assert result == 36
    await binding.close()

    with pytest.raises(Error) as exc_info:
        await page.evaluate(
            """async function() {
                return await window['compute'](9, 4);
            }"""
        )
    assert "is not a function" in exc_info.value.message


async def test_EF_025_should_throw_for_duplicate_registrations(
    context: BrowserContext, server: Server
) -> None:
    await context.expose_function("foo", lambda: None)
    await context.expose_function("bar", lambda: None)
    with pytest.raises(Error) as exc_info:
        await context.expose_function("foo", lambda: None)
    assert 'Function "foo" has been already registered' in exc_info.value.message
    page = await context.new_page()
    with pytest.raises(Error) as exc_info:
        await page.expose_function("foo", lambda: None)
    assert (
        'Function "foo" has been already registered in the browser context'
        in exc_info.value.message
    )
    await page.expose_function("baz", lambda: None)
    with pytest.raises(Error) as exc_info:
        await context.expose_function("baz", lambda: None)
    assert (
        'Function "baz" has been already registered in one of the pages'
        in exc_info.value.message
    )


async def test_EF_026_should_be_callable_from_inside_add_init_script(
    context: BrowserContext, server: Server
) -> None:
    args: List[str] = []
    await context.expose_function("woof", lambda arg: args.append(arg))
    await context.add_init_script('window["woof"]("context")')
    page = await context.new_page()
    await page.evaluate("undefined")
    await poll_until_equal(page, lambda: args, ["context"])
    args.clear()
    await page.add_init_script('window["woof"]("page")')
    await page.reload()
    await poll_until_equal(page, lambda: args, ["context", "page"])


async def test_EF_027_should_work_with_csp(
    page: Page, context: BrowserContext, server: Server
) -> None:
    server.set_csp("/empty.html", 'default-src "self"')
    await page.goto(server.EMPTY_PAGE)
    called = False

    def hi(source: Dict) -> bool:
        nonlocal called
        called = True
        return called

    await context.expose_binding("hi", hi)
    await page.evaluate("() => window.hi()")
    assert called is True


async def test_EF_028_should_call_binding_from_pagehide_handler_when_navigating_away(
    context: BrowserContext, page: Page, server: Server, browser_name: str
) -> None:
    if browser_name == "chromium":
        pytest.skip(
            "fixme: Chromium drops CDP events from the old document after the frame host swap"
        )
    calls: List[str] = []
    await context.expose_binding(
        "reportFromPage", lambda _source, message: calls.append(message)
    )

    def html(body: str) -> str:
        return (
            f"<!doctype html>{body}<script>addEventListener('pagehide', () => "
            "window.reportFromPage('pagehide of ' + location.pathname));</script>"
        )

    def route_a(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("content-type", "text/html")
        request.write(html('<a id="next" href="/b.html">next</a>').encode())
        request.finish()

    def route_b(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("content-type", "text/html")
        request.write(html("<p>b</p>").encode())
        request.finish()

    server.set_route("/a.html", route_a)
    server.set_route("/b.html", route_b)
    await page.goto(server.PREFIX + "/a.html")
    await page.click("#next")
    await page.wait_for_url("**/b.html")
    await poll_until_equal(page, lambda: "pagehide of /a.html" in calls, True)
