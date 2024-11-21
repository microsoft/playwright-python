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

import re
import time
from typing import Any, Awaitable, Callable, Literal, Optional, Union

from playwright.sync_api import Browser, Frame, Page, WebSocketRoute
from tests.server import Server, WebSocketProtocol


def assert_equal(
    actual_cb: Callable[[], Union[Any, Awaitable[Any]]], expected: Any
) -> None:
    __tracebackhide__ = True
    start_time = time.time()
    attempts = 0
    while True:
        actual = actual_cb()
        if actual == expected:
            return
        attempts += 1
        if time.time() - start_time > 10:
            raise TimeoutError(f"Timed out after 10 seconds. Last actual was: {actual}")
        time.sleep(0.1)


def setup_ws(
    target: Union[Page, Frame],
    port: int,
    protocol: Union[Literal["blob"], Literal["arraybuffer"]],
) -> None:
    target.goto("about:blank")
    target.evaluate(
        """({ port, binaryType }) => {
    window.log = [];
    window.ws = new WebSocket('ws://localhost:' + port + '/ws');
    window.ws.binaryType = binaryType;
    window.ws.addEventListener('open', () => window.log.push('open'));
    window.ws.addEventListener('close', event => window.log.push(`close code=${event.code} reason=${event.reason} wasClean=${event.wasClean}`));
    window.ws.addEventListener('error', event => window.log.push(`error`));
    window.ws.addEventListener('message', async event => {
      let data;
      if (typeof event.data === 'string')
        data = event.data;
      else if (event.data instanceof Blob)
        data = 'blob:' + event.data.text();
      else
        data = 'arraybuffer:' + (new Blob([event.data])).text();
      window.log.push(`message: data=${data} origin=${event.origin} lastEventId=${event.lastEventId}`);
    });
    window.wsOpened = new Promise(f => window.ws.addEventListener('open', () => f()));
  }""",
        {"port": port, "binaryType": protocol},
    )


def test_should_work_with_ws_close(page: Page, server: Server) -> None:
    route: Optional["WebSocketRoute"] = None

    def _handle_ws(ws: WebSocketRoute) -> None:
        ws.connect_to_server()
        nonlocal route
        route = ws

    page.route_web_socket(re.compile(".*"), _handle_ws)

    with server.expect_websocket() as ws_task:
        setup_ws(page, server.PORT, "blob")
    page.evaluate("window.wsOpened")
    ws = ws_task.value
    assert route
    route.send("hello")
    assert_equal(
        lambda: page.evaluate("window.log"),
        [
            "open",
            f"message: data=hello origin=ws://localhost:{server.PORT} lastEventId=",
        ],
    )

    closed_event = []
    ws.events.once("close", lambda code, reason: closed_event.append((code, reason)))
    route.close(code=3009, reason="oops")
    assert_equal(
        lambda: page.evaluate("window.log"),
        [
            "open",
            f"message: data=hello origin=ws://localhost:{server.PORT} lastEventId=",
            "close code=3009 reason=oops wasClean=true",
        ],
    )
    assert_equal(lambda: closed_event, [(3009, "oops")])


def test_should_pattern_match(page: Page, server: Server) -> None:
    page.route_web_socket(re.compile(r".*/ws$"), lambda ws: ws.connect_to_server())
    page.route_web_socket(
        "**/mock-ws", lambda ws: ws.on_message(lambda message: ws.send("mock-response"))
    )

    page.goto("about:blank")
    with server.expect_websocket() as ws_info:
        page.evaluate(
            """async ({ port }) => {
                window.log = [];
                window.ws1 = new WebSocket('ws://localhost:' + port + '/ws');
                window.ws1.addEventListener('message', event => window.log.push(`ws1:${event.data}`));
                window.ws2 = new WebSocket('ws://localhost:' + port + '/something/something/mock-ws');
                window.ws2.addEventListener('message', event => window.log.push(`ws2:${event.data}`));
                await Promise.all([
                    new Promise(f => window.ws1.addEventListener('open', f)),
                    new Promise(f => window.ws2.addEventListener('open', f)),
                ]);
            }""",
            {"port": server.PORT},
        )
    ws = ws_info.value
    ws.events.on("message", lambda payload, isBinary: ws.sendMessage(b"response"))

    page.evaluate("window.ws1.send('request')")
    assert_equal(lambda: page.evaluate("window.log"), ["ws1:response"])

    page.evaluate("window.ws2.send('request')")
    assert_equal(
        lambda: page.evaluate("window.log"), ["ws1:response", "ws2:mock-response"]
    )


def test_should_work_with_server(page: Page, server: Server) -> None:
    route = None

    def _handle_ws(ws: WebSocketRoute) -> None:
        server = ws.connect_to_server()

        def _ws_on_message(message: Union[str, bytes]) -> None:
            if message == "to-respond":
                ws.send("response")
                return
            if message == "to-block":
                return
            if message == "to-modify":
                server.send("modified")
                return
            server.send(message)

        ws.on_message(_ws_on_message)

        def _server_on_message(message: Union[str, bytes]) -> None:
            if message == "to-block":
                return
            if message == "to-modify":
                ws.send("modified")
                return
            ws.send(message)

        server.on_message(_server_on_message)
        server.send("fake")
        nonlocal route
        route = ws

    page.route_web_socket(re.compile(".*"), _handle_ws)
    log = []

    def _once_web_socket_connection(ws: WebSocketProtocol) -> None:
        ws.events.on(
            "message", lambda data, is_binary: log.append(f"message: {data.decode()}")
        )
        ws.events.on(
            "close",
            lambda code, reason: log.append(f"close: code={code} reason={reason}"),
        )

    server.once_web_socket_connection(_once_web_socket_connection)

    with server.expect_websocket() as ws_info:
        setup_ws(page, server.PORT, "blob")
    page.evaluate("window.wsOpened")
    ws = ws_info.value
    assert_equal(lambda: log, ["message: fake"])

    ws.sendMessage(b"to-modify")
    ws.sendMessage(b"to-block")
    ws.sendMessage(b"pass-server")
    assert_equal(
        lambda: page.evaluate("window.log"),
        [
            "open",
            f"message: data=modified origin=ws://localhost:{server.PORT} lastEventId=",
            f"message: data=pass-server origin=ws://localhost:{server.PORT} lastEventId=",
        ],
    )

    page.evaluate(
        """() => {
        window.ws.send('to-respond');
        window.ws.send('to-modify');
        window.ws.send('to-block');
        window.ws.send('pass-client');
    }"""
    )
    assert_equal(
        lambda: log, ["message: fake", "message: modified", "message: pass-client"]
    )
    assert_equal(
        lambda: page.evaluate("window.log"),
        [
            "open",
            f"message: data=modified origin=ws://localhost:{server.PORT} lastEventId=",
            f"message: data=pass-server origin=ws://localhost:{server.PORT} lastEventId=",
            f"message: data=response origin=ws://localhost:{server.PORT} lastEventId=",
        ],
    )
    assert route
    route.send("another")
    assert_equal(
        lambda: page.evaluate("window.log"),
        [
            "open",
            f"message: data=modified origin=ws://localhost:{server.PORT} lastEventId=",
            f"message: data=pass-server origin=ws://localhost:{server.PORT} lastEventId=",
            f"message: data=response origin=ws://localhost:{server.PORT} lastEventId=",
            f"message: data=another origin=ws://localhost:{server.PORT} lastEventId=",
        ],
    )

    page.evaluate(
        """() => {
        window.ws.send('pass-client-2');
    }"""
    )
    assert_equal(
        lambda: log,
        [
            "message: fake",
            "message: modified",
            "message: pass-client",
            "message: pass-client-2",
        ],
    )

    page.evaluate(
        """() => {
        window.ws.close(3009, 'problem');
    }"""
    )
    assert_equal(
        lambda: log,
        [
            "message: fake",
            "message: modified",
            "message: pass-client",
            "message: pass-client-2",
            "close: code=3009 reason=problem",
        ],
    )


def test_should_work_without_server(page: Page, server: Server) -> None:
    route = None

    def _handle_ws(ws: WebSocketRoute) -> None:
        def _ws_on_message(message: Union[str, bytes]) -> None:
            if message == "to-respond":
                ws.send("response")

        ws.on_message(_ws_on_message)
        nonlocal route
        route = ws

    page.route_web_socket(re.compile(".*"), _handle_ws)
    setup_ws(page, server.PORT, "blob")

    page.evaluate(
        """async () => {
        await window.wsOpened;
        window.ws.send('to-respond');
        window.ws.send('to-block');
        window.ws.send('to-respond');
    }"""
    )

    assert_equal(
        lambda: page.evaluate("window.log"),
        [
            "open",
            f"message: data=response origin=ws://localhost:{server.PORT} lastEventId=",
            f"message: data=response origin=ws://localhost:{server.PORT} lastEventId=",
        ],
    )
    assert route
    route.send("another")
    # wait for the message to be processed
    page.wait_for_timeout(100)
    route.close(code=3008, reason="oops")
    assert_equal(
        lambda: page.evaluate("window.log"),
        [
            "open",
            f"message: data=response origin=ws://localhost:{server.PORT} lastEventId=",
            f"message: data=response origin=ws://localhost:{server.PORT} lastEventId=",
            f"message: data=another origin=ws://localhost:{server.PORT} lastEventId=",
            "close code=3008 reason=oops wasClean=true",
        ],
    )


def test_should_work_with_base_url(browser: Browser, server: Server) -> None:
    context = browser.new_context(base_url=f"http://localhost:{server.PORT}")
    page = context.new_page()

    def _handle_ws(ws: WebSocketRoute) -> None:
        ws.on_message(lambda message: ws.send(message))

    page.route_web_socket("/ws", _handle_ws)
    setup_ws(page, server.PORT, "blob")

    page.evaluate(
        """async () => {
        await window.wsOpened;
        window.ws.send('echo');
    }"""
    )

    assert_equal(
        lambda: page.evaluate("window.log"),
        [
            "open",
            f"message: data=echo origin=ws://localhost:{server.PORT} lastEventId=",
        ],
    )
