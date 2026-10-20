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

import asyncio
import json
import time
from typing import Any, Awaitable, Callable, List, Optional

import pytest

from playwright.async_api import (
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


async def poll_until_equal(
    actual: Callable[[], Awaitable[Any]], expected: Any, timeout: float = 5000
) -> None:
    """Port of `await expect.poll(actual).toEqual(expected)`."""
    deadline = time.monotonic() + timeout / 1000
    value = await actual()
    while value != expected and time.monotonic() < deadline:
        await asyncio.sleep(0.1)
        value = await actual()
    assert value == expected


async def test_BC_001_should_create_new_context_smoke(browser: Browser) -> None:
    assert len(browser.contexts) == 0
    context = await browser.new_context()
    context2: Optional[BrowserContext] = None
    try:
        assert browser.contexts == [context]
        assert browser == context.browser
        context2 = await browser.new_context()
        assert browser.contexts == [context, context2]
        await context.close()
        assert browser.contexts == [context2]
        assert browser == context.browser
        await context2.close()
    finally:
        # Do not leak the contexts into the next tests when an assertion fails.
        await context.close()
        if context2:
            await context2.close()


async def test_BC_002_should_be_able_to_click_across_browser_contexts(
    browser: Browser,
) -> None:
    assert len(browser.contexts) == 0

    async def create_page() -> Page:
        page = await browser.new_page()
        await page.set_content("<button>Click me</button>")
        await page.locator("button").evaluate(
            """button => {
              window['clicks'] = 0;
              button.addEventListener('click', () => ++window['clicks'], false);
            }"""
        )
        return page

    async def click_in_page(page: Page, count: int) -> None:
        for _ in range(count):
            await page.locator("button").click()

    async def get_clicks(page: Page) -> int:
        return await page.evaluate("() => window['clicks']")

    page1 = await create_page()
    page2 = await create_page()

    CLICK_COUNT = 20
    await asyncio.gather(
        click_in_page(page1, CLICK_COUNT),
        click_in_page(page2, CLICK_COUNT),
    )
    assert await get_clicks(page1) == CLICK_COUNT
    assert await get_clicks(page2) == CLICK_COUNT

    await page1.close()
    await page2.close()


async def test_BC_003_should_be_able_to_hover_across_browser_contexts_in_parallel(
    browser: Browser, browser_name: str, headless: bool
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

    async def create_page() -> Page:
        context = await browser.new_context()
        page = await context.new_page()
        await page.set_content(html)
        return page

    pages: List[Page] = await asyncio.gather(*[create_page() for _ in range(5)])

    async def hover(page: Page) -> None:
        await page.get_by_role("button", name="Hover me").hover()
        await expect(page.get_by_role("tooltip")).to_be_visible()

    await asyncio.gather(*[hover(page) for page in pages])

    await asyncio.gather(*[page.context.close() for page in pages])


async def test_BC_004_window_open_should_use_parent_tab_context(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_popup() as popup_info:
        await page.evaluate("url => window.open(url)", server.EMPTY_PAGE)
    popup = await popup_info.value
    assert popup.context == context
    await context.close()


async def test_BC_005_should_isolate_local_storage_and_cookies_smoke(
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
          localStorage.setItem('name', 'page1');
          document.cookie = 'name=page1';
        }"""
    )

    assert len(context1.pages) == 1
    assert len(context2.pages) == 0

    # Create a page in second incognito context.
    page2 = await context2.new_page()
    await page2.goto(server.EMPTY_PAGE)
    await page2.evaluate(
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
    assert await page1.evaluate("() => localStorage.getItem('name')") == "page1"
    assert await page1.evaluate("() => document.cookie") == "name=page1"
    assert await page2.evaluate("() => localStorage.getItem('name')") == "page2"
    assert await page2.evaluate("() => document.cookie") == "name=page2"

    # Cleanup contexts.
    await asyncio.gather(context1.close(), context2.close())
    assert len(browser.contexts) == 0


async def test_BC_006_should_propagate_default_viewport_to_the_page(
    browser: Browser, utils: Utils
) -> None:
    context = await browser.new_context(viewport={"width": 456, "height": 789})
    page = await context.new_page()
    await utils.verify_viewport(page, 456, 789)
    await context.close()


async def test_BC_007_should_make_a_copy_of_default_viewport(
    browser: Browser, utils: Utils
) -> None:
    viewport: ViewportSize = {"width": 456, "height": 789}
    context = await browser.new_context(viewport=viewport)
    viewport["width"] = 567
    page = await context.new_page()
    await utils.verify_viewport(page, 456, 789)
    await context.close()


async def test_BC_008_should_respect_device_scale_factor(browser: Browser) -> None:
    context = await browser.new_context(device_scale_factor=3)
    page = await context.new_page()
    assert await page.evaluate("window.devicePixelRatio") == 3
    await context.close()


async def test_BC_009_should_not_allow_device_scale_factor_with_null_viewport(
    browser: Browser,
) -> None:
    with pytest.raises(Error) as exc_info:
        await browser.new_context(no_viewport=True, device_scale_factor=1)
    assert (
        '"deviceScaleFactor" option is not supported with null "viewport"'
        in exc_info.value.message
    )


async def test_BC_010_should_not_allow_is_mobile_with_null_viewport(
    browser: Browser,
) -> None:
    with pytest.raises(Error) as exc_info:
        await browser.new_context(no_viewport=True, is_mobile=True)
    assert (
        '"isMobile" option is not supported with null "viewport"'
        in exc_info.value.message
    )


async def test_BC_011_close_should_work_for_empty_context(browser: Browser) -> None:
    context = await browser.new_context()
    await context.close()


async def test_BC_012_close_should_abort_wait_for_event(browser: Browser) -> None:
    context = await browser.new_context()
    with pytest.raises(Error) as exc_info:
        async with context.expect_event("page"):
            await context.close()
    assert TARGET_CLOSED_ERROR_MESSAGE in exc_info.value.message


async def test_BC_013_close_should_be_callable_twice(browser: Browser) -> None:
    context = await browser.new_context()
    await context.close()
    await context.close()


async def test_BC_014_should_pass_self_to_close_event(browser: Browser) -> None:
    new_context = await browser.new_context()
    async with new_context.expect_event("close") as event_info:
        await new_context.close()
    closed_context = await event_info.value
    assert closed_context == new_context


async def test_BC_015_should_not_report_frameless_pages_on_error(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()
    page = await context.new_page()

    def handler(request: TestServerRequest) -> None:
        request.write(
            f'<a href="{server.EMPTY_PAGE}" target="_blank">Click me</a>'.encode()
        )
        request.finish()

    server.set_route("/empty.html", handler)
    popups: List[Page] = []
    context.on("page", lambda p: popups.append(p))
    await page.goto(server.EMPTY_PAGE)
    await page.click('"Click me"')
    await context.close()
    if popups:
        popup = popups[-1]
        # This races on Firefox :/
        assert popup.is_closed()
        assert popup.main_frame


async def test_BC_016_should_return_all_of_the_pages(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    second = await context.new_page()
    all_pages = context.pages
    assert len(all_pages) == 2
    assert page in all_pages
    assert second in all_pages
    await context.close()


async def test_BC_017_should_close_all_belonging_pages_once_closing_context(
    browser: Browser,
) -> None:
    context = await browser.new_context()
    await context.new_page()
    assert len(context.pages) == 1

    await context.close()
    assert len(context.pages) == 0


async def test_BC_018_should_disable_javascript(
    browser: Browser, browser_name: str
) -> None:
    context = await browser.new_context(java_script_enabled=False)
    page = await context.new_page()
    await page.goto('data:text/html, <script>var something = "forbidden"</script>')
    with pytest.raises(Error) as exc_info:
        await page.evaluate("something")
    if browser_name == "webkit":
        assert "Can't find variable: something" in exc_info.value.message
    else:
        assert "something is not defined" in exc_info.value.message
    await context.close()

    context = await browser.new_context()
    page = await context.new_page()
    await page.goto('data:text/html, <script>var something = "forbidden"</script>')
    assert await page.evaluate("something") == "forbidden"
    await context.close()


async def test_BC_019_should_be_able_to_navigate_after_disabling_javascript(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context(java_script_enabled=False)
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    await context.close()


async def test_BC_020_should_not_hang_on_promises_after_disabling_javascript(
    browser_name: str, context_factory: Callable[..., Awaitable[BrowserContext]]
) -> None:
    if browser_name == "firefox":
        pytest.skip("fixme")
    context = await context_factory(java_script_enabled=False)
    page = await context.new_page()
    assert await page.evaluate("() => 1") == 1
    assert await page.evaluate("async () => 2") == 2


async def test_BC_021_set_content_should_work_after_disabling_javascript(
    context_factory: Callable[..., Awaitable[BrowserContext]],
) -> None:
    context = await context_factory(java_script_enabled=False)
    page = await context.new_page()
    await page.set_content("<h1>Hello</h1>")
    await expect(page.locator("h1")).to_have_text("Hello")


async def test_BC_022_should_retry_click_after_disabling_javascript(
    context_factory: Callable[..., Awaitable[BrowserContext]],
) -> None:
    context = await context_factory(java_script_enabled=False)
    page = await context.new_page()
    await page.set_content(
        """
    <details><summary>Continue</summary>Details</details>
    <div id="cover" style="position: fixed; inset: 0;"></div>
  """
    )
    clicked = False

    async def click() -> None:
        nonlocal clicked
        await page.locator("summary").click()
        clicked = True

    async def uncover() -> None:
        # Give it enough time to go through a few retries while the button is covered.
        await page.wait_for_timeout(2000)
        assert clicked is False
        await page.locator("#cover").evaluate("e => e.remove()")

    await asyncio.gather(click(), uncover())
    await expect(page.locator("details")).to_have_attribute("open", "")


async def test_BC_023_should_work_with_offline_option(
    browser: Browser, server: Server, browser_name: str
) -> None:
    context = await browser.new_context(offline=True)
    page = await context.new_page()
    error: Optional[Error] = None
    if browser_name == "firefox":
        # Firefox navigates to an error page, and this navigation might conflict with the
        # next navigation we do in test.
        # So we need to wait for the navigation explicitly.
        async with page.expect_event("framenavigated"):
            try:
                await page.goto(server.EMPTY_PAGE)
            except Error as e:
                error = e
    else:
        try:
            await page.goto(server.EMPTY_PAGE)
        except Error as e:
            error = e
    assert error
    await context.set_offline(False)
    response = await page.goto(server.EMPTY_PAGE)
    assert response
    assert response.status == 200
    await context.close()


async def test_BC_024_fetch_with_keepalive_should_throw_when_offline(
    context_factory: Callable[..., Awaitable[BrowserContext]], server: Server
) -> None:
    context = await context_factory()
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)

    url = server.PREFIX + "/fetch"

    def handler(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "application/json")
        request.write(json.dumps("hello").encode())
        request.finish()

    server.set_route("/fetch", handler)

    ok_response = await page.evaluate(
        "url => fetch(url, { cache: 'no-store', keepalive: true }).then(response => response.json())",
        url,
    )
    assert ok_response == "hello"

    await context.set_offline(True)
    offline_response = await page.evaluate(
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


async def test_BC_025_should_emulate_navigator_on_line(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    assert await page.evaluate("() => window.navigator.onLine") is True
    await context.set_offline(True)
    assert await page.evaluate("() => window.navigator.onLine") is False
    await context.set_offline(False)
    assert await page.evaluate("() => window.navigator.onLine") is True
    await context.close()


async def test_BC_026_should_emulate_navigator_on_line_across_navigations(
    browser: Browser, server: Server, browser_name: str, browser_major_version: int
) -> None:
    if browser_name == "chromium" and browser_major_version < 155:
        pytest.skip("does not survive cross-process navgiation")

    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    assert await page.evaluate("() => window.navigator.onLine") is True
    await context.set_offline(True)
    assert await page.evaluate("() => window.navigator.onLine") is False

    await page.goto("about:blank")
    assert await page.evaluate("() => window.navigator.onLine") is False
    await page.goto("data:text/html,<title>offline</title>")
    assert await page.evaluate("() => window.navigator.onLine") is False

    if browser_name == "chromium":
        # Try a cross-process navigation in Chromium, which allows routing while offline.
        async def handle(route: Route) -> None:
            await route.fulfill(content_type="text/html", body="<html></html>")

        await page.route("**/*", handle)
        await page.goto(server.CROSS_PROCESS_PREFIX + "/empty.html")
        assert await page.evaluate("() => window.navigator.onLine") is False

    await context.set_offline(False)
    assert await page.evaluate("() => window.navigator.onLine") is True
    await context.close()


async def test_BC_027_should_emulate_offline_event(browser: Browser) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    events = await page.evaluate_handle(
        """() => {
          const events = [];
          window.addEventListener('offline', () => events.push('offline'));
          window.addEventListener('online', () => events.push('online'));
          return events;
        }"""
    )
    await context.set_offline(True)
    await poll_until_equal(lambda: events.json_value(), ["offline"])
    await context.set_offline(False)
    await poll_until_equal(lambda: events.json_value(), ["offline", "online"])
    await context.close()


async def test_BC_028_should_emulate_media_in_popup(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context(color_scheme="dark")
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_popup() as popup_info:
        await page.evaluate("url => { window.open(url); }", server.EMPTY_PAGE)
    popup = await popup_info.value
    assert (
        await popup.evaluate(
            "() => matchMedia('(prefers-color-scheme: light)').matches"
        )
        is False
    )
    assert (
        await popup.evaluate("() => matchMedia('(prefers-color-scheme: dark)').matches")
        is True
    )
    await context.close()

    page = await browser.new_page(color_scheme="light")
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_popup() as popup_info:
        await page.evaluate("url => { window.open(url); }", server.EMPTY_PAGE)
    popup = await popup_info.value
    assert (
        await popup.evaluate(
            "() => matchMedia('(prefers-color-scheme: light)').matches"
        )
        is True
    )
    assert (
        await popup.evaluate("() => matchMedia('(prefers-color-scheme: dark)').matches")
        is False
    )
    await page.close()


async def test_BC_029_should_emulate_media_in_cross_process_iframe(
    browser: Browser, server: Server, utils: Utils
) -> None:
    page = await browser.new_page(color_scheme="dark")
    await page.goto(server.EMPTY_PAGE)
    await utils.attach_frame(
        page, "frame1", server.CROSS_PROCESS_PREFIX + "/empty.html"
    )
    frame = page.frames[1]
    assert (
        await frame.evaluate("() => matchMedia('(prefers-color-scheme: dark)').matches")
        is True
    )
    await page.close()


async def test_BC_030_default_user_agent(browser: Browser, page: Page) -> None:
    result = await browser._impl_obj._channel.defaultUserAgentForTest()
    assert await page.evaluate("() => navigator.userAgent") == result["userAgent"]


async def test_BC_031_should_create_two_pages_in_parallel_in_various_contexts(
    browser: Browser,
) -> None:
    context1 = await browser.new_context()
    context2 = await browser.new_context()
    await asyncio.gather(
        context1.new_page(),
        context1.new_page(),
        context2.new_page(),
        context2.new_page(),
    )
    await context1.close()
    await context2.close()
    context3 = await browser.new_context()
    await asyncio.gather(
        context3.new_page(),
        context3.new_page(),
    )
    await context3.close()
