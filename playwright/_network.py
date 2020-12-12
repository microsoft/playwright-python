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
import mimetypes
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Union, cast
from urllib import parse

from playwright._connection import ChannelOwner, from_channel, from_nullable_channel
from playwright._event_context_manager import EventContextManagerImpl
from playwright._helper import ContinueParameters, Header, locals_to_params
from playwright._types import Error, RequestFailure, ResourceTiming
from playwright._wait_helper import WaitHelper

if TYPE_CHECKING:  # pragma: no cover
    from playwright._frame import Frame


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
        self._timing: ResourceTiming = {
            "startTime": 0,
            "domainLookupStart": -1,
            "domainLookupEnd": -1,
            "connectStart": -1,
            "secureConnectionStart": -1,
            "connectEnd": -1,
            "requestStart": -1,
            "responseStart": -1,
            "responseEnd": -1,
        }
        self._headers: Dict[str, str] = parse_headers(self._initializer["headers"])

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
        data = self.postDataBuffer
        if not data:
            return None
        return data.decode()

    @property
    def postDataJSON(self) -> Optional[Dict]:
        post_data = self.postData
        if not post_data:
            return None
        content_type = self.headers["content-type"]
        if not content_type:
            return None
        if content_type == "application/x-www-form-urlencoded":
            return dict(parse.parse_qsl(post_data))
        return json.loads(post_data)

    @property
    def postDataBuffer(self) -> Optional[bytes]:
        b64_content = self._initializer.get("postData")
        if not b64_content:
            return None
        return base64.b64decode(b64_content)

    @property
    def headers(self) -> Dict[str, str]:
        return self._headers

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
    def failure(self) -> Optional[RequestFailure]:
        return {"errorText": self._failure_text} if self._failure_text else None

    @property
    def timing(self) -> ResourceTiming:
        return self._timing


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
        path: Union[str, Path] = None,
        contentType: str = None,
    ) -> None:
        params = locals_to_params(locals())
        length = 0
        if isinstance(body, str):
            params["body"] = body
            params["isBase64"] = False
            length = len(body.encode())
        elif isinstance(body, bytes):
            params["body"] = base64.b64encode(body).decode()
            params["isBase64"] = True
            length = len(body)
        elif path:
            del params["path"]
            file_content = Path(path).read_bytes()
            params["body"] = base64.b64encode(file_content).decode()
            params["isBase64"] = True
            length = len(file_content)

        headers = {k.lower(): str(v) for k, v in params.get("headers", {}).items()}
        if params.get("contentType"):
            headers["content-type"] = params["contentType"]
        elif path:
            headers["content-type"] = (
                mimetypes.guess_type(str(Path(path)))[0] or "application/octet-stream"
            )
        if length and "content-length" not in headers:
            headers["content-length"] = str(length)
        params["headers"] = serialize_headers(headers)
        await self._channel.send("fulfill", params)

    async def continue_(
        self,
        url: str = None,
        method: str = None,
        headers: Dict[str, str] = None,
        postData: Union[str, bytes] = None,
    ) -> None:
        overrides: ContinueParameters = {}
        if url:
            overrides["url"] = url
        if method:
            overrides["method"] = method
        if headers:
            overrides["headers"] = serialize_headers(headers)
        if isinstance(postData, str):
            overrides["postData"] = base64.b64encode(postData.encode()).decode()
        elif isinstance(postData, bytes):
            overrides["postData"] = base64.b64encode(postData).decode()
        await self._channel.send("continue", cast(Any, overrides))


class Response(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._request: Request = from_channel(self._initializer["request"])
        timing = self._initializer["timing"]
        self._request._timing["startTime"] = timing["startTime"]
        self._request._timing["domainLookupStart"] = timing["domainLookupStart"]
        self._request._timing["domainLookupEnd"] = timing["domainLookupEnd"]
        self._request._timing["connectStart"] = timing["connectStart"]
        self._request._timing["secureConnectionStart"] = timing["secureConnectionStart"]
        self._request._timing["connectEnd"] = timing["connectEnd"]
        self._request._timing["requestStart"] = timing["requestStart"]
        self._request._timing["responseStart"] = timing["responseStart"]
        self._request._headers = parse_headers(self._initializer["requestHeaders"])

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
        return content.decode()

    async def json(self) -> Union[Dict, List]:
        return json.loads(await self.text())

    @property
    def request(self) -> Request:
        return self._request

    @property
    def frame(self) -> "Frame":
        return self._request.frame


class WebSocket(ChannelOwner):

    Events = SimpleNamespace(
        Close="close",
        FrameReceived="framereceived",
        FrameSent="framesent",
        Error="socketerror",
    )

    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._is_closed = False
        self._channel.on(
            "frameSent",
            lambda params: self._on_frame_sent(params["opcode"], params["data"]),
        )
        self._channel.on(
            "frameReceived",
            lambda params: self._on_frame_received(params["opcode"], params["data"]),
        )
        self._channel.on(
            "error", lambda params: self.emit(WebSocket.Events.Error, params["error"])
        )
        self._channel.on("close", lambda params: self._on_close())

    @property
    def url(self) -> str:
        return self._initializer["url"]

    async def waitForEvent(
        self, event: str, predicate: Callable[[Any], bool] = None, timeout: int = None
    ) -> Any:
        if timeout is None:
            timeout = cast(Any, self._parent)._timeout_settings.timeout()
        wait_helper = WaitHelper(self._loop)
        wait_helper.reject_on_timeout(
            timeout, f'Timeout while waiting for event "${event}"'
        )
        if event != WebSocket.Events.Close:
            wait_helper.reject_on_event(
                self, WebSocket.Events.Close, Error("Socket closed")
            )
        if event != WebSocket.Events.Error:
            wait_helper.reject_on_event(
                self, WebSocket.Events.Error, Error("Socket error")
            )
        wait_helper.reject_on_event(self._parent, "close", Error("Page closed"))
        return await wait_helper.wait_for_event(self, event, predicate)

    def expect_event(
        self,
        event: str,
        predicate: Callable[[Any], bool] = None,
        timeout: int = None,
    ) -> EventContextManagerImpl:
        return EventContextManagerImpl(self.waitForEvent(event, predicate, timeout))

    def _on_frame_sent(self, opcode: int, data: str) -> None:
        if opcode == 2:
            self.emit(WebSocket.Events.FrameSent, base64.b64decode(data))
        else:
            self.emit(WebSocket.Events.FrameSent, data)

    def _on_frame_received(self, opcode: int, data: str) -> None:
        if opcode == 2:
            self.emit(WebSocket.Events.FrameReceived, base64.b64decode(data))
        else:
            self.emit(WebSocket.Events.FrameReceived, data)

    def isClosed(self) -> bool:
        return self._is_closed

    def _on_close(self) -> None:
        self._is_closed = True
        self.emit(WebSocket.Events.Close)


def serialize_headers(headers: Dict[str, str]) -> List[Header]:
    return [{"name": name, "value": value} for name, value in headers.items()]


def parse_headers(headers: List[Header]) -> Dict[str, str]:
    return {header["name"].lower(): header["value"] for header in headers}
