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

"""An HTTP CONNECT proxy that resolves host names with a given function, in both flavors.

Upstream tests in tests/library/browsercontext-fetch.spec.ts pass { __testHookLookup } as
an untyped request option: a Node.js function that the request uses in place of the DNS
lookup, so that a host such as www.my.playwright.dev reaches the local test server. Only
the in-process Node.js client can pass a function. The Python tests get the same effect
with this proxy: the browser context sends its API requests through it
(proxy={"server": proxy.server}), and the proxy connects each CONNECT tunnel to the address
that the lookup function returns for the host. The request inside the tunnel, with its
Host and Cookie headers, is the request that the upstream test sends directly.

Unlike tests/helpers/lookup_proxy.py, the test gives the lookup function.
"""

import socket
import threading
from typing import Callable, List, Set

_HEAD_END = b"\r\n\r\n"


class ResolvingProxy:
    """Listens on 127.0.0.1 and tunnels CONNECT host:port to lookup(host):port.

    lookup returns an IP address, or raises an exception to fail the host (the proxy
    then answers 502). lookups lists the host names that the proxy looked up.
    """

    def __init__(self, lookup: Callable[[str], str]) -> None:
        self._lookup = lookup
        self.lookups: List[str] = []
        self._sockets: Set[socket.socket] = set()
        self._lock = threading.Lock()
        self._closed = False
        self._listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listener.bind(("127.0.0.1", 0))
        self._listener.listen(64)
        self.port: int = self._listener.getsockname()[1]
        self.server = f"http://127.0.0.1:{self.port}"
        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()

    def close(self) -> None:
        with self._lock:
            self._closed = True
            sockets = list(self._sockets)
            self._sockets.clear()
        for sock in [self._listener, *sockets]:
            _close_socket(sock)
        self._thread.join()

    def _track(self, sock: socket.socket) -> bool:
        with self._lock:
            if self._closed:
                _close_socket(sock)
                return False
            self._sockets.add(sock)
            return True

    def _untrack(self, sock: socket.socket) -> None:
        with self._lock:
            self._sockets.discard(sock)
        _close_socket(sock)

    def _accept_loop(self) -> None:
        while True:
            try:
                client, _ = self._listener.accept()
            except OSError:
                return
            if self._track(client):
                threading.Thread(
                    target=self._serve, args=(client,), daemon=True
                ).start()

    def _serve(self, client: socket.socket) -> None:
        try:
            head = b""
            while _HEAD_END not in head:
                chunk = client.recv(65536)
                if not chunk:
                    return
                head += chunk
            head, rest = head.split(_HEAD_END, 1)
            parts = head.split(b"\r\n", 1)[0].decode("latin-1").split(" ")
            if len(parts) != 3 or parts[0].upper() != "CONNECT":
                client.sendall(
                    b"HTTP/1.1 405 Method Not Allowed\r\nContent-Length: 0\r\n\r\n"
                )
                return
            host, _, port = parts[1].rpartition(":")
            host = host.strip("[]")
            self.lookups.append(host)
            try:
                upstream = socket.create_connection((self._lookup(host), int(port)))
            except Exception:
                client.sendall(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\n\r\n")
                return
            if not self._track(upstream):
                return
            try:
                client.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                if rest:
                    upstream.sendall(rest)
                pump = threading.Thread(
                    target=_pipe, args=(upstream, client), daemon=True
                )
                pump.start()
                _pipe(client, upstream)
                pump.join()
            finally:
                self._untrack(upstream)
        except OSError:
            pass
        finally:
            self._untrack(client)


def _pipe(source: socket.socket, target: socket.socket) -> None:
    """Copies source to target until source ends, then ends target."""
    while True:
        try:
            data = source.recv(65536)
        except OSError:
            data = b""
        if not data:
            break
        try:
            target.sendall(data)
        except OSError:
            break
    try:
        target.shutdown(socket.SHUT_WR)
    except OSError:
        pass


def _close_socket(sock: socket.socket) -> None:
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    sock.close()
