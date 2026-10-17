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

"""Port of tests/page/wheel.spec.ts."""

import time
from typing import Any, Dict

import pytest

from playwright.sync_api import Page
from tests.server import Server

from ..utils import Utils


@pytest.fixture
def ignore_delta(browser_name: str, platform: str) -> bool:
    # Chromium reports deltaX/deltaY scaled by host device scale factor.
    # https://bugs.chromium.org/p/chromium/issues/detail?id=1324819
    # https://github.com/microsoft/playwright/issues/7362
    # Different bots have different scale factors (usually 1 or 2), so we just ignore the values
    # instead of guessing the host scale factor.
    return browser_name == "chromium" and platform == "darwin"


def expect_event(
    page: Page, expected: Dict[str, Any], ignore_delta: bool, timeout: float = 5000
) -> None:
    # Port of `expect.poll(() => page.evaluate('window.lastEvent')).toBeTruthy()`.
    deadline = time.monotonic() + timeout / 1000
    received = page.evaluate("window.lastEvent")
    while not received and time.monotonic() < deadline:
        page.wait_for_timeout(100)
        received = page.evaluate("window.lastEvent")
    assert received
    if ignore_delta:
        del received["deltaX"]
        del received["deltaY"]
        del expected["deltaX"]
        del expected["deltaY"]
    assert received == expected


def listen_for_wheel_events(page: Page, selector: str) -> None:
    page.evaluate(
        """selector => {
        document.querySelector(selector).addEventListener('wheel', event => {
          const e = event;
          window['lastEvent'] = {
            deltaX: e.deltaX,
            deltaY: e.deltaY,
            clientX: e.clientX,
            clientY: e.clientY,
            deltaMode: e.deltaMode,
            ctrlKey: e.ctrlKey,
            shiftKey: e.shiftKey,
            altKey: e.altKey,
            metaKey: e.metaKey,
          };
        }, { passive: false });
      }""",
        selector,
    )


def test_MO_017_should_dispatch_wheel_events_smoke(
    page: Page, server: Server, ignore_delta: bool
) -> None:
    page.set_content('<div style="width: 5000px; height: 5000px;"></div>')
    page.mouse.move(50, 60)
    listen_for_wheel_events(page, "div")
    page.mouse.wheel(0, 100)
    page.wait_for_function("window.scrollY === 100")
    expect_event(
        page,
        {
            "deltaX": 0,
            "deltaY": 100,
            "clientX": 50,
            "clientY": 60,
            "deltaMode": 0,
            "ctrlKey": False,
            "shiftKey": False,
            "altKey": False,
            "metaKey": False,
        },
        ignore_delta,
    )


def test_MO_018_should_dispatch_wheel_events_after_popup_was_opened_smoke(
    page: Page, server: Server, ignore_delta: bool
) -> None:
    page.set_content(
        """
    <div style="width: 5000px; height: 5000px;"></div>
  """
    )
    page.mouse.move(50, 60)
    listen_for_wheel_events(page, "div")
    with page.expect_popup():
        page.evaluate("() => window.open('')")
    page.mouse.wheel(0, 100)
    page.wait_for_function("window.scrollY === 100")
    expect_event(
        page,
        {
            "deltaX": 0,
            "deltaY": 100,
            "clientX": 50,
            "clientY": 60,
            "deltaMode": 0,
            "ctrlKey": False,
            "shiftKey": False,
            "altKey": False,
            "metaKey": False,
        },
        ignore_delta,
    )


def test_MO_019_should_dispatch_wheel_event_on_svg_element(
    page: Page, browser_name: str, headless: bool, is_linux: bool, ignore_delta: bool
) -> None:
    # https://github.com/microsoft/playwright/issues/15566
    page.set_content(
        """
    <body>
      <svg class="scroll-box"></svg>
    </body>
    <style>
      .scroll-box {
        position: absolute;
        top: 0px;
        left: 0px;
        background-color: brown;
        width: 200px;
        height: 200px;
      }
    </style>"""
    )
    listen_for_wheel_events(page, "svg")
    page.mouse.move(100, 100)
    page.mouse.wheel(0, 100)
    page.wait_for_function("!!window.lastEvent")
    expect_event(
        page,
        {
            "deltaX": 0,
            "deltaY": 100,
            "clientX": 100,
            "clientY": 100,
            "deltaMode": 0,
            "ctrlKey": False,
            "shiftKey": False,
            "altKey": False,
            "metaKey": False,
        },
        ignore_delta,
    )


def test_MO_020_should_scroll_when_nobody_is_listening(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/input/scrollable.html")
    page.mouse.move(50, 60)
    page.mouse.wheel(0, 100)
    page.wait_for_function("window.scrollY === 100")


def test_MO_021_should_set_the_modifiers(page: Page, ignore_delta: bool) -> None:
    page.set_content('<div style="width: 5000px; height: 5000px;"></div>')
    page.mouse.move(50, 60)
    listen_for_wheel_events(page, "div")
    page.keyboard.down("Shift")
    page.mouse.wheel(0, 100)
    expect_event(
        page,
        {
            "deltaX": 0,
            "deltaY": 100,
            "clientX": 50,
            "clientY": 60,
            "deltaMode": 0,
            "ctrlKey": False,
            "shiftKey": True,
            "altKey": False,
            "metaKey": False,
        },
        ignore_delta,
    )


def test_MO_022_should_scroll_horizontally(page: Page, ignore_delta: bool) -> None:
    page.set_content('<div style="width: 5000px; height: 5000px;"></div>')
    page.mouse.move(50, 60)
    listen_for_wheel_events(page, "div")
    page.mouse.wheel(100, 0)
    expect_event(
        page,
        {
            "deltaX": 100,
            "deltaY": 0,
            "clientX": 50,
            "clientY": 60,
            "deltaMode": 0,
            "ctrlKey": False,
            "shiftKey": False,
            "altKey": False,
            "metaKey": False,
        },
        ignore_delta,
    )
    page.wait_for_function("window.scrollX === 100")


def test_MO_023_should_work_when_the_event_is_canceled(
    page: Page, utils: Utils, ignore_delta: bool
) -> None:
    page.set_content('<div style="width: 5000px; height: 5000px;"></div>')
    page.mouse.move(50, 60)
    listen_for_wheel_events(page, "div")
    page.evaluate(
        """() => {
        document.querySelector('div').addEventListener('wheel', e => e.preventDefault());
      }"""
    )
    # Give wheel listener a chance to propagate through all the layers in Firefox.
    utils.rafraf(page, 10)
    page.mouse.wheel(0, 100)
    expect_event(
        page,
        {
            "deltaX": 0,
            "deltaY": 100,
            "clientX": 50,
            "clientY": 60,
            "deltaMode": 0,
            "ctrlKey": False,
            "shiftKey": False,
            "altKey": False,
            "metaKey": False,
        },
        ignore_delta,
    )
    # Give the page a chance to scroll.
    page.wait_for_function("!!window['lastEvent']")
    # Ensure that it did not.
    assert page.evaluate("window.scrollY") == 0
