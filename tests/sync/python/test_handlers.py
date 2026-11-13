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

"""Python only: tests of behaviors that no upstream test covers."""

from dataclasses import dataclass, field
from typing import List
from unittest.mock import MagicMock

from playwright.sync_api import ConsoleMessage, Page, Route
from tests.server import Server


@dataclass(slots=True)
class SlottedCollector:
    messages: List[str] = field(default_factory=list)

    def handle(self, msg: ConsoleMessage) -> None:
        self.messages.append(msg.text)

    def __call__(self, msg: ConsoleMessage) -> None:
        self.messages.append(msg.text)


@dataclass(frozen=True)
class FrozenCollector:
    messages: List[str] = field(default_factory=list)

    def handle(self, msg: ConsoleMessage) -> None:
        self.messages.append(msg.text)

    def __call__(self, msg: ConsoleMessage) -> None:
        self.messages.append(msg.text)


@dataclass(slots=True)
class SlottedRouteHandler:
    hits: List[str] = field(default_factory=list)

    def fulfill(self, route: Route) -> None:
        self.hits.append(route.request.url)
        route.fulfill(body="intercepted")


def test_event_listener_builtin_bound_method_and_removal(page: Page) -> None:
    messages: List[ConsoleMessage] = []
    page.on("console", messages.append)
    page.evaluate('() => console.log("one")')
    assert [m.text for m in messages] == ["one"]

    page.remove_listener("console", messages.append)
    page.evaluate('() => console.log("two")')
    assert [m.text for m in messages] == ["one"]


def test_expose_function_with_builtin_callables(page: Page) -> None:
    recorded: List[str] = []
    page.expose_function("record_value", recorded.append)
    page.expose_function("get_len", len)

    length = page.evaluate(
        """async () => {
            await window.record_value("hello");
            return await window.get_len("hello");
        }"""
    )
    assert recorded == ["hello"]
    assert length == 5


def test_event_listener_slotted_frozen_and_mock_callables(page: Page) -> None:
    slotted_a = SlottedCollector()
    slotted_b = SlottedCollector()
    frozen_a = FrozenCollector()
    frozen_b = FrozenCollector()
    mock = MagicMock()

    page.on("console", slotted_a.handle)
    page.on("console", slotted_b)
    page.on("console", frozen_a.handle)
    page.on("console", frozen_b)
    page.on("console", mock)

    page.evaluate('() => console.log("ok")')
    assert slotted_a.messages == ["ok"]
    assert slotted_b.messages == ["ok"]
    assert frozen_a.messages == ["ok"]
    assert frozen_b.messages == ["ok"]
    assert mock.call_count == 1
    assert mock.call_args[0][0].text == "ok"

    page.remove_listener("console", slotted_a.handle)
    page.remove_listener("console", slotted_b)
    page.remove_listener("console", frozen_a.handle)
    page.remove_listener("console", frozen_b)
    page.remove_listener("console", mock)

    page.evaluate('() => console.log("after")')
    assert slotted_a.messages == ["ok"]
    assert slotted_b.messages == ["ok"]
    assert frozen_a.messages == ["ok"]
    assert frozen_b.messages == ["ok"]
    assert mock.call_count == 1


def test_route_and_unroute_with_builtin_method_predicate_and_slotted_handler(
    page: Page, server: Server
) -> None:
    allowed_urls = {server.EMPTY_PAGE}
    handler = SlottedRouteHandler()

    page.route(allowed_urls.__contains__, handler.fulfill)
    page.goto(server.EMPTY_PAGE)
    assert page.locator("body").inner_text() == "intercepted"
    assert handler.hits == [server.EMPTY_PAGE]

    page.unroute(allowed_urls.__contains__, handler.fulfill)
    page.goto(server.EMPTY_PAGE)
    assert page.locator("body").inner_text() == ""
    assert handler.hits == [server.EMPTY_PAGE]

    page.route(server.EMPTY_PAGE.__eq__, handler.fulfill)
    page.goto(server.EMPTY_PAGE)
    assert page.locator("body").inner_text() == "intercepted"
    assert handler.hits == [server.EMPTY_PAGE, server.EMPTY_PAGE]

    page.unroute(server.EMPTY_PAGE.__eq__, handler.fulfill)
    page.goto(server.EMPTY_PAGE)
    assert page.locator("body").inner_text() == ""
    assert handler.hits == [server.EMPTY_PAGE, server.EMPTY_PAGE]
