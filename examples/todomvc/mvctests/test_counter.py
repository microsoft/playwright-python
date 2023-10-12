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

from .utils import TODO_ITEMS, assert_number_of_todos_in_local_storage


@pytest.fixture(autouse=True)
def run_around_tests(page: Page) -> Generator[None, None, None]:
    # setup before a test
    page.goto("https://demo.playwright.dev/todomvc")
    # run the actual test
    yield
    # run any cleanup code


def test_should_display_the_current_number_of_todo_items(page: Page) -> None:
    page.locator(".new-todo").fill(TODO_ITEMS[0])
    page.locator(".new-todo").press("Enter")
    expect(page.locator(".todo-count")).to_contain_text("1")

    page.locator(".new-todo").fill(TODO_ITEMS[1])
    page.locator(".new-todo").press("Enter")
    expect(page.locator(".todo-count")).to_contain_text("2")

    assert_number_of_todos_in_local_storage(page, 2)
