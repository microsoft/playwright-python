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

"""Port of tests/library/tap.spec.ts."""

import asyncio
from typing import Awaitable, Callable, List

import pytest

from playwright.async_api import BrowserContext, ElementHandle, JSHandle, Page
from tests.server import Server, TestServerRequest


@pytest.fixture
async def context(
    context_factory: "Callable[..., Awaitable[BrowserContext]]",
) -> BrowserContext:
    # Port of `it.use({ hasTouch: true })`.
    return await context_factory(has_touch=True)


async def track_events(target: ElementHandle) -> JSHandle:
    return await target.evaluate_handle(
        """target => {
        const events = [];
        for (const event of [
          'mousedown', 'mouseenter', 'mouseleave', 'mousemove', 'mouseout', 'mouseover', 'mouseup', 'click',
          'pointercancel', 'pointerdown', 'pointerenter', 'pointerleave', 'pointermove', 'pointerout', 'pointerover', 'pointerup',
          'touchstart', 'touchend', 'touchmove', 'touchcancel',
        ])
          target.addEventListener(event, () => events.push(event), false);
        return events;
      }"""
    )


async def test_TA_001_should_send_all_of_the_correct_events_smoke(page: Page) -> None:
    await page.set_content(
        """
  <div id="a" style="background: lightblue; width: 50px; height: 50px">a</div>
  <div id="b" style="background: pink; width: 50px; height: 50px">b</div>
"""
    )
    await page.tap("#a")
    target = await page.query_selector("#b")
    assert target
    events_handle = await track_events(target)
    await page.tap("#b")
    # webkit doesn't send pointerenter or pointerleave or mouseout
    assert await events_handle.json_value() == [
        "pointerover",
        "pointerenter",
        "pointerdown",
        "touchstart",
        "pointerup",
        "pointerout",
        "pointerleave",
        "touchend",
        "mouseover",
        "mouseenter",
        "mousemove",
        "mousedown",
        "mouseup",
        "click",
    ]

    await events_handle.evaluate("events => events.length = 0")
    await page.locator("#b").evaluate(
        """target => {
      target.addEventListener('pointerdown', event => event.preventDefault(), { once: true });
    }"""
    )
    await page.tap("#b")
    events = [
        event
        for event in await events_handle.json_value()
        if event in ["pointerdown", "pointerup", "mousedown", "mouseup", "click"]
    ]
    assert events == ["pointerdown", "pointerup", "click"]


async def test_TA_002_trial_run_should_not_tap(page: Page) -> None:
    await page.set_content(
        """
    <div id="a" style="background: lightblue; width: 50px; height: 50px">a</div>
    <div id="b" style="background: pink; width: 50px; height: 50px">b</div>
  """
    )
    await page.tap("#a")
    target = await page.query_selector("#b")
    assert target
    events_handle = await track_events(target)
    await page.tap("#b", trial=True)
    expected = ["pointerover", "pointerenter", "pointerout", "pointerleave"]
    assert await events_handle.json_value() == expected


async def test_TA_003_should_not_send_mouse_events_touchstart_is_canceled(
    page: Page,
) -> None:
    await page.set_content('<div style="width: 50px; height: 50px; background: red">')
    await page.evaluate(
        """() => {
        // touchstart is not cancelable unless passive is false
        document.addEventListener('touchstart', t => t.preventDefault(), { passive: false });
      }"""
    )
    target = await page.query_selector("div")
    assert target
    events_handle = await track_events(target)
    await page.tap("div")
    assert await events_handle.json_value() == [
        "pointerover",
        "pointerenter",
        "pointerdown",
        "touchstart",
        "pointerup",
        "pointerout",
        "pointerleave",
        "touchend",
    ]


async def test_TA_004_should_not_send_mouse_events_when_touchend_is_canceled(
    page: Page,
) -> None:
    await page.set_content('<div style="width: 50px; height: 50px; background: red">')
    await page.evaluate(
        """() => {
        document.addEventListener('touchend', t => t.preventDefault());
      }"""
    )
    target = await page.query_selector("div")
    assert target
    events_handle = await track_events(target)
    await page.tap("div")
    assert await events_handle.json_value() == [
        "pointerover",
        "pointerenter",
        "pointerdown",
        "touchstart",
        "pointerup",
        "pointerout",
        "pointerleave",
        "touchend",
    ]


async def test_TA_005_should_not_wait_for_a_navigation_caused_by_a_tap(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content('<a href="/intercept-this.html">link</a>;')
    # The route never responds, so the navigation never finishes.
    requests: List[TestServerRequest] = []
    server.set_route("/intercept-this.html", requests.append)
    await page.tap("a")
    while not requests:
        await page.wait_for_timeout(50)


async def test_TA_006_should_work_with_modifiers(page: Page) -> None:
    await page.set_content("hello world")

    async def tap() -> None:
        # make sure the evals hit the page
        await page.evaluate("() => void 0")
        await page.tap("body", modifiers=["Alt"])

    alt_key, _ = await asyncio.gather(
        page.evaluate(
            """() => new Promise(resolve => {
            document.addEventListener('touchstart', event => {
              resolve(event.altKey);
            }, { passive: false });
          })"""
        ),
        tap(),
    )
    assert alt_key is True


async def test_TA_007_should_send_well_formed_touch_points(page: Page) -> None:
    async def tap() -> None:
        # make sure the evals hit the page
        await page.evaluate("() => void 0")
        await page.touchscreen.tap(40, 60)

    touchstart, touchend, _ = await asyncio.gather(
        page.evaluate(
            """() => new Promise(resolve => {
            document.addEventListener('touchstart', event => {
              resolve([...event.touches].map(t => ({
                identifier: t.identifier,
                clientX: t.clientX,
                clientY: t.clientY,
                pageX: t.pageX,
                pageY: t.pageY,
                radiusX: 'radiusX' in t ? t.radiusX : t['webkitRadiusX'],
                radiusY: 'radiusY' in t ? t.radiusY : t['webkitRadiusY'],
                rotationAngle: 'rotationAngle' in t ? t.rotationAngle : t['webkitRotationAngle'],
                force: 'force' in t ? t.force : t['webkitForce'],
              })));
            }, false);
          })"""
        ),
        page.evaluate(
            """() => new Promise(resolve => {
            document.addEventListener('touchend', event => {
              resolve([...event.touches].map(t => ({
                identifier: t.identifier,
                clientX: t.clientX,
                clientY: t.clientY,
                pageX: t.pageX,
                pageY: t.pageY,
                radiusX: 'radiusX' in t ? t.radiusX : t['webkitRadiusX'],
                radiusY: 'radiusY' in t ? t.radiusY : t['webkitRadiusY'],
                rotationAngle: 'rotationAngle' in t ? t.rotationAngle : t['webkitRotationAngle'],
                force: 'force' in t ? t.force : t['webkitForce'],
              })));
            }, false);
          })"""
        ),
        tap(),
    )

    assert touchstart == [
        {
            "clientX": 40,
            "clientY": 60,
            "force": 1,
            "identifier": 0,
            "pageX": 40,
            "pageY": 60,
            "radiusX": 1,
            "radiusY": 1,
            "rotationAngle": 0,
        }
    ]
    assert touchend == []


async def test_TA_008_should_wait_until_an_element_is_visible_to_tap_it(
    page: Page,
) -> None:
    div = (
        await page.evaluate_handle(
            """() => {
            const button = document.createElement('button');
            button.textContent = 'not clicked';
            document.body.appendChild(button);
            button.style.display = 'none';
            return button;
          }"""
        )
    ).as_element()
    assert div

    async def show() -> None:
        assert div
        await div.evaluate("div => div.onclick = () => div.textContent = 'clicked'")
        await div.evaluate("div => div.style.display = 'block'")

    await asyncio.gather(div.tap(), show())
    assert await div.text_content() == "clicked"


async def test_TA_009_locators_should_send_all_of_the_correct_events(
    page: Page,
) -> None:
    await page.set_content(
        """
      <div id="a" style="background: lightblue; width: 50px; height: 50px">a</div>
      <div id="b" style="background: pink; width: 50px; height: 50px">b</div>
    """
    )
    await page.locator("#a").tap()
    await page.locator("#b").tap()
