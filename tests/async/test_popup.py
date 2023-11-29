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
from typing import List, Optional

from playwright.async_api import Browser, BrowserContext, Request, Route
from tests.server import Server
from tests.utils import must


async def test_link_navigation_inherit_user_agent_from_browser_context(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context(user_agent="hey")

    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        '<a target=_blank rel=noopener href="/popup/popup.html">link</a>'
    )
    request_waitable = asyncio.create_task(server.wait_for_request("/popup/popup.html"))
    await asyncio.sleep(0)  # execute scheduled tasks, but don't await them
    async with context.expect_page() as page_info:
        await page.click("a")
    popup = await page_info.value
    await popup.wait_for_load_state("domcontentloaded")
    user_agent = await popup.evaluate("window.initialUserAgent")
    request = await request_waitable
    assert user_agent == "hey"
    assert request.requestHeaders.getRawHeaders("user-agent") == ["hey"]
    await context.close()


async def test_link_navigation_respect_routes_from_browser_context(
    context: BrowserContext, server: Server
) -> None:
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    await page.set_content('<a target=_blank rel=noopener href="empty.html">link</a>')

    intercepted: List[bool] = []

    async def handle_request(route: Route) -> None:
        intercepted.append(True)
        await route.continue_()

    await context.route("**/empty.html", handle_request)
    async with context.expect_page():
        await page.click("a")
    assert intercepted == [True]


async def test_window_open_inherit_user_agent_from_browser_context(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context(user_agent="hey")

    page = await context.new_page()
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
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context(extra_http_headers={"foo": "bar"})

    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    request_promise = asyncio.create_task(server.wait_for_request("/dummy.html"))
    await asyncio.sleep(0)  # execute scheduled tasks, but don't await them
    await page.evaluate(
        "url => window._popup = window.open(url)", server.PREFIX + "/dummy.html"
    )
    request = await request_promise
    assert request.requestHeaders.getRawHeaders("foo") == ["bar"]
    await context.close()


async def test_should_inherit_offline_from_browser_context(
    context: BrowserContext, server: Server
) -> None:
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    await context.set_offline(True)
    online = await page.evaluate(
        """url => {
            win = window.open(url)
            return win.navigator.onLine
        }""",
        server.PREFIX + "/dummy.html",
    )
    assert online is False


async def test_should_inherit_http_credentials_from_browser_context(
    browser: Browser, server: Server
) -> None:
    server.set_auth("/title.html", "user", "pass")
    context = await browser.new_context(
        http_credentials={"username": "user", "password": "pass"}
    )
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_popup() as popup_info:
        await page.evaluate(
            "url => window._popup = window.open(url)", server.PREFIX + "/title.html"
        )
    popup = await popup_info.value
    await popup.wait_for_load_state("domcontentloaded")
    assert await popup.title() == "Woof-Woof"
    await context.close()


async def test_should_inherit_touch_support_from_browser_context(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context(
        viewport={"width": 400, "height": 500}, has_touch=True
    )

    page = await context.new_page()
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
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context(viewport={"width": 400, "height": 500})

    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    size = await page.evaluate(
        """() => {
            win = window.open('about:blank')
            return { width: win.innerWidth, height: win.innerHeight }
        }"""
    )

    assert size == {"width": 400, "height": 500}
    await context.close()


async def test_should_use_viewport_size_from_window_features(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context(viewport={"width": 700, "height": 700})
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    size = None
    async with page.expect_popup() as popup_info:
        size = await page.evaluate(
            """async () => {
                const win = window.open(window.location.href, 'Title', 'toolbar=no,location=no,directories=no,status=no,menubar=no,scrollbars=yes,resizable=yes,width=600,height=300,top=0,left=0');
                await new Promise(resolve => {
                    const interval = setInterval(() => {
                    if (win.innerWidth === 600 && win.innerHeight === 300) {
                        clearInterval(interval);
                        resolve();
                    }
                    }, 10);
                });
                return { width: win.innerWidth, height: win.innerHeight }
            }"""
        )
    popup = await popup_info.value
    await popup.set_viewport_size({"width": 500, "height": 400})
    await popup.wait_for_load_state()
    resized = await popup.evaluate(
        "() => ({ width: window.innerWidth, height: window.innerHeight })"
    )
    await context.close()
    assert size == {"width": 600, "height": 300}
    assert resized == {"width": 500, "height": 400}


async def test_should_respect_routes_from_browser_context(
    context: BrowserContext, server: Server
) -> None:
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)

    def handle_request(route: Route, request: Request, intercepted: List[bool]) -> None:
        asyncio.create_task(route.continue_())
        intercepted.append(True)

    intercepted: List[bool] = []
    await context.route(
        "**/empty.html",
        lambda route, request: handle_request(route, request, intercepted),
    )

    async with page.expect_popup():
        await page.evaluate(
            "url => window.__popup = window.open(url)", server.EMPTY_PAGE
        )
    assert len(intercepted) == 1


async def test_browser_context_add_init_script_should_apply_to_an_in_process_popup(
    context: BrowserContext, server: Server
) -> None:
    await context.add_init_script("window.injected = 123")
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    injected = await page.evaluate(
        """() => {
            const win = window.open('about:blank');
            return win.injected;
        }"""
    )

    assert injected == 123


async def test_browser_context_add_init_script_should_apply_to_a_cross_process_popup(
    context: BrowserContext, server: Server
) -> None:
    await context.add_init_script("window.injected = 123")
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_popup() as popup_info:
        await page.evaluate(
            "url => window.open(url)", server.CROSS_PROCESS_PREFIX + "/title.html"
        )
    popup = await popup_info.value
    assert await popup.evaluate("injected") == 123
    await popup.reload()
    assert await popup.evaluate("injected") == 123


async def test_should_expose_function_from_browser_context(
    context: BrowserContext, server: Server
) -> None:
    await context.expose_function("add", lambda a, b: a + b)
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    added = await page.evaluate(
        """async () => {
            win = window.open('about:blank')
            return win.add(9, 4)
        }"""
    )

    assert added == 13


async def test_should_work(context: BrowserContext) -> None:
    page = await context.new_page()
    async with page.expect_popup() as popup_info:
        await page.evaluate('window.__popup = window.open("about:blank")')
    popup = await popup_info.value
    assert await page.evaluate("!!window.opener") is False
    assert await popup.evaluate("!!window.opener")


async def test_should_work_with_window_features(
    context: BrowserContext, server: Server
) -> None:
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_popup() as popup_info:
        await page.evaluate(
            'window.__popup = window.open(window.location.href, "Title", "toolbar=no,location=no,directories=no,status=no,menubar=no,scrollbars=yes,resizable=yes,width=780,height=200,top=0,left=0")'
        )
    popup = await popup_info.value
    assert await page.evaluate("!!window.opener") is False
    assert await popup.evaluate("!!window.opener")


async def test_window_open_emit_for_immediately_closed_popups(
    context: BrowserContext,
) -> None:
    page = await context.new_page()
    async with page.expect_popup() as popup_info:
        await page.evaluate(
            """() => {
                win = window.open('about:blank')
                win.close()
            }"""
        )
    popup = await popup_info.value
    assert popup


async def test_should_emit_for_immediately_closed_popups(
    context: BrowserContext, server: Server
) -> None:
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_popup() as popup_info:
        await page.evaluate(
            """() => {
                win = window.open(window.location.href)
                win.close()
            }"""
        )
    popup = await popup_info.value
    assert popup


async def test_should_be_able_to_capture_alert(context: BrowserContext) -> None:
    page = await context.new_page()
    evaluate_task: Optional[asyncio.Future] = None

    async def evaluate() -> None:
        nonlocal evaluate_task
        evaluate_task = asyncio.create_task(
            page.evaluate(
                """() => {
                const win = window.open('')
                win.alert('hello')
            }"""
            )
        )

    [popup, dialog, _] = await asyncio.gather(
        page.wait_for_event("popup"), context.wait_for_event("dialog"), evaluate()
    )

    assert dialog.message == "hello"
    assert dialog.page == popup
    await dialog.dismiss()
    await must(evaluate_task)


async def test_should_work_with_empty_url(context: BrowserContext) -> None:
    page = await context.new_page()
    async with page.expect_popup() as popup_info:
        await page.evaluate("() => window.__popup = window.open('')")
    popup = await popup_info.value
    assert await page.evaluate("!!window.opener") is False
    assert await popup.evaluate("!!window.opener")


async def test_should_work_with_noopener_and_no_url(context: BrowserContext) -> None:
    page = await context.new_page()
    async with page.expect_popup() as popup_info:
        await page.evaluate(
            '() => window.__popup = window.open(undefined, null, "noopener")'
        )
    popup = await popup_info.value
    # Chromium reports 'about:blank#blocked' here.
    assert popup.url.split("#")[0] == "about:blank"
    assert await page.evaluate("!!window.opener") is False
    assert await popup.evaluate("!!window.opener") is False


async def test_should_work_with_noopener_and_about_blank(
    context: BrowserContext,
) -> None:
    page = await context.new_page()
    async with page.expect_popup() as popup_info:
        await page.evaluate(
            '() => window.__popup = window.open("about:blank", null, "noopener")'
        )
    popup = await popup_info.value
    assert await page.evaluate("!!window.opener") is False
    assert await popup.evaluate("!!window.opener") is False


async def test_should_work_with_noopener_and_url(
    context: BrowserContext, server: Server
) -> None:
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_popup() as popup_info:
        await page.evaluate(
            'url => window.__popup = window.open(url, null, "noopener")',
            server.EMPTY_PAGE,
        )
    popup = await popup_info.value
    assert await page.evaluate("!!window.opener") is False
    assert await popup.evaluate("!!window.opener") is False


async def test_should_work_with_clicking_target__blank(
    context: BrowserContext, server: Server
) -> None:
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        '<a target=_blank rel="opener" href="/one-style.html">yo</a>'
    )
    async with page.expect_popup() as popup_info:
        await page.click("a")
    popup = await popup_info.value
    assert await page.evaluate("!!window.opener") is False
    assert await popup.evaluate("!!window.opener")
    assert popup.main_frame.page == popup


async def test_should_work_with_fake_clicking_target__blank_and_rel_noopener(
    context: BrowserContext, server: Server
) -> None:
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        '<a target=_blank rel=noopener href="/one-style.html">yo</a>'
    )
    async with page.expect_popup() as popup_info:
        await page.eval_on_selector("a", "a => a.click()")
    popup = await popup_info.value
    assert await page.evaluate("!!window.opener") is False
    assert await popup.evaluate("!!window.opener") is False


async def test_should_work_with_clicking_target__blank_and_rel_noopener(
    context: BrowserContext, server: Server
) -> None:
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        '<a target=_blank rel=noopener href="/one-style.html">yo</a>'
    )
    async with page.expect_popup() as popup_info:
        await page.click("a")
    popup = await popup_info.value
    assert await page.evaluate("!!window.opener") is False
    assert await popup.evaluate("!!window.opener") is False


async def test_should_not_treat_navigations_as_new_popups(
    context: BrowserContext, server: Server
) -> None:
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        '<a target=_blank rel=noopener href="/one-style.html">yo</a>'
    )
    async with page.expect_popup() as popup_info:
        await page.click("a")
    popup = await popup_info.value
    handled_popups = []
    page.on(
        "popup",
        lambda popup: handled_popups.append(True),
    )

    await popup.goto(server.CROSS_PROCESS_PREFIX + "/empty.html")
    assert len(handled_popups) == 0
