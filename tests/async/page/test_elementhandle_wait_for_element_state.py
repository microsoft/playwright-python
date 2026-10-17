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

"""Port of tests/page/elementhandle-wait-for-element-state.spec.ts."""

import asyncio

import pytest

from playwright.async_api import Error, Page
from tests.server import Server

from ..utils import Utils


async def give_it_a_chance_to_resolve(page: Page, utils: Utils) -> None:
    await utils.rafraf(page, 5)


async def test_EH_112_should_wait_for_visible(page: Page, utils: Utils) -> None:
    await page.set_content("<div style='display:none'>content</div>")
    div = await page.query_selector("div")
    assert div
    done = False

    async def wait() -> None:
        nonlocal done
        await div.wait_for_element_state("visible")
        done = True

    async def make_visible() -> None:
        await give_it_a_chance_to_resolve(page, utils)
        assert done is False
        await div.evaluate("div => div.style.display = 'block'")

    await asyncio.gather(wait(), make_visible())


async def test_EH_113_should_wait_for_already_visible(page: Page) -> None:
    await page.set_content("<div>content</div>")
    div = await page.query_selector("div")
    assert div
    await div.wait_for_element_state("visible")


async def test_EH_114_should_timeout_waiting_for_visible(page: Page) -> None:
    await page.set_content("<div style='display:none'>content</div>")
    div = await page.query_selector("div")
    assert div
    with pytest.raises(Error) as exc_info:
        await div.wait_for_element_state("visible", timeout=1000)
    assert "Timeout 1000ms exceeded" in exc_info.value.message


async def test_EH_115_should_throw_waiting_for_visible_when_detached(
    page: Page,
) -> None:
    await page.set_content("<div style='display:none'>content</div>")
    div = await page.query_selector("div")
    assert div

    async def wait() -> None:
        await div.wait_for_element_state("visible")

    async def remove() -> None:
        await div.evaluate("div => div.remove()")

    with pytest.raises(Error) as exc_info:
        await asyncio.gather(wait(), remove())
    assert "Element is not attached to the DOM" in exc_info.value.message


async def test_EH_116_should_wait_for_hidden(page: Page, utils: Utils) -> None:
    await page.set_content("<div>content</div>")
    div = await page.query_selector("div")
    assert div
    done = False

    async def wait() -> None:
        nonlocal done
        await div.wait_for_element_state("hidden")
        done = True

    async def hide() -> None:
        await give_it_a_chance_to_resolve(page, utils)
        assert done is False
        await div.evaluate("div => div.style.display = 'none'")

    await asyncio.gather(wait(), hide())


async def test_EH_117_should_wait_for_already_hidden(page: Page) -> None:
    await page.set_content("<div></div>")
    div = await page.query_selector("div")
    assert div
    await div.wait_for_element_state("hidden")


async def test_EH_118_should_wait_for_hidden_when_detached(
    page: Page, utils: Utils
) -> None:
    await page.set_content("<div>content</div>")
    div = await page.query_selector("div")
    assert div
    done = False

    async def wait() -> None:
        nonlocal done
        await div.wait_for_element_state("hidden")
        done = True

    async def remove() -> None:
        await give_it_a_chance_to_resolve(page, utils)
        assert done is False
        await div.evaluate("div => div.remove()")

    await asyncio.gather(wait(), remove())


async def test_EH_119_should_throw_waiting_for_enabled_when_detached(
    page: Page,
) -> None:
    await page.set_content("<button disabled>Target</button>")
    button = await page.query_selector("button")
    assert button

    async def wait() -> None:
        await button.wait_for_element_state("enabled")

    async def remove() -> None:
        await button.evaluate("button => button.remove()")

    with pytest.raises(Error) as exc_info:
        await asyncio.gather(wait(), remove())
    assert "Element is not attached to the DOM" in exc_info.value.message


async def test_EH_120_should_wait_for_aria_enabled_button(
    page: Page, utils: Utils
) -> None:
    await page.set_content("<button aria-disabled=true><span>Target</span></button>")
    span = await page.query_selector("text=Target")
    assert span
    done = False

    async def wait() -> None:
        nonlocal done
        await span.wait_for_element_state("enabled")
        done = True

    async def enable() -> None:
        await give_it_a_chance_to_resolve(page, utils)
        assert done is False
        await span.evaluate(
            "span => span.parentElement.setAttribute('aria-disabled', 'false')"
        )

    await asyncio.gather(wait(), enable())


async def test_EH_121_should_wait_for_button_with_an_aria_disabled_parent(
    page: Page, utils: Utils
) -> None:
    await page.set_content(
        '<div role="group" aria-disabled=true><button><span>Target</span></button></div>'
    )
    span = await page.query_selector("text=Target")
    assert span
    done = False

    async def wait() -> None:
        nonlocal done
        await span.wait_for_element_state("enabled")
        done = True

    async def enable() -> None:
        await give_it_a_chance_to_resolve(page, utils)
        assert done is False
        await span.evaluate(
            "span => span.parentElement.parentElement.setAttribute('aria-disabled', 'false')"
        )

    await asyncio.gather(wait(), enable())


async def test_EH_122_should_wait_for_stable_position(
    page: Page, server: Server, utils: Utils
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    button = await page.query_selector("button")
    assert button
    await page.eval_on_selector(
        "button",
        """button => {
    button.style.transition = 'margin 10000ms linear 0s';
    button.style.marginLeft = '20000px';
  }""",
    )
    # rafraf for Firefox to kick in the animation.
    await utils.rafraf(page)
    done = False

    async def wait() -> None:
        nonlocal done
        await button.wait_for_element_state("stable")
        done = True

    async def stop() -> None:
        await give_it_a_chance_to_resolve(page, utils)
        assert done is False
        await button.evaluate("button => button.style.transition = ''")

    await asyncio.gather(wait(), stop())


async def test_EH_123_should_wait_for_editable_input(page: Page, utils: Utils) -> None:
    await page.set_content("<input readonly>")
    input = await page.query_selector("input")
    assert input
    done = False

    async def wait() -> None:
        nonlocal done
        await input.wait_for_element_state("editable")
        done = True

    async def make_editable() -> None:
        await give_it_a_chance_to_resolve(page, utils)
        assert done is False
        await input.evaluate("input => input.readOnly = false")

    await asyncio.gather(wait(), make_editable())
