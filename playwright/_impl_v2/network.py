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

"""Port of packages/playwright-core/src/client/network.ts.

Python: binary values (post data, bodies, WebSocket messages) are base64 strings on
the wire; this module encodes and decodes them where upstream has a Buffer. An empty
bytes value is falsy in Python and an empty Buffer is truthy in JS, and so is an
empty dict, so the checks for "is there a value" are `is not None` checks. The
options objects are separate parameters. The Python API returns the error text from
Request.failure, and the WebSocket frame events carry the payload itself. A route
handler may be an async def: its result is awaited.
"""

import asyncio
import base64
import inspect
import json
import re
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Set,
    TypedDict,
    Union,
    cast,
)
from urllib import parse

from playwright._impl._api_structures import (
    Cookie,
    RemoteAddr,
    RequestSizes,
    ResourceTiming,
    SecurityDetails,
    SetCookieParam,
)
from playwright._impl._errors import Error
from playwright._impl_v2.channel_owner import (
    ChannelOwner,
    api_call,
    from_channel,
    internal,
)
from playwright._impl_v2.errors import is_target_closed_error
from playwright._impl_v2.event_context_manager import EventContextManagerImpl
from playwright._impl_v2.events import Events
from playwright._impl_v2.internal_structures import Headers, HeadersArray
from playwright._impl_v2.isomorphic.headers import headers_object_to_array
from playwright._impl_v2.isomorphic.manual_promise import (
    LongStandingScope,
    ManualPromise,
)
from playwright._impl_v2.isomorphic.mime_type import get_mime_type_for_path
from playwright._impl_v2.isomorphic.string_utils import escape_regex_flags, js_string
from playwright._impl_v2.isomorphic.url_match import (
    URLMatch,
    resolve_glob_to_regex_pattern,
    serialize_url_match,
    url_matches,
)
from playwright._impl_v2.timeout_settings import NO_TIMEOUT
from playwright._impl_v2.utils.promise import all_, catch, resolved, start, then
from playwright._impl_v2.utils.stack_trace import rewrite_error_message
from playwright._impl_v2.utils.zones import Zone, current_zone
from playwright._impl_v2.waiter import Waiter

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl_v2 import protocol_types as channels
    from playwright._impl_v2.browser_context import BrowserContext
    from playwright._impl_v2.fetch import APIResponse
    from playwright._impl_v2.frame import Frame
    from playwright._impl_v2.page import Page
    from playwright._impl_v2.protocol_channels import (
        RequestChannel,
        ResponseChannel,
        RouteChannel,
        WebSocketChannel,
        WebSocketRouteChannel,
    )
    from playwright._impl_v2.worker import Worker

# Python: the cookie types are the TypedDicts of the API.
NetworkCookie = Cookie

SetNetworkCookieParam = SetCookieParam

# Python: ClearNetworkCookieOptions is the name, domain and path parameters of
# to_clear_cookies_params().


# Python: channels.BrowserContextClearCookiesParams; _protocol_types.py has no types
# for the parameters of the commands.
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
    name: Optional[Union[str, "re.Pattern[str]"]],
    domain: Optional[Union[str, "re.Pattern[str]"]],
    path: Optional[Union[str, "re.Pattern[str]"]],
) -> ClearCookiesParams:
    # Python: escape_regex_flags() is the `flags` of a RegExp.
    return {
        "name": name if isinstance(name, str) else None,
        "nameRegexSource": name.pattern if isinstance(name, re.Pattern) else None,
        "nameRegexFlags": (
            escape_regex_flags(name) if isinstance(name, re.Pattern) else None
        ),
        "domain": domain if isinstance(domain, str) else None,
        "domainRegexSource": (
            domain.pattern if isinstance(domain, re.Pattern) else None
        ),
        "domainRegexFlags": (
            escape_regex_flags(domain) if isinstance(domain, re.Pattern) else None
        ),
        "path": path if isinstance(path, str) else None,
        "pathRegexSource": path.pattern if isinstance(path, re.Pattern) else None,
        "pathRegexFlags": (
            escape_regex_flags(path) if isinstance(path, re.Pattern) else None
        ),
    }


class SerializedFallbackOverrides:
    # Python: a class for the object type; an absent field is None.
    def __init__(self) -> None:
        self.url: Optional[str] = None
        self.method: Optional[str] = None
        self.headers: Optional[Headers] = None
        self.post_data_buffer: Optional[bytes] = None


# Python: FallbackOverrides is the url, method, headers and post_data parameters.


class Request(ChannelOwner):
    _channel: "RequestChannel"

    @staticmethod
    def from_(request: "RequestChannel") -> "Request":
        return from_channel(request)

    @staticmethod
    def from_nullable(request: Optional["RequestChannel"]) -> Optional["Request"]:
        return Request.from_(request) if request else None

    def __init__(
        self,
        parent: ChannelOwner,
        type: str,
        guid: str,
        initializer: "channels.RequestInitializer",
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._redirected_from: Optional[Request] = None
        self._redirected_to: Optional[Request] = None
        self._failure_text: Optional[str] = None
        self._response: Optional[Response] = None
        self._provisional_headers: RawHeaders
        self._actual_headers_promise: Optional["asyncio.Future[RawHeaders]"] = None
        self._timing: ResourceTiming
        self._fallback_overrides: SerializedFallbackOverrides = (
            SerializedFallbackOverrides()
        )

        self._redirected_from = Request.from_nullable(initializer.get("redirectedFrom"))
        if self._redirected_from:
            self._redirected_from._redirected_to = self
        self._provisional_headers = RawHeaders(initializer["headers"])
        self._timing = {
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

    @property
    def url(self) -> str:
        return self._fallback_overrides.url or self._initializer["url"]

    @property
    def resource_type(self) -> str:
        return self._initializer["resourceType"]

    @property
    def method(self) -> str:
        return self._fallback_overrides.method or self._initializer["method"]

    @property
    def post_data(self) -> Optional[str]:
        # Python: the post data of the initializer is base64.
        buffer = self._fallback_overrides.post_data_buffer
        if buffer is None and self._initializer.get("postData") is not None:
            buffer = base64.b64decode(self._initializer["postData"])
        return buffer.decode("utf-8", errors="replace") if buffer is not None else None

    @property
    def post_data_buffer(self) -> Optional[bytes]:
        # Python: an empty buffer is a value, as in JS.
        if self._fallback_overrides.post_data_buffer is not None:
            return self._fallback_overrides.post_data_buffer
        if self._initializer.get("postData") is not None:
            return base64.b64decode(self._initializer["postData"])
        return None

    @property
    def post_data_json(self) -> Optional[Any]:
        post_data = self.post_data
        if not post_data:
            return None

        content_type = self.headers.get("content-type")
        if content_type and "application/x-www-form-urlencoded" in content_type:
            entries: Dict[str, str] = {}
            # Python: parse_qsl() parses as URLSearchParams does.
            parsed = parse.parse_qsl(post_data, keep_blank_values=True)
            for k, v in parsed:
                entries[k] = v
            return entries

        try:
            return json.loads(post_data)
        except Exception:
            raise Error("POST data is not a valid JSON object: " + post_data)

    # @deprecated
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

        if not self._actual_headers_promise:
            self._actual_headers_promise = then(
                self._channel.rawRequestHeaders(timeout=NO_TIMEOUT),
                lambda result: RawHeaders(result["headers"]),
            )
        # Python: shield(), so that a cancelled caller does not cancel the promise
        # that the other callers share.
        return await asyncio.shield(self._actual_headers_promise)

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
        return Response.from_nullable(
            (await self._channel.response(timeout=NO_TIMEOUT))["response"]
        )

    async def _internal_response(self) -> Optional["Response"]:
        return Response.from_nullable(
            (await self._channel.response(timeout=NO_TIMEOUT))["response"]
        )

    @property
    def existing_response(self) -> Optional["Response"]:
        return self._response

    @property
    def frame(self) -> "Frame":
        # Python: imported here, to avoid an import cycle.
        from playwright._impl_v2.frame import Frame

        if not self._initializer.get("frame"):
            assert self.service_worker
            raise Error("Service Worker requests do not have an associated frame.")
        frame = Frame.from_(self._initializer["frame"])
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

    def _safe_page(self) -> Optional["Page"]:
        # Python: imported here, to avoid an import cycle.
        from playwright._impl_v2.frame import Frame

        frame = Frame.from_nullable(self._initializer.get("frame"))
        return frame._page if frame else None

    @property
    def service_worker(self) -> Optional["Worker"]:
        # Python: imported here, to avoid an import cycle.
        from playwright._impl_v2.worker import Worker

        return (
            Worker.from_(self._initializer["serviceWorker"])
            if self._initializer.get("serviceWorker")
            else None
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
        if self._failure_text is None:
            return None
        # Python: the API returns the error text, not { errorText }.
        return self._failure_text

    @property
    def timing(self) -> ResourceTiming:
        return self._timing

    async def sizes(self) -> RequestSizes:
        response = await self.response()
        if not response:
            raise Error("Unable to fetch sizes for failed request")
        return (await response._channel.sizes(timeout=NO_TIMEOUT))["sizes"]

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
        headers: Optional[Headers],
        post_data: Optional[Union[Any, str, bytes]],
    ) -> None:
        if url:
            self._fallback_overrides.url = url
        if method:
            self._fallback_overrides.method = method
        # Python: {} is truthy in JS.
        if headers is not None:
            self._fallback_overrides.headers = headers

        if isinstance(post_data, str):
            self._fallback_overrides.post_data_buffer = post_data.encode("utf-8")
        elif isinstance(post_data, bytes):
            self._fallback_overrides.post_data_buffer = post_data
        # Python: [] and {} are truthy in JS.
        elif post_data or isinstance(post_data, (list, tuple, dict)):
            self._fallback_overrides.post_data_buffer = _json_stringify(
                post_data
            ).encode("utf-8")

    def _fallback_overrides_for_continue(self) -> SerializedFallbackOverrides:
        return self._fallback_overrides

    def _target_closed_scope(self) -> LongStandingScope:
        service_worker = self.service_worker
        scope = service_worker._closed_scope if service_worker else None
        if not scope:
            page = self._safe_page()
            scope = page._closed_or_crashed_scope if page else None
        return scope or LongStandingScope()

    # Python only: the members of the Python API that upstream does not have.

    def __repr__(self) -> str:
        return f"<Request url={self.url!r} method={self.method!r}>"


class Route(ChannelOwner):
    _channel: "RouteChannel"
    # Python: set by the BrowserContext or the Page that routes the request.
    _context: "BrowserContext"

    @staticmethod
    def from_(route: "RouteChannel") -> "Route":
        return from_channel(route)

    def __init__(
        self,
        parent: ChannelOwner,
        type: str,
        guid: str,
        initializer: "channels.RouteInitializer",
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._handling_promise: Optional[ManualPromise[bool]] = None
        self._did_throw: bool = False

    @property
    def request(self) -> Request:
        return Request.from_(self._initializer["request"])

    async def _race_with_target_close(self, promise: "asyncio.Future[Any]") -> None:
        # When page closes or crashes, we catch any potential rejects from this Route.
        # Note that page could be missing when routing popup's initial request that
        # does not have a Page initialized just yet.
        return await self.request._target_closed_scope().safe_race(promise)

    def _start_handling(self) -> "ManualPromise[bool]":
        # Python: not an async def, so that the handling promise is set before the
        # handler runs, as the synchronous part of the JS async function does.
        self._handling_promise = ManualPromise()
        return self._handling_promise

    async def fallback(
        self,
        url: Optional[str],
        method: Optional[str],
        headers: Optional[Headers],
        post_data: Optional[Union[Any, str, bytes]],
    ) -> None:
        self._check_not_handled()
        self.request._apply_fallback_overrides(
            url=url, method=method, headers=headers, post_data=post_data
        )
        self._report_handled(False)

    async def abort(self, error_code: Optional[str]) -> None:
        async def callback() -> None:
            await self._race_with_target_close(
                self._channel.abort(errorCode=error_code, timeout=NO_TIMEOUT)
            )

        await self._handle_route(callback)

    async def _redirect_navigation_request(self, url: str) -> None:
        async def callback() -> None:
            await self._race_with_target_close(
                self._channel.redirectNavigationRequest(url=url, timeout=NO_TIMEOUT)
            )

        await self._handle_route(callback)

    @api_call()
    async def fetch(
        self,
        url: Optional[str],
        method: Optional[str],
        headers: Optional[Headers],
        post_data: Optional[Union[Any, str, bytes]],
        max_redirects: Optional[int],
        max_retries: Optional[int],
        timeout: Optional[float],
    ) -> "APIResponse":
        # Python: `{ request, data: options.postData, ...options }` is every parameter
        # of _inner_fetch(); the options that Route.fetch() does not have are None.
        return await self._context.request._inner_fetch(
            request=self.request,
            data=post_data,
            url=url,
            method=method,
            headers=headers,
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
        response: Optional["APIResponse"],
        status: Optional[int],
        headers: Optional[Headers],
        content_type: Optional[str],
        body: Optional[Union[str, bytes]],
        json: Optional[Any],
        path: Optional[Union[str, Path]],
    ) -> None:
        async def callback() -> None:
            await self._inner_fulfill(
                response=response,
                status=status,
                headers=headers,
                content_type=content_type,
                body=body,
                json=json,
                path=path,
            )

        await self._handle_route(callback)

    async def _handle_route(self, callback: Callable[[], Awaitable[None]]) -> None:
        self._check_not_handled()
        try:
            await callback()
            self._report_handled(True)
        except Exception as e:
            self._did_throw = True
            raise e

    async def _inner_fulfill(
        self,
        response: Optional["APIResponse"],
        status: Optional[int],
        headers: Optional[Headers],
        content_type: Optional[str],
        body: Optional[Union[str, bytes]],
        json: Optional[Any],
        path: Optional[Union[str, Path]],
    ) -> None:
        # Python: imported here, to avoid an import cycle.
        from playwright._impl_v2.fetch import APIResponse

        fetch_response_uid: Optional[str] = None
        status_option, headers_option = status, headers

        if json is not None:
            # Python: assert() with a message throws an Error with that message.
            if body is not None:
                raise Error("Can specify either body or json parameters")
            body = _json_stringify(json)

        if isinstance(response, APIResponse):
            if status_option is None:
                status_option = response.status
            if headers_option is None:
                headers_option = response.headers
            if body is None and path is None:
                if response._request._connection is self._connection:
                    fetch_response_uid = response._fetch_uid()
                else:
                    body = await response.body()

        is_base64 = False
        length = 0
        if path:
            buffer = await _read_file(path)
            body = base64.b64encode(buffer).decode()
            is_base64 = True
            length = len(buffer)
        elif isinstance(body, str):
            is_base64 = False
            length = len(body.encode("utf-8"))
        # Python: an empty buffer is a value, as in JS.
        elif body is not None:
            length = len(body)
            body = base64.b64encode(body).decode()
            is_base64 = True

        protocol_headers: Headers = {}
        for header in (headers_option or {}).keys():
            protocol_headers[header.lower()] = js_string(
                cast(Headers, headers_option)[header]
            )
        if content_type:
            protocol_headers["content-type"] = js_string(content_type)
        # Python: [] and {} are truthy in JS.
        elif json or isinstance(json, (list, tuple, dict)):
            protocol_headers["content-type"] = "application/json"
        elif path:
            protocol_headers["content-type"] = (
                get_mime_type_for_path(str(path)) or "application/octet-stream"
            )
        if length and "content-length" not in protocol_headers:
            protocol_headers["content-length"] = str(length)

        await self._race_with_target_close(
            self._channel.fulfill(
                status=status_option or 200,
                headers=headers_object_to_array(protocol_headers),
                body=body,
                isBase64=is_base64,
                fetchResponseUid=fetch_response_uid,
                timeout=NO_TIMEOUT,
            )
        )

    async def continue_(
        self,
        url: Optional[str],
        method: Optional[str],
        headers: Optional[Headers],
        post_data: Optional[Union[Any, str, bytes]],
    ) -> None:
        async def callback() -> None:
            self.request._apply_fallback_overrides(
                url=url, method=method, headers=headers, post_data=post_data
            )
            await self._inner_continue(False)  # isFallback

        await self._handle_route(callback)

    def _check_not_handled(self) -> None:
        if not self._handling_promise:
            raise Error("Route is already handled!")

    def _report_handled(self, done: bool) -> None:
        chain = cast(ManualPromise[bool], self._handling_promise)
        self._handling_promise = None
        chain.resolve(done)

    async def _inner_continue(self, is_fallback: bool) -> None:
        options = self.request._fallback_overrides_for_continue()
        return await self._race_with_target_close(
            self._channel.continue_(
                url=options.url,
                method=options.method,
                # Python: {} is truthy in JS.
                headers=(
                    headers_object_to_array(options.headers)
                    if options.headers is not None
                    else None
                ),
                # Python: binary is base64 on the wire.
                postData=(
                    base64.b64encode(options.post_data_buffer).decode()
                    if options.post_data_buffer is not None
                    else None
                ),
                isFallback=is_fallback,
                timeout=NO_TIMEOUT,
            )
        )

    # Python only: the members of the Python API that upstream does not have.

    def __repr__(self) -> str:
        return f"<Route request={self.request}>"


class WebSocketRoute(ChannelOwner):
    _channel: "WebSocketRouteChannel"

    @staticmethod
    def from_(route: "WebSocketRouteChannel") -> "WebSocketRoute":
        return from_channel(route)

    def __init__(
        self,
        parent: ChannelOwner,
        type: str,
        guid: str,
        initializer: "channels.WebSocketRouteInitializer",
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
        self._server: _WebSocketRouteServer
        self._connected = False

        self._server = _WebSocketRouteServer(self)

        # Python: each listener returns the result of the user's handler, so that the
        # event emitter of the channel runs an async def handler. A JS handler's
        # promise runs by itself.

        def on_message_from_page(
            event: "channels.WebSocketRouteMessageFromPageEvent",
        ) -> Any:
            message, is_base64 = event["message"], event["isBase64"]
            if self._on_page_message:
                return self._on_page_message(
                    base64.b64decode(message) if is_base64 else message
                )
            elif self._connected:
                catch(
                    self._channel.sendToServer(
                        message=message, isBase64=is_base64, timeout=NO_TIMEOUT
                    )
                )
            return None

        self._channel.onMessageFromPage(on_message_from_page)

        def on_message_from_server(
            event: "channels.WebSocketRouteMessageFromServerEvent",
        ) -> Any:
            message, is_base64 = event["message"], event["isBase64"]
            if self._on_server_message:
                return self._on_server_message(
                    base64.b64decode(message) if is_base64 else message
                )
            else:
                catch(
                    self._channel.sendToPage(
                        message=message, isBase64=is_base64, timeout=NO_TIMEOUT
                    )
                )
            return None

        self._channel.onMessageFromServer(on_message_from_server)

        def on_close_page(event: "channels.WebSocketRouteClosePageEvent") -> Any:
            code, reason, was_clean = event["code"], event["reason"], event["wasClean"]
            if self._on_page_close:
                return self._on_page_close(code, reason)
            else:
                catch(
                    self._channel.closeServer(
                        code=code, reason=reason, wasClean=was_clean, timeout=NO_TIMEOUT
                    )
                )
            return None

        self._channel.onClosePage(on_close_page)

        def on_close_server(event: "channels.WebSocketRouteCloseServerEvent") -> Any:
            code, reason, was_clean = event["code"], event["reason"], event["wasClean"]
            if self._on_server_close:
                return self._on_server_close(code, reason)
            else:
                catch(
                    self._channel.closePage(
                        code=code, reason=reason, wasClean=was_clean, timeout=NO_TIMEOUT
                    )
                )
            return None

        self._channel.onCloseServer(on_close_server)

    @property
    def url(self) -> str:
        return self._initializer["url"]

    @property
    def protocols(self) -> List[str]:
        return list(self._initializer["protocols"])

    async def close(self, code: Optional[int], reason: Optional[str]) -> None:
        await catch(
            self._channel.closePage(
                code=code, reason=reason, wasClean=True, timeout=NO_TIMEOUT
            )
        )

    def connect_to_server(self) -> "_WebSocketRouteServer":
        if self._connected:
            raise Error("Already connected to the server")
        self._connected = True
        catch(self._channel.connect(timeout=NO_TIMEOUT))
        return self._server

    def send(self, message: Union[str, bytes]) -> None:
        if isinstance(message, str):
            catch(
                self._channel.sendToPage(
                    message=message, isBase64=False, timeout=NO_TIMEOUT
                )
            )
        else:
            catch(
                self._channel.sendToPage(
                    message=base64.b64encode(message).decode(),
                    isBase64=True,
                    timeout=NO_TIMEOUT,
                )
            )

    def on_message(self, handler: Callable[[Union[str, bytes]], Any]) -> None:
        self._on_page_message = handler

    def on_close(self, handler: Callable[[Optional[int], Optional[str]], Any]) -> None:
        self._on_page_close = handler

    # Not ported: [Symbol.asyncDispose]() is JavaScript only.

    async def _after_handle(self) -> None:
        if self._connected:
            return
        # Ensure that websocket is "open" and can send messages without an actual server connection.
        # If this happens after the page has been closed, ignore the error.
        await catch(self._channel.ensureOpened(timeout=NO_TIMEOUT))


class _WebSocketRouteServer:
    """Python: the object literal of WebSocketRoute._server.

    It is the server side of the route, with the API of a WebSocketRoute; its
    methods are the arrow functions of the literal, on the route.
    """

    def __init__(self, route: WebSocketRoute) -> None:
        self._route = route
        # Python: the generated API reads the event loop of each object.
        self._loop = route._loop

    @property
    def _api_impl_class(self) -> type:
        # Python: the generated API wraps this object as a WebSocketRoute.
        return WebSocketRoute

    def on_message(self, handler: Callable[[Union[str, bytes]], Any]) -> None:
        self._route._on_server_message = handler

    def on_close(self, handler: Callable[[Optional[int], Optional[str]], Any]) -> None:
        self._route._on_server_close = handler

    def connect_to_server(self) -> None:
        raise Error("connectToServer must be called on the page-side WebSocketRoute")

    @property
    def url(self) -> str:
        return self._route._initializer["url"]

    @property
    def protocols(self) -> List[str]:
        return list(self._route._initializer["protocols"])

    async def close(self, code: Optional[int], reason: Optional[str]) -> None:
        await catch(
            self._route._channel.closeServer(
                code=code, reason=reason, wasClean=True, timeout=NO_TIMEOUT
            )
        )

    def send(self, message: Union[str, bytes]) -> None:
        if isinstance(message, str):
            catch(
                self._route._channel.sendToServer(
                    message=message, isBase64=False, timeout=NO_TIMEOUT
                )
            )
        else:
            catch(
                self._route._channel.sendToServer(
                    message=base64.b64encode(message).decode(),
                    isBase64=True,
                    timeout=NO_TIMEOUT,
                )
            )

    # Not ported: [Symbol.asyncDispose]() is JavaScript only.


class WebSocketRouteHandler:
    def __init__(
        self,
        base_url: Optional[str],
        url: URLMatch,
        handler: "WebSocketRouteHandlerCallback",
    ) -> None:
        self._base_url = base_url
        self.url = url
        self.handler = handler
        # Eagerly validate string globs so that invalid patterns throw at the call site
        # (e.g. page.routeWebSocket()) rather than silently failing later.
        if isinstance(url, str):
            resolve_glob_to_regex_pattern(base_url, url, True)

    @staticmethod
    def prepare_interception_patterns(
        handlers: List["WebSocketRouteHandler"],
    ) -> List["channels.BrowserContextSetWebSocketInterceptionPatternsParamsPatterns"]:
        patterns: List[
            "channels.BrowserContextSetWebSocketInterceptionPatternsParamsPatterns"
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

    def matches(self, ws_url: str) -> bool:
        return url_matches(self._base_url, ws_url, self.url, True)

    async def handle(self, web_socket_route: WebSocketRoute) -> None:
        handler = self.handler
        # Python: the handler may return an awaitable, as a JS handler returns a
        # promise.
        result = handler(web_socket_route)
        if inspect.isawaitable(result):
            await result
        await web_socket_route._after_handle()


# Python: the API calls a handler with the arguments that it takes, so a handler
# may take the route only.
RouteHandlerCallback = Callable[["Route", "Request"], Any]
WebSocketRouteHandlerCallback = Callable[["WebSocketRoute"], Any]

# Python: ResourceTiming and RequestSizes are the TypedDicts of the API.


class Response(ChannelOwner):
    _channel: "ResponseChannel"

    @staticmethod
    def from_(response: "ResponseChannel") -> "Response":
        return from_channel(response)

    @staticmethod
    def from_nullable(response: Optional["ResponseChannel"]) -> Optional["Response"]:
        return Response.from_(response) if response else None

    def __init__(
        self,
        parent: ChannelOwner,
        type: str,
        guid: str,
        initializer: "channels.ResponseInitializer",
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._provisional_headers: RawHeaders
        self._actual_headers_promise: Optional["asyncio.Future[RawHeaders]"] = None
        self._request: Request
        self._finished_promise: ManualPromise[None] = ManualPromise()

        self._provisional_headers = RawHeaders(initializer["headers"])
        self._request = Request.from_(self._initializer["request"])
        self._request._response = self
        self._request._timing.update(self._initializer["timing"])

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

    # @deprecated
    @property
    def headers(self) -> Headers:
        return self._provisional_headers.headers()

    async def _actual_headers(self) -> "RawHeaders":
        if not self._actual_headers_promise:
            # Python: the async IIFE; then() sends the message at once, as the IIFE
            # does before its first await.
            self._actual_headers_promise = then(
                self._channel.rawResponseHeaders(timeout=NO_TIMEOUT),
                lambda result: RawHeaders(result["headers"]),
            )
        # Python: shield(), so that a cancelled caller does not cancel the promise
        # that the other callers share.
        return await asyncio.shield(self._actual_headers_promise)

    async def all_headers(self) -> Headers:
        return (await self._actual_headers()).headers()

    async def headers_array(self) -> HeadersArray:
        return list((await self._actual_headers()).headers_array())

    async def header_value(self, name: str) -> Optional[str]:
        return (await self._actual_headers()).get(name)

    async def header_values(self, name: str) -> List[str]:
        return (await self._actual_headers()).get_all(name)

    async def finished(self) -> None:
        return await self.request._target_closed_scope().race(self._finished_promise)

    async def body(self) -> bytes:
        # Python: binary is base64 on the wire.
        return base64.b64decode(
            (await self._channel.body(timeout=NO_TIMEOUT))["binary"]
        )

    async def text(self) -> str:
        content = await self.body()
        return content.decode("utf-8", errors="replace")

    async def json(self) -> Any:
        content = await self.text()
        return json.loads(content)

    @property
    def request(self) -> Request:
        return self._request

    @property
    def frame(self) -> "Frame":
        return self._request.frame

    async def server_addr(self) -> Optional[RemoteAddr]:
        return (await self._channel.serverAddr(timeout=NO_TIMEOUT))["value"] or None

    async def security_details(self) -> Optional[SecurityDetails]:
        return (
            cast(
                Optional[SecurityDetails],
                (await self._channel.securityDetails(timeout=NO_TIMEOUT))["value"],
            )
            or None
        )

    async def http_version(self) -> str:
        return (await self._channel.httpVersion(timeout=NO_TIMEOUT))["value"]

    # Python only: the members of the Python API that upstream does not have.

    def __repr__(self) -> str:
        return f"<Response url={self.url!r} request={self.request}>"


class WebSocket(ChannelOwner):
    _channel: "WebSocketChannel"

    @staticmethod
    def from_(web_socket: "WebSocketChannel") -> "WebSocket":
        return from_channel(web_socket)

    def __init__(
        self,
        parent: ChannelOwner,
        type: str,
        guid: str,
        initializer: "channels.WebSocketInitializer",
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._page: "Page"
        self._is_closed: bool
        self._is_closed = False
        self._page = cast("Page", parent)

        # Python: the event is the payload, not { payload }.

        def on_frame_sent(event: "channels.WebSocketFrameSentEvent") -> None:
            if event["opcode"] == 1:
                self.emit(Events.WebSocket.FrameSent, event["data"])
            elif event["opcode"] == 2:
                self.emit(Events.WebSocket.FrameSent, base64.b64decode(event["data"]))

        self._channel.onFrameSent(on_frame_sent)

        def on_frame_received(event: "channels.WebSocketFrameReceivedEvent") -> None:
            if event["opcode"] == 1:
                self.emit(Events.WebSocket.FrameReceived, event["data"])
            elif event["opcode"] == 2:
                self.emit(
                    Events.WebSocket.FrameReceived, base64.b64decode(event["data"])
                )

        self._channel.onFrameReceived(on_frame_received)
        self._channel.onSocketError(
            lambda event: self.emit(Events.WebSocket.Error, event["error"])
        )

        def on_close() -> None:
            self._is_closed = True
            self.emit(Events.WebSocket.Close, self)

        self._channel.onClose(on_close)

    @property
    def url(self) -> str:
        return self._initializer["url"]

    def is_closed(self) -> bool:
        return self._is_closed

    @api_call()
    async def wait_for_event(
        self,
        event: str,
        predicate: Optional[Callable[[Any], Any]],
        timeout: Optional[float],
    ) -> Any:
        # Python: optionsOrPredicate is the predicate and timeout parameters, and the
        # timeout settings return the timeout itself.
        timeout_options = self._page._timeout_settings.timeout(timeout)
        waiter = Waiter.create_for_event(self, event)
        waiter.reject_on_timeout(
            timeout_options,
            f'Timeout {js_string(timeout_options)}ms exceeded while waiting for event "{event}"',
        )
        if event != Events.WebSocket.Error:
            waiter.reject_on_event(self, Events.WebSocket.Error, Error("Socket error"))
        if event != Events.WebSocket.Close:
            waiter.reject_on_event(self, Events.WebSocket.Close, Error("Socket closed"))
        waiter.reject_on_event(
            self._page,
            Events.Page.Close,
            lambda: self._page._close_error_with_reason(),
        )
        result = await waiter.wait_for_event(self, event, predicate)
        waiter.dispose()
        return result

    # Python only: the members of the Python API that upstream does not have.

    def __repr__(self) -> str:
        return f"<WebSocket url={self.url!r}>"

    def expect_event(
        self,
        event: str,
        predicate: Optional[Callable[[Any], Any]],
        timeout: Optional[float],
    ) -> EventContextManagerImpl:
        # waitForEvent() as a context manager. The wait runs in a task, which starts
        # before the action in the with block makes the event happen.
        return EventContextManagerImpl(
            start(
                self.wait_for_event(event=event, predicate=predicate, timeout=timeout)
            )
        )


def validate_headers(headers: Headers) -> None:
    for key in headers.keys():
        value = headers[key]
        # Python: a dict has no undefined values; None is JavaScript's null, which
        # is not a string.
        if not isinstance(value, str):
            raise Error(
                f'Expected value of header "{key}" to be String, but "{_js_typeof(value)}" is found.'
            )


class _HandlerInvocation:
    # Python: a class for the { complete, route } object type.
    def __init__(self, complete: "ManualPromise[None]", route: Route) -> None:
        self.complete = complete
        self.route = route


# Python: Number.MAX_SAFE_INTEGER.
MAX_SAFE_INTEGER = 2**53 - 1


class RouteHandler:
    def __init__(
        self,
        base_url: Optional[str],
        url: URLMatch,
        handler: RouteHandlerCallback,
        times: Optional[int],
    ) -> None:
        self.handled_count = 0
        self._ignore_exception: bool = False
        self._active_invocations: Set[_HandlerInvocation] = set()
        self._saved_zone: Zone

        self._base_url = base_url
        # Python: None is undefined, which takes the default.
        self._times = times if times is not None else MAX_SAFE_INTEGER
        self.url = url
        self.handler = handler
        self._saved_zone = current_zone().without("apiZone")
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

    async def handle(self, route: Route) -> bool:
        return await self._saved_zone.run_async(lambda: self._handle_impl(route))

    async def _handle_impl(self, route: Route) -> bool:
        handler_invocation = _HandlerInvocation(ManualPromise(), route)
        self._active_invocations.add(handler_invocation)
        try:
            return await self._handle_internal(route)
        except Exception as e:
            # If the handler was stopped (without waiting for completion), we ignore all exceptions.
            if self._ignore_exception:
                return False
            if is_target_closed_error(e):
                # We are failing in the handler because the target close closed.
                # Give user a hint!
                # Python: the hint names the Python method and option.
                e = rewrite_error_message(
                    e,
                    f"\"{cast(Error, e).message}\" while running route callback.\nConsider awaiting `await page.unroute_all(behavior='ignoreErrors')`\nbefore the end of the test to ignore remaining routes in flight.",
                )
            raise e
        finally:
            handler_invocation.complete.resolve()
            self._active_invocations.discard(handler_invocation)

    async def stop(self, behavior: Literal["wait", "ignoreErrors"]) -> None:
        # When a handler is manually unrouted or its page/context is closed we either
        # - wait for the current handler invocations to finish
        # - or do not wait, if the user opted out of it, but swallow all exceptions
        #   that happen after the unroute/close.
        if behavior == "ignoreErrors":
            self._ignore_exception = True
        else:
            promises = []
            for activation in self._active_invocations:
                if not activation.route._did_throw:
                    promises.append(activation.complete)
            await all_(promises)

    async def _handle_internal(self, route: Route) -> bool:
        self.handled_count += 1
        handled_promise = route._start_handling()
        # Extract handler into a variable to avoid [RouteHandler.handler] in the stack.
        handler = self.handler
        # Python: the handler may return an awaitable, as a JS handler returns a
        # promise; Promise.all() takes a value too.
        result = handler(route, route.request)
        [handled, _] = await all_(
            [
                handled_promise,
                result if inspect.isawaitable(result) else resolved(result),
            ]
        )
        return handled

    def will_expire(self) -> bool:
        return self.handled_count + 1 >= self._times


class RawHeaders:
    @staticmethod
    def _from_headers_object_lossy(headers: Headers) -> "RawHeaders":
        headers_array: HeadersArray = [
            {"name": name, "value": value}
            for name, value in headers.items()
            if value is not None
        ]
        return RawHeaders(headers_array)

    def __init__(self, headers: HeadersArray) -> None:
        # Python: a dict of lists is the MultiMap.
        self._headers_map: Dict[str, List[str]] = {}
        self._headers_array = headers
        for header in headers:
            self._headers_map.setdefault(header["name"].lower(), []).append(
                header["value"]
            )

    def get(self, name: str) -> Optional[str]:
        values = self.get_all(name)
        if not values or not len(values):
            return None
        return ("\n" if name.lower() == "set-cookie" else ", ").join(values)

    def get_all(self, name: str) -> List[str]:
        return list(self._headers_map.get(name.lower(), []))

    def headers(self) -> Headers:
        result: Headers = {}
        for name in self._headers_map.keys():
            result[name] = cast(str, self.get(name))
        return result

    def headers_array(self) -> HeadersArray:
        return self._headers_array


# Python only: the helpers for what JavaScript has built in.


def _json_stringify(value: Any) -> str:
    # JSON.stringify(value): no spaces, and no escapes for non-ASCII characters.
    return json.dumps(value, allow_nan=False, ensure_ascii=False, separators=(",", ":"))


def _js_typeof(value: Any) -> str:
    # typeof value, for the value that the driver would get.
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if callable(value):
        return "function"
    return "object"


async def _read_file(path: Union[str, Path]) -> bytes:
    # fs.promises.readFile(path) reads in a thread.
    def read() -> bytes:
        with open(path, "rb") as file:
            return file.read()

    return await asyncio.get_running_loop().run_in_executor(None, read)
