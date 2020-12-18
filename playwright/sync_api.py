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

from playwright._accessibility import Accessibility as AccessibilityImpl
from playwright._api_structures import Cookie, ResourceTiming, StorageState
from playwright._api_types import (
    DeviceDescriptor,
    FilePayload,
    FloatRect,
    Geolocation,
    PdfMargins,
    ProxySettings,
    SourceLocation,
)
from playwright._browser import Browser as BrowserImpl
from playwright._browser_context import BrowserContext as BrowserContextImpl
from playwright._browser_type import BrowserType as BrowserTypeImpl
from playwright._cdp_session import CDPSession as CDPSessionImpl
from playwright._chromium_browser_context import (
    ChromiumBrowserContext as ChromiumBrowserContextImpl,
)
from playwright._console_message import ConsoleMessage as ConsoleMessageImpl
from playwright._dialog import Dialog as DialogImpl
from playwright._download import Download as DownloadImpl
from playwright._element_handle import ElementHandle as ElementHandleImpl
from playwright._file_chooser import FileChooser as FileChooserImpl
from playwright._frame import Frame as FrameImpl
from playwright._input import Keyboard as KeyboardImpl
from playwright._input import Mouse as MouseImpl
from playwright._input import Touchscreen as TouchscreenImpl
from playwright._js_handle import JSHandle as JSHandleImpl
from playwright._network import Request as RequestImpl
from playwright._network import Response as ResponseImpl
from playwright._network import Route as RouteImpl
from playwright._network import WebSocket as WebSocketImpl
from playwright._page import BindingCall as BindingCallImpl
from playwright._page import Page as PageImpl
from playwright._page import Worker as WorkerImpl
from playwright._playwright import Playwright as PlaywrightImpl
from playwright._selectors import Selectors as SelectorsImpl
from playwright._sync_base import EventContextManager, SyncBase, mapping
from playwright._video import Video as VideoImpl

NoneType = type(None)


class Request(SyncBase):
    def __init__(self, obj: RequestImpl):
        super().__init__(obj)

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
        return mapping.from_maybe_impl(self._impl_obj.resourceType)

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
    def post_data(self) -> typing.Union[str, NoneType]:
        """Request.post_data

        Request's post body, if any.

        Returns
        -------
        Optional[str]
        """
        return mapping.from_maybe_impl(self._impl_obj.postData)

    @property
    def post_data_json(self) -> typing.Union[typing.Dict, NoneType]:
        """Request.post_data_json

        Returns parsed request's body for `form-urlencoded` and JSON as a fallback if any.
        When the response is `application/x-www-form-urlencoded` then a key/value object of the values will be returned.
        Otherwise it will be parsed as JSON.

        Returns
        -------
        Optional[Dict]
        """
        return mapping.from_maybe_impl(self._impl_obj.postDataJSON)

    @property
    def post_data_buffer(self) -> typing.Union[bytes, NoneType]:
        """Request.post_data_buffer

        Request's post body in a binary form, if any.

        Returns
        -------
        Optional[bytes]
        """
        return mapping.from_maybe_impl(self._impl_obj.postDataBuffer)

    @property
    def headers(self) -> typing.Dict[str, str]:
        """Request.headers

        An object with HTTP headers associated with the request. All header names are lower-case.

        Returns
        -------
        Dict[str, str]
        """
        return mapping.from_maybe_impl(self._impl_obj.headers)

    @property
    def frame(self) -> "Frame":
        """Request.frame

        Returns the Frame that initiated this request.

        Returns
        -------
        Frame
        """
        return mapping.from_impl(self._impl_obj.frame)

    @property
    def is_navigation_request(self) -> bool:
        """Request.is_navigation_request

        Whether this request is driving frame's navigation.

        Returns
        -------
        bool
        """
        return mapping.from_maybe_impl(self._impl_obj.isNavigationRequest)

    @property
    def redirected_from(self) -> typing.Union["Request", NoneType]:
        """Request.redirected_from

        Request that was redirected by the server to this one, if any.
        When the server responds with a redirect, Playwright creates a new Request object. The two requests are connected by
        `redirectedFrom()` and `redirectedTo()` methods. When multiple server redirects has happened, it is possible to
        construct the whole redirect chain by repeatedly calling `redirectedFrom()`.
        For example, if the website `http://example.com` redirects to `https://example.com`:
        If the website `https://google.com` has no redirects:

        Returns
        -------
        Optional[Request]
        """
        return mapping.from_impl_nullable(self._impl_obj.redirectedFrom)

    @property
    def redirected_to(self) -> typing.Union["Request", NoneType]:
        """Request.redirected_to

        New request issued by the browser if the server responded with redirect.
        This method is the opposite of request.redirected_from():

        Returns
        -------
        Optional[Request]
        """
        return mapping.from_impl_nullable(self._impl_obj.redirectedTo)

    @property
    def failure(self) -> typing.Union[str, NoneType]:
        """Request.failure

        The method returns `null` unless this request has failed, as reported by `requestfailed` event.
        Example of logging of all the failed requests:

        Returns
        -------
        Optional[str]
        """
        return mapping.from_maybe_impl(self._impl_obj.failure)

    @property
    def timing(self) -> "ResourceTiming":
        """Request.timing

        Returns resource timing information for given request. Most of the timing values become available upon the response,
        `responseEnd` becomes available when request finishes. Find more information at Resource Timing
        API.

        Returns
        -------
        {"startTime": float, "domainLookupStart": float, "domainLookupEnd": float, "connectStart": float, "secureConnectionStart": float, "connectEnd": float, "requestStart": float, "responseStart": float, "responseEnd": float}
        """
        return mapping.from_impl(self._impl_obj.timing)

    def response(self) -> typing.Union["Response", NoneType]:
        """Request.response

        Returns the matching Response object, or `null` if the response was not received due to error.

        Returns
        -------
        Optional[Response]
        """
        return mapping.from_impl_nullable(self._sync(self._impl_obj.response()))


mapping.register(RequestImpl, Request)


class Response(SyncBase):
    def __init__(self, obj: ResponseImpl):
        super().__init__(obj)

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

        Contains the status text of the response (e.g. usually an "OK" for a success).

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.statusText)

    @property
    def headers(self) -> typing.Dict[str, str]:
        """Response.headers

        Returns the object with HTTP headers associated with the response. All header names are lower-case.

        Returns
        -------
        Dict[str, str]
        """
        return mapping.from_maybe_impl(self._impl_obj.headers)

    @property
    def request(self) -> "Request":
        """Response.request

        Returns the matching Request object.

        Returns
        -------
        Request
        """
        return mapping.from_impl(self._impl_obj.request)

    @property
    def frame(self) -> "Frame":
        """Response.frame

        Returns the Frame that initiated this response.

        Returns
        -------
        Frame
        """
        return mapping.from_impl(self._impl_obj.frame)

    def finished(self) -> typing.Union[str, NoneType]:
        """Response.finished

        Waits for this response to finish, returns failure error if request failed.

        Returns
        -------
        Optional[str]
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

    def json(self) -> typing.Union[typing.Dict, typing.List]:
        """Response.json

        Returns the JSON representation of response body.
        This method will throw if the response body is not parsable via `JSON.parse`.

        Returns
        -------
        Union[Dict, List]
        """
        return mapping.from_maybe_impl(self._sync(self._impl_obj.json()))


mapping.register(ResponseImpl, Response)


class Route(SyncBase):
    def __init__(self, obj: RouteImpl):
        super().__init__(obj)

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
        error_code : Optional[str]
            Optional error code. Defaults to `failed`, could be one of the following:
             - `'aborted'` - An operation was aborted (due to user action)
             - `'accessdenied'` - Permission to access a resource, other than the network, was denied
             - `'addressunreachable'` - The IP address is unreachable. This usually means that there is no route to the specified host or network.
             - `'blockedbyclient'` - The client chose to block the request.
             - `'blockedbyresponse'` - The request failed because the response was delivered along with requirements which are not met ('X-Frame-Options' and 'Content-Security-Policy' ancestor checks, for instance).
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
        status: int = None,
        headers: typing.Union[typing.Dict[str, str]] = None,
        body: typing.Union[str, bytes] = None,
        path: typing.Union[str, pathlib.Path] = None,
        content_type: str = None,
    ) -> NoneType:
        """Route.fulfill

        Fulfills route's request with given response.
        An example of fulfilling all requests with 404 responses:
        An example of serving static file:

        Parameters
        ----------
        status : Optional[int]
            Response status code, defaults to `200`.
        headers : Optional[Dict[str, str]]
            Optional response headers. Header values will be converted to a string.
        body : Union[str, bytes, NoneType]
            Optional response body.
        path : Union[str, pathlib.Path, NoneType]
            Optional file path to respond with. The content type will be inferred from file extension. If `path` is a relative path, then it is resolved relative to current working directory.
        content_type : Optional[str]
            If set, equals to setting `Content-Type` response header.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.fulfill(
                    status=status,
                    headers=mapping.to_impl(headers),
                    body=body,
                    path=path,
                    contentType=content_type,
                )
            )
        )

    def continue_(
        self,
        url: str = None,
        method: str = None,
        headers: typing.Union[typing.Dict[str, str]] = None,
        post_data: typing.Union[str, bytes] = None,
    ) -> NoneType:
        """Route.continue_

        Continues route's request with optional overrides.

        Parameters
        ----------
        url : Optional[str]
            If set changes the request URL. New URL must have same protocol as original one.
        method : Optional[str]
            If set changes the request method (e.g. GET or POST)
        headers : Optional[Dict[str, str]]
            If set changes the request HTTP headers. Header values will be converted to a string.
        post_data : Union[str, bytes, NoneType]
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
    def __init__(self, obj: WebSocketImpl):
        super().__init__(obj)

    @property
    def url(self) -> str:
        """WebSocket.url

        Contains the URL of the WebSocket.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.url)

    def wait_for_event(
        self,
        event: str,
        predicate: typing.Union[typing.Callable[[typing.Any], bool]] = None,
        timeout: int = None,
    ) -> typing.Any:
        """WebSocket.wait_for_event

        Returns the event data value.
        Waits for event to fire and passes its value into the predicate function. Resolves when the predicate returns truthy
        value. Will throw an error if the webSocket is closed before the event is fired.

        Parameters
        ----------
        event : str
            Event name, same one would pass into `webSocket.on(event)`.

        Returns
        -------
        Any
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.waitForEvent(
                    event=event,
                    predicate=self._wrap_handler(predicate),
                    timeout=timeout,
                )
            )
        )

    def expect_event(
        self,
        event: str,
        predicate: typing.Union[typing.Callable[[typing.Any], bool]] = None,
        timeout: int = None,
    ) -> EventContextManager:
        """WebSocket.expect_event

        Returns context manager that waits for ``event`` to fire upon exit. It passes event's value
        into the ``predicate`` function and waits for the predicate to return a truthy value. Will throw
        an error if the page is closed before the ``event`` is fired.

        with page.expect_event() as event_info:
            page.click("button")
        value = event_info.value

        Parameters
        ----------
        predicate : Optional[typing.Callable[[Any], bool]]
            Predicate receiving event data.
        timeout : Optional[int]
            Maximum wait time in milliseconds, defaults to 30 seconds, pass `0` to disable the timeout.
            The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or
            page.setDefaultTimeout(timeout) methods.
        """
        return EventContextManager(
            self, self._impl_obj.waitForEvent(event, predicate, timeout)
        )

    def is_closed(self) -> bool:
        """WebSocket.is_closed

        Indicates that the web socket has been closed.

        Returns
        -------
        bool
        """
        return mapping.from_maybe_impl(self._impl_obj.isClosed())


mapping.register(WebSocketImpl, WebSocket)


class Keyboard(SyncBase):
    def __init__(self, obj: KeyboardImpl):
        super().__init__(obj)

    def down(self, key: str) -> NoneType:
        """Keyboard.down

        Dispatches a `keydown` event.
        `key` can specify the intended keyboardEvent.key
        value or a single character to generate the text for. A superset of the `key` values can be found
        here. Examples of the keys are:
        `F1` - `F12`, `Digit0`- `Digit9`, `KeyA`- `KeyZ`, `Backquote`, `Minus`, `Equal`, `Backslash`, `Backspace`, `Tab`,
        `Delete`, `Escape`, `ArrowDown`, `End`, `Enter`, `Home`, `Insert`, `PageDown`, `PageUp`, `ArrowRight`, `ArrowUp`, etc.
        Following modification shortcuts are also suported: `Shift`, `Control`, `Alt`, `Meta`, `ShiftLeft`.
        Holding down `Shift` will type the text that corresponds to the `key` in the upper case.
        If `key` is a single character, it is case-sensitive, so the values `a` and `A` will generate different respective
        texts.
        If `key` is a modifier key, `Shift`, `Meta`, `Control`, or `Alt`, subsequent key presses will be sent with that modifier
        active. To release the modifier key, use keyboard.up(key).
        After the key is pressed once, subsequent calls to keyboard.down(key) will have
        repeat set to true. To release the key, use
        keyboard.up(key).

        **NOTE** Modifier keys DO influence `keyboard.down`. Holding down `Shift` will type the text in upper case.

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

        **NOTE** Modifier keys DO NOT effect `keyboard.insert_text`. Holding down `Shift` will not type the text in upper case.

        Parameters
        ----------
        text : str
            Sets input to the specified text value.
        """
        return mapping.from_maybe_impl(self._sync(self._impl_obj.insertText(text=text)))

    def type(self, text: str, delay: int = None) -> NoneType:
        """Keyboard.type

        Sends a `keydown`, `keypress`/`input`, and `keyup` event for each character in the text.
        To press a special key, like `Control` or `ArrowDown`, use keyboard.press(key[, options]).

        **NOTE** Modifier keys DO NOT effect `keyboard.type`. Holding down `Shift` will not type the text in upper case.

        Parameters
        ----------
        text : str
            A text to type into a focused element.
        delay : Optional[int]
            Time to wait between key presses in milliseconds. Defaults to 0.
        """
        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.type(text=text, delay=delay))
        )

    def press(self, key: str, delay: int = None) -> NoneType:
        """Keyboard.press

        `key` can specify the intended keyboardEvent.key
        value or a single character to generate the text for. A superset of the `key` values can be found
        here. Examples of the keys are:
        `F1` - `F12`, `Digit0`- `Digit9`, `KeyA`- `KeyZ`, `Backquote`, `Minus`, `Equal`, `Backslash`, `Backspace`, `Tab`,
        `Delete`, `Escape`, `ArrowDown`, `End`, `Enter`, `Home`, `Insert`, `PageDown`, `PageUp`, `ArrowRight`, `ArrowUp`, etc.
        Following modification shortcuts are also suported: `Shift`, `Control`, `Alt`, `Meta`, `ShiftLeft`.
        Holding down `Shift` will type the text that corresponds to the `key` in the upper case.
        If `key` is a single character, it is case-sensitive, so the values `a` and `A` will generate different respective
        texts.
        Shortcuts such as `key: "Control+o"` or `key: "Control+Shift+T"` are supported as well. When speficied with the
        modifier, modifier is pressed and being held while the subsequent key is being pressed.
        Shortcut for keyboard.down(key) and keyboard.up(key).

        Parameters
        ----------
        key : str
            Name of the key to press or a character to generate, such as `ArrowLeft` or `a`.
        delay : Optional[int]
            Time to wait between `keydown` and `keyup` in milliseconds. Defaults to 0.
        """
        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.press(key=key, delay=delay))
        )


mapping.register(KeyboardImpl, Keyboard)


class Mouse(SyncBase):
    def __init__(self, obj: MouseImpl):
        super().__init__(obj)

    def move(self, x: float, y: float, steps: int = None) -> NoneType:
        """Mouse.move

        Dispatches a `mousemove` event.

        Parameters
        ----------
        x : float
        y : float
        steps : Optional[int]
            defaults to 1. Sends intermediate `mousemove` events.
        """
        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.move(x=x, y=y, steps=steps))
        )

    def down(
        self, button: Literal["left", "middle", "right"] = None, click_count: int = None
    ) -> NoneType:
        """Mouse.down

        Dispatches a `mousedown` event.

        Parameters
        ----------
        button : Optional[Literal['left', 'middle', 'right']]
            Defaults to `left`.
        click_count : Optional[int]
            defaults to 1. See UIEvent.detail.
        """
        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.down(button=button, clickCount=click_count))
        )

    def up(
        self, button: Literal["left", "middle", "right"] = None, click_count: int = None
    ) -> NoneType:
        """Mouse.up

        Dispatches a `mouseup` event.

        Parameters
        ----------
        button : Optional[Literal['left', 'middle', 'right']]
            Defaults to `left`.
        click_count : Optional[int]
            defaults to 1. See UIEvent.detail.
        """
        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.up(button=button, clickCount=click_count))
        )

    def click(
        self,
        x: float,
        y: float,
        delay: int = None,
        button: Literal["left", "middle", "right"] = None,
        click_count: int = None,
    ) -> NoneType:
        """Mouse.click

        Shortcut for mouse.move(x, y[, options]), mouse.down([options]), mouse.up([options]).

        Parameters
        ----------
        x : float
        y : float
        delay : Optional[int]
            Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        button : Optional[Literal['left', 'middle', 'right']]
            Defaults to `left`.
        click_count : Optional[int]
            defaults to 1. See UIEvent.detail.
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
        delay: int = None,
        button: Literal["left", "middle", "right"] = None,
    ) -> NoneType:
        """Mouse.dblclick

        Shortcut for mouse.move(x, y[, options]), mouse.down([options]), mouse.up([options]), mouse.down([options]) and mouse.up([options]).

        Parameters
        ----------
        x : float
        y : float
        delay : Optional[int]
            Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        button : Optional[Literal['left', 'middle', 'right']]
            Defaults to `left`.
        """
        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.dblclick(x=x, y=y, delay=delay, button=button))
        )


mapping.register(MouseImpl, Mouse)


class Touchscreen(SyncBase):
    def __init__(self, obj: TouchscreenImpl):
        super().__init__(obj)

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
    def __init__(self, obj: JSHandleImpl):
        super().__init__(obj)

    def evaluate(
        self, expression: str, arg: typing.Any = None, force_expr: bool = None
    ) -> typing.Any:
        """JSHandle.evaluate

        Returns the return value of `pageFunction`
        This method passes this handle as the first argument to `pageFunction`.
        If `pageFunction` returns a Promise, then `handle.evaluate` would wait for the promise to resolve and return its
        value.
        Examples:

        Parameters
        ----------
        expression : str
            Function to be evaluated in browser context
        force_expr : bool
            Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        arg : Optional[Any]
            Optional argument to pass to `pageFunction`

        Returns
        -------
        Any
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.evaluate(
                    expression=expression,
                    arg=mapping.to_impl(arg),
                    force_expr=force_expr,
                )
            )
        )

    def evaluate_handle(
        self, expression: str, arg: typing.Any = None, force_expr: bool = None
    ) -> "JSHandle":
        """JSHandle.evaluate_handle

        Returns the return value of `pageFunction` as in-page object (JSHandle).
        This method passes this handle as the first argument to `pageFunction`.
        The only difference between `jsHandle.evaluate` and `jsHandle.evaluateHandle` is that `jsHandle.evaluateHandle` returns
        in-page object (JSHandle).
        If the function passed to the `jsHandle.evaluateHandle` returns a Promise, then `jsHandle.evaluateHandle` would wait
        for the promise to resolve and return its value.
        See page.evaluate_handle(pageFunction[, arg]) for more details.

        Parameters
        ----------
        expression : str
            Function to be evaluated
        force_expr : bool
            Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        arg : Optional[Any]
            Optional argument to pass to `pageFunction`

        Returns
        -------
        JSHandle
        """
        return mapping.from_impl(
            self._sync(
                self._impl_obj.evaluateHandle(
                    expression=expression,
                    arg=mapping.to_impl(arg),
                    force_expr=force_expr,
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
            self._sync(self._impl_obj.getProperty(propertyName=property_name))
        )

    def get_properties(self) -> typing.Dict[str, "JSHandle"]:
        """JSHandle.get_properties

        The method returns a map with **own property names** as keys and JSHandle instances for the property values.

        Returns
        -------
        Dict[str, JSHandle]
        """
        return mapping.from_impl_dict(self._sync(self._impl_obj.getProperties()))

    def as_element(self) -> typing.Union["ElementHandle", NoneType]:
        """JSHandle.as_element

        Returns either `null` or the object handle itself, if the object handle is an instance of ElementHandle.

        Returns
        -------
        Optional[ElementHandle]
        """
        return mapping.from_impl_nullable(self._impl_obj.asElement())

    def dispose(self) -> NoneType:
        """JSHandle.dispose

        The `jsHandle.dispose` method stops referencing the element handle.
        """
        return mapping.from_maybe_impl(self._sync(self._impl_obj.dispose()))

    def json_value(self) -> typing.Any:
        """JSHandle.json_value

        Returns a JSON representation of the object. If the object has a
        `toJSON`
        function, it **will not be called**.

        **NOTE** The method will return an empty JSON object if the referenced object is not stringifiable. It will throw an
        error if the object has circular references.

        Returns
        -------
        Any
        """
        return mapping.from_maybe_impl(self._sync(self._impl_obj.jsonValue()))


mapping.register(JSHandleImpl, JSHandle)


class ElementHandle(JSHandle):
    def __init__(self, obj: ElementHandleImpl):
        super().__init__(obj)

    def to_string(self) -> str:
        """ElementHandle.to_string

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.toString())

    def as_element(self) -> typing.Union["ElementHandle", NoneType]:
        """ElementHandle.as_element

        Returns either `null` or the object handle itself, if the object handle is an instance of ElementHandle.

        Returns
        -------
        Optional[ElementHandle]
        """
        return mapping.from_impl_nullable(self._impl_obj.asElement())

    def owner_frame(self) -> typing.Union["Frame", NoneType]:
        """ElementHandle.owner_frame

        Returns the frame containing the given element.

        Returns
        -------
        Optional[Frame]
        """
        return mapping.from_impl_nullable(self._sync(self._impl_obj.ownerFrame()))

    def content_frame(self) -> typing.Union["Frame", NoneType]:
        """ElementHandle.content_frame

        Returns the content frame for element handles referencing iframe nodes, or `null` otherwise

        Returns
        -------
        Optional[Frame]
        """
        return mapping.from_impl_nullable(self._sync(self._impl_obj.contentFrame()))

    def get_attribute(self, name: str) -> typing.Union[str, NoneType]:
        """ElementHandle.get_attribute

        Returns element attribute value.

        Parameters
        ----------
        name : str
            Attribute name to get the value for.

        Returns
        -------
        Optional[str]
        """
        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.getAttribute(name=name))
        )

    def text_content(self) -> typing.Union[str, NoneType]:
        """ElementHandle.text_content

        Returns the `node.textContent`.

        Returns
        -------
        Optional[str]
        """
        return mapping.from_maybe_impl(self._sync(self._impl_obj.textContent()))

    def inner_text(self) -> str:
        """ElementHandle.inner_text

        Returns the `element.innerText`.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._sync(self._impl_obj.innerText()))

    def inner_html(self) -> str:
        """ElementHandle.inner_html

        Returns the `element.innerHTML`.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._sync(self._impl_obj.innerHTML()))

    def dispatch_event(self, type: str, event_init: typing.Dict = None) -> NoneType:
        """ElementHandle.dispatch_event

        The snippet below dispatches the `click` event on the element. Regardless of the visibility state of the elment, `click`
        is dispatched. This is equivalend to calling
        element.click().
        Under the hood, it creates an instance of an event based on the given `type`, initializes it with `eventInit` properties
        and dispatches it on the element. Events are `composed`, `cancelable` and bubble by default.
        Since `eventInit` is event-specific, please refer to the events documentation for the lists of initial properties:

        DragEvent
        FocusEvent
        KeyboardEvent
        MouseEvent
        PointerEvent
        TouchEvent
        Event

        You can also specify `JSHandle` as the property value if you want live objects to be passed into the event:

        Parameters
        ----------
        type : str
            DOM event type: `"click"`, `"dragstart"`, etc.
        event_init : Optional[Dict]
            Optional event-specific initialization properties.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.dispatchEvent(
                    type=type, eventInit=mapping.to_impl(event_init)
                )
            )
        )

    def scroll_into_view_if_needed(self, timeout: int = None) -> NoneType:
        """ElementHandle.scroll_into_view_if_needed

        This method waits for actionability checks, then tries to scroll element into view, unless it is
        completely visible as defined by
        IntersectionObserver's `ratio`.
        Throws when `elementHandle` does not point to an element
        connected to a Document or a ShadowRoot.

        Parameters
        ----------
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        """
        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.scrollIntoViewIfNeeded(timeout=timeout))
        )

    def hover(
        self,
        modifiers: typing.Union[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: typing.Union[typing.Tuple[float, float]] = None,
        timeout: int = None,
        force: bool = None,
    ) -> NoneType:
        """ElementHandle.hover

        This method hovers over the element by performing the following steps:

        Wait for actionability checks on the element, unless `force` option is set.
        Scroll the element into view if needed.
        Use page.mouse to hover over the center of the element, or the specified `position`.
        Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.

        If the element is detached from the DOM at any moment during the action, this method rejects.
        When all steps combined have not finished during the specified `timeout`, this method rejects with a TimeoutError.
        Passing zero timeout disables this.

        Parameters
        ----------
        modifiers : Optional[List[Literal['Alt', 'Control', 'Meta', 'Shift']]]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores current modifiers back. If not specified, currently pressed modifiers are used.
        position : Optional[typing.Tuple[float, float]]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the element.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        force : Optional[bool]
            Whether to bypass the actionability checks. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.hover(
                    modifiers=modifiers, position=position, timeout=timeout, force=force
                )
            )
        )

    def click(
        self,
        modifiers: typing.Union[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: typing.Union[typing.Tuple[float, float]] = None,
        delay: int = None,
        button: Literal["left", "middle", "right"] = None,
        click_count: int = None,
        timeout: int = None,
        force: bool = None,
        no_wait_after: bool = None,
    ) -> NoneType:
        """ElementHandle.click

        This method clicks the element by performing the following steps:

        Wait for actionability checks on the element, unless `force` option is set.
        Scroll the element into view if needed.
        Use page.mouse to click in the center of the element, or the specified `position`.
        Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.

        If the element is detached from the DOM at any moment during the action, this method rejects.
        When all steps combined have not finished during the specified `timeout`, this method rejects with a TimeoutError.
        Passing zero timeout disables this.

        Parameters
        ----------
        modifiers : Optional[List[Literal['Alt', 'Control', 'Meta', 'Shift']]]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores current modifiers back. If not specified, currently pressed modifiers are used.
        position : Optional[typing.Tuple[float, float]]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the element.
        delay : Optional[int]
            Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        button : Optional[Literal['left', 'middle', 'right']]
            Defaults to `left`.
        click_count : Optional[int]
            defaults to 1. See UIEvent.detail.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        force : Optional[bool]
            Whether to bypass the actionability checks. Defaults to `false`.
        no_wait_after : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.click(
                    modifiers=modifiers,
                    position=position,
                    delay=delay,
                    button=button,
                    clickCount=click_count,
                    timeout=timeout,
                    force=force,
                    noWaitAfter=no_wait_after,
                )
            )
        )

    def dblclick(
        self,
        modifiers: typing.Union[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: typing.Union[typing.Tuple[float, float]] = None,
        delay: int = None,
        button: Literal["left", "middle", "right"] = None,
        timeout: int = None,
        force: bool = None,
        no_wait_after: bool = None,
    ) -> NoneType:
        """ElementHandle.dblclick

        This method double clicks the element by performing the following steps:

        Wait for actionability checks on the element, unless `force` option is set.
        Scroll the element into view if needed.
        Use page.mouse to double click in the center of the element, or the specified `position`.
        Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set. Note that if the first click of the `dblclick()` triggers a navigation event, this method will reject.

        If the element is detached from the DOM at any moment during the action, this method rejects.
        When all steps combined have not finished during the specified `timeout`, this method rejects with a TimeoutError.
        Passing zero timeout disables this.

        **NOTE** `element_handle.dblclick()` dispatches two `click` events and a single `dblclick` event.

        Parameters
        ----------
        modifiers : Optional[List[Literal['Alt', 'Control', 'Meta', 'Shift']]]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores current modifiers back. If not specified, currently pressed modifiers are used.
        position : Optional[typing.Tuple[float, float]]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the element.
        delay : Optional[int]
            Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        button : Optional[Literal['left', 'middle', 'right']]
            Defaults to `left`.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        force : Optional[bool]
            Whether to bypass the actionability checks. Defaults to `false`.
        no_wait_after : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.dblclick(
                    modifiers=modifiers,
                    position=position,
                    delay=delay,
                    button=button,
                    timeout=timeout,
                    force=force,
                    noWaitAfter=no_wait_after,
                )
            )
        )

    def select_option(
        self,
        value: typing.Union[str, typing.List[str]] = None,
        index: typing.Union[int, typing.List[int]] = None,
        label: typing.Union[str, typing.List[str]] = None,
        element: typing.Union["ElementHandle", typing.List["ElementHandle"]] = None,
        timeout: int = None,
        no_wait_after: bool = None,
    ) -> typing.List[str]:
        """ElementHandle.select_option

        Returns the array of option values that have been successfully selected.
        Triggers a `change` and `input` event once all the provided options have been selected. If element is not a `<select>`
        element, the method throws an error.

        Parameters
        ----------
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        no_wait_after : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.

        Returns
        -------
        List[str]
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.selectOption(
                    value=value,
                    index=index,
                    label=label,
                    element=mapping.to_impl(element),
                    timeout=timeout,
                    noWaitAfter=no_wait_after,
                )
            )
        )

    def tap(
        self,
        modifiers: typing.Union[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: typing.Union[typing.Tuple[float, float]] = None,
        timeout: int = None,
        force: bool = None,
        no_wait_after: bool = None,
    ) -> NoneType:
        """ElementHandle.tap

        This method taps the element by performing the following steps:

        Wait for actionability checks on the element, unless `force` option is set.
        Scroll the element into view if needed.
        Use page.touchscreen to tap in the center of the element, or the specified `position`.
        Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.

        If the element is detached from the DOM at any moment during the action, this method rejects.
        When all steps combined have not finished during the specified `timeout`, this method rejects with a TimeoutError.
        Passing zero timeout disables this.

        **NOTE** `element_handle.tap()` requires that the `hasTouch` option of the browser context be set to true.

        Parameters
        ----------
        modifiers : Optional[List[Literal['Alt', 'Control', 'Meta', 'Shift']]]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores current modifiers back. If not specified, currently pressed modifiers are used.
        position : Optional[typing.Tuple[float, float]]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the element.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        force : Optional[bool]
            Whether to bypass the actionability checks. Defaults to `false`.
        no_wait_after : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.tap(
                    modifiers=modifiers,
                    position=position,
                    timeout=timeout,
                    force=force,
                    noWaitAfter=no_wait_after,
                )
            )
        )

    def fill(
        self, value: str, timeout: int = None, no_wait_after: bool = None
    ) -> NoneType:
        """ElementHandle.fill

        This method waits for actionability checks, focuses the element, fills it and triggers an `input`
        event after filling. If the element is not an `<input>`, `<textarea>` or `[contenteditable]` element, this method throws
        an error. Note that you can pass an empty string to clear the input field.

        Parameters
        ----------
        value : str
            Value to set for the `<input>`, `<textarea>` or `[contenteditable]` element.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        no_wait_after : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.fill(
                    value=value, timeout=timeout, noWaitAfter=no_wait_after
                )
            )
        )

    def select_text(self, timeout: int = None) -> NoneType:
        """ElementHandle.select_text

        This method waits for actionability checks, then focuses the element and selects all its text
        content.

        Parameters
        ----------
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        """
        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.selectText(timeout=timeout))
        )

    def set_input_files(
        self,
        files: typing.Union[
            str,
            pathlib.Path,
            "FilePayload",
            typing.List[str],
            typing.List[pathlib.Path],
            typing.List["FilePayload"],
        ],
        timeout: int = None,
        no_wait_after: bool = None,
    ) -> NoneType:
        """ElementHandle.set_input_files

        This method expects `elementHandle` to point to an input
        element.
        Sets the value of the file input to these file paths or files. If some of the `filePaths` are relative paths, then they
        are resolved relative to the current working directory. For
        empty array, clears the selected files.

        Parameters
        ----------
        files : Union[str, pathlib.Path, Dict, List[str], List[pathlib.Path], List[Dict]]
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        no_wait_after : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.setInputFiles(
                    files=files, timeout=timeout, noWaitAfter=no_wait_after
                )
            )
        )

    def focus(self) -> NoneType:
        """ElementHandle.focus

        Calls focus on the element.
        """
        return mapping.from_maybe_impl(self._sync(self._impl_obj.focus()))

    def type(
        self,
        text: str,
        delay: int = None,
        timeout: int = None,
        no_wait_after: bool = None,
    ) -> NoneType:
        """ElementHandle.type

        Focuses the element, and then sends a `keydown`, `keypress`/`input`, and `keyup` event for each character in the text.
        To press a special key, like `Control` or `ArrowDown`, use element_handle.press(key[, options]).
        An example of typing into a text field and then submitting the form:

        Parameters
        ----------
        text : str
            A text to type into a focused element.
        delay : Optional[int]
            Time to wait between key presses in milliseconds. Defaults to 0.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        no_wait_after : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
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
        delay: int = None,
        timeout: int = None,
        no_wait_after: bool = None,
    ) -> NoneType:
        """ElementHandle.press

        Focuses the element, and then uses keyboard.down(key) and keyboard.up(key).
        `key` can specify the intended keyboardEvent.key
        value or a single character to generate the text for. A superset of the `key` values can be found
        here. Examples of the keys are:
        `F1` - `F12`, `Digit0`- `Digit9`, `KeyA`- `KeyZ`, `Backquote`, `Minus`, `Equal`, `Backslash`, `Backspace`, `Tab`,
        `Delete`, `Escape`, `ArrowDown`, `End`, `Enter`, `Home`, `Insert`, `PageDown`, `PageUp`, `ArrowRight`, `ArrowUp`, etc.
        Following modification shortcuts are also suported: `Shift`, `Control`, `Alt`, `Meta`, `ShiftLeft`.
        Holding down `Shift` will type the text that corresponds to the `key` in the upper case.
        If `key` is a single character, it is case-sensitive, so the values `a` and `A` will generate different respective
        texts.
        Shortcuts such as `key: "Control+o"` or `key: "Control+Shift+T"` are supported as well. When speficied with the
        modifier, modifier is pressed and being held while the subsequent key is being pressed.

        Parameters
        ----------
        key : str
            Name of the key to press or a character to generate, such as `ArrowLeft` or `a`.
        delay : Optional[int]
            Time to wait between `keydown` and `keyup` in milliseconds. Defaults to 0.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        no_wait_after : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.press(
                    key=key, delay=delay, timeout=timeout, noWaitAfter=no_wait_after
                )
            )
        )

    def check(
        self, timeout: int = None, force: bool = None, no_wait_after: bool = None
    ) -> NoneType:
        """ElementHandle.check

        This method checks the element by performing the following steps:

        Ensure that element is a checkbox or a radio input. If not, this method rejects. If the element is already checked, this method returns immediately.
        Wait for actionability checks on the element, unless `force` option is set.
        Scroll the element into view if needed.
        Use page.mouse to click in the center of the element.
        Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.
        Ensure that the element is now checked. If not, this method rejects.

        If the element is detached from the DOM at any moment during the action, this method rejects.
        When all steps combined have not finished during the specified `timeout`, this method rejects with a TimeoutError.
        Passing zero timeout disables this.

        Parameters
        ----------
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        force : Optional[bool]
            Whether to bypass the actionability checks. Defaults to `false`.
        no_wait_after : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.check(
                    timeout=timeout, force=force, noWaitAfter=no_wait_after
                )
            )
        )

    def uncheck(
        self, timeout: int = None, force: bool = None, no_wait_after: bool = None
    ) -> NoneType:
        """ElementHandle.uncheck

        This method checks the element by performing the following steps:

        Ensure that element is a checkbox or a radio input. If not, this method rejects. If the element is already unchecked, this method returns immediately.
        Wait for actionability checks on the element, unless `force` option is set.
        Scroll the element into view if needed.
        Use page.mouse to click in the center of the element.
        Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.
        Ensure that the element is now unchecked. If not, this method rejects.

        If the element is detached from the DOM at any moment during the action, this method rejects.
        When all steps combined have not finished during the specified `timeout`, this method rejects with a TimeoutError.
        Passing zero timeout disables this.

        Parameters
        ----------
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        force : Optional[bool]
            Whether to bypass the actionability checks. Defaults to `false`.
        no_wait_after : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.uncheck(
                    timeout=timeout, force=force, noWaitAfter=no_wait_after
                )
            )
        )

    def bounding_box(self) -> typing.Union["FloatRect", NoneType]:
        """ElementHandle.bounding_box

        This method returns the bounding box of the element, or `null` if the element is not visible. The bounding box is
        calculated relative to the main frame viewport - which is usually the same as the browser window.
        Scrolling affects the returned bonding box, similarly to
        Element.getBoundingClientRect. That
        means `x` and/or `y` may be negative.
        Elements from child frames return the bounding box relative to the main frame, unlike the
        Element.getBoundingClientRect.
        Assuming the page is static, it is safe to use bounding box coordinates to perform input. For example, the following
        snippet should click the center of the element.

        Returns
        -------
        Optional[{"x": float, "y": float, "width": float, "height": float}]
        """
        return mapping.from_impl_nullable(self._sync(self._impl_obj.boundingBox()))

    def screenshot(
        self,
        timeout: int = None,
        type: Literal["jpeg", "png"] = None,
        path: typing.Union[str, pathlib.Path] = None,
        quality: int = None,
        omit_background: bool = None,
    ) -> bytes:
        """ElementHandle.screenshot

        Returns the buffer with the captured screenshot.
        This method waits for the actionability checks, then scrolls element into view before taking a
        screenshot. If the element is detached from DOM, the method throws an error.

        Parameters
        ----------
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        type : Optional[Literal['jpeg', 'png']]
            Specify screenshot type, defaults to `png`.
        path : Union[str, pathlib.Path, NoneType]
            The file path to save the image to. The screenshot type will be inferred from file extension. If `path` is a relative path, then it is resolved relative to current working directory. If no path is provided, the image won't be saved to the disk.
        quality : Optional[int]
            The quality of the image, between 0-100. Not applicable to `png` images.
        omit_background : Optional[bool]
            Hides default white background and allows capturing screenshots with transparency. Not applicable to `jpeg` images. Defaults to `false`.

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
                )
            )
        )

    def query_selector(self, selector: str) -> typing.Union["ElementHandle", NoneType]:
        """ElementHandle.query_selector

        The method finds an element matching the specified selector in the `ElementHandle`'s subtree. See Working with
        selectors for more details. If no elements match the selector, the return value resolves to
        `null`.

        Parameters
        ----------
        selector : str
            A selector to query for. See working with selectors for more details.

        Returns
        -------
        Optional[ElementHandle]
        """
        return mapping.from_impl_nullable(
            self._sync(self._impl_obj.querySelector(selector=selector))
        )

    def query_selector_all(self, selector: str) -> typing.List["ElementHandle"]:
        """ElementHandle.query_selector_all

        The method finds all elements matching the specified selector in the `ElementHandle`s subtree. See Working with
        selectors for more details. If no elements match the selector, the return value resolves to
        `[]`.

        Parameters
        ----------
        selector : str
            A selector to query for. See working with selectors for more details.

        Returns
        -------
        List[ElementHandle]
        """
        return mapping.from_impl_list(
            self._sync(self._impl_obj.querySelectorAll(selector=selector))
        )

    def eval_on_selector(
        self,
        selector: str,
        expression: str,
        arg: typing.Any = None,
        force_expr: bool = None,
    ) -> typing.Any:
        """ElementHandle.eval_on_selector

        Returns the return value of `pageFunction`
        The method finds an element matching the specified selector in the `ElementHandle`s subtree and passes it as a first
        argument to `pageFunction`. See Working with selectors for more details. If no elements match
        the selector, the method throws an error.
        If `pageFunction` returns a Promise, then `frame.$eval` would wait for the promise to resolve and return its value.
        Examples:

        Parameters
        ----------
        selector : str
            A selector to query for. See working with selectors for more details.
        expression : str
            Function to be evaluated in browser context
        force_expr : bool
            Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        arg : Optional[Any]
            Optional argument to pass to `pageFunction`

        Returns
        -------
        Any
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.evalOnSelector(
                    selector=selector,
                    expression=expression,
                    arg=mapping.to_impl(arg),
                    force_expr=force_expr,
                )
            )
        )

    def eval_on_selector_all(
        self,
        selector: str,
        expression: str,
        arg: typing.Any = None,
        force_expr: bool = None,
    ) -> typing.Any:
        """ElementHandle.eval_on_selector_all

        Returns the return value of `pageFunction`
        The method finds all elements matching the specified selector in the `ElementHandle`'s subtree and passes an array of
        matched elements as a first argument to `pageFunction`. See Working with selectors for more
        details.
        If `pageFunction` returns a Promise, then `frame.$$eval` would wait for the promise to resolve and return its value.
        Examples:
        ```html
        <div class="feed">
          <div class="tweet">Hello!</div>
          <div class="tweet">Hi!</div>
        </div>
        ```

        Parameters
        ----------
        selector : str
            A selector to query for. See working with selectors for more details.
        expression : str
            Function to be evaluated in browser context
        force_expr : bool
            Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        arg : Optional[Any]
            Optional argument to pass to `pageFunction`

        Returns
        -------
        Any
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.evalOnSelectorAll(
                    selector=selector,
                    expression=expression,
                    arg=mapping.to_impl(arg),
                    force_expr=force_expr,
                )
            )
        )

    def wait_for_element_state(
        self,
        state: Literal["disabled", "enabled", "hidden", "stable", "visible"],
        timeout: int = None,
    ) -> NoneType:
        """ElementHandle.wait_for_element_state

        Returns the element satisfies the `state`.
        Depending on the `state` parameter, this method waits for one of the actionability checks to pass.
        This method throws when the element is detached while waiting, unless waiting for the `"hidden"` state.

        `"visible"` Wait until the element is visible.
        `"hidden"` Wait until the element is not visible or not attached. Note that waiting for hidden does not throw when the element detaches.
        `"stable"` Wait until the element is both visible and stable.
        `"enabled"` Wait until the element is enabled.
        `"disabled"` Wait until the element is not enabled.

        If the element does not satisfy the condition for the `timeout` milliseconds, this method will throw.

        Parameters
        ----------
        state : Literal['disabled', 'enabled', 'hidden', 'stable', 'visible']
            A state to wait for, see below for more details.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        """
        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.waitForElementState(state=state, timeout=timeout))
        )

    def wait_for_selector(
        self,
        selector: str,
        state: Literal["attached", "detached", "hidden", "visible"] = None,
        timeout: int = None,
    ) -> typing.Union["ElementHandle", NoneType]:
        """ElementHandle.wait_for_selector

        Returns element specified by selector satisfies `state` option. Resolves to `null` if waiting for `hidden` or
        `detached`.
        Wait for the `selector` relative to the element handle to satisfy `state` option (either appear/disappear from dom, or
        become visible/hidden). If at the moment of calling the method `selector` already satisfies the condition, the method
        will return immediately. If the selector doesn't satisfy the condition for the `timeout` milliseconds, the function will
        throw.

        **NOTE** This method does not work across navigations, use page.wait_for_selector(selector[, options]) instead.

        Parameters
        ----------
        selector : str
            A selector to query for. See working with selectors for more details.
        state : Optional[Literal['attached', 'detached', 'hidden', 'visible']]
            Defaults to `'visible'`. Can be either:
             - `'attached'` - wait for element to be present in DOM.
             - `'detached'` - wait for element to not be present in DOM.
             - `'visible'` - wait for element to have non-empty bounding box and no `visibility:hidden`. Note that element without any content or with `display:none` has an empty bounding box and is not considered visible.
             - `'hidden'` - wait for element to be either detached from DOM, or have an empty bounding box or `visibility:hidden`. This is opposite to the `'visible'` option.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.

        Returns
        -------
        Optional[ElementHandle]
        """
        return mapping.from_impl_nullable(
            self._sync(
                self._impl_obj.waitForSelector(
                    selector=selector, state=state, timeout=timeout
                )
            )
        )


mapping.register(ElementHandleImpl, ElementHandle)


class Accessibility(SyncBase):
    def __init__(self, obj: AccessibilityImpl):
        super().__init__(obj)

    def snapshot(
        self, interesting_only: bool = None, root: "ElementHandle" = None
    ) -> typing.Union[typing.Dict, NoneType]:
        """Accessibility.snapshot

        Captures the current state of the accessibility tree. The returned object represents the root accessible node of the
        page.

        **NOTE** The Chromium accessibility tree contains nodes that go unused on most platforms and by most screen readers.
        Playwright will discard them as well for an easier to process tree, unless `interestingOnly` is set to `false`.

        An example of dumping the entire accessibility tree:
        An example of logging the focused node's name:

        Parameters
        ----------
        interesting_only : Optional[bool]
            Prune uninteresting nodes from the tree. Defaults to `true`.
        root : Optional[ElementHandle]
            The root DOM element for the snapshot. Defaults to the whole page.

        Returns
        -------
        Optional[Dict]
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
    def __init__(self, obj: FileChooserImpl):
        super().__init__(obj)

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

    @property
    def is_multiple(self) -> bool:
        """FileChooser.is_multiple

        Returns whether this file chooser accepts multiple files.

        Returns
        -------
        bool
        """
        return mapping.from_maybe_impl(self._impl_obj.isMultiple)

    def set_files(
        self,
        files: typing.Union[
            str, "FilePayload", typing.List[str], typing.List["FilePayload"]
        ],
        timeout: int = None,
        no_wait_after: bool = None,
    ) -> NoneType:
        """FileChooser.set_files

        Sets the value of the file input this chooser is associated with. If some of the `filePaths` are relative paths, then
        they are resolved relative to the current working directory.
        For empty array, clears the selected files.

        Parameters
        ----------
        files : Union[str, Dict, List[str], List[Dict]]
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        no_wait_after : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.setFiles(
                    files=files, timeout=timeout, noWaitAfter=no_wait_after
                )
            )
        )


mapping.register(FileChooserImpl, FileChooser)


class Frame(SyncBase):
    def __init__(self, obj: FrameImpl):
        super().__init__(obj)

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

        **NOTE** This value is calculated once when the frame is created, and will not update if the attribute is changed
        later.

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
    def parent_frame(self) -> typing.Union["Frame", NoneType]:
        """Frame.parent_frame

        Parent frame, if any. Detached frames and main frames return `null`.

        Returns
        -------
        Optional[Frame]
        """
        return mapping.from_impl_nullable(self._impl_obj.parentFrame)

    @property
    def child_frames(self) -> typing.List["Frame"]:
        """Frame.child_frames

        Returns
        -------
        List[Frame]
        """
        return mapping.from_impl_list(self._impl_obj.childFrames)

    def goto(
        self,
        url: str,
        timeout: int = None,
        wait_until: Literal["domcontentloaded", "load", "networkidle"] = None,
        referer: str = None,
    ) -> typing.Union["Response", NoneType]:
        """Frame.goto

        Returns the main resource response. In case of multiple redirects, the navigation will resolve with the response of the
        last redirect.
        `frame.goto` will throw an error if:

        there's an SSL error (e.g. in case of self-signed certificates).
        target URL is invalid.
        the `timeout` is exceeded during navigation.
        the remote server does not respond or is unreachable.
        the main resource failed to load.

        `frame.goto` will not throw an error when any valid HTTP status code is returned by the remote server, including 404
        "Not Found" and 500 "Internal Server Error".  The status code for such responses can be retrieved by calling
        response.status().

        **NOTE** `frame.goto` either throws an error or returns a main resource response. The only exceptions are navigation
        to `about:blank` or navigation to the same URL with a different hash, which would succeed and return `null`.
        **NOTE** Headless mode doesn't support navigation to a PDF document. See the upstream
        issue.

        Parameters
        ----------
        url : str
            URL to navigate frame to. The url should include scheme, e.g. `https://`.
        timeout : Optional[int]
            Maximum operation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultNavigationTimeout(timeout), browserContext.setDefaultTimeout(timeout), page.setDefaultNavigationTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        wait_until : Optional[Literal['domcontentloaded', 'load', 'networkidle']]
            When to consider operation succeeded, defaults to `load`. Events can be either:
             - `'domcontentloaded'` - consider operation to be finished when the `DOMContentLoaded` event is fired.
             - `'load'` - consider operation to be finished when the `load` event is fired.
             - `'networkidle'` - consider operation to be finished when there are no network connections for at least `500` ms.
        referer : Optional[str]
            Referer header value. If provided it will take preference over the referer header value set by page.setExtraHTTPHeaders(headers).

        Returns
        -------
        Optional[Response]
        """
        return mapping.from_impl_nullable(
            self._sync(
                self._impl_obj.goto(
                    url=url, timeout=timeout, waitUntil=wait_until, referer=referer
                )
            )
        )

    def wait_for_navigation(
        self,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]] = None,
        wait_until: Literal["domcontentloaded", "load", "networkidle"] = None,
        timeout: int = None,
    ) -> typing.Union["Response", NoneType]:
        """Frame.wait_for_navigation

        Returns the main resource response. In case of multiple redirects, the navigation will resolve with the response of the
        last redirect. In case of navigation to a different anchor or navigation due to History API usage, the navigation will
        resolve with `null`.
        This resolves when the frame navigates to a new URL. It is useful for when you run code which will indirectly cause the
        frame to navigate. Consider this example:
        **NOTE** Usage of the History API to change the URL is
        considered a navigation.

        Parameters
        ----------
        url : Union[str, Pattern, Callable[[str], bool], NoneType]
            URL string, URL regex pattern or predicate receiving URL to match while waiting for the navigation.
        wait_until : Optional[Literal['domcontentloaded', 'load', 'networkidle']]
            When to consider operation succeeded, defaults to `load`. Events can be either:
             - `'domcontentloaded'` - consider operation to be finished when the `DOMContentLoaded` event is fired.
             - `'load'` - consider operation to be finished when the `load` event is fired.
             - `'networkidle'` - consider operation to be finished when there are no network connections for at least `500` ms.
        timeout : Optional[int]
            Maximum operation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultNavigationTimeout(timeout), browserContext.setDefaultTimeout(timeout), page.setDefaultNavigationTimeout(timeout) or page.setDefaultTimeout(timeout) methods.

        Returns
        -------
        Optional[Response]
        """
        return mapping.from_impl_nullable(
            self._sync(
                self._impl_obj.waitForNavigation(
                    url=self._wrap_handler(url), waitUntil=wait_until, timeout=timeout
                )
            )
        )

    def wait_for_load_state(
        self,
        state: Literal["domcontentloaded", "load", "networkidle"] = None,
        timeout: int = None,
    ) -> NoneType:
        """Frame.wait_for_load_state

        Returns when the required load state has been reached.
        This resolves when the frame reaches a required load state, `load` by default. The navigation must have been committed
        when this method is called. If current document has already reached the required state, resolves immediately.

        Parameters
        ----------
        state : Optional[Literal['domcontentloaded', 'load', 'networkidle']]
            Load state to wait for, defaults to `load`. If the state has been already reached while loading current document, the method resolves immediately. Optional.
             - `'load'` - wait for the `load` event to be fired.
             - `'domcontentloaded'` - wait for the `DOMContentLoaded` event to be fired.
             - `'networkidle'` - wait until there are no network connections for at least `500` ms.
        timeout : Optional[int]
            Maximum operation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultNavigationTimeout(timeout), browserContext.setDefaultTimeout(timeout), page.setDefaultNavigationTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        """
        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.waitForLoadState(state=state, timeout=timeout))
        )

    def frame_element(self) -> "ElementHandle":
        """Frame.frame_element

        Returns the `frame` or `iframe` element handle which corresponds to this frame.
        This is an inverse of element_handle.content_frame(). Note that returned handle actually belongs to the parent frame.
        This method throws an error if the frame has been detached before `frameElement()` returns.

        Returns
        -------
        ElementHandle
        """
        return mapping.from_impl(self._sync(self._impl_obj.frameElement()))

    def evaluate(
        self, expression: str, arg: typing.Any = None, force_expr: bool = None
    ) -> typing.Any:
        """Frame.evaluate

        Returns the return value of `pageFunction`
        If the function passed to the `frame.evaluate` returns a Promise, then `frame.evaluate` would wait for the promise to
        resolve and return its value.
        If the function passed to the `frame.evaluate` returns a non-Serializable value, then `frame.evaluate` resolves to
        `undefined`. DevTools Protocol also supports transferring some additional values that are not serializable by `JSON`:
        `-0`, `NaN`, `Infinity`, `-Infinity`, and bigint literals.
        A string can also be passed in instead of a function.
        ElementHandle instances can be passed as an argument to the `frame.evaluate`:

        Parameters
        ----------
        expression : str
            Function to be evaluated in browser context
        force_expr : bool
            Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        arg : Optional[Any]
            Optional argument to pass to `pageFunction`

        Returns
        -------
        Any
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.evaluate(
                    expression=expression,
                    arg=mapping.to_impl(arg),
                    force_expr=force_expr,
                )
            )
        )

    def evaluate_handle(
        self, expression: str, arg: typing.Any = None, force_expr: bool = None
    ) -> "JSHandle":
        """Frame.evaluate_handle

        Returns the return value of `pageFunction` as in-page object (JSHandle).
        The only difference between `frame.evaluate` and `frame.evaluate_handle` is that `frame.evaluate_handle` returns in-page
        object (JSHandle).
        If the function, passed to the `frame.evaluate_handle`, returns a Promise, then `frame.evaluate_handle` would wait for
        the promise to resolve and return its value.
        A string can also be passed in instead of a function.
        JSHandle instances can be passed as an argument to the `frame.evaluate_handle`:

        Parameters
        ----------
        expression : str
            Function to be evaluated in the page context
        force_expr : bool
            Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        arg : Optional[Any]
            Optional argument to pass to `pageFunction`

        Returns
        -------
        JSHandle
        """
        return mapping.from_impl(
            self._sync(
                self._impl_obj.evaluateHandle(
                    expression=expression,
                    arg=mapping.to_impl(arg),
                    force_expr=force_expr,
                )
            )
        )

    def query_selector(self, selector: str) -> typing.Union["ElementHandle", NoneType]:
        """Frame.query_selector

        Returns the ElementHandle pointing to the frame element.
        The method finds an element matching the specified selector within the frame. See Working with
        selectors for more details. If no elements match the selector, the return value resolves to
        `null`.

        Parameters
        ----------
        selector : str
            A selector to query for. See working with selectors for more details.

        Returns
        -------
        Optional[ElementHandle]
        """
        return mapping.from_impl_nullable(
            self._sync(self._impl_obj.querySelector(selector=selector))
        )

    def query_selector_all(self, selector: str) -> typing.List["ElementHandle"]:
        """Frame.query_selector_all

        Returns the ElementHandles pointing to the frame elements.
        The method finds all elements matching the specified selector within the frame. See Working with
        selectors for more details. If no elements match the selector, the return value resolves to
        `[]`.

        Parameters
        ----------
        selector : str
            A selector to query for. See working with selectors for more details.

        Returns
        -------
        List[ElementHandle]
        """
        return mapping.from_impl_list(
            self._sync(self._impl_obj.querySelectorAll(selector=selector))
        )

    def wait_for_selector(
        self,
        selector: str,
        timeout: int = None,
        state: Literal["attached", "detached", "hidden", "visible"] = None,
    ) -> typing.Union["ElementHandle", NoneType]:
        """Frame.wait_for_selector

        Returns when element specified by selector satisfies `state` option. Resolves to `null` if waiting for `hidden` or
        `detached`.
        Wait for the `selector` to satisfy `state` option (either appear/disappear from dom, or become visible/hidden). If at
        the moment of calling the method `selector` already satisfies the condition, the method will return immediately. If the
        selector doesn't satisfy the condition for the `timeout` milliseconds, the function will throw.
        This method works across navigations:

        Parameters
        ----------
        selector : str
            A selector to query for. See working with selectors for more details.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        state : Optional[Literal['attached', 'detached', 'hidden', 'visible']]
            Defaults to `'visible'`. Can be either:
             - `'attached'` - wait for element to be present in DOM.
             - `'detached'` - wait for element to not be present in DOM.
             - `'visible'` - wait for element to have non-empty bounding box and no `visibility:hidden`. Note that element without any content or with `display:none` has an empty bounding box and is not considered visible.
             - `'hidden'` - wait for element to be either detached from DOM, or have an empty bounding box or `visibility:hidden`. This is opposite to the `'visible'` option.

        Returns
        -------
        Optional[ElementHandle]
        """
        return mapping.from_impl_nullable(
            self._sync(
                self._impl_obj.waitForSelector(
                    selector=selector, timeout=timeout, state=state
                )
            )
        )

    def dispatch_event(
        self,
        selector: str,
        type: str,
        event_init: typing.Dict = None,
        timeout: int = None,
    ) -> NoneType:
        """Frame.dispatch_event

        The snippet below dispatches the `click` event on the element. Regardless of the visibility state of the elment, `click`
        is dispatched. This is equivalend to calling
        element.click().
        Under the hood, it creates an instance of an event based on the given `type`, initializes it with `eventInit` properties
        and dispatches it on the element. Events are `composed`, `cancelable` and bubble by default.
        Since `eventInit` is event-specific, please refer to the events documentation for the lists of initial properties:

        DragEvent
        FocusEvent
        KeyboardEvent
        MouseEvent
        PointerEvent
        TouchEvent
        Event

        You can also specify `JSHandle` as the property value if you want live objects to be passed into the event:

        Parameters
        ----------
        selector : str
            A selector to search for element. If there are multiple elements satisfying the selector, the first will be used. See working with selectors for more details.
        type : str
            DOM event type: `"click"`, `"dragstart"`, etc.
        event_init : Optional[Dict]
            Optional event-specific initialization properties.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.dispatchEvent(
                    selector=selector,
                    type=type,
                    eventInit=mapping.to_impl(event_init),
                    timeout=timeout,
                )
            )
        )

    def eval_on_selector(
        self,
        selector: str,
        expression: str,
        arg: typing.Any = None,
        force_expr: bool = None,
    ) -> typing.Any:
        """Frame.eval_on_selector

        Returns the return value of `pageFunction`
        The method finds an element matching the specified selector within the frame and passes it as a first argument to
        `pageFunction`. See Working with selectors for more details. If no elements match the
        selector, the method throws an error.
        If `pageFunction` returns a Promise, then `frame.$eval` would wait for the promise to resolve and return its value.
        Examples:

        Parameters
        ----------
        selector : str
            A selector to query for. See working with selectors for more details.
        expression : str
            Function to be evaluated in browser context
        force_expr : bool
            Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        arg : Optional[Any]
            Optional argument to pass to `pageFunction`

        Returns
        -------
        Any
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.evalOnSelector(
                    selector=selector,
                    expression=expression,
                    arg=mapping.to_impl(arg),
                    force_expr=force_expr,
                )
            )
        )

    def eval_on_selector_all(
        self,
        selector: str,
        expression: str,
        arg: typing.Any = None,
        force_expr: bool = None,
    ) -> typing.Any:
        """Frame.eval_on_selector_all

        Returns the return value of `pageFunction`
        The method finds all elements matching the specified selector within the frame and passes an array of matched elements
        as a first argument to `pageFunction`. See Working with selectors for more details.
        If `pageFunction` returns a Promise, then `frame.$$eval` would wait for the promise to resolve and return its value.
        Examples:

        Parameters
        ----------
        selector : str
            A selector to query for. See working with selectors for more details.
        expression : str
            Function to be evaluated in browser context
        force_expr : bool
            Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        arg : Optional[Any]
            Optional argument to pass to `pageFunction`

        Returns
        -------
        Any
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.evalOnSelectorAll(
                    selector=selector,
                    expression=expression,
                    arg=mapping.to_impl(arg),
                    force_expr=force_expr,
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
        timeout: int = None,
        wait_until: Literal["domcontentloaded", "load", "networkidle"] = None,
    ) -> NoneType:
        """Frame.set_content

        Parameters
        ----------
        html : str
            HTML markup to assign to the page.
        timeout : Optional[int]
            Maximum operation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultNavigationTimeout(timeout), browserContext.setDefaultTimeout(timeout), page.setDefaultNavigationTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        wait_until : Optional[Literal['domcontentloaded', 'load', 'networkidle']]
            When to consider operation succeeded, defaults to `load`. Events can be either:
             - `'domcontentloaded'` - consider operation to be finished when the `DOMContentLoaded` event is fired.
             - `'load'` - consider operation to be finished when the `load` event is fired.
             - `'networkidle'` - consider operation to be finished when there are no network connections for at least `500` ms.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.setContent(
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
        return mapping.from_maybe_impl(self._impl_obj.isDetached())

    def add_script_tag(
        self,
        url: str = None,
        path: typing.Union[str, pathlib.Path] = None,
        content: str = None,
        type: str = None,
    ) -> "ElementHandle":
        """Frame.add_script_tag

        Returns the added tag when the script's onload fires or when the script content was injected into frame.
        Adds a `<script>` tag into the page with the desired url or content.

        Parameters
        ----------
        url : Optional[str]
            URL of a script to be added.
        path : Union[str, pathlib.Path, NoneType]
            Path to the JavaScript file to be injected into frame. If `path` is a relative path, then it is resolved relative to current working directory.
        content : Optional[str]
            Raw JavaScript content to be injected into frame.
        type : Optional[str]
            Script type. Use 'module' in order to load a Javascript ES6 module. See script for more details.

        Returns
        -------
        ElementHandle
        """
        return mapping.from_impl(
            self._sync(
                self._impl_obj.addScriptTag(
                    url=url, path=path, content=content, type=type
                )
            )
        )

    def add_style_tag(
        self,
        url: str = None,
        path: typing.Union[str, pathlib.Path] = None,
        content: str = None,
    ) -> "ElementHandle":
        """Frame.add_style_tag

        Returns the added tag when the stylesheet's onload fires or when the CSS content was injected into frame.
        Adds a `<link rel="stylesheet">` tag into the page with the desired url or a `<style type="text/css">` tag with the
        content.

        Parameters
        ----------
        url : Optional[str]
            URL of the `<link>` tag.
        path : Union[str, pathlib.Path, NoneType]
            Path to the CSS file to be injected into frame. If `path` is a relative path, then it is resolved relative to current working directory.
        content : Optional[str]
            Raw CSS content to be injected into frame.

        Returns
        -------
        ElementHandle
        """
        return mapping.from_impl(
            self._sync(self._impl_obj.addStyleTag(url=url, path=path, content=content))
        )

    def click(
        self,
        selector: str,
        modifiers: typing.Union[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: typing.Union[typing.Tuple[float, float]] = None,
        delay: int = None,
        button: Literal["left", "middle", "right"] = None,
        click_count: int = None,
        timeout: int = None,
        force: bool = None,
        no_wait_after: bool = None,
    ) -> NoneType:
        """Frame.click

        This method clicks an element matching `selector` by performing the following steps:

        Find an element match matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        Wait for actionability checks on the matched element, unless `force` option is set. If the element is detached during the checks, the whole action is retried.
        Scroll the element into view if needed.
        Use page.mouse to click in the center of the element, or the specified `position`.
        Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.

        When all steps combined have not finished during the specified `timeout`, this method rejects with a TimeoutError.
        Passing zero timeout disables this.

        Parameters
        ----------
        selector : str
            A selector to search for element. If there are multiple elements satisfying the selector, the first will be used. See working with selectors for more details.
        modifiers : Optional[List[Literal['Alt', 'Control', 'Meta', 'Shift']]]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores current modifiers back. If not specified, currently pressed modifiers are used.
        position : Optional[typing.Tuple[float, float]]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the element.
        delay : Optional[int]
            Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        button : Optional[Literal['left', 'middle', 'right']]
            Defaults to `left`.
        click_count : Optional[int]
            defaults to 1. See UIEvent.detail.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        force : Optional[bool]
            Whether to bypass the actionability checks. Defaults to `false`.
        no_wait_after : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.click(
                    selector=selector,
                    modifiers=modifiers,
                    position=position,
                    delay=delay,
                    button=button,
                    clickCount=click_count,
                    timeout=timeout,
                    force=force,
                    noWaitAfter=no_wait_after,
                )
            )
        )

    def dblclick(
        self,
        selector: str,
        modifiers: typing.Union[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: typing.Union[typing.Tuple[float, float]] = None,
        delay: int = None,
        button: Literal["left", "middle", "right"] = None,
        timeout: int = None,
        force: bool = None,
        no_wait_after: bool = None,
    ) -> NoneType:
        """Frame.dblclick

        This method double clicks an element matching `selector` by performing the following steps:

        Find an element match matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        Wait for actionability checks on the matched element, unless `force` option is set. If the element is detached during the checks, the whole action is retried.
        Scroll the element into view if needed.
        Use page.mouse to double click in the center of the element, or the specified `position`.
        Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set. Note that if the first click of the `dblclick()` triggers a navigation event, this method will reject.

        When all steps combined have not finished during the specified `timeout`, this method rejects with a TimeoutError.
        Passing zero timeout disables this.

        **NOTE** `frame.dblclick()` dispatches two `click` events and a single `dblclick` event.

        Parameters
        ----------
        selector : str
            A selector to search for element. If there are multiple elements satisfying the selector, the first will be used. See working with selectors for more details.
        modifiers : Optional[List[Literal['Alt', 'Control', 'Meta', 'Shift']]]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores current modifiers back. If not specified, currently pressed modifiers are used.
        position : Optional[typing.Tuple[float, float]]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the element.
        delay : Optional[int]
            Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        button : Optional[Literal['left', 'middle', 'right']]
            Defaults to `left`.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        force : Optional[bool]
            Whether to bypass the actionability checks. Defaults to `false`.
        no_wait_after : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.dblclick(
                    selector=selector,
                    modifiers=modifiers,
                    position=position,
                    delay=delay,
                    button=button,
                    timeout=timeout,
                    force=force,
                    noWaitAfter=no_wait_after,
                )
            )
        )

    def tap(
        self,
        selector: str,
        modifiers: typing.Union[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: typing.Union[typing.Tuple[float, float]] = None,
        timeout: int = None,
        force: bool = None,
        no_wait_after: bool = None,
    ) -> NoneType:
        """Frame.tap

        This method taps an element matching `selector` by performing the following steps:

        Find an element match matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        Wait for actionability checks on the matched element, unless `force` option is set. If the element is detached during the checks, the whole action is retried.
        Scroll the element into view if needed.
        Use page.touchscreen to tap the center of the element, or the specified `position`.
        Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.

        When all steps combined have not finished during the specified `timeout`, this method rejects with a TimeoutError.
        Passing zero timeout disables this.

        **NOTE** `frame.tap()` requires that the `hasTouch` option of the browser context be set to true.

        Parameters
        ----------
        selector : str
            A selector to search for element. If there are multiple elements satisfying the selector, the first will be used. See working with selectors for more details.
        modifiers : Optional[List[Literal['Alt', 'Control', 'Meta', 'Shift']]]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores current modifiers back. If not specified, currently pressed modifiers are used.
        position : Optional[typing.Tuple[float, float]]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the element.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        force : Optional[bool]
            Whether to bypass the actionability checks. Defaults to `false`.
        no_wait_after : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.tap(
                    selector=selector,
                    modifiers=modifiers,
                    position=position,
                    timeout=timeout,
                    force=force,
                    noWaitAfter=no_wait_after,
                )
            )
        )

    def fill(
        self, selector: str, value: str, timeout: int = None, no_wait_after: bool = None
    ) -> NoneType:
        """Frame.fill

        This method waits for an element matching `selector`, waits for actionability checks, focuses the
        element, fills it and triggers an `input` event after filling. If the element matching `selector` is not an `<input>`,
        `<textarea>` or `[contenteditable]` element, this method throws an error. Note that you can pass an empty string to
        clear the input field.
        To send fine-grained keyboard events, use frame.type(selector, text[, options]).

        Parameters
        ----------
        selector : str
            A selector to search for element. If there are multiple elements satisfying the selector, the first will be used. See working with selectors for more details.
        value : str
            Value to fill for the `<input>`, `<textarea>` or `[contenteditable]` element.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        no_wait_after : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.fill(
                    selector=selector,
                    value=value,
                    timeout=timeout,
                    noWaitAfter=no_wait_after,
                )
            )
        )

    def focus(self, selector: str, timeout: int = None) -> NoneType:
        """Frame.focus

        This method fetches an element with `selector` and focuses it. If there's no element matching `selector`, the method
        waits until a matching element appears in the DOM.

        Parameters
        ----------
        selector : str
            A selector to search for element. If there are multiple elements satisfying the selector, the first will be used. See working with selectors for more details.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        """
        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.focus(selector=selector, timeout=timeout))
        )

    def text_content(
        self, selector: str, timeout: int = None
    ) -> typing.Union[str, NoneType]:
        """Frame.text_content

        Resolves to the `element.textContent`.

        Parameters
        ----------
        selector : str
            A selector to search for element. If there are multiple elements satisfying the selector, the first will be used. See working with selectors for more details.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.

        Returns
        -------
        Optional[str]
        """
        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.textContent(selector=selector, timeout=timeout))
        )

    def inner_text(self, selector: str, timeout: int = None) -> str:
        """Frame.inner_text

        Resolves to the `element.innerText`.

        Parameters
        ----------
        selector : str
            A selector to search for element. If there are multiple elements satisfying the selector, the first will be used. See working with selectors for more details.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.innerText(selector=selector, timeout=timeout))
        )

    def inner_html(self, selector: str, timeout: int = None) -> str:
        """Frame.inner_html

        Resolves to the `element.innerHTML`.

        Parameters
        ----------
        selector : str
            A selector to search for element. If there are multiple elements satisfying the selector, the first will be used. See working with selectors for more details.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.innerHTML(selector=selector, timeout=timeout))
        )

    def get_attribute(
        self, selector: str, name: str, timeout: int = None
    ) -> typing.Union[str, NoneType]:
        """Frame.get_attribute

        Returns element attribute value.

        Parameters
        ----------
        selector : str
            A selector to search for element. If there are multiple elements satisfying the selector, the first will be used. See working with selectors for more details.
        name : str
            Attribute name to get the value for.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.

        Returns
        -------
        Optional[str]
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.getAttribute(
                    selector=selector, name=name, timeout=timeout
                )
            )
        )

    def hover(
        self,
        selector: str,
        modifiers: typing.Union[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: typing.Union[typing.Tuple[float, float]] = None,
        timeout: int = None,
        force: bool = None,
    ) -> NoneType:
        """Frame.hover

        This method hovers over an element matching `selector` by performing the following steps:

        Find an element match matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        Wait for actionability checks on the matched element, unless `force` option is set. If the element is detached during the checks, the whole action is retried.
        Scroll the element into view if needed.
        Use page.mouse to hover over the center of the element, or the specified `position`.
        Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.

        When all steps combined have not finished during the specified `timeout`, this method rejects with a TimeoutError.
        Passing zero timeout disables this.

        Parameters
        ----------
        selector : str
            A selector to search for element. If there are multiple elements satisfying the selector, the first will be used. See working with selectors for more details.
        modifiers : Optional[List[Literal['Alt', 'Control', 'Meta', 'Shift']]]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores current modifiers back. If not specified, currently pressed modifiers are used.
        position : Optional[typing.Tuple[float, float]]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the element.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        force : Optional[bool]
            Whether to bypass the actionability checks. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.hover(
                    selector=selector,
                    modifiers=modifiers,
                    position=position,
                    timeout=timeout,
                    force=force,
                )
            )
        )

    def select_option(
        self,
        selector: str,
        value: typing.Union[str, typing.List[str]] = None,
        index: typing.Union[int, typing.List[int]] = None,
        label: typing.Union[str, typing.List[str]] = None,
        element: typing.Union["ElementHandle", typing.List["ElementHandle"]] = None,
        timeout: int = None,
        no_wait_after: bool = None,
    ) -> typing.List[str]:
        """Frame.select_option

        Returns the array of option values that have been successfully selected.
        Triggers a `change` and `input` event once all the provided options have been selected. If there's no `<select>` element
        matching `selector`, the method throws an error.

        Parameters
        ----------
        selector : str
            A selector to query for. See working with selectors for more details.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        no_wait_after : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.

        Returns
        -------
        List[str]
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.selectOption(
                    selector=selector,
                    value=value,
                    index=index,
                    label=label,
                    element=mapping.to_impl(element),
                    timeout=timeout,
                    noWaitAfter=no_wait_after,
                )
            )
        )

    def set_input_files(
        self,
        selector: str,
        files: typing.Union[
            str,
            pathlib.Path,
            "FilePayload",
            typing.List[str],
            typing.List[pathlib.Path],
            typing.List["FilePayload"],
        ],
        timeout: int = None,
        no_wait_after: bool = None,
    ) -> NoneType:
        """Frame.set_input_files

        This method expects `selector` to point to an input
        element.
        Sets the value of the file input to these file paths or files. If some of the `filePaths` are relative paths, then they
        are resolved relative to the current working directory. For
        empty array, clears the selected files.

        Parameters
        ----------
        selector : str
            A selector to search for element. If there are multiple elements satisfying the selector, the first will be used. See working with selectors for more details.
        files : Union[str, pathlib.Path, Dict, List[str], List[pathlib.Path], List[Dict]]
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        no_wait_after : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.setInputFiles(
                    selector=selector,
                    files=files,
                    timeout=timeout,
                    noWaitAfter=no_wait_after,
                )
            )
        )

    def type(
        self,
        selector: str,
        text: str,
        delay: int = None,
        timeout: int = None,
        no_wait_after: bool = None,
    ) -> NoneType:
        """Frame.type

        Sends a `keydown`, `keypress`/`input`, and `keyup` event for each character in the text. `frame.type` can be used to
        send fine-grained keyboard events. To fill values in form fields, use frame.fill(selector, value[, options]).
        To press a special key, like `Control` or `ArrowDown`, use keyboard.press(key[, options]).

        Parameters
        ----------
        selector : str
            A selector to search for element. If there are multiple elements satisfying the selector, the first will be used. See working with selectors for more details.
        text : str
            A text to type into a focused element.
        delay : Optional[int]
            Time to wait between key presses in milliseconds. Defaults to 0.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        no_wait_after : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.type(
                    selector=selector,
                    text=text,
                    delay=delay,
                    timeout=timeout,
                    noWaitAfter=no_wait_after,
                )
            )
        )

    def press(
        self,
        selector: str,
        key: str,
        delay: int = None,
        timeout: int = None,
        no_wait_after: bool = None,
    ) -> NoneType:
        """Frame.press

        `key` can specify the intended keyboardEvent.key
        value or a single character to generate the text for. A superset of the `key` values can be found
        here. Examples of the keys are:
        `F1` - `F12`, `Digit0`- `Digit9`, `KeyA`- `KeyZ`, `Backquote`, `Minus`, `Equal`, `Backslash`, `Backspace`, `Tab`,
        `Delete`, `Escape`, `ArrowDown`, `End`, `Enter`, `Home`, `Insert`, `PageDown`, `PageUp`, `ArrowRight`, `ArrowUp`, etc.
        Following modification shortcuts are also suported: `Shift`, `Control`, `Alt`, `Meta`, `ShiftLeft`.
        Holding down `Shift` will type the text that corresponds to the `key` in the upper case.
        If `key` is a single character, it is case-sensitive, so the values `a` and `A` will generate different respective
        texts.
        Shortcuts such as `key: "Control+o"` or `key: "Control+Shift+T"` are supported as well. When speficied with the
        modifier, modifier is pressed and being held while the subsequent key is being pressed.

        Parameters
        ----------
        selector : str
            A selector to search for element. If there are multiple elements satisfying the selector, the first will be used. See working with selectors for more details.
        key : str
            Name of the key to press or a character to generate, such as `ArrowLeft` or `a`.
        delay : Optional[int]
            Time to wait between `keydown` and `keyup` in milliseconds. Defaults to 0.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        no_wait_after : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.press(
                    selector=selector,
                    key=key,
                    delay=delay,
                    timeout=timeout,
                    noWaitAfter=no_wait_after,
                )
            )
        )

    def check(
        self,
        selector: str,
        timeout: int = None,
        force: bool = None,
        no_wait_after: bool = None,
    ) -> NoneType:
        """Frame.check

        This method checks an element matching `selector` by performing the following steps:

        Find an element match matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        Ensure that matched element is a checkbox or a radio input. If not, this method rejects. If the element is already checked, this method returns immediately.
        Wait for actionability checks on the matched element, unless `force` option is set. If the element is detached during the checks, the whole action is retried.
        Scroll the element into view if needed.
        Use page.mouse to click in the center of the element.
        Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.
        Ensure that the element is now checked. If not, this method rejects.

        When all steps combined have not finished during the specified `timeout`, this method rejects with a TimeoutError.
        Passing zero timeout disables this.

        Parameters
        ----------
        selector : str
            A selector to search for element. If there are multiple elements satisfying the selector, the first will be used. See working with selectors for more details.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        force : Optional[bool]
            Whether to bypass the actionability checks. Defaults to `false`.
        no_wait_after : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.check(
                    selector=selector,
                    timeout=timeout,
                    force=force,
                    noWaitAfter=no_wait_after,
                )
            )
        )

    def uncheck(
        self,
        selector: str,
        timeout: int = None,
        force: bool = None,
        no_wait_after: bool = None,
    ) -> NoneType:
        """Frame.uncheck

        This method checks an element matching `selector` by performing the following steps:

        Find an element match matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        Ensure that matched element is a checkbox or a radio input. If not, this method rejects. If the element is already unchecked, this method returns immediately.
        Wait for actionability checks on the matched element, unless `force` option is set. If the element is detached during the checks, the whole action is retried.
        Scroll the element into view if needed.
        Use page.mouse to click in the center of the element.
        Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.
        Ensure that the element is now unchecked. If not, this method rejects.

        When all steps combined have not finished during the specified `timeout`, this method rejects with a TimeoutError.
        Passing zero timeout disables this.

        Parameters
        ----------
        selector : str
            A selector to search for element. If there are multiple elements satisfying the selector, the first will be used. See working with selectors for more details.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        force : Optional[bool]
            Whether to bypass the actionability checks. Defaults to `false`.
        no_wait_after : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.uncheck(
                    selector=selector,
                    timeout=timeout,
                    force=force,
                    noWaitAfter=no_wait_after,
                )
            )
        )

    def wait_for_timeout(self, timeout: int) -> NoneType:
        """Frame.wait_for_timeout

        Returns a promise that resolves after the timeout.
        Note that `frame.wait_for_timeout()` should only be used for debugging. Tests using the timer in production are going to
        be flaky. Use signals such as network events, selectors becoming visible and others instead.

        Parameters
        ----------
        timeout : int
            A timeout to wait for
        """
        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.waitForTimeout(timeout=timeout))
        )

    def wait_for_function(
        self,
        expression: str,
        arg: typing.Any = None,
        force_expr: bool = None,
        timeout: int = None,
        polling: typing.Union[int, Literal["raf"]] = None,
    ) -> "JSHandle":
        """Frame.wait_for_function

        Returns when the `pageFunction` returns a truthy value. It resolves to a JSHandle of the truthy value.
        The `waitForFunction` can be used to observe viewport size change:

        To pass an argument from Node.js to the predicate of `frame.wait_for_function` function:

        Parameters
        ----------
        expression : str
            Function to be evaluated in browser context
        force_expr : bool
            Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        arg : Optional[Any]
            Optional argument to pass to `pageFunction`
        timeout : Optional[int]
            maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout).
        polling : Union[int, 'raf', NoneType]
            If `polling` is `'raf'`, then `pageFunction` is constantly executed in `requestAnimationFrame` callback. If `polling` is a number, then it is treated as an interval in milliseconds at which the function would be executed. Defaults to `raf`.

        Returns
        -------
        JSHandle
        """
        return mapping.from_impl(
            self._sync(
                self._impl_obj.waitForFunction(
                    expression=expression,
                    arg=mapping.to_impl(arg),
                    force_expr=force_expr,
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

    def expect_load_state(
        self,
        state: Literal["domcontentloaded", "load", "networkidle"] = None,
        timeout: int = None,
    ) -> EventContextManager[typing.Union["Response", NoneType]]:
        """Frame.expect_load_state

        Returns context manager that waits for ``event`` to fire upon exit. It passes event's value
        into the ``predicate`` function and waits for the predicate to return a truthy value. Will throw
        an error if the page is closed before the ``event`` is fired.

        with page.expect_loadstate() as event_info:
            page.click("button")
        value = event_info.value

        Parameters
        ----------
        predicate : Optional[typing.Callable[[Any], bool]]
            Predicate receiving event data.
        timeout : Optional[int]
            Maximum wait time in milliseconds, defaults to 30 seconds, pass `0` to disable the timeout.
            The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or
            page.setDefaultTimeout(timeout) methods.
        """
        return EventContextManager(
            self, self._impl_obj.waitForLoadState(state, timeout)
        )

    def expect_navigation(
        self,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]] = None,
        wait_until: Literal["domcontentloaded", "load", "networkidle"] = None,
        timeout: int = None,
    ) -> EventContextManager[typing.Union["Response", NoneType]]:
        """Frame.expect_navigation

        Returns context manager that waits for ``event`` to fire upon exit. It passes event's value
        into the ``predicate`` function and waits for the predicate to return a truthy value. Will throw
        an error if the page is closed before the ``event`` is fired.

        with page.expect_navigation() as event_info:
            page.click("button")
        value = event_info.value

        Parameters
        ----------
        predicate : Optional[typing.Callable[[Any], bool]]
            Predicate receiving event data.
        timeout : Optional[int]
            Maximum wait time in milliseconds, defaults to 30 seconds, pass `0` to disable the timeout.
            The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or
            page.setDefaultTimeout(timeout) methods.
        """
        return EventContextManager(
            self, self._impl_obj.waitForNavigation(url, wait_until, timeout)
        )


mapping.register(FrameImpl, Frame)


class Worker(SyncBase):
    def __init__(self, obj: WorkerImpl):
        super().__init__(obj)

    @property
    def url(self) -> str:
        """Worker.url

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.url)

    def evaluate(
        self, expression: str, arg: typing.Any = None, force_expr: bool = None
    ) -> typing.Any:
        """Worker.evaluate

        Returns the return value of `pageFunction`
        If the function passed to the `worker.evaluate` returns a Promise, then `worker.evaluate` would wait for the promise
        to resolve and return its value.
        If the function passed to the `worker.evaluate` returns a non-Serializable value, then `worker.evaluate` resolves to
        `undefined`. DevTools Protocol also supports transferring some additional values that are not serializable by `JSON`:
        `-0`, `NaN`, `Infinity`, `-Infinity`, and bigint literals.

        Parameters
        ----------
        expression : str
            Function to be evaluated in the worker context
        force_expr : bool
            Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        arg : Optional[Any]
            Optional argument to pass to `pageFunction`

        Returns
        -------
        Any
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.evaluate(
                    expression=expression,
                    arg=mapping.to_impl(arg),
                    force_expr=force_expr,
                )
            )
        )

    def evaluate_handle(
        self, expression: str, arg: typing.Any = None, force_expr: bool = None
    ) -> "JSHandle":
        """Worker.evaluate_handle

        Returns the return value of `pageFunction` as in-page object (JSHandle).
        The only difference between `worker.evaluate` and `worker.evaluate_handle` is that `worker.evaluate_handle` returns
        in-page object (JSHandle).
        If the function passed to the `worker.evaluate_handle` returns a Promise, then `worker.evaluate_handle` would wait for
        the promise to resolve and return its value.

        Parameters
        ----------
        expression : str
            Function to be evaluated in the page context
        force_expr : bool
            Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        arg : Optional[Any]
            Optional argument to pass to `pageFunction`

        Returns
        -------
        JSHandle
        """
        return mapping.from_impl(
            self._sync(
                self._impl_obj.evaluateHandle(
                    expression=expression,
                    arg=mapping.to_impl(arg),
                    force_expr=force_expr,
                )
            )
        )


mapping.register(WorkerImpl, Worker)


class Selectors(SyncBase):
    def __init__(self, obj: SelectorsImpl):
        super().__init__(obj)

    def register(
        self,
        name: str,
        source: str = None,
        path: typing.Union[str, pathlib.Path] = None,
        content_script: bool = None,
    ) -> NoneType:
        """Selectors.register

        An example of registering selector engine that queries elements based on a tag name:

        Parameters
        ----------
        name : str
            Name that is used in selectors as a prefix, e.g. `{name: 'foo'}` enables `foo=myselectorbody` selectors. May only contain `[a-zA-Z0-9_]` characters.
        source : Optional[str]
            Script that evaluates to a selector engine instance.
        content_script : Optional[bool]
            Whether to run this selector engine in isolated JavaScript environment. This environment has access to the same DOM, but not any JavaScript objects from the frame's scripts. Defaults to `false`. Note that running as a content script is not guaranteed when this engine is used together with other registered engines.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.register(
                    name=name, source=source, path=path, contentScript=content_script
                )
            )
        )


mapping.register(SelectorsImpl, Selectors)


class ConsoleMessage(SyncBase):
    def __init__(self, obj: ConsoleMessageImpl):
        super().__init__(obj)

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

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.text)

    @property
    def args(self) -> typing.List["JSHandle"]:
        """ConsoleMessage.args

        Returns
        -------
        List[JSHandle]
        """
        return mapping.from_impl_list(self._impl_obj.args)

    @property
    def location(self) -> "SourceLocation":
        """ConsoleMessage.location

        Returns
        -------
        {"url": str, "lineNumber": int, "columnNumber": int}
        """
        return mapping.from_impl(self._impl_obj.location)


mapping.register(ConsoleMessageImpl, ConsoleMessage)


class Dialog(SyncBase):
    def __init__(self, obj: DialogImpl):
        super().__init__(obj)

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
        return mapping.from_maybe_impl(self._impl_obj.defaultValue)

    def accept(self, prompt_text: str = None) -> NoneType:
        """Dialog.accept

        Returns when the dialog has been accepted.

        Parameters
        ----------
        prompt_text : Optional[str]
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
    def __init__(self, obj: DownloadImpl):
        super().__init__(obj)

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
        `Content-Disposition` response header
        or the `download` attribute. See the spec on whatwg. Different
        browsers can use different logic for computing it.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.suggestedFilename)

    def delete(self) -> NoneType:
        """Download.delete

        Deletes the downloaded file.
        """
        return mapping.from_maybe_impl(self._sync(self._impl_obj.delete()))

    def failure(self) -> typing.Union[str, NoneType]:
        """Download.failure

        Returns download error if any.

        Returns
        -------
        Optional[str]
        """
        return mapping.from_maybe_impl(self._sync(self._impl_obj.failure()))

    def path(self) -> typing.Union[str, NoneType]:
        """Download.path

        Returns path to the downloaded file in case of successful download.

        Returns
        -------
        Optional[str]
        """
        return mapping.from_maybe_impl(self._sync(self._impl_obj.path()))

    def save_as(self, path: typing.Union[str, pathlib.Path]) -> NoneType:
        """Download.save_as

        Saves the download to a user-specified path.

        Parameters
        ----------
        path : Union[str, pathlib.Path]
            Path where the download should be saved.
        """
        return mapping.from_maybe_impl(self._sync(self._impl_obj.saveAs(path=path)))


mapping.register(DownloadImpl, Download)


class Video(SyncBase):
    def __init__(self, obj: VideoImpl):
        super().__init__(obj)

    def path(self) -> str:
        """Video.path

        Returns the file system path this video will be recorded to. The video is guaranteed to be written to the filesystem
        upon closing the browser context.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._sync(self._impl_obj.path()))


mapping.register(VideoImpl, Video)


class BindingCall(SyncBase):
    def __init__(self, obj: BindingCallImpl):
        super().__init__(obj)

    def call(self, func: typing.Callable) -> NoneType:
        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.call(func=self._wrap_handler(func)))
        )


mapping.register(BindingCallImpl, BindingCall)


class Page(SyncBase):
    def __init__(self, obj: PageImpl):
        super().__init__(obj)

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
        return mapping.from_impl(self._impl_obj.mainFrame)

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

        Shortcut for main frame's frame.url().

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.url)

    @property
    def workers(self) -> typing.List["Worker"]:
        """Page.workers

        This method returns all of the dedicated WebWorkers
        associated with the page.

        **NOTE** This does not contain ServiceWorkers

        Returns
        -------
        List[Worker]
        """
        return mapping.from_impl_list(self._impl_obj.workers)

    @property
    def video(self) -> typing.Union["Video", NoneType]:
        """Page.video

        Video object associated with this page.

        Returns
        -------
        Optional[Video]
        """
        return mapping.from_impl_nullable(self._impl_obj.video)

    def opener(self) -> typing.Union["Page", NoneType]:
        """Page.opener

        Returns the opener for popup pages and `null` for others. If the opener has been closed already the promise may resolve
        to `null`.

        Returns
        -------
        Optional[Page]
        """
        return mapping.from_impl_nullable(self._sync(self._impl_obj.opener()))

    def frame(
        self,
        name: str = None,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]] = None,
    ) -> typing.Union["Frame", NoneType]:
        """Page.frame

        Returns frame matching the specified criteria. Either `name` or `url` must be specified.

        Parameters
        ----------
        name : Optional[str]
            frame name specified in the `iframe`'s `name` attribute
        url : Union[str, Pattern, Callable[[str], bool], NoneType]
            A glob pattern, regex pattern or predicate receiving frame's `url` as a URL object.

        Returns
        -------
        Optional[Frame]
        """
        return mapping.from_impl_nullable(
            self._impl_obj.frame(name=name, url=self._wrap_handler(url))
        )

    def set_default_navigation_timeout(self, timeout: int) -> NoneType:
        """Page.set_default_navigation_timeout

        This setting will change the default maximum navigation time for the following methods and related shortcuts:

        page.go_back([options])
        page.go_forward([options])
        page.goto(url[, options])
        page.reload([options])
        page.set_content(html[, options])
        page.wait_for_navigation([options])

        **NOTE** page.set_default_navigation_timeout(timeout) takes priority over page.set_default_timeout(timeout),
        browser_context.set_default_timeout(timeout) and browser_context.set_default_navigation_timeout(timeout).

        Parameters
        ----------
        timeout : int
            Maximum navigation time in milliseconds
        """
        return mapping.from_maybe_impl(
            self._impl_obj.setDefaultNavigationTimeout(timeout=timeout)
        )

    def set_default_timeout(self, timeout: int) -> NoneType:
        """Page.set_default_timeout

        This setting will change the default maximum time for all the methods accepting `timeout` option.

        **NOTE** page.set_default_navigation_timeout(timeout) takes priority over page.set_default_timeout(timeout).

        Parameters
        ----------
        timeout : int
            Maximum time in milliseconds
        """
        return mapping.from_maybe_impl(
            self._impl_obj.setDefaultTimeout(timeout=timeout)
        )

    def query_selector(self, selector: str) -> typing.Union["ElementHandle", NoneType]:
        """Page.query_selector

        The method finds an element matching the specified selector within the page. If no elements match the selector, the
        return value resolves to `null`.
        Shortcut for main frame's frame.$(selector).

        Parameters
        ----------
        selector : str
            A selector to query for. See working with selectors for more details.

        Returns
        -------
        Optional[ElementHandle]
        """
        return mapping.from_impl_nullable(
            self._sync(self._impl_obj.querySelector(selector=selector))
        )

    def query_selector_all(self, selector: str) -> typing.List["ElementHandle"]:
        """Page.query_selector_all

        The method finds all elements matching the specified selector within the page. If no elements match the selector, the
        return value resolves to `[]`.
        Shortcut for main frame's frame.$$(selector).

        Parameters
        ----------
        selector : str
            A selector to query for. See working with selectors for more details.

        Returns
        -------
        List[ElementHandle]
        """
        return mapping.from_impl_list(
            self._sync(self._impl_obj.querySelectorAll(selector=selector))
        )

    def wait_for_selector(
        self,
        selector: str,
        timeout: int = None,
        state: Literal["attached", "detached", "hidden", "visible"] = None,
    ) -> typing.Union["ElementHandle", NoneType]:
        """Page.wait_for_selector

        Returns when element specified by selector satisfies `state` option. Resolves to `null` if waiting for `hidden` or
        `detached`.
        Wait for the `selector` to satisfy `state` option (either appear/disappear from dom, or become visible/hidden). If at
        the moment of calling the method `selector` already satisfies the condition, the method will return immediately. If the
        selector doesn't satisfy the condition for the `timeout` milliseconds, the function will throw.
        This method works across navigations:

        Parameters
        ----------
        selector : str
            A selector to query for. See working with selectors for more details.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        state : Optional[Literal['attached', 'detached', 'hidden', 'visible']]
            Defaults to `'visible'`. Can be either:
             - `'attached'` - wait for element to be present in DOM.
             - `'detached'` - wait for element to not be present in DOM.
             - `'visible'` - wait for element to have non-empty bounding box and no `visibility:hidden`. Note that element without any content or with `display:none` has an empty bounding box and is not considered visible.
             - `'hidden'` - wait for element to be either detached from DOM, or have an empty bounding box or `visibility:hidden`. This is opposite to the `'visible'` option.

        Returns
        -------
        Optional[ElementHandle]
        """
        return mapping.from_impl_nullable(
            self._sync(
                self._impl_obj.waitForSelector(
                    selector=selector, timeout=timeout, state=state
                )
            )
        )

    def dispatch_event(
        self,
        selector: str,
        type: str,
        event_init: typing.Dict = None,
        timeout: int = None,
    ) -> NoneType:
        """Page.dispatch_event

        The snippet below dispatches the `click` event on the element. Regardless of the visibility state of the elment, `click`
        is dispatched. This is equivalend to calling
        element.click().
        Under the hood, it creates an instance of an event based on the given `type`, initializes it with `eventInit` properties
        and dispatches it on the element. Events are `composed`, `cancelable` and bubble by default.
        Since `eventInit` is event-specific, please refer to the events documentation for the lists of initial properties:

        DragEvent
        FocusEvent
        KeyboardEvent
        MouseEvent
        PointerEvent
        TouchEvent
        Event

        You can also specify `JSHandle` as the property value if you want live objects to be passed into the event:

        Parameters
        ----------
        selector : str
            A selector to search for element. If there are multiple elements satisfying the selector, the first will be used. See working with selectors for more details.
        type : str
            DOM event type: `"click"`, `"dragstart"`, etc.
        event_init : Optional[Dict]
            Optional event-specific initialization properties.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.dispatchEvent(
                    selector=selector,
                    type=type,
                    eventInit=mapping.to_impl(event_init),
                    timeout=timeout,
                )
            )
        )

    def evaluate(
        self, expression: str, arg: typing.Any = None, force_expr: bool = None
    ) -> typing.Any:
        """Page.evaluate

        Returns the value of the `pageFunction` invacation.
        If the function passed to the `page.evaluate` returns a Promise, then `page.evaluate` would wait for the promise to
        resolve and return its value.
        If the function passed to the `page.evaluate` returns a non-Serializable value, then `page.evaluate` resolves to
        `undefined`. DevTools Protocol also supports transferring some additional values that are not serializable by `JSON`:
        `-0`, `NaN`, `Infinity`, `-Infinity`, and bigint literals.
        Passing argument to `pageFunction`:
        A string can also be passed in instead of a function:
        ElementHandle instances can be passed as an argument to the `page.evaluate`:
        Shortcut for main frame's frame.evaluate(pageFunction[, arg]).

        Parameters
        ----------
        expression : str
            Function to be evaluated in the page context
        force_expr : bool
            Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        arg : Optional[Any]
            Optional argument to pass to `pageFunction`

        Returns
        -------
        Any
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.evaluate(
                    expression=expression,
                    arg=mapping.to_impl(arg),
                    force_expr=force_expr,
                )
            )
        )

    def evaluate_handle(
        self, expression: str, arg: typing.Any = None, force_expr: bool = None
    ) -> "JSHandle":
        """Page.evaluate_handle

        Returns the value of the `pageFunction` invacation as in-page object (JSHandle).
        The only difference between `page.evaluate` and `page.evaluate_handle` is that `page.evaluate_handle` returns in-page
        object (JSHandle).
        If the function passed to the `page.evaluate_handle` returns a Promise, then `page.evaluate_handle` would wait for the
        promise to resolve and return its value.
        A string can also be passed in instead of a function:
        JSHandle instances can be passed as an argument to the `page.evaluate_handle`:

        Parameters
        ----------
        expression : str
            Function to be evaluated in the page context
        force_expr : bool
            Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        arg : Optional[Any]
            Optional argument to pass to `pageFunction`

        Returns
        -------
        JSHandle
        """
        return mapping.from_impl(
            self._sync(
                self._impl_obj.evaluateHandle(
                    expression=expression,
                    arg=mapping.to_impl(arg),
                    force_expr=force_expr,
                )
            )
        )

    def eval_on_selector(
        self,
        selector: str,
        expression: str,
        arg: typing.Any = None,
        force_expr: bool = None,
    ) -> typing.Any:
        """Page.eval_on_selector

        The method finds an element matching the specified selector within the page and passes it as a first argument to
        `pageFunction`. If no elements match the selector, the method throws an error. Returns the value of `pageFunction`.
        If `pageFunction` returns a Promise, then `page.$eval` would wait for the promise to resolve and return its value.
        Examples:
        Shortcut for main frame's frame.$eval(selector, pageFunction[, arg]).

        Parameters
        ----------
        selector : str
            A selector to query for. See working with selectors for more details.
        expression : str
            Function to be evaluated in browser context
        force_expr : bool
            Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        arg : Optional[Any]
            Optional argument to pass to `pageFunction`

        Returns
        -------
        Any
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.evalOnSelector(
                    selector=selector,
                    expression=expression,
                    arg=mapping.to_impl(arg),
                    force_expr=force_expr,
                )
            )
        )

    def eval_on_selector_all(
        self,
        selector: str,
        expression: str,
        arg: typing.Any = None,
        force_expr: bool = None,
    ) -> typing.Any:
        """Page.eval_on_selector_all

        The method finds all elements matching the specified selector within the page and passes an array of matched elements as
        a first argument to `pageFunction`. Returns the result of `pageFunction` invocation.
        If `pageFunction` returns a Promise, then `page.$$eval` would wait for the promise to resolve and return its value.
        Examples:

        Parameters
        ----------
        selector : str
            A selector to query for. See working with selectors for more details.
        expression : str
            Function to be evaluated in browser context
        force_expr : bool
            Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        arg : Optional[Any]
            Optional argument to pass to `pageFunction`

        Returns
        -------
        Any
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.evalOnSelectorAll(
                    selector=selector,
                    expression=expression,
                    arg=mapping.to_impl(arg),
                    force_expr=force_expr,
                )
            )
        )

    def add_script_tag(
        self,
        url: str = None,
        path: typing.Union[str, pathlib.Path] = None,
        content: str = None,
        type: str = None,
    ) -> "ElementHandle":
        """Page.add_script_tag

        Adds a `<script>` tag into the page with the desired url or content. Returns the added tag when the script's onload
        fires or when the script content was injected into frame.
        Shortcut for main frame's frame.add_script_tag(script).

        Parameters
        ----------
        url : Optional[str]
            URL of a script to be added.
        path : Union[str, pathlib.Path, NoneType]
            Path to the JavaScript file to be injected into frame. If `path` is a relative path, then it is resolved relative to current working directory.
        content : Optional[str]
            Raw JavaScript content to be injected into frame.
        type : Optional[str]
            Script type. Use 'module' in order to load a Javascript ES6 module. See script for more details.

        Returns
        -------
        ElementHandle
        """
        return mapping.from_impl(
            self._sync(
                self._impl_obj.addScriptTag(
                    url=url, path=path, content=content, type=type
                )
            )
        )

    def add_style_tag(
        self,
        url: str = None,
        path: typing.Union[str, pathlib.Path] = None,
        content: str = None,
    ) -> "ElementHandle":
        """Page.add_style_tag

        Adds a `<link rel="stylesheet">` tag into the page with the desired url or a `<style type="text/css">` tag with the
        content. Returns the added tag when the stylesheet's onload fires or when the CSS content was injected into frame.
        Shortcut for main frame's frame.add_style_tag(style).

        Parameters
        ----------
        url : Optional[str]
            URL of the `<link>` tag.
        path : Union[str, pathlib.Path, NoneType]
            Path to the CSS file to be injected into frame. If `path` is a relative path, then it is resolved relative to current working directory.
        content : Optional[str]
            Raw CSS content to be injected into frame.

        Returns
        -------
        ElementHandle
        """
        return mapping.from_impl(
            self._sync(self._impl_obj.addStyleTag(url=url, path=path, content=content))
        )

    def expose_function(self, name: str, binding: typing.Callable) -> NoneType:
        """Page.expose_function

        The method adds a function called `name` on the `window` object of every frame in the page. When called, the function
        executes `playwrightFunction` in Node.js and returns a Promise which resolves to the return value of
        `playwrightFunction`.
        If the `playwrightFunction` returns a Promise, it will be awaited.
        See browser_context.expose_function(name, playwrightFunction) for context-wide exposed function.

        **NOTE** Functions installed via `page.expose_function` survive navigations.

        An example of adding an `md5` function to the page:

        An example of adding a `window.readfile` function to the page:

        Parameters
        ----------
        name : str
            Name of the function on the window object
        binding : Callable
            Callback function which will be called in Playwright's context.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.exposeFunction(
                    name=name, binding=self._wrap_handler(binding)
                )
            )
        )

    def expose_binding(
        self, name: str, binding: typing.Callable, handle: bool = None
    ) -> NoneType:
        """Page.expose_binding

        The method adds a function called `name` on the `window` object of every frame in this page. When called, the function
        executes `playwrightBinding` in Node.js and returns a Promise which resolves to the return value of
        `playwrightBinding`. If the `playwrightBinding` returns a Promise, it will be awaited.
        The first argument of the `playwrightBinding` function contains information about the caller: `{ browserContext: BrowserContext, page: Page, frame: Frame }`.
        See browser_context.expose_binding(name, playwrightBinding[, options]) for the context-wide version.

        **NOTE** Functions installed via `page.expose_binding` survive navigations.

        An example of exposing page URL to all frames in a page:

        An example of passing an element handle:

        Parameters
        ----------
        name : str
            Name of the function on the window object.
        binding : Callable
            Callback function that will be called in the Playwright's context.
        handle : Optional[bool]
            Whether to pass the argument as a handle, instead of passing by value. When passing a handle, only one argument is supported. When passing by value, multiple arguments are supported.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.exposeBinding(
                    name=name, binding=self._wrap_handler(binding), handle=handle
                )
            )
        )

    def set_extra_http_headers(self, headers: typing.Dict[str, str]) -> NoneType:
        """Page.set_extra_http_headers

        The extra HTTP headers will be sent with every request the page initiates.

        **NOTE** page.set_extra_http_headers does not guarantee the order of headers in the outgoing requests.

        Parameters
        ----------
        headers : Dict[str, str]
            An object containing additional HTTP headers to be sent with every request. All header values must be strings.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.setExtraHTTPHeaders(headers=mapping.to_impl(headers))
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
        timeout: int = None,
        wait_until: Literal["domcontentloaded", "load", "networkidle"] = None,
    ) -> NoneType:
        """Page.set_content

        Parameters
        ----------
        html : str
            HTML markup to assign to the page.
        timeout : Optional[int]
            Maximum operation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultNavigationTimeout(timeout), browserContext.setDefaultTimeout(timeout), page.setDefaultNavigationTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        wait_until : Optional[Literal['domcontentloaded', 'load', 'networkidle']]
            When to consider operation succeeded, defaults to `load`. Events can be either:
             - `'domcontentloaded'` - consider operation to be finished when the `DOMContentLoaded` event is fired.
             - `'load'` - consider operation to be finished when the `load` event is fired.
             - `'networkidle'` - consider operation to be finished when there are no network connections for at least `500` ms.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.setContent(
                    html=html, timeout=timeout, waitUntil=wait_until
                )
            )
        )

    def goto(
        self,
        url: str,
        timeout: int = None,
        wait_until: Literal["domcontentloaded", "load", "networkidle"] = None,
        referer: str = None,
    ) -> typing.Union["Response", NoneType]:
        """Page.goto

        Returns the main resource response. In case of multiple redirects, the navigation will resolve with the response of the
        last redirect.
        `page.goto` will throw an error if:

        there's an SSL error (e.g. in case of self-signed certificates).
        target URL is invalid.
        the `timeout` is exceeded during navigation.
        the remote server does not respond or is unreachable.
        the main resource failed to load.

        `page.goto` will not throw an error when any valid HTTP status code is returned by the remote server, including 404 "Not
        Found" and 500 "Internal Server Error".  The status code for such responses can be retrieved by calling
        response.status().

        **NOTE** `page.goto` either throws an error or returns a main resource response. The only exceptions are navigation to
        `about:blank` or navigation to the same URL with a different hash, which would succeed and return `null`.
        **NOTE** Headless mode doesn't support navigation to a PDF document. See the upstream
        issue.

        Shortcut for main frame's frame.goto(url[, options])

        Parameters
        ----------
        url : str
            URL to navigate page to. The url should include scheme, e.g. `https://`.
        timeout : Optional[int]
            Maximum operation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultNavigationTimeout(timeout), browserContext.setDefaultTimeout(timeout), page.setDefaultNavigationTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        wait_until : Optional[Literal['domcontentloaded', 'load', 'networkidle']]
            When to consider operation succeeded, defaults to `load`. Events can be either:
             - `'domcontentloaded'` - consider operation to be finished when the `DOMContentLoaded` event is fired.
             - `'load'` - consider operation to be finished when the `load` event is fired.
             - `'networkidle'` - consider operation to be finished when there are no network connections for at least `500` ms.
        referer : Optional[str]
            Referer header value. If provided it will take preference over the referer header value set by page.setExtraHTTPHeaders(headers).

        Returns
        -------
        Optional[Response]
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
        timeout: int = None,
        wait_until: Literal["domcontentloaded", "load", "networkidle"] = None,
    ) -> typing.Union["Response", NoneType]:
        """Page.reload

        Returns the main resource response. In case of multiple redirects, the navigation will resolve with the response of the
        last redirect.

        Parameters
        ----------
        timeout : Optional[int]
            Maximum operation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultNavigationTimeout(timeout), browserContext.setDefaultTimeout(timeout), page.setDefaultNavigationTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        wait_until : Optional[Literal['domcontentloaded', 'load', 'networkidle']]
            When to consider operation succeeded, defaults to `load`. Events can be either:
             - `'domcontentloaded'` - consider operation to be finished when the `DOMContentLoaded` event is fired.
             - `'load'` - consider operation to be finished when the `load` event is fired.
             - `'networkidle'` - consider operation to be finished when there are no network connections for at least `500` ms.

        Returns
        -------
        Optional[Response]
        """
        return mapping.from_impl_nullable(
            self._sync(self._impl_obj.reload(timeout=timeout, waitUntil=wait_until))
        )

    def wait_for_load_state(
        self,
        state: Literal["domcontentloaded", "load", "networkidle"] = None,
        timeout: int = None,
    ) -> NoneType:
        """Page.wait_for_load_state

        Returns when the required load state has been reached.
        This resolves when the page reaches a required load state, `load` by default. The navigation must have been committed
        when this method is called. If current document has already reached the required state, resolves immediately.
        Shortcut for main frame's frame.wait_for_load_state([state, options]).

        Parameters
        ----------
        state : Optional[Literal['domcontentloaded', 'load', 'networkidle']]
            Load state to wait for, defaults to `load`. If the state has been already reached while loading current document, the method resolves immediately. Optional.
             - `'load'` - wait for the `load` event to be fired.
             - `'domcontentloaded'` - wait for the `DOMContentLoaded` event to be fired.
             - `'networkidle'` - wait until there are no network connections for at least `500` ms.
        timeout : Optional[int]
            Maximum operation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultNavigationTimeout(timeout), browserContext.setDefaultTimeout(timeout), page.setDefaultNavigationTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        """
        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.waitForLoadState(state=state, timeout=timeout))
        )

    def wait_for_navigation(
        self,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]] = None,
        wait_until: Literal["domcontentloaded", "load", "networkidle"] = None,
        timeout: int = None,
    ) -> typing.Union["Response", NoneType]:
        """Page.wait_for_navigation

        Returns the main resource response. In case of multiple redirects, the navigation will resolve with the response of the
        last redirect. In case of navigation to a different anchor or navigation due to History API usage, the navigation will
        resolve with `null`.
        This resolves when the page navigates to a new URL or reloads. It is useful for when you run code which will indirectly
        cause the page to navigate. e.g. The click target has an `onclick` handler that triggers navigation from a `setTimeout`.
        Consider this example:
        **NOTE** Usage of the History API to change the URL is
        considered a navigation.
        Shortcut for main frame's frame.wait_for_navigation([options]).

        Parameters
        ----------
        url : Union[str, Pattern, Callable[[str], bool], NoneType]
            A glob pattern, regex pattern or predicate receiving URL to match while waiting for the navigation.
        wait_until : Optional[Literal['domcontentloaded', 'load', 'networkidle']]
            When to consider operation succeeded, defaults to `load`. Events can be either:
             - `'domcontentloaded'` - consider operation to be finished when the `DOMContentLoaded` event is fired.
             - `'load'` - consider operation to be finished when the `load` event is fired.
             - `'networkidle'` - consider operation to be finished when there are no network connections for at least `500` ms.
        timeout : Optional[int]
            Maximum operation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultNavigationTimeout(timeout), browserContext.setDefaultTimeout(timeout), page.setDefaultNavigationTimeout(timeout) or page.setDefaultTimeout(timeout) methods.

        Returns
        -------
        Optional[Response]
        """
        return mapping.from_impl_nullable(
            self._sync(
                self._impl_obj.waitForNavigation(
                    url=self._wrap_handler(url), waitUntil=wait_until, timeout=timeout
                )
            )
        )

    def wait_for_request(
        self,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]] = None,
        predicate: typing.Union[typing.Callable[["Request"], bool]] = None,
        timeout: int = None,
    ) -> "Request":
        """Page.wait_for_request

        Returns promise that resolves to the matched request.

        Parameters
        ----------
        url : Union[str, Pattern, Callable[[str], bool], NoneType]
            Request URL string, regex or predicate receiving Request object.
        timeout : Optional[int]
            Maximum wait time in milliseconds, defaults to 30 seconds, pass `0` to disable the timeout. The default value can be changed by using the page.setDefaultTimeout(timeout) method.

        Returns
        -------
        Request
        """
        return mapping.from_impl(
            self._sync(
                self._impl_obj.waitForRequest(
                    url=self._wrap_handler(url),
                    predicate=self._wrap_handler(predicate),
                    timeout=timeout,
                )
            )
        )

    def wait_for_response(
        self,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]] = None,
        predicate: typing.Union[typing.Callable[["Response"], bool]] = None,
        timeout: int = None,
    ) -> "Response":
        """Page.wait_for_response

        Returns the matched response.

        Parameters
        ----------
        url : Union[str, Pattern, Callable[[str], bool], NoneType]
            Request URL string, regex or predicate receiving Response object.
        timeout : Optional[int]
            Maximum wait time in milliseconds, defaults to 30 seconds, pass `0` to disable the timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.

        Returns
        -------
        Response
        """
        return mapping.from_impl(
            self._sync(
                self._impl_obj.waitForResponse(
                    url=self._wrap_handler(url),
                    predicate=self._wrap_handler(predicate),
                    timeout=timeout,
                )
            )
        )

    def wait_for_event(
        self,
        event: str,
        predicate: typing.Union[typing.Callable[[typing.Any], bool]] = None,
        timeout: int = None,
    ) -> typing.Any:
        """Page.wait_for_event

        Returns the event data value.
        Waits for event to fire and passes its value into the predicate function. Resolves when the predicate returns truthy
        value. Will throw an error if the page is closed before the event is fired.

        Parameters
        ----------
        event : str
            Event name, same one would pass into `page.on(event)`.

        Returns
        -------
        Any
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.waitForEvent(
                    event=event,
                    predicate=self._wrap_handler(predicate),
                    timeout=timeout,
                )
            )
        )

    def go_back(
        self,
        timeout: int = None,
        wait_until: Literal["domcontentloaded", "load", "networkidle"] = None,
    ) -> typing.Union["Response", NoneType]:
        """Page.go_back

        Returns the main resource response. In case of multiple redirects, the navigation will resolve with the response of the
        last redirect. If can not go back, resolves to `null`.
        Navigate to the previous page in history.

        Parameters
        ----------
        timeout : Optional[int]
            Maximum operation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultNavigationTimeout(timeout), browserContext.setDefaultTimeout(timeout), page.setDefaultNavigationTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        wait_until : Optional[Literal['domcontentloaded', 'load', 'networkidle']]
            When to consider operation succeeded, defaults to `load`. Events can be either:
             - `'domcontentloaded'` - consider operation to be finished when the `DOMContentLoaded` event is fired.
             - `'load'` - consider operation to be finished when the `load` event is fired.
             - `'networkidle'` - consider operation to be finished when there are no network connections for at least `500` ms.

        Returns
        -------
        Optional[Response]
        """
        return mapping.from_impl_nullable(
            self._sync(self._impl_obj.goBack(timeout=timeout, waitUntil=wait_until))
        )

    def go_forward(
        self,
        timeout: int = None,
        wait_until: Literal["domcontentloaded", "load", "networkidle"] = None,
    ) -> typing.Union["Response", NoneType]:
        """Page.go_forward

        Returns the main resource response. In case of multiple redirects, the navigation will resolve with the response of the
        last redirect. If can not go forward, resolves to `null`.
        Navigate to the next page in history.

        Parameters
        ----------
        timeout : Optional[int]
            Maximum operation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultNavigationTimeout(timeout), browserContext.setDefaultTimeout(timeout), page.setDefaultNavigationTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        wait_until : Optional[Literal['domcontentloaded', 'load', 'networkidle']]
            When to consider operation succeeded, defaults to `load`. Events can be either:
             - `'domcontentloaded'` - consider operation to be finished when the `DOMContentLoaded` event is fired.
             - `'load'` - consider operation to be finished when the `load` event is fired.
             - `'networkidle'` - consider operation to be finished when there are no network connections for at least `500` ms.

        Returns
        -------
        Optional[Response]
        """
        return mapping.from_impl_nullable(
            self._sync(self._impl_obj.goForward(timeout=timeout, waitUntil=wait_until))
        )

    def emulate_media(
        self,
        media: Literal["print", "screen"] = None,
        color_scheme: Literal["dark", "light", "no-preference"] = None,
    ) -> NoneType:
        """Page.emulate_media


        Parameters
        ----------
        media : Optional[Literal['print', 'screen']]
            Changes the CSS media type of the page. The only allowed values are `'screen'`, `'print'` and `null`. Passing `null` disables CSS media emulation. Omitting `media` or passing `undefined` does not change the emulated value.
        color_scheme : Optional[Literal['dark', 'light', 'no-preference']]
            Emulates `'prefers-colors-scheme'` media feature, supported values are `'light'`, `'dark'`, `'no-preference'`. Passing `null` disables color scheme emulation. Omitting `colorScheme` or passing `undefined` does not change the emulated value.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.emulateMedia(media=media, colorScheme=color_scheme)
            )
        )

    def set_viewport_size(self, width: int, height: int) -> NoneType:
        """Page.set_viewport_size

        In the case of multiple pages in a single browser, each page can have its own viewport size. However,
        browser.new_context([options]) allows to set viewport size (and more) for all pages in the context at once.
        `page.set_viewport_size` will resize the page. A lot of websites don't expect phones to change size, so you should set the
        viewport size before navigating to the page.

        Parameters
        ----------
        width : int
            page width in pixels. **required**
        height : int
            page height in pixels. **required**
        """
        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.setViewportSize(width=width, height=height))
        )

    def viewport_size(self) -> typing.Union[typing.Tuple[int, int], NoneType]:
        """Page.viewport_size

        Returns
        -------
        Optional[typing.Tuple[int, int]]
        """
        return mapping.from_maybe_impl(self._impl_obj.viewportSize())

    def bring_to_front(self) -> NoneType:
        """Page.bring_to_front

        Brings page to front (activates tab).
        """
        return mapping.from_maybe_impl(self._sync(self._impl_obj.bringToFront()))

    def add_init_script(
        self, source: str = None, path: typing.Union[str, pathlib.Path] = None
    ) -> NoneType:
        """Page.add_init_script

        Adds a script which would be evaluated in one of the following scenarios:

        Whenever the page is navigated.
        Whenever the child frame is attached or navigated. In this case, the script is evaluated in the context of the newly attached frame.

        The script is evaluated after the document was created but before any of its scripts were run. This is useful to amend
        the JavaScript environment, e.g. to seed `Math.random`.
        An example of overriding `Math.random` before the page loads:

        **NOTE** The order of evaluation of multiple scripts installed via browser_context.add_init_script(script[, arg]) and
        page.add_init_script(script[, arg]) is not defined.

        Parameters
        ----------
        source : Optional[str]
            Script to be evaluated in the page.
        """
        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.addInitScript(source=source, path=path))
        )

    def route(
        self,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]],
        handler: typing.Union[
            typing.Callable[["Route"], typing.Any],
            typing.Callable[["Route", "Request"], typing.Any],
        ],
    ) -> NoneType:
        """Page.route

        Routing provides the capability to modify network requests that are made by a page.
        Once routing is enabled, every request matching the url pattern will stall unless it's continued, fulfilled or aborted.

        **NOTE** The handler will only be called for the first url if the response is a redirect.

        An example of a naïve handler that aborts all image requests:
        or the same snippet using a regex pattern instead:
        Page routes take precedence over browser context routes (set up with browser_context.route(url, handler)) when request matches
        both handlers.

        **NOTE** Enabling routing disables http cache.

        Parameters
        ----------
        url : Union[str, Pattern, Callable[[str], bool]]
            A glob pattern, regex pattern or predicate receiving URL to match while routing.
        handler : Union[Callable[[Route], Any], Callable[[Route, Request], Any]]
            handler function to route the request.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.route(
                    url=self._wrap_handler(url), handler=self._wrap_handler(handler)
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

        Removes a route created with page.route(url, handler). When `handler` is not specified, removes all routes for the `url`.

        Parameters
        ----------
        url : Union[str, Pattern, Callable[[str], bool]]
            A glob pattern, regex pattern or predicate receiving URL to match while routing.
        handler : Union[Callable[[Route], Any], Callable[[Route, Request], Any], NoneType]
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
        timeout: int = None,
        type: Literal["jpeg", "png"] = None,
        path: typing.Union[str, pathlib.Path] = None,
        quality: int = None,
        omit_background: bool = None,
        full_page: bool = None,
        clip: "FloatRect" = None,
    ) -> bytes:
        """Page.screenshot

        Returns the buffer with the captured screenshot.

        **NOTE** Screenshots take at least 1/6 second on Chromium OS X and Chromium Windows. See https://crbug.com/741689 for
        discussion.

        Parameters
        ----------
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        type : Optional[Literal['jpeg', 'png']]
            Specify screenshot type, defaults to `png`.
        path : Union[str, pathlib.Path, NoneType]
            The file path to save the image to. The screenshot type will be inferred from file extension. If `path` is a relative path, then it is resolved relative to current working directory. If no path is provided, the image won't be saved to the disk.
        quality : Optional[int]
            The quality of the image, between 0-100. Not applicable to `png` images.
        omit_background : Optional[bool]
            Hides default white background and allows capturing screenshots with transparency. Not applicable to `jpeg` images. Defaults to `false`.
        full_page : Optional[bool]
            When true, takes a screenshot of the full scrollable page, instead of the currently visible viewport. Defaults to `false`.
        clip : Optional[{"x": float, "y": float, "width": float, "height": float}]
            An object which specifies clipping of the resulting image. Should have the following fields:

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
                )
            )
        )

    def title(self) -> str:
        """Page.title

        Returns the page's title. Shortcut for main frame's frame.title().

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._sync(self._impl_obj.title()))

    def close(self, run_before_unload: bool = None) -> NoneType:
        """Page.close

        If `runBeforeUnload` is `false` the result will resolve only after the page has been closed. If `runBeforeUnload` is
        `true` the method will **not** wait for the page to close. By default, `page.close()` **does not** run beforeunload
        handlers.

        **NOTE** if `runBeforeUnload` is passed as true, a `beforeunload` dialog might be summoned
        and should be handled manually via page.on('dialog') event.

        Parameters
        ----------
        run_before_unload : Optional[bool]
            Defaults to `false`. Whether to run the before unload page handlers.
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
        return mapping.from_maybe_impl(self._impl_obj.isClosed())

    def click(
        self,
        selector: str,
        modifiers: typing.Union[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: typing.Union[typing.Tuple[float, float]] = None,
        delay: int = None,
        button: Literal["left", "middle", "right"] = None,
        click_count: int = None,
        timeout: int = None,
        force: bool = None,
        no_wait_after: bool = None,
    ) -> NoneType:
        """Page.click

        This method clicks an element matching `selector` by performing the following steps:

        Find an element match matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        Wait for actionability checks on the matched element, unless `force` option is set. If the element is detached during the checks, the whole action is retried.
        Scroll the element into view if needed.
        Use page.mouse to click in the center of the element, or the specified `position`.
        Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.

        When all steps combined have not finished during the specified `timeout`, this method rejects with a TimeoutError.
        Passing zero timeout disables this.
        Shortcut for main frame's frame.click(selector[, options]).

        Parameters
        ----------
        selector : str
            A selector to search for element. If there are multiple elements satisfying the selector, the first will be used. See working with selectors for more details.
        modifiers : Optional[List[Literal['Alt', 'Control', 'Meta', 'Shift']]]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores current modifiers back. If not specified, currently pressed modifiers are used.
        position : Optional[typing.Tuple[float, float]]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the element.
        delay : Optional[int]
            Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        button : Optional[Literal['left', 'middle', 'right']]
            Defaults to `left`.
        click_count : Optional[int]
            defaults to 1. See UIEvent.detail.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        force : Optional[bool]
            Whether to bypass the actionability checks. Defaults to `false`.
        no_wait_after : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.click(
                    selector=selector,
                    modifiers=modifiers,
                    position=position,
                    delay=delay,
                    button=button,
                    clickCount=click_count,
                    timeout=timeout,
                    force=force,
                    noWaitAfter=no_wait_after,
                )
            )
        )

    def dblclick(
        self,
        selector: str,
        modifiers: typing.Union[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: typing.Union[typing.Tuple[float, float]] = None,
        delay: int = None,
        button: Literal["left", "middle", "right"] = None,
        timeout: int = None,
        force: bool = None,
        no_wait_after: bool = None,
    ) -> NoneType:
        """Page.dblclick

        This method double clicks an element matching `selector` by performing the following steps:

        Find an element match matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        Wait for actionability checks on the matched element, unless `force` option is set. If the element is detached during the checks, the whole action is retried.
        Scroll the element into view if needed.
        Use page.mouse to double click in the center of the element, or the specified `position`.
        Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set. Note that if the first click of the `dblclick()` triggers a navigation event, this method will reject.

        When all steps combined have not finished during the specified `timeout`, this method rejects with a TimeoutError.
        Passing zero timeout disables this.

        **NOTE** `page.dblclick()` dispatches two `click` events and a single `dblclick` event.

        Shortcut for main frame's frame.dblclick(selector[, options]).

        Parameters
        ----------
        selector : str
            A selector to search for element. If there are multiple elements satisfying the selector, the first will be used. See working with selectors for more details.
        modifiers : Optional[List[Literal['Alt', 'Control', 'Meta', 'Shift']]]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores current modifiers back. If not specified, currently pressed modifiers are used.
        position : Optional[typing.Tuple[float, float]]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the element.
        delay : Optional[int]
            Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        button : Optional[Literal['left', 'middle', 'right']]
            Defaults to `left`.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        force : Optional[bool]
            Whether to bypass the actionability checks. Defaults to `false`.
        no_wait_after : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.dblclick(
                    selector=selector,
                    modifiers=modifiers,
                    position=position,
                    delay=delay,
                    button=button,
                    timeout=timeout,
                    force=force,
                    noWaitAfter=no_wait_after,
                )
            )
        )

    def tap(
        self,
        selector: str,
        modifiers: typing.Union[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: typing.Union[typing.Tuple[float, float]] = None,
        timeout: int = None,
        force: bool = None,
        no_wait_after: bool = None,
    ) -> NoneType:
        """Page.tap

        This method taps an element matching `selector` by performing the following steps:

        Find an element match matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        Wait for actionability checks on the matched element, unless `force` option is set. If the element is detached during the checks, the whole action is retried.
        Scroll the element into view if needed.
        Use page.touchscreen to tap the center of the element, or the specified `position`.
        Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.

        When all steps combined have not finished during the specified `timeout`, this method rejects with a TimeoutError.
        Passing zero timeout disables this.

        **NOTE** `page.tap()` requires that the `hasTouch` option of the browser context be set to true.

        Shortcut for main frame's frame.tap(selector[, options]).

        Parameters
        ----------
        selector : str
            A selector to search for element. If there are multiple elements satisfying the selector, the first will be used. See working with selectors for more details.
        modifiers : Optional[List[Literal['Alt', 'Control', 'Meta', 'Shift']]]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores current modifiers back. If not specified, currently pressed modifiers are used.
        position : Optional[typing.Tuple[float, float]]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the element.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        force : Optional[bool]
            Whether to bypass the actionability checks. Defaults to `false`.
        no_wait_after : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.tap(
                    selector=selector,
                    modifiers=modifiers,
                    position=position,
                    timeout=timeout,
                    force=force,
                    noWaitAfter=no_wait_after,
                )
            )
        )

    def fill(
        self, selector: str, value: str, timeout: int = None, no_wait_after: bool = None
    ) -> NoneType:
        """Page.fill

        This method waits for an element matching `selector`, waits for actionability checks, focuses the
        element, fills it and triggers an `input` event after filling. If the element matching `selector` is not an `<input>`,
        `<textarea>` or `[contenteditable]` element, this method throws an error. Note that you can pass an empty string to
        clear the input field.
        To send fine-grained keyboard events, use page.type(selector, text[, options]).
        Shortcut for main frame's frame.fill(selector, value[, options])

        Parameters
        ----------
        selector : str
            A selector to search for element. If there are multiple elements satisfying the selector, the first will be used. See working with selectors for more details.
        value : str
            Value to fill for the `<input>`, `<textarea>` or `[contenteditable]` element.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        no_wait_after : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.fill(
                    selector=selector,
                    value=value,
                    timeout=timeout,
                    noWaitAfter=no_wait_after,
                )
            )
        )

    def focus(self, selector: str, timeout: int = None) -> NoneType:
        """Page.focus

        This method fetches an element with `selector` and focuses it. If there's no element matching `selector`, the method
        waits until a matching element appears in the DOM.
        Shortcut for main frame's frame.focus(selector[, options]).

        Parameters
        ----------
        selector : str
            A selector to search for element. If there are multiple elements satisfying the selector, the first will be used. See working with selectors for more details.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        """
        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.focus(selector=selector, timeout=timeout))
        )

    def text_content(
        self, selector: str, timeout: int = None
    ) -> typing.Union[str, NoneType]:
        """Page.text_content

        Returns `element.textContent`.

        Parameters
        ----------
        selector : str
            A selector to search for element. If there are multiple elements satisfying the selector, the first will be used. See working with selectors for more details.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.

        Returns
        -------
        Optional[str]
        """
        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.textContent(selector=selector, timeout=timeout))
        )

    def inner_text(self, selector: str, timeout: int = None) -> str:
        """Page.inner_text

        Returns `element.innerText`.

        Parameters
        ----------
        selector : str
            A selector to search for element. If there are multiple elements satisfying the selector, the first will be used. See working with selectors for more details.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.innerText(selector=selector, timeout=timeout))
        )

    def inner_html(self, selector: str, timeout: int = None) -> str:
        """Page.inner_html

        Returns `element.innerHTML`.

        Parameters
        ----------
        selector : str
            A selector to search for element. If there are multiple elements satisfying the selector, the first will be used. See working with selectors for more details.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.innerHTML(selector=selector, timeout=timeout))
        )

    def get_attribute(
        self, selector: str, name: str, timeout: int = None
    ) -> typing.Union[str, NoneType]:
        """Page.get_attribute

        Returns element attribute value.

        Parameters
        ----------
        selector : str
            A selector to search for element. If there are multiple elements satisfying the selector, the first will be used. See working with selectors for more details.
        name : str
            Attribute name to get the value for.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.

        Returns
        -------
        Optional[str]
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.getAttribute(
                    selector=selector, name=name, timeout=timeout
                )
            )
        )

    def hover(
        self,
        selector: str,
        modifiers: typing.Union[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: typing.Union[typing.Tuple[float, float]] = None,
        timeout: int = None,
        force: bool = None,
    ) -> NoneType:
        """Page.hover

        This method hovers over an element matching `selector` by performing the following steps:

        Find an element match matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        Wait for actionability checks on the matched element, unless `force` option is set. If the element is detached during the checks, the whole action is retried.
        Scroll the element into view if needed.
        Use page.mouse to hover over the center of the element, or the specified `position`.
        Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.

        When all steps combined have not finished during the specified `timeout`, this method rejects with a TimeoutError.
        Passing zero timeout disables this.
        Shortcut for main frame's frame.hover(selector[, options]).

        Parameters
        ----------
        selector : str
            A selector to search for element. If there are multiple elements satisfying the selector, the first will be used. See working with selectors for more details.
        modifiers : Optional[List[Literal['Alt', 'Control', 'Meta', 'Shift']]]
            Modifier keys to press. Ensures that only these modifiers are pressed during the operation, and then restores current modifiers back. If not specified, currently pressed modifiers are used.
        position : Optional[typing.Tuple[float, float]]
            A point to use relative to the top-left corner of element padding box. If not specified, uses some visible point of the element.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        force : Optional[bool]
            Whether to bypass the actionability checks. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.hover(
                    selector=selector,
                    modifiers=modifiers,
                    position=position,
                    timeout=timeout,
                    force=force,
                )
            )
        )

    def select_option(
        self,
        selector: str,
        value: typing.Union[str, typing.List[str]] = None,
        index: typing.Union[int, typing.List[int]] = None,
        label: typing.Union[str, typing.List[str]] = None,
        element: typing.Union["ElementHandle", typing.List["ElementHandle"]] = None,
        timeout: int = None,
        no_wait_after: bool = None,
    ) -> typing.List[str]:
        """Page.select_option

        Returns the array of option values that have been successfully selected.
        Triggers a `change` and `input` event once all the provided options have been selected. If there's no `<select>` element
        matching `selector`, the method throws an error.

        Shortcut for main frame's frame.select_option(selector, values[, options])

        Parameters
        ----------
        selector : str
            A selector to search for element. If there are multiple elements satisfying the selector, the first will be used. See working with selectors for more details.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        no_wait_after : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.

        Returns
        -------
        List[str]
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.selectOption(
                    selector=selector,
                    value=value,
                    index=index,
                    label=label,
                    element=mapping.to_impl(element),
                    timeout=timeout,
                    noWaitAfter=no_wait_after,
                )
            )
        )

    def set_input_files(
        self,
        selector: str,
        files: typing.Union[
            str, "FilePayload", typing.List[str], typing.List["FilePayload"]
        ],
        timeout: int = None,
        no_wait_after: bool = None,
    ) -> NoneType:
        """Page.set_input_files

        This method expects `selector` to point to an input
        element.
        Sets the value of the file input to these file paths or files. If some of the `filePaths` are relative paths, then they
        are resolved relative to the current working directory. For
        empty array, clears the selected files.

        Parameters
        ----------
        selector : str
            A selector to search for element. If there are multiple elements satisfying the selector, the first will be used. See working with selectors for more details.
        files : Union[str, Dict, List[str], List[Dict]]
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        no_wait_after : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.setInputFiles(
                    selector=selector,
                    files=files,
                    timeout=timeout,
                    noWaitAfter=no_wait_after,
                )
            )
        )

    def type(
        self,
        selector: str,
        text: str,
        delay: int = None,
        timeout: int = None,
        no_wait_after: bool = None,
    ) -> NoneType:
        """Page.type

        Sends a `keydown`, `keypress`/`input`, and `keyup` event for each character in the text. `page.type` can be used to send
        fine-grained keyboard events. To fill values in form fields, use page.fill(selector, value[, options]).
        To press a special key, like `Control` or `ArrowDown`, use keyboard.press(key[, options]).
        Shortcut for main frame's frame.type(selector, text[, options]).

        Parameters
        ----------
        selector : str
            A selector to search for element. If there are multiple elements satisfying the selector, the first will be used. See working with selectors for more details.
        text : str
            A text to type into a focused element.
        delay : Optional[int]
            Time to wait between key presses in milliseconds. Defaults to 0.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        no_wait_after : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.type(
                    selector=selector,
                    text=text,
                    delay=delay,
                    timeout=timeout,
                    noWaitAfter=no_wait_after,
                )
            )
        )

    def press(
        self,
        selector: str,
        key: str,
        delay: int = None,
        timeout: int = None,
        no_wait_after: bool = None,
    ) -> NoneType:
        """Page.press

        Focuses the element, and then uses keyboard.down(key) and keyboard.up(key).
        `key` can specify the intended keyboardEvent.key
        value or a single character to generate the text for. A superset of the `key` values can be found
        here. Examples of the keys are:
        `F1` - `F12`, `Digit0`- `Digit9`, `KeyA`- `KeyZ`, `Backquote`, `Minus`, `Equal`, `Backslash`, `Backspace`, `Tab`,
        `Delete`, `Escape`, `ArrowDown`, `End`, `Enter`, `Home`, `Insert`, `PageDown`, `PageUp`, `ArrowRight`, `ArrowUp`, etc.
        Following modification shortcuts are also suported: `Shift`, `Control`, `Alt`, `Meta`, `ShiftLeft`.
        Holding down `Shift` will type the text that corresponds to the `key` in the upper case.
        If `key` is a single character, it is case-sensitive, so the values `a` and `A` will generate different respective
        texts.
        Shortcuts such as `key: "Control+o"` or `key: "Control+Shift+T"` are supported as well. When speficied with the
        modifier, modifier is pressed and being held while the subsequent key is being pressed.

        Parameters
        ----------
        selector : str
            A selector to search for element. If there are multiple elements satisfying the selector, the first will be used. See working with selectors for more details.
        key : str
            Name of the key to press or a character to generate, such as `ArrowLeft` or `a`.
        delay : Optional[int]
            Time to wait between `keydown` and `keyup` in milliseconds. Defaults to 0.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        no_wait_after : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.press(
                    selector=selector,
                    key=key,
                    delay=delay,
                    timeout=timeout,
                    noWaitAfter=no_wait_after,
                )
            )
        )

    def check(
        self,
        selector: str,
        timeout: int = None,
        force: bool = None,
        no_wait_after: bool = None,
    ) -> NoneType:
        """Page.check

        This method checks an element matching `selector` by performing the following steps:

        Find an element match matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        Ensure that matched element is a checkbox or a radio input. If not, this method rejects. If the element is already checked, this method returns immediately.
        Wait for actionability checks on the matched element, unless `force` option is set. If the element is detached during the checks, the whole action is retried.
        Scroll the element into view if needed.
        Use page.mouse to click in the center of the element.
        Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.
        Ensure that the element is now checked. If not, this method rejects.

        When all steps combined have not finished during the specified `timeout`, this method rejects with a TimeoutError.
        Passing zero timeout disables this.
        Shortcut for main frame's frame.check(selector[, options]).

        Parameters
        ----------
        selector : str
            A selector to search for element. If there are multiple elements satisfying the selector, the first will be used. See working with selectors for more details.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        force : Optional[bool]
            Whether to bypass the actionability checks. Defaults to `false`.
        no_wait_after : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.check(
                    selector=selector,
                    timeout=timeout,
                    force=force,
                    noWaitAfter=no_wait_after,
                )
            )
        )

    def uncheck(
        self,
        selector: str,
        timeout: int = None,
        force: bool = None,
        no_wait_after: bool = None,
    ) -> NoneType:
        """Page.uncheck

        This method unchecks an element matching `selector` by performing the following steps:

        Find an element match matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        Ensure that matched element is a checkbox or a radio input. If not, this method rejects. If the element is already unchecked, this method returns immediately.
        Wait for actionability checks on the matched element, unless `force` option is set. If the element is detached during the checks, the whole action is retried.
        Scroll the element into view if needed.
        Use page.mouse to click in the center of the element.
        Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.
        Ensure that the element is now unchecked. If not, this method rejects.

        When all steps combined have not finished during the specified `timeout`, this method rejects with a TimeoutError.
        Passing zero timeout disables this.
        Shortcut for main frame's frame.uncheck(selector[, options]).

        Parameters
        ----------
        selector : str
            A selector to search for element. If there are multiple elements satisfying the selector, the first will be used. See working with selectors for more details.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        force : Optional[bool]
            Whether to bypass the actionability checks. Defaults to `false`.
        no_wait_after : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.uncheck(
                    selector=selector,
                    timeout=timeout,
                    force=force,
                    noWaitAfter=no_wait_after,
                )
            )
        )

    def wait_for_timeout(self, timeout: int) -> NoneType:
        """Page.wait_for_timeout

        Returns a promise that resolves after the timeout.
        Note that `page.wait_for_timeout()` should only be used for debugging. Tests using the timer in production are going to be
        flaky. Use signals such as network events, selectors becoming visible and others instead.
        Shortcut for main frame's frame.wait_for_timeout(timeout).

        Parameters
        ----------
        timeout : int
            A timeout to wait for
        """
        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.waitForTimeout(timeout=timeout))
        )

    def wait_for_function(
        self,
        expression: str,
        arg: typing.Any = None,
        force_expr: bool = None,
        timeout: int = None,
        polling: typing.Union[int, Literal["raf"]] = None,
    ) -> "JSHandle":
        """Page.wait_for_function

        Returns when the `pageFunction` returns a truthy value. It resolves to a JSHandle of the truthy value.
        The `waitForFunction` can be used to observe viewport size change:

        To pass an argument from Node.js to the predicate of `page.wait_for_function` function:
        Shortcut for main frame's frame.wait_for_function(pageFunction[, arg, options]).

        Parameters
        ----------
        expression : str
            Function to be evaluated in browser context
        force_expr : bool
            Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        arg : Optional[Any]
            Optional argument to pass to `pageFunction`
        timeout : Optional[int]
            maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout).
        polling : Union[int, 'raf', NoneType]
            If `polling` is `'raf'`, then `pageFunction` is constantly executed in `requestAnimationFrame` callback. If `polling` is a number, then it is treated as an interval in milliseconds at which the function would be executed. Defaults to `raf`.

        Returns
        -------
        JSHandle
        """
        return mapping.from_impl(
            self._sync(
                self._impl_obj.waitForFunction(
                    expression=expression,
                    arg=mapping.to_impl(arg),
                    force_expr=force_expr,
                    timeout=timeout,
                    polling=polling,
                )
            )
        )

    def pdf(
        self,
        scale: int = None,
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
        margin: "PdfMargins" = None,
        path: typing.Union[str, pathlib.Path] = None,
    ) -> bytes:
        """Page.pdf

        Returns the PDF buffer.

        **NOTE** Generating a pdf is currently only supported in Chromium headless.

        `page.pdf()` generates a pdf of the page with `print` css media. To generate a pdf with `screen` media, call
        page.emulate_media(params) before calling `page.pdf()`:

        **NOTE** By default, `page.pdf()` generates a pdf with modified colors for printing. Use the
        `-webkit-print-color-adjust` property to
        force rendering of exact colors.

        The `width`, `height`, and `margin` options accept values labeled with units. Unlabeled values are treated as pixels.
        A few examples:

        `page.pdf({width: 100})` - prints with width set to 100 pixels
        `page.pdf({width: '100px'})` - prints with width set to 100 pixels
        `page.pdf({width: '10cm'})` - prints with width set to 10 centimeters.

        All possible units are:

        `px` - pixel
        `in` - inch
        `cm` - centimeter
        `mm` - millimeter

        The `format` options are:

        `Letter`: 8.5in x 11in
        `Legal`: 8.5in x 14in
        `Tabloid`: 11in x 17in
        `Ledger`: 17in x 11in
        `A0`: 33.1in x 46.8in
        `A1`: 23.4in x 33.1in
        `A2`: 16.54in x 23.4in
        `A3`: 11.7in x 16.54in
        `A4`: 8.27in x 11.7in
        `A5`: 5.83in x 8.27in
        `A6`: 4.13in x 5.83in

        **NOTE** `headerTemplate` and `footerTemplate` markup have the following limitations:

        Script tags inside templates are not evaluated.
        Page styles are not visible inside templates.

        Parameters
        ----------
        scale : Optional[int]
            Scale of the webpage rendering. Defaults to `1`. Scale amount must be between 0.1 and 2.
        display_header_footer : Optional[bool]
            Display header and footer. Defaults to `false`.
        header_template : Optional[str]
            HTML template for the print header. Should be valid HTML markup with following classes used to inject printing values into them:
             - `'date'` formatted print date
             - `'title'` document title
             - `'url'` document location
             - `'pageNumber'` current page number
             - `'totalPages'` total pages in the document
        footer_template : Optional[str]
            HTML template for the print footer. Should use the same format as the `headerTemplate`.
        print_background : Optional[bool]
            Print background graphics. Defaults to `false`.
        landscape : Optional[bool]
            Paper orientation. Defaults to `false`.
        page_ranges : Optional[str]
            Paper ranges to print, e.g., '1-5, 8, 11-13'. Defaults to the empty string, which means print all pages.
        format : Optional[str]
            Paper format. If set, takes priority over `width` or `height` options. Defaults to 'Letter'.
        width : Union[str, float, NoneType]
            Paper width, accepts values labeled with units.
        height : Union[str, float, NoneType]
            Paper height, accepts values labeled with units.
        prefer_css_page_size : Optional[bool]
            Give any CSS `@page` size declared in the page priority over what is declared in `width` and `height` or `format` options. Defaults to `false`, which will scale the content to fit the paper size.
        margin : Optional[{"top": Union[str, int, NoneType], "right": Union[str, int, NoneType], "bottom": Union[str, int, NoneType], "left": Union[str, int, NoneType]}]
            Paper margins, defaults to none.
        path : Union[str, pathlib.Path, NoneType]
            The file path to save the PDF to. If `path` is a relative path, then it is resolved relative to current working directory. If no path is provided, the PDF won't be saved to the disk.

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
        self,
        event: str,
        predicate: typing.Union[typing.Callable[[typing.Any], bool]] = None,
        timeout: int = None,
    ) -> EventContextManager:
        """Page.expect_event

        Returns context manager that waits for ``event`` to fire upon exit. It passes event's value
        into the ``predicate`` function and waits for the predicate to return a truthy value. Will throw
        an error if the page is closed before the ``event`` is fired.

        with page.expect_event() as event_info:
            page.click("button")
        value = event_info.value

        Parameters
        ----------
        predicate : Optional[typing.Callable[[Any], bool]]
            Predicate receiving event data.
        timeout : Optional[int]
            Maximum wait time in milliseconds, defaults to 30 seconds, pass `0` to disable the timeout.
            The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or
            page.setDefaultTimeout(timeout) methods.
        """
        return EventContextManager(
            self, self._impl_obj.waitForEvent(event, predicate, timeout)
        )

    def expect_console_message(
        self,
        predicate: typing.Union[typing.Callable[["ConsoleMessage"], bool]] = None,
        timeout: int = None,
    ) -> EventContextManager["ConsoleMessage"]:
        """Page.expect_console_message

        Returns context manager that waits for ``event`` to fire upon exit. It passes event's value
        into the ``predicate`` function and waits for the predicate to return a truthy value. Will throw
        an error if the page is closed before the ``event`` is fired.

        with page.expect_console() as event_info:
            page.click("button")
        value = event_info.value

        Parameters
        ----------
        predicate : Optional[typing.Callable[[Any], bool]]
            Predicate receiving event data.
        timeout : Optional[int]
            Maximum wait time in milliseconds, defaults to 30 seconds, pass `0` to disable the timeout.
            The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or
            page.setDefaultTimeout(timeout) methods.
        """
        event = "console"
        return EventContextManager(
            self, self._impl_obj.waitForEvent(event, predicate, timeout)
        )

    def expect_download(
        self,
        predicate: typing.Union[typing.Callable[["Download"], bool]] = None,
        timeout: int = None,
    ) -> EventContextManager["Download"]:
        """Page.expect_download

        Returns context manager that waits for ``event`` to fire upon exit. It passes event's value
        into the ``predicate`` function and waits for the predicate to return a truthy value. Will throw
        an error if the page is closed before the ``event`` is fired.

        with page.expect_download() as event_info:
            page.click("button")
        value = event_info.value

        Parameters
        ----------
        predicate : Optional[typing.Callable[[Any], bool]]
            Predicate receiving event data.
        timeout : Optional[int]
            Maximum wait time in milliseconds, defaults to 30 seconds, pass `0` to disable the timeout.
            The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or
            page.setDefaultTimeout(timeout) methods.
        """
        event = "download"
        return EventContextManager(
            self, self._impl_obj.waitForEvent(event, predicate, timeout)
        )

    def expect_file_chooser(
        self,
        predicate: typing.Union[typing.Callable[["FileChooser"], bool]] = None,
        timeout: int = None,
    ) -> EventContextManager["FileChooser"]:
        """Page.expect_file_chooser

        Returns context manager that waits for ``event`` to fire upon exit. It passes event's value
        into the ``predicate`` function and waits for the predicate to return a truthy value. Will throw
        an error if the page is closed before the ``event`` is fired.

        with page.expect_filechooser() as event_info:
            page.click("button")
        value = event_info.value

        Parameters
        ----------
        predicate : Optional[typing.Callable[[Any], bool]]
            Predicate receiving event data.
        timeout : Optional[int]
            Maximum wait time in milliseconds, defaults to 30 seconds, pass `0` to disable the timeout.
            The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or
            page.setDefaultTimeout(timeout) methods.
        """
        event = "filechooser"
        return EventContextManager(
            self, self._impl_obj.waitForEvent(event, predicate, timeout)
        )

    def expect_load_state(
        self,
        state: Literal["domcontentloaded", "load", "networkidle"] = None,
        timeout: int = None,
    ) -> EventContextManager[typing.Union["Response", NoneType]]:
        """Page.expect_load_state

        Returns context manager that waits for ``event`` to fire upon exit. It passes event's value
        into the ``predicate`` function and waits for the predicate to return a truthy value. Will throw
        an error if the page is closed before the ``event`` is fired.

        with page.expect_loadstate() as event_info:
            page.click("button")
        value = event_info.value

        Parameters
        ----------
        predicate : Optional[typing.Callable[[Any], bool]]
            Predicate receiving event data.
        timeout : Optional[int]
            Maximum wait time in milliseconds, defaults to 30 seconds, pass `0` to disable the timeout.
            The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or
            page.setDefaultTimeout(timeout) methods.
        """
        return EventContextManager(
            self, self._impl_obj.waitForLoadState(state, timeout)
        )

    def expect_navigation(
        self,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]] = None,
        wait_until: Literal["domcontentloaded", "load", "networkidle"] = None,
        timeout: int = None,
    ) -> EventContextManager[typing.Union["Response", NoneType]]:
        """Page.expect_navigation

        Returns context manager that waits for ``event`` to fire upon exit. It passes event's value
        into the ``predicate`` function and waits for the predicate to return a truthy value. Will throw
        an error if the page is closed before the ``event`` is fired.

        with page.expect_navigation() as event_info:
            page.click("button")
        value = event_info.value

        Parameters
        ----------
        predicate : Optional[typing.Callable[[Any], bool]]
            Predicate receiving event data.
        timeout : Optional[int]
            Maximum wait time in milliseconds, defaults to 30 seconds, pass `0` to disable the timeout.
            The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or
            page.setDefaultTimeout(timeout) methods.
        """
        return EventContextManager(
            self, self._impl_obj.waitForNavigation(url, wait_until, timeout)
        )

    def expect_popup(
        self,
        predicate: typing.Union[typing.Callable[["Page"], bool]] = None,
        timeout: int = None,
    ) -> EventContextManager["Page"]:
        """Page.expect_popup

        Returns context manager that waits for ``event`` to fire upon exit. It passes event's value
        into the ``predicate`` function and waits for the predicate to return a truthy value. Will throw
        an error if the page is closed before the ``event`` is fired.

        with page.expect_popup() as event_info:
            page.click("button")
        value = event_info.value

        Parameters
        ----------
        predicate : Optional[typing.Callable[[Any], bool]]
            Predicate receiving event data.
        timeout : Optional[int]
            Maximum wait time in milliseconds, defaults to 30 seconds, pass `0` to disable the timeout.
            The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or
            page.setDefaultTimeout(timeout) methods.
        """
        event = "popup"
        return EventContextManager(
            self, self._impl_obj.waitForEvent(event, predicate, timeout)
        )

    def expect_request(
        self,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]] = None,
        predicate: typing.Union[typing.Callable[["Request"], bool]] = None,
        timeout: int = None,
    ) -> EventContextManager["Request"]:
        """Page.expect_request

        Returns context manager that waits for ``event`` to fire upon exit. It passes event's value
        into the ``predicate`` function and waits for the predicate to return a truthy value. Will throw
        an error if the page is closed before the ``event`` is fired.

        with page.expect_request() as event_info:
            page.click("button")
        value = event_info.value

        Parameters
        ----------
        predicate : Optional[typing.Callable[[Any], bool]]
            Predicate receiving event data.
        timeout : Optional[int]
            Maximum wait time in milliseconds, defaults to 30 seconds, pass `0` to disable the timeout.
            The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or
            page.setDefaultTimeout(timeout) methods.
        """
        return EventContextManager(
            self, self._impl_obj.waitForRequest(url, predicate, timeout)
        )

    def expect_response(
        self,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]] = None,
        predicate: typing.Union[typing.Callable[["Request"], bool]] = None,
        timeout: int = None,
    ) -> EventContextManager["Response"]:
        """Page.expect_response

        Returns context manager that waits for ``event`` to fire upon exit. It passes event's value
        into the ``predicate`` function and waits for the predicate to return a truthy value. Will throw
        an error if the page is closed before the ``event`` is fired.

        with page.expect_response() as event_info:
            page.click("button")
        value = event_info.value

        Parameters
        ----------
        predicate : Optional[typing.Callable[[Any], bool]]
            Predicate receiving event data.
        timeout : Optional[int]
            Maximum wait time in milliseconds, defaults to 30 seconds, pass `0` to disable the timeout.
            The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or
            page.setDefaultTimeout(timeout) methods.
        """
        return EventContextManager(
            self, self._impl_obj.waitForResponse(url, predicate, timeout)
        )

    def expect_worker(
        self,
        predicate: typing.Union[typing.Callable[["Worker"], bool]] = None,
        timeout: int = None,
    ) -> EventContextManager["Worker"]:
        """Page.expect_worker

        Returns context manager that waits for ``event`` to fire upon exit. It passes event's value
        into the ``predicate`` function and waits for the predicate to return a truthy value. Will throw
        an error if the page is closed before the ``event`` is fired.

        with page.expect_worker() as event_info:
            page.click("button")
        value = event_info.value

        Parameters
        ----------
        predicate : Optional[typing.Callable[[Any], bool]]
            Predicate receiving event data.
        timeout : Optional[int]
            Maximum wait time in milliseconds, defaults to 30 seconds, pass `0` to disable the timeout.
            The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or
            page.setDefaultTimeout(timeout) methods.
        """
        event = "worker"
        return EventContextManager(
            self, self._impl_obj.waitForEvent(event, predicate, timeout)
        )


mapping.register(PageImpl, Page)


class BrowserContext(SyncBase):
    def __init__(self, obj: BrowserContextImpl):
        super().__init__(obj)

    @property
    def pages(self) -> typing.List["Page"]:
        """BrowserContext.pages

        Returns all open pages in the context. Non visible pages, such as `"background_page"`, will not be listed here. You can
        find them using chromium_browser_context.background_pages().

        Returns
        -------
        List[Page]
        """
        return mapping.from_impl_list(self._impl_obj.pages)

    @property
    def browser(self) -> typing.Union["Browser", NoneType]:
        """BrowserContext.browser

        Returns the browser instance of the context. If it was launched as a persistent context null gets returned.

        Returns
        -------
        Optional[Browser]
        """
        return mapping.from_impl_nullable(self._impl_obj.browser)

    def set_default_navigation_timeout(self, timeout: int) -> NoneType:
        """BrowserContext.set_default_navigation_timeout

        This setting will change the default maximum navigation time for the following methods and related shortcuts:

        page.go_back([options])
        page.go_forward([options])
        page.goto(url[, options])
        page.reload([options])
        page.set_content(html[, options])
        page.wait_for_navigation([options])

        **NOTE** page.set_default_navigation_timeout(timeout) and page.set_default_timeout(timeout) take priority over
        browser_context.set_default_navigation_timeout(timeout).

        Parameters
        ----------
        timeout : int
            Maximum navigation time in milliseconds
        """
        return mapping.from_maybe_impl(
            self._impl_obj.setDefaultNavigationTimeout(timeout=timeout)
        )

    def set_default_timeout(self, timeout: int) -> NoneType:
        """BrowserContext.set_default_timeout

        This setting will change the default maximum time for all the methods accepting `timeout` option.

        **NOTE** page.set_default_navigation_timeout(timeout), page.set_default_timeout(timeout) and
        browser_context.set_default_navigation_timeout(timeout) take priority over browser_context.set_default_timeout(timeout).

        Parameters
        ----------
        timeout : int
            Maximum time in milliseconds
        """
        return mapping.from_maybe_impl(
            self._impl_obj.setDefaultTimeout(timeout=timeout)
        )

    def new_page(self) -> "Page":
        """BrowserContext.new_page

        Creates a new page in the browser context.

        Returns
        -------
        Page
        """
        return mapping.from_impl(self._sync(self._impl_obj.newPage()))

    def cookies(
        self, urls: typing.Union[str, typing.List[str]] = None
    ) -> typing.List["Cookie"]:
        """BrowserContext.cookies

        If no URLs are specified, this method returns all cookies. If URLs are specified, only cookies that affect those URLs
        are returned.

        Parameters
        ----------
        urls : Union[str, List[str], NoneType]
            Optional list of URLs.

        Returns
        -------
        List[{"name": str, "value": str, "url": Optional[str], "domain": Optional[str], "path": Optional[str], "expires": Optional[int], "httpOnly": Optional[bool], "secure": Optional[bool], "sameSite": Optional[Literal['Strict', 'Lax', 'None']]}]
        """
        return mapping.from_impl_list(self._sync(self._impl_obj.cookies(urls=urls)))

    def add_cookies(self, cookies: typing.List["Cookie"]) -> NoneType:
        """BrowserContext.add_cookies

        Adds cookies into this browser context. All pages within this context will have these cookies installed. Cookies can be
        obtained via browser_context.cookies([urls]).

        Parameters
        ----------
        cookies : List[{"name": str, "value": str, "url": Optional[str], "domain": Optional[str], "path": Optional[str], "expires": Optional[int], "httpOnly": Optional[bool], "secure": Optional[bool], "sameSite": Optional[Literal['Strict', 'Lax', 'None']]}]
        """
        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.addCookies(cookies=cookies))
        )

    def clear_cookies(self) -> NoneType:
        """BrowserContext.clear_cookies

        Clears context cookies.
        """
        return mapping.from_maybe_impl(self._sync(self._impl_obj.clearCookies()))

    def grant_permissions(
        self, permissions: typing.List[str], origin: str = None
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
             - `'push'`
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
        origin : Optional[str]
            The origin to grant permissions to, e.g. "https://example.com".
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.grantPermissions(permissions=permissions, origin=origin)
            )
        )

    def clear_permissions(self) -> NoneType:
        """BrowserContext.clear_permissions

        Clears all permission overrides for the browser context.
        """
        return mapping.from_maybe_impl(self._sync(self._impl_obj.clearPermissions()))

    def set_geolocation(
        self, latitude: float, longitude: float, accuracy: float = None
    ) -> NoneType:
        """BrowserContext.set_geolocation

        Sets the context's geolocation. Passing `null` or `undefined` emulates position unavailable.

        **NOTE** Consider using browser_context.grant_permissions(permissions[, options]) to grant permissions for the browser context pages to
        read its geolocation.

        Parameters
        ----------
        latitude : float
            Latitude between -90 and 90. **required**
        longitude : float
            Longitude between -180 and 180. **required**
        accuracy : Optional[float]
            Non-negative accuracy value. Defaults to `0`.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.setGeolocation(
                    latitude=latitude, longitude=longitude, accuracy=accuracy
                )
            )
        )

    def reset_geolocation(self) -> NoneType:
        return mapping.from_maybe_impl(self._sync(self._impl_obj.resetGeolocation()))

    def set_extra_http_headers(self, headers: typing.Dict[str, str]) -> NoneType:
        """BrowserContext.set_extra_http_headers

        The extra HTTP headers will be sent with every request initiated by any page in the context. These headers are merged
        with page-specific extra HTTP headers set with page.set_extra_http_headers(headers). If page overrides a particular header,
        page-specific header value will be used instead of the browser context header value.

        **NOTE** `browser_context.set_extra_http_headers` does not guarantee the order of headers in the outgoing requests.

        Parameters
        ----------
        headers : Dict[str, str]
            An object containing additional HTTP headers to be sent with every request. All header values must be strings.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.setExtraHTTPHeaders(headers=mapping.to_impl(headers))
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
            self._sync(self._impl_obj.setOffline(offline=offline))
        )

    def add_init_script(
        self, source: str = None, path: typing.Union[str, pathlib.Path] = None
    ) -> NoneType:
        """BrowserContext.add_init_script

        Adds a script which would be evaluated in one of the following scenarios:

        Whenever a page is created in the browser context or is navigated.
        Whenever a child frame is attached or navigated in any page in the browser context. In this case, the script is evaluated in the context of the newly attached frame.

        The script is evaluated after the document was created but before any of its scripts were run. This is useful to amend
        the JavaScript environment, e.g. to seed `Math.random`.
        An example of overriding `Math.random` before the page loads:

        **NOTE** The order of evaluation of multiple scripts installed via browser_context.add_init_script(script[, arg]) and
        page.add_init_script(script[, arg]) is not defined.

        Parameters
        ----------
        source : Optional[str]
            Script to be evaluated in all pages in the browser context.
        """
        return mapping.from_maybe_impl(
            self._sync(self._impl_obj.addInitScript(source=source, path=path))
        )

    def expose_binding(
        self, name: str, binding: typing.Callable, handle: bool = None
    ) -> NoneType:
        """BrowserContext.expose_binding

        The method adds a function called `name` on the `window` object of every frame in every page in the context. When
        called, the function executes `playwrightBinding` in Node.js and returns a Promise which resolves to the return value
        of `playwrightBinding`. If the `playwrightBinding` returns a Promise, it will be awaited.
        The first argument of the `playwrightBinding` function contains information about the caller: `{ browserContext: BrowserContext, page: Page, frame: Frame }`.
        See page.expose_binding(name, playwrightBinding[, options]) for page-only version.
        An example of exposing page URL to all frames in all pages in the context:

        An example of passing an element handle:

        Parameters
        ----------
        name : str
            Name of the function on the window object.
        binding : Callable
            Callback function that will be called in the Playwright's context.
        handle : Optional[bool]
            Whether to pass the argument as a handle, instead of passing by value. When passing a handle, only one argument is supported. When passing by value, multiple arguments are supported.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.exposeBinding(
                    name=name, binding=self._wrap_handler(binding), handle=handle
                )
            )
        )

    def expose_function(self, name: str, binding: typing.Callable) -> NoneType:
        """BrowserContext.expose_function

        The method adds a function called `name` on the `window` object of every frame in every page in the context. When
        called, the function executes `playwrightFunction` in Node.js and returns a Promise which resolves to the return value
        of `playwrightFunction`.
        If the `playwrightFunction` returns a Promise, it will be awaited.
        See page.expose_function(name, playwrightFunction) for page-only version.
        An example of adding an `md5` function to all pages in the context:

        Parameters
        ----------
        name : str
            Name of the function on the window object.
        binding : Callable
            Callback function that will be called in the Playwright's context.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.exposeFunction(
                    name=name, binding=self._wrap_handler(binding)
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
    ) -> NoneType:
        """BrowserContext.route

        Routing provides the capability to modify network requests that are made by any page in the browser context. Once route
        is enabled, every request matching the url pattern will stall unless it's continued, fulfilled or aborted.
        An example of a naïve handler that aborts all image requests:
        or the same snippet using a regex pattern instead:
        Page routes (set up with page.route(url, handler)) take precedence over browser context routes when request matches both
        handlers.

        **NOTE** Enabling routing disables http cache.

        Parameters
        ----------
        url : Union[str, Pattern, Callable[[str], bool]]
            A glob pattern, regex pattern or predicate receiving URL to match while routing.
        handler : Union[Callable[[Route], Any], Callable[[Route, Request], Any]]
            handler function to route the request.
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.route(
                    url=self._wrap_handler(url), handler=self._wrap_handler(handler)
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

        Removes a route created with browser_context.route(url, handler). When `handler` is not specified, removes all routes for the
        `url`.

        Parameters
        ----------
        url : Union[str, Pattern, Callable[[str], bool]]
            A glob pattern, regex pattern or predicate receiving URL used to register a routing with browser_context.route(url, handler).
        handler : Union[Callable[[Route], Any], Callable[[Route, Request], Any], NoneType]
            Optional handler function used to register a routing with browser_context.route(url, handler).
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.unroute(
                    url=self._wrap_handler(url), handler=self._wrap_handler(handler)
                )
            )
        )

    def wait_for_event(
        self,
        event: str,
        predicate: typing.Union[typing.Callable[[typing.Any], bool]] = None,
        timeout: int = None,
    ) -> typing.Any:
        """BrowserContext.wait_for_event

        Waits for event to fire and passes its value into the predicate function. Resolves when the predicate returns truthy
        value. Will throw an error if the context closes before the event is fired. Returns the event data value.

        Parameters
        ----------
        event : str
            Event name, same one would pass into `browserContext.on(event)`.

        Returns
        -------
        Any
        """
        return mapping.from_maybe_impl(
            self._sync(
                self._impl_obj.waitForEvent(
                    event=event,
                    predicate=self._wrap_handler(predicate),
                    timeout=timeout,
                )
            )
        )

    def close(self) -> NoneType:
        """BrowserContext.close

        Closes the browser context. All the pages that belong to the browser context will be closed.

        **NOTE** the default browser context cannot be closed.
        """
        return mapping.from_maybe_impl(self._sync(self._impl_obj.close()))

    def storage_state(
        self, path: typing.Union[str, pathlib.Path] = None
    ) -> "StorageState":
        """BrowserContext.storage_state

        Returns storage state for this browser context, contains current cookies and local storage snapshot.

        Parameters
        ----------
        path : Union[str, pathlib.Path, NoneType]
            The file path to save the storage state to. If `path` is a relative path, then it is resolved relative to current working directory. If no path is provided, storage state is still returned, but won't be saved to the disk.

        Returns
        -------
        {"cookies": Optional[List[{"name": str, "value": str, "url": Optional[str], "domain": Optional[str], "path": Optional[str], "expires": Optional[int], "httpOnly": Optional[bool], "secure": Optional[bool], "sameSite": Optional[Literal['Strict', 'Lax', 'None']]}]], "origins": Optional[List[Dict]]}
        """
        return mapping.from_impl(self._sync(self._impl_obj.storageState(path=path)))

    def expect_event(
        self,
        event: str,
        predicate: typing.Union[typing.Callable[[typing.Any], bool]] = None,
        timeout: int = None,
    ) -> EventContextManager:
        """BrowserContext.expect_event

        Returns context manager that waits for ``event`` to fire upon exit. It passes event's value
        into the ``predicate`` function and waits for the predicate to return a truthy value. Will throw
        an error if the page is closed before the ``event`` is fired.

        with page.expect_event() as event_info:
            page.click("button")
        value = event_info.value

        Parameters
        ----------
        predicate : Optional[typing.Callable[[Any], bool]]
            Predicate receiving event data.
        timeout : Optional[int]
            Maximum wait time in milliseconds, defaults to 30 seconds, pass `0` to disable the timeout.
            The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or
            page.setDefaultTimeout(timeout) methods.
        """
        return EventContextManager(
            self, self._impl_obj.waitForEvent(event, predicate, timeout)
        )

    def expect_page(
        self,
        predicate: typing.Union[typing.Callable[["Page"], bool]] = None,
        timeout: int = None,
    ) -> EventContextManager["Page"]:
        """BrowserContext.expect_page

        Returns context manager that waits for ``event`` to fire upon exit. It passes event's value
        into the ``predicate`` function and waits for the predicate to return a truthy value. Will throw
        an error if the page is closed before the ``event`` is fired.

        with page.expect_page() as event_info:
            page.click("button")
        value = event_info.value

        Parameters
        ----------
        predicate : Optional[typing.Callable[[Any], bool]]
            Predicate receiving event data.
        timeout : Optional[int]
            Maximum wait time in milliseconds, defaults to 30 seconds, pass `0` to disable the timeout.
            The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or
            page.setDefaultTimeout(timeout) methods.
        """
        event = "page"
        return EventContextManager(
            self, self._impl_obj.waitForEvent(event, predicate, timeout)
        )


mapping.register(BrowserContextImpl, BrowserContext)


class CDPSession(SyncBase):
    def __init__(self, obj: CDPSessionImpl):
        super().__init__(obj)

    def send(self, method: str, params: typing.Dict = None) -> typing.Dict:
        """CDPSession.send

        Parameters
        ----------
        method : str
            protocol method name
        params : Optional[Dict]
            Optional method parameters

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


class ChromiumBrowserContext(BrowserContext):
    def __init__(self, obj: ChromiumBrowserContextImpl):
        super().__init__(obj)

    def background_pages(self) -> typing.List["Page"]:
        """ChromiumBrowserContext.background_pages

        All existing background pages in the context.

        Returns
        -------
        List[Page]
        """
        return mapping.from_impl_list(self._impl_obj.backgroundPages())

    def service_workers(self) -> typing.List["Worker"]:
        """ChromiumBrowserContext.service_workers

        All existing service workers in the context.

        Returns
        -------
        List[Worker]
        """
        return mapping.from_impl_list(self._impl_obj.serviceWorkers())

    def new_cdp_session(self, page: "Page") -> "CDPSession":
        """ChromiumBrowserContext.new_cdp_session

        Returns the newly created session.

        Parameters
        ----------
        page : Page
            Page to create new session for.

        Returns
        -------
        CDPSession
        """
        return mapping.from_impl(
            self._sync(self._impl_obj.newCDPSession(page=page._impl_obj))
        )


mapping.register(ChromiumBrowserContextImpl, ChromiumBrowserContext)


class Browser(SyncBase):
    def __init__(self, obj: BrowserImpl):
        super().__init__(obj)

    @property
    def contexts(self) -> typing.List["BrowserContext"]:
        """Browser.contexts

        Returns an array of all open browser contexts. In a newly created browser, this will return zero browser contexts.

        Returns
        -------
        List[BrowserContext]
        """
        return mapping.from_impl_list(self._impl_obj.contexts)

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
        return mapping.from_maybe_impl(self._impl_obj.isConnected())

    def new_context(
        self,
        viewport: typing.Union[typing.Tuple[int, int], Literal[0]] = None,
        ignore_https_errors: bool = None,
        java_script_enabled: bool = None,
        bypass_csp: bool = None,
        user_agent: str = None,
        locale: str = None,
        timezone_id: str = None,
        geolocation: "Geolocation" = None,
        permissions: typing.List[str] = None,
        extra_http_headers: typing.Union[typing.Dict[str, str]] = None,
        offline: bool = None,
        http_credentials: typing.Union[typing.Tuple[str, str]] = None,
        device_scale_factor: int = None,
        is_mobile: bool = None,
        has_touch: bool = None,
        color_scheme: Literal["dark", "light", "no-preference"] = None,
        accept_downloads: bool = None,
        default_browser_type: str = None,
        proxy: "ProxySettings" = None,
        record_har_path: typing.Union[str, pathlib.Path] = None,
        record_har_omit_content: bool = None,
        record_video_dir: typing.Union[str, pathlib.Path] = None,
        record_video_size: typing.Union[typing.Tuple[int, int]] = None,
        storage_state: typing.Union["StorageState", str, pathlib.Path] = None,
    ) -> "BrowserContext":
        """Browser.new_context

        Creates a new browser context. It won't share cookies/cache with other browser contexts.

        Parameters
        ----------
        viewport : Union[typing.Tuple[int, int], '0', NoneType]
            Sets a consistent viewport for each page. Defaults to an 1280x720 viewport. `null` disables the default viewport.
        ignore_https_errors : Optional[bool]
            Whether to ignore HTTPS errors during navigation. Defaults to `false`.
        java_script_enabled : Optional[bool]
            Whether or not to enable JavaScript in the context. Defaults to `true`.
        bypass_csp : Optional[bool]
            Toggles bypassing page's Content-Security-Policy.
        user_agent : Optional[str]
            Specific user agent to use in this context.
        locale : Optional[str]
            Specify user locale, for example `en-GB`, `de-DE`, etc. Locale will affect `navigator.language` value, `Accept-Language` request header value as well as number and date formatting rules.
        timezone_id : Optional[str]
            Changes the timezone of the context. See ICU’s `metaZones.txt` for a list of supported timezone IDs.
        geolocation : Optional[{"latitude": float, "longitude": float, "accuracy": Optional[float]}]
        permissions : Optional[List[str]]
            A list of permissions to grant to all pages in this context. See browserContext.grantPermissions(permissions[, options]) for more details.
        extra_http_headers : Optional[Dict[str, str]]
            An object containing additional HTTP headers to be sent with every request. All header values must be strings.
        offline : Optional[bool]
            Whether to emulate network being offline. Defaults to `false`.
        http_credentials : Optional[typing.Tuple[str, str]]
            Credentials for HTTP authentication.
        device_scale_factor : Optional[int]
            Specify device scale factor (can be thought of as dpr). Defaults to `1`.
        is_mobile : Optional[bool]
            Whether the `meta viewport` tag is taken into account and touch events are enabled. Defaults to `false`. Not supported in Firefox.
        has_touch : Optional[bool]
            Specifies if viewport supports touch events. Defaults to false.
        color_scheme : Optional[Literal['dark', 'light', 'no-preference']]
            Emulates `'prefers-colors-scheme'` media feature, supported values are `'light'`, `'dark'`, `'no-preference'`. See page.emulateMedia(params) for more details. Defaults to '`light`'.
        accept_downloads : Optional[bool]
            Whether to automatically download all the attachments. Defaults to `false` where all the downloads are canceled.
        proxy : Optional[{"server": str, "bypass": Optional[str], "username": Optional[str], "password": Optional[str]}]
            Network proxy settings to use with this context. Note that browser needs to be launched with the global proxy for this option to work. If all contexts override the proxy, global proxy will be never used and can be any string, for example `launch({ proxy: { server: 'per-context' } })`.
        record_har_path : Union[str, pathlib.Path, NoneType]
            Path on the filesystem to write the HAR file to.
        record_har_omit_content : Optional[bool]
            Optional setting to control whether to omit request content from the HAR. Defaults to `false`.
        record_video_dir : Union[str, pathlib.Path, NoneType]
            Path to the directory to put videos into.
        record_video_size : Optional[typing.Tuple[int, int]]
            Optional dimensions of the recorded videos. If not specified the size will be equal to `viewport`. If `viewport` is not configured explicitly the video size defaults to 1280x720. Actual picture of each page will be scaled down if necessary to fit the specified size.
        storage_state : Union[{"cookies": Optional[List[{"name": str, "value": str, "url": Optional[str], "domain": Optional[str], "path": Optional[str], "expires": Optional[int], "httpOnly": Optional[bool], "secure": Optional[bool], "sameSite": Optional[Literal['Strict', 'Lax', 'None']]}]], "origins": Optional[List[Dict]]}, str, pathlib.Path, NoneType]
            Populates context with given storage state. This method can be used to initialize context with logged-in information obtained via browserContext.storageState([options]). Either a path to the file with saved storage, or an object with the following fields:

        Returns
        -------
        BrowserContext
        """
        return mapping.from_impl(
            self._sync(
                self._impl_obj.newContext(
                    viewport=viewport,
                    ignoreHTTPSErrors=ignore_https_errors,
                    javaScriptEnabled=java_script_enabled,
                    bypassCSP=bypass_csp,
                    userAgent=user_agent,
                    locale=locale,
                    timezoneId=timezone_id,
                    geolocation=geolocation,
                    permissions=permissions,
                    extraHTTPHeaders=mapping.to_impl(extra_http_headers),
                    offline=offline,
                    httpCredentials=http_credentials,
                    deviceScaleFactor=device_scale_factor,
                    isMobile=is_mobile,
                    hasTouch=has_touch,
                    colorScheme=color_scheme,
                    acceptDownloads=accept_downloads,
                    defaultBrowserType=default_browser_type,
                    proxy=proxy,
                    recordHarPath=record_har_path,
                    recordHarOmitContent=record_har_omit_content,
                    recordVideoDir=record_video_dir,
                    recordVideoSize=record_video_size,
                    storageState=storage_state,
                )
            )
        )

    def new_page(
        self,
        viewport: typing.Union[typing.Tuple[int, int], Literal[0]] = None,
        ignore_https_errors: bool = None,
        java_script_enabled: bool = None,
        bypass_csp: bool = None,
        user_agent: str = None,
        locale: str = None,
        timezone_id: str = None,
        geolocation: "Geolocation" = None,
        permissions: typing.List[str] = None,
        extra_http_headers: typing.Union[typing.Dict[str, str]] = None,
        offline: bool = None,
        http_credentials: typing.Union[typing.Tuple[str, str]] = None,
        device_scale_factor: int = None,
        is_mobile: bool = None,
        has_touch: bool = None,
        color_scheme: Literal["dark", "light", "no-preference"] = None,
        accept_downloads: bool = None,
        default_browser_type: str = None,
        proxy: "ProxySettings" = None,
        record_har_path: typing.Union[str, pathlib.Path] = None,
        record_har_omit_content: bool = None,
        record_video_dir: typing.Union[str, pathlib.Path] = None,
        record_video_size: typing.Union[typing.Tuple[int, int]] = None,
        storage_state: typing.Union["StorageState", str, pathlib.Path] = None,
    ) -> "Page":
        """Browser.new_page

        Creates a new page in a new browser context. Closing this page will close the context as well.
        This is a convenience API that should only be used for the single-page scenarios and short snippets. Production code and
        testing frameworks should explicitly create browser.new_context([options]) followed by the browser_context.new_page() to
        control their exact life times.

        Parameters
        ----------
        viewport : Union[typing.Tuple[int, int], '0', NoneType]
            Sets a consistent viewport for each page. Defaults to an 1280x720 viewport. `null` disables the default viewport.
        ignore_https_errors : Optional[bool]
            Whether to ignore HTTPS errors during navigation. Defaults to `false`.
        java_script_enabled : Optional[bool]
            Whether or not to enable JavaScript in the context. Defaults to `true`.
        bypass_csp : Optional[bool]
            Toggles bypassing page's Content-Security-Policy.
        user_agent : Optional[str]
            Specific user agent to use in this context.
        locale : Optional[str]
            Specify user locale, for example `en-GB`, `de-DE`, etc. Locale will affect `navigator.language` value, `Accept-Language` request header value as well as number and date formatting rules.
        timezone_id : Optional[str]
            Changes the timezone of the context. See ICU’s `metaZones.txt` for a list of supported timezone IDs.
        geolocation : Optional[{"latitude": float, "longitude": float, "accuracy": Optional[float]}]
        permissions : Optional[List[str]]
            A list of permissions to grant to all pages in this context. See browserContext.grantPermissions(permissions[, options]) for more details.
        extra_http_headers : Optional[Dict[str, str]]
            An object containing additional HTTP headers to be sent with every request. All header values must be strings.
        offline : Optional[bool]
            Whether to emulate network being offline. Defaults to `false`.
        http_credentials : Optional[typing.Tuple[str, str]]
            Credentials for HTTP authentication.
        device_scale_factor : Optional[int]
            Specify device scale factor (can be thought of as dpr). Defaults to `1`.
        is_mobile : Optional[bool]
            Whether the `meta viewport` tag is taken into account and touch events are enabled. Defaults to `false`. Not supported in Firefox.
        has_touch : Optional[bool]
            Specifies if viewport supports touch events. Defaults to false.
        color_scheme : Optional[Literal['dark', 'light', 'no-preference']]
            Emulates `'prefers-colors-scheme'` media feature, supported values are `'light'`, `'dark'`, `'no-preference'`. See page.emulateMedia(params) for more details. Defaults to '`light`'.
        accept_downloads : Optional[bool]
            Whether to automatically download all the attachments. Defaults to `false` where all the downloads are canceled.
        proxy : Optional[{"server": str, "bypass": Optional[str], "username": Optional[str], "password": Optional[str]}]
            Network proxy settings to use with this context. Note that browser needs to be launched with the global proxy for this option to work. If all contexts override the proxy, global proxy will be never used and can be any string, for example `launch({ proxy: { server: 'per-context' } })`.
        record_har_path : Union[str, pathlib.Path, NoneType]
            Path on the filesystem to write the HAR file to.
        record_har_omit_content : Optional[bool]
            Optional setting to control whether to omit request content from the HAR. Defaults to `false`.
        record_video_dir : Union[str, pathlib.Path, NoneType]
            Path to the directory to put videos into.
        record_video_size : Optional[typing.Tuple[int, int]]
            Optional dimensions of the recorded videos. If not specified the size will be equal to `viewport`. If `viewport` is not configured explicitly the video size defaults to 1280x720. Actual picture of each page will be scaled down if necessary to fit the specified size.
        storage_state : Union[{"cookies": Optional[List[{"name": str, "value": str, "url": Optional[str], "domain": Optional[str], "path": Optional[str], "expires": Optional[int], "httpOnly": Optional[bool], "secure": Optional[bool], "sameSite": Optional[Literal['Strict', 'Lax', 'None']]}]], "origins": Optional[List[Dict]]}, str, pathlib.Path, NoneType]
            Populates context with given storage state. This method can be used to initialize context with logged-in information obtained via browserContext.storageState([options]). Either a path to the file with saved storage, or an object with the following fields:

        Returns
        -------
        Page
        """
        return mapping.from_impl(
            self._sync(
                self._impl_obj.newPage(
                    viewport=viewport,
                    ignoreHTTPSErrors=ignore_https_errors,
                    javaScriptEnabled=java_script_enabled,
                    bypassCSP=bypass_csp,
                    userAgent=user_agent,
                    locale=locale,
                    timezoneId=timezone_id,
                    geolocation=geolocation,
                    permissions=permissions,
                    extraHTTPHeaders=mapping.to_impl(extra_http_headers),
                    offline=offline,
                    httpCredentials=http_credentials,
                    deviceScaleFactor=device_scale_factor,
                    isMobile=is_mobile,
                    hasTouch=has_touch,
                    colorScheme=color_scheme,
                    acceptDownloads=accept_downloads,
                    defaultBrowserType=default_browser_type,
                    proxy=proxy,
                    recordHarPath=record_har_path,
                    recordHarOmitContent=record_har_omit_content,
                    recordVideoDir=record_video_dir,
                    recordVideoSize=record_video_size,
                    storageState=storage_state,
                )
            )
        )

    def close(self) -> NoneType:
        """Browser.close

        In case this browser is obtained using browser_type.launch([options]), closes the browser and all of its pages (if any were
        opened).
        In case this browser is obtained using browser_type.connect(params), clears all created contexts belonging to this browser
        and disconnects from the browser server.
        The Browser object itself is considered to be disposed and cannot be used anymore.
        """
        return mapping.from_maybe_impl(self._sync(self._impl_obj.close()))


mapping.register(BrowserImpl, Browser)


class BrowserType(SyncBase):
    def __init__(self, obj: BrowserTypeImpl):
        super().__init__(obj)

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
        return mapping.from_maybe_impl(self._impl_obj.executablePath)

    def launch(
        self,
        executable_path: typing.Union[str, pathlib.Path] = None,
        args: typing.List[str] = None,
        ignore_default_args: typing.Union[bool, typing.List[str]] = None,
        handle_sigint: bool = None,
        handle_sigterm: bool = None,
        handle_sighup: bool = None,
        timeout: int = None,
        env: typing.Union[typing.Dict[str, typing.Union[str, int, bool]]] = None,
        headless: bool = None,
        devtools: bool = None,
        proxy: "ProxySettings" = None,
        downloads_path: typing.Union[str, pathlib.Path] = None,
        slow_mo: int = None,
        chromium_sandbox: bool = None,
        firefox_user_prefs: typing.Union[
            typing.Dict[str, typing.Union[str, int, bool]]
        ] = None,
    ) -> "Browser":
        """BrowserType.launch

        Returns the browser instance.
        You can use `ignoreDefaultArgs` to filter out `--mute-audio` from default arguments:

        **Chromium-only** Playwright can also be used to control the Chrome browser, but it works best with the version of
        Chromium it is bundled with. There is no guarantee it will work with any other version. Use `executablePath` option with
        extreme caution.
        If Google Chrome (rather than Chromium) is preferred, a Chrome
        Canary or Dev
        Channel build is suggested.
        In browser_type.launch([options]) above, any mention of Chromium also applies to Chrome.
        See `this article` for
        a description of the differences between Chromium and Chrome. `This article` describes
        some differences for Linux users.

        Parameters
        ----------
        executable_path : Union[str, pathlib.Path, NoneType]
            Path to a browser executable to run instead of the bundled one. If `executablePath` is a relative path, then it is resolved relative to current working directory. Note that Playwright only works with the bundled Chromium, Firefox or WebKit, use at your own risk.
        args : Optional[List[str]]
            Additional arguments to pass to the browser instance. The list of Chromium flags can be found here.
        ignore_default_args : Union[bool, List[str], NoneType]
            If `true`, Playwright does not pass its own configurations args and only uses the ones from `args`. If an array is given, then filters out the given default arguments. Dangerous option; use with care. Defaults to `false`.
        handle_sigint : Optional[bool]
            Close the browser process on Ctrl-C. Defaults to `true`.
        handle_sigterm : Optional[bool]
            Close the browser process on SIGTERM. Defaults to `true`.
        handle_sighup : Optional[bool]
            Close the browser process on SIGHUP. Defaults to `true`.
        timeout : Optional[int]
            Maximum time in milliseconds to wait for the browser instance to start. Defaults to `30000` (30 seconds). Pass `0` to disable timeout.
        env : Optional[Dict[str, Union[str, int, bool]]]
            Specify environment variables that will be visible to the browser. Defaults to `process.env`.
        headless : Optional[bool]
            Whether to run browser in headless mode. More details for Chromium and Firefox. Defaults to `true` unless the `devtools` option is `true`.
        devtools : Optional[bool]
            **Chromium-only** Whether to auto-open a Developer Tools panel for each tab. If this option is `true`, the `headless` option will be set `false`.
        proxy : Optional[{"server": str, "bypass": Optional[str], "username": Optional[str], "password": Optional[str]}]
            Network proxy settings.
        downloads_path : Union[str, pathlib.Path, NoneType]
            If specified, accepted downloads are downloaded into this directory. Otherwise, temporary directory is created and is deleted when browser is closed.
        slow_mo : Optional[int]
            Slows down Playwright operations by the specified amount of milliseconds. Useful so that you can see what is going on.
        chromium_sandbox : Optional[bool]
            Enable Chromium sandboxing. Defaults to `false`.
        firefox_user_prefs : Optional[Dict[str, Union[str, int, bool]]]
            Firefox user preferences. Learn more about the Firefox user preferences at `about:config`.

        Returns
        -------
        Browser
        """
        return mapping.from_impl(
            self._sync(
                self._impl_obj.launch(
                    executablePath=executable_path,
                    args=args,
                    ignoreDefaultArgs=ignore_default_args,
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
                    chromiumSandbox=chromium_sandbox,
                    firefoxUserPrefs=mapping.to_impl(firefox_user_prefs),
                )
            )
        )

    def launch_persistent_context(
        self,
        user_data_dir: typing.Union[str, pathlib.Path],
        executable_path: typing.Union[str, pathlib.Path] = None,
        args: typing.List[str] = None,
        ignore_default_args: typing.Union[bool, typing.List[str]] = None,
        handle_sigint: bool = None,
        handle_sigterm: bool = None,
        handle_sighup: bool = None,
        timeout: int = None,
        env: typing.Union[typing.Dict[str, typing.Union[str, int, bool]]] = None,
        headless: bool = None,
        devtools: bool = None,
        proxy: "ProxySettings" = None,
        downloads_path: typing.Union[str, pathlib.Path] = None,
        slow_mo: int = None,
        viewport: typing.Union[typing.Tuple[int, int], Literal[0]] = None,
        ignore_https_errors: bool = None,
        java_script_enabled: bool = None,
        bypass_csp: bool = None,
        user_agent: str = None,
        locale: str = None,
        timezone_id: str = None,
        geolocation: "Geolocation" = None,
        permissions: typing.List[str] = None,
        extra_http_headers: typing.Union[typing.Dict[str, str]] = None,
        offline: bool = None,
        http_credentials: typing.Union[typing.Tuple[str, str]] = None,
        device_scale_factor: int = None,
        is_mobile: bool = None,
        has_touch: bool = None,
        color_scheme: Literal["dark", "light", "no-preference"] = None,
        accept_downloads: bool = None,
        chromium_sandbox: bool = None,
        record_har_path: typing.Union[str, pathlib.Path] = None,
        record_har_omit_content: bool = None,
        record_video_dir: typing.Union[str, pathlib.Path] = None,
        record_video_size: typing.Union[typing.Tuple[int, int]] = None,
    ) -> "BrowserContext":
        """BrowserType.launch_persistent_context

        Returns the persistent browser context instance.
        Launches browser that uses persistent storage located at `userDataDir` and returns the only context. Closing this
        context will automatically close the browser.

        Parameters
        ----------
        user_data_dir : Union[str, pathlib.Path]
            Path to a User Data Directory, which stores browser session data like cookies and local storage. More details for Chromium and Firefox.
        executable_path : Union[str, pathlib.Path, NoneType]
            Path to a browser executable to run instead of the bundled one. If `executablePath` is a relative path, then it is resolved relative to current working directory. **BEWARE**: Playwright is only guaranteed to work with the bundled Chromium, Firefox or WebKit, use at your own risk.
        args : Optional[List[str]]
            Additional arguments to pass to the browser instance. The list of Chromium flags can be found here.
        ignore_default_args : Union[bool, List[str], NoneType]
            If `true`, then do not use any of the default arguments. If an array is given, then filter out the given default arguments. Dangerous option; use with care. Defaults to `false`.
        handle_sigint : Optional[bool]
            Close the browser process on Ctrl-C. Defaults to `true`.
        handle_sigterm : Optional[bool]
            Close the browser process on SIGTERM. Defaults to `true`.
        handle_sighup : Optional[bool]
            Close the browser process on SIGHUP. Defaults to `true`.
        timeout : Optional[int]
            Maximum time in milliseconds to wait for the browser instance to start. Defaults to `30000` (30 seconds). Pass `0` to disable timeout.
        env : Optional[Dict[str, Union[str, int, bool]]]
            Specify environment variables that will be visible to the browser. Defaults to `process.env`.
        headless : Optional[bool]
            Whether to run browser in headless mode. More details for Chromium and Firefox. Defaults to `true` unless the `devtools` option is `true`.
        devtools : Optional[bool]
            **Chromium-only** Whether to auto-open a Developer Tools panel for each tab. If this option is `true`, the `headless` option will be set `false`.
        proxy : Optional[{"server": str, "bypass": Optional[str], "username": Optional[str], "password": Optional[str]}]
            Network proxy settings.
        downloads_path : Union[str, pathlib.Path, NoneType]
            If specified, accepted downloads are downloaded into this directory. Otherwise, temporary directory is created and is deleted when browser is closed.
        slow_mo : Optional[int]
            Slows down Playwright operations by the specified amount of milliseconds. Useful so that you can see what is going on. Defaults to 0.
        viewport : Union[typing.Tuple[int, int], '0', NoneType]
            Sets a consistent viewport for each page. Defaults to an 1280x720 viewport. `null` disables the default viewport.
        ignore_https_errors : Optional[bool]
            Whether to ignore HTTPS errors during navigation. Defaults to `false`.
        java_script_enabled : Optional[bool]
            Whether or not to enable JavaScript in the context. Defaults to `true`.
        bypass_csp : Optional[bool]
            Toggles bypassing page's Content-Security-Policy.
        user_agent : Optional[str]
            Specific user agent to use in this context.
        locale : Optional[str]
            Specify user locale, for example `en-GB`, `de-DE`, etc. Locale will affect `navigator.language` value, `Accept-Language` request header value as well as number and date formatting rules.
        timezone_id : Optional[str]
            Changes the timezone of the context. See ICU’s `metaZones.txt` for a list of supported timezone IDs.
        geolocation : Optional[{"latitude": float, "longitude": float, "accuracy": Optional[float]}]
        permissions : Optional[List[str]]
            A list of permissions to grant to all pages in this context. See browserContext.grantPermissions(permissions[, options]) for more details.
        extra_http_headers : Optional[Dict[str, str]]
            An object containing additional HTTP headers to be sent with every request. All header values must be strings.
        offline : Optional[bool]
            Whether to emulate network being offline. Defaults to `false`.
        http_credentials : Optional[typing.Tuple[str, str]]
            Credentials for HTTP authentication.
        device_scale_factor : Optional[int]
            Specify device scale factor (can be thought of as dpr). Defaults to `1`.
        is_mobile : Optional[bool]
            Whether the `meta viewport` tag is taken into account and touch events are enabled. Defaults to `false`. Not supported in Firefox.
        has_touch : Optional[bool]
            Specifies if viewport supports touch events. Defaults to false.
        color_scheme : Optional[Literal['dark', 'light', 'no-preference']]
            Emulates `'prefers-colors-scheme'` media feature, supported values are `'light'`, `'dark'`, `'no-preference'`. See page.emulateMedia(params) for more details. Defaults to '`light`'.
        accept_downloads : Optional[bool]
            Whether to automatically download all the attachments. Defaults to `false` where all the downloads are canceled.
        chromium_sandbox : Optional[bool]
            Enable Chromium sandboxing. Defaults to `true`.
        record_har_path : Union[str, pathlib.Path, NoneType]
            Path on the filesystem to write the HAR file to.
        record_har_omit_content : Optional[bool]
            Optional setting to control whether to omit request content from the HAR. Defaults to `false`.
        record_video_dir : Union[str, pathlib.Path, NoneType]
            Path to the directory to put videos into.
        record_video_size : Optional[typing.Tuple[int, int]]
            Optional dimensions of the recorded videos. If not specified the size will be equal to `viewport`. If `viewport` is not configured explicitly the video size defaults to 1280x720. Actual picture of each page will be scaled down if necessary to fit the specified size.

        Returns
        -------
        BrowserContext
        """
        return mapping.from_impl(
            self._sync(
                self._impl_obj.launchPersistentContext(
                    userDataDir=user_data_dir,
                    executablePath=executable_path,
                    args=args,
                    ignoreDefaultArgs=ignore_default_args,
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
                    ignoreHTTPSErrors=ignore_https_errors,
                    javaScriptEnabled=java_script_enabled,
                    bypassCSP=bypass_csp,
                    userAgent=user_agent,
                    locale=locale,
                    timezoneId=timezone_id,
                    geolocation=geolocation,
                    permissions=permissions,
                    extraHTTPHeaders=mapping.to_impl(extra_http_headers),
                    offline=offline,
                    httpCredentials=http_credentials,
                    deviceScaleFactor=device_scale_factor,
                    isMobile=is_mobile,
                    hasTouch=has_touch,
                    colorScheme=color_scheme,
                    acceptDownloads=accept_downloads,
                    chromiumSandbox=chromium_sandbox,
                    recordHarPath=record_har_path,
                    recordHarOmitContent=record_har_omit_content,
                    recordVideoDir=record_video_dir,
                    recordVideoSize=record_video_size,
                )
            )
        )


mapping.register(BrowserTypeImpl, BrowserType)


class Playwright(SyncBase):
    def __init__(self, obj: PlaywrightImpl):
        super().__init__(obj)

    @property
    def chromium(self) -> "BrowserType":
        return mapping.from_impl(self._impl_obj.chromium)

    @property
    def firefox(self) -> "BrowserType":
        return mapping.from_impl(self._impl_obj.firefox)

    @property
    def webkit(self) -> "BrowserType":
        return mapping.from_impl(self._impl_obj.webkit)

    @property
    def selectors(self) -> "Selectors":
        return mapping.from_impl(self._impl_obj.selectors)

    @property
    def devices(self) -> typing.Dict[str, "DeviceDescriptor"]:
        return mapping.from_impl_dict(self._impl_obj.devices)

    def stop(self) -> NoneType:
        return mapping.from_maybe_impl(self._impl_obj.stop())


mapping.register(PlaywrightImpl, Playwright)
