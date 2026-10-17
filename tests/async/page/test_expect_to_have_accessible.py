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

"""Port of tests/page/expect-to-have-accessible.spec.ts."""

import re
from typing import Optional

import pytest

from playwright.async_api import Error, Locator, Page, expect

ERROR_MESSAGE_TEXT = "Error message"


async def test_EX_259_to_have_accessible_name(page: Page) -> None:
    await page.set_content(
        """
    <div role="button" aria-label="Hello"></div>
  """
    )
    await expect(page.locator("div")).to_have_accessible_name("Hello")
    await expect(page.locator("div")).not_to_have_accessible_name("hello")
    await expect(page.locator("div")).to_have_accessible_name("hello", ignore_case=True)
    await expect(page.locator("div")).to_have_accessible_name(re.compile(r"ell\w"))
    await expect(page.locator("div")).not_to_have_accessible_name(re.compile(r"hello"))
    await expect(page.locator("div")).to_have_accessible_name(
        re.compile(r"hello"), ignore_case=True
    )

    await page.set_content("<button>foo&nbsp;bar\nbaz</button>")
    await expect(page.locator("button")).to_have_accessible_name("foo bar baz")

    await page.set_content(
        """
    <select>
      <option>&nbsp;HTML</option>
    </select>
  """
    )
    await expect(page.locator("option")).to_have_accessible_name("HTML")


async def test_EX_260_to_have_accessible_description(page: Page) -> None:
    await page.set_content(
        """
    <div role="button" aria-description="Hello"></div>
  """
    )
    await expect(page.locator("div")).to_have_accessible_description("Hello")
    await expect(page.locator("div")).not_to_have_accessible_description("hello")
    await expect(page.locator("div")).to_have_accessible_description(
        "hello", ignore_case=True
    )
    await expect(page.locator("div")).to_have_accessible_description(
        re.compile(r"ell\w")
    )
    await expect(page.locator("div")).not_to_have_accessible_description(
        re.compile(r"hello")
    )
    await expect(page.locator("div")).to_have_accessible_description(
        re.compile(r"hello"), ignore_case=True
    )

    await page.set_content(
        """
    <div role="button" aria-describedby="desc"></div>
    <span id="desc">foo&nbsp;bar\nbaz</span>
  """
    )
    await expect(page.locator("div")).to_have_accessible_description("foo bar baz")


async def test_EX_261_to_have_accessible_error_message(page: Page) -> None:
    await page.set_content(
        """
    <form>
      <input role="textbox" aria-invalid="true" aria-errormessage="error-message" />
      <div id="error-message">Hello</div>
      <div id="irrelevant-error">This should not be considered.</div>
    </form>
  """
    )

    locator = page.locator('input[role="textbox"]')
    await expect(locator).to_have_accessible_error_message("Hello")
    await expect(locator).not_to_have_accessible_error_message("hello")
    await expect(locator).to_have_accessible_error_message("hello", ignore_case=True)
    await expect(locator).to_have_accessible_error_message(re.compile(r"ell\w"))
    await expect(locator).not_to_have_accessible_error_message(re.compile(r"hello"))
    await expect(locator).to_have_accessible_error_message(
        re.compile(r"hello"), ignore_case=True
    )
    await expect(locator).not_to_have_accessible_error_message(
        "This should not be considered."
    )


async def test_EX_262_to_have_accessible_error_message_should_handle_multiple_aria_errormessage_references(
    page: Page,
) -> None:
    await page.set_content(
        """
    <form>
      <input role="textbox" aria-invalid="true" aria-errormessage="error1 error2" />
      <div id="error1">First error message.</div>
      <div id="error2">Second error message.</div>
      <div id="irrelevant-error">This should not be considered.</div>
    </form>
  """
    )

    locator = page.locator('input[role="textbox"]')

    await expect(locator).to_have_accessible_error_message(
        "First error message. Second error message."
    )
    await expect(locator).to_have_accessible_error_message(
        re.compile(r"first error message.", re.IGNORECASE)
    )
    await expect(locator).to_have_accessible_error_message(
        re.compile(r"second error message.", re.IGNORECASE)
    )
    await expect(locator).not_to_have_accessible_error_message(
        re.compile(r"This should not be considered.", re.IGNORECASE)
    )


async def setup_page(page: Page, aria_invalid_value: Optional[str]) -> Locator:
    aria_invalid_attr = (
        "" if aria_invalid_value is None else f'aria-invalid="{aria_invalid_value}"'
    )
    await page.set_content(
        f"""
        <form>
          <input id="node" role="textbox" {aria_invalid_attr} aria-errormessage="error-msg" />
          <div id="error-msg">{ERROR_MESSAGE_TEXT}</div>
        </form>
      """
    )
    return page.locator("#node")


async def test_EX_263_to_have_accessible_error_message_should_handle_aria_invalid_attribute_evaluated_in_false_no_aria_invalid_attribute(
    page: Page,
) -> None:
    locator = await setup_page(page, None)
    await expect(locator).not_to_have_accessible_error_message(ERROR_MESSAGE_TEXT)


async def test_EX_264_to_have_accessible_error_message_should_handle_aria_invalid_attribute_evaluated_in_false_aria_invalid_false(
    page: Page,
) -> None:
    locator = await setup_page(page, "false")
    await expect(locator).not_to_have_accessible_error_message(ERROR_MESSAGE_TEXT)


async def test_EX_265_to_have_accessible_error_message_should_handle_aria_invalid_attribute_evaluated_in_false_aria_invalid_empty_string(
    page: Page,
) -> None:
    locator = await setup_page(page, "")
    await expect(locator).not_to_have_accessible_error_message(ERROR_MESSAGE_TEXT)


async def test_EX_266_to_have_accessible_error_message_should_handle_aria_invalid_attribute_evaluated_in_true_aria_invalid_true(
    page: Page,
) -> None:
    locator = await setup_page(page, "true")
    await expect(locator).to_have_accessible_error_message(ERROR_MESSAGE_TEXT)


async def test_EX_267_to_have_accessible_error_message_should_handle_aria_invalid_attribute_evaluated_in_true_aria_invalid_foo_unrecognized_value(
    page: Page,
) -> None:
    locator = await setup_page(page, "foo")
    await expect(locator).to_have_accessible_error_message(ERROR_MESSAGE_TEXT)


async def test_EX_268_should_show_error_message_when_validity_is_false_and_aria_invalid_is_true(
    page: Page,
) -> None:
    await page.set_content(
        f"""
    <form>
      <input id="node" role="textbox" type="number" min="1" max="100" aria-invalid="true" aria-errormessage="error-msg" />
      <div id="error-msg">{ERROR_MESSAGE_TEXT}</div>
    </form>
  """
    )
    locator = page.locator("#node")
    await locator.fill("101")
    await expect(locator).to_have_accessible_error_message(ERROR_MESSAGE_TEXT)


async def test_EX_269_should_show_error_message_when_validity_is_true_and_aria_invalid_is_true(
    page: Page,
) -> None:
    await page.set_content(
        f"""
    <form>
      <input id="node" role="textbox" type="number" min="1" max="100" aria-invalid="true" aria-errormessage="error-msg" />
      <div id="error-msg">{ERROR_MESSAGE_TEXT}</div>
    </form>
  """
    )
    locator = page.locator("#node")
    await locator.fill("99")
    await expect(locator).to_have_accessible_error_message(ERROR_MESSAGE_TEXT)


async def test_EX_270_should_show_error_message_when_validity_is_false_and_aria_invalid_is_false(
    page: Page,
) -> None:
    await page.set_content(
        f"""
    <form>
      <input id="node" role="textbox" type="number" min="1" max="100" aria-invalid="false" aria-errormessage="error-msg" />
      <div id="error-msg">{ERROR_MESSAGE_TEXT}</div>
    </form>
  """
    )
    locator = page.locator("#node")
    await locator.fill("101")
    await expect(locator).to_have_accessible_error_message(ERROR_MESSAGE_TEXT)


async def test_EX_271_should_not_show_error_message_when_validity_is_true_and_aria_invalid_is_false(
    page: Page,
) -> None:
    await page.set_content(
        f"""
    <form>
      <input id="node" role="textbox" type="number" min="1" max="100" aria-invalid="false" aria-errormessage="error-msg" />
      <div id="error-msg">{ERROR_MESSAGE_TEXT}</div>
    </form>
  """
    )
    locator = page.locator("#node")
    await locator.fill("99")
    await expect(locator).not_to_have_accessible_error_message(ERROR_MESSAGE_TEXT)


async def test_EX_272_should_show_error_message_for_all_roles(page: Page) -> None:
    await page.set_content(
        """
    <label for="file">File input</label>
    <input id="file" aria-invalid="true" aria-errormessage="file-error-id" type="file" />
    <p id="file-error-id" role="alert">File is incorrect</p>
  """
    )
    locator = page.get_by_label("File input")
    await expect(locator).to_have_accessible_error_message("File is incorrect")


async def test_EX_273_to_have_role(page: Page) -> None:
    await page.set_content('<div role="button">Button!</div>')
    await expect(page.locator("div")).to_have_role("button")
    await expect(page.locator("div")).not_to_have_role("checkbox")
    with pytest.raises(Error) as exc_info:
        await expect(page.locator("div")).to_have_role(
            re.compile(r"button|checkbox")  # type: ignore[arg-type]
        )
    assert exc_info.value.message == '"role" argument in to_have_role must be a string'
