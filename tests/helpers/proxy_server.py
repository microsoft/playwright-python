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

"""An HTTP proxy for the proxy tests, in both flavors.

Port of TestProxy in tests/config/proxy.ts (the proxyServer fixture) and of the proxy
in tests/third_party/proxy/index.ts that it wraps. The proxy:

- forwards plain HTTP requests (GET http://host/path) to the host,
- answers CONNECT host:port with a tunnel to the host,
- passes WebSocket upgrade requests (GET ws://host/path) to the host,
- asks for credentials (407) when the auth handler returns False.

forward_to(port) sends every request to 127.0.0.1:port instead of the host, and
records the request URLs and the CONNECT hosts, as upstream's forwardTo() does.
"""

import http.client
import socket
import threading
from typing import Callable, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlsplit, urlunsplit

# Certain browsers perform telemetry requests which we want to ignore.
_CONNECT_HOSTS_TO_IGNORE = {"www.bing.com:443", "www.google.com:443"}

_HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}

_VIA = f"1.1 {socket.gethostname()} (proxy/1.0.0)"


class ProxyRequest:
    """The request that the auth handler gets, like Node's IncomingMessage.

    headers has lower-case names, as req.headers in Node.js.
    """

    def __init__(
        self, method: str, url: str, raw_headers: List[Tuple[str, str]]
    ) -> None:
        self.method = method
        self.url = url
        self.raw_headers = raw_headers
        self.headers: Dict[str, str] = {}
        for name, value in raw_headers:
            key = name.lower()
            if key in self.headers:
                self.headers[key] += ", " + value
            else:
                self.headers[key] = value


class _ForwardOptions:
    def __init__(
        self,
        port: int,
        allow_connect_requests: bool,
        remove_prefix: Optional[str],
        preserve_hostname: bool,
    ) -> None:
        self.port = port
        self.allow_connect_requests = allow_connect_requests
        self.remove_prefix = remove_prefix
        self.preserve_hostname = preserve_hostname


class _Reader:
    """Reads a socket with a buffer: heads, lines and bodies."""

    def __init__(self, sock: socket.socket) -> None:
        self.sock = sock
        self.buffer = b""

    def _fill(self) -> bool:
        data = self.sock.recv(65536)
        if not data:
            return False
        self.buffer += data
        return True

    def read_until(self, separator: bytes) -> Optional[bytes]:
        while separator not in self.buffer:
            if not self._fill():
                return None
        result, self.buffer = self.buffer.split(separator, 1)
        return result

    def read_exact(self, size: int) -> bytes:
        while len(self.buffer) < size:
            if not self._fill():
                raise ConnectionError("connection closed")
        result, self.buffer = self.buffer[:size], self.buffer[size:]
        return result

    def read_body(self, headers: Dict[str, str]) -> Tuple[bytes, bool]:
        """Returns the body and whether it was chunked."""
        if "chunked" in headers.get("transfer-encoding", "").lower():
            body = b""
            while True:
                line = self.read_until(b"\r\n")
                if line is None:
                    raise ConnectionError("connection closed")
                size = int(line.split(b";")[0].strip() or b"0", 16)
                if size == 0:
                    # Trailers end with an empty line.
                    while self.read_until(b"\r\n") not in (b"", None):
                        pass
                    return body, True
                body += self.read_exact(size)
                self.read_exact(2)
        length = int(headers.get("content-length", "0") or "0")
        return self.read_exact(length), False


def _parse_head(head: bytes) -> Tuple[str, str, str, List[Tuple[str, str]]]:
    lines = head.decode("latin-1").split("\r\n")
    method, url, version = (lines[0].split(" ") + ["", ""])[:3]
    raw_headers: List[Tuple[str, str]] = []
    for line in lines[1:]:
        if ":" in line:
            name, value = line.split(":", 1)
            raw_headers.append((name.strip(), value.strip()))
    return method, url, version, raw_headers


def _close_socket(sock: socket.socket) -> None:
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    sock.close()


class ProxyServer:
    """Listens on localhost (127.0.0.1 and ::1), on a free port."""

    def __init__(self) -> None:
        self._listeners: List[socket.socket] = []
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen(128)
        self._listeners.append(listener)
        self.PORT: int = listener.getsockname()[1]
        try:
            listener6 = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            listener6.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
            listener6.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener6.bind(("::1", self.PORT))
            listener6.listen(128)
            self._listeners.append(listener6)
        except OSError:
            pass
        self.URL = f"http://localhost:{self.PORT}"
        self.HOST = f"localhost:{self.PORT}"

        self.connect_hosts: List[str] = []
        self.request_urls: List[str] = []
        self.request_hosts: List[Optional[str]] = []
        self.ws_urls: List[str] = []

        self._forward: Optional[_ForwardOptions] = None
        self._auth_handler: Optional[Callable[[ProxyRequest], bool]] = None
        self._sockets: Set[socket.socket] = set()
        self._lock = threading.Lock()
        self._closed = False
        self._threads = [
            threading.Thread(target=self._accept_loop, args=(sock,), daemon=True)
            for sock in self._listeners
        ]
        for thread in self._threads:
            thread.start()

    def forward_to(
        self,
        port: int,
        allow_connect_requests: bool = False,
        remove_prefix: Optional[str] = None,
        preserve_hostname: bool = False,
    ) -> None:
        self._forward = _ForwardOptions(
            port, allow_connect_requests, remove_prefix, preserve_hostname
        )

    def set_auth_handler(self, handler: Callable[[ProxyRequest], bool]) -> None:
        self._auth_handler = handler

    def reset(self) -> None:
        self.connect_hosts = []
        self.request_urls = []
        self.request_hosts = []
        self._forward = None
        self._auth_handler = None

    def stop(self) -> None:
        self.reset()
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

    def _authenticate(self, request: ProxyRequest) -> bool:
        handler = self._auth_handler
        if not handler:
            return True
        try:
            return bool(handler(request))
        except Exception:
            return False

    def _rewrite_url(self, url: str, host: Optional[str]) -> str:
        """Port of the URL rewrite in forwardTo(): new URL(req.url, `http://${host}`)."""
        assert self._forward
        parts = urlsplit(urljoin(f"http://{host}", url))
        hostname = parts.hostname or ""
        if ":" in hostname:
            hostname = f"[{hostname}]"
        if self._forward.preserve_hostname:
            netloc = f"{hostname}:{self._forward.port}"
        else:
            netloc = f"127.0.0.1:{self._forward.port}"
        path = parts.path
        if self._forward.remove_prefix:
            path = path.replace(self._forward.remove_prefix, "", 1)
        scheme = parts.scheme
        if scheme == "ws":
            scheme = "http"
        elif scheme == "wss":
            scheme = "https"
        return urlunsplit((scheme, netloc, path, parts.query, parts.fragment))

    def _serve(self, conn: socket.socket) -> None:
        reader = _Reader(conn)
        try:
            while True:
                head = reader.read_until(b"\r\n\r\n")
                if head is None:
                    return
                method, url, version, raw_headers = _parse_head(head)
                request = ProxyRequest(method, url, raw_headers)
                if method.upper() == "CONNECT":
                    self._on_connect(conn, reader, request)
                    return
                connection = request.headers.get("connection", "").lower()
                if "upgrade" in request.headers and "upgrade" in connection:
                    self._on_upgrade(conn, reader, request)
                    return
                body, chunked = reader.read_body(request.headers)
                keep_alive = version != "HTTP/1.0" and "close" not in connection
                self._on_request(conn, request, body, chunked, keep_alive)
                if not keep_alive:
                    return
        except (OSError, ValueError, http.client.HTTPException):
            pass
        finally:
            self._untrack(conn)

    def _send_response(
        self,
        conn: socket.socket,
        status: int,
        reason: str,
        headers: List[Tuple[str, str]],
        body: bytes,
        keep_alive: bool,
    ) -> None:
        lines = [f"HTTP/1.1 {status} {reason}"]
        lines += [f"{name}: {value}" for name, value in headers]
        lines.append(f"Content-Length: {len(body)}")
        if not keep_alive:
            lines.append("Connection: close")
        conn.sendall(("\r\n".join(lines) + "\r\n\r\n").encode("latin-1") + body)

    def _send_407(self, conn: socket.socket, keep_alive: bool) -> None:
        self._send_response(
            conn,
            407,
            "Proxy Authentication Required",
            [("Proxy-Authenticate", 'Basic realm="proxy"')],
            b"Proxy authorization required",
            keep_alive,
        )

    def _on_request(
        self,
        conn: socket.socket,
        request: ProxyRequest,
        body: bytes,
        chunked: bool,
        keep_alive: bool,
    ) -> None:
        forward = self._forward
        if forward:
            self.request_urls.append(request.url)
            self.request_hosts.append(request.headers.get("host"))
            request.url = self._rewrite_url(request.url, request.headers.get("host"))

        if not self._authenticate(request):
            self._send_407(conn, keep_alive)
            return

        parsed = urlsplit(urljoin("http://localhost", request.url))
        if parsed.scheme != "http":
            message = (
                f'Only "http:" protocol prefix is supported (got: "{parsed.scheme}:")\n'
            )
            self._send_response(conn, 400, "Bad Request", [], message.encode(), True)
            return

        # Port of the header handling in onrequest() of tests/third_party/proxy.
        headers: List[Tuple[str, str]] = []
        has_x_forwarded_for = False
        has_via = False
        remote_address = conn.getpeername()[0]
        for name, value in request.raw_headers:
            key = name.lower()
            if not has_x_forwarded_for and key == "x-forwarded-for":
                has_x_forwarded_for = True
                value += ", " + remote_address
            if not has_via and key == "via":
                has_via = True
                value += ", " + _VIA
            if key in _HOP_BY_HOP_HEADERS:
                continue
            if chunked and key == "content-length":
                continue
            headers.append((name, value))
        if not has_x_forwarded_for:
            headers.append(("X-Forwarded-For", remote_address))
        if not has_via:
            headers.append(("Via", _VIA))
        if chunked:
            headers.append(("Content-Length", str(len(body))))

        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        target = http.client.HTTPConnection(parsed.hostname or "", parsed.port or 80)
        try:
            try:
                target.putrequest(
                    request.method, path, skip_host=True, skip_accept_encoding=True
                )
                for name, value in headers:
                    target.putheader(name, value)
                target.endheaders(body or None)
                response = target.getresponse()
            except socket.gaierror:
                self._send_response(conn, 404, "Not Found", [], b"", keep_alive)
                return
            except (OSError, http.client.HTTPException):
                self._send_response(
                    conn, 500, "Internal Server Error", [], b"", keep_alive
                )
                return
            # After the response head, an error destroys the client socket (in _serve).
            response_body = response.read()
            response_headers = [
                (name, value)
                for name, value in response.getheaders()
                if name.lower() not in _HOP_BY_HOP_HEADERS
            ]
            no_body = (
                request.method.upper() == "HEAD"
                or response.status in (204, 304)
                or 100 <= response.status < 200
            )
            if no_body:
                lines = [f"HTTP/1.1 {response.status} {response.reason}"]
                lines += [f"{name}: {value}" for name, value in response_headers]
                if not keep_alive:
                    lines.append("Connection: close")
                conn.sendall(("\r\n".join(lines) + "\r\n\r\n").encode("latin-1"))
                return
            self._send_response(
                conn,
                response.status,
                response.reason,
                [
                    (name, value)
                    for name, value in response_headers
                    if name.lower() != "content-length"
                ],
                response_body,
                keep_alive,
            )
        finally:
            target.close()

    def _on_connect(
        self, conn: socket.socket, reader: _Reader, request: ProxyRequest
    ) -> None:
        forward = self._forward
        if (
            forward
            and forward.allow_connect_requests
            and request.url not in _CONNECT_HOSTS_TO_IGNORE
        ):
            self.connect_hosts.append(request.url)
            request.url = f"127.0.0.1:{forward.port}"

        if not self._authenticate(request):
            # Like upstream, the proxy closes the socket after a 407 to CONNECT.
            self._send_407(conn, False)
            return

        host, _, port = request.url.rpartition(":")
        try:
            target = socket.create_connection((host.strip("[]"), int(port)))
        except socket.gaierror:
            self._send_response(conn, 404, "Not Found", [], b"", False)
            return
        except (OSError, ValueError):
            self._send_response(conn, 500, "Internal Server Error", [], b"", False)
            return
        if not self._track(target):
            return
        try:
            conn.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
            if reader.buffer:
                target.sendall(reader.buffer)
                reader.buffer = b""
            _pipe_both_ways(conn, target)
        finally:
            self._untrack(target)

    def _on_upgrade(
        self, conn: socket.socket, reader: _Reader, request: ProxyRequest
    ) -> None:
        if self._forward:
            self.ws_urls.append(request.url)
            request.url = self._rewrite_url(request.url, request.headers.get("host"))
        parsed = urlsplit(request.url)
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        try:
            target = socket.create_connection(
                (parsed.hostname or "", parsed.port or 80)
            )
        except (OSError, ValueError):
            return
        if not self._track(target):
            return
        try:
            lines = [f"{request.method} {path} HTTP/1.1"]
            lines += [f"{name}: {value}" for name, value in request.raw_headers]
            target.sendall(
                ("\r\n".join(lines) + "\r\n\r\n").encode("latin-1") + reader.buffer
            )
            reader.buffer = b""
            # The 101 response of the target and the frames go through unchanged.
            _pipe_both_ways(conn, target)
        finally:
            self._untrack(target)


def _pipe_both_ways(a: socket.socket, b: socket.socket) -> None:
    """Copies the bytes both ways. When one side ends, closes both, like upstream."""

    def pipe(source: socket.socket, target: socket.socket) -> None:
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
        _close_socket(a)
        _close_socket(b)

    other = threading.Thread(target=pipe, args=(b, a), daemon=True)
    other.start()
    pipe(a, b)
    other.join()
