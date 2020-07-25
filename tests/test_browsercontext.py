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

import pytest

from playwright import Error, devices


async def test_page_event_should_create_new_context(browser):
    assert len(browser.contexts) == 0
    context = await browser.newContext()
    assert len(browser.contexts) == 1
    assert context in browser.contexts
    await context.close()
    assert len(browser.contexts) == 0


async def test_window_open_should_use_parent_tab_context(browser, server):
    context = await browser.newContext()
    page = await context.newPage()
    await page.goto(server.EMPTY_PAGE)
    [popup, _] = await asyncio.gather(
        page.waitForEvent("popup"),
        page.evaluate("url => window.open(url)", server.EMPTY_PAGE),
    )
    assert popup.context == context
    await context.close()


async def test_page_event_should_isolate_localStorage_and_cookies(browser, server):
    # Create two incognito contexts.
    context1 = await browser.newContext()
    context2 = await browser.newContext()
    assert len(context1.pages) == 0
    assert len(context2.pages) == 0

    # Create a page in first incognito context.
    page1 = await context1.newPage()
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
    page2 = await context2.newPage()
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


async def test_page_event_should_propagate_default_viewport_to_the_page(browser, utils):
    context = await browser.newContext(viewport={"width": 456, "height": 789})
    page = await context.newPage()
    await utils.verify_viewport(page, 456, 789)
    await context.close()


async def test_page_event_should_make_a_copy_of_default_viewport(browser, utils):
    viewport = {"width": 456, "height": 789}
    context = await browser.newContext(viewport=viewport)
    viewport["width"] = 567
    page = await context.newPage()
    await utils.verify_viewport(page, 456, 789)
    await context.close()


async def test_page_event_should_respect_deviceScaleFactor(browser):
    context = await browser.newContext(deviceScaleFactor=3)
    page = await context.newPage()
    assert await page.evaluate("window.devicePixelRatio") == 3
    await context.close()


async def test_page_event_should_not_allow_deviceScaleFactor_with_null_viewport(
    browser,
):
    with pytest.raises(Error) as exc_info:
        await browser.newContext(viewport=0, deviceScaleFactor=1)
    assert (
        exc_info.value.message
        == '"deviceScaleFactor" option is not supported with null "viewport"'
    )


async def test_page_event_should_not_allow_isMobile_with_null_viewport(browser):
    with pytest.raises(Error) as exc_info:
        await browser.newContext(viewport=0, isMobile=True)
    assert (
        exc_info.value.message
        == '"isMobile" option is not supported with null "viewport"'
    )


async def test_close_should_work_for_empty_context(browser):
    context = await browser.newContext()
    await context.close()


async def test_close_should_abort_wait_for_event(browser):
    context = await browser.newContext()
    promise = asyncio.create_task(context.waitForEvent("page"))
    await context.close()
    with pytest.raises(Error) as exc_info:
        await promise
    assert "Context closed" in exc_info.value.message


async def test_close_should_be_callable_twice(browser):
    context = await browser.newContext()
    await asyncio.gather(
        context.close(), context.close(),
    )
    await context.close()


async def test_user_agent_should_work(browser, server):
    async def baseline():
        context = await browser.newContext()
        page = await context.newPage()
        assert "Mozilla" in await page.evaluate("navigator.userAgent")
        await context.close()

    await baseline()

    async def override():
        context = await browser.newContext(userAgent="foobar")
        page = await context.newPage()
        [request, _] = await asyncio.gather(
            server.wait_for_request("/empty.html"), page.goto(server.EMPTY_PAGE),
        )
        assert request.getHeader("user-agent") == "foobar"
        await context.close()

    await override()


async def test_user_agent_should_work_for_subframes(browser, server, utils):
    context = await browser.newContext(userAgent="foobar")
    page = await context.newPage()
    [request, _] = await asyncio.gather(
        server.wait_for_request("/empty.html"),
        utils.attach_frame(page, "frame1", server.EMPTY_PAGE),
    )
    assert request.getHeader("user-agent") == "foobar"
    await context.close()


async def test_user_agent_should_emulate_device_user_agent(browser, server):
    context = await browser.newContext(userAgent=devices["iPhone 6"]["userAgent"])
    page = await context.newPage()
    await page.goto(server.PREFIX + "/mobile.html")
    assert "iPhone" in await page.evaluate("navigator.userAgent")
    await context.close()


async def test_user_agent_should_make_a_copy_of_default_options(browser, server):
    options = {"userAgent": "foobar"}
    context = await browser.newContext(**options)
    options["userAgent"] = "wrong"
    page = await context.newPage()
    [request, _] = await asyncio.gather(
        server.wait_for_request("/empty.html"), page.goto(server.EMPTY_PAGE),
    )
    assert request.getHeader("user-agent") == "foobar"
    await context.close()


async def test_page_event_should_bypass_csp_meta_tag(browser, server):
    async def baseline():
        context = await browser.newContext()
        page = await context.newPage()
        await page.goto(server.PREFIX + "/csp.html")
        try:
            await page.addScriptTag(content="window.__injected = 42;")
        except Error:
            pass
        assert await page.evaluate("window.__injected") is None
        await context.close()

    await baseline()

    # By-pass CSP and try one more time.
    async def override():
        context = await browser.newContext(bypassCSP=True)
        page = await context.newPage()
        await page.goto(server.PREFIX + "/csp.html")
        await page.addScriptTag(content="window.__injected = 42;")
        assert await page.evaluate("() => window.__injected") == 42
        await context.close()

    await override()


async def test_page_event_should_bypass_csp_header(browser, server):
    # Make sure CSP prohibits addScriptTag.
    server.set_csp("/empty.html", 'default-src "self"')

    async def baseline():
        context = await browser.newContext()
        page = await context.newPage()
        await page.goto(server.EMPTY_PAGE)
        try:
            await page.addScriptTag(content="window.__injected = 42;")
        except Error:
            pass
        assert await page.evaluate("() => window.__injected") is None
        await context.close()

    await baseline()

    # By-pass CSP and try one more time.
    async def override():
        context = await browser.newContext(bypassCSP=True)
        page = await context.newPage()
        await page.goto(server.EMPTY_PAGE)
        await page.addScriptTag(content="window.__injected = 42;")
        assert await page.evaluate("window.__injected") == 42
        await context.close()

    await override()


async def test_page_event_should_bypass_after_cross_process_navigation(browser, server):
    context = await browser.newContext(bypassCSP=True)
    page = await context.newPage()
    await page.goto(server.PREFIX + "/csp.html")
    await page.addScriptTag(content="window.__injected = 42;")
    assert await page.evaluate("window.__injected") == 42

    await page.goto(server.CROSS_PROCESS_PREFIX + "/csp.html")
    await page.addScriptTag(content="window.__injected = 42;")
    assert await page.evaluate("window.__injected") == 42
    await context.close()


async def test_page_event_should_bypass_csp_in_iframes_as_well(browser, server, utils):
    async def baseline():
        # Make sure CSP prohibits addScriptTag in an iframe.
        context = await browser.newContext()
        page = await context.newPage()
        await page.goto(server.EMPTY_PAGE)
        frame = await utils.attach_frame(page, "frame1", server.PREFIX + "/csp.html")
        try:
            await frame.addScriptTag(content="window.__injected = 42;")
        except Error:
            pass
        assert await frame.evaluate("window.__injected") is None
        await context.close()

    await baseline()

    # By-pass CSP and try one more time.
    async def override():
        context = await browser.newContext(bypassCSP=True)
        page = await context.newPage()
        await page.goto(server.EMPTY_PAGE)
        frame = await utils.attach_frame(page, "frame1", server.PREFIX + "/csp.html")
        try:
            await frame.addScriptTag(content="window.__injected = 42;")
        except Error:
            pass
        assert await frame.evaluate("window.__injected") == 42
        await context.close()

    await override()


async def test_csp_should_work(browser, is_webkit):
    async def baseline():
        context = await browser.newContext(javaScriptEnabled=False)
        page = await context.newPage()
        await page.goto('data:text/html, <script>var something = "forbidden"</script>')
        with pytest.raises(Error) as exc_info:
            await page.evaluate("something")
            if is_webkit:
                assert "Can't find variable: something" in exc_info.value.message
            else:
                assert "something is not defined" in exc_info.value.message
        await context.close()

    await baseline()

    async def override():
        context = await browser.newContext()
        page = await context.newPage()
        await page.goto('data:text/html, <script>var something = "forbidden"</script>')
        assert await page.evaluate("something") == "forbidden"
        await context.close()

    await override()


async def test_csp_should_be_able_to_navigate_after_disabling_javascript(
    browser, server
):
    context = await browser.newContext(javaScriptEnabled=False)
    page = await context.newPage()
    await page.goto(server.EMPTY_PAGE)
    await context.close()


async def test_pages_should_return_all_of_the_pages(context, server):
    page = await context.newPage()
    second = await context.newPage()
    all_pages = context.pages
    assert len(all_pages) == 2
    assert page in all_pages
    assert second in all_pages


async def test_pages_should_close_all_belonging_pages_once_closing_context(context):
    await context.newPage()
    assert len(context.pages) == 1
    await context.close()
    assert context.pages == []


async def test_expose_binding_should_work(context):
    binding_source = []

    def binding(source, a, b):
        binding_source.append(source)
        return a + b

    await context.exposeBinding("add", lambda source, a, b: binding(source, a, b))

    page = await context.newPage()
    result = await page.evaluate("add(5, 6)")
    assert binding_source[0]["context"] == context
    assert binding_source[0]["page"] == page
    assert binding_source[0]["frame"] == page.mainFrame
    assert result == 11


async def test_expose_function_should_work(context):
    await context.exposeFunction("add", lambda a, b: a + b)
    page = await context.newPage()
    await page.exposeFunction("mul", lambda a, b: a * b)
    await context.exposeFunction("sub", lambda a, b: a - b)
    result = await page.evaluate(
        """async function() {
      return { mul: await mul(9, 4), add: await add(9, 4), sub: await sub(9, 4) }
    }"""
    )

    assert result == {"mul": 36, "add": 13, "sub": 5}


async def test_expose_function_should_throw_for_duplicate_registrations(
    context, server
):
    await context.exposeFunction("foo", lambda: None)
    await context.exposeFunction("bar", lambda: None)
    with pytest.raises(Error) as exc_info:
        await context.exposeFunction("foo", lambda: None)
    assert exc_info.value.message == 'Function "foo" has been already registered'
    page = await context.newPage()
    with pytest.raises(Error) as exc_info:
        await page.exposeFunction("foo", lambda: None)
    assert (
        exc_info.value.message
        == 'Function "foo" has been already registered in the browser context'
    )
    await page.exposeFunction("baz", lambda: None)
    with pytest.raises(Error) as exc_info:
        await context.exposeFunction("baz", lambda: None)
    assert (
        exc_info.value.message
        == 'Function "baz" has been already registered in one of the pages'
    )


async def test_expose_function_should_be_callable_from_inside_addInitScript(
    context, server
):
    args = []
    await context.exposeFunction("woof", lambda arg: args.append(arg))
    await context.addInitScript("woof('context')")
    page = await context.newPage()
    await page.addInitScript("woof('page')")
    args = []
    await page.reload()
    assert args == ["context", "page"]


async def test_route_should_intercept(context, server):
    intercepted = []

    def handle(route, request):
        intercepted.append(True)
        assert "empty.html" in request.url
        assert request.headers["user-agent"]
        assert request.method == "GET"
        assert request.postData is None
        assert request.isNavigationRequest()
        assert request.resourceType == "document"
        assert request.frame == page.mainFrame
        assert request.frame.url == "about:blank"
        asyncio.create_task(route.continue_())

    await context.route("**/empty.html", lambda route, request: handle(route, request))
    page = await context.newPage()
    response = await page.goto(server.EMPTY_PAGE)
    assert response.ok
    assert intercepted == [True]
    await context.close()


async def test_route_should_unroute(context, server):
    page = await context.newPage()

    intercepted = []

    def handler(route, request, ordinal):
        intercepted.append(ordinal)
        asyncio.create_task(route.continue_())

    def handler1(route, request):
        handler(route, request, 1)

    await context.route("**/empty.html", handler1)
    await context.route(
        "**/empty.html", lambda route, request: handler(route, request, 2)
    )
    await context.route(
        "**/empty.html", lambda route, request: handler(route, request, 3)
    )
    await context.route("**/*", lambda route, request: handler(route, request, 4))

    await page.goto(server.EMPTY_PAGE)
    assert intercepted == [1]

    intercepted = []
    await context.unroute("**/empty.html", handler1)
    await page.goto(server.EMPTY_PAGE)
    assert intercepted == [2]

    intercepted = []
    await context.unroute("**/empty.html")
    await page.goto(server.EMPTY_PAGE)
    assert intercepted == [4]


async def test_route_should_yield_to_page_route(context, server):
    await context.route(
        "**/empty.html",
        lambda route, request: asyncio.create_task(
            route.fulfill(status=200, body="context")
        ),
    )

    page = await context.newPage()
    await page.route(
        "**/empty.html",
        lambda route, request: asyncio.create_task(
            route.fulfill(status=200, body="page")
        ),
    )

    response = await page.goto(server.EMPTY_PAGE)
    assert response.ok
    assert await response.text() == "page"


async def test_route_should_fall_back_to_context_route(context, server):
    await context.route(
        "**/empty.html",
        lambda route, request: asyncio.create_task(
            route.fulfill(status=200, body="context")
        ),
    )

    page = await context.newPage()
    await page.route(
        "**/non-empty.html",
        lambda route, request: asyncio.create_task(
            route.fulfill(status=200, body="page")
        ),
    )

    response = await page.goto(server.EMPTY_PAGE)
    assert response.ok
    assert await response.text() == "context"


async def test_auth_should_fail_without_credentials(context, server):
    server.set_auth("/empty.html", b"user", b"pass")
    page = await context.newPage()
    response = await page.goto(server.EMPTY_PAGE)
    assert response.status == 401


async def test_auth_should_work_with_correct_credentials(browser, server):
    server.set_auth("/empty.html", b"user", b"pass")
    context = await browser.newContext(
        httpCredentials={"username": "user", "password": "pass"}
    )
    page = await context.newPage()
    response = await page.goto(server.EMPTY_PAGE)
    assert response.status == 200
    await context.close()


async def test_auth_should_fail_with_wrong_credentials(browser, server):
    server.set_auth("/empty.html", b"user", b"pass")
    context = await browser.newContext(
        httpCredentials={"username": "foo", "password": "bar"}
    )
    page = await context.newPage()
    response = await page.goto(server.EMPTY_PAGE)
    assert response.status == 401
    await context.close()


async def test_auth_should_return_resource_body(browser, server):
    server.set_auth("/playground.html", b"user", b"pass")
    context = await browser.newContext(
        httpCredentials={"username": "user", "password": "pass"}
    )
    page = await context.newPage()
    response = await page.goto(server.PREFIX + "/playground.html")
    assert response.status == 200
    assert await page.title() == "Playground"
    assert "Playground" in await response.text()
    await context.close()


async def test_offline_should_work_with_initial_option(browser, server):
    context = await browser.newContext(offline=True)
    page = await context.newPage()
    with pytest.raises(Error) as exc_info:
        await page.goto(server.EMPTY_PAGE)
    assert exc_info.value
    await context.setOffline(False)
    response = await page.goto(server.EMPTY_PAGE)
    assert response.status == 200
    await context.close()


async def test_offline_should_emulate_navigator_online(context, server):
    page = await context.newPage()
    assert await page.evaluate("window.navigator.onLine")
    await context.setOffline(True)
    assert await page.evaluate("window.navigator.onLine") is False
    await context.setOffline(False)
    assert await page.evaluate("window.navigator.onLine")


async def test_page_event_should_have_url(context, server):
    page = await context.newPage()
    async with context.expect_page() as other_page_info:
        await page.evaluate("url => window.open(url)", server.EMPTY_PAGE)
    other_page = await other_page_info.value
    assert other_page.url == server.EMPTY_PAGE


async def test_page_event_should_have_url_after_domcontentloaded(context, server):
    page = await context.newPage()
    async with context.expect_page() as other_page_info:
        await page.evaluate("url => window.open(url)", server.EMPTY_PAGE)
    other_page = await other_page_info.value
    await other_page.waitForLoadState("domcontentloaded")
    assert other_page.url == server.EMPTY_PAGE


async def test_page_event_should_have_about_blank_url_with_domcontentloaded(
    context, server
):
    page = await context.newPage()
    async with context.expect_page() as other_page_info:
        await page.evaluate("url => window.open(url)", "about:blank")
    other_page = await other_page_info.value
    await other_page.waitForLoadState("domcontentloaded")
    assert other_page.url == "about:blank"


async def test_page_event_should_have_about_blank_for_empty_url_with_domcontentloaded(
    context, server
):
    page = await context.newPage()
    async with context.expect_page() as other_page_info:
        await page.evaluate("window.open()")
    other_page = await other_page_info.value
    await other_page.waitForLoadState("domcontentloaded")
    assert other_page.url == "about:blank"


async def test_page_event_should_report_when_a_new_page_is_created_and_closed(
    context, server
):
    page = await context.newPage()
    [other_page, _] = await asyncio.gather(
        context.waitForEvent("page"),
        page.evaluate(
            "url => window.open(url)", server.CROSS_PROCESS_PREFIX + "/empty.html"
        ),
    )
    # The url is about:blank in FF when 'page' event is fired.
    assert server.CROSS_PROCESS_PREFIX in other_page.url
    assert await other_page.evaluate("['Hello', 'world'].join(' ')") == "Hello world"
    assert await other_page.querySelector("body")

    all_pages = context.pages
    assert page in all_pages
    assert other_page in all_pages

    close_event_received = []
    other_page.once("close", lambda: close_event_received.append(True))
    await other_page.close()
    assert close_event_received == [True]

    all_pages = context.pages
    assert page in all_pages
    assert other_page not in all_pages


async def test_page_event_should_report_initialized_pages(context, server):
    page_event_promise = asyncio.create_task(context.waitForEvent("page"))
    asyncio.create_task(context.newPage())
    newPage = await page_event_promise
    assert newPage.url == "about:blank"

    popup_event_promise = asyncio.create_task(context.waitForEvent("page"))
    evaluate_promise = asyncio.create_task(
        newPage.evaluate("window.open('about:blank')")
    )
    popup = await popup_event_promise
    assert popup.url == "about:blank"
    await evaluate_promise


# TODO: fix the server to issue callbacks on the Playwright loop
# async def test_page_event_should_not_crash_while_redirecting_of_original_request_was_missed(
#     context, server
# ):
#     page = await context.newPage()
#     requests = []
#     server.set_route("/one-style.css", lambda request: requests.append(request))
#     # Open a new page. Use window.open to connect to the page later.

#     [new_page, _, _] = await asyncio.gather(
#         context.waitForEvent("page"),
#         page.evaluate("url => window.open(url)", server.PREFIX + "/one-style.html"),
#         server.wait_for_request("/one-style.css")
#     )
#     # Issue a redirect.
#     requests[0].setResponseCode(302)
#     requests[0].setHeader("location", "/injectedstyle.css")
#     requests[0].finish()

#     await new_page.waitForLoadState("domcontentloaded")
#     assert new_page.url == server.PREFIX + "/one-style.html"


async def test_page_event_should_have_an_opener(context, server):
    page = await context.newPage()
    await page.goto(server.EMPTY_PAGE)
    [popup, _] = await asyncio.gather(
        context.waitForEvent("page"),
        page.goto(server.PREFIX + "/popup/window-open.html"),
    )
    assert popup.url == server.PREFIX + "/popup/popup.html"
    assert await popup.opener() == page
    assert await page.opener() is None


async def test_page_event_should_fire_page_lifecycle_events(context, server):
    events = []

    def handle_page(page):
        events.append("CREATED: " + page.url)
        page.on("close", lambda: events.append("DESTROYED: " + page.url))

    context.on("page", lambda page: handle_page(page))

    page = await context.newPage()
    await page.goto(server.EMPTY_PAGE)
    await page.close()
    assert events == ["CREATED: about:blank", f"DESTROYED: {server.EMPTY_PAGE}"]


@pytest.mark.skip_browser("webkit")
async def test_page_event_should_work_with_shift_clicking(context, server):
    # WebKit: Shift+Click does not open a new window.
    page = await context.newPage()
    await page.goto(server.EMPTY_PAGE)
    await page.setContent('<a href="/one-style.html">yo</a>')
    [popup, _] = await asyncio.gather(
        context.waitForEvent("page"), page.click("a", modifiers=["Shift"])
    )
    assert await popup.opener() is None


@pytest.mark.only_browser("chromium")
async def test_page_event_should_work_with_ctrl_clicking(context, server, is_mac):
    # Firefox: reports an opener in this case.
    # WebKit: Ctrl+Click does not open a new tab.
    page = await context.newPage()
    await page.goto(server.EMPTY_PAGE)
    await page.setContent('<a href="/one-style.html">yo</a>')
    [popup, _] = await asyncio.gather(
        context.waitForEvent("page"),
        page.click("a", modifiers=["Meta" if is_mac else "Control"]),
    )
    assert await popup.opener() is None
