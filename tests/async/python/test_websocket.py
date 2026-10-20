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

from playwright.async_api import Page, WebSocket
from tests.server import Server, WebSocketProtocol


async def test_should_emit_close_events(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    close_future: asyncio.Future[None] = asyncio.Future()
    async with page.expect_websocket() as ws_info:
        await page.evaluate(
            """port => {
            const ws = new WebSocket('ws://localhost:' + port + '/ws');
            ws.addEventListener('open', data => ws.close());
        }""",
            server.PORT,
        )
    ws = await ws_info.value
    ws.on("close", lambda ws: close_future.set_result(None))
    assert ws.url == f"ws://localhost:{server.PORT}/ws"
    assert repr(ws) == f"<WebSocket url={ws.url!r}>"
    await close_future
    assert ws.is_closed()


async def test_should_emit_binary_frame_events(page: Page, server: Server) -> None:
    def _handle_ws_connection(ws: WebSocketProtocol) -> None:
        ws.sendMessage(b"incoming")

        def _onMessage(payload: bytes, isBinary: bool) -> None:
            if payload == b"echo-bin":
                ws.sendMessage(b"\x04\x02", True)
                ws.sendClose()
            if payload == b"echo-text":
                ws.sendMessage(b"text", False)
                ws.sendClose()

        setattr(ws, "onMessage", _onMessage)

    server.once_web_socket_connection(_handle_ws_connection)
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
            server.PORT,
        )
    await done_task
    assert sent == [b"\x00\x01\x02\x03\x04", "echo-bin"]
    assert received == ["incoming", b"\x04\x02"]
