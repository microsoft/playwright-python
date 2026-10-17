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

"""Port of tests/library/web-socket.spec.ts."""

import asyncio
from typing import Any, Callable, List, Optional, TypeVar, Union

import pytest

from playwright.sync_api import Error, Page, WebSocket
from tests.helpers import web_socket_server
from tests.server import Server, WebSocketProtocol
from tests.utils import TARGET_CLOSED_ERROR_MESSAGE

T = TypeVar("T")


def wait_for(page: Page, future: "asyncio.Future[T]") -> T:
    """Like `await future`: runs the Playwright loop until the future is done."""
    while not future.done():
        page.wait_for_timeout(10)
    return future.result()


def wait_for_web_socket_frame(page: Page, action: Callable[[], Any]) -> WebSocket:
    """Port of Promise.all([page.waitForEvent('websocket').then(ws => ws.waitForEvent('framereceived')), action()]).

    Like the .then() upstream, it listens to the frames of the WebSocket as the page
    reports it, so it does not miss a frame that arrives right after.
    """
    frame_received: "asyncio.Future[WebSocket]" = asyncio.Future()

    def on_web_socket(ws: WebSocket) -> None:
        ws.once("framereceived", lambda _: frame_received.set_result(ws))

    page.once("websocket", on_web_socket)
    action()
    return wait_for(page, frame_received)


def test_WS_001_should_work_smoke(page: Page, server: Server) -> None:
    server.send_on_web_socket_connection(b"incoming")
    value = page.evaluate(
        """host => {
            let cb;
            const result = new Promise(f => cb = f);
            const ws = new WebSocket('ws://' + host + '/ws');
            ws.addEventListener('message', data => { ws.close(); cb(data.data); });
            return result;
        }""",
        server.HOST,
    )
    assert value == "incoming"


def test_WS_002_should_emit_close_events(page: Page, server: Server) -> None:
    socket_closed: "asyncio.Future[None]" = asyncio.Future()
    log: List[str] = []
    web_socket: Optional[WebSocket] = None

    def on_web_socket(ws: WebSocket) -> None:
        nonlocal web_socket
        log.append(f"open<{ws.url}>")
        web_socket = ws

        def on_close(_: WebSocket) -> None:
            log.append("close")
            socket_closed.set_result(None)

        ws.on("close", on_close)

    page.on("websocket", on_web_socket)
    page.evaluate(
        """host => {
            const ws = new WebSocket('ws://' + host + '/ws');
            ws.addEventListener('open', () => ws.close());
        }""",
        server.HOST,
    )
    wait_for(page, socket_closed)
    assert ":".join(log) == f"open<ws://{server.HOST}/ws>:close"
    assert web_socket
    assert web_socket.is_closed()


def test_WS_003_should_emit_frame_events(page: Page, server: Server) -> None:
    def on_connection(ws: WebSocketProtocol) -> None:
        ws.events.on(
            "message", lambda payload, is_binary: ws.sendMessage(b"incoming", False)
        )

    server.once_web_socket_connection(on_connection)
    socket_closed: "asyncio.Future[None]" = asyncio.Future()
    log: List[str] = []

    def on_web_socket(ws: WebSocket) -> None:
        log.append("open")
        ws.on("framesent", lambda payload: log.append(f"sent<{payload!s}>"))
        ws.on("framereceived", lambda payload: log.append(f"received<{payload!s}>"))

        def on_close(_: WebSocket) -> None:
            log.append("close")
            socket_closed.set_result(None)

        ws.on("close", on_close)

    page.on("websocket", on_web_socket)
    page.evaluate(
        """host => {
            const ws = new WebSocket('ws://' + host + '/ws');
            ws.addEventListener('open', () => ws.send('outgoing'));
            ws.addEventListener('message', () => { ws.close(); });
            window.ws = ws;
        }""",
        server.HOST,
    )
    wait_for(page, socket_closed)
    assert log == ["open", "sent<outgoing>", "received<incoming>", "close"]


def test_WS_004_should_filter_out_the_close_events_when_the_server_closes_with_a_message(
    page: Page, server: Server
) -> None:
    def on_connection(ws: WebSocketProtocol) -> None:
        ws.sendMessage(b"incoming", False)
        ws.events.on(
            "message",
            lambda payload, is_binary: web_socket_server.close_on_reactor_thread(
                ws, 1003, "closed by Playwright test-server"
            ),
        )

    server.once_web_socket_connection(on_connection)
    socket_closed: "asyncio.Future[None]" = asyncio.Future()
    log: List[str] = []

    def on_web_socket(ws: WebSocket) -> None:
        log.append("open")
        ws.on("framesent", lambda payload: log.append(f"sent<{payload!s}>"))
        ws.on("framereceived", lambda payload: log.append(f"received<{payload!s}>"))

        def on_close(_: WebSocket) -> None:
            log.append("close")
            socket_closed.set_result(None)

        ws.on("close", on_close)

    page.on("websocket", on_web_socket)
    page.evaluate(
        """host => {
            const ws = new WebSocket('ws://' + host + '/ws');
            ws.addEventListener('message', () => ws.send('outgoing'));
            window.ws = ws;
        }""",
        server.HOST,
    )
    wait_for(page, socket_closed)
    assert log == ["open", "received<incoming>", "sent<outgoing>", "close"]


def test_WS_005_should_pass_self_as_argument_to_close_event(
    page: Page, server: Server
) -> None:
    socket_closed: "asyncio.Future[WebSocket]" = asyncio.Future()
    web_socket: Optional[WebSocket] = None

    def on_web_socket(ws: WebSocket) -> None:
        nonlocal web_socket
        web_socket = ws
        ws.on("close", lambda arg: socket_closed.set_result(arg))

    page.on("websocket", on_web_socket)
    page.evaluate(
        """host => {
            const ws = new WebSocket('ws://' + host + '/ws');
            ws.addEventListener('open', () => ws.close());
        }""",
        server.HOST,
    )
    event_arg = wait_for(page, socket_closed)
    assert event_arg is web_socket


def test_WS_006_should_emit_binary_frame_events(page: Page, server: Server) -> None:
    done: "asyncio.Future[None]" = asyncio.Future()
    sent: List[Union[str, bytes]] = []

    def on_web_socket(ws: WebSocket) -> None:
        ws.on("close", lambda _: done.set_result(None))
        ws.on("framesent", lambda payload: sent.append(payload))

    page.on("websocket", on_web_socket)
    page.evaluate(
        """host => {
            const ws = new WebSocket('ws://' + host + '/ws');
            ws.addEventListener('open', () => {
                const binary = new Uint8Array(5);
                for (let i = 0; i < 5; ++i)
                    binary[i] = i;
                ws.send('text');
                ws.send(binary);
                ws.close();
            });
        }""",
        server.HOST,
    )
    wait_for(page, done)
    assert sent[0] == "text"
    for i in range(5):
        assert sent[1][i] == i


def test_WS_007_should_emit_error(
    page: Page, server: Server, browser_channel: Optional[str]
) -> None:
    result: "asyncio.Future[str]" = asyncio.Future()

    def on_socket_error(error: str) -> None:
        if not result.done():
            result.set_result(error)

    page.on("websocket", lambda ws: ws.on("socketerror", on_socket_error))
    page.evaluate(
        """host => {
            new WebSocket('ws://' + host + '/bogus-ws');
        }""",
        server.HOST,
    )
    message = wait_for(page, result)
    # Upstream's test server answers 400 to an upgrade request for an unknown path,
    # the Python test server answers 404.
    assert ("" if browser_channel and "msedge" in browser_channel else ": 404") in (
        message
    )


def test_WS_008_should_not_have_stray_error_events(page: Page, server: Server) -> None:
    server.send_on_web_socket_connection(b"incoming")
    error: List[str] = []

    def on_web_socket(ws: WebSocket) -> None:
        ws.on("socketerror", lambda e: error.append(e))

    page.on("websocket", on_web_socket)
    wait_for_web_socket_frame(
        page,
        lambda: page.evaluate(
            """host => {
                window.ws = new WebSocket('ws://' + host + '/ws');
            }""",
            server.HOST,
        ),
    )
    page.evaluate("window.ws.close()")
    assert not error


def test_WS_009_should_reject_wait_for_event_on_socket_close(
    page: Page, server: Server
) -> None:
    server.send_on_web_socket_connection(b"incoming")
    ws = wait_for_web_socket_frame(
        page,
        lambda: page.evaluate(
            """host => {
                window.ws = new WebSocket('ws://' + host + '/ws');
            }""",
            server.HOST,
        ),
    )
    with pytest.raises(Error) as exc_info:
        with ws.expect_event("framesent"):
            page.evaluate("window.ws.close()")
    assert "Socket closed" in exc_info.value.message


def test_WS_010_should_reject_wait_for_event_on_page_close(
    page: Page, server: Server
) -> None:
    server.send_on_web_socket_connection(b"incoming")
    ws = wait_for_web_socket_frame(
        page,
        lambda: page.evaluate(
            """host => {
                window.ws = new WebSocket('ws://' + host + '/ws');
            }""",
            server.HOST,
        ),
    )
    with pytest.raises(Error) as exc_info:
        with ws.expect_event("framesent"):
            page.close()
    assert TARGET_CLOSED_ERROR_MESSAGE in exc_info.value.message


def test_WS_011_should_not_tear_down_the_page_when_a_web_socket_is_opened_inside_a_worker(
    page: Page, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/41742
    server.send_on_web_socket_connection(b"incoming")
    page.goto(server.EMPTY_PAGE)
    received = page.evaluate(
        """host => {
            const code = `
              const ws = new WebSocket(${JSON.stringify('ws://' + host + '/ws')});
              ws.addEventListener('message', event => self.postMessage(event.data));
            `;
            const worker = new Worker(URL.createObjectURL(new Blob([code], { type: 'text/javascript' })));
            return new Promise(resolve => worker.addEventListener('message', event => resolve(event.data)));
        }""",
        server.HOST,
    )
    assert received == "incoming"
    # Opening a `WebSocket` inside a worker must not tear down the page session.
    assert page.evaluate("() => 1 + 1") == 2


def test_WS_012_should_turn_off_when_offline(page: Page, server: Server) -> None:
    pytest.skip("fixme")

    socket_promise = server.wait_for_web_socket()
    ws_handle = page.evaluate_handle(
        """async address => {
            const ws = new WebSocket(`ws://${address}/ws`);
            await new Promise(x => ws.onopen = x);
            return ws;
        }""",
        server.HOST,
    )
    socket = wait_for(page, socket_promise)
    failures: List[str] = []
    socket.events.on(
        "message",
        lambda payload, is_binary: failures.append(web_socket_server.to_text(payload)),
    )
    page.context.set_offline(True)
    ws_handle.evaluate("ws => ws.send('if this arrives it failed')")
    result = ws_handle.evaluate(
        """async ws => {
            if (ws.readyState !== WebSocket.CLOSED)
                await new Promise(x => ws.onclose = x);
            return 'successfully closed';
        }"""
    )
    assert failures == []
    assert result == "successfully closed"


def test_WS_013_should_send_extra_http_headers_on_web_socket_handshake(
    page: Page, server: Server, browser_name: str, browser_major_version: int
) -> None:
    # https://github.com/microsoft/playwright/issues/28948
    if browser_name == "chromium" and browser_major_version < 151:
        pytest.skip(
            "fixme: Chromium before 151 does not send extra HTTP headers on WebSocket handshake"
        )

    page.set_extra_http_headers({"foo": "bar"})
    page.goto(server.EMPTY_PAGE)
    request_promise = server.wait_for_web_socket_connection_request()
    page.evaluate(
        "host => { new WebSocket(`ws://${host}/ws`); }",
        server.HOST,
    )
    request = wait_for(page, request_promise)
    assert request.headers["foo"] == "bar"


def test_WS_014_should_send_extra_http_headers_on_web_socket_handshake_from_a_worker(
    page: Page, server: Server, browser_name: str, browser_major_version: int
) -> None:
    # https://github.com/microsoft/playwright/issues/28948
    if browser_name == "chromium" and browser_major_version < 151:
        pytest.skip(
            "fixme: Chromium before 151 does not send extra HTTP headers on WebSocket handshake"
        )

    page.set_extra_http_headers({"foo": "bar"})
    page.goto(server.EMPTY_PAGE)
    request_promise = server.wait_for_web_socket_connection_request()
    page.evaluate(
        """host => {
            const code = `new WebSocket(${JSON.stringify('ws://' + host + '/ws')});`;
            new Worker(URL.createObjectURL(new Blob([code], { type: 'text/javascript' })));
        }""",
        server.HOST,
    )
    request = wait_for(page, request_promise)
    assert request.headers["foo"] == "bar"
