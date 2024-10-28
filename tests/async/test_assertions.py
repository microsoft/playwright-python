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

import asyncio
import datetime
import re

import pytest

from playwright.async_api import Browser, Error, Page, expect
from tests.server import Server


async def test_assertions_page_to_have_title(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<title>new title</title>")
    await expect(page).to_have_title("new title")
    await expect(page).to_have_title(re.compile("new title"))
    with pytest.raises(AssertionError):
        await expect(page).to_have_title("not the current title", timeout=750)
    with pytest.raises(AssertionError):
        await expect(page).to_have_title(
            re.compile("not the current title"), timeout=750
        )
    with pytest.raises(AssertionError):
        await expect(page).not_to_have_title(re.compile("new title"), timeout=750)
    with pytest.raises(AssertionError):
        await expect(page).not_to_have_title("new title", timeout=750)
    await expect(page).not_to_have_title("great title", timeout=750)
    await page.evaluate(
        """
        setTimeout(() => {
            document.title = 'great title';
        }, 2000);
    """
    )
    await expect(page).to_have_title("great title")
    await expect(page).to_have_title(re.compile("great title"))


async def test_assertions_page_to_have_url(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await expect(page).to_have_url(server.EMPTY_PAGE)
    await expect(page).to_have_url(re.compile(r".*/empty\.html"))
    with pytest.raises(AssertionError):
        await expect(page).to_have_url("nooooo", timeout=750)
    with pytest.raises(AssertionError):
        await expect(page).to_have_url(re.compile("not-the-url"), timeout=750)
    await page.evaluate(
        """
        setTimeout(() => {
            window.location = window.location.origin + '/grid.html';
        }, 2000);
    """
    )
    await expect(page).to_have_url(server.PREFIX + "/grid.html")
    await expect(page).not_to_have_url(server.EMPTY_PAGE, timeout=750)
    with pytest.raises(AssertionError):
        await expect(page).not_to_have_url(re.compile(r".*/grid\.html"), timeout=750)
    with pytest.raises(AssertionError):
        await expect(page).not_to_have_url(server.PREFIX + "/grid.html", timeout=750)
    await expect(page).to_have_url(re.compile(r".*/grid\.html"))
    await expect(page).not_to_have_url("**/empty.html", timeout=750)


async def test_assertions_page_to_have_url_with_base_url(
    browser: Browser, server: Server
) -> None:
    page = await browser.new_page(base_url=server.PREFIX)
    await page.goto("/empty.html")
    await expect(page).to_have_url("/empty.html")
    await expect(page).to_have_url(re.compile(r".*/empty\.html"))
    await page.close()


async def test_assertions_page_to_have_url_support_ignore_case(page: Page) -> None:
    await page.goto("data:text/html,<div>A</div>")
    await expect(page).to_have_url("DATA:teXT/HTml,<div>a</div>", ignore_case=True)


async def test_assertions_locator_to_contain_text(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<div id=foobar>kek</div>")
    await expect(page.locator("div#foobar")).to_contain_text("kek")
    await expect(page.locator("div#foobar")).not_to_contain_text("bar", timeout=100)
    with pytest.raises(AssertionError):
        await expect(page.locator("div#foobar")).to_contain_text("bar", timeout=100)

    await page.set_content("<div>Text \n1</div><div>Text2</div><div>Text3</div>")
    await expect(page.locator("div")).to_contain_text(["ext     1", re.compile("ext3")])


async def test_assertions_locator_to_contain_text_should_throw_if_arg_is_unsupported_type(
    page: Page,
) -> None:
    with pytest.raises(Error, match="value must be a string or regular expression"):
        await expect(page.locator("div")).to_contain_text(1)  # type: ignore


async def test_assertions_locator_to_have_attribute(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<div id=foobar>kek</div>")
    await expect(page.locator("div#foobar")).to_have_attribute("id", "foobar")
    await expect(page.locator("div#foobar")).to_have_attribute(
        "id", re.compile("foobar")
    )
    await expect(page.locator("div#foobar")).not_to_have_attribute(
        "id", "kek", timeout=100
    )
    with pytest.raises(AssertionError):
        await expect(page.locator("div#foobar")).to_have_attribute(
            "id", "koko", timeout=100
        )


async def test_assertions_locator_to_have_attribute_ignore_case(
    page: Page, server: Page
) -> None:
    await page.set_content("<div id=NoDe>Text content</div>")
    locator = page.locator("#NoDe")
    await expect(locator).to_have_attribute("id", "node", ignore_case=True)
    await expect(locator).not_to_have_attribute("id", "node")


async def test_assertions_locator_to_have_class(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<div class=foobar>kek</div>")
    await expect(page.locator("div.foobar")).to_have_class("foobar")
    await expect(page.locator("div.foobar")).to_have_class(["foobar"])
    await expect(page.locator("div.foobar")).to_have_class(re.compile("foobar"))
    await expect(page.locator("div.foobar")).to_have_class([re.compile("foobar")])
    await expect(page.locator("div.foobar")).not_to_have_class("kekstar", timeout=100)
    with pytest.raises(AssertionError):
        await expect(page.locator("div.foobar")).to_have_class("oh-no", timeout=100)


async def test_assertions_locator_to_have_count(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<div class=foobar>kek</div><div class=foobar>kek</div>")
    await expect(page.locator("div.foobar")).to_have_count(2)
    await expect(page.locator("div.foobar")).not_to_have_count(42, timeout=100)
    with pytest.raises(AssertionError):
        await expect(page.locator("div.foobar")).to_have_count(42, timeout=100)


async def test_assertions_locator_to_have_css(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        "<div class=foobar style='color: rgb(234, 74, 90);'>kek</div>"
    )
    await expect(page.locator("div.foobar")).to_have_css("color", "rgb(234, 74, 90)")
    await expect(page.locator("div.foobar")).not_to_have_css(
        "color", "rgb(42, 42, 42)", timeout=100
    )
    with pytest.raises(AssertionError):
        await expect(page.locator("div.foobar")).to_have_css(
            "color", "rgb(42, 42, 42)", timeout=100
        )


async def test_assertions_locator_to_have_id(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<div class=foobar id=kek>kek</div>")
    await expect(page.locator("div.foobar")).to_have_id("kek")
    await expect(page.locator("div.foobar")).not_to_have_id("top", timeout=100)
    with pytest.raises(AssertionError):
        await expect(page.locator("div.foobar")).to_have_id("top", timeout=100)


async def test_assertions_locator_to_have_js_property(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<div></div>")
    await page.eval_on_selector(
        "div", "e => e.foo = { a: 1, b: 'string', c: new Date(1627503992000) }"
    )
    await expect(page.locator("div")).to_have_js_property(
        "foo",
        {
            "a": 1,
            "b": "string",
            "c": datetime.datetime.fromtimestamp(1627503992000 / 1000),
        },
    )


async def test_to_have_js_property_pass_string(page: Page) -> None:
    await page.set_content("<div></div>")
    await page.eval_on_selector("div", "e => e.foo = 'string'")
    locator = page.locator("div")
    await expect(locator).to_have_js_property("foo", "string")


async def test_to_have_js_property_fail_string(page: Page) -> None:
    await page.set_content("<div></div>")
    await page.eval_on_selector("div", "e => e.foo = 'string'")
    locator = page.locator("div")
    with pytest.raises(AssertionError):
        await expect(locator).to_have_js_property("foo", "error", timeout=500)


async def test_to_have_js_property_pass_number(page: Page) -> None:
    await page.set_content("<div></div>")
    await page.eval_on_selector("div", "e => e.foo = 2021")
    locator = page.locator("div")
    await expect(locator).to_have_js_property("foo", 2021)


async def test_to_have_js_property_fail_number(page: Page) -> None:
    await page.set_content("<div></div>")
    await page.eval_on_selector("div", "e => e.foo = 2021")
    locator = page.locator("div")
    with pytest.raises(AssertionError):
        await expect(locator).to_have_js_property("foo", 1, timeout=500)


async def test_to_have_js_property_pass_boolean(page: Page) -> None:
    await page.set_content("<div></div>")
    await page.eval_on_selector("div", "e => e.foo = true")
    locator = page.locator("div")
    await expect(locator).to_have_js_property("foo", True)


async def test_to_have_js_property_fail_boolean(page: Page) -> None:
    await page.set_content("<div></div>")
    await page.eval_on_selector("div", "e => e.foo = false")
    locator = page.locator("div")
    with pytest.raises(AssertionError):
        await expect(locator).to_have_js_property("foo", True, timeout=500)


async def test_to_have_js_property_pass_boolean_2(page: Page) -> None:
    await page.set_content("<div></div>")
    await page.eval_on_selector("div", "e => e.foo = false")
    locator = page.locator("div")
    await expect(locator).to_have_js_property("foo", False)


async def test_to_have_js_property_fail_boolean_2(page: Page) -> None:
    await page.set_content("<div></div>")
    await page.eval_on_selector("div", "e => e.foo = false")
    locator = page.locator("div")
    with pytest.raises(AssertionError):
        await expect(locator).to_have_js_property("foo", True, timeout=500)


async def test_to_have_js_property_pass_null(page: Page) -> None:
    await page.set_content("<div></div>")
    await page.eval_on_selector("div", "e => e.foo = null")
    locator = page.locator("div")
    await expect(locator).to_have_js_property("foo", None)


async def test_assertions_locator_to_have_text(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<div id=foobar>kek</div>")
    await expect(page.locator("div#foobar")).to_have_text("kek")
    await expect(page.locator("div#foobar")).not_to_have_text("top", timeout=100)

    await page.set_content("<div>Text    \n1</div><div>Text   2a</div>")
    # Should only normalize whitespace in the first item.
    await expect(page.locator("div")).to_have_text(
        ["Text  1", re.compile(r"Text   \d+a")]
    )


@pytest.mark.parametrize(
    "method",
    ["to_have_text", "to_contain_text"],
)
async def test_ignore_case(page: Page, server: Server, method: str) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<div id=target>apple BANANA</div><div>orange</div>")
    await getattr(expect(page.locator("div#target")), method)("apple BANANA")
    await getattr(expect(page.locator("div#target")), method)(
        "apple banana", ignore_case=True
    )
    # defaults false
    with pytest.raises(AssertionError) as excinfo:
        await getattr(expect(page.locator("div#target")), method)(
            "apple banana", timeout=300
        )
    expected_error_msg = method.replace("_", " ")
    assert expected_error_msg in str(excinfo.value)

    # Array Variants
    await getattr(expect(page.locator("div")), method)(["apple BANANA", "orange"])
    await getattr(expect(page.locator("div")), method)(
        ["apple banana", "ORANGE"], ignore_case=True
    )
    # defaults false
    with pytest.raises(AssertionError) as excinfo:
        await getattr(expect(page.locator("div")), method)(
            ["apple banana", "ORANGE"], timeout=300
        )
    assert expected_error_msg in str(excinfo.value)

    # not variant
    await getattr(expect(page.locator("div#target")), f"not_{method}")("apple banana")
    with pytest.raises(AssertionError) as excinfo:
        await getattr(expect(page.locator("div#target")), f"not_{method}")(
            "apple banana", ignore_case=True, timeout=300
        )
    assert f"not {expected_error_msg}" in str(excinfo)


@pytest.mark.parametrize(
    "method",
    ["to_have_text", "to_contain_text"],
)
async def test_ignore_case_regex(page: Page, server: Server, method: str) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<div id=target>apple BANANA</div><div>orange</div>")
    await getattr(expect(page.locator("div#target")), method)(
        re.compile("apple BANANA")
    )
    await getattr(expect(page.locator("div#target")), method)(
        re.compile("apple banana"), ignore_case=True
    )
    # defaults to regex flag
    with pytest.raises(AssertionError) as excinfo:
        await getattr(expect(page.locator("div#target")), method)(
            re.compile("apple banana"), timeout=300
        )
    expected_error_msg = method.replace("_", " ")
    assert expected_error_msg in str(excinfo.value)
    # overrides regex flag
    with pytest.raises(AssertionError) as excinfo:
        await getattr(expect(page.locator("div#target")), method)(
            re.compile("apple banana", re.IGNORECASE), ignore_case=False, timeout=300
        )
    assert expected_error_msg in str(excinfo.value)

    # Array Variants
    await getattr(expect(page.locator("div")), method)(
        [re.compile("apple BANANA"), re.compile("orange")]
    )
    await getattr(expect(page.locator("div")), method)(
        [re.compile("apple banana"), re.compile("ORANGE")], ignore_case=True
    )
    # defaults regex flag
    with pytest.raises(AssertionError) as excinfo:
        await getattr(expect(page.locator("div")), method)(
            [re.compile("apple banana"), re.compile("ORANGE")], timeout=300
        )
    assert expected_error_msg in str(excinfo.value)
    # overrides regex flag
    with pytest.raises(AssertionError) as excinfo:
        await getattr(expect(page.locator("div")), method)(
            [
                re.compile("apple banana", re.IGNORECASE),
                re.compile("ORANGE", re.IGNORECASE),
            ],
            ignore_case=False,
            timeout=300,
        )
    assert expected_error_msg in str(excinfo.value)

    # not variant
    await getattr(expect(page.locator("div#target")), f"not_{method}")(
        re.compile("apple banana")
    )
    with pytest.raises(AssertionError) as excinfo:
        await getattr(expect(page.locator("div#target")), f"not_{method}")(
            re.compile("apple banana"), ignore_case=True, timeout=300
        )
    assert f"not {expected_error_msg}" in str(excinfo)


async def test_assertions_locator_to_have_value(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<input type=text id=foo>")
    my_input = page.locator("#foo")
    await expect(my_input).to_have_value("")
    await expect(my_input).not_to_have_value("bar", timeout=100)
    await my_input.fill("kektus")
    await expect(my_input).to_have_value("kektus")


async def test_to_have_values_works_with_text(page: Page, server: Server) -> None:
    await page.set_content(
        """
        <select multiple>
            <option value="R">Red</option>
            <option value="G">Green</option>
            <option value="B">Blue</option>
        </select>
    """
    )
    locator = page.locator("select")
    await locator.select_option(["R", "G"])
    await expect(locator).to_have_values(["R", "G"])


async def test_to_have_values_follows_labels(page: Page, server: Server) -> None:
    await page.set_content(
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
    await locator.select_option(["R", "G"])
    await expect(locator).to_have_values(["R", "G"])


async def test_to_have_values_exact_match_with_text(page: Page, server: Server) -> None:
    await page.set_content(
        """
        <select multiple>
            <option value="RR">Red</option>
            <option value="GG">Green</option>
        </select>
    """
    )
    locator = page.locator("select")
    await locator.select_option(["RR", "GG"])
    with pytest.raises(AssertionError) as excinfo:
        await expect(locator).to_have_values(["R", "G"], timeout=500)
    assert "Locator expected to have Values '['R', 'G']'" in str(excinfo.value)
    assert "Actual value: ['RR', 'GG']" in str(excinfo.value)


async def test_to_have_values_works_with_regex(page: Page, server: Server) -> None:
    await page.set_content(
        """
        <select multiple>
            <option value="R">Red</option>
            <option value="G">Green</option>
            <option value="B">Blue</option>
        </select>
    """
    )
    locator = page.locator("select")
    await locator.select_option(["R", "G"])
    await expect(locator).to_have_values([re.compile("R"), re.compile("G")])


async def test_to_have_values_fails_when_items_not_selected(
    page: Page, server: Server
) -> None:
    await page.set_content(
        """
        <select multiple>
            <option value="R">Red</option>
            <option value="G">Green</option>
            <option value="B">Blue</option>
        </select>
    """
    )
    locator = page.locator("select")
    await locator.select_option(["B"])
    with pytest.raises(AssertionError) as excinfo:
        await expect(locator).to_have_values(["R", "G"], timeout=500)
    assert "Locator expected to have Values '['R', 'G']'" in str(excinfo.value)
    assert "Actual value: ['B']" in str(excinfo.value)


async def test_to_have_values_fails_when_multiple_not_specified(
    page: Page, server: Server
) -> None:
    await page.set_content(
        """
        <select>
            <option value="R">Red</option>
            <option value="G">Green</option>
            <option value="B">Blue</option>
        </select>
    """
    )
    locator = page.locator("select")
    await locator.select_option(["B"])
    with pytest.raises(Error) as excinfo:
        await expect(locator).to_have_values(["R", "G"], timeout=500)
    assert "Error: Not a select element with a multiple attribute" in str(excinfo.value)


async def test_to_have_values_fails_when_not_a_select_element(
    page: Page, server: Server
) -> None:
    await page.set_content(
        """
        <input type="text">
    """
    )
    locator = page.locator("input")
    with pytest.raises(Error) as excinfo:
        await expect(locator).to_have_values(["R", "G"], timeout=500)
    assert "Error: Not a select element with a multiple attribute" in str(excinfo.value)


async def test_assertions_locator_to_be_checked(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<input type=checkbox>")
    my_checkbox = page.locator("input")
    await expect(my_checkbox).not_to_be_checked()
    with pytest.raises(AssertionError, match="Locator expected to be checked"):
        await expect(my_checkbox).to_be_checked(timeout=100)
    await expect(my_checkbox).to_be_checked(timeout=100, checked=False)
    with pytest.raises(AssertionError):
        await expect(my_checkbox).to_be_checked(timeout=100, checked=True)
    await my_checkbox.check()
    await expect(my_checkbox).to_be_checked(timeout=100, checked=True)
    with pytest.raises(AssertionError, match="Locator expected to be unchecked"):
        await expect(my_checkbox).to_be_checked(timeout=100, checked=False)
    await expect(my_checkbox).to_be_checked()


async def test_assertions_locator_to_be_disabled_enabled(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<input type=checkbox>")
    my_checkbox = page.locator("input")
    await expect(my_checkbox).not_to_be_disabled()
    await expect(my_checkbox).to_be_enabled()
    with pytest.raises(AssertionError):
        await expect(my_checkbox).to_be_disabled(timeout=100)
    await my_checkbox.evaluate("e => e.disabled = true")
    await expect(my_checkbox).to_be_disabled()
    with pytest.raises(AssertionError, match="Locator expected to be enabled"):
        await expect(my_checkbox).to_be_enabled(timeout=100)


async def test_assertions_locator_to_be_enabled_with_true(page: Page) -> None:
    await page.set_content("<button>Text</button>")
    await expect(page.locator("button")).to_be_enabled(enabled=True)


async def test_assertions_locator_to_be_enabled_with_false_throws_good_exception(
    page: Page,
) -> None:
    await page.set_content("<button>Text</button>")
    with pytest.raises(AssertionError, match="Locator expected to be disabled"):
        await expect(page.locator("button")).to_be_enabled(enabled=False)


async def test_assertions_locator_to_be_enabled_with_false(page: Page) -> None:
    await page.set_content("<button disabled>Text</button>")
    await expect(page.locator("button")).to_be_enabled(enabled=False)


async def test_assertions_locator_to_be_enabled_with_not_and_false(page: Page) -> None:
    await page.set_content("<button>Text</button>")
    await expect(page.locator("button")).not_to_be_enabled(enabled=False)


async def test_assertions_locator_to_be_enabled_eventually(page: Page) -> None:
    await page.set_content("<button disabled>Text</button>")
    await page.eval_on_selector(
        "button",
        """
        button => setTimeout(() => {
            button.removeAttribute('disabled');
        }, 700);
    """,
    )
    await expect(page.locator("button")).to_be_enabled()


async def test_assertions_locator_to_be_enabled_eventually_with_not(page: Page) -> None:
    await page.set_content("<button>Text</button>")
    await page.eval_on_selector(
        "button",
        """
        button => setTimeout(() => {
            button.setAttribute('disabled', '');
        }, 700);
    """,
    )
    await expect(page.locator("button")).not_to_be_enabled()


async def test_assertions_locator_to_be_editable(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<input></input><button disabled>Text</button>")
    await expect(page.locator("button")).not_to_be_editable()
    await expect(page.locator("input")).to_be_editable()
    with pytest.raises(AssertionError, match="Locator expected to be editable"):
        await expect(page.locator("button")).to_be_editable(timeout=100)


async def test_assertions_locator_to_be_editable_with_true(page: Page) -> None:
    await page.set_content("<input></input>")
    await expect(page.locator("input")).to_be_editable(editable=True)


async def test_assertions_locator_to_be_editable_with_false(page: Page) -> None:
    await page.set_content("<input readonly></input>")
    await expect(page.locator("input")).to_be_editable(editable=False)


async def test_assertions_locator_to_be_editable_with_false_and_throw_good_exception(
    page: Page,
) -> None:
    await page.set_content("<input></input>")
    with pytest.raises(AssertionError, match="Locator expected to be readonly"):
        await expect(page.locator("input")).to_be_editable(editable=False)


async def test_assertions_locator_to_be_editable_with_not_and_false(page: Page) -> None:
    await page.set_content("<input></input>")
    await expect(page.locator("input")).not_to_be_editable(editable=False)


async def test_assertions_locator_to_be_empty(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        "<input value=text name=input1></input><input name=input2></input>"
    )
    await expect(page.locator("input[name=input1]")).not_to_be_empty()
    await expect(page.locator("input[name=input2]")).to_be_empty()
    with pytest.raises(AssertionError):
        await expect(page.locator("input[name=input1]")).to_be_empty(timeout=100)


async def test_assertions_locator_to_be_focused(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<input type=checkbox>")
    my_checkbox = page.locator("input")
    with pytest.raises(AssertionError):
        await expect(my_checkbox).to_be_focused(timeout=100)
    await my_checkbox.focus()
    await expect(my_checkbox).to_be_focused()


async def test_assertions_locator_to_be_hidden_visible(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<div style='width: 50px; height: 50px;'>Something</div>")
    my_checkbox = page.locator("div")
    await expect(my_checkbox).to_be_visible()
    with pytest.raises(AssertionError):
        await expect(my_checkbox).to_be_hidden(timeout=100)
    await my_checkbox.evaluate("e => e.style.display = 'none'")
    await expect(my_checkbox).to_be_hidden()
    with pytest.raises(AssertionError, match="Locator expected to be visible"):
        await expect(my_checkbox).to_be_visible(timeout=100)


async def test_assertions_locator_to_be_visible_with_true(page: Page) -> None:
    await page.set_content("<button>hello</button>")
    await expect(page.locator("button")).to_be_visible(visible=True)


async def test_assertions_locator_to_be_visible_with_false(page: Page) -> None:
    await page.set_content("<button hidden>hello</button>")
    await expect(page.locator("button")).to_be_visible(visible=False)


async def test_assertions_locator_to_be_visible_with_false_throws_good_exception(
    page: Page,
) -> None:
    await page.set_content("<button>hello</button>")
    with pytest.raises(AssertionError, match="Locator expected to be hidden"):
        await expect(page.locator("button")).to_be_visible(visible=False)


async def test_assertions_locator_to_be_visible_with_not_and_false(page: Page) -> None:
    await page.set_content("<button>hello</button>")
    await expect(page.locator("button")).not_to_be_visible(visible=False)


async def test_assertions_locator_to_be_visible_eventually(page: Page) -> None:
    await page.set_content("<div></div>")
    await page.eval_on_selector(
        "div",
        """
        div => setTimeout(() => {
            div.innerHTML = '<span>Hello</span>';
        }, 700);
    """,
    )
    await expect(page.locator("span")).to_be_visible()


async def test_assertions_locator_to_be_visible_eventually_with_not(page: Page) -> None:
    await page.set_content("<div><span>Hello</span></div>")
    await page.eval_on_selector(
        "span",
        """
        span => setTimeout(() => {
            span.textContent = '';
        }, 700);
    """,
    )
    await expect(page.locator("span")).not_to_be_visible()


async def test_assertions_should_serialize_regexp_correctly(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<div>iGnOrEcAsE</div>")
    await expect(page.locator("div")).to_have_text(
        re.compile(r"ignorecase", re.IGNORECASE)
    )
    await page.set_content(
        """<div>start
some
lines
between
end</div>"""
    )
    await expect(page.locator("div")).to_have_text(re.compile(r"start.*end", re.DOTALL))
    await page.set_content(
        """<div>line1
line2
line3</div>"""
    )
    await expect(page.locator("div")).to_have_text(re.compile(r"^line2$", re.MULTILINE))


async def test_assertions_response_is_ok_pass(page: Page, server: Server) -> None:
    response = await page.request.get(server.EMPTY_PAGE)
    await expect(response).to_be_ok()


async def test_assertions_response_is_ok_pass_with_not(
    page: Page, server: Server
) -> None:
    response = await page.request.get(server.PREFIX + "/unknown")
    await expect(response).not_to_be_ok()


async def test_assertions_response_is_ok_fail(page: Page, server: Server) -> None:
    response = await page.request.get(server.PREFIX + "/unknown")
    with pytest.raises(AssertionError) as excinfo:
        await expect(response).to_be_ok()
    error_message = str(excinfo.value)
    assert ("→ GET " + server.PREFIX + "/unknown") in error_message
    assert "← 404 Not Found" in error_message


async def test_should_print_response_with_text_content_type_if_to_be_ok_fails(
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

    response = await page.request.get(server.PREFIX + "/text-content-type")
    with pytest.raises(AssertionError) as excinfo:
        await expect(response).to_be_ok()
    error_message = str(excinfo.value)
    assert ("→ GET " + server.PREFIX + "/text-content-type") in error_message
    assert "← 404 Not Found" in error_message
    assert "Response Text:" in error_message
    assert "Text error" in error_message

    response = await page.request.get(server.PREFIX + "/no-content-type")
    with pytest.raises(AssertionError) as excinfo:
        await expect(response).to_be_ok()
    error_message = str(excinfo.value)
    assert ("→ GET " + server.PREFIX + "/no-content-type") in error_message
    assert "← 404 Not Found" in error_message
    assert "Response Text:" not in error_message
    assert "No content type error" not in error_message

    response = await page.request.get(server.PREFIX + "/binary-content-type")
    with pytest.raises(AssertionError) as excinfo:
        await expect(response).to_be_ok()
    error_message = str(excinfo.value)
    assert ("→ GET " + server.PREFIX + "/binary-content-type") in error_message
    assert "← 404 Not Found" in error_message
    assert "Response Text:" not in error_message
    assert "Image content type error" not in error_message


async def test_should_print_users_message_for_page_based_assertion(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<title>new title</title>")
    with pytest.raises(AssertionError) as excinfo:
        await expect(page, "Title is not new").to_have_title("old title", timeout=100)
    assert "Title is not new" in str(excinfo.value)
    with pytest.raises(AssertionError) as excinfo:
        await expect(page).to_have_title("old title", timeout=100)
    assert "Page title expected to be" in str(excinfo.value)


async def test_should_print_expected_value_with_custom_message(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<title>new title</title>")
    with pytest.raises(AssertionError) as excinfo:
        await expect(page, "custom-message").to_have_title("old title", timeout=100)
    assert "custom-message" in str(excinfo.value)
    assert "Expected value: 'old title'" in str(excinfo.value)
    with pytest.raises(AssertionError) as excinfo:
        await expect(page.get_by_text("hello"), "custom-message").to_be_visible(
            timeout=100
        )
    assert "custom-message" in str(excinfo.value)
    assert "Expected value" not in str(excinfo.value)


async def test_should_be_attached_default(page: Page) -> None:
    await page.set_content("<input></input>")
    locator = page.locator("input")
    await expect(locator).to_be_attached()


async def test_should_be_attached_with_hidden_element(page: Page) -> None:
    await page.set_content('<button style="display:none">hello</button>')
    locator = page.locator("button")
    await expect(locator).to_be_attached()


async def test_should_be_attached_with_not(page: Page) -> None:
    await page.set_content("<button>hello</button>")
    locator = page.locator("input")
    await expect(locator).not_to_be_attached()


async def test_should_be_attached_with_attached_true(page: Page) -> None:
    await page.set_content("<button>hello</button>")
    locator = page.locator("button")
    await expect(locator).to_be_attached(attached=True)


async def test_should_be_attached_with_attached_false(page: Page) -> None:
    await page.set_content("<button>hello</button>")
    locator = page.locator("input")
    await expect(locator).to_be_attached(attached=False)


async def test_should_be_attached_with_attached_false_and_throw_good_error(
    page: Page,
) -> None:
    await page.set_content("<button>hello</button>")
    locator = page.locator("button")
    with pytest.raises(AssertionError, match="Locator expected to be detached"):
        await expect(locator).to_be_attached(attached=False, timeout=1)


async def test_should_be_attached_with_not_and_attached_false(page: Page) -> None:
    await page.set_content("<button>hello</button>")
    locator = page.locator("button")
    await expect(locator).not_to_be_attached(attached=False)


async def test_should_be_attached_eventually(page: Page) -> None:
    await page.set_content("<div></div>")
    locator = page.locator("span")
    await page.locator("div").evaluate(
        "(e) => setTimeout(() => e.innerHTML = '<span>hello</span>', 1000)"
    )
    await expect(locator).to_be_attached()


async def test_should_be_attached_eventually_with_not(page: Page) -> None:
    await page.set_content("<div><span>Hello</span></div>")
    locator = page.locator("span")
    await page.locator("div").evaluate(
        "(e) => setTimeout(() => e.textContent = '', 1000)"
    )
    await expect(locator).not_to_be_attached()


async def test_should_be_attached_fail(page: Page) -> None:
    await page.set_content("<button>Hello</button>")
    locator = page.locator("input")
    with pytest.raises(
        AssertionError, match="Locator expected to be attached"
    ) as exc_info:
        await expect(locator).to_be_attached(timeout=1000)
    assert "locator resolved to" not in exc_info.value.args[0]


async def test_should_be_attached_fail_with_not(page: Page) -> None:
    await page.set_content("<input></input>")
    locator = page.locator("input")
    with pytest.raises(AssertionError) as exc_info:
        await expect(locator).not_to_be_attached(timeout=1000)
    assert "locator resolved to <input/>" in exc_info.value.args[0]


async def test_should_be_attached_with_impossible_timeout(page: Page) -> None:
    await page.set_content("<div id=node>Text content</div>")
    await expect(page.locator("#node")).to_be_attached(timeout=1)


async def test_should_be_attached_with_impossible_timeout_not(page: Page) -> None:
    await page.set_content("<div id=node>Text content</div>")
    await expect(page.locator("no-such-thing")).not_to_be_attached(timeout=1)


async def test_should_be_attached_with_frame_locator(page: Page) -> None:
    await page.set_content("<div></div>")
    locator = page.frame_locator("iframe").locator("input")
    task = asyncio.create_task(expect(locator).to_be_attached())
    await page.wait_for_timeout(1000)
    assert not task.done()
    await page.set_content('<iframe srcdoc="<input>"></iframe>')
    await task
    assert task.done()


async def test_should_be_attached_over_navigation(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    task = asyncio.create_task(expect(page.locator("input")).to_be_attached())
    await page.wait_for_timeout(1000)
    assert not task.done()
    await page.goto(server.PREFIX + "/input/checkbox.html")
    await task
    assert task.done()


async def test_should_be_able_to_set_custom_timeout(page: Page) -> None:
    with pytest.raises(AssertionError) as exc_info:
        await expect(page.locator("#a1")).to_be_visible(timeout=111)
    assert "LocatorAssertions.to_be_visible with timeout 111ms" in str(exc_info.value)


async def test_should_be_able_to_set_custom_global_timeout(page: Page) -> None:
    try:
        expect.set_options(timeout=111)
        with pytest.raises(AssertionError) as exc_info:
            await expect(page.locator("#a1")).to_be_visible()
        assert "LocatorAssertions.to_be_visible with timeout 111ms" in str(
            exc_info.value
        )
    finally:
        expect.set_options(timeout=None)


async def test_to_have_accessible_name(page: Page) -> None:
    await page.set_content('<div role="button" aria-label="Hello"></div>')
    locator = page.locator("div")
    await expect(locator).to_have_accessible_name("Hello")
    await expect(locator).not_to_have_accessible_name("hello")
    await expect(locator).to_have_accessible_name("hello", ignore_case=True)
    await expect(locator).to_have_accessible_name(re.compile(r"ell\w"))
    await expect(locator).not_to_have_accessible_name(re.compile(r"hello"))
    await expect(locator).to_have_accessible_name(
        re.compile(r"hello"), ignore_case=True
    )


async def test_to_have_accessible_description(page: Page) -> None:
    await page.set_content('<div role="button" aria-description="Hello"></div>')
    locator = page.locator("div")
    await expect(locator).to_have_accessible_description("Hello")
    await expect(locator).not_to_have_accessible_description("hello")
    await expect(locator).to_have_accessible_description("hello", ignore_case=True)
    await expect(locator).to_have_accessible_description(re.compile(r"ell\w"))
    await expect(locator).not_to_have_accessible_description(re.compile(r"hello"))
    await expect(locator).to_have_accessible_description(
        re.compile(r"hello"), ignore_case=True
    )


async def test_to_have_role(page: Page) -> None:
    await page.set_content('<div role="button">Button!</div>')
    await expect(page.locator("div")).to_have_role("button")
    await expect(page.locator("div")).not_to_have_role("checkbox")
    with pytest.raises(Error) as excinfo:
        await expect(page.locator("div")).to_have_role(re.compile(r"button|checkbox"))  # type: ignore
    assert '"role" argument in to_have_role must be a string' in str(excinfo.value)
