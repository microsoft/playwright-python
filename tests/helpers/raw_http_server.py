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

"""An HTTP(S) server that gives each connection to the test, in both flavors.

The test server (tests/server.py, twisted) reads the whole request body before a route
runs. Tests that must answer before they read the body, or that need their own TLS
certificate (like utils.createHttpsServer upstream), use this server. It reads the
request head, then calls the handler with the socket and the head. The handler writes
the response; the server closes the socket when the handler returns.
"""

import socket
import ssl
import threading
from typing import Callable, List, Optional, Set

RawHandler = Callable[[socket.socket, bytes], None]


class RawHttpServer:
    """Listens on 127.0.0.1, on a free port. Pass ssl_context for HTTPS."""

    def __init__(
        self, handler: RawHandler, ssl_context: Optional[ssl.SSLContext] = None
    ) -> None:
        self._handler = handler
        self._ssl_context = ssl_context
        self._listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._listener.bind(("127.0.0.1", 0))
        self._listener.listen(64)
        self.port: int = self._listener.getsockname()[1]
        scheme = "https" if ssl_context else "http"
        self.PREFIX = f"{scheme}://127.0.0.1:{self.port}"
        # The head (request line and headers) of each request, in order.
        self.heads: List[bytes] = []
        self._sockets: Set[socket.socket] = set()
        self._lock = threading.Lock()
        self._closed = False
        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()

    def close(self) -> None:
        with self._lock:
            self._closed = True
            sockets = list(self._sockets)
            self._sockets.clear()
        for sock in [self._listener, *sockets]:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()
        self._thread.join()

    def _accept_loop(self) -> None:
        while True:
            try:
                conn, _ = self._listener.accept()
            except OSError:
                return
            with self._lock:
                if self._closed:
                    conn.close()
                    return
                self._sockets.add(conn)
            threading.Thread(target=self._serve, args=(conn,), daemon=True).start()

    def _serve(self, conn: socket.socket) -> None:
        sock = conn
        try:
            if self._ssl_context:
                sock = self._ssl_context.wrap_socket(conn, server_side=True)
            head = b""
            while b"\r\n\r\n" not in head:
                chunk = sock.recv(1)
                if not chunk:
                    return
                head += chunk
            self.heads.append(head)
            self._handler(sock, head)
        except OSError:
            pass
        finally:
            with self._lock:
                self._sockets.discard(conn)
            sock.close()


def write_response(
    sock: socket.socket, status: str, headers: List[str], body: bytes = b""
) -> None:
    """Writes a response that closes the connection; status is like "200 OK"."""
    lines = [
        f"HTTP/1.1 {status}",
        *headers,
        f"Content-Length: {len(body)}",
        "Connection: close",
    ]
    sock.sendall(("\r\n".join(lines) + "\r\n\r\n").encode() + body)
