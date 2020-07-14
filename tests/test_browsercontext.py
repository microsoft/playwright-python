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


async def test_should_create_new_context(browser):
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


async def test_should_isolate_localStorage_and_cookies(browser, server):
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


async def test_should_propagate_default_viewport_to_the_page(browser, utils):
    context = await browser.newContext(viewport={"width": 456, "height": 789})
    page = await context.newPage()
    await utils.verify_viewport(page, 456, 789)
    await context.close()


async def test_should_make_a_copy_of_default_viewport(browser, utils):
    viewport = {"width": 456, "height": 789}
    context = await browser.newContext(viewport=viewport)
    viewport["width"] = 567
    page = await context.newPage()
    await utils.verify_viewport(page, 456, 789)
    await context.close()


async def test_should_respect_deviceScaleFactor(browser):
    context = await browser.newContext(deviceScaleFactor=3)
    page = await context.newPage()
    assert await page.evaluate("window.devicePixelRatio") == 3
    await context.close()


async def test_should_not_allow_deviceScaleFactor_with_null_viewport(browser):
    with pytest.raises(Error) as exc_info:
        await browser.newContext(viewport=0, deviceScaleFactor=1)
    assert (
        exc_info.value.message
        == '"deviceScaleFactor" option is not supported with null "viewport"'
    )


async def test_should_not_allow_isMobile_with_null_viewport(browser):
    with pytest.raises(Error) as exc_info:
        await browser.newContext(viewport=0, isMobile=True)
    assert (
        exc_info.value.message
        == '"isMobile" option is not supported with null "viewport"'
    )


async def test_close_should_work_for_empty_context(browser):
    context = await browser.newContext()
    await context.close()


async def test_close_should_abort_waitForEvent(browser):
    context = await browser.newContext()
    promise = asyncio.ensure_future(context.waitForEvent("page"))
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


async def test_should_bypass_csp_meta_tag(browser, server):
    async def baseline():
        context = await browser.newContext()
        page = await context.newPage()
        await page.goto(server.PREFIX + "/csp.html")
        with pytest.raises(Error):
            await page.addScriptTag(content="window.__injected = 42;")
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
