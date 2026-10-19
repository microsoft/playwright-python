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

"""Port of tests/page/elementhandle-misc.spec.ts."""

from playwright.async_api import Page
from tests.server import Server


async def test_EH_045_should_hover(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/scrollable.html")
    button = await page.query_selector("#button-6")
    assert button
    await button.hover()
    assert (
        await page.evaluate("() => document.querySelector('button:hover').id")
        == "button-6"
    )


async def test_EH_046_should_hover_when_node_is_removed(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/scrollable.html")
    await page.evaluate("() => delete window['Node']")
    button = await page.query_selector("#button-6")
    assert button
    await button.hover()
    assert (
        await page.evaluate("() => document.querySelector('button:hover').id")
        == "button-6"
    )


async def test_EH_047_should_fill_input(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/textarea.html")
    handle = await page.query_selector("input")
    assert handle
    await handle.fill("some value")
    assert await page.evaluate("() => window['result']") == "some value"


async def test_EH_048_should_fill_input_when_node_is_removed(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/textarea.html")
    await page.evaluate("() => delete window['Node']")
    handle = await page.query_selector("input")
    assert handle
    await handle.fill("some value")
    assert await page.evaluate("() => window['result']") == "some value"


async def test_EH_049_should_check_the_box(page: Page) -> None:
    await page.set_content("<input id='checkbox' type='checkbox'></input>")
    input = await page.query_selector("input")
    assert input
    await input.check()
    assert await page.evaluate("checkbox.checked") is True


async def test_EH_050_should_check_the_box_using_set_checked(page: Page) -> None:
    await page.set_content("<input id='checkbox' type='checkbox'></input>")
    input = await page.query_selector("input")
    assert input
    await input.set_checked(True)
    assert await page.evaluate("checkbox.checked") is True
    await input.set_checked(False)
    assert await page.evaluate("checkbox.checked") is False


async def test_EH_051_should_uncheck_the_box(page: Page) -> None:
    await page.set_content("<input id='checkbox' type='checkbox' checked></input>")
    input = await page.query_selector("input")
    assert input
    await input.uncheck()
    assert await page.evaluate("checkbox.checked") is False


async def test_EH_052_should_select_single_option(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    select = await page.query_selector("select")
    assert select
    await select.select_option("blue")
    assert await page.evaluate("() => window['result'].onInput") == ["blue"]
    assert await page.evaluate("() => window['result'].onChange") == ["blue"]


async def test_EH_053_should_focus_a_button(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    button = await page.query_selector("button")
    assert button
    assert await button.evaluate("button => document.activeElement === button") is False
    await button.focus()
    assert await button.evaluate("button => document.activeElement === button") is True


async def test_EH_054_should_allow_disposing_twice(page: Page) -> None:
    await page.set_content("<section>39</section>")
    element = await page.query_selector("section")
    assert element
    await element.dispose()
    await element.dispose()
