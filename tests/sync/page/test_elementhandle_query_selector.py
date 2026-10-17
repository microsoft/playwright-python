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

from playwright.sync_api import Page
from tests.server import Server


def test_EH_067_should_query_existing_element(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/playground.html")
    page.set_content(
        '<html><body><div class="second"><div class="inner">A</div></div></body></html>'
    )
    html = page.query_selector("html")
    assert html
    second = html.query_selector(".second")
    assert second
    inner = second.query_selector(".inner")
    content = page.evaluate("e => e.textContent", inner)
    assert content == "A"


def test_EH_068_should_return_null_for_non_existing_element(page: Page) -> None:
    page.set_content(
        '<html><body><div class="second"><div class="inner">B</div></div></body></html>'
    )
    html = page.query_selector("html")
    assert html
    second = html.query_selector(".third")
    assert second is None


def test_EH_069_should_work_for_adopted_elements(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    with page.expect_popup() as popup_info:
        page.evaluate("url => window['__popup'] = window.open(url)", server.EMPTY_PAGE)
    popup = popup_info.value
    div_handle = (
        page.evaluate_handle(
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
    assert div_handle.query_selector("span")
    assert div_handle.eval_on_selector("span", "e => e.textContent") == "hello"

    popup.wait_for_load_state("domcontentloaded")
    page.evaluate(
        """() => {
    const div = document.querySelector('div');
    window['__popup'].document.body.appendChild(div);
  }"""
    )
    assert div_handle.query_selector("span")
    assert div_handle.eval_on_selector("span", "e => e.textContent") == "hello"


def test_EH_070_should_query_existing_elements(page: Page) -> None:
    page.set_content("<html><body><div>A</div><br/><div>B</div></body></html>")
    html = page.query_selector("html")
    assert html
    elements = html.query_selector_all("div")
    assert len(elements) == 2
    contents = [page.evaluate("e => e.textContent", element) for element in elements]
    assert contents == ["A", "B"]


def test_EH_071_should_return_empty_array_for_non_existing_elements(
    page: Page,
) -> None:
    page.set_content("<html><body><span>A</span><br/><span>B</span></body></html>")
    html = page.query_selector("html")
    assert html
    elements = html.query_selector_all("div")
    assert len(elements) == 0


def test_EH_072_xpath_should_query_existing_element(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/playground.html")
    page.set_content(
        '<html><body><div class="second"><div class="inner">A</div></div></body></html>'
    )
    html = page.query_selector("html")
    assert html
    second = html.query_selector_all("xpath=./body/div[contains(@class, 'second')]")
    inner = second[0].query_selector_all("xpath=./div[contains(@class, 'inner')]")
    content = page.evaluate("e => e.textContent", inner[0])
    assert content == "A"


def test_EH_073_xpath_should_return_null_for_non_existing_element(
    page: Page,
) -> None:
    page.set_content(
        '<html><body><div class="second"><div class="inner">B</div></div></body></html>'
    )
    html = page.query_selector("html")
    assert html
    second = html.query_selector_all("xpath=/div[contains(@class, 'third')]")
    assert second == []
