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
import gc
from typing import Dict

import pytest

from playwright.async_api import Page, async_playwright
from tests.server import Server
from tests.utils import TARGET_CLOSED_ERROR_MESSAGE


async def test_should_cancel_underlying_protocol_calls(
    browser_name: str, launch_arguments: Dict
) -> None:
    handler_exception = None

    def exception_handlerdler(loop: asyncio.AbstractEventLoop, context: Dict) -> None:
        nonlocal handler_exception
        handler_exception = context["exception"]

    asyncio.get_running_loop().set_exception_handler(exception_handlerdler)

    async with async_playwright() as p:
        browser = await p[browser_name].launch(**launch_arguments)
        page = await browser.new_page()
        task = asyncio.create_task(page.wait_for_selector("will-never-find"))
        # make sure that the wait_for_selector message was sent to the server (driver)
        await asyncio.sleep(0.1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await browser.close()

    # The actual 'Future exception was never retrieved' is logged inside the Future destructor (__del__).
    gc.collect()

    assert handler_exception is None

    asyncio.get_running_loop().set_exception_handler(None)


async def test_async_playwright_stop_multiple_times() -> None:
    playwright = await async_playwright().start()
    await playwright.stop()
    await playwright.stop()


async def test_cancel_pending_protocol_call_on_playwright_stop(server: Server) -> None:
    server.set_route("/hang", lambda _: None)
    playwright = await async_playwright().start()
    api_request_context = await playwright.request.new_context()
    pending_task = asyncio.create_task(api_request_context.get(server.PREFIX + "/hang"))
    await playwright.stop()
    with pytest.raises(Exception) as exc_info:
        await pending_task
    assert TARGET_CLOSED_ERROR_MESSAGE in str(exc_info.value)


async def test_should_collect_stale_handles(page: Page, server: Server) -> None:
    page.on("request", lambda _: None)
    response = await page.goto(server.PREFIX + "/title.html")
    assert response
    for i in range(1000):
        await page.evaluate(
            """async () => {
            const response = await fetch('/');
            await response.text();
        }"""
        )
    with pytest.raises(Exception) as exc_info:
        await response.all_headers()
    assert "The object has been collected to prevent unbounded heap growth." in str(
        exc_info.value
    )
