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

"""Port of tests/library/browsercontext-clearcookies.spec.ts."""

import re
import time
from urllib.parse import urlparse

import pytest

from playwright.sync_api import Browser, BrowserContext, Page
from tests.server import Server


def hostname(prefix: str) -> str:
    """Like `new URL(prefix).hostname`."""
    result = urlparse(prefix).hostname
    assert result
    return result


def test_CO_042_should_clear_cookies(
    context: BrowserContext, page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    context.add_cookies([{"url": server.EMPTY_PAGE, "name": "cookie1", "value": "1"}])
    assert page.evaluate("document.cookie") == "cookie1=1"
    context.clear_cookies()
    assert context.cookies() == []
    page.reload()
    assert page.evaluate("document.cookie") == ""


def test_CO_043_should_isolate_cookies_when_clearing(
    context: BrowserContext, server: Server, browser: Browser
) -> None:
    another_context = browser.new_context()
    context.add_cookies(
        [{"url": server.EMPTY_PAGE, "name": "page1cookie", "value": "page1value"}]
    )
    another_context.add_cookies(
        [{"url": server.EMPTY_PAGE, "name": "page2cookie", "value": "page2value"}]
    )

    assert len(context.cookies()) == 1
    assert len(another_context.cookies()) == 1

    context.clear_cookies()
    assert len(context.cookies()) == 0
    assert len(another_context.cookies()) == 1

    another_context.clear_cookies()
    assert len(context.cookies()) == 0
    assert len(another_context.cookies()) == 0
    another_context.close()


def test_CO_044_should_remove_cookies_by_name(
    context: BrowserContext, page: Page, server: Server
) -> None:
    context.add_cookies(
        [
            {
                "name": "cookie1",
                "value": "1",
                "domain": hostname(server.PREFIX),
                "path": "/",
            },
            {
                "name": "cookie2",
                "value": "2",
                "domain": hostname(server.PREFIX),
                "path": "/",
            },
        ]
    )
    page.goto(server.PREFIX)
    assert page.evaluate("document.cookie") == "cookie1=1; cookie2=2"
    context.clear_cookies(name="cookie1")
    assert page.evaluate("document.cookie") == "cookie2=2"


def test_CO_045_should_remove_cookies_by_name_regex(
    context: BrowserContext, page: Page, server: Server
) -> None:
    context.add_cookies(
        [
            {
                "name": "cookie1",
                "value": "1",
                "domain": hostname(server.PREFIX),
                "path": "/",
            },
            {
                "name": "cookie2",
                "value": "2",
                "domain": hostname(server.PREFIX),
                "path": "/",
            },
        ]
    )
    page.goto(server.PREFIX)
    assert page.evaluate("document.cookie") == "cookie1=1; cookie2=2"
    context.clear_cookies(name=re.compile("coo.*1"))
    assert page.evaluate("document.cookie") == "cookie2=2"


def test_CO_046_should_remove_cookies_by_domain(
    context: BrowserContext, page: Page, server: Server
) -> None:
    context.add_cookies(
        [
            {
                "name": "cookie1",
                "value": "1",
                "domain": hostname(server.PREFIX),
                "path": "/",
            },
            {
                "name": "cookie2",
                "value": "2",
                "domain": hostname(server.CROSS_PROCESS_PREFIX),
                "path": "/",
            },
        ]
    )
    page.goto(server.PREFIX)
    assert page.evaluate("document.cookie") == "cookie1=1"
    page.goto(server.CROSS_PROCESS_PREFIX)
    assert page.evaluate("document.cookie") == "cookie2=2"
    context.clear_cookies(domain=hostname(server.CROSS_PROCESS_PREFIX))
    assert page.evaluate("document.cookie") == ""
    page.goto(server.PREFIX)
    assert page.evaluate("document.cookie") == "cookie1=1"


def test_CO_047_should_remove_cookies_by_path(
    context: BrowserContext, page: Page, server: Server
) -> None:
    context.add_cookies(
        [
            {
                "name": "cookie1",
                "value": "1",
                "domain": hostname(server.PREFIX),
                "path": "/api/v1",
            },
            {
                "name": "cookie2",
                "value": "2",
                "domain": hostname(server.PREFIX),
                "path": "/api/v2",
            },
            {
                "name": "cookie3",
                "value": "3",
                "domain": hostname(server.PREFIX),
                "path": "/",
            },
        ]
    )
    page.goto(server.PREFIX + "/api/v1")
    assert page.evaluate("document.cookie") == "cookie1=1; cookie3=3"
    context.clear_cookies(path="/api/v1")
    assert page.evaluate("document.cookie") == "cookie3=3"
    page.goto(server.PREFIX + "/api/v2")
    assert page.evaluate("document.cookie") == "cookie2=2; cookie3=3"
    page.goto(server.PREFIX + "/")
    assert page.evaluate("document.cookie") == "cookie3=3"


def test_CO_048_should_remove_cookies_by_name_and_domain(
    context: BrowserContext, page: Page, server: Server
) -> None:
    context.add_cookies(
        [
            {
                "name": "cookie1",
                "value": "1",
                "domain": hostname(server.PREFIX),
                "path": "/",
            },
            {
                "name": "cookie1",
                "value": "1",
                "domain": hostname(server.CROSS_PROCESS_PREFIX),
                "path": "/",
            },
        ]
    )
    page.goto(server.PREFIX)
    assert page.evaluate("document.cookie") == "cookie1=1"
    context.clear_cookies(name="cookie1", domain=hostname(server.PREFIX))
    assert page.evaluate("document.cookie") == ""
    page.goto(server.CROSS_PROCESS_PREFIX)
    assert page.evaluate("document.cookie") == "cookie1=1"


def test_CO_049_should_not_transiently_delete_non_matching_cookies_when_filtering(
    context: BrowserContext,
    page: Page,
    server: Server,
    browser_name: str,
    is_win: bool,
    is_frozen_webkit: bool,
) -> None:
    if browser_name == "webkit" and is_win:
        pytest.skip(
            "cookieStore change events not supported on WebKit/Windows "
            "(curl backend lacks cookie change notifications)"
        )
    if is_frozen_webkit:
        pytest.skip("frozen WebKit")

    context.add_cookies(
        [
            {
                "name": "keep_me",
                "value": "1",
                "domain": hostname(server.PREFIX),
                "path": "/",
            },
            {
                "name": "delete_me",
                "value": "2",
                "domain": hostname(server.PREFIX),
                "path": "/",
            },
        ]
    )
    page.goto(server.PREFIX)

    events_handle = page.evaluate_handle(
        """() => {
            const events = [];
            cookieStore.addEventListener('change', event => {
                for (const changed of event.changed)
                    events.push(`changed ${changed.name}`);
                for (const deleted of event.deleted)
                    events.push(`deleted ${deleted.name}`);
            });
            return events;
        }"""
    )

    context.clear_cookies(name="delete_me")
    # Like expect.poll(): wait until the events are as expected.
    deadline = time.monotonic() + 5
    events = events_handle.json_value()
    while events != ["deleted delete_me"] and time.monotonic() < deadline:
        page.wait_for_timeout(100)
        events = events_handle.json_value()
    assert events == ["deleted delete_me"]
    assert page.evaluate("document.cookie") == "keep_me=1"


def test_CO_050_should_remove_partitioned_cookies_by_name(
    browser: Browser, https_server: Server, browser_name: str
) -> None:
    if browser_name != "chromium":
        pytest.skip("Partitioned cookies (CHIPS) are Chromium-specific")
    context = browser.new_context(ignore_https_errors=True)
    context.add_cookies(
        [
            {
                "name": "delete_me",
                "value": "1",
                "domain": https_server.HOSTNAME,
                "path": "/",
                "secure": True,
                "sameSite": "None",
                "partitionKey": f"https://{https_server.HOSTNAME}",
            },
            {
                "name": "keep_me",
                "value": "2",
                "domain": https_server.HOSTNAME,
                "path": "/",
                "secure": True,
                "sameSite": "None",
                "partitionKey": f"https://{https_server.HOSTNAME}",
            },
        ]
    )
    before = context.cookies()
    assert [(c["name"], c.get("partitionKey")) for c in before] == [
        ("delete_me", f"https://{https_server.HOSTNAME}"),
        ("keep_me", f"https://{https_server.HOSTNAME}"),
    ]

    context.clear_cookies(name="delete_me")
    assert [(c["name"], c.get("partitionKey")) for c in context.cookies()] == [
        ("keep_me", f"https://{https_server.HOSTNAME}"),
    ]
    context.close()


def test_CO_051_should_remove_nameless_cookies_by_empty_name(
    context: BrowserContext,
) -> None:
    context.add_cookies(
        [
            {"name": "", "value": "nameless", "domain": "example.com", "path": "/"},
            {
                "name": "session",
                "value": "secret",
                "domain": "example.com",
                "path": "/",
            },
        ]
    )
    context.clear_cookies(name="")
    assert [cookie["name"] for cookie in context.cookies()] == ["session"]
