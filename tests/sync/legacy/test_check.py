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

from playwright.sync_api import Page


def test_check_the_box(page: Page) -> None:
    page.set_content('<input id="checkbox" type="checkbox"></input>')
    page.check("input")
    assert page.evaluate("checkbox.checked")


def test_not_check_the_checked_box(page: Page) -> None:
    page.set_content('<input id="checkbox" type="checkbox" checked></input>')
    page.check("input")
    assert page.evaluate("checkbox.checked")


def test_uncheck_the_box(page: Page) -> None:
    page.set_content('<input id="checkbox" type="checkbox" checked></input>')
    page.uncheck("input")
    assert page.evaluate("checkbox.checked") is False


def test_not_uncheck_the_unchecked_box(page: Page) -> None:
    page.set_content('<input id="checkbox" type="checkbox"></input>')
    page.uncheck("input")
    assert page.evaluate("checkbox.checked") is False


def test_check_the_box_by_label(page: Page) -> None:
    page.set_content(
        '<label for="checkbox"><input id="checkbox" type="checkbox"></input></label>'
    )
    page.check("label")
    assert page.evaluate("checkbox.checked")


def test_check_the_box_outside_label(page: Page) -> None:
    page.set_content(
        '<label for="checkbox">Text</label><div><input id="checkbox" type="checkbox"></input></div>'
    )
    page.check("label")
    assert page.evaluate("checkbox.checked")


def test_check_the_box_inside_label_without_id(page: Page) -> None:
    page.set_content(
        '<label>Text<span><input id="checkbox" type="checkbox"></input></span></label>'
    )
    page.check("label")
    assert page.evaluate("checkbox.checked")


def test_check_radio(page: Page) -> None:
    page.set_content(
        """
      <input type='radio'>one</input>
      <input id='two' type='radio'>two</input>
      <input type='radio'>three</input>"""
    )
    page.check("#two")
    assert page.evaluate("two.checked")


def test_check_the_box_by_aria_role(page: Page) -> None:
    page.set_content(
        """<div role='checkbox' id='checkbox'>CHECKBOX</div>
      <script>
        checkbox.addEventListener('click', () => checkbox.setAttribute('aria-checked', 'true'))
      </script>"""
    )
    page.check("div")
    assert page.evaluate("checkbox.getAttribute ('aria-checked')")
