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
import inspect
import json
import json as json_utils
import mimetypes
import sys
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

if sys.version_info >= (3, 8):  # pragma: no cover
    from typing import TypedDict
else:  # pragma: no cover
    from typing_extensions import TypedDict

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
    filter_none,
    from_channel,
    from_nullable_channel,
)
from playwright._impl._event_context_manager import EventContextManagerImpl
from playwright._impl._helper import locals_to_params
from playwright._impl._wait_helper import WaitHelper

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._browser_context import BrowserContext
    from playwright._impl._fetch import APIResponse
    from playwright._impl._frame import Frame
    from playwright._impl._page import Page


class FallbackOverrideParameters(TypedDict, total=False):
    url: Optional[str]
    method: Optional[str]
    headers: Optional[Dict[str, str]]
    postData: Optional[Union[str, bytes]]


class SerializedFallbackOverrides:
    def __init__(self) -> None:
        self.url: Optional[str] = None
        self.method: Optional[str] = None
        self.headers: Optional[Dict[str, str]] = None
        self.post_data_buffer: Optional[bytes] = None


def serialize_headers(headers: Dict[str, str]) -> HeadersArray:
    return [
        {"name": name, "value": value}
        for name, value in headers.items()
        if value is not None
    ]


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
        self._fallback_overrides: SerializedFallbackOverrides = (
            SerializedFallbackOverrides()
        )
        base64_post_data = initializer.get("postData")
        if base64_post_data is not None:
            self._fallback_overrides.post_data_buffer = base64.b64decode(
                base64_post_data
            )

    def __repr__(self) -> str:
        return f"<Request url={self.url!r} method={self.method!r}>"

    def _apply_fallback_overrides(self, overrides: FallbackOverrideParameters) -> None:
        self._fallback_overrides.url = overrides.get(
            "url", self._fallback_overrides.url
        )
        self._fallback_overrides.method = overrides.get(
            "method", self._fallback_overrides.method
        )
        self._fallback_overrides.headers = overrides.get(
            "headers", self._fallback_overrides.headers
        )
        post_data = overrides.get("postData")
        if isinstance(post_data, str):
            self._fallback_overrides.post_data_buffer = post_data.encode()
        elif isinstance(post_data, bytes):
            self._fallback_overrides.post_data_buffer = post_data
        elif post_data is not None:
            self._fallback_overrides.post_data_buffer = json.dumps(post_data).encode()

    @property
    def url(self) -> str:
        return cast(str, self._fallback_overrides.url or self._initializer["url"])

    @property
    def resource_type(self) -> str:
        return self._initializer["resourceType"]

    @property
    def method(self) -> str:
        return cast(str, self._fallback_overrides.method or self._initializer["method"])

    async def sizes(self) -> RequestSizes:
        response = await self.response()
        if not response:
            raise Error("Unable to fetch sizes for failed request")
        return await response._channel.send("sizes")

    @property
    def post_data(self) -> Optional[str]:
        data = self._fallback_overrides.post_data_buffer
        if not data:
            return None
        return data.decode() if isinstance(data, bytes) else data

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
        return self._fallback_overrides.post_data_buffer

    async def response(self) -> Optional["Response"]:
        return from_nullable_channel(await self._channel.send("response"))

    @property
    def frame(self) -> "Frame":
        if not self._initializer.get("frame"):
            raise Error("Service Worker requests do not have an associated frame.")
        frame = cast("Frame", from_channel(self._initializer["frame"]))
        if not frame._page:
            raise Error(
                "\n".join(
                    [
                        "Frame for this navigation request is not available, because the request",
                        "was issued before the frame is created. You can check whether the request",
                        "is a navigation request by calling isNavigationRequest() method.",
                    ]
                )
            )
        return frame

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

    def _set_response_end_timing(self, response_end_timing: float) -> None:
        self._timing["responseEnd"] = response_end_timing
        if self._timing["responseStart"] == -1:
            self._timing["responseStart"] = response_end_timing

    @property
    def headers(self) -> Headers:
        override = self._fallback_overrides.headers
        if override:
            return RawHeaders._from_headers_dict_lossy(override).headers()
        return self._provisional_headers.headers()

    async def all_headers(self) -> Headers:
        return (await self._actual_headers()).headers()

    async def headers_array(self) -> HeadersArray:
        return (await self._actual_headers()).headers_array()

    async def header_value(self, name: str) -> Optional[str]:
        return (await self._actual_headers()).get(name)

    async def _actual_headers(self) -> "RawHeaders":
        override = self._fallback_overrides.headers
        if override:
            return RawHeaders(serialize_headers(override))
        if not self._all_headers_future:
            self._all_headers_future = asyncio.Future()
            headers = await self._channel.send("rawRequestHeaders")
            self._all_headers_future.set_result(RawHeaders(headers))
        return await self._all_headers_future

    def _target_closed_future(self) -> asyncio.Future:
        frame = cast(
            Optional["Frame"], from_nullable_channel(self._initializer.get("frame"))
        )
        if not frame:
            return asyncio.Future()
        page = frame._page
        if not page:
            return asyncio.Future()
        return page._closed_or_crashed_future


class Route(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._handling_future: Optional[asyncio.Future["bool"]] = None
        self._context: "BrowserContext" = cast("BrowserContext", None)

    def _start_handling(self) -> "asyncio.Future[bool]":
        self._handling_future = asyncio.Future()
        return self._handling_future

    def _report_handled(self, done: bool) -> None:
        chain = self._handling_future
        assert chain
        self._handling_future = None
        chain.set_result(done)

    def _check_not_handled(self) -> None:
        if not self._handling_future:
            raise Error("Route is already handled!")

    def __repr__(self) -> str:
        return f"<Route request={self.request}>"

    @property
    def request(self) -> Request:
        return from_channel(self._initializer["request"])

    async def abort(self, errorCode: str = None) -> None:
        self._check_not_handled()
        await self._race_with_page_close(
            self._channel.send(
                "abort",
                filter_none(
                    {
                        "errorCode": errorCode,
                        "requestUrl": self.request._initializer["url"],
                    }
                ),
            )
        )
        self._report_handled(True)

    async def fulfill(
        self,
        status: int = None,
        headers: Dict[str, str] = None,
        body: Union[str, bytes] = None,
        json: Any = None,
        path: Union[str, Path] = None,
        contentType: str = None,
        response: "APIResponse" = None,
    ) -> None:
        self._check_not_handled()
        params = locals_to_params(locals())

        if json is not None:
            if body is not None:
                raise Error("Can specify either body or json parameters")
            body = json_utils.dumps(json)

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
        elif json:
            headers["content-type"] = "application/json"
        elif path:
            headers["content-type"] = (
                mimetypes.guess_type(str(Path(path)))[0] or "application/octet-stream"
            )
        if length and "content-length" not in headers:
            headers["content-length"] = str(length)
        params["headers"] = serialize_headers(headers)
        params["requestUrl"] = self.request._initializer["url"]

        await self._race_with_page_close(self._channel.send("fulfill", params))
        self._report_handled(True)

    async def fetch(
        self,
        url: str = None,
        method: str = None,
        headers: Dict[str, str] = None,
        postData: Union[Any, str, bytes] = None,
        maxRedirects: int = None,
        timeout: float = None,
    ) -> "APIResponse":
        return await self._connection.wrap_api_call(
            lambda: self._context.request._inner_fetch(
                self.request,
                url,
                method,
                headers,
                postData,
                maxRedirects=maxRedirects,
                timeout=timeout,
            )
        )

    async def fallback(
        self,
        url: str = None,
        method: str = None,
        headers: Dict[str, str] = None,
        postData: Union[Any, str, bytes] = None,
    ) -> None:
        overrides = cast(FallbackOverrideParameters, locals_to_params(locals()))
        self._check_not_handled()
        self.request._apply_fallback_overrides(overrides)
        self._report_handled(False)

    async def continue_(
        self,
        url: str = None,
        method: str = None,
        headers: Dict[str, str] = None,
        postData: Union[Any, str, bytes] = None,
    ) -> None:
        overrides = cast(FallbackOverrideParameters, locals_to_params(locals()))
        self._check_not_handled()
        self.request._apply_fallback_overrides(overrides)
        await self._internal_continue()
        self._report_handled(True)

    def _internal_continue(
        self, is_internal: bool = False
    ) -> Coroutine[Any, Any, None]:
        async def continue_route() -> None:
            try:
                params: Dict[str, Any] = {}
                params["url"] = self.request._fallback_overrides.url
                params["method"] = self.request._fallback_overrides.method
                params["headers"] = self.request._fallback_overrides.headers
                if self.request._fallback_overrides.post_data_buffer is not None:
                    params["postData"] = base64.b64encode(
                        self.request._fallback_overrides.post_data_buffer
                    ).decode()
                params = locals_to_params(params)

                if "headers" in params:
                    params["headers"] = serialize_headers(params["headers"])
                params["requestUrl"] = self.request._initializer["url"]
                params["isFallback"] = is_internal
                await self._connection.wrap_api_call(
                    lambda: self._race_with_page_close(
                        self._channel.send(
                            "continue",
                            params,
                        )
                    ),
                    is_internal,
                )
            except Exception as e:
                if not is_internal:
                    raise e

        return continue_route()

    async def _redirected_navigation_request(self, url: str) -> None:
        self._check_not_handled()
        await self._race_with_page_close(
            self._channel.send("redirectNavigationRequest", {"url": url})
        )
        self._report_handled(True)

    async def _race_with_page_close(self, future: Coroutine) -> None:
        fut = asyncio.create_task(future)
        # Rewrite the user's stack to the new task which runs in the background.
        setattr(
            fut,
            "__pw_stack__",
            getattr(asyncio.current_task(self._loop), "__pw_stack__", inspect.stack()),
        )
        target_closed_future = self.request._target_closed_future()
        await asyncio.wait(
            [fut, target_closed_future],
            return_when=asyncio.FIRST_COMPLETED,
        )
        if fut.done() and fut.exception():
            raise cast(BaseException, fut.exception())
        if target_closed_future.done():
            await asyncio.gather(fut, return_exceptions=True)


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

    @property
    def from_service_worker(self) -> bool:
        return self._initializer["fromServiceWorker"]

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
        async def on_finished() -> None:
            await self._request._target_closed_future()
            raise Error("Target closed")

        on_finished_task = asyncio.create_task(on_finished())
        await asyncio.wait(
            cast(
                List[Union[asyncio.Task, asyncio.Future]],
                [self._finished_future, on_finished_task],
            ),
            return_when=asyncio.FIRST_COMPLETED,
        )
        if on_finished_task.done():
            await on_finished_task

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
        self._page = cast("Page", parent)
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
        wait_helper.reject_on_event(self._page, "close", Error("Page closed"))
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


class RawHeaders:
    def __init__(self, headers: HeadersArray) -> None:
        self._headers_array = headers
        self._headers_map: Dict[str, Dict[str, bool]] = defaultdict(dict)
        for header in headers:
            self._headers_map[header["name"].lower()][header["value"]] = True

    @staticmethod
    def _from_headers_dict_lossy(headers: Dict[str, str]) -> "RawHeaders":
        return RawHeaders(serialize_headers(headers))

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
