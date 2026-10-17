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

"""Port of tests/library/locator-dispatchevent-touch.spec.ts."""

from typing import Callable

import pytest

from playwright.sync_api import BrowserContext, Page
from tests.server import Server


@pytest.fixture
def context(
    context_factory: "Callable[..., BrowserContext]",
) -> BrowserContext:
    # Port of `it.use({ hasTouch: true })`.
    return context_factory(has_touch=True)


def test_TA_010_should_support_touch_points_in_touch_event_arguments(
    page: Page, server: Server, browser_name: str
) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content(
        """
      <div data-testid='outer' style="position: absolute; width: 120px; height: 120px; background-color: red;">
        <div data-testid='inner' style="position: absolute; width: 100px; height: 100px; top: 10px; left: 10px; background-color: green; z-index: 3;">inner</div>
      </div>"""
    )
    outer = page.get_by_test_id("outer")
    outer.evaluate(
        """el => {
        const events = [];
        window.events = events;
        el.addEventListener('touchstart', e => events.push('touchstart: ' + [...e.touches].map(t => `${t.constructor.name}(id: ${t.identifier}, clientX: ${t.clientX}, clientY: ${t.clientY})`)));
        el.addEventListener('touchmove', e => events.push('touchmove: ' + [...e.touches].map(t => `${t.constructor.name}(id: ${t.identifier}, clientX: ${t.clientX}, clientY: ${t.clientY})`)));
        el.addEventListener('touchend', e => events.push('touchend: ' + [...e.touches].map(t => `${t.constructor.name}(id: ${t.identifier}, clientX: ${t.clientX}, clientY: ${t.clientY})`)));
      }"""
    )

    touches = [
        {"identifier": 0, "clientX": 61, "clientY": 60},
        {"identifier": 1, "clientX": 59, "clientY": 60},
    ]
    inner = page.get_by_test_id("inner")
    inner.dispatch_event(
        "touchstart",
        {
            "touches": touches,
            "changedTouches": touches,
            "targetTouches": touches,
        },
    )
    inner.dispatch_event(
        "touchmove",
        {
            "touches": touches,
            "changedTouches": touches,
            "targetTouches": touches,
        },
    )
    inner.dispatch_event(
        "touchend",
        {
            "touches": [],
            "changedTouches": touches,
            "targetTouches": [],
        },
    )
    assert page.evaluate("() => window.events") == [
        "touchstart: Touch(id: 0, clientX: 61, clientY: 60),Touch(id: 1, clientX: 59, clientY: 60)",
        "touchmove: Touch(id: 0, clientX: 61, clientY: 60),Touch(id: 1, clientX: 59, clientY: 60)",
        "touchend: ",
    ]
