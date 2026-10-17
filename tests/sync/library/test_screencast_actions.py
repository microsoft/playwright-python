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
from typing import Any, Awaitable, Callable, Dict, TypeVar

import pytest
from greenlet import greenlet

from playwright._impl._greenlets import wait_for_future
from playwright.sync_api import Browser, Page, ScreencastActionStyle, expect
from tests.server import Server

STYLE: ScreencastActionStyle = {
    "point": "width: 20px; height: 20px; border-radius: 50%; background: red",
    "highlight": "outline: 2px solid #333",
}


T = TypeVar("T")


def wait_for(page: Page, awaitable: "Awaitable[T]") -> T:
    """Port of `await promise`: runs the event loop until the awaitable settles."""
    future = asyncio.ensure_future(awaitable, loop=page._loop)
    wait_for_future(page._loop, page._dispatcher_fiber, future)
    return future.result()


def run_in_background(page: Page, action: Callable[[], Any]) -> "asyncio.Future[Any]":
    """Like calling an async function without await: starts the action and goes on.

    The action runs in a greenlet of its own. The future settles with the result or the
    error of the action; wait_for(page, future) waits for it.
    """
    result: "asyncio.Future[Any]" = page._loop.create_future()

    def run() -> None:
        try:
            result.set_result(action())
        except Exception as error:
            result.set_result(error)

    async def start() -> None:
        greenlet(run).switch()

    # start() returns once the action waits for the driver, after it sent its message.
    wait_for(page, start())
    return result


def poll_until(
    page: Page, predicate: Callable[[], bool], timeout: float = 5000
) -> None:
    """Like `await expect.poll(...)`: retries until the predicate is true."""
    deadline = time.monotonic() + timeout / 1000
    while not predicate():
        assert time.monotonic() < deadline, "poll timed out"
        wait_for(page, asyncio.sleep(0.1))


def test_SC_016_should_show_annotation_on_click(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context()
    page = context.new_page()
    page.goto(server.PREFIX + "/input/button.html")

    page.screencast.show_actions(duration=5000)
    run_in_background(page, lambda: page.click("button"))

    expect(page.locator("x-pw-title")).to_be_visible()
    expect(page.locator("x-pw-title")).to_have_text(re.compile("click", re.I))
    # Point and highlight are only shown when styled.
    expect(page.locator("x-pw-screencast-highlight")).to_have_count(0)
    expect(page.locator("x-pw-screencast-point")).to_have_count(0)

    context.close()


def test_SC_017_should_render_annotation_styles(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context()
    page = context.new_page()
    page.goto(server.PREFIX + "/input/button.html")

    page.screencast.show_actions(
        duration=5000,
        font_size=32,
        style={**STYLE, "title": "top: 100px; background-color: rgb(1, 2, 3)"},
    )
    button_box = page.locator("button").bounding_box()
    assert button_box
    run_in_background(page, lambda: page.click("button"))

    # Highlight: styled box that covers the target.
    highlight = page.locator("x-pw-screencast-highlight")
    expect(highlight).to_be_visible()
    assert highlight.evaluate("el => getComputedStyle(el).outlineWidth") == "2px"
    box = highlight.bounding_box()
    assert box
    assert abs(box["x"] - button_box["x"]) < 0.5
    assert abs(box["y"] - button_box["y"]) < 0.5
    assert abs(box["width"] - button_box["width"]) < 0.5
    assert abs(box["height"] - button_box["height"]) < 0.5

    # Point: styled marker centered on the click point, Firefox rounds the click point.
    point_box = page.locator("x-pw-screencast-point").bounding_box()
    assert point_box
    assert point_box["width"] == 20
    assert abs(point_box["x"] + 10 - (button_box["x"] + button_box["width"] / 2)) <= 1
    assert abs(point_box["y"] + 10 - (button_box["y"] + button_box["height"] / 2)) <= 1

    # Title: style applies on top of deprecated fontSize, position wins over style.
    title = page.locator("x-pw-title")
    expect(title).to_be_visible()
    title_style = title.evaluate(
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

    context.close()


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
def test_SC_018_should_position_title_at(
    browser: Browser, server: Server, position: Any, expected: Dict[str, str]
) -> None:
    context = browser.new_context()
    page = context.new_page()
    page.goto(server.PREFIX + "/input/button.html")

    page.screencast.show_actions(duration=5000, position=position)
    run_in_background(page, lambda: page.click("button"))

    title = page.locator("x-pw-title")
    expect(title).to_be_visible()

    title_style = title.evaluate(
        """el => ({
    top: el.style.top,
    bottom: el.style.bottom,
    left: el.style.left,
    right: el.style.right,
  })"""
    )

    for key, value in expected.items():
        assert title_style[key] == value

    context.close()


def test_SC_019_should_clear_annotation_after_duration(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context()
    page = context.new_page()
    page.goto(server.PREFIX + "/input/button.html")

    page.screencast.show_actions(duration=1000, style=STYLE)
    page.click("button")

    expect(page.locator("x-pw-screencast-point")).to_have_count(0)
    expect(page.locator("x-pw-screencast-highlight")).to_have_count(0)
    expect(page.locator("x-pw-title")).to_be_hidden()

    context.close()


def test_SC_020_should_annotate_fill_action(browser: Browser, server: Server) -> None:
    context = browser.new_context()
    page = context.new_page()
    page.goto(server.PREFIX + "/input/textarea.html")

    page.screencast.show_actions(duration=5000)
    run_in_background(page, lambda: page.fill("textarea", "hello"))

    title = page.locator("x-pw-title")
    expect(title).to_be_visible()
    expect(title).to_have_text(re.compile("fill", re.I))

    context.close()


def test_SC_021_should_stop_showing_actions_after_dispose(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context()
    page = context.new_page()
    page.goto(server.PREFIX + "/input/button.html")

    with page.screencast.show_actions(duration=1000):
        page.click("button")

    page.goto(server.PREFIX + "/input/button.html")
    page.click("button")

    expect(page.locator("x-pw-title")).to_be_hidden()

    context.close()


def test_SC_022_should_stop_showing_actions_after_hide_actions(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context()
    page = context.new_page()
    page.goto(server.PREFIX + "/input/button.html")

    page.screencast.show_actions(duration=1000)
    page.click("button")
    page.screencast.hide_actions()

    page.goto(server.PREFIX + "/input/button.html")
    page.click("button")

    expect(page.locator("x-pw-title")).to_be_hidden()

    context.close()


def test_SC_023_should_render_an_action_cursor_that_animates_to_the_click_point(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context()
    page = context.new_page()
    page.goto(server.PREFIX + "/input/button.html")

    page.screencast.show_actions(duration=5000)
    run_in_background(page, lambda: page.click("button"))

    cursor = page.locator("x-pw-action-cursor")
    expect(cursor).to_be_visible()

    initial = cursor.evaluate(
        """el => ({
    top: el.style.top,
    left: el.style.left,
  })"""
    )
    assert re.search(r"\d+px", initial["top"])
    assert re.search(r"\d+px", initial["left"])

    context.close()


def test_SC_024_cursor_moves_between_two_pointer_actions(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context()
    page = context.new_page()
    page.set_content(
        """
    <div style="position: fixed; top: 20px; left: 20px; width: 60px; height: 60px;" id="a">A</div>
    <div style="position: fixed; bottom: 20px; right: 20px; width: 60px; height: 60px;" id="b">B</div>
  """
    )

    page.screencast.show_actions(duration=5000)
    cursor = page.locator("x-pw-action-cursor")

    run_in_background(page, lambda: page.click("#a", force=True))
    expect(cursor).to_be_visible()
    first = cursor.evaluate("el => ({ top: el.style.top, left: el.style.left })")

    run_in_background(page, lambda: page.click("#b", force=True))

    def moved() -> bool:
        position = cursor.evaluate("el => ({ top: el.style.top, left: el.style.left })")
        return position != first

    poll_until(page, moved)

    context.close()


def test_SC_025_cursor_none_suppresses_the_action_cursor_decoration(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context()
    page = context.new_page()
    page.goto(server.PREFIX + "/input/button.html")

    page.screencast.show_actions(duration=5000, cursor="none")
    run_in_background(page, lambda: page.click("button"))

    # The title still renders, but the cursor does not.
    expect(page.locator("x-pw-title")).to_be_visible()
    expect(page.locator("x-pw-action-cursor")).to_be_hidden()

    context.close()


def test_SC_026_cursor_stays_at_the_last_action_point_until_hide_actions(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context()
    page = context.new_page()
    page.goto(server.PREFIX + "/input/button.html")

    page.screencast.show_actions(duration=100)
    page.click("button")
    expect(page.locator("x-pw-title")).to_be_hidden()
    cursor = page.locator("x-pw-action-cursor")
    expect(cursor).to_be_visible()
    position = cursor.evaluate("el => ({ top: el.style.top, left: el.style.left })")

    page.goto(server.EMPTY_PAGE)
    expect(cursor).to_be_visible()
    assert (
        cursor.evaluate("el => ({ top: el.style.top, left: el.style.left })")
        == position
    )

    page.screencast.hide_actions()
    expect(cursor).to_be_hidden()

    context.close()


def test_SC_027_should_survive_navigation(browser: Browser, server: Server) -> None:
    context = browser.new_context()
    page = context.new_page()
    page.goto(server.PREFIX + "/input/button.html")

    page.screencast.show_actions(duration=5000)
    run_in_background(page, lambda: page.click("button"))

    expect(page.locator("x-pw-title")).to_be_visible()

    page.goto(server.PREFIX + "/input/button.html")
    run_in_background(page, lambda: page.click("button"))

    expect(page.locator("x-pw-title")).to_be_visible()

    context.close()
