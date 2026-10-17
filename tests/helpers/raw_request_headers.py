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

"""The request headers as the browser sent them, like `req.rawHeaders` in Node.js.

The test server (twisted) changes the case of each header name when it parses the
request. Node.js keeps the names as they are. Call record_raw_headers() at the start
of a test, then raw_headers(request) in a route handler.
"""

from typing import List, Tuple

import pytest

from tests.server import TestServerHTTPChannel, TestServerRequest

_ATTRIBUTE = "_pwtest_raw_headers"


def record_raw_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Records the header lines of each request until the end of the test."""
    original = TestServerHTTPChannel.headerReceived

    def header_received(channel: TestServerHTTPChannel, line: bytes) -> bool:
        # Runs on the server thread, for each header line of the request.
        request = channel.requests[-1]
        valid = original(channel, line)
        if valid:
            name, value = line.split(b":", 1)
            if not hasattr(request, _ATTRIBUTE):
                setattr(request, _ATTRIBUTE, [])
            getattr(request, _ATTRIBUTE).append(
                (name.decode(), value.strip(b" \t").decode())
            )
        return valid

    monkeypatch.setattr(TestServerHTTPChannel, "headerReceived", header_received)


def raw_headers(request: TestServerRequest) -> List[Tuple[str, str]]:
    """The (name, value) pairs of the request headers, in order and case as sent."""
    return list(getattr(request, _ATTRIBUTE, []))
