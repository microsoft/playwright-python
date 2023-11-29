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
from typing import List

import pytest

from playwright.async_api import ElementHandle, Error, Page
from tests.server import Server


async def give_it_a_chance_to_resolve(page: Page) -> None:
    for i in range(5):
        await page.evaluate(
            "() => new Promise(f => requestAnimationFrame(() => requestAnimationFrame(f)))"
        )


async def wait_for_state(div: ElementHandle, state: str, done: List[bool]) -> None:
    await div.wait_for_element_state(state)  # type: ignore
    done[0] = True


async def wait_for_state_to_throw(
    div: ElementHandle, state: str
) -> pytest.ExceptionInfo[Error]:
    with pytest.raises(Error) as exc_info:
        await div.wait_for_element_state(state)  # type: ignore
    return exc_info


async def test_should_wait_for_visible(page: Page) -> None:
    await page.set_content('<div style="display:none">content</div>')
    div = await page.query_selector("div")
    assert div
    done = [False]
    promise = asyncio.create_task(wait_for_state(div, "visible", done))
    await give_it_a_chance_to_resolve(page)
    assert done[0] is False
    assert div
    await div.evaluate('div => div.style.display = "block"')
    await promise


async def test_should_wait_for_already_visible(page: Page) -> None:
    await page.set_content("<div>content</div>")
    div = await page.query_selector("div")
    assert div
    await div.wait_for_element_state("visible")


async def test_should_timeout_waiting_for_visible(page: Page) -> None:
    await page.set_content('<div style="display:none">content</div>')
    div = await page.query_selector("div")
    assert div
    with pytest.raises(Error) as exc_info:
        await div.wait_for_element_state("visible", timeout=1000)
    assert "Timeout 1000ms exceeded" in exc_info.value.message


async def test_should_throw_waiting_for_visible_when_detached(page: Page) -> None:
    await page.set_content('<div style="display:none">content</div>')
    div = await page.query_selector("div")
    assert div
    promise = asyncio.create_task(wait_for_state_to_throw(div, "visible"))
    await div.evaluate("div => div.remove()")
    exc_info = await promise
    assert "Element is not attached to the DOM" in exc_info.value.message


async def test_should_wait_for_hidden(page: Page) -> None:
    await page.set_content("<div>content</div>")
    div = await page.query_selector("div")
    assert div
    done = [False]
    promise = asyncio.create_task(wait_for_state(div, "hidden", done))
    await give_it_a_chance_to_resolve(page)
    assert done[0] is False
    await div.evaluate('div => div.style.display = "none"')
    await promise


async def test_should_wait_for_already_hidden(page: Page) -> None:
    await page.set_content("<div></div>")
    div = await page.query_selector("div")
    assert div
    await div.wait_for_element_state("hidden")


async def test_should_wait_for_hidden_when_detached(page: Page) -> None:
    await page.set_content("<div>content</div>")
    div = await page.query_selector("div")
    assert div
    done = [False]
    promise = asyncio.create_task(wait_for_state(div, "hidden", done))
    await give_it_a_chance_to_resolve(page)
    assert done[0] is False
    assert div
    await div.evaluate("div => div.remove()")
    await promise


async def test_should_wait_for_enabled_button(page: Page, server: Server) -> None:
    await page.set_content("<button disabled><span>Target</span></button>")
    span = await page.query_selector("text=Target")
    assert span
    done = [False]
    promise = asyncio.create_task(wait_for_state(span, "enabled", done))
    await give_it_a_chance_to_resolve(page)
    assert done[0] is False
    await span.evaluate("span => span.parentElement.disabled = false")
    await promise


async def test_should_throw_waiting_for_enabled_when_detached(page: Page) -> None:
    await page.set_content("<button disabled>Target</button>")
    button = await page.query_selector("button")
    assert button
    promise = asyncio.create_task(wait_for_state_to_throw(button, "enabled"))
    await button.evaluate("button => button.remove()")
    exc_info = await promise
    assert "Element is not attached to the DOM" in exc_info.value.message


async def test_should_wait_for_disabled_button(page: Page) -> None:
    await page.set_content("<button><span>Target</span></button>")
    span = await page.query_selector("text=Target")
    assert span
    done = [False]
    promise = asyncio.create_task(wait_for_state(span, "disabled", done))
    await give_it_a_chance_to_resolve(page)
    assert done[0] is False
    await span.evaluate("span => span.parentElement.disabled = true")
    await promise


async def test_should_wait_for_editable_input(page: Page, server: Server) -> None:
    await page.set_content("<input readonly>")
    input = await page.query_selector("input")
    assert input
    done = [False]
    promise = asyncio.create_task(wait_for_state(input, "editable", done))
    await give_it_a_chance_to_resolve(page)
    assert done[0] is False
    await input.evaluate("input => input.readOnly = false")
    await promise
