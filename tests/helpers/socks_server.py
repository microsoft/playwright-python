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

"""SOCKS5 servers for the proxy tests, in both flavors.

Port of the SOCKS5 server side of packages/utils/socksProxy.ts (RFC 1928, no
authentication, CONNECT only), with the two servers that the upstream tests use:

- MockSocksServer (tests/config/serverFixtures.ts, the socksPort fixture) answers
  every connection with a fixed page, "Served by the SOCKS proxy".
- SocksForwardingServer (setupSocksForwardingServer in tests/config/proxy.ts)
  connects allowed hosts to a local port.
"""

import socket
import struct
import threading
from typing import List, Optional, Set, Tuple

from tests.server import listen_localhost

_SUCCEEDED = 0x00
_CONNECTION_REFUSED = 0x05
_COMMAND_NOT_SUPPORTED = 0x07


def _recv_exact(sock: socket.socket, size: int) -> bytes:
    data = b""
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise ConnectionError("connection closed")
        data += chunk
    return data


def _socks_address(host: str) -> bytes:
    """ATYP and address of a reply, like ipToSocksAddress() upstream."""
    if host.lower().startswith("::ffff:") and "." in host:
        host = host[7:]
    try:
        return b"\x01" + socket.inet_pton(socket.AF_INET, host)
    except OSError:
        return b"\x04" + socket.inet_pton(socket.AF_INET6, host)


def _close_socket(sock: socket.socket) -> None:
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    sock.close()


class _SocksServer:
    """Accepts SOCKS5 connections; subclasses handle the CONNECT requests."""

    def __init__(self, dual_stack: bool) -> None:
        self._listeners, self.port = listen_localhost(128, ipv6=dual_stack)
        self._sockets: Set[socket.socket] = set()
        self._lock = threading.Lock()
        self._closed = False
        self._threads = [
            threading.Thread(target=self._accept_loop, args=(sock,), daemon=True)
            for sock in self._listeners
        ]
        for thread in self._threads:
            thread.start()

    def close(self) -> None:
        with self._lock:
            self._closed = True
            sockets = list(self._sockets)
            self._sockets.clear()
        for sock in self._listeners + sockets:
            _close_socket(sock)
        for thread in self._threads:
            thread.join()

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

    def _accept_loop(self, listener: socket.socket) -> None:
        while True:
            try:
                conn, _ = listener.accept()
            except OSError:
                return
            if self._track(conn):
                threading.Thread(target=self._serve, args=(conn,), daemon=True).start()

    def _serve(self, conn: socket.socket) -> None:
        try:
            request = self._handshake(conn)
            if request:
                self._on_connect(conn, *request)
        except (OSError, ValueError):
            pass
        finally:
            self._untrack(conn)

    def _handshake(self, conn: socket.socket) -> Optional[Tuple[str, int]]:
        """Reads the greeting and the request. Returns the CONNECT host and port."""
        version, methods_count = _recv_exact(conn, 2)
        if version != 0x05 or not methods_count:
            return None
        methods = _recv_exact(conn, methods_count)
        if 0x00 not in methods:
            conn.sendall(bytes([0x05, 0xFF]))
            return None
        conn.sendall(bytes([0x05, 0x00]))

        version, command, _, address_type = _recv_exact(conn, 4)
        if version != 0x05:
            return None
        if address_type == 0x01:
            host = socket.inet_ntop(socket.AF_INET, _recv_exact(conn, 4))
        elif address_type == 0x03:
            host = _recv_exact(conn, _recv_exact(conn, 1)[0]).decode()
        elif address_type == 0x04:
            tokens = struct.unpack("!8H", _recv_exact(conn, 16))
            host = ":".join(format(token, "x") for token in tokens)
        else:
            return None
        port = int.from_bytes(_recv_exact(conn, 2), "big")
        if command != 0x01:
            self._reply(conn, _COMMAND_NOT_SUPPORTED, "0.0.0.0", 0)
            return None
        return host, port

    def _reply(self, conn: socket.socket, code: int, host: str, port: int) -> None:
        conn.sendall(
            bytes([0x05, code, 0x00]) + _socks_address(host) + port.to_bytes(2, "big")
        )

    def _on_connect(self, conn: socket.socket, host: str, port: int) -> None:
        raise NotImplementedError


class MockSocksServer(_SocksServer):
    """Port of MockSocksServer in tests/config/serverFixtures.ts.

    Accepts every CONNECT request and answers the first data with a fixed page.
    """

    def __init__(self) -> None:
        # Upstream listens on all addresses: socks5://localhost may resolve to ::1.
        super().__init__(dual_stack=True)

    def _on_connect(self, conn: socket.socket, host: str, port: int) -> None:
        self._reply(conn, _SUCCEEDED, "127.0.0.1", 0)
        if not conn.recv(65536):
            return
        body = b"<html><title>Served by the SOCKS proxy</title></html>"
        conn.sendall(
            b"\r\n".join(
                [
                    b"HTTP/1.1 200 OK",
                    b"Connection: close",
                    b"Content-Type: text/html",
                    b"Content-Length: " + str(len(body)).encode(),
                    b"",
                    body,
                ]
            )
        )
        # sendSocketEnd(): end our side, then wait for the client to close.
        conn.shutdown(socket.SHUT_WR)
        while conn.recv(65536):
            pass


class SocksForwardingServer(_SocksServer):
    """Port of setupSocksForwardingServer in tests/config/proxy.ts.

    Connects CONNECT requests for a local host name and allowed_target_port to
    127.0.0.1:forward_port, and refuses the others.
    """

    def __init__(self, forward_port: int, allowed_target_port: int) -> None:
        self._forward_port = forward_port
        self._allowed_target_port = allowed_target_port
        self.connect_hosts: List[str] = []
        super().__init__(dual_stack=False)
        self.proxy_server_addr = f"socks5://127.0.0.1:{self.port}"

    def _on_connect(self, conn: socket.socket, host: str, port: int) -> None:
        if (
            host not in ("127.0.0.1", "fake-localhost-127-0-0-1.nip.io", "localhost")
            or port != self._allowed_target_port
        ):
            # sendSocketError() destroys the client socket.
            return
        try:
            target = socket.create_connection(("127.0.0.1", self._forward_port))
        except OSError:
            return
        if not self._track(target):
            return
        try:
            if f"{host}:{port}" not in self.connect_hosts:
                self.connect_hosts.append(f"{host}:{port}")
            local_host, local_port = target.getsockname()[:2]
            self._reply(conn, _SUCCEEDED, local_host, local_port)
            _pipe_both_ways(conn, target)
        finally:
            self._untrack(target)


def _pipe_both_ways(client: socket.socket, target: socket.socket) -> None:
    """Copies the bytes both ways until one side ends, then closes both."""

    def pipe(source: socket.socket, sink: socket.socket) -> None:
        while True:
            try:
                data = source.recv(65536)
            except OSError:
                data = b""
            if not data:
                break
            try:
                sink.sendall(data)
            except OSError:
                break
        _close_socket(client)
        _close_socket(target)

    other = threading.Thread(target=pipe, args=(target, client), daemon=True)
    other.start()
    pipe(client, target)
    other.join()
