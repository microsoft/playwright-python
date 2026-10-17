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

"""Port of tests/page/locator-element-handle.spec.ts."""

from playwright.async_api import Page
from tests.server import Server


async def test_LO_079_should_query_existing_element_smoke(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/playground.html")
    await page.set_content(
        '<html><body><div class="second"><div class="inner">A</div></div></body></html>'
    )
    html = page.locator("html")
    second = html.locator(".second")
    inner = second.locator(".inner")
    content = await page.evaluate("e => e.textContent", await inner.element_handle())
    assert content == "A"


async def test_LO_080_should_query_existing_elements(
    page: Page, server: Server
) -> None:
    await page.set_content("<html><body><div>A</div><br/><div>B</div></body></html>")
    html = page.locator("html")
    elements = await html.locator("div").element_handles()
    assert len(elements) == 2
    result = []
    for element in elements:
        result.append(await page.evaluate("e => e.textContent", element))
    assert result == ["A", "B"]


async def test_LO_081_should_return_empty_array_for_non_existing_elements(
    page: Page, server: Server
) -> None:
    await page.set_content(
        "<html><body><span>A</span><br/><span>B</span></body></html>"
    )
    html = page.locator("html")
    elements = await html.locator("div").element_handles()
    assert len(elements) == 0


async def test_LO_082_xpath_should_query_existing_element(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/playground.html")
    await page.set_content(
        '<html><body><div class="second"><div class="inner">A</div></div></body></html>'
    )
    html = page.locator("html")
    second = html.locator("xpath=./body/div[contains(@class, 'second')]")
    inner = second.locator("xpath=./div[contains(@class, 'inner')]")
    content = await page.evaluate("e => e.textContent", await inner.element_handle())
    assert content == "A"


async def test_LO_083_xpath_should_return_null_for_non_existing_element(
    page: Page, server: Server
) -> None:
    await page.set_content(
        '<html><body><div class="second"><div class="inner">B</div></div></body></html>'
    )
    html = page.locator("html")
    second = await html.locator(
        "xpath=/div[contains(@class, 'third')]"
    ).element_handles()
    assert second == []
