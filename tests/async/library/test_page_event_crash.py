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

"""Port of tests/library/page-event-crash.spec.ts."""


import asyncio
import re
import sys
from pathlib import Path
from typing import Any, AsyncGenerator, Awaitable, Callable, List, Optional

import pytest

from playwright.async_api import Error, Page, expect
from tests.server import Server


def host_platform() -> str:
    """The start of hostPlatform (packages/playwright-core/src/server/utils/hostPlatform.ts) on Linux."""
    if not sys.platform.startswith("linux"):
        return sys.platform
    try:
        os_release = Path("/etc/os-release").read_text()
    except OSError:
        return "linux"
    fields = dict(re.findall(r'^(\w+)="?([^"\n]*)"?$', os_release, re.MULTILINE))
    if fields.get("ID") in ("ubuntu", "debian"):
        return fields["ID"] + fields.get("VERSION_ID", "")
    return "linux"


async def error_of(awaitable: Awaitable[Any]) -> Any:
    """Like `promise.catch(e => e)`: returns the result or the error."""
    try:
        return await awaitable
    except Exception as e:
        return e


@pytest.fixture(autouse=True)
def before_each(browser_name: str, browser_channel: Optional[str]) -> None:
    if browser_channel == "webkit-wsl":
        pytest.skip("WebKit on WSL is even slower than above ^^ - skipping for now")
    if browser_name == "chromium" and host_platform().startswith("ubuntu24.04"):
        pytest.skip("never dispatches the crash event")
    if browser_name == "webkit" and host_platform().startswith("debian13"):
        pytest.skip("never dispatches the crash event")
    if browser_name != "chromium":
        pytest.skip(
            "crashes the page with toImpl(page) (Page.crash), the Python client can not reach server internals"
        )


@pytest.fixture
async def crash(
    page: Page, browser_name: str
) -> AsyncGenerator[Callable[[], None], None]:
    tasks: List["asyncio.Task[Any]"] = []

    def do_crash() -> None:
        if browser_name == "chromium":
            tasks.append(asyncio.create_task(error_of(page.goto("chrome://crash"))))

    yield do_crash
    for task in tasks:
        await task


async def test_ER_014_should_emit_crash_event_when_page_crashes(
    page: Page, crash: Callable[[], None]
) -> None:
    await page.set_content("<div>This page should crash</div>")
    async with page.expect_event("crash") as crash_info:
        crash()
    assert await crash_info.value == page


async def test_ER_015_should_throw_on_any_action_after_page_crashes(
    page: Page, crash: Callable[[], None], server: Server, browser_name: str
) -> None:
    await page.set_content("<div>This page should crash</div>")
    async with page.expect_event("crash"):
        crash()

    def expect_crash_error(error: Optional[Exception]) -> None:
        assert error, "action should reject after crash"
        assert isinstance(error, Error)
        # In Firefox, crashed page is sometimes "closed".
        if browser_name == "firefox":
            assert (
                "has been closed" in error.message or "crashed" in error.message
            ), error.message
        else:
            assert "crashed" in error.message

    async def error_or_none(awaitable: Awaitable[Any]) -> Optional[Exception]:
        try:
            await awaitable
            return None
        except Exception as e:
            return e

    expect_crash_error(await error_or_none(page.evaluate("() => {}")))
    expect_crash_error(await error_or_none(page.goto(server.EMPTY_PAGE)))
    expect_crash_error(await error_or_none(page.reload()))


async def test_ER_016_expect_should_not_hang_when_page_crashed(
    page: Page, crash: Callable[[], None]
) -> None:
    expect_task = asyncio.create_task(expect(page.get_by_text("child")).to_be_visible())
    crash()
    with pytest.raises((Error, AssertionError)):
        await expect_task


async def test_ER_017_should_cancel_wait_for_event_when_page_crashes(
    page: Page, crash: Callable[[], None]
) -> None:
    await page.set_content("<div>This page should crash</div>")
    with pytest.raises(Error) as exc_info:
        async with page.expect_event("response"):
            crash()
    assert "Page crashed" in exc_info.value.message


async def test_ER_018_should_cancel_navigation_when_page_crashes(
    server: Server, page: Page, crash: Callable[[], None]
) -> None:
    await page.set_content("<div>This page should crash</div>")
    server.set_route("/one-style.css", lambda request: None)
    async with page.expect_navigation(wait_until="domcontentloaded"):
        goto_task = asyncio.create_task(
            error_of(page.goto(server.PREFIX + "/one-style.html"))
        )
    crash()
    error = await goto_task
    assert isinstance(error, Error)
    assert "Page.goto: Page crashed" in error.message


async def test_ER_019_should_be_able_to_close_context_when_page_crashes(
    page: Page, crash: Callable[[], None]
) -> None:
    await page.set_content("<div>This page should crash</div>")
    async with page.expect_event("crash"):
        crash()
    await page.context.close()


async def test_ER_020_should_be_able_to_close_page_after_crash(
    page: Page, crash: Callable[[], None]
) -> None:
    await page.set_content("<div>This page should crash</div>")
    async with page.expect_event("crash"):
        crash()
    # Give the browser a chance to erroneously "close" the crashed page.
    await asyncio.sleep(3)
    assert page.is_closed() is False
    assert page.context.pages == [page]
    await page.close()
    assert page.is_closed() is True
    assert page.context.pages == []


async def test_ER_021_should_reject_in_flight_worker_evaluate_when_page_crashes(
    page: Page, crash: Callable[[], None], server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_worker() as worker_info:
        await page.evaluate(
            """() => new Worker(URL.createObjectURL(
        new Blob(['self.onmessage = () => {}'], { type: 'application/javascript' })))"""
        )
    worker = await worker_info.value
    async with worker.expect_event("close"):
        # never resolves in-worker
        eval_task = asyncio.create_task(
            error_of(worker.evaluate("() => new Promise(() => {})"))
        )
        crash()
        error = await eval_task
        assert isinstance(error, Error)
        # Chromium may detach the worker before it reports the crash.
        assert re.search(
            r"Page crashed|Target page, context or browser has been closed",
            error.message,
        )
    assert page.workers == []
