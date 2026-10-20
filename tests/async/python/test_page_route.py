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

import asyncio
import re
from typing import List

from playwright.async_api import Page, Request, Route
from tests.server import Server


async def test_page_route_should_unroute(page: Page, server: Server) -> None:
    intercepted = []

    def _handle1(route: Route) -> None:
        intercepted.append(1)
        asyncio.create_task(route.continue_())

    await page.route("**/*", _handle1)

    def _handle2(route: Route, request: Request) -> None:
        intercepted.append(2)
        asyncio.create_task(route.continue_())

    await page.route("**/empty.html", _handle2)

    def _handle3(route: Route, request: Request) -> None:
        intercepted.append(3)
        asyncio.create_task(route.continue_())

    await page.route(
        "**/empty.html",
        _handle3,
    )

    def handler4(route: Route) -> None:
        intercepted.append(4)
        asyncio.create_task(route.continue_())

    await page.route(re.compile("empty.html"), handler4)

    await page.goto(server.EMPTY_PAGE)
    assert intercepted == [4]

    intercepted = []
    await page.unroute(re.compile("empty.html"), handler4)
    await page.goto(server.EMPTY_PAGE)
    assert intercepted == [3]

    intercepted = []
    await page.unroute("**/empty.html")
    await page.goto(server.EMPTY_PAGE)
    assert intercepted == [1]


async def test_page_route_returns_disposable(page: Page, server: Server) -> None:
    intercepted: List[str] = []

    async def handler(route: Route) -> None:
        intercepted.append(route.request.url)
        await route.continue_()

    async with await page.route("**/*", handler):
        await page.goto(server.EMPTY_PAGE)
        assert any(server.EMPTY_PAGE in url for url in intercepted)
    intercepted.clear()
    await page.goto(server.EMPTY_PAGE)
    assert intercepted == []
