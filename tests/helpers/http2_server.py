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

"""A minimal HTTP/2 server over TLS that answers every request with one fixed response.

It replaces createHttp2Server() (node:http2) that tests/library/har.spec.ts uses. It
implements only what a browser needs to load one page: the connection preface, SETTINGS,
PING, HEADERS (+ CONTINUATION) and one HEADERS + DATA response per request stream. The
response headers are HPACK-encoded as literals without Huffman coding; the request
headers are not decoded.
"""

import socket
import ssl
import struct
import threading
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

# The certificate of the HTTPS test server, like TestServer.certOptions() upstream.
_CERT_DIR = Path(__file__).resolve().parent.parent / "testserver"

_PREFACE = b"PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"

_DATA = 0x0
_HEADERS = 0x1
_SETTINGS = 0x4
_PING = 0x6
_GOAWAY = 0x7
_CONTINUATION = 0x9

_END_STREAM = 0x1
_ACK = 0x1
_END_HEADERS = 0x4


def _frame(frame_type: int, flags: int, stream_id: int, payload: bytes) -> bytes:
    length = len(payload)
    return (
        struct.pack(
            ">BHBBI", length >> 16, length & 0xFFFF, frame_type, flags, stream_id
        )
        + payload
    )


def _hpack_int(value: int, prefix_bits: int) -> bytes:
    limit = (1 << prefix_bits) - 1
    if value < limit:
        return bytes([value])
    result = bytearray([limit])
    value -= limit
    while value >= 128:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.append(value)
    return bytes(result)


def _hpack_encode(headers: Sequence[Tuple[str, str]]) -> bytes:
    block = bytearray()
    for name, value in headers:
        # Literal Header Field without Indexing, new name, no Huffman coding.
        block.append(0x00)
        for text in (name.encode(), value.encode()):
            block += _hpack_int(len(text), 7)
            block += text
    return bytes(block)


class Http2Server:
    """Listens on a free port of all the local addresses, like listen(0) in Node.js."""

    def __init__(self, headers: Sequence[Tuple[str, str]], body: bytes) -> None:
        self._context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self._context.load_cert_chain(
            str(_CERT_DIR / "cert.pem"), str(_CERT_DIR / "key.pem")
        )
        self._context.set_alpn_protocols(["h2"])
        self._headers = list(headers)
        self._body = body
        if socket.has_dualstack_ipv6():
            self._socket = socket.create_server(
                ("", 0), family=socket.AF_INET6, dualstack_ipv6=True
            )
        else:
            self._socket = socket.create_server(("127.0.0.1", 0))
        self.port: int = self._socket.getsockname()[1]
        self._connections: List[socket.socket] = []
        self._closed = False
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def close(self) -> None:
        self._closed = True
        self._socket.close()
        for connection in self._connections:
            try:
                connection.close()
            except OSError:
                pass

    def _accept_loop(self) -> None:
        while not self._closed:
            try:
                connection, _ = self._socket.accept()
            except OSError:
                return
            self._connections.append(connection)
            threading.Thread(
                target=self._serve, args=(connection,), daemon=True
            ).start()

    def _serve(self, raw_connection: socket.socket) -> None:
        try:
            connection = self._context.wrap_socket(raw_connection, server_side=True)
        except (OSError, ssl.SSLError):
            raw_connection.close()
            return
        self._connections.append(connection)
        try:
            self._serve_http2(connection)
        except (OSError, ssl.SSLError, ConnectionError):
            pass
        finally:
            connection.close()

    def _serve_http2(self, connection: ssl.SSLSocket) -> None:
        if _read_exactly(connection, len(_PREFACE)) != _PREFACE:
            return
        connection.sendall(_frame(_SETTINGS, 0, 0, b""))
        header_stream: Optional[int] = None
        while True:
            header = _read_exactly(connection, 9)
            if header is None:
                return
            length = (header[0] << 16) | (header[1] << 8) | header[2]
            frame_type, flags = header[3], header[4]
            stream_id = struct.unpack(">I", header[5:9])[0] & 0x7FFFFFFF
            payload = _read_exactly(connection, length) if length else b""
            if payload is None:
                return
            if frame_type == _SETTINGS and not flags & _ACK:
                connection.sendall(_frame(_SETTINGS, _ACK, 0, b""))
            elif frame_type == _PING and not flags & _ACK:
                connection.sendall(_frame(_PING, _ACK, 0, payload))
            elif frame_type == _GOAWAY:
                return
            elif frame_type in (_HEADERS, _CONTINUATION):
                if frame_type == _HEADERS:
                    header_stream = stream_id
                if flags & _END_HEADERS and header_stream is not None:
                    self._respond(connection, header_stream)
                    header_stream = None

    def _respond(self, connection: ssl.SSLSocket, stream_id: int) -> None:
        connection.sendall(
            _frame(_HEADERS, _END_HEADERS, stream_id, _hpack_encode(self._headers))
            + _frame(_DATA, _END_STREAM, stream_id, self._body)
        )


def _read_exactly(connection: ssl.SSLSocket, size: int) -> Optional[bytes]:
    data = bytearray()
    while len(data) < size:
        chunk = connection.recv(size - len(data))
        if not chunk:
            return None
        data += chunk
    return bytes(data)
