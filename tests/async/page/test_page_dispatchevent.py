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

import asyncio

import pytest

from playwright.async_api import Error, Page, Playwright
from tests.server import Server

from ..utils import Utils


async def test_DE_001_should_dispatch_click_event_smoke(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    await page.dispatch_event("button", "click")
    assert await page.evaluate("() => window['result']") == "Clicked"


async def test_DE_002_should_dispatch_click_event_properties(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    await page.dispatch_event("button", "click")
    assert await page.evaluate("bubbles")
    assert await page.evaluate("cancelable")
    assert await page.evaluate("composed")


async def test_DE_003_should_dispatch_click_svg(page: Page) -> None:
    await page.set_content(
        """
    <svg height="100" width="100">
      <circle onclick="javascript:window.__CLICKED=42" cx="50" cy="50" r="40" stroke="black" stroke-width="3" fill="red" />
    </svg>
  """
    )
    await page.dispatch_event("circle", "click")
    assert await page.evaluate("() => window['__CLICKED']") == 42


async def test_DE_004_should_dispatch_click_on_a_span_with_an_inline_element_inside(
    page: Page,
) -> None:
    await page.set_content(
        """
    <style>
    span::before {
      content: 'q';
    }
    </style>
    <span onclick='javascript:window.CLICKED=42'></span>
  """
    )
    await page.dispatch_event("span", "click")
    assert await page.evaluate("() => window['CLICKED']") == 42


async def test_DE_005_should_dispatch_click_after_navigation(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    await page.dispatch_event("button", "click")
    await page.goto(server.PREFIX + "/input/button.html")
    await page.dispatch_event("button", "click")
    assert await page.evaluate("() => window['result']") == "Clicked"


async def test_DE_006_should_dispatch_click_after_a_cross_origin_navigation(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    await page.dispatch_event("button", "click")
    await page.goto(server.CROSS_PROCESS_PREFIX + "/input/button.html")
    await page.dispatch_event("button", "click")
    assert await page.evaluate("() => window['result']") == "Clicked"


async def test_DE_007_should_not_fail_when_element_is_blocked_on_hover(
    page: Page,
) -> None:
    await page.set_content(
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
    await page.dispatch_event("button", "click")
    assert await page.evaluate("() => window['clicked']")


async def test_DE_008_should_dispatch_click_when_node_is_added_in_shadow_dom(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    watchdog = asyncio.create_task(page.dispatch_event("span", "click"))
    await page.evaluate(
        """() => {
    const div = document.createElement('div');
    div.attachShadow({ mode: 'open' });
    document.body.appendChild(div);
  }"""
    )
    await page.wait_for_timeout(100)
    await page.evaluate(
        """() => {
    const span = document.createElement('span');
    span.textContent = 'Hello from shadow';
    span.addEventListener('click', () => window['clicked'] = true);
    document.querySelector('div').shadowRoot.appendChild(span);
  }"""
    )
    await watchdog
    assert await page.evaluate("() => window['clicked']") is True


async def test_DE_009_should_be_atomic(
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
    await utils.register_selector_engine(
        playwright.selectors, "dispatchEvent", create_dummy_selector
    )
    await page.goto('data:text/html,<div onclick="window._clicked=true">Hello</div>')
    await page.dispatch_event("dispatchEvent=div", "click")
    assert await page.evaluate("() => window['_clicked']") is True


async def test_DE_010_should_dispatch_drag_drop_events(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/drag-n-drop.html")
    data_transfer = await page.evaluate_handle("() => new DataTransfer()")
    await page.dispatch_event("#source", "dragstart", {"dataTransfer": data_transfer})
    await page.dispatch_event("#target", "drop", {"dataTransfer": data_transfer})
    source = await page.query_selector("#source")
    target = await page.query_selector("#target")
    assert await page.evaluate(
        """({ source, target }) => {
    return source.parentElement === target;
  }""",
        {"source": source, "target": target},
    )


async def test_DE_011_should_dispatch_drag_drop_events_via_element_handles(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/drag-n-drop.html")
    data_transfer = await page.evaluate_handle("() => new DataTransfer()")
    source = await page.query_selector("#source")
    assert source
    await source.dispatch_event("dragstart", {"dataTransfer": data_transfer})
    target = await page.query_selector("#target")
    assert target
    await target.dispatch_event("drop", {"dataTransfer": data_transfer})
    assert await page.evaluate(
        """({ source, target }) => {
    return source.parentElement === target;
  }""",
        {"source": source, "target": target},
    )


async def test_DE_012_should_dispatch_click_event_via_element_handles(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    button = await page.query_selector("button")
    assert button
    await button.dispatch_event("click")
    assert await page.evaluate("() => window['result']") == "Clicked"


async def test_DE_013_should_dispatch_wheel_event(page: Page, server: Server) -> None:
    # https://github.com/microsoft/playwright/issues/15562
    await page.goto(server.PREFIX + "/input/scrollable.html")
    events_handle = await page.locator("body").evaluate_handle(
        """e => {
    const events = [];
    e.addEventListener('wheel', event => {
      events.push(event);
      console.log(event);
    });
    return events;
  }"""
    )
    await page.locator("body").dispatch_event("wheel", {"deltaX": 100, "deltaY": 200})
    assert await events_handle.evaluate("e => e.length") == 1
    assert await events_handle.evaluate("e => e[0] instanceof WheelEvent")
    assert await events_handle.evaluate(
        "e => ({ deltaX: e[0].deltaX, deltaY: e[0].deltaY })"
    ) == {"deltaX": 100, "deltaY": 200}


async def test_DE_014_should_dispatch_device_orientation_event(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/device-orientation.html")
    await page.locator("html").dispatch_event(
        "deviceorientation", {"alpha": 10, "beta": 20, "gamma": 30}
    )
    assert await page.evaluate("result") == "Oriented"
    assert await page.evaluate("alpha") == 10
    assert await page.evaluate("beta") == 20
    assert await page.evaluate("gamma") == 30
    assert not await page.evaluate("absolute")


async def test_DE_015_should_dispatch_absolute_device_orientation_event(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/device-orientation.html")
    await page.locator("html").dispatch_event(
        "deviceorientationabsolute",
        {"alpha": 10, "beta": 20, "gamma": 30, "absolute": True},
    )
    assert await page.evaluate("result") == "Oriented"
    assert await page.evaluate("alpha") == 10
    assert await page.evaluate("beta") == 20
    assert await page.evaluate("gamma") == 30
    assert await page.evaluate("absolute")


async def test_DE_016_should_dispatch_device_motion_event(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/device-motion.html")
    await page.locator("html").dispatch_event(
        "devicemotion",
        {
            "acceleration": {"x": 10, "y": 20, "z": 30},
            "accelerationIncludingGravity": {"x": 15, "y": 25, "z": 35},
            "rotationRate": {"alpha": 5, "beta": 10, "gamma": 15},
            "interval": 16,
        },
    )
    assert await page.evaluate("result") == "Moved"
    assert await page.evaluate("acceleration.x") == 10
    assert await page.evaluate("acceleration.y") == 20
    assert await page.evaluate("acceleration.z") == 30
    assert await page.evaluate("accelerationIncludingGravity.x") == 15
    assert await page.evaluate("accelerationIncludingGravity.y") == 25
    assert await page.evaluate("accelerationIncludingGravity.z") == 35
    assert await page.evaluate("rotationRate.alpha") == 5
    assert await page.evaluate("rotationRate.beta") == 10
    assert await page.evaluate("rotationRate.gamma") == 15
    assert await page.evaluate("interval") == 16


async def test_DE_017_should_throw_if_argument_is_from_different_frame(
    page: Page, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/28690
    await page.goto(server.PREFIX + "/frames/one-frame.html")
    data_transfer = await page.frames[1].evaluate_handle("() => new DataTransfer()")
    await page.frame_locator("iframe").locator("div").dispatch_event(
        "drop", {"dataTransfer": data_transfer}
    )

    data_transfer = await page.evaluate_handle("() => new DataTransfer()")
    with pytest.raises(Error) as exc_info:
        await page.frame_locator("iframe").locator("div").dispatch_event(
            "drop", {"dataTransfer": data_transfer}
        )
    assert (
        "JSHandles can be evaluated only in the context they were created!"
        in exc_info.value.message
    )
