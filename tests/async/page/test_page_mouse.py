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

"""Port of tests/page/page-mouse.spec.ts."""

import math
import time
from typing import Any, Awaitable, Callable, Dict, List, Literal

import pytest

from playwright.async_api import Page
from tests.server import Server

from ..utils import Utils

DIMENSIONS = """() => {
  const rect = document.querySelector('textarea').getBoundingClientRect();
  return {
    x: rect.left,
    y: rect.top,
    width: rect.width,
    height: rect.height
  };
}"""


async def poll_until_equal(
    page: Page,
    actual: Callable[[], Awaitable[Any]],
    expected: Any,
    timeout: float = 5000,
) -> None:
    """Port of `await expect.poll(actual).toEqual(expected)`."""
    deadline = time.monotonic() + timeout / 1000
    value = await actual()
    while value != expected and time.monotonic() < deadline:
        await page.wait_for_timeout(100)
        value = await actual()
    assert value == expected


def round_half_up(value: float) -> int:
    """Like JavaScript's Math.round()."""
    return math.floor(value + 0.5)


async def test_MO_001_should_click_the_document_smoke(
    page: Page, server: Server
) -> None:
    await page.evaluate(
        """() => {
        window['clickPromise'] = new Promise(resolve => {
          document.addEventListener('click', event => {
            resolve({
              type: event.type,
              detail: event.detail,
              clientX: event.clientX,
              clientY: event.clientY,
              isTrusted: event.isTrusted,
              button: event.button
            });
          });
        });
      }"""
    )
    await page.mouse.click(50, 60)
    event = await page.evaluate("() => window['clickPromise']")
    assert event["type"] == "click"
    assert event["detail"] == 1
    assert event["clientX"] == 50
    assert event["clientY"] == 60
    assert event["isTrusted"] is True
    assert event["button"] == 0


async def test_MO_002_should_dblclick_the_div(page: Page, server: Server) -> None:
    await page.set_content("<div style='width: 100px; height: 100px;'>Click me</div>")
    await page.evaluate(
        """() => {
        window['dblclickPromise'] = new Promise(resolve => {
          document.querySelector('div').addEventListener('dblclick', event => {
            resolve({
              type: event.type,
              detail: event.detail,
              clientX: event.clientX,
              clientY: event.clientY,
              isTrusted: event.isTrusted,
              button: event.button,
            });
          });
        });
      }"""
    )
    await page.mouse.dblclick(50, 60)
    event = await page.evaluate("() => window['dblclickPromise']")
    assert event["type"] == "dblclick"
    assert event["detail"] == 2
    assert event["clientX"] == 50
    assert event["clientY"] == 60
    assert event["isTrusted"] is True
    assert event["button"] == 0


async def test_MO_003_down_and_up_should_generate_click(
    page: Page, server: Server
) -> None:
    await page.evaluate(
        """() => {
        window['clickPromise'] = new Promise(resolve => {
          document.addEventListener('click', event => {
            resolve({
              type: event.type,
              detail: event.detail,
              clientX: event.clientX,
              clientY: event.clientY,
              isTrusted: event.isTrusted,
              button: event.button
            });
          });
        });
      }"""
    )
    await page.mouse.move(50, 60)
    await page.mouse.down()
    await page.mouse.up()
    event = await page.evaluate("() => window['clickPromise']")
    assert event["type"] == "click"
    assert event["detail"] == 1
    assert event["clientX"] == 50
    assert event["clientY"] == 60
    assert event["isTrusted"] is True
    assert event["button"] == 0


async def test_MO_004_should_pointerdown_the_div_with_a_custom_button(
    page: Page, server: Server, browser_name: str
) -> None:
    await page.set_content("<div style='width: 100px; height: 100px;'>Click me</div>")
    await page.evaluate(
        """() => {
        window['pointerdownPromise'] = new Promise(resolve => {
          document.querySelector('div').addEventListener('pointerdown', event => {
            resolve({
              type: event.type,
              detail: event.detail,
              clientX: event.clientX,
              clientY: event.clientY,
              isTrusted: event.isTrusted,
              button: event.button,
              buttons: event.buttons,
              pointerId: event.pointerId,
            });
          });
        });
      }"""
    )
    await page.mouse.click(50, 60, button="middle")
    event = await page.evaluate("() => window['pointerdownPromise']")
    assert event["type"] == "pointerdown"
    assert event["detail"] == (1 if browser_name == "webkit" else 0)
    assert event["clientX"] == 50
    assert event["clientY"] == 60
    assert event["isTrusted"] is True
    assert event["button"] == 1
    assert event["buttons"] == 4
    assert event["pointerId"] == (0 if browser_name == "firefox" else 1)


async def test_MO_005_should_report_correct_buttons_property(page: Page) -> None:
    await page.evaluate(
        """() => {
        window.__EVENTS = [];
        const handler = event => {
          window.__EVENTS.push({
            type: event.type,
            button: event.button,
            buttons: event.buttons,
          });
        };
        window.addEventListener('mousedown', handler, false);
        window.addEventListener('mouseup', handler, false);
      }"""
    )
    await page.mouse.move(50, 60)
    await page.mouse.down(button="middle")
    await page.mouse.down(button="left")
    await page.mouse.up(button="middle")
    await page.mouse.up(button="left")
    assert await page.evaluate("() => window.__EVENTS") == [
        {"type": "mousedown", "button": 1, "buttons": 4},
        {"type": "mousedown", "button": 0, "buttons": 5},
        {"type": "mouseup", "button": 1, "buttons": 1},
        {"type": "mouseup", "button": 0, "buttons": 0},
    ]


async def test_MO_006_should_report_correct_pointer_type_property(page: Page) -> None:
    # https://github.com/microsoft/playwright/issues/38376
    await page.mouse.move(50, 60)
    await page.evaluate(
        """() => {
        window.__EVENTS = [];
        const handler = event => {
          window.__EVENTS.push({
            type: event.type,
            pointerType: event.pointerType,
          });
        };
        window.addEventListener('pointerdown', handler, false);
        window.addEventListener('pointermove', handler, false);
        window.addEventListener('pointerup', handler, false);
      }"""
    )
    await page.mouse.move(60, 50)
    await page.mouse.down()
    await page.mouse.up()
    assert await page.evaluate("() => window.__EVENTS") == [
        {"type": "pointermove", "pointerType": "mouse"},
        {"type": "pointerdown", "pointerType": "mouse"},
        {"type": "pointerup", "pointerType": "mouse"},
    ]


async def test_MO_007_should_select_the_text_with_mouse(
    page: Page, server: Server, utils: Utils
) -> None:
    await page.goto(server.PREFIX + "/input/textarea.html")
    await page.focus("textarea")
    text = "This is the text that we are going to try to select. Let's see how it goes."
    await page.keyboard.type(text)
    # Firefox needs an extra frame here after typing or it will fail to set the scrollTop
    await utils.rafraf(page)
    await page.evaluate("() => document.querySelector('textarea').scrollTop = 0")
    dimensions = await page.evaluate(DIMENSIONS)
    x = dimensions["x"]
    y = dimensions["y"]
    await page.mouse.move(x + 2, y + 2)
    await page.mouse.down()
    await page.mouse.move(200, 200)
    await page.mouse.up()
    assert (
        await page.evaluate(
            """() => {
            const textarea = document.querySelector('textarea');
            return textarea.value.substring(textarea.selectionStart, textarea.selectionEnd);
          }"""
        )
        == text
    )


async def test_MO_008_should_trigger_hover_state(
    page: Page, server: Server, headless: bool
) -> None:
    if not headless:
        pytest.skip("headed messes up with hover")

    await page.goto(server.PREFIX + "/input/scrollable.html")
    await page.hover("#button-6")
    assert (
        await page.evaluate("() => document.querySelector('button:hover').id")
        == "button-6"
    )
    await page.hover("#button-2")
    assert (
        await page.evaluate("() => document.querySelector('button:hover').id")
        == "button-2"
    )
    await page.hover("#button-91")
    assert (
        await page.evaluate("() => document.querySelector('button:hover').id")
        == "button-91"
    )


async def test_MO_009_should_trigger_hover_state_on_disabled_button(
    page: Page, server: Server, headless: bool
) -> None:
    if not headless:
        pytest.skip("headed messes up with hover")

    await page.goto(server.PREFIX + "/input/scrollable.html")
    await page.eval_on_selector("#button-6", "button => button.disabled = true")
    await page.hover("#button-6", timeout=5000)
    assert (
        await page.evaluate("() => document.querySelector('button:hover').id")
        == "button-6"
    )


async def test_MO_010_should_trigger_hover_state_with_removed_window_node(
    page: Page, server: Server, headless: bool
) -> None:
    if not headless:
        pytest.skip("headed messes up with hover")

    await page.goto(server.PREFIX + "/input/scrollable.html")
    await page.evaluate("() => delete window.Node")
    await page.hover("#button-6")
    assert (
        await page.evaluate("() => document.querySelector('button:hover').id")
        == "button-6"
    )


async def test_MO_011_should_set_modifier_keys_on_click(
    page: Page, server: Server, browser_name: str, is_mac: bool
) -> None:
    await page.goto(server.PREFIX + "/input/scrollable.html")
    await page.evaluate(
        "() => document.querySelector('#button-3').addEventListener('mousedown', e => window['lastEvent'] = e, true)"
    )
    modifiers: Dict[str, str] = {
        "Shift": "shiftKey",
        "Control": "ctrlKey",
        "Alt": "altKey",
        "Meta": "metaKey",
    }
    # In Firefox, the Meta modifier only exists on Mac
    if browser_name == "firefox" and not is_mac:
        del modifiers["Meta"]
    for modifier in modifiers:
        await page.keyboard.down(modifier)
        await page.click("#button-3")
        if not await page.evaluate(
            "mod => window['lastEvent'][mod]", modifiers[modifier]
        ):
            raise Exception(modifiers[modifier] + " should be true")
        await page.keyboard.up(modifier)
    await page.click("#button-3")
    for modifier in modifiers:
        if await page.evaluate("mod => window['lastEvent'][mod]", modifiers[modifier]):
            raise Exception(modifiers[modifier] + " should be false")


async def test_MO_012_should_tween_mouse_movement(
    page: Page, browser_name: str, headless: bool
) -> None:
    if not headless:
        pytest.skip("actual mouse interferes with the exact mousemove events")

    # The test becomes flaky on WebKit without next line.
    if browser_name == "webkit":
        await page.evaluate("() => new Promise(requestAnimationFrame)")
    await page.mouse.move(100, 100)
    await page.evaluate(
        """() => {
        window['result'] = [];
        document.addEventListener('mousemove', event => {
          window['result'].push([event.clientX, event.clientY, event.movementX, event.movementY]);
        });
      }"""
    )
    await page.mouse.move(200, 300, steps=5)
    assert await page.evaluate("result") == [
        [120, 140, 20, 40],
        [140, 180, 20, 40],
        [160, 220, 20, 40],
        [180, 260, 20, 40],
        [200, 300, 20, 40],
    ]


async def test_MO_013_should_always_round_down(page: Page) -> None:
    await page.evaluate(
        """() => {
        document.addEventListener('mousedown', event => {
          window['result'] = [event.clientX, event.clientY];
        });
      }"""
    )
    await page.mouse.click(50.1, 50.9)
    assert await page.evaluate("result") == [50, 50]


async def test_MO_014_should_not_crash_on_mouse_drag_with_any_button(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/16609
    await page.evaluate(
        """() => {
        // Do not show contextmenu on right click since it is poorly supported.
        window.addEventListener('contextmenu', e => e.preventDefault(), false);
      }"""
    )
    buttons: List[Literal["left", "middle", "right"]] = ["left", "middle", "right"]
    for button in buttons:
        await page.mouse.move(50, 50)
        await page.mouse.down(button=button)
        await page.mouse.move(100, 100)


async def test_MO_015_should_dispatch_mouse_move_after_context_menu_was_opened(
    page: Page, browser_name: str, is_win: bool
) -> None:
    # https://github.com/microsoft/playwright/issues/20823
    if browser_name == "chromium" and is_win:
        pytest.skip("fixme: context menu support is best-effort for Linux and MacOS")
    await page.evaluate(
        """() => {
        window['contextMenuPromise'] = new Promise(x => {
          window.addEventListener('contextmenu', x, false);
        });
      }"""
    )
    CX = 100
    CY = 100
    await page.mouse.move(CX, CY)
    await page.mouse.down(button="right")
    await page.evaluate("() => window['contextMenuPromise']")
    N = 20
    for radius in [10, 30, 60, 90]:
        for i in range(N):
            angle = 2 * math.pi * i / N
            x = CX + round_half_up(radius * math.cos(angle))
            y = CY + round_half_up(radius * math.sin(angle))
            await page.mouse.move(x, y)


async def test_MO_016_should_track_hover_across_iframe_boundaries(
    page: Page, headless: bool
) -> None:
    if not headless:
        pytest.skip("headed messes up with hover")

    await page.set_content(
        """
    <style>
      body, html { margin: 0; padding: 0; }
      #parentBox { position: absolute; left: 10px; top: 10px; width: 100px; height: 100px; }
      iframe { position: absolute; left: 200px; top: 10px; width: 200px; height: 200px; border: none; }
    </style>
    <div id="parentBox"></div>
    <iframe srcdoc="
      <style>body, html { margin: 0; padding: 0; } #childBox { width: 180px; height: 180px; }</style>
      <div id='childBox'></div>
      <script>
        const box = document.querySelector('#childBox');
        box.addEventListener('mouseenter', () => window.top.__log.push('child:enter'));
        box.addEventListener('mouseleave', () => window.top.__log.push('child:leave'));
      </script>
    "></iframe>
    <script>
      window.__log = [];
      const box = document.querySelector('#parentBox');
      box.addEventListener('mouseenter', () => window.__log.push('parent:enter'));
      box.addEventListener('mouseleave', () => window.__log.push('parent:leave'));
    </script>
  """
    )
    await page.wait_for_selector("iframe")
    await page.frames[1].wait_for_selector("#childBox")

    def log() -> Awaitable[Any]:
        return page.evaluate("() => window['__log']")

    parent_box = await page.locator("#parentBox").bounding_box()
    assert parent_box
    iframe_box = await page.locator("iframe").bounding_box()
    assert iframe_box
    parent_center = {
        "x": parent_box["x"] + parent_box["width"] / 2,
        "y": parent_box["y"] + parent_box["height"] / 2,
    }
    child_center = {"x": iframe_box["x"] + 90, "y": iframe_box["y"] + 90}

    await page.mouse.move(parent_center["x"], parent_center["y"])
    await poll_until_equal(page, log, ["parent:enter"])

    # Crossing into the iframe leaves the parent element and enters the child.
    await page.mouse.move(child_center["x"], child_center["y"])
    await poll_until_equal(page, log, ["parent:enter", "parent:leave", "child:enter"])

    # Crossing back out leaves the child element and re-enters the parent.
    await page.mouse.move(parent_center["x"], parent_center["y"])
    await poll_until_equal(
        page,
        log,
        [
            "parent:enter",
            "parent:leave",
            "child:enter",
            "child:leave",
            "parent:enter",
        ],
    )
