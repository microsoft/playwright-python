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

"""Port of tests/library/browsercontext-page-event.spec.ts."""

from typing import List

from playwright.async_api import Browser, Page
from tests.server import ExpectResponse, Server, TestServerRequest, reactor


async def wait_for_server_request(
    page: Page, request_info: ExpectResponse[TestServerRequest]
) -> TestServerRequest:
    """Waits until the test server gets the request of server.expect_request()."""
    while True:
        try:
            return request_info.value
        except ValueError:
            await page.wait_for_timeout(10)


async def test_BC_062_should_have_url(browser: Browser, server: Server) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    async with context.expect_page() as other_page_info:
        await page.evaluate("url => window.open(url)", server.EMPTY_PAGE)
    other_page = await other_page_info.value
    assert other_page.url == server.EMPTY_PAGE
    await context.close()


async def test_BC_063_should_have_url_after_domcontentloaded(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    async with context.expect_page() as other_page_info:
        await page.evaluate("url => window.open(url)", server.EMPTY_PAGE)
    other_page = await other_page_info.value
    await other_page.wait_for_load_state("domcontentloaded")
    assert other_page.url == server.EMPTY_PAGE
    await context.close()


async def test_BC_064_should_have_about_blank_url_with_domcontentloaded(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    async with context.expect_page() as other_page_info:
        await page.evaluate("url => window.open(url)", "about:blank")
    other_page = await other_page_info.value
    await other_page.wait_for_load_state("domcontentloaded")
    assert other_page.url == "about:blank"
    await context.close()


async def test_BC_065_should_have_about_blank_for_empty_url_with_domcontentloaded(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    async with context.expect_page() as other_page_info:
        await page.evaluate("() => window.open()")
    other_page = await other_page_info.value
    await other_page.wait_for_load_state("domcontentloaded")
    assert other_page.url == "about:blank"
    await context.close()


async def test_BC_066_should_report_when_a_new_page_is_created_and_closed(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    async with context.expect_page() as other_page_info:
        await page.evaluate(
            "url => window.open(url)", server.CROSS_PROCESS_PREFIX + "/empty.html"
        )
    other_page = await other_page_info.value
    # The url is about:blank in FF when 'page' event is fired.
    assert server.CROSS_PROCESS_PREFIX in other_page.url
    assert (
        await other_page.evaluate("() => ['Hello', 'world'].join(' ')") == "Hello world"
    )
    assert await other_page.query_selector("body")

    all_pages = context.pages
    assert page in all_pages
    assert other_page in all_pages

    close_event_received: List[bool] = []
    other_page.once("close", lambda _: close_event_received.append(True))
    await other_page.close()
    assert close_event_received

    all_pages = context.pages
    assert page in all_pages
    assert other_page not in all_pages
    await context.close()


async def test_BC_067_should_report_initialized_pages(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()
    async with context.expect_page() as page_info:
        await context.new_page()
    new_page = await page_info.value
    assert new_page.url == "about:blank"

    async with context.expect_page() as popup_info:
        await new_page.evaluate("() => window.open('about:blank')")
    popup = await popup_info.value
    assert popup.url == "about:blank"
    await context.close()


async def test_BC_068_should_not_crash_while_redirecting_of_original_request_was_missed(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    # Hold the response.
    server.set_route("/one-style.css", lambda request: None)
    # Open a new page. Use window.open to connect to the page later.
    with server.expect_request("/one-style.css") as request_info:
        async with context.expect_page() as new_page_info:
            await page.evaluate(
                "url => window.open(url)", server.PREFIX + "/one-style.html"
            )
    new_page = await new_page_info.value
    server_response = await wait_for_server_request(new_page, request_info)

    # Issue a redirect.
    def redirect() -> None:
        server_response.setResponseCode(302)
        server_response.setHeader("location", "/injectedstyle.css")
        server_response.finish()

    reactor.callFromThread(redirect)
    await new_page.wait_for_load_state("domcontentloaded")
    assert new_page.url == server.PREFIX + "/one-style.html"
    # Cleanup.
    await context.close()


async def test_BC_069_should_have_an_opener(browser: Browser, server: Server) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    async with context.expect_page() as popup_info:
        await page.goto(server.PREFIX + "/popup/window-open.html")
    popup = await popup_info.value
    assert popup.url == server.PREFIX + "/popup/popup.html"
    assert await popup.opener() == page
    assert await page.opener() is None
    await context.close()


async def test_BC_070_should_fire_page_lifecycle_events(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()
    events: List[str] = []

    def on_page(page: Page) -> None:
        events.append("CREATED: " + page.url)
        page.on("close", lambda _: events.append("DESTROYED: " + page.url))

    context.on("page", on_page)
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    await page.close()
    assert events == ["CREATED: about:blank", f"DESTROYED: {server.EMPTY_PAGE}"]
    await context.close()


async def test_BC_071_should_work_with_shift_clicking(
    browser: Browser, server: Server, browser_name: str
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    await page.set_content('<a href="/one-style.html">yo</a>')
    async with context.expect_page() as popup_info:
        await page.click("a", modifiers=["Shift"])
    popup = await popup_info.value
    assert await popup.opener() is None
    await context.close()


async def test_BC_072_should_work_with_ctrl_clicking(
    browser: Browser, server: Server, browser_name: str
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    await page.set_content('<a href="/one-style.html">yo</a>')
    async with context.expect_page() as popup_info:
        await page.click("a", modifiers=["ControlOrMeta"])
    popup = await popup_info.value
    assert await popup.opener() == (page if browser_name == "firefox" else None)
    await context.close()
