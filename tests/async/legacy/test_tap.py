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

import asyncio
from typing import AsyncGenerator, Optional, cast

import pytest

from playwright.async_api import Browser, BrowserContext, ElementHandle, JSHandle, Page


@pytest.fixture
async def context(browser: Browser) -> AsyncGenerator[BrowserContext, None]:
    context = await browser.new_context(has_touch=True)
    yield context
    await context.close()


async def test_should_send_all_of_the_correct_events(page: Page) -> None:
    await page.set_content(
        """
            <div id="a" style="background: lightblue; width: 50px; height: 50px">a</div>
            <div id="b" style="background: pink; width: 50px; height: 50px">b</div>
        """
    )
    await page.tap("#a")
    element_handle = await track_events(await page.query_selector("#b"))
    await page.tap("#b")
    assert await element_handle.json_value() == [
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


async def test_should_not_send_mouse_events_touchstart_is_canceled(page: Page) -> None:
    await page.set_content("hello world")
    await page.evaluate(
        """() => {
            // touchstart is not cancelable unless passive is false
            document.addEventListener('touchstart', t => t.preventDefault(), {passive: false});
        }"""
    )
    events_handle = await track_events(await page.query_selector("body"))
    await page.tap("body")
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


async def test_should_not_send_mouse_events_touchend_is_canceled(page: Page) -> None:
    await page.set_content("hello world")
    await page.evaluate(
        """() => {
            // touchstart is not cancelable unless passive is false
            document.addEventListener('touchend', t => t.preventDefault());
        }"""
    )
    events_handle = await track_events(await page.query_selector("body"))
    await page.tap("body")
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


async def test_should_work_with_modifiers(page: Page) -> None:
    await page.set_content("hello world")
    alt_key_promise = asyncio.create_task(
        page.evaluate(
            """() => new Promise(resolve => {
                document.addEventListener('touchstart', event => {
                    resolve(event.altKey);
                }, {passive: false});
            })"""
        )
    )
    await asyncio.sleep(0)  # make sure the evals hit the page
    await page.evaluate("""() => void 0""")
    await page.tap("body", modifiers=["Alt"])
    assert await alt_key_promise is True


async def test_should_send_well_formed_touch_points(page: Page) -> None:
    promises = asyncio.gather(
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
    )
    # make sure the evals hit the page
    await page.evaluate("""() => void 0""")
    await page.touchscreen.tap(40, 60)
    [touchstart, touchend] = await promises
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


async def test_should_wait_until_an_element_is_visible_to_tap_it(page: Page) -> None:
    div = cast(
        ElementHandle,
        await page.evaluate_handle(
            """() => {
            const button = document.createElement('button');
            button.textContent = 'not clicked';
            document.body.appendChild(button);
            button.style.display = 'none';
            return button;
        }"""
        ),
    )
    tap_promise = asyncio.create_task(div.tap())
    await asyncio.sleep(0)  # issue tap
    await div.evaluate("""div => div.onclick = () => div.textContent = 'clicked'""")
    await div.evaluate("""div => div.style.display = 'block'""")
    await tap_promise
    assert await div.text_content() == "clicked"


async def test_locators_tap(page: Page) -> None:
    await page.set_content(
        """
        <div id="a" style="background: lightblue; width: 50px; height: 50px">a</div>
        <div id="b" style="background: pink; width: 50px; height: 50px">b</div>
    """
    )
    await page.locator("#a").tap()
    element_handle = await track_events(await page.query_selector("#b"))
    await page.locator("#b").tap()
    assert await element_handle.json_value() == [
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


async def track_events(target: Optional[ElementHandle]) -> JSHandle:
    assert target
    return await target.evaluate_handle(
        """target => {
            const events = [];
            for (const event of [
                'mousedown', 'mouseenter', 'mouseleave', 'mousemove', 'mouseout', 'mouseover', 'mouseup', 'click',
                'pointercancel', 'pointerdown', 'pointerenter', 'pointerleave', 'pointermove', 'pointerout', 'pointerover', 'pointerup',
                'touchstart', 'touchend', 'touchmove', 'touchcancel',])
                target.addEventListener(event, () => events.push(event), false);
            return events;
        }"""
    )
