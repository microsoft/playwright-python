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

import pytest

from playwright.async_api import Page


async def test_should_work(page: Page) -> None:
    await page.set_content("<div id=d1 tabIndex=0></div>")
    assert await page.evaluate("() => document.activeElement.nodeName") == "BODY"
    await page.focus("#d1")
    assert await page.evaluate("() => document.activeElement.id") == "d1"


async def test_should_emit_focus_event(page: Page) -> None:
    await page.set_content("<div id=d1 tabIndex=0></div>")
    focused = []
    await page.expose_function("focusEvent", lambda: focused.append(True))
    await page.evaluate("() => d1.addEventListener('focus', focusEvent)")
    await page.focus("#d1")
    assert focused == [True]


async def test_should_emit_blur_event(page: Page) -> None:
    await page.set_content(
        "<div id=d1 tabIndex=0>DIV1</div><div id=d2 tabIndex=0>DIV2</div>"
    )
    await page.focus("#d1")
    focused = []
    blurred = []
    await page.expose_function("focusEvent", lambda: focused.append(True))
    await page.expose_function("blurEvent", lambda: blurred.append(True))
    await page.evaluate("() => d1.addEventListener('blur', blurEvent)")
    await page.evaluate("() => d2.addEventListener('focus', focusEvent)")
    await page.focus("#d2")
    assert focused == [True]
    assert blurred == [True]


async def test_should_traverse_focus(page: Page) -> None:
    await page.set_content('<input id="i1"><input id="i2">')
    focused = []
    await page.expose_function("focusEvent", lambda: focused.append(True))
    await page.evaluate("() => i2.addEventListener('focus', focusEvent)")

    await page.focus("#i1")
    await page.keyboard.type("First")
    await page.keyboard.press("Tab")
    await page.keyboard.type("Last")

    assert focused == [True]
    assert await page.eval_on_selector("#i1", "e => e.value") == "First"
    assert await page.eval_on_selector("#i2", "e => e.value") == "Last"


async def test_should_traverse_focus_in_all_directions(page: Page) -> None:
    await page.set_content('<input value="1"><input value="2"><input value="3">')
    await page.keyboard.press("Tab")
    assert await page.evaluate("() => document.activeElement.value") == "1"
    await page.keyboard.press("Tab")
    assert await page.evaluate("() => document.activeElement.value") == "2"
    await page.keyboard.press("Tab")
    assert await page.evaluate("() => document.activeElement.value") == "3"
    await page.keyboard.press("Shift+Tab")
    assert await page.evaluate("() => document.activeElement.value") == "2"
    await page.keyboard.press("Shift+Tab")
    assert await page.evaluate("() => document.activeElement.value") == "1"


@pytest.mark.only_platform("darwin")
@pytest.mark.only_browser("webkit")
async def test_should_traverse_only_form_elements(page: Page) -> None:
    await page.set_content(
        """
      <input id="input-1">
      <button id="button">button</button>
      <a href id="link">link</a>
      <input id="input-2">
    """
    )
    await page.keyboard.press("Tab")
    assert await page.evaluate("() => document.activeElement.id") == "input-1"
    await page.keyboard.press("Tab")
    assert await page.evaluate("() => document.activeElement.id") == "input-2"
    await page.keyboard.press("Shift+Tab")
    assert await page.evaluate("() => document.activeElement.id") == "input-1"
    await page.keyboard.press("Alt+Tab")
    assert await page.evaluate("() => document.activeElement.id") == "button"
    await page.keyboard.press("Alt+Tab")
    assert await page.evaluate("() => document.activeElement.id") == "link"
    await page.keyboard.press("Alt+Tab")
    assert await page.evaluate("() => document.activeElement.id") == "input-2"
    await page.keyboard.press("Alt+Shift+Tab")
    assert await page.evaluate("() => document.activeElement.id") == "link"
    await page.keyboard.press("Alt+Shift+Tab")
    assert await page.evaluate("() => document.activeElement.id") == "button"
    await page.keyboard.press("Alt+Shift+Tab")
    assert await page.evaluate("() => document.activeElement.id") == "input-1"
