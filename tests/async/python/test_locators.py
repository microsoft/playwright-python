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

"""Python only: tests of behaviors that no upstream test covers."""

import re
import traceback

import pytest

from playwright.async_api import Error, Page
from tests.server import Server


async def test_locators_screenshot_should_respect_timeout(page: Page) -> None:
    page.set_default_timeout(5_000)
    await page.set_content("<div>hello</div>")
    with pytest.raises(Error, match="Locator.screenshot: Timeout 500ms exceeded."):
        await page.locator("#missing").screenshot(timeout=500)


async def test_drag_to_with_position(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        """
      <div style="width:100px;height:100px;background:red;" id="red">
      </div>
      <div style="width:100px;height:100px;background:blue;" id="blue">
      </div>
    """
    )
    events_handle = await page.evaluate_handle(
        """
        () => {
        const events = [];
        document.getElementById('red').addEventListener('mousedown', event => {
            events.push({
            type: 'mousedown',
            x: event.offsetX,
            y: event.offsetY,
            });
        });
        document.getElementById('blue').addEventListener('mouseup', event => {
            events.push({
            type: 'mouseup',
            x: event.offsetX,
            y: event.offsetY,
            });
        });
        return events;
        }
    """
    )
    await page.locator("#red").drag_to(
        page.locator("#blue"),
        source_position={"x": 34, "y": 7},
        target_position={"x": 10, "y": 20},
    )
    assert await events_handle.json_value() == [
        {"type": "mousedown", "x": 34, "y": 7},
        {"type": "mouseup", "x": 10, "y": 20},
    ]


async def test_locators_has_does_not_encode_unicode(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    locators = [
        page.locator("button", has_text="Драматург"),
        page.locator("button", has_text=re.compile("Драматург")),
        page.locator("button", has=page.locator("text=Драматург")),
    ]
    for locator in locators:
        with pytest.raises(Error) as exc_info:
            await locator.click(timeout=1_000)
        assert "Драматург" in exc_info.value.message


async def test_locator_click_timeout_error_should_contain_call_log(page: Page) -> None:
    with pytest.raises(Error) as exc_info:
        await page.get_by_role("button", name="Hello Python").click(timeout=42)
    formatted_exception = "".join(
        traceback.format_exception(type(exc_info.value), value=exc_info.value, tb=None)
    )
    assert "Locator.click: Timeout 42ms exceeded." in formatted_exception
    assert (
        'waiting for get_by_role("button", name="Hello Python")' in formatted_exception
    )
    assert (
        "During handling of the above exception, another exception occurred"
        not in formatted_exception
    )


async def test_locator_should_ignore_deprecated_is_hidden_and_visible_timeout(
    page: Page,
) -> None:
    await page.set_content("<div>foo</div>")
    div = page.locator("div")
    assert await div.is_hidden(timeout=10) is False
    assert await div.is_visible(timeout=10) is True
