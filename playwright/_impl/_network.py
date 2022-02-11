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

import asyncio
import base64
import json
import mimetypes
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Coroutine,
    Dict,
    List,
    Optional,
    Union,
    cast,
)
from urllib import parse

from playwright._impl._api_structures import (
    Headers,
    HeadersArray,
    RemoteAddr,
    RequestSizes,
    ResourceTiming,
    SecurityDetails,
)
from playwright._impl._api_types import Error
from playwright._impl._connection import (
    ChannelOwner,
    from_channel,
    from_nullable_channel,
)
from playwright._impl._event_context_manager import EventContextManagerImpl
from playwright._impl._helper import ContinueParameters, locals_to_params
from playwright._impl._wait_helper import WaitHelper

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._fetch import APIResponse
    from playwright._impl._frame import Frame


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
        self._provisional_headers = RawHeaders(self._initializer["headers"])
        self._all_headers_future: Optional[asyncio.Future[RawHeaders]] = None

    def __repr__(self) -> str:
        return f"<Request url={self.url!r} method={self.method!r}>"

    @property
    def url(self) -> str:
        return self._initializer["url"]

    @property
    def resource_type(self) -> str:
        return self._initializer["resourceType"]

    @property
    def method(self) -> str:
        return self._initializer["method"]

    async def sizes(self) -> RequestSizes:
        response = await self.response()
        if not response:
            raise Error("Unable to fetch sizes for failed request")
        return await response._channel.send("sizes")

    @property
    def post_data(self) -> Optional[str]:
        data = self.post_data_buffer
        if not data:
            return None
        return data.decode()

    @property
    def post_data_json(self) -> Optional[Any]:
        post_data = self.post_data
        if not post_data:
            return None
        content_type = self.headers["content-type"]
        if content_type == "application/x-www-form-urlencoded":
            return dict(parse.parse_qsl(post_data))
        try:
            return json.loads(post_data)
        except Exception:
            raise Error(f"POST data is not a valid JSON object: {post_data}")

    @property
    def post_data_buffer(self) -> Optional[bytes]:
        b64_content = self._initializer.get("postData")
        if b64_content is None:
            return None
        return base64.b64decode(b64_content)

    async def response(self) -> Optional["Response"]:
        return from_nullable_channel(await self._channel.send("response"))

    @property
    def frame(self) -> "Frame":
        return from_channel(self._initializer["frame"])

    def is_navigation_request(self) -> bool:
        return self._initializer["isNavigationRequest"]

    @property
    def redirected_from(self) -> Optional["Request"]:
        return self._redirected_from

    @property
    def redirected_to(self) -> Optional["Request"]:
        return self._redirected_to

    @property
    def failure(self) -> Optional[str]:
        return self._failure_text

    @property
    def timing(self) -> ResourceTiming:
        return self._timing

    @property
    def headers(self) -> Headers:
        return self._provisional_headers.headers()

    async def all_headers(self) -> Headers:
        return (await self._actual_headers()).headers()

    async def headers_array(self) -> HeadersArray:
        return (await self._actual_headers()).headers_array()

    async def header_value(self, name: str) -> Optional[str]:
        return (await self._actual_headers()).get(name)

    async def _actual_headers(self) -> "RawHeaders":
        if not self._all_headers_future:
            self._all_headers_future = asyncio.Future()
            headers = await self._channel.send("rawRequestHeaders")
            self._all_headers_future.set_result(RawHeaders(headers))
        return await self._all_headers_future


class Route(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)

    def __repr__(self) -> str:
        return f"<Route request={self.request}>"

    @property
    def request(self) -> Request:
        return from_channel(self._initializer["request"])

    async def abort(self, errorCode: str = None) -> None:
        await self._race_with_page_close(
            self._channel.send("abort", locals_to_params(locals()))
        )

    async def fulfill(
        self,
        status: int = None,
        headers: Dict[str, str] = None,
        body: Union[str, bytes] = None,
        path: Union[str, Path] = None,
        contentType: str = None,
        response: "APIResponse" = None,
    ) -> None:
        params = locals_to_params(locals())
        if response:
            del params["response"]
            params["status"] = (
                params["status"] if params.get("status") else response.status
            )
            params["headers"] = (
                params["headers"] if params.get("headers") else response.headers
            )
            from playwright._impl._fetch import APIResponse

            if body is None and path is None and isinstance(response, APIResponse):
                if response._request._connection is self._connection:
                    params["fetchResponseUid"] = response._fetch_uid
                else:
                    body = await response.body()

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
        await self._race_with_page_close(self._channel.send("fulfill", params))

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
        await self._race_with_page_close(
            self._channel.send("continue", cast(Any, overrides))
        )

    def _internal_continue(self) -> None:
        async def continue_route() -> None:
            try:
                await self.continue_()
            except Exception:
                pass

        asyncio.create_task(continue_route())

    async def _race_with_page_close(self, future: Coroutine) -> None:
        if hasattr(self.request.frame, "_page"):
            page = self.request.frame._page
            # When page closes or crashes, we catch any potential rejects from this Route.
            # Note that page could be missing when routing popup's initial request that
            # does not have a Page initialized just yet.
            await asyncio.wait(
                [asyncio.create_task(future), page._closed_or_crashed_future],
                return_when=asyncio.FIRST_COMPLETED,
            )
        else:
            await future


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
        self._provisional_headers = RawHeaders(
            cast(HeadersArray, self._initializer["headers"])
        )
        self._raw_headers_future: Optional[asyncio.Future[RawHeaders]] = None
        self._finished_future: asyncio.Future[bool] = asyncio.Future()

    def __repr__(self) -> str:
        return f"<Response url={self.url!r} request={self.request}>"

    @property
    def url(self) -> str:
        return self._initializer["url"]

    @property
    def ok(self) -> bool:
        # Status 0 is for file:// URLs
        return self._initializer["status"] == 0 or (
            self._initializer["status"] >= 200 and self._initializer["status"] <= 299
        )

    @property
    def status(self) -> int:
        return self._initializer["status"]

    @property
    def status_text(self) -> str:
        return self._initializer["statusText"]

    @property
    def headers(self) -> Headers:
        return self._provisional_headers.headers()

    async def all_headers(self) -> Headers:
        return (await self._actual_headers()).headers()

    async def headers_array(self) -> HeadersArray:
        return (await self._actual_headers()).headers_array()

    async def header_value(self, name: str) -> Optional[str]:
        return (await self._actual_headers()).get(name)

    async def header_values(self, name: str) -> List[str]:
        return (await self._actual_headers()).get_all(name)

    async def _actual_headers(self) -> "RawHeaders":
        if not self._raw_headers_future:
            self._raw_headers_future = asyncio.Future()
            headers = cast(HeadersArray, await self._channel.send("rawResponseHeaders"))
            self._raw_headers_future.set_result(RawHeaders(headers))
        return await self._raw_headers_future

    async def server_addr(self) -> Optional[RemoteAddr]:
        return await self._channel.send("serverAddr")

    async def security_details(self) -> Optional[SecurityDetails]:
        return await self._channel.send("securityDetails")

    async def finished(self) -> None:
        await self._finished_future

    async def body(self) -> bytes:
        binary = await self._channel.send("body")
        return base64.b64decode(binary)

    async def text(self) -> str:
        content = await self.body()
        return content.decode()

    async def json(self) -> Any:
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
            "socketError",
            lambda params: self.emit(WebSocket.Events.Error, params["error"]),
        )
        self._channel.on("close", lambda params: self._on_close())

    def __repr__(self) -> str:
        return f"<WebSocket url={self.url!r}>"

    @property
    def url(self) -> str:
        return self._initializer["url"]

    def expect_event(
        self,
        event: str,
        predicate: Callable = None,
        timeout: float = None,
    ) -> EventContextManagerImpl:
        if timeout is None:
            timeout = cast(Any, self._parent)._timeout_settings.timeout()
        wait_helper = WaitHelper(self, f"web_socket.expect_event({event})")
        wait_helper.reject_on_timeout(
            cast(float, timeout),
            f'Timeout {timeout}ms exceeded while waiting for event "{event}"',
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
        wait_helper.wait_for_event(self, event, predicate)
        return EventContextManagerImpl(wait_helper.result())

    async def wait_for_event(
        self, event: str, predicate: Callable = None, timeout: float = None
    ) -> Any:
        async with self.expect_event(event, predicate, timeout) as event_info:
            pass
        return await event_info

    def _on_frame_sent(self, opcode: int, data: str) -> None:
        if opcode == 2:
            self.emit(WebSocket.Events.FrameSent, base64.b64decode(data))
        elif opcode == 1:
            self.emit(WebSocket.Events.FrameSent, data)

    def _on_frame_received(self, opcode: int, data: str) -> None:
        if opcode == 2:
            self.emit(WebSocket.Events.FrameReceived, base64.b64decode(data))
        elif opcode == 1:
            self.emit(WebSocket.Events.FrameReceived, data)

    def is_closed(self) -> bool:
        return self._is_closed

    def _on_close(self) -> None:
        self._is_closed = True
        self.emit(WebSocket.Events.Close, self)


def serialize_headers(headers: Dict[str, str]) -> HeadersArray:
    return [{"name": name, "value": value} for name, value in headers.items()]


class RawHeaders:
    def __init__(self, headers: HeadersArray) -> None:
        self._headers_array = headers
        self._headers_map: Dict[str, Dict[str, bool]] = defaultdict(dict)
        for header in headers:
            self._headers_map[header["name"].lower()][header["value"]] = True

    def get(self, name: str) -> Optional[str]:
        values = self.get_all(name)
        if not values:
            return None
        separator = "\n" if name.lower() == "set-cookie" else ", "
        return separator.join(values)

    def get_all(self, name: str) -> List[str]:
        return list(self._headers_map[name.lower()].keys())

    def headers(self) -> Dict[str, str]:
        result = {}
        for name in self._headers_map.keys():
            result[name] = cast(str, self.get(name))
        return result

    def headers_array(self) -> HeadersArray:
        return self._headers_array
