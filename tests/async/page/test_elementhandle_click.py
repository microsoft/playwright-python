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

"""Port of tests/page/elementhandle-click.spec.ts."""

import pytest

from playwright.async_api import Error, Page
from tests.server import Server


async def test_EH_010_should_work_smoke(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    button = await page.query_selector("button")
    assert button
    await button.click()
    assert await page.evaluate("() => window['result']") == "Clicked"


async def test_EH_011_should_work_with_node_removed(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    await page.evaluate("() => delete window['Node']")
    button = await page.query_selector("button")
    assert button
    await button.click()
    assert await page.evaluate("() => window['result']") == "Clicked"


async def test_EH_012_should_work_for_shadow_dom_v1(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/shadow.html")
    button_handle = (await page.evaluate_handle("() => window['button']")).as_element()
    assert button_handle
    await button_handle.click()
    assert await page.evaluate("clicked") is True


async def test_EH_013_should_work_for_text_nodes(page: Page) -> None:
    await page.set_content(
        """
    <div id='outer' onclick="window['result'] = 'Clicked ' + event.target.id;">
      <div id='inner' style="max-width: 50px">Lorem ipsum dolor sit amet consectetur adipiscing elit proin, integer curabitur imperdiet rhoncus cursus tincidunt bibendum, consequat sed magnis laoreet luctus mollis tellus. Nisl parturient mus accumsan feugiat sem laoreet magnis nisi, aptent per sollicitudin gravida orci ac blandit, viverra eros praesent auctor vivamus semper bibendum. Consequat sed habitasse luctus dictumst gravida platea semper phasellus, nascetur ridiculus purus est varius quisque et scelerisque, id vehicula eleifend montes sollicitudin dis velit. Pellentesque ridiculus per natoque et eleifend taciti nunc, laoreet auctor at condimentum imperdiet ante, conubia mi cubilia scelerisque sociosqu sem.</div>
      Custom Text.
    </div>
  """
    )
    button_text_node = (
        await page.evaluate_handle("() => document.querySelector('#outer').lastChild")
    ).as_element()
    assert button_text_node
    await button_text_node.click()
    assert await page.evaluate("() => window['result']") == "Clicked outer"


async def test_EH_014_should_throw_for_detached_nodes(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    button = await page.query_selector("button")
    assert button
    await page.evaluate("button => button.remove()", button)
    with pytest.raises(Error) as exc_info:
        await button.click()
    assert "Element is not attached to the DOM" in exc_info.value.message


async def test_EH_015_should_throw_for_hidden_nodes_with_force(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    button = await page.query_selector("button")
    assert button
    await page.evaluate("button => button.style.display = 'none'", button)
    with pytest.raises(Error) as exc_info:
        await button.click(force=True)
    assert "Element is not visible" in exc_info.value.message


async def test_EH_016_should_throw_for_recursively_hidden_nodes_with_force(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    button = await page.query_selector("button")
    assert button
    await page.evaluate("button => button.parentElement.style.display = 'none'", button)
    with pytest.raises(Error) as exc_info:
        await button.click(force=True)
    assert "Element is not visible" in exc_info.value.message


async def test_EH_017_should_throw_for_br_elements_with_force(page: Page) -> None:
    await page.set_content("hello<br>goodbye")
    br = await page.query_selector("br")
    assert br
    with pytest.raises(Error) as exc_info:
        await br.click(force=True)
    assert "Element is outside of the viewport" in exc_info.value.message


async def test_EH_018_should_double_click_the_button(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    await page.evaluate(
        """() => {
    window['double'] = false;
    const button = document.querySelector('button');
    button.addEventListener('dblclick', event => {
      window['double'] = true;
    });
  }"""
    )
    button = await page.query_selector("button")
    assert button
    await button.dblclick()
    assert await page.evaluate("double") is True
    assert await page.evaluate("result") == "Clicked"
