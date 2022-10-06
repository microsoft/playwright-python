# Copyright (c) Microsoft Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License")
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

import re

from playwright.sync_api import Page, expect


def test_get_by_test_id(page: Page) -> None:
    page.set_content("<div><div data-testid='Hello'>Hello world</div></div>")
    expect(page.get_by_test_id("Hello")).to_have_text("Hello world")
    expect(page.main_frame.get_by_test_id("Hello")).to_have_text("Hello world")
    expect(page.locator("div").get_by_test_id("Hello")).to_have_text("Hello world")


def test_get_by_test_id_escape_id(page: Page) -> None:
    page.set_content("<div><div data-testid='He\"llo'>Hello world</div></div>")
    expect(page.get_by_test_id('He"llo')).to_have_text("Hello world")


def test_get_by_text(page: Page) -> None:
    page.set_content("<div><div>yo</div><div>ya</div><div>\nye  </div></div>")

    expect(page.get_by_text("yo")).to_have_count(1)
    expect(page.main_frame.get_by_text("yo")).to_have_count(1)
    expect(page.locator("div").get_by_text("yo")).to_have_count(1)

    assert ">\nye  </div>" in page.get_by_text("ye").evaluate("e => e.outerHTML")
    assert ">\nye  </div>" in page.get_by_text(r"ye").evaluate("e => e.outerHTML")

    page.set_content("<div> ye </div><div>ye</div>")
    assert "> ye </div>" in page.get_by_text("ye", exact=True).first.evaluate(
        "e => e.outerHTML"
    )

    page.set_content("<div>Hello world</div><div>Hello</div>")
    assert (
        page.get_by_text("Hello", exact=True).evaluate("e => e.outerHTML")
        == "<div>Hello</div>"
    )


def test_get_by_label(page: Page) -> None:
    page.set_content(
        "<div><label for=target>Name</label><input id=target type=text></div>"
    )

    expect(page.get_by_label("Name")).to_have_count(1)
    expect(page.main_frame.get_by_label("Name")).to_have_count(1)
    expect(page.locator("div").get_by_label("Name")).to_have_count(1)

    assert page.get_by_text("Name").evaluate("e => e.nodeName") == "LABEL"
    assert page.get_by_label("Name").evaluate("e => e.nodeName") == "INPUT"
    assert page.main_frame.get_by_label("Name").evaluate("e => e.nodeName") == "INPUT"
    assert (
        page.locator("div").get_by_label("Name").evaluate("e => e.nodeName") == "INPUT"
    )


def test_get_by_label_with_nested_elements(page: Page) -> None:
    page.set_content(
        "<label for=target>Last <span>Name</span></label><input id=target type=text>"
    )

    expect(page.get_by_label("last name")).to_have_attribute("id", "target")
    expect(page.get_by_label("st na")).to_have_attribute("id", "target")
    expect(page.get_by_label("Name")).to_have_attribute("id", "target")
    expect(page.get_by_label("Last Name", exact=True)).to_have_attribute("id", "target")
    expect(
        page.get_by_label(re.compile(r"Last\s+name", re.IGNORECASE))
    ).to_have_attribute("id", "target")

    expect(page.get_by_label("Last", exact=True)).to_have_count(0)
    expect(page.get_by_label("last name", exact=True)).to_have_count(0)
    expect(page.get_by_label("Name", exact=True)).to_have_count(0)
    expect(page.get_by_label("what?")).to_have_count(0)
    expect(page.get_by_label(re.compile(r"last name"))).to_have_count(0)


def test_get_by_placeholder(page: Page) -> None:
    page.set_content(
        """<div>
    <input placeholder="Hello">
    <input placeholder="Hello World">
  </div>"""
    )

    expect(page.get_by_placeholder("hello")).to_have_count(2)
    expect(page.main_frame.get_by_placeholder("hello")).to_have_count(2)
    expect(page.locator("div").get_by_placeholder("hello")).to_have_count(2)

    expect(page.get_by_placeholder("hello")).to_have_count(2)
    expect(page.get_by_placeholder("Hello", exact=True)).to_have_count(1)
    expect(page.get_by_placeholder(re.compile(r"wor", re.IGNORECASE))).to_have_count(1)

    # Coverage
    expect(page.main_frame.get_by_placeholder("hello")).to_have_count(2)
    expect(page.locator("div").get_by_placeholder("hello")).to_have_count(2)


def test_get_by_alt_text(page: Page) -> None:
    page.set_content(
        """<div>
    <input alt="Hello">
    <input alt="Hello World">
  </div>"""
    )

    expect(page.get_by_alt_text("hello")).to_have_count(2)
    expect(page.main_frame.get_by_alt_text("hello")).to_have_count(2)
    expect(page.locator("div").get_by_alt_text("hello")).to_have_count(2)

    expect(page.get_by_alt_text("hello")).to_have_count(2)
    expect(page.get_by_alt_text("Hello", exact=True)).to_have_count(1)
    expect(page.get_by_alt_text(re.compile(r"wor", re.IGNORECASE))).to_have_count(1)

    # Coverage
    expect(page.main_frame.get_by_alt_text("hello")).to_have_count(2)
    expect(page.locator("div").get_by_alt_text("hello")).to_have_count(2)


def test_get_by_title(page: Page) -> None:
    page.set_content(
        """<div>
    <input title="Hello">
    <input title="Hello World">
  </div>"""
    )

    expect(page.get_by_title("hello")).to_have_count(2)
    expect(page.main_frame.get_by_title("hello")).to_have_count(2)
    expect(page.locator("div").get_by_title("hello")).to_have_count(2)

    expect(page.get_by_title("hello")).to_have_count(2)
    expect(page.get_by_title("Hello", exact=True)).to_have_count(1)
    expect(page.get_by_title(re.compile(r"wor", re.IGNORECASE))).to_have_count(1)

    # Coverage
    expect(page.main_frame.get_by_title("hello")).to_have_count(2)
    expect(page.locator("div").get_by_title("hello")).to_have_count(2)


def test_get_by_escaping(page: Page) -> None:
    page.set_content(
        """<label id=label for=control>Hello
wo"rld</label><input id=control />"""
    )
    page.locator("input").evaluate(
        """input => {
    input.setAttribute('placeholder', 'hello\\nwo"rld');
    input.setAttribute('title', 'hello\\nwo"rld');
    input.setAttribute('alt', 'hello\\nwo"rld');
  }"""
    )
    expect(page.get_by_text('hello\nwo"rld')).to_have_attribute("id", "label")
    expect(page.get_by_label('hello\nwo"rld')).to_have_attribute("id", "control")
    expect(page.get_by_placeholder('hello\nwo"rld')).to_have_attribute("id", "control")
    expect(page.get_by_alt_text('hello\nwo"rld')).to_have_attribute("id", "control")
    expect(page.get_by_title('hello\nwo"rld')).to_have_attribute("id", "control")

    page.set_content(
        """<label id=label for=control>Hello
world</label><input id=control />"""
    )
    page.locator("input").evaluate(
        """input => {
    input.setAttribute('placeholder', 'hello\\nworld');
    input.setAttribute('title', 'hello\\nworld');
    input.setAttribute('alt', 'hello\\nworld');
  }"""
    )
    expect(page.get_by_text("hello\nworld")).to_have_attribute("id", "label")
    expect(page.get_by_label("hello\nworld")).to_have_attribute("id", "control")
    expect(page.get_by_placeholder("hello\nworld")).to_have_attribute("id", "control")
    expect(page.get_by_alt_text("hello\nworld")).to_have_attribute("id", "control")
    expect(page.get_by_title("hello\nworld")).to_have_attribute("id", "control")
