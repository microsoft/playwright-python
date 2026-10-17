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

"""An HTTP server that answers every request with the same body, in both flavors.

Port of the dummyServerPort and ipV6ServerPort fixtures in
tests/library/browsertype-connect.spec.ts.
"""

import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Type


class FixedResponseServer:
    """Listens on host (only), on a free port, and answers every request with body."""

    def __init__(self, host: str, body: str) -> None:
        data = body.encode()

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                self.send_response(200)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, format: str, *args: Any) -> None:
                pass

        server_class: Type[ThreadingHTTPServer] = ThreadingHTTPServer
        if ":" in host:

            class IPv6Server(ThreadingHTTPServer):
                address_family = socket.AF_INET6

            server_class = IPv6Server
        self._server = server_class((host, 0), Handler)
        self._server.daemon_threads = True
        self.port: int = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join()
