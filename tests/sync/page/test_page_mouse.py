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
from typing import Any, Callable, Dict, List, Literal

import pytest

from playwright.sync_api import Page
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


def poll_until_equal(
    page: Page,
    actual: Callable[[], Any],
    expected: Any,
    timeout: float = 5000,
) -> None:
    """Port of `expect.poll(actual).toEqual(expected)`."""
    deadline = time.monotonic() + timeout / 1000
    value = actual()
    while value != expected and time.monotonic() < deadline:
        page.wait_for_timeout(100)
        value = actual()
    assert value == expected


def round_half_up(value: float) -> int:
    """Like JavaScript's Math.round()."""
    return math.floor(value + 0.5)


def test_MO_001_should_click_the_document_smoke(page: Page, server: Server) -> None:
    page.evaluate(
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
    page.mouse.click(50, 60)
    event = page.evaluate("() => window['clickPromise']")
    assert event["type"] == "click"
    assert event["detail"] == 1
    assert event["clientX"] == 50
    assert event["clientY"] == 60
    assert event["isTrusted"] is True
    assert event["button"] == 0


def test_MO_002_should_dblclick_the_div(page: Page, server: Server) -> None:
    page.set_content("<div style='width: 100px; height: 100px;'>Click me</div>")
    page.evaluate(
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
    page.mouse.dblclick(50, 60)
    event = page.evaluate("() => window['dblclickPromise']")
    assert event["type"] == "dblclick"
    assert event["detail"] == 2
    assert event["clientX"] == 50
    assert event["clientY"] == 60
    assert event["isTrusted"] is True
    assert event["button"] == 0


def test_MO_003_down_and_up_should_generate_click(page: Page, server: Server) -> None:
    page.evaluate(
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
    page.mouse.move(50, 60)
    page.mouse.down()
    page.mouse.up()
    event = page.evaluate("() => window['clickPromise']")
    assert event["type"] == "click"
    assert event["detail"] == 1
    assert event["clientX"] == 50
    assert event["clientY"] == 60
    assert event["isTrusted"] is True
    assert event["button"] == 0


def test_MO_004_should_pointerdown_the_div_with_a_custom_button(
    page: Page, server: Server, browser_name: str
) -> None:
    page.set_content("<div style='width: 100px; height: 100px;'>Click me</div>")
    page.evaluate(
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
    page.mouse.click(50, 60, button="middle")
    event = page.evaluate("() => window['pointerdownPromise']")
    assert event["type"] == "pointerdown"
    assert event["detail"] == (1 if browser_name == "webkit" else 0)
    assert event["clientX"] == 50
    assert event["clientY"] == 60
    assert event["isTrusted"] is True
    assert event["button"] == 1
    assert event["buttons"] == 4
    assert event["pointerId"] == (0 if browser_name == "firefox" else 1)


def test_MO_005_should_report_correct_buttons_property(page: Page) -> None:
    page.evaluate(
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
    page.mouse.move(50, 60)
    page.mouse.down(button="middle")
    page.mouse.down(button="left")
    page.mouse.up(button="middle")
    page.mouse.up(button="left")
    assert page.evaluate("() => window.__EVENTS") == [
        {"type": "mousedown", "button": 1, "buttons": 4},
        {"type": "mousedown", "button": 0, "buttons": 5},
        {"type": "mouseup", "button": 1, "buttons": 1},
        {"type": "mouseup", "button": 0, "buttons": 0},
    ]


def test_MO_006_should_report_correct_pointer_type_property(page: Page) -> None:
    # https://github.com/microsoft/playwright/issues/38376
    page.mouse.move(50, 60)
    page.evaluate(
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
    page.mouse.move(60, 50)
    page.mouse.down()
    page.mouse.up()
    assert page.evaluate("() => window.__EVENTS") == [
        {"type": "pointermove", "pointerType": "mouse"},
        {"type": "pointerdown", "pointerType": "mouse"},
        {"type": "pointerup", "pointerType": "mouse"},
    ]


def test_MO_007_should_select_the_text_with_mouse(
    page: Page, server: Server, utils: Utils
) -> None:
    page.goto(server.PREFIX + "/input/textarea.html")
    page.focus("textarea")
    text = "This is the text that we are going to try to select. Let's see how it goes."
    page.keyboard.type(text)
    # Firefox needs an extra frame here after typing or it will fail to set the scrollTop
    utils.rafraf(page)
    page.evaluate("() => document.querySelector('textarea').scrollTop = 0")
    dimensions = page.evaluate(DIMENSIONS)
    x = dimensions["x"]
    y = dimensions["y"]
    page.mouse.move(x + 2, y + 2)
    page.mouse.down()
    page.mouse.move(200, 200)
    page.mouse.up()
    assert (
        page.evaluate(
            """() => {
            const textarea = document.querySelector('textarea');
            return textarea.value.substring(textarea.selectionStart, textarea.selectionEnd);
          }"""
        )
        == text
    )


def test_MO_008_should_trigger_hover_state(
    page: Page, server: Server, headless: bool
) -> None:
    if not headless:
        pytest.skip("headed messes up with hover")

    page.goto(server.PREFIX + "/input/scrollable.html")
    page.hover("#button-6")
    assert (
        page.evaluate("() => document.querySelector('button:hover').id") == "button-6"
    )
    page.hover("#button-2")
    assert (
        page.evaluate("() => document.querySelector('button:hover').id") == "button-2"
    )
    page.hover("#button-91")
    assert (
        page.evaluate("() => document.querySelector('button:hover').id") == "button-91"
    )


def test_MO_009_should_trigger_hover_state_on_disabled_button(
    page: Page, server: Server, headless: bool
) -> None:
    if not headless:
        pytest.skip("headed messes up with hover")

    page.goto(server.PREFIX + "/input/scrollable.html")
    page.eval_on_selector("#button-6", "button => button.disabled = true")
    page.hover("#button-6", timeout=5000)
    assert (
        page.evaluate("() => document.querySelector('button:hover').id") == "button-6"
    )


def test_MO_010_should_trigger_hover_state_with_removed_window_node(
    page: Page, server: Server, headless: bool
) -> None:
    if not headless:
        pytest.skip("headed messes up with hover")

    page.goto(server.PREFIX + "/input/scrollable.html")
    page.evaluate("() => delete window.Node")
    page.hover("#button-6")
    assert (
        page.evaluate("() => document.querySelector('button:hover').id") == "button-6"
    )


def test_MO_011_should_set_modifier_keys_on_click(
    page: Page, server: Server, browser_name: str, is_mac: bool
) -> None:
    page.goto(server.PREFIX + "/input/scrollable.html")
    page.evaluate(
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
        page.keyboard.down(modifier)
        page.click("#button-3")
        if not page.evaluate("mod => window['lastEvent'][mod]", modifiers[modifier]):
            raise Exception(modifiers[modifier] + " should be true")
        page.keyboard.up(modifier)
    page.click("#button-3")
    for modifier in modifiers:
        if page.evaluate("mod => window['lastEvent'][mod]", modifiers[modifier]):
            raise Exception(modifiers[modifier] + " should be false")


def test_MO_012_should_tween_mouse_movement(
    page: Page, browser_name: str, headless: bool
) -> None:
    if not headless:
        pytest.skip("actual mouse interferes with the exact mousemove events")

    # The test becomes flaky on WebKit without next line.
    if browser_name == "webkit":
        page.evaluate("() => new Promise(requestAnimationFrame)")
    page.mouse.move(100, 100)
    page.evaluate(
        """() => {
        window['result'] = [];
        document.addEventListener('mousemove', event => {
          window['result'].push([event.clientX, event.clientY]);
        });
      }"""
    )
    page.mouse.move(200, 300, steps=5)
    assert page.evaluate("result") == [
        [120, 140],
        [140, 180],
        [160, 220],
        [180, 260],
        [200, 300],
    ]


def test_MO_013_should_always_round_down(page: Page) -> None:
    page.evaluate(
        """() => {
        document.addEventListener('mousedown', event => {
          window['result'] = [event.clientX, event.clientY];
        });
      }"""
    )
    page.mouse.click(50.1, 50.9)
    assert page.evaluate("result") == [50, 50]


def test_MO_014_should_not_crash_on_mouse_drag_with_any_button(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/16609
    page.evaluate(
        """() => {
        // Do not show contextmenu on right click since it is poorly supported.
        window.addEventListener('contextmenu', e => e.preventDefault(), false);
      }"""
    )
    buttons: List[Literal["left", "middle", "right"]] = ["left", "middle", "right"]
    for button in buttons:
        page.mouse.move(50, 50)
        page.mouse.down(button=button)
        page.mouse.move(100, 100)


def test_MO_015_should_dispatch_mouse_move_after_context_menu_was_opened(
    page: Page, browser_name: str, is_win: bool
) -> None:
    # https://github.com/microsoft/playwright/issues/20823
    if browser_name == "chromium" and is_win:
        pytest.skip("fixme: context menu support is best-effort for Linux and MacOS")
    page.evaluate(
        """() => {
        window['contextMenuPromise'] = new Promise(x => {
          window.addEventListener('contextmenu', x, false);
        });
      }"""
    )
    CX = 100
    CY = 100
    page.mouse.move(CX, CY)
    page.mouse.down(button="right")
    page.evaluate("() => window['contextMenuPromise']")
    N = 20
    for radius in [10, 30, 60, 90]:
        for i in range(N):
            angle = 2 * math.pi * i / N
            x = CX + round_half_up(radius * math.cos(angle))
            y = CY + round_half_up(radius * math.sin(angle))
            page.mouse.move(x, y)


def test_MO_016_should_track_hover_across_iframe_boundaries(
    page: Page, headless: bool
) -> None:
    if not headless:
        pytest.skip("headed messes up with hover")

    page.set_content(
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
    page.wait_for_selector("iframe")
    page.frames[1].wait_for_selector("#childBox")

    def log() -> Any:
        return page.evaluate("() => window['__log']")

    parent_box = page.locator("#parentBox").bounding_box()
    assert parent_box
    iframe_box = page.locator("iframe").bounding_box()
    assert iframe_box
    parent_center = {
        "x": parent_box["x"] + parent_box["width"] / 2,
        "y": parent_box["y"] + parent_box["height"] / 2,
    }
    child_center = {"x": iframe_box["x"] + 90, "y": iframe_box["y"] + 90}

    page.mouse.move(parent_center["x"], parent_center["y"])
    poll_until_equal(page, log, ["parent:enter"])

    # Crossing into the iframe leaves the parent element and enters the child.
    page.mouse.move(child_center["x"], child_center["y"])
    poll_until_equal(page, log, ["parent:enter", "parent:leave", "child:enter"])

    # Crossing back out leaves the child element and re-enters the parent.
    page.mouse.move(parent_center["x"], parent_center["y"])
    poll_until_equal(
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
