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


async def test_should_return_none_paused_details_initially(
    context: BrowserContext,
) -> None:
    dbg = context.debugger
    assert dbg.paused_details is None


async def test_should_pause_at_next_and_resume(
    page: Page, context: BrowserContext
) -> None:
    await page.set_content("<div>click me</div>")
    dbg = context.debugger
    assert dbg.paused_details is None

    await dbg.request_pause()

    paused_event = asyncio.Event()

    def on_paused_state_changed() -> None:
        if dbg.paused_details is not None:
            assert "Click" in dbg.paused_details["title"]
            paused_event.set()
            asyncio.ensure_future(dbg.resume())

    dbg.on("pausedstatechanged", on_paused_state_changed)

    click_task = asyncio.ensure_future(page.click("div"))
    await asyncio.wait_for(paused_event.wait(), timeout=10)
    await asyncio.wait_for(click_task, timeout=10)
    assert dbg.paused_details is None


async def test_should_step_with_next(page: Page, context: BrowserContext) -> None:
    await page.set_content("<div>click me</div>")
    dbg = context.debugger
    assert dbg.paused_details is None

    await dbg.request_pause()

    first_pause_seen = [False]

    def on_paused_state_changed() -> None:
        if dbg.paused_details is not None and not first_pause_seen[0]:
            assert "Click" in dbg.paused_details["title"]
            first_pause_seen[0] = True
            asyncio.ensure_future(dbg.next())
        elif dbg.paused_details is not None and first_pause_seen[0]:
            asyncio.ensure_future(dbg.resume())

    dbg.on("pausedstatechanged", on_paused_state_changed)

    click_task = asyncio.ensure_future(page.click("div"))
    await asyncio.wait_for(click_task, timeout=10)
    assert dbg.paused_details is None


async def test_should_pause_at_pause_call(page: Page, context: BrowserContext) -> None:
    await page.set_content("<div>click me</div>")
    dbg = context.debugger
    assert dbg.paused_details is None

    await dbg.request_pause()

    paused_event = asyncio.Event()

    def on_paused_state_changed() -> None:
        if dbg.paused_details is not None:
            assert "Pause" in dbg.paused_details["title"]
            paused_event.set()
            asyncio.ensure_future(dbg.resume())

    dbg.on("pausedstatechanged", on_paused_state_changed)

    pause_task = asyncio.ensure_future(page.pause())
    await asyncio.wait_for(paused_event.wait(), timeout=10)
    await asyncio.wait_for(pause_task, timeout=10)
    assert dbg.paused_details is None
