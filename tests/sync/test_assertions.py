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
from datetime import datetime

import pytest

from playwright.sync_api import Browser, Page, expect
from tests.server import Server


def test_assertions_page_to_have_title(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content(
        """
        <script>
            document.title = 'new title';
            setTimeout(() => {
                document.title = 'great title';
            }, 2000);
        </script>
    """
    )
    expect(page).to_have_title("new title")
    expect(page).to_have_title(re.compile("new title"))
    with pytest.raises(AssertionError):
        expect(page).to_have_title("not the current title", timeout=100)
    with pytest.raises(AssertionError):
        expect(page).to_have_title(re.compile("not the current title"), timeout=100)
    with pytest.raises(AssertionError):
        expect(page).not_to_have_title(re.compile("new title"), timeout=100)
    with pytest.raises(AssertionError):
        expect(page).not_to_have_title("new title", timeout=100)
    expect(page).not_to_have_title("great title", timeout=100)
    expect(page).to_have_title("great title")
    expect(page).to_have_title(re.compile("great title"))


def test_assertions_page_to_have_url(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content(
        """
        <script>
            setTimeout(() => {
                window.location = window.location.origin + '/grid.html';
            }, 2000);
        </script>
    """
    )
    expect(page).to_have_url(server.EMPTY_PAGE)
    expect(page).to_have_url(re.compile(r".*/empty\.html"))
    with pytest.raises(AssertionError):
        expect(page).to_have_url("nooooo", timeout=100)
    with pytest.raises(AssertionError):
        expect(page).to_have_url(re.compile("not-the-url"), timeout=100)
    expect(page).to_have_url(server.PREFIX + "/grid.html")
    expect(page).not_to_have_url(server.EMPTY_PAGE, timeout=100)
    with pytest.raises(AssertionError):
        expect(page).not_to_have_url(re.compile(r".*/grid\.html"), timeout=100)
    with pytest.raises(AssertionError):
        expect(page).not_to_have_url(server.PREFIX + "/grid.html", timeout=100)
    expect(page).to_have_url(re.compile(r".*/grid\.html"))
    expect(page).not_to_have_url("**/empty.html", timeout=100)


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
        {"a": 1, "b": "string", "c": datetime.utcfromtimestamp(1627503992000 / 1000)},
    )


def test_assertions_locator_to_have_text(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content("<div id=foobar>kek</div>")
    expect(page.locator("div#foobar")).to_have_text("kek")
    expect(page.locator("div#foobar")).not_to_have_text("top", timeout=100)

    page.set_content("<div>Text    \n1</div><div>Text   2a</div>")
    # Should only normalize whitespace in the first item.
    expect(page.locator("div")).to_have_text(["Text  1", re.compile(r"Text   \d+a")])


def test_assertions_locator_to_have_value(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content("<input type=text id=foo>")
    my_input = page.locator("#foo")
    expect(my_input).to_have_value("")
    expect(my_input).not_to_have_value("bar", timeout=100)
    my_input.fill("kektus")
    expect(my_input).to_have_value("kektus")


def test_assertions_locator_to_be_checked(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content("<input type=checkbox>")
    my_checkbox = page.locator("input")
    expect(my_checkbox).not_to_be_checked()
    with pytest.raises(AssertionError):
        expect(my_checkbox).to_be_checked(timeout=100)
    my_checkbox.check()
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
    with pytest.raises(AssertionError):
        expect(my_checkbox).to_be_enabled(timeout=100)


def test_assertions_locator_to_be_editable(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content("<input></input><button disabled>Text</button>")
    expect(page.locator("button")).not_to_be_editable()
    expect(page.locator("input")).to_be_editable()
    with pytest.raises(AssertionError):
        expect(page.locator("button")).to_be_editable(timeout=100)


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
    with pytest.raises(AssertionError):
        expect(my_checkbox).to_be_visible(timeout=100)


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
