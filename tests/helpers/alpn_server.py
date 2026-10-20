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

"""A TLS server that records the ALPN protocols that clients offer, in both flavors.

Port of the https.createServer({ ALPNCallback }) server in
tests/library/fetch-proxy.spec.ts. Python's ssl module does not show the offered
protocols, so the server uses pyOpenSSL's ALPN select callback. Like the upstream
callback, it selects no protocol, so the handshake fails and the client gets an
error.
"""

import socket
import threading
from pathlib import Path
from typing import List, Optional, Set, cast

from OpenSSL import SSL

_CERT_DIR = Path(__file__).parent.parent / "testserver"


class AlpnRecordingServer:
    """Listens on 127.0.0.1, on a free port, with the test server certificate."""

    def __init__(self) -> None:
        self.offered_protocols: Optional[List[str]] = None
        self._context = SSL.Context(SSL.TLS_SERVER_METHOD)
        self._context.use_certificate_file(str(_CERT_DIR / "cert.pem"))
        self._context.use_privatekey_file(str(_CERT_DIR / "key.pem"))
        self._context.set_alpn_select_callback(self._select)
        self._listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listener.bind(("127.0.0.1", 0))
        self._listener.listen(16)
        self.port: int = self._listener.getsockname()[1]
        self._sockets: Set[socket.socket] = set()
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()

    def close(self) -> None:
        with self._lock:
            sockets = list(self._sockets)
        for sock in [self._listener, *sockets]:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()
        self._thread.join()

    def _select(self, connection: SSL.Connection, protocols: List[bytes]) -> bytes:
        self.offered_protocols = [protocol.decode() for protocol in protocols]
        return cast(bytes, SSL.NO_OVERLAPPING_PROTOCOLS)

    def _accept_loop(self) -> None:
        while True:
            try:
                sock, _ = self._listener.accept()
            except OSError:
                return
            with self._lock:
                self._sockets.add(sock)
            threading.Thread(target=self._serve, args=(sock,), daemon=True).start()

    def _serve(self, sock: socket.socket) -> None:
        connection = SSL.Connection(self._context, sock)
        connection.set_accept_state()
        try:
            connection.do_handshake()
            # The server does not answer requests: the client gets an error.
        except (SSL.Error, OSError):
            pass
        finally:
            with self._lock:
                self._sockets.discard(sock)
            sock.close()
