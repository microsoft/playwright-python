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

"""Python only: tests of behaviors that no upstream test covers."""


import pytest

from playwright.sync_api import Page, expect
from tests.server import Server


def test_should_print_users_message_for_page_based_assertion(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content("<title>new title</title>")
    with pytest.raises(AssertionError) as excinfo:
        expect(page, "Title is not new").to_have_title("old title", timeout=100)
    assert "Title is not new" in str(excinfo.value)
    with pytest.raises(AssertionError) as excinfo:
        expect(page).to_have_title("old title", timeout=100)
    assert "Page title expected to be" in str(excinfo.value)


def test_should_print_expected_value_with_custom_message(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content("<title>new title</title>")
    with pytest.raises(AssertionError) as excinfo:
        expect(page, "custom-message").to_have_title("old title", timeout=100)
    assert "custom-message" in str(excinfo.value)
    assert "Expected value: 'old title'" in str(excinfo.value)
    with pytest.raises(AssertionError) as excinfo:
        expect(page.get_by_text("hello"), "custom-message").to_be_visible(timeout=100)
    assert "custom-message" in str(excinfo.value)
    assert "Expected value" not in str(excinfo.value)


def test_should_be_able_to_set_custom_global_timeout(page: Page) -> None:
    try:
        expect.set_options(timeout=111)
        with pytest.raises(AssertionError) as exc_info:
            expect(page.locator("#a1")).to_be_visible()
        assert 'Expect "to_be_visible" locator("#a1") with timeout 111ms' in str(
            exc_info.value
        )
    finally:
        expect.set_options(timeout=5_000)


def test_soft_outside_scope_raises_runtime_error(page: Page, server: Server) -> None:
    page.set_content("<div>hello</div>")
    with pytest.raises(RuntimeError, match="pytest-playwright"):
        expect.soft(page.locator("div")).to_have_text("nope", timeout=500)


def test_soft_inside_scope_collects_failures(page: Page, server: Server) -> None:
    from playwright._impl._assertions import _soft_scope

    page.goto(server.EMPTY_PAGE)
    page.set_content("<title>actual</title><div>hello</div>")

    with _soft_scope() as errors:
        expect.soft(page).to_have_title("expected", timeout=500)
        expect.soft(page.locator("div")).to_have_text("goodbye", timeout=500)
        expect.soft(page.locator("div")).to_have_text("hello")
        expect.soft(page.locator("div")).not_to_have_text("hello", timeout=500)

    assert len(errors) == 3
    assert all(isinstance(e, AssertionError) for e in errors)
