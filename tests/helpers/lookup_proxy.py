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

"""A proxy that resolves host names like upstream's __testHookLookup, in both flavors.

Upstream tests in tests/library/global-fetch-cookie.spec.ts pass a __testHookLookup
function as a fetch option, so that host names such as a.b.one.com resolve to
127.0.0.1. Only the in-process Node.js client can pass a function. The Python tests
send the requests through this proxy instead (the proxy option of
APIRequest.new_context()). The API request context opens a CONNECT tunnel for each
request; the proxy resolves the host with lookup_host() and connects the tunnel to
that address. The cookie jar still sees the original URL.
"""

import select
import socket
import threading
from typing import Set

from playwright._impl._api_structures import ProxySettings


def lookup_host(hostname: str) -> str:
    """Port of __testHookLookup in tests/library/global-fetch-cookie.spec.ts."""
    hostname = hostname.lower()
    if (
        hostname.endswith("localhost")
        or hostname.endswith("one.com")
        or hostname.endswith("two.com")
    ):
        return "127.0.0.1"
    raise Exception(f"Failed to resolve hostname: {hostname}")


class LookupProxy:
    """A CONNECT proxy on 127.0.0.1 that resolves each host with lookup_host()."""

    def __init__(self) -> None:
        self._listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._listener.bind(("127.0.0.1", 0))
        self._listener.listen(64)
        self.port: int = self._listener.getsockname()[1]
        self._sockets: Set[socket.socket] = set()
        self._lock = threading.Lock()
        self._closed = False
        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()

    @property
    def settings(self) -> ProxySettings:
        """The proxy option for APIRequest.new_context()."""
        return {"server": f"http://127.0.0.1:{self.port}"}

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

    def _track(self, sock: socket.socket) -> bool:
        with self._lock:
            if self._closed:
                sock.close()
                return False
            self._sockets.add(sock)
            return True

    def _untrack(self, sock: socket.socket) -> None:
        with self._lock:
            self._sockets.discard(sock)
        sock.close()

    def _accept_loop(self) -> None:
        while True:
            try:
                conn, _ = self._listener.accept()
            except OSError:
                return
            if self._track(conn):
                threading.Thread(target=self._serve, args=(conn,), daemon=True).start()

    def _serve(self, conn: socket.socket) -> None:
        try:
            data = b""
            while b"\r\n\r\n" not in data:
                chunk = conn.recv(65536)
                if not chunk:
                    return
                data += chunk
            head, rest = data.split(b"\r\n\r\n", 1)
            method, target = head.split(b"\r\n", 1)[0].decode().split(" ")[:2]
            if method != "CONNECT":
                conn.sendall(
                    b"HTTP/1.1 405 Method Not Allowed\r\nContent-Length: 0\r\n\r\n"
                )
                return
            host, _, port = target.rpartition(":")
            try:
                upstream = socket.create_connection(
                    (lookup_host(host.strip("[]")), int(port))
                )
            except Exception:
                conn.sendall(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\n\r\n")
                return
            if not self._track(upstream):
                return
            try:
                conn.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                if rest:
                    upstream.sendall(rest)
                self._pipe(conn, upstream)
            finally:
                self._untrack(upstream)
        except OSError:
            pass
        finally:
            self._untrack(conn)

    def _pipe(self, a: socket.socket, b: socket.socket) -> None:
        # Copies the bytes both ways until one side closes the connection.
        while True:
            readable, _, _ = select.select([a, b], [], [])
            for source in readable:
                data = source.recv(65536)
                if not data:
                    return
                (b if source is a else a).sendall(data)
