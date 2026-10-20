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

"""Port of tests/library/browsercontext-storage-state.spec.ts."""

import datetime
import json
from pathlib import Path
from typing import Any, Awaitable, Callable, List, Optional

import pytest

from playwright.async_api import BrowserContext, Error, Page, Route, expect
from tests.server import Server, TestServerRequest

from ..utils import Utils

ContextFactory = Callable[..., Awaitable[BrowserContext]]


async def fulfill_empty_html(route: Route) -> None:
    """Upstream: route.fulfill({ body: '<html></html>' }).catch(() => {})."""
    try:
        await route.fulfill(body="<html></html>")
    except Error:
        pass


async def test_ST_001_should_capture_local_storage(
    context_factory: ContextFactory,
) -> None:
    context = await context_factory()
    page1 = await context.new_page()
    await page1.route("**/*", fulfill_empty_html)
    await page1.goto("https://www.example.com")
    await page1.evaluate("() => { localStorage['name1'] = 'value1'; }")
    await page1.goto("https://www.domain.com")
    await page1.evaluate("() => { localStorage['name2'] = 'value2'; }")
    state = await context.storage_state()
    assert state["origins"] == [
        {
            "origin": "https://www.domain.com",
            "localStorage": [{"name": "name2", "value": "value2"}],
        },
        {
            "origin": "https://www.example.com",
            "localStorage": [{"name": "name1", "value": "value1"}],
        },
    ]


async def test_ST_002_should_set_local_storage(
    context_factory: ContextFactory, browser_channel: Optional[str]
) -> None:
    if browser_channel and browser_channel.startswith("msedge"):
        pytest.skip("fixme: Network.clearBrowserCache sometimes stalls")

    context = await context_factory(
        storage_state={
            "cookies": [],
            "origins": [
                {
                    "origin": "https://www.example.com",
                    "localStorage": [{"name": "name1", "value": "value1"}],
                },
            ],
        }
    )
    page = await context.new_page()
    await page.route("**/*", fulfill_empty_html)
    await page.goto("https://www.example.com")
    local_storage = await page.evaluate("window.localStorage")
    assert local_storage == {"name1": "value1"}

    # Now use setStorageState to replace the storage
    await context.set_storage_state(
        {
            "cookies": [],
            "origins": [
                {
                    "origin": "https://www.example.com",
                    "localStorage": [{"name": "name2", "value": "value2"}],
                },
            ],
        }
    )
    assert len(context.pages) == 1
    await page.goto("https://www.example.com")
    local_storage2 = await page.evaluate("window.localStorage")
    assert local_storage2 == {"name2": "value2"}

    await context.close()


async def test_ST_003_should_report_good_error_if_the_url_is_not_valid(
    context_factory: ContextFactory,
) -> None:
    with pytest.raises(Error) as exc_info:
        await context_factory(
            storage_state={
                "cookies": [],
                "origins": [
                    {
                        "origin": "foo",
                        "localStorage": [{"name": "name1", "value": "value1"}],
                    },
                ],
            }
        )
    assert "Browser.new_context: Error setting storage state:" in exc_info.value.message
    assert "foo" in exc_info.value.message


async def test_ST_004_should_round_trip_through_the_file(
    context_factory: ContextFactory, browser_channel: Optional[str], tmp_path: Path
) -> None:
    if browser_channel and browser_channel.startswith("msedge"):
        pytest.skip("fixme: Network.clearBrowserCache sometimes stalls")

    context = await context_factory()
    page1 = await context.new_page()
    await page1.route("**/*", fulfill_empty_html)
    await page1.goto("https://www.example.com")
    await page1.evaluate(
        """async () => {
        localStorage['name1'] = 'value1';
        document.cookie = 'username=John Doe';

        await new Promise((resolve, reject) => {
          const openRequest = indexedDB.open('db', 42);
          openRequest.onupgradeneeded = () => {
            openRequest.result.createObjectStore('store', { keyPath: 'name' });
            openRequest.result.createObjectStore('store2');
          };
          openRequest.onsuccess = () => {
            const transaction = openRequest.result.transaction(['store', 'store2'], 'readwrite');
            transaction
                .objectStore('store')
                .put({ name: 'foo', date: new Date(0), null: null });
            transaction
                .objectStore('store2')
                .put(new TextEncoder().encode('bar'), 'foo');
            transaction.addEventListener('complete', resolve);
            transaction.addEventListener('error', reject);
          };
        });

        return document.cookie;
    }"""
    )

    path = tmp_path / "storage-state.json"
    state = await context.storage_state(path=path, indexed_db=True)
    written = path.read_text(encoding="utf-8")
    assert json.dumps(state, indent=2) == written

    async def check_context(context: BrowserContext) -> None:
        page = await context.new_page()
        await page.route("**/*", fulfill_empty_html)
        await page.goto("https://www.example.com")
        local_storage = await page.evaluate("window.localStorage")
        assert local_storage == {"name1": "value1"}
        cookie = await page.evaluate("document.cookie")
        assert cookie == "username=John Doe"
        idb_values = await page.evaluate(
            """() => new Promise((resolve, reject) => {
          const openRequest = indexedDB.open('db', 42);
          openRequest.addEventListener('success', async () => {
            const db = openRequest.result;
            const transaction = db.transaction(['store', 'store2'], 'readonly');
            const request1 = transaction.objectStore('store').get('foo');
            const request2 = transaction.objectStore('store2').get('foo');

            const [result1, result2] = await Promise.all([request1, request2].map(request => new Promise((resolve, reject) => {
              request.addEventListener('success', () => resolve(request.result));
              request.addEventListener('error', () => reject(request.error));
            })));

            resolve([result1, new TextDecoder().decode(result2)]);
          });
          openRequest.addEventListener('error', () => reject(openRequest.error));
        })"""
        )
        assert idb_values == [
            {
                "name": "foo",
                "date": datetime.datetime.fromtimestamp(0, datetime.timezone.utc),
                "null": None,
            },
            "bar",
        ]

    context2 = await context_factory(storage_state=path)
    await check_context(context2)
    await context2.close()

    context3 = await context_factory()
    await context3.set_storage_state(path)
    assert len(context3.pages) == 0
    await check_context(context3)
    await context3.close()


async def test_ST_005_should_round_trip_opfs(
    browser_name: str,
    context_factory: ContextFactory,
    page: Page,
    server: Server,
    tmp_path: Path,
) -> None:
    # https://github.com/microsoft/playwright/issues/41400
    if browser_name == "webkit":
        pytest.skip("OPFS is unavailable in non-persistent WebKit contexts")

    await page.goto(server.EMPTY_PAGE)
    await page.evaluate(
        """async () => {
        const root = await navigator.storage.getDirectory();
        const nested = await root.getDirectoryHandle('nested', { create: true });
        await nested.getDirectoryHandle('empty', { create: true });

        const binary = await nested.getFileHandle('data.bin', { create: true });
        const binaryWritable = await binary.createWritable();
        await binaryWritable.write(new Uint8Array([0, 1, 2, 255]));
        await binaryWritable.close();

        const text = await root.getFileHandle('hello.txt', { create: true });
        const textWritable = await text.createWritable();
        await textWritable.write('Hello, world!');
        await textWritable.close();
    }"""
    )

    assert await page.context.storage_state() == {"cookies": [], "origins": []}

    path = tmp_path / "storage-state.json"
    storage_state = await page.context.storage_state(path=path, opfs=True)
    assert storage_state["origins"] == [
        {
            "origin": server.PREFIX,
            "localStorage": [],
            "opfs": [
                {"path": "hello.txt", "type": "file", "base64": "SGVsbG8sIHdvcmxkIQ=="},
                {"path": "nested", "type": "directory"},
                {"path": "nested/data.bin", "type": "file", "base64": "AAEC/w=="},
                {"path": "nested/empty", "type": "directory"},
            ],
        }
    ]
    assert json.loads(path.read_text(encoding="utf-8")) == storage_state
    assert await page.context.request.storage_state(opfs=True) == storage_state

    async def check_context(context: BrowserContext) -> None:
        assert await context.storage_state(opfs=True) == storage_state
        check_page = await context.new_page()
        await check_page.goto(server.EMPTY_PAGE)
        assert (
            await check_page.evaluate(
                """async () => {
          const root = await navigator.storage.getDirectory();
          const hello = await (await root.getFileHandle('hello.txt')).getFile();
          const nested = await root.getDirectoryHandle('nested');
          const data = await (await nested.getFileHandle('data.bin')).getFile();
          const empty = await nested.getDirectoryHandle('empty');
          const emptyEntries = [];
          for await (const name of empty.keys())
            emptyEntries.push(name);
          return {
            text: await hello.text(),
            bytes: [...new Uint8Array(await data.arrayBuffer())],
            empty: emptyEntries,
          };
        }"""
            )
            == {
                "text": "Hello, world!",
                "bytes": [0, 1, 2, 255],
                "empty": [],
            }
        )

    context2 = await context_factory(storage_state=path)
    await check_context(context2)
    await context2.close()

    context3 = await context_factory()
    page3 = await context3.new_page()
    await page3.goto(server.EMPTY_PAGE)
    await page3.evaluate(
        """async () => {
        const root = await navigator.storage.getDirectory();
        await root.getFileHandle('stale.txt', { create: true });
    }"""
    )
    await context3.set_storage_state(storage_state)
    await check_context(context3)
    await context3.close()


async def test_ST_006_should_capture_cookies(
    server: Server,
    context: BrowserContext,
    page: Page,
    context_factory: ContextFactory,
) -> None:
    def handler(request: TestServerRequest) -> None:
        request.responseHeaders.setRawHeaders("Set-Cookie", ["a=b", "empty="])
        request.finish()

    server.set_route("/setcookie.html", handler)

    await page.goto(server.PREFIX + "/setcookie.html")
    assert (
        await page.evaluate(
            """() => {
        const cookies = document.cookie.split(';');
        return cookies.map(cookie => cookie.trim()).sort();
    }"""
        )
        == [
            "a=b",
            "empty=",
        ]
    )

    storage_state = await context.storage_state()
    assert sorted(
        (cookie["name"], cookie["value"]) for cookie in storage_state["cookies"]
    ) == [("a", "b"), ("empty", "")]
    context2 = await context_factory(storage_state=storage_state)
    page2 = await context2.new_page()
    await page2.goto(server.EMPTY_PAGE)
    assert (
        await page2.evaluate(
            """() => {
        const cookies = document.cookie.split(';');
        return cookies.map(cookie => cookie.trim()).sort();
    }"""
        )
        == [
            "a=b",
            "empty=",
        ]
    )


async def test_ST_007_should_not_emit_events_about_internal_page(
    context_factory: ContextFactory,
) -> None:
    context = await context_factory()
    page = await context.new_page()
    await page.route("**/*", fulfill_empty_html)
    await page.goto("https://www.example.com")
    await page.evaluate("() => localStorage['name1'] = 'value1'")
    await page.goto("https://www.domain.com")
    await page.evaluate("() => localStorage['name2'] = 'value2'")

    events: List[Any] = []
    context.on("page", lambda e: events.append(e))
    context.on("request", lambda e: events.append(e))
    context.on("requestfailed", lambda e: events.append(e))
    context.on("requestfinished", lambda e: events.append(e))
    context.on("response", lambda e: events.append(e))
    await context.storage_state()
    assert len(events) == 0


async def test_ST_008_should_not_restore_local_storage_twice(
    context_factory: ContextFactory,
) -> None:
    context = await context_factory(
        storage_state={
            "cookies": [],
            "origins": [
                {
                    "origin": "https://www.example.com",
                    "localStorage": [{"name": "name1", "value": "value1"}],
                },
            ],
        }
    )
    page = await context.new_page()
    await page.route("**/*", fulfill_empty_html)
    await page.goto("https://www.example.com")
    local_storage1 = await page.evaluate("window.localStorage")
    assert local_storage1 == {"name1": "value1"}

    await page.evaluate("() => window.localStorage['name1'] = 'value2'")

    await page.goto("https://www.example.com")
    local_storage2 = await page.evaluate("window.localStorage")
    assert local_storage2 == {"name1": "value2"}

    await context.close()


async def test_ST_009_should_handle_missing_file(
    context_factory: ContextFactory, tmp_path: Path
) -> None:
    file = tmp_path / "does-not-exist.json"
    with pytest.raises(Exception) as exc_info:
        await context_factory(storage_state=file)
    # Upstream expects Node's "ENOENT"; Python's message for it is "[Errno 2] ...".
    assert (
        f"Error reading storage state from {file}:\n[Errno 2] No such file or directory"
        in str(exc_info.value)
    )


async def test_ST_010_should_handle_malformed_file(
    context_factory: ContextFactory, tmp_path: Path
) -> None:
    file = tmp_path / "state.json"
    file.write_text("not-json", encoding="utf-8")
    with pytest.raises(Exception) as exc_info:
        await context_factory(storage_state=file)
    # Upstream expects the message of Node's JSON.parse; this is the message of
    # Python's json.loads.
    assert (
        f"Error reading storage state from {file}:\n"
        "Expecting value: line 1 column 1 (char 0)"
    ) in str(exc_info.value)


@pytest.mark.xfail(
    reason="driver: it replaces lone surrogates with U+FFFD in the messages to the "
    "clients other than JavaScript (toWellFormed() in cli/driver.ts)",
    strict=True,
)
async def test_ST_011_should_serialize_storage_state_with_lone_surrogates(
    page: Page, context: BrowserContext, server: Server
) -> None:
    # https://github.com/microsoft/playwright-dotnet/issues/2819
    await page.goto(server.EMPTY_PAGE)
    await page.evaluate(
        "() => window.localStorage.setItem('foo', String.fromCharCode(55934))"
    )
    storage_state = await context.storage_state()
    value = storage_state["origins"][0]["localStorage"][0]["value"]
    # Compare the code points: a lone surrogate in the report crashes pytest-xdist.
    assert [ord(c) for c in value] == [55934]


async def test_ST_012_should_work_when_service_worker_is_intefering(
    page: Page, context: BrowserContext, server: Server
) -> None:
    def handle_root(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("content-type", "text/html")
        request.write(
            b"""
      <script>
        console.log('from page');
        window.localStorage.foo = 'bar';
        window.registrationPromise = navigator.serviceWorker.register('sw.js');
        window.activationPromise = new Promise(resolve => navigator.serviceWorker.oncontrollerchange = resolve);
      </script>
    """
        )
        request.finish()

    server.set_route("/", handle_root)

    def handle_sw(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("content-type", "application/javascript")
        request.write(
            b"""
      const kHtmlPage = `
        <script>
          console.log('from sw page');
          let counter = window.localStorage.counter || 0;
          ++counter;
          window.localStorage.counter = counter;
          setTimeout(() => {
            window.location.href = counter + '.html';
          }, 0);
        </script>
      `;

      console.log('from sw 1');
      self.addEventListener('fetch', event => {
        console.log('fetching ' + event.request.url);
        const blob = new Blob([kHtmlPage], { type: 'text/html' });
        const response = new Response(blob, { status: 200 , statusText: 'OK' });
        event.respondWith(response);
      });

      self.addEventListener('activate', event => {
        console.log('from sw 2');
        event.waitUntil(clients.claim());
      });
    """
        )
        request.finish()

    server.set_route("/sw.js", handle_sw)

    await page.goto(server.PREFIX)
    await page.evaluate("() => window['activationPromise']")

    storage_state = await context.storage_state()
    assert storage_state["origins"][0]["localStorage"][0] == {
        "name": "foo",
        "value": "bar",
    }


async def test_ST_013_should_work_when_service_worker_is_intefering_and_the_origin_is_not_open(
    page: Page, context: BrowserContext, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/42656
    def handle_root(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("content-type", "text/html")
        request.write(
            b"""
      <script>
        window.localStorage.foo = 'bar';
        window.registrationPromise = navigator.serviceWorker.register('sw.js');
        window.activationPromise = new Promise(resolve => navigator.serviceWorker.oncontrollerchange = resolve);
      </script>
    """
        )
        request.finish()

    server.set_route("/", handle_root)

    def handle_sw(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("content-type", "application/javascript")
        request.write(
            b"""
      const kHtmlPage = `
        <script>
          window.localStorage.fromServiceWorker = 'yes';
          window.location.href = 'redirected.html';
        </script>
      `;

      self.addEventListener('fetch', event => {
        if (new URL(event.request.url).pathname !== '/')
          return;
        const blob = new Blob([kHtmlPage], { type: 'text/html' });
        event.respondWith(new Response(blob, { status: 200, statusText: 'OK' }));
      });

      self.addEventListener('activate', event => {
        event.waitUntil(clients.claim());
      });
    """
        )
        request.finish()

    server.set_route("/sw.js", handle_sw)

    def handle_redirected(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("content-type", "text/html")
        request.write(b"<html></html>")
        request.finish()

    server.set_route("/redirected.html", handle_redirected)

    await page.goto(server.PREFIX)
    await page.evaluate("() => window['activationPromise']")
    await page.goto("about:blank")

    storage_state = await context.storage_state()
    assert storage_state["origins"][0]["localStorage"] == [
        {"name": "foo", "value": "bar"}
    ]


async def test_ST_014_should_set_local_storage_in_third_party_context(
    context_factory: ContextFactory, server: Server, utils: Utils
) -> None:
    context = await context_factory(
        storage_state={
            "cookies": [],
            "origins": [
                {
                    "origin": server.CROSS_PROCESS_PREFIX,
                    "localStorage": [{"name": "name1", "value": "value1"}],
                },
            ],
        }
    )
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    frame = await utils.attach_frame(
        page, "frame1", server.CROSS_PROCESS_PREFIX + "/empty.html"
    )

    local_storage = await frame.evaluate("window.localStorage")
    assert local_storage == {"name1": "value1"}
    await context.close()


async def test_ST_015_should_roundtrip_local_storage_in_third_party_context(
    page: Page, context_factory: ContextFactory, server: Server, utils: Utils
) -> None:
    await page.goto(server.EMPTY_PAGE)
    frame = await utils.attach_frame(
        page, "frame1", server.CROSS_PROCESS_PREFIX + "/empty.html"
    )
    await frame.evaluate("() => window.localStorage.setItem('name1', 'value1')")
    storage_state = await page.context.storage_state()

    context2 = await context_factory(storage_state=storage_state)
    page2 = await context2.new_page()
    await page2.goto(server.EMPTY_PAGE)
    frame2 = await utils.attach_frame(
        page2, "frame1", server.CROSS_PROCESS_PREFIX + "/empty.html"
    )

    local_storage = await frame2.evaluate("window.localStorage")
    assert local_storage == {"name1": "value1"}
    await context2.close()


async def test_ST_016_should_support_indexed_db(
    page: Page, server: Server, context_factory: ContextFactory
) -> None:
    await page.goto(server.PREFIX + "/to-do-notifications/index.html")

    await expect(page.locator("#notifications")).to_match_aria_snapshot(
        """
    - list:
      - listitem: Database initialised.
  """
    )
    await page.get_by_label("Task title").fill("Pet the cat")
    await page.get_by_label("Hours").fill("1")
    await page.get_by_label("Mins").fill("1")
    await page.get_by_text("Add Task").click()
    await expect(page.locator("#notifications")).to_match_aria_snapshot(
        """
    - list:
      - listitem: "Transaction completed: database modification finished."
  """
    )

    storage_state = await page.context.storage_state(indexed_db=True)
    assert storage_state["origins"] == [
        {
            "origin": server.PREFIX,
            "localStorage": [],
            "indexedDB": [
                {
                    "name": "toDoList",
                    "version": 4,
                    "stores": [
                        {
                            "name": "toDoList",
                            "autoIncrement": False,
                            "keyPath": "taskTitle",
                            "records": [
                                {
                                    "valueEncoded": {
                                        "id": 1,
                                        "o": [
                                            {"k": "taskTitle", "v": "Pet the cat"},
                                            {"k": "hours", "v": "1"},
                                            {"k": "minutes", "v": "1"},
                                            {"k": "day", "v": "01"},
                                            {"k": "month", "v": "January"},
                                            {"k": "year", "v": "2025"},
                                            {"k": "notified", "v": "no"},
                                            {
                                                "k": "binaryTitle",
                                                "v": {"ab": {"b": "UGV0IHRoZSBjYXQ="}},
                                            },
                                        ],
                                    },
                                },
                            ],
                            "indexes": [
                                {
                                    "name": "day",
                                    "keyPath": "day",
                                    "multiEntry": False,
                                    "unique": False,
                                },
                                {
                                    "name": "hours",
                                    "keyPath": "hours",
                                    "multiEntry": False,
                                    "unique": False,
                                },
                                {
                                    "name": "minutes",
                                    "keyPath": "minutes",
                                    "multiEntry": False,
                                    "unique": False,
                                },
                                {
                                    "name": "month",
                                    "keyPath": "month",
                                    "multiEntry": False,
                                    "unique": False,
                                },
                                {
                                    "name": "notified",
                                    "keyPath": "notified",
                                    "multiEntry": False,
                                    "unique": False,
                                },
                                {
                                    "name": "year",
                                    "keyPath": "year",
                                    "multiEntry": False,
                                    "unique": False,
                                },
                            ],
                        },
                    ],
                },
            ],
        },
    ]

    context = await context_factory(storage_state=storage_state)
    assert await context.storage_state(indexed_db=True) == storage_state

    recreated_page = await context.new_page()
    await recreated_page.goto(server.PREFIX + "/to-do-notifications/index.html")
    await expect(recreated_page.locator("#task-list")).to_match_aria_snapshot(
        """
    - list:
      - listitem:
        - text: /Pet the cat \\[Pet the cat\\]/
  """
    )

    assert await context.storage_state() == {"cookies": [], "origins": []}


@pytest.mark.parametrize("restore", ["newContext", "setStorageState"])
async def test_ST_017_should_roundtrip_indexed_db_values_and_keys_with(
    page: Page,
    server: Server,
    context_factory: ContextFactory,
    tmp_path: Path,
    restore: str,
) -> None:
    # https://github.com/microsoft/playwright/issues/42703
    # https://github.com/microsoft/playwright/issues/43418
    await page.goto(server.EMPTY_PAGE)
    await page.evaluate(
        """() => new Promise((resolve, reject) => {
        const request = indexedDB.open('collections', 1);
        request.onupgradeneeded = () => request.result.createObjectStore('store');
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
          const db = request.result;
          const transaction = db.transaction('store', 'readwrite');
          const store = transaction.objectStore('store');
          store.put(new Map([['mk', 'mv']]), 'map');
          store.put(new Set([1, 2]), 'set');
          store.put(0, 'zero');
          store.put(false, 'false');
          store.put('', 'empty');
          store.put(null, 'null');
          store.put(Infinity, 'infinity');
          store.put('first', 0);
          store.put('second', '');
          transaction.oncomplete = () => {
            db.close();
            resolve();
          };
          transaction.onerror = () => reject(transaction.error);
        };
    })"""
    )

    path = tmp_path / "storage-state.json"
    storage_state = await page.context.storage_state(indexed_db=True, path=path)
    context = await (
        context_factory(storage_state=path)
        if restore == "newContext"
        else context_factory()
    )
    if restore == "setStorageState":
        await context.set_storage_state(storage_state)
    assert await context.storage_state(indexed_db=True) == storage_state

    restored_page = await context.new_page()
    await restored_page.goto(server.EMPTY_PAGE)
    entries = await restored_page.evaluate(
        """async () => {
        const db = await new Promise((resolve, reject) => {
          const request = indexedDB.open('collections', 1);
          request.onerror = () => reject(request.error);
          request.onsuccess = () => resolve(request.result);
        });
        const transaction = db.transaction('store', 'readonly');
        const store = transaction.objectStore('store');
        transaction.oncomplete = () => db.close();
        const [keys, values] = await Promise.all([store.getAllKeys(), store.getAll()].map(request => new Promise((resolve, reject) => {
          request.onsuccess = () => resolve(request.result);
          request.onerror = () => reject(request.error);
        })));
        return keys.map((key, i) => {
          const value = values[i];
          if (value instanceof Map)
            return [key, { map: [...value] }];
          if (value instanceof Set)
            return [key, { set: [...value] }];
          return [key, value];
        });
    }"""
    )
    assert entries == [
        [0, "first"],
        ["", "second"],
        ["empty", ""],
        ["false", False],
        ["infinity", float("inf")],
        ["map", {"map": [["mk", "mv"]]}],
        ["null", None],
        ["set", {"set": [1, 2]}],
        ["zero", 0],
    ]


async def test_ST_018_should_support_empty_indexed_db(
    page: Page, server: Server, context_factory: ContextFactory
) -> None:
    # https://github.com/microsoft/playwright/issues/35760
    await page.goto(server.EMPTY_PAGE)
    await page.evaluate(
        """() => new Promise(resolve => {
        const openRequest = indexedDB.open('unused-db');
        openRequest.onsuccess = () => resolve();
        openRequest.onerror = () => resolve();
    })"""
    )
    storage_state = await page.context.storage_state(indexed_db=True)
    assert storage_state["origins"] == [
        {
            "origin": server.PREFIX,
            "localStorage": [],
            "indexedDB": [
                {
                    "name": "unused-db",
                    "version": 1,
                    "stores": [],
                }
            ],
        }
    ]

    context = await context_factory(storage_state=storage_state)
    assert await context.storage_state(indexed_db=True) == storage_state


async def test_ST_019_should_not_leave_indexed_db_connections_open(
    context_factory: ContextFactory, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/42258
    context = await context_factory()
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    await page.evaluate(
        """async () => {
        const openRequest = indexedDB.open('db', 1);
        openRequest.onupgradeneeded = () => openRequest.result.createObjectStore('store');
        await new Promise((resolve, reject) => {
          openRequest.onsuccess = () => {
            const db = openRequest.result;
            const transaction = db.transaction('store', 'readwrite');
            transaction.objectStore('store').put('value', 'key');
            transaction.oncomplete = () => {
              db.close();
              resolve();
            };
            transaction.onerror = () => reject(transaction.error);
          };
          openRequest.onerror = () => reject(openRequest.error);
        });
    }"""
    )

    state = await context.storage_state(indexed_db=True)

    await page.evaluate(
        """() => new Promise((resolve, reject) => {
        const request = indexedDB.deleteDatabase('db');
        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
        request.onblocked = () => reject(new Error('deleteDatabase was blocked'));
    })"""
    )

    await context.set_storage_state(state)
    assert await context.storage_state(indexed_db=True) == state


async def test_ST_020_should_round_trip_web_authn_credentials_with_storage_state(
    context_factory: ContextFactory, server: Server
) -> None:
    context = await context_factory()
    credential = await context.credentials.create(server.HOSTNAME)

    # Credentials are opt-in, omitted by default.
    assert await context.storage_state() == {"cookies": [], "origins": []}

    storage_state = await context.storage_state(credentials=True)
    assert storage_state == {"cookies": [], "origins": [], "credentials": [credential]}

    # A fresh context seeded from the storage state holds the same credential and round-trips equal.
    context2 = await context_factory(storage_state=storage_state)
    assert await context2.credentials.get() == [credential]
    assert await context2.storage_state(credentials=True) == storage_state


async def test_ST_021_set_storage_state_should_replace_credentials(
    context_factory: ContextFactory,
) -> None:
    ctx_a = await context_factory()
    cred_a = await ctx_a.credentials.create("a.example.com")
    state_a = await ctx_a.storage_state(credentials=True)

    ctx_b = await context_factory()
    cred_b = await ctx_b.credentials.create("b.example.com")
    state_b = await ctx_b.storage_state(credentials=True)

    context = await context_factory(storage_state=state_a)
    assert await context.credentials.get() == [cred_a]

    # Replacing the storage state swaps in the new credentials.
    await context.set_storage_state(state_b)
    assert await context.credentials.get() == [cred_b]

    # A storage state without credentials clears them.
    await context.set_storage_state({"cookies": [], "origins": []})
    assert await context.credentials.get() == []

    # Credentials can be installed again afterwards.
    await context.set_storage_state(state_a)
    assert await context.credentials.get() == [cred_a]


async def test_ST_022_set_storage_state_should_handle_missing_file(
    context_factory: ContextFactory, tmp_path: Path
) -> None:
    context = await context_factory()
    file = tmp_path / "does-not-exist.json"
    with pytest.raises(Exception) as exc_info:
        await context.set_storage_state(file)
    assert f"Error reading storage state from {file}" in str(exc_info.value)
