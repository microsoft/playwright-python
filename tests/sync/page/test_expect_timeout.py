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

"""Port of tests/page/expect-timeout.spec.ts."""

from typing import Any, Callable, List

import pytest

from playwright.sync_api import Locator, Page, TimeoutError, expect
from tests.server import Server

# Python's assertion messages have their own format: upstream's
# "expect(locator).toHaveText(expected) failed\n\nLocator: ...\nExpected: "hey"\n
# Received: ...\nTimeout: 1000ms" is "Locator expected to have text 'hey'\n
# Actual value: ..." followed by the call log, whose first line holds the timeout.
# The call log comes from the driver, with locators in Python syntax.


def test_EX_244_should_print_element_not_found(page: Page) -> None:
    page.set_content("<div id=node>Text content</div>")
    with pytest.raises(AssertionError) as exc_info:
        expect(page.locator("no-such-thing")).to_have_text("hey", timeout=1000)
    message = str(exc_info.value)
    assert (
        "Locator expected to have text 'hey'\n"
        "Actual value: None\n"
        "Error: element(s) not found"
    ) in message
    assert (
        "Call log:\n"
        '  - Expect "to_have_text" locator("no-such-thing") with timeout 1000ms\n'
    ) in message


def test_EX_245_should_print_timed_out_error_message_when_value_does_not_match(
    page: Page,
) -> None:
    page.set_content("<div id=node>Text content</div>")
    with pytest.raises(AssertionError) as exc_info:
        expect(page.locator("div")).to_have_text("hey", timeout=1000)
    message = str(exc_info.value)
    assert (
        "Locator expected to have text 'hey'\nActual value: Text content"
    ) in message
    assert (
        "Call log:\n" '  - Expect "to_have_text" locator("div") with timeout 1000ms\n'
    ) in message


def test_EX_246_should_print_timed_out_error_message_with_impossible_timeout(
    page: Page,
) -> None:
    page.set_content("<div id=node>Text content</div>")
    with pytest.raises(AssertionError) as exc_info:
        expect(page.locator("no-such-thing")).to_have_text("hey", timeout=1)
    message = str(exc_info.value)
    assert (
        "Locator expected to have text 'hey'\n"
        "Actual value: None\n"
        "Error: element(s) not found"
    ) in message
    assert (
        "Call log:\n"
        '  - Expect "to_have_text" locator("no-such-thing") with timeout 1ms'
    ) in message


def test_EX_247_should_print_timed_out_error_message_when_value_does_not_match_with_impossible_timeout(
    page: Page,
) -> None:
    page.set_content("<div id=node>Text content</div>")
    with pytest.raises(AssertionError) as exc_info:
        expect(page.locator("div")).to_have_text("hey", timeout=1)
    message = str(exc_info.value)
    assert (
        "Locator expected to have text 'hey'\nActual value: Text content"
    ) in message
    assert (
        "Call log:\n" '  - Expect "to_have_text" locator("div") with timeout 1ms\n'
    ) in message


def test_EX_248_should_have_timeout_error_name(page: Page) -> None:
    with pytest.raises(TimeoutError) as exc_info:
        page.wait_for_selector("#not-found", timeout=1)
    assert exc_info.value.name == "TimeoutError"


def test_EX_249_should_not_throw_when_navigating_during_one_shot_check(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_content("<div>hello</div>")

    def check() -> None:
        expect(page.locator("div")).to_have_text("bye")

    def navigate() -> None:
        page.goto(server.EMPTY_PAGE)
        page.set_content("<div>bye</div>")

    sync_gather(check, navigate)


def test_EX_250_should_not_throw_when_navigating_during_first_locator_handler_check(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    def handler(locator: Locator) -> None:
        pass

    page.add_locator_handler(page.locator("span"), handler)
    page.set_content("<div>hello</div>")

    def check() -> None:
        expect(page.locator("div")).to_have_text("bye")

    def navigate() -> None:
        page.goto(server.EMPTY_PAGE)
        page.set_content("<div>bye</div>")

    sync_gather(check, navigate)


def test_EX_251_should_timeout_during_first_locator_handler_check(
    page: Page,
) -> None:
    def handler(locator: Locator) -> None:
        pass

    page.add_locator_handler(page.locator("div"), handler)
    page.set_content("<div>hello</div><span>bye</span>")
    with pytest.raises(AssertionError) as exc_info:
        expect(page.locator("span")).to_have_text("bye", timeout=3000)
    message = str(exc_info.value)
    # Upstream prints the missing value as 'Received: ""'; Python prints None.
    assert "Locator expected to have text 'bye'\nActual value: None" in message
    assert (
        "Call log:\n" '  - Expect "to_have_text" locator("span") with timeout 3000ms\n'
    ) in message
    assert (
        'locator handler has finished, waiting for locator("div") to be hidden'
        in message
    )
    assert "locator resolved to visible <div>hello</div>" in message


def test_EX_252_should_not_miss_element_that_appears_between_retries_before_the_deadline(
    page: Page,
) -> None:
    page.set_content('<div id="target" style="display:none">content</div>')
    page.evaluate(
        """() => {
        window.builtins.setTimeout(() => {
          document.getElementById('target').style.display = 'block';
        }, 1500);
      }"""
    )
    expect(page.locator("#target")).to_be_visible(timeout=1800)
