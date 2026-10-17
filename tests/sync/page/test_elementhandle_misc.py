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

"""Port of tests/page/elementhandle-misc.spec.ts."""

from playwright.sync_api import Page
from tests.server import Server


def test_EH_045_should_hover(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/scrollable.html")
    button = page.query_selector("#button-6")
    assert button
    button.hover()
    assert (
        page.evaluate("() => document.querySelector('button:hover').id") == "button-6"
    )


def test_EH_046_should_hover_when_node_is_removed(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/scrollable.html")
    page.evaluate("() => delete window['Node']")
    button = page.query_selector("#button-6")
    assert button
    button.hover()
    assert (
        page.evaluate("() => document.querySelector('button:hover').id") == "button-6"
    )


def test_EH_047_should_fill_input(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/textarea.html")
    handle = page.query_selector("input")
    assert handle
    handle.fill("some value")
    assert page.evaluate("() => window['result']") == "some value"


def test_EH_048_should_fill_input_when_node_is_removed(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/input/textarea.html")
    page.evaluate("() => delete window['Node']")
    handle = page.query_selector("input")
    assert handle
    handle.fill("some value")
    assert page.evaluate("() => window['result']") == "some value"


def test_EH_049_should_check_the_box(page: Page) -> None:
    page.set_content("<input id='checkbox' type='checkbox'></input>")
    input = page.query_selector("input")
    assert input
    input.check()
    assert page.evaluate("checkbox.checked") is True


def test_EH_050_should_check_the_box_using_set_checked(page: Page) -> None:
    page.set_content("<input id='checkbox' type='checkbox'></input>")
    input = page.query_selector("input")
    assert input
    input.set_checked(True)
    assert page.evaluate("checkbox.checked") is True
    input.set_checked(False)
    assert page.evaluate("checkbox.checked") is False


def test_EH_051_should_uncheck_the_box(page: Page) -> None:
    page.set_content("<input id='checkbox' type='checkbox' checked></input>")
    input = page.query_selector("input")
    assert input
    input.uncheck()
    assert page.evaluate("checkbox.checked") is False


def test_EH_052_should_select_single_option(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/select.html")
    select = page.query_selector("select")
    assert select
    select.select_option("blue")
    assert page.evaluate("() => window['result'].onInput") == ["blue"]
    assert page.evaluate("() => window['result'].onChange") == ["blue"]


def test_EH_053_should_focus_a_button(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/button.html")
    button = page.query_selector("button")
    assert button
    assert button.evaluate("button => document.activeElement === button") is False
    button.focus()
    assert button.evaluate("button => document.activeElement === button") is True


def test_EH_054_should_allow_disposing_twice(page: Page) -> None:
    page.set_content("<section>39</section>")
    element = page.query_selector("section")
    assert element
    element.dispose()
    element.dispose()
