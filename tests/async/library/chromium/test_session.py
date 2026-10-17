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

"""Port of tests/library/chromium/session.spec.ts."""

import asyncio
from typing import Any, Dict, List, Optional, cast

import pytest

from playwright.async_api import (
    Browser,
    CDPSession,
    Error,
    Page,
    Playwright,
    TimeoutError,
)
from tests.server import Server
from tests.utils import TARGET_CLOSED_ERROR_MESSAGE

pytestmark = pytest.mark.only_browser("chromium")


async def test_CD_037_should_work(page: Page) -> None:
    client = await page.context.new_cdp_session(page)

    await asyncio.gather(
        client.send("Runtime.enable"),
        client.send("Runtime.evaluate", {"expression": 'window.foo = "bar"'}),
    )
    foo = await page.evaluate("() => window['foo']")
    assert foo == "bar"


@pytest.mark.xfail(
    reason="python: CDPSession.send() has no timeout option",
    raises=TypeError,
    strict=True,
)
async def test_CD_038_should_respect_timeout_and_signal_options(
    page: Page, playwright: Playwright
) -> None:
    client = await page.context.new_cdp_session(page)
    send = cast(Any, client.send)
    eval_response = await send(
        "Runtime.evaluate", {"expression": "1 + 2", "returnByValue": True}, timeout=5000
    )
    assert eval_response["result"]["value"] == 3
    with pytest.raises(TimeoutError) as exc_info:
        await send(
            "Runtime.evaluate",
            {"expression": "new Promise(() => {})", "awaitPromise": True},
            timeout=500,
        )
    assert "Timeout 500ms exceeded" in exc_info.value.message
    # The signal option (an AbortSignal) is JavaScript-only.


async def test_CD_039_should_send_events(page: Page, server: Server) -> None:
    client = await page.context.new_cdp_session(page)
    await client.send("Network.enable")
    events: List[Dict] = []
    client.on("Network.requestWillBeSent", lambda event: events.append(event))
    await page.goto(server.EMPTY_PAGE)
    assert len(events) == 1


async def test_CD_040_should_only_accept_a_page_or_frame(page: Page) -> None:
    with pytest.raises(Error) as exc_info:
        await page.context.new_cdp_session(cast(Any, page.context))
    assert "page: expected Page or Frame" in exc_info.value.message

    # non-channelable types hit validation at a different layer
    with pytest.raises(Error) as exc_info_alt:
        await page.context.new_cdp_session(cast(Any, {}))
    assert "page: expected Page or Frame" in exc_info_alt.value.message


async def test_CD_042_should_be_able_to_detach_session(page: Page) -> None:
    client = await page.context.new_cdp_session(page)
    await client.send("Runtime.enable")
    eval_response = await client.send(
        "Runtime.evaluate", {"expression": "1 + 2", "returnByValue": True}
    )
    assert eval_response["result"]["value"] == 3
    await client.detach()
    error: Optional[Error] = None
    try:
        await client.send(
            "Runtime.evaluate", {"expression": "3 + 1", "returnByValue": True}
        )
    except Error as e:
        error = e
    assert error
    assert "Target page, context or browser has been closed" in error.message


async def test_CD_043_should_throw_nice_errors(page: Page) -> None:
    client = await page.context.new_cdp_session(page)

    async def the_source_of_the_problems() -> None:
        await client.send("ThisCommand.DoesNotExist")

    with pytest.raises(Error) as exc_info:
        await the_source_of_the_problems()
    assert "the_source_of_the_problems" in [entry.name for entry in exc_info.traceback]
    assert "ThisCommand.DoesNotExist" in exc_info.value.message


async def test_CD_044_should_work_with_main_frame(page: Page) -> None:
    client = await page.context.new_cdp_session(page.main_frame)

    await asyncio.gather(
        client.send("Runtime.enable"),
        client.send("Runtime.evaluate", {"expression": 'window.foo = "bar"'}),
    )
    foo = await page.evaluate("() => window['foo']")
    assert foo == "bar"


async def test_CD_045_should_throw_if_target_is_part_of_main(
    server: Server, page: Page
) -> None:
    await page.goto(server.PREFIX + "/frames/one-frame.html")
    assert "/frames/one-frame.html" in page.frames[0].url
    assert "/frames/frame.html" in page.frames[1].url

    with pytest.raises(Error) as exc_info:
        await page.context.new_cdp_session(page.frames[1])
    assert (
        "This frame does not have a separate CDP session, it is a part of the parent frame's session"
        in exc_info.value.message
    )


async def test_CD_046_should_not_break_page_close(browser: Browser) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    session = await page.context.new_cdp_session(page)
    await session.detach()
    await page.close()
    await context.close()


async def test_CD_047_should_detach_when_page_closes(browser: Browser) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    session = await context.new_cdp_session(page)
    await page.close()
    error: Optional[Error] = None
    try:
        await session.detach()
    except Error as e:
        error = e
    assert error
    await context.close()


async def test_CD_048_should_reject_protocol_calls_when_page_closes(
    browser: Browser,
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    session = await context.new_cdp_session(page)
    task = asyncio.create_task(
        session.send(
            "Runtime.evaluate",
            {"expression": "new Promise(() => {})", "awaitPromise": True},
        )
    )
    # Let the command reach the driver before the page closes.
    await asyncio.sleep(0)
    await page.close()
    with pytest.raises(Error) as exc_info1:
        await task
    assert TARGET_CLOSED_ERROR_MESSAGE in exc_info1.value.message
    with pytest.raises(Error) as exc_info2:
        await session.send(
            "Runtime.evaluate",
            {"expression": "new Promise(() => {})", "awaitPromise": True},
        )
    assert "Target page, context or browser has been closed" in exc_info2.value.message
    await context.close()


async def test_CD_049_should_emit_event_for_each_cdp_event(
    page: Page, server: Server
) -> None:
    client = await page.context.new_cdp_session(page)
    await client.send("Network.enable")
    events: List[Dict] = []
    client.on("event", lambda event: events.append(event))
    await page.goto(server.EMPTY_PAGE)
    assert len(events) > 0
    request_event = next(
        (e for e in events if e["method"] == "Network.requestWillBeSent"), None
    )
    assert request_event
    assert request_event["params"]["request"]["url"] == server.EMPTY_PAGE


async def test_CD_050_should_emit_close_event_when_session_is_detached(
    page: Page,
) -> None:
    client = await page.context.new_cdp_session(page)
    closed_session: Optional[CDPSession] = None

    def on_close(session: CDPSession) -> None:
        nonlocal closed_session
        closed_session = session

    client.on("close", on_close)
    await client.detach()
    assert closed_session == client


async def test_CD_051_should_emit_close_event_when_page_closes(
    browser: Browser,
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    session = await context.new_cdp_session(page)
    close_future: "asyncio.Future[CDPSession]" = asyncio.Future()
    session.on("close", lambda s: close_future.set_result(s))
    await page.close()
    closed_session = await close_future
    assert closed_session == session
    await context.close()


async def test_CD_052_should_work_with_new_browser_cdp_session(
    browser: Browser,
) -> None:
    session = await browser.new_browser_cdp_session()

    version = await session.send("Browser.getVersion")
    assert version["userAgent"]

    got_event = False

    def on_target_created(event: Dict) -> None:
        nonlocal got_event
        got_event = True

    session.on("Target.targetCreated", on_target_created)
    await session.send("Target.setDiscoverTargets", {"discover": True})
    page = await browser.new_page()
    assert got_event is True
    await page.close()

    await session.detach()
