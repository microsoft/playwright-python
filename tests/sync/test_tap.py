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

from typing import Generator, Optional

import pytest

from playwright.sync_api import Browser, BrowserContext, ElementHandle, JSHandle, Page


@pytest.fixture
def context(browser: Browser) -> Generator[BrowserContext, None, None]:
    context = browser.new_context(has_touch=True)
    yield context
    context.close()


def test_should_send_all_of_the_correct_events(page: Page) -> None:
    page.set_content(
        """
            <div id="a" style="background: lightblue; width: 50px; height: 50px">a</div>
            <div id="b" style="background: pink; width: 50px; height: 50px">b</div>
        """
    )
    page.tap("#a")
    element_handle = track_events(page.query_selector("#b"))
    page.tap("#b")
    assert element_handle.json_value() == [
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


def test_should_not_send_mouse_events_touchstart_is_canceled(page: Page) -> None:
    page.set_content("hello world")
    page.evaluate(
        """() => {
            // touchstart is not cancelable unless passive is false
            document.addEventListener('touchstart', t => t.preventDefault(), {passive: false});
        }"""
    )
    events_handle = track_events(page.query_selector("body"))
    page.tap("body")
    assert events_handle.json_value() == [
        "pointerover",
        "pointerenter",
        "pointerdown",
        "touchstart",
        "pointerup",
        "pointerout",
        "pointerleave",
        "touchend",
    ]


def test_should_not_send_mouse_events_touchend_is_canceled(page: Page) -> None:
    page.set_content("hello world")
    page.evaluate(
        """() => {
            // touchstart is not cancelable unless passive is false
            document.addEventListener('touchend', t => t.preventDefault());
        }"""
    )
    events_handle = track_events(page.query_selector("body"))
    page.tap("body")
    assert events_handle.json_value() == [
        "pointerover",
        "pointerenter",
        "pointerdown",
        "touchstart",
        "pointerup",
        "pointerout",
        "pointerleave",
        "touchend",
    ]


def track_events(target: Optional[ElementHandle]) -> JSHandle:
    assert target
    return target.evaluate_handle(
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
