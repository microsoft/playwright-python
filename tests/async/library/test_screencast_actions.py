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

"""Port of tests/library/screencast-actions.spec.ts."""

import asyncio
import re
import time
from typing import Any, Awaitable, Callable, Dict

import pytest

from playwright.async_api import Browser, Page, ScreencastActionStyle, expect
from tests.server import Server

STYLE: ScreencastActionStyle = {
    "point": "width: 20px; height: 20px; border-radius: 50%; background: red",
    "highlight": "outline: 2px solid #333",
}


async def run_in_background(
    page: Page, action: Callable[[], Awaitable[Any]]
) -> "asyncio.Future[Any]":
    """Like calling an async function without await: starts the action and goes on.

    The future settles with the result or the error of the action. The page is not used
    here; the sync flavor takes the event loop from it.
    """

    async def run() -> Any:
        try:
            return await action()
        except Exception as error:
            return error

    task = asyncio.ensure_future(run())
    # Let the action send its message, as the JavaScript call does before it returns.
    await asyncio.sleep(0)
    return task


async def poll_until(
    page: Page, predicate: Callable[[], Awaitable[bool]], timeout: float = 5000
) -> None:
    """Like `await expect.poll(...)`: retries until the predicate is true."""
    deadline = time.monotonic() + timeout / 1000
    while not await predicate():
        assert time.monotonic() < deadline, "poll timed out"
        await asyncio.sleep(0.1)


async def test_SC_016_should_show_annotation_on_click(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(server.PREFIX + "/input/button.html")

    await page.screencast.show_actions(duration=5000)
    await run_in_background(page, lambda: page.click("button"))

    await expect(page.locator("x-pw-title")).to_be_visible()
    await expect(page.locator("x-pw-title")).to_have_text(re.compile("click", re.I))
    # Point and highlight are only shown when styled.
    await expect(page.locator("x-pw-screencast-highlight")).to_have_count(0)
    await expect(page.locator("x-pw-screencast-point")).to_have_count(0)

    await context.close()


async def test_SC_017_should_render_annotation_styles(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(server.PREFIX + "/input/button.html")

    await page.screencast.show_actions(
        duration=5000,
        font_size=32,
        style={**STYLE, "title": "top: 100px; background-color: rgb(1, 2, 3)"},
    )
    button_box = await page.locator("button").bounding_box()
    assert button_box
    await run_in_background(page, lambda: page.click("button"))

    # Highlight: styled box that covers the target.
    highlight = page.locator("x-pw-screencast-highlight")
    await expect(highlight).to_be_visible()
    assert await highlight.evaluate("el => getComputedStyle(el).outlineWidth") == "2px"
    box = await highlight.bounding_box()
    assert box
    assert abs(box["x"] - button_box["x"]) < 0.5
    assert abs(box["y"] - button_box["y"]) < 0.5
    assert abs(box["width"] - button_box["width"]) < 0.5
    assert abs(box["height"] - button_box["height"]) < 0.5

    # Point: styled marker centered on the click point, Firefox rounds the click point.
    point_box = await page.locator("x-pw-screencast-point").bounding_box()
    assert point_box
    assert point_box["width"] == 20
    assert abs(point_box["x"] + 10 - (button_box["x"] + button_box["width"] / 2)) <= 1
    assert abs(point_box["y"] + 10 - (button_box["y"] + button_box["height"] / 2)) <= 1

    # Title: style applies on top of deprecated fontSize, position wins over style.
    title = page.locator("x-pw-title")
    await expect(title).to_be_visible()
    title_style = await title.evaluate(
        """el => {
    const cs = getComputedStyle(el);
    return {
      color: cs.color, borderRadius: cs.borderRadius, padding: cs.padding, backgroundColor: cs.backgroundColor,
      top: el.style.top, right: el.style.right, fontSize: el.style.fontSize,
    };
  }"""
    )
    assert title_style["backgroundColor"] == "rgb(1, 2, 3)"
    assert title_style["color"] == "rgb(255, 255, 255)"
    assert title_style["borderRadius"] == "6px"
    assert title_style["padding"] == "6px"
    assert title_style["top"] == "6px"
    assert title_style["right"] == "6px"
    assert title_style["fontSize"] == "32px"

    await context.close()


@pytest.mark.parametrize(
    "position, expected",
    [
        ("top-left", {"top": "6px", "left": "6px"}),
        ("top", {"top": "6px", "left": "50%"}),
        ("bottom-left", {"bottom": "6px", "left": "6px"}),
        ("bottom", {"bottom": "6px", "left": "50%"}),
        ("bottom-right", {"bottom": "6px", "right": "6px"}),
    ],
)
async def test_SC_018_should_position_title_at(
    browser: Browser, server: Server, position: Any, expected: Dict[str, str]
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(server.PREFIX + "/input/button.html")

    await page.screencast.show_actions(duration=5000, position=position)
    await run_in_background(page, lambda: page.click("button"))

    title = page.locator("x-pw-title")
    await expect(title).to_be_visible()

    title_style = await title.evaluate(
        """el => ({
    top: el.style.top,
    bottom: el.style.bottom,
    left: el.style.left,
    right: el.style.right,
  })"""
    )

    for key, value in expected.items():
        assert title_style[key] == value

    await context.close()


async def test_SC_019_should_clear_annotation_after_duration(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(server.PREFIX + "/input/button.html")

    await page.screencast.show_actions(duration=1000, style=STYLE)
    await page.click("button")

    await expect(page.locator("x-pw-screencast-point")).to_have_count(0)
    await expect(page.locator("x-pw-screencast-highlight")).to_have_count(0)
    await expect(page.locator("x-pw-title")).to_be_hidden()

    await context.close()


async def test_SC_020_should_annotate_fill_action(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(server.PREFIX + "/input/textarea.html")

    await page.screencast.show_actions(duration=5000)
    await run_in_background(page, lambda: page.fill("textarea", "hello"))

    title = page.locator("x-pw-title")
    await expect(title).to_be_visible()
    await expect(title).to_have_text(re.compile("fill", re.I))

    await context.close()


async def test_SC_021_should_stop_showing_actions_after_dispose(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(server.PREFIX + "/input/button.html")

    async with await page.screencast.show_actions(duration=1000):
        await page.click("button")

    await page.goto(server.PREFIX + "/input/button.html")
    await page.click("button")

    await expect(page.locator("x-pw-title")).to_be_hidden()

    await context.close()


async def test_SC_022_should_stop_showing_actions_after_hide_actions(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(server.PREFIX + "/input/button.html")

    await page.screencast.show_actions(duration=1000)
    await page.click("button")
    await page.screencast.hide_actions()

    await page.goto(server.PREFIX + "/input/button.html")
    await page.click("button")

    await expect(page.locator("x-pw-title")).to_be_hidden()

    await context.close()


async def test_SC_023_should_render_an_action_cursor_that_animates_to_the_click_point(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(server.PREFIX + "/input/button.html")

    await page.screencast.show_actions(duration=5000)
    await run_in_background(page, lambda: page.click("button"))

    cursor = page.locator("x-pw-action-cursor")
    await expect(cursor).to_be_visible()

    initial = await cursor.evaluate(
        """el => ({
    top: el.style.top,
    left: el.style.left,
  })"""
    )
    assert re.search(r"\d+px", initial["top"])
    assert re.search(r"\d+px", initial["left"])

    await context.close()


async def test_SC_024_cursor_moves_between_two_pointer_actions(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    await page.set_content(
        """
    <div style="position: fixed; top: 20px; left: 20px; width: 60px; height: 60px;" id="a">A</div>
    <div style="position: fixed; bottom: 20px; right: 20px; width: 60px; height: 60px;" id="b">B</div>
  """
    )

    await page.screencast.show_actions(duration=5000)
    cursor = page.locator("x-pw-action-cursor")

    await run_in_background(page, lambda: page.click("#a", force=True))
    await expect(cursor).to_be_visible()
    first = await cursor.evaluate("el => ({ top: el.style.top, left: el.style.left })")

    await run_in_background(page, lambda: page.click("#b", force=True))

    async def moved() -> bool:
        position = await cursor.evaluate(
            "el => ({ top: el.style.top, left: el.style.left })"
        )
        return position != first

    await poll_until(page, moved)

    await context.close()


async def test_SC_025_cursor_none_suppresses_the_action_cursor_decoration(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(server.PREFIX + "/input/button.html")

    await page.screencast.show_actions(duration=5000, cursor="none")
    await run_in_background(page, lambda: page.click("button"))

    # The title still renders, but the cursor does not.
    await expect(page.locator("x-pw-title")).to_be_visible()
    await expect(page.locator("x-pw-action-cursor")).to_be_hidden()

    await context.close()


async def test_SC_026_cursor_stays_at_the_last_action_point_until_hide_actions(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(server.PREFIX + "/input/button.html")

    await page.screencast.show_actions(duration=100)
    await page.click("button")
    await expect(page.locator("x-pw-title")).to_be_hidden()
    cursor = page.locator("x-pw-action-cursor")
    await expect(cursor).to_be_visible()
    position = await cursor.evaluate(
        "el => ({ top: el.style.top, left: el.style.left })"
    )

    await page.goto(server.EMPTY_PAGE)
    await expect(cursor).to_be_visible()
    assert (
        await cursor.evaluate("el => ({ top: el.style.top, left: el.style.left })")
        == position
    )

    await page.screencast.hide_actions()
    await expect(cursor).to_be_hidden()

    await context.close()


async def test_SC_027_should_survive_navigation(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(server.PREFIX + "/input/button.html")

    await page.screencast.show_actions(duration=5000)
    await run_in_background(page, lambda: page.click("button"))

    await expect(page.locator("x-pw-title")).to_be_visible()

    await page.goto(server.PREFIX + "/input/button.html")
    await run_in_background(page, lambda: page.click("button"))

    await expect(page.locator("x-pw-title")).to_be_visible()

    await context.close()
