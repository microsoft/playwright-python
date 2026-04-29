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

import asyncio

from playwright.async_api import BrowserContext, Page
from tests.server import Server


async def test_should_expose_debugger_property(context: BrowserContext) -> None:
    assert context.debugger is context.debugger
    assert context.debugger.paused_details is None


async def test_should_pause_and_resume(
    context: BrowserContext, page: Page, server: Server
) -> None:
    paused_event = asyncio.Event()
    context.debugger.on("pausedstatechanged", lambda: paused_event.set())

    await context.debugger.request_pause()
    next_call = asyncio.create_task(page.goto(server.EMPTY_PAGE))

    await asyncio.wait_for(paused_event.wait(), timeout=5)
    assert context.debugger.paused_details is not None

    paused_event.clear()
    await context.debugger.resume()
    await asyncio.wait_for(paused_event.wait(), timeout=5)
    assert context.debugger.paused_details is None

    await next_call
