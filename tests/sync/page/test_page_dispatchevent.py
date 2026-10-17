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

"""Port of tests/page/page-dispatchevent.spec.ts."""

from typing import Any, Callable, List

import pytest

from playwright.sync_api import Error, Page, Playwright
from tests.server import Server

from ..utils import Utils


def test_DE_001_should_dispatch_click_event_smoke(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/button.html")
    page.dispatch_event("button", "click")
    assert page.evaluate("() => window['result']") == "Clicked"


def test_DE_002_should_dispatch_click_event_properties(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/input/button.html")
    page.dispatch_event("button", "click")
    assert page.evaluate("bubbles")
    assert page.evaluate("cancelable")
    assert page.evaluate("composed")


def test_DE_003_should_dispatch_click_svg(page: Page) -> None:
    page.set_content(
        """
    <svg height="100" width="100">
      <circle onclick="javascript:window.__CLICKED=42" cx="50" cy="50" r="40" stroke="black" stroke-width="3" fill="red" />
    </svg>
  """
    )
    page.dispatch_event("circle", "click")
    assert page.evaluate("() => window['__CLICKED']") == 42


def test_DE_004_should_dispatch_click_on_a_span_with_an_inline_element_inside(
    page: Page,
) -> None:
    page.set_content(
        """
    <style>
    span::before {
      content: 'q';
    }
    </style>
    <span onclick='javascript:window.CLICKED=42'></span>
  """
    )
    page.dispatch_event("span", "click")
    assert page.evaluate("() => window['CLICKED']") == 42


def test_DE_005_should_dispatch_click_after_navigation(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/input/button.html")
    page.dispatch_event("button", "click")
    page.goto(server.PREFIX + "/input/button.html")
    page.dispatch_event("button", "click")
    assert page.evaluate("() => window['result']") == "Clicked"


def test_DE_006_should_dispatch_click_after_a_cross_origin_navigation(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/input/button.html")
    page.dispatch_event("button", "click")
    page.goto(server.CROSS_PROCESS_PREFIX + "/input/button.html")
    page.dispatch_event("button", "click")
    assert page.evaluate("() => window['result']") == "Clicked"


def test_DE_007_should_not_fail_when_element_is_blocked_on_hover(
    page: Page,
) -> None:
    page.set_content(
        """<style>
    container { display: block; position: relative; width: 200px; height: 50px; }
    div, button { position: absolute; left: 0; top: 0; bottom: 0; right: 0; }
    div { pointer-events: none; }
    container:hover div { pointer-events: auto; background: red; }
  </style>
  <container>
    <button onclick="window.clicked=true">Click me</button>
    <div></div>
  </container>"""
    )
    page.dispatch_event("button", "click")
    assert page.evaluate("() => window['clicked']")


def test_DE_008_should_dispatch_click_when_node_is_added_in_shadow_dom(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    page.goto(server.EMPTY_PAGE)

    def watchdog() -> None:
        page.dispatch_event("span", "click")

    def add_span() -> None:
        page.evaluate(
            """() => {
    const div = document.createElement('div');
    div.attachShadow({ mode: 'open' });
    document.body.appendChild(div);
  }"""
        )
        page.wait_for_timeout(100)
        page.evaluate(
            """() => {
    const span = document.createElement('span');
    span.textContent = 'Hello from shadow';
    span.addEventListener('click', () => window['clicked'] = true);
    document.querySelector('div').shadowRoot.appendChild(span);
  }"""
        )

    sync_gather(watchdog, add_span)
    assert page.evaluate("() => window['clicked']") is True


def test_DE_009_should_be_atomic(
    playwright: Playwright, page: Page, utils: Utils
) -> None:
    create_dummy_selector = """({
    query(root, selector) {
      const result = root.querySelector(selector);
      if (result)
        void Promise.resolve().then(() => result.onclick = '');
      return result;
    },
    queryAll(root, selector) {
      const result = Array.from(root.querySelectorAll(selector));
      for (const e of result)
        void Promise.resolve().then(() => e.onclick = null);
      return result;
    }
  })"""
    utils.register_selector_engine(
        playwright.selectors, "dispatchEvent", create_dummy_selector
    )
    page.goto('data:text/html,<div onclick="window._clicked=true">Hello</div>')
    page.dispatch_event("dispatchEvent=div", "click")
    assert page.evaluate("() => window['_clicked']") is True


def test_DE_010_should_dispatch_drag_drop_events(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/drag-n-drop.html")
    data_transfer = page.evaluate_handle("() => new DataTransfer()")
    page.dispatch_event("#source", "dragstart", {"dataTransfer": data_transfer})
    page.dispatch_event("#target", "drop", {"dataTransfer": data_transfer})
    source = page.query_selector("#source")
    target = page.query_selector("#target")
    assert page.evaluate(
        """({ source, target }) => {
    return source.parentElement === target;
  }""",
        {"source": source, "target": target},
    )


def test_DE_011_should_dispatch_drag_drop_events_via_element_handles(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/drag-n-drop.html")
    data_transfer = page.evaluate_handle("() => new DataTransfer()")
    source = page.query_selector("#source")
    assert source
    source.dispatch_event("dragstart", {"dataTransfer": data_transfer})
    target = page.query_selector("#target")
    assert target
    target.dispatch_event("drop", {"dataTransfer": data_transfer})
    assert page.evaluate(
        """({ source, target }) => {
    return source.parentElement === target;
  }""",
        {"source": source, "target": target},
    )


def test_DE_012_should_dispatch_click_event_via_element_handles(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/input/button.html")
    button = page.query_selector("button")
    assert button
    button.dispatch_event("click")
    assert page.evaluate("() => window['result']") == "Clicked"


def test_DE_013_should_dispatch_wheel_event(page: Page, server: Server) -> None:
    # https://github.com/microsoft/playwright/issues/15562
    page.goto(server.PREFIX + "/input/scrollable.html")
    events_handle = page.locator("body").evaluate_handle(
        """e => {
    const events = [];
    e.addEventListener('wheel', event => {
      events.push(event);
      console.log(event);
    });
    return events;
  }"""
    )
    page.locator("body").dispatch_event("wheel", {"deltaX": 100, "deltaY": 200})
    assert events_handle.evaluate("e => e.length") == 1
    assert events_handle.evaluate("e => e[0] instanceof WheelEvent")
    assert events_handle.evaluate(
        "e => ({ deltaX: e[0].deltaX, deltaY: e[0].deltaY })"
    ) == {"deltaX": 100, "deltaY": 200}


def test_DE_014_should_dispatch_device_orientation_event(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/device-orientation.html")
    page.locator("html").dispatch_event(
        "deviceorientation", {"alpha": 10, "beta": 20, "gamma": 30}
    )
    assert page.evaluate("result") == "Oriented"
    assert page.evaluate("alpha") == 10
    assert page.evaluate("beta") == 20
    assert page.evaluate("gamma") == 30
    assert not page.evaluate("absolute")


def test_DE_015_should_dispatch_absolute_device_orientation_event(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/device-orientation.html")
    page.locator("html").dispatch_event(
        "deviceorientationabsolute",
        {"alpha": 10, "beta": 20, "gamma": 30, "absolute": True},
    )
    assert page.evaluate("result") == "Oriented"
    assert page.evaluate("alpha") == 10
    assert page.evaluate("beta") == 20
    assert page.evaluate("gamma") == 30
    assert page.evaluate("absolute")


def test_DE_016_should_dispatch_device_motion_event(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/device-motion.html")
    page.locator("html").dispatch_event(
        "devicemotion",
        {
            "acceleration": {"x": 10, "y": 20, "z": 30},
            "accelerationIncludingGravity": {"x": 15, "y": 25, "z": 35},
            "rotationRate": {"alpha": 5, "beta": 10, "gamma": 15},
            "interval": 16,
        },
    )
    assert page.evaluate("result") == "Moved"
    assert page.evaluate("acceleration.x") == 10
    assert page.evaluate("acceleration.y") == 20
    assert page.evaluate("acceleration.z") == 30
    assert page.evaluate("accelerationIncludingGravity.x") == 15
    assert page.evaluate("accelerationIncludingGravity.y") == 25
    assert page.evaluate("accelerationIncludingGravity.z") == 35
    assert page.evaluate("rotationRate.alpha") == 5
    assert page.evaluate("rotationRate.beta") == 10
    assert page.evaluate("rotationRate.gamma") == 15
    assert page.evaluate("interval") == 16


def test_DE_017_should_throw_if_argument_is_from_different_frame(
    page: Page, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/28690
    page.goto(server.PREFIX + "/frames/one-frame.html")
    data_transfer = page.frames[1].evaluate_handle("() => new DataTransfer()")
    page.frame_locator("iframe").locator("div").dispatch_event(
        "drop", {"dataTransfer": data_transfer}
    )

    data_transfer = page.evaluate_handle("() => new DataTransfer()")
    with pytest.raises(Error) as exc_info:
        page.frame_locator("iframe").locator("div").dispatch_event(
            "drop", {"dataTransfer": data_transfer}
        )
    assert (
        "JSHandles can be evaluated only in the context they were created!"
        in exc_info.value.message
    )
