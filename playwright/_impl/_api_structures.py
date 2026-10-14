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

# Generated from the docs by scripts/codegen/generate_api.js. Do not edit.

from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Sequence, TypedDict, Union


class BrowserBindResult(TypedDict):
    endpoint: str


class ClientCertificate(TypedDict, total=False):
    origin: str
    certPath: Optional[Union[str, Path]]
    cert: Optional[bytes]
    keyPath: Optional[Union[str, Path]]
    key: Optional[bytes]
    pfxPath: Optional[Union[str, Path]]
    pfx: Optional[bytes]
    passphrase: Optional[str]


class Clip(TypedDict):
    x: float
    y: float
    width: float
    height: float


class Cookie(TypedDict, total=False):
    name: str
    value: str
    domain: str
    path: str
    expires: float
    httpOnly: bool
    secure: bool
    sameSite: Literal["Lax", "None", "Strict"]
    partitionKey: Optional[str]


class DebuggerLocation(TypedDict):
    file: str
    line: Optional[int]
    column: Optional[int]


class DebuggerPausedDetails(TypedDict):
    location: DebuggerLocation
    title: str


class FilePayload(TypedDict):
    name: str
    mimeType: str
    buffer: bytes


class DropPayload(TypedDict, total=False):
    files: Optional[
        Union[str, Path, Sequence[Union[str, Path]], FilePayload, Sequence[FilePayload]]
    ]
    data: Optional[Dict[str, str]]


class FloatRect(TypedDict):
    x: float
    y: float
    width: float
    height: float


class Geolocation(TypedDict, total=False):
    latitude: float
    longitude: float
    accuracy: Optional[float]


class HttpCredentials(TypedDict, total=False):
    username: str
    password: str
    origin: Optional[str]
    send: Optional[Literal["always", "unauthorized"]]


class HttpHeader(TypedDict):
    name: str
    value: str


class LocalStorageEntry(TypedDict):
    name: str
    value: str


class Location(TypedDict, total=False):
    file: str
    line: Optional[int]
    column: Optional[int]


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


class RecordVideoSize(TypedDict):
    width: int
    height: int


class RemoteAddr(TypedDict):
    ipAddress: str
    port: int


class RequestSizes(TypedDict):
    requestBodySize: int
    requestHeadersSize: int
    responseBodySize: int
    responseHeadersSize: int


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


class ScreenSize(TypedDict):
    width: int
    height: int


class ScreencastActionStyle(TypedDict, total=False):
    point: Optional[str]
    highlight: Optional[str]
    title: Optional[str]


class ScreencastFrame(TypedDict):
    data: bytes
    timestamp: float
    viewportWidth: int
    viewportHeight: int


class ScreencastSize(TypedDict):
    width: int
    height: int


class SecurityDetails(TypedDict):
    issuer: Optional[str]
    protocol: Optional[str]
    subjectName: Optional[str]
    validFrom: Optional[float]
    validTo: Optional[float]


class SetCookieParam(TypedDict, total=False):
    name: str
    value: str
    url: Optional[str]
    domain: Optional[str]
    path: Optional[str]
    expires: Optional[float]
    httpOnly: Optional[bool]
    secure: Optional[bool]
    sameSite: Optional[Literal["Lax", "None", "Strict"]]
    partitionKey: Optional[str]


class SourceLocation(TypedDict):
    url: str
    line: int
    column: int
    lineNumber: int
    columnNumber: int


class StorageStateCookie(TypedDict, total=False):
    name: str
    value: str
    domain: str
    path: str
    expires: float
    httpOnly: bool
    secure: bool
    sameSite: Literal["Lax", "None", "Strict"]


class StorageState(TypedDict, total=False):
    cookies: List[StorageStateCookie]
    origins: List[OriginState]


class ViewportSize(TypedDict):
    width: int
    height: int


class VirtualCredential(TypedDict):
    id: str
    rpId: str
    userHandle: str
    privateKey: str
    publicKey: str
    signCount: int


class WebErrorLocation(TypedDict):
    url: str
    line: int
    column: int


class WebMCPToolAnnotations(TypedDict, total=False):
    readOnly: Optional[bool]
    untrustedContent: Optional[bool]
    consequential: Optional[bool]


class WebMCPTool(TypedDict, total=False):
    name: str
    description: str
    inputSchema: Optional[Any]
    annotations: Optional[WebMCPToolAnnotations]


class WebStorageItem(TypedDict):
    name: str
    value: str
