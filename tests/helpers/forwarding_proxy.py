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

"""Proxies that forward every connection to one local port, in both flavors.

Ports of tests/config/proxy.ts:

- ConnectForwardingProxy is the TestProxy of the proxyServer fixture, with
  forwardTo(port, { allowConnectRequests: true }), for CONNECT requests (the requests
  that proxy HTTPS). It tunnels each CONNECT to 127.0.0.1:port and lists the CONNECT
  targets in connect_hosts. Other requests are not supported.
- SocksForwardingServer is setupSocksForwardingServer({ forwardPort, allowedTargetPort }):
  a SOCKS5 proxy that tunnels the connections to the allowed target to 127.0.0.1:forwardPort
  and lists the targets in connect_hosts.
"""

import socket
import struct
import threading
from typing import List, Optional, Set

_HEAD_END = b"\r\n\r\n"

# Certain browsers perform telemetry requests which we want to ignore.
_CONNECT_HOSTS_TO_IGNORE = {"www.bing.com:443", "www.google.com:443"}


class _Server:
    """Accepts connections on a thread; serves each one in _serve() on a thread of its own."""

    def __init__(self, listener: socket.socket) -> None:
        self._listener = listener
        self.port: int = listener.getsockname()[1]
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
                threading.Thread(target=self._run, args=(client,), daemon=True).start()

    def _run(self, client: socket.socket) -> None:
        try:
            self._serve(client)
        except OSError:
            pass
        finally:
            self._untrack(client)

    def _serve(self, client: socket.socket) -> None:
        raise NotImplementedError

    def _tunnel(self, client: socket.socket, upstream: socket.socket) -> None:
        """Copies the data both ways until both sides end."""
        if not self._track(upstream):
            return
        try:
            pump = threading.Thread(target=_pipe, args=(upstream, client), daemon=True)
            pump.start()
            _pipe(client, upstream)
            pump.join()
        finally:
            self._untrack(upstream)


class ConnectForwardingProxy(_Server):
    """An HTTP proxy for CONNECT requests. Listens on all the local addresses, like
    server.listen(port) in Node.js. Call forward_to(port) to accept CONNECT requests."""

    def __init__(self) -> None:
        if socket.has_dualstack_ipv6():
            listener = socket.create_server(
                ("", 0), family=socket.AF_INET6, dualstack_ipv6=True
            )
        else:
            listener = socket.create_server(("127.0.0.1", 0))
        super().__init__(listener)
        self.PORT = self.port
        # The host:port of each CONNECT request, in order.
        self.connect_hosts: List[str] = []
        self._forward_port: Optional[int] = None

    def forward_to(self, port: int) -> None:
        """Port of forwardTo(port, { allowConnectRequests: true })."""
        self._forward_port = port

    def _serve(self, client: socket.socket) -> None:
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
        target = parts[1]
        host, _, port = target.rpartition(":")
        address = (host.strip("[]"), int(port))
        if self._forward_port is not None and target not in _CONNECT_HOSTS_TO_IGNORE:
            self.connect_hosts.append(target)
            address = ("127.0.0.1", self._forward_port)
        try:
            upstream = socket.create_connection(address)
        except OSError:
            client.sendall(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\n\r\n")
            return
        client.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        if rest:
            upstream.sendall(rest)
        self._tunnel(client, upstream)


class SocksForwardingServer(_Server):
    """Port of setupSocksForwardingServer() in tests/config/proxy.ts. Listens on 127.0.0.1."""

    ALLOWED_HOSTS = ("127.0.0.1", "fake-localhost-127-0-0-1.nip.io", "localhost")

    def __init__(self, forward_port: int, allowed_target_port: int) -> None:
        self._forward_port = forward_port
        self._allowed_target_port = allowed_target_port
        # The distinct host:port targets of the connections, in order.
        self.connect_hosts: List[str] = []
        listener = socket.create_server(("127.0.0.1", 0))
        super().__init__(listener)
        self.proxy_server_addr = f"socks5://127.0.0.1:{self.port}"

    def _serve(self, client: socket.socket) -> None:
        greeting = _recv_exactly(client, 2)
        if not greeting or greeting[0] != 5:
            return
        if _recv_exactly(client, greeting[1]) is None:
            return
        # No authentication.
        client.sendall(b"\x05\x00")
        request = _recv_exactly(client, 4)
        if not request:
            return
        command, address_type = request[1], request[3]
        host: Optional[str] = None
        if address_type == 1:
            raw = _recv_exactly(client, 4)
            host = socket.inet_ntop(socket.AF_INET, raw) if raw else None
        elif address_type == 3:
            size = _recv_exactly(client, 1)
            name = _recv_exactly(client, size[0]) if size else None
            host = name.decode() if name is not None else None
        elif address_type == 4:
            raw = _recv_exactly(client, 16)
            host = socket.inet_ntop(socket.AF_INET6, raw) if raw else None
        raw_port = _recv_exactly(client, 2)
        if host is None or raw_port is None:
            return
        port = struct.unpack(">H", raw_port)[0]
        if command != 1:
            # Command not supported.
            client.sendall(_socks_reply(7))
            return
        if host not in self.ALLOWED_HOSTS or port != self._allowed_target_port:
            client.sendall(_socks_reply(5))
            return
        try:
            upstream = socket.create_connection(("127.0.0.1", self._forward_port))
        except OSError:
            client.sendall(_socks_reply(5))
            return
        if f"{host}:{port}" not in self.connect_hosts:
            self.connect_hosts.append(f"{host}:{port}")
        local_host, local_port = upstream.getsockname()[:2]
        client.sendall(_socks_reply(0, local_host, local_port))
        self._tunnel(client, upstream)


def _socks_reply(code: int, host: str = "0.0.0.0", port: int = 0) -> bytes:
    return (
        bytes([5, code, 0, 1])
        + socket.inet_pton(socket.AF_INET, host)
        + struct.pack(">H", port)
    )


def _recv_exactly(sock: socket.socket, size: int) -> Optional[bytes]:
    data = b""
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            return None
        data += chunk
    return data


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
