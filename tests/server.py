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
from contextlib import closing

import os
import socket
import threading
import os
import binascii

from twisted.internet import reactor
from twisted.web.static import File
from twisted.web import server as web_server, resource
from twisted.web._responses import UNAUTHORIZED


def find_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


class UnauthorizedResource(resource.ErrorPage):
    def __init__(self, message="Sorry, resource is unauthorized."):
        resource.ErrorPage.__init__(
            self, UNAUTHORIZED, "Unauthorized Resource", message
        )


class Server:
    def __init__(self):
        self.PORT = find_free_port()
        self.EMPTY_PAGE = f"http://localhost:{self.PORT}/empty.html"
        self.PREFIX = f"http://localhost:{self.PORT}"
        self.CROSS_PROCESS_PREFIX = f"http://127.0.0.1:{self.PORT}"

    def start(self):
        request_subscribers = {}
        auth = {}
        self.request_subscribers = request_subscribers
        self.auth = auth

        class CustomFileServer(File):
            def getChild(self, path, request):
                uri_path = request.uri.decode()
                if request_subscribers.get(uri_path):
                    request_subscribers[uri_path].set_result(request)
                    request_subscribers.pop(uri_path)

                if auth.get(uri_path):
                    authorization_header = request.requestHeaders.getRawHeaders(
                        "authorization"
                    )
                    creds_correct = False
                    if authorization_header:
                        creds = binascii.a2b_base64(
                            authorization_header[0].split(" ")[1].encode() + b"==="
                        ).decode()
                        creds_correct = ":".join(auth.get(uri_path)) == creds
                    if not (authorization_header or creds_correct):
                        request.responseHeaders.addRawHeader(
                            b"www-authenticate", b'Basic realm="Secure Area"'
                        )
                        return UnauthorizedResource()

                return super().getChild(path, request)

        static_path = os.path.join(os.path.dirname(__file__), "assets")
        resource = CustomFileServer(static_path)
        site = web_server.Site(resource)
        reactor.listenTCP(self.PORT, site)
        self.thread = threading.Thread(
            target=lambda: reactor.run(installSignalHandlers=0)
        )
        self.thread.start()

    def stop(self):
        reactor.stop()
        self.thread.join()

    async def wait_for_request(self, path):
        future = asyncio.Future()
        self.request_subscribers[path] = future
        future.add_done_callback(lambda f: self.request_subscribers.pop(path, None))
        return await future

    def set_auth(self, path: str, username: str, password: str):
        self.auth[path] = (username, password)

    def reset(self):
        self.request_subscribers.clear()
        self.auth.clear()


server = Server()
