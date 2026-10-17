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

"""Port of tests/library/popup.spec.ts."""


import asyncio
from typing import Any, Awaitable, Callable, Dict, List, Optional, TypeVar

import pytest

from playwright._impl._greenlets import wait_for_future
from playwright.sync_api import Browser, Page, Route
from tests.server import Server

T = TypeVar("T")


def wait_for(page: Page, awaitable: "Awaitable[T]") -> T:
    """Port of `await promise`: runs the event loop until the awaitable settles."""
    future = asyncio.ensure_future(awaitable)
    wait_for_future(page._loop, page._dispatcher_fiber, future)
    return future.result()


def test_PO_014_should_inherit_user_agent_from_browser_context_smoke(
    browser: Browser, server: Server, is_frozen_webkit: bool
) -> None:
    if is_frozen_webkit:
        pytest.skip("frozen WebKit")

    context = browser.new_context(user_agent="hey")
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)
    page.set_content('<a target=_blank rel=noopener href="/popup/popup.html">link</a>')
    request_task = asyncio.ensure_future(server.wait_for_request("/popup/popup.html"))
    with context.expect_page() as popup_info:
        page.click("a")
    popup = popup_info.value
    popup.wait_for_load_state("domcontentloaded")
    user_agent = popup.evaluate("() => window['initialUserAgent']")
    request = wait_for(page, request_task)
    context.close()
    assert user_agent == "hey"
    assert request.getHeader("user-agent") == "hey"


def test_PO_015_should_respect_routes_from_browser_context(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context()
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)
    page.set_content('<a target=_blank rel=noopener href="empty.html">link</a>')
    intercepted = False

    def handle(route: Route) -> None:
        nonlocal intercepted
        # The sync continue_() waits, so the flag is set first.
        intercepted = True
        route.continue_()

    context.route("**/empty.html", handle)
    with context.expect_page():
        page.click("a")
    context.close()
    assert intercepted is True


def test_PO_016_should_inherit_extra_headers_from_browser_context(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context(extra_http_headers={"foo": "bar"})
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)
    request_task = asyncio.ensure_future(server.wait_for_request("/dummy.html"))
    page.evaluate(
        "url => window['_popup'] = window.open(url)", server.PREFIX + "/dummy.html"
    )
    request = wait_for(page, request_task)
    context.close()
    assert request.getHeader("foo") == "bar"


def test_PO_017_should_inherit_offline_from_browser_context(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context()
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)
    context.set_offline(True)
    online = page.evaluate(
        """url => {
    const win = window.open(url);
    return win.navigator.onLine;
  }""",
        server.PREFIX + "/dummy.html",
    )
    context.close()
    assert online is False


def test_PO_018_should_inherit_http_credentials_from_browser_context(
    browser: Browser, server: Server
) -> None:
    server.set_auth("/title.html", "user", "pass")
    context = browser.new_context(
        http_credentials={"username": "user", "password": "pass"}
    )
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)
    with page.expect_popup() as popup_info:
        page.evaluate(
            "url => window['_popup'] = window.open(url)", server.PREFIX + "/title.html"
        )
    popup = popup_info.value
    popup.wait_for_load_state("domcontentloaded")
    assert popup.title() == "Woof-Woof"
    context.close()


def test_PO_019_should_inherit_touch_support_from_browser_context(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context(
        viewport={"width": 400, "height": 500}, has_touch=True
    )
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)
    has_touch = page.evaluate(
        """() => {
    const win = window.open('');
    return 'ontouchstart' in win;
  }"""
    )
    context.close()
    assert has_touch is True


def test_PO_020_should_inherit_viewport_size_from_browser_context(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context(viewport={"width": 400, "height": 500})
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)
    size = page.evaluate(
        """() => {
    const win = window.open('about:blank');
    return { width: win.innerWidth, height: win.innerHeight };
  }"""
    )
    context.close()
    assert size == {"width": 400, "height": 500}


def test_PO_021_should_use_viewport_size_from_window_features(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context(viewport={"width": 700, "height": 700})
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)
    with page.expect_popup() as popup_info:
        size = page.evaluate(
            """async () => {
      const win = window.open(window.location.href, 'Title', 'toolbar=no,location=no,directories=no,status=no,menubar=no,scrollbars=yes,resizable=yes,width=600,height=300,top=0,left=0');
      await new Promise(resolve => {
        const interval = window.builtins.setInterval(() => {
          if (win.innerWidth === 600 && win.innerHeight === 300) {
            window.builtins.clearInterval(interval);
            resolve();
          }
        }, 10);
      });
      return { width: win.innerWidth, height: win.innerHeight };
    }"""
        )
    popup = popup_info.value
    popup.set_viewport_size({"width": 500, "height": 400})
    popup.wait_for_load_state()
    resized = popup.evaluate(
        "() => ({ width: window.innerWidth, height: window.innerHeight })"
    )
    context.close()
    assert size == {"width": 600, "height": 300}
    assert resized == {"width": 500, "height": 400}


def test_PO_022_should_respect_routes_from_browser_context_when_using_window_open(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context()
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)
    intercepted = False

    def handle(route: Route) -> None:
        nonlocal intercepted
        # The sync continue_() waits, so the flag is set first.
        intercepted = True
        route.continue_()

    context.route("**/empty.html", handle)
    with page.expect_popup():
        page.evaluate("url => window['__popup'] = window.open(url)", server.EMPTY_PAGE)
    assert intercepted is True
    context.close()


def test_PO_023_browser_context_add_init_script_should_apply_to_an_in_process_popup(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context()
    context.add_init_script("window['injected'] = 123")
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)
    injected = page.evaluate(
        """() => {
    const win = window.open('about:blank');
    return win['injected'];
  }"""
    )
    context.close()
    assert injected == 123


def test_PO_024_browser_context_add_init_script_should_apply_to_a_cross_process_popup(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context()
    context.add_init_script("window['injected'] = 123")
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)
    with page.expect_popup() as popup_info:
        page.evaluate(
            "url => window.open(url)", server.CROSS_PROCESS_PREFIX + "/title.html"
        )
    popup = popup_info.value
    assert popup.evaluate("injected") == 123
    popup.reload()
    assert popup.evaluate("injected") == 123
    context.close()


def test_PO_025_should_expose_function_from_browser_context(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context()
    messages: List[str] = []

    def add(a: int, b: int) -> int:
        messages.append("binding")
        return a + b

    context.expose_function("add", add)
    page = context.new_page()
    context.on("page", lambda _: messages.append("page"))
    page.goto(server.EMPTY_PAGE)
    added = page.evaluate(
        """async () => {
    const win = window.open('about:blank');
    return win['add'](9, 4);
  }"""
    )
    context.close()
    assert added == 13
    assert "|".join(messages) == "page|binding"


def test_PO_026_should_not_dispatch_binding_on_a_closed_page(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context()
    was_closed: Optional[bool] = None

    def add(source: Dict[str, Any], a: int, b: int) -> int:
        nonlocal was_closed
        was_closed = source["page"].is_closed()
        return a + b

    context.expose_binding("add", add)
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)
    with page.expect_popup():
        page.evaluate(
            """async () => {
      const win = window.open('about:blank');
      win['add'](9, 4);
      win.close();
    }"""
        )
    # Give it a chance to dispatch the binding on the closed page.
    page.wait_for_timeout(1000)
    context.close()
    assert not was_closed


def test_PO_027_should_not_throttle_r_af_in_the_opener_page(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    page.goto(server.EMPTY_PAGE)
    with page.expect_popup() as popup_info:
        page.evaluate("() => { window.open('about:blank'); }")
    popup = popup_info.value
    sync_gather(lambda: wait_for_rafs(page, 30), lambda: wait_for_rafs(popup, 30))


def test_PO_028_should_not_throw_when_click_closes_popup(
    browser_name: str, page: Page, server: Server
) -> None:
    if browser_name == "firefox":
        pytest.skip(
            "fixme: locator.click: Target page, context or browser has been closed"
        )

    page.goto(server.EMPTY_PAGE)
    with page.expect_popup() as popup_info:
        page.evaluate(
            """async browserName => {
      const w = window.open('about:blank');
      if (browserName === 'firefox')
        await new Promise(x => w.onload = x);
      w.document.body.innerHTML = `<button onclick="window.close()">close</button>`;
    }""",
            browser_name,
        )
    popup = popup_info.value
    popup.get_by_role("button").click()


def wait_for_rafs(page: Page, count: int) -> None:
    page.evaluate(
        """count => new Promise(resolve => {
    const onRaf = () => {
      --count;
      if (!count)
        resolve();
      else
        window.builtins.requestAnimationFrame(onRaf);
    };
    window.builtins.requestAnimationFrame(onRaf);
  })""",
        count,
    )
