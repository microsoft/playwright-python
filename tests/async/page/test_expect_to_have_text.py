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

"""Port of tests/page/expect-to-have-text.spec.ts."""

import asyncio
import re

import pytest

from playwright.async_api import Error, Page, expect


async def test_EX_274_to_have_text_with_regex_pass(page: Page) -> None:
    await page.set_content("<div id=node>Text   content</div>")
    locator = page.locator("#node")
    await expect(locator).to_have_text(re.compile(r"Text"))

    # Should not normalize whitespace.
    await expect(locator).to_have_text(re.compile(r"Text   content"))
    # Should respect ignoreCase.
    await expect(locator).to_have_text(re.compile(r"text   content"), ignore_case=True)
    # Should override regex flag with ignoreCase.
    await expect(locator).not_to_have_text(
        re.compile(r"text   content", re.IGNORECASE), ignore_case=False
    )


async def test_EX_275_to_have_text_with_regex_fail(page: Page) -> None:
    await page.set_content("<div id=node>Text content</div>")
    locator = page.locator("#node")
    with pytest.raises(AssertionError) as exc_info:
        await expect(locator).to_have_text(re.compile(r"Text 2"), timeout=1000)
    message = str(exc_info.value)
    assert (
        "Locator expected to have text 're.compile('Text 2')'\n"
        "Actual value: Text content \n"
        "Call log:\n" in message
    )
    assert '- Expect "to_have_text" locator("#node") with timeout 1000ms' in message


async def test_EX_276_to_contain_text_with_regex_pass(page: Page) -> None:
    await page.set_content("<div id=node>Text   content</div>")
    locator = page.locator("#node")
    await expect(locator).to_contain_text(re.compile(r"ex"))

    # Should not normalize whitespace.
    await expect(locator).to_contain_text(re.compile(r"ext   cont"))


async def test_EX_277_to_contain_text_with_regex_fail(page: Page) -> None:
    await page.set_content("<div id=node>Text content</div>")
    locator = page.locator("#node")
    with pytest.raises(AssertionError) as exc_info:
        await expect(locator).to_contain_text(re.compile(r"ex2"), timeout=1000)
    message = str(exc_info.value)
    assert "Locator expected to contain text 're.compile('ex2')'" in message
    assert "Actual value: Text content" in message


async def test_EX_278_to_contain_text_with_string_pass(page: Page) -> None:
    await page.set_content("<div id=node>Text   content</div>")
    locator = page.locator("#node")
    await expect(locator).to_contain_text("content")


async def test_EX_279_to_contain_text_with_string_fail(page: Page) -> None:
    await page.set_content("<div id=node>Text content</div>")
    locator = page.locator("#node")
    with pytest.raises(AssertionError) as exc_info:
        await expect(locator).to_contain_text("foo", timeout=1000)
    message = str(exc_info.value)
    assert (
        "Locator expected to contain text 'foo'\n"
        "Actual value: Text content \n"
        "Call log:\n" in message
    )
    assert '- Expect "to_contain_text" locator("#node") with timeout 1000ms' in message


async def test_EX_280_to_have_text_with_text_pass(page: Page) -> None:
    await page.set_content("<div id=node><span></span>Text \ncontent&nbsp;    </div>")
    locator = page.locator("#node")
    # Should normalize whitespace.
    await expect(locator).to_have_text("Text                        content")
    # Should normalize zero width whitespace.
    await expect(locator).to_have_text("T​e​x​t content")
    # Should support ignoreCase.
    await expect(locator).to_have_text("text CONTENT", ignore_case=True)
    # Should support falsy ignoreCase.
    await expect(locator).not_to_have_text("TEXT", ignore_case=False)
    # Should normalize soft hyphens.
    await expect(locator).to_have_text("T­e­xt content")


async def test_EX_281_to_have_text_with_text_pass_contain(page: Page) -> None:
    await page.set_content("<div id=node>Text content</div>")
    locator = page.locator("#node")
    await expect(locator).to_contain_text("Text")
    # Should normalize whitespace.
    await expect(locator).to_contain_text("   ext        cont\n  ")
    # Should support ignoreCase.
    await expect(locator).to_contain_text("EXT", ignore_case=True)
    # Should support falsy ignoreCase.
    await expect(locator).not_to_contain_text("TEXT", ignore_case=False)


async def test_EX_282_to_have_text_with_text_fail(page: Page) -> None:
    await page.set_content("<div id=node>Text content</div>")
    locator = page.locator("#node")
    with pytest.raises(AssertionError) as exc_info:
        await expect(locator).to_have_text("Text", timeout=1000)
    message = str(exc_info.value)
    assert "Locator expected to have text 'Text'" in message
    assert "Actual value: Text content" in message


async def test_EX_283_to_have_text_with_text_pass_eventually(page: Page) -> None:
    await page.set_content("<div id=node>Text content</div>")
    locator = page.locator("#node")

    async def change_text() -> None:
        await page.wait_for_timeout(1000)
        await locator.evaluate("element => element.textContent = 'Text 2 content'")

    async def check() -> None:
        await expect(locator).to_have_text(re.compile(r"Text 2"))

    await asyncio.gather(check(), change_text())


async def test_EX_284_to_have_text_with_text_with_user_inner_text(page: Page) -> None:
    await page.set_content(
        "<div id=node>Text <span hidden>garbage</span> content</div>"
    )
    locator = page.locator("#node")
    await expect(locator).to_have_text("Text content", use_inner_text=True)


async def test_EX_285_to_have_text_with_text_in_shadow_dom(page: Page) -> None:
    await page.set_content(
        """
      <div></div>
      <script>
        const div = document.querySelector('div');
        const span = document.createElement('span');
        span.textContent = 'some text';
        div.attachShadow({ mode: 'open' }).appendChild(span);
      </script>
    """
    )
    await expect(page.locator("span")).to_have_text("some text")
    await expect(page.locator("span")).to_contain_text("text")
    await expect(page.locator("div")).to_have_text("some text")
    await expect(page.locator("div")).to_contain_text("text")
    await expect(page.locator("span")).to_have_text("some text", use_inner_text=True)
    await expect(page.locator("span")).to_contain_text("text", use_inner_text=True)
    # Playwright intentionally does not perform innerText piercing on shadow dom.
    await expect(page.locator("div")).not_to_have_text("some text", use_inner_text=True)
    await expect(page.locator("div")).not_to_contain_text("text", use_inner_text=True)


async def test_EX_286_to_have_text_with_text_fail_with_impossible_timeout(
    page: Page,
) -> None:
    await page.set_content("<div id=node>Text content</div>")
    with pytest.raises(AssertionError) as exc_info:
        await expect(page.locator("#node")).to_have_text("Text", timeout=1)
    message = str(exc_info.value)
    assert "Locator expected to have text 'Text'" in message
    assert "Actual value: Text content" in message


async def test_EX_287_to_have_text_with_text_do_not_show_element_s_not_found_when_the_real_failure_is_a_string_mismatch(
    page: Page,
) -> None:
    await page.set_content(
        """
      <div>Initial</div>
      <script>
        const field = document.querySelector('div');
        setTimeout(() => {
          field.id = 'field';
          field.textContent = 'Final value';
        }, 1000);
      </script>
    """
    )

    cell = page.locator("#field")
    with pytest.raises(AssertionError) as exc_info:
        await expect(cell).to_have_text("Something", timeout=3000)
    message = str(exc_info.value)
    assert "Locator expected to have text 'Something'" in message
    assert "Actual value: Final value" in message


async def test_EX_288_not_to_have_text_pass(page: Page) -> None:
    await page.set_content("<div id=node>Text content</div>")
    locator = page.locator("#node")
    await expect(locator).not_to_have_text("Text2")
    # Should be case-sensitive by default.
    await expect(locator).not_to_have_text("TEXT")


async def test_EX_289_not_to_have_text_fail(page: Page) -> None:
    await page.set_content("<div id=node>Text content</div>")
    locator = page.locator("#node")
    with pytest.raises(AssertionError) as exc_info:
        await expect(locator).not_to_have_text("Text content", timeout=1000)
    message = str(exc_info.value)
    assert "Locator expected not to have text 'Text content'" in message
    assert "Actual value: Text content" in message


async def test_EX_290_not_to_have_text_should_work_when_selector_does_not_match(
    page: Page,
) -> None:
    await page.set_content("<div>hello</div>")
    with pytest.raises(AssertionError) as exc_info:
        await expect(page.locator("span")).not_to_have_text("hello", timeout=1000)
    message = str(exc_info.value)
    assert "Locator expected not to have text 'hello'" in message
    assert "Error: element(s) not found" in message
    assert 'waiting for locator("span")' in message


async def test_EX_291_to_have_text_with_array_pass(page: Page) -> None:
    await page.set_content("<div>Text    \n1</div><div>Text   2a</div>")
    locator = page.locator("div")
    # Should only normalize whitespace in the first item.
    await expect(locator).to_have_text(["Text  1", re.compile(r"Text   \d+a")])
    # Should support ignoreCase.
    await expect(locator).to_have_text(["tEXT 1", "TExt 2A"], ignore_case=True)


async def test_EX_292_to_have_text_with_array_pass_lazy(page: Page) -> None:
    await page.set_content("<div id=div></div>")
    locator = page.locator("p")

    async def add_paragraphs() -> None:
        await page.wait_for_timeout(500)
        try:
            await page.evaluate(
                "() => { document.querySelector('div').innerHTML = '<p>Text 1</p><p>Text 2</p>'; }"
            )
        except Error:
            pass

    async def check() -> None:
        await expect(locator).to_have_text(["Text 1", "Text 2"])

    await asyncio.gather(add_paragraphs(), check())


async def test_EX_293_to_have_text_with_array_pass_empty(page: Page) -> None:
    await page.set_content("<div></div>")
    locator = page.locator("p")
    await expect(locator).to_have_text([])


async def test_EX_294_to_have_text_with_array_pass_not_empty(page: Page) -> None:
    await page.set_content("<div><p>Test</p></div>")
    locator = page.locator("p")
    await expect(locator).not_to_have_text([])


async def test_EX_295_to_have_text_with_array_pass_on_empty(page: Page) -> None:
    await page.set_content("<div></div>")
    locator = page.locator("p")
    await expect(locator).not_to_have_text(["Test"])


async def test_EX_296_to_have_text_with_array_fail_on_not_empty(page: Page) -> None:
    await page.set_content("<div></div>")
    locator = page.locator("p")
    with pytest.raises(AssertionError) as exc_info:
        await expect(locator).not_to_have_text([], timeout=1000)
    message = str(exc_info.value)
    assert "Locator expected not to have text '[]'" in message
    assert '- Expect "not_to_have_text" locator("p") with timeout 1000ms' in message


async def test_EX_297_to_have_text_with_array_pass_eventually_empty(
    page: Page,
) -> None:
    await page.set_content("<div id=div><p>Text</p></div>")
    locator = page.locator("p")

    async def clear_later() -> None:
        await page.wait_for_timeout(500)
        try:
            await page.evaluate("() => document.querySelector('div').innerHTML = ''")
        except Error:
            pass

    async def check() -> None:
        await expect(locator).not_to_have_text([])

    await asyncio.gather(clear_later(), check())


async def test_EX_298_to_have_text_with_array_fail(page: Page) -> None:
    await page.set_content("<div>Text 1</div><div>Text 3</div>")
    locator = page.locator("div")
    with pytest.raises(AssertionError) as exc_info:
        await expect(locator).to_have_text(
            ["Text 1", re.compile(r"Text \d"), "Extra"], timeout=1000
        )
    message = str(exc_info.value)
    assert (
        r"Locator expected to have text '['Text 1', re.compile('Text \\d'), 'Extra']'"
        "\n"
        "Actual value: ['Text 1', 'Text 3'] \n"
        "Call log:\n"
        '  - Expect "to_have_text" locator("div") with timeout 1000ms\n'
        '  - waiting for locator("div")\n' in message
    )
    assert "locator resolved to 2 elements" in message


async def test_EX_299_to_have_text_with_array_fail_on_repeating_array_matchers(
    page: Page,
) -> None:
    await page.set_content("<div>KekFoo</div>")
    locator = page.locator("div")
    with pytest.raises(AssertionError) as exc_info:
        await expect(locator).to_contain_text(
            ["KekFoo", "KekFoo", "KekFoo"], timeout=1000
        )
    assert "locator resolved to 1 element" in str(exc_info.value)


async def test_EX_300_to_contain_text_with_array_pass(page: Page) -> None:
    await page.set_content("<div>Text \n1</div><div>Text2</div><div>Text3</div>")
    locator = page.locator("div")
    await expect(locator).to_contain_text(["ext     1", re.compile(r"ext3")])
    # Should support ignoreCase.
    await expect(locator).to_contain_text(["EXT 1", "eXt3"], ignore_case=True)


async def test_EX_301_to_contain_text_with_array_fail(page: Page) -> None:
    await page.set_content("<div>Text 1</div><div>Text 3</div>")
    locator = page.locator("div")
    with pytest.raises(AssertionError) as exc_info:
        await expect(locator).to_contain_text(["Text 2"], timeout=1000)
    message = str(exc_info.value)
    assert "Locator expected to contain text '['Text 2']'" in message
    assert "Actual value: ['Text 1', 'Text 3']" in message
