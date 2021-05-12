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

import time

import pytest

from playwright.sync_api import BrowserType, Error
from tests.server import Server


def test_browser_type_connect_slow_mo(
    server: Server, browser_type: BrowserType, launch_server
):
    remote_server = launch_server()
    browser = browser_type.connect(remote_server.ws_endpoint, slow_mo=100)
    browser_context = browser.new_context()
    t1 = time.monotonic()
    page = browser_context.new_page()
    assert page.evaluate("11 * 11") == 121
    assert (time.monotonic() - t1) >= 0.2
    page.goto(server.EMPTY_PAGE)
    browser.close()


def test_browser_type_connect_should_be_able_to_reconnect_to_a_browser(
    server: Server, browser_type: BrowserType, launch_server
):
    remote_server = launch_server()
    browser = browser_type.connect(remote_server.ws_endpoint)
    browser_context = browser.new_context()
    assert len(browser_context.pages) == 0
    page = browser_context.new_page()
    assert len(browser_context.pages) == 1
    assert page.evaluate("11 * 11") == 121
    page.goto(server.EMPTY_PAGE)
    browser.close()

    browser = browser_type.connect(remote_server.ws_endpoint)
    browser_context = browser.new_context()
    page = browser_context.new_page()
    page.goto(server.EMPTY_PAGE)
    browser.close()


def test_browser_type_connect_should_be_able_to_connect_two_browsers_at_the_same_time(
    browser_type: BrowserType, launch_server
):
    remote_server = launch_server()
    browser1 = browser_type.connect(remote_server.ws_endpoint)
    assert len(browser1.contexts) == 0
    browser1.new_context()
    assert len(browser1.contexts) == 1

    browser2 = browser_type.connect(remote_server.ws_endpoint)
    assert len(browser2.contexts) == 0
    browser2.new_context()
    assert len(browser2.contexts) == 1
    assert len(browser1.contexts) == 1

    browser1.close()
    page2 = browser2.new_page()
    # original browser should still work
    assert page2.evaluate("7 * 6") == 42

    browser2.close()


def test_browser_type_connect_disconnected_event_should_be_emitted_when_browser_is_closed_or_server_is_closed(
    browser_type: BrowserType, launch_server
):
    # Launch another server to not affect other tests.
    remote = launch_server()

    browser1 = browser_type.connect(remote.ws_endpoint)
    browser2 = browser_type.connect(remote.ws_endpoint)

    disconnected1 = []
    disconnected2 = []
    browser1.on("disconnected", lambda: disconnected1.append(True))
    browser2.on("disconnected", lambda: disconnected2.append(True))

    page2 = browser2.new_page()

    browser1.close()
    assert len(disconnected1) == 1
    assert len(disconnected2) == 0

    remote.kill()
    assert len(disconnected1) == 1

    with pytest.raises(Error):
        # Tickle connection so that it gets a chance to dispatch disconnect event.
        page2.title()
    assert len(disconnected2) == 1


def test_browser_type_disconnected_event_should_have_browser_as_argument(
    browser_type: BrowserType, launch_server
):
    remote_server = launch_server()
    browser = browser_type.connect(remote_server.ws_endpoint)
    event_payloads = []
    browser.on("disconnected", lambda b: event_payloads.append(b))
    browser.close()
    assert event_payloads[0] == browser


def test_browser_type_connect_set_browser_connected_state(
    browser_type: BrowserType, launch_server
):
    remote_server = launch_server()
    browser = browser_type.connect(remote_server.ws_endpoint)
    assert browser.is_connected()
    browser.close()
    assert browser.is_connected() is False


def test_browser_type_connect_should_throw_when_used_after_is_connected_returns_false(
    browser_type: BrowserType, launch_server
):
    remote_server = launch_server()
    browser = browser_type.connect(remote_server.ws_endpoint)
    page = browser.new_page()

    remote_server.kill()

    with pytest.raises(Error) as exc_info:
        page.evaluate("1 + 1")
    assert "Playwright connection closed" == exc_info.value.message
    assert browser.is_connected() is False


def test_browser_type_connect_should_forward_close_events_to_pages(
    browser_type: BrowserType, launch_server
):
    # Launch another server to not affect other tests.
    remote = launch_server()

    browser = browser_type.connect(remote.ws_endpoint)
    context = browser.new_context()
    page = context.new_page()

    events = []
    browser.on("disconnected", lambda: events.append("browser::disconnected"))
    context.on("close", lambda: events.append("context::close"))
    page.on("close", lambda: events.append("page::close"))

    browser.close()
    assert events == ["page::close", "context::close", "browser::disconnected"]
    remote.kill()
    assert events == ["page::close", "context::close", "browser::disconnected"]


def test_browser_type_connect_should_forward_close_events_on_remote_kill(
    browser_type: BrowserType, launch_server
):
    # Launch another server to not affect other tests.
    remote = launch_server()

    browser = browser_type.connect(remote.ws_endpoint)
    context = browser.new_context()
    page = context.new_page()

    events = []
    browser.on("disconnected", lambda: events.append("browser::disconnected"))
    context.on("close", lambda: events.append("context::close"))
    page.on("close", lambda: events.append("page::close"))
    remote.kill()
    with pytest.raises(Error):
        page.title()
    assert events == ["page::close", "context::close", "browser::disconnected"]


def test_connect_to_closed_server_without_hangs(
    browser_type: BrowserType, launch_server
):
    remote_server = launch_server()
    remote_server.kill()
    with pytest.raises(Error) as exc:
        browser_type.connect(remote_server.ws_endpoint)
    assert "websocket.connect: " in exc.value.message
