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
from typing import List, cast

from playwright.browser import Browser, Page
from playwright.network import Request, Route


async def test_link_navigation_inherit_user_agent_from_browser_context(
    browser: Browser, server
):
    context = await browser.newContext(userAgent="hey")

    page = await context.newPage()
    await page.goto(server.EMPTY_PAGE)
    await page.setContent(
        '<a target=_blank rel=noopener href="/popup/popup.html">link</a>'
    )
    request_waitable = asyncio.create_task(server.wait_for_request("/popup/popup.html"))
    await asyncio.sleep(0)  # execute scheduled tasks, but don't await them
    popup = cast(
        Page, (await asyncio.gather(context.waitForEvent("page"), page.click("a"),))[0]
    )
    await popup.waitForLoadState("domcontentloaded")
    user_agent = await popup.evaluate("window.initialUserAgent")
    request = await request_waitable
    assert user_agent == "hey"
    assert request.requestHeaders.getRawHeaders("user-agent") == ["hey"]
    await context.close()


async def test_link_navigation_respect_routes_from_browser_context(context, server):
    page = await context.newPage()
    await page.goto(server.EMPTY_PAGE)
    await page.setContent('<a target=_blank rel=noopener href="empty.html">link</a>')

    def handle_request(route: Route, request: Request, intercepted) -> None:
        asyncio.create_task(route.continue_())
        intercepted.append(True)

    intercepted: List[bool] = []
    await context.route(
        "**/empty.html",
        lambda route, request: handle_request(route, request, intercepted),
    )
    await asyncio.gather(
        context.waitForEvent("page"), page.click("a"),
    )
    assert intercepted == [True]


async def test_window_open_inherit_user_agent_from_browser_context(
    browser: Browser, server
):
    context = await browser.newContext(userAgent="hey")

    page = await context.newPage()
    await page.goto(server.EMPTY_PAGE)
    request_promise = asyncio.create_task(server.wait_for_request("/dummy.html"))
    await asyncio.sleep(0)  # execute scheduled tasks, but don't await them
    user_agent = await page.evaluate(
        """url => {
            win = window.open(url)
            return win.navigator.userAgent
        }""",
        server.PREFIX + "/dummy.html",
    )
    request = await request_promise
    assert user_agent == "hey"
    assert request.requestHeaders.getRawHeaders("user-agent") == ["hey"]
    await context.close()


async def test_should_inherit_extra_headers_from_browser_context(
    browser: Browser, server
):
    context = await browser.newContext(extraHTTPHeaders={"foo": "bar"})

    page = await context.newPage()
    await page.goto(server.EMPTY_PAGE)
    request_promise = asyncio.create_task(server.wait_for_request("/dummy.html"))
    await asyncio.sleep(0)  # execute scheduled tasks, but don't await them
    await page.evaluate(
        "url => window._popup = window.open(url)", server.PREFIX + "/dummy.html"
    )
    request = await request_promise
    assert request.requestHeaders.getRawHeaders("foo") == ["bar"]
    await context.close()


async def test_should_inherit_offline_from_browser_context(context, server):
    page = await context.newPage()
    await page.goto(server.EMPTY_PAGE)
    await context.setOffline(True)
    online = await page.evaluate(
        """url => {
            win = window.open(url)
            return win.navigator.onLine
        }""",
        server.PREFIX + "/dummy.html",
    )
    assert online is False


async def test_should_inherit_http_credentials_from_browser_context(
    browser: Browser, server
):
    server.set_auth("/title.html", b"user", b"pass")
    context = await browser.newContext(
        httpCredentials={"username": "user", "password": "pass"}
    )
    page = await context.newPage()
    await page.goto(server.EMPTY_PAGE)
    popup = (
        await asyncio.gather(
            page.waitForEvent("popup"),
            page.evaluate(
                "url => window._popup = window.open(url)", server.PREFIX + "/title.html"
            ),
        )
    )[0]
    await popup.waitForLoadState("domcontentloaded")
    assert await popup.title() == "Woof-Woof"
    await context.close()


async def test_should_inherit_touch_support_from_browser_context(
    browser: Browser, server
):
    context = await browser.newContext(
        viewport={"width": 400, "height": 500}, hasTouch=True
    )

    page = await context.newPage()
    await page.goto(server.EMPTY_PAGE)
    has_touch = await page.evaluate(
        """() => {
            win = window.open('')
            return 'ontouchstart' in win
        }"""
    )

    assert has_touch
    await context.close()


async def test_should_inherit_viewport_size_from_browser_context(
    browser: Browser, server
):
    context = await browser.newContext(viewport={"width": 400, "height": 500})

    page = await context.newPage()
    await page.goto(server.EMPTY_PAGE)
    size = await page.evaluate(
        """() => {
            win = window.open('about:blank')
            return { width: win.innerWidth, height: win.innerHeight }
        }"""
    )

    assert size == {"width": 400, "height": 500}
    await context.close()


async def test_should_use_viewport_size_from_window_features(browser: Browser, server):
    context = await browser.newContext(viewport={"width": 700, "height": 700})
    page = await context.newPage()
    await page.goto(server.EMPTY_PAGE)
    [size, popup] = await asyncio.gather(
        page.evaluate(
            """() => {
                win = window.open(window.location.href, 'Title', 'toolbar=no,location=no,directories=no,status=no,menubar=no,scrollbars=yes,resizable=yes,width=600,height=300,top=0,left=0')
                return { width: win.innerWidth, height: win.innerHeight }
            }"""
        ),
        page.waitForEvent("popup"),
    )
    await popup.setViewportSize(width=500, height=400)
    await popup.waitForLoadState()
    resized = await popup.evaluate(
        "() => ({ width: window.innerWidth, height: window.innerHeight })"
    )
    await context.close()
    assert size == {"width": 600, "height": 300}
    assert resized == {"width": 500, "height": 400}


async def test_should_respect_routes_from_browser_context(context, server):
    page = await context.newPage()
    await page.goto(server.EMPTY_PAGE)

    def handle_request(route, request, intercepted):
        asyncio.create_task(route.continue_())
        intercepted.append(True)

    intercepted = []
    await context.route(
        "**/empty.html",
        lambda route, request: handle_request(route, request, intercepted),
    )

    await asyncio.gather(
        page.waitForEvent("popup"),
        page.evaluate("url => window.__popup = window.open(url)", server.EMPTY_PAGE),
    )
    assert len(intercepted) == 1


async def test_browser_context_add_init_script_should_apply_to_an_in_process_popup(
    context, server
):
    await context.addInitScript("window.injected = 123")
    page = await context.newPage()
    await page.goto(server.EMPTY_PAGE)
    injected = await page.evaluate(
        """() => {
            const win = window.open('about:blank');
            return win.injected;
        }"""
    )

    assert injected == 123


async def test_browser_context_add_init_script_should_apply_to_a_cross_process_popup(
    context, server
):
    await context.addInitScript("window.injected = 123")
    page = await context.newPage()
    await page.goto(server.EMPTY_PAGE)
    popup = (
        await asyncio.gather(
            page.waitForEvent("popup"),
            page.evaluate(
                "url => window.open(url)", server.CROSS_PROCESS_PREFIX + "/title.html"
            ),
        )
    )[0]
    assert await popup.evaluate("injected") == 123
    await popup.reload()
    assert await popup.evaluate("injected") == 123


async def test_should_expose_function_from_browser_context(context, server):
    await context.exposeFunction("add", lambda a, b: a + b)
    page = await context.newPage()
    await page.goto(server.EMPTY_PAGE)
    added = await page.evaluate(
        """async () => {
            win = window.open('about:blank')
            return win.add(9, 4)
        }"""
    )

    assert added == 13


async def test_should_work(context):
    page = await context.newPage()
    popup = (
        await asyncio.gather(
            page.waitForEvent("popup"),
            page.evaluate('window.__popup = window.open("about:blank")'),
        )
    )[0]
    assert await page.evaluate("!!window.opener") is False
    assert await popup.evaluate("!!window.opener")


async def test_should_work_with_window_features(context, server):
    page = await context.newPage()
    await page.goto(server.EMPTY_PAGE)
    popup = (
        await asyncio.gather(
            page.waitForEvent("popup"),
            page.evaluate(
                'window.__popup = window.open(window.location.href, "Title", "toolbar=no,location=no,directories=no,status=no,menubar=no,scrollbars=yes,resizable=yes,width=780,height=200,top=0,left=0")'
            ),
        )
    )[0]
    assert await page.evaluate("!!window.opener") is False
    assert await popup.evaluate("!!window.opener")


async def test_window_open_emit_for_immediately_closed_popups(context):
    page = await context.newPage()
    popup = (
        await asyncio.gather(
            page.waitForEvent("popup"),
            page.evaluate(
                """() => {
                    win = window.open('about:blank')
                    win.close()
                }"""
            ),
        )
    )[0]
    assert popup


async def test_should_emit_for_immediately_closed_popups(context, server):
    page = await context.newPage()
    await page.goto(server.EMPTY_PAGE)
    popup = (
        await asyncio.gather(
            page.waitForEvent("popup"),
            page.evaluate(
                """() => {
                    win = window.open(window.location.href)
                    win.close()
                }"""
            ),
        )
    )[0]
    assert popup


async def test_should_be_able_to_capture_alert(context):
    page = await context.newPage()
    evaluate_promise = asyncio.create_task(
        page.evaluate(
            """() => {
                const win = window.open('')
                win.alert('hello')
            }"""
        )
    )

    popup = await page.waitForEvent("popup")
    dialog = await popup.waitForEvent("dialog")
    assert dialog.message == "hello"
    await dialog.dismiss()
    await evaluate_promise


async def test_should_work_with_empty_url(context):
    page = await context.newPage()
    popup = (
        await asyncio.gather(
            page.waitForEvent("popup"),
            page.evaluate('() => window.__popup = window.open("")'),
        )
    )[0]
    assert await page.evaluate("!!window.opener") is False
    assert await popup.evaluate("!!window.opener")


async def test_should_work_with_noopener_and_no_url(context):
    page = await context.newPage()
    popup = (
        await asyncio.gather(
            page.waitForEvent("popup"),
            page.evaluate(
                '() => window.__popup = window.open(undefined, null, "noopener")'
            ),
        )
    )[0]
    # Chromium reports 'about:blank#blocked' here.
    assert popup.url.split("#")[0] == "about:blank"
    assert await page.evaluate("!!window.opener") is False
    assert await popup.evaluate("!!window.opener") is False


async def test_should_work_with_noopener_and_about_blank(context):
    page = await context.newPage()
    popup = (
        await asyncio.gather(
            page.waitForEvent("popup"),
            page.evaluate(
                '() => window.__popup = window.open("about:blank", null, "noopener")'
            ),
        )
    )[0]
    assert await page.evaluate("!!window.opener") is False
    assert await popup.evaluate("!!window.opener") is False


async def test_should_work_with_noopener_and_url(context, server):
    page = await context.newPage()
    await page.goto(server.EMPTY_PAGE)
    popup = (
        await asyncio.gather(
            page.waitForEvent("popup"),
            page.evaluate(
                'url => window.__popup = window.open(url, null, "noopener")',
                server.EMPTY_PAGE,
            ),
        )
    )[0]
    assert await page.evaluate("!!window.opener") is False
    assert await popup.evaluate("!!window.opener") is False


async def test_should_work_with_clicking_target__blank(context, server):
    page = await context.newPage()
    await page.goto(server.EMPTY_PAGE)
    await page.setContent('<a target=_blank rel="opener" href="/one-style.html">yo</a>')
    popup = (await asyncio.gather(page.waitForEvent("popup"), page.click("a"),))[0]
    assert await page.evaluate("!!window.opener") is False
    assert await popup.evaluate("!!window.opener")


async def test_should_work_with_fake_clicking_target__blank_and_rel_noopener(
    context, server
):
    page = await context.newPage()
    await page.goto(server.EMPTY_PAGE)
    await page.setContent('<a target=_blank rel=noopener href="/one-style.html">yo</a>')
    popup = (
        await asyncio.gather(
            page.waitForEvent("popup"), page.evalOnSelector("a", "a => a.click()"),
        )
    )[0]
    assert await page.evaluate("!!window.opener") is False
    assert await popup.evaluate("!!window.opener") is False


async def test_should_work_with_clicking_target__blank_and_rel_noopener(
    context, server
):
    page = await context.newPage()
    await page.goto(server.EMPTY_PAGE)
    await page.setContent('<a target=_blank rel=noopener href="/one-style.html">yo</a>')
    popup = (await asyncio.gather(page.waitForEvent("popup"), page.click("a"),))[0]
    assert await page.evaluate("!!window.opener") is False
    assert await popup.evaluate("!!window.opener") is False


async def test_should_not_treat_navigations_as_new_popups(context, server):
    page = await context.newPage()
    await page.goto(server.EMPTY_PAGE)
    await page.setContent('<a target=_blank rel=noopener href="/one-style.html">yo</a>')
    popup = (await asyncio.gather(page.waitForEvent("popup"), page.click("a")))[0]

    handled_popups = []
    page.on(
        "popup", lambda popup: handled_popups.append(True),
    )

    await popup.goto(server.CROSS_PROCESS_PREFIX + "/empty.html")
    assert len(handled_popups) == 0
