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
from typing import Union

import pytest
from flaky import flaky

from playwright.async_api import Error, Page, WebSocket
from tests.conftest import WebSocketServerServer
from tests.server import Server


async def test_should_work(page: Page, ws_server: WebSocketServerServer) -> None:
    value = await page.evaluate(
        """port => {
        let cb;
        const result = new Promise(f => cb = f);
        const ws = new WebSocket('ws://localhost:' + port + '/ws');
        ws.addEventListener('message', data => { ws.close(); cb(data.data); });
        return result;
    }""",
        ws_server.PORT,
    )
    assert value == "incoming"
    pass


async def test_should_emit_close_events(
    page: Page, ws_server: WebSocketServerServer
) -> None:
    async with page.expect_websocket() as ws_info:
        await page.evaluate(
            """port => {
            let cb;
            const result = new Promise(f => cb = f);
            const ws = new WebSocket('ws://localhost:' + port + '/ws');
            ws.addEventListener('message', data => { ws.close(); cb(data.data); });
            return result;
        }""",
            ws_server.PORT,
        )
    ws = await ws_info.value
    assert ws.url == f"ws://localhost:{ws_server.PORT}/ws"
    assert repr(ws) == f"<WebSocket url={ws.url!r}>"
    if not ws.is_closed():
        await ws.wait_for_event("close")
    assert ws.is_closed()


async def test_should_emit_frame_events(
    page: Page, ws_server: WebSocketServerServer
) -> None:
    log = []
    socke_close_future: "asyncio.Future[None]" = asyncio.Future()

    def on_web_socket(ws: WebSocket) -> None:
        log.append("open")

        def _on_framesent(payload: Union[bytes, str]) -> None:
            assert isinstance(payload, str)
            log.append(f"sent<{payload}>")

        ws.on("framesent", _on_framesent)

        def _on_framereceived(payload: Union[bytes, str]) -> None:
            assert isinstance(payload, str)
            log.append(f"received<{payload}>")

        ws.on("framereceived", _on_framereceived)

        def _handle_close(ws: WebSocket) -> None:
            log.append("close")
            socke_close_future.set_result(None)

        ws.on("close", _handle_close)

    page.on("websocket", on_web_socket)
    async with page.expect_event("websocket"):
        await page.evaluate(
            """port => {
            const ws = new WebSocket('ws://localhost:' + port + '/ws');
            ws.addEventListener('open', () => ws.send('outgoing'));
            ws.addEventListener('message', () => ws.close())
        }""",
            ws_server.PORT,
        )
    await socke_close_future
    assert log[0] == "open"
    assert log[3] == "close"
    log.sort()
    assert log == ["close", "open", "received<incoming>", "sent<outgoing>"]


async def test_should_emit_binary_frame_events(
    page: Page, ws_server: WebSocketServerServer
) -> None:
    done_task: "asyncio.Future[None]" = asyncio.Future()
    sent = []
    received = []

    def on_web_socket(ws: WebSocket) -> None:
        ws.on("framesent", lambda payload: sent.append(payload))
        ws.on("framereceived", lambda payload: received.append(payload))
        ws.on("close", lambda _: done_task.set_result(None))

    page.on("websocket", on_web_socket)
    async with page.expect_event("websocket"):
        await page.evaluate(
            """port => {
            const ws = new WebSocket('ws://localhost:' + port + '/ws');
            ws.addEventListener('open', () => {
                const binary = new Uint8Array(5);
                for (let i = 0; i < 5; ++i)
                    binary[i] = i;
                ws.send(binary);
                ws.send('echo-bin');
            });
        }""",
            ws_server.PORT,
        )
    await done_task
    assert sent == [b"\x00\x01\x02\x03\x04", "echo-bin"]
    assert received == ["incoming", b"\x04\x02"]


@flaky
async def test_should_reject_wait_for_event_on_close_and_error(
    page: Page, ws_server: WebSocketServerServer
) -> None:
    async with page.expect_event("websocket") as ws_info:
        await page.evaluate(
            """port => {
            window.ws = new WebSocket('ws://localhost:' + port + '/ws');
        }""",
            ws_server.PORT,
        )
    ws = await ws_info.value
    await ws.wait_for_event("framereceived")
    with pytest.raises(Error) as exc_info:
        async with ws.expect_event("framesent"):
            await page.evaluate("window.ws.close()")
    assert exc_info.value.message == "Socket closed"


async def test_should_emit_error_event(
    page: Page, server: Server, browser_name: str
) -> None:
    future: "asyncio.Future[str]" = asyncio.Future()

    def _on_ws_socket_error(err: str) -> None:
        future.set_result(err)

    def _on_websocket(websocket: WebSocket) -> None:
        websocket.on("socketerror", _on_ws_socket_error)

    page.on(
        "websocket",
        _on_websocket,
    )
    await page.evaluate(
        """port => new WebSocket(`ws://localhost:${port}/bogus-ws`)""",
        server.PORT,
    )
    err = await future
    if browser_name == "firefox":
        assert err == "CLOSE_ABNORMAL"
    else:
        assert ": 404" in err
