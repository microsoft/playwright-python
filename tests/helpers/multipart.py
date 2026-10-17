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

"""A multipart/form-data body parser for test server routes, in both flavors.

It replaces the parsers that upstream tests use on the server side: formidable, and the
WHATWG Request.formData() of Node.js. Like Request.formData(), it decodes the escapes that
the HTML standard puts in the name and filename parameters: %22 for a quote, %0D and %0A
for CR and LF.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional

_PARAM = re.compile(r';\s*([A-Za-z0-9_*-]+)="([^"]*)"')
_ESCAPES = {"%22": '"', "%0D": "\r", "%0A": "\n"}


@dataclass
class MultipartPart:
    name: str
    filename: Optional[str]
    content_type: Optional[str]
    data: bytes

    @property
    def text(self) -> str:
        return self.data.decode()


def _unescape(value: str) -> str:
    return re.sub("%22|%0D|%0A", lambda match: _ESCAPES[match.group(0)], value)


def _boundary(content_type: str) -> bytes:
    match = re.search(r'boundary=(?:"([^"]+)"|([^;\s]+))', content_type)
    if not match:
        raise ValueError(f"No boundary in content-type: {content_type}")
    return (match.group(1) or match.group(2)).encode()


def parse_multipart(content_type: str, body: bytes) -> List[MultipartPart]:
    """Returns the parts of a multipart/form-data body, in order."""
    delimiter = b"--" + _boundary(content_type)
    sections = body.split(delimiter)
    parts: List[MultipartPart] = []
    # sections[0] is the preamble; the section that starts with "--" is the epilogue.
    for section in sections[1:]:
        if section.startswith(b"--"):
            break
        section = section[2:] if section.startswith(b"\r\n") else section
        section = section[:-2] if section.endswith(b"\r\n") else section
        raw_headers, _, data = section.partition(b"\r\n\r\n")
        headers: Dict[str, str] = {}
        for line in raw_headers.decode().split("\r\n"):
            name, _, value = line.partition(":")
            headers[name.strip().lower()] = value.strip()
        params = dict(_PARAM.findall(headers.get("content-disposition", "")))
        filename = params.get("filename")
        parts.append(
            MultipartPart(
                name=_unescape(params.get("name", "")),
                filename=_unescape(filename) if filename is not None else None,
                content_type=headers.get("content-type"),
                data=data,
            )
        )
    return parts
