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

"""Port of tests/page/elementhandle-query-selector.spec.ts."""

import asyncio

from playwright.async_api import Page
from tests.server import Server


async def test_EH_067_should_query_existing_element(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/playground.html")
    await page.set_content(
        '<html><body><div class="second"><div class="inner">A</div></div></body></html>'
    )
    html = await page.query_selector("html")
    assert html
    second = await html.query_selector(".second")
    assert second
    inner = await second.query_selector(".inner")
    content = await page.evaluate("e => e.textContent", inner)
    assert content == "A"


async def test_EH_068_should_return_null_for_non_existing_element(page: Page) -> None:
    await page.set_content(
        '<html><body><div class="second"><div class="inner">B</div></div></body></html>'
    )
    html = await page.query_selector("html")
    assert html
    second = await html.query_selector(".third")
    assert second is None


async def test_EH_069_should_work_for_adopted_elements(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_popup() as popup_info:
        await page.evaluate(
            "url => window['__popup'] = window.open(url)", server.EMPTY_PAGE
        )
    popup = await popup_info.value
    div_handle = (
        await page.evaluate_handle(
            """() => {
    const div = document.createElement('div');
    document.body.appendChild(div);
    const span = document.createElement('span');
    span.textContent = 'hello';
    div.appendChild(span);
    return div;
  }"""
        )
    ).as_element()
    assert div_handle
    assert await div_handle.query_selector("span")
    assert await div_handle.eval_on_selector("span", "e => e.textContent") == "hello"

    await popup.wait_for_load_state("domcontentloaded")
    await page.evaluate(
        """() => {
    const div = document.querySelector('div');
    window['__popup'].document.body.appendChild(div);
  }"""
    )
    assert await div_handle.query_selector("span")
    assert await div_handle.eval_on_selector("span", "e => e.textContent") == "hello"


async def test_EH_070_should_query_existing_elements(page: Page) -> None:
    await page.set_content("<html><body><div>A</div><br/><div>B</div></body></html>")
    html = await page.query_selector("html")
    assert html
    elements = await html.query_selector_all("div")
    assert len(elements) == 2
    promises = [page.evaluate("e => e.textContent", element) for element in elements]
    assert await asyncio.gather(*promises) == ["A", "B"]


async def test_EH_071_should_return_empty_array_for_non_existing_elements(
    page: Page,
) -> None:
    await page.set_content(
        "<html><body><span>A</span><br/><span>B</span></body></html>"
    )
    html = await page.query_selector("html")
    assert html
    elements = await html.query_selector_all("div")
    assert len(elements) == 0


async def test_EH_072_xpath_should_query_existing_element(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/playground.html")
    await page.set_content(
        '<html><body><div class="second"><div class="inner">A</div></div></body></html>'
    )
    html = await page.query_selector("html")
    assert html
    second = await html.query_selector_all(
        "xpath=./body/div[contains(@class, 'second')]"
    )
    inner = await second[0].query_selector_all("xpath=./div[contains(@class, 'inner')]")
    content = await page.evaluate("e => e.textContent", inner[0])
    assert content == "A"


async def test_EH_073_xpath_should_return_null_for_non_existing_element(
    page: Page,
) -> None:
    await page.set_content(
        '<html><body><div class="second"><div class="inner">B</div></div></body></html>'
    )
    html = await page.query_selector("html")
    assert html
    second = await html.query_selector_all("xpath=/div[contains(@class, 'third')]")
    assert second == []
