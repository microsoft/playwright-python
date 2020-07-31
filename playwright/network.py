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

import base64
import json
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union, cast

from playwright.connection import ChannelOwner, from_channel, from_nullable_channel
from playwright.helper import ContinueParameters, Error, Header, locals_to_params

if TYPE_CHECKING:  # pragma: no cover
    from playwright.frame import Frame


class Request(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._redirected_from: Optional["Request"] = from_nullable_channel(
            initializer.get("redirectedFrom")
        )
        self._redirected_to: Optional["Request"] = None
        if self._redirected_from:
            self._redirected_from._redirected_to = self
        self._failure_text: Optional[str] = None

    @property
    def url(self) -> str:
        return self._initializer["url"]

    @property
    def resourceType(self) -> str:
        return self._initializer["resourceType"]

    @property
    def method(self) -> str:
        return self._initializer["method"]

    @property
    def postData(self) -> Optional[str]:
        b64_content = self._initializer.get("postData")
        if not b64_content:
            return None
        return base64.b64decode(bytes(b64_content, "utf-8")).decode()

    @property
    def headers(self) -> Dict[str, str]:
        return parse_headers(self._initializer["headers"])

    async def response(self) -> Optional["Response"]:
        return from_nullable_channel(await self._channel.send("response"))

    @property
    def frame(self) -> "Frame":
        return from_channel(self._initializer["frame"])

    def isNavigationRequest(self) -> bool:
        return self._initializer["isNavigationRequest"]

    @property
    def redirectedFrom(self) -> Optional["Request"]:
        return self._redirected_from

    @property
    def redirectedTo(self) -> Optional["Request"]:
        return self._redirected_to

    @property
    def failure(self) -> Optional[str]:
        return self._failure_text


class Route(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)

    @property
    def request(self) -> Request:
        return from_channel(self._initializer["request"])

    async def abort(self, errorCode: str = None) -> None:
        await self._channel.send("abort", locals_to_params(locals()))

    async def fulfill(
        self,
        status: int = None,
        headers: Dict[str, str] = None,
        body: Union[str, bytes] = None,
        contentType: str = None,
    ) -> None:
        params = locals_to_params(locals())
        if contentType:
            if headers is None:
                headers = {}
            headers["Content-Type"] = contentType
            del params["contentType"]
        if headers:
            params["headers"] = serialize_headers(headers)
        if isinstance(body, str):
            params["body"] = body
            params["isBase64"] = False
        elif isinstance(body, bytes):
            params["body"] = base64.b64encode(body).decode()
            params["isBase64"] = True
        await self._channel.send("fulfill", params)

    async def continue_(
        self,
        method: str = None,
        headers: Dict[str, str] = None,
        postData: Union[str, bytes] = None,
    ) -> None:
        overrides: ContinueParameters = {}
        if method:
            overrides["method"] = method
        if headers:
            overrides["headers"] = serialize_headers(headers)
        if isinstance(postData, str):
            overrides["postData"] = base64.b64encode(bytes(postData, "utf-8")).decode()
        elif isinstance(postData, bytes):
            overrides["postData"] = base64.b64encode(postData).decode()
        await self._channel.send("continue", cast(Any, overrides))


class Response(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)

    @property
    def url(self) -> str:
        return self._initializer["url"]

    @property
    def ok(self) -> bool:
        return self._initializer["status"] == 0 or (
            self._initializer["status"] >= 200 and self._initializer["status"] <= 299
        )

    @property
    def status(self) -> int:
        return self._initializer["status"]

    @property
    def statusText(self) -> str:
        return self._initializer["statusText"]

    @property
    def headers(self) -> Dict[str, str]:
        return parse_headers(self._initializer["headers"])

    async def finished(self) -> Optional[Error]:
        return await self._channel.send("finished")

    async def body(self) -> bytes:
        binary = await self._channel.send("body")
        return base64.b64decode(binary)

    async def text(self) -> str:
        content = await self.body()
        return content.decode("utf-8")

    async def json(self) -> Union[Dict, List]:
        return json.loads(await self.text())

    @property
    def request(self) -> Request:
        return from_channel(self._initializer["request"])

    @property
    def frame(self) -> "Frame":
        return self.request.frame


def serialize_headers(headers: Dict[str, str]) -> List[Header]:
    return [{"name": name, "value": value} for name, value in headers.items()]


def parse_headers(headers: List[Header]) -> Dict[str, str]:
    return {header["name"]: header["value"] for header in headers}
