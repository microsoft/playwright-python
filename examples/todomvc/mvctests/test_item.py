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
    check_number_of_completed_todos_in_local_storage,
    check_todos_in_local_storage,
    create_default_todos,
)


@pytest.fixture(autouse=True)
def run_around_tests(page: Page) -> Generator[None, None, None]:
    # setup before a test
    page.goto("https://demo.playwright.dev/todomvc")
    # run the actual test
    yield
    # run any cleanup code


def test_should_allow_me_to_mark_items_as_completed(page: Page) -> None:
    # Create two items.
    for item in TODO_ITEMS[:2]:
        page.locator(".new-todo").fill(item)
        page.locator(".new-todo").press("Enter")

    # Check first item.
    firstTodo = page.locator(".todo-list li").nth(0)
    firstTodo.locator(".toggle").check()
    expect(firstTodo).to_have_class("completed")

    # Check second item.
    secondTodo = page.locator(".todo-list li").nth(1)
    expect(secondTodo).not_to_have_class("completed")
    secondTodo.locator(".toggle").check()

    # Assert completed class.
    expect(firstTodo).to_have_class("completed")
    expect(secondTodo).to_have_class("completed")


def test_should_allow_me_to_un_mark_items_as_completed(page: Page) -> None:
    # Create two items.
    for item in TODO_ITEMS[:2]:
        page.locator(".new-todo").fill(item)
        page.locator(".new-todo").press("Enter")

    firstTodo = page.locator(".todo-list li").nth(0)
    secondTodo = page.locator(".todo-list li").nth(1)
    firstTodo.locator(".toggle").check()
    expect(firstTodo).to_have_class("completed")
    expect(secondTodo).not_to_have_class("completed")
    check_number_of_completed_todos_in_local_storage(page, 1)

    firstTodo.locator(".toggle").uncheck()
    expect(firstTodo).not_to_have_class("completed")
    expect(secondTodo).not_to_have_class("completed")
    check_number_of_completed_todos_in_local_storage(page, 0)


def test_should_allow_me_to_edit_an_item(page: Page) -> None:
    create_default_todos(page)

    todo_items = page.locator(".todo-list li")
    secondTodo = todo_items.nth(1)
    secondTodo.dblclick()
    expect(secondTodo.locator(".edit")).to_have_value(TODO_ITEMS[1])
    secondTodo.locator(".edit").fill("buy some sausages")
    secondTodo.locator(".edit").press("Enter")

    # Explicitly assert the new text value.
    expect(todo_items).to_have_text([TODO_ITEMS[0], "buy some sausages", TODO_ITEMS[2]])
    check_todos_in_local_storage(page, "buy some sausages")
