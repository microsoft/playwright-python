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

"""Port of tests/page/locator-convenience.spec.ts."""

import pytest

from playwright.sync_api import Error, Page, expect
from tests.server import Server


def test_LO_057_should_have_a_nice_preview(page: Page, server: Server) -> None:
    page.goto(f"{server.PREFIX}/dom.html")
    outer = page.locator("#outer")
    inner = outer.locator("#inner")
    check = page.locator("#check")
    text = inner.evaluate_handle("e => e.firstChild")
    page.evaluate("() => 1")  # Give them a chance to calculate the preview.
    # Locator.toString() is JavaScript-only: str() of a Python locator shows its selector.
    frame = f"<Frame name= url='{server.PREFIX}/dom.html'>"
    assert str(outer) == f"<Locator frame={frame} selector='#outer'>"
    assert str(inner) == f"<Locator frame={frame} selector='#outer >> #inner'>"
    assert str(text) == "JSHandle@#text=Text,↵more text"
    assert str(check) == f"<Locator frame={frame} selector='#check'>"


def test_LO_058_get_attribute_should_work(page: Page, server: Server) -> None:
    page.goto(f"{server.PREFIX}/dom.html")
    locator = page.locator("#outer")
    assert locator.get_attribute("name") == "value"
    assert locator.get_attribute("foo") is None
    assert page.get_attribute("#outer", "name") == "value"
    assert page.get_attribute("#outer", "foo") is None


def test_LO_059_input_value_should_work(page: Page, server: Server) -> None:
    page.goto(f"{server.PREFIX}/dom.html")

    page.select_option("#select", "foo")
    assert page.input_value("#select") == "foo"

    page.fill("#textarea", "text value")
    assert page.input_value("#textarea") == "text value"

    page.fill("#input", "input value")
    assert page.input_value("#input") == "input value"
    locator = page.locator("#input")
    assert locator.input_value() == "input value"

    with pytest.raises(Error) as exc_info:
        page.input_value("#inner")
    assert (
        "Node is not an <input>, <textarea> or <select> element"
        in exc_info.value.message
    )
    locator2 = page.locator("#inner")
    with pytest.raises(Error) as exc_info:
        locator2.input_value()
    assert (
        "Node is not an <input>, <textarea> or <select> element"
        in exc_info.value.message
    )


def test_LO_060_inner_html_should_work(page: Page, server: Server) -> None:
    page.goto(f"{server.PREFIX}/dom.html")
    locator = page.locator("#outer")
    assert locator.inner_html() == '<div id="inner">Text,\nmore text</div>'
    assert page.inner_html("#outer") == '<div id="inner">Text,\nmore text</div>'


def test_LO_061_inner_text_should_work(page: Page, server: Server) -> None:
    page.goto(f"{server.PREFIX}/dom.html")
    locator = page.locator("#inner")
    assert locator.inner_text() == "Text, more text"
    assert page.inner_text("#inner") == "Text, more text"


def test_LO_062_inner_text_should_throw(page: Page, server: Server) -> None:
    page.set_content("<svg>text</svg>")
    with pytest.raises(Error) as exc_info:
        page.inner_text("svg")
    assert "Node is not an HTMLElement" in exc_info.value.message
    locator = page.locator("svg")
    with pytest.raises(Error) as exc_info:
        locator.inner_text()
    assert "Node is not an HTMLElement" in exc_info.value.message


def test_LO_063_inner_text_should_produce_log(page: Page, server: Server) -> None:
    page.set_content("<div>Hello</div>")
    locator = page.locator("span")
    with pytest.raises(Error) as exc_info:
        locator.inner_text(timeout=1000)
    assert 'waiting for locator("span")' in exc_info.value.message


def test_LO_064_text_content_should_work(page: Page, server: Server) -> None:
    page.goto(f"{server.PREFIX}/dom.html")
    locator = page.locator("#inner")
    assert locator.text_content() == "Text,\nmore text"
    assert page.text_content("#inner") == "Text,\nmore text"


def test_LO_065_is_enabled_and_is_disabled_should_work(page: Page) -> None:
    page.set_content(
        """
    <button disabled>button1</button>
    <button>button2</button>
    <div>div</div>
  """
    )
    div = page.locator("div")
    assert div.is_enabled() is True
    assert div.is_disabled() is False
    assert page.is_enabled("div") is True
    assert page.is_disabled("div") is False
    button1 = page.locator(':text("button1")')
    assert button1.is_enabled() is False
    assert button1.is_disabled() is True
    assert page.is_enabled(':text("button1")') is False
    assert page.is_disabled(':text("button1")') is True
    button2 = page.locator(':text("button2")')
    assert button2.is_enabled() is True
    assert button2.is_disabled() is False
    assert page.is_enabled(':text("button2")') is True
    assert page.is_disabled(':text("button2")') is False


def test_LO_066_is_editable_should_work(page: Page) -> None:
    page.set_content(
        """
    <input id=input1 disabled>
    <textarea></textarea>
    <input id=input2>
    <div contenteditable="true"></div>
    <span id=span1 role=textbox aria-readonly=true></span>
    <span id=span2 role=textbox></span>
    <button>button</button>
  """
    )
    page.eval_on_selector("textarea", "t => t.readOnly = true")
    input1 = page.locator("#input1")
    assert input1.is_editable() is False
    assert page.is_editable("#input1") is False
    input2 = page.locator("#input2")
    assert input2.is_editable() is True
    assert page.is_editable("#input2") is True
    textarea = page.locator("textarea")
    assert textarea.is_editable() is False
    assert page.is_editable("textarea") is False
    assert page.locator("div").is_editable() is True
    assert page.locator("#span1").is_editable() is False
    assert page.locator("#span2").is_editable() is True
    with pytest.raises(Error) as exc_info:
        page.locator("button").is_editable()
    assert (
        "Element is not an <input>, <textarea>, <select> or [contenteditable] and does not have a role allowing [aria-readonly]"
        in exc_info.value.message
    )


def test_LO_067_is_checked_should_work(page: Page) -> None:
    page.set_content("<input type='checkbox' checked><div>Not a checkbox</div>")
    element = page.locator("input")
    assert element.is_checked() is True
    assert page.is_checked("input") is True
    element.evaluate("input => input.checked = false")
    assert element.is_checked() is False
    assert page.is_checked("input") is False
    with pytest.raises(Error) as exc_info:
        page.is_checked("div")
    assert "Not a checkbox or radio button" in exc_info.value.message


def test_LO_068_is_checked_should_work_for_indeterminate_input(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/20190
    page.set_content('<input type="checkbox" checked>')
    page.locator("input").evaluate("e => e.indeterminate = true")

    assert page.locator("input").is_checked() is True
    expect(page.locator("input")).to_be_checked()

    page.locator("input").uncheck()

    assert page.locator("input").is_checked() is False
    expect(page.locator("input")).not_to_be_checked()


def test_LO_069_all_text_contents_should_work(page: Page) -> None:
    page.set_content("<div>A</div><div>B</div><div>C</div>")
    assert page.locator("div").all_text_contents() == ["A", "B", "C"]


def test_LO_070_all_inner_texts_should_work(page: Page) -> None:
    page.set_content("<div>A</div><div>B</div><div>C</div>")
    assert page.locator("div").all_inner_texts() == ["A", "B", "C"]


def test_LO_071_should_return_page(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/frames/two-frames.html")
    outer = page.locator("#outer")
    assert outer.page == page

    inner = outer.locator("#inner")
    assert inner.page == page

    in_frame = page.frames[1].locator("div")
    assert in_frame.page == page


def test_LO_072_description_should_return_null_for_locator_without_description(
    page: Page,
) -> None:
    locator = page.locator("button")
    assert locator.description is None


def test_LO_073_description_should_return_description_for_locator_with_simple_description(
    page: Page,
) -> None:
    locator = page.locator("button").describe("Submit button")
    assert locator.description == "Submit button"


def test_LO_074_description_should_return_description_with_special_characters(
    page: Page,
) -> None:
    locator = page.locator("div").describe("Button with \"quotes\" and 'apostrophes'")
    assert locator.description == "Button with \"quotes\" and 'apostrophes'"


def test_LO_075_description_should_return_description_for_chained_locators(
    page: Page,
) -> None:
    locator = page.locator("form").locator("input").describe("Form input field")
    assert locator.description == "Form input field"


def test_LO_076_description_should_return_description_for_locator_with_multiple_describe_calls(
    page: Page,
) -> None:
    locator1 = page.locator("foo").describe("First description")
    assert locator1.description == "First description"
    locator2 = locator1.locator("button").describe("Second description")
    assert locator2.description == "Second description"
    locator3 = locator2.locator("button")
    assert locator3.description is None
