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

import sys
from typing import Any, Dict, Optional, Tuple, Union

if sys.version_info >= (3, 8):  # pragma: no cover
    from typing import TypedDict
else:  # pragma: no cover
    from typing_extensions import TypedDict


class Error(Exception):
    def __init__(self, message: str, stack: str = None) -> None:
        self.message = message
        self.stack = stack
        super().__init__(message)


class TimeoutError(Error):
    pass


class ApiType:
    def __eq__(self, other: Any) -> bool:
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        else:
            return False

    def _to_json(self) -> Dict:
        return filter_out_none(self.__dict__)


class FilePayload(ApiType):
    name: str
    mime_type: str
    buffer: bytes

    def __init__(self, name: str, mime_type: str, buffer: bytes):
        self.name = name
        self.mime_type = mime_type
        self.buffer = buffer


class FloatRect(ApiType):
    x: float
    y: float
    width: float
    height: float

    @classmethod
    def _parse(cls, dict: Optional[Dict]) -> Optional["FloatRect"]:
        if not dict:
            return None
        return FloatRect(dict["x"], dict["y"], dict["width"], dict["height"])

    def __init__(self, x: float, y: float, width: float, height: float):
        self.x = x
        self.y = y
        self.width = width
        self.height = height


class DeviceDescriptor(TypedDict):
    user_agent: Optional[str]
    viewport: Optional[Tuple[int, int]]
    device_scale_factor: Optional[int]
    is_mobile: Optional[bool]
    has_touch: Optional[bool]


class Geolocation(ApiType):
    latitude: float
    longitude: float
    accuracy: Optional[float]

    def __init__(self, latitude: float, longitude: float, accuracy: float = None):
        self.latitude = latitude
        self.longitude = longitude
        self.accuracy = accuracy


class PdfMargins(ApiType):
    top: Optional[Union[str, int]]
    right: Optional[Union[str, int]]
    bottom: Optional[Union[str, int]]
    left: Optional[Union[str, int]]

    def __init__(
        self,
        top: Union[str, int],
        right: Union[str, int],
        bottom: Union[str, int],
        left: Union[str, int],
    ):
        self.top = top
        self.right = right
        self.bottom = bottom
        self.left = left


class ProxySettings(ApiType):
    server: str
    bypass: Optional[str]
    username: Optional[str]
    password: Optional[str]

    def __init__(
        self,
        server: str,
        bypass: str = None,
        username: str = None,
        password: str = None,
    ):
        self.server = server
        self.bypass = bypass
        self.username = username
        self.password = password


class SourceLocation(ApiType):
    url: str
    line: int
    column: int

    def __init__(self, url: str, line: int, column: int):
        self.url = url
        self.line = line
        self.column = column


def filter_out_none(args: Dict) -> Any:
    copy = {}
    for key in args:
        if key == "self":
            continue
        if args[key] is not None:
            copy[key] = args[key]
    return copy
