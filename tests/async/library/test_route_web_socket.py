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

"""Port of tests/library/route-web-socket.spec.ts."""

import asyncio
import inspect
import re
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse

import pytest

from playwright.async_api import Error, Frame, Page, WebSocketRoute
from tests.helpers import web_socket_server
from tests.helpers.web_socket_server import to_text
from tests.server import Server, WebSocketProtocol

from ..utils import Utils

MOCKS = ["no-mock", "no-match", "pass-through"]


async def expect_poll(
    page: Page, actual: Callable[[], Any], expected: Any, timeout: float = 5000
) -> None:
    """Port of `await expect.poll(actual).toEqual(expected)`."""
    deadline = time.monotonic() + timeout / 1000
    while True:
        value = actual()
        if inspect.isawaitable(value):
            value = await value
        if value == expected or time.monotonic() > deadline:
            break
        await page.wait_for_timeout(100)
    assert value == expected


async def setup_ws(
    target: Union[Page, Frame],
    server: Server,
    binary_type: str,
    protocols: Optional[Union[str, List[str]]] = None,
    relative_url: bool = False,
) -> None:
    await target.goto(server.EMPTY_PAGE)
    ws_url = "/ws" if relative_url else "ws://" + server.HOST + "/ws"
    arg: Dict[str, Any] = {"wsUrl": ws_url, "binaryType": binary_type}
    if protocols is not None:
        arg["protocols"] = protocols
    await target.evaluate(
        """({ wsUrl, binaryType, protocols }) => {
            window.log = [];
            window.ws = new WebSocket(wsUrl, protocols);
            window.ws.binaryType = binaryType;
            window.ws.addEventListener('open', () => window.log.push('open'));
            window.ws.addEventListener('close', event => window.log.push(`close code=${event.code} reason=${event.reason} wasClean=${event.wasClean}`));
            window.ws.addEventListener('error', event => window.log.push(`error`));
            window.ws.addEventListener('message', async event => {
                let data;
                if (typeof event.data === 'string')
                    data = event.data;
                else if (event.data instanceof Blob)
                    data = 'blob:' + await event.data.text();
                else
                    data = 'arraybuffer:' + await (new Blob([event.data])).text();
                window.log.push(`message: data=${data} origin=${event.origin} lastEventId=${event.lastEventId}`);
            });
            window.wsOpened = new Promise(f => window.ws.addEventListener('open', () => f()));
        }""",
        arg,
    )


async def setup_mock(page: Page, mock: str) -> None:
    """Port of the beforeEach of the {no-mock, no-match, pass-through} describes."""
    if mock == "no-match":
        await page.route_web_socket(re.compile(r"zzz"), lambda ws: None)
    elif mock == "pass-through":

        def handler(ws: WebSocketRoute) -> None:
            server = ws.connect_to_server()
            ws.on_message(lambda message: server.send(message))
            server.on_message(lambda message: ws.send(message))

        await page.route_web_socket(re.compile(r".*"), handler)


def on_next_message(ws: WebSocketProtocol, messages: List[str]) -> None:
    """Port of `ws.once('message', data => f(data.toString()))` on the server."""
    ws.events.once(
        "message", lambda payload, is_binary: messages.append(to_text(payload))
    )


@pytest.mark.parametrize("mock", MOCKS)
async def test_WS_015_should_work_with_text_message(
    page: Page, server: Server, mock: str
) -> None:
    await setup_mock(page, mock)
    ws_promise = server.wait_for_web_socket()
    upgrade_promise = server.wait_for_upgrade()
    await setup_ws(page, server, "blob")
    assert await page.evaluate("() => window.ws.readyState") == 0
    upgrade = await upgrade_promise
    assert await page.evaluate("() => window.ws.readyState") == 0
    assert await page.evaluate("() => window.log") == []
    upgrade.do_upgrade()
    await expect_poll(page, lambda: page.evaluate("() => window.ws.readyState"), 1)
    assert await page.evaluate("() => window.log") == ["open"]
    ws = await ws_promise
    web_socket_server.send(ws, "hello")
    await expect_poll(
        page,
        lambda: page.evaluate("() => window.log"),
        [
            "open",
            f"message: data=hello origin=ws://{server.HOST} lastEventId=",
        ],
    )
    assert await page.evaluate("() => window.ws.readyState") == 1
    messages: List[str] = []
    on_next_message(ws, messages)
    await page.evaluate("() => window.ws.send('hi')")
    await expect_poll(page, lambda: messages, ["hi"])
    web_socket_server.close(ws, 1008, "oops")
    await expect_poll(page, lambda: page.evaluate("() => window.ws.readyState"), 3)
    assert await page.evaluate("() => window.log") == [
        "open",
        f"message: data=hello origin=ws://{server.HOST} lastEventId=",
        "close code=1008 reason=oops wasClean=true",
    ]


@pytest.mark.parametrize("mock", MOCKS)
async def test_WS_016_should_work_with_binary_type_blob(
    page: Page, server: Server, mock: str
) -> None:
    await setup_mock(page, mock)
    ws_promise = server.wait_for_web_socket()
    await setup_ws(page, server, "blob")
    ws = await ws_promise
    web_socket_server.send(ws, b"hi")
    await expect_poll(
        page,
        lambda: page.evaluate("() => window.log"),
        [
            "open",
            f"message: data=blob:hi origin=ws://{server.HOST} lastEventId=",
        ],
    )
    messages: List[str] = []
    on_next_message(ws, messages)
    await page.evaluate(
        "() => window.ws.send(new Blob([new Uint8Array(['h'.charCodeAt(0), 'i'.charCodeAt(0)])]))"
    )
    await expect_poll(page, lambda: messages, ["hi"])


@pytest.mark.parametrize("mock", MOCKS)
async def test_WS_017_should_work_with_binary_type_arraybuffer(
    page: Page, server: Server, mock: str
) -> None:
    await setup_mock(page, mock)
    ws_promise = server.wait_for_web_socket()
    await setup_ws(page, server, "arraybuffer")
    ws = await ws_promise
    web_socket_server.send(ws, b"hi")
    await expect_poll(
        page,
        lambda: page.evaluate("() => window.log"),
        [
            "open",
            f"message: data=arraybuffer:hi origin=ws://{server.HOST} lastEventId=",
        ],
    )
    messages: List[str] = []
    on_next_message(ws, messages)
    await page.evaluate(
        "() => window.ws.send(new Uint8Array(['h'.charCodeAt(0), 'i'.charCodeAt(0)]).buffer)"
    )
    await expect_poll(page, lambda: messages, ["hi"])


@pytest.mark.parametrize("mock", MOCKS)
async def test_WS_018_should_work_when_connection_errors_out(
    page: Page, server: Server, mock: str, browser_name: str
) -> None:
    if browser_name == "webkit":
        pytest.skip("WebKit ignores the connection error and fires no events!")

    await setup_mock(page, mock)
    upgrade_promise = server.wait_for_upgrade()
    await setup_ws(page, server, "blob")
    upgrade = await upgrade_promise
    assert await page.evaluate("() => window.ws.readyState") == 0
    assert await page.evaluate("() => window.log") == []
    upgrade.socket.destroy()
    await expect_poll(page, lambda: page.evaluate("() => window.ws.readyState"), 3)
    log = await page.evaluate("() => window.log")
    assert len(log) == 2
    assert log[0] == "error"
    assert re.search(r"close code=\d+ reason= wasClean=false", log[1])


@pytest.mark.parametrize("mock", MOCKS)
async def test_WS_019_should_work_with_error_after_successful_open(
    page: Page,
    server: Server,
    mock: str,
    browser_name: str,
    is_linux: bool,
    is_win: bool,
) -> None:
    if browser_name == "firefox":
        pytest.skip("Firefox does not close the websocket upon a bad frame")
    if browser_name == "webkit" and is_linux:
        pytest.skip("WebKit linux does not close the websocket upon a bad frame")
    if browser_name == "webkit" and is_win:
        pytest.skip("WebKit Windows does not close the websocket upon a bad frame")

    await setup_mock(page, mock)
    upgrade_promise = server.wait_for_upgrade()
    await setup_ws(page, server, "blob")
    upgrade = await upgrade_promise
    upgrade.do_upgrade()
    await expect_poll(page, lambda: page.evaluate("() => window.ws.readyState"), 1)
    assert await page.evaluate("() => window.log") == ["open"]
    upgrade.socket.write("garbage")
    await expect_poll(page, lambda: page.evaluate("() => window.ws.readyState"), 3)
    log = await page.evaluate("() => window.log")
    assert len(log) == 3
    assert log[:2] == ["open", "error"]
    assert re.search(r"close code=\d+ reason= wasClean=false", log[2])


@pytest.mark.parametrize("mock", MOCKS)
async def test_WS_020_should_work_with_client_side_close(
    page: Page, server: Server, mock: str
) -> None:
    await setup_mock(page, mock)
    ws_promise = server.wait_for_web_socket()
    upgrade_promise = server.wait_for_upgrade()
    await setup_ws(page, server, "blob")
    assert await page.evaluate("() => window.ws.readyState") == 0
    upgrade = await upgrade_promise
    assert await page.evaluate("() => window.ws.readyState") == 0
    assert await page.evaluate("() => window.log") == []
    upgrade.do_upgrade()
    await expect_poll(page, lambda: page.evaluate("() => window.ws.readyState"), 1)
    assert await page.evaluate("() => window.log") == ["open"]
    ws = await ws_promise
    closed: List[Tuple[int, str]] = []
    ws.events.once("close", lambda code, reason: closed.append((code, reason)))
    ready_state = await page.evaluate(
        """() => {
            window.ws.close(3002, 'oops');
            return window.ws.readyState;
        }"""
    )
    assert ready_state == 2
    await expect_poll(page, lambda: page.evaluate("() => window.ws.readyState"), 3)
    assert await page.evaluate("() => window.log") == [
        "open",
        "close code=3002 reason=oops wasClean=true",
    ]
    await expect_poll(page, lambda: len(closed), 1)
    code, reason = closed[0]
    assert code == 3002
    assert reason == "oops"


@pytest.mark.parametrize("mock", MOCKS)
async def test_WS_021_should_pass_through_the_required_protocol(
    page: Page, server: Server, mock: str
) -> None:
    await setup_mock(page, mock)
    await setup_ws(page, server, "blob", "my-custom-protocol")
    await page.evaluate("() => window.wsOpened")
    protocol = await page.evaluate("() => window.ws.protocol")
    assert protocol == "my-custom-protocol"


@pytest.mark.parametrize("mock", MOCKS)
async def test_WS_022_should_work_with_relative_web_socket_url(
    page: Page, server: Server, mock: str
) -> None:
    await setup_mock(page, mock)
    ws_promise = server.wait_for_web_socket()
    await setup_ws(page, server, "blob", None, True)
    ws = await ws_promise
    web_socket_server.send(ws, b"hi")
    await expect_poll(
        page,
        lambda: page.evaluate("() => window.log"),
        [
            "open",
            f"message: data=blob:hi origin=ws://{server.HOST} lastEventId=",
        ],
    )
    messages: List[str] = []
    on_next_message(ws, messages)
    await page.evaluate(
        "() => window.ws.send(new Blob([new Uint8Array(['h'.charCodeAt(0), 'i'.charCodeAt(0)])]))"
    )
    await expect_poll(page, lambda: messages, ["hi"])


async def test_WS_023_should_work_with_ws_close(page: Page, server: Server) -> None:
    promise: "asyncio.Future[WebSocketRoute]" = asyncio.Future()

    def handler(ws: WebSocketRoute) -> None:
        ws.connect_to_server()
        promise.set_result(ws)

    await page.route_web_socket(re.compile(r".*"), handler)

    ws_promise = server.wait_for_web_socket()
    await setup_ws(page, server, "blob")
    ws = await ws_promise

    route = await promise
    route.send("hello")
    await expect_poll(
        page,
        lambda: page.evaluate("() => window.log"),
        [
            "open",
            f"message: data=hello origin=ws://{server.HOST} lastEventId=",
        ],
    )

    closed: List[Dict[str, Any]] = []
    ws.events.once(
        "close", lambda code, reason: closed.append({"code": code, "reason": reason})
    )
    await route.close(code=3009, reason="oops")
    await expect_poll(
        page,
        lambda: page.evaluate("() => window.log"),
        [
            "open",
            f"message: data=hello origin=ws://{server.HOST} lastEventId=",
            "close code=3009 reason=oops wasClean=true",
        ],
    )
    await expect_poll(page, lambda: closed, [{"code": 3009, "reason": "oops"}])


async def test_WS_024_should_observe_upstream_handshake_failure_when_connect_to_server_is_used(
    page: Page, server: Server
) -> None:
    # Exercises the WebSocket-as-network-request path used by Firefox after the
    # har-WebSocket plumbing change, where a 4xx handshake response is synthesized
    # into a full lifecycle in FFPage._onWebSocketRequestFinished.
    server_closes: List[Tuple[Optional[int], Optional[str]]] = []
    route_handler_invoked = 0

    def handler(ws: WebSocketRoute) -> None:
        nonlocal route_handler_invoked
        route_handler_invoked += 1
        server_route = ws.connect_to_server()

        def on_close(code: Optional[int], reason: Optional[str]) -> None:
            server_closes.append((code, reason))
            asyncio.create_task(ws.close())

        server_route.on_close(on_close)

    await page.route_web_socket(re.compile(r".*"), handler)

    upgrade_promise = server.wait_for_upgrade()
    await setup_ws(page, server, "blob")
    upgrade = await upgrade_promise
    upgrade.socket.write("HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n")
    upgrade.socket.destroy()

    # Server-side route handler observes the close caused by the rejected handshake.
    await expect_poll(page, lambda: len(server_closes), 1)
    code = server_closes[0][0]
    assert code is not None and code >= 1000

    # Once the route closes the page-side socket, the page sees the close.
    await expect_poll(page, lambda: page.evaluate("() => window.ws.readyState"), 3)
    assert route_handler_invoked == 1


async def test_WS_025_should_observe_multiple_concurrent_routed_web_sockets_with_connect_to_server(
    page: Page, server: Server
) -> None:
    # Exercises FFNetworkManager._webSocketRequestIds tracking by routing two
    # simultaneous WebSocket connections through `connectToServer()`. Each request
    # gets a distinct id in the new Firefox WebSocket-as-network-request flow.
    routed_connections = 0

    def handler(ws: WebSocketRoute) -> None:
        nonlocal routed_connections
        routed_connections += 1
        server_route = ws.connect_to_server()
        ws.on_message(lambda message: server_route.send(message))
        server_route.on_message(lambda message: ws.send(message))

    await page.route_web_socket(re.compile(r".*"), handler)

    # Echo all incoming messages on whichever connection arrives; re-register after each.
    def handle_connection(ws: WebSocketProtocol) -> None:
        ws.events.on(
            "message",
            lambda payload, is_binary: ws.sendMessage(
                f"echo-{to_text(payload)}".encode(), False
            ),
        )
        server.once_web_socket_connection(handle_connection)

    server.once_web_socket_connection(handle_connection)

    await page.goto(server.EMPTY_PAGE)
    results = await page.evaluate(
        """async host => {
            const collect = tag => new Promise(resolve => {
                const ws = new WebSocket(`ws://${host}/ws`);
                ws.addEventListener('open', () => ws.send(`hi-${tag}`));
                ws.addEventListener('message', event => {
                    resolve(event.data);
                    ws.close();
                });
            });
            return Promise.all([collect('a'), collect('b')]);
        }""",
        server.HOST,
    )

    assert sorted(results) == ["echo-hi-a", "echo-hi-b"]
    assert routed_connections == 2


async def test_WS_026_should_pattern_match(page: Page, server: Server) -> None:
    await page.route_web_socket(
        re.compile(r".*/ws$"), lambda ws: ws.connect_to_server()
    )

    def mock_handler(ws: WebSocketRoute) -> None:
        ws.on_message(lambda message: ws.send("mock-response"))

    await page.route_web_socket("**/mock-ws", mock_handler)

    ws_promise = server.wait_for_web_socket()

    await page.goto(server.EMPTY_PAGE)
    await page.evaluate(
        """async ({ host }) => {
            window.log = [];
            window.ws1 = new WebSocket('ws://' + host + '/ws');
            window.ws1.addEventListener('message', event => window.log.push(`ws1:${event.data}`));
            window.ws2 = new WebSocket('ws://' + host + '/something/something/mock-ws');
            window.ws2.addEventListener('message', event => window.log.push(`ws2:${event.data}`));
            await Promise.all([
                new Promise(f => window.ws1.addEventListener('open', f)),
                new Promise(f => window.ws2.addEventListener('open', f)),
            ]);
        }""",
        {"host": server.HOST},
    )

    ws = await ws_promise
    ws.events.on(
        "message", lambda payload, is_binary: ws.sendMessage(b"response", False)
    )

    await page.evaluate("() => window.ws1.send('request')")
    await expect_poll(page, lambda: page.evaluate("() => window.log"), ["ws1:response"])

    await page.evaluate("() => window.ws2.send('request')")
    await expect_poll(
        page,
        lambda: page.evaluate("() => window.log"),
        ["ws1:response", "ws2:mock-response"],
    )


async def test_WS_027_should_work_with_server(page: Page, server: Server) -> None:
    promise: "asyncio.Future[WebSocketRoute]" = asyncio.Future()

    def handler(ws: WebSocketRoute) -> None:
        server_route = ws.connect_to_server()

        def on_page_message(message: Union[str, bytes]) -> None:
            if message == "to-respond":
                ws.send("response")
                return
            if message == "to-block":
                return
            if message == "to-modify":
                server_route.send("modified")
                return
            server_route.send(message)

        ws.on_message(on_page_message)

        def on_server_message(message: Union[str, bytes]) -> None:
            if message == "to-block":
                return
            if message == "to-modify":
                ws.send("modified")
                return
            ws.send(message)

        server_route.on_message(on_server_message)
        server_route.send("fake")
        promise.set_result(ws)

    await page.route_web_socket(re.compile(r".*"), handler)

    ws_promise = server.wait_for_web_socket()
    log: List[str] = []

    def on_connection(ws: WebSocketProtocol) -> None:
        ws.events.on(
            "message",
            lambda payload, is_binary: log.append(f"message: {to_text(payload)}"),
        )
        ws.events.on(
            "close",
            lambda code, reason: log.append(f"close: code={code} reason={reason}"),
        )

    server.once_web_socket_connection(on_connection)

    await setup_ws(page, server, "blob")
    ws = await ws_promise
    await expect_poll(page, lambda: log, ["message: fake"])

    web_socket_server.send(ws, "to-modify")
    web_socket_server.send(ws, "to-block")
    web_socket_server.send(ws, "pass-server")
    await expect_poll(
        page,
        lambda: page.evaluate("() => window.log"),
        [
            "open",
            f"message: data=modified origin=ws://{server.HOST} lastEventId=",
            f"message: data=pass-server origin=ws://{server.HOST} lastEventId=",
        ],
    )

    await page.evaluate(
        """() => {
            window.ws.send('to-respond');
            window.ws.send('to-modify');
            window.ws.send('to-block');
            window.ws.send('pass-client');
        }"""
    )
    await expect_poll(
        page,
        lambda: log,
        ["message: fake", "message: modified", "message: pass-client"],
    )
    await expect_poll(
        page,
        lambda: page.evaluate("() => window.log"),
        [
            "open",
            f"message: data=modified origin=ws://{server.HOST} lastEventId=",
            f"message: data=pass-server origin=ws://{server.HOST} lastEventId=",
            f"message: data=response origin=ws://{server.HOST} lastEventId=",
        ],
    )

    route = await promise
    route.send("another")
    await expect_poll(
        page,
        lambda: page.evaluate("() => window.log"),
        [
            "open",
            f"message: data=modified origin=ws://{server.HOST} lastEventId=",
            f"message: data=pass-server origin=ws://{server.HOST} lastEventId=",
            f"message: data=response origin=ws://{server.HOST} lastEventId=",
            f"message: data=another origin=ws://{server.HOST} lastEventId=",
        ],
    )

    await page.evaluate(
        """() => {
            window.ws.send('pass-client-2');
        }"""
    )
    await expect_poll(
        page,
        lambda: log,
        [
            "message: fake",
            "message: modified",
            "message: pass-client",
            "message: pass-client-2",
        ],
    )

    await page.evaluate(
        """() => {
            window.ws.close(3009, 'problem');
        }"""
    )
    await expect_poll(
        page,
        lambda: log,
        [
            "message: fake",
            "message: modified",
            "message: pass-client",
            "message: pass-client-2",
            "close: code=3009 reason=problem",
        ],
    )


async def test_WS_028_should_work_without_server(page: Page, server: Server) -> None:
    promise: "asyncio.Future[WebSocketRoute]" = asyncio.Future()

    def handler(ws: WebSocketRoute) -> None:
        def on_message(message: Union[str, bytes]) -> None:
            if message == "to-respond":
                ws.send("response")
                return

        ws.on_message(on_message)
        promise.set_result(ws)

    await page.route_web_socket(re.compile(r".*"), handler)

    await setup_ws(page, server, "blob")

    await page.evaluate(
        """async () => {
            await window.wsOpened;
            window.ws.send('to-respond');
            window.ws.send('to-block');
            window.ws.send('to-respond');
        }"""
    )

    await expect_poll(
        page,
        lambda: page.evaluate("() => window.log"),
        [
            "open",
            f"message: data=response origin=ws://{server.HOST} lastEventId=",
            f"message: data=response origin=ws://{server.HOST} lastEventId=",
        ],
    )

    route = await promise
    route.send("another")
    await route.close(code=3008, reason="oops")

    await expect_poll(
        page,
        lambda: page.evaluate("() => window.log"),
        [
            "open",
            f"message: data=response origin=ws://{server.HOST} lastEventId=",
            f"message: data=response origin=ws://{server.HOST} lastEventId=",
            f"message: data=another origin=ws://{server.HOST} lastEventId=",
            "close code=3008 reason=oops wasClean=true",
        ],
    )


async def test_WS_029_should_route_web_sockets_in_already_loaded_documents(
    page: Page, server: Server, utils: Utils
) -> None:
    # https://github.com/microsoft/playwright/issues/43105
    await page.goto(server.EMPTY_PAGE)
    frame = await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)

    def handler(ws: WebSocketRoute) -> None:
        ws.on_message(lambda message: ws.send("mock-" + to_text(message)))

    await page.route_web_socket(re.compile(r".*"), handler)

    for target in [page.main_frame, frame]:
        await target.evaluate(
            """({ host }) => {
                window.log = [];
                window.ws = new WebSocket('ws://' + host + '/ws');
                window.ws.addEventListener('message', event => window.log.push(event.data));
                window.ws.addEventListener('close', () => window.log.push('close'));
                window.ws.addEventListener('open', () => window.ws.send('hi'));
            }""",
            {"host": server.HOST},
        )
        await expect_poll(
            page, lambda: target.evaluate("() => window.log"), ["mock-hi"]
        )


async def test_WS_030_should_emit_close_upon_frame_navigation(
    page: Page, server: Server
) -> None:
    promise: "asyncio.Future[WebSocketRoute]" = asyncio.Future()

    def handler(ws: WebSocketRoute) -> None:
        ws.connect_to_server()
        promise.set_result(ws)

    await page.route_web_socket(re.compile(r".*"), handler)

    await setup_ws(page, server, "blob")

    route = await promise
    route.send("hello")

    await expect_poll(
        page,
        lambda: page.evaluate("() => window.log"),
        [
            "open",
            f"message: data=hello origin=ws://{server.HOST} lastEventId=",
        ],
    )

    closed: "asyncio.Future[None]" = asyncio.Future()
    route.on_close(lambda code, reason: closed.set_result(None))
    await page.goto(server.EMPTY_PAGE)
    await closed


async def test_WS_031_should_emit_close_upon_frame_detach(
    page: Page, server: Server, utils: Utils
) -> None:
    promise: "asyncio.Future[WebSocketRoute]" = asyncio.Future()

    def handler(ws: WebSocketRoute) -> None:
        ws.connect_to_server()
        promise.set_result(ws)

    await page.route_web_socket(re.compile(r".*"), handler)

    frame = await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    await setup_ws(frame, server, "blob")

    route = await promise
    route.send("hello")

    await expect_poll(
        page,
        lambda: frame.evaluate("() => window.log"),
        [
            "open",
            f"message: data=hello origin=ws://{server.HOST} lastEventId=",
        ],
    )

    closed: "asyncio.Future[None]" = asyncio.Future()
    route.on_close(lambda code, reason: closed.set_result(None))
    await utils.detach_frame(page, "frame1")
    await closed


async def test_WS_032_should_route_on_context(page: Page, server: Server) -> None:
    def page_handler_1(ws: WebSocketRoute) -> None:
        ws.on_message(lambda message: ws.send("page-mock-1"))

    await page.route_web_socket(re.compile(r"ws1"), page_handler_1)

    def page_handler_2(ws: WebSocketRoute) -> None:
        ws.on_message(lambda message: ws.send("page-mock-2"))

    await page.route_web_socket(re.compile(r"ws1"), page_handler_2)

    def context_handler(ws: WebSocketRoute) -> None:
        ws.on_message(lambda message: ws.send("context-mock-1"))
        ws.on_message(lambda message: ws.send("context-mock-2"))

    await page.context.route_web_socket(re.compile(r".*"), context_handler)

    await page.goto(server.EMPTY_PAGE)
    await page.evaluate(
        """({ host }) => {
            window.log = [];
            window.ws1 = new WebSocket('ws://' + host + '/ws1');
            window.ws1.addEventListener('message', event => window.log.push(`ws1:${event.data}`));
            window.ws2 = new WebSocket('ws://' + host + '/ws2');
            window.ws2.addEventListener('message', event => window.log.push(`ws2:${event.data}`));
        }""",
        {"host": server.HOST},
    )

    await page.evaluate("() => window.ws1.send('request')")
    await expect_poll(
        page, lambda: page.evaluate("() => window.log"), ["ws1:page-mock-2"]
    )

    await page.evaluate("() => window.ws2.send('request')")
    await expect_poll(
        page,
        lambda: page.evaluate("() => window.log"),
        ["ws1:page-mock-2", "ws2:context-mock-2"],
    )


async def test_WS_033_should_not_throw_after_page_closure(
    page: Page, server: Server
) -> None:
    promise: "asyncio.Future[WebSocketRoute]" = asyncio.Future()

    def handler(ws: WebSocketRoute) -> None:
        ws.connect_to_server()
        promise.set_result(ws)

    await page.route_web_socket(re.compile(r".*"), handler)

    await setup_ws(page, server, "blob")

    route = await promise

    async def send() -> None:
        route.send("hello")

    await asyncio.gather(page.close(), send())


async def test_WS_034_should_not_throw_with_empty_handler(
    page: Page, server: Server
) -> None:
    await page.route_web_socket(re.compile(r".*"), lambda ws: None)
    await setup_ws(page, server, "blob")
    await expect_poll(page, lambda: page.evaluate("() => window.log"), ["open"])
    await page.evaluate("() => window.ws.send('hi')")
    await page.evaluate("() => window.ws.send('hi2')")
    await expect_poll(page, lambda: page.evaluate("() => window.log"), ["open"])


async def test_WS_035_should_throw_when_connecting_twice(
    page: Page, server: Server
) -> None:
    promise: "asyncio.Future[Error]" = asyncio.Future()

    def handler(ws: WebSocketRoute) -> None:
        ws.connect_to_server()
        try:
            ws.connect_to_server()
        except Error as e:
            promise.set_result(e)

    await page.route_web_socket(re.compile(r".*"), handler)
    await setup_ws(page, server, "blob")
    error = await promise
    assert "Already connected to the server" in error.message


async def test_WS_036_should_work_with_no_trailing_slash(
    page: Page, server: Server
) -> None:
    log: List[str] = []

    def handler(ws: WebSocketRoute) -> None:
        def on_message(message: Union[str, bytes]) -> None:
            log.append(to_text(message))
            ws.send("response")

        ws.on_message(on_message)

    # No trailing slash!
    await page.route_web_socket("ws://" + server.HOST, handler)

    await page.goto(server.EMPTY_PAGE)
    await page.evaluate(
        """({ host }) => {
            window.log = [];
            // No trailing slash!
            window.ws = new WebSocket('ws://' + host);
            window.ws.addEventListener('message', event => window.log.push(event.data));
        }""",
        {"host": server.HOST},
    )

    await expect_poll(page, lambda: page.evaluate("() => window.ws.readyState"), 1)
    await page.evaluate("() => window.ws.send('query')")
    await expect_poll(page, lambda: log, ["query"])
    assert await page.evaluate("() => window.log") == ["response"]


async def test_WS_037_should_work_with_base_url(
    context_factory: Callable[..., Any], server: Server
) -> None:
    context = await context_factory(base_url="http://" + server.HOST)
    page = await context.new_page()

    def handler(ws: WebSocketRoute) -> None:
        ws.on_message(lambda message: ws.send(message))

    await page.route_web_socket("/ws", handler)

    await setup_ws(page, server, "blob")

    await page.evaluate(
        """async () => {
            await window.wsOpened;
            window.ws.send('echo');
        }"""
    )

    await expect_poll(
        page,
        lambda: page.evaluate("() => window.log"),
        [
            "open",
            f"message: data=echo origin=ws://{server.HOST} lastEventId=",
        ],
    )


async def test_WS_038_should_work_with_base_url_regardless_of_scheme_casing(
    context_factory: Callable[..., Any], server: Server
) -> None:
    # baseURL schemes are case-insensitive, same as everywhere else in URL matching.
    context = await context_factory(base_url="HTTP://" + server.HOST)
    page = await context.new_page()

    def handler(ws: WebSocketRoute) -> None:
        ws.on_message(lambda message: ws.send(message))

    await page.route_web_socket("/ws", handler)

    await setup_ws(page, server, "blob")

    await page.evaluate(
        """async () => {
            await window.wsOpened;
            window.ws.send('echo');
        }"""
    )

    await expect_poll(
        page,
        lambda: page.evaluate("() => window.log"),
        [
            "open",
            f"message: data=echo origin=ws://{server.HOST} lastEventId=",
        ],
    )


async def test_WS_039_should_expose_protocols_to_the_route_handler(
    page: Page, server: Server
) -> None:
    routes: List[WebSocketRoute] = []
    await page.route_web_socket(re.compile(r".*"), lambda ws: routes.append(ws))

    await page.goto(server.EMPTY_PAGE)
    await page.evaluate(
        """({ host }) => {
            window.wsNone = new WebSocket('ws://' + host + '/ws-none');
            window.wsString = new WebSocket('ws://' + host + '/ws-string', 'chat.v1');
            window.wsArray = new WebSocket('ws://' + host + '/ws-array', ['chat.v2', 'chat.v1']);
        }""",
        {"host": server.HOST},
    )

    await expect_poll(page, lambda: len(routes), 3)

    by_url = {urlparse(r.url).path: r for r in routes}
    assert by_url["/ws-none"].protocols == []
    assert by_url["/ws-string"].protocols == ["chat.v1"]
    assert by_url["/ws-array"].protocols == ["chat.v2", "chat.v1"]


async def test_WS_040_should_expose_protocols_on_server_side_route(
    page: Page, server: Server
) -> None:
    promise: "asyncio.Future[Tuple[WebSocketRoute, WebSocketRoute]]" = asyncio.Future()

    def handler(ws: WebSocketRoute) -> None:
        server_route = ws.connect_to_server()
        promise.set_result((ws, server_route))

    await page.route_web_socket(re.compile(r".*"), handler)

    await setup_ws(page, server, "blob", ["chat.v2", "chat.v1"])
    page_route, server_route = await promise
    assert page_route.protocols == ["chat.v2", "chat.v1"]
    assert server_route.protocols == ["chat.v2", "chat.v1"]
