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
from typing import List, Optional, Union

if sys.version_info >= (3, 8):  # pragma: no cover
    from typing import Literal, TypedDict
else:  # pragma: no cover
    from typing_extensions import Literal, TypedDict

# These are the structures that we like keeping in a JSON form for their potential
# reuse between SDKs / services. They are public and are a part of the
# stable API.

# Explicitly mark optional params as such for the documentation
# If there is at least one optional param, set total=False for better mypy handling.


class Cookie(TypedDict, total=False):
    name: str
    value: str
    url: Optional[str]
    domain: Optional[str]
    path: Optional[str]
    expires: Optional[float]
    httpOnly: Optional[bool]
    secure: Optional[bool]
    sameSite: Optional[Literal["Lax", "None", "Strict"]]


class FloatRect(TypedDict):
    x: float
    y: float
    width: float
    height: float


class Geolocation(TypedDict, total=False):
    latitude: float
    longitude: float
    accuracy: Optional[float]


class HttpCredentials(TypedDict):
    username: str
    password: str


class LocalStorageEntry(TypedDict):
    name: str
    value: str


class OriginState(TypedDict):
    origin: str
    localStorage: List[LocalStorageEntry]


class PdfMargins(TypedDict, total=False):
    top: Optional[Union[str, float]]
    right: Optional[Union[str, float]]
    bottom: Optional[Union[str, float]]
    left: Optional[Union[str, float]]


class Position(TypedDict):
    x: float
    y: float


class ProxySettings(TypedDict, total=False):
    server: str
    bypass: Optional[str]
    username: Optional[str]
    password: Optional[str]


class StorageState(TypedDict, total=False):
    cookies: Optional[List[Cookie]]
    origins: Optional[List[OriginState]]


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


class ViewportSize(TypedDict):
    width: int
    height: int


class SourceLocation(TypedDict):
    url: str
    lineNumber: int
    columnNumber: int


class FilePayload(TypedDict):
    name: str
    mimeType: str
    buffer: bytes


class RemoteAddr(TypedDict):
    ipAddress: str
    port: int


class SecurityDetails(TypedDict):
    issuer: Optional[str]
    protocol: Optional[str]
    subjectName: Optional[str]
    validFrom: Optional[float]
    validTo: Optional[float]
