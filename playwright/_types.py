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
from pathlib import Path
from typing import Dict, List, Optional, Union

if sys.version_info >= (3, 8):  # pragma: no cover
    from typing import Literal, TypedDict
else:  # pragma: no cover
    from typing_extensions import Literal, TypedDict

# Explicitly mark optional params as such for the documentation
# If there is at least one optional param, set total=False for better mypy handling.


class Cookie(TypedDict, total=False):
    name: str
    value: str
    url: Optional[str]
    domain: Optional[str]
    path: Optional[str]
    expires: Optional[int]
    httpOnly: Optional[bool]
    secure: Optional[bool]
    sameSite: Optional[Literal["Strict", "Lax", "None"]]


class StorageState(TypedDict, total=False):
    cookies: Optional[List[Cookie]]
    origins: Optional[List[Dict]]


class MousePosition(TypedDict):
    x: float
    y: float


class ResourceTiming(TypedDict):
    startTime: float
    domainLookupStart: float
    domainLookupEnd: float
    connectStart: float
    secureConnectionStart: float
    connectEnd: float
    requestStart: float
    responseStart: float
    responseEnd: float


class FilePayload(TypedDict):
    name: str
    mimeType: str
    buffer: bytes


class SelectOption(TypedDict, total=False):
    value: Optional[str]
    label: Optional[str]
    index: Optional[str]


class ConsoleMessageLocation(TypedDict):
    url: str
    lineNumber: int
    columnNumber: int


class RequestFailure(TypedDict):
    errorText: str


class Credentials(TypedDict):
    username: str
    password: str


class IntSize(TypedDict):
    width: int
    height: int


class FloatRect(TypedDict):
    x: float
    y: float
    width: float
    height: float


class Geolocation(TypedDict, total=False):
    latitude: float
    longitude: float
    accuracy: Optional[float]


class ProxyServer(TypedDict, total=False):
    server: str
    bypass: Optional[str]
    username: Optional[str]
    password: Optional[str]


class PdfMargins(TypedDict, total=False):
    top: Optional[Union[str, int]]
    right: Optional[Union[str, int]]
    bottom: Optional[Union[str, int]]
    left: Optional[Union[str, int]]


class RecordHarOptions(TypedDict, total=False):
    omitContent: Optional[bool]
    path: Union[str, Path]


class RecordVideoOptions(TypedDict, total=False):
    dir: Union[str, Path]
    size: Optional[IntSize]


class DeviceDescriptor(TypedDict, total=False):
    userAgent: Optional[str]
    viewport: Optional[IntSize]
    deviceScaleFactor: Optional[int]
    isMobile: Optional[bool]
    hasTouch: Optional[bool]


class Error(Exception):
    def __init__(self, message: str, stack: str = None) -> None:
        self.message = message
        self.stack = stack
        super().__init__(message)


class TimeoutError(Error):
    pass
