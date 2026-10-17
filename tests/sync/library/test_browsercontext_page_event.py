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

from playwright.sync_api import Browser, Page
from tests.server import ExpectResponse, Server, TestServerRequest, reactor


def wait_for_server_request(
    page: Page, request_info: ExpectResponse[TestServerRequest]
) -> TestServerRequest:
    """Waits until the test server gets the request of server.expect_request()."""
    while True:
        try:
            return request_info.value
        except ValueError:
            page.wait_for_timeout(10)


def test_BC_062_should_have_url(browser: Browser, server: Server) -> None:
    context = browser.new_context()
    page = context.new_page()
    with context.expect_page() as other_page_info:
        page.evaluate("url => window.open(url)", server.EMPTY_PAGE)
    other_page = other_page_info.value
    assert other_page.url == server.EMPTY_PAGE
    context.close()


def test_BC_063_should_have_url_after_domcontentloaded(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context()
    page = context.new_page()
    with context.expect_page() as other_page_info:
        page.evaluate("url => window.open(url)", server.EMPTY_PAGE)
    other_page = other_page_info.value
    other_page.wait_for_load_state("domcontentloaded")
    assert other_page.url == server.EMPTY_PAGE
    context.close()


def test_BC_064_should_have_about_blank_url_with_domcontentloaded(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context()
    page = context.new_page()
    with context.expect_page() as other_page_info:
        page.evaluate("url => window.open(url)", "about:blank")
    other_page = other_page_info.value
    other_page.wait_for_load_state("domcontentloaded")
    assert other_page.url == "about:blank"
    context.close()


def test_BC_065_should_have_about_blank_for_empty_url_with_domcontentloaded(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context()
    page = context.new_page()
    with context.expect_page() as other_page_info:
        page.evaluate("() => window.open()")
    other_page = other_page_info.value
    other_page.wait_for_load_state("domcontentloaded")
    assert other_page.url == "about:blank"
    context.close()


def test_BC_066_should_report_when_a_new_page_is_created_and_closed(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context()
    page = context.new_page()
    with context.expect_page() as other_page_info:
        page.evaluate(
            "url => window.open(url)", server.CROSS_PROCESS_PREFIX + "/empty.html"
        )
    other_page = other_page_info.value
    # The url is about:blank in FF when 'page' event is fired.
    assert server.CROSS_PROCESS_PREFIX in other_page.url
    assert other_page.evaluate("() => ['Hello', 'world'].join(' ')") == "Hello world"
    assert other_page.query_selector("body")

    all_pages = context.pages
    assert page in all_pages
    assert other_page in all_pages

    close_event_received: List[bool] = []
    other_page.once("close", lambda _: close_event_received.append(True))
    other_page.close()
    assert close_event_received

    all_pages = context.pages
    assert page in all_pages
    assert other_page not in all_pages
    context.close()


def test_BC_067_should_report_initialized_pages(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context()
    with context.expect_page() as page_info:
        context.new_page()
    new_page = page_info.value
    assert new_page.url == "about:blank"

    with context.expect_page() as popup_info:
        new_page.evaluate("() => window.open('about:blank')")
    popup = popup_info.value
    assert popup.url == "about:blank"
    context.close()


def test_BC_068_should_not_crash_while_redirecting_of_original_request_was_missed(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context()
    page = context.new_page()
    # Hold the response.
    server.set_route("/one-style.css", lambda request: None)
    # Open a new page. Use window.open to connect to the page later.
    with server.expect_request("/one-style.css") as request_info:
        with context.expect_page() as new_page_info:
            page.evaluate("url => window.open(url)", server.PREFIX + "/one-style.html")
    new_page = new_page_info.value
    server_response = wait_for_server_request(new_page, request_info)

    # Issue a redirect.
    def redirect() -> None:
        server_response.setResponseCode(302)
        server_response.setHeader("location", "/injectedstyle.css")
        server_response.finish()

    reactor.callFromThread(redirect)
    new_page.wait_for_load_state("domcontentloaded")
    assert new_page.url == server.PREFIX + "/one-style.html"
    # Cleanup.
    context.close()


def test_BC_069_should_have_an_opener(browser: Browser, server: Server) -> None:
    context = browser.new_context()
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)
    with context.expect_page() as popup_info:
        page.goto(server.PREFIX + "/popup/window-open.html")
    popup = popup_info.value
    assert popup.url == server.PREFIX + "/popup/popup.html"
    assert popup.opener() == page
    assert page.opener() is None
    context.close()


def test_BC_070_should_fire_page_lifecycle_events(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context()
    events: List[str] = []

    def on_page(page: Page) -> None:
        events.append("CREATED: " + page.url)
        page.on("close", lambda _: events.append("DESTROYED: " + page.url))

    context.on("page", on_page)
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)
    page.close()
    assert events == ["CREATED: about:blank", f"DESTROYED: {server.EMPTY_PAGE}"]
    context.close()


def test_BC_071_should_work_with_shift_clicking(
    browser: Browser, server: Server, browser_name: str
) -> None:
    context = browser.new_context()
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)
    page.set_content('<a href="/one-style.html">yo</a>')
    with context.expect_page() as popup_info:
        page.click("a", modifiers=["Shift"])
    popup = popup_info.value
    assert popup.opener() is None
    context.close()


def test_BC_072_should_work_with_ctrl_clicking(
    browser: Browser, server: Server, browser_name: str
) -> None:
    context = browser.new_context()
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)
    page.set_content('<a href="/one-style.html">yo</a>')
    with context.expect_page() as popup_info:
        page.click("a", modifiers=["ControlOrMeta"])
    popup = popup_info.value
    assert popup.opener() == (page if browser_name == "firefox" else None)
    context.close()
