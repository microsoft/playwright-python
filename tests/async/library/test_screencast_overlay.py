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
from typing import Awaitable, Callable, List

import pytest
from PIL import Image

from playwright.async_api import Browser, Page, expect
from tests.server import Server


def pixel(screenshot: bytes, x: int, y: int) -> List[int]:
    with Image.open(io.BytesIO(screenshot)) as image:
        png = image.convert("RGBA")
    data = png.tobytes()
    offset = (y * png.width + x) * 4
    return [data[offset], data[offset + 1], data[offset + 2]]


async def poll_until(
    page: Page, predicate: Callable[[], Awaitable[bool]], timeout: float = 5000
) -> None:
    """Like `await expect.poll(...)`: retries until the predicate is true."""
    deadline = time.monotonic() + timeout / 1000
    while not await predicate():
        assert time.monotonic() < deadline, "poll timed out"
        await asyncio.sleep(0.1)


async def test_SC_028_should_add_and_remove_overlay(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)

    async with await page.screencast.show_overlay(
        '<div id="my-overlay">Hello Overlay</div>'
    ):
        await expect(page.locator("x-pw-user-overlays")).to_be_visible()
        await expect(page.locator(".x-pw-user-overlay")).to_have_count(1)
        await expect(page.locator("#my-overlay")).to_have_text("Hello Overlay")

    await expect(page.locator(".x-pw-user-overlay")).to_have_count(0)

    await context.close()


async def test_SC_029_should_add_multiple_overlays(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)

    d1 = await page.screencast.show_overlay('<div id="overlay-1">First</div>')
    d2 = await page.screencast.show_overlay('<div id="overlay-2">Second</div>')
    await expect(page.locator(".x-pw-user-overlay")).to_have_count(2)
    await expect(page.locator("#overlay-1")).to_have_text("First")
    await expect(page.locator("#overlay-2")).to_have_text("Second")

    # Disposes the overlay, like d1.dispose().
    await d1.__aexit__(None, None, None)
    await expect(page.locator(".x-pw-user-overlay")).to_have_count(1)
    await expect(page.locator("#overlay-2")).to_have_text("Second")

    await d2.__aexit__(None, None, None)
    await expect(page.locator(".x-pw-user-overlay")).to_have_count(0)

    await context.close()


async def test_SC_030_should_hide_and_show_overlays(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)

    await page.screencast.show_overlay('<div id="my-overlay">Visible</div>')
    await expect(page.locator("x-pw-user-overlays")).to_be_visible()

    await page.screencast.hide_overlays()
    await expect(page.locator("x-pw-user-overlays")).to_be_hidden()

    await page.screencast.show_overlays()
    await expect(page.locator("x-pw-user-overlays")).to_be_visible()
    await expect(page.locator("#my-overlay")).to_have_text("Visible")

    await context.close()


async def test_SC_031_should_survive_navigation(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)

    await page.screencast.show_overlay('<div id="persistent">Survives Reload</div>')
    await expect(page.locator("#persistent")).to_have_text("Survives Reload")

    await page.goto(server.EMPTY_PAGE)
    await expect(page.locator("#persistent")).to_have_text("Survives Reload")

    await page.reload()
    await expect(page.locator("#persistent")).to_have_text("Survives Reload")

    await context.close()


async def test_SC_032_should_remove_overlay_and_not_restore_after_navigation(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)

    async with await page.screencast.show_overlay('<div id="temp">Temporary</div>'):
        await expect(page.locator("#temp")).to_have_text("Temporary")

    await expect(page.locator(".x-pw-user-overlay")).to_have_count(0)

    await page.reload()
    await expect(page.locator(".x-pw-user-overlay")).to_have_count(0)

    await context.close()


async def test_SC_033_should_sanitize_scripts_from_overlay_html(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)

    await page.screencast.show_overlay(
        '<div id="safe">Safe</div><script>window.__injected = true</script>'
    )
    await expect(page.locator("#safe")).to_have_text("Safe")
    assert await page.evaluate("() => window.__injected") is None

    await context.close()


async def test_SC_034_should_strip_event_handlers_from_overlay_html(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)

    await page.screencast.show_overlay(
        '<div id="clean" onclick="window.__clicked=true">Click me</div>'
    )
    await expect(page.locator("#clean")).to_have_text("Click me")
    has_onclick = await page.locator("#clean").evaluate(
        "el => el.hasAttribute('onclick')"
    )
    assert has_onclick is False

    await context.close()


async def test_SC_035_should_auto_remove_overlay_after_timeout(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)

    await page.screencast.show_overlay('<div id="timed">Temporary</div>', duration=1)
    await expect(page.locator(".x-pw-user-overlay")).to_have_count(0)

    await context.close()


async def test_SC_036_should_allow_styles_in_overlay_html(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)

    await page.screencast.show_overlay(
        '<div id="styled" style="color: red; font-size: 20px;">Styled</div>'
    )
    await expect(page.locator("#styled")).to_have_text("Styled")
    color = await page.locator("#styled").evaluate("el => getComputedStyle(el).color")
    assert color == "rgb(255, 0, 0)"

    await context.close()


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
async def test_SC_037_should_show_overlay_above_opened_before_it(
    browser: Browser, kind: str
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    await page.set_content(TOP_LAYER_PAGES[kind])
    async with await page.screencast.show_overlay("<div></div>"):
        pass

    await page.get_by_role("button", name="Open").click()
    assert pixel(await page.screenshot(), 100, 100) == [200, 200, 200]

    await page.screencast.show_overlay(RED_OVERLAY)
    assert pixel(await page.screenshot(), 100, 100) == [255, 0, 0]

    await context.close()


@pytest.mark.parametrize("kind", list(TOP_LAYER_PAGES))
async def test_SC_038_should_keep_overlay_above_opened_after_it(
    browser: Browser, kind: str
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    await page.set_content(TOP_LAYER_PAGES[kind])
    await page.screencast.show_overlay(RED_OVERLAY)
    assert pixel(await page.screenshot(), 100, 100) == [255, 0, 0]

    await page.get_by_role("button", name="Open").click()

    async def is_red() -> bool:
        return pixel(await page.screenshot(), 100, 100) == [255, 0, 0]

    await poll_until(page, is_red)

    await context.close()
