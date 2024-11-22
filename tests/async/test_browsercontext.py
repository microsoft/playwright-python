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
from typing import Any, List
from urllib.parse import urlparse

import pytest

from playwright.async_api import (
    Browser,
    BrowserContext,
    Error,
    JSHandle,
    Page,
    Playwright,
)
from tests.server import Server
from tests.utils import TARGET_CLOSED_ERROR_MESSAGE

from .utils import Utils


@pytest.fixture(scope="session")
def fails_on_401(browser_name: str, is_headless_shell: bool) -> bool:
    return browser_name == "chromium" and not is_headless_shell


async def test_page_event_should_create_new_context(browser: Browser) -> None:
    assert len(browser.contexts) == 0
    context = await browser.new_context()
    assert len(browser.contexts) == 1
    assert context in browser.contexts
    await context.close()
    assert len(browser.contexts) == 0
    assert context.browser == browser


async def test_window_open_should_use_parent_tab_context(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_popup() as page_info:
        await page.evaluate("url => window.open(url)", server.EMPTY_PAGE)
    popup = await page_info.value
    assert popup.context == context
    await context.close()


async def test_page_event_should_isolate_localStorage_and_cookies(
    browser: Browser, server: Server
) -> None:
    # Create two incognito contexts.
    context1 = await browser.new_context()
    context2 = await browser.new_context()
    assert len(context1.pages) == 0
    assert len(context2.pages) == 0

    # Create a page in first incognito context.
    page1 = await context1.new_page()
    await page1.goto(server.EMPTY_PAGE)
    await page1.evaluate(
        """() => {
            localStorage.setItem('name', 'page1')
            document.cookie = 'name=page1'
        }"""
    )

    assert len(context1.pages) == 1
    assert len(context2.pages) == 0

    # Create a page in second incognito context.
    page2 = await context2.new_page()
    await page2.goto(server.EMPTY_PAGE)
    await page2.evaluate(
        """() => {
            localStorage.setItem('name', 'page2')
            document.cookie = 'name=page2'
        }"""
    )

    assert len(context1.pages) == 1
    assert len(context2.pages) == 1
    assert context1.pages[0] == page1
    assert context2.pages[0] == page2

    # Make sure pages don't share localstorage or cookies.
    assert await page1.evaluate("localStorage.getItem('name')") == "page1"
    assert await page1.evaluate("document.cookie") == "name=page1"
    assert await page2.evaluate("localStorage.getItem('name')") == "page2"
    assert await page2.evaluate("document.cookie") == "name=page2"

    # Cleanup contexts.
    await asyncio.gather(context1.close(), context2.close())
    assert browser.contexts == []


async def test_page_event_should_propagate_default_viewport_to_the_page(
    browser: Browser, utils: Utils
) -> None:
    context = await browser.new_context(viewport={"width": 456, "height": 789})
    page = await context.new_page()
    await utils.verify_viewport(page, 456, 789)
    await context.close()


async def test_page_event_should_respect_device_scale_factor(browser: Browser) -> None:
    context = await browser.new_context(device_scale_factor=3)
    page = await context.new_page()
    assert await page.evaluate("window.devicePixelRatio") == 3
    await context.close()


async def test_page_event_should_not_allow_device_scale_factor_with_null_viewport(
    browser: Browser,
) -> None:
    with pytest.raises(Error) as exc_info:
        await browser.new_context(no_viewport=True, device_scale_factor=1)
    assert (
        exc_info.value.message
        == 'Browser.new_context: "deviceScaleFactor" option is not supported with null "viewport"'
    )


async def test_page_event_should_not_allow_is_mobile_with_null_viewport(
    browser: Browser,
) -> None:
    with pytest.raises(Error) as exc_info:
        await browser.new_context(no_viewport=True, is_mobile=True)
    assert (
        exc_info.value.message
        == 'Browser.new_context: "isMobile" option is not supported with null "viewport"'
    )


async def test_close_should_work_for_empty_context(browser: Browser) -> None:
    context = await browser.new_context()
    await context.close()


async def test_close_should_abort_wait_for_event(browser: Browser) -> None:
    context = await browser.new_context()
    with pytest.raises(Error) as exc_info:
        async with context.expect_page():
            await context.close()
    assert TARGET_CLOSED_ERROR_MESSAGE in exc_info.value.message


async def test_close_should_be_callable_twice(browser: Browser) -> None:
    context = await browser.new_context()
    await asyncio.gather(
        context.close(),
        context.close(),
    )
    await context.close()


async def test_user_agent_should_work(browser: Browser, server: Server) -> None:
    async def baseline() -> None:
        context = await browser.new_context()
        page = await context.new_page()
        assert "Mozilla" in await page.evaluate("navigator.userAgent")
        await context.close()

    await baseline()

    async def override() -> None:
        context = await browser.new_context(user_agent="foobar")
        page = await context.new_page()
        [request, _] = await asyncio.gather(
            server.wait_for_request("/empty.html"),
            page.goto(server.EMPTY_PAGE),
        )
        assert request.getHeader("user-agent") == "foobar"
        await context.close()

    await override()


async def test_user_agent_should_work_for_subframes(
    browser: Browser, server: Server, utils: Utils
) -> None:
    context = await browser.new_context(user_agent="foobar")
    page = await context.new_page()
    [request, _] = await asyncio.gather(
        server.wait_for_request("/empty.html"),
        utils.attach_frame(page, "frame1", server.EMPTY_PAGE),
    )
    assert request.getHeader("user-agent") == "foobar"
    await context.close()


async def test_user_agent_should_emulate_device_user_agent(
    playwright: Playwright, browser: Browser, server: Server
) -> None:
    context = await browser.new_context(
        user_agent=playwright.devices["iPhone 6"]["user_agent"]
    )
    page = await context.new_page()
    await page.goto(server.PREFIX + "/mobile.html")
    assert "iPhone" in await page.evaluate("navigator.userAgent")
    await context.close()


async def test_user_agent_should_make_a_copy_of_default_options(
    browser: Browser, server: Server
) -> None:
    options: Any = {"user_agent": "foobar"}
    context = await browser.new_context(**options)
    options["user_agent"] = "wrong"
    page = await context.new_page()
    [request, _] = await asyncio.gather(
        server.wait_for_request("/empty.html"),
        page.goto(server.EMPTY_PAGE),
    )
    assert request.getHeader("user-agent") == "foobar"
    await context.close()


async def test_page_event_should_bypass_csp_meta_tag(
    browser: Browser, server: Server
) -> None:
    async def baseline() -> None:
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(server.PREFIX + "/csp.html")
        try:
            await page.add_script_tag(content="window.__injected = 42;")
        except Error:
            pass
        assert await page.evaluate("window.__injected") is None
        await context.close()

    await baseline()

    # By-pass CSP and try one more time.
    async def override() -> None:
        context = await browser.new_context(bypass_csp=True)
        page = await context.new_page()
        await page.goto(server.PREFIX + "/csp.html")
        await page.add_script_tag(content="window.__injected = 42;")
        assert await page.evaluate("() => window.__injected") == 42
        await context.close()

    await override()


async def test_page_event_should_bypass_csp_header(
    browser: Browser, server: Server
) -> None:
    # Make sure CSP prohibits add_script_tag.
    server.set_csp("/empty.html", 'default-src "self"')

    async def baseline() -> None:
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(server.EMPTY_PAGE)
        try:
            await page.add_script_tag(content="window.__injected = 42;")
        except Error:
            pass
        assert await page.evaluate("() => window.__injected") is None
        await context.close()

    await baseline()

    # By-pass CSP and try one more time.
    async def override() -> None:
        context = await browser.new_context(bypass_csp=True)
        page = await context.new_page()
        await page.goto(server.EMPTY_PAGE)
        await page.add_script_tag(content="window.__injected = 42;")
        assert await page.evaluate("window.__injected") == 42
        await context.close()

    await override()


async def test_page_event_should_bypass_after_cross_process_navigation(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context(bypass_csp=True)
    page = await context.new_page()
    await page.goto(server.PREFIX + "/csp.html")
    await page.add_script_tag(content="window.__injected = 42;")
    assert await page.evaluate("window.__injected") == 42

    await page.goto(server.CROSS_PROCESS_PREFIX + "/csp.html")
    await page.add_script_tag(content="window.__injected = 42;")
    assert await page.evaluate("window.__injected") == 42
    await context.close()


async def test_page_event_should_bypass_csp_in_iframes_as_well(
    browser: Browser, server: Server, utils: Utils
) -> None:
    async def baseline() -> None:
        # Make sure CSP prohibits add_script_tag in an iframe.
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(server.EMPTY_PAGE)
        frame = await utils.attach_frame(page, "frame1", server.PREFIX + "/csp.html")
        try:
            await frame.add_script_tag(content="window.__injected = 42;")
        except Error:
            pass
        assert await frame.evaluate("window.__injected") is None
        await context.close()

    await baseline()

    # By-pass CSP and try one more time.
    async def override() -> None:
        context = await browser.new_context(bypass_csp=True)
        page = await context.new_page()
        await page.goto(server.EMPTY_PAGE)
        frame = await utils.attach_frame(page, "frame1", server.PREFIX + "/csp.html")
        try:
            await frame.add_script_tag(content="window.__injected = 42;")
        except Error:
            pass
        assert await frame.evaluate("window.__injected") == 42
        await context.close()

    await override()


async def test_csp_should_work(browser: Browser, is_webkit: bool) -> None:
    async def baseline() -> None:
        context = await browser.new_context(java_script_enabled=False)
        page = await context.new_page()
        await page.goto('data:text/html, <script>var something = "forbidden"</script>')
        with pytest.raises(Error) as exc_info:
            await page.evaluate("something")
            if is_webkit:
                assert "Can't find variable: something" in exc_info.value.message
            else:
                assert "something is not defined" in exc_info.value.message
        await context.close()

    await baseline()

    async def override() -> None:
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto('data:text/html, <script>var something = "forbidden"</script>')
        assert await page.evaluate("something") == "forbidden"
        await context.close()

    await override()


async def test_csp_should_be_able_to_navigate_after_disabling_javascript(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context(java_script_enabled=False)
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    await context.close()


async def test_pages_should_return_all_of_the_pages(
    context: BrowserContext, server: Server
) -> None:
    page = await context.new_page()
    second = await context.new_page()
    all_pages = context.pages
    assert len(all_pages) == 2
    assert page in all_pages
    assert second in all_pages


async def test_pages_should_close_all_belonging_pages_once_closing_context(
    context: BrowserContext,
) -> None:
    await context.new_page()
    assert len(context.pages) == 1
    await context.close()
    assert context.pages == []


async def test_expose_binding_should_work(context: BrowserContext) -> None:
    binding_source = []

    def binding(source: Any, a: int, b: int) -> int:
        binding_source.append(source)
        return a + b

    await context.expose_binding("add", lambda source, a, b: binding(source, a, b))

    page = await context.new_page()
    result = await page.evaluate("add(5, 6)")
    assert binding_source[0]["context"] == context
    assert binding_source[0]["page"] == page
    assert binding_source[0]["frame"] == page.main_frame
    assert result == 11


async def test_expose_function_should_work(context: BrowserContext) -> None:
    await context.expose_function("add", lambda a, b: a + b)
    page = await context.new_page()
    await page.expose_function("mul", lambda a, b: a * b)
    await context.expose_function("sub", lambda a, b: a - b)
    result = await page.evaluate(
        """async function() {
      return { mul: await mul(9, 4), add: await add(9, 4), sub: await sub(9, 4) }
    }"""
    )

    assert result == {"mul": 36, "add": 13, "sub": 5}


async def test_expose_function_should_throw_for_duplicate_registrations(
    context: BrowserContext, server: Server
) -> None:
    await context.expose_function("foo", lambda: None)
    await context.expose_function("bar", lambda: None)
    with pytest.raises(Error) as exc_info:
        await context.expose_function("foo", lambda: None)
    assert exc_info.value.message == 'Function "foo" has been already registered'
    page = await context.new_page()
    with pytest.raises(Error) as exc_info:
        await page.expose_function("foo", lambda: None)
    assert (
        exc_info.value.message
        == 'Function "foo" has been already registered in the browser context'
    )
    await page.expose_function("baz", lambda: None)
    with pytest.raises(Error) as exc_info:
        await context.expose_function("baz", lambda: None)
    assert (
        exc_info.value.message
        == 'Function "baz" has been already registered in one of the pages'
    )


async def test_expose_function_should_be_callable_from_inside_add_init_script(
    context: BrowserContext, server: Server
) -> None:
    args = []
    await context.expose_function("woof", lambda arg: args.append(arg))
    await context.add_init_script("woof('context')")
    page = await context.new_page()
    await page.evaluate("undefined")
    assert args == ["context"]
    args = []
    await page.add_init_script("woof('page')")
    await page.reload()
    assert args == ["context", "page"]


async def test_expose_bindinghandle_should_work(context: BrowserContext) -> None:
    targets: List[JSHandle] = []

    def logme(t: JSHandle) -> int:
        targets.append(t)
        return 17

    page = await context.new_page()
    await page.expose_binding("logme", lambda source, t: logme(t), handle=True)
    result = await page.evaluate("logme({ foo: 42 })")
    assert (await targets[0].evaluate("x => x.foo")) == 42
    assert result == 17


async def test_auth_should_fail_without_credentials(
    context: BrowserContext, server: Server, fails_on_401: bool
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    page = await context.new_page()
    try:
        response = await page.goto(server.EMPTY_PAGE)
        assert response
        assert response.status == 401
    except Error as exc:
        assert fails_on_401
        assert "net::ERR_INVALID_AUTH_CREDENTIALS" in exc.message


async def test_auth_should_work_with_correct_credentials(
    browser: Browser, server: Server
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    context = await browser.new_context(
        http_credentials={"username": "user", "password": "pass"}
    )
    page = await context.new_page()
    response = await page.goto(server.EMPTY_PAGE)
    assert response
    assert response.status == 200
    await context.close()


async def test_auth_should_fail_with_wrong_credentials(
    browser: Browser, server: Server
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    context = await browser.new_context(
        http_credentials={"username": "foo", "password": "bar"}
    )
    page = await context.new_page()
    response = await page.goto(server.EMPTY_PAGE)
    assert response
    assert response.status == 401
    await context.close()


async def test_auth_should_return_resource_body(
    browser: Browser, server: Server
) -> None:
    server.set_auth("/playground.html", "user", "pass")
    context = await browser.new_context(
        http_credentials={"username": "user", "password": "pass"}
    )
    page = await context.new_page()
    response = await page.goto(server.PREFIX + "/playground.html")
    assert response
    assert response.status == 200
    assert await page.title() == "Playground"
    assert "Playground" in await response.text()
    await context.close()


async def test_should_work_with_correct_credentials_and_matching_origin(
    browser: Browser, server: Server
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    context = await browser.new_context(
        http_credentials={
            "username": "user",
            "password": "pass",
            "origin": server.PREFIX,
        }
    )
    page = await context.new_page()
    response = await page.goto(server.EMPTY_PAGE)
    assert response
    assert response.status == 200
    await context.close()


async def test_should_work_with_correct_credentials_and_matching_origin_case_insensitive(
    browser: Browser, server: Server
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    context = await browser.new_context(
        http_credentials={
            "username": "user",
            "password": "pass",
            "origin": server.PREFIX.upper(),
        }
    )
    page = await context.new_page()
    response = await page.goto(server.EMPTY_PAGE)
    assert response
    assert response.status == 200
    await context.close()


async def test_should_fail_with_correct_credentials_and_mismatching_scheme(
    browser: Browser, server: Server, fails_on_401: bool
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    context = await browser.new_context(
        http_credentials={
            "username": "user",
            "password": "pass",
            "origin": server.PREFIX.replace("http://", "https://"),
        }
    )
    page = await context.new_page()
    try:
        response = await page.goto(server.EMPTY_PAGE)
        assert response
        assert response.status == 401
    except Error as exc:
        assert fails_on_401
        assert "net::ERR_INVALID_AUTH_CREDENTIALS" in exc.message
    await context.close()


async def test_should_fail_with_correct_credentials_and_mismatching_hostname(
    browser: Browser, server: Server, fails_on_401: bool
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    hostname = urlparse(server.PREFIX).hostname
    assert hostname
    origin = server.PREFIX.replace(hostname, "mismatching-hostname")
    context = await browser.new_context(
        http_credentials={"username": "user", "password": "pass", "origin": origin}
    )
    page = await context.new_page()
    try:
        response = await page.goto(server.EMPTY_PAGE)
        assert response
        assert response.status == 401
    except Error as exc:
        assert fails_on_401
        assert "net::ERR_INVALID_AUTH_CREDENTIALS" in exc.message
    await context.close()


async def test_should_fail_with_correct_credentials_and_mismatching_port(
    browser: Browser, server: Server, fails_on_401: bool
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    origin = server.PREFIX.replace(str(server.PORT), str(server.PORT + 1))
    context = await browser.new_context(
        http_credentials={"username": "user", "password": "pass", "origin": origin}
    )
    page = await context.new_page()
    try:
        response = await page.goto(server.EMPTY_PAGE)
        assert response
        assert response.status == 401
    except Error as exc:
        assert fails_on_401
        assert "net::ERR_INVALID_AUTH_CREDENTIALS" in exc.message
    await context.close()


async def test_offline_should_work_with_initial_option(
    browser: Browser,
    server: Server,
    browser_name: str,
) -> None:
    context = await browser.new_context(offline=True)
    page = await context.new_page()
    frame_navigated_task = asyncio.create_task(page.wait_for_event("framenavigated"))
    with pytest.raises(Error) as exc_info:
        await page.goto(server.EMPTY_PAGE)
    if browser_name == "firefox":
        await frame_navigated_task
    assert exc_info.value
    await context.set_offline(False)
    response = await page.goto(server.EMPTY_PAGE)
    assert response
    assert response.status == 200
    await context.close()


async def test_offline_should_emulate_navigator_online(
    context: BrowserContext, server: Server
) -> None:
    page = await context.new_page()
    assert await page.evaluate("window.navigator.onLine")
    await context.set_offline(True)
    assert await page.evaluate("window.navigator.onLine") is False
    await context.set_offline(False)
    assert await page.evaluate("window.navigator.onLine")


async def test_page_event_should_have_url(
    context: BrowserContext, server: Server
) -> None:
    page = await context.new_page()
    async with context.expect_page() as other_page_info:
        await page.evaluate("url => window.open(url)", server.EMPTY_PAGE)
    other_page = await other_page_info.value
    assert other_page.url == server.EMPTY_PAGE


async def test_page_event_should_have_url_after_domcontentloaded(
    context: BrowserContext, server: Server
) -> None:
    page = await context.new_page()
    async with context.expect_page() as other_page_info:
        await page.evaluate("url => window.open(url)", server.EMPTY_PAGE)
    other_page = await other_page_info.value
    await other_page.wait_for_load_state("domcontentloaded")
    assert other_page.url == server.EMPTY_PAGE


async def test_page_event_should_have_about_blank_url_with_domcontentloaded(
    context: BrowserContext, server: Server
) -> None:
    page = await context.new_page()
    async with context.expect_page() as other_page_info:
        await page.evaluate("url => window.open(url)", "about:blank")
    other_page = await other_page_info.value
    await other_page.wait_for_load_state("domcontentloaded")
    assert other_page.url == "about:blank"


async def test_page_event_should_have_about_blank_for_empty_url_with_domcontentloaded(
    context: BrowserContext, server: Server
) -> None:
    page = await context.new_page()
    async with context.expect_page() as other_page_info:
        await page.evaluate("window.open()")
    other_page = await other_page_info.value
    await other_page.wait_for_load_state("domcontentloaded")
    assert other_page.url == "about:blank"


async def test_page_event_should_report_when_a_new_page_is_created_and_closed(
    context: BrowserContext, server: Server
) -> None:
    page = await context.new_page()
    async with context.expect_page() as page_info:
        await page.evaluate(
            "url => window.open(url)", server.CROSS_PROCESS_PREFIX + "/empty.html"
        )
    other_page = await page_info.value

    # The url is about:blank in FF when 'page' event is fired.
    assert server.CROSS_PROCESS_PREFIX in other_page.url
    assert await other_page.evaluate("['Hello', 'world'].join(' ')") == "Hello world"
    assert await other_page.query_selector("body")

    all_pages = context.pages
    assert page in all_pages
    assert other_page in all_pages

    close_event_received = []
    other_page.once("close", lambda _: close_event_received.append(True))
    await other_page.close()
    assert close_event_received == [True]

    all_pages = context.pages
    assert page in all_pages
    assert other_page not in all_pages


async def test_page_event_should_report_initialized_pages(
    context: BrowserContext, server: Server
) -> None:
    async with context.expect_page() as page_info:
        await context.new_page()
    new_page = await page_info.value
    assert new_page.url == "about:blank"

    async with context.expect_page() as popup_info:
        await new_page.evaluate("window.open('about:blank')")
    popup = await popup_info.value
    assert popup.url == "about:blank"


async def test_page_event_should_have_an_opener(
    context: BrowserContext, server: Server
) -> None:
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    async with context.expect_page() as page_info:
        await page.goto(server.PREFIX + "/popup/window-open.html")
    popup = await page_info.value
    assert popup.url == server.PREFIX + "/popup/popup.html"
    assert await popup.opener() == page
    assert await page.opener() is None


async def test_page_event_should_fire_page_lifecycle_events(
    context: BrowserContext, server: Server
) -> None:
    events: List[str] = []

    def handle_page(page: Page) -> None:
        events.append("CREATED: " + page.url)
        page.on("close", lambda _: events.append("DESTROYED: " + page.url))

    context.on("page", handle_page)

    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    await page.close()
    assert events == ["CREATED: about:blank", f"DESTROYED: {server.EMPTY_PAGE}"]


@pytest.mark.skip_browser("webkit")
async def test_page_event_should_work_with_shift_clicking(
    context: BrowserContext, server: Server
) -> None:
    # WebKit: Shift+Click does not open a new window.
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    await page.set_content('<a href="/one-style.html">yo</a>')
    async with context.expect_page() as page_info:
        await page.click("a", modifiers=["Shift"])
    popup = await page_info.value
    assert await popup.opener() is None


@pytest.mark.only_browser("chromium")
async def test_page_event_should_work_with_ctrl_clicking(
    context: BrowserContext, server: Server
) -> None:
    # Firefox: reports an opener in this case.
    # WebKit: Ctrl+Click does not open a new tab.
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    await page.set_content('<a href="/one-style.html">yo</a>')
    async with context.expect_page() as popup_info:
        await page.click("a", modifiers=["ControlOrMeta"])
    popup = await popup_info.value
    assert await popup.opener() is None


async def test_strict_selectors_on_context(browser: Browser, server: Server) -> None:
    context = await browser.new_context(strict_selectors=True)
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        """
        <button>Hello</button>
        <button>Hello</button>
    """
    )
    with pytest.raises(Error):
        await page.text_content("button")
    with pytest.raises(Error):
        await page.query_selector("button")
    await context.close()


@pytest.mark.skip_browser("webkit")  # https://bugs.webkit.org/show_bug.cgi?id=225281
async def test_should_support_forced_colors(browser: Browser) -> None:
    context = await browser.new_context(forced_colors="active")
    page = await context.new_page()
    assert await page.evaluate("matchMedia('(forced-colors: active)').matches")
    assert not await page.evaluate("matchMedia('(forced-colors: none)').matches")
