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

"""An HTTPS server that serves the files of a directory, in both flavors.

Port of `new TestServer(dirPath, port, loopback, { key, cert })` in
tests/config/testserver/index.ts, as tests/library/firefox/launcher.spec.ts uses it: a
static file server over TLS with a given key and certificate.
"""

import functools
import socket
import ssl
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Tuple


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        pass


class _TLSServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, context: ssl.SSLContext, directory: Path) -> None:
        self._context = context
        super().__init__(
            ("127.0.0.1", 0),
            functools.partial(_QuietHandler, directory=str(directory)),
        )

    def get_request(self) -> Tuple[socket.socket, Any]:
        sock, address = self.socket.accept()
        # The TLS handshake runs on the thread of the request, not on the accept
        # thread: a browser may open a connection and never use it.
        return (
            self._context.wrap_socket(
                sock, server_side=True, do_handshake_on_connect=False
            ),
            address,
        )

    def handle_error(self, request: Any, client_address: Any) -> None:
        # A browser drops connections, for example after a failed handshake.
        pass


class StaticHTTPSServer:
    """Serves the files of directory on https://localhost:<port>."""

    def __init__(self, directory: Path, cert: Path, key: Path) -> None:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert, key)
        self._server = _TLSServer(context, directory)
        self.PORT: int = self._server.server_address[1]
        self.PREFIX = f"https://localhost:{self.PORT}"
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join()
