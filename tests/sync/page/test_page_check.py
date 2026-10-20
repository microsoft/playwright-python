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

"""Port of tests/page/page-check.spec.ts."""

import json

import pytest

from playwright.sync_api import Error, Page
from tests.server import Server

ROLES = [
    "checkbox",
    "menuitemcheckbox",
    "option",
    "radio",
    "switch",
    "menuitemradio",
    "treeitem",
]


def test_CH_001_should_check_the_box_smoke(page: Page) -> None:
    page.set_content("<input id='checkbox' type='checkbox'></input>")
    page.check("input")
    assert page.evaluate("() => window['checkbox'].checked") is True


def test_CH_002_should_not_check_the_checked_box(page: Page) -> None:
    page.set_content("<input id='checkbox' type='checkbox' checked></input>")
    page.check("input")
    assert page.evaluate("() => window['checkbox'].checked") is True


def test_CH_003_should_uncheck_the_box(page: Page) -> None:
    page.set_content("<input id='checkbox' type='checkbox' checked></input>")
    page.uncheck("input")
    assert page.evaluate("() => window['checkbox'].checked") is False


def test_CH_004_should_not_uncheck_the_unchecked_box(page: Page) -> None:
    page.set_content("<input id='checkbox' type='checkbox'></input>")
    page.uncheck("input")
    assert page.evaluate("() => window['checkbox'].checked") is False


def test_CH_005_should_check_radio(page: Page) -> None:
    page.set_content(
        """
    <input type='radio'>one</input>
    <input id='two' type='radio'>two</input>
    <input type='radio'>three</input>"""
    )
    page.check("#two")
    assert page.evaluate("() => window['two'].checked") is True


def test_CH_006_should_check_radio_by_aria_role(page: Page) -> None:
    page.set_content(
        """<div role='radio' id='checkbox'>CHECKBOX</div>
    <script>
      checkbox.addEventListener('click', () => checkbox.setAttribute('aria-checked', 'true'));
    </script>"""
    )
    page.check("div")
    assert (
        page.evaluate("() => window['checkbox'].getAttribute('aria-checked')") == "true"
    )


def test_CH_007_should_uncheck_radio_by_aria_role(page: Page) -> None:
    page.set_content(
        """<div role='radio' id='checkbox' aria-checked="true">CHECKBOX</div>
    <script>
      checkbox.addEventListener('click', () => checkbox.setAttribute('aria-checked', 'false'));
    </script>"""
    )
    page.uncheck("div")
    assert (
        page.evaluate("() => window['checkbox'].getAttribute('aria-checked')")
        == "false"
    )


def test_CH_008_should_check_the_box_by_aria_role(page: Page) -> None:
    for role in ROLES:
        page.set_content(
            f"""<div role='{role}' id='checkbox'>CHECKBOX</div>
        <script>
          checkbox.addEventListener('click', () => checkbox.setAttribute('aria-checked', 'true'));
        </script>"""
        )
        page.check("div")
        assert (
            page.evaluate("() => window['checkbox'].getAttribute('aria-checked')")
            == "true"
        ), f"role={role}"


def test_CH_009_should_uncheck_the_box_by_aria_role(page: Page) -> None:
    for role in ROLES:
        page.set_content(
            f"""<div role='{role}' id='checkbox' aria-checked="true">CHECKBOX</div>
        <script>
          checkbox.addEventListener('click', () => checkbox.setAttribute('aria-checked', 'false'));
        </script>"""
        )
        page.uncheck("div")
        assert (
            page.evaluate("() => window['checkbox'].getAttribute('aria-checked')")
            == "false"
        ), f"role={role}"


def test_CH_010_should_throw_when_not_a_checkbox(page: Page) -> None:
    page.set_content("<div>Check me</div>")
    with pytest.raises(Error) as exc_info:
        page.check("div")
    assert "Not a checkbox or radio button" in exc_info.value.message


def test_CH_011_should_throw_when_not_a_checkbox_2(page: Page) -> None:
    page.set_content("<div role=button>Check me</div>")
    with pytest.raises(Error) as exc_info:
        page.check("div")
    assert "Not a checkbox or radio button" in exc_info.value.message


def test_CH_012_should_check_the_box_inside_a_button(page: Page) -> None:
    page.set_content("<div role='button'><input type='checkbox'></div>")
    page.check("input")
    assert page.eval_on_selector("input", "input => input.checked") is True
    assert page.is_checked("input") is True
    handle = page.query_selector("input")
    assert handle
    assert handle.is_checked() is True


def test_CH_013_should_check_the_label_with_position(
    page: Page, server: Server
) -> None:
    page.set_content(
        f"""
    <input id='checkbox' type='checkbox' style='width: 5px; height: 5px;'>
    <label for='checkbox'>
      <a href={json.dumps(server.EMPTY_PAGE)}>I am a long link that goes away so that nothing good will happen if you click on me</a>
      Click me
    </label>"""
    )
    handle = page.query_selector("text=Click me")
    assert handle
    box = handle.bounding_box()
    assert box
    page.check("text=Click me", position={"x": box["width"] - 10, "y": 2})
    assert page.eval_on_selector("input", "input => input.checked") is True


def test_CH_014_trial_run_should_not_check(page: Page) -> None:
    page.set_content("<input id='checkbox' type='checkbox'></input>")
    page.check("input", trial=True)
    assert page.evaluate("() => window['checkbox'].checked") is False


def test_CH_015_trial_run_should_not_uncheck(page: Page) -> None:
    page.set_content("<input id='checkbox' type='checkbox' checked></input>")
    page.uncheck("input", trial=True)
    assert page.evaluate("() => window['checkbox'].checked") is True


def test_CH_016_should_check_the_box_using_set_checked(page: Page) -> None:
    page.set_content("<input id='checkbox' type='checkbox'></input>")
    page.set_checked("input", True)
    assert page.evaluate("() => window['checkbox'].checked") is True
    page.set_checked("input", False)
    assert page.evaluate("() => window['checkbox'].checked") is False


def test_CH_017_should_throw_when_trying_to_uncheck_radio_button(
    page: Page,
) -> None:
    page.set_content("<input type='radio' name='test' checked id='radio'>")
    with pytest.raises(Error) as exc_info:
        page.uncheck("#radio")
    assert "Cannot uncheck radio button" in exc_info.value.message
