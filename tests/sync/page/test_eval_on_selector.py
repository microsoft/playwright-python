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

"""Port of tests/page/eval-on-selector.spec.ts."""

from typing import Callable

import pytest

from playwright.sync_api import Error, Page
from tests.server import Server


def test_ES_001_should_work_with_css_selector(page: Page) -> None:
    page.set_content('<section id="testAttribute">43543</section>')
    id_attribute = page.eval_on_selector("css=section", "e => e.id")
    assert id_attribute == "testAttribute"


def test_ES_002_should_work_with_id_selector(page: Page) -> None:
    page.set_content('<section id="testAttribute">43543</section>')
    id_attribute = page.eval_on_selector("id=testAttribute", "e => e.id")
    assert id_attribute == "testAttribute"


def test_ES_003_should_work_with_data_test_selector(page: Page) -> None:
    page.set_content('<section data-test=foo id="testAttribute">43543</section>')
    id_attribute = page.eval_on_selector("data-test=foo", "e => e.id")
    assert id_attribute == "testAttribute"


def test_ES_004_should_work_with_data_testid_selector(page: Page) -> None:
    page.set_content('<section data-testid=foo id="testAttribute">43543</section>')
    id_attribute = page.eval_on_selector("data-testid=foo", "e => e.id")
    assert id_attribute == "testAttribute"


def test_ES_005_should_work_with_data_test_id_selector(page: Page) -> None:
    page.set_content('<section data-test-id=foo id="testAttribute">43543</section>')
    id_attribute = page.eval_on_selector("data-test-id=foo", "e => e.id")
    assert id_attribute == "testAttribute"


def test_ES_006_should_work_with_text_selector_in_quotes(page: Page) -> None:
    page.set_content('<section id="testAttribute">43543</section>')
    id_attribute = page.eval_on_selector('text="43543"', "e => e.id")
    assert id_attribute == "testAttribute"


def test_ES_007_should_work_with_xpath_selector(page: Page) -> None:
    page.set_content('<section id="testAttribute">43543</section>')
    id_attribute = page.eval_on_selector("xpath=/html/body/section", "e => e.id")
    assert id_attribute == "testAttribute"


def test_ES_008_should_work_with_text_selector(page: Page) -> None:
    page.set_content('<section id="testAttribute">43543</section>')
    id_attribute = page.eval_on_selector("text=43543", "e => e.id")
    assert id_attribute == "testAttribute"


def test_ES_009_should_auto_detect_css_selector(page: Page) -> None:
    page.set_content('<section id="testAttribute">43543</section>')
    id_attribute = page.eval_on_selector("section", "e => e.id")
    assert id_attribute == "testAttribute"


def test_ES_010_should_auto_detect_css_selector_with_attributes(
    page: Page,
) -> None:
    page.set_content('<section id="testAttribute">43543</section>')
    id_attribute = page.eval_on_selector('section[id="testAttribute"]', "e => e.id")
    assert id_attribute == "testAttribute"


def test_ES_011_should_auto_detect_nested_selectors(page: Page) -> None:
    page.set_content(
        "<div foo=bar><section>43543<span>Hello<div id=target></div></span></section></div>"
    )
    id_attribute = page.eval_on_selector(
        'div[foo=bar] > section >> "Hello" >> div', "e => e.id"
    )
    assert id_attribute == "target"


def test_ES_012_should_accept_arguments(page: Page) -> None:
    page.set_content("<section>hello</section>")
    text = page.eval_on_selector(
        "section", "(e, suffix) => e.textContent + suffix", " world!"
    )
    assert text == "hello world!"


def test_ES_013_should_accept_element_handles_as_arguments(page: Page) -> None:
    page.set_content("<section>hello</section><div> world</div>")
    div_handle = page.query_selector("div")
    text = page.eval_on_selector(
        "section", "(e, div) => e.textContent + div.textContent", div_handle
    )
    assert text == "hello world"


def test_ES_014_should_throw_error_if_no_element_is_found(page: Page) -> None:
    with pytest.raises(Error) as exc_info:
        page.eval_on_selector("section", "e => e.id")
    assert 'Failed to find element matching selector "section"' in (
        exc_info.value.message
    )


def test_ES_015_should_support_syntax(page: Page) -> None:
    page.set_content("<section><div>hello</div></section>")
    text = page.eval_on_selector(
        "css=section >> css=div", "(e, suffix) => e.textContent + suffix", " world!"
    )
    assert text == "hello world!"


def test_ES_016_should_support_syntax_with_different_engines(
    page: Page,
) -> None:
    page.set_content("<section><div><span>hello</span></div></section>")
    text = page.eval_on_selector(
        'xpath=/html/body/section >> css=div >> text="hello"',
        "(e, suffix) => e.textContent + suffix",
        " world!",
    )
    assert text == "hello world!"


def test_ES_017_should_support_spaces_with_syntax(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/deep-shadow.html")
    text = page.eval_on_selector(
        " css = div >>css=div>>css   = span  ", "e => e.textContent"
    )
    assert text == "Hello from root2"


def test_ES_018_should_not_stop_at_first_failure_with_syntax(
    page: Page,
) -> None:
    page.set_content(
        "<div><span>Next</span><button>Previous</button><button>Next</button></div>"
    )
    html = page.eval_on_selector('button >> "Next"', "e => e.outerHTML")
    assert html == "<button>Next</button>"


def test_ES_019_should_support_capture(page: Page) -> None:
    page.set_content(
        "<section><div><span>a</span></div></section><section><div><span>b</span></div></section>"
    )
    assert (
        page.eval_on_selector('*css=div >> "b"', "e => e.outerHTML")
        == "<div><span>b</span></div>"
    )
    assert (
        page.eval_on_selector('section >> *css=div >> "b"', "e => e.outerHTML")
        == "<div><span>b</span></div>"
    )
    assert (
        page.eval_on_selector('css=div >> *text="b"', "e => e.outerHTML")
        == "<span>b</span>"
    )
    assert page.query_selector("*")


def test_ES_020_should_throw_on_multiple_captures(page: Page) -> None:
    with pytest.raises(Error) as exc_info:
        page.eval_on_selector("*css=div >> *css=span", "e => e.outerHTML")
    assert "Only one of the selectors can capture using * modifier" in (
        exc_info.value.message
    )


def test_ES_021_should_throw_on_malformed_capture(page: Page) -> None:
    with pytest.raises(Error) as exc_info:
        page.eval_on_selector("*=div", "e => e.outerHTML")
    assert 'Unknown engine "" while parsing selector *=div' in exc_info.value.message


def test_ES_022_should_work_with_spaces_in_css_attributes(page: Page) -> None:
    page.set_content('<div><input placeholder="Select date"></div>')
    assert page.wait_for_selector('[placeholder="Select date"]')
    assert page.wait_for_selector("[placeholder='Select date']")
    assert page.wait_for_selector('input[placeholder="Select date"]')
    assert page.wait_for_selector("input[placeholder='Select date']")
    assert page.query_selector('[placeholder="Select date"]')
    assert page.query_selector("[placeholder='Select date']")
    assert page.query_selector('input[placeholder="Select date"]')
    assert page.query_selector("input[placeholder='Select date']")
    for selector in [
        '[placeholder="Select date"]',
        "[placeholder='Select date']",
        'input[placeholder="Select date"]',
        "input[placeholder='Select date']",
        'css=[placeholder="Select date"]',
        "css=[placeholder='Select date']",
        'css=input[placeholder="Select date"]',
        "css=input[placeholder='Select date']",
        'div >> [placeholder="Select date"]',
        "div >> [placeholder='Select date']",
    ]:
        assert (
            page.eval_on_selector(selector, "e => e.outerHTML")
            == '<input placeholder="Select date">'
        )


def test_ES_023_should_work_with_quotes_in_css_attributes(page: Page) -> None:
    page.set_content('<div><input placeholder="Select&quot;date"></div>')
    assert page.query_selector('[placeholder="Select\\"date"]')
    assert page.query_selector("[placeholder='Select\"date']")
    page.set_content('<div><input placeholder="Select &quot; date"></div>')
    assert page.query_selector('[placeholder="Select \\" date"]')
    assert page.query_selector("[placeholder='Select \" date']")
    page.set_content('<div><input placeholder="Select&apos;date"></div>')
    assert page.query_selector('[placeholder="Select\'date"]')
    assert page.query_selector("[placeholder='Select\\'date']")
    page.set_content('<div><input placeholder="Select &apos; date"></div>')
    assert page.query_selector('[placeholder="Select \' date"]')
    assert page.query_selector("[placeholder='Select \\' date']")


def test_ES_024_should_work_with_spaces_in_css_attributes_when_missing(
    page: Page, sync_gather: Callable
) -> None:
    def query_and_set_content() -> None:
        assert page.query_selector('[placeholder="Select date"]') is None
        page.set_content('<div><input placeholder="Select date"></div>')

    sync_gather(
        lambda: page.wait_for_selector('[placeholder="Select date"]'),
        query_and_set_content,
    )


def test_ES_025_should_work_with_quotes_in_css_attributes_when_missing(
    page: Page, sync_gather: Callable
) -> None:
    def query_and_set_content() -> None:
        assert page.query_selector('[placeholder="Select\\"date"]') is None
        page.set_content('<div><input placeholder="Select&quot;date"></div>')

    sync_gather(
        lambda: page.wait_for_selector('[placeholder="Select\\"date"]'),
        query_and_set_content,
    )


def test_ES_026_should_return_complex_values(page: Page) -> None:
    page.set_content('<section id="testAttribute">43543</section>')
    id_attribute = page.eval_on_selector("css=section", "e => [{ id: e.id }]")
    assert id_attribute == [{"id": "testAttribute"}]
