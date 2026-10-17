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

"""Port of tests/page/queryselector.spec.ts."""

from typing import Any, cast

import pytest

from playwright.sync_api import Error, Page
from tests.server import Server


@pytest.mark.skip_protocol_check
def test_QS_001_should_throw_for_non_string_selector(page: Page) -> None:
    with pytest.raises(Error) as exc_info:
        page.query_selector(cast(Any, None))
    # The Python client leaves out a parameter that is None, so the driver gets
    # undefined where the JavaScript client sends null ("got object").
    assert "selector: expected string, got undefined" in exc_info.value.message


def test_QS_002_should_query_existing_element_with_css_selector_smoke(
    page: Page, server: Server
) -> None:
    page.set_content("<section>test</section>")
    element = page.query_selector("css=section")
    assert element


def test_QS_003_should_query_existing_element_with_text_selector(
    page: Page, server: Server
) -> None:
    page.set_content("<section>test</section>")
    element = page.query_selector('text="test"')
    assert element


def test_QS_004_should_query_existing_element_with_xpath_selector(
    page: Page, server: Server
) -> None:
    page.set_content("<section>test</section>")
    element = page.query_selector("xpath=/html/body/section")
    assert element


def test_QS_005_should_return_null_for_non_existing_element(
    page: Page, server: Server
) -> None:
    element = page.query_selector("non-existing-element")
    assert element is None


def test_QS_006_should_auto_detect_xpath_selector(page: Page, server: Server) -> None:
    page.set_content("<section>test</section>")
    element = page.query_selector("//html/body/section")
    assert element


def test_QS_007_should_auto_detect_xpath_selector_with_starting_parenthesis(
    page: Page, server: Server
) -> None:
    page.set_content("<section>test</section>")
    element = page.query_selector("(//section)[1]")
    assert element


def test_QS_008_should_auto_detect_xpath_selector_starting_with(
    page: Page, server: Server
) -> None:
    page.set_content("<div><section>test</section><span></span></div>")
    span = page.query_selector('"test" >> ../span')
    assert span
    assert span.evaluate("e => e.nodeName") == "SPAN"
    div = page.query_selector('"test" >> ..')
    assert div
    assert div.evaluate("e => e.nodeName") == "DIV"


def test_QS_009_should_auto_detect_text_selector(page: Page, server: Server) -> None:
    page.set_content("<section>test</section>")
    element = page.query_selector('"test"')
    assert element


def test_QS_010_should_auto_detect_css_selector(page: Page, server: Server) -> None:
    page.set_content("<section>test</section>")
    element = page.query_selector("section")
    assert element


def test_QS_011_should_support_syntax(page: Page, server: Server) -> None:
    page.set_content("<section><div>test</div></section>")
    element = page.query_selector("css=section >> css=div")
    assert element


def test_QS_012_should_query_existing_elements(page: Page, server: Server) -> None:
    page.set_content("<div>A</div><br/><div>B</div>")
    elements = page.query_selector_all("div")
    assert len(elements) == 2
    texts = [page.evaluate("e => e.textContent", element) for element in elements]
    assert texts == ["A", "B"]


def test_QS_013_should_return_empty_array_if_nothing_is_found(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    elements = page.query_selector_all("div")
    assert len(elements) == 0


def test_QS_014_xpath_should_query_existing_element(page: Page, server: Server) -> None:
    page.set_content("<section>test</section>")
    elements = page.query_selector_all("xpath=/html/body/section")
    assert elements[0]
    assert len(elements) == 1


def test_QS_015_xpath_should_return_empty_array_for_non_existing_element(
    page: Page, server: Server
) -> None:
    element = page.query_selector_all("//html/body/non-existing-element")
    assert element == []


def test_QS_016_xpath_should_return_multiple_elements(
    page: Page, server: Server
) -> None:
    page.set_content("<div></div><div></div>")
    elements = page.query_selector_all("xpath=/html/body/div")
    assert len(elements) == 2


def test_QS_017_should_work_with_bogus_array_from(page: Page, server: Server) -> None:
    page.set_content("<div>hello</div><div></div>")
    div1 = page.evaluate_handle(
        """() => {
          Array.from = () => [];
          return document.querySelector('div');
        }"""
    )
    elements = page.query_selector_all("div")
    assert len(elements) == 2
    # Check that element handle is functional and belongs to the main world.
    assert elements[0].evaluate("(div, div1) => div === div1", div1) is True
