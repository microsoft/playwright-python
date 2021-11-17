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

from playwright.async_api import Browser, Page, assert_that
from tests.server import Server


async def test_assertions_page_has_title(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        """
        <script>
            document.title = 'new title';
            setTimeout(() => {
                document.title = 'great title';
            }, 2000);
        </script>
    """
    )
    await assert_that(page).has_title("new title")
    await assert_that(page).has_title(re.compile("new title"))
    with pytest.raises(AssertionError):
        await assert_that(page).has_title("not the current title", timeout=100)
    with pytest.raises(AssertionError):
        await assert_that(page).has_title(
            re.compile("not the current title"), timeout=100
        )
    with pytest.raises(AssertionError):
        await assert_that(page).does_not.has_title(re.compile("new title"), timeout=100)
    with pytest.raises(AssertionError):
        await assert_that(page).does_not.has_title("new title", timeout=100)
    await assert_that(page).does_not.has_title("great title", timeout=100)
    await assert_that(page).has_title("great title")
    await assert_that(page).has_title(re.compile("great title"))
    await assert_that(page).does_not.has_title("new title", timeout=100)


async def test_assertions_page_has_url(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        """
        <script>
            setTimeout(() => {
                window.location = window.location.origin + '/grid.html';
            }, 2000);
        </script>
    """
    )
    await assert_that(page).has_url(server.EMPTY_PAGE)
    await assert_that(page).has_url(re.compile(r".*/empty\.html"))
    with pytest.raises(AssertionError):
        await assert_that(page).has_url("nooooo", timeout=100)
    with pytest.raises(AssertionError):
        await assert_that(page).has_url(re.compile("not-the-url"), timeout=100)
    await assert_that(page).has_url(server.PREFIX + "/grid.html")
    await assert_that(page).does_not.has_url(server.EMPTY_PAGE, timeout=100)
    with pytest.raises(AssertionError):
        await assert_that(page).does_not.has_url(
            re.compile(r".*/grid\.html"), timeout=100
        )
    with pytest.raises(AssertionError):
        await assert_that(page).does_not.has_url(
            server.PREFIX + "/grid.html", timeout=100
        )
    await assert_that(page).has_url(re.compile(r".*/grid\.html"))
    await assert_that(page).does_not.has_url("**/empty.html", timeout=100)


async def test_assertions_page_has_url_with_base_url(
    browser: Browser, server: Server
) -> None:
    page = await browser.new_page(base_url=server.PREFIX)
    await page.goto("/empty.html")
    await assert_that(page).has_url("/empty.html")
    await assert_that(page).has_url(re.compile(r".*/empty\.html"))
    await page.close()


async def test_assertions_locator_contains_text(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<div id=foobar>kek</div>")
    await assert_that(page.locator("div#foobar")).contains_text("kek")
    await assert_that(page.locator("div#foobar")).does_not.contains_text(
        "bar", timeout=100
    )
    with pytest.raises(AssertionError):
        await assert_that(page.locator("div#foobar")).contains_text("bar", timeout=100)

    await page.set_content("<div>Text \n1</div><div>Text2</div><div>Text3</div>")
    await assert_that(page.locator("div")).contains_text(
        ["ext     1", re.compile("ext3")]
    )


async def test_assertions_locator_has_attribute(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<div id=foobar>kek</div>")
    await assert_that(page.locator("div#foobar")).has_attribute("id", "foobar")
    await assert_that(page.locator("div#foobar")).has_attribute(
        "id", re.compile("foobar")
    )
    await assert_that(page.locator("div#foobar")).does_not.has_attribute(
        "id", "kek", timeout=100
    )
    with pytest.raises(AssertionError):
        await assert_that(page.locator("div#foobar")).has_attribute(
            "id", "koko", timeout=100
        )


async def test_assertions_locator_has_class(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<div class=foobar>kek</div>")
    await assert_that(page.locator("div.foobar")).has_class("foobar")
    await assert_that(page.locator("div.foobar")).has_class(["foobar"])
    await assert_that(page.locator("div.foobar")).has_class(re.compile("foobar"))
    await assert_that(page.locator("div.foobar")).has_class([re.compile("foobar")])
    await assert_that(page.locator("div.foobar")).does_not.has_class(
        "kekstar", timeout=100
    )
    with pytest.raises(AssertionError):
        await assert_that(page.locator("div.foobar")).has_class("oh-no", timeout=100)


async def test_assertions_locator_has_count(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<div class=foobar>kek</div><div class=foobar>kek</div>")
    await assert_that(page.locator("div.foobar")).has_count(2)
    await assert_that(page.locator("div.foobar")).does_not.has_count(42, timeout=100)
    with pytest.raises(AssertionError):
        await assert_that(page.locator("div.foobar")).has_count(42, timeout=100)


async def test_assertions_locator_has_css(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        "<div class=foobar style='color: rgb(234, 74, 90);'>kek</div>"
    )
    await assert_that(page.locator("div.foobar")).has_css("color", "rgb(234, 74, 90)")
    await assert_that(page.locator("div.foobar")).does_not.has_css(
        "color", "rgb(42, 42, 42)", timeout=100
    )
    with pytest.raises(AssertionError):
        await assert_that(page.locator("div.foobar")).has_css(
            "color", "rgb(42, 42, 42)", timeout=100
        )


async def test_assertions_locator_has_id(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<div class=foobar id=kek>kek</div>")
    await assert_that(page.locator("div.foobar")).has_id("kek")
    await assert_that(page.locator("div.foobar")).does_not.has_id("top", timeout=100)
    with pytest.raises(AssertionError):
        await assert_that(page.locator("div.foobar")).has_id("top", timeout=100)


async def test_assertions_locator_has_js_property(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<div></div>")
    await page.eval_on_selector(
        "div", "e => e.foo = { a: 1, b: 'string', c: new Date(1627503992000) }"
    )
    await assert_that(page.locator("div")).has_js_property(
        "foo",
        {"a": 1, "b": "string", "c": datetime.utcfromtimestamp(1627503992000 / 1000)},
    )


async def test_assertions_locator_has_text(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<div id=foobar>kek</div>")
    await assert_that(page.locator("div#foobar")).has_text("kek")
    await assert_that(page.locator("div#foobar")).does_not.has_text("top", timeout=100)

    await page.set_content("<div>Text    \n1</div><div>Text   2a</div>")
    # Should only normalize whitespace in the first item.
    await assert_that(page.locator("div")).has_text(
        ["Text  1", re.compile(r"Text   \d+a")]
    )


async def test_assertions_locator_value(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<input type=text id=foo>")
    my_input = page.locator("#foo")
    await assert_that(my_input).has_value("")
    await assert_that(my_input).does_not.has_value("bar", timeout=100)
    await my_input.fill("kektus")
    await assert_that(my_input).has_value("kektus")


async def test_assertions_locator_is_checked(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<input type=checkbox>")
    my_checkbox = page.locator("input")
    await assert_that(my_checkbox).does_not.is_checked()
    with pytest.raises(AssertionError):
        await assert_that(my_checkbox).is_checked(timeout=100)
    await my_checkbox.check()
    await assert_that(my_checkbox).is_checked()


async def test_assertions_locator_is_disabled_enabled(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<input type=checkbox>")
    my_checkbox = page.locator("input")
    await assert_that(my_checkbox).does_not.is_disabled()
    await assert_that(my_checkbox).is_enabled()
    with pytest.raises(AssertionError):
        await assert_that(my_checkbox).is_disabled(timeout=100)
    await my_checkbox.evaluate("e => e.disabled = true")
    await assert_that(my_checkbox).is_disabled()
    with pytest.raises(AssertionError):
        await assert_that(my_checkbox).is_enabled(timeout=100)


async def test_assertions_locator_is_editable(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<input></input><button disabled>Text</button>")
    await assert_that(page.locator("button")).does_not.is_editable()
    await assert_that(page.locator("input")).is_editable()
    with pytest.raises(AssertionError):
        await assert_that(page.locator("button")).is_editable(timeout=100)


async def test_assertions_locator_is_empty(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        "<input value=text name=input1></input><input name=input2></input>"
    )
    await assert_that(page.locator("input[name=input1]")).does_not.is_empty()
    await assert_that(page.locator("input[name=input2]")).is_empty()
    with pytest.raises(AssertionError):
        await assert_that(page.locator("input[name=input1]")).is_empty(timeout=100)


async def test_assertions_locator_is_focused(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<input type=checkbox>")
    my_checkbox = page.locator("input")
    with pytest.raises(AssertionError):
        await assert_that(my_checkbox).is_focused(timeout=100)
    await my_checkbox.focus()
    await assert_that(my_checkbox).is_focused()


async def test_assertions_locator_is_hidden_visible(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<div style='width: 50px; height: 50px;'>Something</div>")
    my_checkbox = page.locator("div")
    await assert_that(my_checkbox).is_visible()
    with pytest.raises(AssertionError):
        await assert_that(my_checkbox).is_hidden(timeout=100)
    await my_checkbox.evaluate("e => e.style.display = 'none'")
    await assert_that(my_checkbox).is_hidden()
    with pytest.raises(AssertionError):
        await assert_that(my_checkbox).is_visible(timeout=100)


async def test_assertions_should_serialize_regexp_correctly(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<div>iGnOrEcAsE</div>")
    await assert_that(page.locator("div")).has_text(
        re.compile(r"ignorecase", re.IGNORECASE)
    )
    await page.set_content(
        """<div>start
some
lines
between
end</div>"""
    )
    await assert_that(page.locator("div")).has_text(
        re.compile(r"start.*end", re.DOTALL)
    )
    await page.set_content(
        """<div>line1
line2
line3</div>"""
    )
    await assert_that(page.locator("div")).has_text(
        re.compile(r"^line2$", re.MULTILINE)
    )
