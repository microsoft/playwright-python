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

"""Port of tests/library/har-websocket.spec.ts."""

import asyncio
import base64
import json
import re
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Dict, List, Literal, Optional, TypeVar, Union

import pytest

from playwright.sync_api import (
    BrowserContext,
    Page,
    WebSocket,
    WebSocketRoute,
    sync_playwright,
)
from tests.helpers.har import (
    har_time_to_ms,
    message_size,
    parse_har,
    read_har_log,
    request_headers_size,
    response_headers_size,
)
from tests.server import Server, WebSocketProtocol, reactor

# Browser-reported message times are derived from a wall-clock baseline plus
# monotonic timestamps in the browser process, so they can drift by a few
# milliseconds relative to the clock of the test process.
CLOCK_SKEW_MS = 100

T = TypeVar("T")


def wait_for(page: Page, future: "asyncio.Future[T]") -> T:
    """Like `await future`: runs the Playwright loop until the future is done."""
    while not future.done():
        page.wait_for_timeout(10)
    return future.result()


def now_ms() -> float:
    return time.time() * 1000


class HarPage:
    """The object that pageWithHar() returns upstream."""

    def __init__(self, page: Page, context: BrowserContext, har_path: Path) -> None:
        self.page = page
        self.context = context
        self.har_path = har_path

    def get_log(self) -> Dict[str, Any]:
        self.context.close()
        return read_har_log(self.har_path)

    def get_zip(self) -> Dict[str, bytes]:
        self.context.close()
        return parse_har(self.har_path)


PageWithHar = Callable[..., HarPage]


@pytest.fixture
def page_with_har(
    context_factory: Callable[..., BrowserContext], tmp_path: Path
) -> PageWithHar:
    """Port of pageWithHar() in the upstream file."""

    def create(
        output_path: Optional[str] = None,
        content: Optional[Literal["attach", "embed", "omit"]] = None,
        omit_content: Optional[bool] = None,
        mode: Optional[Literal["full", "minimal"]] = None,
    ) -> HarPage:
        har_path = tmp_path / (output_path or "test.har")
        context = context_factory(
            record_har_path=har_path,
            record_har_content=content,
            record_har_omit_content=omit_content,
            record_har_mode=mode,
            ignore_https_errors=True,
        )
        page = context.new_page()
        return HarPage(page, context, har_path)

    return create


def close_on_message(ws: WebSocketProtocol) -> None:
    ws.events.on("message", lambda payload, is_binary: ws.sendClose())


def find_entry(log: Dict[str, Any], url: str) -> Dict[str, Any]:
    return next(e for e in log["entries"] if e["request"]["url"] == url)


def message_data(message: Dict[str, Any]) -> Union[str, List[int]]:
    if message["opcode"] == 1:
        return message["data"]
    return list(base64.b64decode(message["data"]))


def to_text(message: Union[str, bytes]) -> str:
    """Like message.toString() in Node.js."""
    return message.decode() if isinstance(message, bytes) else message


def read_jsonl(data: bytes) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in data.decode().split("\n") if line]


def test_HA_101_should_only_have_one_websocket_entry(
    page_with_har: PageWithHar, server: Server
) -> None:
    server.once_web_socket_connection(close_on_message)
    har = page_with_har()
    har.page.goto(server.EMPTY_PAGE)
    ws_url = f"ws://{server.HOST}/ws"
    har.page.evaluate(
        """url => new Promise(resolve => {
            const ws = new WebSocket(url);
            ws.addEventListener('open', () => ws.send('ping'));
            ws.addEventListener('close', () => resolve());
        })""",
        ws_url,
    )
    log = har.get_log()
    ws_entries = [
        e
        for e in log["entries"]
        if e["request"]["url"].endswith(f"://{server.HOST}/ws")
    ]
    assert len(ws_entries) == 1

    ws_entry = ws_entries[0]
    assert ws_entry["_resourceType"] == "websocket"


def test_HA_102_should_include_websocket_handshake_headers_and_status(
    page_with_har: PageWithHar, server: Server
) -> None:
    server.once_web_socket_connection(close_on_message)

    har = page_with_har()
    har.page.goto(server.EMPTY_PAGE)

    before_ms = now_ms()
    ws_url = f"ws://{server.HOST}/ws"
    har.page.evaluate(
        """url => new Promise(resolve => {
            const ws = new WebSocket(url);
            ws.addEventListener('open', () => ws.send('ping'));
            ws.addEventListener('close', () => resolve());
        })""",
        ws_url,
    )
    log = har.get_log()
    after_ms = now_ms()

    ws_entry = find_entry(log, ws_url)
    assert ws_entry["_resourceType"] == "websocket"
    assert ws_entry["request"]["headersSize"] == request_headers_size(
        ws_entry["request"]["headers"]
    )
    assert ws_entry["response"]["status"] == 101
    assert ws_entry["response"]["statusText"] == "Switching Protocols"
    assert ws_entry["response"]["headersSize"] == response_headers_size(
        ws_entry["response"]["headers"]
    )

    wall_time_ms = har_time_to_ms(ws_entry["startedDateTime"])
    assert wall_time_ms >= before_ms - CLOCK_SKEW_MS
    assert wall_time_ms <= after_ms + CLOCK_SKEW_MS

    request_header_names = [h["name"].lower() for h in ws_entry["request"]["headers"]]
    assert "upgrade" in request_header_names
    assert "connection" in request_header_names
    assert "sec-websocket-key" in request_header_names
    assert "sec-websocket-version" in request_header_names
    upgrade_header = next(
        h for h in ws_entry["request"]["headers"] if h["name"].lower() == "upgrade"
    )
    assert upgrade_header["value"].lower() == "websocket"

    response_header_names = [h["name"].lower() for h in ws_entry["response"]["headers"]]
    assert "upgrade" in response_header_names
    assert "connection" in response_header_names
    assert "sec-websocket-accept" in response_header_names


def check_web_socket_messages(
    page_with_har: PageWithHar,
    server: Server,
    content: Literal["attach", "embed", "omit"],
    channel: Optional[str] = None,
) -> None:
    """Port of testWebSocketMessages() in the upstream file."""
    incoming_text = ["x" * 125, "x" * 126, "x" * 2**16]
    incoming_binary = [[0x01] * 125, [0x01] * 126, [0x01] * 2**16]
    outgoing_text = ["y" * 125, "y" * 126, "y" * 2**16]
    outgoing_binary = [[0x02] * 125, [0x02] * 126, [0x02] * 2**16]
    incoming_count = len(incoming_text) + len(incoming_binary)
    delay_ms = 100

    def on_connection(ws: WebSocketProtocol) -> None:
        # Send each text, then wait; wait, then send each binary.
        delay = 0
        for text in incoming_text:
            reactor.callLater(delay / 1000, ws.sendMessage, text.encode(), False)
            delay += delay_ms
        for binary in incoming_binary:
            delay += delay_ms
            reactor.callLater(delay / 1000, ws.sendMessage, bytes(binary), True)

    server.once_web_socket_connection(on_connection)

    output_path = None if content == "embed" else "test.har.zip"
    har = page_with_har(content=content, output_path=output_path)
    har.page.goto(server.EMPTY_PAGE)

    before_ms = now_ms()
    ws_url = f"ws://{server.HOST}/ws"
    har.page.evaluate(
        """({ url, incomingCount, outgoingText, outgoingBinary, delayMs }) => new Promise(resolve => {
            let count = 0;
            const ws = new WebSocket(url);
            ws.addEventListener('message', async () => {
                if (++count < incomingCount)
                    return;
                for (const text of outgoingText) {
                    ws.send(text);
                    await new Promise(resolve => window.builtins.setTimeout(resolve, delayMs));
                }
                for (const binary of outgoingBinary) {
                    await new Promise(resolve => window.builtins.setTimeout(resolve, delayMs));
                    ws.send(new Uint8Array(binary));
                }
                ws.close();
            });
            ws.addEventListener('close', () => resolve());
        })""",
        {
            "url": ws_url,
            "incomingCount": incoming_count,
            "outgoingText": outgoing_text,
            "outgoingBinary": outgoing_binary,
            "delayMs": delay_ms,
        },
    )
    after_ms = now_ms()

    zip: Dict[str, bytes] = {}
    if output_path:
        zip = har.get_zip()
        log = json.loads(zip["har.har"])["log"]
    else:
        log = har.get_log()
    ws_entry = find_entry(log, ws_url)
    assert ws_entry["response"]["_transferSize"] == response_headers_size(
        ws_entry["response"]["headers"]
    ) + sum(message_size(m) for m in incoming_text) + sum(
        message_size(m) for m in incoming_binary
    )
    assert ws_entry["time"] <= after_ms - before_ms

    if content == "omit":
        assert "_file" not in ws_entry["response"]["content"]
        return

    messages: List[Dict[str, Any]]
    if content == "attach":
        assert "_webSocketMessages" not in ws_entry
        file = ws_entry["response"]["content"]["_file"]
        assert re.search(r"^[0-9a-f]+\.jsonl$", file)
        messages = read_jsonl(zip[file])
    else:
        messages = ws_entry["_webSocketMessages"]
    assert [
        {"type": m["type"], "opcode": m["opcode"], "data": message_data(m)}
        for m in messages
    ] == [
        *[{"type": "receive", "opcode": 1, "data": m} for m in incoming_text],
        *[{"type": "receive", "opcode": 2, "data": m} for m in incoming_binary],
        *[{"type": "send", "opcode": 1, "data": m} for m in outgoing_text],
        *[{"type": "send", "opcode": 2, "data": m} for m in outgoing_binary],
    ]
    # The WSL VM clock drifts relative to the Windows host clock, so the browser-reported
    # message times cannot be compared against the host wall clock.
    if channel != "webkit-wsl":
        for m in messages:
            assert m["time"] >= before_ms - CLOCK_SKEW_MS
            assert m["time"] <= after_ms + CLOCK_SKEW_MS
    assert messages[0]["time"] <= messages[1]["time"]
    assert ws_entry["time"] >= messages[-1]["time"] - messages[0]["time"]


def test_HA_103_should_embed_websocket_messages(
    page_with_har: PageWithHar, server: Server, browser_channel: Optional[str]
) -> None:
    check_web_socket_messages(page_with_har, server, "embed", browser_channel)


def test_HA_104_should_attach_websocket_messages(
    page_with_har: PageWithHar, server: Server, browser_channel: Optional[str]
) -> None:
    check_web_socket_messages(page_with_har, server, "attach", browser_channel)


def test_HA_105_should_attach_websocket_messages_for_a_still_open_websocket_after_stopping(
    page_with_har: PageWithHar,
    server: Server,
    browser_channel: Optional[str],
    sync_gather: Callable[..., List[Any]],
) -> None:
    incoming_text = "incoming"
    incoming_binary = [0x01, 0x02, 0x03, 0x04]
    outgoing_text = "outgoing"
    outgoing_binary = [0x05, 0x06, 0x07, 0x08]

    def on_connection(ws: WebSocketProtocol) -> None:
        count = 0

        def on_message(payload: bytes, is_binary: bool) -> None:
            nonlocal count
            count += 1
            if count < 2:
                ws.sendMessage(incoming_text.encode(), False)
            else:
                ws.sendMessage(bytes(incoming_binary), True)

        ws.events.on("message", on_message)

    server.once_web_socket_connection(on_connection)

    har = page_with_har(content="attach", output_path="test.har.zip")
    har.page.goto(server.EMPTY_PAGE)

    before_ms = now_ms()
    ws_url = f"ws://{server.HOST}/ws"

    def wait_for_frames() -> WebSocket:
        ws = har.page.wait_for_event("websocket")
        # Wait for all frames so the HAR tracer has observed them before the context is closed.
        ws.wait_for_event("framesent")
        ws.wait_for_event("framereceived")
        ws.wait_for_event("framesent")
        ws.wait_for_event("framereceived")
        return ws

    [ws, _] = sync_gather(
        wait_for_frames,
        lambda: har.page.evaluate(
            """({ url, outgoingText, outgoingBinary }) => {
                const ws = new WebSocket(url);
                window.ws = ws;
                let count = 0;
                ws.addEventListener('open', () => ws.send(outgoingText));
                ws.addEventListener('message', () => {
                    if (++count < 2)
                        ws.send(new Uint8Array(outgoingBinary));
                });
            }""",
            {
                "url": ws_url,
                "outgoingText": outgoing_text,
                "outgoingBinary": outgoing_binary,
            },
        ),
    )
    after_ms = now_ms()

    # Do not close the WebSocket on the page side. Closing the context should still flush messages.
    assert har.page.evaluate("() => window.ws.readyState") == 1  # OPEN

    zip = har.get_zip()
    log = json.loads(zip["har.har"])["log"]

    ws_entry = find_entry(log, ws_url)
    assert ws_entry["response"]["_transferSize"] == response_headers_size(
        ws_entry["response"]["headers"]
    ) + message_size(incoming_text) + message_size(incoming_binary)
    assert ws_entry["time"] <= after_ms - before_ms
    assert "_webSocketMessages" not in ws_entry

    file = ws_entry["response"]["content"]["_file"]
    assert re.search(r"^[0-9a-f]+\.jsonl$", file)

    messages = read_jsonl(zip[file])
    assert [
        {"type": m["type"], "opcode": m["opcode"], "data": message_data(m)}
        for m in messages
    ] == [
        {"type": "send", "opcode": 1, "data": outgoing_text},
        {"type": "receive", "opcode": 1, "data": incoming_text},
        {"type": "send", "opcode": 2, "data": outgoing_binary},
        {"type": "receive", "opcode": 2, "data": incoming_binary},
    ]
    # The WSL VM clock drifts relative to the Windows host clock, so the browser-reported
    # message times cannot be compared against the host wall clock.
    if browser_channel != "webkit-wsl":
        for m in messages:
            assert m["time"] >= before_ms - CLOCK_SKEW_MS
            assert m["time"] <= after_ms + CLOCK_SKEW_MS
    assert messages[0]["time"] <= messages[1]["time"]
    assert ws_entry["time"] >= messages[-1]["time"] - messages[0]["time"]


def test_HA_106_should_omit_websocket_messages(
    page_with_har: PageWithHar, server: Server
) -> None:
    check_web_socket_messages(page_with_har, server, "omit")


def test_HA_107_should_record_websocket_connection_failure(
    page_with_har: PageWithHar, server: Server, browser_channel: Optional[str]
) -> None:
    if browser_channel == "webkit-wsl":
        pytest.skip(
            "Connection to an unbound localhost port from WSL is not refused in mirrored networking mode"
        )
    # Reserve a port and immediately release it so the WebSocket connect attempt is refused.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as port_reservation:
        port_reservation.bind(("127.0.0.1", 0))
        port = port_reservation.getsockname()[1]

    har = page_with_har()
    har.page.goto(server.EMPTY_PAGE)

    ws_url = f"ws://127.0.0.1:{port}/ws-connect-fail"
    with har.page.expect_websocket():
        har.page.evaluate(
            """url => new Promise(resolve => {
                const ws = new WebSocket(url);
                ws.addEventListener('close', () => resolve());
                ws.addEventListener('error', () => resolve());
            })""",
            ws_url,
        )
    log = har.get_log()

    ws_entry = find_entry(log, ws_url)
    assert ws_entry["_resourceType"] == "websocket"
    assert ws_entry["response"]["_failureText"]


def test_HA_108_should_record_websocket_handshake_failure(
    page_with_har: PageWithHar,
    server: Server,
    browser_name: str,
    sync_gather: Callable[..., List[Any]],
) -> None:
    har = page_with_har()
    har.page.goto(server.EMPTY_PAGE)

    ws_url = f"ws://{server.HOST}/ws-handshake-fail"

    upgrade_promise = server.wait_for_upgrade()

    def answer_upgrade() -> None:
        upgrade = wait_for(har.page, upgrade_promise)
        upgrade.socket.write("HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n")
        upgrade.socket.destroy()

    sync_gather(
        lambda: har.page.evaluate(
            """url => new Promise(resolve => {
                const ws = new WebSocket(url);
                ws.addEventListener('close', () => resolve());
                ws.addEventListener('error', () => resolve());
            })""",
            ws_url,
        ),
        answer_upgrade,
    )
    log = har.get_log()

    ws_entry = find_entry(log, ws_url)
    assert ws_entry["_resourceType"] == "websocket"
    if browser_name != "chromium":
        # Chromium only reports an error instead of giving a status code and text.
        assert ws_entry["response"]["status"] == 403
        assert ws_entry["response"]["statusText"] == "Forbidden"
    assert ws_entry["response"]["_failureText"]


def test_HA_109_should_still_capture_websocket_when_route_passes_messages_through(
    page_with_har: PageWithHar, server: Server
) -> None:
    def on_connection(ws: WebSocketProtocol) -> None:
        ws.events.on(
            "message", lambda payload, is_binary: ws.sendMessage(b"incoming", False)
        )

    server.once_web_socket_connection(on_connection)

    har = page_with_har()
    route_handler_called = 0

    def handle(ws: WebSocketRoute) -> None:
        nonlocal route_handler_called
        route_handler_called += 1
        server_route = ws.connect_to_server()
        ws.on_message(lambda message: server_route.send(message))
        server_route.on_message(lambda message: ws.send(message))

    har.page.route_web_socket(re.compile(r"/ws$"), handle)
    har.page.goto(server.EMPTY_PAGE)

    ws_url = f"ws://{server.HOST}/ws"
    messages = har.page.evaluate(
        """url => new Promise(resolve => {
            const seen = [];
            const ws = new WebSocket(url);
            ws.addEventListener('open', () => ws.send('outgoing'));
            ws.addEventListener('message', event => {
                seen.push(event.data);
                ws.close();
            });
            ws.addEventListener('close', () => resolve(seen));
        })""",
        ws_url,
    )
    assert route_handler_called == 1
    assert messages == ["incoming"]
    log = har.get_log()

    ws_entries = [e for e in log["entries"] if e["request"]["url"] == ws_url]
    assert len(ws_entries) == 1
    assert ws_entries[0]["_resourceType"] == "websocket"
    assert ws_entries[0]["response"]["status"] == 101
    assert [
        {"type": m["type"], "data": m["data"]}
        for m in ws_entries[0]["_webSocketMessages"]
    ] == [
        {"type": "send", "data": "outgoing"},
        {"type": "receive", "data": "incoming"},
    ]


def test_HA_110_should_still_allow_route_web_socket_to_fully_mock_the_connection_when_capturing_har(
    page_with_har: PageWithHar, server: Server
) -> None:
    har = page_with_har()
    route_handler_called = 0

    def handle(ws: WebSocketRoute) -> None:
        nonlocal route_handler_called
        route_handler_called += 1

        def on_message(message: Union[str, bytes]) -> None:
            if message == "ping":
                ws.send("pong")

        ws.on_message(on_message)

    har.page.route_web_socket(re.compile(r"/ws$"), handle)
    har.page.goto(server.EMPTY_PAGE)

    ws_url = f"ws://{server.HOST}/ws"
    messages = har.page.evaluate(
        """url => new Promise(resolve => {
            const seen = [];
            const ws = new WebSocket(url);
            ws.addEventListener('open', () => ws.send('ping'));
            ws.addEventListener('message', event => {
                seen.push(event.data);
                ws.close();
            });
            ws.addEventListener('close', () => resolve(seen));
        })""",
        ws_url,
    )
    assert route_handler_called == 1
    assert messages == ["pong"]
    log = har.get_log()

    # Fully mocked routes never create a native WebSocket, so nothing should be recorded.
    ws_entries = [e for e in log["entries"] if e["request"]["url"] == ws_url]
    assert ws_entries == []


def test_HA_111_should_still_allow_route_web_socket_to_modify_messages_when_capturing_har(
    page_with_har: PageWithHar, server: Server
) -> None:
    def on_connection(ws: WebSocketProtocol) -> None:
        ws.events.on(
            "message",
            lambda payload, is_binary: ws.sendMessage(b"server-saw-" + payload, False),
        )

    server.once_web_socket_connection(on_connection)

    har = page_with_har()
    route_handler_called = 0

    def handle(ws: WebSocketRoute) -> None:
        nonlocal route_handler_called
        route_handler_called += 1
        server_route = ws.connect_to_server()
        ws.on_message(lambda message: server_route.send(f"modified-{to_text(message)}"))
        server_route.on_message(lambda message: ws.send(f"page-got-{to_text(message)}"))

    har.page.route_web_socket(re.compile(r"/ws$"), handle)
    har.page.goto(server.EMPTY_PAGE)

    ws_url = f"ws://{server.HOST}/ws"
    messages = har.page.evaluate(
        """url => new Promise(resolve => {
            const seen = [];
            const ws = new WebSocket(url);
            ws.addEventListener('open', () => ws.send('hello'));
            ws.addEventListener('message', event => {
                seen.push(event.data);
                ws.close();
            });
            ws.addEventListener('close', () => resolve(seen));
        })""",
        ws_url,
    )
    assert route_handler_called == 1
    # The page sees the route-modified server response.
    assert messages == ["page-got-server-saw-modified-hello"]
    log = har.get_log()

    # HAR records actual wire traffic from the native WebSocket: outgoing messages
    # are modified by the client-side route handler before they hit the server,
    # and incoming messages are recorded before the server-side route handler modifies them.
    ws_entries = [e for e in log["entries"] if e["request"]["url"] == ws_url]
    assert len(ws_entries) == 1
    assert [
        {"type": m["type"], "data": m["data"]}
        for m in ws_entries[0]["_webSocketMessages"]
    ] == [
        {"type": "send", "data": "modified-hello"},
        {"type": "receive", "data": "server-saw-modified-hello"},
    ]


def test_HA_112_should_respect_playwright_har_no_websocket_frames(
    server: Server,
    browser_name: str,
    launch_arguments: Dict,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Upstream sets the variable in the test process, which also runs the Playwright
    # server. Here the driver is another process that reads the variable when it starts,
    # so start a new driver with the variable set, and use a browser of that driver.
    monkeypatch.setenv("PLAYWRIGHT_HAR_NO_WEBSOCKET_FRAMES", "1")
    server.once_web_socket_connection(close_on_message)

    def record_har() -> Dict[str, Any]:
        with sync_playwright() as playwright:
            browser = playwright[browser_name].launch(**launch_arguments)
            har_path = tmp_path / "test.har"
            context = browser.new_context(
                record_har_path=har_path, ignore_https_errors=True
            )
            har = HarPage(context.new_page(), context, har_path)
            har.page.goto(server.EMPTY_PAGE)
            ws_url = f"ws://{server.HOST}/ws"
            har.page.evaluate(
                """url => new Promise(resolve => {
                    const ws = new WebSocket(url);
                    ws.addEventListener('open', () => ws.send('ping'));
                    ws.addEventListener('close', () => resolve());
                })""",
                ws_url,
            )
            log = har.get_log()
            browser.close()
            return log

    # The sync API can not start a second driver in a thread that runs one already.
    with ThreadPoolExecutor(max_workers=1) as executor:
        log = executor.submit(record_har).result()
    ws_entry = [
        e
        for e in log["entries"]
        if e["request"]["url"].endswith(f"://{server.HOST}/ws")
    ][0]
    assert ws_entry["_resourceType"] == "websocket"
    assert "_webSocketMessages" not in ws_entry
    assert "_file" not in ws_entry["response"]["content"]
