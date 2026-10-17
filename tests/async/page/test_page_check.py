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

from playwright.async_api import Error, Page
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


async def test_CH_001_should_check_the_box_smoke(page: Page) -> None:
    await page.set_content("<input id='checkbox' type='checkbox'></input>")
    await page.check("input")
    assert await page.evaluate("() => window['checkbox'].checked") is True


async def test_CH_002_should_not_check_the_checked_box(page: Page) -> None:
    await page.set_content("<input id='checkbox' type='checkbox' checked></input>")
    await page.check("input")
    assert await page.evaluate("() => window['checkbox'].checked") is True


async def test_CH_003_should_uncheck_the_box(page: Page) -> None:
    await page.set_content("<input id='checkbox' type='checkbox' checked></input>")
    await page.uncheck("input")
    assert await page.evaluate("() => window['checkbox'].checked") is False


async def test_CH_004_should_not_uncheck_the_unchecked_box(page: Page) -> None:
    await page.set_content("<input id='checkbox' type='checkbox'></input>")
    await page.uncheck("input")
    assert await page.evaluate("() => window['checkbox'].checked") is False


async def test_CH_005_should_check_radio(page: Page) -> None:
    await page.set_content(
        """
    <input type='radio'>one</input>
    <input id='two' type='radio'>two</input>
    <input type='radio'>three</input>"""
    )
    await page.check("#two")
    assert await page.evaluate("() => window['two'].checked") is True


async def test_CH_006_should_check_radio_by_aria_role(page: Page) -> None:
    await page.set_content(
        """<div role='radio' id='checkbox'>CHECKBOX</div>
    <script>
      checkbox.addEventListener('click', () => checkbox.setAttribute('aria-checked', 'true'));
    </script>"""
    )
    await page.check("div")
    assert (
        await page.evaluate("() => window['checkbox'].getAttribute('aria-checked')")
        == "true"
    )


async def test_CH_007_should_uncheck_radio_by_aria_role(page: Page) -> None:
    await page.set_content(
        """<div role='radio' id='checkbox' aria-checked="true">CHECKBOX</div>
    <script>
      checkbox.addEventListener('click', () => checkbox.setAttribute('aria-checked', 'false'));
    </script>"""
    )
    await page.uncheck("div")
    assert (
        await page.evaluate("() => window['checkbox'].getAttribute('aria-checked')")
        == "false"
    )


async def test_CH_008_should_check_the_box_by_aria_role(page: Page) -> None:
    for role in ROLES:
        await page.set_content(
            f"""<div role='{role}' id='checkbox'>CHECKBOX</div>
        <script>
          checkbox.addEventListener('click', () => checkbox.setAttribute('aria-checked', 'true'));
        </script>"""
        )
        await page.check("div")
        assert (
            await page.evaluate("() => window['checkbox'].getAttribute('aria-checked')")
            == "true"
        ), f"role={role}"


async def test_CH_009_should_uncheck_the_box_by_aria_role(page: Page) -> None:
    for role in ROLES:
        await page.set_content(
            f"""<div role='{role}' id='checkbox' aria-checked="true">CHECKBOX</div>
        <script>
          checkbox.addEventListener('click', () => checkbox.setAttribute('aria-checked', 'false'));
        </script>"""
        )
        await page.uncheck("div")
        assert (
            await page.evaluate("() => window['checkbox'].getAttribute('aria-checked')")
            == "false"
        ), f"role={role}"


async def test_CH_010_should_throw_when_not_a_checkbox(page: Page) -> None:
    await page.set_content("<div>Check me</div>")
    with pytest.raises(Error) as exc_info:
        await page.check("div")
    assert "Not a checkbox or radio button" in exc_info.value.message


async def test_CH_011_should_throw_when_not_a_checkbox_2(page: Page) -> None:
    await page.set_content("<div role=button>Check me</div>")
    with pytest.raises(Error) as exc_info:
        await page.check("div")
    assert "Not a checkbox or radio button" in exc_info.value.message


async def test_CH_012_should_check_the_box_inside_a_button(page: Page) -> None:
    await page.set_content("<div role='button'><input type='checkbox'></div>")
    await page.check("input")
    assert await page.eval_on_selector("input", "input => input.checked") is True
    assert await page.is_checked("input") is True
    handle = await page.query_selector("input")
    assert handle
    assert await handle.is_checked() is True


async def test_CH_013_should_check_the_label_with_position(
    page: Page, server: Server
) -> None:
    await page.set_content(
        f"""
    <input id='checkbox' type='checkbox' style='width: 5px; height: 5px;'>
    <label for='checkbox'>
      <a href={json.dumps(server.EMPTY_PAGE)}>I am a long link that goes away so that nothing good will happen if you click on me</a>
      Click me
    </label>"""
    )
    handle = await page.query_selector("text=Click me")
    assert handle
    box = await handle.bounding_box()
    assert box
    await page.check("text=Click me", position={"x": box["width"] - 10, "y": 2})
    assert await page.eval_on_selector("input", "input => input.checked") is True


async def test_CH_014_trial_run_should_not_check(page: Page) -> None:
    await page.set_content("<input id='checkbox' type='checkbox'></input>")
    await page.check("input", trial=True)
    assert await page.evaluate("() => window['checkbox'].checked") is False


async def test_CH_015_trial_run_should_not_uncheck(page: Page) -> None:
    await page.set_content("<input id='checkbox' type='checkbox' checked></input>")
    await page.uncheck("input", trial=True)
    assert await page.evaluate("() => window['checkbox'].checked") is True


async def test_CH_016_should_check_the_box_using_set_checked(page: Page) -> None:
    await page.set_content("<input id='checkbox' type='checkbox'></input>")
    await page.set_checked("input", True)
    assert await page.evaluate("() => window['checkbox'].checked") is True
    await page.set_checked("input", False)
    assert await page.evaluate("() => window['checkbox'].checked") is False


async def test_CH_017_should_throw_when_trying_to_uncheck_radio_button(
    page: Page,
) -> None:
    await page.set_content("<input type='radio' name='test' checked id='radio'>")
    with pytest.raises(Error) as exc_info:
        await page.uncheck("#radio")
    assert "Cannot uncheck radio button" in exc_info.value.message
