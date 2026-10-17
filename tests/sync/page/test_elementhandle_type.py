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

"""Port of tests/page/elementhandle-type.spec.ts."""

import pytest

from playwright.sync_api import Page


def test_EH_107_should_work(page: Page) -> None:
    page.set_content("<input type='text' />")
    page.type("input", "hello")
    assert page.eval_on_selector("input", "input => input.value") == "hello"


def test_EH_108_should_not_select_existing_value(page: Page) -> None:
    page.set_content("<input type='text' value='hello' />")
    page.type("input", "world")
    assert page.eval_on_selector("input", "input => input.value") == "worldhello"


def test_EH_109_should_reset_selection_when_not_focused(page: Page) -> None:
    page.set_content("<input type='text' value='hello' /><div tabIndex=2>text</div>")
    page.eval_on_selector(
        "input",
        """input => {
    input.selectionStart = 2;
    input.selectionEnd = 4;
    document.querySelector('div').focus();
  }""",
    )
    page.type("input", "world")
    assert page.eval_on_selector("input", "input => input.value") == "worldhello"


def test_EH_110_should_not_modify_selection_when_focused(page: Page) -> None:
    page.set_content("<input type='text' value='hello' />")
    page.eval_on_selector(
        "input",
        """input => {
    input.focus();
    input.selectionStart = 2;
    input.selectionEnd = 4;
  }""",
    )
    page.type("input", "world")
    assert page.eval_on_selector("input", "input => input.value") == "heworldo"


def test_EH_111_should_work_with_number_input(
    page: Page, browser_name: str, request: pytest.FixtureRequest
) -> None:
    if browser_name == "webkit":
        request.applymarker(
            pytest.mark.xfail(
                reason="upstream: Started failing after https://github.com/WebKit/WebKit/commit/c92a2aea185d63b5e9998608a9c0321a461c496c",
                strict=True,
            )
        )
    page.set_content("<input type='number' value=2 />")
    page.type("input", "13")
    assert page.eval_on_selector("input", "input => input.value") == "132"
