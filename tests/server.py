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

import asyncio
import gzip
import mimetypes
import os
import socket
import threading
from contextlib import closing
from http import HTTPStatus

from twisted.internet import reactor
from twisted.web import http


def find_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


class Server:
    def __init__(self):
        self.PORT = find_free_port()
        self.EMPTY_PAGE = f"http://localhost:{self.PORT}/empty.html"
        self.PREFIX = f"http://localhost:{self.PORT}"
        self.CROSS_PROCESS_PREFIX = f"http://127.0.0.1:{self.PORT}"
        # On Windows, this list can be empty, reporting text/plain for scripts.
        mimetypes.add_type("text/html", ".html")
        mimetypes.add_type("text/css", ".css")
        mimetypes.add_type("application/javascript", ".js")
        mimetypes.add_type("image/png", ".png")
        mimetypes.add_type("font/woff2", ".woff2")

    def __repr__(self) -> str:
        return self.PREFIX

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
        static_path = os.path.join(os.path.dirname(__file__), "assets")

        class TestServerHTTPHandler(http.Request):
            def process(self):
                request = self
                self.post_body = request.content.read().decode()
                request.content.seek(0, 0)
                uri = request.uri.decode()
                if request_subscribers.get(uri):
                    request_subscribers[uri].set_result(request)
                    request_subscribers.pop(uri)

                if auth.get(uri):
                    authorization_header = request.requestHeaders.getRawHeaders(
                        "authorization"
                    )
                    creds_correct = False
                    if authorization_header:
                        creds_correct = auth.get(uri) == (
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
                if csp.get(uri):
                    request.setHeader(b"Content-Security-Policy", csp[uri])
                if routes.get(uri):
                    routes[uri](request)
                    return
                file_content = None
                try:
                    file_content = open(
                        os.path.join(static_path, request.path.decode()[1:]), "rb"
                    ).read()
                except (FileNotFoundError, IsADirectoryError):
                    request.setResponseCode(HTTPStatus.NOT_FOUND)
                if file_content:
                    request.setHeader("Content-Type", mimetypes.guess_type(uri)[0])
                    if uri in gzip_routes:
                        request.setHeader("Content-Encoding", "gzip")
                        request.write(gzip.compress(file_content))
                    else:
                        request.write(file_content)
                    self.setResponseCode(HTTPStatus.OK)
                self.finish()

        class MyHttp(http.HTTPChannel):
            requestFactory = TestServerHTTPHandler

        class MyHttpFactory(http.HTTPFactory):
            protocol = MyHttp

        reactor.listenTCP(self.PORT, MyHttpFactory())
        self.thread = threading.Thread(
            target=lambda: reactor.run(installSignalHandlers=0)
        )
        self.thread.start()

    def stop(self):
        reactor.stop()
        self.thread.join()

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


server = Server()
