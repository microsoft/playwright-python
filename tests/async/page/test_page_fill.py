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

"""Port of tests/page/page-fill.spec.ts."""

import asyncio
from typing import Any, Optional, cast

import pytest

from playwright.async_api import Error, Page, TimeoutError, expect
from tests.server import Server

from ..utils import Utils


async def give_it_a_chance_to_fill(utils: Utils, page: Page) -> None:
    await utils.rafraf(page, 5)


async def test_FI_001_should_fill_textarea_smoke(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/textarea.html")
    await page.fill("textarea", "some value")
    assert await page.evaluate("() => window['result']") == "some value"


async def test_FI_002_should_fill_input(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/textarea.html")
    await page.fill("input", "some value")
    assert await page.evaluate("() => window['result']") == "some value"


async def test_FI_003_should_throw_on_unsupported_inputs(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/textarea.html")
    for type in ["button", "checkbox", "file", "image", "radio", "reset", "submit"]:
        await page.eval_on_selector(
            "input", "(input, type) => input.setAttribute('type', type)", type
        )
        with pytest.raises(Error) as exc_info:
            await page.fill("input", "")
        assert f'Input of type "{type}" cannot be filled' in exc_info.value.message


async def test_FI_004_should_fill_different_input_types(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/textarea.html")
    for type in ["password", "search", "tel", "text", "url", "invalid-type"]:
        await page.eval_on_selector(
            "input", "(input, type) => input.setAttribute('type', type)", type
        )
        await page.fill("input", "text " + type)
        assert await page.evaluate("() => window['result']") == "text " + type


async def test_FI_005_should_fill_range_input(page: Page) -> None:
    # https://github.com/microsoft/playwright/issues/43328
    await page.set_content("<input type=range min=0 max=100 value=50>")
    await page.fill("input", "42")
    assert await page.eval_on_selector("input", "input => input.value") == "42"
    # Valid numbers that the browser may serialize differently.
    for value, expected in [("42.0", 42), ("1e1", 10)]:
        await page.fill("input", value)
        assert (
            await page.eval_on_selector("input", "input => input.valueAsNumber")
            == expected
        )


async def test_FI_006_should_fill_color_input(page: Page) -> None:
    await page.set_content('<input type=color value="#e66465">')
    await page.fill("input", "#aaaaaa")
    assert await page.eval_on_selector("input", "input => input.value") == "#aaaaaa"


async def test_FI_007_should_fill_color_input_case_insensitive(
    page: Page, browser_name: str, is_win: bool, browser_channel: Optional[str]
) -> None:
    await page.set_content('<input type=color value="#e66465">')
    await page.fill("input", "#AbCd00")
    if browser_name == "webkit" and is_win and browser_channel != "webkit-wsl":
        assert await page.eval_on_selector("input", "input => input.value") == "#AbCd00"
    else:
        assert await page.eval_on_selector("input", "input => input.value") == "#abcd00"


async def test_FI_008_should_fill_date_input_after_clicking(
    page: Page, server: Server
) -> None:
    await page.set_content("<input type=date>")
    await page.click("input")
    await page.fill("input", "2020-03-02")
    assert await page.eval_on_selector("input", "input => input.value") == "2020-03-02"


@pytest.mark.parametrize(
    "type,value",
    [
        ("color", "#aaaaaa"),
        ("date", "2020-03-02"),
        ("time", "13:15"),
        ("datetime-local", "2020-03-02T13:15:30"),
        ("month", "2020-03"),
        ("range", "42"),
        ("week", "2020-W50"),
    ],
)
async def test_FI_009_input_event_composed_should_be_true_and_cross_shadow_dom_boundary(
    page: Page,
    server: Server,
    browser_name: str,
    is_win: bool,
    type: str,
    value: str,
) -> None:
    # https://github.com/microsoft/playwright/issues/28726
    if browser_name != "chromium" and type in ["month", "week"]:
        pytest.skip("Some browser/platforms do not implement certain input types")
    if (
        browser_name == "webkit"
        and is_win
        and type in ["color", "date", "time", "datetime-local"]
    ):
        pytest.skip("Some browser/platforms do not implement certain input types")
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        f"""<body><script>
    const div = document.createElement('div');
    const shadowRoot = div.attachShadow({{mode: 'open'}});
    shadowRoot.innerHTML = '<input type={type}></input>';
    document.body.appendChild(div);
  </script></body>"""
    )
    await page.locator("body").evaluate(
        """select => {
      window.firedBodyEvents = [];
      for (const event of ['input', 'change']) {
        select.addEventListener(event, e => {
          window.firedBodyEvents.push(e.type + ':' + e.composed);
        }, false);
      }
    }"""
    )

    await page.locator("input").evaluate(
        """select => {
      window.firedEvents = [];
      for (const event of ['input', 'change']) {
        select.addEventListener(event, e => {
          window.firedEvents.push(e.type + ':' + e.composed);
        }, false);
      }
    }"""
    )
    await page.locator("input").fill(value)

    assert await page.evaluate("() => window['firedEvents']") == [
        "input:true",
        "change:false",
    ]
    assert await page.evaluate("() => window['firedBodyEvents']") == ["input:true"]


async def test_FI_010_should_fill_time_input(page: Page) -> None:
    await page.set_content("<input type=time>")
    await page.fill("input", "13:15")
    assert await page.eval_on_selector("input", "input => input.value") == "13:15"


async def test_FI_011_should_fill_month_input(page: Page) -> None:
    await page.set_content("<input type=month>")
    await page.fill("input", "2020-07")
    assert await page.eval_on_selector("input", "input => input.value") == "2020-07"


async def test_FI_012_should_fill_week_input(page: Page) -> None:
    await page.set_content("<input type=week>")
    await page.fill("input", "2020-W50")
    assert await page.eval_on_selector("input", "input => input.value") == "2020-W50"


async def test_FI_013_should_fill_datetime_local_input(
    page: Page,
    server: Server,
    browser_name: str,
    is_win: bool,
    browser_channel: Optional[str],
) -> None:
    # https://github.com/microsoft/playwright/issues/43370
    await page.set_content("<input type=datetime-local>")
    await page.fill("input", "2020-03-02T05:15")
    assert (
        await page.eval_on_selector("input", "input => input.value")
        == "2020-03-02T05:15"
    )
    # The browser omits zero seconds. WebKit on Windows does not implement datetime-local inputs and keeps the value as is.
    await page.fill("input", "2020-03-02T06:20:00")
    if browser_name == "webkit" and is_win and browser_channel != "webkit-wsl":
        assert (
            await page.eval_on_selector("input", "input => input.value")
            == "2020-03-02T06:20:00"
        )
    else:
        assert (
            await page.eval_on_selector("input", "input => input.value")
            == "2020-03-02T06:20"
        )


async def test_FI_014_should_fill_contenteditable(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/textarea.html")
    await page.fill("div[contenteditable]", "some value")
    assert (
        await page.eval_on_selector("div[contenteditable]", "div => div.textContent")
        == "some value"
    )


async def test_FI_015_should_fill_contenteditable_with_new_lines(
    page: Page, server: Server, browser_name: str
) -> None:
    if browser_name == "firefox":
        pytest.skip("fixme: Firefox does not handle new lines in contenteditable")

    await page.goto(server.EMPTY_PAGE)
    await page.set_content('<div contenteditable="true"></div>')
    await page.locator("div[contenteditable]").fill("John\nDoe")
    assert await page.locator("div[contenteditable]").inner_text() == "John\nDoe"


async def test_FI_016_should_not_double_fill_in_contenteditable_with_beforeinput_handler_in_firefox(
    page: Page, browser_name: str
) -> None:
    # https://github.com/microsoft/playwright/issues/36715
    if browser_name == "firefox":
        pytest.skip("fixme: https://github.com/microsoft/playwright/issues/36715")

    await page.set_content(
        """
    <div id="editor" contenteditable="true"></div>
    <script>
      const editor = document.getElementById('editor');
      editor.addEventListener('beforeinput', (event) => {
        event.preventDefault();
        editor.textContent = event.data;
      });
    </script>
  """
    )

    locator = page.locator("#editor")
    test_value = "Playwright"
    await locator.fill(test_value)
    await expect(locator).to_have_text(test_value)


async def test_FI_017_should_fill_elements_with_existing_value_and_selection(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/textarea.html")

    await page.eval_on_selector("input", "input => input.value = 'value one'")
    await page.fill("input", "another value")
    assert await page.evaluate("() => window['result']") == "another value"

    await page.eval_on_selector(
        "input",
        """input => {
    input.selectionStart = 1;
    input.selectionEnd = 2;
  }""",
    )
    await page.fill("input", "maybe this one")
    assert await page.evaluate("() => window['result']") == "maybe this one"

    await page.eval_on_selector(
        "div[contenteditable]",
        """div => {
    div.innerHTML = 'some text <span>some more text<span> and even more text';
    const range = document.createRange();
    range.selectNodeContents(div.querySelector('span'));
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
  }""",
    )
    await page.fill("div[contenteditable]", "replace with this")
    assert (
        await page.eval_on_selector("div[contenteditable]", "div => div.textContent")
        == "replace with this"
    )


async def test_FI_018_should_throw_nice_error_without_injected_script_stack_when_element_is_not_an_input(
    page: Page, server: Server
) -> None:
    await page.set_content("<select><option>value1</option></select>")
    with pytest.raises(Error) as exc_info:
        await page.fill("select", "")
    assert (
        "Page.fill: Error: Element is not an <input>, <textarea> or [contenteditable] element\nCall log:"
        in exc_info.value.message
    )


async def test_FI_019_should_throw_if_passed_a_non_string_value(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/textarea.html")
    with pytest.raises(Error) as exc_info:
        await page.fill("textarea", cast(Any, 123))
    assert "value: expected string, got number" in exc_info.value.message


async def test_FI_020_should_retry_on_disabled_element(
    page: Page, server: Server, utils: Utils
) -> None:
    await page.goto(server.PREFIX + "/input/textarea.html")
    await page.eval_on_selector("input", "i => i.disabled = true")
    done = False

    async def fill() -> None:
        nonlocal done
        await page.fill("input", "some value")
        done = True

    promise = asyncio.create_task(fill())
    await give_it_a_chance_to_fill(utils, page)
    assert done is False
    assert await page.evaluate("() => window['result']") == ""

    await page.eval_on_selector("input", "i => i.disabled = false")
    await promise
    assert await page.evaluate("() => window['result']") == "some value"


async def test_FI_021_should_retry_on_readonly_element(
    page: Page, server: Server, utils: Utils
) -> None:
    await page.goto(server.PREFIX + "/input/textarea.html")
    await page.eval_on_selector("textarea", "i => i.readOnly = true")
    done = False

    async def fill() -> None:
        nonlocal done
        await page.fill("textarea", "some value")
        done = True

    promise = asyncio.create_task(fill())
    await give_it_a_chance_to_fill(utils, page)
    assert done is False
    assert await page.evaluate("() => window['result']") == ""

    await page.eval_on_selector("textarea", "i => i.readOnly = false")
    await promise
    assert await page.evaluate("() => window['result']") == "some value"


async def test_FI_022_should_retry_on_invisible_element(
    page: Page, server: Server, utils: Utils
) -> None:
    await page.goto(server.PREFIX + "/input/textarea.html")
    await page.eval_on_selector("input", "i => i.style.display = 'none'")
    done = False

    async def fill() -> None:
        nonlocal done
        await page.fill("input", "some value")
        done = True

    promise = asyncio.create_task(fill())
    await give_it_a_chance_to_fill(utils, page)
    assert done is False
    assert await page.evaluate("() => window['result']") == ""

    await page.eval_on_selector("input", "i => i.style.display = 'inline'")
    await promise
    assert await page.evaluate("() => window['result']") == "some value"


async def test_FI_023_should_be_able_to_fill_the_body(page: Page) -> None:
    await page.set_content('<body contentEditable="true"></body>')
    await page.fill("body", "some value")
    assert await page.evaluate("() => document.body.textContent") == "some value"


async def test_FI_024_should_fill_fixed_position_input(page: Page) -> None:
    await page.set_content("<input style='position: fixed;' />")
    await page.fill("input", "some value")
    assert (
        await page.evaluate("() => document.querySelector('input').value")
        == "some value"
    )


async def test_FI_025_should_be_able_to_fill_when_focus_is_in_the_wrong_frame(
    page: Page,
) -> None:
    await page.set_content(
        """
    <div contentEditable="true"></div>
    <iframe></iframe>
  """
    )
    await page.focus("iframe")
    await page.fill("div", "some value")
    assert await page.eval_on_selector("div", "d => d.textContent") == "some value"


async def test_FI_026_should_be_able_to_fill_the_input_type_number(
    page: Page,
) -> None:
    await page.set_content('<input id="input" type="number"></input>')
    await page.fill("input", "42")
    assert await page.evaluate("() => window['input'].value") == "42"


async def test_FI_027_should_be_able_to_fill_exponent_into_the_input_type_number(
    page: Page,
) -> None:
    await page.set_content('<input id="input" type="number"></input>')
    await page.fill("input", "-10e5")
    assert await page.evaluate("() => window['input'].value") == "-10e5"


async def test_FI_028_should_be_able_to_fill_input_type_number_with_empty_string(
    page: Page,
) -> None:
    await page.set_content('<input id="input" type="number" value="123"></input>')
    await page.fill("input", "")
    assert await page.evaluate("() => window['input'].value") == ""


async def test_FI_029_should_not_be_able_to_fill_text_into_the_input_type_number(
    page: Page,
) -> None:
    await page.set_content('<input id="input" type="number"></input>')
    with pytest.raises(Error) as exc_info:
        await page.fill("input", "abc")
    assert "Cannot type text into input[type=number]" in exc_info.value.message


async def test_FI_030_should_be_able_to_clear_using_fill(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/textarea.html")
    await page.fill("input", "some value")
    assert await page.evaluate("() => window['result']") == "some value"
    await page.fill("input", "")
    assert await page.evaluate("() => window['result']") == ""


async def test_FI_031_should_not_throw_when_fill_causes_navigation(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/textarea.html")
    await page.set_content("<input type=date>")
    await page.eval_on_selector(
        "input",
        "select => select.addEventListener('input', () => window.location.href = '/empty.html')",
    )
    async with page.expect_navigation():
        await page.fill("input", "2020-03-02")
    assert "empty.html" in page.url


async def test_FI_032_fill_back_to_back(page: Page) -> None:
    # https://github.com/microsoft/playwright/issues/15925
    await page.set_content('<input id="one"></input><input id="two"></input>')
    await page.fill("id=one", "first value")
    await page.fill("id=two", "second value")
    await expect(page.locator("id=one")).to_have_value("first value")
    await expect(page.locator("id=two")).to_have_value("second value")


async def test_FI_033_should_fill_contenteditable_with_focus_handler_that_collapses_selection(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/39492
    await page.set_content(
        """
    <div contenteditable="true">initial text</div>
    <script>
      const editor = document.querySelector('[contenteditable]');
      editor.addEventListener('focus', () => {
        const selection = window.getSelection();
        if (selection.rangeCount > 0)
          selection.collapseToEnd();
      });
    </script>
  """
    )

    await page.fill("div[contenteditable]", "some value")
    assert await page.locator("div[contenteditable]").text_content() == "some value"


async def test_FI_034_should_retry_on_inert_element(page: Page, utils: Utils) -> None:
    # https://github.com/microsoft/playwright/issues/42967
    await page.set_content(
        """
    <div inert id=container>
      <input id=target>
    </div>
    <input id=outside>
  """
    )
    await page.focus("#outside")
    done = False

    async def fill() -> None:
        nonlocal done
        await page.fill("#target", "some value")
        done = True

    promise = asyncio.create_task(fill())
    await give_it_a_chance_to_fill(utils, page)
    assert done is False
    assert await page.eval_on_selector("#target", "i => i.value") == ""
    assert await page.eval_on_selector("#outside", "i => i.value") == ""

    await page.eval_on_selector("#container", "e => e.removeAttribute('inert')")
    await promise
    assert await page.eval_on_selector("#target", "i => i.value") == "some value"
    assert await page.eval_on_selector("#outside", "i => i.value") == ""


async def test_FI_035_should_retry_on_element_outside_of_a_modal_dialog(
    page: Page, utils: Utils
) -> None:
    # https://github.com/microsoft/playwright/issues/42967
    await page.set_content(
        """
    <input id=target>
    <dialog id=dialog><input id=inside></dialog>
    <script>
      document.getElementById('dialog').showModal();
    </script>
  """
    )
    done = False

    await page.fill("#inside", "inside value")
    assert await page.eval_on_selector("#inside", "i => i.value") == "inside value"

    async def fill() -> None:
        nonlocal done
        await page.fill("#target", "some value")
        done = True

    promise = asyncio.create_task(fill())
    await give_it_a_chance_to_fill(utils, page)
    assert done is False
    assert await page.eval_on_selector("#target", "i => i.value") == ""

    await page.eval_on_selector("#dialog", "e => e.close()")
    await promise
    assert await page.eval_on_selector("#target", "i => i.value") == "some value"


async def test_FI_036_should_fail_with_a_nice_error_on_inert_element(
    page: Page,
) -> None:
    await page.set_content("<div inert><input></div>")
    with pytest.raises(TimeoutError) as exc_info:
        await page.fill("input", "some value", timeout=1000)
    assert "Timeout 1000ms exceeded" in exc_info.value.message
    assert "element is inert" in exc_info.value.message
