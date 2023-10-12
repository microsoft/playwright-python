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
from playwright.sync_api import Page

TODO_ITEMS = ["buy some cheese", "feed the cat", "book a doctors appointment"]


def create_default_todos(page: Page) -> None:
    for item in TODO_ITEMS:
        page.locator(".new-todo").fill(item)
        page.locator(".new-todo").press("Enter")


def check_number_of_completed_todos_in_local_storage(page: Page, expected: int) -> None:
    assert (
        page.evaluate(
            "JSON.parse(localStorage['react-todos']).filter(i => i.completed).length"
        )
        == expected
    )


def assert_number_of_todos_in_local_storage(page: Page, expected: int) -> None:
    assert len(page.evaluate("JSON.parse(localStorage['react-todos'])")) == expected


def check_todos_in_local_storage(page: Page, title: str) -> None:
    assert title in page.evaluate(
        "JSON.parse(localStorage['react-todos']).map(i => i.title)"
    )
