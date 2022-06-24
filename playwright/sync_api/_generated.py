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


import pathlib
import sys
import typing

if sys.version_info >= (3, 8):  # pragma: no cover
    from typing import Literal
else:  # pragma: no cover
    from typing_extensions import Literal

from playwright._impl._accessibility import Accessibility as AccessibilityImpl
from playwright._impl._api_structures import (
    Cookie,
    FilePayload,
    FloatRect,
    Geolocation,
    HttpCredentials,
    NameValue,
    PdfMargins,
    Position,
    ProxySettings,
    RemoteAddr,
    RequestSizes,
    ResourceTiming,
    SecurityDetails,
    SetCookieParam,
    SourceLocation,
    StorageState,
    ViewportSize,
)
from playwright._impl._api_types import Error
from playwright._impl._assertions import (
    APIResponseAssertions as APIResponseAssertionsImpl,
)
from playwright._impl._assertions import LocatorAssertions as LocatorAssertionsImpl
from playwright._impl._assertions import PageAssertions as PageAssertionsImpl
from playwright._impl._browser import Browser as BrowserImpl
from playwright._impl._browser_context import BrowserContext as BrowserContextImpl
from playwright._impl._browser_type import BrowserType as BrowserTypeImpl
from playwright._impl._cdp_session import CDPSession as CDPSessionImpl
from playwright._impl._console_message import ConsoleMessage as ConsoleMessageImpl
from playwright._impl._dialog import Dialog as DialogImpl
from playwright._impl._download import Download as DownloadImpl
from playwright._impl._element_handle import ElementHandle as ElementHandleImpl
from playwright._impl._fetch import APIRequest as APIRequestImpl
from playwright._impl._fetch import APIRequestContext as APIRequestContextImpl
from playwright._impl._fetch import APIResponse as APIResponseImpl
from playwright._impl._file_chooser import FileChooser as FileChooserImpl
from playwright._impl._frame import Frame as FrameImpl
from playwright._impl._input import Keyboard as KeyboardImpl
from playwright._impl._input import Mouse as MouseImpl
from playwright._impl._input import Touchscreen as TouchscreenImpl
from playwright._impl._js_handle import JSHandle as JSHandleImpl
from playwright._impl._locator import FrameLocator as FrameLocatorImpl
from playwright._impl._locator import Locator as LocatorImpl
from playwright._impl._network import Request as RequestImpl
from playwright._impl._network import Response as ResponseImpl
from playwright._impl._network import Route as RouteImpl
from playwright._impl._network import WebSocket as WebSocketImpl
from playwright._impl._page import Page as PageImpl
from playwright._impl._page import Worker as WorkerImpl
from playwright._impl._playwright import Playwright as PlaywrightImpl
from playwright._impl._selectors import Selectors as SelectorsImpl
from playwright._impl._sync_base import (
    EventContextManager,
    SyncBase,
    SyncContextManager,
    mapping,
)
from playwright._impl._tracing import Tracing as TracingImpl
from playwright._impl._video import Video as VideoImpl

NoneType = type(None)


class Request(SyncBase):
    @property
    def url(self) -> str:
        """Request.url

        URL of the request.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.url)

    @property
    def resource_type(self) -> str:
        """Request.resource_type

        Contains the request's resource type as it was perceived by the rendering engine. ResourceType will be one of the
        following: `document`, `stylesheet`, `image`, `media`, `font`, `script`, `texttrack`, `xhr`, `fetch`, `eventsource`,
        `websocket`, `manifest`, `other`.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.resource_type)

    @property
    def method(self) -> str:
        """Request.method

        Request's method (GET, POST, etc.)

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.method)

    @property
    def post_data(self) -> typing.Optional[str]:
        """Request.post_data

        Request's post body, if any.

        Returns
        -------
        Union[str, NoneType]
        """
        return mapping.from_maybe_impl(self._impl_obj.post_data)

    @property
    def post_data_json(self) -> typing.Optional[typing.Any]:
        """Request.post_data_json

        Returns parsed request's body for `form-urlencoded` and JSON as a fallback if any.

        When the response is `application/x-www-form-urlencoded` then a key/value object of the values will be returned.
        Otherwise it will be parsed as JSON.

        Returns
        -------
        Union[Any, NoneType]
        """
        return mapping.from_maybe_impl(self._impl_obj.post_data_json)

    @property
    def post_data_buffer(self) -> typing.Optional[bytes]:
        """Request.post_data_buffer

        Request's post body in a binary form, if any.

        Returns
        -------
        Union[bytes, NoneType]
        """
        return mapping.from_maybe_impl(self._impl_obj.post_data_buffer)

    @property
    def frame(self) -> "Frame":
        """Request.frame

        Returns the `Frame` that initiated this request.

        Returns
        -------
        Frame
        """
        return mapping.from_impl(self._impl_obj.frame)

    @property
    def redirected_from(self) -> typing.Optional["Request"]:
        """Request.redirected_from

        Request that was redirected by the server to this one, if any.

        When the server responds with a redirect, Playwright creates a new `Request` object. The two requests are connected by
        `redirectedFrom()` and `redirectedTo()` methods. When multiple server redirects has happened, it is possible to
        construct the whole redirect chain by repeatedly calling `redirectedFrom()`.

        For example, if the website `http://example.com` redirects to `https://example.com`:

        ```py
        response = page.goto(\"http://example.com\")
        print(response.request.redirected_from.url) # \"http://example.com\"
        ```

        If the website `https://google.com` has no redirects:

        ```py
        response = page.goto(\"https://google.com\")
        print(response.request.redirected_from) # None
        ```

        Returns
        -------
        Union[Request, NoneType]
        """
        return mapping.from_impl_nullable(self._impl_obj.redirected_from)

    @property
    def redirected_to(self) -> typing.Optional["Request"]:
        """Request.redirected_to

        New request issued by the browser if the server responded with redirect.

        This method is the opposite of `request.redirected_from()`:

        ```py
        assert request.redirected_from.redirected_to == request
        ```

        Returns
        -------
        Union[Request, NoneType]
        """
        return mapping.from_impl_nullable(self._impl_obj.redirected_to)

    @property
    def failure(self) -> typing.Optional[str]:
        """Request.failure

        The method returns `null` unless this request has failed, as reported by `requestfailed` event.

        Example of logging of all the failed requests:

        ```py
        page.on(\"requestfailed\", lambda request: print(request.url + \" \" + request.failure))
        ```

        Returns
        -------
        Union[str, NoneType]
        """
        return mapping.from_maybe_impl(self._impl_obj.failure)

    @property
    def timing(self) -> ResourceTiming:
        """Request.timing

        Returns resource timing information for given request. Most of the timing values become available upon the response,
        `responseEnd` becomes available when request finishes. Find more information at
        [Resource Timing API](https://developer.mozilla.org/en-US/docs/Web/API/PerformanceResourceTiming).

        ```py
        with page.expect_event(\"requestfinished\") as request_info:
            page.goto(\"http://example.com\")
        request = request_info.value
        print(request.timing)
        ```

        Returns
        -------
        {startTime: float, domainLookupStart: float, domainLookupEnd: float, connectStart: float, secureConnectionStart: float, connectEnd: float, requestStart: float, responseStart: float, responseEnd: float}
        """
        return mapping.from_impl(self._impl_obj.timing)

    @property
    def headers(self) -> typing.Dict[str, str]:
        """Request.headers

        **DEPRECATED** Incomplete list of headers as seen by the rendering engine. Use `request.all_headers()` instead.

        Returns
        -------
        Dict[str, str]
        """
        return mapping.from_maybe_impl(self._impl_obj.headers)

    def sizes(self) -> RequestSizes:
        """Request.sizes

        Returns resource size information for given request.

        Returns
        -------
        {requestBodySize: int, requestHeadersSize: int, responseBodySize: int, responseHeadersSize: int}
        """

        return mapping.from_impl(self._sync(self._impl_obj.sizes()))

    def response(self) -> typing.Optional["Response"]:
        """Request.response

        Returns the matching `Response` object, or `null` if the response was not received due to error.

        Returns
        -------
        Union[Response, NoneType]
        """

        return mapping.from_impl_nullable(self._sync(self._impl_obj.response()))

    def is_navigation_request(self) -> bool:
        """Request.is_navigation_request

        Whether this request is driving frame's navigation.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(self._impl_obj.is_navigation_request())

    def all_headers(self) -> typing.Dict[str, str]:
        """Request.all_headers

        An object with all the request HTTP headers associated with this request. The header names are lower-cased.

        Returns
        -------
        Dict[str, str]
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.all_headers()))

    def headers_array(self) -> typing.List[NameValue]:
        """Request.headers_array

        An array with all the request HTTP headers associated with this request. Unlike `request.all_headers()`, header
        names are NOT lower-cased. Headers with multiple entries, such as `Set-Cookie`, appear in the array multiple times.

        Returns
        -------
        List[{name: str, value: str}]
        """

        return mapping.from_impl_list(self._sync(self._impl_obj.headers_array()))

    def header_value(self, name: str) -> typing.Optional[str]:
        """Request.header_value

        Returns the value of the header matching the name. The name is case insensitive.

        Parameters
        ----------
        name : str
            Name of the header.

        Returns
        -------
        Union[str, NoneType]
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.header_value(name=name))
        )


mapping.register(RequestImpl, Request)


class Response(SyncBase):
    @property
    def url(self) -> str:
        """Response.url

        Contains the URL of the response.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.url)

    @property
    def ok(self) -> bool:
        """Response.ok

        Contains a boolean stating whether the response was successful (status in the range 200-299) or not.

        Returns
        -------
        bool
        """
        return mapping.from_maybe_impl(self._impl_obj.ok)

    @property
    def status(self) -> int:
        """Response.status

        Contains the status code of the response (e.g., 200 for a success).

        Returns
        -------
        int
        """
        return mapping.from_maybe_impl(self._impl_obj.status)

    @property
    def status_text(self) -> str:
        """Response.status_text

        Contains the status text of the response (e.g. usually an \"OK\" for a success).

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.status_text)

    @property
    def headers(self) -> typing.Dict[str, str]:
        """Response.headers

        **DEPRECATED** Incomplete list of headers as seen by the rendering engine. Use `response.all_headers()` instead.

        Returns
        -------
        Dict[str, str]
        """
        return mapping.from_maybe_impl(self._impl_obj.headers)

    @property
    def from_service_worker(self) -> bool:
        """Response.from_service_worker

        Indicates whether this Response was fullfilled by a Service Worker's Fetch Handler (i.e. via
        [FetchEvent.respondWith](https://developer.mozilla.org/en-US/docs/Web/API/FetchEvent/respondWith)).

        Returns
        -------
        bool
        """
        return mapping.from_maybe_impl(self._impl_obj.from_service_worker)

    @property
    def request(self) -> "Request":
        """Response.request

        Returns the matching `Request` object.

        Returns
        -------
        Request
        """
        return mapping.from_impl(self._impl_obj.request)

    @property
    def frame(self) -> "Frame":
        """Response.frame

        Returns the `Frame` that initiated this response.

        Returns
        -------
        Frame
        """
        return mapping.from_impl(self._impl_obj.frame)

    def all_headers(self) -> typing.Dict[str, str]:
        """Response.all_headers

        An object with all the response HTTP headers associated with this response.

        Returns
        -------
        Dict[str, str]
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.all_headers()))

    def headers_array(self) -> typing.List[NameValue]:
        """Response.headers_array

        An array with all the request HTTP headers associated with this response. Unlike `response.all_headers()`, header
        names are NOT lower-cased. Headers with multiple entries, such as `Set-Cookie`, appear in the array multiple times.

        Returns
        -------
        List[{name: str, value: str}]
        """

        return mapping.from_impl_list(self._sync(self._impl_obj.headers_array()))

    def header_value(self, name: str) -> typing.Optional[str]:
        """Response.header_value

        Returns the value of the header matching the name. The name is case insensitive. If multiple headers have the same name
        (except `set-cookie`), they are returned as a list separated by `, `. For `set-cookie`, the `\\n` separator is used. If
        no headers are found, `null` is returned.

        Parameters
        ----------
        name : str
            Name of the header.

        Returns
        -------
        Union[str, NoneType]
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.header_value(name=name))
        )

    def header_values(self, name: str) -> typing.List[str]:
        """Response.header_values

        Returns all values of the headers matching the name, for example `set-cookie`. The name is case insensitive.

        Parameters
        ----------
        name : str
            Name of the header.

        Returns
        -------
        List[str]
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.header_values(name=name))
        )

    def server_addr(self) -> typing.Optional[RemoteAddr]:
        """Response.server_addr

        Returns the IP address and port of the server.

        Returns
        -------
        Union[{ipAddress: str, port: int}, NoneType]
        """

        return mapping.from_impl_nullable(self._sync(self._impl_obj.server_addr()))

    def security_details(self) -> typing.Optional[SecurityDetails]:
        """Response.security_details

        Returns SSL and other security information.

        Returns
        -------
        Union[{issuer: Union[str, NoneType], protocol: Union[str, NoneType], subjectName: Union[str, NoneType], validFrom: Union[float, NoneType], validTo: Union[float, NoneType]}, NoneType]
        """

        return mapping.from_impl_nullable(self._sync(self._impl_obj.security_details()))

    def finished(self) -> NoneType:
        """Response.finished

        Waits for this response to finish, returns always `null`.
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.finished()))

    def body(self) -> bytes:
        """Response.body

        Returns the buffer with response body.

        Returns
        -------
        bytes
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.body()))

    def text(self) -> str:
        """Response.text

        Returns the text representation of response body.

        Returns
        -------
        str
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.text()))

    def json(self) -> typing.Any:
        """Response.json

        Returns the JSON representation of response body.

        This method will throw if the response body is not parsable via `JSON.parse`.

        Returns
        -------
        Any
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.json()))


mapping.register(ResponseImpl, Response)


class Route(SyncBase):
    @property
    def request(self) -> "Request":
        """Route.request

        A request to be routed.

        Returns
        -------
        Request
        """
        return mapping.from_impl(self._impl_obj.request)

    def abort(self, error_code: str = None) -> NoneType:
        """Route.abort

        Aborts the route's request.

        Parameters
        ----------
        error_code : Union[str, NoneType]
            Optional error code. Defaults to `failed`, could be one of the following:
            - `'aborted'` - An operation was aborted (due to user action)
            - `'accessdenied'` - Permission to access a resource, other than the network, was denied
            - `'addressunreachable'` - The IP address is unreachable. This usually means that there is no route to the specified
              host or network.
            - `'blockedbyclient'` - The client chose to block the request.
            - `'blockedbyresponse'` - The request failed because the response was delivered along with requirements which are not
              met ('X-Frame-Options' and 'Content-Security-Policy' ancestor checks, for instance).
            - `'connectionaborted'` - A connection timed out as a result of not receiving an ACK for data sent.
            - `'connectionclosed'` - A connection was closed (corresponding to a TCP FIN).
            - `'connectionfailed'` - A connection attempt failed.
            - `'connectionrefused'` - A connection attempt was refused.
            - `'connectionreset'` - A connection was reset (corresponding to a TCP RST).
            - `'internetdisconnected'` - The Internet connection has been lost.
            - `'namenotresolved'` - The host name could not be resolved.
            - `'timedout'` - An operation timed out.
            - `'failed'` - A generic failure occurred.
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.abort(errorCode=error_code))
        )

    def fulfill(
        self,
        *,
        status: int = None,
        headers: typing.Optional[typing.Dict[str, str]] = None,
        body: typing.Union[str, bytes] = None,
        path: typing.Union[str, pathlib.Path] = None,
        content_type: str = None,
        response: "APIResponse" = None
    ) -> NoneType:
        """Route.fulfill

        Fulfills route's request with given response.

        An example of fulfilling all requests with 404 responses:

        ```py
        page.route(\"**/*\", lambda route: route.fulfill(
            status=404,
            content_type=\"text/plain\",
            body=\"not found!\"))
        ```

        An example of serving static file:

        ```py
        page.route(\"**/xhr_endpoint\", lambda route: route.fulfill(path=\"mock_data.json\"))
        ```

        Parameters
        ----------
        status : Union[int, NoneType]
            Response status code, defaults to `200`.
        headers : Union[Dict[str, str], NoneType]
            Response headers. Header values will be converted to a string.
        body : Union[bytes, str, NoneType]
            Response body.
        path : Union[pathlib.Path, str, NoneType]
            File path to respond with. The content type will be inferred from file extension. If `path` is a relative path, then it
            is resolved relative to the current working directory.
        content_type : Union[str, NoneType]
            If set, equals to setting `Content-Type` response header.
        response : Union[APIResponse, NoneType]
            `APIResponse` to fulfill route's request with. Individual fields of the response (such as headers) can be overridden
            using fulfill options.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.fulfill(
                    status=status,
                    headers=mapping.to_impl(headers),
                    body=body,
                    path=path,
                    contentType=content_type,
                    response=response._impl_obj if response else None,
                )
            )
        )

    def fallback(
        self,
        *,
        url: str = None,
        method: str = None,
        headers: typing.Optional[typing.Dict[str, str]] = None,
        post_data: typing.Union[str, bytes] = None
    ) -> NoneType:
        """Route.fallback

        When several routes match the given pattern, they run in the order opposite to their registration. That way the last
        registered route can always override all the previos ones. In the example below, request will be handled by the
        bottom-most handler first, then it'll fall back to the previous one and in the end will be aborted by the first
        registered route.

        ```py
        page.route(\"**/*\", lambda route: route.abort())  # Runs last.
        page.route(\"**/*\", lambda route: route.fallback())  # Runs second.
        page.route(\"**/*\", lambda route: route.fallback())  # Runs first.
        ```

        Registering multiple routes is useful when you want separate handlers to handle different kinds of requests, for example
        API calls vs page resources or GET requests vs POST requests as in the example below.

        ```py
        # Handle GET requests.
        def handle_post(route):
            if route.request.method != \"GET\":
                route.fallback()
                return
          # Handling GET only.
          # ...

        # Handle POST requests.
        def handle_post(route):
            if route.request.method != \"POST\":
                route.fallback()
                return
          # Handling POST only.
          # ...

        page.route(\"**/*\", handle_get)
        page.route(\"**/*\", handle_post)
        ```

        One can also modify request while falling back to the subsequent handler, that way intermediate route handler can modify
        url, method, headers and postData of the request.

        ```py
        def handle(route, request):
            # override headers
            headers = {
                **request.headers,
                \"foo\": \"foo-value\" # set \"foo\" header
                \"bar\": None # remove \"bar\" header
            }
            route.fallback(headers=headers)
        }
        page.route(\"**/*\", handle)
        ```

        Parameters
        ----------
        url : Union[str, NoneType]
            If set changes the request URL. New URL must have same protocol as original one. Changing the URL won't affect the route
            matching, all the routes are matched using the original request URL.
        method : Union[str, NoneType]
            If set changes the request method (e.g. GET or POST)
        headers : Union[Dict[str, str], NoneType]
            If set changes the request HTTP headers. Header values will be converted to a string.
        post_data : Union[bytes, str, NoneType]
            If set changes the post data of request
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.fallback(
                    url=url,
                    method=method,
                    headers=mapping.to_impl(headers),
                    postData=post_data,
                )
            )
        )

    def continue_(
        self,
        *,
        url: str = None,
        method: str = None,
        headers: typing.Optional[typing.Dict[str, str]] = None,
        post_data: typing.Union[str, bytes] = None
    ) -> NoneType:
        """Route.continue_

        Continues route's request with optional overrides.

        ```py
        def handle(route, request):
            # override headers
            headers = {
                **request.headers,
                \"foo\": \"foo-value\" # set \"foo\" header
                \"bar\": None # remove \"bar\" header
            }
            route.continue_(headers=headers)
        }
        page.route(\"**/*\", handle)
        ```

        Parameters
        ----------
        url : Union[str, NoneType]
            If set changes the request URL. New URL must have same protocol as original one.
        method : Union[str, NoneType]
            If set changes the request method (e.g. GET or POST)
        headers : Union[Dict[str, str], NoneType]
            If set changes the request HTTP headers. Header values will be converted to a string.
        post_data : Union[bytes, str, NoneType]
            If set changes the post data of request
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.continue_(
                    url=url,
                    method=method,
                    headers=mapping.to_impl(headers),
                    postData=post_data,
                )
            )
        )


mapping.register(RouteImpl, Route)


class WebSocket(SyncBase):
    @typing.overload
    def on(
        self, event: Literal["close"], f: typing.Callable[["WebSocket"], "None"]
    ) -> None:
        """
        Fired when the websocket closes."""

    @typing.overload
    def on(
        self,
        event: Literal["framereceived"],
        f: typing.Callable[["typing.Dict"], "None"],
    ) -> None:
        """
        Fired when the websocket receives a frame."""

    @typing.overload
    def on(
        self, event: Literal["framesent"], f: typing.Callable[["typing.Dict"], "None"]
    ) -> None:
        """
        Fired when the websocket sends a frame."""

    @typing.overload
    def on(
        self, event: Literal["socketerror"], f: typing.Callable[["str"], "None"]
    ) -> None:
        """
        Fired when the websocket has an error."""

    def on(self, event: str, f: typing.Callable[..., None]) -> None:
        return super().on(event=event, f=f)

    @typing.overload
    def once(
        self, event: Literal["close"], f: typing.Callable[["WebSocket"], "None"]
    ) -> None:
        """
        Fired when the websocket closes."""

    @typing.overload
    def once(
        self,
        event: Literal["framereceived"],
        f: typing.Callable[["typing.Dict"], "None"],
    ) -> None:
        """
        Fired when the websocket receives a frame."""

    @typing.overload
    def once(
        self, event: Literal["framesent"], f: typing.Callable[["typing.Dict"], "None"]
    ) -> None:
        """
        Fired when the websocket sends a frame."""

    @typing.overload
    def once(
        self, event: Literal["socketerror"], f: typing.Callable[["str"], "None"]
    ) -> None:
        """
        Fired when the websocket has an error."""

    def once(self, event: str, f: typing.Callable[..., None]) -> None:
        return super().once(event=event, f=f)

    @property
    def url(self) -> str:
        """WebSocket.url

        Contains the URL of the WebSocket.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.url)

    def expect_event(
        self, event: str, predicate: typing.Callable = None, *, timeout: float = None
    ) -> EventContextManager:
        """WebSocket.expect_event

        Waits for event to fire and passes its value into the predicate function. Returns when the predicate returns truthy
        value. Will throw an error if the webSocket is closed before the event is fired. Returns the event data value.

        Parameters
        ----------
        event : str
            Event name, same one would pass into `webSocket.on(event)`.
        predicate : Union[Callable, NoneType]
            Receives the event data and resolves to truthy value when the waiting should resolve.
        timeout : Union[float, NoneType]
            Maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default
            value can be changed by using the `browser_context.set_default_timeout()`.

        Returns
        -------
        EventContextManager
        """
        return EventContextManager(
            self,
            self._impl_obj.expect_event(
                event=event, predicate=self._wrap_handler(predicate), timeout=timeout
            ).future,
        )

    def wait_for_event(
        self, event: str, predicate: typing.Callable = None, *, timeout: float = None
    ) -> typing.Any:
        """WebSocket.wait_for_event

        > NOTE: In most cases, you should use `web_socket.expect_event()`.

        Waits for given `event` to fire. If predicate is provided, it passes event's value into the `predicate` function and
        waits for `predicate(event)` to return a truthy value. Will throw an error if the socket is closed before the `event` is
        fired.

        Parameters
        ----------
        event : str
            Event name, same one typically passed into `*.on(event)`.
        predicate : Union[Callable, NoneType]
            Receives the event data and resolves to truthy value when the waiting should resolve.
        timeout : Union[float, NoneType]
            Maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default
            value can be changed by using the `browser_context.set_default_timeout()`.

        Returns
        -------
        Any
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.wait_for_event(
                    event=event,
                    predicate=self._wrap_handler(predicate),
                    timeout=timeout,
                )
            )
        )

    def is_closed(self) -> bool:
        """WebSocket.is_closed

        Indicates that the web socket has been closed.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(self._impl_obj.is_closed())


mapping.register(WebSocketImpl, WebSocket)


class Keyboard(SyncBase):
    def down(self, key: str) -> NoneType:
        """Keyboard.down

        Dispatches a `keydown` event.

        `key` can specify the intended [keyboardEvent.key](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/key)
        value or a single character to generate the text for. A superset of the `key` values can be found
        [here](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/key/Key_Values). Examples of the keys are:

        `F1` - `F12`, `Digit0`- `Digit9`, `KeyA`- `KeyZ`, `Backquote`, `Minus`, `Equal`, `Backslash`, `Backspace`, `Tab`,
        `Delete`, `Escape`, `ArrowDown`, `End`, `Enter`, `Home`, `Insert`, `PageDown`, `PageUp`, `ArrowRight`, `ArrowUp`, etc.

        Following modification shortcuts are also supported: `Shift`, `Control`, `Alt`, `Meta`, `ShiftLeft`.

        Holding down `Shift` will type the text that corresponds to the `key` in the upper case.

        If `key` is a single character, it is case-sensitive, so the values `a` and `A` will generate different respective
        texts.

        If `key` is a modifier key, `Shift`, `Meta`, `Control`, or `Alt`, subsequent key presses will be sent with that modifier
        active. To release the modifier key, use `keyboard.up()`.

        After the key is pressed once, subsequent calls to `keyboard.down()` will have
        [repeat](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/repeat) set to true. To release the key, use
        `keyboard.up()`.

        > NOTE: Modifier keys DO influence `keyboard.down`. Holding down `Shift` will type the text in upper case.

        Parameters
        ----------
        key : str
            Name of the key to press or a character to generate, such as `ArrowLeft` or `a`.
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.down(key=key)))

    def up(self, key: str) -> NoneType:
        """Keyboard.up

        Dispatches a `keyup` event.

        Parameters
        ----------
        key : str
            Name of the key to press or a character to generate, such as `ArrowLeft` or `a`.
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.up(key=key)))

    def insert_text(self, text: str) -> NoneType:
        """Keyboard.insert_text

        Dispatches only `input` event, does not emit the `keydown`, `keyup` or `keypress` events.

        ```py
        page.keyboard.insert_text(\"嗨\")
        ```

        > NOTE: Modifier keys DO NOT effect `keyboard.insertText`. Holding down `Shift` will not type the text in upper case.

        Parameters
        ----------
        text : str
            Sets input to the specified text value.
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.insert_text(text=text))
        )

    def type(self, text: str, *, delay: float = None) -> NoneType:
        """Keyboard.type

        Sends a `keydown`, `keypress`/`input`, and `keyup` event for each character in the text.

        To press a special key, like `Control` or `ArrowDown`, use `keyboard.press()`.

        ```py
        page.keyboard.type(\"Hello\") # types instantly
        page.keyboard.type(\"World\", delay=100) # types slower, like a user
        ```

        > NOTE: Modifier keys DO NOT effect `keyboard.type`. Holding down `Shift` will not type the text in upper case.
        > NOTE: For characters that are not on a US keyboard, only an `input` event will be sent.

        Parameters
        ----------
        text : str
            A text to type into a focused element.
        delay : Union[float, NoneType]
            Time to wait between key presses in milliseconds. Defaults to 0.
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.type(text=text, delay=delay))
        )

    def press(self, key: str, *, delay: float = None) -> NoneType:
        """Keyboard.press

        `key` can specify the intended [keyboardEvent.key](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/key)
        value or a single character to generate the text for. A superset of the `key` values can be found
        [here](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/key/Key_Values). Examples of the keys are:

        `F1` - `F12`, `Digit0`- `Digit9`, `KeyA`- `KeyZ`, `Backquote`, `Minus`, `Equal`, `Backslash`, `Backspace`, `Tab`,
        `Delete`, `Escape`, `ArrowDown`, `End`, `Enter`, `Home`, `Insert`, `PageDown`, `PageUp`, `ArrowRight`, `ArrowUp`, etc.

        Following modification shortcuts are also supported: `Shift`, `Control`, `Alt`, `Meta`, `ShiftLeft`.

        Holding down `Shift` will type the text that corresponds to the `key` in the upper case.

        If `key` is a single character, it is case-sensitive, so the values `a` and `A` will generate different respective
        texts.

        Shortcuts such as `key: \"Control+o\"` or `key: \"Control+Shift+T\"` are supported as well. When specified with the
        modifier, modifier is pressed and being held while the subsequent key is being pressed.

        ```py
        page = browser.new_page()
        page.goto(\"https://keycode.info\")
        page.keyboard.press(\"a\")
        page.screenshot(path=\"a.png\")
        page.keyboard.press(\"ArrowLeft\")
        page.screenshot(path=\"arrow_left.png\")
        page.keyboard.press(\"Shift+O\")
        page.screenshot(path=\"o.png\")
        browser.close()
        ```

        Shortcut for `keyboard.down()` and `keyboard.up()`.

        Parameters
        ----------
        key : str
            Name of the key to press or a character to generate, such as `ArrowLeft` or `a`.
        delay : Union[float, NoneType]
            Time to wait between `keydown` and `keyup` in milliseconds. Defaults to 0.
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.press(key=key, delay=delay))
        )


mapping.register(KeyboardImpl, Keyboard)


class Mouse(SyncBase):
    def move(self, x: float, y: float, *, steps: int = None) -> NoneType:
        """Mouse.move

        Dispatches a `mousemove` event.

        Parameters
        ----------
        x : float
        y : float
        steps : Union[int, NoneType]
            Defaults to 1. Sends intermediate `mousemove` events.
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.move(x=x, y=y, steps=steps))
        )

    def down(
        self,
        *,
        button: Literal["left", "middle", "right"] = None,
        click_count: int = None
    ) -> NoneType:
        """Mouse.down

        Dispatches a `mousedown` event.

        Parameters
        ----------
        button : Union["left", "middle", "right", NoneType]
            Defaults to `left`.
        click_count : Union[int, NoneType]
            defaults to 1. See [UIEvent.detail].
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.down(button=button, clickCount=click_count))
        )

    def up(
        self,
        *,
        button: Literal["left", "middle", "right"] = None,
        click_count: int = None
    ) -> NoneType:
        """Mouse.up

        Dispatches a `mouseup` event.

        Parameters
        ----------
        button : Union["left", "middle", "right", NoneType]
            Defaults to `left`.
        click_count : Union[int, NoneType]
            defaults to 1. See [UIEvent.detail].
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.up(button=button, clickCount=click_count))
        )

    def click(
        self,
        x: float,
        y: float,
        *,
        delay: float = None,
        button: Literal["left", "middle", "right"] = None,
        click_count: int = None
    ) -> NoneType:
        """Mouse.click

        Shortcut for `mouse.move()`, `mouse.down()`, `mouse.up()`.

        Parameters
        ----------
        x : float
        y : float
        delay : Union[float, NoneType]
            Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        button : Union["left", "middle", "right", NoneType]
            Defaults to `left`.
        click_count : Union[int, NoneType]
            defaults to 1. See [UIEvent.detail].
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.click(
                    x=x, y=y, delay=delay, button=button, clickCount=click_count
                )
            )
        )

    def dblclick(
        self,
        x: float,
        y: float,
        *,
        delay: float = None,
        button: Literal["left", "middle", "right"] = None
    ) -> NoneType:
        """Mouse.dblclick

        Shortcut for `mouse.move()`, `mouse.down()`, `mouse.up()`, `mouse.down()` and
        `mouse.up()`.

        Parameters
        ----------
        x : float
        y : float
        delay : Union[float, NoneType]
            Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        button : Union["left", "middle", "right", NoneType]
            Defaults to `left`.
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.dblclick(x=x, y=y, delay=delay, button=button))
        )

    def wheel(self, delta_x: float, delta_y: float) -> NoneType:
        """Mouse.wheel

        Dispatches a `wheel` event.

        > NOTE: Wheel events may cause scrolling if they are not handled, and this method does not wait for the scrolling to
        finish before returning.

        Parameters
        ----------
        delta_x : float
            Pixels to scroll horizontally.
        delta_y : float
            Pixels to scroll vertically.
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.wheel(deltaX=delta_x, deltaY=delta_y))
        )


mapping.register(MouseImpl, Mouse)


class Touchscreen(SyncBase):
    def tap(self, x: float, y: float) -> NoneType:
        """Touchscreen.tap

        Dispatches a `touchstart` and `touchend` event with a single touch at the position (`x`,`y`).

        Parameters
        ----------
        x : float
        y : float
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.tap(x=x, y=y)))


mapping.register(TouchscreenImpl, Touchscreen)


class JSHandle(SyncBase):
    def evaluate(self, expression: str, arg: typing.Any = None) -> typing.Any:
        """JSHandle.evaluate

        Returns the return value of `expression`.

        This method passes this handle as the first argument to `expression`.

        If `expression` returns a [Promise], then `handle.evaluate` would wait for the promise to resolve and return its value.

        Examples:

        ```py
        tweet_handle = page.query_selector(\".tweet .retweets\")
        assert tweet_handle.evaluate(\"node => node.innerText\") == \"10 retweets\"
        ```

        Parameters
        ----------
        expression : str
            JavaScript expression to be evaluated in the browser context. If it looks like a function declaration, it is interpreted
            as a function. Otherwise, evaluated as an expression.
        arg : Union[Any, NoneType]
            Optional argument to pass to `expression`.

        Returns
        -------
        Any
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.evaluate(expression=expression, arg=mapping.to_impl(arg))
            )
        )

    def evaluate_handle(self, expression: str, arg: typing.Any = None) -> "JSHandle":
        """JSHandle.evaluate_handle

        Returns the return value of `expression` as a `JSHandle`.

        This method passes this handle as the first argument to `expression`.

        The only difference between `jsHandle.evaluate` and `jsHandle.evaluateHandle` is that `jsHandle.evaluateHandle` returns
        `JSHandle`.

        If the function passed to the `jsHandle.evaluateHandle` returns a [Promise], then `jsHandle.evaluateHandle` would wait
        for the promise to resolve and return its value.

        See `page.evaluate_handle()` for more details.

        Parameters
        ----------
        expression : str
            JavaScript expression to be evaluated in the browser context. If it looks like a function declaration, it is interpreted
            as a function. Otherwise, evaluated as an expression.
        arg : Union[Any, NoneType]
            Optional argument to pass to `expression`.

        Returns
        -------
        JSHandle
        """

        return mapping.from_impl(
            self._sync(
                self._impl_obj.evaluate_handle(
                    expression=expression, arg=mapping.to_impl(arg)
                )
            )
        )

    def get_property(self, property_name: str) -> "JSHandle":
        """JSHandle.get_property

        Fetches a single property from the referenced object.

        Parameters
        ----------
        property_name : str
            property to get

        Returns
        -------
        JSHandle
        """

        return mapping.from_impl(
            self._sync(self._impl_obj.get_property(propertyName=property_name))
        )

    def get_properties(self) -> typing.Dict[str, "JSHandle"]:
        """JSHandle.get_properties

        The method returns a map with **own property names** as keys and JSHandle instances for the property values.

        ```py
        handle = page.evaluate_handle(\"{window, document}\")
        properties = handle.get_properties()
        window_handle = properties.get(\"window\")
        document_handle = properties.get(\"document\")
        handle.dispose()
        ```

        Returns
        -------
        Dict[str, JSHandle]
        """

        return mapping.from_impl_dict(self._sync(self._impl_obj.get_properties()))

    def as_element(self) -> typing.Optional["ElementHandle"]:
        """JSHandle.as_element

        Returns either `null` or the object handle itself, if the object handle is an instance of `ElementHandle`.

        Returns
        -------
        Union[ElementHandle, NoneType]
        """

        return mapping.from_impl_nullable(self._impl_obj.as_element())

    def dispose(self) -> NoneType:
        """JSHandle.dispose

        The `jsHandle.dispose` method stops referencing the element handle.
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.dispose()))

    def json_value(self) -> typing.Any:
        """JSHandle.json_value

        Returns a JSON representation of the object. If the object has a `toJSON` function, it **will not be called**.

        > NOTE: The method will return an empty JSON object if the referenced object is not stringifiable. It will throw an
        error if the object has circular references.

        Returns
        -------
        Any
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.json_value()))


mapping.register(JSHandleImpl, JSHandle)


class ElementHandle(JSHandle):
    def as_element(self) -> typing.Optional["ElementHandle"]:
        """ElementHandle.as_element

        Returns either `null` or the object handle itself, if the object handle is an instance of `ElementHandle`.

        Returns
        -------
        Union[ElementHandle, NoneType]
        """

        return mapping.from_impl_nullable(self._impl_obj.as_element())

    def owner_frame(self) -> typing.Optional["Frame"]:
        """ElementHandle.owner_frame

        Returns the frame containing the given element.

        Returns
        -------
        Union[Frame, NoneType]
        """

        return mapping.from_impl_nullable(self._sync(self._impl_obj.owner_frame()))

    def content_frame(self) -> typing.Optional["Frame"]:
        """ElementHandle.content_frame

        Returns the content frame for element handles referencing iframe nodes, or `null` otherwise

        Returns
        -------
        Union[Frame, NoneType]
        """

        return mapping.from_impl_nullable(self._sync(self._impl_obj.content_frame()))

    def get_attribute(self, name: str) -> typing.Optional[str]:
        """ElementHandle.get_attribute

        Returns element attribute value.

        Parameters
        ----------
        name : str
            Attribute name to get the value for.

        Returns
        -------
        Union[str, NoneType]
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.get_attribute(name=name))
        )

    def text_content(self) -> typing.Optional[str]:
        """ElementHandle.text_content

        Returns the `node.textContent`.

        Returns
        -------
        Union[str, NoneType]
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.text_content()))

    def inner_text(self) -> str:
        """ElementHandle.inner_text

        Returns the `element.innerText`.

        Returns
        -------
        str
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.inner_text()))

    def inner_html(self) -> str:
        """ElementHandle.inner_html

        Returns the `element.innerHTML`.

        Returns
        -------
        str
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.inner_html()))

    def is_checked(self) -> bool:
        """ElementHandle.is_checked

        Returns whether the element is checked. Throws if the element is not a checkbox or radio input.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.is_checked()))

    def is_disabled(self) -> bool:
        """ElementHandle.is_disabled

        Returns whether the element is disabled, the opposite of [enabled](https://playwright.dev/python/docs/actionability#enabled).

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.is_disabled()))

    def is_editable(self) -> bool:
        """ElementHandle.is_editable

        Returns whether the element is [editable](https://playwright.dev/python/docs/actionability#editable).

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.is_editable()))

    def is_enabled(self) -> bool:
        """ElementHandle.is_enabled

        Returns whether the element is [enabled](https://playwright.dev/python/docs/actionability#enabled).

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.is_enabled()))

    def is_hidden(self) -> bool:
        """ElementHandle.is_hidden

        Returns whether the element is hidden, the opposite of [visible](https://playwright.dev/python/docs/actionability#visible).

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.is_hidden()))

    def is_visible(self) -> bool:
        """ElementHandle.is_visible

        Returns whether the element is [visible](https://playwright.dev/python/docs/actionability#visible).

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.is_visible()))

    def dispatch_event(self, type: str, event_init: typing.Dict = None) -> NoneType:
        """ElementHandle.dispatch_event

        The snippet below dispatches the `click` event on the element. Regardless of the visibility state of the element,
        `click` is dispatched. This is equivalent to calling
        [element.click()](https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/click).

        ```py
        element_handle.dispatch_event(\"click\")
        ```

        Under the hood, it creates an instance of an event based on the given `type`, initializes it with `eventInit` properties
        and dispatches it on the element. Events are `composed`, `cancelable` and bubble by default.

        Since `eventInit` is event-specific, please refer to the events documentation for the lists of initial properties:
        - [DragEvent](https://developer.mozilla.org/en-US/docs/Web/API/DragEvent/DragEvent)
        - [FocusEvent](https://developer.mozilla.org/en-US/docs/Web/API/FocusEvent/FocusEvent)
        - [KeyboardEvent](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/KeyboardEvent)
        - [MouseEvent](https://developer.mozilla.org/en-US/docs/Web/API/MouseEvent/MouseEvent)
        - [PointerEvent](https://developer.mozilla.org/en-US/docs/Web/API/PointerEvent/PointerEvent)
        - [TouchEvent](https://developer.mozilla.org/en-US/docs/Web/API/TouchEvent/TouchEvent)
        - [Event](https://developer.mozilla.org/en-US/docs/Web/API/Event/Event)

        You can also specify `JSHandle` as the property value if you want live objects to be passed into the event:

        ```py
        # note you can only create data_transfer in chromium and firefox
        data_transfer = page.evaluate_handle(\"new DataTransfer()\")
        element_handle.dispatch_event(\"#source\", \"dragstart\", {\"dataTransfer\": data_transfer})
        ```

        Parameters
        ----------
        type : str
            DOM event type: `"click"`, `"dragstart"`, etc.
        event_init : Union[Dict, NoneType]
            Optional event-specific initialization properties.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.dispatch_event(
                    type=type, eventInit=mapping.to_impl(event_init)
                )
            )
        )

    def scroll_into_view_if_needed(self, *, timeout: float = None) -> NoneType:
        """ElementHandle.scroll_into_view_if_needed

        This method waits for [actionability](https://playwright.dev/python/docs/actionability) checks, then tries to scroll element into view, unless it is
        completely visible as defined by
        [IntersectionObserver](https://developer.mozilla.org/en-US/docs/Web/API/Intersection_Observer_API)'s `ratio`.

        Throws when `elementHandle` does not point to an element
        [connected](https://developer.mozilla.org/en-US/docs/Web/API/Node/isConnected) to a Document or a ShadowRoot.

        Parameters
        ----------
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.scroll_into_view_if_needed(timeout=timeout))
        )

    def hover(
        self,
        *,
        modifiers: typing.Optional[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        trial: bool = None
    ) -> NoneType:
        """ElementHandle.hover

        This method hovers over the element by performing the following steps:
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the element, unless `force` option is set.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to hover over the center of the element, or the specified `position`.
        1. Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.

        If the element is detached from the DOM at any moment during the action, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`. Passing
        zero timeout disables this.

        Parameters
        ----------
        modifiers : Union[List[Union["Alt", "Control", "Meta", "Shift"]], NoneType]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores current
            modifiers back. If not specified, currently pressed modifiers are used.
        position : Union[{x: float, y: float}, NoneType]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the
            element.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        trial : Union[bool, NoneType]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults to
            `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.hover(
                    modifiers=mapping.to_impl(modifiers),
                    position=position,
                    timeout=timeout,
                    force=force,
                    trial=trial,
                )
            )
        )

    def click(
        self,
        *,
        modifiers: typing.Optional[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: Position = None,
        delay: float = None,
        button: Literal["left", "middle", "right"] = None,
        click_count: int = None,
        timeout: float = None,
        force: bool = None,
        no_wait_after: bool = None,
        trial: bool = None
    ) -> NoneType:
        """ElementHandle.click

        This method clicks the element by performing the following steps:
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the element, unless `force` option is set.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to click in the center of the element, or the specified `position`.
        1. Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.

        If the element is detached from the DOM at any moment during the action, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`. Passing
        zero timeout disables this.

        Parameters
        ----------
        modifiers : Union[List[Union["Alt", "Control", "Meta", "Shift"]], NoneType]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores current
            modifiers back. If not specified, currently pressed modifiers are used.
        position : Union[{x: float, y: float}, NoneType]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the
            element.
        delay : Union[float, NoneType]
            Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        button : Union["left", "middle", "right", NoneType]
            Defaults to `left`.
        click_count : Union[int, NoneType]
            defaults to 1. See [UIEvent.detail].
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        trial : Union[bool, NoneType]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults to
            `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.click(
                    modifiers=mapping.to_impl(modifiers),
                    position=position,
                    delay=delay,
                    button=button,
                    clickCount=click_count,
                    timeout=timeout,
                    force=force,
                    noWaitAfter=no_wait_after,
                    trial=trial,
                )
            )
        )

    def dblclick(
        self,
        *,
        modifiers: typing.Optional[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: Position = None,
        delay: float = None,
        button: Literal["left", "middle", "right"] = None,
        timeout: float = None,
        force: bool = None,
        no_wait_after: bool = None,
        trial: bool = None
    ) -> NoneType:
        """ElementHandle.dblclick

        This method double clicks the element by performing the following steps:
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the element, unless `force` option is set.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to double click in the center of the element, or the specified `position`.
        1. Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set. Note that if the
           first click of the `dblclick()` triggers a navigation event, this method will throw.

        If the element is detached from the DOM at any moment during the action, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`. Passing
        zero timeout disables this.

        > NOTE: `elementHandle.dblclick()` dispatches two `click` events and a single `dblclick` event.

        Parameters
        ----------
        modifiers : Union[List[Union["Alt", "Control", "Meta", "Shift"]], NoneType]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores current
            modifiers back. If not specified, currently pressed modifiers are used.
        position : Union[{x: float, y: float}, NoneType]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the
            element.
        delay : Union[float, NoneType]
            Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        button : Union["left", "middle", "right", NoneType]
            Defaults to `left`.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        trial : Union[bool, NoneType]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults to
            `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.dblclick(
                    modifiers=mapping.to_impl(modifiers),
                    position=position,
                    delay=delay,
                    button=button,
                    timeout=timeout,
                    force=force,
                    noWaitAfter=no_wait_after,
                    trial=trial,
                )
            )
        )

    def select_option(
        self,
        value: typing.Union[str, typing.List[str]] = None,
        *,
        index: typing.Union[int, typing.List[int]] = None,
        label: typing.Union[str, typing.List[str]] = None,
        element: typing.Union["ElementHandle", typing.List["ElementHandle"]] = None,
        timeout: float = None,
        force: bool = None,
        no_wait_after: bool = None
    ) -> typing.List[str]:
        """ElementHandle.select_option

        This method waits for [actionability](https://playwright.dev/python/docs/actionability) checks, waits until all specified options are present in the
        `<select>` element and selects these options.

        If the target element is not a `<select>` element, this method throws an error. However, if the element is inside the
        `<label>` element that has an associated
        [control](https://developer.mozilla.org/en-US/docs/Web/API/HTMLLabelElement/control), the control will be used instead.

        Returns the array of option values that have been successfully selected.

        Triggers a `change` and `input` event once all the provided options have been selected.

        ```py
        # single selection matching the value
        handle.select_option(\"blue\")
        # single selection matching both the label
        handle.select_option(label=\"blue\")
        # multiple selection
        handle.select_option(value=[\"red\", \"green\", \"blue\"])
        ```

        Parameters
        ----------
        value : Union[List[str], str, NoneType]
            Options to select by value. If the `<select>` has the `multiple` attribute, all given options are selected, otherwise
            only the first option matching one of the passed options is selected. Optional.
        index : Union[List[int], int, NoneType]
            Options to select by index. Optional.
        label : Union[List[str], str, NoneType]
            Options to select by label. If the `<select>` has the `multiple` attribute, all given options are selected, otherwise
            only the first option matching one of the passed options is selected. Optional.
        element : Union[ElementHandle, List[ElementHandle], NoneType]
            Option elements to select. Optional.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.

        Returns
        -------
        List[str]
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.select_option(
                    value=mapping.to_impl(value),
                    index=mapping.to_impl(index),
                    label=mapping.to_impl(label),
                    element=mapping.to_impl(element),
                    timeout=timeout,
                    force=force,
                    noWaitAfter=no_wait_after,
                )
            )
        )

    def tap(
        self,
        *,
        modifiers: typing.Optional[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        no_wait_after: bool = None,
        trial: bool = None
    ) -> NoneType:
        """ElementHandle.tap

        This method taps the element by performing the following steps:
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the element, unless `force` option is set.
        1. Scroll the element into view if needed.
        1. Use `page.touchscreen` to tap the center of the element, or the specified `position`.
        1. Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.

        If the element is detached from the DOM at any moment during the action, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`. Passing
        zero timeout disables this.

        > NOTE: `elementHandle.tap()` requires that the `hasTouch` option of the browser context be set to true.

        Parameters
        ----------
        modifiers : Union[List[Union["Alt", "Control", "Meta", "Shift"]], NoneType]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores current
            modifiers back. If not specified, currently pressed modifiers are used.
        position : Union[{x: float, y: float}, NoneType]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the
            element.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        trial : Union[bool, NoneType]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults to
            `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.tap(
                    modifiers=mapping.to_impl(modifiers),
                    position=position,
                    timeout=timeout,
                    force=force,
                    noWaitAfter=no_wait_after,
                    trial=trial,
                )
            )
        )

    def fill(
        self,
        value: str,
        *,
        timeout: float = None,
        no_wait_after: bool = None,
        force: bool = None
    ) -> NoneType:
        """ElementHandle.fill

        This method waits for [actionability](https://playwright.dev/python/docs/actionability) checks, focuses the element, fills it and triggers an `input`
        event after filling. Note that you can pass an empty string to clear the input field.

        If the target element is not an `<input>`, `<textarea>` or `[contenteditable]` element, this method throws an error.
        However, if the element is inside the `<label>` element that has an associated
        [control](https://developer.mozilla.org/en-US/docs/Web/API/HTMLLabelElement/control), the control will be filled
        instead.

        To send fine-grained keyboard events, use `element_handle.type()`.

        Parameters
        ----------
        value : str
            Value to set for the `<input>`, `<textarea>` or `[contenteditable]` element.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.fill(
                    value=value, timeout=timeout, noWaitAfter=no_wait_after, force=force
                )
            )
        )

    def select_text(self, *, force: bool = None, timeout: float = None) -> NoneType:
        """ElementHandle.select_text

        This method waits for [actionability](https://playwright.dev/python/docs/actionability) checks, then focuses the element and selects all its text
        content.

        If the element is inside the `<label>` element that has an associated
        [control](https://developer.mozilla.org/en-US/docs/Web/API/HTMLLabelElement/control), focuses and selects text in the
        control instead.

        Parameters
        ----------
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.select_text(force=force, timeout=timeout))
        )

    def input_value(self, *, timeout: float = None) -> str:
        """ElementHandle.input_value

        Returns `input.value` for the selected `<input>` or `<textarea>` or `<select>` element.

        Throws for non-input elements. However, if the element is inside the `<label>` element that has an associated
        [control](https://developer.mozilla.org/en-US/docs/Web/API/HTMLLabelElement/control), returns the value of the control.

        Parameters
        ----------
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        str
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.input_value(timeout=timeout))
        )

    def set_input_files(
        self,
        files: typing.Union[
            str,
            pathlib.Path,
            FilePayload,
            typing.List[typing.Union[str, pathlib.Path]],
            typing.List[FilePayload],
        ],
        *,
        timeout: float = None,
        no_wait_after: bool = None
    ) -> NoneType:
        """ElementHandle.set_input_files

        Sets the value of the file input to these file paths or files. If some of the `filePaths` are relative paths, then they
        are resolved relative to the current working directory. For empty array, clears the selected files.

        This method expects `ElementHandle` to point to an
        [input element](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/input). However, if the element is inside the
        `<label>` element that has an associated
        [control](https://developer.mozilla.org/en-US/docs/Web/API/HTMLLabelElement/control), targets the control instead.

        Parameters
        ----------
        files : Union[List[Union[pathlib.Path, str]], List[{name: str, mimeType: str, buffer: bytes}], pathlib.Path, str, {name: str, mimeType: str, buffer: bytes}]
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.set_input_files(
                    files=mapping.to_impl(files),
                    timeout=timeout,
                    noWaitAfter=no_wait_after,
                )
            )
        )

    def focus(self) -> NoneType:
        """ElementHandle.focus

        Calls [focus](https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/focus) on the element.
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.focus()))

    def type(
        self,
        text: str,
        *,
        delay: float = None,
        timeout: float = None,
        no_wait_after: bool = None
    ) -> NoneType:
        """ElementHandle.type

        Focuses the element, and then sends a `keydown`, `keypress`/`input`, and `keyup` event for each character in the text.

        To press a special key, like `Control` or `ArrowDown`, use `element_handle.press()`.

        ```py
        element_handle.type(\"hello\") # types instantly
        element_handle.type(\"world\", delay=100) # types slower, like a user
        ```

        An example of typing into a text field and then submitting the form:

        ```py
        element_handle = page.query_selector(\"input\")
        element_handle.type(\"some text\")
        element_handle.press(\"Enter\")
        ```

        Parameters
        ----------
        text : str
            A text to type into a focused element.
        delay : Union[float, NoneType]
            Time to wait between key presses in milliseconds. Defaults to 0.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.type(
                    text=text, delay=delay, timeout=timeout, noWaitAfter=no_wait_after
                )
            )
        )

    def press(
        self,
        key: str,
        *,
        delay: float = None,
        timeout: float = None,
        no_wait_after: bool = None
    ) -> NoneType:
        """ElementHandle.press

        Focuses the element, and then uses `keyboard.down()` and `keyboard.up()`.

        `key` can specify the intended [keyboardEvent.key](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/key)
        value or a single character to generate the text for. A superset of the `key` values can be found
        [here](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/key/Key_Values). Examples of the keys are:

        `F1` - `F12`, `Digit0`- `Digit9`, `KeyA`- `KeyZ`, `Backquote`, `Minus`, `Equal`, `Backslash`, `Backspace`, `Tab`,
        `Delete`, `Escape`, `ArrowDown`, `End`, `Enter`, `Home`, `Insert`, `PageDown`, `PageUp`, `ArrowRight`, `ArrowUp`, etc.

        Following modification shortcuts are also supported: `Shift`, `Control`, `Alt`, `Meta`, `ShiftLeft`.

        Holding down `Shift` will type the text that corresponds to the `key` in the upper case.

        If `key` is a single character, it is case-sensitive, so the values `a` and `A` will generate different respective
        texts.

        Shortcuts such as `key: \"Control+o\"` or `key: \"Control+Shift+T\"` are supported as well. When specified with the
        modifier, modifier is pressed and being held while the subsequent key is being pressed.

        Parameters
        ----------
        key : str
            Name of the key to press or a character to generate, such as `ArrowLeft` or `a`.
        delay : Union[float, NoneType]
            Time to wait between `keydown` and `keyup` in milliseconds. Defaults to 0.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.press(
                    key=key, delay=delay, timeout=timeout, noWaitAfter=no_wait_after
                )
            )
        )

    def set_checked(
        self,
        checked: bool,
        *,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        no_wait_after: bool = None,
        trial: bool = None
    ) -> NoneType:
        """ElementHandle.set_checked

        This method checks or unchecks an element by performing the following steps:
        1. Ensure that element is a checkbox or a radio input. If not, this method throws.
        1. If the element already has the right checked state, this method returns immediately.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the matched element, unless `force` option is set. If the
           element is detached during the checks, the whole action is retried.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to click in the center of the element.
        1. Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.
        1. Ensure that the element is now checked or unchecked. If not, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`. Passing
        zero timeout disables this.

        Parameters
        ----------
        checked : bool
            Whether to check or uncheck the checkbox.
        position : Union[{x: float, y: float}, NoneType]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the
            element.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        trial : Union[bool, NoneType]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults to
            `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.set_checked(
                    checked=checked,
                    position=position,
                    timeout=timeout,
                    force=force,
                    noWaitAfter=no_wait_after,
                    trial=trial,
                )
            )
        )

    def check(
        self,
        *,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        no_wait_after: bool = None,
        trial: bool = None
    ) -> NoneType:
        """ElementHandle.check

        This method checks the element by performing the following steps:
        1. Ensure that element is a checkbox or a radio input. If not, this method throws. If the element is already checked,
           this method returns immediately.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the element, unless `force` option is set.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to click in the center of the element.
        1. Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.
        1. Ensure that the element is now checked. If not, this method throws.

        If the element is detached from the DOM at any moment during the action, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`. Passing
        zero timeout disables this.

        Parameters
        ----------
        position : Union[{x: float, y: float}, NoneType]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the
            element.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        trial : Union[bool, NoneType]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults to
            `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.check(
                    position=position,
                    timeout=timeout,
                    force=force,
                    noWaitAfter=no_wait_after,
                    trial=trial,
                )
            )
        )

    def uncheck(
        self,
        *,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        no_wait_after: bool = None,
        trial: bool = None
    ) -> NoneType:
        """ElementHandle.uncheck

        This method checks the element by performing the following steps:
        1. Ensure that element is a checkbox or a radio input. If not, this method throws. If the element is already
           unchecked, this method returns immediately.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the element, unless `force` option is set.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to click in the center of the element.
        1. Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.
        1. Ensure that the element is now unchecked. If not, this method throws.

        If the element is detached from the DOM at any moment during the action, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`. Passing
        zero timeout disables this.

        Parameters
        ----------
        position : Union[{x: float, y: float}, NoneType]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the
            element.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        trial : Union[bool, NoneType]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults to
            `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.uncheck(
                    position=position,
                    timeout=timeout,
                    force=force,
                    noWaitAfter=no_wait_after,
                    trial=trial,
                )
            )
        )

    def bounding_box(self) -> typing.Optional[FloatRect]:
        """ElementHandle.bounding_box

        This method returns the bounding box of the element, or `null` if the element is not visible. The bounding box is
        calculated relative to the main frame viewport - which is usually the same as the browser window.

        Scrolling affects the returned bonding box, similarly to
        [Element.getBoundingClientRect](https://developer.mozilla.org/en-US/docs/Web/API/Element/getBoundingClientRect). That
        means `x` and/or `y` may be negative.

        Elements from child frames return the bounding box relative to the main frame, unlike the
        [Element.getBoundingClientRect](https://developer.mozilla.org/en-US/docs/Web/API/Element/getBoundingClientRect).

        Assuming the page is static, it is safe to use bounding box coordinates to perform input. For example, the following
        snippet should click the center of the element.

        ```py
        box = element_handle.bounding_box()
        page.mouse.click(box[\"x\"] + box[\"width\"] / 2, box[\"y\"] + box[\"height\"] / 2)
        ```

        Returns
        -------
        Union[{x: float, y: float, width: float, height: float}, NoneType]
        """

        return mapping.from_impl_nullable(self._sync(self._impl_obj.bounding_box()))

    def screenshot(
        self,
        *,
        timeout: float = None,
        type: Literal["jpeg", "png"] = None,
        path: typing.Union[str, pathlib.Path] = None,
        quality: int = None,
        omit_background: bool = None,
        animations: Literal["allow", "disabled"] = None,
        caret: Literal["hide", "initial"] = None,
        scale: Literal["css", "device"] = None,
        mask: typing.List["Locator"] = None
    ) -> bytes:
        """ElementHandle.screenshot

        This method captures a screenshot of the page, clipped to the size and position of this particular element. If the
        element is covered by other elements, it will not be actually visible on the screenshot. If the element is a scrollable
        container, only the currently scrolled content will be visible on the screenshot.

        This method waits for the [actionability](https://playwright.dev/python/docs/actionability) checks, then scrolls element into view before taking a
        screenshot. If the element is detached from DOM, the method throws an error.

        Returns the buffer with the captured screenshot.

        Parameters
        ----------
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        type : Union["jpeg", "png", NoneType]
            Specify screenshot type, defaults to `png`.
        path : Union[pathlib.Path, str, NoneType]
            The file path to save the image to. The screenshot type will be inferred from file extension. If `path` is a relative
            path, then it is resolved relative to the current working directory. If no path is provided, the image won't be saved to
            the disk.
        quality : Union[int, NoneType]
            The quality of the image, between 0-100. Not applicable to `png` images.
        omit_background : Union[bool, NoneType]
            Hides default white background and allows capturing screenshots with transparency. Not applicable to `jpeg` images.
            Defaults to `false`.
        animations : Union["allow", "disabled", NoneType]
            When set to `"disabled"`, stops CSS animations, CSS transitions and Web Animations. Animations get different treatment
            depending on their duration:
            - finite animations are fast-forwarded to completion, so they'll fire `transitionend` event.
            - infinite animations are canceled to initial state, and then played over after the screenshot.

            Defaults to `"allow"` that leaves animations untouched.
        caret : Union["hide", "initial", NoneType]
            When set to `"hide"`, screenshot will hide text caret. When set to `"initial"`, text caret behavior will not be changed.
            Defaults to `"hide"`.
        scale : Union["css", "device", NoneType]
            When set to `"css"`, screenshot will have a single pixel per each css pixel on the page. For high-dpi devices, this will
            keep screenshots small. Using `"device"` option will produce a single pixel per each device pixel, so screenhots of
            high-dpi devices will be twice as large or even larger.

            Defaults to `"device"`.
        mask : Union[List[Locator], NoneType]
            Specify locators that should be masked when the screenshot is taken. Masked elements will be overlayed with a pink box
            `#FF00FF` that completely covers its bounding box.

        Returns
        -------
        bytes
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.screenshot(
                    timeout=timeout,
                    type=type,
                    path=path,
                    quality=quality,
                    omitBackground=omit_background,
                    animations=animations,
                    caret=caret,
                    scale=scale,
                    mask=mapping.to_impl(mask),
                )
            )
        )

    def query_selector(self, selector: str) -> typing.Optional["ElementHandle"]:
        """ElementHandle.query_selector

        The method finds an element matching the specified selector in the `ElementHandle`'s subtree. See
        [Working with selectors](https://playwright.dev/python/docs/selectors) for more details. If no elements match the selector, returns `null`.

        Parameters
        ----------
        selector : str
            A selector to query for. See [working with selectors](../selectors.md) for more details.

        Returns
        -------
        Union[ElementHandle, NoneType]
        """

        return mapping.from_impl_nullable(
            self._sync(self._impl_obj.query_selector(selector=selector))
        )

    def query_selector_all(self, selector: str) -> typing.List["ElementHandle"]:
        """ElementHandle.query_selector_all

        The method finds all elements matching the specified selector in the `ElementHandle`s subtree. See
        [Working with selectors](https://playwright.dev/python/docs/selectors) for more details. If no elements match the selector, returns empty array.

        Parameters
        ----------
        selector : str
            A selector to query for. See [working with selectors](../selectors.md) for more details.

        Returns
        -------
        List[ElementHandle]
        """

        return mapping.from_impl_list(
            self._sync(self._impl_obj.query_selector_all(selector=selector))
        )

    def eval_on_selector(
        self, selector: str, expression: str, arg: typing.Any = None
    ) -> typing.Any:
        """ElementHandle.eval_on_selector

        Returns the return value of `expression`.

        The method finds an element matching the specified selector in the `ElementHandle`s subtree and passes it as a first
        argument to `expression`. See [Working with selectors](https://playwright.dev/python/docs/selectors) for more details. If no elements match the
        selector, the method throws an error.

        If `expression` returns a [Promise], then `element_handle.eval_on_selector()` would wait for the promise to resolve
        and return its value.

        Examples:

        ```py
        tweet_handle = page.query_selector(\".tweet\")
        assert tweet_handle.eval_on_selector(\".like\", \"node => node.innerText\") == \"100\"
        assert tweet_handle.eval_on_selector(\".retweets\", \"node => node.innerText\") = \"10\"
        ```

        Parameters
        ----------
        selector : str
            A selector to query for. See [working with selectors](../selectors.md) for more details.
        expression : str
            JavaScript expression to be evaluated in the browser context. If it looks like a function declaration, it is interpreted
            as a function. Otherwise, evaluated as an expression.
        arg : Union[Any, NoneType]
            Optional argument to pass to `expression`.

        Returns
        -------
        Any
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.eval_on_selector(
                    selector=selector, expression=expression, arg=mapping.to_impl(arg)
                )
            )
        )

    def eval_on_selector_all(
        self, selector: str, expression: str, arg: typing.Any = None
    ) -> typing.Any:
        """ElementHandle.eval_on_selector_all

        Returns the return value of `expression`.

        The method finds all elements matching the specified selector in the `ElementHandle`'s subtree and passes an array of
        matched elements as a first argument to `expression`. See [Working with selectors](https://playwright.dev/python/docs/selectors) for more details.

        If `expression` returns a [Promise], then `element_handle.eval_on_selector_all()` would wait for the promise to
        resolve and return its value.

        Examples:

        ```html
        <div class=\"feed\">
          <div class=\"tweet\">Hello!</div>
          <div class=\"tweet\">Hi!</div>
        </div>
        ```

        ```py
        feed_handle = page.query_selector(\".feed\")
        assert feed_handle.eval_on_selector_all(\".tweet\", \"nodes => nodes.map(n => n.innerText)\") == [\"hello!\", \"hi!\"]
        ```

        Parameters
        ----------
        selector : str
            A selector to query for. See [working with selectors](../selectors.md) for more details.
        expression : str
            JavaScript expression to be evaluated in the browser context. If it looks like a function declaration, it is interpreted
            as a function. Otherwise, evaluated as an expression.
        arg : Union[Any, NoneType]
            Optional argument to pass to `expression`.

        Returns
        -------
        Any
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.eval_on_selector_all(
                    selector=selector, expression=expression, arg=mapping.to_impl(arg)
                )
            )
        )

    def wait_for_element_state(
        self,
        state: Literal[
            "disabled", "editable", "enabled", "hidden", "stable", "visible"
        ],
        *,
        timeout: float = None
    ) -> NoneType:
        """ElementHandle.wait_for_element_state

        Returns when the element satisfies the `state`.

        Depending on the `state` parameter, this method waits for one of the [actionability](https://playwright.dev/python/docs/actionability) checks to
        pass. This method throws when the element is detached while waiting, unless waiting for the `\"hidden\"` state.
        - `\"visible\"` Wait until the element is [visible](https://playwright.dev/python/docs/actionability#visible).
        - `\"hidden\"` Wait until the element is [not visible](https://playwright.dev/python/docs/actionability#visible) or
          [not attached](https://playwright.dev/python/docs/actionability#attached). Note that waiting for hidden does not throw when the element detaches.
        - `\"stable\"` Wait until the element is both [visible](https://playwright.dev/python/docs/actionability#visible) and
          [stable](https://playwright.dev/python/docs/actionability#stable).
        - `\"enabled\"` Wait until the element is [enabled](https://playwright.dev/python/docs/actionability#enabled).
        - `\"disabled\"` Wait until the element is [not enabled](https://playwright.dev/python/docs/actionability#enabled).
        - `\"editable\"` Wait until the element is [editable](https://playwright.dev/python/docs/actionability#editable).

        If the element does not satisfy the condition for the `timeout` milliseconds, this method will throw.

        Parameters
        ----------
        state : Union["disabled", "editable", "enabled", "hidden", "stable", "visible"]
            A state to wait for, see below for more details.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.wait_for_element_state(state=state, timeout=timeout)
            )
        )

    def wait_for_selector(
        self,
        selector: str,
        *,
        state: Literal["attached", "detached", "hidden", "visible"] = None,
        timeout: float = None,
        strict: bool = None
    ) -> typing.Optional["ElementHandle"]:
        """ElementHandle.wait_for_selector

        Returns element specified by selector when it satisfies `state` option. Returns `null` if waiting for `hidden` or
        `detached`.

        Wait for the `selector` relative to the element handle to satisfy `state` option (either appear/disappear from dom, or
        become visible/hidden). If at the moment of calling the method `selector` already satisfies the condition, the method
        will return immediately. If the selector doesn't satisfy the condition for the `timeout` milliseconds, the function will
        throw.

        ```py
        page.set_content(\"<div><span></span></div>\")
        div = page.query_selector(\"div\")
        # waiting for the \"span\" selector relative to the div.
        span = div.wait_for_selector(\"span\", state=\"attached\")
        ```

        > NOTE: This method does not work across navigations, use `page.wait_for_selector()` instead.

        Parameters
        ----------
        selector : str
            A selector to query for. See [working with selectors](../selectors.md) for more details.
        state : Union["attached", "detached", "hidden", "visible", NoneType]
            Defaults to `'visible'`. Can be either:
            - `'attached'` - wait for element to be present in DOM.
            - `'detached'` - wait for element to not be present in DOM.
            - `'visible'` - wait for element to have non-empty bounding box and no `visibility:hidden`. Note that element without
              any content or with `display:none` has an empty bounding box and is not considered visible.
            - `'hidden'` - wait for element to be either detached from DOM, or have an empty bounding box or `visibility:hidden`.
              This is opposite to the `'visible'` option.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.

        Returns
        -------
        Union[ElementHandle, NoneType]
        """

        return mapping.from_impl_nullable(
            self._sync(
                self._impl_obj.wait_for_selector(
                    selector=selector, state=state, timeout=timeout, strict=strict
                )
            )
        )


mapping.register(ElementHandleImpl, ElementHandle)


class Accessibility(SyncBase):
    def snapshot(
        self, *, interesting_only: bool = None, root: "ElementHandle" = None
    ) -> typing.Optional[typing.Dict]:
        """Accessibility.snapshot

        Captures the current state of the accessibility tree. The returned object represents the root accessible node of the
        page.

        > NOTE: The Chromium accessibility tree contains nodes that go unused on most platforms and by most screen readers.
        Playwright will discard them as well for an easier to process tree, unless `interestingOnly` is set to `false`.

        An example of dumping the entire accessibility tree:

        ```py
        snapshot = page.accessibility.snapshot()
        print(snapshot)
        ```

        An example of logging the focused node's name:

        ```py
        def find_focused_node(node):
            if (node.get(\"focused\"))
                return node
            for child in (node.get(\"children\") or []):
                found_node = find_focused_node(child)
                if (found_node)
                    return found_node
            return None

        snapshot = page.accessibility.snapshot()
        node = find_focused_node(snapshot)
        if node:
            print(node[\"name\"])
        ```

        Parameters
        ----------
        interesting_only : Union[bool, NoneType]
            Prune uninteresting nodes from the tree. Defaults to `true`.
        root : Union[ElementHandle, NoneType]
            The root DOM element for the snapshot. Defaults to the whole page.

        Returns
        -------
        Union[Dict, NoneType]
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.snapshot(
                    interestingOnly=interesting_only, root=mapping.to_impl(root)
                )
            )
        )


mapping.register(AccessibilityImpl, Accessibility)


class FileChooser(SyncBase):
    @property
    def page(self) -> "Page":
        """FileChooser.page

        Returns page this file chooser belongs to.

        Returns
        -------
        Page
        """
        return mapping.from_impl(self._impl_obj.page)

    @property
    def element(self) -> "ElementHandle":
        """FileChooser.element

        Returns input element associated with this file chooser.

        Returns
        -------
        ElementHandle
        """
        return mapping.from_impl(self._impl_obj.element)

    def is_multiple(self) -> bool:
        """FileChooser.is_multiple

        Returns whether this file chooser accepts multiple files.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(self._impl_obj.is_multiple())

    def set_files(
        self,
        files: typing.Union[
            str,
            pathlib.Path,
            FilePayload,
            typing.List[typing.Union[str, pathlib.Path]],
            typing.List[FilePayload],
        ],
        *,
        timeout: float = None,
        no_wait_after: bool = None
    ) -> NoneType:
        """FileChooser.set_files

        Sets the value of the file input this chooser is associated with. If some of the `filePaths` are relative paths, then
        they are resolved relative to the current working directory. For empty array, clears the selected files.

        Parameters
        ----------
        files : Union[List[Union[pathlib.Path, str]], List[{name: str, mimeType: str, buffer: bytes}], pathlib.Path, str, {name: str, mimeType: str, buffer: bytes}]
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.set_files(
                    files=mapping.to_impl(files),
                    timeout=timeout,
                    noWaitAfter=no_wait_after,
                )
            )
        )


mapping.register(FileChooserImpl, FileChooser)


class Frame(SyncBase):
    @property
    def page(self) -> "Page":
        """Frame.page

        Returns the page containing this frame.

        Returns
        -------
        Page
        """
        return mapping.from_impl(self._impl_obj.page)

    @property
    def name(self) -> str:
        """Frame.name

        Returns frame's name attribute as specified in the tag.

        If the name is empty, returns the id attribute instead.

        > NOTE: This value is calculated once when the frame is created, and will not update if the attribute is changed later.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.name)

    @property
    def url(self) -> str:
        """Frame.url

        Returns frame's url.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.url)

    @property
    def parent_frame(self) -> typing.Optional["Frame"]:
        """Frame.parent_frame

        Parent frame, if any. Detached frames and main frames return `null`.

        Returns
        -------
        Union[Frame, NoneType]
        """
        return mapping.from_impl_nullable(self._impl_obj.parent_frame)

    @property
    def child_frames(self) -> typing.List["Frame"]:
        """Frame.child_frames

        Returns
        -------
        List[Frame]
        """
        return mapping.from_impl_list(self._impl_obj.child_frames)

    def goto(
        self,
        url: str,
        *,
        timeout: float = None,
        wait_until: Literal["commit", "domcontentloaded", "load", "networkidle"] = None,
        referer: str = None
    ) -> typing.Optional["Response"]:
        """Frame.goto

        Returns the main resource response. In case of multiple redirects, the navigation will resolve with the response of the
        last redirect.

        The method will throw an error if:
        - there's an SSL error (e.g. in case of self-signed certificates).
        - target URL is invalid.
        - the `timeout` is exceeded during navigation.
        - the remote server does not respond or is unreachable.
        - the main resource failed to load.

        The method will not throw an error when any valid HTTP status code is returned by the remote server, including 404 \"Not
        Found\" and 500 \"Internal Server Error\".  The status code for such responses can be retrieved by calling
        `response.status()`.

        > NOTE: The method either throws an error or returns a main resource response. The only exceptions are navigation to
        `about:blank` or navigation to the same URL with a different hash, which would succeed and return `null`.
        > NOTE: Headless mode doesn't support navigation to a PDF document. See the
        [upstream issue](https://bugs.chromium.org/p/chromium/issues/detail?id=761295).

        Parameters
        ----------
        url : str
            URL to navigate frame to. The url should include scheme, e.g. `https://`.
        timeout : Union[float, NoneType]
            Maximum operation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be
            changed by using the `browser_context.set_default_navigation_timeout()`,
            `browser_context.set_default_timeout()`, `page.set_default_navigation_timeout()` or
            `page.set_default_timeout()` methods.
        wait_until : Union["commit", "domcontentloaded", "load", "networkidle", NoneType]
            When to consider operation succeeded, defaults to `load`. Events can be either:
            - `'domcontentloaded'` - consider operation to be finished when the `DOMContentLoaded` event is fired.
            - `'load'` - consider operation to be finished when the `load` event is fired.
            - `'networkidle'` - consider operation to be finished when there are no network connections for at least `500` ms.
            - `'commit'` - consider operation to be finished when network response is received and the document started loading.
        referer : Union[str, NoneType]
            Referer header value. If provided it will take preference over the referer header value set by
            `page.set_extra_http_headers()`.

        Returns
        -------
        Union[Response, NoneType]
        """

        return mapping.from_impl_nullable(
            self._sync(
                self._impl_obj.goto(
                    url=url, timeout=timeout, waitUntil=wait_until, referer=referer
                )
            )
        )

    def expect_navigation(
        self,
        *,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]] = None,
        wait_until: Literal["commit", "domcontentloaded", "load", "networkidle"] = None,
        timeout: float = None
    ) -> EventContextManager["Response"]:
        """Frame.expect_navigation

        Waits for the frame navigation and returns the main resource response. In case of multiple redirects, the navigation
        will resolve with the response of the last redirect. In case of navigation to a different anchor or navigation due to
        History API usage, the navigation will resolve with `null`.

        This method waits for the frame to navigate to a new URL. It is useful for when you run code which will indirectly cause
        the frame to navigate. Consider this example:

        ```py
        with frame.expect_navigation():
            frame.click(\"a.delayed-navigation\") # clicking the link will indirectly cause a navigation
        # Resolves after navigation has finished
        ```

        > NOTE: Usage of the [History API](https://developer.mozilla.org/en-US/docs/Web/API/History_API) to change the URL is
        considered a navigation.

        Parameters
        ----------
        url : Union[Callable[[str], bool], Pattern, str, NoneType]
            A glob pattern, regex pattern or predicate receiving [URL] to match while waiting for the navigation. Note that if the
            parameter is a string without wildcard characters, the method will wait for navigation to URL that is exactly equal to
            the string.
        wait_until : Union["commit", "domcontentloaded", "load", "networkidle", NoneType]
            When to consider operation succeeded, defaults to `load`. Events can be either:
            - `'domcontentloaded'` - consider operation to be finished when the `DOMContentLoaded` event is fired.
            - `'load'` - consider operation to be finished when the `load` event is fired.
            - `'networkidle'` - consider operation to be finished when there are no network connections for at least `500` ms.
            - `'commit'` - consider operation to be finished when network response is received and the document started loading.
        timeout : Union[float, NoneType]
            Maximum operation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be
            changed by using the `browser_context.set_default_navigation_timeout()`,
            `browser_context.set_default_timeout()`, `page.set_default_navigation_timeout()` or
            `page.set_default_timeout()` methods.

        Returns
        -------
        EventContextManager[Response]
        """
        return EventContextManager(
            self,
            self._impl_obj.expect_navigation(
                url=self._wrap_handler(url), wait_until=wait_until, timeout=timeout
            ).future,
        )

    def wait_for_url(
        self,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]],
        *,
        wait_until: Literal["commit", "domcontentloaded", "load", "networkidle"] = None,
        timeout: float = None
    ) -> NoneType:
        """Frame.wait_for_url

        Waits for the frame to navigate to the given URL.

        ```py
        frame.click(\"a.delayed-navigation\") # clicking the link will indirectly cause a navigation
        frame.wait_for_url(\"**/target.html\")
        ```

        Parameters
        ----------
        url : Union[Callable[[str], bool], Pattern, str]
            A glob pattern, regex pattern or predicate receiving [URL] to match while waiting for the navigation. Note that if the
            parameter is a string without wildcard characters, the method will wait for navigation to URL that is exactly equal to
            the string.
        wait_until : Union["commit", "domcontentloaded", "load", "networkidle", NoneType]
            When to consider operation succeeded, defaults to `load`. Events can be either:
            - `'domcontentloaded'` - consider operation to be finished when the `DOMContentLoaded` event is fired.
            - `'load'` - consider operation to be finished when the `load` event is fired.
            - `'networkidle'` - consider operation to be finished when there are no network connections for at least `500` ms.
            - `'commit'` - consider operation to be finished when network response is received and the document started loading.
        timeout : Union[float, NoneType]
            Maximum operation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be
            changed by using the `browser_context.set_default_navigation_timeout()`,
            `browser_context.set_default_timeout()`, `page.set_default_navigation_timeout()` or
            `page.set_default_timeout()` methods.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.wait_for_url(
                    url=self._wrap_handler(url), wait_until=wait_until, timeout=timeout
                )
            )
        )

    def wait_for_load_state(
        self,
        state: Literal["domcontentloaded", "load", "networkidle"] = None,
        *,
        timeout: float = None
    ) -> NoneType:
        """Frame.wait_for_load_state

        Waits for the required load state to be reached.

        This returns when the frame reaches a required load state, `load` by default. The navigation must have been committed
        when this method is called. If current document has already reached the required state, resolves immediately.

        ```py
        frame.click(\"button\") # click triggers navigation.
        frame.wait_for_load_state() # the promise resolves after \"load\" event.
        ```

        Parameters
        ----------
        state : Union["domcontentloaded", "load", "networkidle", NoneType]
            Optional load state to wait for, defaults to `load`. If the state has been already reached while loading current
            document, the method resolves immediately. Can be one of:
            - `'load'` - wait for the `load` event to be fired.
            - `'domcontentloaded'` - wait for the `DOMContentLoaded` event to be fired.
            - `'networkidle'` - wait until there are no network connections for at least `500` ms.
        timeout : Union[float, NoneType]
            Maximum operation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be
            changed by using the `browser_context.set_default_navigation_timeout()`,
            `browser_context.set_default_timeout()`, `page.set_default_navigation_timeout()` or
            `page.set_default_timeout()` methods.
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.wait_for_load_state(state=state, timeout=timeout))
        )

    def frame_element(self) -> "ElementHandle":
        """Frame.frame_element

        Returns the `frame` or `iframe` element handle which corresponds to this frame.

        This is an inverse of `element_handle.content_frame()`. Note that returned handle actually belongs to the parent
        frame.

        This method throws an error if the frame has been detached before `frameElement()` returns.

        ```py
        frame_element = frame.frame_element()
        content_frame = frame_element.content_frame()
        assert frame == content_frame
        ```

        Returns
        -------
        ElementHandle
        """

        return mapping.from_impl(self._sync(self._impl_obj.frame_element()))

    def evaluate(self, expression: str, arg: typing.Any = None) -> typing.Any:
        """Frame.evaluate

        Returns the return value of `expression`.

        If the function passed to the `frame.evaluate()` returns a [Promise], then `frame.evaluate()` would wait
        for the promise to resolve and return its value.

        If the function passed to the `frame.evaluate()` returns a non-[Serializable] value, then
        `frame.evaluate()` returns `undefined`. Playwright also supports transferring some additional values that are
        not serializable by `JSON`: `-0`, `NaN`, `Infinity`, `-Infinity`.

        ```py
        result = frame.evaluate(\"([x, y]) => Promise.resolve(x * y)\", [7, 8])
        print(result) # prints \"56\"
        ```

        A string can also be passed in instead of a function.

        ```py
        print(frame.evaluate(\"1 + 2\")) # prints \"3\"
        x = 10
        print(frame.evaluate(f\"1 + {x}\")) # prints \"11\"
        ```

        `ElementHandle` instances can be passed as an argument to the `frame.evaluate()`:

        ```py
        body_handle = frame.evaluate(\"document.body\")
        html = frame.evaluate(\"([body, suffix]) => body.innerHTML + suffix\", [body_handle, \"hello\"])
        body_handle.dispose()
        ```

        Parameters
        ----------
        expression : str
            JavaScript expression to be evaluated in the browser context. If it looks like a function declaration, it is interpreted
            as a function. Otherwise, evaluated as an expression.
        arg : Union[Any, NoneType]
            Optional argument to pass to `expression`.

        Returns
        -------
        Any
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.evaluate(expression=expression, arg=mapping.to_impl(arg))
            )
        )

    def evaluate_handle(self, expression: str, arg: typing.Any = None) -> "JSHandle":
        """Frame.evaluate_handle

        Returns the return value of `expression` as a `JSHandle`.

        The only difference between `frame.evaluate()` and `frame.evaluate_handle()` is that
        `frame.evaluate_handle()` returns `JSHandle`.

        If the function, passed to the `frame.evaluate_handle()`, returns a [Promise], then
        `frame.evaluate_handle()` would wait for the promise to resolve and return its value.

        ```py
        a_window_handle = frame.evaluate_handle(\"Promise.resolve(window)\")
        a_window_handle # handle for the window object.
        ```

        A string can also be passed in instead of a function.

        ```py
        a_handle = page.evaluate_handle(\"document\") # handle for the \"document\"
        ```

        `JSHandle` instances can be passed as an argument to the `frame.evaluate_handle()`:

        ```py
        a_handle = page.evaluate_handle(\"document.body\")
        result_handle = page.evaluate_handle(\"body => body.innerHTML\", a_handle)
        print(result_handle.json_value())
        result_handle.dispose()
        ```

        Parameters
        ----------
        expression : str
            JavaScript expression to be evaluated in the browser context. If it looks like a function declaration, it is interpreted
            as a function. Otherwise, evaluated as an expression.
        arg : Union[Any, NoneType]
            Optional argument to pass to `expression`.

        Returns
        -------
        JSHandle
        """

        return mapping.from_impl(
            self._sync(
                self._impl_obj.evaluate_handle(
                    expression=expression, arg=mapping.to_impl(arg)
                )
            )
        )

    def query_selector(
        self, selector: str, *, strict: bool = None
    ) -> typing.Optional["ElementHandle"]:
        """Frame.query_selector

        Returns the ElementHandle pointing to the frame element.

        > NOTE: The use of `ElementHandle` is discouraged, use `Locator` objects and web-first assertions instead.

        The method finds an element matching the specified selector within the frame. See
        [Working with selectors](https://playwright.dev/python/docs/selectors) for more details. If no elements match the selector, returns `null`.

        Parameters
        ----------
        selector : str
            A selector to query for. See [working with selectors](../selectors.md) for more details.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.

        Returns
        -------
        Union[ElementHandle, NoneType]
        """

        return mapping.from_impl_nullable(
            self._sync(self._impl_obj.query_selector(selector=selector, strict=strict))
        )

    def query_selector_all(self, selector: str) -> typing.List["ElementHandle"]:
        """Frame.query_selector_all

        Returns the ElementHandles pointing to the frame elements.

        > NOTE: The use of `ElementHandle` is discouraged, use `Locator` objects instead.

        The method finds all elements matching the specified selector within the frame. See
        [Working with selectors](https://playwright.dev/python/docs/selectors) for more details. If no elements match the selector, returns empty array.

        Parameters
        ----------
        selector : str
            A selector to query for. See [working with selectors](../selectors.md) for more details.

        Returns
        -------
        List[ElementHandle]
        """

        return mapping.from_impl_list(
            self._sync(self._impl_obj.query_selector_all(selector=selector))
        )

    def wait_for_selector(
        self,
        selector: str,
        *,
        strict: bool = None,
        timeout: float = None,
        state: Literal["attached", "detached", "hidden", "visible"] = None
    ) -> typing.Optional["ElementHandle"]:
        """Frame.wait_for_selector

        Returns when element specified by selector satisfies `state` option. Returns `null` if waiting for `hidden` or
        `detached`.

        > NOTE: Playwright automatically waits for element to be ready before performing an action. Using `Locator` objects and
        web-first assertions make the code wait-for-selector-free.

        Wait for the `selector` to satisfy `state` option (either appear/disappear from dom, or become visible/hidden). If at
        the moment of calling the method `selector` already satisfies the condition, the method will return immediately. If the
        selector doesn't satisfy the condition for the `timeout` milliseconds, the function will throw.

        This method works across navigations:

        ```py
        from playwright.sync_api import sync_playwright

        def run(playwright):
            chromium = playwright.chromium
            browser = chromium.launch()
            page = browser.new_page()
            for current_url in [\"https://google.com\", \"https://bbc.com\"]:
                page.goto(current_url, wait_until=\"domcontentloaded\")
                element = page.main_frame.wait_for_selector(\"img\")
                print(\"Loaded image: \" + str(element.get_attribute(\"src\")))
            browser.close()

        with sync_playwright() as playwright:
            run(playwright)
        ```

        Parameters
        ----------
        selector : str
            A selector to query for. See [working with selectors](../selectors.md) for more details.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        state : Union["attached", "detached", "hidden", "visible", NoneType]
            Defaults to `'visible'`. Can be either:
            - `'attached'` - wait for element to be present in DOM.
            - `'detached'` - wait for element to not be present in DOM.
            - `'visible'` - wait for element to have non-empty bounding box and no `visibility:hidden`. Note that element without
              any content or with `display:none` has an empty bounding box and is not considered visible.
            - `'hidden'` - wait for element to be either detached from DOM, or have an empty bounding box or `visibility:hidden`.
              This is opposite to the `'visible'` option.

        Returns
        -------
        Union[ElementHandle, NoneType]
        """

        return mapping.from_impl_nullable(
            self._sync(
                self._impl_obj.wait_for_selector(
                    selector=selector, strict=strict, timeout=timeout, state=state
                )
            )
        )

    def is_checked(
        self, selector: str, *, strict: bool = None, timeout: float = None
    ) -> bool:
        """Frame.is_checked

        Returns whether the element is checked. Throws if the element is not a checkbox or radio input.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.is_checked(
                    selector=selector, strict=strict, timeout=timeout
                )
            )
        )

    def is_disabled(
        self, selector: str, *, strict: bool = None, timeout: float = None
    ) -> bool:
        """Frame.is_disabled

        Returns whether the element is disabled, the opposite of [enabled](https://playwright.dev/python/docs/actionability#enabled).

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.is_disabled(
                    selector=selector, strict=strict, timeout=timeout
                )
            )
        )

    def is_editable(
        self, selector: str, *, strict: bool = None, timeout: float = None
    ) -> bool:
        """Frame.is_editable

        Returns whether the element is [editable](https://playwright.dev/python/docs/actionability#editable).

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.is_editable(
                    selector=selector, strict=strict, timeout=timeout
                )
            )
        )

    def is_enabled(
        self, selector: str, *, strict: bool = None, timeout: float = None
    ) -> bool:
        """Frame.is_enabled

        Returns whether the element is [enabled](https://playwright.dev/python/docs/actionability#enabled).

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.is_enabled(
                    selector=selector, strict=strict, timeout=timeout
                )
            )
        )

    def is_hidden(
        self, selector: str, *, strict: bool = None, timeout: float = None
    ) -> bool:
        """Frame.is_hidden

        Returns whether the element is hidden, the opposite of [visible](https://playwright.dev/python/docs/actionability#visible).  `selector` that does not
        match any elements is considered hidden.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        timeout : Union[float, NoneType]
            **DEPRECATED** This option is ignored. `frame.is_hidden()` does not wait for the element to become hidden and
            returns immediately.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.is_hidden(
                    selector=selector, strict=strict, timeout=timeout
                )
            )
        )

    def is_visible(
        self, selector: str, *, strict: bool = None, timeout: float = None
    ) -> bool:
        """Frame.is_visible

        Returns whether the element is [visible](https://playwright.dev/python/docs/actionability#visible). `selector` that does not match any elements is
        considered not visible.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        timeout : Union[float, NoneType]
            **DEPRECATED** This option is ignored. `frame.is_visible()` does not wait for the element to become visible and
            returns immediately.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.is_visible(
                    selector=selector, strict=strict, timeout=timeout
                )
            )
        )

    def dispatch_event(
        self,
        selector: str,
        type: str,
        event_init: typing.Dict = None,
        *,
        strict: bool = None,
        timeout: float = None
    ) -> NoneType:
        """Frame.dispatch_event

        The snippet below dispatches the `click` event on the element. Regardless of the visibility state of the element,
        `click` is dispatched. This is equivalent to calling
        [element.click()](https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/click).

        ```py
        frame.dispatch_event(\"button#submit\", \"click\")
        ```

        Under the hood, it creates an instance of an event based on the given `type`, initializes it with `eventInit` properties
        and dispatches it on the element. Events are `composed`, `cancelable` and bubble by default.

        Since `eventInit` is event-specific, please refer to the events documentation for the lists of initial properties:
        - [DragEvent](https://developer.mozilla.org/en-US/docs/Web/API/DragEvent/DragEvent)
        - [FocusEvent](https://developer.mozilla.org/en-US/docs/Web/API/FocusEvent/FocusEvent)
        - [KeyboardEvent](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/KeyboardEvent)
        - [MouseEvent](https://developer.mozilla.org/en-US/docs/Web/API/MouseEvent/MouseEvent)
        - [PointerEvent](https://developer.mozilla.org/en-US/docs/Web/API/PointerEvent/PointerEvent)
        - [TouchEvent](https://developer.mozilla.org/en-US/docs/Web/API/TouchEvent/TouchEvent)
        - [Event](https://developer.mozilla.org/en-US/docs/Web/API/Event/Event)

        You can also specify `JSHandle` as the property value if you want live objects to be passed into the event:

        ```py
        # note you can only create data_transfer in chromium and firefox
        data_transfer = frame.evaluate_handle(\"new DataTransfer()\")
        frame.dispatch_event(\"#source\", \"dragstart\", { \"dataTransfer\": data_transfer })
        ```

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        type : str
            DOM event type: `"click"`, `"dragstart"`, etc.
        event_init : Union[Dict, NoneType]
            Optional event-specific initialization properties.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.dispatch_event(
                    selector=selector,
                    type=type,
                    eventInit=mapping.to_impl(event_init),
                    strict=strict,
                    timeout=timeout,
                )
            )
        )

    def eval_on_selector(
        self,
        selector: str,
        expression: str,
        arg: typing.Any = None,
        *,
        strict: bool = None
    ) -> typing.Any:
        """Frame.eval_on_selector

        Returns the return value of `expression`.

        > NOTE: This method does not wait for the element to pass actionability checks and therefore can lead to the flaky
        tests. Use `locator.evaluate()`, other `Locator` helper methods or web-first assertions instead.

        The method finds an element matching the specified selector within the frame and passes it as a first argument to
        `expression`. See [Working with selectors](https://playwright.dev/python/docs/selectors) for more details. If no elements match the selector, the
        method throws an error.

        If `expression` returns a [Promise], then `frame.eval_on_selector()` would wait for the promise to resolve and
        return its value.

        Examples:

        ```py
        search_value = frame.eval_on_selector(\"#search\", \"el => el.value\")
        preload_href = frame.eval_on_selector(\"link[rel=preload]\", \"el => el.href\")
        html = frame.eval_on_selector(\".main-container\", \"(e, suffix) => e.outerHTML + suffix\", \"hello\")
        ```

        Parameters
        ----------
        selector : str
            A selector to query for. See [working with selectors](../selectors.md) for more details.
        expression : str
            JavaScript expression to be evaluated in the browser context. If it looks like a function declaration, it is interpreted
            as a function. Otherwise, evaluated as an expression.
        arg : Union[Any, NoneType]
            Optional argument to pass to `expression`.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.

        Returns
        -------
        Any
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.eval_on_selector(
                    selector=selector,
                    expression=expression,
                    arg=mapping.to_impl(arg),
                    strict=strict,
                )
            )
        )

    def eval_on_selector_all(
        self, selector: str, expression: str, arg: typing.Any = None
    ) -> typing.Any:
        """Frame.eval_on_selector_all

        Returns the return value of `expression`.

        > NOTE: In most cases, `locator.evaluate_all()`, other `Locator` helper methods and web-first assertions do a
        better job.

        The method finds all elements matching the specified selector within the frame and passes an array of matched elements
        as a first argument to `expression`. See [Working with selectors](https://playwright.dev/python/docs/selectors) for more details.

        If `expression` returns a [Promise], then `frame.eval_on_selector_all()` would wait for the promise to resolve and
        return its value.

        Examples:

        ```py
        divs_counts = frame.eval_on_selector_all(\"div\", \"(divs, min) => divs.length >= min\", 10)
        ```

        Parameters
        ----------
        selector : str
            A selector to query for. See [working with selectors](../selectors.md) for more details.
        expression : str
            JavaScript expression to be evaluated in the browser context. If it looks like a function declaration, it is interpreted
            as a function. Otherwise, evaluated as an expression.
        arg : Union[Any, NoneType]
            Optional argument to pass to `expression`.

        Returns
        -------
        Any
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.eval_on_selector_all(
                    selector=selector, expression=expression, arg=mapping.to_impl(arg)
                )
            )
        )

    def content(self) -> str:
        """Frame.content

        Gets the full HTML contents of the frame, including the doctype.

        Returns
        -------
        str
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.content()))

    def set_content(
        self,
        html: str,
        *,
        timeout: float = None,
        wait_until: Literal["commit", "domcontentloaded", "load", "networkidle"] = None
    ) -> NoneType:
        """Frame.set_content

        Parameters
        ----------
        html : str
            HTML markup to assign to the page.
        timeout : Union[float, NoneType]
            Maximum operation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be
            changed by using the `browser_context.set_default_navigation_timeout()`,
            `browser_context.set_default_timeout()`, `page.set_default_navigation_timeout()` or
            `page.set_default_timeout()` methods.
        wait_until : Union["commit", "domcontentloaded", "load", "networkidle", NoneType]
            When to consider operation succeeded, defaults to `load`. Events can be either:
            - `'domcontentloaded'` - consider operation to be finished when the `DOMContentLoaded` event is fired.
            - `'load'` - consider operation to be finished when the `load` event is fired.
            - `'networkidle'` - consider operation to be finished when there are no network connections for at least `500` ms.
            - `'commit'` - consider operation to be finished when network response is received and the document started loading.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.set_content(
                    html=html, timeout=timeout, waitUntil=wait_until
                )
            )
        )

    def is_detached(self) -> bool:
        """Frame.is_detached

        Returns `true` if the frame has been detached, or `false` otherwise.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(self._impl_obj.is_detached())

    def add_script_tag(
        self,
        *,
        url: str = None,
        path: typing.Union[str, pathlib.Path] = None,
        content: str = None,
        type: str = None
    ) -> "ElementHandle":
        """Frame.add_script_tag

        Returns the added tag when the script's onload fires or when the script content was injected into frame.

        Adds a `<script>` tag into the page with the desired url or content.

        Parameters
        ----------
        url : Union[str, NoneType]
            URL of a script to be added.
        path : Union[pathlib.Path, str, NoneType]
            Path to the JavaScript file to be injected into frame. If `path` is a relative path, then it is resolved relative to the
            current working directory.
        content : Union[str, NoneType]
            Raw JavaScript content to be injected into frame.
        type : Union[str, NoneType]
            Script type. Use 'module' in order to load a Javascript ES6 module. See
            [script](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/script) for more details.

        Returns
        -------
        ElementHandle
        """

        return mapping.from_impl(
            self._sync(
                self._impl_obj.add_script_tag(
                    url=url, path=path, content=content, type=type
                )
            )
        )

    def add_style_tag(
        self,
        *,
        url: str = None,
        path: typing.Union[str, pathlib.Path] = None,
        content: str = None
    ) -> "ElementHandle":
        """Frame.add_style_tag

        Returns the added tag when the stylesheet's onload fires or when the CSS content was injected into frame.

        Adds a `<link rel=\"stylesheet\">` tag into the page with the desired url or a `<style type=\"text/css\">` tag with the
        content.

        Parameters
        ----------
        url : Union[str, NoneType]
            URL of the `<link>` tag.
        path : Union[pathlib.Path, str, NoneType]
            Path to the CSS file to be injected into frame. If `path` is a relative path, then it is resolved relative to the
            current working directory.
        content : Union[str, NoneType]
            Raw CSS content to be injected into frame.

        Returns
        -------
        ElementHandle
        """

        return mapping.from_impl(
            self._sync(
                self._impl_obj.add_style_tag(url=url, path=path, content=content)
            )
        )

    def click(
        self,
        selector: str,
        *,
        modifiers: typing.Optional[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: Position = None,
        delay: float = None,
        button: Literal["left", "middle", "right"] = None,
        click_count: int = None,
        timeout: float = None,
        force: bool = None,
        no_wait_after: bool = None,
        strict: bool = None,
        trial: bool = None
    ) -> NoneType:
        """Frame.click

        This method clicks an element matching `selector` by performing the following steps:
        1. Find an element matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the matched element, unless `force` option is set. If the
           element is detached during the checks, the whole action is retried.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to click in the center of the element, or the specified `position`.
        1. Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`. Passing
        zero timeout disables this.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        modifiers : Union[List[Union["Alt", "Control", "Meta", "Shift"]], NoneType]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores current
            modifiers back. If not specified, currently pressed modifiers are used.
        position : Union[{x: float, y: float}, NoneType]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the
            element.
        delay : Union[float, NoneType]
            Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        button : Union["left", "middle", "right", NoneType]
            Defaults to `left`.
        click_count : Union[int, NoneType]
            defaults to 1. See [UIEvent.detail].
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        trial : Union[bool, NoneType]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults to
            `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.click(
                    selector=selector,
                    modifiers=mapping.to_impl(modifiers),
                    position=position,
                    delay=delay,
                    button=button,
                    clickCount=click_count,
                    timeout=timeout,
                    force=force,
                    noWaitAfter=no_wait_after,
                    strict=strict,
                    trial=trial,
                )
            )
        )

    def dblclick(
        self,
        selector: str,
        *,
        modifiers: typing.Optional[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: Position = None,
        delay: float = None,
        button: Literal["left", "middle", "right"] = None,
        timeout: float = None,
        force: bool = None,
        no_wait_after: bool = None,
        strict: bool = None,
        trial: bool = None
    ) -> NoneType:
        """Frame.dblclick

        This method double clicks an element matching `selector` by performing the following steps:
        1. Find an element matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the matched element, unless `force` option is set. If the
           element is detached during the checks, the whole action is retried.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to double click in the center of the element, or the specified `position`.
        1. Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set. Note that if the
           first click of the `dblclick()` triggers a navigation event, this method will throw.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`. Passing
        zero timeout disables this.

        > NOTE: `frame.dblclick()` dispatches two `click` events and a single `dblclick` event.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        modifiers : Union[List[Union["Alt", "Control", "Meta", "Shift"]], NoneType]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores current
            modifiers back. If not specified, currently pressed modifiers are used.
        position : Union[{x: float, y: float}, NoneType]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the
            element.
        delay : Union[float, NoneType]
            Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        button : Union["left", "middle", "right", NoneType]
            Defaults to `left`.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        trial : Union[bool, NoneType]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults to
            `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.dblclick(
                    selector=selector,
                    modifiers=mapping.to_impl(modifiers),
                    position=position,
                    delay=delay,
                    button=button,
                    timeout=timeout,
                    force=force,
                    noWaitAfter=no_wait_after,
                    strict=strict,
                    trial=trial,
                )
            )
        )

    def tap(
        self,
        selector: str,
        *,
        modifiers: typing.Optional[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        no_wait_after: bool = None,
        strict: bool = None,
        trial: bool = None
    ) -> NoneType:
        """Frame.tap

        This method taps an element matching `selector` by performing the following steps:
        1. Find an element matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the matched element, unless `force` option is set. If the
           element is detached during the checks, the whole action is retried.
        1. Scroll the element into view if needed.
        1. Use `page.touchscreen` to tap the center of the element, or the specified `position`.
        1. Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`. Passing
        zero timeout disables this.

        > NOTE: `frame.tap()` requires that the `hasTouch` option of the browser context be set to true.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        modifiers : Union[List[Union["Alt", "Control", "Meta", "Shift"]], NoneType]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores current
            modifiers back. If not specified, currently pressed modifiers are used.
        position : Union[{x: float, y: float}, NoneType]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the
            element.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        trial : Union[bool, NoneType]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults to
            `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.tap(
                    selector=selector,
                    modifiers=mapping.to_impl(modifiers),
                    position=position,
                    timeout=timeout,
                    force=force,
                    noWaitAfter=no_wait_after,
                    strict=strict,
                    trial=trial,
                )
            )
        )

    def fill(
        self,
        selector: str,
        value: str,
        *,
        timeout: float = None,
        no_wait_after: bool = None,
        strict: bool = None,
        force: bool = None
    ) -> NoneType:
        """Frame.fill

        This method waits for an element matching `selector`, waits for [actionability](https://playwright.dev/python/docs/actionability) checks, focuses the
        element, fills it and triggers an `input` event after filling. Note that you can pass an empty string to clear the input
        field.

        If the target element is not an `<input>`, `<textarea>` or `[contenteditable]` element, this method throws an error.
        However, if the element is inside the `<label>` element that has an associated
        [control](https://developer.mozilla.org/en-US/docs/Web/API/HTMLLabelElement/control), the control will be filled
        instead.

        To send fine-grained keyboard events, use `frame.type()`.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        value : str
            Value to fill for the `<input>`, `<textarea>` or `[contenteditable]` element.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.fill(
                    selector=selector,
                    value=value,
                    timeout=timeout,
                    noWaitAfter=no_wait_after,
                    strict=strict,
                    force=force,
                )
            )
        )

    def locator(
        self,
        selector: str,
        *,
        has_text: typing.Union[str, typing.Pattern] = None,
        has: "Locator" = None
    ) -> "Locator":
        """Frame.locator

        The method returns an element locator that can be used to perform actions in the frame. Locator is resolved to the
        element immediately before performing an action, so a series of actions on the same locator can in fact be performed on
        different DOM elements. That would happen if the DOM structure between those actions has changed.

        [Learn more about locators](https://playwright.dev/python/docs/locators).

        Parameters
        ----------
        selector : str
            A selector to use when resolving DOM element. See [working with selectors](../selectors.md) for more details.
        has_text : Union[Pattern, str, NoneType]
            Matches elements containing specified text somewhere inside, possibly in a child or a descendant element. When passed a
            [string], matching is case-insensitive and searches for a substring. For example, `"Playwright"` matches
            `<article><div>Playwright</div></article>`.
        has : Union[Locator, NoneType]
            Matches elements containing an element that matches an inner locator. Inner locator is queried against the outer one.
            For example, `article` that has `text=Playwright` matches `<article><div>Playwright</div></article>`.

            Note that outer and inner locators must belong to the same frame. Inner locator must not contain `FrameLocator`s.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(
            self._impl_obj.locator(
                selector=selector, has_text=has_text, has=has._impl_obj if has else None
            )
        )

    def frame_locator(self, selector: str) -> "FrameLocator":
        """Frame.frame_locator

        When working with iframes, you can create a frame locator that will enter the iframe and allow selecting elements in
        that iframe. Following snippet locates element with text \"Submit\" in the iframe with id `my-frame`, like `<iframe
        id=\"my-frame\">`:

        ```py
        locator = frame.frame_locator(\"#my-iframe\").locator(\"text=Submit\")
        locator.click()
        ```

        Parameters
        ----------
        selector : str
            A selector to use when resolving DOM element. See [working with selectors](../selectors.md) for more details.

        Returns
        -------
        FrameLocator
        """

        return mapping.from_impl(self._impl_obj.frame_locator(selector=selector))

    def focus(
        self, selector: str, *, strict: bool = None, timeout: float = None
    ) -> NoneType:
        """Frame.focus

        This method fetches an element with `selector` and focuses it. If there's no element matching `selector`, the method
        waits until a matching element appears in the DOM.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.focus(selector=selector, strict=strict, timeout=timeout)
            )
        )

    def text_content(
        self, selector: str, *, strict: bool = None, timeout: float = None
    ) -> typing.Optional[str]:
        """Frame.text_content

        Returns `element.textContent`.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        Union[str, NoneType]
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.text_content(
                    selector=selector, strict=strict, timeout=timeout
                )
            )
        )

    def inner_text(
        self, selector: str, *, strict: bool = None, timeout: float = None
    ) -> str:
        """Frame.inner_text

        Returns `element.innerText`.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        str
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.inner_text(
                    selector=selector, strict=strict, timeout=timeout
                )
            )
        )

    def inner_html(
        self, selector: str, *, strict: bool = None, timeout: float = None
    ) -> str:
        """Frame.inner_html

        Returns `element.innerHTML`.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        str
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.inner_html(
                    selector=selector, strict=strict, timeout=timeout
                )
            )
        )

    def get_attribute(
        self, selector: str, name: str, *, strict: bool = None, timeout: float = None
    ) -> typing.Optional[str]:
        """Frame.get_attribute

        Returns element attribute value.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        name : str
            Attribute name to get the value for.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        Union[str, NoneType]
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.get_attribute(
                    selector=selector, name=name, strict=strict, timeout=timeout
                )
            )
        )

    def hover(
        self,
        selector: str,
        *,
        modifiers: typing.Optional[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        strict: bool = None,
        trial: bool = None
    ) -> NoneType:
        """Frame.hover

        This method hovers over an element matching `selector` by performing the following steps:
        1. Find an element matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the matched element, unless `force` option is set. If the
           element is detached during the checks, the whole action is retried.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to hover over the center of the element, or the specified `position`.
        1. Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`. Passing
        zero timeout disables this.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        modifiers : Union[List[Union["Alt", "Control", "Meta", "Shift"]], NoneType]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores current
            modifiers back. If not specified, currently pressed modifiers are used.
        position : Union[{x: float, y: float}, NoneType]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the
            element.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        trial : Union[bool, NoneType]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults to
            `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.hover(
                    selector=selector,
                    modifiers=mapping.to_impl(modifiers),
                    position=position,
                    timeout=timeout,
                    force=force,
                    strict=strict,
                    trial=trial,
                )
            )
        )

    def drag_and_drop(
        self,
        source: str,
        target: str,
        *,
        source_position: Position = None,
        target_position: Position = None,
        force: bool = None,
        no_wait_after: bool = None,
        strict: bool = None,
        timeout: float = None,
        trial: bool = None
    ) -> NoneType:
        """Frame.drag_and_drop

        Parameters
        ----------
        source : str
        target : str
        source_position : Union[{x: float, y: float}, NoneType]
            Clicks on the source element at this point relative to the top-left corner of the element's padding box. If not
            specified, some visible point of the element is used.
        target_position : Union[{x: float, y: float}, NoneType]
            Drops on the target element at this point relative to the top-left corner of the element's padding box. If not
            specified, some visible point of the element is used.
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        trial : Union[bool, NoneType]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults to
            `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.drag_and_drop(
                    source=source,
                    target=target,
                    sourcePosition=source_position,
                    targetPosition=target_position,
                    force=force,
                    noWaitAfter=no_wait_after,
                    strict=strict,
                    timeout=timeout,
                    trial=trial,
                )
            )
        )

    def select_option(
        self,
        selector: str,
        value: typing.Union[str, typing.List[str]] = None,
        *,
        index: typing.Union[int, typing.List[int]] = None,
        label: typing.Union[str, typing.List[str]] = None,
        element: typing.Union["ElementHandle", typing.List["ElementHandle"]] = None,
        timeout: float = None,
        no_wait_after: bool = None,
        strict: bool = None,
        force: bool = None
    ) -> typing.List[str]:
        """Frame.select_option

        This method waits for an element matching `selector`, waits for [actionability](https://playwright.dev/python/docs/actionability) checks, waits until
        all specified options are present in the `<select>` element and selects these options.

        If the target element is not a `<select>` element, this method throws an error. However, if the element is inside the
        `<label>` element that has an associated
        [control](https://developer.mozilla.org/en-US/docs/Web/API/HTMLLabelElement/control), the control will be used instead.

        Returns the array of option values that have been successfully selected.

        Triggers a `change` and `input` event once all the provided options have been selected.

        ```py
        # single selection matching the value
        frame.select_option(\"select#colors\", \"blue\")
        # single selection matching both the label
        frame.select_option(\"select#colors\", label=\"blue\")
        # multiple selection
        frame.select_option(\"select#colors\", value=[\"red\", \"green\", \"blue\"])
        ```

        Parameters
        ----------
        selector : str
            A selector to query for. See [working with selectors](../selectors.md) for more details.
        value : Union[List[str], str, NoneType]
            Options to select by value. If the `<select>` has the `multiple` attribute, all given options are selected, otherwise
            only the first option matching one of the passed options is selected. Optional.
        index : Union[List[int], int, NoneType]
            Options to select by index. Optional.
        label : Union[List[str], str, NoneType]
            Options to select by label. If the `<select>` has the `multiple` attribute, all given options are selected, otherwise
            only the first option matching one of the passed options is selected. Optional.
        element : Union[ElementHandle, List[ElementHandle], NoneType]
            Option elements to select. Optional.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.

        Returns
        -------
        List[str]
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.select_option(
                    selector=selector,
                    value=mapping.to_impl(value),
                    index=mapping.to_impl(index),
                    label=mapping.to_impl(label),
                    element=mapping.to_impl(element),
                    timeout=timeout,
                    noWaitAfter=no_wait_after,
                    strict=strict,
                    force=force,
                )
            )
        )

    def input_value(
        self, selector: str, *, strict: bool = None, timeout: float = None
    ) -> str:
        """Frame.input_value

        Returns `input.value` for the selected `<input>` or `<textarea>` or `<select>` element.

        Throws for non-input elements. However, if the element is inside the `<label>` element that has an associated
        [control](https://developer.mozilla.org/en-US/docs/Web/API/HTMLLabelElement/control), returns the value of the control.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        str
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.input_value(
                    selector=selector, strict=strict, timeout=timeout
                )
            )
        )

    def set_input_files(
        self,
        selector: str,
        files: typing.Union[
            str,
            pathlib.Path,
            FilePayload,
            typing.List[typing.Union[str, pathlib.Path]],
            typing.List[FilePayload],
        ],
        *,
        strict: bool = None,
        timeout: float = None,
        no_wait_after: bool = None
    ) -> NoneType:
        """Frame.set_input_files

        Sets the value of the file input to these file paths or files. If some of the `filePaths` are relative paths, then they
        are resolved relative to the current working directory. For empty array, clears the selected files.

        This method expects `selector` to point to an
        [input element](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/input). However, if the element is inside the
        `<label>` element that has an associated
        [control](https://developer.mozilla.org/en-US/docs/Web/API/HTMLLabelElement/control), targets the control instead.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        files : Union[List[Union[pathlib.Path, str]], List[{name: str, mimeType: str, buffer: bytes}], pathlib.Path, str, {name: str, mimeType: str, buffer: bytes}]
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.set_input_files(
                    selector=selector,
                    files=mapping.to_impl(files),
                    strict=strict,
                    timeout=timeout,
                    noWaitAfter=no_wait_after,
                )
            )
        )

    def type(
        self,
        selector: str,
        text: str,
        *,
        delay: float = None,
        strict: bool = None,
        timeout: float = None,
        no_wait_after: bool = None
    ) -> NoneType:
        """Frame.type

        Sends a `keydown`, `keypress`/`input`, and `keyup` event for each character in the text. `frame.type` can be used to
        send fine-grained keyboard events. To fill values in form fields, use `frame.fill()`.

        To press a special key, like `Control` or `ArrowDown`, use `keyboard.press()`.

        ```py
        frame.type(\"#mytextarea\", \"hello\") # types instantly
        frame.type(\"#mytextarea\", \"world\", delay=100) # types slower, like a user
        ```

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        text : str
            A text to type into a focused element.
        delay : Union[float, NoneType]
            Time to wait between key presses in milliseconds. Defaults to 0.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.type(
                    selector=selector,
                    text=text,
                    delay=delay,
                    strict=strict,
                    timeout=timeout,
                    noWaitAfter=no_wait_after,
                )
            )
        )

    def press(
        self,
        selector: str,
        key: str,
        *,
        delay: float = None,
        strict: bool = None,
        timeout: float = None,
        no_wait_after: bool = None
    ) -> NoneType:
        """Frame.press

        `key` can specify the intended [keyboardEvent.key](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/key)
        value or a single character to generate the text for. A superset of the `key` values can be found
        [here](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/key/Key_Values). Examples of the keys are:

        `F1` - `F12`, `Digit0`- `Digit9`, `KeyA`- `KeyZ`, `Backquote`, `Minus`, `Equal`, `Backslash`, `Backspace`, `Tab`,
        `Delete`, `Escape`, `ArrowDown`, `End`, `Enter`, `Home`, `Insert`, `PageDown`, `PageUp`, `ArrowRight`, `ArrowUp`, etc.

        Following modification shortcuts are also supported: `Shift`, `Control`, `Alt`, `Meta`, `ShiftLeft`.

        Holding down `Shift` will type the text that corresponds to the `key` in the upper case.

        If `key` is a single character, it is case-sensitive, so the values `a` and `A` will generate different respective
        texts.

        Shortcuts such as `key: \"Control+o\"` or `key: \"Control+Shift+T\"` are supported as well. When specified with the
        modifier, modifier is pressed and being held while the subsequent key is being pressed.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        key : str
            Name of the key to press or a character to generate, such as `ArrowLeft` or `a`.
        delay : Union[float, NoneType]
            Time to wait between `keydown` and `keyup` in milliseconds. Defaults to 0.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.press(
                    selector=selector,
                    key=key,
                    delay=delay,
                    strict=strict,
                    timeout=timeout,
                    noWaitAfter=no_wait_after,
                )
            )
        )

    def check(
        self,
        selector: str,
        *,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        no_wait_after: bool = None,
        strict: bool = None,
        trial: bool = None
    ) -> NoneType:
        """Frame.check

        This method checks an element matching `selector` by performing the following steps:
        1. Find an element matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        1. Ensure that matched element is a checkbox or a radio input. If not, this method throws. If the element is already
           checked, this method returns immediately.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the matched element, unless `force` option is set. If the
           element is detached during the checks, the whole action is retried.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to click in the center of the element.
        1. Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.
        1. Ensure that the element is now checked. If not, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`. Passing
        zero timeout disables this.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        position : Union[{x: float, y: float}, NoneType]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the
            element.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        trial : Union[bool, NoneType]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults to
            `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.check(
                    selector=selector,
                    position=position,
                    timeout=timeout,
                    force=force,
                    noWaitAfter=no_wait_after,
                    strict=strict,
                    trial=trial,
                )
            )
        )

    def uncheck(
        self,
        selector: str,
        *,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        no_wait_after: bool = None,
        strict: bool = None,
        trial: bool = None
    ) -> NoneType:
        """Frame.uncheck

        This method checks an element matching `selector` by performing the following steps:
        1. Find an element matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        1. Ensure that matched element is a checkbox or a radio input. If not, this method throws. If the element is already
           unchecked, this method returns immediately.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the matched element, unless `force` option is set. If the
           element is detached during the checks, the whole action is retried.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to click in the center of the element.
        1. Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.
        1. Ensure that the element is now unchecked. If not, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`. Passing
        zero timeout disables this.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        position : Union[{x: float, y: float}, NoneType]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the
            element.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        trial : Union[bool, NoneType]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults to
            `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.uncheck(
                    selector=selector,
                    position=position,
                    timeout=timeout,
                    force=force,
                    noWaitAfter=no_wait_after,
                    strict=strict,
                    trial=trial,
                )
            )
        )

    def wait_for_timeout(self, timeout: float) -> NoneType:
        """Frame.wait_for_timeout

        Waits for the given `timeout` in milliseconds.

        Note that `frame.waitForTimeout()` should only be used for debugging. Tests using the timer in production are going to
        be flaky. Use signals such as network events, selectors becoming visible and others instead.

        Parameters
        ----------
        timeout : float
            A timeout to wait for
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.wait_for_timeout(timeout=timeout))
        )

    def wait_for_function(
        self,
        expression: str,
        *,
        arg: typing.Any = None,
        timeout: float = None,
        polling: typing.Union[float, Literal["raf"]] = None
    ) -> "JSHandle":
        """Frame.wait_for_function

        Returns when the `expression` returns a truthy value, returns that value.

        The `frame.wait_for_function()` can be used to observe viewport size change:

        ```py
        from playwright.sync_api import sync_playwright

        def run(playwright):
            webkit = playwright.webkit
            browser = webkit.launch()
            page = browser.new_page()
            page.evaluate(\"window.x = 0; setTimeout(() => { window.x = 100 }, 1000);\")
            page.main_frame.wait_for_function(\"() => window.x > 0\")
            browser.close()

        with sync_playwright() as playwright:
            run(playwright)
        ```

        To pass an argument to the predicate of `frame.waitForFunction` function:

        ```py
        selector = \".foo\"
        frame.wait_for_function(\"selector => !!document.querySelector(selector)\", selector)
        ```

        Parameters
        ----------
        expression : str
            JavaScript expression to be evaluated in the browser context. If it looks like a function declaration, it is interpreted
            as a function. Otherwise, evaluated as an expression.
        arg : Union[Any, NoneType]
            Optional argument to pass to `expression`.
        timeout : Union[float, NoneType]
            maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default
            value can be changed by using the `browser_context.set_default_timeout()`.
        polling : Union["raf", float, NoneType]
            If `polling` is `'raf'`, then `expression` is constantly executed in `requestAnimationFrame` callback. If `polling` is a
            number, then it is treated as an interval in milliseconds at which the function would be executed. Defaults to `raf`.

        Returns
        -------
        JSHandle
        """

        return mapping.from_impl(
            self._sync(
                self._impl_obj.wait_for_function(
                    expression=expression,
                    arg=mapping.to_impl(arg),
                    timeout=timeout,
                    polling=polling,
                )
            )
        )

    def title(self) -> str:
        """Frame.title

        Returns the page title.

        Returns
        -------
        str
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.title()))

    def set_checked(
        self,
        selector: str,
        checked: bool,
        *,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        no_wait_after: bool = None,
        strict: bool = None,
        trial: bool = None
    ) -> NoneType:
        """Frame.set_checked

        This method checks or unchecks an element matching `selector` by performing the following steps:
        1. Find an element matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        1. Ensure that matched element is a checkbox or a radio input. If not, this method throws.
        1. If the element already has the right checked state, this method returns immediately.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the matched element, unless `force` option is set. If the
           element is detached during the checks, the whole action is retried.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to click in the center of the element.
        1. Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.
        1. Ensure that the element is now checked or unchecked. If not, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`. Passing
        zero timeout disables this.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        checked : bool
            Whether to check or uncheck the checkbox.
        position : Union[{x: float, y: float}, NoneType]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the
            element.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        trial : Union[bool, NoneType]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults to
            `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.set_checked(
                    selector=selector,
                    checked=checked,
                    position=position,
                    timeout=timeout,
                    force=force,
                    noWaitAfter=no_wait_after,
                    strict=strict,
                    trial=trial,
                )
            )
        )


mapping.register(FrameImpl, Frame)


class FrameLocator(SyncBase):
    @property
    def first(self) -> "FrameLocator":
        """FrameLocator.first

        Returns locator to the first matching frame.

        Returns
        -------
        FrameLocator
        """
        return mapping.from_impl(self._impl_obj.first)

    @property
    def last(self) -> "FrameLocator":
        """FrameLocator.last

        Returns locator to the last matching frame.

        Returns
        -------
        FrameLocator
        """
        return mapping.from_impl(self._impl_obj.last)

    def locator(
        self,
        selector: str,
        *,
        has_text: typing.Union[str, typing.Pattern] = None,
        has: "Locator" = None
    ) -> "Locator":
        """FrameLocator.locator

        The method finds an element matching the specified selector in the FrameLocator's subtree.

        Parameters
        ----------
        selector : str
            A selector to use when resolving DOM element. See [working with selectors](../selectors.md) for more details.
        has_text : Union[Pattern, str, NoneType]
            Matches elements containing specified text somewhere inside, possibly in a child or a descendant element. When passed a
            [string], matching is case-insensitive and searches for a substring. For example, `"Playwright"` matches
            `<article><div>Playwright</div></article>`.
        has : Union[Locator, NoneType]
            Matches elements containing an element that matches an inner locator. Inner locator is queried against the outer one.
            For example, `article` that has `text=Playwright` matches `<article><div>Playwright</div></article>`.

            Note that outer and inner locators must belong to the same frame. Inner locator must not contain `FrameLocator`s.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(
            self._impl_obj.locator(
                selector=selector, has_text=has_text, has=has._impl_obj if has else None
            )
        )

    def frame_locator(self, selector: str) -> "FrameLocator":
        """FrameLocator.frame_locator

        When working with iframes, you can create a frame locator that will enter the iframe and allow selecting elements in
        that iframe.

        Parameters
        ----------
        selector : str
            A selector to use when resolving DOM element. See [working with selectors](../selectors.md) for more details.

        Returns
        -------
        FrameLocator
        """

        return mapping.from_impl(self._impl_obj.frame_locator(selector=selector))

    def nth(self, index: int) -> "FrameLocator":
        """FrameLocator.nth

        Returns locator to the n-th matching frame. It's zero based, `nth(0)` selects the first frame.

        Parameters
        ----------
        index : int

        Returns
        -------
        FrameLocator
        """

        return mapping.from_impl(self._impl_obj.nth(index=index))


mapping.register(FrameLocatorImpl, FrameLocator)


class Worker(SyncBase):
    def on(
        self, event: Literal["close"], f: typing.Callable[["Worker"], "None"]
    ) -> None:
        """
        Emitted when this dedicated [WebWorker](https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API) is terminated."""
        return super().on(event=event, f=f)

    def once(
        self, event: Literal["close"], f: typing.Callable[["Worker"], "None"]
    ) -> None:
        """
        Emitted when this dedicated [WebWorker](https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API) is terminated."""
        return super().once(event=event, f=f)

    @property
    def url(self) -> str:
        """Worker.url

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.url)

    def evaluate(self, expression: str, arg: typing.Any = None) -> typing.Any:
        """Worker.evaluate

        Returns the return value of `expression`.

        If the function passed to the `worker.evaluate()` returns a [Promise], then `worker.evaluate()` would
        wait for the promise to resolve and return its value.

        If the function passed to the `worker.evaluate()` returns a non-[Serializable] value, then
        `worker.evaluate()` returns `undefined`. Playwright also supports transferring some additional values that are
        not serializable by `JSON`: `-0`, `NaN`, `Infinity`, `-Infinity`.

        Parameters
        ----------
        expression : str
            JavaScript expression to be evaluated in the browser context. If it looks like a function declaration, it is interpreted
            as a function. Otherwise, evaluated as an expression.
        arg : Union[Any, NoneType]
            Optional argument to pass to `expression`.

        Returns
        -------
        Any
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.evaluate(expression=expression, arg=mapping.to_impl(arg))
            )
        )

    def evaluate_handle(self, expression: str, arg: typing.Any = None) -> "JSHandle":
        """Worker.evaluate_handle

        Returns the return value of `expression` as a `JSHandle`.

        The only difference between `worker.evaluate()` and `worker.evaluate_handle()` is that
        `worker.evaluate_handle()` returns `JSHandle`.

        If the function passed to the `worker.evaluate_handle()` returns a [Promise], then
        `worker.evaluate_handle()` would wait for the promise to resolve and return its value.

        Parameters
        ----------
        expression : str
            JavaScript expression to be evaluated in the browser context. If it looks like a function declaration, it is interpreted
            as a function. Otherwise, evaluated as an expression.
        arg : Union[Any, NoneType]
            Optional argument to pass to `expression`.

        Returns
        -------
        JSHandle
        """

        return mapping.from_impl(
            self._sync(
                self._impl_obj.evaluate_handle(
                    expression=expression, arg=mapping.to_impl(arg)
                )
            )
        )


mapping.register(WorkerImpl, Worker)


class Selectors(SyncBase):
    def register(
        self,
        name: str,
        script: str = None,
        *,
        path: typing.Union[str, pathlib.Path] = None,
        content_script: bool = None
    ) -> NoneType:
        """Selectors.register

        An example of registering selector engine that queries elements based on a tag name:

        ```py
        from playwright.sync_api import sync_playwright

        def run(playwright):
            tag_selector = \"\"\"
              {
                  // Returns the first element matching given selector in the root's subtree.
                  query(root, selector) {
                      return root.querySelector(selector);
                  },
                  // Returns all elements matching given selector in the root's subtree.
                  queryAll(root, selector) {
                      return Array.from(root.querySelectorAll(selector));
                  }
              }\"\"\"

            # Register the engine. Selectors will be prefixed with \"tag=\".
            playwright.selectors.register(\"tag\", tag_selector)
            browser = playwright.chromium.launch()
            page = browser.new_page()
            page.set_content('<div><button>Click me</button></div>')

            # Use the selector prefixed with its name.
            button = page.locator('tag=button')
            # Combine it with other selector engines.
            page.click('tag=div >> text=\"Click me\"')
            # Can use it in any methods supporting selectors.
            button_count = page.locator('tag=button').count()
            print(button_count)
            browser.close()

        with sync_playwright() as playwright:
            run(playwright)
        ```

        Parameters
        ----------
        name : str
            Name that is used in selectors as a prefix, e.g. `{name: 'foo'}` enables `foo=myselectorbody` selectors. May only
            contain `[a-zA-Z0-9_]` characters.
        script : Union[str, NoneType]
            Raw script content.
        path : Union[pathlib.Path, str, NoneType]
            Path to the JavaScript file. If `path` is a relative path, then it is resolved relative to the current working
            directory.
        content_script : Union[bool, NoneType]
            Whether to run this selector engine in isolated JavaScript environment. This environment has access to the same DOM, but
            not any JavaScript objects from the frame's scripts. Defaults to `false`. Note that running as a content script is not
            guaranteed when this engine is used together with other registered engines.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.register(
                    name=name, script=script, path=path, contentScript=content_script
                )
            )
        )


mapping.register(SelectorsImpl, Selectors)


class ConsoleMessage(SyncBase):
    @property
    def type(self) -> str:
        """ConsoleMessage.type

        One of the following values: `'log'`, `'debug'`, `'info'`, `'error'`, `'warning'`, `'dir'`, `'dirxml'`, `'table'`,
        `'trace'`, `'clear'`, `'startGroup'`, `'startGroupCollapsed'`, `'endGroup'`, `'assert'`, `'profile'`, `'profileEnd'`,
        `'count'`, `'timeEnd'`.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.type)

    @property
    def text(self) -> str:
        """ConsoleMessage.text

        The text of the console message.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.text)

    @property
    def args(self) -> typing.List["JSHandle"]:
        """ConsoleMessage.args

        List of arguments passed to a `console` function call. See also `page.on('console')`.

        Returns
        -------
        List[JSHandle]
        """
        return mapping.from_impl_list(self._impl_obj.args)

    @property
    def location(self) -> SourceLocation:
        """ConsoleMessage.location

        Returns
        -------
        {url: str, lineNumber: int, columnNumber: int}
        """
        return mapping.from_impl(self._impl_obj.location)


mapping.register(ConsoleMessageImpl, ConsoleMessage)


class Dialog(SyncBase):
    @property
    def type(self) -> str:
        """Dialog.type

        Returns dialog's type, can be one of `alert`, `beforeunload`, `confirm` or `prompt`.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.type)

    @property
    def message(self) -> str:
        """Dialog.message

        A message displayed in the dialog.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.message)

    @property
    def default_value(self) -> str:
        """Dialog.default_value

        If dialog is prompt, returns default prompt value. Otherwise, returns empty string.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.default_value)

    def accept(self, prompt_text: str = None) -> NoneType:
        """Dialog.accept

        Returns when the dialog has been accepted.

        Parameters
        ----------
        prompt_text : Union[str, NoneType]
            A text to enter in prompt. Does not cause any effects if the dialog's `type` is not prompt. Optional.
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.accept(promptText=prompt_text))
        )

    def dismiss(self) -> NoneType:
        """Dialog.dismiss

        Returns when the dialog has been dismissed.
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.dismiss()))


mapping.register(DialogImpl, Dialog)


class Download(SyncBase):
    @property
    def page(self) -> "Page":
        """Download.page

        Get the page that the download belongs to.

        Returns
        -------
        Page
        """
        return mapping.from_impl(self._impl_obj.page)

    @property
    def url(self) -> str:
        """Download.url

        Returns downloaded url.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.url)

    @property
    def suggested_filename(self) -> str:
        """Download.suggested_filename

        Returns suggested filename for this download. It is typically computed by the browser from the
        [`Content-Disposition`](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Disposition) response header
        or the `download` attribute. See the spec on [whatwg](https://html.spec.whatwg.org/#downloading-resources). Different
        browsers can use different logic for computing it.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.suggested_filename)

    def delete(self) -> NoneType:
        """Download.delete

        Deletes the downloaded file. Will wait for the download to finish if necessary.
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.delete()))

    def failure(self) -> typing.Optional[str]:
        """Download.failure

        Returns download error if any. Will wait for the download to finish if necessary.

        Returns
        -------
        Union[str, NoneType]
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.failure()))

    def path(self) -> typing.Optional[pathlib.Path]:
        """Download.path

        Returns path to the downloaded file in case of successful download. The method will wait for the download to finish if
        necessary. The method throws when connected remotely.

        Note that the download's file name is a random GUID, use `download.suggested_filename()` to get suggested file
        name.

        Returns
        -------
        Union[pathlib.Path, NoneType]
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.path()))

    def save_as(self, path: typing.Union[str, pathlib.Path]) -> NoneType:
        """Download.save_as

        Copy the download to a user-specified path. It is safe to call this method while the download is still in progress. Will
        wait for the download to finish if necessary.

        Parameters
        ----------
        path : Union[pathlib.Path, str]
            Path where the download should be copied.
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.save_as(path=path)))

    def cancel(self) -> NoneType:
        """Download.cancel

        Cancels a download. Will not fail if the download is already finished or canceled. Upon successful cancellations,
        `download.failure()` would resolve to `'canceled'`.
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.cancel()))


mapping.register(DownloadImpl, Download)


class Video(SyncBase):
    def path(self) -> pathlib.Path:
        """Video.path

        Returns the file system path this video will be recorded to. The video is guaranteed to be written to the filesystem
        upon closing the browser context. This method throws when connected remotely.

        Returns
        -------
        pathlib.Path
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.path()))

    def save_as(self, path: typing.Union[str, pathlib.Path]) -> NoneType:
        """Video.save_as

        Saves the video to a user-specified path. It is safe to call this method while the video is still in progress, or after
        the page has closed. This method waits until the page is closed and the video is fully saved.

        Parameters
        ----------
        path : Union[pathlib.Path, str]
            Path where the video should be saved.
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.save_as(path=path)))

    def delete(self) -> NoneType:
        """Video.delete

        Deletes the video file. Will wait for the video to finish if necessary.
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.delete()))


mapping.register(VideoImpl, Video)


class Page(SyncContextManager):
    @typing.overload
    def on(self, event: Literal["close"], f: typing.Callable[["Page"], "None"]) -> None:
        """
        Emitted when the page closes."""

    @typing.overload
    def on(
        self, event: Literal["console"], f: typing.Callable[["ConsoleMessage"], "None"]
    ) -> None:
        """
        Emitted when JavaScript within the page calls one of console API methods, e.g. `console.log` or `console.dir`. Also
        emitted if the page throws an error or a warning.

        The arguments passed into `console.log` appear as arguments on the event handler.

        An example of handling `console` event:

        ```py
        def print_args(msg):
            for arg in msg.args:
                print(arg.json_value())

        page.on(\"console\", print_args)
        page.evaluate(\"console.log('hello', 5, {foo: 'bar'})\")
        ```"""

    @typing.overload
    def on(self, event: Literal["crash"], f: typing.Callable[["Page"], "None"]) -> None:
        """
        Emitted when the page crashes. Browser pages might crash if they try to allocate too much memory. When the page crashes,
        ongoing and subsequent operations will throw.

        The most common way to deal with crashes is to catch an exception:

        ```py
        try:
            # crash might happen during a click.
            page.click(\"button\")
            # or while waiting for an event.
            page.wait_for_event(\"popup\")
        except Error as e:
            # when the page crashes, exception message contains \"crash\".
        ```"""

    @typing.overload
    def on(
        self, event: Literal["dialog"], f: typing.Callable[["Dialog"], "None"]
    ) -> None:
        """
        Emitted when a JavaScript dialog appears, such as `alert`, `prompt`, `confirm` or `beforeunload`. Listener **must**
        either `dialog.accept()` or `dialog.dismiss()` the dialog - otherwise the page will
        [freeze](https://developer.mozilla.org/en-US/docs/Web/JavaScript/EventLoop#never_blocking) waiting for the dialog, and
        actions like click will never finish.

        ```python
        page.on(\"dialog\", lambda dialog: dialog.accept())
        ```

        > NOTE: When no `page.on('dialog')` listeners are present, all dialogs are automatically dismissed."""

    @typing.overload
    def on(
        self, event: Literal["domcontentloaded"], f: typing.Callable[["Page"], "None"]
    ) -> None:
        """
        Emitted when the JavaScript [`DOMContentLoaded`](https://developer.mozilla.org/en-US/docs/Web/Events/DOMContentLoaded)
        event is dispatched."""

    @typing.overload
    def on(
        self, event: Literal["download"], f: typing.Callable[["Download"], "None"]
    ) -> None:
        """
        Emitted when attachment download started. User can access basic file operations on downloaded content via the passed
        `Download` instance."""

    @typing.overload
    def on(
        self, event: Literal["filechooser"], f: typing.Callable[["FileChooser"], "None"]
    ) -> None:
        """
        Emitted when a file chooser is supposed to appear, such as after clicking the  `<input type=file>`. Playwright can
        respond to it via setting the input files using `file_chooser.set_files()` that can be uploaded after that.

        ```py
        page.on(\"filechooser\", lambda file_chooser: file_chooser.set_files(\"/tmp/myfile.pdf\"))
        ```"""

    @typing.overload
    def on(
        self, event: Literal["frameattached"], f: typing.Callable[["Frame"], "None"]
    ) -> None:
        """
        Emitted when a frame is attached."""

    @typing.overload
    def on(
        self, event: Literal["framedetached"], f: typing.Callable[["Frame"], "None"]
    ) -> None:
        """
        Emitted when a frame is detached."""

    @typing.overload
    def on(
        self, event: Literal["framenavigated"], f: typing.Callable[["Frame"], "None"]
    ) -> None:
        """
        Emitted when a frame is navigated to a new url."""

    @typing.overload
    def on(self, event: Literal["load"], f: typing.Callable[["Page"], "None"]) -> None:
        """
        Emitted when the JavaScript [`load`](https://developer.mozilla.org/en-US/docs/Web/Events/load) event is dispatched."""

    @typing.overload
    def on(
        self, event: Literal["pageerror"], f: typing.Callable[["Error"], "None"]
    ) -> None:
        """
        Emitted when an uncaught exception happens within the page.

        ```py
        # Log all uncaught errors to the terminal
        page.on(\"pageerror\", lambda exc: print(f\"uncaught exception: {exc}\"))

        # Navigate to a page with an exception.
        page.goto(\"data:text/html,<script>throw new Error('test')</script>\")
        ```"""

    @typing.overload
    def on(self, event: Literal["popup"], f: typing.Callable[["Page"], "None"]) -> None:
        """
        Emitted when the page opens a new tab or window. This event is emitted in addition to the
        `browser_context.on('page')`, but only for popups relevant to this page.

        The earliest moment that page is available is when it has navigated to the initial url. For example, when opening a
        popup with `window.open('http://example.com')`, this event will fire when the network request to \"http://example.com\" is
        done and its response has started loading in the popup.

        ```py
        with page.expect_event(\"popup\") as page_info:
            page.evaluate(\"window.open('https://example.com')\")
        popup = page_info.value
        print(popup.evaluate(\"location.href\"))
        ```

        > NOTE: Use `page.wait_for_load_state()` to wait until the page gets to a particular state (you should not need it
        in most cases)."""

    @typing.overload
    def on(
        self, event: Literal["request"], f: typing.Callable[["Request"], "None"]
    ) -> None:
        """
        Emitted when a page issues a request. The [request] object is read-only. In order to intercept and mutate requests, see
        `page.route()` or `browser_context.route()`."""

    @typing.overload
    def on(
        self, event: Literal["requestfailed"], f: typing.Callable[["Request"], "None"]
    ) -> None:
        """
        Emitted when a request fails, for example by timing out.

        ```python
        page.on(\"requestfailed\", lambda request: print(request.url + \" \" + request.failure.error_text))
        ```

        > NOTE: HTTP Error responses, such as 404 or 503, are still successful responses from HTTP standpoint, so request will
        complete with `page.on('request_finished')` event and not with `page.on('request_failed')`. A request will only be
        considered failed when the client cannot get an HTTP response from the server, e.g. due to network error
        net::ERR_FAILED."""

    @typing.overload
    def on(
        self, event: Literal["requestfinished"], f: typing.Callable[["Request"], "None"]
    ) -> None:
        """
        Emitted when a request finishes successfully after downloading the response body. For a successful response, the
        sequence of events is `request`, `response` and `requestfinished`."""

    @typing.overload
    def on(
        self, event: Literal["response"], f: typing.Callable[["Response"], "None"]
    ) -> None:
        """
        Emitted when [response] status and headers are received for a request. For a successful response, the sequence of events
        is `request`, `response` and `requestfinished`."""

    @typing.overload
    def on(
        self, event: Literal["websocket"], f: typing.Callable[["WebSocket"], "None"]
    ) -> None:
        """
        Emitted when `WebSocket` request is sent."""

    @typing.overload
    def on(
        self, event: Literal["worker"], f: typing.Callable[["Worker"], "None"]
    ) -> None:
        """
        Emitted when a dedicated [WebWorker](https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API) is spawned by the
        page."""

    def on(self, event: str, f: typing.Callable[..., None]) -> None:
        return super().on(event=event, f=f)

    @typing.overload
    def once(
        self, event: Literal["close"], f: typing.Callable[["Page"], "None"]
    ) -> None:
        """
        Emitted when the page closes."""

    @typing.overload
    def once(
        self, event: Literal["console"], f: typing.Callable[["ConsoleMessage"], "None"]
    ) -> None:
        """
        Emitted when JavaScript within the page calls one of console API methods, e.g. `console.log` or `console.dir`. Also
        emitted if the page throws an error or a warning.

        The arguments passed into `console.log` appear as arguments on the event handler.

        An example of handling `console` event:

        ```py
        def print_args(msg):
            for arg in msg.args:
                print(arg.json_value())

        page.on(\"console\", print_args)
        page.evaluate(\"console.log('hello', 5, {foo: 'bar'})\")
        ```"""

    @typing.overload
    def once(
        self, event: Literal["crash"], f: typing.Callable[["Page"], "None"]
    ) -> None:
        """
        Emitted when the page crashes. Browser pages might crash if they try to allocate too much memory. When the page crashes,
        ongoing and subsequent operations will throw.

        The most common way to deal with crashes is to catch an exception:

        ```py
        try:
            # crash might happen during a click.
            page.click(\"button\")
            # or while waiting for an event.
            page.wait_for_event(\"popup\")
        except Error as e:
            # when the page crashes, exception message contains \"crash\".
        ```"""

    @typing.overload
    def once(
        self, event: Literal["dialog"], f: typing.Callable[["Dialog"], "None"]
    ) -> None:
        """
        Emitted when a JavaScript dialog appears, such as `alert`, `prompt`, `confirm` or `beforeunload`. Listener **must**
        either `dialog.accept()` or `dialog.dismiss()` the dialog - otherwise the page will
        [freeze](https://developer.mozilla.org/en-US/docs/Web/JavaScript/EventLoop#never_blocking) waiting for the dialog, and
        actions like click will never finish.

        ```python
        page.on(\"dialog\", lambda dialog: dialog.accept())
        ```

        > NOTE: When no `page.on('dialog')` listeners are present, all dialogs are automatically dismissed."""

    @typing.overload
    def once(
        self, event: Literal["domcontentloaded"], f: typing.Callable[["Page"], "None"]
    ) -> None:
        """
        Emitted when the JavaScript [`DOMContentLoaded`](https://developer.mozilla.org/en-US/docs/Web/Events/DOMContentLoaded)
        event is dispatched."""

    @typing.overload
    def once(
        self, event: Literal["download"], f: typing.Callable[["Download"], "None"]
    ) -> None:
        """
        Emitted when attachment download started. User can access basic file operations on downloaded content via the passed
        `Download` instance."""

    @typing.overload
    def once(
        self, event: Literal["filechooser"], f: typing.Callable[["FileChooser"], "None"]
    ) -> None:
        """
        Emitted when a file chooser is supposed to appear, such as after clicking the  `<input type=file>`. Playwright can
        respond to it via setting the input files using `file_chooser.set_files()` that can be uploaded after that.

        ```py
        page.on(\"filechooser\", lambda file_chooser: file_chooser.set_files(\"/tmp/myfile.pdf\"))
        ```"""

    @typing.overload
    def once(
        self, event: Literal["frameattached"], f: typing.Callable[["Frame"], "None"]
    ) -> None:
        """
        Emitted when a frame is attached."""

    @typing.overload
    def once(
        self, event: Literal["framedetached"], f: typing.Callable[["Frame"], "None"]
    ) -> None:
        """
        Emitted when a frame is detached."""

    @typing.overload
    def once(
        self, event: Literal["framenavigated"], f: typing.Callable[["Frame"], "None"]
    ) -> None:
        """
        Emitted when a frame is navigated to a new url."""

    @typing.overload
    def once(
        self, event: Literal["load"], f: typing.Callable[["Page"], "None"]
    ) -> None:
        """
        Emitted when the JavaScript [`load`](https://developer.mozilla.org/en-US/docs/Web/Events/load) event is dispatched."""

    @typing.overload
    def once(
        self, event: Literal["pageerror"], f: typing.Callable[["Error"], "None"]
    ) -> None:
        """
        Emitted when an uncaught exception happens within the page.

        ```py
        # Log all uncaught errors to the terminal
        page.on(\"pageerror\", lambda exc: print(f\"uncaught exception: {exc}\"))

        # Navigate to a page with an exception.
        page.goto(\"data:text/html,<script>throw new Error('test')</script>\")
        ```"""

    @typing.overload
    def once(
        self, event: Literal["popup"], f: typing.Callable[["Page"], "None"]
    ) -> None:
        """
        Emitted when the page opens a new tab or window. This event is emitted in addition to the
        `browser_context.on('page')`, but only for popups relevant to this page.

        The earliest moment that page is available is when it has navigated to the initial url. For example, when opening a
        popup with `window.open('http://example.com')`, this event will fire when the network request to \"http://example.com\" is
        done and its response has started loading in the popup.

        ```py
        with page.expect_event(\"popup\") as page_info:
            page.evaluate(\"window.open('https://example.com')\")
        popup = page_info.value
        print(popup.evaluate(\"location.href\"))
        ```

        > NOTE: Use `page.wait_for_load_state()` to wait until the page gets to a particular state (you should not need it
        in most cases)."""

    @typing.overload
    def once(
        self, event: Literal["request"], f: typing.Callable[["Request"], "None"]
    ) -> None:
        """
        Emitted when a page issues a request. The [request] object is read-only. In order to intercept and mutate requests, see
        `page.route()` or `browser_context.route()`."""

    @typing.overload
    def once(
        self, event: Literal["requestfailed"], f: typing.Callable[["Request"], "None"]
    ) -> None:
        """
        Emitted when a request fails, for example by timing out.

        ```python
        page.on(\"requestfailed\", lambda request: print(request.url + \" \" + request.failure.error_text))
        ```

        > NOTE: HTTP Error responses, such as 404 or 503, are still successful responses from HTTP standpoint, so request will
        complete with `page.on('request_finished')` event and not with `page.on('request_failed')`. A request will only be
        considered failed when the client cannot get an HTTP response from the server, e.g. due to network error
        net::ERR_FAILED."""

    @typing.overload
    def once(
        self, event: Literal["requestfinished"], f: typing.Callable[["Request"], "None"]
    ) -> None:
        """
        Emitted when a request finishes successfully after downloading the response body. For a successful response, the
        sequence of events is `request`, `response` and `requestfinished`."""

    @typing.overload
    def once(
        self, event: Literal["response"], f: typing.Callable[["Response"], "None"]
    ) -> None:
        """
        Emitted when [response] status and headers are received for a request. For a successful response, the sequence of events
        is `request`, `response` and `requestfinished`."""

    @typing.overload
    def once(
        self, event: Literal["websocket"], f: typing.Callable[["WebSocket"], "None"]
    ) -> None:
        """
        Emitted when `WebSocket` request is sent."""

    @typing.overload
    def once(
        self, event: Literal["worker"], f: typing.Callable[["Worker"], "None"]
    ) -> None:
        """
        Emitted when a dedicated [WebWorker](https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API) is spawned by the
        page."""

    def once(self, event: str, f: typing.Callable[..., None]) -> None:
        return super().once(event=event, f=f)

    @property
    def accessibility(self) -> "Accessibility":
        """Page.accessibility

        Returns
        -------
        Accessibility
        """
        return mapping.from_impl(self._impl_obj.accessibility)

    @property
    def keyboard(self) -> "Keyboard":
        """Page.keyboard

        Returns
        -------
        Keyboard
        """
        return mapping.from_impl(self._impl_obj.keyboard)

    @property
    def mouse(self) -> "Mouse":
        """Page.mouse

        Returns
        -------
        Mouse
        """
        return mapping.from_impl(self._impl_obj.mouse)

    @property
    def touchscreen(self) -> "Touchscreen":
        """Page.touchscreen

        Returns
        -------
        Touchscreen
        """
        return mapping.from_impl(self._impl_obj.touchscreen)

    @property
    def context(self) -> "BrowserContext":
        """Page.context

        Get the browser context that the page belongs to.

        Returns
        -------
        BrowserContext
        """
        return mapping.from_impl(self._impl_obj.context)

    @property
    def main_frame(self) -> "Frame":
        """Page.main_frame

        The page's main frame. Page is guaranteed to have a main frame which persists during navigations.

        Returns
        -------
        Frame
        """
        return mapping.from_impl(self._impl_obj.main_frame)

    @property
    def frames(self) -> typing.List["Frame"]:
        """Page.frames

        An array of all frames attached to the page.

        Returns
        -------
        List[Frame]
        """
        return mapping.from_impl_list(self._impl_obj.frames)

    @property
    def url(self) -> str:
        """Page.url

        Shortcut for main frame's `frame.url()`.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.url)

    @property
    def viewport_size(self) -> typing.Optional[ViewportSize]:
        """Page.viewport_size

        Returns
        -------
        Union[{width: int, height: int}, NoneType]
        """
        return mapping.from_impl_nullable(self._impl_obj.viewport_size)

    @property
    def workers(self) -> typing.List["Worker"]:
        """Page.workers

        This method returns all of the dedicated [WebWorkers](https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API)
        associated with the page.

        > NOTE: This does not contain ServiceWorkers

        Returns
        -------
        List[Worker]
        """
        return mapping.from_impl_list(self._impl_obj.workers)

    @property
    def request(self) -> "APIRequestContext":
        """Page.request

        API testing helper associated with this page. This method returns the same instance as
        `browser_context.request` on the page's context. See `browser_context.request` for more details.

        Returns
        -------
        APIRequestContext
        """
        return mapping.from_impl(self._impl_obj.request)

    @property
    def video(self) -> typing.Optional["Video"]:
        """Page.video

        Video object associated with this page.

        Returns
        -------
        Union[Video, NoneType]
        """
        return mapping.from_impl_nullable(self._impl_obj.video)

    def opener(self) -> typing.Optional["Page"]:
        """Page.opener

        Returns the opener for popup pages and `null` for others. If the opener has been closed already the returns `null`.

        Returns
        -------
        Union[Page, NoneType]
        """

        return mapping.from_impl_nullable(self._sync(self._impl_obj.opener()))

    def frame(
        self,
        name: str = None,
        *,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]] = None
    ) -> typing.Optional["Frame"]:
        """Page.frame

        Returns frame matching the specified criteria. Either `name` or `url` must be specified.

        ```py
        frame = page.frame(name=\"frame-name\")
        ```

        ```py
        frame = page.frame(url=r\".*domain.*\")
        ```

        Parameters
        ----------
        name : Union[str, NoneType]
            Frame name specified in the `iframe`'s `name` attribute. Optional.
        url : Union[Callable[[str], bool], Pattern, str, NoneType]
            A glob pattern, regex pattern or predicate receiving frame's `url` as a [URL] object. Optional.

        Returns
        -------
        Union[Frame, NoneType]
        """

        return mapping.from_impl_nullable(
            self._impl_obj.frame(name=name, url=self._wrap_handler(url))
        )

    def set_default_navigation_timeout(self, timeout: float) -> NoneType:
        """Page.set_default_navigation_timeout

        This setting will change the default maximum navigation time for the following methods and related shortcuts:
        - `page.go_back()`
        - `page.go_forward()`
        - `page.goto()`
        - `page.reload()`
        - `page.set_content()`
        - `page.expect_navigation()`
        - `page.wait_for_url()`

        > NOTE: `page.set_default_navigation_timeout()` takes priority over `page.set_default_timeout()`,
        `browser_context.set_default_timeout()` and `browser_context.set_default_navigation_timeout()`.

        Parameters
        ----------
        timeout : float
            Maximum navigation time in milliseconds
        """

        return mapping.from_maybe_impl(
            self._impl_obj.set_default_navigation_timeout(timeout=timeout)
        )

    def set_default_timeout(self, timeout: float) -> NoneType:
        """Page.set_default_timeout

        This setting will change the default maximum time for all the methods accepting `timeout` option.

        > NOTE: `page.set_default_navigation_timeout()` takes priority over `page.set_default_timeout()`.

        Parameters
        ----------
        timeout : float
            Maximum time in milliseconds
        """

        return mapping.from_maybe_impl(
            self._impl_obj.set_default_timeout(timeout=timeout)
        )

    def query_selector(
        self, selector: str, *, strict: bool = None
    ) -> typing.Optional["ElementHandle"]:
        """Page.query_selector

        > NOTE: The use of `ElementHandle` is discouraged, use `Locator` objects and web-first assertions instead.

        The method finds an element matching the specified selector within the page. If no elements match the selector, the
        return value resolves to `null`. To wait for an element on the page, use `locator.wait_for()`.

        Shortcut for main frame's `frame.query_selector()`.

        Parameters
        ----------
        selector : str
            A selector to query for. See [working with selectors](../selectors.md) for more details.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.

        Returns
        -------
        Union[ElementHandle, NoneType]
        """

        return mapping.from_impl_nullable(
            self._sync(self._impl_obj.query_selector(selector=selector, strict=strict))
        )

    def query_selector_all(self, selector: str) -> typing.List["ElementHandle"]:
        """Page.query_selector_all

        > NOTE: The use of `ElementHandle` is discouraged, use `Locator` objects and web-first assertions instead.

        The method finds all elements matching the specified selector within the page. If no elements match the selector, the
        return value resolves to `[]`.

        Shortcut for main frame's `frame.query_selector_all()`.

        Parameters
        ----------
        selector : str
            A selector to query for. See [working with selectors](../selectors.md) for more details.

        Returns
        -------
        List[ElementHandle]
        """

        return mapping.from_impl_list(
            self._sync(self._impl_obj.query_selector_all(selector=selector))
        )

    def wait_for_selector(
        self,
        selector: str,
        *,
        timeout: float = None,
        state: Literal["attached", "detached", "hidden", "visible"] = None,
        strict: bool = None
    ) -> typing.Optional["ElementHandle"]:
        """Page.wait_for_selector

        Returns when element specified by selector satisfies `state` option. Returns `null` if waiting for `hidden` or
        `detached`.

        > NOTE: Playwright automatically waits for element to be ready before performing an action. Using `Locator` objects and
        web-first assertions make the code wait-for-selector-free.

        Wait for the `selector` to satisfy `state` option (either appear/disappear from dom, or become visible/hidden). If at
        the moment of calling the method `selector` already satisfies the condition, the method will return immediately. If the
        selector doesn't satisfy the condition for the `timeout` milliseconds, the function will throw.

        This method works across navigations:

        ```py
        from playwright.sync_api import sync_playwright

        def run(playwright):
            chromium = playwright.chromium
            browser = chromium.launch()
            page = browser.new_page()
            for current_url in [\"https://google.com\", \"https://bbc.com\"]:
                page.goto(current_url, wait_until=\"domcontentloaded\")
                element = page.wait_for_selector(\"img\")
                print(\"Loaded image: \" + str(element.get_attribute(\"src\")))
            browser.close()

        with sync_playwright() as playwright:
            run(playwright)
        ```

        Parameters
        ----------
        selector : str
            A selector to query for. See [working with selectors](../selectors.md) for more details.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        state : Union["attached", "detached", "hidden", "visible", NoneType]
            Defaults to `'visible'`. Can be either:
            - `'attached'` - wait for element to be present in DOM.
            - `'detached'` - wait for element to not be present in DOM.
            - `'visible'` - wait for element to have non-empty bounding box and no `visibility:hidden`. Note that element without
              any content or with `display:none` has an empty bounding box and is not considered visible.
            - `'hidden'` - wait for element to be either detached from DOM, or have an empty bounding box or `visibility:hidden`.
              This is opposite to the `'visible'` option.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.

        Returns
        -------
        Union[ElementHandle, NoneType]
        """

        return mapping.from_impl_nullable(
            self._sync(
                self._impl_obj.wait_for_selector(
                    selector=selector, timeout=timeout, state=state, strict=strict
                )
            )
        )

    def is_checked(
        self, selector: str, *, strict: bool = None, timeout: float = None
    ) -> bool:
        """Page.is_checked

        Returns whether the element is checked. Throws if the element is not a checkbox or radio input.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.is_checked(
                    selector=selector, strict=strict, timeout=timeout
                )
            )
        )

    def is_disabled(
        self, selector: str, *, strict: bool = None, timeout: float = None
    ) -> bool:
        """Page.is_disabled

        Returns whether the element is disabled, the opposite of [enabled](https://playwright.dev/python/docs/actionability#enabled).

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.is_disabled(
                    selector=selector, strict=strict, timeout=timeout
                )
            )
        )

    def is_editable(
        self, selector: str, *, strict: bool = None, timeout: float = None
    ) -> bool:
        """Page.is_editable

        Returns whether the element is [editable](https://playwright.dev/python/docs/actionability#editable).

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.is_editable(
                    selector=selector, strict=strict, timeout=timeout
                )
            )
        )

    def is_enabled(
        self, selector: str, *, strict: bool = None, timeout: float = None
    ) -> bool:
        """Page.is_enabled

        Returns whether the element is [enabled](https://playwright.dev/python/docs/actionability#enabled).

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.is_enabled(
                    selector=selector, strict=strict, timeout=timeout
                )
            )
        )

    def is_hidden(
        self, selector: str, *, strict: bool = None, timeout: float = None
    ) -> bool:
        """Page.is_hidden

        Returns whether the element is hidden, the opposite of [visible](https://playwright.dev/python/docs/actionability#visible).  `selector` that does not
        match any elements is considered hidden.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        timeout : Union[float, NoneType]
            **DEPRECATED** This option is ignored. `page.is_hidden()` does not wait for the element to become hidden and
            returns immediately.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.is_hidden(
                    selector=selector, strict=strict, timeout=timeout
                )
            )
        )

    def is_visible(
        self, selector: str, *, strict: bool = None, timeout: float = None
    ) -> bool:
        """Page.is_visible

        Returns whether the element is [visible](https://playwright.dev/python/docs/actionability#visible). `selector` that does not match any elements is
        considered not visible.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        timeout : Union[float, NoneType]
            **DEPRECATED** This option is ignored. `page.is_visible()` does not wait for the element to become visible and
            returns immediately.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.is_visible(
                    selector=selector, strict=strict, timeout=timeout
                )
            )
        )

    def dispatch_event(
        self,
        selector: str,
        type: str,
        event_init: typing.Dict = None,
        *,
        timeout: float = None,
        strict: bool = None
    ) -> NoneType:
        """Page.dispatch_event

        The snippet below dispatches the `click` event on the element. Regardless of the visibility state of the element,
        `click` is dispatched. This is equivalent to calling
        [element.click()](https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/click).

        ```py
        page.dispatch_event(\"button#submit\", \"click\")
        ```

        Under the hood, it creates an instance of an event based on the given `type`, initializes it with `eventInit` properties
        and dispatches it on the element. Events are `composed`, `cancelable` and bubble by default.

        Since `eventInit` is event-specific, please refer to the events documentation for the lists of initial properties:
        - [DragEvent](https://developer.mozilla.org/en-US/docs/Web/API/DragEvent/DragEvent)
        - [FocusEvent](https://developer.mozilla.org/en-US/docs/Web/API/FocusEvent/FocusEvent)
        - [KeyboardEvent](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/KeyboardEvent)
        - [MouseEvent](https://developer.mozilla.org/en-US/docs/Web/API/MouseEvent/MouseEvent)
        - [PointerEvent](https://developer.mozilla.org/en-US/docs/Web/API/PointerEvent/PointerEvent)
        - [TouchEvent](https://developer.mozilla.org/en-US/docs/Web/API/TouchEvent/TouchEvent)
        - [Event](https://developer.mozilla.org/en-US/docs/Web/API/Event/Event)

        You can also specify `JSHandle` as the property value if you want live objects to be passed into the event:

        ```py
        # note you can only create data_transfer in chromium and firefox
        data_transfer = page.evaluate_handle(\"new DataTransfer()\")
        page.dispatch_event(\"#source\", \"dragstart\", { \"dataTransfer\": data_transfer })
        ```

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        type : str
            DOM event type: `"click"`, `"dragstart"`, etc.
        event_init : Union[Dict, NoneType]
            Optional event-specific initialization properties.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.dispatch_event(
                    selector=selector,
                    type=type,
                    eventInit=mapping.to_impl(event_init),
                    timeout=timeout,
                    strict=strict,
                )
            )
        )

    def evaluate(self, expression: str, arg: typing.Any = None) -> typing.Any:
        """Page.evaluate

        Returns the value of the `expression` invocation.

        If the function passed to the `page.evaluate()` returns a [Promise], then `page.evaluate()` would wait
        for the promise to resolve and return its value.

        If the function passed to the `page.evaluate()` returns a non-[Serializable] value, then
        `page.evaluate()` resolves to `undefined`. Playwright also supports transferring some additional values that are
        not serializable by `JSON`: `-0`, `NaN`, `Infinity`, `-Infinity`.

        Passing argument to `expression`:

        ```py
        result = page.evaluate(\"([x, y]) => Promise.resolve(x * y)\", [7, 8])
        print(result) # prints \"56\"
        ```

        A string can also be passed in instead of a function:

        ```py
        print(page.evaluate(\"1 + 2\")) # prints \"3\"
        x = 10
        print(page.evaluate(f\"1 + {x}\")) # prints \"11\"
        ```

        `ElementHandle` instances can be passed as an argument to the `page.evaluate()`:

        ```py
        body_handle = page.evaluate(\"document.body\")
        html = page.evaluate(\"([body, suffix]) => body.innerHTML + suffix\", [body_handle, \"hello\"])
        body_handle.dispose()
        ```

        Shortcut for main frame's `frame.evaluate()`.

        Parameters
        ----------
        expression : str
            JavaScript expression to be evaluated in the browser context. If it looks like a function declaration, it is interpreted
            as a function. Otherwise, evaluated as an expression.
        arg : Union[Any, NoneType]
            Optional argument to pass to `expression`.

        Returns
        -------
        Any
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.evaluate(expression=expression, arg=mapping.to_impl(arg))
            )
        )

    def evaluate_handle(self, expression: str, arg: typing.Any = None) -> "JSHandle":
        """Page.evaluate_handle

        Returns the value of the `expression` invocation as a `JSHandle`.

        The only difference between `page.evaluate()` and `page.evaluate_handle()` is that
        `page.evaluate_handle()` returns `JSHandle`.

        If the function passed to the `page.evaluate_handle()` returns a [Promise], then `page.evaluate_handle()`
        would wait for the promise to resolve and return its value.

        ```py
        a_window_handle = page.evaluate_handle(\"Promise.resolve(window)\")
        a_window_handle # handle for the window object.
        ```

        A string can also be passed in instead of a function:

        ```py
        a_handle = page.evaluate_handle(\"document\") # handle for the \"document\"
        ```

        `JSHandle` instances can be passed as an argument to the `page.evaluate_handle()`:

        ```py
        a_handle = page.evaluate_handle(\"document.body\")
        result_handle = page.evaluate_handle(\"body => body.innerHTML\", a_handle)
        print(result_handle.json_value())
        result_handle.dispose()
        ```

        Parameters
        ----------
        expression : str
            JavaScript expression to be evaluated in the browser context. If it looks like a function declaration, it is interpreted
            as a function. Otherwise, evaluated as an expression.
        arg : Union[Any, NoneType]
            Optional argument to pass to `expression`.

        Returns
        -------
        JSHandle
        """

        return mapping.from_impl(
            self._sync(
                self._impl_obj.evaluate_handle(
                    expression=expression, arg=mapping.to_impl(arg)
                )
            )
        )

    def eval_on_selector(
        self,
        selector: str,
        expression: str,
        arg: typing.Any = None,
        *,
        strict: bool = None
    ) -> typing.Any:
        """Page.eval_on_selector

        > NOTE: This method does not wait for the element to pass actionability checks and therefore can lead to the flaky
        tests. Use `locator.evaluate()`, other `Locator` helper methods or web-first assertions instead.

        The method finds an element matching the specified selector within the page and passes it as a first argument to
        `expression`. If no elements match the selector, the method throws an error. Returns the value of `expression`.

        If `expression` returns a [Promise], then `page.eval_on_selector()` would wait for the promise to resolve and
        return its value.

        Examples:

        ```py
        search_value = page.eval_on_selector(\"#search\", \"el => el.value\")
        preload_href = page.eval_on_selector(\"link[rel=preload]\", \"el => el.href\")
        html = page.eval_on_selector(\".main-container\", \"(e, suffix) => e.outer_html + suffix\", \"hello\")
        ```

        Shortcut for main frame's `frame.eval_on_selector()`.

        Parameters
        ----------
        selector : str
            A selector to query for. See [working with selectors](../selectors.md) for more details.
        expression : str
            JavaScript expression to be evaluated in the browser context. If it looks like a function declaration, it is interpreted
            as a function. Otherwise, evaluated as an expression.
        arg : Union[Any, NoneType]
            Optional argument to pass to `expression`.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.

        Returns
        -------
        Any
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.eval_on_selector(
                    selector=selector,
                    expression=expression,
                    arg=mapping.to_impl(arg),
                    strict=strict,
                )
            )
        )

    def eval_on_selector_all(
        self, selector: str, expression: str, arg: typing.Any = None
    ) -> typing.Any:
        """Page.eval_on_selector_all

        > NOTE: In most cases, `locator.evaluate_all()`, other `Locator` helper methods and web-first assertions do a
        better job.

        The method finds all elements matching the specified selector within the page and passes an array of matched elements as
        a first argument to `expression`. Returns the result of `expression` invocation.

        If `expression` returns a [Promise], then `page.eval_on_selector_all()` would wait for the promise to resolve and
        return its value.

        Examples:

        ```py
        div_counts = page.eval_on_selector_all(\"div\", \"(divs, min) => divs.length >= min\", 10)
        ```

        Parameters
        ----------
        selector : str
            A selector to query for. See [working with selectors](../selectors.md) for more details.
        expression : str
            JavaScript expression to be evaluated in the browser context. If it looks like a function declaration, it is interpreted
            as a function. Otherwise, evaluated as an expression.
        arg : Union[Any, NoneType]
            Optional argument to pass to `expression`.

        Returns
        -------
        Any
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.eval_on_selector_all(
                    selector=selector, expression=expression, arg=mapping.to_impl(arg)
                )
            )
        )

    def add_script_tag(
        self,
        *,
        url: str = None,
        path: typing.Union[str, pathlib.Path] = None,
        content: str = None,
        type: str = None
    ) -> "ElementHandle":
        """Page.add_script_tag

        Adds a `<script>` tag into the page with the desired url or content. Returns the added tag when the script's onload
        fires or when the script content was injected into frame.

        Shortcut for main frame's `frame.add_script_tag()`.

        Parameters
        ----------
        url : Union[str, NoneType]
            URL of a script to be added.
        path : Union[pathlib.Path, str, NoneType]
            Path to the JavaScript file to be injected into frame. If `path` is a relative path, then it is resolved relative to the
            current working directory.
        content : Union[str, NoneType]
            Raw JavaScript content to be injected into frame.
        type : Union[str, NoneType]
            Script type. Use 'module' in order to load a Javascript ES6 module. See
            [script](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/script) for more details.

        Returns
        -------
        ElementHandle
        """

        return mapping.from_impl(
            self._sync(
                self._impl_obj.add_script_tag(
                    url=url, path=path, content=content, type=type
                )
            )
        )

    def add_style_tag(
        self,
        *,
        url: str = None,
        path: typing.Union[str, pathlib.Path] = None,
        content: str = None
    ) -> "ElementHandle":
        """Page.add_style_tag

        Adds a `<link rel=\"stylesheet\">` tag into the page with the desired url or a `<style type=\"text/css\">` tag with the
        content. Returns the added tag when the stylesheet's onload fires or when the CSS content was injected into frame.

        Shortcut for main frame's `frame.add_style_tag()`.

        Parameters
        ----------
        url : Union[str, NoneType]
            URL of the `<link>` tag.
        path : Union[pathlib.Path, str, NoneType]
            Path to the CSS file to be injected into frame. If `path` is a relative path, then it is resolved relative to the
            current working directory.
        content : Union[str, NoneType]
            Raw CSS content to be injected into frame.

        Returns
        -------
        ElementHandle
        """

        return mapping.from_impl(
            self._sync(
                self._impl_obj.add_style_tag(url=url, path=path, content=content)
            )
        )

    def expose_function(self, name: str, callback: typing.Callable) -> NoneType:
        """Page.expose_function

        The method adds a function called `name` on the `window` object of every frame in the page. When called, the function
        executes `callback` and returns a [Promise] which resolves to the return value of `callback`.

        If the `callback` returns a [Promise], it will be awaited.

        See `browser_context.expose_function()` for context-wide exposed function.

        > NOTE: Functions installed via `page.expose_function()` survive navigations.

        An example of adding a `sha256` function to the page:

        ```py
        import hashlib
        from playwright.sync_api import sync_playwright

        def sha256(text):
            m = hashlib.sha256()
            m.update(bytes(text, \"utf8\"))
            return m.hexdigest()

        def run(playwright):
            webkit = playwright.webkit
            browser = webkit.launch(headless=False)
            page = browser.new_page()
            page.expose_function(\"sha256\", sha256)
            page.set_content(\"\"\"
                <script>
                  async function onClick() {
                    document.querySelector('div').textContent = await window.sha256('PLAYWRIGHT');
                  }
                </script>
                <button onclick=\"onClick()\">Click me</button>
                <div></div>
            \"\"\")
            page.click(\"button\")

        with sync_playwright() as playwright:
            run(playwright)
        ```

        Parameters
        ----------
        name : str
            Name of the function on the window object
        callback : Callable
            Callback function which will be called in Playwright's context.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.expose_function(
                    name=name, callback=self._wrap_handler(callback)
                )
            )
        )

    def expose_binding(
        self, name: str, callback: typing.Callable, *, handle: bool = None
    ) -> NoneType:
        """Page.expose_binding

        The method adds a function called `name` on the `window` object of every frame in this page. When called, the function
        executes `callback` and returns a [Promise] which resolves to the return value of `callback`. If the `callback` returns
        a [Promise], it will be awaited.

        The first argument of the `callback` function contains information about the caller: `{ browserContext: BrowserContext,
        page: Page, frame: Frame }`.

        See `browser_context.expose_binding()` for the context-wide version.

        > NOTE: Functions installed via `page.expose_binding()` survive navigations.

        An example of exposing page URL to all frames in a page:

        ```py
        from playwright.sync_api import sync_playwright

        def run(playwright):
            webkit = playwright.webkit
            browser = webkit.launch(headless=false)
            context = browser.new_context()
            page = context.new_page()
            page.expose_binding(\"pageURL\", lambda source: source[\"page\"].url)
            page.set_content(\"\"\"
            <script>
              async function onClick() {
                document.querySelector('div').textContent = await window.pageURL();
              }
            </script>
            <button onclick=\"onClick()\">Click me</button>
            <div></div>
            \"\"\")
            page.click(\"button\")

        with sync_playwright() as playwright:
            run(playwright)
        ```

        An example of passing an element handle:

        ```py
        def print(source, element):
            print(element.text_content())

        page.expose_binding(\"clicked\", print, handle=true)
        page.set_content(\"\"\"
          <script>
            document.addEventListener('click', event => window.clicked(event.target));
          </script>
          <div>Click me</div>
          <div>Or click me</div>
        \"\"\")
        ```

        Parameters
        ----------
        name : str
            Name of the function on the window object.
        callback : Callable
            Callback function that will be called in the Playwright's context.
        handle : Union[bool, NoneType]
            Whether to pass the argument as a handle, instead of passing by value. When passing a handle, only one argument is
            supported. When passing by value, multiple arguments are supported.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.expose_binding(
                    name=name, callback=self._wrap_handler(callback), handle=handle
                )
            )
        )

    def set_extra_http_headers(self, headers: typing.Dict[str, str]) -> NoneType:
        """Page.set_extra_http_headers

        The extra HTTP headers will be sent with every request the page initiates.

        > NOTE: `page.set_extra_http_headers()` does not guarantee the order of headers in the outgoing requests.

        Parameters
        ----------
        headers : Dict[str, str]
            An object containing additional HTTP headers to be sent with every request. All header values must be strings.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.set_extra_http_headers(headers=mapping.to_impl(headers))
            )
        )

    def content(self) -> str:
        """Page.content

        Gets the full HTML contents of the page, including the doctype.

        Returns
        -------
        str
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.content()))

    def set_content(
        self,
        html: str,
        *,
        timeout: float = None,
        wait_until: Literal["commit", "domcontentloaded", "load", "networkidle"] = None
    ) -> NoneType:
        """Page.set_content

        Parameters
        ----------
        html : str
            HTML markup to assign to the page.
        timeout : Union[float, NoneType]
            Maximum operation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be
            changed by using the `browser_context.set_default_navigation_timeout()`,
            `browser_context.set_default_timeout()`, `page.set_default_navigation_timeout()` or
            `page.set_default_timeout()` methods.
        wait_until : Union["commit", "domcontentloaded", "load", "networkidle", NoneType]
            When to consider operation succeeded, defaults to `load`. Events can be either:
            - `'domcontentloaded'` - consider operation to be finished when the `DOMContentLoaded` event is fired.
            - `'load'` - consider operation to be finished when the `load` event is fired.
            - `'networkidle'` - consider operation to be finished when there are no network connections for at least `500` ms.
            - `'commit'` - consider operation to be finished when network response is received and the document started loading.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.set_content(
                    html=html, timeout=timeout, waitUntil=wait_until
                )
            )
        )

    def goto(
        self,
        url: str,
        *,
        timeout: float = None,
        wait_until: Literal["commit", "domcontentloaded", "load", "networkidle"] = None,
        referer: str = None
    ) -> typing.Optional["Response"]:
        """Page.goto

        Returns the main resource response. In case of multiple redirects, the navigation will resolve with the first
        non-redirect response.

        The method will throw an error if:
        - there's an SSL error (e.g. in case of self-signed certificates).
        - target URL is invalid.
        - the `timeout` is exceeded during navigation.
        - the remote server does not respond or is unreachable.
        - the main resource failed to load.

        The method will not throw an error when any valid HTTP status code is returned by the remote server, including 404 \"Not
        Found\" and 500 \"Internal Server Error\".  The status code for such responses can be retrieved by calling
        `response.status()`.

        > NOTE: The method either throws an error or returns a main resource response. The only exceptions are navigation to
        `about:blank` or navigation to the same URL with a different hash, which would succeed and return `null`.
        > NOTE: Headless mode doesn't support navigation to a PDF document. See the
        [upstream issue](https://bugs.chromium.org/p/chromium/issues/detail?id=761295).

        Shortcut for main frame's `frame.goto()`

        Parameters
        ----------
        url : str
            URL to navigate page to. The url should include scheme, e.g. `https://`. When a `baseURL` via the context options was
            provided and the passed URL is a path, it gets merged via the
            [`new URL()`](https://developer.mozilla.org/en-US/docs/Web/API/URL/URL) constructor.
        timeout : Union[float, NoneType]
            Maximum operation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be
            changed by using the `browser_context.set_default_navigation_timeout()`,
            `browser_context.set_default_timeout()`, `page.set_default_navigation_timeout()` or
            `page.set_default_timeout()` methods.
        wait_until : Union["commit", "domcontentloaded", "load", "networkidle", NoneType]
            When to consider operation succeeded, defaults to `load`. Events can be either:
            - `'domcontentloaded'` - consider operation to be finished when the `DOMContentLoaded` event is fired.
            - `'load'` - consider operation to be finished when the `load` event is fired.
            - `'networkidle'` - consider operation to be finished when there are no network connections for at least `500` ms.
            - `'commit'` - consider operation to be finished when network response is received and the document started loading.
        referer : Union[str, NoneType]
            Referer header value. If provided it will take preference over the referer header value set by
            `page.set_extra_http_headers()`.

        Returns
        -------
        Union[Response, NoneType]
        """

        return mapping.from_impl_nullable(
            self._sync(
                self._impl_obj.goto(
                    url=url, timeout=timeout, waitUntil=wait_until, referer=referer
                )
            )
        )

    def reload(
        self,
        *,
        timeout: float = None,
        wait_until: Literal["commit", "domcontentloaded", "load", "networkidle"] = None
    ) -> typing.Optional["Response"]:
        """Page.reload

        This method reloads the current page, in the same way as if the user had triggered a browser refresh. Returns the main
        resource response. In case of multiple redirects, the navigation will resolve with the response of the last redirect.

        Parameters
        ----------
        timeout : Union[float, NoneType]
            Maximum operation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be
            changed by using the `browser_context.set_default_navigation_timeout()`,
            `browser_context.set_default_timeout()`, `page.set_default_navigation_timeout()` or
            `page.set_default_timeout()` methods.
        wait_until : Union["commit", "domcontentloaded", "load", "networkidle", NoneType]
            When to consider operation succeeded, defaults to `load`. Events can be either:
            - `'domcontentloaded'` - consider operation to be finished when the `DOMContentLoaded` event is fired.
            - `'load'` - consider operation to be finished when the `load` event is fired.
            - `'networkidle'` - consider operation to be finished when there are no network connections for at least `500` ms.
            - `'commit'` - consider operation to be finished when network response is received and the document started loading.

        Returns
        -------
        Union[Response, NoneType]
        """

        return mapping.from_impl_nullable(
            self._sync(self._impl_obj.reload(timeout=timeout, waitUntil=wait_until))
        )

    def wait_for_load_state(
        self,
        state: Literal["domcontentloaded", "load", "networkidle"] = None,
        *,
        timeout: float = None
    ) -> NoneType:
        """Page.wait_for_load_state

        Returns when the required load state has been reached.

        This resolves when the page reaches a required load state, `load` by default. The navigation must have been committed
        when this method is called. If current document has already reached the required state, resolves immediately.

        ```py
        page.click(\"button\") # click triggers navigation.
        page.wait_for_load_state() # the promise resolves after \"load\" event.
        ```

        ```py
        with page.expect_popup() as page_info:
            page.click(\"button\") # click triggers a popup.
        popup = page_info.value
         # Following resolves after \"domcontentloaded\" event.
        popup.wait_for_load_state(\"domcontentloaded\")
        print(popup.title()) # popup is ready to use.
        ```

        Shortcut for main frame's `frame.wait_for_load_state()`.

        Parameters
        ----------
        state : Union["domcontentloaded", "load", "networkidle", NoneType]
            Optional load state to wait for, defaults to `load`. If the state has been already reached while loading current
            document, the method resolves immediately. Can be one of:
            - `'load'` - wait for the `load` event to be fired.
            - `'domcontentloaded'` - wait for the `DOMContentLoaded` event to be fired.
            - `'networkidle'` - wait until there are no network connections for at least `500` ms.
        timeout : Union[float, NoneType]
            Maximum operation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be
            changed by using the `browser_context.set_default_navigation_timeout()`,
            `browser_context.set_default_timeout()`, `page.set_default_navigation_timeout()` or
            `page.set_default_timeout()` methods.
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.wait_for_load_state(state=state, timeout=timeout))
        )

    def wait_for_url(
        self,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]],
        *,
        wait_until: Literal["commit", "domcontentloaded", "load", "networkidle"] = None,
        timeout: float = None
    ) -> NoneType:
        """Page.wait_for_url

        Waits for the main frame to navigate to the given URL.

        ```py
        page.click(\"a.delayed-navigation\") # clicking the link will indirectly cause a navigation
        page.wait_for_url(\"**/target.html\")
        ```

        Shortcut for main frame's `frame.wait_for_url()`.

        Parameters
        ----------
        url : Union[Callable[[str], bool], Pattern, str]
            A glob pattern, regex pattern or predicate receiving [URL] to match while waiting for the navigation. Note that if the
            parameter is a string without wildcard characters, the method will wait for navigation to URL that is exactly equal to
            the string.
        wait_until : Union["commit", "domcontentloaded", "load", "networkidle", NoneType]
            When to consider operation succeeded, defaults to `load`. Events can be either:
            - `'domcontentloaded'` - consider operation to be finished when the `DOMContentLoaded` event is fired.
            - `'load'` - consider operation to be finished when the `load` event is fired.
            - `'networkidle'` - consider operation to be finished when there are no network connections for at least `500` ms.
            - `'commit'` - consider operation to be finished when network response is received and the document started loading.
        timeout : Union[float, NoneType]
            Maximum operation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be
            changed by using the `browser_context.set_default_navigation_timeout()`,
            `browser_context.set_default_timeout()`, `page.set_default_navigation_timeout()` or
            `page.set_default_timeout()` methods.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.wait_for_url(
                    url=self._wrap_handler(url), wait_until=wait_until, timeout=timeout
                )
            )
        )

    def wait_for_event(
        self, event: str, predicate: typing.Callable = None, *, timeout: float = None
    ) -> typing.Any:
        """Page.wait_for_event

        > NOTE: In most cases, you should use `page.expect_event()`.

        Waits for given `event` to fire. If predicate is provided, it passes event's value into the `predicate` function and
        waits for `predicate(event)` to return a truthy value. Will throw an error if the page is closed before the `event` is
        fired.

        Parameters
        ----------
        event : str
            Event name, same one typically passed into `*.on(event)`.
        predicate : Union[Callable, NoneType]
            Receives the event data and resolves to truthy value when the waiting should resolve.
        timeout : Union[float, NoneType]
            Maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default
            value can be changed by using the `browser_context.set_default_timeout()`.

        Returns
        -------
        Any
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.wait_for_event(
                    event=event,
                    predicate=self._wrap_handler(predicate),
                    timeout=timeout,
                )
            )
        )

    def go_back(
        self,
        *,
        timeout: float = None,
        wait_until: Literal["commit", "domcontentloaded", "load", "networkidle"] = None
    ) -> typing.Optional["Response"]:
        """Page.go_back

        Returns the main resource response. In case of multiple redirects, the navigation will resolve with the response of the
        last redirect. If can not go back, returns `null`.

        Navigate to the previous page in history.

        Parameters
        ----------
        timeout : Union[float, NoneType]
            Maximum operation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be
            changed by using the `browser_context.set_default_navigation_timeout()`,
            `browser_context.set_default_timeout()`, `page.set_default_navigation_timeout()` or
            `page.set_default_timeout()` methods.
        wait_until : Union["commit", "domcontentloaded", "load", "networkidle", NoneType]
            When to consider operation succeeded, defaults to `load`. Events can be either:
            - `'domcontentloaded'` - consider operation to be finished when the `DOMContentLoaded` event is fired.
            - `'load'` - consider operation to be finished when the `load` event is fired.
            - `'networkidle'` - consider operation to be finished when there are no network connections for at least `500` ms.
            - `'commit'` - consider operation to be finished when network response is received and the document started loading.

        Returns
        -------
        Union[Response, NoneType]
        """

        return mapping.from_impl_nullable(
            self._sync(self._impl_obj.go_back(timeout=timeout, waitUntil=wait_until))
        )

    def go_forward(
        self,
        *,
        timeout: float = None,
        wait_until: Literal["commit", "domcontentloaded", "load", "networkidle"] = None
    ) -> typing.Optional["Response"]:
        """Page.go_forward

        Returns the main resource response. In case of multiple redirects, the navigation will resolve with the response of the
        last redirect. If can not go forward, returns `null`.

        Navigate to the next page in history.

        Parameters
        ----------
        timeout : Union[float, NoneType]
            Maximum operation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be
            changed by using the `browser_context.set_default_navigation_timeout()`,
            `browser_context.set_default_timeout()`, `page.set_default_navigation_timeout()` or
            `page.set_default_timeout()` methods.
        wait_until : Union["commit", "domcontentloaded", "load", "networkidle", NoneType]
            When to consider operation succeeded, defaults to `load`. Events can be either:
            - `'domcontentloaded'` - consider operation to be finished when the `DOMContentLoaded` event is fired.
            - `'load'` - consider operation to be finished when the `load` event is fired.
            - `'networkidle'` - consider operation to be finished when there are no network connections for at least `500` ms.
            - `'commit'` - consider operation to be finished when network response is received and the document started loading.

        Returns
        -------
        Union[Response, NoneType]
        """

        return mapping.from_impl_nullable(
            self._sync(self._impl_obj.go_forward(timeout=timeout, waitUntil=wait_until))
        )

    def emulate_media(
        self,
        *,
        media: Literal["print", "screen"] = None,
        color_scheme: Literal["dark", "light", "no-preference"] = None,
        reduced_motion: Literal["no-preference", "reduce"] = None,
        forced_colors: Literal["active", "none"] = None
    ) -> NoneType:
        """Page.emulate_media

        This method changes the `CSS media type` through the `media` argument, and/or the `'prefers-colors-scheme'` media
        feature, using the `colorScheme` argument.

        ```py
        page.evaluate(\"matchMedia('screen').matches\")
        # → True
        page.evaluate(\"matchMedia('print').matches\")
        # → False

        page.emulate_media(media=\"print\")
        page.evaluate(\"matchMedia('screen').matches\")
        # → False
        page.evaluate(\"matchMedia('print').matches\")
        # → True

        page.emulate_media()
        page.evaluate(\"matchMedia('screen').matches\")
        # → True
        page.evaluate(\"matchMedia('print').matches\")
        # → False
        ```

        ```py
        page.emulate_media(color_scheme=\"dark\")
        page.evaluate(\"matchMedia('(prefers-color-scheme: dark)').matches\")
        # → True
        page.evaluate(\"matchMedia('(prefers-color-scheme: light)').matches\")
        # → False
        page.evaluate(\"matchMedia('(prefers-color-scheme: no-preference)').matches\")
        ```

        Parameters
        ----------
        media : Union["print", "screen", NoneType]
            Changes the CSS media type of the page. The only allowed values are `'screen'`, `'print'` and `null`. Passing `null`
            disables CSS media emulation.
        color_scheme : Union["dark", "light", "no-preference", NoneType]
            Emulates `'prefers-colors-scheme'` media feature, supported values are `'light'`, `'dark'`, `'no-preference'`. Passing
            `null` disables color scheme emulation.
        reduced_motion : Union["no-preference", "reduce", NoneType]
            Emulates `'prefers-reduced-motion'` media feature, supported values are `'reduce'`, `'no-preference'`. Passing `null`
            disables reduced motion emulation.
        forced_colors : Union["active", "none", NoneType]
            Emulates `'forced-colors'` media feature, supported values are `'active'` and `'none'`. Passing `null` disables forced
            colors emulation.

            > NOTE: It's not supported in WebKit, see [here](https://bugs.webkit.org/show_bug.cgi?id=225281) in their issue tracker.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.emulate_media(
                    media=media,
                    colorScheme=color_scheme,
                    reducedMotion=reduced_motion,
                    forcedColors=forced_colors,
                )
            )
        )

    def set_viewport_size(self, viewport_size: ViewportSize) -> NoneType:
        """Page.set_viewport_size

        In the case of multiple pages in a single browser, each page can have its own viewport size. However,
        `browser.new_context()` allows to set viewport size (and more) for all pages in the context at once.

        `page.set_viewport_size()` will resize the page. A lot of websites don't expect phones to change size, so you
        should set the viewport size before navigating to the page. `page.set_viewport_size()` will also reset `screen`
        size, use `browser.new_context()` with `screen` and `viewport` parameters if you need better control of these
        properties.

        ```py
        page = browser.new_page()
        page.set_viewport_size({\"width\": 640, \"height\": 480})
        page.goto(\"https://example.com\")
        ```

        Parameters
        ----------
        viewport_size : {width: int, height: int}
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.set_viewport_size(viewportSize=viewport_size))
        )

    def bring_to_front(self) -> NoneType:
        """Page.bring_to_front

        Brings page to front (activates tab).
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.bring_to_front()))

    def add_init_script(
        self, script: str = None, *, path: typing.Union[str, pathlib.Path] = None
    ) -> NoneType:
        """Page.add_init_script

        Adds a script which would be evaluated in one of the following scenarios:
        - Whenever the page is navigated.
        - Whenever the child frame is attached or navigated. In this case, the script is evaluated in the context of the newly
          attached frame.

        The script is evaluated after the document was created but before any of its scripts were run. This is useful to amend
        the JavaScript environment, e.g. to seed `Math.random`.

        An example of overriding `Math.random` before the page loads:

        ```py
        # in your playwright script, assuming the preload.js file is in same directory
        page.add_init_script(path=\"./preload.js\")
        ```

        > NOTE: The order of evaluation of multiple scripts installed via `browser_context.add_init_script()` and
        `page.add_init_script()` is not defined.

        Parameters
        ----------
        script : Union[str, NoneType]
            Script to be evaluated in all pages in the browser context. Optional.
        path : Union[pathlib.Path, str, NoneType]
            Path to the JavaScript file. If `path` is a relative path, then it is resolved relative to the current working
            directory. Optional.
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.add_init_script(script=script, path=path))
        )

    def route(
        self,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]],
        handler: typing.Union[
            typing.Callable[["Route"], typing.Any],
            typing.Callable[["Route", "Request"], typing.Any],
        ],
        *,
        times: int = None
    ) -> NoneType:
        """Page.route

        Routing provides the capability to modify network requests that are made by a page.

        Once routing is enabled, every request matching the url pattern will stall unless it's continued, fulfilled or aborted.

        > NOTE: The handler will only be called for the first url if the response is a redirect.
        > NOTE: `page.route()` will not intercept requests intercepted by Service Worker. See
        [this](https://github.com/microsoft/playwright/issues/1090) issue. We recommend disabling Service Workers when using
        request interception by setting `Browser.newContext.serviceWorkers` to `'block'`.

        An example of a naive handler that aborts all image requests:

        ```py
        page = browser.new_page()
        page.route(\"**/*.{png,jpg,jpeg}\", lambda route: route.abort())
        page.goto(\"https://example.com\")
        browser.close()
        ```

        or the same snippet using a regex pattern instead:

        ```py
        page = browser.new_page()
        page.route(re.compile(r\"(\\.png$)|(\\.jpg$)\"), lambda route: route.abort())
        page.goto(\"https://example.com\")
        browser.close()
        ```

        It is possible to examine the request to decide the route action. For example, mocking all requests that contain some
        post data, and leaving all other requests as is:

        ```py
        def handle_route(route):
          if (\"my-string\" in route.request.post_data)
            route.fulfill(body=\"mocked-data\")
          else
            route.continue_()
        page.route(\"/api/**\", handle_route)
        ```

        Page routes take precedence over browser context routes (set up with `browser_context.route()`) when request
        matches both handlers.

        To remove a route with its handler you can use `page.unroute()`.

        > NOTE: Enabling routing disables http cache.

        Parameters
        ----------
        url : Union[Callable[[str], bool], Pattern, str]
            A glob pattern, regex pattern or predicate receiving [URL] to match while routing. When a `baseURL` via the context
            options was provided and the passed URL is a path, it gets merged via the
            [`new URL()`](https://developer.mozilla.org/en-US/docs/Web/API/URL/URL) constructor.
        handler : Union[Callable[[Route, Request], Any], Callable[[Route], Any]]
            handler function to route the request.
        times : Union[int, NoneType]
            How often a route should be used. By default it will be used every time.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.route(
                    url=self._wrap_handler(url),
                    handler=self._wrap_handler(handler),
                    times=times,
                )
            )
        )

    def unroute(
        self,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]],
        handler: typing.Union[
            typing.Callable[["Route"], typing.Any],
            typing.Callable[["Route", "Request"], typing.Any],
        ] = None,
    ) -> NoneType:
        """Page.unroute

        Removes a route created with `page.route()`. When `handler` is not specified, removes all routes for the `url`.

        Parameters
        ----------
        url : Union[Callable[[str], bool], Pattern, str]
            A glob pattern, regex pattern or predicate receiving [URL] to match while routing.
        handler : Union[Callable[[Route, Request], Any], Callable[[Route], Any], NoneType]
            Optional handler function to route the request.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.unroute(
                    url=self._wrap_handler(url), handler=self._wrap_handler(handler)
                )
            )
        )

    def screenshot(
        self,
        *,
        timeout: float = None,
        type: Literal["jpeg", "png"] = None,
        path: typing.Union[str, pathlib.Path] = None,
        quality: int = None,
        omit_background: bool = None,
        full_page: bool = None,
        clip: FloatRect = None,
        animations: Literal["allow", "disabled"] = None,
        caret: Literal["hide", "initial"] = None,
        scale: Literal["css", "device"] = None,
        mask: typing.List["Locator"] = None
    ) -> bytes:
        """Page.screenshot

        Returns the buffer with the captured screenshot.

        Parameters
        ----------
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        type : Union["jpeg", "png", NoneType]
            Specify screenshot type, defaults to `png`.
        path : Union[pathlib.Path, str, NoneType]
            The file path to save the image to. The screenshot type will be inferred from file extension. If `path` is a relative
            path, then it is resolved relative to the current working directory. If no path is provided, the image won't be saved to
            the disk.
        quality : Union[int, NoneType]
            The quality of the image, between 0-100. Not applicable to `png` images.
        omit_background : Union[bool, NoneType]
            Hides default white background and allows capturing screenshots with transparency. Not applicable to `jpeg` images.
            Defaults to `false`.
        full_page : Union[bool, NoneType]
            When true, takes a screenshot of the full scrollable page, instead of the currently visible viewport. Defaults to
            `false`.
        clip : Union[{x: float, y: float, width: float, height: float}, NoneType]
            An object which specifies clipping of the resulting image. Should have the following fields:
        animations : Union["allow", "disabled", NoneType]
            When set to `"disabled"`, stops CSS animations, CSS transitions and Web Animations. Animations get different treatment
            depending on their duration:
            - finite animations are fast-forwarded to completion, so they'll fire `transitionend` event.
            - infinite animations are canceled to initial state, and then played over after the screenshot.

            Defaults to `"allow"` that leaves animations untouched.
        caret : Union["hide", "initial", NoneType]
            When set to `"hide"`, screenshot will hide text caret. When set to `"initial"`, text caret behavior will not be changed.
            Defaults to `"hide"`.
        scale : Union["css", "device", NoneType]
            When set to `"css"`, screenshot will have a single pixel per each css pixel on the page. For high-dpi devices, this will
            keep screenshots small. Using `"device"` option will produce a single pixel per each device pixel, so screenhots of
            high-dpi devices will be twice as large or even larger.

            Defaults to `"device"`.
        mask : Union[List[Locator], NoneType]
            Specify locators that should be masked when the screenshot is taken. Masked elements will be overlayed with a pink box
            `#FF00FF` that completely covers its bounding box.

        Returns
        -------
        bytes
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.screenshot(
                    timeout=timeout,
                    type=type,
                    path=path,
                    quality=quality,
                    omitBackground=omit_background,
                    fullPage=full_page,
                    clip=clip,
                    animations=animations,
                    caret=caret,
                    scale=scale,
                    mask=mapping.to_impl(mask),
                )
            )
        )

    def title(self) -> str:
        """Page.title

        Returns the page's title. Shortcut for main frame's `frame.title()`.

        Returns
        -------
        str
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.title()))

    def close(self, *, run_before_unload: bool = None) -> NoneType:
        """Page.close

        If `runBeforeUnload` is `false`, does not run any unload handlers and waits for the page to be closed. If
        `runBeforeUnload` is `true` the method will run unload handlers, but will **not** wait for the page to close.

        By default, `page.close()` **does not** run `beforeunload` handlers.

        > NOTE: if `runBeforeUnload` is passed as true, a `beforeunload` dialog might be summoned and should be handled manually
        via `page.on('dialog')` event.

        Parameters
        ----------
        run_before_unload : Union[bool, NoneType]
            Defaults to `false`. Whether to run the
            [before unload](https://developer.mozilla.org/en-US/docs/Web/Events/beforeunload) page handlers.
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.close(runBeforeUnload=run_before_unload))
        )

    def is_closed(self) -> bool:
        """Page.is_closed

        Indicates that the page has been closed.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(self._impl_obj.is_closed())

    def click(
        self,
        selector: str,
        *,
        modifiers: typing.Optional[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: Position = None,
        delay: float = None,
        button: Literal["left", "middle", "right"] = None,
        click_count: int = None,
        timeout: float = None,
        force: bool = None,
        no_wait_after: bool = None,
        trial: bool = None,
        strict: bool = None
    ) -> NoneType:
        """Page.click

        This method clicks an element matching `selector` by performing the following steps:
        1. Find an element matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the matched element, unless `force` option is set. If the
           element is detached during the checks, the whole action is retried.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to click in the center of the element, or the specified `position`.
        1. Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`. Passing
        zero timeout disables this.

        Shortcut for main frame's `frame.click()`.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        modifiers : Union[List[Union["Alt", "Control", "Meta", "Shift"]], NoneType]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores current
            modifiers back. If not specified, currently pressed modifiers are used.
        position : Union[{x: float, y: float}, NoneType]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the
            element.
        delay : Union[float, NoneType]
            Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        button : Union["left", "middle", "right", NoneType]
            Defaults to `left`.
        click_count : Union[int, NoneType]
            defaults to 1. See [UIEvent.detail].
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        trial : Union[bool, NoneType]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults to
            `false`. Useful to wait until the element is ready for the action without performing it.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.click(
                    selector=selector,
                    modifiers=mapping.to_impl(modifiers),
                    position=position,
                    delay=delay,
                    button=button,
                    clickCount=click_count,
                    timeout=timeout,
                    force=force,
                    noWaitAfter=no_wait_after,
                    trial=trial,
                    strict=strict,
                )
            )
        )

    def dblclick(
        self,
        selector: str,
        *,
        modifiers: typing.Optional[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: Position = None,
        delay: float = None,
        button: Literal["left", "middle", "right"] = None,
        timeout: float = None,
        force: bool = None,
        no_wait_after: bool = None,
        strict: bool = None,
        trial: bool = None
    ) -> NoneType:
        """Page.dblclick

        This method double clicks an element matching `selector` by performing the following steps:
        1. Find an element matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the matched element, unless `force` option is set. If the
           element is detached during the checks, the whole action is retried.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to double click in the center of the element, or the specified `position`.
        1. Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set. Note that if the
           first click of the `dblclick()` triggers a navigation event, this method will throw.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`. Passing
        zero timeout disables this.

        > NOTE: `page.dblclick()` dispatches two `click` events and a single `dblclick` event.

        Shortcut for main frame's `frame.dblclick()`.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        modifiers : Union[List[Union["Alt", "Control", "Meta", "Shift"]], NoneType]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores current
            modifiers back. If not specified, currently pressed modifiers are used.
        position : Union[{x: float, y: float}, NoneType]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the
            element.
        delay : Union[float, NoneType]
            Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        button : Union["left", "middle", "right", NoneType]
            Defaults to `left`.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        trial : Union[bool, NoneType]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults to
            `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.dblclick(
                    selector=selector,
                    modifiers=mapping.to_impl(modifiers),
                    position=position,
                    delay=delay,
                    button=button,
                    timeout=timeout,
                    force=force,
                    noWaitAfter=no_wait_after,
                    strict=strict,
                    trial=trial,
                )
            )
        )

    def tap(
        self,
        selector: str,
        *,
        modifiers: typing.Optional[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        no_wait_after: bool = None,
        strict: bool = None,
        trial: bool = None
    ) -> NoneType:
        """Page.tap

        This method taps an element matching `selector` by performing the following steps:
        1. Find an element matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the matched element, unless `force` option is set. If the
           element is detached during the checks, the whole action is retried.
        1. Scroll the element into view if needed.
        1. Use `page.touchscreen` to tap the center of the element, or the specified `position`.
        1. Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`. Passing
        zero timeout disables this.

        > NOTE: `page.tap()` requires that the `hasTouch` option of the browser context be set to true.

        Shortcut for main frame's `frame.tap()`.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        modifiers : Union[List[Union["Alt", "Control", "Meta", "Shift"]], NoneType]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores current
            modifiers back. If not specified, currently pressed modifiers are used.
        position : Union[{x: float, y: float}, NoneType]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the
            element.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        trial : Union[bool, NoneType]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults to
            `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.tap(
                    selector=selector,
                    modifiers=mapping.to_impl(modifiers),
                    position=position,
                    timeout=timeout,
                    force=force,
                    noWaitAfter=no_wait_after,
                    strict=strict,
                    trial=trial,
                )
            )
        )

    def fill(
        self,
        selector: str,
        value: str,
        *,
        timeout: float = None,
        no_wait_after: bool = None,
        strict: bool = None,
        force: bool = None
    ) -> NoneType:
        """Page.fill

        This method waits for an element matching `selector`, waits for [actionability](https://playwright.dev/python/docs/actionability) checks, focuses the
        element, fills it and triggers an `input` event after filling. Note that you can pass an empty string to clear the input
        field.

        If the target element is not an `<input>`, `<textarea>` or `[contenteditable]` element, this method throws an error.
        However, if the element is inside the `<label>` element that has an associated
        [control](https://developer.mozilla.org/en-US/docs/Web/API/HTMLLabelElement/control), the control will be filled
        instead.

        To send fine-grained keyboard events, use `page.type()`.

        Shortcut for main frame's `frame.fill()`.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        value : str
            Value to fill for the `<input>`, `<textarea>` or `[contenteditable]` element.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.fill(
                    selector=selector,
                    value=value,
                    timeout=timeout,
                    noWaitAfter=no_wait_after,
                    strict=strict,
                    force=force,
                )
            )
        )

    def locator(
        self,
        selector: str,
        *,
        has_text: typing.Union[str, typing.Pattern] = None,
        has: "Locator" = None
    ) -> "Locator":
        """Page.locator

        The method returns an element locator that can be used to perform actions on the page. Locator is resolved to the
        element immediately before performing an action, so a series of actions on the same locator can in fact be performed on
        different DOM elements. That would happen if the DOM structure between those actions has changed.

        [Learn more about locators](https://playwright.dev/python/docs/locators).

        Shortcut for main frame's `frame.locator()`.

        Parameters
        ----------
        selector : str
            A selector to use when resolving DOM element. See [working with selectors](../selectors.md) for more details.
        has_text : Union[Pattern, str, NoneType]
            Matches elements containing specified text somewhere inside, possibly in a child or a descendant element. When passed a
            [string], matching is case-insensitive and searches for a substring. For example, `"Playwright"` matches
            `<article><div>Playwright</div></article>`.
        has : Union[Locator, NoneType]
            Matches elements containing an element that matches an inner locator. Inner locator is queried against the outer one.
            For example, `article` that has `text=Playwright` matches `<article><div>Playwright</div></article>`.

            Note that outer and inner locators must belong to the same frame. Inner locator must not contain `FrameLocator`s.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(
            self._impl_obj.locator(
                selector=selector, has_text=has_text, has=has._impl_obj if has else None
            )
        )

    def frame_locator(self, selector: str) -> "FrameLocator":
        """Page.frame_locator

        When working with iframes, you can create a frame locator that will enter the iframe and allow selecting elements in
        that iframe. Following snippet locates element with text \"Submit\" in the iframe with id `my-frame`, like `<iframe
        id=\"my-frame\">`:

        ```py
        locator = page.frame_locator(\"#my-iframe\").locator(\"text=Submit\")
        locator.click()
        ```

        Parameters
        ----------
        selector : str
            A selector to use when resolving DOM element. See [working with selectors](../selectors.md) for more details.

        Returns
        -------
        FrameLocator
        """

        return mapping.from_impl(self._impl_obj.frame_locator(selector=selector))

    def focus(
        self, selector: str, *, strict: bool = None, timeout: float = None
    ) -> NoneType:
        """Page.focus

        This method fetches an element with `selector` and focuses it. If there's no element matching `selector`, the method
        waits until a matching element appears in the DOM.

        Shortcut for main frame's `frame.focus()`.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.focus(selector=selector, strict=strict, timeout=timeout)
            )
        )

    def text_content(
        self, selector: str, *, strict: bool = None, timeout: float = None
    ) -> typing.Optional[str]:
        """Page.text_content

        Returns `element.textContent`.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        Union[str, NoneType]
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.text_content(
                    selector=selector, strict=strict, timeout=timeout
                )
            )
        )

    def inner_text(
        self, selector: str, *, strict: bool = None, timeout: float = None
    ) -> str:
        """Page.inner_text

        Returns `element.innerText`.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        str
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.inner_text(
                    selector=selector, strict=strict, timeout=timeout
                )
            )
        )

    def inner_html(
        self, selector: str, *, strict: bool = None, timeout: float = None
    ) -> str:
        """Page.inner_html

        Returns `element.innerHTML`.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        str
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.inner_html(
                    selector=selector, strict=strict, timeout=timeout
                )
            )
        )

    def get_attribute(
        self, selector: str, name: str, *, strict: bool = None, timeout: float = None
    ) -> typing.Optional[str]:
        """Page.get_attribute

        Returns element attribute value.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        name : str
            Attribute name to get the value for.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        Union[str, NoneType]
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.get_attribute(
                    selector=selector, name=name, strict=strict, timeout=timeout
                )
            )
        )

    def hover(
        self,
        selector: str,
        *,
        modifiers: typing.Optional[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        strict: bool = None,
        trial: bool = None
    ) -> NoneType:
        """Page.hover

        This method hovers over an element matching `selector` by performing the following steps:
        1. Find an element matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the matched element, unless `force` option is set. If the
           element is detached during the checks, the whole action is retried.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to hover over the center of the element, or the specified `position`.
        1. Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`. Passing
        zero timeout disables this.

        Shortcut for main frame's `frame.hover()`.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        modifiers : Union[List[Union["Alt", "Control", "Meta", "Shift"]], NoneType]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores current
            modifiers back. If not specified, currently pressed modifiers are used.
        position : Union[{x: float, y: float}, NoneType]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the
            element.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        trial : Union[bool, NoneType]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults to
            `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.hover(
                    selector=selector,
                    modifiers=mapping.to_impl(modifiers),
                    position=position,
                    timeout=timeout,
                    force=force,
                    strict=strict,
                    trial=trial,
                )
            )
        )

    def drag_and_drop(
        self,
        source: str,
        target: str,
        *,
        source_position: Position = None,
        target_position: Position = None,
        force: bool = None,
        no_wait_after: bool = None,
        timeout: float = None,
        strict: bool = None,
        trial: bool = None
    ) -> NoneType:
        """Page.drag_and_drop

        Parameters
        ----------
        source : str
        target : str
        source_position : Union[{x: float, y: float}, NoneType]
            Clicks on the source element at this point relative to the top-left corner of the element's padding box. If not
            specified, some visible point of the element is used.
        target_position : Union[{x: float, y: float}, NoneType]
            Drops on the target element at this point relative to the top-left corner of the element's padding box. If not
            specified, some visible point of the element is used.
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        trial : Union[bool, NoneType]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults to
            `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.drag_and_drop(
                    source=source,
                    target=target,
                    sourcePosition=source_position,
                    targetPosition=target_position,
                    force=force,
                    noWaitAfter=no_wait_after,
                    timeout=timeout,
                    strict=strict,
                    trial=trial,
                )
            )
        )

    def select_option(
        self,
        selector: str,
        value: typing.Union[str, typing.List[str]] = None,
        *,
        index: typing.Union[int, typing.List[int]] = None,
        label: typing.Union[str, typing.List[str]] = None,
        element: typing.Union["ElementHandle", typing.List["ElementHandle"]] = None,
        timeout: float = None,
        no_wait_after: bool = None,
        force: bool = None,
        strict: bool = None
    ) -> typing.List[str]:
        """Page.select_option

        This method waits for an element matching `selector`, waits for [actionability](https://playwright.dev/python/docs/actionability) checks, waits until
        all specified options are present in the `<select>` element and selects these options.

        If the target element is not a `<select>` element, this method throws an error. However, if the element is inside the
        `<label>` element that has an associated
        [control](https://developer.mozilla.org/en-US/docs/Web/API/HTMLLabelElement/control), the control will be used instead.

        Returns the array of option values that have been successfully selected.

        Triggers a `change` and `input` event once all the provided options have been selected.

        ```py
        # single selection matching the value
        page.select_option(\"select#colors\", \"blue\")
        # single selection matching both the label
        page.select_option(\"select#colors\", label=\"blue\")
        # multiple selection
        page.select_option(\"select#colors\", value=[\"red\", \"green\", \"blue\"])
        ```

        Shortcut for main frame's `frame.select_option()`.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        value : Union[List[str], str, NoneType]
            Options to select by value. If the `<select>` has the `multiple` attribute, all given options are selected, otherwise
            only the first option matching one of the passed options is selected. Optional.
        index : Union[List[int], int, NoneType]
            Options to select by index. Optional.
        label : Union[List[str], str, NoneType]
            Options to select by label. If the `<select>` has the `multiple` attribute, all given options are selected, otherwise
            only the first option matching one of the passed options is selected. Optional.
        element : Union[ElementHandle, List[ElementHandle], NoneType]
            Option elements to select. Optional.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.

        Returns
        -------
        List[str]
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.select_option(
                    selector=selector,
                    value=mapping.to_impl(value),
                    index=mapping.to_impl(index),
                    label=mapping.to_impl(label),
                    element=mapping.to_impl(element),
                    timeout=timeout,
                    noWaitAfter=no_wait_after,
                    force=force,
                    strict=strict,
                )
            )
        )

    def input_value(
        self, selector: str, *, strict: bool = None, timeout: float = None
    ) -> str:
        """Page.input_value

        Returns `input.value` for the selected `<input>` or `<textarea>` or `<select>` element.

        Throws for non-input elements. However, if the element is inside the `<label>` element that has an associated
        [control](https://developer.mozilla.org/en-US/docs/Web/API/HTMLLabelElement/control), returns the value of the control.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        str
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.input_value(
                    selector=selector, strict=strict, timeout=timeout
                )
            )
        )

    def set_input_files(
        self,
        selector: str,
        files: typing.Union[
            str,
            pathlib.Path,
            FilePayload,
            typing.List[typing.Union[str, pathlib.Path]],
            typing.List[FilePayload],
        ],
        *,
        timeout: float = None,
        strict: bool = None,
        no_wait_after: bool = None
    ) -> NoneType:
        """Page.set_input_files

        Sets the value of the file input to these file paths or files. If some of the `filePaths` are relative paths, then they
        are resolved relative to the current working directory. For empty array, clears the selected files.

        This method expects `selector` to point to an
        [input element](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/input). However, if the element is inside the
        `<label>` element that has an associated
        [control](https://developer.mozilla.org/en-US/docs/Web/API/HTMLLabelElement/control), targets the control instead.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        files : Union[List[Union[pathlib.Path, str]], List[{name: str, mimeType: str, buffer: bytes}], pathlib.Path, str, {name: str, mimeType: str, buffer: bytes}]
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.set_input_files(
                    selector=selector,
                    files=mapping.to_impl(files),
                    timeout=timeout,
                    strict=strict,
                    noWaitAfter=no_wait_after,
                )
            )
        )

    def type(
        self,
        selector: str,
        text: str,
        *,
        delay: float = None,
        timeout: float = None,
        no_wait_after: bool = None,
        strict: bool = None
    ) -> NoneType:
        """Page.type

        Sends a `keydown`, `keypress`/`input`, and `keyup` event for each character in the text. `page.type` can be used to send
        fine-grained keyboard events. To fill values in form fields, use `page.fill()`.

        To press a special key, like `Control` or `ArrowDown`, use `keyboard.press()`.

        ```py
        page.type(\"#mytextarea\", \"hello\") # types instantly
        page.type(\"#mytextarea\", \"world\", delay=100) # types slower, like a user
        ```

        Shortcut for main frame's `frame.type()`.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        text : str
            A text to type into a focused element.
        delay : Union[float, NoneType]
            Time to wait between key presses in milliseconds. Defaults to 0.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.type(
                    selector=selector,
                    text=text,
                    delay=delay,
                    timeout=timeout,
                    noWaitAfter=no_wait_after,
                    strict=strict,
                )
            )
        )

    def press(
        self,
        selector: str,
        key: str,
        *,
        delay: float = None,
        timeout: float = None,
        no_wait_after: bool = None,
        strict: bool = None
    ) -> NoneType:
        """Page.press

        Focuses the element, and then uses `keyboard.down()` and `keyboard.up()`.

        `key` can specify the intended [keyboardEvent.key](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/key)
        value or a single character to generate the text for. A superset of the `key` values can be found
        [here](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/key/Key_Values). Examples of the keys are:

        `F1` - `F12`, `Digit0`- `Digit9`, `KeyA`- `KeyZ`, `Backquote`, `Minus`, `Equal`, `Backslash`, `Backspace`, `Tab`,
        `Delete`, `Escape`, `ArrowDown`, `End`, `Enter`, `Home`, `Insert`, `PageDown`, `PageUp`, `ArrowRight`, `ArrowUp`, etc.

        Following modification shortcuts are also supported: `Shift`, `Control`, `Alt`, `Meta`, `ShiftLeft`.

        Holding down `Shift` will type the text that corresponds to the `key` in the upper case.

        If `key` is a single character, it is case-sensitive, so the values `a` and `A` will generate different respective
        texts.

        Shortcuts such as `key: \"Control+o\"` or `key: \"Control+Shift+T\"` are supported as well. When specified with the
        modifier, modifier is pressed and being held while the subsequent key is being pressed.

        ```py
        page = browser.new_page()
        page.goto(\"https://keycode.info\")
        page.press(\"body\", \"A\")
        page.screenshot(path=\"a.png\")
        page.press(\"body\", \"ArrowLeft\")
        page.screenshot(path=\"arrow_left.png\")
        page.press(\"body\", \"Shift+O\")
        page.screenshot(path=\"o.png\")
        browser.close()
        ```

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        key : str
            Name of the key to press or a character to generate, such as `ArrowLeft` or `a`.
        delay : Union[float, NoneType]
            Time to wait between `keydown` and `keyup` in milliseconds. Defaults to 0.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.press(
                    selector=selector,
                    key=key,
                    delay=delay,
                    timeout=timeout,
                    noWaitAfter=no_wait_after,
                    strict=strict,
                )
            )
        )

    def check(
        self,
        selector: str,
        *,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        no_wait_after: bool = None,
        strict: bool = None,
        trial: bool = None
    ) -> NoneType:
        """Page.check

        This method checks an element matching `selector` by performing the following steps:
        1. Find an element matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        1. Ensure that matched element is a checkbox or a radio input. If not, this method throws. If the element is already
           checked, this method returns immediately.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the matched element, unless `force` option is set. If the
           element is detached during the checks, the whole action is retried.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to click in the center of the element.
        1. Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.
        1. Ensure that the element is now checked. If not, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`. Passing
        zero timeout disables this.

        Shortcut for main frame's `frame.check()`.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        position : Union[{x: float, y: float}, NoneType]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the
            element.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        trial : Union[bool, NoneType]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults to
            `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.check(
                    selector=selector,
                    position=position,
                    timeout=timeout,
                    force=force,
                    noWaitAfter=no_wait_after,
                    strict=strict,
                    trial=trial,
                )
            )
        )

    def uncheck(
        self,
        selector: str,
        *,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        no_wait_after: bool = None,
        strict: bool = None,
        trial: bool = None
    ) -> NoneType:
        """Page.uncheck

        This method unchecks an element matching `selector` by performing the following steps:
        1. Find an element matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        1. Ensure that matched element is a checkbox or a radio input. If not, this method throws. If the element is already
           unchecked, this method returns immediately.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the matched element, unless `force` option is set. If the
           element is detached during the checks, the whole action is retried.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to click in the center of the element.
        1. Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.
        1. Ensure that the element is now unchecked. If not, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`. Passing
        zero timeout disables this.

        Shortcut for main frame's `frame.uncheck()`.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        position : Union[{x: float, y: float}, NoneType]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the
            element.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        trial : Union[bool, NoneType]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults to
            `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.uncheck(
                    selector=selector,
                    position=position,
                    timeout=timeout,
                    force=force,
                    noWaitAfter=no_wait_after,
                    strict=strict,
                    trial=trial,
                )
            )
        )

    def wait_for_timeout(self, timeout: float) -> NoneType:
        """Page.wait_for_timeout

        Waits for the given `timeout` in milliseconds.

        Note that `page.waitForTimeout()` should only be used for debugging. Tests using the timer in production are going to be
        flaky. Use signals such as network events, selectors becoming visible and others instead.

        ```py
        # wait for 1 second
        page.wait_for_timeout(1000)
        ```

        Shortcut for main frame's `frame.wait_for_timeout()`.

        Parameters
        ----------
        timeout : float
            A timeout to wait for
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.wait_for_timeout(timeout=timeout))
        )

    def wait_for_function(
        self,
        expression: str,
        *,
        arg: typing.Any = None,
        timeout: float = None,
        polling: typing.Union[float, Literal["raf"]] = None
    ) -> "JSHandle":
        """Page.wait_for_function

        Returns when the `expression` returns a truthy value. It resolves to a JSHandle of the truthy value.

        The `page.wait_for_function()` can be used to observe viewport size change:

        ```py
        from playwright.sync_api import sync_playwright

        def run(playwright):
            webkit = playwright.webkit
            browser = webkit.launch()
            page = browser.new_page()
            page.evaluate(\"window.x = 0; setTimeout(() => { window.x = 100 }, 1000);\")
            page.wait_for_function(\"() => window.x > 0\")
            browser.close()

        with sync_playwright() as playwright:
            run(playwright)
        ```

        To pass an argument to the predicate of `page.wait_for_function()` function:

        ```py
        selector = \".foo\"
        page.wait_for_function(\"selector => !!document.querySelector(selector)\", selector)
        ```

        Shortcut for main frame's `frame.wait_for_function()`.

        Parameters
        ----------
        expression : str
            JavaScript expression to be evaluated in the browser context. If it looks like a function declaration, it is interpreted
            as a function. Otherwise, evaluated as an expression.
        arg : Union[Any, NoneType]
            Optional argument to pass to `expression`.
        timeout : Union[float, NoneType]
            maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default
            value can be changed by using the `browser_context.set_default_timeout()`.
        polling : Union["raf", float, NoneType]
            If `polling` is `'raf'`, then `expression` is constantly executed in `requestAnimationFrame` callback. If `polling` is a
            number, then it is treated as an interval in milliseconds at which the function would be executed. Defaults to `raf`.

        Returns
        -------
        JSHandle
        """

        return mapping.from_impl(
            self._sync(
                self._impl_obj.wait_for_function(
                    expression=expression,
                    arg=mapping.to_impl(arg),
                    timeout=timeout,
                    polling=polling,
                )
            )
        )

    def pause(self) -> NoneType:
        """Page.pause

        Pauses script execution. Playwright will stop executing the script and wait for the user to either press 'Resume' button
        in the page overlay or to call `playwright.resume()` in the DevTools console.

        User can inspect selectors or perform manual steps while paused. Resume will continue running the original script from
        the place it was paused.

        > NOTE: This method requires Playwright to be started in a headed mode, with a falsy `headless` value in the
        `browser_type.launch()`.
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.pause()))

    def pdf(
        self,
        *,
        scale: float = None,
        display_header_footer: bool = None,
        header_template: str = None,
        footer_template: str = None,
        print_background: bool = None,
        landscape: bool = None,
        page_ranges: str = None,
        format: str = None,
        width: typing.Union[str, float] = None,
        height: typing.Union[str, float] = None,
        prefer_css_page_size: bool = None,
        margin: PdfMargins = None,
        path: typing.Union[str, pathlib.Path] = None
    ) -> bytes:
        """Page.pdf

        Returns the PDF buffer.

        > NOTE: Generating a pdf is currently only supported in Chromium headless.

        `page.pdf()` generates a pdf of the page with `print` css media. To generate a pdf with `screen` media, call
        `page.emulate_media()` before calling `page.pdf()`:

        > NOTE: By default, `page.pdf()` generates a pdf with modified colors for printing. Use the
        [`-webkit-print-color-adjust`](https://developer.mozilla.org/en-US/docs/Web/CSS/-webkit-print-color-adjust) property to
        force rendering of exact colors.

        ```py
        # generates a pdf with \"screen\" media type.
        page.emulate_media(media=\"screen\")
        page.pdf(path=\"page.pdf\")
        ```

        The `width`, `height`, and `margin` options accept values labeled with units. Unlabeled values are treated as pixels.

        A few examples:
        - `page.pdf({width: 100})` - prints with width set to 100 pixels
        - `page.pdf({width: '100px'})` - prints with width set to 100 pixels
        - `page.pdf({width: '10cm'})` - prints with width set to 10 centimeters.

        All possible units are:
        - `px` - pixel
        - `in` - inch
        - `cm` - centimeter
        - `mm` - millimeter

        The `format` options are:
        - `Letter`: 8.5in x 11in
        - `Legal`: 8.5in x 14in
        - `Tabloid`: 11in x 17in
        - `Ledger`: 17in x 11in
        - `A0`: 33.1in x 46.8in
        - `A1`: 23.4in x 33.1in
        - `A2`: 16.54in x 23.4in
        - `A3`: 11.7in x 16.54in
        - `A4`: 8.27in x 11.7in
        - `A5`: 5.83in x 8.27in
        - `A6`: 4.13in x 5.83in

        > NOTE: `headerTemplate` and `footerTemplate` markup have the following limitations: > 1. Script tags inside templates
        are not evaluated. > 2. Page styles are not visible inside templates.

        Parameters
        ----------
        scale : Union[float, NoneType]
            Scale of the webpage rendering. Defaults to `1`. Scale amount must be between 0.1 and 2.
        display_header_footer : Union[bool, NoneType]
            Display header and footer. Defaults to `false`.
        header_template : Union[str, NoneType]
            HTML template for the print header. Should be valid HTML markup with following classes used to inject printing values
            into them:
            - `'date'` formatted print date
            - `'title'` document title
            - `'url'` document location
            - `'pageNumber'` current page number
            - `'totalPages'` total pages in the document
        footer_template : Union[str, NoneType]
            HTML template for the print footer. Should use the same format as the `headerTemplate`.
        print_background : Union[bool, NoneType]
            Print background graphics. Defaults to `false`.
        landscape : Union[bool, NoneType]
            Paper orientation. Defaults to `false`.
        page_ranges : Union[str, NoneType]
            Paper ranges to print, e.g., '1-5, 8, 11-13'. Defaults to the empty string, which means print all pages.
        format : Union[str, NoneType]
            Paper format. If set, takes priority over `width` or `height` options. Defaults to 'Letter'.
        width : Union[float, str, NoneType]
            Paper width, accepts values labeled with units.
        height : Union[float, str, NoneType]
            Paper height, accepts values labeled with units.
        prefer_css_page_size : Union[bool, NoneType]
            Give any CSS `@page` size declared in the page priority over what is declared in `width` and `height` or `format`
            options. Defaults to `false`, which will scale the content to fit the paper size.
        margin : Union[{top: Union[float, str, NoneType], right: Union[float, str, NoneType], bottom: Union[float, str, NoneType], left: Union[float, str, NoneType]}, NoneType]
            Paper margins, defaults to none.
        path : Union[pathlib.Path, str, NoneType]
            The file path to save the PDF to. If `path` is a relative path, then it is resolved relative to the current working
            directory. If no path is provided, the PDF won't be saved to the disk.

        Returns
        -------
        bytes
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.pdf(
                    scale=scale,
                    displayHeaderFooter=display_header_footer,
                    headerTemplate=header_template,
                    footerTemplate=footer_template,
                    printBackground=print_background,
                    landscape=landscape,
                    pageRanges=page_ranges,
                    format=format,
                    width=width,
                    height=height,
                    preferCSSPageSize=prefer_css_page_size,
                    margin=margin,
                    path=path,
                )
            )
        )

    def expect_event(
        self, event: str, predicate: typing.Callable = None, *, timeout: float = None
    ) -> EventContextManager:
        """Page.expect_event

        Waits for event to fire and passes its value into the predicate function. Returns when the predicate returns truthy
        value. Will throw an error if the page is closed before the event is fired. Returns the event data value.

        ```py
        with page.expect_event(\"framenavigated\") as event_info:
            page.click(\"button\")
        frame = event_info.value
        ```

        Parameters
        ----------
        event : str
            Event name, same one typically passed into `*.on(event)`.
        predicate : Union[Callable, NoneType]
            Receives the event data and resolves to truthy value when the waiting should resolve.
        timeout : Union[float, NoneType]
            Maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default
            value can be changed by using the `browser_context.set_default_timeout()`.

        Returns
        -------
        EventContextManager
        """
        return EventContextManager(
            self,
            self._impl_obj.expect_event(
                event=event, predicate=self._wrap_handler(predicate), timeout=timeout
            ).future,
        )

    def expect_console_message(
        self,
        predicate: typing.Optional[typing.Callable[["ConsoleMessage"], bool]] = None,
        *,
        timeout: float = None
    ) -> EventContextManager["ConsoleMessage"]:
        """Page.expect_console_message

        Performs action and waits for a `ConsoleMessage` to be logged by in the page. If predicate is provided, it passes
        `ConsoleMessage` value into the `predicate` function and waits for `predicate(message)` to return a truthy value. Will
        throw an error if the page is closed before the `page.on('console')` event is fired.

        Parameters
        ----------
        predicate : Union[Callable[[ConsoleMessage], bool], NoneType]
            Receives the `ConsoleMessage` object and resolves to truthy value when the waiting should resolve.
        timeout : Union[float, NoneType]
            Maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default
            value can be changed by using the `browser_context.set_default_timeout()`.

        Returns
        -------
        EventContextManager[ConsoleMessage]
        """
        return EventContextManager(
            self,
            self._impl_obj.expect_console_message(
                predicate=self._wrap_handler(predicate), timeout=timeout
            ).future,
        )

    def expect_download(
        self,
        predicate: typing.Optional[typing.Callable[["Download"], bool]] = None,
        *,
        timeout: float = None
    ) -> EventContextManager["Download"]:
        """Page.expect_download

        Performs action and waits for a new `Download`. If predicate is provided, it passes `Download` value into the
        `predicate` function and waits for `predicate(download)` to return a truthy value. Will throw an error if the page is
        closed before the download event is fired.

        Parameters
        ----------
        predicate : Union[Callable[[Download], bool], NoneType]
            Receives the `Download` object and resolves to truthy value when the waiting should resolve.
        timeout : Union[float, NoneType]
            Maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default
            value can be changed by using the `browser_context.set_default_timeout()`.

        Returns
        -------
        EventContextManager[Download]
        """
        return EventContextManager(
            self,
            self._impl_obj.expect_download(
                predicate=self._wrap_handler(predicate), timeout=timeout
            ).future,
        )

    def expect_file_chooser(
        self,
        predicate: typing.Optional[typing.Callable[["FileChooser"], bool]] = None,
        *,
        timeout: float = None
    ) -> EventContextManager["FileChooser"]:
        """Page.expect_file_chooser

        Performs action and waits for a new `FileChooser` to be created. If predicate is provided, it passes `FileChooser` value
        into the `predicate` function and waits for `predicate(fileChooser)` to return a truthy value. Will throw an error if
        the page is closed before the file chooser is opened.

        Parameters
        ----------
        predicate : Union[Callable[[FileChooser], bool], NoneType]
            Receives the `FileChooser` object and resolves to truthy value when the waiting should resolve.
        timeout : Union[float, NoneType]
            Maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default
            value can be changed by using the `browser_context.set_default_timeout()`.

        Returns
        -------
        EventContextManager[FileChooser]
        """
        return EventContextManager(
            self,
            self._impl_obj.expect_file_chooser(
                predicate=self._wrap_handler(predicate), timeout=timeout
            ).future,
        )

    def expect_navigation(
        self,
        *,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]] = None,
        wait_until: Literal["commit", "domcontentloaded", "load", "networkidle"] = None,
        timeout: float = None
    ) -> EventContextManager["Response"]:
        """Page.expect_navigation

        Waits for the main frame navigation and returns the main resource response. In case of multiple redirects, the
        navigation will resolve with the response of the last redirect. In case of navigation to a different anchor or
        navigation due to History API usage, the navigation will resolve with `null`.

        This resolves when the page navigates to a new URL or reloads. It is useful for when you run code which will indirectly
        cause the page to navigate. e.g. The click target has an `onclick` handler that triggers navigation from a `setTimeout`.
        Consider this example:

        ```py
        with page.expect_navigation():
            page.click(\"a.delayed-navigation\") # clicking the link will indirectly cause a navigation
        # Resolves after navigation has finished
        ```

        > NOTE: Usage of the [History API](https://developer.mozilla.org/en-US/docs/Web/API/History_API) to change the URL is
        considered a navigation.

        Shortcut for main frame's `frame.expect_navigation()`.

        Parameters
        ----------
        url : Union[Callable[[str], bool], Pattern, str, NoneType]
            A glob pattern, regex pattern or predicate receiving [URL] to match while waiting for the navigation. Note that if the
            parameter is a string without wildcard characters, the method will wait for navigation to URL that is exactly equal to
            the string.
        wait_until : Union["commit", "domcontentloaded", "load", "networkidle", NoneType]
            When to consider operation succeeded, defaults to `load`. Events can be either:
            - `'domcontentloaded'` - consider operation to be finished when the `DOMContentLoaded` event is fired.
            - `'load'` - consider operation to be finished when the `load` event is fired.
            - `'networkidle'` - consider operation to be finished when there are no network connections for at least `500` ms.
            - `'commit'` - consider operation to be finished when network response is received and the document started loading.
        timeout : Union[float, NoneType]
            Maximum operation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be
            changed by using the `browser_context.set_default_navigation_timeout()`,
            `browser_context.set_default_timeout()`, `page.set_default_navigation_timeout()` or
            `page.set_default_timeout()` methods.

        Returns
        -------
        EventContextManager[Response]
        """
        return EventContextManager(
            self,
            self._impl_obj.expect_navigation(
                url=self._wrap_handler(url), wait_until=wait_until, timeout=timeout
            ).future,
        )

    def expect_popup(
        self,
        predicate: typing.Optional[typing.Callable[["Page"], bool]] = None,
        *,
        timeout: float = None
    ) -> EventContextManager["Page"]:
        """Page.expect_popup

        Performs action and waits for a popup `Page`. If predicate is provided, it passes [Popup] value into the `predicate`
        function and waits for `predicate(page)` to return a truthy value. Will throw an error if the page is closed before the
        popup event is fired.

        Parameters
        ----------
        predicate : Union[Callable[[Page], bool], NoneType]
            Receives the `Page` object and resolves to truthy value when the waiting should resolve.
        timeout : Union[float, NoneType]
            Maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default
            value can be changed by using the `browser_context.set_default_timeout()`.

        Returns
        -------
        EventContextManager[Page]
        """
        return EventContextManager(
            self,
            self._impl_obj.expect_popup(
                predicate=self._wrap_handler(predicate), timeout=timeout
            ).future,
        )

    def expect_request(
        self,
        url_or_predicate: typing.Union[
            str, typing.Pattern, typing.Callable[["Request"], bool]
        ],
        *,
        timeout: float = None
    ) -> EventContextManager["Request"]:
        """Page.expect_request

        Waits for the matching request and returns it. See [waiting for event](https://playwright.dev/python/docs/events#waiting-for-event) for more details
        about events.

        ```py
        with page.expect_request(\"http://example.com/resource\") as first:
            page.click('button')
        first_request = first.value

        # or with a lambda
        with page.expect_request(lambda request: request.url == \"http://example.com\" and request.method == \"get\") as second:
            page.click('img')
        second_request = second.value
        ```

        Parameters
        ----------
        url_or_predicate : Union[Callable[[Request], bool], Pattern, str]
            Request URL string, regex or predicate receiving `Request` object. When a `baseURL` via the context options was provided
            and the passed URL is a path, it gets merged via the
            [`new URL()`](https://developer.mozilla.org/en-US/docs/Web/API/URL/URL) constructor.
        timeout : Union[float, NoneType]
            Maximum wait time in milliseconds, defaults to 30 seconds, pass `0` to disable the timeout. The default value can be
            changed by using the `page.set_default_timeout()` method.

        Returns
        -------
        EventContextManager[Request]
        """
        return EventContextManager(
            self,
            self._impl_obj.expect_request(
                url_or_predicate=self._wrap_handler(url_or_predicate), timeout=timeout
            ).future,
        )

    def expect_request_finished(
        self,
        predicate: typing.Optional[typing.Callable[["Request"], bool]] = None,
        *,
        timeout: float = None
    ) -> EventContextManager["Request"]:
        """Page.expect_request_finished

        Performs action and waits for a `Request` to finish loading. If predicate is provided, it passes `Request` value into
        the `predicate` function and waits for `predicate(request)` to return a truthy value. Will throw an error if the page is
        closed before the `page.on('request_finished')` event is fired.

        Parameters
        ----------
        predicate : Union[Callable[[Request], bool], NoneType]
            Receives the `Request` object and resolves to truthy value when the waiting should resolve.
        timeout : Union[float, NoneType]
            Maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default
            value can be changed by using the `browser_context.set_default_timeout()`.

        Returns
        -------
        EventContextManager[Request]
        """
        return EventContextManager(
            self,
            self._impl_obj.expect_request_finished(
                predicate=self._wrap_handler(predicate), timeout=timeout
            ).future,
        )

    def expect_response(
        self,
        url_or_predicate: typing.Union[
            str, typing.Pattern, typing.Callable[["Response"], bool]
        ],
        *,
        timeout: float = None
    ) -> EventContextManager["Response"]:
        """Page.expect_response

        Returns the matched response. See [waiting for event](https://playwright.dev/python/docs/events#waiting-for-event) for more details about events.

        ```py
        with page.expect_response(\"https://example.com/resource\") as response_info:
            page.click(\"input\")
        response = response_info.value
        return response.ok

        # or with a lambda
        with page.expect_response(lambda response: response.url == \"https://example.com\" and response.status == 200) as response_info:
            page.click(\"input\")
        response = response_info.value
        return response.ok
        ```

        Parameters
        ----------
        url_or_predicate : Union[Callable[[Response], bool], Pattern, str]
            Request URL string, regex or predicate receiving `Response` object. When a `baseURL` via the context options was
            provided and the passed URL is a path, it gets merged via the
            [`new URL()`](https://developer.mozilla.org/en-US/docs/Web/API/URL/URL) constructor.
        timeout : Union[float, NoneType]
            Maximum wait time in milliseconds, defaults to 30 seconds, pass `0` to disable the timeout. The default value can be
            changed by using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        EventContextManager[Response]
        """
        return EventContextManager(
            self,
            self._impl_obj.expect_response(
                url_or_predicate=self._wrap_handler(url_or_predicate), timeout=timeout
            ).future,
        )

    def expect_websocket(
        self,
        predicate: typing.Optional[typing.Callable[["WebSocket"], bool]] = None,
        *,
        timeout: float = None
    ) -> EventContextManager["WebSocket"]:
        """Page.expect_websocket

        Performs action and waits for a new `WebSocket`. If predicate is provided, it passes `WebSocket` value into the
        `predicate` function and waits for `predicate(webSocket)` to return a truthy value. Will throw an error if the page is
        closed before the WebSocket event is fired.

        Parameters
        ----------
        predicate : Union[Callable[[WebSocket], bool], NoneType]
            Receives the `WebSocket` object and resolves to truthy value when the waiting should resolve.
        timeout : Union[float, NoneType]
            Maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default
            value can be changed by using the `browser_context.set_default_timeout()`.

        Returns
        -------
        EventContextManager[WebSocket]
        """
        return EventContextManager(
            self,
            self._impl_obj.expect_websocket(
                predicate=self._wrap_handler(predicate), timeout=timeout
            ).future,
        )

    def expect_worker(
        self,
        predicate: typing.Optional[typing.Callable[["Worker"], bool]] = None,
        *,
        timeout: float = None
    ) -> EventContextManager["Worker"]:
        """Page.expect_worker

        Performs action and waits for a new `Worker`. If predicate is provided, it passes `Worker` value into the `predicate`
        function and waits for `predicate(worker)` to return a truthy value. Will throw an error if the page is closed before
        the worker event is fired.

        Parameters
        ----------
        predicate : Union[Callable[[Worker], bool], NoneType]
            Receives the `Worker` object and resolves to truthy value when the waiting should resolve.
        timeout : Union[float, NoneType]
            Maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default
            value can be changed by using the `browser_context.set_default_timeout()`.

        Returns
        -------
        EventContextManager[Worker]
        """
        return EventContextManager(
            self,
            self._impl_obj.expect_worker(
                predicate=self._wrap_handler(predicate), timeout=timeout
            ).future,
        )

    def set_checked(
        self,
        selector: str,
        checked: bool,
        *,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        no_wait_after: bool = None,
        strict: bool = None,
        trial: bool = None
    ) -> NoneType:
        """Page.set_checked

        This method checks or unchecks an element matching `selector` by performing the following steps:
        1. Find an element matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        1. Ensure that matched element is a checkbox or a radio input. If not, this method throws.
        1. If the element already has the right checked state, this method returns immediately.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the matched element, unless `force` option is set. If the
           element is detached during the checks, the whole action is retried.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to click in the center of the element.
        1. Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.
        1. Ensure that the element is now checked or unchecked. If not, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`. Passing
        zero timeout disables this.

        Shortcut for main frame's `frame.set_checked()`.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be used. See
            [working with selectors](../selectors.md) for more details.
        checked : bool
            Whether to check or uncheck the checkbox.
        position : Union[{x: float, y: float}, NoneType]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the
            element.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        strict : Union[bool, NoneType]
            When true, the call requires selector to resolve to a single element. If given selector resolves to more then one
            element, the call throws an exception.
        trial : Union[bool, NoneType]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults to
            `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.set_checked(
                    selector=selector,
                    checked=checked,
                    position=position,
                    timeout=timeout,
                    force=force,
                    noWaitAfter=no_wait_after,
                    strict=strict,
                    trial=trial,
                )
            )
        )


mapping.register(PageImpl, Page)


class BrowserContext(SyncContextManager):
    @typing.overload
    def on(
        self, event: Literal["backgroundpage"], f: typing.Callable[["Page"], "None"]
    ) -> None:
        """
        > NOTE: Only works with Chromium browser's persistent context.

        Emitted when new background page is created in the context.

        ```py
        background_page = context.wait_for_event(\"backgroundpage\")
        ```"""

    @typing.overload
    def on(
        self, event: Literal["close"], f: typing.Callable[["BrowserContext"], "None"]
    ) -> None:
        """
        Emitted when Browser context gets closed. This might happen because of one of the following:
        - Browser context is closed.
        - Browser application is closed or crashed.
        - The `browser.close()` method was called."""

    @typing.overload
    def on(self, event: Literal["page"], f: typing.Callable[["Page"], "None"]) -> None:
        """
        The event is emitted when a new Page is created in the BrowserContext. The page may still be loading. The event will
        also fire for popup pages. See also `page.on('popup')` to receive events about popups relevant to a specific page.

        The earliest moment that page is available is when it has navigated to the initial url. For example, when opening a
        popup with `window.open('http://example.com')`, this event will fire when the network request to \"http://example.com\" is
        done and its response has started loading in the popup.

        ```py
        with context.expect_page() as page_info:
            page.click(\"a[target=_blank]\"),
        page = page_info.value
        print(page.evaluate(\"location.href\"))
        ```

        > NOTE: Use `page.wait_for_load_state()` to wait until the page gets to a particular state (you should not need it
        in most cases)."""

    @typing.overload
    def on(
        self, event: Literal["request"], f: typing.Callable[["Request"], "None"]
    ) -> None:
        """
        Emitted when a request is issued from any pages created through this context. The [request] object is read-only. To only
        listen for requests from a particular page, use `page.on('request')`.

        In order to intercept and mutate requests, see `browser_context.route()` or `page.route()`."""

    @typing.overload
    def on(
        self, event: Literal["requestfailed"], f: typing.Callable[["Request"], "None"]
    ) -> None:
        """
        Emitted when a request fails, for example by timing out. To only listen for failed requests from a particular page, use
        `page.on('request_failed')`.

        > NOTE: HTTP Error responses, such as 404 or 503, are still successful responses from HTTP standpoint, so request will
        complete with `browser_context.on('request_finished')` event and not with `browser_context.on('request_failed')`."""

    @typing.overload
    def on(
        self, event: Literal["requestfinished"], f: typing.Callable[["Request"], "None"]
    ) -> None:
        """
        Emitted when a request finishes successfully after downloading the response body. For a successful response, the
        sequence of events is `request`, `response` and `requestfinished`. To listen for successful requests from a particular
        page, use `page.on('request_finished')`."""

    @typing.overload
    def on(
        self, event: Literal["response"], f: typing.Callable[["Response"], "None"]
    ) -> None:
        """
        Emitted when [response] status and headers are received for a request. For a successful response, the sequence of events
        is `request`, `response` and `requestfinished`. To listen for response events from a particular page, use
        `page.on('response')`."""

    @typing.overload
    def on(
        self, event: Literal["serviceworker"], f: typing.Callable[["Worker"], "None"]
    ) -> None:
        """
        > NOTE: Service workers are only supported on Chromium-based browsers.

        Emitted when new service worker is created in the context."""

    def on(self, event: str, f: typing.Callable[..., None]) -> None:
        return super().on(event=event, f=f)

    @typing.overload
    def once(
        self, event: Literal["backgroundpage"], f: typing.Callable[["Page"], "None"]
    ) -> None:
        """
        > NOTE: Only works with Chromium browser's persistent context.

        Emitted when new background page is created in the context.

        ```py
        background_page = context.wait_for_event(\"backgroundpage\")
        ```"""

    @typing.overload
    def once(
        self, event: Literal["close"], f: typing.Callable[["BrowserContext"], "None"]
    ) -> None:
        """
        Emitted when Browser context gets closed. This might happen because of one of the following:
        - Browser context is closed.
        - Browser application is closed or crashed.
        - The `browser.close()` method was called."""

    @typing.overload
    def once(
        self, event: Literal["page"], f: typing.Callable[["Page"], "None"]
    ) -> None:
        """
        The event is emitted when a new Page is created in the BrowserContext. The page may still be loading. The event will
        also fire for popup pages. See also `page.on('popup')` to receive events about popups relevant to a specific page.

        The earliest moment that page is available is when it has navigated to the initial url. For example, when opening a
        popup with `window.open('http://example.com')`, this event will fire when the network request to \"http://example.com\" is
        done and its response has started loading in the popup.

        ```py
        with context.expect_page() as page_info:
            page.click(\"a[target=_blank]\"),
        page = page_info.value
        print(page.evaluate(\"location.href\"))
        ```

        > NOTE: Use `page.wait_for_load_state()` to wait until the page gets to a particular state (you should not need it
        in most cases)."""

    @typing.overload
    def once(
        self, event: Literal["request"], f: typing.Callable[["Request"], "None"]
    ) -> None:
        """
        Emitted when a request is issued from any pages created through this context. The [request] object is read-only. To only
        listen for requests from a particular page, use `page.on('request')`.

        In order to intercept and mutate requests, see `browser_context.route()` or `page.route()`."""

    @typing.overload
    def once(
        self, event: Literal["requestfailed"], f: typing.Callable[["Request"], "None"]
    ) -> None:
        """
        Emitted when a request fails, for example by timing out. To only listen for failed requests from a particular page, use
        `page.on('request_failed')`.

        > NOTE: HTTP Error responses, such as 404 or 503, are still successful responses from HTTP standpoint, so request will
        complete with `browser_context.on('request_finished')` event and not with `browser_context.on('request_failed')`."""

    @typing.overload
    def once(
        self, event: Literal["requestfinished"], f: typing.Callable[["Request"], "None"]
    ) -> None:
        """
        Emitted when a request finishes successfully after downloading the response body. For a successful response, the
        sequence of events is `request`, `response` and `requestfinished`. To listen for successful requests from a particular
        page, use `page.on('request_finished')`."""

    @typing.overload
    def once(
        self, event: Literal["response"], f: typing.Callable[["Response"], "None"]
    ) -> None:
        """
        Emitted when [response] status and headers are received for a request. For a successful response, the sequence of events
        is `request`, `response` and `requestfinished`. To listen for response events from a particular page, use
        `page.on('response')`."""

    @typing.overload
    def once(
        self, event: Literal["serviceworker"], f: typing.Callable[["Worker"], "None"]
    ) -> None:
        """
        > NOTE: Service workers are only supported on Chromium-based browsers.

        Emitted when new service worker is created in the context."""

    def once(self, event: str, f: typing.Callable[..., None]) -> None:
        return super().once(event=event, f=f)

    @property
    def pages(self) -> typing.List["Page"]:
        """BrowserContext.pages

        Returns all open pages in the context.

        Returns
        -------
        List[Page]
        """
        return mapping.from_impl_list(self._impl_obj.pages)

    @property
    def browser(self) -> typing.Optional["Browser"]:
        """BrowserContext.browser

        Returns the browser instance of the context. If it was launched as a persistent context null gets returned.

        Returns
        -------
        Union[Browser, NoneType]
        """
        return mapping.from_impl_nullable(self._impl_obj.browser)

    @property
    def background_pages(self) -> typing.List["Page"]:
        """BrowserContext.background_pages

        > NOTE: Background pages are only supported on Chromium-based browsers.

        All existing background pages in the context.

        Returns
        -------
        List[Page]
        """
        return mapping.from_impl_list(self._impl_obj.background_pages)

    @property
    def service_workers(self) -> typing.List["Worker"]:
        """BrowserContext.service_workers

        > NOTE: Service workers are only supported on Chromium-based browsers.

        All existing service workers in the context.

        Returns
        -------
        List[Worker]
        """
        return mapping.from_impl_list(self._impl_obj.service_workers)

    @property
    def tracing(self) -> "Tracing":
        """BrowserContext.tracing

        Returns
        -------
        Tracing
        """
        return mapping.from_impl(self._impl_obj.tracing)

    @property
    def request(self) -> "APIRequestContext":
        """BrowserContext.request

        API testing helper associated with this context. Requests made with this API will use context cookies.

        Returns
        -------
        APIRequestContext
        """
        return mapping.from_impl(self._impl_obj.request)

    def set_default_navigation_timeout(self, timeout: float) -> NoneType:
        """BrowserContext.set_default_navigation_timeout

        This setting will change the default maximum navigation time for the following methods and related shortcuts:
        - `page.go_back()`
        - `page.go_forward()`
        - `page.goto()`
        - `page.reload()`
        - `page.set_content()`
        - `page.expect_navigation()`

        > NOTE: `page.set_default_navigation_timeout()` and `page.set_default_timeout()` take priority over
        `browser_context.set_default_navigation_timeout()`.

        Parameters
        ----------
        timeout : float
            Maximum navigation time in milliseconds
        """

        return mapping.from_maybe_impl(
            self._impl_obj.set_default_navigation_timeout(timeout=timeout)
        )

    def set_default_timeout(self, timeout: float) -> NoneType:
        """BrowserContext.set_default_timeout

        This setting will change the default maximum time for all the methods accepting `timeout` option.

        > NOTE: `page.set_default_navigation_timeout()`, `page.set_default_timeout()` and
        `browser_context.set_default_navigation_timeout()` take priority over `browser_context.set_default_timeout()`.

        Parameters
        ----------
        timeout : float
            Maximum time in milliseconds
        """

        return mapping.from_maybe_impl(
            self._impl_obj.set_default_timeout(timeout=timeout)
        )

    def new_page(self) -> "Page":
        """BrowserContext.new_page

        Creates a new page in the browser context.

        Returns
        -------
        Page
        """

        return mapping.from_impl(self._sync(self._impl_obj.new_page()))

    def cookies(
        self, urls: typing.Union[str, typing.List[str]] = None
    ) -> typing.List[Cookie]:
        """BrowserContext.cookies

        If no URLs are specified, this method returns all cookies. If URLs are specified, only cookies that affect those URLs
        are returned.

        Parameters
        ----------
        urls : Union[List[str], str, NoneType]
            Optional list of URLs.

        Returns
        -------
        List[{name: str, value: str, domain: str, path: str, expires: float, httpOnly: bool, secure: bool, sameSite: Union["Lax", "None", "Strict"]}]
        """

        return mapping.from_impl_list(
            self._sync(self._impl_obj.cookies(urls=mapping.to_impl(urls)))
        )

    def add_cookies(self, cookies: typing.List[SetCookieParam]) -> NoneType:
        """BrowserContext.add_cookies

        Adds cookies into this browser context. All pages within this context will have these cookies installed. Cookies can be
        obtained via `browser_context.cookies()`.

        ```py
        browser_context.add_cookies([cookie_object1, cookie_object2])
        ```

        Parameters
        ----------
        cookies : List[{name: str, value: str, url: Union[str, NoneType], domain: Union[str, NoneType], path: Union[str, NoneType], expires: Union[float, NoneType], httpOnly: Union[bool, NoneType], secure: Union[bool, NoneType], sameSite: Union["Lax", "None", "Strict", NoneType]}]
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.add_cookies(cookies=mapping.to_impl(cookies)))
        )

    def clear_cookies(self) -> NoneType:
        """BrowserContext.clear_cookies

        Clears context cookies.
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.clear_cookies()))

    def grant_permissions(
        self, permissions: typing.List[str], *, origin: str = None
    ) -> NoneType:
        """BrowserContext.grant_permissions

        Grants specified permissions to the browser context. Only grants corresponding permissions to the given origin if
        specified.

        Parameters
        ----------
        permissions : List[str]
            A permission or an array of permissions to grant. Permissions can be one of the following values:
            - `'geolocation'`
            - `'midi'`
            - `'midi-sysex'` (system-exclusive midi)
            - `'notifications'`
            - `'camera'`
            - `'microphone'`
            - `'background-sync'`
            - `'ambient-light-sensor'`
            - `'accelerometer'`
            - `'gyroscope'`
            - `'magnetometer'`
            - `'accessibility-events'`
            - `'clipboard-read'`
            - `'clipboard-write'`
            - `'payment-handler'`
        origin : Union[str, NoneType]
            The [origin] to grant permissions to, e.g. "https://example.com".
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.grant_permissions(
                    permissions=mapping.to_impl(permissions), origin=origin
                )
            )
        )

    def clear_permissions(self) -> NoneType:
        """BrowserContext.clear_permissions

        Clears all permission overrides for the browser context.

        ```py
        context = browser.new_context()
        context.grant_permissions([\"clipboard-read\"])
        # do stuff ..
        context.clear_permissions()
        ```
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.clear_permissions()))

    def set_geolocation(self, geolocation: Geolocation = None) -> NoneType:
        """BrowserContext.set_geolocation

        Sets the context's geolocation. Passing `null` or `undefined` emulates position unavailable.

        ```py
        browser_context.set_geolocation({\"latitude\": 59.95, \"longitude\": 30.31667})
        ```

        > NOTE: Consider using `browser_context.grant_permissions()` to grant permissions for the browser context pages to
        read its geolocation.

        Parameters
        ----------
        geolocation : Union[{latitude: float, longitude: float, accuracy: Union[float, NoneType]}, NoneType]
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.set_geolocation(geolocation=geolocation))
        )

    def set_extra_http_headers(self, headers: typing.Dict[str, str]) -> NoneType:
        """BrowserContext.set_extra_http_headers

        The extra HTTP headers will be sent with every request initiated by any page in the context. These headers are merged
        with page-specific extra HTTP headers set with `page.set_extra_http_headers()`. If page overrides a particular
        header, page-specific header value will be used instead of the browser context header value.

        > NOTE: `browser_context.set_extra_http_headers()` does not guarantee the order of headers in the outgoing requests.

        Parameters
        ----------
        headers : Dict[str, str]
            An object containing additional HTTP headers to be sent with every request. All header values must be strings.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.set_extra_http_headers(headers=mapping.to_impl(headers))
            )
        )

    def set_offline(self, offline: bool) -> NoneType:
        """BrowserContext.set_offline

        Parameters
        ----------
        offline : bool
            Whether to emulate network being offline for the browser context.
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.set_offline(offline=offline))
        )

    def add_init_script(
        self, script: str = None, *, path: typing.Union[str, pathlib.Path] = None
    ) -> NoneType:
        """BrowserContext.add_init_script

        Adds a script which would be evaluated in one of the following scenarios:
        - Whenever a page is created in the browser context or is navigated.
        - Whenever a child frame is attached or navigated in any page in the browser context. In this case, the script is
          evaluated in the context of the newly attached frame.

        The script is evaluated after the document was created but before any of its scripts were run. This is useful to amend
        the JavaScript environment, e.g. to seed `Math.random`.

        An example of overriding `Math.random` before the page loads:

        ```py
        # in your playwright script, assuming the preload.js file is in same directory.
        browser_context.add_init_script(path=\"preload.js\")
        ```

        > NOTE: The order of evaluation of multiple scripts installed via `browser_context.add_init_script()` and
        `page.add_init_script()` is not defined.

        Parameters
        ----------
        script : Union[str, NoneType]
            Script to be evaluated in all pages in the browser context. Optional.
        path : Union[pathlib.Path, str, NoneType]
            Path to the JavaScript file. If `path` is a relative path, then it is resolved relative to the current working
            directory. Optional.
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.add_init_script(script=script, path=path))
        )

    def expose_binding(
        self, name: str, callback: typing.Callable, *, handle: bool = None
    ) -> NoneType:
        """BrowserContext.expose_binding

        The method adds a function called `name` on the `window` object of every frame in every page in the context. When
        called, the function executes `callback` and returns a [Promise] which resolves to the return value of `callback`. If
        the `callback` returns a [Promise], it will be awaited.

        The first argument of the `callback` function contains information about the caller: `{ browserContext: BrowserContext,
        page: Page, frame: Frame }`.

        See `page.expose_binding()` for page-only version.

        An example of exposing page URL to all frames in all pages in the context:

        ```py
        from playwright.sync_api import sync_playwright

        def run(playwright):
            webkit = playwright.webkit
            browser = webkit.launch(headless=false)
            context = browser.new_context()
            context.expose_binding(\"pageURL\", lambda source: source[\"page\"].url)
            page = context.new_page()
            page.set_content(\"\"\"
            <script>
              async function onClick() {
                document.querySelector('div').textContent = await window.pageURL();
              }
            </script>
            <button onclick=\"onClick()\">Click me</button>
            <div></div>
            \"\"\")
            page.click(\"button\")

        with sync_playwright() as playwright:
            run(playwright)
        ```

        An example of passing an element handle:

        ```py
        def print(source, element):
            print(element.text_content())

        context.expose_binding(\"clicked\", print, handle=true)
        page.set_content(\"\"\"
          <script>
            document.addEventListener('click', event => window.clicked(event.target));
          </script>
          <div>Click me</div>
          <div>Or click me</div>
        \"\"\")
        ```

        Parameters
        ----------
        name : str
            Name of the function on the window object.
        callback : Callable
            Callback function that will be called in the Playwright's context.
        handle : Union[bool, NoneType]
            Whether to pass the argument as a handle, instead of passing by value. When passing a handle, only one argument is
            supported. When passing by value, multiple arguments are supported.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.expose_binding(
                    name=name, callback=self._wrap_handler(callback), handle=handle
                )
            )
        )

    def expose_function(self, name: str, callback: typing.Callable) -> NoneType:
        """BrowserContext.expose_function

        The method adds a function called `name` on the `window` object of every frame in every page in the context. When
        called, the function executes `callback` and returns a [Promise] which resolves to the return value of `callback`.

        If the `callback` returns a [Promise], it will be awaited.

        See `page.expose_function()` for page-only version.

        An example of adding a `sha256` function to all pages in the context:

        ```py
        import hashlib
        from playwright.sync_api import sync_playwright

        def sha256(text):
            m = hashlib.sha256()
            m.update(bytes(text, \"utf8\"))
            return m.hexdigest()

        def run(playwright):
            webkit = playwright.webkit
            browser = webkit.launch(headless=False)
            context = browser.new_context()
            context.expose_function(\"sha256\", sha256)
            page = context.new_page()
            page.set_content(\"\"\"
                <script>
                  async function onClick() {
                    document.querySelector('div').textContent = await window.sha256('PLAYWRIGHT');
                  }
                </script>
                <button onclick=\"onClick()\">Click me</button>
                <div></div>
            \"\"\")
            page.click(\"button\")

        with sync_playwright() as playwright:
            run(playwright)
        ```

        Parameters
        ----------
        name : str
            Name of the function on the window object.
        callback : Callable
            Callback function that will be called in the Playwright's context.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.expose_function(
                    name=name, callback=self._wrap_handler(callback)
                )
            )
        )

    def route(
        self,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]],
        handler: typing.Union[
            typing.Callable[["Route"], typing.Any],
            typing.Callable[["Route", "Request"], typing.Any],
        ],
        *,
        times: int = None
    ) -> NoneType:
        """BrowserContext.route

        Routing provides the capability to modify network requests that are made by any page in the browser context. Once route
        is enabled, every request matching the url pattern will stall unless it's continued, fulfilled or aborted.

        > NOTE: `browser_context.route()` will not intercept requests intercepted by Service Worker. See
        [this](https://github.com/microsoft/playwright/issues/1090) issue. We recommend disabling Service Workers when using
        request interception by setting `Browser.newContext.serviceWorkers` to `'block'`.

        An example of a naive handler that aborts all image requests:

        ```py
        context = browser.new_context()
        page = context.new_page()
        context.route(\"**/*.{png,jpg,jpeg}\", lambda route: route.abort())
        page.goto(\"https://example.com\")
        browser.close()
        ```

        or the same snippet using a regex pattern instead:

        ```py
        context = browser.new_context()
        page = context.new_page()
        context.route(re.compile(r\"(\\.png$)|(\\.jpg$)\"), lambda route: route.abort())
        page = await context.new_page()
        page = context.new_page()
        page.goto(\"https://example.com\")
        browser.close()
        ```

        It is possible to examine the request to decide the route action. For example, mocking all requests that contain some
        post data, and leaving all other requests as is:

        ```py
        def handle_route(route):
          if (\"my-string\" in route.request.post_data)
            route.fulfill(body=\"mocked-data\")
          else
            route.continue_()
        context.route(\"/api/**\", handle_route)
        ```

        Page routes (set up with `page.route()`) take precedence over browser context routes when request matches both
        handlers.

        To remove a route with its handler you can use `browser_context.unroute()`.

        > NOTE: Enabling routing disables http cache.

        Parameters
        ----------
        url : Union[Callable[[str], bool], Pattern, str]
            A glob pattern, regex pattern or predicate receiving [URL] to match while routing. When a `baseURL` via the context
            options was provided and the passed URL is a path, it gets merged via the
            [`new URL()`](https://developer.mozilla.org/en-US/docs/Web/API/URL/URL) constructor.
        handler : Union[Callable[[Route, Request], Any], Callable[[Route], Any]]
            handler function to route the request.
        times : Union[int, NoneType]
            How often a route should be used. By default it will be used every time.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.route(
                    url=self._wrap_handler(url),
                    handler=self._wrap_handler(handler),
                    times=times,
                )
            )
        )

    def unroute(
        self,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]],
        handler: typing.Union[
            typing.Callable[["Route"], typing.Any],
            typing.Callable[["Route", "Request"], typing.Any],
        ] = None,
    ) -> NoneType:
        """BrowserContext.unroute

        Removes a route created with `browser_context.route()`. When `handler` is not specified, removes all routes for
        the `url`.

        Parameters
        ----------
        url : Union[Callable[[str], bool], Pattern, str]
            A glob pattern, regex pattern or predicate receiving [URL] used to register a routing with
            `browser_context.route()`.
        handler : Union[Callable[[Route, Request], Any], Callable[[Route], Any], NoneType]
            Optional handler function used to register a routing with `browser_context.route()`.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.unroute(
                    url=self._wrap_handler(url), handler=self._wrap_handler(handler)
                )
            )
        )

    def expect_event(
        self, event: str, predicate: typing.Callable = None, *, timeout: float = None
    ) -> EventContextManager:
        """BrowserContext.expect_event

        Waits for event to fire and passes its value into the predicate function. Returns when the predicate returns truthy
        value. Will throw an error if the context closes before the event is fired. Returns the event data value.

        ```py
        with context.expect_event(\"page\") as event_info:
            page.click(\"button\")
        page = event_info.value
        ```

        Parameters
        ----------
        event : str
            Event name, same one would pass into `browserContext.on(event)`.
        predicate : Union[Callable, NoneType]
            Receives the event data and resolves to truthy value when the waiting should resolve.
        timeout : Union[float, NoneType]
            Maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default
            value can be changed by using the `browser_context.set_default_timeout()`.

        Returns
        -------
        EventContextManager
        """
        return EventContextManager(
            self,
            self._impl_obj.expect_event(
                event=event, predicate=self._wrap_handler(predicate), timeout=timeout
            ).future,
        )

    def close(self) -> NoneType:
        """BrowserContext.close

        Closes the browser context. All the pages that belong to the browser context will be closed.

        > NOTE: The default browser context cannot be closed.
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.close()))

    def storage_state(
        self, *, path: typing.Union[str, pathlib.Path] = None
    ) -> StorageState:
        """BrowserContext.storage_state

        Returns storage state for this browser context, contains current cookies and local storage snapshot.

        Parameters
        ----------
        path : Union[pathlib.Path, str, NoneType]
            The file path to save the storage state to. If `path` is a relative path, then it is resolved relative to current
            working directory. If no path is provided, storage state is still returned, but won't be saved to the disk.

        Returns
        -------
        {cookies: List[{name: str, value: str, domain: str, path: str, expires: float, httpOnly: bool, secure: bool, sameSite: Union["Lax", "None", "Strict"]}], origins: List[{origin: str, localStorage: List[{name: str, value: str}]}]}
        """

        return mapping.from_impl(self._sync(self._impl_obj.storage_state(path=path)))

    def wait_for_event(
        self, event: str, predicate: typing.Callable = None, *, timeout: float = None
    ) -> typing.Any:
        """BrowserContext.wait_for_event

        > NOTE: In most cases, you should use `browser_context.expect_event()`.

        Waits for given `event` to fire. If predicate is provided, it passes event's value into the `predicate` function and
        waits for `predicate(event)` to return a truthy value. Will throw an error if the browser context is closed before the
        `event` is fired.

        Parameters
        ----------
        event : str
            Event name, same one typically passed into `*.on(event)`.
        predicate : Union[Callable, NoneType]
            Receives the event data and resolves to truthy value when the waiting should resolve.
        timeout : Union[float, NoneType]
            Maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default
            value can be changed by using the `browser_context.set_default_timeout()`.

        Returns
        -------
        Any
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.wait_for_event(
                    event=event,
                    predicate=self._wrap_handler(predicate),
                    timeout=timeout,
                )
            )
        )

    def expect_page(
        self,
        predicate: typing.Optional[typing.Callable[["Page"], bool]] = None,
        *,
        timeout: float = None
    ) -> EventContextManager["Page"]:
        """BrowserContext.expect_page

        Performs action and waits for a new `Page` to be created in the context. If predicate is provided, it passes `Page`
        value into the `predicate` function and waits for `predicate(event)` to return a truthy value. Will throw an error if
        the context closes before new `Page` is created.

        Parameters
        ----------
        predicate : Union[Callable[[Page], bool], NoneType]
            Receives the `Page` object and resolves to truthy value when the waiting should resolve.
        timeout : Union[float, NoneType]
            Maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default
            value can be changed by using the `browser_context.set_default_timeout()`.

        Returns
        -------
        EventContextManager[Page]
        """
        return EventContextManager(
            self,
            self._impl_obj.expect_page(
                predicate=self._wrap_handler(predicate), timeout=timeout
            ).future,
        )

    def new_cdp_session(self, page: typing.Union["Page", "Frame"]) -> "CDPSession":
        """BrowserContext.new_cdp_session

        > NOTE: CDP sessions are only supported on Chromium-based browsers.

        Returns the newly created session.

        Parameters
        ----------
        page : Union[Frame, Page]
            Target to create new session for. For backwards-compatibility, this parameter is named `page`, but it can be a `Page` or
            `Frame` type.

        Returns
        -------
        CDPSession
        """

        return mapping.from_impl(self._sync(self._impl_obj.new_cdp_session(page=page)))


mapping.register(BrowserContextImpl, BrowserContext)


class CDPSession(SyncBase):
    def send(self, method: str, params: typing.Dict = None) -> typing.Dict:
        """CDPSession.send

        Parameters
        ----------
        method : str
            Protocol method name.
        params : Union[Dict, NoneType]
            Optional method parameters.

        Returns
        -------
        Dict
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.send(method=method, params=mapping.to_impl(params))
            )
        )

    def detach(self) -> NoneType:
        """CDPSession.detach

        Detaches the CDPSession from the target. Once detached, the CDPSession object won't emit any events and can't be used to
        send messages.
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.detach()))


mapping.register(CDPSessionImpl, CDPSession)


class Browser(SyncContextManager):
    def on(
        self, event: Literal["disconnected"], f: typing.Callable[["Browser"], "None"]
    ) -> None:
        """
        Emitted when Browser gets disconnected from the browser application. This might happen because of one of the following:
        - Browser application is closed or crashed.
        - The `browser.close()` method was called."""
        return super().on(event=event, f=f)

    def once(
        self, event: Literal["disconnected"], f: typing.Callable[["Browser"], "None"]
    ) -> None:
        """
        Emitted when Browser gets disconnected from the browser application. This might happen because of one of the following:
        - Browser application is closed or crashed.
        - The `browser.close()` method was called."""
        return super().once(event=event, f=f)

    @property
    def contexts(self) -> typing.List["BrowserContext"]:
        """Browser.contexts

        Returns an array of all open browser contexts. In a newly created browser, this will return zero browser contexts.

        ```py
        browser = pw.webkit.launch()
        print(len(browser.contexts())) # prints `0`
        context = browser.new_context()
        print(len(browser.contexts())) # prints `1`
        ```

        Returns
        -------
        List[BrowserContext]
        """
        return mapping.from_impl_list(self._impl_obj.contexts)

    @property
    def browser_type(self) -> "BrowserType":
        """Browser.browser_type

        Get the browser type (chromium, firefox or webkit) that the browser belongs to.

        Returns
        -------
        BrowserType
        """
        return mapping.from_impl(self._impl_obj.browser_type)

    @property
    def version(self) -> str:
        """Browser.version

        Returns the browser version.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.version)

    def is_connected(self) -> bool:
        """Browser.is_connected

        Indicates that the browser is connected.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(self._impl_obj.is_connected())

    def new_context(
        self,
        *,
        viewport: ViewportSize = None,
        screen: ViewportSize = None,
        no_viewport: bool = None,
        ignore_https_errors: bool = None,
        java_script_enabled: bool = None,
        bypass_csp: bool = None,
        user_agent: str = None,
        locale: str = None,
        timezone_id: str = None,
        geolocation: Geolocation = None,
        permissions: typing.List[str] = None,
        extra_http_headers: typing.Optional[typing.Dict[str, str]] = None,
        offline: bool = None,
        http_credentials: HttpCredentials = None,
        device_scale_factor: float = None,
        is_mobile: bool = None,
        has_touch: bool = None,
        color_scheme: Literal["dark", "light", "no-preference"] = None,
        reduced_motion: Literal["no-preference", "reduce"] = None,
        forced_colors: Literal["active", "none"] = None,
        accept_downloads: bool = None,
        default_browser_type: str = None,
        proxy: ProxySettings = None,
        record_har_path: typing.Union[str, pathlib.Path] = None,
        record_har_omit_content: bool = None,
        record_video_dir: typing.Union[str, pathlib.Path] = None,
        record_video_size: ViewportSize = None,
        storage_state: typing.Union[StorageState, str, pathlib.Path] = None,
        base_url: str = None,
        strict_selectors: bool = None,
        service_workers: Literal["allow", "block"] = None,
        record_har_url_filter: typing.Union[str, typing.Pattern] = None,
        record_har_mode: Literal["full", "minimal"] = None,
        record_har_content: Literal["attach", "embed", "omit"] = None
    ) -> "BrowserContext":
        """Browser.new_context

        Creates a new browser context. It won't share cookies/cache with other browser contexts.

        ```py
        browser = playwright.firefox.launch() # or \"chromium\" or \"webkit\".
        # create a new incognito browser context.
        context = browser.new_context()
        # create a new page in a pristine context.
        page = context.new_page()
        page.goto(\"https://example.com\")
        ```

        Parameters
        ----------
        viewport : Union[{width: int, height: int}, NoneType]
            Sets a consistent viewport for each page. Defaults to an 1280x720 viewport. `no_viewport` disables the fixed viewport.
        screen : Union[{width: int, height: int}, NoneType]
            Emulates consistent window screen size available inside web page via `window.screen`. Is only used when the `viewport`
            is set.
        no_viewport : Union[bool, NoneType]
            Does not enforce fixed viewport, allows resizing window in the headed mode.
        ignore_https_errors : Union[bool, NoneType]
            Whether to ignore HTTPS errors when sending network requests. Defaults to `false`.
        java_script_enabled : Union[bool, NoneType]
            Whether or not to enable JavaScript in the context. Defaults to `true`.
        bypass_csp : Union[bool, NoneType]
            Toggles bypassing page's Content-Security-Policy.
        user_agent : Union[str, NoneType]
            Specific user agent to use in this context.
        locale : Union[str, NoneType]
            Specify user locale, for example `en-GB`, `de-DE`, etc. Locale will affect `navigator.language` value, `Accept-Language`
            request header value as well as number and date formatting rules.
        timezone_id : Union[str, NoneType]
            Changes the timezone of the context. See
            [ICU's metaZones.txt](https://cs.chromium.org/chromium/src/third_party/icu/source/data/misc/metaZones.txt?rcl=faee8bc70570192d82d2978a71e2a615788597d1)
            for a list of supported timezone IDs.
        geolocation : Union[{latitude: float, longitude: float, accuracy: Union[float, NoneType]}, NoneType]
        permissions : Union[List[str], NoneType]
            A list of permissions to grant to all pages in this context. See `browser_context.grant_permissions()` for more
            details.
        extra_http_headers : Union[Dict[str, str], NoneType]
            An object containing additional HTTP headers to be sent with every request.
        offline : Union[bool, NoneType]
            Whether to emulate network being offline. Defaults to `false`.
        http_credentials : Union[{username: str, password: str}, NoneType]
            Credentials for [HTTP authentication](https://developer.mozilla.org/en-US/docs/Web/HTTP/Authentication).
        device_scale_factor : Union[float, NoneType]
            Specify device scale factor (can be thought of as dpr). Defaults to `1`.
        is_mobile : Union[bool, NoneType]
            Whether the `meta viewport` tag is taken into account and touch events are enabled. Defaults to `false`. Not supported
            in Firefox.
        has_touch : Union[bool, NoneType]
            Specifies if viewport supports touch events. Defaults to false.
        color_scheme : Union["dark", "light", "no-preference", NoneType]
            Emulates `'prefers-colors-scheme'` media feature, supported values are `'light'`, `'dark'`, `'no-preference'`. See
            `page.emulate_media()` for more details. Defaults to `'light'`.
        reduced_motion : Union["no-preference", "reduce", NoneType]
            Emulates `'prefers-reduced-motion'` media feature, supported values are `'reduce'`, `'no-preference'`. See
            `page.emulate_media()` for more details. Defaults to `'no-preference'`.
        forced_colors : Union["active", "none", NoneType]
            Emulates `'forced-colors'` media feature, supported values are `'active'`, `'none'`. See `page.emulate_media()`
            for more details. Defaults to `'none'`.

            > NOTE: It's not supported in WebKit, see [here](https://bugs.webkit.org/show_bug.cgi?id=225281) in their issue tracker.
        accept_downloads : Union[bool, NoneType]
            Whether to automatically download all the attachments. Defaults to `true` where all the downloads are accepted.
        proxy : Union[{server: str, bypass: Union[str, NoneType], username: Union[str, NoneType], password: Union[str, NoneType]}, NoneType]
            Network proxy settings to use with this context.

            > NOTE: For Chromium on Windows the browser needs to be launched with the global proxy for this option to work. If all
            contexts override the proxy, global proxy will be never used and can be any string, for example `launch({ proxy: {
            server: 'http://per-context' } })`.
        record_har_path : Union[pathlib.Path, str, NoneType]
            Enables [HAR](http://www.softwareishard.com/blog/har-12-spec) recording for all pages into the specified HAR file on the
            filesystem. If not specified, the HAR is not recorded. Make sure to call `browser_context.close()` for the HAR to
            be saved.
        record_har_omit_content : Union[bool, NoneType]
            Optional setting to control whether to omit request content from the HAR. Defaults to `false`.
        record_video_dir : Union[pathlib.Path, str, NoneType]
            Enables video recording for all pages into the specified directory. If not specified videos are not recorded. Make sure
            to call `browser_context.close()` for videos to be saved.
        record_video_size : Union[{width: int, height: int}, NoneType]
            Dimensions of the recorded videos. If not specified the size will be equal to `viewport` scaled down to fit into
            800x800. If `viewport` is not configured explicitly the video size defaults to 800x450. Actual picture of each page will
            be scaled down if necessary to fit the specified size.
        storage_state : Union[pathlib.Path, str, {cookies: List[{name: str, value: str, domain: str, path: str, expires: float, httpOnly: bool, secure: bool, sameSite: Union["Lax", "None", "Strict"]}], origins: List[{origin: str, localStorage: List[{name: str, value: str}]}]}, NoneType]
            Populates context with given storage state. This option can be used to initialize context with logged-in information
            obtained via `browser_context.storage_state()`. Either a path to the file with saved storage, or an object with
            the following fields:
        base_url : Union[str, NoneType]
            When using `page.goto()`, `page.route()`, `page.wait_for_url()`, `page.expect_request()`,
            or `page.expect_response()` it takes the base URL in consideration by using the
            [`URL()`](https://developer.mozilla.org/en-US/docs/Web/API/URL/URL) constructor for building the corresponding URL.
            Examples:
            - baseURL: `http://localhost:3000` and navigating to `/bar.html` results in `http://localhost:3000/bar.html`
            - baseURL: `http://localhost:3000/foo/` and navigating to `./bar.html` results in `http://localhost:3000/foo/bar.html`
            - baseURL: `http://localhost:3000/foo` (without trailing slash) and navigating to `./bar.html` results in
              `http://localhost:3000/bar.html`
        strict_selectors : Union[bool, NoneType]
            If specified, enables strict selectors mode for this context. In the strict selectors mode all operations on selectors
            that imply single target DOM element will throw when more than one element matches the selector. See `Locator` to learn
            more about the strict mode.
        service_workers : Union["allow", "block", NoneType]
            Whether to allow sites to register Service workers. Defaults to `'allow'`.
            - `'allow'`: [Service Workers](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API) can be registered.
            - `'block'`: Playwright will block all registration of Service Workers.
        record_har_url_filter : Union[Pattern, str, NoneType]
        record_har_mode : Union["full", "minimal", NoneType]
            When set to `minimal`, only record information necessary for routing from HAR. This omits sizes, timing, page, cookies,
            security and other types of HAR information that are not used when replaying from HAR. Defaults to `full`.
        record_har_content : Union["attach", "embed", "omit", NoneType]
            Optional setting to control resource content management. If `omit` is specified, content is not persisted. If `attach`
            is specified, resources are persistet as separate files and all of these files are archived along with the HAR file.
            Defaults to `embed`, which stores content inline the HAR file as per HAR specification.

        Returns
        -------
        BrowserContext
        """

        return mapping.from_impl(
            self._sync(
                self._impl_obj.new_context(
                    viewport=viewport,
                    screen=screen,
                    noViewport=no_viewport,
                    ignoreHTTPSErrors=ignore_https_errors,
                    javaScriptEnabled=java_script_enabled,
                    bypassCSP=bypass_csp,
                    userAgent=user_agent,
                    locale=locale,
                    timezoneId=timezone_id,
                    geolocation=geolocation,
                    permissions=mapping.to_impl(permissions),
                    extraHTTPHeaders=mapping.to_impl(extra_http_headers),
                    offline=offline,
                    httpCredentials=http_credentials,
                    deviceScaleFactor=device_scale_factor,
                    isMobile=is_mobile,
                    hasTouch=has_touch,
                    colorScheme=color_scheme,
                    reducedMotion=reduced_motion,
                    forcedColors=forced_colors,
                    acceptDownloads=accept_downloads,
                    defaultBrowserType=default_browser_type,
                    proxy=proxy,
                    recordHarPath=record_har_path,
                    recordHarOmitContent=record_har_omit_content,
                    recordVideoDir=record_video_dir,
                    recordVideoSize=record_video_size,
                    storageState=storage_state,
                    baseURL=base_url,
                    strictSelectors=strict_selectors,
                    serviceWorkers=service_workers,
                    recordHarUrlFilter=record_har_url_filter,
                    recordHarMode=record_har_mode,
                    recordHarContent=record_har_content,
                )
            )
        )

    def new_page(
        self,
        *,
        viewport: ViewportSize = None,
        screen: ViewportSize = None,
        no_viewport: bool = None,
        ignore_https_errors: bool = None,
        java_script_enabled: bool = None,
        bypass_csp: bool = None,
        user_agent: str = None,
        locale: str = None,
        timezone_id: str = None,
        geolocation: Geolocation = None,
        permissions: typing.List[str] = None,
        extra_http_headers: typing.Optional[typing.Dict[str, str]] = None,
        offline: bool = None,
        http_credentials: HttpCredentials = None,
        device_scale_factor: float = None,
        is_mobile: bool = None,
        has_touch: bool = None,
        color_scheme: Literal["dark", "light", "no-preference"] = None,
        forced_colors: Literal["active", "none"] = None,
        reduced_motion: Literal["no-preference", "reduce"] = None,
        accept_downloads: bool = None,
        default_browser_type: str = None,
        proxy: ProxySettings = None,
        record_har_path: typing.Union[str, pathlib.Path] = None,
        record_har_omit_content: bool = None,
        record_video_dir: typing.Union[str, pathlib.Path] = None,
        record_video_size: ViewportSize = None,
        storage_state: typing.Union[StorageState, str, pathlib.Path] = None,
        base_url: str = None,
        strict_selectors: bool = None,
        service_workers: Literal["allow", "block"] = None,
        record_har_url_filter: typing.Union[str, typing.Pattern] = None,
        record_har_mode: Literal["full", "minimal"] = None,
        record_har_content: Literal["attach", "embed", "omit"] = None
    ) -> "Page":
        """Browser.new_page

        Creates a new page in a new browser context. Closing this page will close the context as well.

        This is a convenience API that should only be used for the single-page scenarios and short snippets. Production code and
        testing frameworks should explicitly create `browser.new_context()` followed by the
        `browser_context.new_page()` to control their exact life times.

        Parameters
        ----------
        viewport : Union[{width: int, height: int}, NoneType]
            Sets a consistent viewport for each page. Defaults to an 1280x720 viewport. `no_viewport` disables the fixed viewport.
        screen : Union[{width: int, height: int}, NoneType]
            Emulates consistent window screen size available inside web page via `window.screen`. Is only used when the `viewport`
            is set.
        no_viewport : Union[bool, NoneType]
            Does not enforce fixed viewport, allows resizing window in the headed mode.
        ignore_https_errors : Union[bool, NoneType]
            Whether to ignore HTTPS errors when sending network requests. Defaults to `false`.
        java_script_enabled : Union[bool, NoneType]
            Whether or not to enable JavaScript in the context. Defaults to `true`.
        bypass_csp : Union[bool, NoneType]
            Toggles bypassing page's Content-Security-Policy.
        user_agent : Union[str, NoneType]
            Specific user agent to use in this context.
        locale : Union[str, NoneType]
            Specify user locale, for example `en-GB`, `de-DE`, etc. Locale will affect `navigator.language` value, `Accept-Language`
            request header value as well as number and date formatting rules.
        timezone_id : Union[str, NoneType]
            Changes the timezone of the context. See
            [ICU's metaZones.txt](https://cs.chromium.org/chromium/src/third_party/icu/source/data/misc/metaZones.txt?rcl=faee8bc70570192d82d2978a71e2a615788597d1)
            for a list of supported timezone IDs.
        geolocation : Union[{latitude: float, longitude: float, accuracy: Union[float, NoneType]}, NoneType]
        permissions : Union[List[str], NoneType]
            A list of permissions to grant to all pages in this context. See `browser_context.grant_permissions()` for more
            details.
        extra_http_headers : Union[Dict[str, str], NoneType]
            An object containing additional HTTP headers to be sent with every request.
        offline : Union[bool, NoneType]
            Whether to emulate network being offline. Defaults to `false`.
        http_credentials : Union[{username: str, password: str}, NoneType]
            Credentials for [HTTP authentication](https://developer.mozilla.org/en-US/docs/Web/HTTP/Authentication).
        device_scale_factor : Union[float, NoneType]
            Specify device scale factor (can be thought of as dpr). Defaults to `1`.
        is_mobile : Union[bool, NoneType]
            Whether the `meta viewport` tag is taken into account and touch events are enabled. Defaults to `false`. Not supported
            in Firefox.
        has_touch : Union[bool, NoneType]
            Specifies if viewport supports touch events. Defaults to false.
        color_scheme : Union["dark", "light", "no-preference", NoneType]
            Emulates `'prefers-colors-scheme'` media feature, supported values are `'light'`, `'dark'`, `'no-preference'`. See
            `page.emulate_media()` for more details. Defaults to `'light'`.
        forced_colors : Union["active", "none", NoneType]
            Emulates `'forced-colors'` media feature, supported values are `'active'`, `'none'`. See `page.emulate_media()`
            for more details. Defaults to `'none'`.

            > NOTE: It's not supported in WebKit, see [here](https://bugs.webkit.org/show_bug.cgi?id=225281) in their issue tracker.
        reduced_motion : Union["no-preference", "reduce", NoneType]
            Emulates `'prefers-reduced-motion'` media feature, supported values are `'reduce'`, `'no-preference'`. See
            `page.emulate_media()` for more details. Defaults to `'no-preference'`.
        accept_downloads : Union[bool, NoneType]
            Whether to automatically download all the attachments. Defaults to `true` where all the downloads are accepted.
        proxy : Union[{server: str, bypass: Union[str, NoneType], username: Union[str, NoneType], password: Union[str, NoneType]}, NoneType]
            Network proxy settings to use with this context.

            > NOTE: For Chromium on Windows the browser needs to be launched with the global proxy for this option to work. If all
            contexts override the proxy, global proxy will be never used and can be any string, for example `launch({ proxy: {
            server: 'http://per-context' } })`.
        record_har_path : Union[pathlib.Path, str, NoneType]
            Enables [HAR](http://www.softwareishard.com/blog/har-12-spec) recording for all pages into the specified HAR file on the
            filesystem. If not specified, the HAR is not recorded. Make sure to call `browser_context.close()` for the HAR to
            be saved.
        record_har_omit_content : Union[bool, NoneType]
            Optional setting to control whether to omit request content from the HAR. Defaults to `false`.
        record_video_dir : Union[pathlib.Path, str, NoneType]
            Enables video recording for all pages into the specified directory. If not specified videos are not recorded. Make sure
            to call `browser_context.close()` for videos to be saved.
        record_video_size : Union[{width: int, height: int}, NoneType]
            Dimensions of the recorded videos. If not specified the size will be equal to `viewport` scaled down to fit into
            800x800. If `viewport` is not configured explicitly the video size defaults to 800x450. Actual picture of each page will
            be scaled down if necessary to fit the specified size.
        storage_state : Union[pathlib.Path, str, {cookies: List[{name: str, value: str, domain: str, path: str, expires: float, httpOnly: bool, secure: bool, sameSite: Union["Lax", "None", "Strict"]}], origins: List[{origin: str, localStorage: List[{name: str, value: str}]}]}, NoneType]
            Populates context with given storage state. This option can be used to initialize context with logged-in information
            obtained via `browser_context.storage_state()`. Either a path to the file with saved storage, or an object with
            the following fields:
        base_url : Union[str, NoneType]
            When using `page.goto()`, `page.route()`, `page.wait_for_url()`, `page.expect_request()`,
            or `page.expect_response()` it takes the base URL in consideration by using the
            [`URL()`](https://developer.mozilla.org/en-US/docs/Web/API/URL/URL) constructor for building the corresponding URL.
            Examples:
            - baseURL: `http://localhost:3000` and navigating to `/bar.html` results in `http://localhost:3000/bar.html`
            - baseURL: `http://localhost:3000/foo/` and navigating to `./bar.html` results in `http://localhost:3000/foo/bar.html`
            - baseURL: `http://localhost:3000/foo` (without trailing slash) and navigating to `./bar.html` results in
              `http://localhost:3000/bar.html`
        strict_selectors : Union[bool, NoneType]
            If specified, enables strict selectors mode for this context. In the strict selectors mode all operations on selectors
            that imply single target DOM element will throw when more than one element matches the selector. See `Locator` to learn
            more about the strict mode.
        service_workers : Union["allow", "block", NoneType]
            Whether to allow sites to register Service workers. Defaults to `'allow'`.
            - `'allow'`: [Service Workers](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API) can be registered.
            - `'block'`: Playwright will block all registration of Service Workers.
        record_har_url_filter : Union[Pattern, str, NoneType]
        record_har_mode : Union["full", "minimal", NoneType]
            When set to `minimal`, only record information necessary for routing from HAR. This omits sizes, timing, page, cookies,
            security and other types of HAR information that are not used when replaying from HAR. Defaults to `full`.
        record_har_content : Union["attach", "embed", "omit", NoneType]
            Optional setting to control resource content management. If `omit` is specified, content is not persisted. If `attach`
            is specified, resources are persistet as separate files and all of these files are archived along with the HAR file.
            Defaults to `embed`, which stores content inline the HAR file as per HAR specification.

        Returns
        -------
        Page
        """

        return mapping.from_impl(
            self._sync(
                self._impl_obj.new_page(
                    viewport=viewport,
                    screen=screen,
                    noViewport=no_viewport,
                    ignoreHTTPSErrors=ignore_https_errors,
                    javaScriptEnabled=java_script_enabled,
                    bypassCSP=bypass_csp,
                    userAgent=user_agent,
                    locale=locale,
                    timezoneId=timezone_id,
                    geolocation=geolocation,
                    permissions=mapping.to_impl(permissions),
                    extraHTTPHeaders=mapping.to_impl(extra_http_headers),
                    offline=offline,
                    httpCredentials=http_credentials,
                    deviceScaleFactor=device_scale_factor,
                    isMobile=is_mobile,
                    hasTouch=has_touch,
                    colorScheme=color_scheme,
                    forcedColors=forced_colors,
                    reducedMotion=reduced_motion,
                    acceptDownloads=accept_downloads,
                    defaultBrowserType=default_browser_type,
                    proxy=proxy,
                    recordHarPath=record_har_path,
                    recordHarOmitContent=record_har_omit_content,
                    recordVideoDir=record_video_dir,
                    recordVideoSize=record_video_size,
                    storageState=storage_state,
                    baseURL=base_url,
                    strictSelectors=strict_selectors,
                    serviceWorkers=service_workers,
                    recordHarUrlFilter=record_har_url_filter,
                    recordHarMode=record_har_mode,
                    recordHarContent=record_har_content,
                )
            )
        )

    def close(self) -> NoneType:
        """Browser.close

        In case this browser is obtained using `browser_type.launch()`, closes the browser and all of its pages (if any
        were opened).

        In case this browser is connected to, clears all created contexts belonging to this browser and disconnects from the
        browser server.

        The `Browser` object itself is considered to be disposed and cannot be used anymore.
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.close()))

    def new_browser_cdp_session(self) -> "CDPSession":
        """Browser.new_browser_cdp_session

        > NOTE: CDP Sessions are only supported on Chromium-based browsers.

        Returns the newly created browser session.

        Returns
        -------
        CDPSession
        """

        return mapping.from_impl(self._sync(self._impl_obj.new_browser_cdp_session()))

    def start_tracing(
        self,
        *,
        page: "Page" = None,
        path: typing.Union[str, pathlib.Path] = None,
        screenshots: bool = None,
        categories: typing.List[str] = None
    ) -> NoneType:
        """Browser.start_tracing

        > NOTE: This API controls [Chromium Tracing](https://www.chromium.org/developers/how-tos/trace-event-profiling-tool)
        which is a low-level chromium-specific debugging tool. API to control [Playwright Tracing](https://playwright.dev/python/docs/trace-viewer) could be
        found [here](https://playwright.dev/python/docs/api/class-tracing).

        You can use `browser.start_tracing()` and `browser.stop_tracing()` to create a trace file that can be
        opened in Chrome DevTools performance panel.

        ```py
        browser.start_tracing(page, path=\"trace.json\")
        page.goto(\"https://www.google.com\")
        browser.stop_tracing()
        ```

        Parameters
        ----------
        page : Union[Page, NoneType]
            Optional, if specified, tracing includes screenshots of the given page.
        path : Union[pathlib.Path, str, NoneType]
            A path to write the trace file to.
        screenshots : Union[bool, NoneType]
            captures screenshots in the trace.
        categories : Union[List[str], NoneType]
            specify custom categories to use instead of default.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.start_tracing(
                    page=page._impl_obj if page else None,
                    path=path,
                    screenshots=screenshots,
                    categories=mapping.to_impl(categories),
                )
            )
        )

    def stop_tracing(self) -> bytes:
        """Browser.stop_tracing

        > NOTE: This API controls [Chromium Tracing](https://www.chromium.org/developers/how-tos/trace-event-profiling-tool)
        which is a low-level chromium-specific debugging tool. API to control [Playwright Tracing](https://playwright.dev/python/docs/trace-viewer) could be
        found [here](https://playwright.dev/python/docs/api/class-tracing).

        Returns the buffer with trace data.

        Returns
        -------
        bytes
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.stop_tracing()))


mapping.register(BrowserImpl, Browser)


class BrowserType(SyncBase):
    @property
    def name(self) -> str:
        """BrowserType.name

        Returns browser name. For example: `'chromium'`, `'webkit'` or `'firefox'`.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.name)

    @property
    def executable_path(self) -> str:
        """BrowserType.executable_path

        A path where Playwright expects to find a bundled browser executable.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.executable_path)

    def launch(
        self,
        *,
        executable_path: typing.Union[str, pathlib.Path] = None,
        channel: str = None,
        args: typing.List[str] = None,
        ignore_default_args: typing.Union[bool, typing.List[str]] = None,
        handle_sigint: bool = None,
        handle_sigterm: bool = None,
        handle_sighup: bool = None,
        timeout: float = None,
        env: typing.Optional[typing.Dict[str, typing.Union[str, float, bool]]] = None,
        headless: bool = None,
        devtools: bool = None,
        proxy: ProxySettings = None,
        downloads_path: typing.Union[str, pathlib.Path] = None,
        slow_mo: float = None,
        traces_dir: typing.Union[str, pathlib.Path] = None,
        chromium_sandbox: bool = None,
        firefox_user_prefs: typing.Optional[
            typing.Dict[str, typing.Union[str, float, bool]]
        ] = None
    ) -> "Browser":
        """BrowserType.launch

        Returns the browser instance.

        You can use `ignoreDefaultArgs` to filter out `--mute-audio` from default arguments:

        ```py
        browser = playwright.chromium.launch( # or \"firefox\" or \"webkit\".
            ignore_default_args=[\"--mute-audio\"]
        )
        ```

        > **Chromium-only** Playwright can also be used to control the Google Chrome or Microsoft Edge browsers, but it works
        best with the version of Chromium it is bundled with. There is no guarantee it will work with any other version. Use
        `executablePath` option with extreme caution.
        >
        > If Google Chrome (rather than Chromium) is preferred, a
        [Chrome Canary](https://www.google.com/chrome/browser/canary.html) or
        [Dev Channel](https://www.chromium.org/getting-involved/dev-channel) build is suggested.
        >
        > Stock browsers like Google Chrome and Microsoft Edge are suitable for tests that require proprietary media codecs for
        video playback. See
        [this article](https://www.howtogeek.com/202825/what%E2%80%99s-the-difference-between-chromium-and-chrome/) for other
        differences between Chromium and Chrome.
        [This article](https://chromium.googlesource.com/chromium/src/+/lkgr/docs/chromium_browser_vs_google_chrome.md)
        describes some differences for Linux users.

        Parameters
        ----------
        executable_path : Union[pathlib.Path, str, NoneType]
            Path to a browser executable to run instead of the bundled one. If `executablePath` is a relative path, then it is
            resolved relative to the current working directory. Note that Playwright only works with the bundled Chromium, Firefox
            or WebKit, use at your own risk.
        channel : Union[str, NoneType]
            Browser distribution channel.  Supported values are "chrome", "chrome-beta", "chrome-dev", "chrome-canary", "msedge",
            "msedge-beta", "msedge-dev", "msedge-canary". Read more about using
            [Google Chrome and Microsoft Edge](../browsers.md#google-chrome--microsoft-edge).
        args : Union[List[str], NoneType]
            Additional arguments to pass to the browser instance. The list of Chromium flags can be found
            [here](http://peter.sh/experiments/chromium-command-line-switches/).
        ignore_default_args : Union[List[str], bool, NoneType]
            If `true`, Playwright does not pass its own configurations args and only uses the ones from `args`. If an array is
            given, then filters out the given default arguments. Dangerous option; use with care. Defaults to `false`.
        handle_sigint : Union[bool, NoneType]
            Close the browser process on Ctrl-C. Defaults to `true`.
        handle_sigterm : Union[bool, NoneType]
            Close the browser process on SIGTERM. Defaults to `true`.
        handle_sighup : Union[bool, NoneType]
            Close the browser process on SIGHUP. Defaults to `true`.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds to wait for the browser instance to start. Defaults to `30000` (30 seconds). Pass `0` to
            disable timeout.
        env : Union[Dict[str, Union[bool, float, str]], NoneType]
            Specify environment variables that will be visible to the browser. Defaults to `process.env`.
        headless : Union[bool, NoneType]
            Whether to run browser in headless mode. More details for
            [Chromium](https://developers.google.com/web/updates/2017/04/headless-chrome) and
            [Firefox](https://developer.mozilla.org/en-US/docs/Mozilla/Firefox/Headless_mode). Defaults to `true` unless the
            `devtools` option is `true`.
        devtools : Union[bool, NoneType]
            **Chromium-only** Whether to auto-open a Developer Tools panel for each tab. If this option is `true`, the `headless`
            option will be set `false`.
        proxy : Union[{server: str, bypass: Union[str, NoneType], username: Union[str, NoneType], password: Union[str, NoneType]}, NoneType]
            Network proxy settings.
        downloads_path : Union[pathlib.Path, str, NoneType]
            If specified, accepted downloads are downloaded into this directory. Otherwise, temporary directory is created and is
            deleted when browser is closed. In either case, the downloads are deleted when the browser context they were created in
            is closed.
        slow_mo : Union[float, NoneType]
            Slows down Playwright operations by the specified amount of milliseconds. Useful so that you can see what is going on.
        traces_dir : Union[pathlib.Path, str, NoneType]
            If specified, traces are saved into this directory.
        chromium_sandbox : Union[bool, NoneType]
            Enable Chromium sandboxing. Defaults to `false`.
        firefox_user_prefs : Union[Dict[str, Union[bool, float, str]], NoneType]
            Firefox user preferences. Learn more about the Firefox user preferences at
            [`about:config`](https://support.mozilla.org/en-US/kb/about-config-editor-firefox).

        Returns
        -------
        Browser
        """

        return mapping.from_impl(
            self._sync(
                self._impl_obj.launch(
                    executablePath=executable_path,
                    channel=channel,
                    args=mapping.to_impl(args),
                    ignoreDefaultArgs=mapping.to_impl(ignore_default_args),
                    handleSIGINT=handle_sigint,
                    handleSIGTERM=handle_sigterm,
                    handleSIGHUP=handle_sighup,
                    timeout=timeout,
                    env=mapping.to_impl(env),
                    headless=headless,
                    devtools=devtools,
                    proxy=proxy,
                    downloadsPath=downloads_path,
                    slowMo=slow_mo,
                    tracesDir=traces_dir,
                    chromiumSandbox=chromium_sandbox,
                    firefoxUserPrefs=mapping.to_impl(firefox_user_prefs),
                )
            )
        )

    def launch_persistent_context(
        self,
        user_data_dir: typing.Union[str, pathlib.Path],
        *,
        channel: str = None,
        executable_path: typing.Union[str, pathlib.Path] = None,
        args: typing.List[str] = None,
        ignore_default_args: typing.Union[bool, typing.List[str]] = None,
        handle_sigint: bool = None,
        handle_sigterm: bool = None,
        handle_sighup: bool = None,
        timeout: float = None,
        env: typing.Optional[typing.Dict[str, typing.Union[str, float, bool]]] = None,
        headless: bool = None,
        devtools: bool = None,
        proxy: ProxySettings = None,
        downloads_path: typing.Union[str, pathlib.Path] = None,
        slow_mo: float = None,
        viewport: ViewportSize = None,
        screen: ViewportSize = None,
        no_viewport: bool = None,
        ignore_https_errors: bool = None,
        java_script_enabled: bool = None,
        bypass_csp: bool = None,
        user_agent: str = None,
        locale: str = None,
        timezone_id: str = None,
        geolocation: Geolocation = None,
        permissions: typing.List[str] = None,
        extra_http_headers: typing.Optional[typing.Dict[str, str]] = None,
        offline: bool = None,
        http_credentials: HttpCredentials = None,
        device_scale_factor: float = None,
        is_mobile: bool = None,
        has_touch: bool = None,
        color_scheme: Literal["dark", "light", "no-preference"] = None,
        reduced_motion: Literal["no-preference", "reduce"] = None,
        forced_colors: Literal["active", "none"] = None,
        accept_downloads: bool = None,
        traces_dir: typing.Union[str, pathlib.Path] = None,
        chromium_sandbox: bool = None,
        record_har_path: typing.Union[str, pathlib.Path] = None,
        record_har_omit_content: bool = None,
        record_video_dir: typing.Union[str, pathlib.Path] = None,
        record_video_size: ViewportSize = None,
        base_url: str = None,
        strict_selectors: bool = None,
        service_workers: Literal["allow", "block"] = None,
        record_har_url_filter: typing.Union[str, typing.Pattern] = None,
        record_har_mode: Literal["full", "minimal"] = None,
        record_har_content: Literal["attach", "embed", "omit"] = None
    ) -> "BrowserContext":
        """BrowserType.launch_persistent_context

        Returns the persistent browser context instance.

        Launches browser that uses persistent storage located at `userDataDir` and returns the only context. Closing this
        context will automatically close the browser.

        Parameters
        ----------
        user_data_dir : Union[pathlib.Path, str]
            Path to a User Data Directory, which stores browser session data like cookies and local storage. More details for
            [Chromium](https://chromium.googlesource.com/chromium/src/+/master/docs/user_data_dir.md#introduction) and
            [Firefox](https://developer.mozilla.org/en-US/docs/Mozilla/Command_Line_Options#User_Profile). Note that Chromium's user
            data directory is the **parent** directory of the "Profile Path" seen at `chrome://version`. Pass an empty string to use
            a temporary directory instead.
        channel : Union[str, NoneType]
            Browser distribution channel.  Supported values are "chrome", "chrome-beta", "chrome-dev", "chrome-canary", "msedge",
            "msedge-beta", "msedge-dev", "msedge-canary". Read more about using
            [Google Chrome and Microsoft Edge](../browsers.md#google-chrome--microsoft-edge).
        executable_path : Union[pathlib.Path, str, NoneType]
            Path to a browser executable to run instead of the bundled one. If `executablePath` is a relative path, then it is
            resolved relative to the current working directory. Note that Playwright only works with the bundled Chromium, Firefox
            or WebKit, use at your own risk.
        args : Union[List[str], NoneType]
            Additional arguments to pass to the browser instance. The list of Chromium flags can be found
            [here](http://peter.sh/experiments/chromium-command-line-switches/).
        ignore_default_args : Union[List[str], bool, NoneType]
            If `true`, Playwright does not pass its own configurations args and only uses the ones from `args`. If an array is
            given, then filters out the given default arguments. Dangerous option; use with care. Defaults to `false`.
        handle_sigint : Union[bool, NoneType]
            Close the browser process on Ctrl-C. Defaults to `true`.
        handle_sigterm : Union[bool, NoneType]
            Close the browser process on SIGTERM. Defaults to `true`.
        handle_sighup : Union[bool, NoneType]
            Close the browser process on SIGHUP. Defaults to `true`.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds to wait for the browser instance to start. Defaults to `30000` (30 seconds). Pass `0` to
            disable timeout.
        env : Union[Dict[str, Union[bool, float, str]], NoneType]
            Specify environment variables that will be visible to the browser. Defaults to `process.env`.
        headless : Union[bool, NoneType]
            Whether to run browser in headless mode. More details for
            [Chromium](https://developers.google.com/web/updates/2017/04/headless-chrome) and
            [Firefox](https://developer.mozilla.org/en-US/docs/Mozilla/Firefox/Headless_mode). Defaults to `true` unless the
            `devtools` option is `true`.
        devtools : Union[bool, NoneType]
            **Chromium-only** Whether to auto-open a Developer Tools panel for each tab. If this option is `true`, the `headless`
            option will be set `false`.
        proxy : Union[{server: str, bypass: Union[str, NoneType], username: Union[str, NoneType], password: Union[str, NoneType]}, NoneType]
            Network proxy settings.
        downloads_path : Union[pathlib.Path, str, NoneType]
            If specified, accepted downloads are downloaded into this directory. Otherwise, temporary directory is created and is
            deleted when browser is closed. In either case, the downloads are deleted when the browser context they were created in
            is closed.
        slow_mo : Union[float, NoneType]
            Slows down Playwright operations by the specified amount of milliseconds. Useful so that you can see what is going on.
        viewport : Union[{width: int, height: int}, NoneType]
            Sets a consistent viewport for each page. Defaults to an 1280x720 viewport. `no_viewport` disables the fixed viewport.
        screen : Union[{width: int, height: int}, NoneType]
            Emulates consistent window screen size available inside web page via `window.screen`. Is only used when the `viewport`
            is set.
        no_viewport : Union[bool, NoneType]
            Does not enforce fixed viewport, allows resizing window in the headed mode.
        ignore_https_errors : Union[bool, NoneType]
            Whether to ignore HTTPS errors when sending network requests. Defaults to `false`.
        java_script_enabled : Union[bool, NoneType]
            Whether or not to enable JavaScript in the context. Defaults to `true`.
        bypass_csp : Union[bool, NoneType]
            Toggles bypassing page's Content-Security-Policy.
        user_agent : Union[str, NoneType]
            Specific user agent to use in this context.
        locale : Union[str, NoneType]
            Specify user locale, for example `en-GB`, `de-DE`, etc. Locale will affect `navigator.language` value, `Accept-Language`
            request header value as well as number and date formatting rules.
        timezone_id : Union[str, NoneType]
            Changes the timezone of the context. See
            [ICU's metaZones.txt](https://cs.chromium.org/chromium/src/third_party/icu/source/data/misc/metaZones.txt?rcl=faee8bc70570192d82d2978a71e2a615788597d1)
            for a list of supported timezone IDs.
        geolocation : Union[{latitude: float, longitude: float, accuracy: Union[float, NoneType]}, NoneType]
        permissions : Union[List[str], NoneType]
            A list of permissions to grant to all pages in this context. See `browser_context.grant_permissions()` for more
            details.
        extra_http_headers : Union[Dict[str, str], NoneType]
            An object containing additional HTTP headers to be sent with every request.
        offline : Union[bool, NoneType]
            Whether to emulate network being offline. Defaults to `false`.
        http_credentials : Union[{username: str, password: str}, NoneType]
            Credentials for [HTTP authentication](https://developer.mozilla.org/en-US/docs/Web/HTTP/Authentication).
        device_scale_factor : Union[float, NoneType]
            Specify device scale factor (can be thought of as dpr). Defaults to `1`.
        is_mobile : Union[bool, NoneType]
            Whether the `meta viewport` tag is taken into account and touch events are enabled. Defaults to `false`. Not supported
            in Firefox.
        has_touch : Union[bool, NoneType]
            Specifies if viewport supports touch events. Defaults to false.
        color_scheme : Union["dark", "light", "no-preference", NoneType]
            Emulates `'prefers-colors-scheme'` media feature, supported values are `'light'`, `'dark'`, `'no-preference'`. See
            `page.emulate_media()` for more details. Defaults to `'light'`.
        reduced_motion : Union["no-preference", "reduce", NoneType]
            Emulates `'prefers-reduced-motion'` media feature, supported values are `'reduce'`, `'no-preference'`. See
            `page.emulate_media()` for more details. Defaults to `'no-preference'`.
        forced_colors : Union["active", "none", NoneType]
            Emulates `'forced-colors'` media feature, supported values are `'active'`, `'none'`. See `page.emulate_media()`
            for more details. Defaults to `'none'`.

            > NOTE: It's not supported in WebKit, see [here](https://bugs.webkit.org/show_bug.cgi?id=225281) in their issue tracker.
        accept_downloads : Union[bool, NoneType]
            Whether to automatically download all the attachments. Defaults to `true` where all the downloads are accepted.
        traces_dir : Union[pathlib.Path, str, NoneType]
            If specified, traces are saved into this directory.
        chromium_sandbox : Union[bool, NoneType]
            Enable Chromium sandboxing. Defaults to `false`.
        record_har_path : Union[pathlib.Path, str, NoneType]
            Enables [HAR](http://www.softwareishard.com/blog/har-12-spec) recording for all pages into the specified HAR file on the
            filesystem. If not specified, the HAR is not recorded. Make sure to call `browser_context.close()` for the HAR to
            be saved.
        record_har_omit_content : Union[bool, NoneType]
            Optional setting to control whether to omit request content from the HAR. Defaults to `false`.
        record_video_dir : Union[pathlib.Path, str, NoneType]
            Enables video recording for all pages into the specified directory. If not specified videos are not recorded. Make sure
            to call `browser_context.close()` for videos to be saved.
        record_video_size : Union[{width: int, height: int}, NoneType]
            Dimensions of the recorded videos. If not specified the size will be equal to `viewport` scaled down to fit into
            800x800. If `viewport` is not configured explicitly the video size defaults to 800x450. Actual picture of each page will
            be scaled down if necessary to fit the specified size.
        base_url : Union[str, NoneType]
            When using `page.goto()`, `page.route()`, `page.wait_for_url()`, `page.expect_request()`,
            or `page.expect_response()` it takes the base URL in consideration by using the
            [`URL()`](https://developer.mozilla.org/en-US/docs/Web/API/URL/URL) constructor for building the corresponding URL.
            Examples:
            - baseURL: `http://localhost:3000` and navigating to `/bar.html` results in `http://localhost:3000/bar.html`
            - baseURL: `http://localhost:3000/foo/` and navigating to `./bar.html` results in `http://localhost:3000/foo/bar.html`
            - baseURL: `http://localhost:3000/foo` (without trailing slash) and navigating to `./bar.html` results in
              `http://localhost:3000/bar.html`
        strict_selectors : Union[bool, NoneType]
            If specified, enables strict selectors mode for this context. In the strict selectors mode all operations on selectors
            that imply single target DOM element will throw when more than one element matches the selector. See `Locator` to learn
            more about the strict mode.
        service_workers : Union["allow", "block", NoneType]
            Whether to allow sites to register Service workers. Defaults to `'allow'`.
            - `'allow'`: [Service Workers](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API) can be registered.
            - `'block'`: Playwright will block all registration of Service Workers.
        record_har_url_filter : Union[Pattern, str, NoneType]
        record_har_mode : Union["full", "minimal", NoneType]
            When set to `minimal`, only record information necessary for routing from HAR. This omits sizes, timing, page, cookies,
            security and other types of HAR information that are not used when replaying from HAR. Defaults to `full`.
        record_har_content : Union["attach", "embed", "omit", NoneType]
            Optional setting to control resource content management. If `omit` is specified, content is not persisted. If `attach`
            is specified, resources are persistet as separate files and all of these files are archived along with the HAR file.
            Defaults to `embed`, which stores content inline the HAR file as per HAR specification.

        Returns
        -------
        BrowserContext
        """

        return mapping.from_impl(
            self._sync(
                self._impl_obj.launch_persistent_context(
                    userDataDir=user_data_dir,
                    channel=channel,
                    executablePath=executable_path,
                    args=mapping.to_impl(args),
                    ignoreDefaultArgs=mapping.to_impl(ignore_default_args),
                    handleSIGINT=handle_sigint,
                    handleSIGTERM=handle_sigterm,
                    handleSIGHUP=handle_sighup,
                    timeout=timeout,
                    env=mapping.to_impl(env),
                    headless=headless,
                    devtools=devtools,
                    proxy=proxy,
                    downloadsPath=downloads_path,
                    slowMo=slow_mo,
                    viewport=viewport,
                    screen=screen,
                    noViewport=no_viewport,
                    ignoreHTTPSErrors=ignore_https_errors,
                    javaScriptEnabled=java_script_enabled,
                    bypassCSP=bypass_csp,
                    userAgent=user_agent,
                    locale=locale,
                    timezoneId=timezone_id,
                    geolocation=geolocation,
                    permissions=mapping.to_impl(permissions),
                    extraHTTPHeaders=mapping.to_impl(extra_http_headers),
                    offline=offline,
                    httpCredentials=http_credentials,
                    deviceScaleFactor=device_scale_factor,
                    isMobile=is_mobile,
                    hasTouch=has_touch,
                    colorScheme=color_scheme,
                    reducedMotion=reduced_motion,
                    forcedColors=forced_colors,
                    acceptDownloads=accept_downloads,
                    tracesDir=traces_dir,
                    chromiumSandbox=chromium_sandbox,
                    recordHarPath=record_har_path,
                    recordHarOmitContent=record_har_omit_content,
                    recordVideoDir=record_video_dir,
                    recordVideoSize=record_video_size,
                    baseURL=base_url,
                    strictSelectors=strict_selectors,
                    serviceWorkers=service_workers,
                    recordHarUrlFilter=record_har_url_filter,
                    recordHarMode=record_har_mode,
                    recordHarContent=record_har_content,
                )
            )
        )

    def connect_over_cdp(
        self,
        endpoint_url: str,
        *,
        timeout: float = None,
        slow_mo: float = None,
        headers: typing.Optional[typing.Dict[str, str]] = None
    ) -> "Browser":
        """BrowserType.connect_over_cdp

        This method attaches Playwright to an existing browser instance using the Chrome DevTools Protocol.

        The default browser context is accessible via `browser.contexts()`.

        > NOTE: Connecting over the Chrome DevTools Protocol is only supported for Chromium-based browsers.

        Parameters
        ----------
        endpoint_url : str
            A CDP websocket endpoint or http url to connect to. For example `http://localhost:9222/` or
            `ws://127.0.0.1:9222/devtools/browser/387adf4c-243f-4051-a181-46798f4a46f4`.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds to wait for the connection to be established. Defaults to `30000` (30 seconds). Pass `0` to
            disable timeout.
        slow_mo : Union[float, NoneType]
            Slows down Playwright operations by the specified amount of milliseconds. Useful so that you can see what is going on.
            Defaults to 0.
        headers : Union[Dict[str, str], NoneType]
            Additional HTTP headers to be sent with connect request. Optional.

        Returns
        -------
        Browser
        """

        return mapping.from_impl(
            self._sync(
                self._impl_obj.connect_over_cdp(
                    endpointURL=endpoint_url,
                    timeout=timeout,
                    slow_mo=slow_mo,
                    headers=mapping.to_impl(headers),
                )
            )
        )

    def connect(
        self,
        ws_endpoint: str,
        *,
        timeout: float = None,
        slow_mo: float = None,
        headers: typing.Optional[typing.Dict[str, str]] = None
    ) -> "Browser":
        """BrowserType.connect

        This method attaches Playwright to an existing browser instance.

        Parameters
        ----------
        ws_endpoint : str
            A browser websocket endpoint to connect to.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds to wait for the connection to be established. Defaults to `0` (no timeout).
        slow_mo : Union[float, NoneType]
            Slows down Playwright operations by the specified amount of milliseconds. Useful so that you can see what is going on.
            Defaults to 0.
        headers : Union[Dict[str, str], NoneType]
            Additional HTTP headers to be sent with web socket connect request. Optional.

        Returns
        -------
        Browser
        """

        return mapping.from_impl(
            self._sync(
                self._impl_obj.connect(
                    ws_endpoint=ws_endpoint,
                    timeout=timeout,
                    slow_mo=slow_mo,
                    headers=mapping.to_impl(headers),
                )
            )
        )


mapping.register(BrowserTypeImpl, BrowserType)


class Playwright(SyncBase):
    @property
    def devices(self) -> typing.Dict:
        """Playwright.devices

        Returns a dictionary of devices to be used with `browser.new_context()` or `browser.new_page()`.

        ```py
        from playwright.sync_api import sync_playwright

        def run(playwright):
            webkit = playwright.webkit
            iphone = playwright.devices[\"iPhone 6\"]
            browser = webkit.launch()
            context = browser.new_context(**iphone)
            page = context.new_page()
            page.goto(\"http://example.com\")
            # other actions...
            browser.close()

        with sync_playwright() as playwright:
            run(playwright)
        ```

        Returns
        -------
        Dict
        """
        return mapping.from_maybe_impl(self._impl_obj.devices)

    @property
    def selectors(self) -> "Selectors":
        """Playwright.selectors

        Selectors can be used to install custom selector engines. See [Working with selectors](https://playwright.dev/python/docs/selectors) for more
        information.

        Returns
        -------
        Selectors
        """
        return mapping.from_impl(self._impl_obj.selectors)

    @property
    def chromium(self) -> "BrowserType":
        """Playwright.chromium

        This object can be used to launch or connect to Chromium, returning instances of `Browser`.

        Returns
        -------
        BrowserType
        """
        return mapping.from_impl(self._impl_obj.chromium)

    @property
    def firefox(self) -> "BrowserType":
        """Playwright.firefox

        This object can be used to launch or connect to Firefox, returning instances of `Browser`.

        Returns
        -------
        BrowserType
        """
        return mapping.from_impl(self._impl_obj.firefox)

    @property
    def webkit(self) -> "BrowserType":
        """Playwright.webkit

        This object can be used to launch or connect to WebKit, returning instances of `Browser`.

        Returns
        -------
        BrowserType
        """
        return mapping.from_impl(self._impl_obj.webkit)

    @property
    def request(self) -> "APIRequest":
        """Playwright.request

        Exposes API that can be used for the Web API testing.

        Returns
        -------
        APIRequest
        """
        return mapping.from_impl(self._impl_obj.request)

    def __getitem__(self, value: str) -> "BrowserType":

        return mapping.from_impl(self._impl_obj.__getitem__(value=value))

    def stop(self) -> NoneType:
        """Playwright.stop

        Terminates this instance of Playwright in case it was created bypassing the Python context manager. This is useful in
        REPL applications.

        ```py
        >>> from playwright.sync_api import sync_playwright

        >>> playwright = sync_playwright().start()

        >>> browser = playwright.chromium.launch()
        >>> page = browser.new_page()
        >>> page.goto(\"http://whatsmyuseragent.org/\")
        >>> page.screenshot(path=\"example.png\")
        >>> browser.close()

        >>> playwright.stop()
        ```
        """

        return mapping.from_maybe_impl(self._impl_obj.stop())


mapping.register(PlaywrightImpl, Playwright)


class Tracing(SyncBase):
    def start(
        self,
        *,
        name: str = None,
        title: str = None,
        snapshots: bool = None,
        screenshots: bool = None,
        sources: bool = None
    ) -> NoneType:
        """Tracing.start

        Start tracing.

        ```py
        context.tracing.start(name=\"trace\", screenshots=True, snapshots=True)
        page = context.new_page()
        page.goto(\"https://playwright.dev\")
        context.tracing.stop(path = \"trace.zip\")
        ```

        Parameters
        ----------
        name : Union[str, NoneType]
            If specified, the trace is going to be saved into the file with the given name inside the `tracesDir` folder specified
            in `browser_type.launch()`.
        title : Union[str, NoneType]
            Trace name to be shown in the Trace Viewer.
        snapshots : Union[bool, NoneType]
            If this option is true tracing will
            - capture DOM snapshot on every action
            - record network activity
        screenshots : Union[bool, NoneType]
            Whether to capture screenshots during tracing. Screenshots are used to build a timeline preview.
        sources : Union[bool, NoneType]
            Whether to include source files for trace actions.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.start(
                    name=name,
                    title=title,
                    snapshots=snapshots,
                    screenshots=screenshots,
                    sources=sources,
                )
            )
        )

    def start_chunk(self, *, title: str = None) -> NoneType:
        """Tracing.start_chunk

        Start a new trace chunk. If you'd like to record multiple traces on the same `BrowserContext`, use
        `tracing.start()` once, and then create multiple trace chunks with `tracing.start_chunk()` and
        `tracing.stop_chunk()`.

        ```py
        context.tracing.start(name=\"trace\", screenshots=True, snapshots=True)
        page = context.new_page()
        page.goto(\"https://playwright.dev\")

        context.tracing.start_chunk()
        page.click(\"text=Get Started\")
        # Everything between start_chunk and stop_chunk will be recorded in the trace.
        context.tracing.stop_chunk(path = \"trace1.zip\")

        context.tracing.start_chunk()
        page.goto(\"http://example.com\")
        # Save a second trace file with different actions.
        context.tracing.stop_chunk(path = \"trace2.zip\")
        ```

        Parameters
        ----------
        title : Union[str, NoneType]
            Trace name to be shown in the Trace Viewer.
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.start_chunk(title=title))
        )

    def stop_chunk(self, *, path: typing.Union[str, pathlib.Path] = None) -> NoneType:
        """Tracing.stop_chunk

        Stop the trace chunk. See `tracing.start_chunk()` for more details about multiple trace chunks.

        Parameters
        ----------
        path : Union[pathlib.Path, str, NoneType]
            Export trace collected since the last `tracing.start_chunk()` call into the file with the given path.
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.stop_chunk(path=path)))

    def stop(self, *, path: typing.Union[str, pathlib.Path] = None) -> NoneType:
        """Tracing.stop

        Stop tracing.

        Parameters
        ----------
        path : Union[pathlib.Path, str, NoneType]
            Export trace into the file with the given path.
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.stop(path=path)))


mapping.register(TracingImpl, Tracing)


class Locator(SyncBase):
    @property
    def page(self) -> "Page":
        """Locator.page

        A page this locator belongs to.

        Returns
        -------
        Page
        """
        return mapping.from_impl(self._impl_obj.page)

    @property
    def first(self) -> "Locator":
        """Locator.first

        Returns locator to the first matching element.

        Returns
        -------
        Locator
        """
        return mapping.from_impl(self._impl_obj.first)

    @property
    def last(self) -> "Locator":
        """Locator.last

        Returns locator to the last matching element.

        Returns
        -------
        Locator
        """
        return mapping.from_impl(self._impl_obj.last)

    def bounding_box(self, *, timeout: float = None) -> typing.Optional[FloatRect]:
        """Locator.bounding_box

        This method returns the bounding box of the element, or `null` if the element is not visible. The bounding box is
        calculated relative to the main frame viewport - which is usually the same as the browser window.

        Scrolling affects the returned bonding box, similarly to
        [Element.getBoundingClientRect](https://developer.mozilla.org/en-US/docs/Web/API/Element/getBoundingClientRect). That
        means `x` and/or `y` may be negative.

        Elements from child frames return the bounding box relative to the main frame, unlike the
        [Element.getBoundingClientRect](https://developer.mozilla.org/en-US/docs/Web/API/Element/getBoundingClientRect).

        Assuming the page is static, it is safe to use bounding box coordinates to perform input. For example, the following
        snippet should click the center of the element.

        ```py
        box = element.bounding_box()
        page.mouse.click(box[\"x\"] + box[\"width\"] / 2, box[\"y\"] + box[\"height\"] / 2)
        ```

        Parameters
        ----------
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        Union[{x: float, y: float, width: float, height: float}, NoneType]
        """

        return mapping.from_impl_nullable(
            self._sync(self._impl_obj.bounding_box(timeout=timeout))
        )

    def check(
        self,
        *,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        no_wait_after: bool = None,
        trial: bool = None
    ) -> NoneType:
        """Locator.check

        This method checks the element by performing the following steps:
        1. Ensure that element is a checkbox or a radio input. If not, this method throws. If the element is already checked,
           this method returns immediately.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the element, unless `force` option is set.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to click in the center of the element.
        1. Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.
        1. Ensure that the element is now checked. If not, this method throws.

        If the element is detached from the DOM at any moment during the action, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`. Passing
        zero timeout disables this.

        Parameters
        ----------
        position : Union[{x: float, y: float}, NoneType]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the
            element.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        trial : Union[bool, NoneType]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults to
            `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.check(
                    position=position,
                    timeout=timeout,
                    force=force,
                    noWaitAfter=no_wait_after,
                    trial=trial,
                )
            )
        )

    def click(
        self,
        *,
        modifiers: typing.Optional[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: Position = None,
        delay: float = None,
        button: Literal["left", "middle", "right"] = None,
        click_count: int = None,
        timeout: float = None,
        force: bool = None,
        no_wait_after: bool = None,
        trial: bool = None
    ) -> NoneType:
        """Locator.click

        This method clicks the element by performing the following steps:
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the element, unless `force` option is set.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to click in the center of the element, or the specified `position`.
        1. Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.

        If the element is detached from the DOM at any moment during the action, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`. Passing
        zero timeout disables this.

        Parameters
        ----------
        modifiers : Union[List[Union["Alt", "Control", "Meta", "Shift"]], NoneType]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores current
            modifiers back. If not specified, currently pressed modifiers are used.
        position : Union[{x: float, y: float}, NoneType]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the
            element.
        delay : Union[float, NoneType]
            Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        button : Union["left", "middle", "right", NoneType]
            Defaults to `left`.
        click_count : Union[int, NoneType]
            defaults to 1. See [UIEvent.detail].
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        trial : Union[bool, NoneType]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults to
            `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.click(
                    modifiers=mapping.to_impl(modifiers),
                    position=position,
                    delay=delay,
                    button=button,
                    clickCount=click_count,
                    timeout=timeout,
                    force=force,
                    noWaitAfter=no_wait_after,
                    trial=trial,
                )
            )
        )

    def dblclick(
        self,
        *,
        modifiers: typing.Optional[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: Position = None,
        delay: float = None,
        button: Literal["left", "middle", "right"] = None,
        timeout: float = None,
        force: bool = None,
        no_wait_after: bool = None,
        trial: bool = None
    ) -> NoneType:
        """Locator.dblclick

        This method double clicks the element by performing the following steps:
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the element, unless `force` option is set.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to double click in the center of the element, or the specified `position`.
        1. Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set. Note that if the
           first click of the `dblclick()` triggers a navigation event, this method will throw.

        If the element is detached from the DOM at any moment during the action, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`. Passing
        zero timeout disables this.

        > NOTE: `element.dblclick()` dispatches two `click` events and a single `dblclick` event.

        Parameters
        ----------
        modifiers : Union[List[Union["Alt", "Control", "Meta", "Shift"]], NoneType]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores current
            modifiers back. If not specified, currently pressed modifiers are used.
        position : Union[{x: float, y: float}, NoneType]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the
            element.
        delay : Union[float, NoneType]
            Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        button : Union["left", "middle", "right", NoneType]
            Defaults to `left`.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        trial : Union[bool, NoneType]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults to
            `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.dblclick(
                    modifiers=mapping.to_impl(modifiers),
                    position=position,
                    delay=delay,
                    button=button,
                    timeout=timeout,
                    force=force,
                    noWaitAfter=no_wait_after,
                    trial=trial,
                )
            )
        )

    def dispatch_event(
        self, type: str, event_init: typing.Dict = None, *, timeout: float = None
    ) -> NoneType:
        """Locator.dispatch_event

        The snippet below dispatches the `click` event on the element. Regardless of the visibility state of the element,
        `click` is dispatched. This is equivalent to calling
        [element.click()](https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/click).

        ```py
        element.dispatch_event(\"click\")
        ```

        Under the hood, it creates an instance of an event based on the given `type`, initializes it with `eventInit` properties
        and dispatches it on the element. Events are `composed`, `cancelable` and bubble by default.

        Since `eventInit` is event-specific, please refer to the events documentation for the lists of initial properties:
        - [DragEvent](https://developer.mozilla.org/en-US/docs/Web/API/DragEvent/DragEvent)
        - [FocusEvent](https://developer.mozilla.org/en-US/docs/Web/API/FocusEvent/FocusEvent)
        - [KeyboardEvent](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/KeyboardEvent)
        - [MouseEvent](https://developer.mozilla.org/en-US/docs/Web/API/MouseEvent/MouseEvent)
        - [PointerEvent](https://developer.mozilla.org/en-US/docs/Web/API/PointerEvent/PointerEvent)
        - [TouchEvent](https://developer.mozilla.org/en-US/docs/Web/API/TouchEvent/TouchEvent)
        - [Event](https://developer.mozilla.org/en-US/docs/Web/API/Event/Event)

        You can also specify `JSHandle` as the property value if you want live objects to be passed into the event:

        ```py
        # note you can only create data_transfer in chromium and firefox
        data_transfer = page.evaluate_handle(\"new DataTransfer()\")
        element.dispatch_event(\"#source\", \"dragstart\", {\"dataTransfer\": data_transfer})
        ```

        Parameters
        ----------
        type : str
            DOM event type: `"click"`, `"dragstart"`, etc.
        event_init : Union[Dict, NoneType]
            Optional event-specific initialization properties.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.dispatch_event(
                    type=type, eventInit=mapping.to_impl(event_init), timeout=timeout
                )
            )
        )

    def evaluate(
        self, expression: str, arg: typing.Any = None, *, timeout: float = None
    ) -> typing.Any:
        """Locator.evaluate

        Returns the return value of `expression`.

        This method passes this handle as the first argument to `expression`.

        If `expression` returns a [Promise], then `handle.evaluate` would wait for the promise to resolve and return its value.

        Examples:

        ```py
        tweets = page.locator(\".tweet .retweets\")
        assert tweets.evaluate(\"node => node.innerText\") == \"10 retweets\"
        ```

        Parameters
        ----------
        expression : str
            JavaScript expression to be evaluated in the browser context. If it looks like a function declaration, it is interpreted
            as a function. Otherwise, evaluated as an expression.
        arg : Union[Any, NoneType]
            Optional argument to pass to `expression`.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        Any
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.evaluate(
                    expression=expression, arg=mapping.to_impl(arg), timeout=timeout
                )
            )
        )

    def evaluate_all(self, expression: str, arg: typing.Any = None) -> typing.Any:
        """Locator.evaluate_all

        The method finds all elements matching the specified locator and passes an array of matched elements as a first argument
        to `expression`. Returns the result of `expression` invocation.

        If `expression` returns a [Promise], then `locator.evaluate_all()` would wait for the promise to resolve and
        return its value.

        Examples:

        ```py
        elements = page.locator(\"div\")
        div_counts = elements(\"(divs, min) => divs.length >= min\", 10)
        ```

        Parameters
        ----------
        expression : str
            JavaScript expression to be evaluated in the browser context. If it looks like a function declaration, it is interpreted
            as a function. Otherwise, evaluated as an expression.
        arg : Union[Any, NoneType]
            Optional argument to pass to `expression`.

        Returns
        -------
        Any
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.evaluate_all(
                    expression=expression, arg=mapping.to_impl(arg)
                )
            )
        )

    def evaluate_handle(
        self, expression: str, arg: typing.Any = None, *, timeout: float = None
    ) -> "JSHandle":
        """Locator.evaluate_handle

        Returns the return value of `expression` as a `JSHandle`.

        This method passes this handle as the first argument to `expression`.

        The only difference between `locator.evaluate()` and `locator.evaluate_handle()` is that
        `locator.evaluate_handle()` returns `JSHandle`.

        If the function passed to the `locator.evaluate_handle()` returns a [Promise], then
        `locator.evaluate_handle()` would wait for the promise to resolve and return its value.

        See `page.evaluate_handle()` for more details.

        Parameters
        ----------
        expression : str
            JavaScript expression to be evaluated in the browser context. If it looks like a function declaration, it is interpreted
            as a function. Otherwise, evaluated as an expression.
        arg : Union[Any, NoneType]
            Optional argument to pass to `expression`.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        JSHandle
        """

        return mapping.from_impl(
            self._sync(
                self._impl_obj.evaluate_handle(
                    expression=expression, arg=mapping.to_impl(arg), timeout=timeout
                )
            )
        )

    def fill(
        self,
        value: str,
        *,
        timeout: float = None,
        no_wait_after: bool = None,
        force: bool = None
    ) -> NoneType:
        """Locator.fill

        This method waits for [actionability](https://playwright.dev/python/docs/actionability) checks, focuses the element, fills it and triggers an `input`
        event after filling. Note that you can pass an empty string to clear the input field.

        If the target element is not an `<input>`, `<textarea>` or `[contenteditable]` element, this method throws an error.
        However, if the element is inside the `<label>` element that has an associated
        [control](https://developer.mozilla.org/en-US/docs/Web/API/HTMLLabelElement/control), the control will be filled
        instead.

        To send fine-grained keyboard events, use `locator.type()`.

        Parameters
        ----------
        value : str
            Value to set for the `<input>`, `<textarea>` or `[contenteditable]` element.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.fill(
                    value=value, timeout=timeout, noWaitAfter=no_wait_after, force=force
                )
            )
        )

    def locator(
        self,
        selector: str,
        *,
        has_text: typing.Union[str, typing.Pattern] = None,
        has: "Locator" = None
    ) -> "Locator":
        """Locator.locator

        The method finds an element matching the specified selector in the `Locator`'s subtree. It also accepts filter options,
        similar to `locator.filter()` method.

        Parameters
        ----------
        selector : str
            A selector to use when resolving DOM element. See [working with selectors](../selectors.md) for more details.
        has_text : Union[Pattern, str, NoneType]
            Matches elements containing specified text somewhere inside, possibly in a child or a descendant element. When passed a
            [string], matching is case-insensitive and searches for a substring. For example, `"Playwright"` matches
            `<article><div>Playwright</div></article>`.
        has : Union[Locator, NoneType]
            Matches elements containing an element that matches an inner locator. Inner locator is queried against the outer one.
            For example, `article` that has `text=Playwright` matches `<article><div>Playwright</div></article>`.

            Note that outer and inner locators must belong to the same frame. Inner locator must not contain `FrameLocator`s.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(
            self._impl_obj.locator(
                selector=selector, has_text=has_text, has=has._impl_obj if has else None
            )
        )

    def frame_locator(self, selector: str) -> "FrameLocator":
        """Locator.frame_locator

        When working with iframes, you can create a frame locator that will enter the iframe and allow selecting elements in
        that iframe:

        ```py
        locator = page.frame_locator(\"iframe\").locator(\"text=Submit\")
        locator.click()
        ```

        Parameters
        ----------
        selector : str
            A selector to use when resolving DOM element. See [working with selectors](../selectors.md) for more details.

        Returns
        -------
        FrameLocator
        """

        return mapping.from_impl(self._impl_obj.frame_locator(selector=selector))

    def element_handle(self, *, timeout: float = None) -> "ElementHandle":
        """Locator.element_handle

        Resolves given locator to the first matching DOM element. If no elements matching the query are visible, waits for them
        up to a given timeout. If multiple elements match the selector, throws.

        Parameters
        ----------
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        ElementHandle
        """

        return mapping.from_impl(
            self._sync(self._impl_obj.element_handle(timeout=timeout))
        )

    def element_handles(self) -> typing.List["ElementHandle"]:
        """Locator.element_handles

        Resolves given locator to all matching DOM elements.

        Returns
        -------
        List[ElementHandle]
        """

        return mapping.from_impl_list(self._sync(self._impl_obj.element_handles()))

    def nth(self, index: int) -> "Locator":
        """Locator.nth

        Returns locator to the n-th matching element. It's zero based, `nth(0)` selects the first element.

        Parameters
        ----------
        index : int

        Returns
        -------
        Locator
        """

        return mapping.from_impl(self._impl_obj.nth(index=index))

    def filter(
        self,
        *,
        has_text: typing.Union[str, typing.Pattern] = None,
        has: "Locator" = None
    ) -> "Locator":
        """Locator.filter

        This method narrows existing locator according to the options, for example filters by text. It can be chained to filter
        multiple times.

        ```py
        row_locator = page.lsocator(\"tr\")
        # ...
        row_locator
            .filter(has_text=\"text in column 1\")
            .filter(has=page.locator(\"tr\", has_text=\"column 2 button\"))
            .screenshot()
        ```

        Parameters
        ----------
        has_text : Union[Pattern, str, NoneType]
            Matches elements containing specified text somewhere inside, possibly in a child or a descendant element. When passed a
            [string], matching is case-insensitive and searches for a substring. For example, `"Playwright"` matches
            `<article><div>Playwright</div></article>`.
        has : Union[Locator, NoneType]
            Matches elements containing an element that matches an inner locator. Inner locator is queried against the outer one.
            For example, `article` that has `text=Playwright` matches `<article><div>Playwright</div></article>`.

            Note that outer and inner locators must belong to the same frame. Inner locator must not contain `FrameLocator`s.

        Returns
        -------
        Locator
        """

        return mapping.from_impl(
            self._impl_obj.filter(has_text=has_text, has=has._impl_obj if has else None)
        )

    def focus(self, *, timeout: float = None) -> NoneType:
        """Locator.focus

        Calls [focus](https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/focus) on the element.

        Parameters
        ----------
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.focus(timeout=timeout))
        )

    def count(self) -> int:
        """Locator.count

        Returns the number of elements matching given selector.

        Returns
        -------
        int
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.count()))

    def drag_to(
        self,
        target: "Locator",
        *,
        force: bool = None,
        no_wait_after: bool = None,
        timeout: float = None,
        trial: bool = None,
        source_position: Position = None,
        target_position: Position = None
    ) -> NoneType:
        """Locator.drag_to

        Parameters
        ----------
        target : Locator
            Locator of the element to drag to.
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        trial : Union[bool, NoneType]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults to
            `false`. Useful to wait until the element is ready for the action without performing it.
        source_position : Union[{x: float, y: float}, NoneType]
            Clicks on the source element at this point relative to the top-left corner of the element's padding box. If not
            specified, some visible point of the element is used.
        target_position : Union[{x: float, y: float}, NoneType]
            Drops on the target element at this point relative to the top-left corner of the element's padding box. If not
            specified, some visible point of the element is used.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.drag_to(
                    target=target._impl_obj,
                    force=force,
                    noWaitAfter=no_wait_after,
                    timeout=timeout,
                    trial=trial,
                    sourcePosition=source_position,
                    targetPosition=target_position,
                )
            )
        )

    def get_attribute(
        self, name: str, *, timeout: float = None
    ) -> typing.Optional[str]:
        """Locator.get_attribute

        Returns element attribute value.

        Parameters
        ----------
        name : str
            Attribute name to get the value for.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        Union[str, NoneType]
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.get_attribute(name=name, timeout=timeout))
        )

    def hover(
        self,
        *,
        modifiers: typing.Optional[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        trial: bool = None
    ) -> NoneType:
        """Locator.hover

        This method hovers over the element by performing the following steps:
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the element, unless `force` option is set.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to hover over the center of the element, or the specified `position`.
        1. Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.

        If the element is detached from the DOM at any moment during the action, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`. Passing
        zero timeout disables this.

        Parameters
        ----------
        modifiers : Union[List[Union["Alt", "Control", "Meta", "Shift"]], NoneType]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores current
            modifiers back. If not specified, currently pressed modifiers are used.
        position : Union[{x: float, y: float}, NoneType]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the
            element.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        trial : Union[bool, NoneType]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults to
            `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.hover(
                    modifiers=mapping.to_impl(modifiers),
                    position=position,
                    timeout=timeout,
                    force=force,
                    trial=trial,
                )
            )
        )

    def inner_html(self, *, timeout: float = None) -> str:
        """Locator.inner_html

        Returns the `element.innerHTML`.

        Parameters
        ----------
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        str
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.inner_html(timeout=timeout))
        )

    def inner_text(self, *, timeout: float = None) -> str:
        """Locator.inner_text

        Returns the `element.innerText`.

        Parameters
        ----------
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        str
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.inner_text(timeout=timeout))
        )

    def input_value(self, *, timeout: float = None) -> str:
        """Locator.input_value

        Returns `input.value` for the selected `<input>` or `<textarea>` or `<select>` element.

        Throws for non-input elements. However, if the element is inside the `<label>` element that has an associated
        [control](https://developer.mozilla.org/en-US/docs/Web/API/HTMLLabelElement/control), returns the value of the control.

        Parameters
        ----------
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        str
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.input_value(timeout=timeout))
        )

    def is_checked(self, *, timeout: float = None) -> bool:
        """Locator.is_checked

        Returns whether the element is checked. Throws if the element is not a checkbox or radio input.

        Parameters
        ----------
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.is_checked(timeout=timeout))
        )

    def is_disabled(self, *, timeout: float = None) -> bool:
        """Locator.is_disabled

        Returns whether the element is disabled, the opposite of [enabled](https://playwright.dev/python/docs/actionability#enabled).

        Parameters
        ----------
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.is_disabled(timeout=timeout))
        )

    def is_editable(self, *, timeout: float = None) -> bool:
        """Locator.is_editable

        Returns whether the element is [editable](https://playwright.dev/python/docs/actionability#editable).

        Parameters
        ----------
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.is_editable(timeout=timeout))
        )

    def is_enabled(self, *, timeout: float = None) -> bool:
        """Locator.is_enabled

        Returns whether the element is [enabled](https://playwright.dev/python/docs/actionability#enabled).

        Parameters
        ----------
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.is_enabled(timeout=timeout))
        )

    def is_hidden(self, *, timeout: float = None) -> bool:
        """Locator.is_hidden

        Returns whether the element is hidden, the opposite of [visible](https://playwright.dev/python/docs/actionability#visible).

        Parameters
        ----------
        timeout : Union[float, NoneType]
            **DEPRECATED** This option is ignored. `locator.is_hidden()` does not wait for the element to become hidden and
            returns immediately.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.is_hidden(timeout=timeout))
        )

    def is_visible(self, *, timeout: float = None) -> bool:
        """Locator.is_visible

        Returns whether the element is [visible](https://playwright.dev/python/docs/actionability#visible).

        Parameters
        ----------
        timeout : Union[float, NoneType]
            **DEPRECATED** This option is ignored. `locator.is_visible()` does not wait for the element to become visible and
            returns immediately.

        Returns
        -------
        bool
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.is_visible(timeout=timeout))
        )

    def press(
        self,
        key: str,
        *,
        delay: float = None,
        timeout: float = None,
        no_wait_after: bool = None
    ) -> NoneType:
        """Locator.press

        Focuses the element, and then uses `keyboard.down()` and `keyboard.up()`.

        `key` can specify the intended [keyboardEvent.key](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/key)
        value or a single character to generate the text for. A superset of the `key` values can be found
        [here](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/key/Key_Values). Examples of the keys are:

        `F1` - `F12`, `Digit0`- `Digit9`, `KeyA`- `KeyZ`, `Backquote`, `Minus`, `Equal`, `Backslash`, `Backspace`, `Tab`,
        `Delete`, `Escape`, `ArrowDown`, `End`, `Enter`, `Home`, `Insert`, `PageDown`, `PageUp`, `ArrowRight`, `ArrowUp`, etc.

        Following modification shortcuts are also supported: `Shift`, `Control`, `Alt`, `Meta`, `ShiftLeft`.

        Holding down `Shift` will type the text that corresponds to the `key` in the upper case.

        If `key` is a single character, it is case-sensitive, so the values `a` and `A` will generate different respective
        texts.

        Shortcuts such as `key: \"Control+o\"` or `key: \"Control+Shift+T\"` are supported as well. When specified with the
        modifier, modifier is pressed and being held while the subsequent key is being pressed.

        Parameters
        ----------
        key : str
            Name of the key to press or a character to generate, such as `ArrowLeft` or `a`.
        delay : Union[float, NoneType]
            Time to wait between `keydown` and `keyup` in milliseconds. Defaults to 0.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.press(
                    key=key, delay=delay, timeout=timeout, noWaitAfter=no_wait_after
                )
            )
        )

    def screenshot(
        self,
        *,
        timeout: float = None,
        type: Literal["jpeg", "png"] = None,
        path: typing.Union[str, pathlib.Path] = None,
        quality: int = None,
        omit_background: bool = None,
        animations: Literal["allow", "disabled"] = None,
        caret: Literal["hide", "initial"] = None,
        scale: Literal["css", "device"] = None,
        mask: typing.List["Locator"] = None
    ) -> bytes:
        """Locator.screenshot

        This method captures a screenshot of the page, clipped to the size and position of a particular element matching the
        locator. If the element is covered by other elements, it will not be actually visible on the screenshot. If the element
        is a scrollable container, only the currently scrolled content will be visible on the screenshot.

        This method waits for the [actionability](https://playwright.dev/python/docs/actionability) checks, then scrolls element into view before taking a
        screenshot. If the element is detached from DOM, the method throws an error.

        Returns the buffer with the captured screenshot.

        Parameters
        ----------
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        type : Union["jpeg", "png", NoneType]
            Specify screenshot type, defaults to `png`.
        path : Union[pathlib.Path, str, NoneType]
            The file path to save the image to. The screenshot type will be inferred from file extension. If `path` is a relative
            path, then it is resolved relative to the current working directory. If no path is provided, the image won't be saved to
            the disk.
        quality : Union[int, NoneType]
            The quality of the image, between 0-100. Not applicable to `png` images.
        omit_background : Union[bool, NoneType]
            Hides default white background and allows capturing screenshots with transparency. Not applicable to `jpeg` images.
            Defaults to `false`.
        animations : Union["allow", "disabled", NoneType]
            When set to `"disabled"`, stops CSS animations, CSS transitions and Web Animations. Animations get different treatment
            depending on their duration:
            - finite animations are fast-forwarded to completion, so they'll fire `transitionend` event.
            - infinite animations are canceled to initial state, and then played over after the screenshot.

            Defaults to `"allow"` that leaves animations untouched.
        caret : Union["hide", "initial", NoneType]
            When set to `"hide"`, screenshot will hide text caret. When set to `"initial"`, text caret behavior will not be changed.
            Defaults to `"hide"`.
        scale : Union["css", "device", NoneType]
            When set to `"css"`, screenshot will have a single pixel per each css pixel on the page. For high-dpi devices, this will
            keep screenshots small. Using `"device"` option will produce a single pixel per each device pixel, so screenhots of
            high-dpi devices will be twice as large or even larger.

            Defaults to `"device"`.
        mask : Union[List[Locator], NoneType]
            Specify locators that should be masked when the screenshot is taken. Masked elements will be overlayed with a pink box
            `#FF00FF` that completely covers its bounding box.

        Returns
        -------
        bytes
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.screenshot(
                    timeout=timeout,
                    type=type,
                    path=path,
                    quality=quality,
                    omitBackground=omit_background,
                    animations=animations,
                    caret=caret,
                    scale=scale,
                    mask=mapping.to_impl(mask),
                )
            )
        )

    def scroll_into_view_if_needed(self, *, timeout: float = None) -> NoneType:
        """Locator.scroll_into_view_if_needed

        This method waits for [actionability](https://playwright.dev/python/docs/actionability) checks, then tries to scroll element into view, unless it is
        completely visible as defined by
        [IntersectionObserver](https://developer.mozilla.org/en-US/docs/Web/API/Intersection_Observer_API)'s `ratio`.

        Parameters
        ----------
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.scroll_into_view_if_needed(timeout=timeout))
        )

    def select_option(
        self,
        value: typing.Union[str, typing.List[str]] = None,
        *,
        index: typing.Union[int, typing.List[int]] = None,
        label: typing.Union[str, typing.List[str]] = None,
        element: typing.Union["ElementHandle", typing.List["ElementHandle"]] = None,
        timeout: float = None,
        no_wait_after: bool = None,
        force: bool = None
    ) -> typing.List[str]:
        """Locator.select_option

        This method waits for [actionability](https://playwright.dev/python/docs/actionability) checks, waits until all specified options are present in the
        `<select>` element and selects these options.

        If the target element is not a `<select>` element, this method throws an error. However, if the element is inside the
        `<label>` element that has an associated
        [control](https://developer.mozilla.org/en-US/docs/Web/API/HTMLLabelElement/control), the control will be used instead.

        Returns the array of option values that have been successfully selected.

        Triggers a `change` and `input` event once all the provided options have been selected.

        ```py
        # single selection matching the value
        element.select_option(\"blue\")
        # single selection matching both the label
        element.select_option(label=\"blue\")
        # multiple selection
        element.select_option(value=[\"red\", \"green\", \"blue\"])
        ```

        Parameters
        ----------
        value : Union[List[str], str, NoneType]
            Options to select by value. If the `<select>` has the `multiple` attribute, all given options are selected, otherwise
            only the first option matching one of the passed options is selected. Optional.
        index : Union[List[int], int, NoneType]
            Options to select by index. Optional.
        label : Union[List[str], str, NoneType]
            Options to select by label. If the `<select>` has the `multiple` attribute, all given options are selected, otherwise
            only the first option matching one of the passed options is selected. Optional.
        element : Union[ElementHandle, List[ElementHandle], NoneType]
            Option elements to select. Optional.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.

        Returns
        -------
        List[str]
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.select_option(
                    value=mapping.to_impl(value),
                    index=mapping.to_impl(index),
                    label=mapping.to_impl(label),
                    element=mapping.to_impl(element),
                    timeout=timeout,
                    noWaitAfter=no_wait_after,
                    force=force,
                )
            )
        )

    def select_text(self, *, force: bool = None, timeout: float = None) -> NoneType:
        """Locator.select_text

        This method waits for [actionability](https://playwright.dev/python/docs/actionability) checks, then focuses the element and selects all its text
        content.

        If the element is inside the `<label>` element that has an associated
        [control](https://developer.mozilla.org/en-US/docs/Web/API/HTMLLabelElement/control), focuses and selects text in the
        control instead.

        Parameters
        ----------
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.select_text(force=force, timeout=timeout))
        )

    def set_input_files(
        self,
        files: typing.Union[
            str,
            pathlib.Path,
            FilePayload,
            typing.List[typing.Union[str, pathlib.Path]],
            typing.List[FilePayload],
        ],
        *,
        timeout: float = None,
        no_wait_after: bool = None
    ) -> NoneType:
        """Locator.set_input_files

        Sets the value of the file input to these file paths or files. If some of the `filePaths` are relative paths, then they
        are resolved relative to the current working directory. For empty array, clears the selected files.

        This method expects `Locator` to point to an
        [input element](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/input). However, if the element is inside the
        `<label>` element that has an associated
        [control](https://developer.mozilla.org/en-US/docs/Web/API/HTMLLabelElement/control), targets the control instead.

        Parameters
        ----------
        files : Union[List[Union[pathlib.Path, str]], List[{name: str, mimeType: str, buffer: bytes}], pathlib.Path, str, {name: str, mimeType: str, buffer: bytes}]
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.set_input_files(
                    files=mapping.to_impl(files),
                    timeout=timeout,
                    noWaitAfter=no_wait_after,
                )
            )
        )

    def tap(
        self,
        *,
        modifiers: typing.Optional[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        no_wait_after: bool = None,
        trial: bool = None
    ) -> NoneType:
        """Locator.tap

        This method taps the element by performing the following steps:
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the element, unless `force` option is set.
        1. Scroll the element into view if needed.
        1. Use `page.touchscreen` to tap the center of the element, or the specified `position`.
        1. Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.

        If the element is detached from the DOM at any moment during the action, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`. Passing
        zero timeout disables this.

        > NOTE: `element.tap()` requires that the `hasTouch` option of the browser context be set to true.

        Parameters
        ----------
        modifiers : Union[List[Union["Alt", "Control", "Meta", "Shift"]], NoneType]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores current
            modifiers back. If not specified, currently pressed modifiers are used.
        position : Union[{x: float, y: float}, NoneType]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the
            element.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        trial : Union[bool, NoneType]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults to
            `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.tap(
                    modifiers=mapping.to_impl(modifiers),
                    position=position,
                    timeout=timeout,
                    force=force,
                    noWaitAfter=no_wait_after,
                    trial=trial,
                )
            )
        )

    def text_content(self, *, timeout: float = None) -> typing.Optional[str]:
        """Locator.text_content

        Returns the `node.textContent`.

        Parameters
        ----------
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.

        Returns
        -------
        Union[str, NoneType]
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.text_content(timeout=timeout))
        )

    def type(
        self,
        text: str,
        *,
        delay: float = None,
        timeout: float = None,
        no_wait_after: bool = None
    ) -> NoneType:
        """Locator.type

        Focuses the element, and then sends a `keydown`, `keypress`/`input`, and `keyup` event for each character in the text.

        To press a special key, like `Control` or `ArrowDown`, use `locator.press()`.

        ```py
        element.type(\"hello\") # types instantly
        element.type(\"world\", delay=100) # types slower, like a user
        ```

        An example of typing into a text field and then submitting the form:

        ```py
        element = page.locator(\"input\")
        element.type(\"some text\")
        element.press(\"Enter\")
        ```

        Parameters
        ----------
        text : str
            A text to type into a focused element.
        delay : Union[float, NoneType]
            Time to wait between key presses in milliseconds. Defaults to 0.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.type(
                    text=text, delay=delay, timeout=timeout, noWaitAfter=no_wait_after
                )
            )
        )

    def uncheck(
        self,
        *,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        no_wait_after: bool = None,
        trial: bool = None
    ) -> NoneType:
        """Locator.uncheck

        This method checks the element by performing the following steps:
        1. Ensure that element is a checkbox or a radio input. If not, this method throws. If the element is already
           unchecked, this method returns immediately.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the element, unless `force` option is set.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to click in the center of the element.
        1. Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.
        1. Ensure that the element is now unchecked. If not, this method throws.

        If the element is detached from the DOM at any moment during the action, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`. Passing
        zero timeout disables this.

        Parameters
        ----------
        position : Union[{x: float, y: float}, NoneType]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the
            element.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        trial : Union[bool, NoneType]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults to
            `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.uncheck(
                    position=position,
                    timeout=timeout,
                    force=force,
                    noWaitAfter=no_wait_after,
                    trial=trial,
                )
            )
        )

    def all_inner_texts(self) -> typing.List[str]:
        """Locator.all_inner_texts

        Returns an array of `node.innerText` values for all matching nodes.

        Returns
        -------
        List[str]
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.all_inner_texts()))

    def all_text_contents(self) -> typing.List[str]:
        """Locator.all_text_contents

        Returns an array of `node.textContent` values for all matching nodes.

        Returns
        -------
        List[str]
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.all_text_contents()))

    def wait_for(
        self,
        *,
        timeout: float = None,
        state: Literal["attached", "detached", "hidden", "visible"] = None
    ) -> NoneType:
        """Locator.wait_for

        Returns when element specified by locator satisfies the `state` option.

        If target element already satisfies the condition, the method returns immediately. Otherwise, waits for up to `timeout`
        milliseconds until the condition is met.

        ```py
        order_sent = page.locator(\"#order-sent\")
        order_sent.wait_for()
        ```

        Parameters
        ----------
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        state : Union["attached", "detached", "hidden", "visible", NoneType]
            Defaults to `'visible'`. Can be either:
            - `'attached'` - wait for element to be present in DOM.
            - `'detached'` - wait for element to not be present in DOM.
            - `'visible'` - wait for element to have non-empty bounding box and no `visibility:hidden`. Note that element without
              any content or with `display:none` has an empty bounding box and is not considered visible.
            - `'hidden'` - wait for element to be either detached from DOM, or have an empty bounding box or `visibility:hidden`.
              This is opposite to the `'visible'` option.
        """

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.wait_for(timeout=timeout, state=state))
        )

    def set_checked(
        self,
        checked: bool,
        *,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        no_wait_after: bool = None,
        trial: bool = None
    ) -> NoneType:
        """Locator.set_checked

        This method checks or unchecks an element by performing the following steps:
        1. Ensure that matched element is a checkbox or a radio input. If not, this method throws.
        1. If the element already has the right checked state, this method returns immediately.
        1. Wait for [actionability](https://playwright.dev/python/docs/actionability) checks on the matched element, unless `force` option is set. If the
           element is detached during the checks, the whole action is retried.
        1. Scroll the element into view if needed.
        1. Use `page.mouse` to click in the center of the element.
        1. Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.
        1. Ensure that the element is now checked or unchecked. If not, this method throws.

        When all steps combined have not finished during the specified `timeout`, this method throws a `TimeoutError`. Passing
        zero timeout disables this.

        Parameters
        ----------
        checked : bool
            Whether to check or uncheck the checkbox.
        position : Union[{x: float, y: float}, NoneType]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the
            element.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by
            using the `browser_context.set_default_timeout()` or `page.set_default_timeout()` methods.
        force : Union[bool, NoneType]
            Whether to bypass the [actionability](../actionability.md) checks. Defaults to `false`.
        no_wait_after : Union[bool, NoneType]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can
            opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to
            inaccessible pages. Defaults to `false`.
        trial : Union[bool, NoneType]
            When set, this method only performs the [actionability](../actionability.md) checks and skips the action. Defaults to
            `false`. Useful to wait until the element is ready for the action without performing it.
        """

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.set_checked(
                    checked=checked,
                    position=position,
                    timeout=timeout,
                    force=force,
                    noWaitAfter=no_wait_after,
                    trial=trial,
                )
            )
        )

    def highlight(self) -> NoneType:
        """Locator.highlight

        Highlight the corresponding element(s) on the screen. Useful for debugging, don't commit the code that uses
        `locator.highlight()`.
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.highlight()))


mapping.register(LocatorImpl, Locator)


class APIResponse(SyncBase):
    @property
    def ok(self) -> bool:
        """APIResponse.ok

        Contains a boolean stating whether the response was successful (status in the range 200-299) or not.

        Returns
        -------
        bool
        """
        return mapping.from_maybe_impl(self._impl_obj.ok)

    @property
    def url(self) -> str:
        """APIResponse.url

        Contains the URL of the response.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.url)

    @property
    def status(self) -> int:
        """APIResponse.status

        Contains the status code of the response (e.g., 200 for a success).

        Returns
        -------
        int
        """
        return mapping.from_maybe_impl(self._impl_obj.status)

    @property
    def status_text(self) -> str:
        """APIResponse.status_text

        Contains the status text of the response (e.g. usually an \"OK\" for a success).

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.status_text)

    @property
    def headers(self) -> typing.Dict[str, str]:
        """APIResponse.headers

        An object with all the response HTTP headers associated with this response.

        Returns
        -------
        Dict[str, str]
        """
        return mapping.from_maybe_impl(self._impl_obj.headers)

    @property
    def headers_array(self) -> typing.List[NameValue]:
        """APIResponse.headers_array

        An array with all the request HTTP headers associated with this response. Header names are not lower-cased. Headers with
        multiple entries, such as `Set-Cookie`, appear in the array multiple times.

        Returns
        -------
        List[{name: str, value: str}]
        """
        return mapping.from_impl_list(self._impl_obj.headers_array)

    def body(self) -> bytes:
        """APIResponse.body

        Returns the buffer with response body.

        Returns
        -------
        bytes
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.body()))

    def text(self) -> str:
        """APIResponse.text

        Returns the text representation of response body.

        Returns
        -------
        str
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.text()))

    def json(self) -> typing.Any:
        """APIResponse.json

        Returns the JSON representation of response body.

        This method will throw if the response body is not parsable via `JSON.parse`.

        Returns
        -------
        Any
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.json()))

    def dispose(self) -> NoneType:
        """APIResponse.dispose

        Disposes the body of this response. If not called then the body will stay in memory until the context closes.
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.dispose()))


mapping.register(APIResponseImpl, APIResponse)


class APIRequestContext(SyncBase):
    def dispose(self) -> NoneType:
        """APIRequestContext.dispose

        All responses returned by `a_pi_request_context.get()` and similar methods are stored in the memory, so that you
        can later call `a_pi_response.body()`. This method discards all stored responses, and makes
        `a_pi_response.body()` throw \"Response disposed\" error.
        """

        return mapping.from_maybe_impl(self._sync(self._impl_obj.dispose()))

    def delete(
        self,
        url: str,
        *,
        params: typing.Optional[
            typing.Dict[str, typing.Union[str, float, bool]]
        ] = None,
        headers: typing.Optional[typing.Dict[str, str]] = None,
        data: typing.Union[typing.Any, bytes, str] = None,
        form: typing.Optional[typing.Dict[str, typing.Union[str, float, bool]]] = None,
        multipart: typing.Optional[
            typing.Dict[str, typing.Union[bytes, bool, float, str, FilePayload]]
        ] = None,
        timeout: float = None,
        fail_on_status_code: bool = None,
        ignore_https_errors: bool = None
    ) -> "APIResponse":
        """APIRequestContext.delete

        Sends HTTP(S) [DELETE](https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/DELETE) request and returns its
        response. The method will populate request cookies from the context and update context cookies from the response. The
        method will automatically follow redirects.

        Parameters
        ----------
        url : str
            Target URL.
        params : Union[Dict[str, Union[bool, float, str]], NoneType]
            Query parameters to be sent with the URL.
        headers : Union[Dict[str, str], NoneType]
            Allows to set HTTP headers.
        data : Union[Any, bytes, str, NoneType]
            Allows to set post data of the request. If the data parameter is an object, it will be serialized to json string and
            `content-type` header will be set to `application/json` if not explicitly set. Otherwise the `content-type` header will
            be set to `application/octet-stream` if not explicitly set.
        form : Union[Dict[str, Union[bool, float, str]], NoneType]
            Provides an object that will be serialized as html form using `application/x-www-form-urlencoded` encoding and sent as
            this request body. If this parameter is specified `content-type` header will be set to
            `application/x-www-form-urlencoded` unless explicitly provided.
        multipart : Union[Dict[str, Union[bool, bytes, float, str, {name: str, mimeType: str, buffer: bytes}]], NoneType]
            Provides an object that will be serialized as html form using `multipart/form-data` encoding and sent as this request
            body. If this parameter is specified `content-type` header will be set to `multipart/form-data` unless explicitly
            provided. File values can be passed either as [`fs.ReadStream`](https://nodejs.org/api/fs.html#fs_class_fs_readstream)
            or as file-like object containing file name, mime-type and its content.
        timeout : Union[float, NoneType]
            Request timeout in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout.
        fail_on_status_code : Union[bool, NoneType]
            Whether to throw on response codes other than 2xx and 3xx. By default response object is returned for all status codes.
        ignore_https_errors : Union[bool, NoneType]
            Whether to ignore HTTPS errors when sending network requests. Defaults to `false`.

        Returns
        -------
        APIResponse
        """

        return mapping.from_impl(
            self._sync(
                self._impl_obj.delete(
                    url=url,
                    params=mapping.to_impl(params),
                    headers=mapping.to_impl(headers),
                    data=mapping.to_impl(data),
                    form=mapping.to_impl(form),
                    multipart=mapping.to_impl(multipart),
                    timeout=timeout,
                    failOnStatusCode=fail_on_status_code,
                    ignoreHTTPSErrors=ignore_https_errors,
                )
            )
        )

    def head(
        self,
        url: str,
        *,
        params: typing.Optional[
            typing.Dict[str, typing.Union[str, float, bool]]
        ] = None,
        headers: typing.Optional[typing.Dict[str, str]] = None,
        timeout: float = None,
        fail_on_status_code: bool = None,
        ignore_https_errors: bool = None
    ) -> "APIResponse":
        """APIRequestContext.head

        Sends HTTP(S) [HEAD](https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/HEAD) request and returns its response.
        The method will populate request cookies from the context and update context cookies from the response. The method will
        automatically follow redirects.

        Parameters
        ----------
        url : str
            Target URL.
        params : Union[Dict[str, Union[bool, float, str]], NoneType]
            Query parameters to be sent with the URL.
        headers : Union[Dict[str, str], NoneType]
            Allows to set HTTP headers.
        timeout : Union[float, NoneType]
            Request timeout in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout.
        fail_on_status_code : Union[bool, NoneType]
            Whether to throw on response codes other than 2xx and 3xx. By default response object is returned for all status codes.
        ignore_https_errors : Union[bool, NoneType]
            Whether to ignore HTTPS errors when sending network requests. Defaults to `false`.

        Returns
        -------
        APIResponse
        """

        return mapping.from_impl(
            self._sync(
                self._impl_obj.head(
                    url=url,
                    params=mapping.to_impl(params),
                    headers=mapping.to_impl(headers),
                    timeout=timeout,
                    failOnStatusCode=fail_on_status_code,
                    ignoreHTTPSErrors=ignore_https_errors,
                )
            )
        )

    def get(
        self,
        url: str,
        *,
        params: typing.Optional[
            typing.Dict[str, typing.Union[str, float, bool]]
        ] = None,
        headers: typing.Optional[typing.Dict[str, str]] = None,
        timeout: float = None,
        fail_on_status_code: bool = None,
        ignore_https_errors: bool = None
    ) -> "APIResponse":
        """APIRequestContext.get

        Sends HTTP(S) [GET](https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/GET) request and returns its response. The
        method will populate request cookies from the context and update context cookies from the response. The method will
        automatically follow redirects.

        Parameters
        ----------
        url : str
            Target URL.
        params : Union[Dict[str, Union[bool, float, str]], NoneType]
            Query parameters to be sent with the URL.
        headers : Union[Dict[str, str], NoneType]
            Allows to set HTTP headers.
        timeout : Union[float, NoneType]
            Request timeout in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout.
        fail_on_status_code : Union[bool, NoneType]
            Whether to throw on response codes other than 2xx and 3xx. By default response object is returned for all status codes.
        ignore_https_errors : Union[bool, NoneType]
            Whether to ignore HTTPS errors when sending network requests. Defaults to `false`.

        Returns
        -------
        APIResponse
        """

        return mapping.from_impl(
            self._sync(
                self._impl_obj.get(
                    url=url,
                    params=mapping.to_impl(params),
                    headers=mapping.to_impl(headers),
                    timeout=timeout,
                    failOnStatusCode=fail_on_status_code,
                    ignoreHTTPSErrors=ignore_https_errors,
                )
            )
        )

    def patch(
        self,
        url: str,
        *,
        params: typing.Optional[
            typing.Dict[str, typing.Union[str, float, bool]]
        ] = None,
        headers: typing.Optional[typing.Dict[str, str]] = None,
        data: typing.Union[typing.Any, bytes, str] = None,
        form: typing.Optional[typing.Dict[str, typing.Union[str, float, bool]]] = None,
        multipart: typing.Optional[
            typing.Dict[str, typing.Union[bytes, bool, float, str, FilePayload]]
        ] = None,
        timeout: float = None,
        fail_on_status_code: bool = None,
        ignore_https_errors: bool = None
    ) -> "APIResponse":
        """APIRequestContext.patch

        Sends HTTP(S) [PATCH](https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/PATCH) request and returns its response.
        The method will populate request cookies from the context and update context cookies from the response. The method will
        automatically follow redirects.

        Parameters
        ----------
        url : str
            Target URL.
        params : Union[Dict[str, Union[bool, float, str]], NoneType]
            Query parameters to be sent with the URL.
        headers : Union[Dict[str, str], NoneType]
            Allows to set HTTP headers.
        data : Union[Any, bytes, str, NoneType]
            Allows to set post data of the request. If the data parameter is an object, it will be serialized to json string and
            `content-type` header will be set to `application/json` if not explicitly set. Otherwise the `content-type` header will
            be set to `application/octet-stream` if not explicitly set.
        form : Union[Dict[str, Union[bool, float, str]], NoneType]
            Provides an object that will be serialized as html form using `application/x-www-form-urlencoded` encoding and sent as
            this request body. If this parameter is specified `content-type` header will be set to
            `application/x-www-form-urlencoded` unless explicitly provided.
        multipart : Union[Dict[str, Union[bool, bytes, float, str, {name: str, mimeType: str, buffer: bytes}]], NoneType]
            Provides an object that will be serialized as html form using `multipart/form-data` encoding and sent as this request
            body. If this parameter is specified `content-type` header will be set to `multipart/form-data` unless explicitly
            provided. File values can be passed either as [`fs.ReadStream`](https://nodejs.org/api/fs.html#fs_class_fs_readstream)
            or as file-like object containing file name, mime-type and its content.
        timeout : Union[float, NoneType]
            Request timeout in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout.
        fail_on_status_code : Union[bool, NoneType]
            Whether to throw on response codes other than 2xx and 3xx. By default response object is returned for all status codes.
        ignore_https_errors : Union[bool, NoneType]
            Whether to ignore HTTPS errors when sending network requests. Defaults to `false`.

        Returns
        -------
        APIResponse
        """

        return mapping.from_impl(
            self._sync(
                self._impl_obj.patch(
                    url=url,
                    params=mapping.to_impl(params),
                    headers=mapping.to_impl(headers),
                    data=mapping.to_impl(data),
                    form=mapping.to_impl(form),
                    multipart=mapping.to_impl(multipart),
                    timeout=timeout,
                    failOnStatusCode=fail_on_status_code,
                    ignoreHTTPSErrors=ignore_https_errors,
                )
            )
        )

    def put(
        self,
        url: str,
        *,
        params: typing.Optional[
            typing.Dict[str, typing.Union[str, float, bool]]
        ] = None,
        headers: typing.Optional[typing.Dict[str, str]] = None,
        data: typing.Union[typing.Any, bytes, str] = None,
        form: typing.Optional[typing.Dict[str, typing.Union[str, float, bool]]] = None,
        multipart: typing.Optional[
            typing.Dict[str, typing.Union[bytes, bool, float, str, FilePayload]]
        ] = None,
        timeout: float = None,
        fail_on_status_code: bool = None,
        ignore_https_errors: bool = None
    ) -> "APIResponse":
        """APIRequestContext.put

        Sends HTTP(S) [PUT](https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/PUT) request and returns its response. The
        method will populate request cookies from the context and update context cookies from the response. The method will
        automatically follow redirects.

        Parameters
        ----------
        url : str
            Target URL.
        params : Union[Dict[str, Union[bool, float, str]], NoneType]
            Query parameters to be sent with the URL.
        headers : Union[Dict[str, str], NoneType]
            Allows to set HTTP headers.
        data : Union[Any, bytes, str, NoneType]
            Allows to set post data of the request. If the data parameter is an object, it will be serialized to json string and
            `content-type` header will be set to `application/json` if not explicitly set. Otherwise the `content-type` header will
            be set to `application/octet-stream` if not explicitly set.
        form : Union[Dict[str, Union[bool, float, str]], NoneType]
            Provides an object that will be serialized as html form using `application/x-www-form-urlencoded` encoding and sent as
            this request body. If this parameter is specified `content-type` header will be set to
            `application/x-www-form-urlencoded` unless explicitly provided.
        multipart : Union[Dict[str, Union[bool, bytes, float, str, {name: str, mimeType: str, buffer: bytes}]], NoneType]
            Provides an object that will be serialized as html form using `multipart/form-data` encoding and sent as this request
            body. If this parameter is specified `content-type` header will be set to `multipart/form-data` unless explicitly
            provided. File values can be passed either as [`fs.ReadStream`](https://nodejs.org/api/fs.html#fs_class_fs_readstream)
            or as file-like object containing file name, mime-type and its content.
        timeout : Union[float, NoneType]
            Request timeout in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout.
        fail_on_status_code : Union[bool, NoneType]
            Whether to throw on response codes other than 2xx and 3xx. By default response object is returned for all status codes.
        ignore_https_errors : Union[bool, NoneType]
            Whether to ignore HTTPS errors when sending network requests. Defaults to `false`.

        Returns
        -------
        APIResponse
        """

        return mapping.from_impl(
            self._sync(
                self._impl_obj.put(
                    url=url,
                    params=mapping.to_impl(params),
                    headers=mapping.to_impl(headers),
                    data=mapping.to_impl(data),
                    form=mapping.to_impl(form),
                    multipart=mapping.to_impl(multipart),
                    timeout=timeout,
                    failOnStatusCode=fail_on_status_code,
                    ignoreHTTPSErrors=ignore_https_errors,
                )
            )
        )

    def post(
        self,
        url: str,
        *,
        params: typing.Optional[
            typing.Dict[str, typing.Union[str, float, bool]]
        ] = None,
        headers: typing.Optional[typing.Dict[str, str]] = None,
        data: typing.Union[typing.Any, bytes, str] = None,
        form: typing.Optional[typing.Dict[str, typing.Union[str, float, bool]]] = None,
        multipart: typing.Optional[
            typing.Dict[str, typing.Union[bytes, bool, float, str, FilePayload]]
        ] = None,
        timeout: float = None,
        fail_on_status_code: bool = None,
        ignore_https_errors: bool = None
    ) -> "APIResponse":
        """APIRequestContext.post

        Sends HTTP(S) [POST](https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/POST) request and returns its response.
        The method will populate request cookies from the context and update context cookies from the response. The method will
        automatically follow redirects.

        Parameters
        ----------
        url : str
            Target URL.
        params : Union[Dict[str, Union[bool, float, str]], NoneType]
            Query parameters to be sent with the URL.
        headers : Union[Dict[str, str], NoneType]
            Allows to set HTTP headers.
        data : Union[Any, bytes, str, NoneType]
            Allows to set post data of the request. If the data parameter is an object, it will be serialized to json string and
            `content-type` header will be set to `application/json` if not explicitly set. Otherwise the `content-type` header will
            be set to `application/octet-stream` if not explicitly set.
        form : Union[Dict[str, Union[bool, float, str]], NoneType]
            Provides an object that will be serialized as html form using `application/x-www-form-urlencoded` encoding and sent as
            this request body. If this parameter is specified `content-type` header will be set to
            `application/x-www-form-urlencoded` unless explicitly provided.
        multipart : Union[Dict[str, Union[bool, bytes, float, str, {name: str, mimeType: str, buffer: bytes}]], NoneType]
            Provides an object that will be serialized as html form using `multipart/form-data` encoding and sent as this request
            body. If this parameter is specified `content-type` header will be set to `multipart/form-data` unless explicitly
            provided. File values can be passed either as [`fs.ReadStream`](https://nodejs.org/api/fs.html#fs_class_fs_readstream)
            or as file-like object containing file name, mime-type and its content.
        timeout : Union[float, NoneType]
            Request timeout in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout.
        fail_on_status_code : Union[bool, NoneType]
            Whether to throw on response codes other than 2xx and 3xx. By default response object is returned for all status codes.
        ignore_https_errors : Union[bool, NoneType]
            Whether to ignore HTTPS errors when sending network requests. Defaults to `false`.

        Returns
        -------
        APIResponse
        """

        return mapping.from_impl(
            self._sync(
                self._impl_obj.post(
                    url=url,
                    params=mapping.to_impl(params),
                    headers=mapping.to_impl(headers),
                    data=mapping.to_impl(data),
                    form=mapping.to_impl(form),
                    multipart=mapping.to_impl(multipart),
                    timeout=timeout,
                    failOnStatusCode=fail_on_status_code,
                    ignoreHTTPSErrors=ignore_https_errors,
                )
            )
        )

    def fetch(
        self,
        url_or_request: typing.Union[str, "Request"],
        *,
        params: typing.Optional[
            typing.Dict[str, typing.Union[str, float, bool]]
        ] = None,
        method: str = None,
        headers: typing.Optional[typing.Dict[str, str]] = None,
        data: typing.Union[typing.Any, bytes, str] = None,
        form: typing.Optional[typing.Dict[str, typing.Union[str, float, bool]]] = None,
        multipart: typing.Optional[
            typing.Dict[str, typing.Union[bytes, bool, float, str, FilePayload]]
        ] = None,
        timeout: float = None,
        fail_on_status_code: bool = None,
        ignore_https_errors: bool = None
    ) -> "APIResponse":
        """APIRequestContext.fetch

        Sends HTTP(S) request and returns its response. The method will populate request cookies from the context and update
        context cookies from the response. The method will automatically follow redirects.

        Parameters
        ----------
        url_or_request : Union[Request, str]
            Target URL or Request to get all parameters from.
        params : Union[Dict[str, Union[bool, float, str]], NoneType]
            Query parameters to be sent with the URL.
        method : Union[str, NoneType]
            If set changes the fetch method (e.g. [PUT](https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/PUT) or
            [POST](https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/POST)). If not specified, GET method is used.
        headers : Union[Dict[str, str], NoneType]
            Allows to set HTTP headers.
        data : Union[Any, bytes, str, NoneType]
            Allows to set post data of the request. If the data parameter is an object, it will be serialized to json string and
            `content-type` header will be set to `application/json` if not explicitly set. Otherwise the `content-type` header will
            be set to `application/octet-stream` if not explicitly set.
        form : Union[Dict[str, Union[bool, float, str]], NoneType]
            Provides an object that will be serialized as html form using `application/x-www-form-urlencoded` encoding and sent as
            this request body. If this parameter is specified `content-type` header will be set to
            `application/x-www-form-urlencoded` unless explicitly provided.
        multipart : Union[Dict[str, Union[bool, bytes, float, str, {name: str, mimeType: str, buffer: bytes}]], NoneType]
            Provides an object that will be serialized as html form using `multipart/form-data` encoding and sent as this request
            body. If this parameter is specified `content-type` header will be set to `multipart/form-data` unless explicitly
            provided. File values can be passed either as [`fs.ReadStream`](https://nodejs.org/api/fs.html#fs_class_fs_readstream)
            or as file-like object containing file name, mime-type and its content.
        timeout : Union[float, NoneType]
            Request timeout in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout.
        fail_on_status_code : Union[bool, NoneType]
            Whether to throw on response codes other than 2xx and 3xx. By default response object is returned for all status codes.
        ignore_https_errors : Union[bool, NoneType]
            Whether to ignore HTTPS errors when sending network requests. Defaults to `false`.

        Returns
        -------
        APIResponse
        """

        return mapping.from_impl(
            self._sync(
                self._impl_obj.fetch(
                    urlOrRequest=url_or_request,
                    params=mapping.to_impl(params),
                    method=method,
                    headers=mapping.to_impl(headers),
                    data=mapping.to_impl(data),
                    form=mapping.to_impl(form),
                    multipart=mapping.to_impl(multipart),
                    timeout=timeout,
                    failOnStatusCode=fail_on_status_code,
                    ignoreHTTPSErrors=ignore_https_errors,
                )
            )
        )

    def storage_state(
        self, *, path: typing.Union[str, pathlib.Path] = None
    ) -> StorageState:
        """APIRequestContext.storage_state

        Returns storage state for this request context, contains current cookies and local storage snapshot if it was passed to
        the constructor.

        Parameters
        ----------
        path : Union[pathlib.Path, str, NoneType]
            The file path to save the storage state to. If `path` is a relative path, then it is resolved relative to current
            working directory. If no path is provided, storage state is still returned, but won't be saved to the disk.

        Returns
        -------
        {cookies: List[{name: str, value: str, domain: str, path: str, expires: float, httpOnly: bool, secure: bool, sameSite: Union["Lax", "None", "Strict"]}], origins: List[{origin: str, localStorage: List[{name: str, value: str}]}]}
        """

        return mapping.from_impl(self._sync(self._impl_obj.storage_state(path=path)))


mapping.register(APIRequestContextImpl, APIRequestContext)


class APIRequest(SyncBase):
    def new_context(
        self,
        *,
        base_url: str = None,
        extra_http_headers: typing.Optional[typing.Dict[str, str]] = None,
        http_credentials: HttpCredentials = None,
        ignore_https_errors: bool = None,
        proxy: ProxySettings = None,
        user_agent: str = None,
        timeout: float = None,
        storage_state: typing.Union[StorageState, str, pathlib.Path] = None
    ) -> "APIRequestContext":
        """APIRequest.new_context

        Creates new instances of `APIRequestContext`.

        Parameters
        ----------
        base_url : Union[str, NoneType]
            Methods like `a_pi_request_context.get()` take the base URL into consideration by using the
            [`URL()`](https://developer.mozilla.org/en-US/docs/Web/API/URL/URL) constructor for building the corresponding URL.
            Examples:
            - baseURL: `http://localhost:3000` and sending request to `/bar.html` results in `http://localhost:3000/bar.html`
            - baseURL: `http://localhost:3000/foo/` and sending request to `./bar.html` results in
              `http://localhost:3000/foo/bar.html`
            - baseURL: `http://localhost:3000/foo` (without trailing slash) and navigating to `./bar.html` results in
              `http://localhost:3000/bar.html`
        extra_http_headers : Union[Dict[str, str], NoneType]
            An object containing additional HTTP headers to be sent with every request.
        http_credentials : Union[{username: str, password: str}, NoneType]
            Credentials for [HTTP authentication](https://developer.mozilla.org/en-US/docs/Web/HTTP/Authentication).
        ignore_https_errors : Union[bool, NoneType]
            Whether to ignore HTTPS errors when sending network requests. Defaults to `false`.
        proxy : Union[{server: str, bypass: Union[str, NoneType], username: Union[str, NoneType], password: Union[str, NoneType]}, NoneType]
            Network proxy settings.
        user_agent : Union[str, NoneType]
            Specific user agent to use in this context.
        timeout : Union[float, NoneType]
            Maximum time in milliseconds to wait for the response. Defaults to `30000` (30 seconds). Pass `0` to disable timeout.
        storage_state : Union[pathlib.Path, str, {cookies: List[{name: str, value: str, domain: str, path: str, expires: float, httpOnly: bool, secure: bool, sameSite: Union["Lax", "None", "Strict"]}], origins: List[{origin: str, localStorage: List[{name: str, value: str}]}]}, NoneType]
            Populates context with given storage state. This option can be used to initialize context with logged-in information
            obtained via `browser_context.storage_state()` or `a_pi_request_context.storage_state()`. Either a path to the
            file with saved storage, or the value returned by one of `browser_context.storage_state()` or
            `a_pi_request_context.storage_state()` methods.

        Returns
        -------
        APIRequestContext
        """

        return mapping.from_impl(
            self._sync(
                self._impl_obj.new_context(
                    baseURL=base_url,
                    extraHTTPHeaders=mapping.to_impl(extra_http_headers),
                    httpCredentials=http_credentials,
                    ignoreHTTPSErrors=ignore_https_errors,
                    proxy=proxy,
                    userAgent=user_agent,
                    timeout=timeout,
                    storageState=storage_state,
                )
            )
        )


mapping.register(APIRequestImpl, APIRequest)


class PageAssertions(SyncBase):
    def to_have_title(
        self,
        title_or_reg_exp: typing.Union[typing.Pattern, str],
        *,
        timeout: float = None
    ) -> NoneType:
        """PageAssertions.to_have_title

        Ensures the page has the given title.

        ```py
        import re
        from playwright.sync_api import expect

        # ...
        expect(page).to_have_title(re.compile(r\".*checkout\"))
        ```

        Parameters
        ----------
        title_or_reg_exp : Union[Pattern, str]
            Expected title or RegExp.
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.to_have_title(
                    title_or_reg_exp=title_or_reg_exp, timeout=timeout
                )
            )
        )

    def not_to_have_title(
        self,
        title_or_reg_exp: typing.Union[typing.Pattern, str],
        *,
        timeout: float = None
    ) -> NoneType:
        """PageAssertions.not_to_have_title

        The opposite of `page_assertions.to_have_title()`.

        Parameters
        ----------
        title_or_reg_exp : Union[Pattern, str]
            Expected title or RegExp.
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.not_to_have_title(
                    title_or_reg_exp=title_or_reg_exp, timeout=timeout
                )
            )
        )

    def to_have_url(
        self,
        url_or_reg_exp: typing.Union[str, typing.Pattern],
        *,
        timeout: float = None
    ) -> NoneType:
        """PageAssertions.to_have_url

        Ensures the page is navigated to the given URL.

        ```py
        import re
        from playwright.sync_api import expect

        # ...
        expect(page).to_have_url(re.compile(\".*checkout\"))
        ```

        Parameters
        ----------
        url_or_reg_exp : Union[Pattern, str]
            Expected substring or RegExp.
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.to_have_url(
                    url_or_reg_exp=url_or_reg_exp, timeout=timeout
                )
            )
        )

    def not_to_have_url(
        self,
        url_or_reg_exp: typing.Union[typing.Pattern, str],
        *,
        timeout: float = None
    ) -> NoneType:
        """PageAssertions.not_to_have_url

        The opposite of `page_assertions.to_have_url()`.

        Parameters
        ----------
        url_or_reg_exp : Union[Pattern, str]
            Expected substring or RegExp.
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.not_to_have_url(
                    url_or_reg_exp=url_or_reg_exp, timeout=timeout
                )
            )
        )


mapping.register(PageAssertionsImpl, PageAssertions)


class LocatorAssertions(SyncBase):
    def to_contain_text(
        self,
        expected: typing.Union[
            typing.List[typing.Union[typing.Pattern, str]], typing.Pattern, str
        ],
        *,
        use_inner_text: bool = None,
        timeout: float = None,
        ignore_case: bool = None
    ) -> NoneType:
        """LocatorAssertions.to_contain_text

        Ensures the `Locator` points to an element that contains the given text. You can use regular expressions for the value
        as well.

        ```py
        import re
        from playwright.sync_api import expect

        locator = page.locator('.title')
        expect(locator).to_contain_text(\"substring\")
        expect(locator).to_contain_text(re.compile(r\"\\d messages\"))
        ```

        Note that if array is passed as an expected value, entire lists of elements can be asserted:

        ```py
        import re
        from playwright.sync_api import expect

        locator = page.locator(\"list > .list-item\")
        expect(locator).to_contain_text([\"Text 1\", \"Text 4\", \"Text 5\"])
        ```

        Parameters
        ----------
        expected : Union[List[Union[Pattern, str]], Pattern, str]
            Expected substring or RegExp or a list of those.
        use_inner_text : Union[bool, NoneType]
            Whether to use `element.innerText` instead of `element.textContent` when retrieving DOM node text.
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        ignore_case : Union[bool, NoneType]
            Whether to perform case-insensitive match. `ignoreCase` option takes precedence over the corresponding regular
            expression flag if specified.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.to_contain_text(
                    expected=mapping.to_impl(expected),
                    use_inner_text=use_inner_text,
                    timeout=timeout,
                    ignore_case=ignore_case,
                )
            )
        )

    def not_to_contain_text(
        self,
        expected: typing.Union[
            typing.List[typing.Union[typing.Pattern, str]], typing.Pattern, str
        ],
        *,
        use_inner_text: bool = None,
        timeout: float = None,
        ignore_case: bool = None
    ) -> NoneType:
        """LocatorAssertions.not_to_contain_text

        The opposite of `locator_assertions.to_contain_text()`.

        Parameters
        ----------
        expected : Union[List[Union[Pattern, str]], Pattern, str]
            Expected substring or RegExp or a list of those.
        use_inner_text : Union[bool, NoneType]
            Whether to use `element.innerText` instead of `element.textContent` when retrieving DOM node text.
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        ignore_case : Union[bool, NoneType]
            Whether to perform case-insensitive match. `ignoreCase` option takes precedence over the corresponding regular
            expression flag if specified.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.not_to_contain_text(
                    expected=mapping.to_impl(expected),
                    use_inner_text=use_inner_text,
                    timeout=timeout,
                    ignore_case=ignore_case,
                )
            )
        )

    def to_have_attribute(
        self,
        name: str,
        value: typing.Union[str, typing.Pattern],
        *,
        timeout: float = None
    ) -> NoneType:
        """LocatorAssertions.to_have_attribute

        Ensures the `Locator` points to an element with given attribute.

        ```py
        from playwright.sync_api import expect

        locator = page.locator(\"input\")
        expect(locator).to_have_attribute(\"type\", \"text\")
        ```

        Parameters
        ----------
        name : str
            Attribute name.
        value : Union[Pattern, str]
            Expected attribute value.
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.to_have_attribute(
                    name=name, value=value, timeout=timeout
                )
            )
        )

    def not_to_have_attribute(
        self,
        name: str,
        value: typing.Union[str, typing.Pattern],
        *,
        timeout: float = None
    ) -> NoneType:
        """LocatorAssertions.not_to_have_attribute

        The opposite of `locator_assertions.to_have_attribute()`.

        Parameters
        ----------
        name : str
            Attribute name.
        value : Union[Pattern, str]
            Expected attribute value.
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.not_to_have_attribute(
                    name=name, value=value, timeout=timeout
                )
            )
        )

    def to_have_class(
        self,
        expected: typing.Union[
            typing.List[typing.Union[typing.Pattern, str]], typing.Pattern, str
        ],
        *,
        timeout: float = None
    ) -> NoneType:
        """LocatorAssertions.to_have_class

        Ensures the `Locator` points to an element with given CSS class.

        ```py
        from playwright.sync_api import expect

        locator = page.locator(\"#component\")
        expect(locator).to_have_class(re.compile(r\"selected\"))
        ```

        Note that if array is passed as an expected value, entire lists of elements can be asserted:

        ```py
        from playwright.sync_api import expect

        locator = page.locator(\"list > .component\")
        expect(locator).to_have_class([\"component\", \"component selected\", \"component\"])
        ```

        Parameters
        ----------
        expected : Union[List[Union[Pattern, str]], Pattern, str]
            Expected class or RegExp or a list of those.
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.to_have_class(
                    expected=mapping.to_impl(expected), timeout=timeout
                )
            )
        )

    def not_to_have_class(
        self,
        expected: typing.Union[
            typing.List[typing.Union[typing.Pattern, str]], typing.Pattern, str
        ],
        *,
        timeout: float = None
    ) -> NoneType:
        """LocatorAssertions.not_to_have_class

        The opposite of `locator_assertions.to_have_class()`.

        Parameters
        ----------
        expected : Union[List[Union[Pattern, str]], Pattern, str]
            Expected class or RegExp or a list of those.
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.not_to_have_class(
                    expected=mapping.to_impl(expected), timeout=timeout
                )
            )
        )

    def to_have_count(self, count: int, *, timeout: float = None) -> NoneType:
        """LocatorAssertions.to_have_count

        Ensures the `Locator` resolves to an exact number of DOM nodes.

        ```py
        from playwright.sync_api import expect

        locator = page.locator(\"list > .component\")
        expect(locator).to_have_count(3)
        ```

        Parameters
        ----------
        count : int
            Expected count.
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.to_have_count(count=count, timeout=timeout))
        )

    def not_to_have_count(self, count: int, *, timeout: float = None) -> NoneType:
        """LocatorAssertions.not_to_have_count

        The opposite of `locator_assertions.to_have_count()`.

        Parameters
        ----------
        count : int
            Expected count.
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.not_to_have_count(count=count, timeout=timeout))
        )

    def to_have_css(
        self,
        name: str,
        value: typing.Union[str, typing.Pattern],
        *,
        timeout: float = None
    ) -> NoneType:
        """LocatorAssertions.to_have_css

        Ensures the `Locator` resolves to an element with the given computed CSS style.

        ```py
        from playwright.sync_api import expect

        locator = page.locator(\"button\")
        expect(locator).to_have_css(\"display\", \"flex\")
        ```

        Parameters
        ----------
        name : str
            CSS property name.
        value : Union[Pattern, str]
            CSS property value.
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.to_have_css(name=name, value=value, timeout=timeout)
            )
        )

    def not_to_have_css(
        self,
        name: str,
        value: typing.Union[str, typing.Pattern],
        *,
        timeout: float = None
    ) -> NoneType:
        """LocatorAssertions.not_to_have_css

        The opposite of `locator_assertions.to_have_css()`.

        Parameters
        ----------
        name : str
            CSS property name.
        value : Union[Pattern, str]
            CSS property value.
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.not_to_have_css(name=name, value=value, timeout=timeout)
            )
        )

    def to_have_id(
        self, id: typing.Union[str, typing.Pattern], *, timeout: float = None
    ) -> NoneType:
        """LocatorAssertions.to_have_id

        Ensures the `Locator` points to an element with the given DOM Node ID.

        ```py
        from playwright.sync_api import expect

        locator = page.locator(\"input\")
        expect(locator).to_have_id(\"lastname\")
        ```

        Parameters
        ----------
        id : Union[Pattern, str]
            Element id.
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.to_have_id(id=id, timeout=timeout))
        )

    def not_to_have_id(
        self, id: typing.Union[str, typing.Pattern], *, timeout: float = None
    ) -> NoneType:
        """LocatorAssertions.not_to_have_id

        The opposite of `locator_assertions.to_have_id()`.

        Parameters
        ----------
        id : Union[Pattern, str]
            Element id.
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.not_to_have_id(id=id, timeout=timeout))
        )

    def to_have_js_property(
        self, name: str, value: typing.Any, *, timeout: float = None
    ) -> NoneType:
        """LocatorAssertions.to_have_js_property

        Ensures the `Locator` points to an element with given JavaScript property. Note that this property can be of a primitive
        type as well as a plain serializable JavaScript object.

        ```py
        from playwright.sync_api import expect

        locator = page.locator(\".component\")
        expect(locator).to_have_js_property(\"loaded\", True)
        ```

        Parameters
        ----------
        name : str
            Property name.
        value : Any
            Property value.
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.to_have_js_property(
                    name=name, value=mapping.to_impl(value), timeout=timeout
                )
            )
        )

    def not_to_have_js_property(
        self, name: str, value: typing.Any, *, timeout: float = None
    ) -> NoneType:
        """LocatorAssertions.not_to_have_js_property

        The opposite of `locator_assertions.to_have_js_property()`.

        Parameters
        ----------
        name : str
            Property name.
        value : Any
            Property value.
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.not_to_have_js_property(
                    name=name, value=mapping.to_impl(value), timeout=timeout
                )
            )
        )

    def to_have_value(
        self, value: typing.Union[str, typing.Pattern], *, timeout: float = None
    ) -> NoneType:
        """LocatorAssertions.to_have_value

        Ensures the `Locator` points to an element with the given input value. You can use regular expressions for the value as
        well.

        ```py
        import re
        from playwright.sync_api import expect

        locator = page.locator(\"input[type=number]\")
        expect(locator).to_have_value(re.compile(r\"[0-9]\"))
        ```

        Parameters
        ----------
        value : Union[Pattern, str]
            Expected value.
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.to_have_value(value=value, timeout=timeout))
        )

    def not_to_have_value(
        self, value: typing.Union[str, typing.Pattern], *, timeout: float = None
    ) -> NoneType:
        """LocatorAssertions.not_to_have_value

        The opposite of `locator_assertions.to_have_value()`.

        Parameters
        ----------
        value : Union[Pattern, str]
            Expected value.
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.not_to_have_value(value=value, timeout=timeout))
        )

    def to_have_values(
        self,
        values: typing.List[typing.Union[typing.Pattern, str]],
        *,
        timeout: float = None
    ) -> NoneType:
        """LocatorAssertions.to_have_values

        Ensures the `Locator` points to multi-select/combobox (i.e. a `select` with the `multiple` attribute) and the specified
        values are selected.

        For example, given the following element:

        ```html
        <select id=\"favorite-colors\" multiple>
          <option value=\"R\">Red</option>
          <option value=\"G\">Green</option>
          <option value=\"B\">Blue</option>
        </select>
        ```

        ```py
        import re
        from playwright.sync_api import expect

        locator = page.locator(\"id=favorite-colors\")
        locator.select_option([\"R\", \"G\"])
        expect(locator).to_have_values([re.compile(r\"R\"), re.compile(r\"G\")])
        ```

        Parameters
        ----------
        values : List[Union[Pattern, str]]
            Expected options currently selected.
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.to_have_values(
                    values=mapping.to_impl(values), timeout=timeout
                )
            )
        )

    def not_to_have_values(
        self,
        values: typing.List[typing.Union[typing.Pattern, str]],
        *,
        timeout: float = None
    ) -> NoneType:
        """LocatorAssertions.not_to_have_values

        The opposite of `locator_assertions.to_have_values()`.

        Parameters
        ----------
        values : List[Union[Pattern, str]]
            Expected options currently selected.
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.not_to_have_values(
                    values=mapping.to_impl(values), timeout=timeout
                )
            )
        )

    def to_have_text(
        self,
        expected: typing.Union[
            typing.List[typing.Union[typing.Pattern, str]], typing.Pattern, str
        ],
        *,
        use_inner_text: bool = None,
        timeout: float = None,
        ignore_case: bool = None
    ) -> NoneType:
        """LocatorAssertions.to_have_text

        Ensures the `Locator` points to an element with the given text. You can use regular expressions for the value as well.

        ```py
        import re
        from playwright.sync_api import expect

        locator = page.locator(\".title\")
        expect(locator).to_have_text(re.compile(r\"Welcome, Test User\"))
        expect(locator).to_have_text(re.compile(r\"Welcome, .*\"))
        ```

        Note that if array is passed as an expected value, entire lists of elements can be asserted:

        ```py
        from playwright.sync_api import expect

        locator = page.locator(\"list > .component\")
        expect(locator).to_have_text([\"Text 1\", \"Text 2\", \"Text 3\"])
        ```

        Parameters
        ----------
        expected : Union[List[Union[Pattern, str]], Pattern, str]
            Expected substring or RegExp or a list of those.
        use_inner_text : Union[bool, NoneType]
            Whether to use `element.innerText` instead of `element.textContent` when retrieving DOM node text.
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        ignore_case : Union[bool, NoneType]
            Whether to perform case-insensitive match. `ignoreCase` option takes precedence over the corresponding regular
            expression flag if specified.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.to_have_text(
                    expected=mapping.to_impl(expected),
                    use_inner_text=use_inner_text,
                    timeout=timeout,
                    ignore_case=ignore_case,
                )
            )
        )

    def not_to_have_text(
        self,
        expected: typing.Union[
            typing.List[typing.Union[typing.Pattern, str]], typing.Pattern, str
        ],
        *,
        use_inner_text: bool = None,
        timeout: float = None,
        ignore_case: bool = None
    ) -> NoneType:
        """LocatorAssertions.not_to_have_text

        The opposite of `locator_assertions.to_have_text()`.

        Parameters
        ----------
        expected : Union[List[Union[Pattern, str]], Pattern, str]
            Expected substring or RegExp or a list of those.
        use_inner_text : Union[bool, NoneType]
            Whether to use `element.innerText` instead of `element.textContent` when retrieving DOM node text.
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        ignore_case : Union[bool, NoneType]
            Whether to perform case-insensitive match. `ignoreCase` option takes precedence over the corresponding regular
            expression flag if specified.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.not_to_have_text(
                    expected=mapping.to_impl(expected),
                    use_inner_text=use_inner_text,
                    timeout=timeout,
                    ignore_case=ignore_case,
                )
            )
        )

    def to_be_checked(self, *, timeout: float = None, checked: bool = None) -> NoneType:
        """LocatorAssertions.to_be_checked

        Ensures the `Locator` points to a checked input.

        ```py
        from playwright.sync_api import expect

        locator = page.locator(\".subscribe\")
        expect(locator).to_be_checked()
        ```

        Parameters
        ----------
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        checked : Union[bool, NoneType]
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.to_be_checked(timeout=timeout, checked=checked))
        )

    def not_to_be_checked(self, *, timeout: float = None) -> NoneType:
        """LocatorAssertions.not_to_be_checked

        The opposite of `locator_assertions.to_be_checked()`.

        Parameters
        ----------
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.not_to_be_checked(timeout=timeout))
        )

    def to_be_disabled(self, *, timeout: float = None) -> NoneType:
        """LocatorAssertions.to_be_disabled

        Ensures the `Locator` points to a disabled element. Element is disabled if it has \"disabled\" attribute or is disabled
        via ['aria-disabled'](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Attributes/aria-disabled). Note
        that only native control elements such as HTML `button`, `input`, `select`, `textarea`, `option`, `optgroup` can be
        disabled by setting \"disabled\" attribute. \"disabled\" attribute on other elements is ignored by the browser.

        ```py
        from playwright.sync_api import expect

        locator = page.locator(\"button.submit\")
        expect(locator).to_be_disabled()
        ```

        Parameters
        ----------
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.to_be_disabled(timeout=timeout))
        )

    def not_to_be_disabled(self, *, timeout: float = None) -> NoneType:
        """LocatorAssertions.not_to_be_disabled

        The opposite of `locator_assertions.to_be_disabled()`.

        Parameters
        ----------
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.not_to_be_disabled(timeout=timeout))
        )

    def to_be_editable(self, *, timeout: float = None) -> NoneType:
        """LocatorAssertions.to_be_editable

        Ensures the `Locator` points to an editable element.

        ```py
        from playwright.sync_api import expect

        locator = page.locator(\".input\")
        expect(locator).to_be_editable()
        ```

        Parameters
        ----------
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.to_be_editable(timeout=timeout))
        )

    def not_to_be_editable(self, *, timeout: float = None) -> NoneType:
        """LocatorAssertions.not_to_be_editable

        The opposite of `locator_assertions.to_be_editable()`.

        Parameters
        ----------
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.not_to_be_editable(timeout=timeout))
        )

    def to_be_empty(self, *, timeout: float = None) -> NoneType:
        """LocatorAssertions.to_be_empty

        Ensures the `Locator` points to an empty editable element or to a DOM node that has no text.

        ```py
        from playwright.sync_api import expect

        locator = page.locator(\"div.warning\")
        expect(locator).to_be_empty()
        ```

        Parameters
        ----------
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.to_be_empty(timeout=timeout))
        )

    def not_to_be_empty(self, *, timeout: float = None) -> NoneType:
        """LocatorAssertions.not_to_be_empty

        The opposite of `locator_assertions.to_be_empty()`.

        Parameters
        ----------
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.not_to_be_empty(timeout=timeout))
        )

    def to_be_enabled(self, *, timeout: float = None) -> NoneType:
        """LocatorAssertions.to_be_enabled

        Ensures the `Locator` points to an enabled element.

        ```py
        from playwright.sync_api import expect

        locator = page.locator(\"button.submit\")
        expect(locator).to_be_enabled()
        ```

        Parameters
        ----------
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.to_be_enabled(timeout=timeout))
        )

    def not_to_be_enabled(self, *, timeout: float = None) -> NoneType:
        """LocatorAssertions.not_to_be_enabled

        The opposite of `locator_assertions.to_be_enabled()`.

        Parameters
        ----------
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.not_to_be_enabled(timeout=timeout))
        )

    def to_be_hidden(self, *, timeout: float = None) -> NoneType:
        """LocatorAssertions.to_be_hidden

        Ensures the `Locator` points to a hidden DOM node, which is the opposite of [visible](https://playwright.dev/python/docs/api/actionability#visible).

        ```py
        from playwright.sync_api import expect

        locator = page.locator('.my-element')
        expect(locator).to_be_hidden()
        ```

        Parameters
        ----------
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.to_be_hidden(timeout=timeout))
        )

    def not_to_be_hidden(self, *, timeout: float = None) -> NoneType:
        """LocatorAssertions.not_to_be_hidden

        The opposite of `locator_assertions.to_be_hidden()`.

        Parameters
        ----------
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.not_to_be_hidden(timeout=timeout))
        )

    def to_be_visible(self, *, timeout: float = None) -> NoneType:
        """LocatorAssertions.to_be_visible

        Ensures the `Locator` points to a [visible](https://playwright.dev/python/docs/api/actionability#visible) DOM node.

        ```py
        from playwright.sync_api import expect

        locator = page.locator('.my-element')
        expect(locator).to_be_visible()
        ```

        Parameters
        ----------
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.to_be_visible(timeout=timeout))
        )

    def not_to_be_visible(self, *, timeout: float = None) -> NoneType:
        """LocatorAssertions.not_to_be_visible

        The opposite of `locator_assertions.to_be_visible()`.

        Parameters
        ----------
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.not_to_be_visible(timeout=timeout))
        )

    def to_be_focused(self, *, timeout: float = None) -> NoneType:
        """LocatorAssertions.to_be_focused

        Ensures the `Locator` points to a focused DOM node.

        ```py
        from playwright.sync_api import expect

        locator = page.locator('input')
        expect(locator).to_be_focused()
        ```

        Parameters
        ----------
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.to_be_focused(timeout=timeout))
        )

    def not_to_be_focused(self, *, timeout: float = None) -> NoneType:
        """LocatorAssertions.not_to_be_focused

        The opposite of `locator_assertions.to_be_focused()`.

        Parameters
        ----------
        timeout : Union[float, NoneType]
            Time to retry the assertion for.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.not_to_be_focused(timeout=timeout))
        )


mapping.register(LocatorAssertionsImpl, LocatorAssertions)


class APIResponseAssertions(SyncBase):
    def to_be_ok(self) -> NoneType:
        """APIResponseAssertions.to_be_ok

        Ensures the response status code is within [200..299] range.

        ```py
        import re
        from playwright.sync_api import expect

        # ...
        expect(response).to_be_ok()
        ```
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(self._sync(self._impl_obj.to_be_ok()))

    def not_to_be_ok(self) -> NoneType:
        """APIResponseAssertions.not_to_be_ok

        The opposite of `a_pi_response_assertions.to_be_ok()`.
        """
        __tracebackhide__ = True

        return mapping.from_maybe_impl(self._sync(self._impl_obj.not_to_be_ok()))


mapping.register(APIResponseAssertionsImpl, APIResponseAssertions)
