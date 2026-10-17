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
import re
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
    Sequence,
    Tuple,
    Union,
    cast,
)
from urllib import parse

from playwright._impl._api_structures import (
    ClientCertificate,
    HttpCredentials,
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
)
from playwright._impl._errors import Error
from playwright._impl._event_context_manager import EventContextManagerImpl
from playwright._impl._headers import serialize_headers
from playwright._impl._helper import (
    URLMatch,
    WebSocketRouteHandlerCallback,
    async_readfile,
    json_stringify,
    url_matches,
)
from playwright._impl._internal_structures import Headers, HeadersArray
from playwright._impl._str_utils import escape_regex_flags
from playwright._impl._url_match import resolve_glob_to_regex_pattern
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


class SerializedFallbackOverrides:
    def __init__(self) -> None:
        self.url: Optional[str] = None
        self.method: Optional[str] = None
        self.headers: Optional[Dict[str, str]] = None
        self.post_data_buffer: Optional[bytes] = None


async def to_client_certificates_protocol(
    clientCertificates: Optional[List[ClientCertificate]],
) -> Optional[List[Dict[str, str]]]:
    if not clientCertificates:
        return None
    out = []
    for clientCertificate in clientCertificates:
        out_record = {
            "origin": clientCertificate["origin"],
        }
        if passphrase := clientCertificate.get("passphrase"):
            out_record["passphrase"] = passphrase
        if pfx := clientCertificate.get("pfx"):
            out_record["pfx"] = base64.b64encode(pfx).decode()
        if pfx_path := clientCertificate.get("pfxPath"):
            out_record["pfx"] = base64.b64encode(
                await async_readfile(pfx_path)
            ).decode()
        if cert := clientCertificate.get("cert"):
            out_record["cert"] = base64.b64encode(cert).decode()
        if cert_path := clientCertificate.get("certPath"):
            out_record["cert"] = base64.b64encode(
                await async_readfile(cert_path)
            ).decode()
        if key := clientCertificate.get("key"):
            out_record["key"] = base64.b64encode(key).decode()
        if key_path := clientCertificate.get("keyPath"):
            out_record["key"] = base64.b64encode(
                await async_readfile(key_path)
            ).decode()
        out.append(out_record)
    return out


def to_http_credentials_protocol(
    httpCredentials: Optional[Union[HttpCredentials, Sequence[HttpCredentials]]],
) -> Optional[List[HttpCredentials]]:
    if not httpCredentials:
        return None
    credentials_list = (
        [httpCredentials] if isinstance(httpCredentials, dict) else httpCredentials
    )
    return [
        cast(HttpCredentials, {k: v for k, v in c.items() if v is not None})
        for c in credentials_list
    ] or None


# Upstream: validateHeaders() in client/network.ts.
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
        self._all_headers_future: Optional[asyncio.Future[RawHeaders]] = None
        self._fallback_overrides: SerializedFallbackOverrides = (
            SerializedFallbackOverrides()
        )
        self._response: Optional["Response"] = None

    def __repr__(self) -> str:
        return f"<Request url={self.url!r} method={self.method!r}>"

    def _apply_fallback_overrides(
        self,
        url: Optional[str],
        method: Optional[str],
        headers: Optional[Dict[str, str]],
        post_data: Optional[Union[Any, str, bytes]],
    ) -> None:
        if url is not None:
            self._fallback_overrides.url = url
        if method is not None:
            self._fallback_overrides.method = method
        if headers is not None:
            # A None value removes the header.
            self._fallback_overrides.headers = {
                name: value for name, value in headers.items() if value is not None
            }
        if isinstance(post_data, str):
            self._fallback_overrides.post_data_buffer = post_data.encode()
        elif isinstance(post_data, bytes):
            self._fallback_overrides.post_data_buffer = post_data
        elif post_data is not None:
            self._fallback_overrides.post_data_buffer = json_stringify(
                post_data
            ).encode()

    @property
    def url(self) -> str:
        return cast(str, self._fallback_overrides.url or self._initializer["url"])

    @property
    def resource_type(self) -> str:
        return self._initializer["resourceType"]

    @property
    def service_worker(self) -> Optional["Worker"]:
        return cast(
            Optional["Worker"],
            from_nullable_channel(self._initializer.get("serviceWorker")),
        )

    @property
    def method(self) -> str:
        return cast(str, self._fallback_overrides.method or self._initializer["method"])

    async def sizes(self) -> RequestSizes:
        response = await self.response()
        if not response:
            raise Error("Unable to fetch sizes for failed request")
        return (await response._channel.sizes())["sizes"]

    @property
    def post_data(self) -> Optional[str]:
        data = self._fallback_overrides.post_data_buffer
        if data is not None:
            return data.decode()
        base64_post_data = self._initializer.get("postData")
        if base64_post_data is not None:
            return base64.b64decode(base64_post_data).decode()
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
    def post_data_buffer(self) -> Optional[bytes]:
        if self._fallback_overrides.post_data_buffer:
            return self._fallback_overrides.post_data_buffer
        if self._initializer.get("postData"):
            return base64.b64decode(self._initializer["postData"])
        return None

    async def response(self) -> Optional["Response"]:
        return from_nullable_channel((await self._channel.response())["response"])

    @property
    def existing_response(self) -> Optional["Response"]:
        return self._response

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
            result = await self._connection.wrap_api_call(
                lambda: self._channel.rawRequestHeaders(), is_internal=True
            )
            self._all_headers_future.set_result(RawHeaders(result["headers"]))
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

    def _safe_page(self) -> "Optional[Page]":
        frame = from_nullable_channel(self._initializer.get("frame"))
        if not frame:
            return None
        return cast("Frame", frame)._page


class Route(ChannelOwner):
    _channel: "RouteChannel"

    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._handling_future: Optional[asyncio.Future["bool"]] = None
        self._context: "BrowserContext" = cast("BrowserContext", None)
        self._did_throw = False

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

    async def abort(self, error_code: Optional[str]) -> None:
        await self._handle_route(
            lambda: self._race_with_page_close(
                self._channel.abort(errorCode=error_code)
            )
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
        if json is not None:
            if body is not None:
                raise Error("Can specify either body or json parameters")
            body = json_stringify(json)

        if headers is not None:
            # A None value removes the header.
            headers = {k: v for k, v in headers.items() if v is not None}

        fetch_response_uid: Optional[str] = None
        if response:
            status = status if status else response.status
            headers = headers if headers else response.headers
            from playwright._impl._fetch import APIResponse

            if body is None and path is None and isinstance(response, APIResponse):
                if response._request._connection is self._connection:
                    fetch_response_uid = response._fetch_uid
                else:
                    body = await response.body()

        length = 0
        encoded_body: Optional[str] = None
        is_base64: Optional[bool] = None
        if isinstance(body, str):
            encoded_body = body
            is_base64 = False
            length = len(body.encode())
        elif isinstance(body, bytes):
            encoded_body = base64.b64encode(body).decode()
            is_base64 = True
            length = len(body)
        elif body is not None:
            raise Error(f"body must be a str or bytes, got {type(body).__name__}")
        elif path:
            file_content = Path(path).read_bytes()
            encoded_body = base64.b64encode(file_content).decode()
            is_base64 = True
            length = len(file_content)

        headers = {k.lower(): str(v) for k, v in (headers or {}).items()}
        if content_type:
            headers["content-type"] = content_type
        elif json or isinstance(json, (list, tuple, dict)):
            # Like the JS client, which checks truthiness: [] and {} are truthy in JS.
            headers["content-type"] = "application/json"
        elif path:
            headers["content-type"] = (
                mimetypes.guess_type(str(Path(path)))[0] or "application/octet-stream"
            )
        if length and "content-length" not in headers:
            headers["content-length"] = str(length)

        await self._race_with_page_close(
            self._channel.fulfill(
                status=status,
                headers=serialize_headers(headers),
                body=encoded_body,
                isBase64=is_base64,
                fetchResponseUid=fetch_response_uid,
            )
        )

    async def _handle_route(self, callback: Callable) -> None:
        self._check_not_handled()
        try:
            await callback()
            self._report_handled(True)
        except Exception as e:
            self._did_throw = True
            raise e

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
        return await self._connection.wrap_api_call(
            lambda: self._context.request._inner_fetch(
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
        )

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

        return await self._handle_route(_inner)

    async def _inner_continue(self, is_fallback: bool = False) -> None:
        options = self.request._fallback_overrides
        await self._race_with_page_close(
            self._channel.continue_(
                url=options.url,
                method=options.method,
                headers=(
                    serialize_headers(options.headers) if options.headers else None
                ),
                postData=(
                    base64.b64encode(options.post_data_buffer).decode()
                    if options.post_data_buffer is not None
                    else None
                ),
                isFallback=is_fallback,
            )
        )

    async def _redirected_navigation_request(self, url: str) -> None:
        await self._handle_route(
            lambda: self._race_with_page_close(
                self._channel.redirectNavigationRequest(url=url)
            )
        )

    async def _race_with_page_close(self, future: Coroutine) -> None:
        fut = asyncio.create_task(future)
        # Rewrite the user's stack to the new task which runs in the background.
        setattr(
            fut,
            "__pw_stack__",
            getattr(asyncio.current_task(self._loop), "__pw_stack__", None)
            or _capture_stack_trace(),
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


class ServerWebSocketRoute:
    def __init__(self, ws: "WebSocketRoute"):
        self._ws = ws

    def on_message(self, handler: Callable[[Union[str, bytes]], Any]) -> None:
        self._ws._on_server_message = handler

    def on_close(self, handler: Callable[[Optional[int], Optional[str]], Any]) -> None:
        self._ws._on_server_close = handler

    def connect_to_server(self) -> None:
        raise NotImplementedError(
            "connectToServer must be called on the page-side WebSocketRoute"
        )

    @property
    def url(self) -> str:
        return self._ws._initializer["url"]

    @property
    def protocols(self) -> List[str]:
        return list(self._ws._initializer.get("protocols", []))

    def close(self, code: Optional[int], reason: Optional[str]) -> None:
        self._ws._send_no_reply(
            "closeServer", {"code": code, "reason": reason, "wasClean": True}
        )

    def send(self, message: Union[str, bytes]) -> None:
        text, is_base64 = _encode_web_socket_message(message)
        self._ws._send_no_reply(
            "sendToServer", {"message": text, "isBase64": is_base64}
        )


def _encode_web_socket_message(message: Union[str, bytes]) -> Tuple[str, bool]:
    if isinstance(message, str):
        return message, False
    return base64.b64encode(message).decode(), True


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
        return list(self._initializer.get("protocols", []))

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
        text, is_base64 = _encode_web_socket_message(message)
        self._send_no_reply("sendToPage", {"message": text, "isBase64": is_base64})

    def on_message(self, handler: Callable[[Union[str, bytes]], Any]) -> None:
        self._on_page_message = handler

    def on_close(self, handler: Callable[[Optional[int], Optional[str]], Any]) -> None:
        self._on_page_close = handler

    async def _after_handle(self) -> None:
        if self._connected:
            return
        # Ensure that websocket is "open" and can send messages without an actual server connection.
        try:
            await self._channel.ensureOpened()
        except Exception:
            pass


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
        all_urls = False
        for handler in handlers:
            if isinstance(handler.url, str):
                patterns.append({"glob": handler.url})
            elif isinstance(handler.url, re.Pattern):
                patterns.append(
                    {
                        "regexSource": handler.url.pattern,
                        "regexFlags": escape_regex_flags(handler.url),
                    }
                )
            else:
                all_urls = True

        if all_urls:
            return [{"glob": "**/*"}]
        return patterns

    def matches(self, ws_url: str) -> bool:
        return url_matches(self._base_url, ws_url, self.url, True)

    async def handle(self, websocket_route: "WebSocketRoute") -> None:
        coro_or_future = self.handler(websocket_route)
        if asyncio.iscoroutine(coro_or_future):
            await coro_or_future
        await websocket_route._after_handle()


class Response(ChannelOwner):
    _channel: "ResponseChannel"

    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._request: Request = from_channel(self._initializer["request"])
        self._request._response = self
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
            headers = (await self._channel.rawResponseHeaders())["headers"]
            self._raw_headers_future.set_result(RawHeaders(headers))
        return await self._raw_headers_future

    async def server_addr(self) -> Optional[RemoteAddr]:
        return (await self._channel.serverAddr())["value"]

    async def security_details(self) -> Optional[SecurityDetails]:
        return cast(
            Optional[SecurityDetails], (await self._channel.securityDetails())["value"]
        )

    async def http_version(self) -> str:
        return (await self._channel.httpVersion())["value"]

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
        return base64.b64decode((await self._channel.body())["binary"])

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
    _channel: "WebSocketChannel"

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

    @property
    def url(self) -> str:
        return self._initializer["url"]

    # Port of waitForEvent() in network.ts.
    @api_call
    def expect_event(
        self,
        event: str,
        predicate: Optional[Callable],
        timeout: Optional[float],
    ) -> EventContextManagerImpl:
        if timeout is None:
            timeout = cast(Any, self._parent)._timeout_settings.timeout()
        waiter = Waiter(self, event)
        waiter.reject_on_timeout(
            cast(float, timeout),
            f'Timeout {timeout}ms exceeded while waiting for event "{event}"',
        )
        if event != WebSocket.Events.Close:
            waiter.reject_on_event(self, WebSocket.Events.Close, Error("Socket closed"))
        if event != WebSocket.Events.Error:
            waiter.reject_on_event(self, WebSocket.Events.Error, Error("Socket error"))
        waiter.reject_on_event(
            self._page, "close", lambda: self._page._close_error_with_reason()
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


# Upstream: RawHeaders in client/network.ts.
class RawHeaders:
    def __init__(self, headers: HeadersArray) -> None:
        self._headers_array = headers
        # A multimap: a header can repeat, with the same value too.
        self._headers_map: Dict[str, List[str]] = {}
        for header in headers:
            self._headers_map.setdefault(header["name"].lower(), []).append(
                header["value"]
            )

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
        return list(self._headers_map.get(name.lower(), []))

    def headers(self) -> Dict[str, str]:
        result = {}
        for name in self._headers_map.keys():
            result[name] = cast(str, self.get(name))
        return result

    def headers_array(self) -> HeadersArray:
        return self._headers_array
