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

"""Port of tests/library/screencast-overlay.spec.ts."""

import asyncio
import io
import time
from typing import Awaitable, Callable, List, TypeVar

import pytest
from PIL import Image

from playwright._impl._greenlets import wait_for_future
from playwright.sync_api import Browser, Page, expect
from tests.server import Server

T = TypeVar("T")


def wait_for(page: Page, awaitable: "Awaitable[T]") -> T:
    """Port of `await promise`: runs the event loop until the awaitable settles."""
    future = asyncio.ensure_future(awaitable, loop=page._loop)
    wait_for_future(page._loop, page._dispatcher_fiber, future)
    return future.result()


def pixel(screenshot: bytes, x: int, y: int) -> List[int]:
    with Image.open(io.BytesIO(screenshot)) as image:
        png = image.convert("RGBA")
    data = png.tobytes()
    offset = (y * png.width + x) * 4
    return [data[offset], data[offset + 1], data[offset + 2]]


def poll_until(
    page: Page, predicate: Callable[[], bool], timeout: float = 5000
) -> None:
    """Like `await expect.poll(...)`: retries until the predicate is true."""
    deadline = time.monotonic() + timeout / 1000
    while not predicate():
        assert time.monotonic() < deadline, "poll timed out"
        wait_for(page, asyncio.sleep(0.1))


def test_SC_028_should_add_and_remove_overlay(browser: Browser, server: Server) -> None:
    context = browser.new_context()
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)

    with page.screencast.show_overlay('<div id="my-overlay">Hello Overlay</div>'):
        expect(page.locator("x-pw-user-overlays")).to_be_visible()
        expect(page.locator(".x-pw-user-overlay")).to_have_count(1)
        expect(page.locator("#my-overlay")).to_have_text("Hello Overlay")

    expect(page.locator(".x-pw-user-overlay")).to_have_count(0)

    context.close()


def test_SC_029_should_add_multiple_overlays(browser: Browser, server: Server) -> None:
    context = browser.new_context()
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)

    d1 = page.screencast.show_overlay('<div id="overlay-1">First</div>')
    d2 = page.screencast.show_overlay('<div id="overlay-2">Second</div>')
    expect(page.locator(".x-pw-user-overlay")).to_have_count(2)
    expect(page.locator("#overlay-1")).to_have_text("First")
    expect(page.locator("#overlay-2")).to_have_text("Second")

    # Disposes the overlay, like d1.dispose().
    d1.__exit__(None, None, None)
    expect(page.locator(".x-pw-user-overlay")).to_have_count(1)
    expect(page.locator("#overlay-2")).to_have_text("Second")

    d2.__exit__(None, None, None)
    expect(page.locator(".x-pw-user-overlay")).to_have_count(0)

    context.close()


def test_SC_030_should_hide_and_show_overlays(browser: Browser, server: Server) -> None:
    context = browser.new_context()
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)

    page.screencast.show_overlay('<div id="my-overlay">Visible</div>')
    expect(page.locator("x-pw-user-overlays")).to_be_visible()

    page.screencast.hide_overlays()
    expect(page.locator("x-pw-user-overlays")).to_be_hidden()

    page.screencast.show_overlays()
    expect(page.locator("x-pw-user-overlays")).to_be_visible()
    expect(page.locator("#my-overlay")).to_have_text("Visible")

    context.close()


def test_SC_031_should_survive_navigation(browser: Browser, server: Server) -> None:
    context = browser.new_context()
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)

    page.screencast.show_overlay('<div id="persistent">Survives Reload</div>')
    expect(page.locator("#persistent")).to_have_text("Survives Reload")

    page.goto(server.EMPTY_PAGE)
    expect(page.locator("#persistent")).to_have_text("Survives Reload")

    page.reload()
    expect(page.locator("#persistent")).to_have_text("Survives Reload")

    context.close()


def test_SC_032_should_remove_overlay_and_not_restore_after_navigation(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context()
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)

    with page.screencast.show_overlay('<div id="temp">Temporary</div>'):
        expect(page.locator("#temp")).to_have_text("Temporary")

    expect(page.locator(".x-pw-user-overlay")).to_have_count(0)

    page.reload()
    expect(page.locator(".x-pw-user-overlay")).to_have_count(0)

    context.close()


def test_SC_033_should_sanitize_scripts_from_overlay_html(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context()
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)

    page.screencast.show_overlay(
        '<div id="safe">Safe</div><script>window.__injected = true</script>'
    )
    expect(page.locator("#safe")).to_have_text("Safe")
    assert page.evaluate("() => window.__injected") is None

    context.close()


def test_SC_034_should_strip_event_handlers_from_overlay_html(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context()
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)

    page.screencast.show_overlay(
        '<div id="clean" onclick="window.__clicked=true">Click me</div>'
    )
    expect(page.locator("#clean")).to_have_text("Click me")
    has_onclick = page.locator("#clean").evaluate("el => el.hasAttribute('onclick')")
    assert has_onclick is False

    context.close()


def test_SC_035_should_auto_remove_overlay_after_timeout(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context()
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)

    page.screencast.show_overlay('<div id="timed">Temporary</div>', duration=1)
    expect(page.locator(".x-pw-user-overlay")).to_have_count(0)

    context.close()


def test_SC_036_should_allow_styles_in_overlay_html(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context()
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)

    page.screencast.show_overlay(
        '<div id="styled" style="color: red; font-size: 20px;">Styled</div>'
    )
    expect(page.locator("#styled")).to_have_text("Styled")
    color = page.locator("#styled").evaluate("el => getComputedStyle(el).color")
    assert color == "rgb(255, 0, 0)"

    context.close()


TOP_LAYER_PAGES = {
    "dialog": """
    <dialog id="target" style="position: fixed; inset: 0; margin: 0; width: 100vw; height: 100vh; padding: 0; border: 0; background: rgb(200, 200, 200);"></dialog>
    <button onclick="target.showModal()">Open</button>
  """,
    "popover": """
    <div id="target" popover="manual" style="inset: 0; margin: 0; width: 100%; height: 100%; max-width: none; max-height: none; padding: 0; border: 0; background: rgb(200, 200, 200);"></div>
    <button onclick="target.showPopover()">Open</button>
  """,
}
RED_OVERLAY = '<div style="position: absolute; top: 50px; left: 50px; width: 200px; height: 100px; background: rgb(255, 0, 0);"></div>'


@pytest.mark.parametrize("kind", list(TOP_LAYER_PAGES))
def test_SC_037_should_show_overlay_above_opened_before_it(
    browser: Browser, kind: str
) -> None:
    context = browser.new_context()
    page = context.new_page()
    page.set_content(TOP_LAYER_PAGES[kind])
    with page.screencast.show_overlay("<div></div>"):
        pass

    page.get_by_role("button", name="Open").click()
    assert pixel(page.screenshot(), 100, 100) == [200, 200, 200]

    page.screencast.show_overlay(RED_OVERLAY)
    assert pixel(page.screenshot(), 100, 100) == [255, 0, 0]

    context.close()


@pytest.mark.parametrize("kind", list(TOP_LAYER_PAGES))
def test_SC_038_should_keep_overlay_above_opened_after_it(
    browser: Browser, kind: str
) -> None:
    context = browser.new_context()
    page = context.new_page()
    page.set_content(TOP_LAYER_PAGES[kind])
    page.screencast.show_overlay(RED_OVERLAY)
    assert pixel(page.screenshot(), 100, 100) == [255, 0, 0]

    page.get_by_role("button", name="Open").click()

    def is_red() -> bool:
        return pixel(page.screenshot(), 100, 100) == [255, 0, 0]

    poll_until(page, is_red)

    context.close()
