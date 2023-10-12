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
from typing import Generator

import pytest

from playwright.sync_api import Page, expect

from .utils import (
    TODO_ITEMS,
    assert_number_of_todos_in_local_storage,
    check_todos_in_local_storage,
    create_default_todos,
)


@pytest.fixture(autouse=True)
def run_around_tests(page: Page) -> Generator[None, None, None]:
    # setup before a test
    page.goto("https://demo.playwright.dev/todomvc")
    create_default_todos(page)
    assert_number_of_todos_in_local_storage(page, 3)
    # run the actual test
    yield
    # run any cleanup code


def test_should_hide_other_controls_when_editing(page: Page) -> None:
    todo_item = page.locator(".todo-list li").nth(1)
    todo_item.dblclick()
    expect(todo_item.locator(".toggle")).not_to_be_visible()
    expect(todo_item.locator("label")).not_to_be_visible()
    assert_number_of_todos_in_local_storage(page, 3)


def test_should_save_edits_on_blur(page: Page) -> None:
    todo_items = page.locator(".todo-list li")
    todo_items.nth(1).dblclick()
    todo_items.nth(1).locator(".edit").fill("buy some sausages")
    todo_items.nth(1).locator(".edit").dispatch_event("blur")

    expect(todo_items).to_have_text(
        [
            TODO_ITEMS[0],
            "buy some sausages",
            TODO_ITEMS[2],
        ]
    )
    check_todos_in_local_storage(page, "buy some sausages")


def test_should_trim_entered_text(page: Page) -> None:
    todo_items = page.locator(".todo-list li")
    todo_items.nth(1).dblclick()
    todo_items.nth(1).locator(".edit").fill("    buy some sausages    ")
    todo_items.nth(1).locator(".edit").press("Enter")

    expect(todo_items).to_have_text(
        [
            TODO_ITEMS[0],
            "buy some sausages",
            TODO_ITEMS[2],
        ]
    )
    check_todos_in_local_storage(page, "buy some sausages")


def test_should_remove_the_item_if_an_empty_text_string_was_entered(page: Page) -> None:
    todo_items = page.locator(".todo-list li")
    todo_items.nth(1).dblclick()
    todo_items.nth(1).locator(".edit").fill("")
    todo_items.nth(1).locator(".edit").press("Enter")

    expect(todo_items).to_have_text(
        [
            TODO_ITEMS[0],
            TODO_ITEMS[2],
        ]
    )


def test_should_cancel_edits_on_escape(page: Page) -> None:
    todo_items = page.locator(".todo-list li")
    todo_items.nth(1).dblclick()
    todo_items.nth(1).locator(".edit").press("Escape")
    expect(todo_items).to_have_text(TODO_ITEMS)
