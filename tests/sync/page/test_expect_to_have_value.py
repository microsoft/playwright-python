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

"""Port of tests/page/expect-to-have-value.spec.ts."""

import re

import pytest

from playwright.sync_api import Page, expect


def test_EX_302_should_work(page: Page) -> None:
    page.set_content("<input id=node></input>")
    locator = page.locator("#node")
    locator.fill("Text content")
    expect(locator).to_have_value("Text content")


def test_EX_303_should_work_with_label(page: Page) -> None:
    page.set_content("<label><input></input></label>")
    page.locator("label input").fill("Text content")
    expect(page.locator("label")).to_have_value("Text content")


def test_EX_304_should_work_with_regex(page: Page) -> None:
    page.set_content("<input id=node></input>")
    locator = page.locator("#node")
    locator.fill("Text content")
    expect(locator).to_have_value(re.compile(r"Text"))


def test_EX_305_should_support_failure(page: Page) -> None:
    page.set_content("<input id=node></input>")
    locator = page.locator("#node")
    locator.fill("Text content")
    with pytest.raises(AssertionError) as exc_info:
        expect(locator).to_have_value(re.compile(r"Text2"), timeout=1000)
    assert "Actual value: Text content" in str(exc_info.value)


def test_EX_306_to_have_values_with_multi_select_works_with_text(
    page: Page,
) -> None:
    page.set_content(
        """
      <select multiple>
        <option value="R">Red</option>
        <option value="G">Green</option>
        <option value="B">Blue</option>
      </select>
    """
    )
    locator = page.locator("select")
    locator.select_option(["R", "G"])
    expect(locator).to_have_values(["R", "G"])


def test_EX_307_to_have_values_with_multi_select_follows_labels(
    page: Page,
) -> None:
    page.set_content(
        """
      <label for="colors">Pick a Color</label>
      <select id="colors" multiple>
        <option value="R">Red</option>
        <option value="G">Green</option>
        <option value="B">Blue</option>
      </select>
    """
    )
    locator = page.locator("text=Pick a Color")
    locator.select_option(["R", "G"])
    expect(locator).to_have_values(["R", "G"])


def test_EX_308_to_have_values_with_multi_select_exact_match_with_text_failure(
    page: Page,
) -> None:
    page.set_content(
        """
      <select multiple>
        <option value="RR">Red</option>
        <option value="GG">Green</option>
      </select>
    """
    )
    locator = page.locator("select")
    locator.select_option(["RR", "GG"])
    with pytest.raises(AssertionError) as exc_info:
        expect(locator).to_have_values(["R", "G"], timeout=1000)
    message = str(exc_info.value)
    assert "Locator expected to have Values '['R', 'G']'" in message
    assert "Actual value: ['RR', 'GG']" in message


def test_EX_309_to_have_values_with_multi_select_works_with_regex(
    page: Page,
) -> None:
    page.set_content(
        """
      <select multiple>
        <option value="R">Red</option>
        <option value="G">Green</option>
        <option value="B">Blue</option>
      </select>
    """
    )
    locator = page.locator("select")
    locator.select_option(["R", "G"])
    expect(locator).to_have_values([re.compile(r"R"), re.compile(r"G")])


def test_EX_310_to_have_values_with_multi_select_fails_when_items_not_selected(
    page: Page,
) -> None:
    page.set_content(
        """
      <select multiple>
        <option value="R">Red</option>
        <option value="G">Green</option>
        <option value="B">Blue</option>
      </select>
    """
    )
    locator = page.locator("select")
    locator.select_option(["B"])
    with pytest.raises(AssertionError) as exc_info:
        expect(locator).to_have_values(
            [re.compile(r"R"), re.compile(r"G")], timeout=1000
        )
    assert "Actual value: ['B']" in str(exc_info.value)


def test_EX_311_to_have_values_with_multi_select_fails_when_multiple_not_specified(
    page: Page,
) -> None:
    page.set_content(
        """
      <select>
        <option value="R">Red</option>
        <option value="G">Green</option>
        <option value="B">Blue</option>
      </select>
    """
    )
    locator = page.locator("select")
    locator.select_option(["B"])
    with pytest.raises(AssertionError) as exc_info:
        expect(locator).to_have_values(
            [re.compile(r"R"), re.compile(r"G")], timeout=1000
        )
    assert "Not a select element with a multiple attribute" in str(exc_info.value)


def test_EX_312_to_have_values_with_multi_select_fails_when_not_a_select_element(
    page: Page,
) -> None:
    page.set_content(
        """
      <input value="foo" />
    """
    )
    locator = page.locator("input")
    with pytest.raises(AssertionError) as exc_info:
        expect(locator).to_have_values(
            [re.compile(r"R"), re.compile(r"G")], timeout=1000
        )
    assert "Not a select element with a multiple attribute" in str(exc_info.value)
