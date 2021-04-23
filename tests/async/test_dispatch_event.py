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


async def test_should_dispatch_click_event(page, server):
    await page.goto(server.PREFIX + "/input/button.html")
    await page.dispatch_event("button", "click")
    assert await page.evaluate("() => result") == "Clicked"


async def test_should_dispatch_click_event_properties(page, server):
    await page.goto(server.PREFIX + "/input/button.html")
    await page.dispatch_event("button", "click")
    assert await page.evaluate("() => bubbles")
    assert await page.evaluate("() => cancelable")
    assert await page.evaluate("() => composed")


async def test_should_dispatch_click_svg(page):
    await page.set_content(
        """
      <svg height="100" width="100">
        <circle onclick="javascript:window.__CLICKED=42" cx="50" cy="50" r="40" stroke="black" stroke-width="3" fill="red" />
      </svg>
    """
    )
    await page.dispatch_event("circle", "click")
    assert await page.evaluate("() => window.__CLICKED") == 42


async def test_should_dispatch_click_on_a_span_with_an_inline_element_inside(page):
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
    assert await page.evaluate("() => window.CLICKED") == 42


async def test_should_dispatch_click_after_navigation(page, server):
    await page.goto(server.PREFIX + "/input/button.html")
    await page.dispatch_event("button", "click")
    await page.goto(server.PREFIX + "/input/button.html")
    await page.dispatch_event("button", "click")
    assert await page.evaluate("() => result") == "Clicked"


async def test_should_dispatch_click_after_a_cross_origin_navigation(page, server):
    await page.goto(server.PREFIX + "/input/button.html")
    await page.dispatch_event("button", "click")
    await page.goto(server.CROSS_PROCESS_PREFIX + "/input/button.html")
    await page.dispatch_event("button", "click")
    assert await page.evaluate("() => result") == "Clicked"


async def test_should_not_fail_when_element_is_blocked_on_hover(page, server):
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
    assert await page.evaluate("() => window.clicked")


async def test_should_dispatch_click_when_node_is_added_in_shadow_dom(page, server):
    await page.goto(server.EMPTY_PAGE)
    watchdog = page.dispatch_event("span", "click")
    await page.evaluate(
        """() => {
      const div = document.createElement('div');
      div.attachShadow({mode: 'open'});
      document.body.appendChild(div);
    }"""
    )
    await page.evaluate("() => new Promise(f => setTimeout(f, 100))")
    await page.evaluate(
        """() => {
      const span = document.createElement('span');
      span.textContent = 'Hello from shadow';
      span.addEventListener('click', () => window.clicked = true);
      document.querySelector('div').shadowRoot.appendChild(span);
    }"""
    )
    await watchdog
    assert await page.evaluate("() => window.clicked")


async def test_should_be_atomic(selectors, page, utils):
    await utils.register_selector_engine(
        selectors,
        "dispatch_event",
        """{
            create(root, target) { },
            query(root, selector) {
                const result = root.querySelector(selector);
                if (result)
                Promise.resolve().then(() => result.onclick = "");
                return result;
            },
            queryAll(root, selector) {
                const result = Array.from(root.query_selector_all(selector));
                for (const e of result)
                Promise.resolve().then(() => result.onclick = "");
                return result;
            }
        }""",
    )
    await page.set_content('<div onclick="window._clicked=true">Hello</div>')
    await page.dispatch_event("dispatch_event=div", "click")
    assert await page.evaluate("() => window._clicked")


async def test_should_dispatch_drag_drop_events(page, server):
    await page.goto(server.PREFIX + "/drag-n-drop.html")
    dataTransfer = await page.evaluate_handle("() => new DataTransfer()")
    await page.dispatch_event("#source", "dragstart", {"dataTransfer": dataTransfer})
    await page.dispatch_event("#target", "drop", {"dataTransfer": dataTransfer})
    assert await page.evaluate(
        """() => {
      return source.parentElement === target;
    }"""
    )


async def test_should_dispatch_drag_and_drop_events_element_handle(page, server):
    await page.goto(server.PREFIX + "/drag-n-drop.html")
    dataTransfer = await page.evaluate_handle("() => new DataTransfer()")
    source = await page.query_selector("#source")
    await source.dispatch_event("dragstart", {"dataTransfer": dataTransfer})
    target = await page.query_selector("#target")
    await target.dispatch_event("drop", {"dataTransfer": dataTransfer})
    assert await page.evaluate(
        """() => {
      return source.parentElement === target;
    }"""
    )


async def test_should_dispatch_click_event_element_handle(page, server):
    await page.goto(server.PREFIX + "/input/button.html")
    button = await page.query_selector("button")
    await button.dispatch_event("click")
    assert await page.evaluate("() => result") == "Clicked"
