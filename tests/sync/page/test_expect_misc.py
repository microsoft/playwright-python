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

"""Port of tests/page/expect-misc.spec.ts."""

import datetime
import re
from pathlib import Path
from typing import Callable

import pytest

from playwright.sync_api import Error, Page, expect


def js_date(milliseconds: int) -> datetime.datetime:
    """The Python value of JavaScript's new Date(milliseconds)."""
    return datetime.datetime(
        1970, 1, 1, tzinfo=datetime.timezone.utc
    ) + datetime.timedelta(milliseconds=milliseconds)


def test_EX_181_to_have_count_to_have_count_pass(
    page: Page, sync_gather: Callable
) -> None:
    page.set_content("<select><option>One</option></select>")
    locator = page.locator("option")
    done = False

    def wait_for_count() -> None:
        nonlocal done
        expect(locator).to_have_count(2)
        done = True

    def add_option() -> None:
        page.wait_for_timeout(1000)
        assert done is False
        page.set_content("<select><option>One</option><option>Two</option></select>")

    sync_gather(wait_for_count, add_option)
    assert done is True


def test_EX_182_to_have_count_pass_zero(page: Page) -> None:
    page.set_content("<div></div>")
    locator = page.locator("span")
    expect(locator).to_have_count(0)
    expect(locator).not_to_have_count(1)


def test_EX_183_to_have_count_eventually_pass_zero(
    page: Page, sync_gather: Callable
) -> None:
    page.set_content("<div><span>hello</span></div>")
    locator = page.locator("span")

    def clear_later() -> None:
        page.wait_for_timeout(200)
        try:
            page.evaluate("() => document.querySelector('div').textContent = ''")
        except Error:
            pass

    def check() -> None:
        expect(locator).to_have_count(0)
        expect(locator).not_to_have_count(1)

    sync_gather(clear_later, check)


def test_EX_184_to_have_count_eventually_pass_non_zero(
    page: Page, sync_gather: Callable
) -> None:
    page.set_content("<ul></ul>")

    def set_content_later() -> None:
        page.wait_for_timeout(500)
        page.set_content("<ul><li>one</li><li>two</li></ul>")

    locator = page.locator("li")

    def check() -> None:
        expect(locator).to_have_count(2)

    sync_gather(set_content_later, check)


def test_EX_185_to_have_count_eventually_pass_not_non_zero(
    page: Page, sync_gather: Callable
) -> None:
    page.set_content("<ul><li>one</li><li>two</li></ul>")

    def set_content_later() -> None:
        page.wait_for_timeout(500)
        page.set_content("<ul></ul>")

    locator = page.locator("li")

    def check() -> None:
        expect(locator).not_to_have_count(2)

    sync_gather(set_content_later, check)


def test_EX_186_to_have_count_fail_zero(page: Page) -> None:
    page.set_content("<div><span></span></div>")
    locator = page.locator("span")
    with pytest.raises(AssertionError) as exc_info:
        expect(locator).to_have_count(0, timeout=1000)
    message = str(exc_info.value)
    assert (
        "Locator expected to have count '0'\nActual value: 1 \nCall log:\n" in message
    )
    assert '- Expect "to_have_count" locator("span") with timeout 1000ms' in message


def test_EX_187_to_have_count_fail_zero_2(page: Page) -> None:
    page.set_content("<div><span></span></div>")
    locator = page.locator("span")
    with pytest.raises(AssertionError) as exc_info:
        expect(locator).not_to_have_count(1, timeout=1000)
    message = str(exc_info.value)
    assert (
        "Locator expected not to have count '1'\nActual value: 1 \nCall log:\n"
        in message
    )
    assert '- Expect "not_to_have_count" locator("span") with timeout 1000ms' in message


def test_EX_188_to_have_js_property_pass(page: Page) -> None:
    page.set_content("<div></div>")
    page.eval_on_selector(
        "div", "e => e.foo = { a: 1, b: 'string', c: new Date(1627503992000) }"
    )
    locator = page.locator("div")
    expect(locator).to_have_js_property(
        "foo", {"a": 1, "b": "string", "c": js_date(1627503992000)}
    )


@pytest.mark.xfail(
    reason="python: parse_value raises KeyError 'id' on an object in expect's received value",
    strict=True,
)
def test_EX_189_to_have_js_property_fail(page: Page) -> None:
    page.set_content("<div></div>")
    page.eval_on_selector(
        "div", "e => e.foo = { a: 1, b: 'string', c: new Date(1627503992000) }"
    )
    locator = page.locator("div")
    with pytest.raises(AssertionError) as exc_info:
        expect(locator).to_have_js_property(
            "foo",
            {"a": 1, "b": "string", "c": js_date(1627503992001)},
            timeout=1000,
        )
    received = {"a": 1, "b": "string", "c": js_date(1627503992000)}
    assert f"Actual value: {received}" in str(exc_info.value)


def test_EX_190_to_have_js_property_pass_string(page: Page) -> None:
    page.set_content("<div></div>")
    page.eval_on_selector("div", "e => e.foo = 'string'")
    locator = page.locator("div")
    expect(locator).to_have_js_property("foo", "string")


def test_EX_191_to_have_js_property_fail_string(page: Page) -> None:
    page.set_content("<div></div>")
    page.eval_on_selector("div", "e => e.foo = 'string'")
    locator = page.locator("div")
    with pytest.raises(AssertionError) as exc_info:
        expect(locator).to_have_js_property("foo", "error", timeout=200)
    message = str(exc_info.value)
    assert (
        "Locator expected to have JS Property 'error'\nActual value: string \nCall log:\n"
        in message
    )
    assert '- Expect "to_have_property" locator("div") with timeout 200ms' in message


def test_EX_192_to_have_js_property_pass_number(page: Page) -> None:
    page.set_content("<div></div>")
    page.eval_on_selector("div", "e => e.foo = 2021")
    locator = page.locator("div")
    expect(locator).to_have_js_property("foo", 2021)


def test_EX_193_to_have_js_property_fail_number(page: Page) -> None:
    page.set_content("<div></div>")
    page.eval_on_selector("div", "e => e.foo = 2021")
    locator = page.locator("div")
    with pytest.raises(AssertionError) as exc_info:
        expect(locator).to_have_js_property("foo", 1, timeout=200)
    message = str(exc_info.value)
    assert (
        "Locator expected to have JS Property '1'\nActual value: 2021 \nCall log:\n"
        in message
    )
    assert '- Expect "to_have_property" locator("div") with timeout 200ms' in message


def test_EX_194_to_have_js_property_pass_boolean(page: Page) -> None:
    page.set_content("<div></div>")
    page.eval_on_selector("div", "e => e.foo = true")
    locator = page.locator("div")
    expect(locator).to_have_js_property("foo", True)


def test_EX_195_to_have_js_property_fail_boolean(page: Page) -> None:
    page.set_content("<div></div>")
    page.eval_on_selector("div", "e => e.foo = false")
    locator = page.locator("div")
    with pytest.raises(AssertionError) as exc_info:
        expect(locator).to_have_js_property("foo", True, timeout=200)
    message = str(exc_info.value)
    assert (
        "Locator expected to have JS Property 'True'\nActual value: False \nCall log:\n"
        in message
    )
    assert '- Expect "to_have_property" locator("div") with timeout 200ms' in message


def test_EX_196_to_have_js_property_pass_boolean_2(page: Page) -> None:
    page.set_content("<div></div>")
    page.eval_on_selector("div", "e => e.foo = false")
    locator = page.locator("div")
    expect(locator).to_have_js_property("foo", False)


def test_EX_197_to_have_js_property_fail_boolean_2(page: Page) -> None:
    page.set_content("<div></div>")
    page.eval_on_selector("div", "e => e.foo = false")
    locator = page.locator("div")
    with pytest.raises(AssertionError) as exc_info:
        expect(locator).to_have_js_property("foo", True, timeout=200)
    message = str(exc_info.value)
    assert (
        "Locator expected to have JS Property 'True'\nActual value: False \nCall log:\n"
        in message
    )
    assert '- Expect "to_have_property" locator("div") with timeout 200ms' in message


def test_EX_199_to_have_js_property_pass_null(page: Page) -> None:
    page.set_content("<div></div>")
    page.eval_on_selector("div", "e => e.foo = null")
    locator = page.locator("div")
    expect(locator).to_have_js_property("foo", None)


def test_EX_200_to_have_js_property_pass_nested(page: Page) -> None:
    page.set_content("<div></div>")
    page.eval_on_selector(
        "div",
        "e => e.foo = { nested: { a: 1, b: 'string', c: new Date(1627503992000) } }",
    )
    locator = page.locator("div")
    expect(locator).to_have_js_property(
        "foo.nested", {"a": 1, "b": "string", "c": js_date(1627503992000)}
    )
    expect(locator).to_have_js_property("foo.nested.a", 1)
    expect(locator).to_have_js_property("foo.nested.b", "string")
    expect(locator).to_have_js_property("foo.nested.c", js_date(1627503992000))


def test_EX_201_to_have_js_property_fail_nested(page: Page) -> None:
    page.set_content("<div></div>")
    page.eval_on_selector(
        "div",
        "e => e.foo = { nested: { a: 1, b: 'string', c: new Date(1627503992000) } }",
    )
    locator = page.locator("div")
    with pytest.raises(AssertionError) as exc_info1:
        expect(locator).to_have_js_property(
            "foo.bar",
            {"a": 1, "b": "string", "c": js_date(1627503992001)},
            timeout=1000,
        )
    # JavaScript's undefined is None in Python.
    assert "Actual value: None" in str(exc_info1.value)
    with pytest.raises(AssertionError) as exc_info2:
        expect(locator).to_have_js_property("foo.nested.a", 2, timeout=1000)
    assert "Actual value: 1" in str(exc_info2.value)


def test_EX_202_to_have_class_pass(page: Page) -> None:
    page.set_content('<div class="foo bar baz"></div>')
    locator = page.locator("div")
    expect(locator).to_have_class("foo bar baz")


def test_EX_203_to_have_class_pass_with_sv_gs(page: Page) -> None:
    page.set_content(
        '<svg class="c1 c2" role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"></svg>'
    )
    expect(page.locator("svg")).to_have_class(re.compile(r"c1"))


def test_EX_204_to_have_class_fail(page: Page) -> None:
    page.set_content('<div class="bar baz"></div>')
    locator = page.locator("div")
    with pytest.raises(AssertionError) as exc_info:
        expect(locator).to_have_class("foo bar baz", timeout=1000)
    message = str(exc_info.value)
    assert (
        "Locator expected to have class 'foo bar baz'\nActual value: bar baz \nCall log:\n"
        in message
    )
    assert '- Expect "to_have_class" locator("div") with timeout 1000ms' in message


def test_EX_205_to_have_class_pass_with_array(page: Page) -> None:
    page.set_content(
        '<div class="foo"></div><div class="bar"></div><div class="baz"></div>'
    )
    locator = page.locator("div")
    expect(locator).to_have_class(["foo", "bar", re.compile(r"[a-z]az")])


def test_EX_206_to_have_class_fail_with_array(page: Page) -> None:
    page.set_content(
        '<div class="foo"></div><div class="bar"></div><div class="bar"></div>'
    )
    locator = page.locator("div")
    with pytest.raises(AssertionError) as exc_info:
        expect(locator).to_have_class(
            ["foo", "bar", re.compile(r"[a-z]az")], timeout=1000
        )
    message = str(exc_info.value)
    assert "Locator expected to have class" in message
    assert '- Expect "to_have_class" locator("div") with timeout 1000ms' in message


def test_EX_207_to_contain_class_pass(page: Page) -> None:
    page.set_content('<div class="foo bar baz"></div>')
    locator = page.locator("div")
    expect(locator).to_contain_class("")
    expect(locator).to_contain_class("bar")
    expect(locator).to_contain_class("baz bar")
    expect(locator).to_contain_class("  bar   foo ")
    # Strip whitespace and match individual classes
    expect(locator).not_to_contain_class("  baz   not-matching ")
    # Python has no client-side check for a regular expression; the driver rejects it.
    with pytest.raises(AssertionError) as exc_info:
        expect(locator).to_contain_class(
            re.compile(r"foo|bar")  # type: ignore[arg-type]
        )
    assert "Partial matching does not support regular expressions" in str(
        exc_info.value
    )


def test_EX_208_to_contain_class_pass_with_sv_gs(page: Page) -> None:
    page.set_content(
        '<svg class="c1 c2" role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"></svg>'
    )
    expect(page.locator("svg")).to_contain_class("c1")


def test_EX_209_to_contain_class_fail(page: Page) -> None:
    page.set_content('<div class="bar baz"></div>')
    locator = page.locator("div")
    with pytest.raises(AssertionError) as exc_info:
        expect(locator).to_contain_class("does-not-exist", timeout=1000)
    message = str(exc_info.value)
    assert (
        "Locator expected to contain class 'does-not-exist'\nActual value: bar baz \nCall log:\n"
        in message
    )
    assert '- Expect "to_contain_class" locator("div") with timeout 1000ms' in message


def test_EX_210_to_contain_class_pass_with_array(page: Page) -> None:
    page.set_content(
        '<div class="foo"></div><div class="hello bar"></div><div class="baz"></div>'
    )
    locator = page.locator("div")
    expect(locator).to_contain_class(["foo", "hello", "baz"])
    # Python has no client-side check for a regular expression; the driver rejects it.
    with pytest.raises(AssertionError) as exc_info:
        expect(locator).to_contain_class(
            ["foo", "hello", re.compile(r"baz")]  # type: ignore[list-item]
        )
    assert "Partial matching does not support regular expressions" in str(
        exc_info.value
    )
    expect(locator).not_to_have_class(["not-there", "hello", "baz"])  # Class not there
    expect(locator).not_to_have_class(["foo", "hello"])  # Length mismatch


def test_EX_211_to_contain_class_fail_with_array(page: Page) -> None:
    page.set_content(
        '<div class="foo"></div><div class="bar"></div><div class="bar"></div>'
    )
    locator = page.locator("div")
    with pytest.raises(AssertionError) as exc_info:
        expect(locator).to_contain_class(["foo", "bar", "baz"], timeout=1000)
    message = str(exc_info.value)
    assert "Locator expected to contain class names" in message
    assert '- Expect "to_contain_class" locator("div") with timeout 1000ms' in message


def test_EX_212_to_have_title_pass(page: Page) -> None:
    page.set_content("<title>  Hello     world</title>")
    expect(page).to_have_title("Hello  world")


def test_EX_213_to_have_title_fail(page: Page) -> None:
    page.set_content("<title>Bye</title>")
    with pytest.raises(AssertionError) as exc_info:
        expect(page).to_have_title("Hello", timeout=1000)
    message = str(exc_info.value)
    assert (
        "Page title expected to be 'Hello'\nActual value: Bye \nCall log:\n" in message
    )
    assert '- Expect "to_have_title" with timeout 1000ms' in message


def test_EX_214_to_have_url_pass(page: Page) -> None:
    page.goto("data:text/html,<div>A</div>")
    expect(page).to_have_url("data:text/html,<div>A</div>")


def test_EX_215_to_have_url_fail_string(page: Page) -> None:
    page.goto("data:text/html,<div>A</div>")
    with pytest.raises(AssertionError) as exc_info:
        expect(page).to_have_url("wrong", timeout=1000)
    message = str(exc_info.value)
    assert (
        "Page URL expected to be 'wrong'\nActual value: data:text/html,<div>A</div> \nCall log:\n"
        in message
    )
    assert '- Expect "to_have_url" with timeout 1000ms' in message


def test_EX_216_to_have_url_fail_with_invalid_argument(page: Page) -> None:
    page.goto("data:text/html,<div>A</div>")
    with pytest.raises(Error) as exc_info:
        expect(page).to_have_url({})  # type: ignore[arg-type]
    assert "value must be a string or regular expression" in exc_info.value.message


def test_EX_221_to_have_url_support_ignore_case(page: Page) -> None:
    page.goto("data:text/html,<div>A</div>")
    expect(page).to_have_url("DATA:teXT/HTml,<div>a</div>", ignore_case=True)


def test_EX_223_to_have_attribute_pass(page: Page) -> None:
    page.set_content("<div id=node>Text content</div>")
    locator = page.locator("#node")
    expect(locator).to_have_attribute("id", "node")


def test_EX_224_to_have_attribute_should_not_match_missing_attribute(
    page: Page,
) -> None:
    page.set_content("<div checked id=node>Text content</div>")
    locator = page.locator("#node")
    with pytest.raises(AssertionError) as exc_info:
        expect(locator).to_have_attribute("disabled", "", timeout=1000)
    message = str(exc_info.value)
    assert (
        "Locator expected to have attribute ''\nActual value: None \nCall log:\n"
        in message
    )
    assert (
        '- Expect "to_have_attribute" locator("#node") with timeout 1000ms' in message
    )
    with pytest.raises(AssertionError) as exc_info:
        expect(locator).to_have_attribute("disabled", re.compile(r".*"), timeout=1000)
    message = str(exc_info.value)
    assert (
        "Locator expected to have attribute 're.compile('.*')'\nActual value: None \nCall log:\n"
        in message
    )
    assert (
        '- Expect "to_have_attribute" locator("#node") with timeout 1000ms' in message
    )
    expect(locator).not_to_have_attribute("disabled", "")
    expect(locator).not_to_have_attribute("disabled", re.compile(r".*"))


def test_EX_225_to_have_attribute_should_match_boolean_attribute(
    page: Page,
) -> None:
    page.set_content("<div checked id=node>Text content</div>")
    locator = page.locator("#node")
    expect(locator).to_have_attribute("checked", "")
    expect(locator).to_have_attribute("checked", re.compile(r".*"))
    with pytest.raises(AssertionError) as exc_info:
        expect(locator).not_to_have_attribute("checked", "", timeout=1000)
    message = str(exc_info.value)
    assert (
        "Locator expected not to have attribute ''\nActual value:  \nCall log:\n"
        in message
    )
    assert (
        '- Expect "not_to_have_attribute" locator("#node") with timeout 1000ms'
        in message
    )
    with pytest.raises(AssertionError) as exc_info:
        expect(locator).not_to_have_attribute(
            "checked", re.compile(r".*"), timeout=1000
        )
    message = str(exc_info.value)
    assert (
        "Locator expected not to have attribute 're.compile('.*')'\nActual value:  \nCall log:\n"
        in message
    )
    assert (
        '- Expect "not_to_have_attribute" locator("#node") with timeout 1000ms'
        in message
    )


def test_EX_226_to_have_attribute_should_match_attribute_without_value(
    page: Page,
) -> None:
    page.set_content("<div checked id=node>Text content</div>")
    locator = page.locator("#node")
    expect(locator).to_have_attribute("id")
    expect(locator).to_have_attribute("checked")
    expect(locator).not_to_have_attribute("open")


def test_EX_227_to_have_attribute_should_support_boolean_attribute_with_options(
    page: Page,
) -> None:
    page.set_content("<div checked id=node>Text content</div>")
    locator = page.locator("#node")
    expect(locator).to_have_attribute("id", timeout=5000)
    expect(locator).to_have_attribute("checked", timeout=5000)
    expect(locator).not_to_have_attribute("open", timeout=5000)


def test_EX_228_to_have_attribute_support_ignore_case(page: Page) -> None:
    page.set_content("<div id=NoDe>Text content</div>")
    locator = page.locator("#NoDe")
    expect(locator).to_have_attribute("id", "node", ignore_case=True)
    expect(locator).not_to_have_attribute("id", "node")


def test_EX_229_to_have_css_pass(page: Page) -> None:
    page.set_content('<div id=node style="color: rgb(255, 0, 0)">Text content</div>')
    locator = page.locator("#node")
    expect(locator).to_have_css("color", "rgb(255, 0, 0)")


def test_EX_230_to_have_css_should_support_pseudo_element(page: Page) -> None:
    page.set_content(
        """
      <style>
        #node::before {
          color: rgb(255, 0, 0);
          content: "Text content";
        }
      </style>
      <div id=node></div>
    """
    )
    locator = page.locator("#node")
    expect(locator).to_have_css("color", "rgb(255, 0, 0)", pseudo="before")


def test_EX_231_to_have_css_custom_css_properties(page: Page) -> None:
    page.set_content(
        '<div id=node style="--custom-color-property:#FF00FF;">Text content</div>'
    )
    locator = page.locator("#node")
    expect(locator).to_have_css("--custom-color-property", "#FF00FF")


def test_EX_232_to_have_id_pass(page: Page) -> None:
    page.set_content("<div id=node>Text content</div>")
    locator = page.locator("#node")
    expect(locator).to_have_id("node")


def test_EX_233_to_be_in_viewport_should_work(page: Page) -> None:
    page.set_content(
        """
      <div id=big style="height: 10000px;"></div>
      <div id=small>foo</div>
    """
    )
    expect(page.locator("#big")).to_be_in_viewport()
    expect(page.locator("#small")).not_to_be_in_viewport()
    page.locator("#small").scroll_into_view_if_needed()
    expect(page.locator("#small")).to_be_in_viewport()
    expect(page.locator("#small")).to_be_in_viewport(ratio=1)


def test_EX_234_to_be_in_viewport_should_respect_ratio_option(
    page: Page,
) -> None:
    page.set_content(
        """
      <style>body, div, html { padding: 0; margin: 0; }</style>
      <div id=big style="height: 400vh;"></div>
    """
    )
    expect(page.locator("div")).to_be_in_viewport()
    expect(page.locator("div")).to_be_in_viewport(ratio=0.1)
    expect(page.locator("div")).to_be_in_viewport(ratio=0.2)

    expect(page.locator("div")).to_be_in_viewport(ratio=0.24)
    # In this test, element's ratio is 0.25.
    expect(page.locator("div")).to_be_in_viewport(ratio=0.25)
    expect(page.locator("div")).not_to_be_in_viewport(ratio=0.26)

    expect(page.locator("div")).not_to_be_in_viewport(ratio=0.3)
    expect(page.locator("div")).not_to_be_in_viewport(ratio=0.7)
    expect(page.locator("div")).not_to_be_in_viewport(ratio=0.8)


def test_EX_235_to_be_in_viewport_should_have_good_stack(page: Page) -> None:
    with pytest.raises(AssertionError) as exc_info:
        expect(page.locator("body")).not_to_be_in_viewport(timeout=3000)
    assert re.search(r'unexpected value "viewport ratio \d+', str(exc_info.value))
    # Python hides the library frames with __tracebackhide__.
    stack_frames = [
        entry for entry in exc_info.traceback if not entry.ishidden(exc_info)
    ]
    assert len(stack_frames) == 1
    assert Path(stack_frames[0].path) == Path(__file__)


def test_EX_236_to_be_in_viewport_should_report_intersection_even_if_fully_covered_by_other_element(
    page: Page,
) -> None:
    page.set_content(
        """
      <h1>hello</h1>
      <div style="position: relative; height: 10000px; top: -5000px;></div>
    """
    )
    expect(page.locator("h1")).to_be_in_viewport()


def test_EX_237_to_have_count_should_not_produce_logs_twice(
    page: Page,
) -> None:
    page.set_content("<select><option>One</option></select>")
    with pytest.raises(AssertionError) as exc_info:
        expect(page.locator("option")).to_have_count(2, timeout=2000)
    message = str(exc_info.value)
    waiting_for_message = 'waiting for locator("option")'
    assert waiting_for_message in message
    assert "locator resolved to 1 element" in message
    assert 'unexpected value "1"' in message
    assert waiting_for_message not in message.replace(
        waiting_for_message, "<redacted>", 1
    )


def test_EX_238_to_have_text_should_not_produce_logs_twice(page: Page) -> None:
    page.set_content("<div>hello</div>")
    with pytest.raises(AssertionError) as exc_info:
        expect(page.locator("div")).to_have_text("world", timeout=2000)
    message = str(exc_info.value)
    waiting_for_message = 'waiting for locator("div")'
    assert waiting_for_message in message
    assert "locator resolved to <div>hello</div>" in message
    assert 'unexpected value "hello"' in message
    assert waiting_for_message not in message.replace(
        waiting_for_message, "<redacted>", 1
    )


def test_EX_239_to_have_text_that_does_not_match_should_not_produce_logs_twice(
    page: Page,
) -> None:
    page.set_content("<div>hello</div>")
    with pytest.raises(AssertionError) as exc_info:
        expect(page.locator("span")).to_have_text("world", timeout=2000)
    message = str(exc_info.value)
    waiting_for_message = 'waiting for locator("span")'
    assert waiting_for_message in message
    assert "locator resolved to" not in message
    assert waiting_for_message not in message.replace(
        waiting_for_message, "<redacted>", 1
    )


def test_EX_240_strict_mode_violation_error_format(page: Page) -> None:
    page.set_content("<div>a</div><div>b</div>")
    with pytest.raises(AssertionError) as exc_info:
        expect(page.locator("div")).to_have_text("foo")
    message = str(exc_info.value)
    assert (
        "Locator expected to have text 'foo'\n"
        "Actual value: None\n"
        'Error: strict mode violation: locator("div") resolved to 2 elements:\n'
        '    1) <div>a</div> aka get_by_text("a")\n'
        '    2) <div>b</div> aka get_by_text("b")\n'
        " \nCall log:\n" in message
    )
    assert '- Expect "to_have_text" locator("div")' in message


def test_EX_241_invalid_selector_error_format(page: Page) -> None:
    page.set_content("<div>a</div><div>b</div>")
    with pytest.raises(AssertionError) as exc_info:
        expect(page.locator("##")).to_be_visible()
    message = str(exc_info.value)
    assert (
        "Locator expected to be visible\n"
        "Actual value: None\n"
        'Error: Unexpected token "#" while parsing css selector "##". Did you mean to CSS.escape it? \n'
        "Call log:\n" in message
    )
    assert '- Expect "to_be_visible" ##' in message


def test_EX_242_should_report_expect_error_details_when_page_closes_during_expect(
    page: Page, sync_gather: Callable
) -> None:
    page.set_content("<div>hello</div>")

    def close_page() -> None:
        page.wait_for_timeout(1000)
        page.close()

    def check() -> None:
        expect(page.locator("div")).to_have_text("world", timeout=10000)

    with pytest.raises(AssertionError) as exc_info:
        sync_gather(check, close_page)
    message = str(exc_info.value)
    assert "Locator expected to have text 'world'" in message
    assert "Actual value: hello" in message


def test_EX_243_should_report_page_close_reason_when_page_closes_during_expect(
    page: Page, sync_gather: Callable
) -> None:
    page.set_content("<div>hello</div>")

    def check() -> None:
        expect(page.locator("non-existent")).to_have_text("world", timeout=10000)

    def close_page() -> None:
        page.close(reason="Bye bye.")

    with pytest.raises(AssertionError) as exc_info:
        sync_gather(check, close_page)
    message = str(exc_info.value)
    assert "Locator expected to have text 'world'" in message
    assert "Bye bye." in message
    assert "Internal server error" not in message
