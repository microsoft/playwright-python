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
from typing import Any, List, cast

import pytest

from playwright.async_api import (
    BrowserContext,
    ConsoleMessage,
    Error,
    Page,
    Response,
    Route,
)
from tests.server import Server


async def test_listeners(page: Page, server: Server) -> None:
    log = []

    def print_response(response: Response) -> None:
        log.append(response)

    page.on("response", print_response)
    await page.goto(f"{server.PREFIX}/input/textarea.html")
    assert len(log) > 0
    page.remove_listener("response", print_response)

    log = []
    await page.goto(f"{server.PREFIX}/input/textarea.html")
    assert len(log) == 0


async def test_listeners_preserve_base_exception(
    context: BrowserContext, server: Server
) -> None:
    # Regression test for https://github.com/microsoft/playwright-python/issues/3360.
    page = await context.new_page()

    def fail_sync(msg: ConsoleMessage) -> None:
        pytest.fail(f"sync: {msg.text}")

    try:
        page.on("console", fail_sync)
        await page.evaluate("console.log('hi')")
        with pytest.raises(pytest.fail.Exception, match="sync: hi"):
            await page.evaluate("1 + 1")
        assert await page.evaluate("1 + 1") == 2

        page.remove_listener("console", fail_sync)

        invoked = asyncio.Event()

        async def fail_async(msg: ConsoleMessage) -> None:
            invoked.set()
            pytest.fail(f"async: {msg.text}")

        page.on("console", fail_async)
        await page.evaluate("console.log('coro')")
        await asyncio.wait_for(invoked.wait(), timeout=5)
        await asyncio.sleep(0)
        with pytest.raises(pytest.fail.Exception, match="async: coro"):
            await page.evaluate("1 + 1")
        assert await page.evaluate("1 + 1") == 2

        page.remove_listener("console", fail_async)
        seen: List[BaseException] = []
        done = asyncio.Event()

        def on_error(err: BaseException) -> None:
            seen.append(err)
            done.set()

        cast(Any, page).on("error", on_error)
        page.on("console", fail_async)
        await page.evaluate("console.log('handled')")
        await asyncio.wait_for(done.wait(), timeout=5)
        assert len(seen) == 1
        assert isinstance(seen[0], pytest.fail.Exception)
        assert "async: handled" in str(seen[0])
        assert await page.evaluate("1 + 1") == 2

        page.remove_listener("console", fail_async)
        cast(Any, page).remove_listener("error", on_error)

        async def fail_after_fulfill(route: Route) -> None:
            await route.fulfill(body="ok")
            pytest.fail("route failed")

        await page.route("**/empty.html", fail_after_fulfill)
        await page.goto(server.EMPTY_PAGE)
        with pytest.raises(pytest.fail.Exception, match="route failed"):
            await page.evaluate("1 + 1")
        await page.unroute("**/empty.html")

        with pytest.raises(pytest.fail.Exception, match="predicate: boom"):
            async with page.expect_console_message(
                lambda msg: pytest.fail(f"predicate: {msg.text}")
            ):
                await page.evaluate("console.log('boom')")
        assert await page.evaluate("1 + 1") == 2

        await page.expose_function("pwFail", lambda: pytest.fail("binding failed"))
        with pytest.raises(Error, match="binding failed"):
            await page.evaluate("window.pwFail()")
        assert await page.evaluate("1 + 1") == 2
    finally:
        await page.close()
