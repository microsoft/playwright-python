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

import datetime
import re

import pytest

from playwright.sync_api import Browser, Error, Page, expect
from tests.server import Server


def test_assertions_page_to_have_title(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content("<title>new title</title>")
    expect(page).to_have_title("new title")
    expect(page).to_have_title(re.compile("new title"))
    with pytest.raises(AssertionError):
        expect(page).to_have_title("not the current title", timeout=750)
    with pytest.raises(AssertionError):
        expect(page).to_have_title(re.compile("not the current title"), timeout=750)
    with pytest.raises(AssertionError):
        expect(page).not_to_have_title(re.compile("new title"), timeout=750)
    with pytest.raises(AssertionError):
        expect(page).not_to_have_title("new title", timeout=750)
    expect(page).not_to_have_title("great title", timeout=750)
    page.evaluate(
        """
        setTimeout(() => {
            document.title = 'great title';
        }, 2000);
    """
    )
    expect(page).to_have_title("great title")
    expect(page).to_have_title(re.compile("great title"))


def test_assertions_page_to_have_url(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    expect(page).to_have_url(server.EMPTY_PAGE)
    expect(page).to_have_url(re.compile(r".*/empty\.html"))
    with pytest.raises(AssertionError):
        expect(page).to_have_url("nooooo", timeout=750)
    with pytest.raises(AssertionError):
        expect(page).to_have_url(re.compile("not-the-url"), timeout=750)
    page.evaluate(
        """
        setTimeout(() => {
            window.location = window.location.origin + '/grid.html';
        }, 2000);
    """
    )
    expect(page).to_have_url(server.PREFIX + "/grid.html")
    expect(page).not_to_have_url(server.EMPTY_PAGE, timeout=750)
    with pytest.raises(AssertionError):
        expect(page).not_to_have_url(re.compile(r".*/grid\.html"), timeout=750)
    with pytest.raises(AssertionError):
        expect(page).not_to_have_url(server.PREFIX + "/grid.html", timeout=750)
    expect(page).to_have_url(re.compile(r".*/grid\.html"))
    expect(page).not_to_have_url("**/empty.html", timeout=750)


def test_assertions_page_to_have_url_with_base_url(
    browser: Browser, server: Server
) -> None:
    page = browser.new_page(base_url=server.PREFIX)
    page.goto("/empty.html")
    expect(page).to_have_url("/empty.html")
    expect(page).to_have_url(re.compile(r".*/empty\.html"))
    page.close()


def test_assertions_locator_to_contain_text(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content("<div id=foobar>kek</div>")
    expect(page.locator("div#foobar")).to_contain_text("kek")
    expect(page.locator("div#foobar")).not_to_contain_text("bar", timeout=100)
    with pytest.raises(AssertionError):
        expect(page.locator("div#foobar")).to_contain_text("bar", timeout=100)

    page.set_content("<div>Text \n1</div><div>Text2</div><div>Text3</div>")
    expect(page.locator("div")).to_contain_text(["ext     1", re.compile("ext3")])


def test_assertions_locator_to_have_attribute(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content("<div id=foobar>kek</div>")
    expect(page.locator("div#foobar")).to_have_attribute("id", "foobar")
    expect(page.locator("div#foobar")).to_have_attribute("id", re.compile("foobar"))
    expect(page.locator("div#foobar")).not_to_have_attribute("id", "kek", timeout=100)
    with pytest.raises(AssertionError):
        expect(page.locator("div#foobar")).to_have_attribute("id", "koko", timeout=100)


def test_assertions_locator_to_have_attribute_ignore_case(
    page: Page, server: Page
) -> None:
    page.set_content("<div id=NoDe>Text content</div>")
    locator = page.locator("#NoDe")
    expect(locator).to_have_attribute("id", "node", ignore_case=True)
    expect(locator).not_to_have_attribute("id", "node")


def test_assertions_locator_to_have_class(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content("<div class=foobar>kek</div>")
    expect(page.locator("div.foobar")).to_have_class("foobar")
    expect(page.locator("div.foobar")).to_have_class(["foobar"])
    expect(page.locator("div.foobar")).to_have_class(re.compile("foobar"))
    expect(page.locator("div.foobar")).to_have_class([re.compile("foobar")])
    expect(page.locator("div.foobar")).not_to_have_class("kekstar", timeout=100)
    with pytest.raises(AssertionError):
        expect(page.locator("div.foobar")).to_have_class("oh-no", timeout=100)


def test_assertions_locator_to_have_count(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content("<div class=foobar>kek</div><div class=foobar>kek</div>")
    expect(page.locator("div.foobar")).to_have_count(2)
    expect(page.locator("div.foobar")).not_to_have_count(42, timeout=100)
    with pytest.raises(AssertionError):
        expect(page.locator("div.foobar")).to_have_count(42, timeout=100)


def test_assertions_locator_to_have_css(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content("<div class=foobar style='color: rgb(234, 74, 90);'>kek</div>")
    expect(page.locator("div.foobar")).to_have_css("color", "rgb(234, 74, 90)")
    expect(page.locator("div.foobar")).not_to_have_css(
        "color", "rgb(42, 42, 42)", timeout=100
    )
    with pytest.raises(AssertionError):
        expect(page.locator("div.foobar")).to_have_css(
            "color", "rgb(42, 42, 42)", timeout=100
        )


def test_assertions_locator_to_have_id(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content("<div class=foobar id=kek>kek</div>")
    expect(page.locator("div.foobar")).to_have_id("kek")
    expect(page.locator("div.foobar")).not_to_have_id("top", timeout=100)
    with pytest.raises(AssertionError):
        expect(page.locator("div.foobar")).to_have_id("top", timeout=100)


def test_assertions_locator_to_have_js_property(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content("<div></div>")
    page.eval_on_selector(
        "div", "e => e.foo = { a: 1, b: 'string', c: new Date(1627503992000) }"
    )
    expect(page.locator("div")).to_have_js_property(
        "foo",
        {
            "a": 1,
            "b": "string",
            "c": datetime.datetime.fromtimestamp(1627503992000 / 1000),
        },
    )


def test_to_have_js_property_pass_string(page: Page) -> None:
    page.set_content("<div></div>")
    page.eval_on_selector("div", "e => e.foo = 'string'")
    locator = page.locator("div")
    expect(locator).to_have_js_property("foo", "string")


def test_to_have_js_property_fail_string(page: Page) -> None:
    page.set_content("<div></div>")
    page.eval_on_selector("div", "e => e.foo = 'string'")
    locator = page.locator("div")
    with pytest.raises(AssertionError):
        expect(locator).to_have_js_property("foo", "error", timeout=500)


def test_to_have_js_property_pass_number(page: Page) -> None:
    page.set_content("<div></div>")
    page.eval_on_selector("div", "e => e.foo = 2021")
    locator = page.locator("div")
    expect(locator).to_have_js_property("foo", 2021)


def test_to_have_js_property_fail_number(page: Page) -> None:
    page.set_content("<div></div>")
    page.eval_on_selector("div", "e => e.foo = 2021")
    locator = page.locator("div")
    with pytest.raises(AssertionError):
        expect(locator).to_have_js_property("foo", 1, timeout=500)


def test_to_have_js_property_pass_boolean(page: Page) -> None:
    page.set_content("<div></div>")
    page.eval_on_selector("div", "e => e.foo = true")
    locator = page.locator("div")
    expect(locator).to_have_js_property("foo", True)


def test_to_have_js_property_fail_boolean(page: Page) -> None:
    page.set_content("<div></div>")
    page.eval_on_selector("div", "e => e.foo = false")
    locator = page.locator("div")
    with pytest.raises(AssertionError):
        expect(locator).to_have_js_property("foo", True, timeout=500)


def test_to_have_js_property_pass_boolean_2(page: Page) -> None:
    page.set_content("<div></div>")
    page.eval_on_selector("div", "e => e.foo = false")
    locator = page.locator("div")
    expect(locator).to_have_js_property("foo", False)


def test_to_have_js_property_fail_boolean_2(page: Page) -> None:
    page.set_content("<div></div>")
    page.eval_on_selector("div", "e => e.foo = false")
    locator = page.locator("div")
    with pytest.raises(AssertionError):
        expect(locator).to_have_js_property("foo", True, timeout=500)


def test_to_have_js_property_pass_null(page: Page) -> None:
    page.set_content("<div></div>")
    page.eval_on_selector("div", "e => e.foo = null")
    locator = page.locator("div")
    expect(locator).to_have_js_property("foo", None)


def test_assertions_locator_to_have_text(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content("<div id=foobar>kek</div>")
    expect(page.locator("div#foobar")).to_have_text("kek")
    expect(page.locator("div#foobar")).not_to_have_text("top", timeout=100)

    page.set_content("<div>Text    \n1</div><div>Text   2a</div>")
    # Should only normalize whitespace in the first item.
    expect(page.locator("div")).to_have_text(["Text  1", re.compile(r"Text   \d+a")])


@pytest.mark.parametrize(
    "method",
    ["to_have_text", "to_contain_text"],
)
def test_ignore_case(page: Page, server: Server, method: str) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content("<div id=target>apple BANANA</div><div>orange</div>")
    getattr(expect(page.locator("div#target")), method)("apple BANANA")
    getattr(expect(page.locator("div#target")), method)(
        "apple banana", ignore_case=True
    )
    # defaults false
    with pytest.raises(AssertionError) as excinfo:
        getattr(expect(page.locator("div#target")), method)(
            "apple banana",
            timeout=300,
        )
    expected_error_msg = method.replace("_", " ")
    assert expected_error_msg in str(excinfo.value)

    # Array Variants
    getattr(expect(page.locator("div")), method)(["apple BANANA", "orange"])
    getattr(expect(page.locator("div")), method)(
        ["apple banana", "ORANGE"], ignore_case=True
    )
    # defaults false
    with pytest.raises(AssertionError) as excinfo:
        getattr(expect(page.locator("div")), method)(
            ["apple banana", "ORANGE"],
            timeout=300,
        )
    assert expected_error_msg in str(excinfo.value)

    # not variant
    getattr(expect(page.locator("div#target")), f"not_{method}")("apple banana")
    with pytest.raises(AssertionError) as excinfo:
        getattr(expect(page.locator("div#target")), f"not_{method}")(
            "apple banana",
            ignore_case=True,
            timeout=300,
        )
    assert f"not {expected_error_msg}" in str(excinfo)


@pytest.mark.parametrize(
    "method",
    ["to_have_text", "to_contain_text"],
)
def test_ignore_case_regex(page: Page, server: Server, method: str) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content("<div id=target>apple BANANA</div><div>orange</div>")
    getattr(expect(page.locator("div#target")), method)(re.compile("apple BANANA"))
    getattr(expect(page.locator("div#target")), method)(
        re.compile("apple banana"), ignore_case=True
    )
    # defaults to regex flag
    with pytest.raises(AssertionError) as excinfo:
        getattr(expect(page.locator("div#target")), method)(
            re.compile("apple banana"), timeout=300
        )
    expected_error_msg = method.replace("_", " ")
    assert expected_error_msg in str(excinfo.value)
    # overrides regex flag
    with pytest.raises(AssertionError) as excinfo:
        getattr(expect(page.locator("div#target")), method)(
            re.compile("apple banana", re.IGNORECASE),
            ignore_case=False,
            timeout=300,
        )
    assert expected_error_msg in str(excinfo.value)

    # Array Variants
    getattr(expect(page.locator("div")), method)(
        [re.compile("apple BANANA"), re.compile("orange")]
    )
    getattr(expect(page.locator("div")), method)(
        [re.compile("apple banana"), re.compile("ORANGE")], ignore_case=True
    )
    # defaults regex flag
    with pytest.raises(AssertionError) as excinfo:
        getattr(expect(page.locator("div")), method)(
            [re.compile("apple banana"), re.compile("ORANGE")],
            timeout=300,
        )
    assert expected_error_msg in str(excinfo.value)
    # overrides regex flag
    with pytest.raises(AssertionError) as excinfo:
        getattr(expect(page.locator("div")), method)(
            [
                re.compile("apple banana", re.IGNORECASE),
                re.compile("ORANGE", re.IGNORECASE),
            ],
            ignore_case=False,
            timeout=300,
        )
    assert expected_error_msg in str(excinfo.value)

    # not variant
    getattr(expect(page.locator("div#target")), f"not_{method}")(
        re.compile("apple banana")
    )
    with pytest.raises(AssertionError) as excinfo:
        getattr(expect(page.locator("div#target")), f"not_{method}")(
            re.compile("apple banana"),
            ignore_case=True,
            timeout=300,
        )
    assert f"not {expected_error_msg}" in str(excinfo)


def test_assertions_locator_to_have_value(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content("<input type=text id=foo>")
    my_input = page.locator("#foo")
    expect(my_input).to_have_value("")
    expect(my_input).not_to_have_value("bar", timeout=100)
    my_input.fill("kektus")
    expect(my_input).to_have_value("kektus")


def test_to_have_values_works_with_text(page: Page, server: Server) -> None:
    page.set_content(
        """
        <select multiple>
            <option value="R">Red</option>
            <option value="G">Green</option>
            <option value="B">Blue</option>
        </select>
    """
    )
    locator = page.locator("select")
    locator.select_option(["R", "G"])
    expect(locator).to_have_values(["R", "G"])


def test_to_have_values_follows_labels(page: Page, server: Server) -> None:
    page.set_content(
        """
        <label for="colors">Pick a Color</label>
        <select id="colors" multiple>
            <option value="R">Red</option>
            <option value="G">Green</option>
            <option value="B">Blue</option>
        </select>
    """
    )
    locator = page.locator("text=Pick a Color")
    locator.select_option(["R", "G"])
    expect(locator).to_have_values(["R", "G"])


def test_to_have_values_exact_match_with_text(page: Page, server: Server) -> None:
    page.set_content(
        """
        <select multiple>
            <option value="RR">Red</option>
            <option value="GG">Green</option>
        </select>
    """
    )
    locator = page.locator("select")
    locator.select_option(["RR", "GG"])
    with pytest.raises(AssertionError) as excinfo:
        expect(locator).to_have_values(["R", "G"], timeout=500)
    assert "Locator expected to have Values '['R', 'G']'" in str(excinfo.value)
    assert "Actual value: ['RR', 'GG']" in str(excinfo.value)


def test_to_have_values_works_with_regex(page: Page, server: Server) -> None:
    page.set_content(
        """
        <select multiple>
            <option value="R">Red</option>
            <option value="G">Green</option>
            <option value="B">Blue</option>
        </select>
    """
    )
    locator = page.locator("select")
    locator.select_option(["R", "G"])
    expect(locator).to_have_values([re.compile("R"), re.compile("G")])


def test_to_have_values_fails_when_items_not_selected(
    page: Page, server: Server
) -> None:
    page.set_content(
        """
        <select multiple>
            <option value="R">Red</option>
            <option value="G">Green</option>
            <option value="B">Blue</option>
        </select>
    """
    )
    locator = page.locator("select")
    locator.select_option(["B"])
    with pytest.raises(AssertionError) as excinfo:
        expect(locator).to_have_values(["R", "G"], timeout=500)
    assert "Locator expected to have Values '['R', 'G']'" in str(excinfo.value)
    assert "Actual value: ['B']" in str(excinfo.value)


def test_to_have_values_fails_when_multiple_not_specified(
    page: Page, server: Server
) -> None:
    page.set_content(
        """
        <select>
            <option value="R">Red</option>
            <option value="G">Green</option>
            <option value="B">Blue</option>
        </select>
    """
    )
    locator = page.locator("select")
    locator.select_option(["B"])
    with pytest.raises(Error) as excinfo:
        expect(locator).to_have_values(["R", "G"], timeout=500)
    assert "Error: Not a select element with a multiple attribute" in str(excinfo.value)


def test_to_have_values_fails_when_not_a_select_element(
    page: Page, server: Server
) -> None:
    page.set_content(
        """
        <input type="text">
    """
    )
    locator = page.locator("input")
    with pytest.raises(Error) as excinfo:
        expect(locator).to_have_values(["R", "G"], timeout=500)
    assert "Error: Not a select element with a multiple attribute" in str(excinfo.value)


def test_assertions_locator_to_be_checked(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content("<input type=checkbox>")
    my_checkbox = page.locator("input")
    expect(my_checkbox).not_to_be_checked()
    with pytest.raises(AssertionError, match="Locator expected to be checked"):
        expect(my_checkbox).to_be_checked(timeout=100)
    expect(my_checkbox).to_be_checked(timeout=100, checked=False)
    with pytest.raises(AssertionError):
        expect(my_checkbox).to_be_checked(timeout=100, checked=True)
    my_checkbox.check()
    expect(my_checkbox).to_be_checked(timeout=100, checked=True)
    with pytest.raises(AssertionError, match="Locator expected to be unchecked"):
        expect(my_checkbox).to_be_checked(timeout=100, checked=False)
    expect(my_checkbox).to_be_checked()


def test_assertions_locator_to_be_disabled_enabled(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content("<input type=checkbox>")
    my_checkbox = page.locator("input")
    expect(my_checkbox).not_to_be_disabled()
    expect(my_checkbox).to_be_enabled()
    with pytest.raises(AssertionError):
        expect(my_checkbox).to_be_disabled(timeout=100)
    my_checkbox.evaluate("e => e.disabled = true")
    expect(my_checkbox).to_be_disabled()
    with pytest.raises(AssertionError, match="Locator expected to be enabled"):
        expect(my_checkbox).to_be_enabled(timeout=100)


def test_assertions_locator_to_be_enabled_with_true(page: Page) -> None:
    page.set_content("<button>Text</button>")
    expect(page.locator("button")).to_be_enabled(enabled=True)


def test_assertions_locator_to_be_enabled_with_false_throws_good_exception(
    page: Page,
) -> None:
    page.set_content("<button>Text</button>")
    with pytest.raises(AssertionError, match="Locator expected to be disabled"):
        expect(page.locator("button")).to_be_enabled(enabled=False)


def test_assertions_locator_to_be_enabled_with_false(page: Page) -> None:
    page.set_content("<button disabled>Text</button>")
    expect(page.locator("button")).to_be_enabled(enabled=False)


def test_assertions_locator_to_be_enabled_with_not_and_false(page: Page) -> None:
    page.set_content("<button>Text</button>")
    expect(page.locator("button")).not_to_be_enabled(enabled=False)


def test_assertions_locator_to_be_enabled_eventually(page: Page) -> None:
    page.set_content("<button disabled>Text</button>")
    page.eval_on_selector(
        "button",
        """
        button => setTimeout(() => {
            button.removeAttribute('disabled');
        }, 700);
    """,
    )
    expect(page.locator("button")).to_be_enabled()


def test_assertions_locator_to_be_enabled_eventually_with_not(page: Page) -> None:
    page.set_content("<button>Text</button>")
    page.eval_on_selector(
        "button",
        """
        button => setTimeout(() => {
            button.setAttribute('disabled', '');
        }, 700);
    """,
    )
    expect(page.locator("button")).not_to_be_enabled()


def test_assertions_locator_to_be_editable(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content("<input></input><button disabled>Text</button>")
    expect(page.locator("button")).not_to_be_editable()
    expect(page.locator("input")).to_be_editable()
    with pytest.raises(AssertionError, match="Locator expected to be editable"):
        expect(page.locator("button")).to_be_editable(timeout=100)


def test_assertions_locator_to_be_editable_with_true(page: Page) -> None:
    page.set_content("<input></input>")
    expect(page.locator("input")).to_be_editable(editable=True)


def test_assertions_locator_to_be_editable_with_false(page: Page) -> None:
    page.set_content("<input readonly></input>")
    expect(page.locator("input")).to_be_editable(editable=False)


def test_assertions_locator_to_be_editable_with_false_and_throw_good_exception(
    page: Page,
) -> None:
    page.set_content("<input></input>")
    with pytest.raises(AssertionError, match="Locator expected to be readonly"):
        expect(page.locator("input")).to_be_editable(editable=False)


def test_assertions_locator_to_be_editable_with_not_and_false(page: Page) -> None:
    page.set_content("<input></input>")
    expect(page.locator("input")).not_to_be_editable(editable=False)


def test_assertions_locator_to_be_empty(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content(
        "<input value=text name=input1></input><input name=input2></input>"
    )
    expect(page.locator("input[name=input1]")).not_to_be_empty()
    expect(page.locator("input[name=input2]")).to_be_empty()
    with pytest.raises(AssertionError):
        expect(page.locator("input[name=input1]")).to_be_empty(timeout=100)


def test_assertions_locator_to_be_focused(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content("<input type=checkbox>")
    my_checkbox = page.locator("input")
    with pytest.raises(AssertionError):
        expect(my_checkbox).to_be_focused(timeout=100)
    my_checkbox.focus()
    expect(my_checkbox).to_be_focused()


def test_assertions_locator_to_be_hidden_visible(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content("<div style='width: 50px; height: 50px;'>Something</div>")
    my_checkbox = page.locator("div")
    expect(my_checkbox).to_be_visible()
    with pytest.raises(AssertionError):
        expect(my_checkbox).to_be_hidden(timeout=100)
    my_checkbox.evaluate("e => e.style.display = 'none'")
    expect(my_checkbox).to_be_hidden()
    with pytest.raises(AssertionError, match="Locator expected to be visible"):
        expect(my_checkbox).to_be_visible(timeout=100)


def test_assertions_locator_to_be_visible_with_true(page: Page) -> None:
    page.set_content("<button>hello</button>")
    expect(page.locator("button")).to_be_visible(visible=True)


def test_assertions_locator_to_be_visible_with_false(page: Page) -> None:
    page.set_content("<button hidden>hello</button>")
    expect(page.locator("button")).to_be_visible(visible=False)


def test_assertions_locator_to_be_visible_with_false_throws_good_exception(
    page: Page,
) -> None:
    page.set_content("<button>hello</button>")
    with pytest.raises(AssertionError, match="Locator expected to be hidden"):
        expect(page.locator("button")).to_be_visible(visible=False)


def test_assertions_locator_to_be_visible_with_not_and_false(page: Page) -> None:
    page.set_content("<button>hello</button>")
    expect(page.locator("button")).not_to_be_visible(visible=False)


def test_assertions_locator_to_be_visible_eventually(page: Page) -> None:
    page.set_content("<div></div>")
    page.eval_on_selector(
        "div",
        """
        div => setTimeout(() => {
            div.innerHTML = '<span>Hello</span>';
        }, 700);
    """,
    )
    expect(page.locator("span")).to_be_visible()


def test_assertions_locator_to_be_visible_eventually_with_not(page: Page) -> None:
    page.set_content("<div><span>Hello</span></div>")
    page.eval_on_selector(
        "span",
        """
        span => setTimeout(() => {
            span.textContent = '';
        }, 700);
    """,
    )
    expect(page.locator("span")).not_to_be_visible()


def test_assertions_should_serialize_regexp_correctly(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content("<div>iGnOrEcAsE</div>")
    expect(page.locator("div")).to_have_text(re.compile(r"ignorecase", re.IGNORECASE))
    page.set_content(
        """<div>start
some
lines
between
end</div>"""
    )
    expect(page.locator("div")).to_have_text(re.compile(r"start.*end", re.DOTALL))
    page.set_content(
        """<div>line1
line2
line3</div>"""
    )
    expect(page.locator("div")).to_have_text(re.compile(r"^line2$", re.MULTILINE))


def test_assertions_response_is_ok_pass(page: Page, server: Server) -> None:
    response = page.request.get(server.EMPTY_PAGE)
    expect(response).to_be_ok()


def test_assertions_response_is_ok_pass_with_not(page: Page, server: Server) -> None:
    response = page.request.get(server.PREFIX + "/unknown")
    expect(response).not_to_be_ok()


def test_assertions_response_is_ok_fail(page: Page, server: Server) -> None:
    response = page.request.get(server.PREFIX + "/unknown")
    with pytest.raises(AssertionError) as excinfo:
        expect(response).to_be_ok()
    error_message = str(excinfo.value)
    assert ("→ GET " + server.PREFIX + "/unknown") in error_message
    assert "← 404 Not Found" in error_message


def test_should_print_response_with_text_content_type_if_to_be_ok_fails(
    page: Page, server: Server
) -> None:
    server.set_route(
        "/text-content-type",
        lambda r: (
            r.setResponseCode(404),
            r.setHeader("content-type", "text/plain"),
            r.write(b"Text error"),
            r.finish(),
        ),
    )
    server.set_route(
        "/no-content-type",
        lambda r: (
            r.setResponseCode(404),
            r.write(b"No content type error"),
            r.finish(),
        ),
    )
    server.set_route(
        "/binary-content-type",
        lambda r: (
            r.setResponseCode(404),
            r.setHeader("content-type", "image/bmp"),
            r.write(b"Image content type error"),
            r.finish(),
        ),
    )

    response = page.request.get(server.PREFIX + "/text-content-type")
    with pytest.raises(AssertionError) as excinfo:
        expect(response).to_be_ok()
    error_message = str(excinfo.value)
    assert ("→ GET " + server.PREFIX + "/text-content-type") in error_message
    assert "← 404 Not Found" in error_message
    assert "Response Text:" in error_message
    assert "Text error" in error_message

    response = page.request.get(server.PREFIX + "/no-content-type")
    with pytest.raises(AssertionError) as excinfo:
        expect(response).to_be_ok()
    error_message = str(excinfo.value)
    assert ("→ GET " + server.PREFIX + "/no-content-type") in error_message
    assert "← 404 Not Found" in error_message
    assert "Response Text:" not in error_message
    assert "No content type error" not in error_message

    response = page.request.get(server.PREFIX + "/binary-content-type")
    with pytest.raises(AssertionError) as excinfo:
        expect(response).to_be_ok()
    error_message = str(excinfo.value)
    assert ("→ GET " + server.PREFIX + "/binary-content-type") in error_message
    assert "← 404 Not Found" in error_message
    assert "Response Text:" not in error_message
    assert "Image content type error" not in error_message


def test_should_print_users_message_for_page_based_assertion(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content("<title>new title</title>")
    with pytest.raises(AssertionError) as excinfo:
        expect(page, "Title is not new").to_have_title("old title", timeout=100)
    assert "Title is not new" in str(excinfo.value)
    with pytest.raises(AssertionError) as excinfo:
        expect(page).to_have_title("old title", timeout=100)
    assert "Page title expected to be" in str(excinfo.value)


def test_should_print_expected_value_with_custom_message(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content("<title>new title</title>")
    with pytest.raises(AssertionError) as excinfo:
        expect(page, "custom-message").to_have_title("old title", timeout=100)
    assert "custom-message" in str(excinfo.value)
    assert "Expected value: 'old title'" in str(excinfo.value)
    with pytest.raises(AssertionError) as excinfo:
        expect(page.get_by_text("hello"), "custom-message").to_be_visible(timeout=100)
    assert "custom-message" in str(excinfo.value)
    assert "Expected value" not in str(excinfo.value)


def test_should_be_attached_default(page: Page) -> None:
    page.set_content("<input></input>")
    locator = page.locator("input")
    expect(locator).to_be_attached()


def test_should_be_attached_with_hidden_element(page: Page) -> None:
    page.set_content('<button style="display:none">hello</button>')
    locator = page.locator("button")
    expect(locator).to_be_attached()


def test_should_be_attached_with_not(page: Page) -> None:
    page.set_content("<button>hello</button>")
    locator = page.locator("input")
    expect(locator).not_to_be_attached()


def test_should_be_attached_with_attached_true(page: Page) -> None:
    page.set_content("<button>hello</button>")
    locator = page.locator("button")
    expect(locator).to_be_attached(attached=True)


def test_should_be_attached_with_attached_false(page: Page) -> None:
    page.set_content("<button>hello</button>")
    locator = page.locator("input")
    expect(locator).to_be_attached(attached=False)


def test_should_be_attached_with_attached_false_and_throw_good_error(
    page: Page,
) -> None:
    page.set_content("<button>hello</button>")
    locator = page.locator("button")
    with pytest.raises(AssertionError, match="Locator expected to be detached"):
        expect(locator).to_be_attached(attached=False, timeout=1)


def test_should_be_attached_with_not_and_attached_false(page: Page) -> None:
    page.set_content("<button>hello</button>")
    locator = page.locator("button")
    expect(locator).not_to_be_attached(attached=False)


def test_should_be_attached_eventually(page: Page) -> None:
    page.set_content("<div></div>")
    locator = page.locator("span")
    page.locator("div").evaluate(
        "(e) => setTimeout(() => e.innerHTML = '<span>hello</span>', 1000)"
    )
    expect(locator).to_be_attached()


def test_should_be_attached_eventually_with_not(page: Page) -> None:
    page.set_content("<div><span>Hello</span></div>")
    locator = page.locator("span")
    page.locator("div").evaluate("(e) => setTimeout(() => e.textContent = '', 1000)")
    expect(locator).not_to_be_attached()


def test_should_be_attached_fail(page: Page) -> None:
    page.set_content("<button>Hello</button>")
    locator = page.locator("input")
    with pytest.raises(
        AssertionError, match="Locator expected to be attached"
    ) as exc_info:
        expect(locator).to_be_attached(timeout=1000)
    assert "locator resolved to" not in exc_info.value.args[0]


def test_should_be_attached_fail_with_not(page: Page) -> None:
    page.set_content("<input></input>")
    locator = page.locator("input")
    with pytest.raises(AssertionError) as exc_info:
        expect(locator).not_to_be_attached(timeout=1000)
    assert "locator resolved to <input/>" in exc_info.value.args[0]


def test_should_be_attached_with_impossible_timeout(page: Page) -> None:
    page.set_content("<div id=node>Text content</div>")
    expect(page.locator("#node")).to_be_attached(timeout=1)


def test_should_be_attached_with_impossible_timeout_not(page: Page) -> None:
    page.set_content("<div id=node>Text content</div>")
    expect(page.locator("no-such-thing")).not_to_be_attached(timeout=1)


def test_should_be_able_to_set_custom_timeout(page: Page) -> None:
    with pytest.raises(AssertionError) as exc_info:
        expect(page.locator("#a1")).to_be_visible(timeout=111)
    assert "LocatorAssertions.to_be_visible with timeout 111ms" in str(exc_info.value)


def test_should_be_able_to_set_custom_global_timeout(page: Page) -> None:
    try:
        expect.set_options(timeout=111)
        with pytest.raises(AssertionError) as exc_info:
            expect(page.locator("#a1")).to_be_visible()
        assert "LocatorAssertions.to_be_visible with timeout 111ms" in str(
            exc_info.value
        )
    finally:
        expect.set_options(timeout=5_000)
