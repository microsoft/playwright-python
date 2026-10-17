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

"""Port of tests/library/browsercontext-basic.spec.ts."""

import functools
import json
import time
from typing import Any, Callable, List, Optional

import pytest

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Error,
    Page,
    Route,
    ViewportSize,
    expect,
)
from tests.server import Server, TestServerRequest
from tests.utils import TARGET_CLOSED_ERROR_MESSAGE

from ..utils import Utils


def poll_until_equal(
    actual: Callable[[], Any], expected: Any, timeout: float = 5000
) -> None:
    """Port of `await expect.poll(actual).toEqual(expected)`."""
    deadline = time.monotonic() + timeout / 1000
    value = actual()
    while value != expected and time.monotonic() < deadline:
        time.sleep(0.1)
        value = actual()
    assert value == expected


@pytest.mark.xfail(
    reason="python: browser.contexts comes from a set, so it is not in creation order",
    strict=False,
)
def test_BC_001_should_create_new_context_smoke(browser: Browser) -> None:
    assert len(browser.contexts) == 0
    context = browser.new_context()
    context2: Optional[BrowserContext] = None
    try:
        assert browser.contexts == [context]
        assert browser == context.browser
        context2 = browser.new_context()
        assert browser.contexts == [context, context2]
        context.close()
        assert browser.contexts == [context2]
        assert browser == context.browser
        context2.close()
    finally:
        # Do not leak the contexts into the next tests when an assertion fails.
        context.close()
        if context2:
            context2.close()


def test_BC_002_should_be_able_to_click_across_browser_contexts(
    browser: Browser, sync_gather: Callable[..., List[Any]]
) -> None:
    assert len(browser.contexts) == 0

    def create_page() -> Page:
        page = browser.new_page()
        page.set_content("<button>Click me</button>")
        page.locator("button").evaluate(
            """button => {
              window['clicks'] = 0;
              button.addEventListener('click', () => ++window['clicks'], false);
            }"""
        )
        return page

    def click_in_page(page: Page, count: int) -> None:
        for _ in range(count):
            page.locator("button").click()

    def get_clicks(page: Page) -> int:
        return page.evaluate("() => window['clicks']")

    page1 = create_page()
    page2 = create_page()

    CLICK_COUNT = 20
    sync_gather(
        lambda: click_in_page(page1, CLICK_COUNT),
        lambda: click_in_page(page2, CLICK_COUNT),
    )
    assert get_clicks(page1) == CLICK_COUNT
    assert get_clicks(page2) == CLICK_COUNT

    page1.close()
    page2.close()


def test_BC_003_should_be_able_to_hover_across_browser_contexts_in_parallel(
    browser: Browser,
    browser_name: str,
    headless: bool,
    sync_gather: Callable[..., List[Any]],
) -> None:
    if browser_name == "firefox" and not headless:
        pytest.skip("fixme: Hover is flaky in headed Firefox")

    html = """
    <style>
      [role="tooltip"] { display: none; }
      [role="tooltip"].visible { display: block; }
    </style>
    <button>Hover me</button>
    <div role="tooltip">Tooltip content</div>
    <script>
      const button = document.querySelector('button');
      const tooltip = document.querySelector('[role="tooltip"]');
      button.addEventListener('pointerenter', () => tooltip.classList.add('visible'));
      button.addEventListener('pointerleave', () => tooltip.classList.remove('visible'));
    </script>
  """

    def create_page() -> Page:
        context = browser.new_context()
        page = context.new_page()
        page.set_content(html)
        return page

    pages: List[Page] = sync_gather(*[lambda: create_page() for _ in range(5)])

    def hover(page: Page) -> None:
        page.get_by_role("button", name="Hover me").hover()
        expect(page.get_by_role("tooltip")).to_be_visible()

    sync_gather(*[functools.partial(hover, page) for page in pages])

    sync_gather(*[functools.partial(page.context.close) for page in pages])


def test_BC_004_window_open_should_use_parent_tab_context(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context()
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)
    with page.expect_popup() as popup_info:
        page.evaluate("url => window.open(url)", server.EMPTY_PAGE)
    popup = popup_info.value
    assert popup.context == context
    context.close()


def test_BC_005_should_isolate_local_storage_and_cookies_smoke(
    browser: Browser, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    # Create two incognito contexts.
    context1 = browser.new_context()
    context2 = browser.new_context()
    assert len(context1.pages) == 0
    assert len(context2.pages) == 0

    # Create a page in first incognito context.
    page1 = context1.new_page()
    page1.goto(server.EMPTY_PAGE)
    page1.evaluate(
        """() => {
          localStorage.setItem('name', 'page1');
          document.cookie = 'name=page1';
        }"""
    )

    assert len(context1.pages) == 1
    assert len(context2.pages) == 0

    # Create a page in second incognito context.
    page2 = context2.new_page()
    page2.goto(server.EMPTY_PAGE)
    page2.evaluate(
        """() => {
          localStorage.setItem('name', 'page2');
          document.cookie = 'name=page2';
        }"""
    )

    assert len(context1.pages) == 1
    assert len(context2.pages) == 1
    assert context1.pages[0] == page1
    assert context2.pages[0] == page2

    # Make sure pages don't share localstorage or cookies.
    assert page1.evaluate("() => localStorage.getItem('name')") == "page1"
    assert page1.evaluate("() => document.cookie") == "name=page1"
    assert page2.evaluate("() => localStorage.getItem('name')") == "page2"
    assert page2.evaluate("() => document.cookie") == "name=page2"

    # Cleanup contexts.
    sync_gather(context1.close, context2.close)
    assert len(browser.contexts) == 0


def test_BC_006_should_propagate_default_viewport_to_the_page(
    browser: Browser, utils: Utils
) -> None:
    context = browser.new_context(viewport={"width": 456, "height": 789})
    page = context.new_page()
    utils.verify_viewport(page, 456, 789)
    context.close()


def test_BC_007_should_make_a_copy_of_default_viewport(
    browser: Browser, utils: Utils
) -> None:
    viewport: ViewportSize = {"width": 456, "height": 789}
    context = browser.new_context(viewport=viewport)
    viewport["width"] = 567
    page = context.new_page()
    utils.verify_viewport(page, 456, 789)
    context.close()


def test_BC_008_should_respect_device_scale_factor(browser: Browser) -> None:
    context = browser.new_context(device_scale_factor=3)
    page = context.new_page()
    assert page.evaluate("window.devicePixelRatio") == 3
    context.close()


def test_BC_009_should_not_allow_device_scale_factor_with_null_viewport(
    browser: Browser,
) -> None:
    with pytest.raises(Error) as exc_info:
        browser.new_context(no_viewport=True, device_scale_factor=1)
    assert (
        '"deviceScaleFactor" option is not supported with null "viewport"'
        in exc_info.value.message
    )


def test_BC_010_should_not_allow_is_mobile_with_null_viewport(
    browser: Browser,
) -> None:
    with pytest.raises(Error) as exc_info:
        browser.new_context(no_viewport=True, is_mobile=True)
    assert (
        '"isMobile" option is not supported with null "viewport"'
        in exc_info.value.message
    )


def test_BC_011_close_should_work_for_empty_context(browser: Browser) -> None:
    context = browser.new_context()
    context.close()


def test_BC_012_close_should_abort_wait_for_event(browser: Browser) -> None:
    context = browser.new_context()
    with pytest.raises(Error) as exc_info:
        with context.expect_event("page"):
            context.close()
    assert TARGET_CLOSED_ERROR_MESSAGE in exc_info.value.message


def test_BC_013_close_should_be_callable_twice(browser: Browser) -> None:
    context = browser.new_context()
    context.close()
    context.close()


def test_BC_014_should_pass_self_to_close_event(browser: Browser) -> None:
    new_context = browser.new_context()
    with new_context.expect_event("close") as event_info:
        new_context.close()
    closed_context = event_info.value
    assert closed_context == new_context


def test_BC_015_should_not_report_frameless_pages_on_error(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context()
    page = context.new_page()

    def handler(request: TestServerRequest) -> None:
        request.write(
            f'<a href="{server.EMPTY_PAGE}" target="_blank">Click me</a>'.encode()
        )
        request.finish()

    server.set_route("/empty.html", handler)
    popups: List[Page] = []
    context.on("page", lambda p: popups.append(p))
    page.goto(server.EMPTY_PAGE)
    page.click('"Click me"')
    context.close()
    if popups:
        popup = popups[-1]
        # This races on Firefox :/
        assert popup.is_closed()
        assert popup.main_frame


def test_BC_016_should_return_all_of_the_pages(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context()
    page = context.new_page()
    second = context.new_page()
    all_pages = context.pages
    assert len(all_pages) == 2
    assert page in all_pages
    assert second in all_pages
    context.close()


def test_BC_017_should_close_all_belonging_pages_once_closing_context(
    browser: Browser,
) -> None:
    context = browser.new_context()
    context.new_page()
    assert len(context.pages) == 1

    context.close()
    assert len(context.pages) == 0


def test_BC_018_should_disable_javascript(browser: Browser, browser_name: str) -> None:
    context = browser.new_context(java_script_enabled=False)
    page = context.new_page()
    page.goto('data:text/html, <script>var something = "forbidden"</script>')
    with pytest.raises(Error) as exc_info:
        page.evaluate("something")
    if browser_name == "webkit":
        assert "Can't find variable: something" in exc_info.value.message
    else:
        assert "something is not defined" in exc_info.value.message
    context.close()

    context = browser.new_context()
    page = context.new_page()
    page.goto('data:text/html, <script>var something = "forbidden"</script>')
    assert page.evaluate("something") == "forbidden"
    context.close()


def test_BC_019_should_be_able_to_navigate_after_disabling_javascript(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context(java_script_enabled=False)
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)
    context.close()


def test_BC_020_should_not_hang_on_promises_after_disabling_javascript(
    browser_name: str, context_factory: Callable[..., BrowserContext]
) -> None:
    if browser_name == "firefox":
        pytest.skip("fixme")
    context = context_factory(java_script_enabled=False)
    page = context.new_page()
    assert page.evaluate("() => 1") == 1
    assert page.evaluate("async () => 2") == 2


def test_BC_021_set_content_should_work_after_disabling_javascript(
    context_factory: Callable[..., BrowserContext],
) -> None:
    context = context_factory(java_script_enabled=False)
    page = context.new_page()
    page.set_content("<h1>Hello</h1>")
    expect(page.locator("h1")).to_have_text("Hello")


def test_BC_022_should_retry_click_after_disabling_javascript(
    context_factory: Callable[..., BrowserContext],
    sync_gather: Callable[..., List[Any]],
) -> None:
    context = context_factory(java_script_enabled=False)
    page = context.new_page()
    page.set_content(
        """
    <details><summary>Continue</summary>Details</details>
    <div id="cover" style="position: fixed; inset: 0;"></div>
  """
    )
    clicked = False

    def click() -> None:
        nonlocal clicked
        page.locator("summary").click()
        clicked = True

    def uncover() -> None:
        # Give it enough time to go through a few retries while the button is covered.
        page.wait_for_timeout(2000)
        assert clicked is False
        page.locator("#cover").evaluate("e => e.remove()")

    sync_gather(click, uncover)
    expect(page.locator("details")).to_have_attribute("open", "")


def test_BC_023_should_work_with_offline_option(
    browser: Browser, server: Server, browser_name: str
) -> None:
    context = browser.new_context(offline=True)
    page = context.new_page()
    error: Optional[Error] = None
    if browser_name == "firefox":
        # Firefox navigates to an error page, and this navigation might conflict with the
        # next navigation we do in test.
        # So we need to wait for the navigation explicitly.
        with page.expect_event("framenavigated"):
            try:
                page.goto(server.EMPTY_PAGE)
            except Error as e:
                error = e
    else:
        try:
            page.goto(server.EMPTY_PAGE)
        except Error as e:
            error = e
    assert error
    context.set_offline(False)
    response = page.goto(server.EMPTY_PAGE)
    assert response
    assert response.status == 200
    context.close()


def test_BC_024_fetch_with_keepalive_should_throw_when_offline(
    context_factory: Callable[..., BrowserContext], server: Server
) -> None:
    context = context_factory()
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)

    url = server.PREFIX + "/fetch"

    def handler(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "application/json")
        request.write(json.dumps("hello").encode())
        request.finish()

    server.set_route("/fetch", handler)

    ok_response = page.evaluate(
        "url => fetch(url, { cache: 'no-store', keepalive: true }).then(response => response.json())",
        url,
    )
    assert ok_response == "hello"

    context.set_offline(True)
    offline_response = page.evaluate(
        """async url => {
          try {
            const response = await fetch(url, { cache: 'no-store', keepalive: true });
            return await response.json();
          } catch {
            return 'error';
          }
        }""",
        url,
    )
    assert offline_response == "error"


def test_BC_025_should_emulate_navigator_on_line(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context()
    page = context.new_page()
    assert page.evaluate("() => window.navigator.onLine") is True
    context.set_offline(True)
    assert page.evaluate("() => window.navigator.onLine") is False
    context.set_offline(False)
    assert page.evaluate("() => window.navigator.onLine") is True
    context.close()


def test_BC_026_should_emulate_navigator_on_line_across_navigations(
    browser: Browser, server: Server, browser_name: str, browser_major_version: int
) -> None:
    if browser_name == "chromium" and browser_major_version < 155:
        pytest.skip("does not survive cross-process navgiation")

    context = browser.new_context()
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)
    assert page.evaluate("() => window.navigator.onLine") is True
    context.set_offline(True)
    assert page.evaluate("() => window.navigator.onLine") is False

    page.goto("about:blank")
    assert page.evaluate("() => window.navigator.onLine") is False
    page.goto("data:text/html,<title>offline</title>")
    assert page.evaluate("() => window.navigator.onLine") is False

    if browser_name == "chromium":
        # Try a cross-process navigation in Chromium, which allows routing while offline.
        def handle(route: Route) -> None:
            route.fulfill(content_type="text/html", body="<html></html>")

        page.route("**/*", handle)
        page.goto(server.CROSS_PROCESS_PREFIX + "/empty.html")
        assert page.evaluate("() => window.navigator.onLine") is False

    context.set_offline(False)
    assert page.evaluate("() => window.navigator.onLine") is True
    context.close()


def test_BC_027_should_emulate_offline_event(browser: Browser) -> None:
    context = browser.new_context()
    page = context.new_page()
    events = page.evaluate_handle(
        """() => {
          const events = [];
          window.addEventListener('offline', () => events.push('offline'));
          window.addEventListener('online', () => events.push('online'));
          return events;
        }"""
    )
    context.set_offline(True)
    poll_until_equal(lambda: events.json_value(), ["offline"])
    context.set_offline(False)
    poll_until_equal(lambda: events.json_value(), ["offline", "online"])
    context.close()


def test_BC_028_should_emulate_media_in_popup(browser: Browser, server: Server) -> None:
    context = browser.new_context(color_scheme="dark")
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)
    with page.expect_popup() as popup_info:
        page.evaluate("url => { window.open(url); }", server.EMPTY_PAGE)
    popup = popup_info.value
    assert (
        popup.evaluate("() => matchMedia('(prefers-color-scheme: light)').matches")
        is False
    )
    assert (
        popup.evaluate("() => matchMedia('(prefers-color-scheme: dark)').matches")
        is True
    )
    context.close()

    page = browser.new_page(color_scheme="light")
    page.goto(server.EMPTY_PAGE)
    with page.expect_popup() as popup_info:
        page.evaluate("url => { window.open(url); }", server.EMPTY_PAGE)
    popup = popup_info.value
    assert (
        popup.evaluate("() => matchMedia('(prefers-color-scheme: light)').matches")
        is True
    )
    assert (
        popup.evaluate("() => matchMedia('(prefers-color-scheme: dark)').matches")
        is False
    )
    page.close()


def test_BC_029_should_emulate_media_in_cross_process_iframe(
    browser: Browser, server: Server, utils: Utils
) -> None:
    page = browser.new_page(color_scheme="dark")
    page.goto(server.EMPTY_PAGE)
    utils.attach_frame(page, "frame1", server.CROSS_PROCESS_PREFIX + "/empty.html")
    frame = page.frames[1]
    assert (
        frame.evaluate("() => matchMedia('(prefers-color-scheme: dark)').matches")
        is True
    )
    page.close()


def test_BC_030_default_user_agent(browser: Browser, page: Page) -> None:
    result = browser._sync(browser._impl_obj._channel.defaultUserAgentForTest())
    assert page.evaluate("() => navigator.userAgent") == result["userAgent"]


def test_BC_031_should_create_two_pages_in_parallel_in_various_contexts(
    browser: Browser, sync_gather: Callable[..., List[Any]]
) -> None:
    context1 = browser.new_context()
    context2 = browser.new_context()
    sync_gather(
        lambda: context1.new_page(),
        lambda: context1.new_page(),
        lambda: context2.new_page(),
        lambda: context2.new_page(),
    )
    context1.close()
    context2.close()
    context3 = browser.new_context()
    sync_gather(
        lambda: context3.new_page(),
        lambda: context3.new_page(),
    )
    context3.close()
