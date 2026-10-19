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

"""TLS servers for the client certificate tests, in both flavors.

Ports of the servers in tests/library/client-certificates.spec.ts, which upstream makes
with Node.js (createHttpsServer, createHttp2Server, tls.createServer) and the files in
tests/assets/client-certificates:

- ClientCertificateServer: the server of the startCCServer fixture. It asks for a client
  certificate and answers HTTP/1.1, or HTTP/2 (h2, with an optional HTTP/1.1 fallback).
- HandshakeRejectingServer: the tls.createServer of 'should not hang on tls errors
  during TLS 1.2 handshake', which drops each connection in the TLS handshake.
- RenegotiatingServer: the server of 'should handle TLS renegotiation with client
  certificates', which asks for the client certificate in a TLS 1.2 renegotiation.

The servers use pyOpenSSL, which, like Node.js, can ask for a client certificate and accept
a certificate that it can not verify (Node.js reports it with tlsSocket.authorized).
Each connection runs on a thread of its own.
"""

import gzip
import select
import socket
import struct
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from cryptography import x509
from OpenSSL import SSL, crypto

CERT_DIR = Path(__file__).resolve().parent.parent / "assets" / "client-certificates"
SERVER_CERT = CERT_DIR / "server" / "server_cert.pem"
SERVER_KEY = CERT_DIR / "server" / "server_key.pem"


@dataclass
class PeerInfo:
    """What Node.js reports on the TLS socket of a request."""

    # tlsSocket.alpnProtocol and tlsSocket.servername; None is false in Node.js.
    alpn_protocol: Optional[str]
    servername: Optional[str]
    # The common names of tlsSocket.getPeerCertificate(); None without a certificate.
    subject_cn: Optional[str]
    issuer_cn: Optional[str]
    # tlsSocket.authorized: the client certificate was verified with the CA.
    authorized: bool


# The status, the headers and the body of a response.
Response = Tuple[int, Dict[str, str], bytes]


def cc_server_response(peer: PeerInfo) -> Response:
    """The request handler of the startCCServer fixture."""

    def js(value: Optional[str]) -> str:
        return "false" if value is None else value

    parts = [
        ("alpn-protocol", js(peer.alpn_protocol)),
        ("servername", js(peer.servername)),
    ]
    if peer.authorized:
        status = 200
        message = (
            f"Hello {peer.subject_cn}, your certificate was issued by {peer.issuer_cn}!"
        )
    elif peer.subject_cn is not None:
        status = 403
        message = f"Sorry {peer.subject_cn}, certificates from {peer.issuer_cn} are not welcome here."
    else:
        status = 401
        message = "Sorry, but you need to provide a client certificate to continue."
    parts.append(("message", message))
    body = "".join(f'<div data-testid="{key}">{value}</div>' for key, value in parts)
    return status, {"Content-Type": "text/html"}, body.encode()


def _server_context(
    request_cert: bool, min_version: int = 0, max_version: int = 0
) -> SSL.Context:
    """Like the TLS options { key, cert, ca: [cert], requestCert } in Node.js."""
    context = SSL.Context(SSL.TLS_SERVER_METHOD)
    context.use_certificate_file(str(SERVER_CERT))
    context.use_privatekey_file(str(SERVER_KEY))
    context.load_verify_locations(str(SERVER_CERT))
    # OpenSSL needs a session id context to resume sessions with client certificates.
    context.set_session_id(b"playwright-tests")
    context.add_client_ca(x509.load_pem_x509_certificate(SERVER_CERT.read_bytes()))
    if min_version:
        context.set_min_proto_version(min_version)
    if max_version:
        context.set_max_proto_version(max_version)
    if request_cert:
        context.set_verify(SSL.VERIFY_PEER, _accept_and_record)
    return context


class _VerifyState:
    def __init__(self) -> None:
        self.failed = False


def _accept_and_record(
    connection: SSL.Connection, cert: crypto.X509, errno: int, depth: int, ok: int
) -> bool:
    """Accepts any client certificate, and records whether it failed verification.

    Node.js does the same: it decides about rejectUnauthorized after the handshake.
    """
    if not ok:
        connection.get_app_data().failed = True
    return True


def _peer_info(connection: SSL.Connection) -> PeerInfo:
    alpn = connection.get_alpn_proto_negotiated()
    servername = connection.get_servername()
    cert = connection.get_peer_certificate()
    state: _VerifyState = connection.get_app_data()
    return PeerInfo(
        alpn_protocol=alpn.decode() if alpn else None,
        servername=servername.decode() if servername else None,
        subject_cn=cert.get_subject().CN if cert else None,
        issuer_cn=cert.get_issuer().CN if cert else None,
        authorized=cert is not None and not state.failed,
    )


def _listen(host: str) -> List[socket.socket]:
    """Listens on host and a free port. "localhost" is 127.0.0.1 and ::1, on one port."""
    addresses = ["127.0.0.1", "::1"] if host == "localhost" else [host]
    listeners: List[socket.socket] = []
    port = 0
    for address in addresses:
        family = socket.AF_INET6 if ":" in address else socket.AF_INET
        try:
            listener = socket.socket(family, socket.SOCK_STREAM)
            listener.bind((address, port))
        except OSError:
            if not listeners:
                raise
            continue
        listener.listen(64)
        port = listener.getsockname()[1]
        listeners.append(listener)
    return listeners


def _close_socket(sock: socket.socket) -> None:
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    sock.close()


class TlsServer:
    """Accepts TLS connections; a subclass serves each connection in serve()."""

    def __init__(self, context: SSL.Context, host: str = "127.0.0.1") -> None:
        self._context = context
        self._lock = threading.Lock()
        self._sockets: Set[socket.socket] = set()
        self._closed = False
        self._listeners = _listen(host)
        self.port: int = self._listeners[0].getsockname()[1]
        self._threads = [
            threading.Thread(target=self._accept_loop, args=(listener,), daemon=True)
            for listener in self._listeners
        ]
        for thread in self._threads:
            thread.start()

    def close(self) -> None:
        """Stops listening and closes the open connections, like decorateServer()."""
        with self._lock:
            self._closed = True
            sockets = list(self._sockets)
            self._sockets.clear()
        for sock in [*self._listeners, *sockets]:
            _close_socket(sock)
        for thread in self._threads:
            thread.join()

    def serve(self, connection: "TlsConnection") -> None:
        raise NotImplementedError

    def _accept_loop(self, listener: socket.socket) -> None:
        while True:
            try:
                raw, _ = listener.accept()
            except OSError:
                return
            with self._lock:
                if self._closed:
                    _close_socket(raw)
                    return
                self._sockets.add(raw)
            threading.Thread(target=self._handle, args=(raw,), daemon=True).start()

    def _handle(self, raw: socket.socket) -> None:
        connection = SSL.Connection(self._context, raw)
        connection.set_app_data(_VerifyState())
        connection.set_accept_state()
        try:
            connection.do_handshake()
            self.serve(TlsConnection(connection, raw))
        except (SSL.Error, OSError):
            pass
        finally:
            with self._lock:
                self._sockets.discard(raw)
            _close_socket(raw)


class TlsConnection:
    """A server TLS connection with a read buffer."""

    def __init__(self, connection: SSL.Connection, raw: socket.socket) -> None:
        self.ssl = connection
        self.raw = raw
        self._buffer = b""

    @property
    def peer(self) -> PeerInfo:
        return _peer_info(self.ssl)

    def _fill(self) -> bool:
        try:
            data = self.ssl.recv(65536)
        except (SSL.ZeroReturnError, SSL.SysCallError):
            return False
        if not data:
            return False
        self._buffer += data
        return True

    def read_until(self, marker: bytes) -> Optional[bytes]:
        """Returns the data up to and with marker, or None when the peer ends first."""
        while marker not in self._buffer:
            if not self._fill():
                return None
        index = self._buffer.index(marker) + len(marker)
        data, self._buffer = self._buffer[:index], self._buffer[index:]
        return data

    def read_exactly(self, size: int) -> Optional[bytes]:
        while len(self._buffer) < size:
            if not self._fill():
                return None
        data, self._buffer = self._buffer[:size], self._buffer[size:]
        return data

    def send(self, data: bytes) -> None:
        self.ssl.sendall(data)

    def renegotiate(self, timeout: float = 10) -> None:
        """Renegotiates TLS 1.2 and asks for a client certificate.

        Like tlsSocket.renegotiate({ requestCert: true, rejectUnauthorized: false }):
        returns when the new handshake is done.
        """
        self.ssl.set_verify(SSL.VERIFY_PEER, _accept_and_record)
        self.ssl.renegotiate()
        # Sends the HelloRequest. The client answers with a new handshake, which
        # OpenSSL runs when it reads from the connection.
        self.ssl.do_handshake()
        deadline = time.monotonic() + timeout
        self.raw.setblocking(False)
        try:
            while self.ssl.renegotiate_pending():
                if time.monotonic() > deadline:
                    raise TimeoutError("TLS renegotiation did not complete")
                select.select([self.raw], [], [], 0.1)
                try:
                    self._buffer += self.ssl.recv(65536)
                except SSL.WantReadError:
                    pass
        finally:
            self.raw.setblocking(True)


@dataclass
class HttpRequest:
    method: str
    path: str
    headers: Dict[str, str]
    body: bytes


def read_http_request(connection: TlsConnection) -> Optional[HttpRequest]:
    """Reads one HTTP/1.1 request, or returns None when the client ends the connection."""
    head = connection.read_until(b"\r\n\r\n")
    if head is None:
        return None
    lines = head.decode("latin-1").split("\r\n")
    method, path, _ = lines[0].split(" ", 2)
    headers: Dict[str, str] = {}
    for line in lines[1:]:
        if ":" in line:
            name, value = line.split(":", 1)
            headers[name.strip().lower()] = value.strip()
    body = b""
    if headers.get("transfer-encoding", "").lower() == "chunked":
        while True:
            size_line = connection.read_until(b"\r\n")
            if size_line is None:
                return None
            size = int(size_line.split(b";")[0], 16)
            chunk = connection.read_exactly(size + 2)
            if chunk is None:
                return None
            if not size:
                break
            body += chunk[:-2]
    else:
        length = int(headers.get("content-length", "0"))
        if length:
            body = connection.read_exactly(length) or b""
    return HttpRequest(method, path, headers, body)


def write_http_head(
    connection: TlsConnection, status: int, headers: Dict[str, str]
) -> None:
    lines = [f"HTTP/1.1 {status} {_REASONS.get(status, 'Unknown')}"]
    lines += [f"{name}: {value}" for name, value in headers.items()]
    connection.send(("\r\n".join(lines) + "\r\n\r\n").encode("latin-1"))


def write_chunk(connection: TlsConnection, data: bytes) -> None:
    """Writes one chunk of a response with Transfer-Encoding: chunked."""
    connection.send(b"%x\r\n" % len(data) + data + b"\r\n")


def end_chunks(connection: TlsConnection) -> None:
    connection.send(b"0\r\n\r\n")


_REASONS = {
    200: "OK",
    302: "Found",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
}


class ClientCertificateServer(TlsServer):
    """Port of the server of the startCCServer fixture.

    It asks for a client certificate (requestCert), unless request_cert is False, and
    accepts a certificate that it can not verify, unless reject_unauthorized is True: then
    it completes the handshake and closes the connection, as Node.js does. respond makes
    the response from the TLS socket of the request. With http2, it speaks HTTP/2 (ALPN
    h2), and with allow_http1 also HTTP/1.1 to a client that does not offer h2.
    """

    def __init__(
        self,
        http2: bool = False,
        allow_http1: bool = False,
        reject_unauthorized: bool = False,
        request_cert: bool = True,
        host: str = "127.0.0.1",
        respond: Callable[[PeerInfo], Response] = cc_server_response,
    ) -> None:
        self._http2 = http2
        self._reject_unauthorized = reject_unauthorized
        self._respond = respond
        context = _server_context(request_cert)
        protocols = [b"h2", b"http/1.1"] if allow_http1 else [b"h2"]
        if not http2:
            # https.createServer() offers http/1.1 when no ALPNProtocols are given.
            protocols = [b"http/1.1"]

        def select_protocol(connection: SSL.Connection, offered: List[bytes]) -> Any:
            for protocol in protocols:
                if protocol in offered:
                    return protocol
            return SSL.NO_OVERLAPPING_PROTOCOLS

        context.set_alpn_select_callback(select_protocol)
        super().__init__(context, host)

    def serve(self, connection: TlsConnection) -> None:
        peer = connection.peer
        if self._reject_unauthorized and not peer.authorized:
            # Node.js destroys the socket after the handshake.
            return
        if peer.alpn_protocol == "h2":
            _serve_http2(connection, lambda: self._respond(peer))
            return
        if self._http2 and peer.alpn_protocol != "http/1.1":
            # An HTTP/2 server without allowHTTP1 does not speak HTTP/1.1.
            return
        while True:
            request = read_http_request(connection)
            if request is None:
                return
            status, headers, body = self._respond(peer)
            write_http_head(
                connection,
                status,
                {
                    **headers,
                    "Content-Length": str(len(body)),
                    "Connection": "keep-alive",
                },
            )
            connection.send(body)


class HandshakeRejectingServer(TlsServer):
    """Port of the tls.createServer of 'should not hang on tls errors during TLS 1.2 handshake'.

    Its SNICallback fails, so Node.js destroys each connection in the handshake, after it
    reads the ClientHello. tls_version is "TLSv1.3" or "TLSv1.2" (minVersion = maxVersion).
    """

    def __init__(self, tls_version: str, host: str = "localhost") -> None:
        version = {"TLSv1.3": SSL.TLS1_3_VERSION, "TLSv1.2": SSL.TLS1_2_VERSION}[
            tls_version
        ]
        context = _server_context(True, version, version)

        def reject(connection: SSL.Connection) -> None:
            # Ends the connection; the handshake then fails to write the ServerHello.
            connection.sock_shutdown(socket.SHUT_RDWR)

        context.set_tlsext_servername_callback(reject)
        super().__init__(context, host)

    def serve(self, connection: TlsConnection) -> None:
        pass


class RenegotiatingServer(TlsServer):
    """Port of the server of 'should handle TLS renegotiation with client certificates'.

    TLS 1.2 only. It does not ask for a client certificate in the first handshake; it
    renegotiates and asks for one in the responses of /from-fetch-api and /style.css.
    """

    STYLESHEET = """
          button {
            background-color: red;
          }
        """

    def __init__(self, host: str = "localhost") -> None:
        context = _server_context(False, SSL.TLS1_2_VERSION, SSL.TLS1_2_VERSION)

        def select_protocol(connection: SSL.Connection, offered: List[bytes]) -> Any:
            if b"http/1.1" in offered:
                return b"http/1.1"
            return SSL.NO_OVERLAPPING_PROTOCOLS

        context.set_alpn_select_callback(select_protocol)
        super().__init__(context, host)

    def serve(self, connection: TlsConnection) -> None:
        while True:
            request = read_http_request(connection)
            if request is None:
                return
            if request.path == "/":
                write_http_head(
                    connection,
                    200,
                    {
                        "Content-Type": "text/html",
                        "connection": "close",
                        "Content-Length": "0",
                    },
                )
                return
            if request.path == "/from-fetch-api":
                write_http_head(
                    connection,
                    200,
                    {
                        "Content-Type": "text/plain",
                        "Transfer-Encoding": "chunked",
                        # A renegotiated connection must not be reused.
                        "Connection": "close",
                    },
                )
                write_chunk(
                    connection, f"server received: {request.body.decode()}\n".encode()
                )
                connection.renegotiate()
                for i in range(4):
                    write_chunk(connection, f"{i}-from-server\n".encode())
                    # Best-effort to trigger a new chunk
                    time.sleep(0.1)
                write_chunk(connection, b"server closed the connection")
                end_chunks(connection)
                return
            if request.path == "/style.css":
                write_http_head(
                    connection,
                    200,
                    {
                        "Content-Type": "text/css",
                        "Content-Encoding": "gzip",
                        "Transfer-Encoding": "chunked",
                        "Connection": "close",
                    },
                )
                connection.renegotiate()
                stylesheet = gzip.compress(self.STYLESHEET.encode())
                for start in range(0, len(stylesheet), 100):
                    end = start + 100
                    write_chunk(connection, stylesheet[start:end])
                    # Best-effort to trigger a new chunk
                    time.sleep(0.02)
                end_chunks(connection)
                return
            write_http_head(
                connection, 404, {"Content-Length": "0", "Connection": "keep-alive"}
            )


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


def _hpack_encode(headers: List[Tuple[str, str]]) -> bytes:
    block = bytearray()
    for name, value in headers:
        # Literal Header Field without Indexing, new name, no Huffman coding.
        block.append(0x00)
        for text in (name.encode(), value.encode()):
            block += _hpack_int(len(text), 7)
            block += text
    return bytes(block)


def _serve_http2(connection: TlsConnection, respond: Callable[[], Response]) -> None:
    """Answers each request stream with respond(). The request headers are not decoded."""
    if connection.read_exactly(len(_PREFACE)) != _PREFACE:
        return
    connection.send(_frame(_SETTINGS, 0, 0, b""))
    header_stream: Optional[int] = None
    while True:
        header = connection.read_exactly(9)
        if header is None:
            return
        length = (header[0] << 16) | (header[1] << 8) | header[2]
        frame_type, flags = header[3], header[4]
        stream_id = struct.unpack(">I", header[5:9])[0] & 0x7FFFFFFF
        payload = connection.read_exactly(length) if length else b""
        if payload is None:
            return
        if frame_type == _SETTINGS and not flags & _ACK:
            connection.send(_frame(_SETTINGS, _ACK, 0, b""))
        elif frame_type == _PING and not flags & _ACK:
            connection.send(_frame(_PING, _ACK, 0, payload))
        elif frame_type == _GOAWAY:
            return
        elif frame_type in (_HEADERS, _CONTINUATION):
            if frame_type == _HEADERS:
                header_stream = stream_id
            if flags & _END_HEADERS and header_stream is not None:
                status, headers, body = respond()
                fields = [(":status", str(status))]
                fields += [(name.lower(), value) for name, value in headers.items()]
                fields.append(("content-length", str(len(body))))
                connection.send(
                    _frame(_HEADERS, _END_HEADERS, header_stream, _hpack_encode(fields))
                    + _frame(_DATA, _END_STREAM, header_stream, body)
                )
                header_stream = None
