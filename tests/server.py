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

import abc
import asyncio
import contextlib
import gzip
import mimetypes
import pathlib
import re
import socket
import threading
from contextlib import closing
from http import HTTPStatus
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    Generic,
    List,
    Optional,
    Set,
    Tuple,
    TypeVar,
    Union,
    cast,
)
from urllib.parse import parse_qs, urlparse

from autobahn.twisted.resource import WebSocketResource
from autobahn.twisted.websocket import WebSocketServerFactory, WebSocketServerProtocol
from autobahn.websocket.types import ConnectionRequest
from OpenSSL import crypto
from pyee import EventEmitter
from twisted.internet import reactor as _twisted_reactor
from twisted.internet import ssl
from twisted.internet.error import CannotListenError
from twisted.internet.selectreactor import SelectReactor
from twisted.web import http

from playwright._impl._path_utils import get_file_dirname

_dirname = get_file_dirname()
reactor = cast(SelectReactor, _twisted_reactor)


def find_free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


T = TypeVar("T")


def _resolve_threadsafe(future: "asyncio.Future[T]", value: T) -> None:
    """Resolves the future from the reactor thread, on the loop that owns it."""

    def resolve() -> None:
        if not future.done():
            future.set_result(value)

    loop = future.get_loop()
    if not loop.is_closed():
        loop.call_soon_threadsafe(resolve)


class ExpectResponse(Generic[T]):
    def __init__(self) -> None:
        self._value: T

    @property
    def value(self) -> T:
        if not hasattr(self, "_value"):
            raise ValueError("no received value")
        return self._value


class TestServerRequest(http.Request):
    __test__ = False
    channel: "TestServerHTTPChannel"
    post_body: Optional[bytes] = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Twisted answers 400 to some multipart bodies that browsers send, and
        # upstream's server accepts any body. process() parses forms leniently.
        kwargs["parsePOSTFormSubmission"] = False
        super().__init__(*args, **kwargs)

    def _parse_form(self) -> None:
        """Adds the fields of a POSTed form to self.args, ignoring a malformed body."""
        if self.method != b"POST" or not self.post_body or self.args is None:
            return
        content_type = (self.getHeader("content-type") or "").encode()
        kind = http._parseContentType(content_type)
        try:
            if kind == b"application/x-www-form-urlencoded":
                self.args.update(parse_qs(self.post_body, keep_blank_values=True))
            elif kind == b"multipart/form-data":
                self.args.update(http._getMultiPartArgs(self.post_body, content_type))
        except Exception:
            pass

    def process(self) -> None:
        server = self.channel.factory.server_instance
        if self.content:
            self.post_body = self.content.read()
            self.content.seek(0, 0)
        else:
            self.post_body = None
        self._parse_form()
        # The headers that Node.js adds to every response; tests measure header sizes.
        self.setHeader(b"Date", http.datetimeToString())
        self.setHeader(b"Connection", b"keep-alive")
        self.setHeader(b"Keep-Alive", b"timeout=5")
        url = urlparse(self.uri.decode())
        path = url.path
        # Like the upstream test server, match the path with the query first.
        keys = [f"{path}?{url.query}", path] if url.query else [path]

        def lookup(table: Dict[str, Any]) -> Optional[str]:
            return next((key for key in keys if key in table), None)

        auth_key = lookup(server.auth)
        if auth_key:
            authorization_header = self.requestHeaders.getRawHeaders("authorization")
            creds_correct = False
            if authorization_header:
                creds_correct = server.auth[auth_key] == (
                    self.getUser().decode(),
                    self.getPassword().decode(),
                )
            if not creds_correct:
                self.setHeader(b"www-authenticate", 'Basic realm="Secure Area"')
                self.setResponseCode(HTTPStatus.UNAUTHORIZED)
                self.write(b"HTTP Error 401 Unauthorized: Access is denied")
                self.finish()
                return

        subscriber_key = lookup(server.request_subscribers)
        if subscriber_key:
            request_subscriber = server.request_subscribers.pop(subscriber_key)
            request_subscriber._loop.call_soon_threadsafe(
                request_subscriber.set_result, self
            )

        if self._is_web_socket_upgrade():
            # Like upstream's 'upgrade' handler: waitForUpgrade() takes every upgrade.
            if server._upgrade_callback:
                server._upgrade_callback(UpgradeActions(self))
                return
            if path == "/ws-401":
                # cast: mypy reads the zope ITransport interface as a plain function.
                transport = cast(Any, self.channel.transport)
                assert transport
                transport.write(b"HTTP/1.1 401 Unauthorized\r\n\r\nUnauthorized body")
                transport.loseConnection()
                return
            if path == "/ws-slow":
                reactor.callLater(2, self._upgrade_to_web_socket)
                return

        if path == "/ws":
            server._ws_resource.render(self)
            return

        if server.csp.get(path):
            self.setHeader(b"Content-Security-Policy", server.csp[path])
        route_key = lookup(server.routes)
        if route_key:
            server.routes[route_key](self)
            return

        if path == "/":
            path = "/index.html"
        self._serve_file(server.static_path / path[1:], path)

    def serve_file(self, path: pathlib.Path) -> None:
        return self._serve_file(path, urlparse(self.uri.decode()).path)

    def _is_web_socket_upgrade(self) -> bool:
        return (self.getHeader("upgrade") or "").lower() == "websocket"

    def _upgrade_to_web_socket(self) -> None:
        """Hands the connection to the WebSocket server, unless it is gone."""
        if self._disconnected or self.channel is None or not self.channel.transport:
            return
        self.channel.factory.server_instance._ws_resource.render(self)

    def _serve_file(self, path: pathlib.Path, request_path: str) -> None:
        server = self.channel.factory.server_instance
        file_content = None
        try:
            file_content = path.read_bytes()
            content_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
            if re.match(r"^text/|^application/(javascript|json)", content_type):
                content_type += "; charset=utf-8"
            self.setHeader(b"Content-Type", content_type)
            self.setHeader(b"Cache-Control", "no-cache, no-store")
            for name, value in server.extra_headers.get(request_path, {}).items():
                self.setHeader(name, value)
            if request_path in server.gzip_routes:
                self.setHeader("Content-Encoding", "gzip")
                compressed = gzip.compress(file_content)
                self.setHeader(b"Content-Length", str(len(compressed)))
                self.write(compressed)
            else:
                self.setHeader(b"Content-Length", str(len(file_content)))
                self.write(file_content)
            self.setResponseCode(HTTPStatus.OK)
        except (FileNotFoundError, IsADirectoryError, PermissionError):
            self.setHeader(b"Content-Type", "text/plain")
            self.setResponseCode(HTTPStatus.NOT_FOUND)
            if self.method != "HEAD":
                self.write(f"File not found: {path}".encode())
        self.finish()


class TestServerHTTPChannel(http.HTTPChannel):
    factory: "TestServerFactory"
    requestFactory = TestServerRequest


class TestServerFactory(http.HTTPFactory):
    server_instance: "Server"
    protocol = TestServerHTTPChannel


class Server:
    protocol = "http"

    def __init__(self) -> None:
        self._set_port(find_free_port())
        self.HOSTNAME = "localhost"
        # On Windows, this list can be empty, reporting text/plain for scripts.
        mimetypes.add_type("text/html", ".html")
        mimetypes.add_type("text/css", ".css")
        mimetypes.add_type("application/javascript", ".js")
        mimetypes.add_type("image/png", ".png")
        mimetypes.add_type("font/woff2", ".woff2")

    def _set_port(self, port: int) -> None:
        self.PORT = port
        self.EMPTY_PAGE = f"{self.protocol}://localhost:{self.PORT}/empty.html"
        self.PREFIX = f"{self.protocol}://localhost:{self.PORT}"
        self.CROSS_PROCESS_PREFIX = f"{self.protocol}://127.0.0.1:{self.PORT}"
        self.HOST = f"localhost:{self.PORT}"

    def __repr__(self) -> str:
        return self.PREFIX

    @abc.abstractmethod
    def listen(self, factory: TestServerFactory) -> None:
        pass

    def start(self, static_path: pathlib.Path = _dirname / "assets") -> None:
        request_subscribers: Dict[str, asyncio.Future] = {}
        auth: Dict[str, Tuple[str, str]] = {}
        csp: Dict[str, str] = {}
        routes: Dict[str, Callable[[TestServerRequest], Any]] = {}
        gzip_routes: Set[str] = set()
        self.extra_headers: Dict[str, Dict[str, str]] = {}
        self.request_subscribers = request_subscribers
        self.auth = auth
        self.csp = csp
        self.routes = routes
        self._ws_handlers: List[Callable[["WebSocketProtocol"], None]] = []
        self._upgrade_callback: Optional[Callable[["UpgradeActions"], None]] = None
        self.gzip_routes = gzip_routes
        self.static_path = static_path
        factory = TestServerFactory()
        factory.server_instance = self

        ws_factory = WebSocketServerFactory()
        ws_factory.protocol = WebSocketProtocol
        # Like upstream's `ws` server, answer a close with the client's code and reason.
        # setProtocolOptions() resets allowNullOrigin unless it is passed.
        ws_factory.setProtocolOptions(echoCloseCodeReason=True, allowNullOrigin=True)
        setattr(ws_factory, "server_instance", self)
        self._ws_resource = WebSocketResource(ws_factory)

        for attempt in range(10):
            try:
                self.listen(factory)
                return
            except CannotListenError:
                # Another process took the port after find_free_port() released it.
                if attempt == 9:
                    raise
                self._set_port(find_free_port())

    async def wait_for_request(self, path: str) -> TestServerRequest:
        if path in self.request_subscribers:
            return await self.request_subscribers[path]
        future: asyncio.Future["TestServerRequest"] = asyncio.Future()
        self.request_subscribers[path] = future
        return await future

    def wait_for_web_socket(self) -> 'asyncio.Future["WebSocketProtocol"]':
        future: asyncio.Future[WebSocketProtocol] = asyncio.Future()
        # The handler runs on the reactor thread.
        self.once_web_socket_connection(lambda ws: _resolve_threadsafe(future, ws))
        return future

    def wait_for_upgrade(self) -> 'asyncio.Future["UpgradeActions"]':
        """Port of waitForUpgrade(): the next WebSocket upgrade request waits for the test.

        The future resolves with the UpgradeActions of the first upgrade request. Like
        upstream, every later upgrade request waits too, until reset().
        """
        future: asyncio.Future[UpgradeActions] = (
            asyncio.get_running_loop().create_future()
        )
        self._upgrade_callback = lambda actions: _resolve_threadsafe(future, actions)
        return future

    def wait_for_web_socket_connection_request(
        self,
    ) -> "asyncio.Future[ConnectionRequest]":
        """Port of waitForWebSocketConnectionRequest().

        Resolves with the handshake request of the next WebSocket connection:
        request.headers maps the lower-case header names to their values, as in Node.js.
        """
        future: asyncio.Future[ConnectionRequest] = (
            asyncio.get_running_loop().create_future()
        )

        def on_connection(ws: WebSocketProtocol) -> None:
            assert ws.connection_request
            _resolve_threadsafe(future, ws.connection_request)

        self.once_web_socket_connection(on_connection)
        return future

    @contextlib.contextmanager
    def expect_request(
        self, path: str
    ) -> Generator[ExpectResponse[TestServerRequest], None, None]:
        future = asyncio.create_task(self.wait_for_request(path))

        cb_wrapper: ExpectResponse[TestServerRequest] = ExpectResponse()

        def done_cb(task: asyncio.Task) -> None:
            cb_wrapper._value = future.result()

        future.add_done_callback(done_cb)
        yield cb_wrapper

    @contextlib.contextmanager
    def expect_websocket(
        self,
    ) -> Generator[ExpectResponse["WebSocketProtocol"], None, None]:
        future = self.wait_for_web_socket()

        cb_wrapper: ExpectResponse["WebSocketProtocol"] = ExpectResponse()

        def done_cb(_: asyncio.Future) -> None:
            cb_wrapper._value = future.result()

        future.add_done_callback(done_cb)
        yield cb_wrapper

    def set_auth(self, path: str, username: str, password: str) -> None:
        self.auth[path] = (username, password)

    def set_csp(self, path: str, value: str) -> None:
        self.csp[path] = value

    def reset(self) -> None:
        self.request_subscribers.clear()
        self.auth.clear()
        self.csp.clear()
        self.gzip_routes.clear()
        self.extra_headers.clear()
        self.routes.clear()
        self._ws_handlers.clear()
        self._upgrade_callback = None

    def set_route(
        self, path: str, callback: Callable[[TestServerRequest], Any]
    ) -> None:
        self.routes[path] = callback

    def enable_gzip(self, path: str) -> None:
        self.gzip_routes.add(path)

    def set_redirect(self, from_: str, to: str) -> None:
        def handle_redirect(request: http.Request) -> None:
            request.setResponseCode(HTTPStatus.FOUND)
            for name, value in self.extra_headers.get(from_, {}).items():
                request.setHeader(name, value)
            request.setHeader("location", to)
            request.finish()

        self.set_route(from_, handle_redirect)

    def set_extra_headers(self, path: str, headers: Dict[str, str]) -> None:
        """Adds headers to the response for a file, or for a redirect from set_redirect()."""
        self.extra_headers[path] = headers

    def set_content(self, path: str, content: str, mime_type: str) -> None:
        def handle_content(request: http.Request) -> None:
            request.setHeader("Content-Type", mime_type)
            body = f"<!DOCTYPE html>{content}" if mime_type == "text/html" else content
            request.write(body.encode())
            request.finish()

        self.set_route(path, handle_content)

    def send_on_web_socket_connection(self, data: bytes) -> None:
        self.once_web_socket_connection(lambda ws: ws.sendMessage(data))

    def once_web_socket_connection(
        self, handler: Callable[["WebSocketProtocol"], None]
    ) -> None:
        self._ws_handlers.append(handler)


class HTTPServer(Server):
    def __init__(self) -> None:
        self._listeners: list[Any] = []
        super().__init__()

    def listen(self, factory: http.HTTPFactory) -> None:
        self._listeners.append(
            reactor.listenTCP(self.PORT, factory, interface="127.0.0.1")
        )
        try:
            self._listeners.append(
                reactor.listenTCP(self.PORT, factory, interface="::1")
            )
        except Exception:
            pass

    def stop(self) -> None:
        for listener in self._listeners:
            listener.stopListening()
        self._listeners.clear()


class HTTPSServer(Server):
    protocol = "https"

    def __init__(self) -> None:
        self._listeners: list[Any] = []
        super().__init__()

    def listen(self, factory: http.HTTPFactory) -> None:
        cert = ssl.PrivateCertificate.fromCertificateAndKeyPair(
            ssl.Certificate.loadPEM(
                (_dirname / "testserver" / "cert.pem").read_bytes()
            ),
            ssl.KeyPair.load(
                (_dirname / "testserver" / "key.pem").read_bytes(), crypto.FILETYPE_PEM
            ),
        )
        contextFactory = cert.options()
        self._listeners.append(
            reactor.listenSSL(self.PORT, factory, contextFactory, interface="127.0.0.1")
        )
        try:
            self._listeners.append(
                reactor.listenSSL(self.PORT, factory, contextFactory, interface="::1")
            )
        except Exception:
            pass

    def stop(self) -> None:
        for listener in self._listeners:
            listener.stopListening()
        self._listeners.clear()


class UpgradeSocket:
    """The connection of an upgrade request: the `socket` of upstream's UpgradeActions.

    The methods are safe to call from any thread.
    """

    def __init__(self, transport: Any) -> None:
        self._transport = transport

    def write(self, data: Union[str, bytes]) -> None:
        """Writes raw bytes to the connection, like socket.write()."""
        payload = data.encode() if isinstance(data, str) else data
        reactor.callFromThread(self._transport.write, payload)

    def destroy(self) -> None:
        """Closes the connection, like socket.destroy()."""
        reactor.callFromThread(self._transport.loseConnection)


class UpgradeActions:
    """Port of UpgradeActions of upstream's waitForUpgrade()."""

    def __init__(self, request: TestServerRequest) -> None:
        self.request = request
        self.socket = UpgradeSocket(request.channel.transport)

    def do_upgrade(self) -> None:
        """Completes the WebSocket handshake. Safe to call from any thread."""
        reactor.callFromThread(self.request._upgrade_to_web_socket)


class WebSocketProtocol(WebSocketServerProtocol):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.events = EventEmitter()
        self.connection_request: Optional[ConnectionRequest] = None

    def onConnect(self, request: ConnectionRequest) -> Optional[str]:
        self.connection_request = request
        # Like upstream's `ws` server, accept the first subprotocol that the client offers.
        return request.protocols[0] if request.protocols else None

    def dropConnection(self, abort: bool = False) -> None:
        # Like upstream's `ws` server, end the TCP connection gracefully after a clean
        # closing handshake. Autobahn resets it, and browsers then report wasClean=false.
        super().dropConnection(abort=abort and not self.wasClean)

    def onClose(self, wasClean: bool, code: int, reason: str) -> None:
        super().onClose(wasClean, code, reason)
        self.events.emit(
            "close",
            code,
            reason,
        )

    def onMessage(self, payload: Union[str, bytes], isBinary: bool) -> None:
        self.events.emit("message", payload, isBinary)

    def onOpen(self) -> None:
        for handler in getattr(self.factory, "server_instance")._ws_handlers.copy():
            getattr(self.factory, "server_instance")._ws_handlers.remove(handler)
            handler(self)


class TestServer:
    def __init__(self) -> None:
        self.server = HTTPServer()
        self.https_server = HTTPSServer()

    def start(self) -> None:
        self.server.start()
        self.https_server.start()
        self.thread = threading.Thread(
            target=lambda: reactor.run(installSignalHandlers=False)
        )
        self.thread.start()

    def stop(self) -> None:
        reactor.stop()
        self.thread.join()

    def reset(self) -> None:
        self.server.reset()
        self.https_server.reset()


test_server = TestServer()
