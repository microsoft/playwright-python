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

from typing import Any, Callable, Dict, List, Optional, cast

import pytest

from playwright.sync_api import (
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


def test_CD_037_should_work(page: Page, sync_gather: Callable) -> None:
    client = page.context.new_cdp_session(page)

    sync_gather(
        lambda: client.send("Runtime.enable"),
        lambda: client.send("Runtime.evaluate", {"expression": 'window.foo = "bar"'}),
    )
    foo = page.evaluate("() => window['foo']")
    assert foo == "bar"


def test_CD_038_should_respect_timeout_and_signal_options(
    page: Page, playwright: Playwright
) -> None:
    client = page.context.new_cdp_session(page)
    send = cast(Any, client.send)
    eval_response = send(
        "Runtime.evaluate", {"expression": "1 + 2", "returnByValue": True}, timeout=5000
    )
    assert eval_response["result"]["value"] == 3
    with pytest.raises(TimeoutError) as exc_info:
        send(
            "Runtime.evaluate",
            {"expression": "new Promise(() => {})", "awaitPromise": True},
            timeout=500,
        )
    assert "Timeout 500ms exceeded" in exc_info.value.message
    # The signal option (an AbortSignal) is JavaScript-only.


def test_CD_039_should_send_events(page: Page, server: Server) -> None:
    client = page.context.new_cdp_session(page)
    client.send("Network.enable")
    events: List[Dict] = []
    client.on("Network.requestWillBeSent", lambda event: events.append(event))
    page.goto(server.EMPTY_PAGE)
    assert len(events) == 1


def test_CD_040_should_only_accept_a_page_or_frame(page: Page) -> None:
    with pytest.raises(Error) as exc_info:
        page.context.new_cdp_session(cast(Any, page.context))
    assert "page: expected Page or Frame" in exc_info.value.message

    # non-channelable types hit validation at a different layer
    with pytest.raises(Error) as exc_info_alt:
        page.context.new_cdp_session(cast(Any, {}))
    assert "page: expected Page or Frame" in exc_info_alt.value.message


def test_CD_042_should_be_able_to_detach_session(page: Page) -> None:
    client = page.context.new_cdp_session(page)
    client.send("Runtime.enable")
    eval_response = client.send(
        "Runtime.evaluate", {"expression": "1 + 2", "returnByValue": True}
    )
    assert eval_response["result"]["value"] == 3
    client.detach()
    error: Optional[Error] = None
    try:
        client.send("Runtime.evaluate", {"expression": "3 + 1", "returnByValue": True})
    except Error as e:
        error = e
    assert error
    assert "Target page, context or browser has been closed" in error.message


def test_CD_043_should_throw_nice_errors(page: Page) -> None:
    client = page.context.new_cdp_session(page)

    def the_source_of_the_problems() -> None:
        client.send("ThisCommand.DoesNotExist")

    with pytest.raises(Error) as exc_info:
        the_source_of_the_problems()
    assert "the_source_of_the_problems" in [entry.name for entry in exc_info.traceback]
    assert "ThisCommand.DoesNotExist" in exc_info.value.message


def test_CD_044_should_work_with_main_frame(page: Page, sync_gather: Callable) -> None:
    client = page.context.new_cdp_session(page.main_frame)

    sync_gather(
        lambda: client.send("Runtime.enable"),
        lambda: client.send("Runtime.evaluate", {"expression": 'window.foo = "bar"'}),
    )
    foo = page.evaluate("() => window['foo']")
    assert foo == "bar"


def test_CD_045_should_throw_if_target_is_part_of_main(
    server: Server, page: Page
) -> None:
    page.goto(server.PREFIX + "/frames/one-frame.html")
    assert "/frames/one-frame.html" in page.frames[0].url
    assert "/frames/frame.html" in page.frames[1].url

    with pytest.raises(Error) as exc_info:
        page.context.new_cdp_session(page.frames[1])
    assert (
        "This frame does not have a separate CDP session, it is a part of the parent frame's session"
        in exc_info.value.message
    )


def test_CD_046_should_not_break_page_close(browser: Browser) -> None:
    context = browser.new_context()
    page = context.new_page()
    session = page.context.new_cdp_session(page)
    session.detach()
    page.close()
    context.close()


def test_CD_047_should_detach_when_page_closes(browser: Browser) -> None:
    context = browser.new_context()
    page = context.new_page()
    session = context.new_cdp_session(page)
    page.close()
    error: Optional[Error] = None
    try:
        session.detach()
    except Error as e:
        error = e
    assert error
    context.close()


def test_CD_048_should_reject_protocol_calls_when_page_closes(
    browser: Browser, sync_gather: Callable
) -> None:
    context = browser.new_context()
    page = context.new_page()
    session = context.new_cdp_session(page)

    def send() -> Optional[Error]:
        try:
            session.send(
                "Runtime.evaluate",
                {"expression": "new Promise(() => {})", "awaitPromise": True},
            )
        except Error as e:
            return e
        return None

    # The sync API runs the pending call and page.close() at the same time.
    error1, _ = sync_gather(send, lambda: page.close())
    assert error1
    assert TARGET_CLOSED_ERROR_MESSAGE in error1.message
    with pytest.raises(Error) as exc_info2:
        session.send(
            "Runtime.evaluate",
            {"expression": "new Promise(() => {})", "awaitPromise": True},
        )
    assert "Target page, context or browser has been closed" in exc_info2.value.message
    context.close()


def test_CD_049_should_emit_event_for_each_cdp_event(
    page: Page, server: Server
) -> None:
    client = page.context.new_cdp_session(page)
    client.send("Network.enable")
    events: List[Dict] = []
    client.on("event", lambda event: events.append(event))
    page.goto(server.EMPTY_PAGE)
    assert len(events) > 0
    request_event = next(
        (e for e in events if e["method"] == "Network.requestWillBeSent"), None
    )
    assert request_event
    assert request_event["params"]["request"]["url"] == server.EMPTY_PAGE


def test_CD_050_should_emit_close_event_when_session_is_detached(
    page: Page,
) -> None:
    client = page.context.new_cdp_session(page)
    closed_session: Optional[CDPSession] = None

    def on_close(session: CDPSession) -> None:
        nonlocal closed_session
        closed_session = session

    client.on("close", on_close)
    client.detach()
    assert closed_session == client


def test_CD_051_should_emit_close_event_when_page_closes(
    browser: Browser,
) -> None:
    context = browser.new_context()
    page = context.new_page()
    session = context.new_cdp_session(page)
    closed_sessions: List[CDPSession] = []
    session.on("close", lambda s: closed_sessions.append(s))
    page.close()
    # The sync API can not wait for a CDPSession event: the client dispatches the
    # event while it waits for other calls.
    while not closed_sessions:
        context.cookies()
    [closed_session] = closed_sessions
    assert closed_session == session
    context.close()


def test_CD_052_should_work_with_new_browser_cdp_session(
    browser: Browser,
) -> None:
    session = browser.new_browser_cdp_session()

    version = session.send("Browser.getVersion")
    assert version["userAgent"]

    got_event = False

    def on_target_created(event: Dict) -> None:
        nonlocal got_event
        got_event = True

    session.on("Target.targetCreated", on_target_created)
    session.send("Target.setDiscoverTargets", {"discover": True})
    page = browser.new_page()
    assert got_event is True
    page.close()

    session.detach()
