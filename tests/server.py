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
from urllib.parse import urlparse

from autobahn.twisted.resource import WebSocketResource
from autobahn.twisted.websocket import WebSocketServerFactory, WebSocketServerProtocol
from OpenSSL import crypto
from pyee import EventEmitter
from twisted.internet import reactor as _twisted_reactor
from twisted.internet import ssl
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

    def process(self) -> None:
        server = self.channel.factory.server_instance
        if self.content:
            self.post_body = self.content.read()
            self.content.seek(0, 0)
        else:
            self.post_body = None
        uri = urlparse(self.uri.decode())
        path = uri.path

        request_subscriber = server.request_subscribers.get(path)
        if request_subscriber:
            request_subscriber._loop.call_soon_threadsafe(
                request_subscriber.set_result, self
            )
            server.request_subscribers.pop(path)

        if path == "/ws":
            server._ws_resource.render(self)
            return

        if server.auth.get(path):
            authorization_header = self.requestHeaders.getRawHeaders("authorization")
            creds_correct = False
            if authorization_header:
                creds_correct = server.auth.get(path) == (
                    self.getUser().decode(),
                    self.getPassword().decode(),
                )
            if not creds_correct:
                self.setHeader(b"www-authenticate", 'Basic realm="Secure Area"')
                self.setResponseCode(HTTPStatus.UNAUTHORIZED)
                self.write(b"HTTP Error 401 Unauthorized: Access is denied")
                self.finish()
                return
        if server.csp.get(path):
            self.setHeader(b"Content-Security-Policy", server.csp[path])
        if server.routes.get(path):
            server.routes[path](self)
            return
        file_content = None
        try:
            file_content = (server.static_path / path[1:]).read_bytes()
            content_type = mimetypes.guess_type(path)[0]
            if content_type and content_type.startswith("text/"):
                content_type += "; charset=utf-8"
            self.setHeader(b"Content-Type", content_type)
            self.setHeader(b"Cache-Control", "no-cache, no-store")
            if path in server.gzip_routes:
                self.setHeader("Content-Encoding", "gzip")
                self.write(gzip.compress(file_content))
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
        self.PORT = find_free_port()
        self.EMPTY_PAGE = f"{self.protocol}://localhost:{self.PORT}/empty.html"
        self.PREFIX = f"{self.protocol}://localhost:{self.PORT}"
        self.CROSS_PROCESS_PREFIX = f"{self.protocol}://127.0.0.1:{self.PORT}"
        # On Windows, this list can be empty, reporting text/plain for scripts.
        mimetypes.add_type("text/html", ".html")
        mimetypes.add_type("text/css", ".css")
        mimetypes.add_type("application/javascript", ".js")
        mimetypes.add_type("image/png", ".png")
        mimetypes.add_type("font/woff2", ".woff2")

    def __repr__(self) -> str:
        return self.PREFIX

    @abc.abstractmethod
    def listen(self, factory: TestServerFactory) -> None:
        pass

    def start(self) -> None:
        request_subscribers: Dict[str, asyncio.Future] = {}
        auth: Dict[str, Tuple[str, str]] = {}
        csp: Dict[str, str] = {}
        routes: Dict[str, Callable[[TestServerRequest], Any]] = {}
        gzip_routes: Set[str] = set()
        self.request_subscribers = request_subscribers
        self.auth = auth
        self.csp = csp
        self.routes = routes
        self._ws_handlers: List[Callable[["WebSocketProtocol"], None]] = []
        self.gzip_routes = gzip_routes
        self.static_path = _dirname / "assets"
        factory = TestServerFactory()
        factory.server_instance = self

        ws_factory = WebSocketServerFactory()
        ws_factory.protocol = WebSocketProtocol
        setattr(ws_factory, "server_instance", self)
        self._ws_resource = WebSocketResource(ws_factory)

        self.listen(factory)

    async def wait_for_request(self, path: str) -> TestServerRequest:
        if path in self.request_subscribers:
            return await self.request_subscribers[path]
        future: asyncio.Future["TestServerRequest"] = asyncio.Future()
        self.request_subscribers[path] = future
        return await future

    def wait_for_web_socket(self) -> 'asyncio.Future["WebSocketProtocol"]':
        future: asyncio.Future[WebSocketProtocol] = asyncio.Future()
        self.once_web_socket_connection(future.set_result)
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
        self.routes.clear()
        self._ws_handlers.clear()

    def set_route(
        self, path: str, callback: Callable[[TestServerRequest], Any]
    ) -> None:
        self.routes[path] = callback

    def enable_gzip(self, path: str) -> None:
        self.gzip_routes.add(path)

    def set_redirect(self, from_: str, to: str) -> None:
        def handle_redirect(request: http.Request) -> None:
            request.setResponseCode(HTTPStatus.FOUND)
            request.setHeader("location", to)
            request.finish()

        self.set_route(from_, handle_redirect)

    def send_on_web_socket_connection(self, data: bytes) -> None:
        self.once_web_socket_connection(lambda ws: ws.sendMessage(data))

    def once_web_socket_connection(
        self, handler: Callable[["WebSocketProtocol"], None]
    ) -> None:
        self._ws_handlers.append(handler)


class HTTPServer(Server):
    def listen(self, factory: http.HTTPFactory) -> None:
        reactor.listenTCP(self.PORT, factory, interface="127.0.0.1")
        try:
            reactor.listenTCP(self.PORT, factory, interface="::1")
        except Exception:
            pass


class HTTPSServer(Server):
    protocol = "https"

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
        reactor.listenSSL(self.PORT, factory, contextFactory, interface="127.0.0.1")
        try:
            reactor.listenSSL(self.PORT, factory, contextFactory, interface="::1")
        except Exception:
            pass


class WebSocketProtocol(WebSocketServerProtocol):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.events = EventEmitter()

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
