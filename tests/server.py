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
import gzip
import mimetypes
import socket
import threading
from contextlib import closing
from http import HTTPStatus
from urllib.parse import urlparse

from autobahn.twisted.websocket import WebSocketServerFactory, WebSocketServerProtocol
from OpenSSL import crypto
from twisted.internet import reactor, ssl
from twisted.web import http

from playwright._impl._path_utils import get_file_dirname

_dirname = get_file_dirname()


def find_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


class Server:
    protocol = "http"

    def __init__(self):
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
    def listen(self, factory):
        pass

    def start(self):
        request_subscribers = {}
        auth = {}
        csp = {}
        routes = {}
        gzip_routes = set()
        self.request_subscribers = request_subscribers
        self.auth = auth
        self.csp = csp
        self.routes = routes
        self.gzip_routes = gzip_routes
        static_path = _dirname / "assets"

        class TestServerHTTPHandler(http.Request):
            def process(self):
                request = self
                self.post_body = request.content.read()
                request.content.seek(0, 0)
                uri = urlparse(request.uri.decode())
                path = uri.path

                if request_subscribers.get(path):
                    request_subscribers[path].set_result(request)
                    request_subscribers.pop(path)

                if auth.get(path):
                    authorization_header = request.requestHeaders.getRawHeaders(
                        "authorization"
                    )
                    creds_correct = False
                    if authorization_header:
                        creds_correct = auth.get(path) == (
                            request.getUser(),
                            request.getPassword(),
                        )
                    if not creds_correct:
                        request.setHeader(
                            b"www-authenticate", 'Basic realm="Secure Area"'
                        )
                        request.setResponseCode(HTTPStatus.UNAUTHORIZED)
                        request.finish()
                        return
                if csp.get(path):
                    request.setHeader(b"Content-Security-Policy", csp[path])
                if routes.get(path):
                    routes[path](request)
                    return
                file_content = None
                try:
                    file_content = (static_path / path[1:]).read_bytes()
                    request.setHeader(b"Content-Type", mimetypes.guess_type(path)[0])
                    request.setHeader(b"Cache-Control", "no-cache, no-store")
                    if path in gzip_routes:
                        request.setHeader("Content-Encoding", "gzip")
                        request.write(gzip.compress(file_content))
                    else:
                        request.write(file_content)
                    self.setResponseCode(HTTPStatus.OK)
                except (FileNotFoundError, IsADirectoryError, PermissionError):
                    request.setResponseCode(HTTPStatus.NOT_FOUND)
                self.finish()

        class MyHttp(http.HTTPChannel):
            requestFactory = TestServerHTTPHandler

        class MyHttpFactory(http.HTTPFactory):
            protocol = MyHttp

        self.listen(MyHttpFactory())

    async def wait_for_request(self, path):
        if path in self.request_subscribers:
            return await self.request_subscribers[path]
        future = asyncio.Future()
        self.request_subscribers[path] = future
        return await future

    def set_auth(self, path: str, username: str, password: str):
        self.auth[path] = (username, password)

    def set_csp(self, path: str, value: str):
        self.csp[path] = value

    def reset(self):
        self.request_subscribers.clear()
        self.auth.clear()
        self.csp.clear()
        self.gzip_routes.clear()
        self.routes.clear()

    def set_route(self, path, callback):
        self.routes[path] = callback

    def enable_gzip(self, path):
        self.gzip_routes.add(path)

    def set_redirect(self, from_, to):
        def handle_redirect(request):
            request.setResponseCode(HTTPStatus.FOUND)
            request.setHeader("location", to)
            request.finish()

        self.set_route(from_, handle_redirect)


class HTTPServer(Server):
    def listen(self, factory):
        reactor.listenTCP(self.PORT, factory)


class HTTPSServer(Server):
    protocol = "https"

    def listen(self, factory):
        cert = ssl.PrivateCertificate.fromCertificateAndKeyPair(
            ssl.Certificate.loadPEM(
                (_dirname / "testserver" / "cert.pem").read_bytes()
            ),
            ssl.KeyPair.load(
                (_dirname / "testserver" / "key.pem").read_bytes(), crypto.FILETYPE_PEM
            ),
        )
        contextFactory = cert.options()
        reactor.listenSSL(self.PORT, factory, contextFactory)


class WebSocketServerServer(WebSocketServerProtocol):
    def __init__(self) -> None:
        super().__init__()
        self.PORT = find_free_port()

    def start(self):
        ws = WebSocketServerFactory("ws://127.0.0.1:" + str(self.PORT))
        ws.protocol = WebSocketProtocol
        reactor.listenTCP(self.PORT, ws)


class WebSocketProtocol(WebSocketServerProtocol):
    def onConnect(self, request):
        pass

    def onOpen(self):
        self.sendMessage(b"incoming")

    def onMessage(self, payload, isBinary):
        if payload == b"echo-bin":
            self.sendMessage(b"\x04\x02", True)
            self.sendClose()
        if payload == b"echo-text":
            self.sendMessage(b"text", False)
            self.sendClose()
        if payload == b"close":
            self.sendClose()

    def onClose(self, wasClean, code, reason):
        pass


class TestServer:
    def __init__(self) -> None:
        self.server = HTTPServer()
        self.https_server = HTTPSServer()
        self.ws_server = WebSocketServerServer()

    def start(self) -> None:
        self.server.start()
        self.https_server.start()
        self.ws_server.start()
        self.thread = threading.Thread(
            target=lambda: reactor.run(installSignalHandlers=0)
        )
        self.thread.start()

    def stop(self) -> None:
        reactor.stop()
        self.thread.join()

    def reset(self) -> None:
        self.server.reset()
        self.https_server.reset()


test_server = TestServer()
