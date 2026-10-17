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

"""Port of tests/page/page-localstorage.spec.ts."""

from typing import Any, List

from playwright.sync_api import Page
from tests.server import Server


def by_name(items: List[Any]) -> List[Any]:
    """The items in name order, to compare them as a set (like `new Set(items)`)."""
    return sorted(items, key=lambda item: item["name"])


def test_ST_023_local_storage_items_returns_empty_array_on_fresh_origin(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    assert page.local_storage.items() == []


def test_ST_024_local_storage_get_item_returns_null_for_missing_key(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    assert page.local_storage.get_item("absent") is None


def test_ST_025_local_storage_set_item_persists_and_surfaces_in_items_get_item(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    page.local_storage.set_item("alpha", "1")
    page.local_storage.set_item("beta", "2")

    assert by_name(page.local_storage.items()) == [
        {"name": "alpha", "value": "1"},
        {"name": "beta", "value": "2"},
    ]
    assert page.local_storage.get_item("alpha") == "1"
    assert page.evaluate("() => localStorage.getItem('alpha')") == "1"


def test_ST_026_local_storage_set_item_overwrites_existing_value(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    page.local_storage.set_item("k", "first")
    page.local_storage.set_item("k", "second")
    assert page.local_storage.get_item("k") == "second"


def test_ST_027_local_storage_remove_item_removes_a_single_item(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    page.local_storage.set_item("a", "1")
    page.local_storage.set_item("b", "2")

    page.local_storage.remove_item("a")
    assert page.local_storage.items() == [{"name": "b", "value": "2"}]


def test_ST_028_local_storage_clear_empties_storage(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    page.local_storage.set_item("a", "1")
    page.local_storage.set_item("b", "2")

    page.local_storage.clear()
    assert page.local_storage.items() == []


def test_ST_029_session_storage_round_trip(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    assert page.session_storage.items() == []

    page.session_storage.set_item("s1", "v1")
    page.session_storage.set_item("s2", "v2")
    assert by_name(page.session_storage.items()) == [
        {"name": "s1", "value": "v1"},
        {"name": "s2", "value": "v2"},
    ]
    assert page.session_storage.get_item("s1") == "v1"

    page.session_storage.remove_item("s1")
    assert page.session_storage.items() == [{"name": "s2", "value": "v2"}]

    page.session_storage.clear()
    assert page.session_storage.items() == []


def test_ST_030_local_storage_and_session_storage_are_independent(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    page.local_storage.set_item("shared", "local")
    page.session_storage.set_item("shared", "session")

    assert page.local_storage.get_item("shared") == "local"
    assert page.session_storage.get_item("shared") == "session"

    page.local_storage.clear()
    assert page.local_storage.items() == []
    assert page.session_storage.get_item("shared") == "session"


def test_ST_031_storage_methods_are_scoped_to_the_current_origin(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/empty.html")
    page.local_storage.set_item("k", "origin-1")

    page.goto(server.CROSS_PROCESS_PREFIX + "/empty.html")
    assert page.local_storage.items() == []
    page.local_storage.set_item("k", "origin-2")

    page.goto(server.PREFIX + "/empty.html")
    assert page.local_storage.get_item("k") == "origin-1"
