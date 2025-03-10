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

import json
from pathlib import Path

from playwright.sync_api import Browser, BrowserContext, Page, StorageState
from tests.server import Server


def test_should_capture_local_storage(context: BrowserContext) -> None:
    page1 = context.new_page()
    page1.route("**/*", lambda route: route.fulfill(body="<html></html>"))
    page1.goto("https://www.example.com")
    page1.evaluate("localStorage['name1'] = 'value1'")
    page1.goto("https://www.domain.com")
    page1.evaluate("localStorage['name2'] = 'value2'")

    state = context.storage_state()
    origins = state["origins"]
    assert origins
    assert len(origins) == 2
    assert origins[0] == {
        "origin": "https://www.domain.com",
        "localStorage": [{"name": "name2", "value": "value2"}],
    }
    assert origins[1] == {
        "origin": "https://www.example.com",
        "localStorage": [{"name": "name1", "value": "value1"}],
    }


def test_should_set_local_storage(browser: Browser) -> None:
    storage_state: StorageState = {
        "origins": [
            {
                "origin": "https://www.example.com",
                "localStorage": [{"name": "name1", "value": "value1"}],
            }
        ]
    }
    # We intentionally hide the indexed_db part in our API for now
    storage_state["origins"][0]["indexedDB"] = [  # type: ignore
        {
            "name": "db",
            "version": 42,
            "stores": [
                {
                    "name": "store",
                    "autoIncrement": False,
                    "records": [{"key": "bar", "value": "foo"}],
                    "indexes": [],
                }
            ],
        }
    ]
    context = browser.new_context(storage_state=storage_state)

    page = context.new_page()
    page.route("**/*", lambda route: route.fulfill(body="<html></html>"))
    page.goto("https://www.example.com")
    local_storage = page.evaluate("window.localStorage")
    assert local_storage == {"name1": "value1"}

    indexed_db = page.evaluate(
        """async () => {
        return new Promise((resolve, reject) => {
            const openRequest = indexedDB.open('db', 42);
            openRequest.addEventListener('success', () => {
                const db = openRequest.result;
                const transaction = db.transaction('store', 'readonly');
                const getRequest = transaction.objectStore('store').get('bar');
                getRequest.addEventListener('success', () => resolve(getRequest.result));
                getRequest.addEventListener('error', () => reject(getRequest.error));
            });
            openRequest.addEventListener('error', () => reject(openRequest.error));
        });
    }"""
    )
    assert indexed_db == "foo"
    context.close()


def test_should_round_trip_through_the_file(
    browser: Browser, context: BrowserContext, tmpdir: Path
) -> None:
    page1 = context.new_page()
    page1.route(
        "**/*",
        lambda route: route.fulfill(body="<html></html>"),
    )
    page1.goto("https://www.example.com")
    page1.evaluate(
        """() => {
            localStorage["name1"] = "value1"
            document.cookie = "username=John Doe"
            return document.cookie
        }"""
    )

    path = tmpdir / "storage-state.json"
    state = context.storage_state(path=path)
    with open(path, "r") as f:
        written = json.load(f)
    assert state == written

    context2 = browser.new_context(storage_state=path)
    page2 = context2.new_page()
    page2.route(
        "**/*",
        lambda route: route.fulfill(body="<html></html>"),
    )
    page2.goto("https://www.example.com")
    local_storage = page2.evaluate("window.localStorage")
    assert local_storage == {"name1": "value1"}
    cookie = page2.evaluate("document.cookie")
    assert cookie == "username=John Doe"
    context2.close()


def test_should_serialise_indexed_db(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    page.evaluate(
        """async () => {
            await new Promise((resolve, reject) => {
                const openRequest = indexedDB.open('db', 42);
                openRequest.onupgradeneeded = () => {
                openRequest.result.createObjectStore('store');
                };
                openRequest.onsuccess = () => {
                const request = openRequest.result.transaction('store', 'readwrite')
                    .objectStore('store')
                    .put('foo', 'bar');
                request.addEventListener('success', resolve);
                request.addEventListener('error', reject);
                };
            });
        }"""
    )
    assert page.context.storage_state() == {"cookies": [], "origins": []}
    assert page.context.storage_state(indexed_db=True) == {
        "cookies": [],
        "origins": [
            {
                "origin": f"http://localhost:{server.PORT}",
                "localStorage": [],
                "indexedDB": [
                    {
                        "name": "db",
                        "version": 42,
                        "stores": [
                            {
                                "name": "store",
                                "autoIncrement": False,
                                "records": [{"key": "bar", "value": "foo"}],
                                "indexes": [],
                            }
                        ],
                    }
                ],
            }
        ],
    }
