# Copyright (c) Microsoft Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http:#www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import asyncio

import pytest


async def test_should_have_default_url_when_launching_browser(
    browser_type, launch_arguments, tmpdir
):
    browser_context = await browser_type.launchPersistentContext(
        tmpdir, **{**launch_arguments, "headless": False}
    )
    urls = [page.url for page in browser_context.pages]
    assert urls == ["about:blank"]
    await browser_context.close()


async def test_headless_should_be_able_to_read_cookies_written_by_headful(
    browser_type, launch_arguments, server, tmpdir, is_chromium, is_win
):
    if is_chromium and is_win:
        pytest.skip("see https://github.com/microsoft/playwright/issues/717")
        return
    # Write a cookie in headful chrome
    headful_context = await browser_type.launchPersistentContext(
        tmpdir, **{**launch_arguments, "headless": False}
    )
    headful_page = await headful_context.newPage()
    await headful_page.goto(server.EMPTY_PAGE)
    await headful_page.evaluate(
        """() => document.cookie = 'foo=true; expires=Fri, 31 Dec 9999 23:59:59 GMT'"""
    )
    await headful_context.close()
    # Read the cookie from headless chrome
    headless_context = await browser_type.launchPersistentContext(
        tmpdir, **{**launch_arguments, "headless": True}
    )
    headless_page = await headless_context.newPage()
    await headless_page.goto(server.EMPTY_PAGE)
    cookie = await headless_page.evaluate("() => document.cookie")
    await headless_context.close()
    # This might throw. See https://github.com/GoogleChrome/puppeteer/issues/2778
    assert cookie == "foo=true"


async def test_should_close_browser_with_beforeunload_page(
    browser_type, launch_arguments, server, tmpdir
):
    browser_context = await browser_type.launchPersistentContext(
        tmpdir, **{**launch_arguments, "headless": False}
    )
    page = await browser_context.newPage()
    await page.goto(server.PREFIX + "/beforeunload.html")
    # We have to interact with a page so that 'beforeunload' handlers
    # fire.
    await page.click("body")
    await browser_context.close()


async def test_should_not_crash_when_creating_second_context(
    browser_type, launch_arguments, server
):
    browser = await browser_type.launch(**{**launch_arguments, "headless": False})
    browser_context = await browser.newContext()
    await browser_context.newPage()
    await browser_context.close()
    browser_context = await browser.newContext()
    await browser_context.newPage()
    await browser_context.close()
    await browser.close()


async def test_should_click_background_tab(browser_type, launch_arguments, server):
    browser = await browser_type.launch(**{**launch_arguments, "headless": False})
    page = await browser.newPage()
    await page.setContent(
        '<button>Hello</button><a target=_blank href="${server.EMPTY_PAGE}">empty.html</a>'
    )
    await page.click("a")
    await page.click("button")
    await browser.close()


async def test_should_close_browser_after_context_menu_was_triggered(
    browser_type, launch_arguments, server
):
    browser = await browser_type.launch(**{**launch_arguments, "headless": False})
    page = await browser.newPage()
    await page.goto(server.PREFIX + "/grid.html")
    await page.click("body", button="right")
    await browser.close()


async def test_should_not_block_third_party_cookies(
    browser_type, launch_arguments, server, is_chromium, is_firefox
):
    browser = await browser_type.launch(**{**launch_arguments, "headless": False})
    page = await browser.newPage()
    await page.goto(server.EMPTY_PAGE)
    await page.evaluate(
        """src => {
    let fulfill;
    const promise = new Promise(x => fulfill = x);
    const iframe = document.createElement('iframe');
    document.body.appendChild(iframe);
    iframe.onload = fulfill;
    iframe.src = src;
    return promise;
  }""",
        server.CROSS_PROCESS_PREFIX + "/grid.html",
    )
    document_cookie = await page.frames[1].evaluate(
        """() => {
    document.cookie = 'username=John Doe';
    return document.cookie;
  }"""
    )

    await page.waitForTimeout(2000)
    allowsThirdParty = is_chromium or is_firefox
    assert document_cookie == ("username=John Doe" if allowsThirdParty else "")
    cookies = await page.context.cookies(server.CROSS_PROCESS_PREFIX + "/grid.html")
    if allowsThirdParty:
        assert cookies == [
            {
                "domain": "127.0.0.1",
                "expires": -1,
                "httpOnly": False,
                "name": "username",
                "path": "/",
                "sameSite": "None",
                "secure": False,
                "value": "John Doe",
            }
        ]
    else:
        assert cookies == []

    await browser.close()


@pytest.mark.skip_browser("webkit")
async def test_should_not_override_viewport_size_when_passed_null(
    browser_type, launch_arguments, server
):
    # Our WebKit embedder does not respect window features.
    browser = await browser_type.launch(**{**launch_arguments, "headless": False})
    context = await browser.newContext(viewport=0)
    page = await context.newPage()
    await page.goto(server.EMPTY_PAGE)
    [popup, _] = await asyncio.gather(
        page.waitForEvent("popup"),
        page.evaluate(
            """() => {
      const win = window.open(window.location.href, 'Title', 'toolbar=no,location=no,directories=no,status=no,menubar=no,scrollbars=yes,resizable=yes,width=600,height=300,top=0,left=0');
      win.resizeTo(500, 450);
    }"""
        ),
    )
    await popup.waitForLoadState()
    await popup.waitForFunction(
        """() => window.outerWidth === 500 && window.outerHeight === 450"""
    )
    await context.close()
    await browser.close()


async def test_page_bring_to_front_should_work(browser_type, launch_arguments):
    browser = await browser_type.launch(**{**launch_arguments, "headless": False})
    page1 = await browser.newPage()
    await page1.setContent("Page1")
    page2 = await browser.newPage()
    await page2.setContent("Page2")

    await page1.bringToFront()
    assert await page1.evaluate("document.visibilityState") == "visible"
    assert await page2.evaluate("document.visibilityState") == "visible"

    await page2.bringToFront()
    assert await page1.evaluate("document.visibilityState") == "visible"
    assert await page2.evaluate("document.visibilityState") == "visible"
    await browser.close()
