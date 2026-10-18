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

"""Port of packages/playwright-core/src/client/network.ts."""

import asyncio
import base64
import inspect
import json
import math
from pathlib import Path
from types import SimpleNamespace
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Coroutine,
    Dict,
    List,
    Literal,
    Optional,
    Pattern,
    Set,
    TypedDict,
    Union,
    cast,
)
from urllib import parse

from playwright._impl._api_structures import (
    RemoteAddr,
    RequestSizes,
    ResourceTiming,
    SecurityDetails,
)
from playwright._impl._connection import (
    ChannelOwner,
    _capture_stack_trace,
    api_call,
    from_channel,
    from_nullable_channel,
    internal,
)
from playwright._impl._errors import (
    Error,
    is_target_closed_error,
    rewrite_error_message,
)
from playwright._impl._event_context_manager import EventContextManagerImpl
from playwright._impl._greenlets import RouteGreenlet
from playwright._impl._headers import headers_object_to_array
from playwright._impl._helper import (
    async_readfile,
    json_stringify,
)
from playwright._impl._internal_structures import Headers, HeadersArray
from playwright._impl._mime_type import get_mime_type_for_path
from playwright._impl._str_utils import escape_regex_flags, js_string
from playwright._impl._url_match import (
    URLMatch,
    resolve_glob_to_regex_pattern,
    serialize_url_match,
    url_matches,
)
from playwright._impl._waiter import Waiter

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl import _protocol_types as channels
    from playwright._impl._browser_context import BrowserContext
    from playwright._impl._fetch import APIResponse
    from playwright._impl._frame import Frame
    from playwright._impl._page import Page, Worker
    from playwright._impl._protocol_channels import (
        RequestChannel,
        ResponseChannel,
        RouteChannel,
        WebSocketChannel,
        WebSocketRouteChannel,
    )


class ClearCookiesParams(TypedDict):
    name: Optional[str]
    nameRegexSource: Optional[str]
    nameRegexFlags: Optional[str]
    domain: Optional[str]
    domainRegexSource: Optional[str]
    domainRegexFlags: Optional[str]
    path: Optional[str]
    pathRegexSource: Optional[str]
    pathRegexFlags: Optional[str]


def to_clear_cookies_params(
    name: Optional[Union[str, Pattern[str]]],
    domain: Optional[Union[str, Pattern[str]]],
    path: Optional[Union[str, Pattern[str]]],
) -> ClearCookiesParams:
    return {
        "name": name if isinstance(name, str) else None,
        "nameRegexSource": name.pattern if isinstance(name, Pattern) else None,
        "nameRegexFlags": (
            escape_regex_flags(name) if isinstance(name, Pattern) else None
        ),
        "domain": domain if isinstance(domain, str) else None,
        "domainRegexSource": domain.pattern if isinstance(domain, Pattern) else None,
        "domainRegexFlags": (
            escape_regex_flags(domain) if isinstance(domain, Pattern) else None
        ),
        "path": path if isinstance(path, str) else None,
        "pathRegexSource": path.pattern if isinstance(path, Pattern) else None,
        "pathRegexFlags": (
            escape_regex_flags(path) if isinstance(path, Pattern) else None
        ),
    }


class SerializedFallbackOverrides:
    def __init__(self) -> None:
        self.url: Optional[str] = None
        self.method: Optional[str] = None
        self.headers: Optional[Dict[str, str]] = None
        self.post_data_buffer: Optional[bytes] = None


class Request(ChannelOwner):
    _channel: "RequestChannel"

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
        self._actual_headers_future: Optional[asyncio.Future[RawHeaders]] = None
        self._fallback_overrides: SerializedFallbackOverrides = (
            SerializedFallbackOverrides()
        )
        self._response: Optional["Response"] = None

    def __repr__(self) -> str:
        return f"<Request url={self.url!r} method={self.method!r}>"

    @property
    def url(self) -> str:
        return cast(str, self._fallback_overrides.url or self._initializer["url"])

    @property
    def resource_type(self) -> str:
        return self._initializer["resourceType"]

    @property
    def method(self) -> str:
        return cast(str, self._fallback_overrides.method or self._initializer["method"])

    @property
    def post_data(self) -> Optional[str]:
        data = self.post_data_buffer
        if data is None:
            return None
        return data.decode("utf-8", errors="replace")

    @property
    def post_data_buffer(self) -> Optional[bytes]:
        if self._fallback_overrides.post_data_buffer is not None:
            return self._fallback_overrides.post_data_buffer
        post_data = self._initializer.get("postData")
        if post_data is not None:
            return base64.b64decode(post_data)
        return None

    @property
    def post_data_json(self) -> Optional[Any]:
        post_data = self.post_data
        if not post_data:
            return None
        content_type = self.headers.get("content-type")
        if content_type and "application/x-www-form-urlencoded" in content_type:
            return dict(parse.parse_qsl(post_data, keep_blank_values=True))
        try:
            return json.loads(post_data)
        except Exception:
            raise Error(f"POST data is not a valid JSON object: {post_data}")

    @property
    def headers(self) -> Headers:
        if self._fallback_overrides.headers is not None:
            return RawHeaders._from_headers_object_lossy(
                self._fallback_overrides.headers
            ).headers()
        return self._provisional_headers.headers()

    async def _actual_headers(self) -> "RawHeaders":
        if self._fallback_overrides.headers is not None:
            return RawHeaders._from_headers_object_lossy(
                self._fallback_overrides.headers
            )
        if not self._actual_headers_future:
            self._actual_headers_future = self._loop.create_future()
            try:
                result = await self._channel.rawRequestHeaders()
                self._actual_headers_future.set_result(RawHeaders(result["headers"]))
            except Exception as e:
                self._actual_headers_future.set_exception(e)
        return await self._actual_headers_future

    @internal
    async def all_headers(self) -> Headers:
        return (await self._actual_headers()).headers()

    @internal
    async def headers_array(self) -> HeadersArray:
        return (await self._actual_headers()).headers_array()

    @internal
    async def header_value(self, name: str) -> Optional[str]:
        return (await self._actual_headers()).get(name)

    async def response(self) -> Optional["Response"]:
        return from_nullable_channel((await self._channel.response())["response"])

    async def _internal_response(self) -> Optional["Response"]:
        return from_nullable_channel((await self._channel.response())["response"])

    @property
    def existing_response(self) -> Optional["Response"]:
        return self._response

    @property
    def frame(self) -> "Frame":
        if not self._initializer.get("frame"):
            assert self.service_worker
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

    def _safe_page(self) -> "Optional[Page]":
        frame = cast(
            Optional["Frame"], from_nullable_channel(self._initializer.get("frame"))
        )
        return frame._page if frame else None

    @property
    def service_worker(self) -> Optional["Worker"]:
        return cast(
            Optional["Worker"],
            from_nullable_channel(self._initializer.get("serviceWorker")),
        )

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

    async def sizes(self) -> RequestSizes:
        response = await self.response()
        if not response:
            raise Error("Unable to fetch sizes for failed request")
        return (await response._channel.sizes())["sizes"]

    def _set_response_end_timing(self, response_end_timing: float) -> None:
        self._timing["responseEnd"] = response_end_timing
        if self._timing["responseStart"] == -1:
            self._timing["responseStart"] = response_end_timing

    def _final_request(self) -> "Request":
        return self._redirected_to._final_request() if self._redirected_to else self

    def _apply_fallback_overrides(
        self,
        url: Optional[str],
        method: Optional[str],
        headers: Optional[Dict[str, str]],
        post_data: Optional[Union[Any, str, bytes]],
    ) -> None:
        if url:
            self._fallback_overrides.url = url
        if method:
            self._fallback_overrides.method = method
        if headers is not None:
            self._fallback_overrides.headers = headers
        if isinstance(post_data, str):
            self._fallback_overrides.post_data_buffer = post_data.encode()
        elif isinstance(post_data, bytes):
            self._fallback_overrides.post_data_buffer = post_data
        elif post_data or isinstance(post_data, (list, tuple, dict)):
            # Like the JS client, which checks truthiness: [] and {} are truthy in JS.
            self._fallback_overrides.post_data_buffer = json_stringify(
                post_data
            ).encode()

    def _fallback_overrides_for_continue(self) -> SerializedFallbackOverrides:
        return self._fallback_overrides

    # Upstream: _targetClosedScope(). The future resolves with the error of the close.
    def _target_closed_future(self) -> asyncio.Future:
        service_worker = self.service_worker
        if service_worker:
            return service_worker._closed_future
        page = self._safe_page()
        if page:
            return page._closed_or_crashed_future
        return self._loop.create_future()


class Route(ChannelOwner):
    _channel: "RouteChannel"

    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._handling_future: Optional[asyncio.Future["bool"]] = None
        self._context: "BrowserContext" = cast("BrowserContext", None)
        self._did_throw = False

    def __repr__(self) -> str:
        return f"<Route request={self.request}>"

    @property
    def request(self) -> Request:
        return from_channel(self._initializer["request"])

    # Upstream: this.request()._targetClosedScope().safeRace(promise).
    async def _race_with_target_close(self, coro: Coroutine) -> None:
        # When page closes or crashes, we catch any potential rejects from this Route.
        # Note that page could be missing when routing popup's initial request that
        # does not have a Page initialized just yet.
        task = asyncio.create_task(coro)
        # Rewrite the user's stack to the new task which runs in the background.
        setattr(
            task,
            "__pw_stack__",
            getattr(asyncio.current_task(self._loop), "__pw_stack__", None)
            or _capture_stack_trace(),
        )
        target_closed_future = self.request._target_closed_future()
        await asyncio.wait(
            [task, target_closed_future],
            return_when=asyncio.FIRST_COMPLETED,
        )
        if task.done():
            await task
            return
        # The target closed first: do not wait for the call, and ignore its error.
        task.add_done_callback(lambda task: task.cancelled() or task.exception())

    def _start_handling(self) -> "asyncio.Future[bool]":
        self._handling_future = self._loop.create_future()
        return self._handling_future

    async def fallback(
        self,
        url: Optional[str],
        method: Optional[str],
        headers: Optional[Dict[str, str]],
        post_data: Optional[Union[Any, str, bytes]],
    ) -> None:
        self._check_not_handled()
        self.request._apply_fallback_overrides(
            url=url, method=method, headers=headers, post_data=post_data
        )
        self._report_handled(False)

    async def abort(self, error_code: Optional[str]) -> None:
        await self._handle_route(
            lambda: self._race_with_target_close(
                self._channel.abort(errorCode=error_code)
            )
        )

    async def _redirect_navigation_request(self, url: str) -> None:
        await self._handle_route(
            lambda: self._race_with_target_close(
                self._channel.redirectNavigationRequest(url=url)
            )
        )

    @api_call
    async def fetch(
        self,
        url: Optional[str],
        method: Optional[str],
        headers: Optional[Dict[str, str]],
        post_data: Optional[Union[Any, str, bytes]],
        max_redirects: Optional[int],
        max_retries: Optional[int],
        timeout: Optional[float],
    ) -> "APIResponse":
        return await self._context.request._inner_fetch(
            request=self.request,
            url=url,
            method=method,
            headers=headers,
            data=post_data,
            params=None,
            form=None,
            multipart=None,
            timeout=timeout,
            fail_on_status_code=None,
            ignore_https_errors=None,
            max_redirects=max_redirects,
            max_retries=max_retries,
        )

    async def fulfill(
        self,
        status: Optional[int],
        headers: Optional[Dict[str, str]],
        body: Optional[Union[str, bytes]],
        json: Optional[Any],
        path: Optional[Union[str, Path]],
        content_type: Optional[str],
        response: Optional["APIResponse"],
    ) -> None:
        await self._handle_route(
            lambda: self._inner_fulfill(
                status=status,
                headers=headers,
                body=body,
                json=json,
                path=path,
                content_type=content_type,
                response=response,
            )
        )

    async def _handle_route(self, callback: Callable[[], Coroutine]) -> None:
        self._check_not_handled()
        try:
            await callback()
            self._report_handled(True)
        except Exception as e:
            self._did_throw = True
            raise e

    async def _inner_fulfill(
        self,
        status: Optional[int],
        headers: Optional[Dict[str, str]],
        body: Optional[Union[str, bytes]],
        json: Optional[Any],
        path: Optional[Union[str, Path]],
        content_type: Optional[str],
        response: Optional["APIResponse"],
    ) -> None:
        from playwright._impl._fetch import APIResponse

        fetch_response_uid: Optional[str] = None

        if json is not None:
            if body is not None:
                raise Error("Can specify either body or json parameters")
            body = json_stringify(json)

        if isinstance(response, APIResponse):
            if status is None:
                status = response.status
            if headers is None:
                headers = response.headers
            if body is None and path is None:
                if response._request._connection is self._connection:
                    fetch_response_uid = response._fetch_uid
                else:
                    body = await response.body()

        is_base64 = False
        length = 0
        encoded_body: Optional[str] = None
        if path:
            buffer = await async_readfile(path)
            encoded_body = base64.b64encode(buffer).decode()
            is_base64 = True
            length = len(buffer)
        elif isinstance(body, str):
            encoded_body = body
            is_base64 = False
            length = len(body.encode())
        elif body:
            length = len(body)
            encoded_body = base64.b64encode(body).decode()
            is_base64 = True

        protocol_headers: Headers = {
            name.lower(): js_string(value) for name, value in (headers or {}).items()
        }
        if content_type:
            protocol_headers["content-type"] = str(content_type)
        elif json or isinstance(json, (list, tuple, dict)):
            # Like the JS client, which checks truthiness: [] and {} are truthy in JS.
            protocol_headers["content-type"] = "application/json"
        elif path:
            protocol_headers["content-type"] = (
                get_mime_type_for_path(str(path)) or "application/octet-stream"
            )
        if length and "content-length" not in protocol_headers:
            protocol_headers["content-length"] = str(length)

        await self._race_with_target_close(
            self._channel.fulfill(
                status=status or 200,
                headers=headers_object_to_array(protocol_headers),
                body=encoded_body,
                isBase64=is_base64,
                fetchResponseUid=fetch_response_uid,
            )
        )

    async def continue_(
        self,
        url: Optional[str],
        method: Optional[str],
        headers: Optional[Dict[str, str]],
        post_data: Optional[Union[Any, str, bytes]],
    ) -> None:
        async def _inner() -> None:
            self.request._apply_fallback_overrides(
                url=url, method=method, headers=headers, post_data=post_data
            )
            await self._inner_continue(False)

        await self._handle_route(_inner)

    def _check_not_handled(self) -> None:
        if not self._handling_future:
            raise Error("Route is already handled!")

    def _report_handled(self, done: bool) -> None:
        chain = self._handling_future
        assert chain
        self._handling_future = None
        chain.set_result(done)

    async def _inner_continue(self, is_fallback: bool) -> None:
        options = self.request._fallback_overrides_for_continue()
        await self._race_with_target_close(
            self._channel.continue_(
                url=options.url,
                method=options.method,
                headers=(
                    headers_object_to_array(options.headers)
                    if options.headers is not None
                    else None
                ),
                postData=(
                    base64.b64encode(options.post_data_buffer).decode()
                    if options.post_data_buffer is not None
                    else None
                ),
                isFallback=is_fallback,
            )
        )


# Upstream: the `_server` object that WebSocketRoute.connectToServer() returns.
class ServerWebSocketRoute:
    # Port of WebSocketRoute._server in client/network.ts: the server side of the
    # route, with the API of a WebSocketRoute.
    def __init__(self, ws: "WebSocketRoute"):
        self._ws = ws
        self._loop = ws._loop
        self._dispatcher_fiber = ws._dispatcher_fiber

    @property
    def _api_impl_class(self) -> type:
        return WebSocketRoute

    def on_message(self, handler: Callable[[Union[str, bytes]], Any]) -> None:
        self._ws._on_server_message = handler

    def on_close(self, handler: Callable[[Optional[int], Optional[str]], Any]) -> None:
        self._ws._on_server_close = handler

    def connect_to_server(self) -> None:
        raise Error("connectToServer must be called on the page-side WebSocketRoute")

    @property
    def url(self) -> str:
        return self._ws._initializer["url"]

    @property
    def protocols(self) -> List[str]:
        return list(self._ws._initializer["protocols"])

    async def close(self, code: Optional[int], reason: Optional[str]) -> None:
        try:
            await self._ws._channel.closeServer(code=code, reason=reason, wasClean=True)
        except Exception:
            pass

    def send(self, message: Union[str, bytes]) -> None:
        if isinstance(message, str):
            self._ws._send_no_reply(
                "sendToServer", {"message": message, "isBase64": False}
            )
        else:
            self._ws._send_no_reply(
                "sendToServer",
                {"message": base64.b64encode(message).decode(), "isBase64": True},
            )


class WebSocketRoute(ChannelOwner):
    _channel: "WebSocketRouteChannel"

    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._on_page_message: Optional[Callable[[Union[str, bytes]], Any]] = None
        self._on_page_close: Optional[Callable[[Optional[int], Optional[str]], Any]] = (
            None
        )
        self._on_server_message: Optional[Callable[[Union[str, bytes]], Any]] = None
        self._on_server_close: Optional[
            Callable[[Optional[int], Optional[str]], Any]
        ] = None
        self._server = ServerWebSocketRoute(self)
        self._connected = False

        self._channel.onMessageFromPage(self._channel_message_from_page)
        self._channel.onMessageFromServer(self._channel_message_from_server)
        self._channel.onClosePage(self._channel_close_page)
        self._channel.onCloseServer(self._channel_close_server)

    # The handlers return the result of the user's handler: the channel's event
    # emitter runs a coroutine that an `async def` handler returns.

    def _channel_message_from_page(
        self, event: "channels.WebSocketRouteMessageFromPageEvent"
    ) -> Any:
        if self._on_page_message:
            return self._on_page_message(
                base64.b64decode(event["message"])
                if event["isBase64"]
                else event["message"]
            )
        if self._connected:
            self._send_no_reply(
                "sendToServer",
                {"message": event["message"], "isBase64": event["isBase64"]},
            )
        return None

    def _channel_message_from_server(
        self, event: "channels.WebSocketRouteMessageFromServerEvent"
    ) -> Any:
        if self._on_server_message:
            return self._on_server_message(
                base64.b64decode(event["message"])
                if event["isBase64"]
                else event["message"]
            )
        self._send_no_reply(
            "sendToPage", {"message": event["message"], "isBase64": event["isBase64"]}
        )
        return None

    def _channel_close_page(
        self, event: "channels.WebSocketRouteClosePageEvent"
    ) -> Any:
        if self._on_page_close:
            return self._on_page_close(event["code"], event["reason"])
        self._send_no_reply(
            "closeServer",
            {
                "code": event["code"],
                "reason": event["reason"],
                "wasClean": event["wasClean"],
            },
        )
        return None

    def _channel_close_server(
        self, event: "channels.WebSocketRouteCloseServerEvent"
    ) -> Any:
        if self._on_server_close:
            return self._on_server_close(event["code"], event["reason"])
        self._send_no_reply(
            "closePage",
            {
                "code": event["code"],
                "reason": event["reason"],
                "wasClean": event["wasClean"],
            },
        )
        return None

    def _send_no_reply(self, method: str, params: Dict[str, Any]) -> None:
        # Upstream sends these messages right away and ignores the result:
        # `this._channel.sendToPage(...).catch(() => {})`. A task would send the
        # message on a later loop iteration, after the message of an awaited call
        # such as close() that comes after it, so the order of messages would change.
        try:
            self._channel.send_no_reply(method, params)
        except Exception:
            pass

    @property
    def url(self) -> str:
        return self._initializer["url"]

    @property
    def protocols(self) -> List[str]:
        return list(self._initializer["protocols"])

    async def close(self, code: Optional[int], reason: Optional[str]) -> None:
        try:
            await self._channel.closePage(code=code, reason=reason, wasClean=True)
        except Exception:
            pass

    def connect_to_server(self) -> "WebSocketRoute":
        if self._connected:
            raise Error("Already connected to the server")
        self._connected = True
        self._send_no_reply("connect", {})
        return cast("WebSocketRoute", self._server)

    def send(self, message: Union[str, bytes]) -> None:
        if isinstance(message, str):
            self._send_no_reply("sendToPage", {"message": message, "isBase64": False})
        else:
            self._send_no_reply(
                "sendToPage",
                {"message": base64.b64encode(message).decode(), "isBase64": True},
            )

    def on_message(self, handler: Callable[[Union[str, bytes]], Any]) -> None:
        self._on_page_message = handler

    def on_close(self, handler: Callable[[Optional[int], Optional[str]], Any]) -> None:
        self._on_page_close = handler

    async def _after_handle(self) -> None:
        if self._connected:
            return
        # Ensure that websocket is "open" and can send messages without an actual server connection.
        # If this happens after the page has been closed, ignore the error.
        try:
            await self._channel.ensureOpened()
        except Exception:
            pass


RouteHandlerCallback = Union[
    Callable[["Route"], Any], Callable[["Route", "Request"], Any]
]
WebSocketRouteHandlerCallback = Callable[["WebSocketRoute"], Any]


class WebSocketRouteHandler:
    def __init__(
        self,
        base_url: Optional[str],
        url: URLMatch,
        handler: WebSocketRouteHandlerCallback,
    ):
        self._base_url = base_url
        self.url = url
        self.handler = handler
        # Eagerly validate string globs so that invalid patterns throw at the call site
        # (e.g. page.route_web_socket()) rather than silently failing later.
        if isinstance(url, str):
            resolve_glob_to_regex_pattern(base_url, url, True)

    @staticmethod
    def prepare_interception_patterns(
        handlers: List["WebSocketRouteHandler"],
    ) -> List["channels.PageSetWebSocketInterceptionPatternsParamsPatterns"]:
        patterns: List[channels.PageSetWebSocketInterceptionPatternsParamsPatterns] = []
        all = False
        for handler in handlers:
            serialized = serialize_url_match(handler.url)
            if serialized:
                patterns.append(serialized)
            else:
                all = True
        if all:
            return [{"glob": "**/*"}]
        return patterns

    def matches(self, ws_url: str) -> bool:
        return url_matches(self._base_url, ws_url, self.url, True)

    async def handle(self, web_socket_route: "WebSocketRoute") -> None:
        handler = self.handler
        if web_socket_route._dispatcher_fiber:
            # As with route handlers, a handler of the sync API may block, so it
            # runs in its own greenlet.
            handler_finished_future = web_socket_route._loop.create_future()

            def _handler() -> None:
                try:
                    handler_finished_future.set_result(handler(web_socket_route))
                except Exception as e:
                    handler_finished_future.set_exception(e)

            RouteGreenlet(_handler).switch()
            result = await handler_finished_future
        else:
            result = handler(web_socket_route)
        if inspect.isawaitable(result):
            await result
        await web_socket_route._after_handle()


class Response(ChannelOwner):
    _channel: "ResponseChannel"

    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._request: Request = from_channel(self._initializer["request"])
        self._request._response = self
        self._request._timing.update(self._initializer["timing"])
        self._provisional_headers = RawHeaders(
            cast(HeadersArray, self._initializer["headers"])
        )
        self._actual_headers_future: Optional[asyncio.Future[RawHeaders]] = None
        self._finished_future: asyncio.Future[bool] = self._loop.create_future()

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
    def from_service_worker(self) -> bool:
        return self._initializer["fromServiceWorker"]

    @property
    def headers(self) -> Headers:
        return self._provisional_headers.headers()

    async def _actual_headers(self) -> "RawHeaders":
        if not self._actual_headers_future:
            self._actual_headers_future = self._loop.create_future()
            try:
                headers = (await self._channel.rawResponseHeaders())["headers"]
                self._actual_headers_future.set_result(RawHeaders(headers))
            except Exception as e:
                self._actual_headers_future.set_exception(e)
        return await self._actual_headers_future

    async def all_headers(self) -> Headers:
        return (await self._actual_headers()).headers()

    async def headers_array(self) -> HeadersArray:
        return list((await self._actual_headers()).headers_array())

    async def header_value(self, name: str) -> Optional[str]:
        return (await self._actual_headers()).get(name)

    async def header_values(self, name: str) -> List[str]:
        return (await self._actual_headers()).get_all(name)

    # Upstream: this.request()._targetClosedScope().race(this._finishedPromise).
    async def finished(self) -> None:
        target_closed_future = self._request._target_closed_future()
        await asyncio.wait(
            [self._finished_future, target_closed_future],
            return_when=asyncio.FIRST_COMPLETED,
        )
        if not self._finished_future.done():
            raise target_closed_future.result()

    async def body(self) -> bytes:
        return base64.b64decode((await self._channel.body())["binary"])

    async def text(self) -> str:
        content = await self.body()
        return content.decode("utf-8", errors="replace")

    async def json(self) -> Any:
        return json.loads(await self.text())

    @property
    def request(self) -> Request:
        return self._request

    @property
    def frame(self) -> "Frame":
        return self._request.frame

    async def server_addr(self) -> Optional[RemoteAddr]:
        return (await self._channel.serverAddr())["value"]

    async def security_details(self) -> Optional[SecurityDetails]:
        return cast(
            Optional[SecurityDetails], (await self._channel.securityDetails())["value"]
        )

    async def http_version(self) -> str:
        return (await self._channel.httpVersion())["value"]


class WebSocket(ChannelOwner):
    _channel: "WebSocketChannel"

    Events = SimpleNamespace(
        Close="close",
        Error="socketerror",
        FrameReceived="framereceived",
        FrameSent="framesent",
    )

    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._is_closed = False
        self._page = cast("Page", parent)
        self._channel.onFrameSent(
            lambda event: self._on_frame_sent(event["opcode"], event["data"])
        )
        self._channel.onFrameReceived(
            lambda event: self._on_frame_received(event["opcode"], event["data"])
        )
        self._channel.onSocketError(
            lambda event: self.emit(WebSocket.Events.Error, event["error"])
        )
        self._channel.onClose(self._on_close)

    def __repr__(self) -> str:
        return f"<WebSocket url={self.url!r}>"

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

    def _on_close(self) -> None:
        self._is_closed = True
        self.emit(WebSocket.Events.Close, self)

    @property
    def url(self) -> str:
        return self._initializer["url"]

    def is_closed(self) -> bool:
        return self._is_closed

    # Port of waitForEvent() in network.ts.
    @api_call
    def expect_event(
        self,
        event: str,
        predicate: Optional[Callable],
        timeout: Optional[float],
    ) -> EventContextManagerImpl:
        timeout = self._page._timeout_settings.timeout(timeout)
        waiter = Waiter.create_for_event(self, event)
        waiter.reject_on_timeout(
            timeout,
            f'Timeout {js_string(timeout)}ms exceeded while waiting for event "{event}"',
        )
        if event != WebSocket.Events.Error:
            waiter.reject_on_event(self, WebSocket.Events.Error, Error("Socket error"))
        if event != WebSocket.Events.Close:
            waiter.reject_on_event(self, WebSocket.Events.Close, Error("Socket closed"))
        waiter.reject_on_event(
            self._page,
            self._page.Events.Close,
            lambda: self._page._close_error_with_reason(),
        )
        waiter.wait_for_event(self, event, predicate)
        return EventContextManagerImpl(waiter.result())

    @api_call
    async def wait_for_event(
        self, event: str, predicate: Optional[Callable], timeout: Optional[float]
    ) -> Any:
        async with self.expect_event(
            event=event, predicate=predicate, timeout=timeout
        ) as event_info:
            pass
        return await event_info


# Upstream: validateHeaders(). None stands for JavaScript's null here, which the
# ported tests expect to be rejected.
def validate_headers(headers: Dict[str, str]) -> None:
    for key, value in headers.items():
        if not isinstance(value, str):
            raise Error(
                f'Expected value of header "{key}" to be String, but "{_js_typeof(value)}" is found.'
            )


def _js_typeof(value: Any) -> str:
    # The result of JavaScript's typeof for the value that the driver would get.
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if callable(value):
        return "function"
    return "object"


class RouteHandlerInvocation:
    def __init__(self, complete: "asyncio.Future[None]", route: Route) -> None:
        self.complete = complete
        self.route = route


class RouteHandler:
    def __init__(
        self,
        base_url: Optional[str],
        url: URLMatch,
        handler: RouteHandlerCallback,
        times: Optional[int],
    ) -> None:
        self._base_url = base_url
        self.url = url
        self.handler = handler
        self._times = times if times is not None else math.inf
        self._handled_count = 0
        self._ignore_exception = False
        self._active_invocations: Set[RouteHandlerInvocation] = set()
        # Eagerly validate string globs so that invalid patterns throw at the call site
        # (e.g. page.route()) rather than silently aborting requests later.
        if isinstance(url, str):
            resolve_glob_to_regex_pattern(base_url, url)

    @staticmethod
    def prepare_interception_patterns(
        handlers: List["RouteHandler"],
    ) -> List["channels.BrowserContextSetNetworkInterceptionPatternsParamsPatterns"]:
        patterns: List[
            "channels.BrowserContextSetNetworkInterceptionPatternsParamsPatterns"
        ] = []
        all = False
        for handler in handlers:
            serialized = serialize_url_match(handler.url)
            if serialized:
                patterns.append(serialized)
            else:
                all = True
        if all:
            return [{"glob": "**/*"}]
        return patterns

    def matches(self, request_url: str) -> bool:
        return url_matches(self._base_url, request_url, self.url)

    # Upstream: handle() and _handleImpl().
    async def handle(self, route: Route) -> bool:
        handler_invocation = RouteHandlerInvocation(route._loop.create_future(), route)
        self._active_invocations.add(handler_invocation)
        try:
            return await self._handle_internal(route)
        except Exception as e:
            # If the handler was stopped (without waiting for completion), we ignore all exceptions.
            if self._ignore_exception:
                return False
            if is_target_closed_error(e):
                # We are failing in the handler because the target has closed.
                # Give user a hint!
                optional_async_prefix = "" if route._dispatcher_fiber else "await "
                raise rewrite_error_message(
                    e,
                    f"\"{str(e)}\" while running route callback.\nConsider awaiting `{optional_async_prefix}page.unroute_all(behavior='ignoreErrors')`\nbefore the end of the test to ignore remaining routes in flight.",
                )
            raise e
        finally:
            handler_invocation.complete.set_result(None)
            self._active_invocations.remove(handler_invocation)

    async def stop(self, behavior: Literal["ignoreErrors", "wait"]) -> None:
        # When a handler is manually unrouted or its page/context is closed we either
        # - wait for the current handler invocations to finish
        # - or do not wait, if the user opted out of it, but swallow all exceptions
        #   that happen after the unroute/close.
        if behavior == "ignoreErrors":
            self._ignore_exception = True
        else:
            tasks = []
            for activation in self._active_invocations:
                if not activation.route._did_throw:
                    tasks.append(activation.complete)
            await asyncio.gather(*tasks)

    async def _handle_internal(self, route: Route) -> bool:
        self._handled_count += 1
        handled_future = route._start_handling()
        # Extract handler into a variable to avoid [RouteHandler.handler] in the stack.
        handler = cast(Callable[..., Any], self.handler)
        if route._dispatcher_fiber:
            handler_finished_future = route._loop.create_future()

            def _handler() -> None:
                try:
                    handler_finished_future.set_result(handler(route, route.request))
                except Exception as e:
                    handler_finished_future.set_exception(e)

            # As with event handlers, each route handler is a potentially blocking context
            # so it needs a fiber.
            g = RouteGreenlet(_handler)
            g.switch()
            result = await handler_finished_future
        else:
            result = handler(route, route.request)
        # Upstream awaits the result of the handler together with the handled promise.
        if inspect.isawaitable(result):
            # separate task so that we get a proper stack trace for exceptions / tracing api_name extraction
            await asyncio.ensure_future(result)
        return await handled_future

    def will_expire(self) -> bool:
        return self._handled_count + 1 >= self._times


# Upstream: RawHeaders in client/network.ts.
class RawHeaders:

    @staticmethod
    def _from_headers_object_lossy(headers: Dict[str, str]) -> "RawHeaders":
        headers_array: HeadersArray = [
            {"name": name, "value": value}
            for name, value in headers.items()
            if value is not None
        ]
        return RawHeaders(headers_array)

    def __init__(self, headers: HeadersArray) -> None:
        self._headers_array = headers
        # A multimap: a header can repeat, with the same value too.
        self._headers_map: Dict[str, List[str]] = {}
        for header in headers:
            self._headers_map.setdefault(header["name"].lower(), []).append(
                header["value"]
            )

    def get(self, name: str) -> Optional[str]:
        values = self.get_all(name)
        if not values:
            return None
        separator = "\n" if name.lower() == "set-cookie" else ", "
        return separator.join(values)

    def get_all(self, name: str) -> List[str]:
        return list(self._headers_map.get(name.lower(), []))

    def headers(self) -> Dict[str, str]:
        result = {}
        for name in self._headers_map.keys():
            result[name] = cast(str, self.get(name))
        return result

    def headers_array(self) -> HeadersArray:
        return self._headers_array
