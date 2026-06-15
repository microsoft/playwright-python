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

from playwright.async_api import Page
from tests.server import Server


async def test_should_expose_local_storage_property(page: Page) -> None:
    assert page.local_storage is page.local_storage


async def test_should_expose_session_storage_property(page: Page) -> None:
    assert page.session_storage is page.session_storage


async def test_local_storage_set_and_get_item(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.local_storage.set_item("foo", "bar")
    value = await page.local_storage.get_item("foo")
    assert value == "bar"
    assert await page.evaluate("() => localStorage.getItem('foo')") == "bar"


async def test_local_storage_items(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.local_storage.set_item("a", "1")
    await page.local_storage.set_item("b", "2")
    items = await page.local_storage.items()
    assert len(items) == 2
    assert {"name": "a", "value": "1"} in items
    assert {"name": "b", "value": "2"} in items


async def test_local_storage_remove_item(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.local_storage.set_item("foo", "bar")
    await page.local_storage.remove_item("foo")
    result = await page.evaluate("() => localStorage.getItem('foo')")
    assert result is None


async def test_local_storage_clear(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.local_storage.set_item("foo", "bar")
    await page.local_storage.clear()
    length = await page.evaluate("() => localStorage.length")
    assert length == 0


async def test_session_storage_set_and_get_item(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.session_storage.set_item("foo", "bar")
    value = await page.session_storage.get_item("foo")
    assert value == "bar"
    assert await page.evaluate("() => sessionStorage.getItem('foo')") == "bar"


async def test_session_storage_items(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.session_storage.set_item("a", "1")
    items = await page.session_storage.items()
    assert len(items) == 1
    assert items[0] == {"name": "a", "value": "1"}


async def test_session_storage_remove_item(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.session_storage.set_item("foo", "bar")
    await page.session_storage.remove_item("foo")
    result = await page.evaluate("() => sessionStorage.getItem('foo')")
    assert result is None


async def test_session_storage_clear(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.session_storage.set_item("foo", "bar")
    await page.session_storage.clear()
    length = await page.evaluate("() => sessionStorage.length")
    assert length == 0
