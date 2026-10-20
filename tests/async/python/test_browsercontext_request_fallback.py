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

from playwright.async_api import BrowserContext, Page
from tests.server import Server


async def test_should_chain_once(
    page: Page, context: BrowserContext, server: Server
) -> None:
    await context.route(
        "**/madeup.txt",
        lambda route: asyncio.create_task(
            route.fulfill(status=200, body="fulfilled one")
        ),
        times=1,
    )
    await context.route(
        "**/madeup.txt", lambda route: asyncio.create_task(route.fallback()), times=1
    )

    resp = await page.goto(server.PREFIX + "/madeup.txt")
    assert resp
    body = await resp.body()
    assert body == b"fulfilled one"
