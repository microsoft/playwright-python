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

"""Calls on the test server's WebSocket connections from a test, in both flavors.

A connection of the test server (tests.server.WebSocketProtocol) runs on the reactor
thread. These functions do from the test thread what upstream tests do with a `ws`
WebSocket of the test server.
"""

from typing import Optional, Union

from tests.server import WebSocketProtocol, reactor


def send(ws: WebSocketProtocol, data: Union[str, bytes]) -> None:
    """Like ws.send(data) in Node.js: a str is a text message, bytes a binary one."""
    if isinstance(data, str):
        reactor.callFromThread(ws.sendMessage, data.encode(), False)
    else:
        reactor.callFromThread(ws.sendMessage, data, True)


def close(
    ws: WebSocketProtocol, code: Optional[int] = None, reason: Optional[str] = None
) -> None:
    """Like ws.close(code, reason) in Node.js."""
    reactor.callFromThread(close_on_reactor_thread, ws, code, reason)


def close_on_reactor_thread(
    ws: WebSocketProtocol, code: Optional[int] = None, reason: Optional[str] = None
) -> None:
    """close() for the reactor thread, for example in a handler of the connection.

    Unlike autobahn's sendClose(), it sends any close code, as the `ws` package does.
    """
    ws.sendCloseFrame(
        code=code,
        reasonUtf8=reason.encode() if reason is not None else None,
        isReply=False,
    )


def to_text(payload: Union[str, bytes]) -> str:
    """Like data.toString() on a message of a `ws` WebSocket."""
    return payload.decode() if isinstance(payload, bytes) else payload
