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

"""A WebSocket client for the tests, in both flavors.

It plays the part of the `ws` package's WebSocket client in upstream tests. It runs
on the reactor thread of the test server (tests/server.py), with autobahn.
"""

import threading
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from autobahn.twisted.websocket import (
    WebSocketClientFactory,
    WebSocketClientProtocol,
    connectWS,
)

from tests.server import WebSocketProtocol, reactor

Payload = Union[str, bytes]


class _ClientProtocol(WebSocketClientProtocol):
    def onOpen(self) -> None:
        getattr(self.factory, "client")._on_open(self)

    def onMessage(self, payload: bytes, isBinary: bool) -> None:
        getattr(self.factory, "client")._on_message(payload, isBinary)

    def onClose(
        self, wasClean: bool, code: Optional[int], reason: Optional[str]
    ) -> None:
        getattr(self.factory, "client")._on_close(code, reason)


class WebSocketClient:
    """Connects to url. The callbacks run on the reactor thread."""

    def __init__(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        on_open: Optional[Callable[[], None]] = None,
        on_message: Optional[Callable[[bytes, bool], None]] = None,
        on_close: Optional[Callable[[], None]] = None,
    ) -> None:
        self._on_open_callback = on_open
        self._on_message_callback = on_message
        self._on_close_callback = on_close
        self._protocol: Optional[_ClientProtocol] = None
        self._pending: List[Tuple[bytes, bool]] = []
        self.opened = threading.Event()
        self.closed = threading.Event()
        factory = WebSocketClientFactory(url, headers=headers or {})
        factory.protocol = _ClientProtocol
        # Like the upstream tests: no compression, messages up to 256Mb.
        factory.setProtocolOptions(
            maxMessagePayloadSize=256 * 1024 * 1024,
            maxFramePayloadSize=256 * 1024 * 1024,
        )
        setattr(factory, "client", self)
        setattr(
            factory,
            "clientConnectionFailed",
            lambda connector, reason: self._on_close(None, str(reason)),
        )
        reactor.callFromThread(connectWS, factory)

    def _on_open(self, protocol: _ClientProtocol) -> None:
        self._protocol = protocol
        self.opened.set()
        for payload, is_binary in self._pending:
            protocol.sendMessage(payload, is_binary)
        self._pending.clear()
        if self._on_open_callback:
            self._on_open_callback()

    def _on_message(self, payload: bytes, is_binary: bool) -> None:
        if self._on_message_callback:
            self._on_message_callback(payload, is_binary)

    def _on_close(self, code: Optional[int], reason: Optional[str]) -> None:
        if self.closed.is_set():
            return
        self.closed.set()
        if self._on_close_callback:
            self._on_close_callback()

    def send(self, payload: Payload, is_binary: bool = False) -> None:
        """Sends a message, after the connection opens. Callable from any thread."""
        data = payload.encode() if isinstance(payload, str) else payload

        def send() -> None:
            if self._protocol:
                self._protocol.sendMessage(data, is_binary)
            else:
                self._pending.append((data, is_binary))

        reactor.callFromThread(send)

    def close(self) -> None:
        """Closes the connection. Callable from any thread."""

        def close() -> None:
            if self._protocol:
                self._protocol.sendClose()

        reactor.callFromThread(close)


def forward_web_socket(server_ws: WebSocketProtocol, url: str) -> None:
    """Forwards a test server WebSocket connection to url, both ways.

    Sends the x-playwright-* headers of the server connection's request along.
    Port of the proxy in the 'should connect over wss' test of
    tests/library/browsertype-connect.spec.ts.
    """
    headers = {
        name: value
        for name, value in server_ws.http_headers.items()
        if name.startswith("x-playwright")
    }
    remote = WebSocketClient(
        url,
        headers=headers,
        on_message=lambda payload, is_binary: server_ws.sendMessage(payload, is_binary),
        on_close=lambda: server_ws.sendClose(),
    )

    def on_message(payload: Any, is_binary: bool) -> None:
        remote.send(payload, is_binary)

    server_ws.events.on("message", on_message)
    server_ws.events.on("close", lambda code, reason: remote.close())
