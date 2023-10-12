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
    create_default_todos(page)
    # make sure the app had a chance to save updated todos in storage
    # before navigating to a new view, otherwise the items can get lost :(
    # in some frameworks like Durandal
    check_todos_in_local_storage(page, TODO_ITEMS[0])
    # run the actual test
    yield
    # run any cleanup code


def test_should_allow_me_to_display_active_item(page: Page) -> None:
    page.locator(".todo-list li .toggle").nth(1).check()
    check_number_of_completed_todos_in_local_storage(page, 1)
    page.locator(".filters >> text=Active").click()
    expect(page.locator(".todo-list li")).to_have_count(2)
    expect(page.locator(".todo-list li")).to_have_text([TODO_ITEMS[0], TODO_ITEMS[2]])


def test_should_respect_the_back_button(page: Page) -> None:
    page.locator(".todo-list li .toggle").nth(1).check()
    check_number_of_completed_todos_in_local_storage(page, 1)

    # Showing all items
    page.locator(".filters >> text=All").click()
    expect(page.locator(".todo-list li")).to_have_count(3)

    # Showing active items
    page.locator(".filters >> text=Active").click()

    # Showing completed items
    page.locator(".filters >> text=Completed").click()

    expect(page.locator(".todo-list li")).to_have_count(1)
    page.go_back()
    expect(page.locator(".todo-list li")).to_have_count(2)
    page.go_back()
    expect(page.locator(".todo-list li")).to_have_count(3)


def test_should_allow_me_to_display_completed_items(page: Page) -> None:
    page.locator(".todo-list li .toggle").nth(1).check()
    check_number_of_completed_todos_in_local_storage(page, 1)
    page.locator(".filters >> text=Completed").click()
    expect(page.locator(".todo-list li")).to_have_count(1)


def test_should_allow_me_to_display_all_items(page: Page) -> None:
    page.locator(".todo-list li .toggle").nth(1).check()
    check_number_of_completed_todos_in_local_storage(page, 1)
    page.locator(".filters >> text=Active").click()
    page.locator(".filters >> text=Completed").click()
    page.locator(".filters >> text=All").click()
    expect(page.locator(".todo-list li")).to_have_count(3)


def test_should_highlight_the_current_applied_filter(page: Page) -> None:
    expect(page.locator(".filters >> text=All")).to_have_class("selected")
    page.locator(".filters >> text=Active").click()
    # Page change - active items.
    expect(page.locator(".filters >> text=Active")).to_have_class("selected")
    page.locator(".filters >> text=Completed").click()
    # Page change - completed items.
    expect(page.locator(".filters >> text=Completed")).to_have_class("selected")
