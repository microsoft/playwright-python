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

from playwright.sync_api import Error, Locator, Page, expect

ERROR_MESSAGE_TEXT = "Error message"


def test_EX_259_to_have_accessible_name(page: Page) -> None:
    page.set_content(
        """
    <div role="button" aria-label="Hello"></div>
  """
    )
    expect(page.locator("div")).to_have_accessible_name("Hello")
    expect(page.locator("div")).not_to_have_accessible_name("hello")
    expect(page.locator("div")).to_have_accessible_name("hello", ignore_case=True)
    expect(page.locator("div")).to_have_accessible_name(re.compile(r"ell\w"))
    expect(page.locator("div")).not_to_have_accessible_name(re.compile(r"hello"))
    expect(page.locator("div")).to_have_accessible_name(
        re.compile(r"hello"), ignore_case=True
    )

    page.set_content("<button>foo&nbsp;bar\nbaz</button>")
    expect(page.locator("button")).to_have_accessible_name("foo bar baz")

    page.set_content(
        """
    <select>
      <option>&nbsp;HTML</option>
    </select>
  """
    )
    expect(page.locator("option")).to_have_accessible_name("HTML")


def test_EX_260_to_have_accessible_description(page: Page) -> None:
    page.set_content(
        """
    <div role="button" aria-description="Hello"></div>
  """
    )
    expect(page.locator("div")).to_have_accessible_description("Hello")
    expect(page.locator("div")).not_to_have_accessible_description("hello")
    expect(page.locator("div")).to_have_accessible_description(
        "hello", ignore_case=True
    )
    expect(page.locator("div")).to_have_accessible_description(re.compile(r"ell\w"))
    expect(page.locator("div")).not_to_have_accessible_description(re.compile(r"hello"))
    expect(page.locator("div")).to_have_accessible_description(
        re.compile(r"hello"), ignore_case=True
    )

    page.set_content(
        """
    <div role="button" aria-describedby="desc"></div>
    <span id="desc">foo&nbsp;bar\nbaz</span>
  """
    )
    expect(page.locator("div")).to_have_accessible_description("foo bar baz")


def test_EX_261_to_have_accessible_error_message(page: Page) -> None:
    page.set_content(
        """
    <form>
      <input role="textbox" aria-invalid="true" aria-errormessage="error-message" />
      <div id="error-message">Hello</div>
      <div id="irrelevant-error">This should not be considered.</div>
    </form>
  """
    )

    locator = page.locator('input[role="textbox"]')
    expect(locator).to_have_accessible_error_message("Hello")
    expect(locator).not_to_have_accessible_error_message("hello")
    expect(locator).to_have_accessible_error_message("hello", ignore_case=True)
    expect(locator).to_have_accessible_error_message(re.compile(r"ell\w"))
    expect(locator).not_to_have_accessible_error_message(re.compile(r"hello"))
    expect(locator).to_have_accessible_error_message(
        re.compile(r"hello"), ignore_case=True
    )
    expect(locator).not_to_have_accessible_error_message(
        "This should not be considered."
    )


def test_EX_262_to_have_accessible_error_message_should_handle_multiple_aria_errormessage_references(
    page: Page,
) -> None:
    page.set_content(
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

    expect(locator).to_have_accessible_error_message(
        "First error message. Second error message."
    )
    expect(locator).to_have_accessible_error_message(
        re.compile(r"first error message.", re.IGNORECASE)
    )
    expect(locator).to_have_accessible_error_message(
        re.compile(r"second error message.", re.IGNORECASE)
    )
    expect(locator).not_to_have_accessible_error_message(
        re.compile(r"This should not be considered.", re.IGNORECASE)
    )


def setup_page(page: Page, aria_invalid_value: Optional[str]) -> Locator:
    aria_invalid_attr = (
        "" if aria_invalid_value is None else f'aria-invalid="{aria_invalid_value}"'
    )
    page.set_content(
        f"""
        <form>
          <input id="node" role="textbox" {aria_invalid_attr} aria-errormessage="error-msg" />
          <div id="error-msg">{ERROR_MESSAGE_TEXT}</div>
        </form>
      """
    )
    return page.locator("#node")


def test_EX_263_to_have_accessible_error_message_should_handle_aria_invalid_attribute_evaluated_in_false_no_aria_invalid_attribute(
    page: Page,
) -> None:
    locator = setup_page(page, None)
    expect(locator).not_to_have_accessible_error_message(ERROR_MESSAGE_TEXT)


def test_EX_264_to_have_accessible_error_message_should_handle_aria_invalid_attribute_evaluated_in_false_aria_invalid_false(
    page: Page,
) -> None:
    locator = setup_page(page, "false")
    expect(locator).not_to_have_accessible_error_message(ERROR_MESSAGE_TEXT)


def test_EX_265_to_have_accessible_error_message_should_handle_aria_invalid_attribute_evaluated_in_false_aria_invalid_empty_string(
    page: Page,
) -> None:
    locator = setup_page(page, "")
    expect(locator).not_to_have_accessible_error_message(ERROR_MESSAGE_TEXT)


def test_EX_266_to_have_accessible_error_message_should_handle_aria_invalid_attribute_evaluated_in_true_aria_invalid_true(
    page: Page,
) -> None:
    locator = setup_page(page, "true")
    expect(locator).to_have_accessible_error_message(ERROR_MESSAGE_TEXT)


def test_EX_267_to_have_accessible_error_message_should_handle_aria_invalid_attribute_evaluated_in_true_aria_invalid_foo_unrecognized_value(
    page: Page,
) -> None:
    locator = setup_page(page, "foo")
    expect(locator).to_have_accessible_error_message(ERROR_MESSAGE_TEXT)


def test_EX_268_should_show_error_message_when_validity_is_false_and_aria_invalid_is_true(
    page: Page,
) -> None:
    page.set_content(
        f"""
    <form>
      <input id="node" role="textbox" type="number" min="1" max="100" aria-invalid="true" aria-errormessage="error-msg" />
      <div id="error-msg">{ERROR_MESSAGE_TEXT}</div>
    </form>
  """
    )
    locator = page.locator("#node")
    locator.fill("101")
    expect(locator).to_have_accessible_error_message(ERROR_MESSAGE_TEXT)


def test_EX_269_should_show_error_message_when_validity_is_true_and_aria_invalid_is_true(
    page: Page,
) -> None:
    page.set_content(
        f"""
    <form>
      <input id="node" role="textbox" type="number" min="1" max="100" aria-invalid="true" aria-errormessage="error-msg" />
      <div id="error-msg">{ERROR_MESSAGE_TEXT}</div>
    </form>
  """
    )
    locator = page.locator("#node")
    locator.fill("99")
    expect(locator).to_have_accessible_error_message(ERROR_MESSAGE_TEXT)


def test_EX_270_should_show_error_message_when_validity_is_false_and_aria_invalid_is_false(
    page: Page,
) -> None:
    page.set_content(
        f"""
    <form>
      <input id="node" role="textbox" type="number" min="1" max="100" aria-invalid="false" aria-errormessage="error-msg" />
      <div id="error-msg">{ERROR_MESSAGE_TEXT}</div>
    </form>
  """
    )
    locator = page.locator("#node")
    locator.fill("101")
    expect(locator).to_have_accessible_error_message(ERROR_MESSAGE_TEXT)


def test_EX_271_should_not_show_error_message_when_validity_is_true_and_aria_invalid_is_false(
    page: Page,
) -> None:
    page.set_content(
        f"""
    <form>
      <input id="node" role="textbox" type="number" min="1" max="100" aria-invalid="false" aria-errormessage="error-msg" />
      <div id="error-msg">{ERROR_MESSAGE_TEXT}</div>
    </form>
  """
    )
    locator = page.locator("#node")
    locator.fill("99")
    expect(locator).not_to_have_accessible_error_message(ERROR_MESSAGE_TEXT)


def test_EX_272_should_show_error_message_for_all_roles(page: Page) -> None:
    page.set_content(
        """
    <label for="file">File input</label>
    <input id="file" aria-invalid="true" aria-errormessage="file-error-id" type="file" />
    <p id="file-error-id" role="alert">File is incorrect</p>
  """
    )
    locator = page.get_by_label("File input")
    expect(locator).to_have_accessible_error_message("File is incorrect")


def test_EX_273_to_have_role(page: Page) -> None:
    page.set_content('<div role="button">Button!</div>')
    expect(page.locator("div")).to_have_role("button")
    expect(page.locator("div")).not_to_have_role("checkbox")
    with pytest.raises(Error) as exc_info:
        expect(page.locator("div")).to_have_role(
            re.compile(r"button|checkbox")  # type: ignore[arg-type]
        )
    assert exc_info.value.message == '"role" argument in to_have_role must be a string'
