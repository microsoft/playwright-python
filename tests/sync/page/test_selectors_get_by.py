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

"""Port of tests/page/selectors-get-by.spec.ts."""

import re

import pytest

from playwright.sync_api import Page, Playwright, expect

OUTERS = "els => els.map(e => e.outerHTML)"
TEXTS = "els => els.map(e => e.textContent)"


def test_SE_071_get_by_test_id_should_work(page: Page) -> None:
    page.set_content('<div><div data-testid="Hello">Hello world</div></div>')
    expect(page.get_by_test_id("Hello")).to_have_text("Hello world")
    expect(page.main_frame.get_by_test_id("Hello")).to_have_text("Hello world")
    expect(page.locator("div").get_by_test_id("Hello")).to_have_text("Hello world")


def test_SE_072_get_by_test_id_with_custom_test_id_should_work(
    page: Page, playwright: Playwright
) -> None:
    page.set_content('<div><div data-my-custom-testid="Hello">Hello world</div></div>')
    playwright.selectors.set_test_id_attribute("data-my-custom-testid")
    try:
        expect(page.get_by_test_id("Hello")).to_have_text("Hello world")
        expect(page.main_frame.get_by_test_id("Hello")).to_have_text("Hello world")
        expect(page.locator("div").get_by_test_id("Hello")).to_have_text("Hello world")
    finally:
        playwright.selectors.set_test_id_attribute("data-testid")


@pytest.mark.xfail(
    reason="python: get_by_test_id does not quote a comma-separated test id attribute name (upstream encodeTestIdAttributeName), so the selector does not parse",
    strict=True,
)
def test_SE_073_get_by_test_id_with_comma_separated_test_id_attributes_should_match_any(
    page: Page, playwright: Playwright
) -> None:
    page.set_content(
        """
    <section>
      <div data-pw="Hello">first</div>
      <div data-ti="Hello">second</div>
      <div data-testid="Hello">third</div>
    </section>
  """
    )
    playwright.selectors.set_test_id_attribute("data-pw,data-ti")
    try:
        expect(page.get_by_test_id("Hello")).to_have_count(2)
        expect(page.get_by_test_id("Hello")).to_have_text(["first", "second"])
        expect(page.main_frame.get_by_test_id("Hello")).to_have_count(2)
        expect(page.locator("section").get_by_test_id("Hello")).to_have_count(2)
    finally:
        playwright.selectors.set_test_id_attribute("data-testid")


def test_SE_074_get_by_test_id_should_escape_id(page: Page) -> None:
    page.set_content("<div><div data-testid='He\"llo'>Hello world</div></div>")
    expect(page.get_by_test_id('He"llo')).to_have_text("Hello world")


def test_SE_075_get_by_test_id_should_work_for_regex(page: Page) -> None:
    page.set_content('<div><div data-testid="Hello">Hello world</div></div>')
    expect(page.get_by_test_id(re.compile(r"He[l]*o"))).to_have_text("Hello world")
    expect(page.main_frame.get_by_test_id("Hello")).to_have_text("Hello world")
    expect(page.locator("div").get_by_test_id("Hello")).to_have_text("Hello world")


def test_SE_076_get_by_text_should_work(page: Page) -> None:
    page.set_content("<div>yo</div><div>ya</div><div>\nye  </div>")
    assert ">\nye  </div>" in page.get_by_text("ye").evaluate("e => e.outerHTML")
    assert ">\nye  </div>" in page.get_by_text(re.compile("ye")).evaluate(
        "e => e.outerHTML"
    )
    assert ">\nye  </div>" in page.get_by_text(re.compile("e")).evaluate(
        "e => e.outerHTML"
    )

    page.set_content("<div> ye </div><div>ye</div>")
    assert "> ye </div>" in page.get_by_text("ye", exact=True).first.evaluate(
        "e => e.outerHTML"
    )

    page.set_content("<div>Hello world</div><div>Hello</div>")
    assert ">Hello</div>" in page.get_by_text("Hello", exact=True).evaluate(
        "e => e.outerHTML"
    )


def test_SE_077_get_by_label_should_work(page: Page) -> None:
    page.set_content(
        "<div><label for=target>Name</label><input id=target type=text></div>"
    )
    assert page.get_by_text("Name").evaluate("e => e.nodeName") == "LABEL"
    assert page.get_by_label("Name").evaluate("e => e.nodeName") == "INPUT"
    assert page.main_frame.get_by_label("Name").evaluate("e => e.nodeName") == "INPUT"
    assert (
        page.locator("div").get_by_label("Name").evaluate("e => e.nodeName") == "INPUT"
    )


def test_SE_078_get_by_label_should_work_with_nested_elements(
    page: Page,
) -> None:
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

    assert page.get_by_label("Last", exact=True).element_handles() == []
    assert page.get_by_label("last name", exact=True).element_handles() == []
    assert page.get_by_label("Name", exact=True).element_handles() == []
    assert page.get_by_label("what?").element_handles() == []
    assert page.get_by_label(re.compile("last name")).element_handles() == []


def test_SE_079_get_by_label_should_work_with_multiply_labelled_input(
    page: Page,
) -> None:
    page.set_content(
        "<label for=target>Name</label><input id=target type=text><label for=target>First or Last</label>"
    )
    assert page.get_by_label("Name").evaluate("e => e.id") == "target"
    assert page.get_by_label("First or Last").evaluate("e => e.id") == "target"


def test_SE_080_get_by_label_should_work_with_ancestor_label_and_multiple_controls(
    page: Page,
) -> None:
    page.set_content(
        "<label>Name<button id=target>Click me</button><input type=text></label>"
    )
    assert page.get_by_label("Name").evaluate("e => e.id") == "target"


def test_SE_081_get_by_label_should_work_with_ancestor_label_and_for(
    page: Page,
) -> None:
    page.set_content(
        """
    <label for=target>Name<input type=text id=nontarget></label>
    <input type=text id=target>
  """
    )
    assert page.get_by_label("Name").evaluate("e => e.id") == "target"


def test_SE_082_get_by_label_should_work_with_aria_labelledby(
    page: Page,
) -> None:
    page.set_content(
        "<label id=name-label>Name</label><button aria-labelledby=name-label>Click me</button>"
    )
    assert page.get_by_label("Name").evaluate("e => e.textContent") == ("Click me")


def test_SE_083_get_by_label_should_prioritize_aria_labelledby_over_native_label(
    page: Page,
) -> None:
    page.set_content(
        """
    <label id=name-label>Name</label>
    <label>Wrong<button aria-labelledby=name-label>Click me</button></label>
  """
    )
    assert page.get_by_label("Name").evaluate("e => e.textContent") == ("Click me")


def test_SE_084_get_by_label_should_work_with_aria_label(page: Page) -> None:
    page.set_content('<input id=target aria-label="Name">')
    assert page.get_by_label("Name").evaluate("e => e.id") == "target"


def test_SE_085_get_by_label_should_ignore_empty_aria_label(page: Page) -> None:
    page.set_content(
        "<label for=target>Last Name</label><input id=target type=text aria-label>"
    )
    assert page.get_by_label("Last Name").evaluate("e => e.id") == "target"


def test_SE_086_get_by_label_should_prioritize_aria_labelledby_over_aria_label(
    page: Page,
) -> None:
    page.set_content(
        '<label id=other-label>Other</label><input id=target aria-label="Name" aria-labelledby=other-label>'
    )
    assert page.get_by_label("Other").evaluate("e => e.id") == "target"


def test_SE_087_get_by_placeholder_should_work(page: Page) -> None:
    page.set_content(
        """<div>
    <input placeholder='Hello'>
    <input placeholder='Hello World'>
  </div>"""
    )
    expect(page.get_by_placeholder("hello")).to_have_count(2)
    expect(page.get_by_placeholder("Hello", exact=True)).to_have_count(1)
    expect(page.get_by_placeholder(re.compile("wor", re.IGNORECASE))).to_have_count(1)

    # Coverage
    expect(page.main_frame.get_by_placeholder("hello")).to_have_count(2)
    expect(page.locator("div").get_by_placeholder("hello")).to_have_count(2)


def test_SE_088_get_by_alt_text_should_work(page: Page) -> None:
    page.set_content(
        """<div>
    <input alt='Hello'>
    <input alt='Hello World'>
  </div>"""
    )
    expect(page.get_by_alt_text("hello")).to_have_count(2)
    expect(page.get_by_alt_text("Hello", exact=True)).to_have_count(1)
    expect(page.get_by_alt_text(re.compile("wor", re.IGNORECASE))).to_have_count(1)

    # Coverage
    expect(page.main_frame.get_by_alt_text("hello")).to_have_count(2)
    expect(page.locator("div").get_by_alt_text("hello")).to_have_count(2)


def test_SE_089_get_by_title_should_work(page: Page) -> None:
    page.set_content(
        """<div>
    <input title='Hello'>
    <input title='Hello World'>
  </div>"""
    )
    expect(page.get_by_title("hello")).to_have_count(2)
    expect(page.get_by_title("Hello", exact=True)).to_have_count(1)
    expect(page.get_by_title(re.compile("wor", re.IGNORECASE))).to_have_count(1)

    # Coverage
    expect(page.main_frame.get_by_title("hello")).to_have_count(2)
    expect(page.locator("div").get_by_title("hello")).to_have_count(2)


def test_SE_090_get_by_escaping(page: Page) -> None:
    page.set_content(
        """<label id=label for=control>Hello my
wo"rld</label><input id=control />"""
    )
    page.eval_on_selector(
        "input",
        """input => {
        input.setAttribute('placeholder', 'hello my\\nwo"rld');
        input.setAttribute('title', 'hello my\\nwo"rld');
        input.setAttribute('alt', 'hello my\\nwo"rld');
      }""",
    )
    expect(page.get_by_text('hello my\nwo"rld')).to_have_attribute("id", "label")
    expect(page.get_by_text('hello       my     wo"rld')).to_have_attribute(
        "id", "label"
    )
    expect(page.get_by_label('hello my\nwo"rld')).to_have_attribute("id", "control")
    expect(page.get_by_placeholder('hello my\nwo"rld')).to_have_attribute(
        "id", "control"
    )
    expect(page.get_by_alt_text('hello my\nwo"rld')).to_have_attribute("id", "control")
    expect(page.get_by_title('hello my\nwo"rld')).to_have_attribute("id", "control")

    page.set_content(
        """<label id=label for=control>Hello my
world</label><input id=control />"""
    )
    page.eval_on_selector(
        "input",
        """input => {
        input.setAttribute('placeholder', 'hello my\\nworld');
        input.setAttribute('title', 'hello my\\nworld');
        input.setAttribute('alt', 'hello my\\nworld');
      }""",
    )
    expect(page.get_by_text("hello my\nworld")).to_have_attribute("id", "label")
    expect(page.get_by_text("hello        my    world")).to_have_attribute(
        "id", "label"
    )
    expect(page.get_by_label("hello my\nworld")).to_have_attribute("id", "control")
    expect(page.get_by_placeholder("hello my\nworld")).to_have_attribute(
        "id", "control"
    )
    expect(page.get_by_alt_text("hello my\nworld")).to_have_attribute("id", "control")
    expect(page.get_by_title("hello my\nworld")).to_have_attribute("id", "control")

    page.set_content('<div id=target title="my title">Text here</div>')
    # Upstream writes these in JavaScript string literals, where "\i" is "i".
    expect(page.get_by_title("my title", exact=True)).to_have_count(1, timeout=500)
    expect(page.get_by_title("my title", exact=True)).to_have_count(1, timeout=500)
    expect(page.get_by_title("my t\\itle", exact=True)).to_have_count(0, timeout=500)
    expect(page.get_by_title("my t\\itle", exact=True)).to_have_count(0, timeout=500)
    expect(page.get_by_title("my t\\\\itle", exact=True)).to_have_count(0, timeout=500)

    page.set_content("<label for=target>foo &gt;&gt; bar</label><input id=target>")
    page.eval_on_selector(
        "input",
        """input => {
        input.setAttribute('placeholder', 'foo >> bar');
        input.setAttribute('title', 'foo >> bar');
        input.setAttribute('alt', 'foo >> bar');
      }""",
    )
    assert page.get_by_text("foo >> bar").text_content() == "foo >> bar"
    expect(page.locator("label")).to_have_text("foo >> bar")
    expect(page.get_by_text("foo >> bar")).to_have_text("foo >> bar")
    assert page.get_by_text(re.compile("foo >> bar")).text_content() == "foo >> bar"
    expect(page.get_by_label("foo >> bar")).to_have_attribute("id", "target")
    expect(page.get_by_label(re.compile("foo >> bar"))).to_have_attribute(
        "id", "target"
    )
    expect(page.get_by_placeholder("foo >> bar")).to_have_attribute("id", "target")
    expect(page.get_by_alt_text("foo >> bar")).to_have_attribute("id", "target")
    expect(page.get_by_title("foo >> bar")).to_have_attribute("id", "target")
    expect(page.get_by_placeholder(re.compile("foo >> bar"))).to_have_attribute(
        "id", "target"
    )
    expect(page.get_by_alt_text(re.compile("foo >> bar"))).to_have_attribute(
        "id", "target"
    )
    expect(page.get_by_title(re.compile("foo >> bar"))).to_have_attribute(
        "id", "target"
    )


def test_SE_091_get_by_role_escaping(page: Page) -> None:
    page.set_content(
        """
    <a href="https://playwright.dev">issues 123</a>
    <a href="https://playwright.dev">he llo 56</a>
    <button>Click me</button>
  """
    )
    assert page.get_by_role("button").evaluate_all(OUTERS) == [
        "<button>Click me</button>",
    ]
    assert page.get_by_role("link").evaluate_all(OUTERS) == [
        '<a href="https://playwright.dev">issues 123</a>',
        '<a href="https://playwright.dev">he llo 56</a>',
    ]

    assert page.get_by_role("link", name="issues 123").evaluate_all(OUTERS) == [
        '<a href="https://playwright.dev">issues 123</a>',
    ]
    assert page.get_by_role("link", name="sues").evaluate_all(OUTERS) == [
        '<a href="https://playwright.dev">issues 123</a>',
    ]
    assert page.get_by_role("link", name="  he    \n  llo ").evaluate_all(OUTERS) == [
        '<a href="https://playwright.dev">he llo 56</a>',
    ]
    assert page.get_by_role("button", name="issues").evaluate_all(OUTERS) == []

    assert page.get_by_role("link", name="sues", exact=True).evaluate_all(OUTERS) == []
    assert page.get_by_role("link", name="   he \n llo 56 ", exact=True).evaluate_all(
        OUTERS
    ) == [
        '<a href="https://playwright.dev">he llo 56</a>',
    ]

    assert page.get_by_role("button", name="Click me", exact=True).evaluate_all(
        OUTERS
    ) == [
        "<button>Click me</button>",
    ]
    # Upstream writes these in JavaScript string literals, where "\m" is "m".
    assert page.get_by_role("button", name="Click me", exact=True).evaluate_all(
        OUTERS
    ) == [
        "<button>Click me</button>",
    ]
    assert (
        page.get_by_role("button", name="Click \\me", exact=True).evaluate_all(OUTERS)
        == []
    )
    assert (
        page.get_by_role("button", name="Click \\me", exact=True).evaluate_all(OUTERS)
        == []
    )
    assert (
        page.get_by_role("button", name="Click \\\\me", exact=True).evaluate_all(OUTERS)
        == []
    )


def test_SE_093_get_by_role_with_description(page: Page) -> None:
    page.set_content(
        """
    <div role="alert" aria-label="Upload successful" aria-description="File doc-2025.pdf was uploaded successfully">Alert 1</div>
    <div role="alert" aria-label="Upload successful" aria-description="File report-2026.pdf was uploaded successfully">Alert 2</div>
    <div role="alert" aria-label="Invalid file" aria-description="File demo.doc has an invalid file format">Alert 3</div>
  """
    )

    # description substring match (default)
    assert page.get_by_role("alert", description="doc-2025").evaluate_all(TEXTS) == [
        "Alert 1"
    ]
    assert page.get_by_role("alert", description="report-2026").evaluate_all(TEXTS) == [
        "Alert 2"
    ]

    # description with name combined
    assert page.get_by_role(
        "alert", name="Upload successful", description="doc-2025"
    ).evaluate_all(TEXTS) == ["Alert 1"]
    assert page.get_by_role(
        "alert", name="Upload successful", description="report-2026"
    ).evaluate_all(TEXTS) == ["Alert 2"]
    assert (
        page.get_by_role(
            "alert", name="Invalid file", description="doc-2025"
        ).evaluate_all(TEXTS)
        == []
    )

    # description exact match
    assert (
        page.get_by_role("alert", description="doc-2025", exact=True).evaluate_all(
            TEXTS
        )
        == []
    )
    assert page.get_by_role(
        "alert", description="File doc-2025.pdf was uploaded successfully", exact=True
    ).evaluate_all(TEXTS) == ["Alert 1"]

    # description regex match
    assert page.get_by_role(
        "alert", description=re.compile(r"report-\d+")
    ).evaluate_all(TEXTS) == ["Alert 2"]
    assert page.get_by_role(
        "alert", description=re.compile(r"uploaded successfully$")
    ).evaluate_all(TEXTS) == ["Alert 1", "Alert 2"]


def test_SE_094_get_by_role_with_description_via_aria_describedby(
    page: Page,
) -> None:
    page.set_content(
        """
    <button aria-describedby="desc1">Submit</button>
    <span id="desc1">Submits the form data</span>
    <button aria-describedby="desc2">Submit</button>
    <span id="desc2">Saves as draft</span>
  """
    )

    assert page.get_by_role(
        "button", name="Submit", description="form data"
    ).evaluate_all(TEXTS) == ["Submit"]
    assert page.get_by_role("button", name="Submit", description="draft").evaluate_all(
        TEXTS
    ) == ["Submit"]


def test_SE_095_get_by_role_with_description_via_title_fallback(
    page: Page,
) -> None:
    page.set_content(
        """
    <button title="Submits the form">Submit</button>
    <button title="Resets the form">Reset</button>
  """
    )

    assert page.get_by_role("button", description="Submits").evaluate_all(TEXTS) == [
        "Submit"
    ]
    assert page.get_by_role("button", description="Resets").evaluate_all(TEXTS) == [
        "Reset"
    ]


def test_SE_096_get_by_role_with_description_whitespace_normalization(
    page: Page,
) -> None:
    page.set_content(
        """
    <div role="alert" aria-description="File  doc-2025.pdf   was uploaded   successfully">Alert</div>
  """
    )

    assert page.get_by_role(
        "alert", description="  doc-2025.pdf \n was  uploaded "
    ).evaluate_all(TEXTS) == ["Alert"]
