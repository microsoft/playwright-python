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

"""Helpers that read HAR files, for the HAR tests in both flavors.

parse_har() is a port of parseHar() in tests/config/utils.ts. The size helpers are
ports of the helpers in tests/library/har-websocket.spec.ts.
"""

import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Sequence, Union


def parse_har(path: Union[str, Path]) -> Dict[str, bytes]:
    """Reads every entry of a .har.zip file. Port of parseHar() in tests/config/utils.ts."""
    with zipfile.ZipFile(path) as zip_file:
        return {name: zip_file.read(name) for name in zip_file.namelist()}


def read_har_log(path: Union[str, Path]) -> Dict[str, Any]:
    """Returns the "log" object of a .har file."""
    return json.loads(Path(path).read_bytes())["log"]


def har_time_to_ms(value: str) -> float:
    """Converts a HAR date (ISO 8601) to milliseconds, like new Date(value).valueOf()."""
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000


def headers_size(headers: Sequence[Dict[str, str]]) -> int:
    result = 0
    for header in headers:
        result += len(header["name"]) + len(": ") + len(header["value"]) + len("\r\n")
    return result


def request_headers_size(headers: Sequence[Dict[str, str]]) -> int:
    return len("GET /ws HTTP/1.1\r\n") + headers_size(headers)


def response_headers_size(headers: Sequence[Dict[str, str]]) -> int:
    return (
        len("HTTP/1.1 101 Switching Protocols\r\n")
        + headers_size(headers)
        + len("\r\n")
    )


def message_size(message: Union[str, List[int]]) -> int:
    """The size of a WebSocket frame that a server sends with this payload."""
    # The payload is short enough that they only need the minimum frame header size.
    if len(message) <= 125:
        return 6 + len(message)
    # The payload is large enough that additional bytes are needed to represent the payload length.
    if len(message) < 2**16:
        return 6 + 2 + len(message)
    return 6 + 8 + len(message)
