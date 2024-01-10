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
import re
from typing import Generator

import pytest

from playwright.sync_api import Page, expect

from .utils import (
    TODO_ITEMS,
    assert_number_of_todos_in_local_storage,
    create_default_todos,
)


@pytest.fixture(autouse=True)
def run_around_tests(page: Page) -> Generator[None, None, None]:
    # setup before a test
    page.goto("https://demo.playwright.dev/todomvc")
    # run the actual test
    yield
    # run any cleanup code


def test_new_todo_test_should_allow_me_to_add_todo_items(page: Page) -> None:
    # Create 1st todo.
    page.locator(".new-todo").fill(TODO_ITEMS[0])
    page.locator(".new-todo").press("Enter")

    # Make sure the list only has one todo item.
    expect(page.locator(".view label")).to_have_text([TODO_ITEMS[0]])

    # Create 2nd todo.
    page.locator(".new-todo").fill(TODO_ITEMS[1])
    page.locator(".new-todo").press("Enter")

    # Make sure the list now has two todo items.
    expect(page.locator(".view label")).to_have_text([TODO_ITEMS[0], TODO_ITEMS[1]])

    assert_number_of_todos_in_local_storage(page, 2)


def test_new_todo_test_should_clear_text_input_field_when_an_item_is_added(
    page: Page,
) -> None:
    # Create one todo item.
    page.locator(".new-todo").fill(TODO_ITEMS[0])
    page.locator(".new-todo").press("Enter")

    # Check that input is empty.
    expect(page.locator(".new-todo")).to_be_empty()
    assert_number_of_todos_in_local_storage(page, 1)


def test_new_todo_test_should_append_new_items_to_the_bottom_of_the_list(
    page: Page,
) -> None:
    # Create 3 items.
    create_default_todos(page)

    # Check test using different methods.
    expect(page.locator(".todo-count")).to_have_text("3 items left")
    expect(page.locator(".todo-count")).to_contain_text("3")
    expect(page.locator(".todo-count")).to_have_text(re.compile("3"))

    # Check all items in one call.
    expect(page.locator(".view label")).to_have_text(TODO_ITEMS)
    assert_number_of_todos_in_local_storage(page, 3)


def test_new_todo_should_show_main_and_foter_when_items_added(page: Page) -> None:
    page.locator(".new-todo").fill(TODO_ITEMS[0])
    page.locator(".new-todo").press("Enter")

    expect(page.locator(".main")).to_be_visible()
    expect(page.locator(".footer")).to_be_visible()
    assert_number_of_todos_in_local_storage(page, 1)
