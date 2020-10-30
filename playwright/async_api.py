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

from playwright.accessibility import Accessibility as AccessibilityImpl
from playwright.async_base import AsyncBase, AsyncEventContextManager, mapping
from playwright.browser import Browser as BrowserImpl
from playwright.browser_context import BrowserContext as BrowserContextImpl
from playwright.browser_type import BrowserType as BrowserTypeImpl
from playwright.cdp_session import CDPSession as CDPSessionImpl
from playwright.chromium_browser_context import (
    ChromiumBrowserContext as ChromiumBrowserContextImpl,
)
from playwright.console_message import ConsoleMessage as ConsoleMessageImpl
from playwright.dialog import Dialog as DialogImpl
from playwright.download import Download as DownloadImpl
from playwright.element_handle import ElementHandle as ElementHandleImpl
from playwright.file_chooser import FileChooser as FileChooserImpl
from playwright.frame import Frame as FrameImpl
from playwright.helper import (
    ConsoleMessageLocation,
    Credentials,
    DeviceDescriptor,
    Error,
    FilePayload,
    FloatRect,
    Geolocation,
    IntSize,
    MousePosition,
    PdfMargins,
    ProxyServer,
    RequestFailure,
    SelectOption,
    Viewport,
)
from playwright.input import Keyboard as KeyboardImpl
from playwright.input import Mouse as MouseImpl
from playwright.js_handle import JSHandle as JSHandleImpl
from playwright.network import Request as RequestImpl
from playwright.network import Response as ResponseImpl
from playwright.network import Route as RouteImpl
from playwright.page import BindingCall as BindingCallImpl
from playwright.page import Page as PageImpl
from playwright.page import Worker as WorkerImpl
from playwright.playwright import Playwright as PlaywrightImpl
from playwright.selectors import Selectors as SelectorsImpl
from playwright.video import Video as VideoImpl

NoneType = type(None)


class Request(AsyncBase):
    def __init__(self, obj: RequestImpl):
        super().__init__(obj)

    @property
    def url(self) -> str:
        """Request.url

        Returns
        -------
        str
            URL of the request.
        """
        return mapping.from_maybe_impl(self._impl_obj.url)

    @property
    def resourceType(self) -> str:
        """Request.resourceType

        Contains the request's resource type as it was perceived by the rendering engine.
        ResourceType will be one of the following: `document`, `stylesheet`, `image`, `media`, `font`, `script`, `texttrack`, `xhr`, `fetch`, `eventsource`, `websocket`, `manifest`, `other`.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.resourceType)

    @property
    def method(self) -> str:
        """Request.method

        Returns
        -------
        str
            Request's method (GET, POST, etc.)
        """
        return mapping.from_maybe_impl(self._impl_obj.method)

    @property
    def postData(self) -> typing.Union[str, NoneType]:
        """Request.postData

        Returns
        -------
        Optional[str]
            Request's post body, if any.
        """
        return mapping.from_maybe_impl(self._impl_obj.postData)

    @property
    def postDataJSON(self) -> typing.Union[typing.Dict, NoneType]:
        """Request.postDataJSON

        When the response is `application/x-www-form-urlencoded` then a key/value object of the values will be returned. Otherwise it will be parsed as JSON.

        Returns
        -------
        Optional[Dict]
            Parsed request's body for `form-urlencoded` and JSON as a fallback if any.
        """
        return mapping.from_maybe_impl(self._impl_obj.postDataJSON)

    @property
    def postDataBuffer(self) -> typing.Union[bytes, NoneType]:
        """Request.postDataBuffer

        Returns
        -------
        Optional[bytes]
            Request's post body in a binary form, if any.
        """
        return mapping.from_maybe_impl(self._impl_obj.postDataBuffer)

    @property
    def headers(self) -> typing.Dict[str, str]:
        """Request.headers

        Returns
        -------
        Dict[str, str]
            An object with HTTP headers associated with the request. All header names are lower-case.
        """
        return mapping.from_maybe_impl(self._impl_obj.headers)

    @property
    def frame(self) -> "Frame":
        """Request.frame

        Returns
        -------
        Frame
            A Frame that initiated this request.
        """
        return mapping.from_impl(self._impl_obj.frame)

    @property
    def redirectedFrom(self) -> typing.Union["Request", NoneType]:
        """Request.redirectedFrom

        When the server responds with a redirect, Playwright creates a new Request object. The two requests are connected by `redirectedFrom()` and `redirectedTo()` methods. When multiple server redirects has happened, it is possible to construct the whole redirect chain by repeatedly calling `redirectedFrom()`.
        For example, if the website `http://example.com` redirects to `https://example.com`:
        If the website `https://google.com` has no redirects:

        Returns
        -------
        Optional[Request]
            Request that was redirected by the server to this one, if any.
        """
        return mapping.from_impl_nullable(self._impl_obj.redirectedFrom)

    @property
    def redirectedTo(self) -> typing.Union["Request", NoneType]:
        """Request.redirectedTo

        This method is the opposite of request.redirectedFrom():

        Returns
        -------
        Optional[Request]
            New request issued by the browser if the server responded with redirect.
        """
        return mapping.from_impl_nullable(self._impl_obj.redirectedTo)

    @property
    def failure(self) -> typing.Union[RequestFailure, NoneType]:
        """Request.failure

        The method returns `null` unless this request has failed, as reported by
        `requestfailed` event.
        Example of logging of all the failed requests:

        Returns
        -------
        Optional[{"errorText": str}]
            Object describing request failure, if any
        """
        return mapping.from_maybe_impl(self._impl_obj.failure)

    async def response(self) -> typing.Union["Response", NoneType]:
        """Request.response

        Returns
        -------
        Optional[Response]
            A matching Response object, or `null` if the response was not received due to error.
        """
        return mapping.from_impl_nullable(await self._impl_obj.response())

    def isNavigationRequest(self) -> bool:
        """Request.isNavigationRequest

        Whether this request is driving frame's navigation.

        Returns
        -------
        bool
        """
        return mapping.from_maybe_impl(self._impl_obj.isNavigationRequest())


mapping.register(RequestImpl, Request)


class Response(AsyncBase):
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
    def statusText(self) -> str:
        """Response.statusText

        Contains the status text of the response (e.g. usually an "OK" for a success).

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.statusText)

    @property
    def headers(self) -> typing.Dict[str, str]:
        """Response.headers

        Returns
        -------
        Dict[str, str]
            An object with HTTP headers associated with the response. All header names are lower-case.
        """
        return mapping.from_maybe_impl(self._impl_obj.headers)

    @property
    def request(self) -> "Request":
        """Response.request

        Returns
        -------
        Request
            A matching Request object.
        """
        return mapping.from_impl(self._impl_obj.request)

    @property
    def frame(self) -> "Frame":
        """Response.frame

        Returns
        -------
        Frame
            A Frame that initiated this response.
        """
        return mapping.from_impl(self._impl_obj.frame)

    async def finished(self) -> typing.Union[Error, NoneType]:
        """Response.finished

        Returns
        -------
        Optional[Error]
            Waits for this response to finish, returns failure error if request failed.
        """
        return mapping.from_maybe_impl(await self._impl_obj.finished())

    async def body(self) -> bytes:
        """Response.body

        Returns
        -------
        bytes
            Promise which resolves to a buffer with response body.
        """
        return mapping.from_maybe_impl(await self._impl_obj.body())

    async def text(self) -> str:
        """Response.text

        Returns
        -------
        str
            Promise which resolves to a text representation of response body.
        """
        return mapping.from_maybe_impl(await self._impl_obj.text())

    async def json(self) -> typing.Union[typing.Dict, typing.List]:
        """Response.json

        This method will throw if the response body is not parsable via `JSON.parse`.

        Returns
        -------
        Union[Dict, List]
            Promise which resolves to a JSON representation of response body.
        """
        return mapping.from_maybe_impl(await self._impl_obj.json())


mapping.register(ResponseImpl, Response)


class Route(AsyncBase):
    def __init__(self, obj: RouteImpl):
        super().__init__(obj)

    @property
    def request(self) -> "Request":
        """Route.request

        Returns
        -------
        Request
            A request to be routed.
        """
        return mapping.from_impl(self._impl_obj.request)

    async def abort(self, errorCode: str = None) -> NoneType:
        """Route.abort

        Aborts the route's request.

        Parameters
        ----------
        errorCode : Optional[str]
            Optional error code. Defaults to `failed`, could be
            one of the following:
             - `'aborted'` - An operation was aborted (due to user action)
             - `'accessdenied'` - Permission to access a resource, other than the network, was denied
             - `'addressunreachable'` - The IP address is unreachable. This usually means
             - that there is no route to the specified host or network.
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
        return mapping.from_maybe_impl(await self._impl_obj.abort(errorCode=errorCode))

    async def fulfill(
        self,
        status: int = None,
        headers: typing.Union[typing.Dict[str, str]] = None,
        body: typing.Union[str, bytes] = None,
        path: typing.Union[str, pathlib.Path] = None,
        contentType: str = None,
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
        contentType : Optional[str]
            If set, equals to setting `Content-Type` response header.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.fulfill(
                status=status,
                headers=mapping.to_impl(headers),
                body=body,
                path=path,
                contentType=contentType,
            )
        )

    async def continue_(
        self,
        method: str = None,
        headers: typing.Union[typing.Dict[str, str]] = None,
        postData: typing.Union[str, bytes] = None,
    ) -> NoneType:
        """Route.continue_

        Continues route's request with optional overrides.

        Parameters
        ----------
        method : Optional[str]
            If set changes the request method (e.g. GET or POST)
        headers : Optional[Dict[str, str]]
            If set changes the request HTTP headers. Header values will be converted to a string.
        postData : Union[str, bytes, NoneType]
            If set changes the post data of request
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.continue_(
                method=method, headers=mapping.to_impl(headers), postData=postData
            )
        )


mapping.register(RouteImpl, Route)


class Keyboard(AsyncBase):
    def __init__(self, obj: KeyboardImpl):
        super().__init__(obj)

    async def down(self, key: str) -> NoneType:
        """Keyboard.down

        Dispatches a `keydown` event.
        `key` can specify the intended keyboardEvent.key value or a single character to generate the text for. A superset of the `key` values can be found here. Examples of the keys are:
        `F1` - `F12`, `Digit0`- `Digit9`, `KeyA`- `KeyZ`, `Backquote`, `Minus`, `Equal`, `Backslash`, `Backspace`, `Tab`, `Delete`, `Escape`, `ArrowDown`, `End`, `Enter`, `Home`, `Insert`, `PageDown`, `PageUp`, `ArrowRight`, `ArrowUp`, etc.
        Following modification shortcuts are also suported: `Shift`, `Control`, `Alt`, `Meta`, `ShiftLeft`.
        Holding down `Shift` will type the text that corresponds to the `key` in the upper case.
        If `key` is a single character, it is case-sensitive, so the values `a` and `A` will generate different respective texts.
        If `key` is a modifier key, `Shift`, `Meta`, `Control`, or `Alt`, subsequent key presses will be sent with that modifier active. To release the modifier key, use `keyboard.up`.
        After the key is pressed once, subsequent calls to `keyboard.down` will have repeat set to true. To release the key, use `keyboard.up`.

        **NOTE** Modifier keys DO influence `keyboard.down`. Holding down `Shift` will type the text in upper case.

        Parameters
        ----------
        key : str
            Name of the key to press or a character to generate, such as `ArrowLeft` or `a`.
        """
        return mapping.from_maybe_impl(await self._impl_obj.down(key=key))

    async def up(self, key: str) -> NoneType:
        """Keyboard.up

        Dispatches a `keyup` event.

        Parameters
        ----------
        key : str
            Name of the key to press or a character to generate, such as `ArrowLeft` or `a`.
        """
        return mapping.from_maybe_impl(await self._impl_obj.up(key=key))

    async def insertText(self, text: str) -> NoneType:
        """Keyboard.insertText

        Dispatches only `input` event, does not emit the `keydown`, `keyup` or `keypress` events.

        **NOTE** Modifier keys DO NOT effect `keyboard.insertText`. Holding down `Shift` will not type the text in upper case.

        Parameters
        ----------
        text : str
            Sets input to the specified text value.
        """
        return mapping.from_maybe_impl(await self._impl_obj.insertText(text=text))

    async def type(self, text: str, delay: int = None) -> NoneType:
        """Keyboard.type

        Sends a `keydown`, `keypress`/`input`, and `keyup` event for each character in the text.
        To press a special key, like `Control` or `ArrowDown`, use `keyboard.press`.

        **NOTE** Modifier keys DO NOT effect `keyboard.type`. Holding down `Shift` will not type the text in upper case.

        Parameters
        ----------
        text : str
            A text to type into a focused element.
        delay : Optional[int]
            Time to wait between key presses in milliseconds. Defaults to 0.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.type(text=text, delay=delay)
        )

    async def press(self, key: str, delay: int = None) -> NoneType:
        """Keyboard.press

        `key` can specify the intended keyboardEvent.key value or a single character to generate the text for. A superset of the `key` values can be found here. Examples of the keys are:
        `F1` - `F12`, `Digit0`- `Digit9`, `KeyA`- `KeyZ`, `Backquote`, `Minus`, `Equal`, `Backslash`, `Backspace`, `Tab`, `Delete`, `Escape`, `ArrowDown`, `End`, `Enter`, `Home`, `Insert`, `PageDown`, `PageUp`, `ArrowRight`, `ArrowUp`, etc.
        Following modification shortcuts are also suported: `Shift`, `Control`, `Alt`, `Meta`, `ShiftLeft`.
        Holding down `Shift` will type the text that corresponds to the `key` in the upper case.
        If `key` is a single character, it is case-sensitive, so the values `a` and `A` will generate different respective texts.
        Shortcuts such as `key: "Control+o"` or `key: "Control+Shift+T"` are supported as well. When speficied with the modifier, modifier is pressed and being held while the subsequent key is being pressed.
        Shortcut for `keyboard.down` and `keyboard.up`.

        Parameters
        ----------
        key : str
            Name of the key to press or a character to generate, such as `ArrowLeft` or `a`.
        delay : Optional[int]
            Time to wait between `keydown` and `keyup` in milliseconds. Defaults to 0.
        """
        return mapping.from_maybe_impl(await self._impl_obj.press(key=key, delay=delay))


mapping.register(KeyboardImpl, Keyboard)


class Mouse(AsyncBase):
    def __init__(self, obj: MouseImpl):
        super().__init__(obj)

    async def move(self, x: float, y: float, steps: int = None) -> NoneType:
        """Mouse.move

        Dispatches a `mousemove` event.

        Parameters
        ----------
        x : float
        y : float
        steps : Optional[int]
            defaults to 1. Sends intermediate `mousemove` events.
        """
        return mapping.from_maybe_impl(await self._impl_obj.move(x=x, y=y, steps=steps))

    async def down(
        self, button: Literal["left", "middle", "right"] = None, clickCount: int = None
    ) -> NoneType:
        """Mouse.down

        Dispatches a `mousedown` event.

        Parameters
        ----------
        button : Optional[Literal['left', 'middle', 'right']]
            Defaults to `left`.
        clickCount : Optional[int]
            defaults to 1. See UIEvent.detail.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.down(button=button, clickCount=clickCount)
        )

    async def up(
        self, button: Literal["left", "middle", "right"] = None, clickCount: int = None
    ) -> NoneType:
        """Mouse.up

        Dispatches a `mouseup` event.

        Parameters
        ----------
        button : Optional[Literal['left', 'middle', 'right']]
            Defaults to `left`.
        clickCount : Optional[int]
            defaults to 1. See UIEvent.detail.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.up(button=button, clickCount=clickCount)
        )

    async def click(
        self,
        x: float,
        y: float,
        delay: int = None,
        button: Literal["left", "middle", "right"] = None,
        clickCount: int = None,
    ) -> NoneType:
        """Mouse.click

        Shortcut for `mouse.move`, `mouse.down` and `mouse.up`.

        Parameters
        ----------
        x : float
        y : float
        delay : Optional[int]
            Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        button : Optional[Literal['left', 'middle', 'right']]
            Defaults to `left`.
        clickCount : Optional[int]
            defaults to 1. See UIEvent.detail.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.click(
                x=x, y=y, delay=delay, button=button, clickCount=clickCount
            )
        )

    async def dblclick(
        self,
        x: float,
        y: float,
        delay: int = None,
        button: Literal["left", "middle", "right"] = None,
    ) -> NoneType:
        """Mouse.dblclick

        Shortcut for `mouse.move`, `mouse.down`, `mouse.up`, `mouse.down` and `mouse.up`.

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
            await self._impl_obj.dblclick(x=x, y=y, delay=delay, button=button)
        )


mapping.register(MouseImpl, Mouse)


class JSHandle(AsyncBase):
    def __init__(self, obj: JSHandleImpl):
        super().__init__(obj)

    async def evaluate(
        self, expression: str, arg: typing.Any = None, force_expr: bool = None
    ) -> typing.Any:
        """JSHandle.evaluate

        This method passes this handle as the first argument to `pageFunction`.
        If `pageFunction` returns a Promise, then `handle.evaluate` would wait for the promise to resolve and return its value.
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
            Promise which resolves to the return value of `pageFunction`
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.evaluate(
                expression=expression, arg=mapping.to_impl(arg), force_expr=force_expr
            )
        )

    async def evaluateHandle(
        self, expression: str, arg: typing.Any = None, force_expr: bool = None
    ) -> "JSHandle":
        """JSHandle.evaluateHandle

        This method passes this handle as the first argument to `pageFunction`.
        The only difference between `jsHandle.evaluate` and `jsHandle.evaluateHandle` is that `jsHandle.evaluateHandle` returns in-page object (JSHandle).
        If the function passed to the `jsHandle.evaluateHandle` returns a Promise, then `jsHandle.evaluateHandle` would wait for the promise to resolve and return its value.
        See page.evaluateHandle() for more details.

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
            Promise which resolves to the return value of `pageFunction` as in-page object (JSHandle)
        """
        return mapping.from_impl(
            await self._impl_obj.evaluateHandle(
                expression=expression, arg=mapping.to_impl(arg), force_expr=force_expr
            )
        )

    async def getProperty(self, propertyName: str) -> "JSHandle":
        """JSHandle.getProperty

        Fetches a single property from the referenced object.

        Parameters
        ----------
        propertyName : str
            property to get

        Returns
        -------
        JSHandle
        """
        return mapping.from_impl(
            await self._impl_obj.getProperty(propertyName=propertyName)
        )

    async def getProperties(self) -> typing.Dict[str, "JSHandle"]:
        """JSHandle.getProperties

        The method returns a map with **own property names** as keys and JSHandle instances for the property values.

        Returns
        -------
        Dict[str, JSHandle]
        """
        return mapping.from_impl_dict(await self._impl_obj.getProperties())

    def asElement(self) -> typing.Union["ElementHandle", NoneType]:
        """JSHandle.asElement

        Returns either `null` or the object handle itself, if the object handle is an instance of ElementHandle.

        Returns
        -------
        Optional[ElementHandle]
        """
        return mapping.from_impl_nullable(self._impl_obj.asElement())

    async def dispose(self) -> NoneType:
        """JSHandle.dispose

        The `jsHandle.dispose` method stops referencing the element handle.
        """
        return mapping.from_maybe_impl(await self._impl_obj.dispose())

    async def jsonValue(self) -> typing.Any:
        """JSHandle.jsonValue

        Returns a JSON representation of the object. If the object has a
        `toJSON`
        function, it **will not be called**.

        **NOTE** The method will return an empty JSON object if the referenced object is not stringifiable. It will throw an error if the object has circular references.

        Returns
        -------
        Any
        """
        return mapping.from_maybe_impl(await self._impl_obj.jsonValue())


mapping.register(JSHandleImpl, JSHandle)


class ElementHandle(JSHandle):
    def __init__(self, obj: ElementHandleImpl):
        super().__init__(obj)

    def toString(self) -> str:
        """ElementHandle.toString

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.toString())

    def asElement(self) -> typing.Union["ElementHandle", NoneType]:
        """ElementHandle.asElement

        Returns either `null` or the object handle itself, if the object handle is an instance of ElementHandle.

        Returns
        -------
        Optional[ElementHandle]
        """
        return mapping.from_impl_nullable(self._impl_obj.asElement())

    async def ownerFrame(self) -> typing.Union["Frame", NoneType]:
        """ElementHandle.ownerFrame

        Returns
        -------
        Optional[Frame]
            Returns the frame containing the given element.
        """
        return mapping.from_impl_nullable(await self._impl_obj.ownerFrame())

    async def contentFrame(self) -> typing.Union["Frame", NoneType]:
        """ElementHandle.contentFrame

        Returns
        -------
        Optional[Frame]
            Resolves to the content frame for element handles referencing iframe nodes, or `null` otherwise
        """
        return mapping.from_impl_nullable(await self._impl_obj.contentFrame())

    async def getAttribute(self, name: str) -> typing.Union[str, NoneType]:
        """ElementHandle.getAttribute

        Returns element attribute value.

        Parameters
        ----------
        name : str
            Attribute name to get the value for.

        Returns
        -------
        Optional[str]
        """
        return mapping.from_maybe_impl(await self._impl_obj.getAttribute(name=name))

    async def textContent(self) -> typing.Union[str, NoneType]:
        """ElementHandle.textContent

        Returns
        -------
        Optional[str]
            Resolves to the `node.textContent`.
        """
        return mapping.from_maybe_impl(await self._impl_obj.textContent())

    async def innerText(self) -> str:
        """ElementHandle.innerText

        Returns
        -------
        str
            Resolves to the `element.innerText`.
        """
        return mapping.from_maybe_impl(await self._impl_obj.innerText())

    async def innerHTML(self) -> str:
        """ElementHandle.innerHTML

        Returns
        -------
        str
            Resolves to the `element.innerHTML`.
        """
        return mapping.from_maybe_impl(await self._impl_obj.innerHTML())

    async def dispatchEvent(self, type: str, eventInit: typing.Dict = None) -> NoneType:
        """ElementHandle.dispatchEvent

        The snippet below dispatches the `click` event on the element. Regardless of the visibility state of the elment, `click` is dispatched. This is equivalend to calling `element.click()`.
        Under the hood, it creates an instance of an event based on the given `type`, initializes it with `eventInit` properties and dispatches it on the element. Events are `composed`, `cancelable` and bubble by default.
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
        eventInit : Optional[Dict]
            event-specific initialization properties.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.dispatchEvent(
                type=type, eventInit=mapping.to_impl(eventInit)
            )
        )

    async def scrollIntoViewIfNeeded(self, timeout: int = None) -> NoneType:
        """ElementHandle.scrollIntoViewIfNeeded

        This method waits for actionability checks, then tries to scroll element into view, unless it is completely visible as defined by IntersectionObserver's `ratio`.
        Throws when `elementHandle` does not point to an element connected to a Document or a ShadowRoot.

        Parameters
        ----------
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.scrollIntoViewIfNeeded(timeout=timeout)
        )

    async def hover(
        self,
        modifiers: typing.Union[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: MousePosition = None,
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
        When all steps combined have not finished during the specified `timeout`, this method rejects with a TimeoutError. Passing zero timeout disables this.

        Parameters
        ----------
        modifiers : Optional[List[Literal['Alt', 'Control', 'Meta', 'Shift']]]
            Modifier keys to press. Ensures that only these modifiers are pressed during the hover, and then restores current modifiers back. If not specified, currently pressed modifiers are used.
        position : Optional[{"x": float, "y": float}]
            A point to hover relative to the top-left corner of element padding box. If not specified, hovers over some visible point of the element.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        force : Optional[bool]
            Whether to bypass the actionability checks. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.hover(
                modifiers=modifiers, position=position, timeout=timeout, force=force
            )
        )

    async def click(
        self,
        modifiers: typing.Union[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: MousePosition = None,
        delay: int = None,
        button: Literal["left", "middle", "right"] = None,
        clickCount: int = None,
        timeout: int = None,
        force: bool = None,
        noWaitAfter: bool = None,
    ) -> NoneType:
        """ElementHandle.click

        This method clicks the element by performing the following steps:

        Wait for actionability checks on the element, unless `force` option is set.
        Scroll the element into view if needed.
        Use page.mouse to click in the center of the element, or the specified `position`.
        Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.

        If the element is detached from the DOM at any moment during the action, this method rejects.
        When all steps combined have not finished during the specified `timeout`, this method rejects with a TimeoutError. Passing zero timeout disables this.

        Parameters
        ----------
        modifiers : Optional[List[Literal['Alt', 'Control', 'Meta', 'Shift']]]
            Modifier keys to press. Ensures that only these modifiers are pressed during the click, and then restores current modifiers back. If not specified, currently pressed modifiers are used.
        position : Optional[{"x": float, "y": float}]
            A point to click relative to the top-left corner of element padding box. If not specified, clicks to some visible point of the element.
        delay : Optional[int]
            Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        button : Optional[Literal['left', 'middle', 'right']]
            Defaults to `left`.
        clickCount : Optional[int]
            defaults to 1. See UIEvent.detail.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        force : Optional[bool]
            Whether to bypass the actionability checks. Defaults to `false`.
        noWaitAfter : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.click(
                modifiers=modifiers,
                position=position,
                delay=delay,
                button=button,
                clickCount=clickCount,
                timeout=timeout,
                force=force,
                noWaitAfter=noWaitAfter,
            )
        )

    async def dblclick(
        self,
        modifiers: typing.Union[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: MousePosition = None,
        delay: int = None,
        button: Literal["left", "middle", "right"] = None,
        timeout: int = None,
        force: bool = None,
        noWaitAfter: bool = None,
    ) -> NoneType:
        """ElementHandle.dblclick

        This method double clicks the element by performing the following steps:

        Wait for actionability checks on the element, unless `force` option is set.
        Scroll the element into view if needed.
        Use page.mouse to double click in the center of the element, or the specified `position`.
        Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set. Note that if the first click of the `dblclick()` triggers a navigation event, this method will reject.

        If the element is detached from the DOM at any moment during the action, this method rejects.
        When all steps combined have not finished during the specified `timeout`, this method rejects with a TimeoutError. Passing zero timeout disables this.

        **NOTE** `elementHandle.dblclick()` dispatches two `click` events and a single `dblclick` event.

        Parameters
        ----------
        modifiers : Optional[List[Literal['Alt', 'Control', 'Meta', 'Shift']]]
            Modifier keys to press. Ensures that only these modifiers are pressed during the double click, and then restores current modifiers back. If not specified, currently pressed modifiers are used.
        position : Optional[{"x": float, "y": float}]
            A point to double click relative to the top-left corner of element padding box. If not specified, double clicks to some visible point of the element.
        delay : Optional[int]
            Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        button : Optional[Literal['left', 'middle', 'right']]
            Defaults to `left`.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        force : Optional[bool]
            Whether to bypass the actionability checks. Defaults to `false`.
        noWaitAfter : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.dblclick(
                modifiers=modifiers,
                position=position,
                delay=delay,
                button=button,
                timeout=timeout,
                force=force,
                noWaitAfter=noWaitAfter,
            )
        )

    async def selectOption(
        self,
        values: typing.Union[
            str,
            "ElementHandle",
            SelectOption,
            typing.List[str],
            typing.List["ElementHandle"],
            typing.List[SelectOption],
        ] = None,
        timeout: int = None,
        noWaitAfter: bool = None,
    ) -> typing.List[str]:
        """ElementHandle.selectOption

        Triggers a `change` and `input` event once all the provided options have been selected.
        If element is not a `<select>` element, the method throws an error.

        Parameters
        ----------
        values : Union[str, ElementHandle, {"value": Optional[str], "label": Optional[str], "index": Optional[str]}, List[str], List[ElementHandle], List[{"value": Optional[str], "label": Optional[str], "index": Optional[str]}], NoneType]
            Options to select. If the `<select>` has the `multiple` attribute, all matching options are selected, otherwise only the first option matching one of the passed options is selected. String values are equivalent to `{value:'string'}`. Option is considered matching if all specified properties match.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        noWaitAfter : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.

        Returns
        -------
        List[str]
            An array of option values that have been successfully selected.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.selectOption(
                values=mapping.to_impl(values), timeout=timeout, noWaitAfter=noWaitAfter
            )
        )

    async def fill(
        self, value: str, timeout: int = None, noWaitAfter: bool = None
    ) -> NoneType:
        """ElementHandle.fill

        This method waits for actionability checks, focuses the element, fills it and triggers an `input` event after filling.
        If the element is not an `<input>`, `<textarea>` or `[contenteditable]` element, this method throws an error.
        Note that you can pass an empty string to clear the input field.

        Parameters
        ----------
        value : str
            Value to set for the `<input>`, `<textarea>` or `[contenteditable]` element.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        noWaitAfter : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.fill(
                value=value, timeout=timeout, noWaitAfter=noWaitAfter
            )
        )

    async def selectText(self, timeout: int = None) -> NoneType:
        """ElementHandle.selectText

        This method waits for actionability checks, then focuses the element and selects all its text content.

        Parameters
        ----------
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        """
        return mapping.from_maybe_impl(await self._impl_obj.selectText(timeout=timeout))

    async def setInputFiles(
        self,
        files: typing.Union[
            str,
            pathlib.Path,
            FilePayload,
            typing.List[str],
            typing.List[pathlib.Path],
            typing.List[FilePayload],
        ],
        timeout: int = None,
        noWaitAfter: bool = None,
    ) -> NoneType:
        """ElementHandle.setInputFiles

        This method expects `elementHandle` to point to an input element.
        Sets the value of the file input to these file paths or files. If some of the `filePaths` are relative paths, then they are resolved relative to the current working directory. For empty array, clears the selected files.

        Parameters
        ----------
        files : Union[str, pathlib.Path, {"name": str, "mimeType": str, "buffer": bytes}, List[str], List[pathlib.Path], List[{"name": str, "mimeType": str, "buffer": bytes}]]
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        noWaitAfter : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.setInputFiles(
                files=files, timeout=timeout, noWaitAfter=noWaitAfter
            )
        )

    async def focus(self) -> NoneType:
        """ElementHandle.focus

        Calls focus on the element.
        """
        return mapping.from_maybe_impl(await self._impl_obj.focus())

    async def type(
        self,
        text: str,
        delay: int = None,
        timeout: int = None,
        noWaitAfter: bool = None,
    ) -> NoneType:
        """ElementHandle.type

        Focuses the element, and then sends a `keydown`, `keypress`/`input`, and `keyup` event for each character in the text.
        To press a special key, like `Control` or `ArrowDown`, use `elementHandle.press`.
        An example of typing into a text field and then submitting the form:

        Parameters
        ----------
        text : str
            A text to type into a focused element.
        delay : Optional[int]
            Time to wait between key presses in milliseconds. Defaults to 0.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        noWaitAfter : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.type(
                text=text, delay=delay, timeout=timeout, noWaitAfter=noWaitAfter
            )
        )

    async def press(
        self, key: str, delay: int = None, timeout: int = None, noWaitAfter: bool = None
    ) -> NoneType:
        """ElementHandle.press

        Focuses the element, and then uses `keyboard.down` and `keyboard.up`.
        `key` can specify the intended keyboardEvent.key value or a single character to generate the text for. A superset of the `key` values can be found here. Examples of the keys are:
        `F1` - `F12`, `Digit0`- `Digit9`, `KeyA`- `KeyZ`, `Backquote`, `Minus`, `Equal`, `Backslash`, `Backspace`, `Tab`, `Delete`, `Escape`, `ArrowDown`, `End`, `Enter`, `Home`, `Insert`, `PageDown`, `PageUp`, `ArrowRight`, `ArrowUp`, etc.
        Following modification shortcuts are also suported: `Shift`, `Control`, `Alt`, `Meta`, `ShiftLeft`.
        Holding down `Shift` will type the text that corresponds to the `key` in the upper case.
        If `key` is a single character, it is case-sensitive, so the values `a` and `A` will generate different respective texts.
        Shortcuts such as `key: "Control+o"` or `key: "Control+Shift+T"` are supported as well. When speficied with the modifier, modifier is pressed and being held while the subsequent key is being pressed.

        Parameters
        ----------
        key : str
            Name of the key to press or a character to generate, such as `ArrowLeft` or `a`.
        delay : Optional[int]
            Time to wait between `keydown` and `keyup` in milliseconds. Defaults to 0.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        noWaitAfter : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.press(
                key=key, delay=delay, timeout=timeout, noWaitAfter=noWaitAfter
            )
        )

    async def check(
        self, timeout: int = None, force: bool = None, noWaitAfter: bool = None
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
        When all steps combined have not finished during the specified `timeout`, this method rejects with a TimeoutError. Passing zero timeout disables this.

        Parameters
        ----------
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        force : Optional[bool]
            Whether to bypass the actionability checks. Defaults to `false`.
        noWaitAfter : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.check(
                timeout=timeout, force=force, noWaitAfter=noWaitAfter
            )
        )

    async def uncheck(
        self, timeout: int = None, force: bool = None, noWaitAfter: bool = None
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
        When all steps combined have not finished during the specified `timeout`, this method rejects with a TimeoutError. Passing zero timeout disables this.

        Parameters
        ----------
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        force : Optional[bool]
            Whether to bypass the actionability checks. Defaults to `false`.
        noWaitAfter : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.uncheck(
                timeout=timeout, force=force, noWaitAfter=noWaitAfter
            )
        )

    async def boundingBox(self) -> typing.Union[FloatRect, NoneType]:
        """ElementHandle.boundingBox

        This method returns the bounding box of the element (relative to the main frame), or `null` if the element is not visible.

        Returns
        -------
        Optional[{"x": float, "y": float, "width": float, "height": float}]
        """
        return mapping.from_maybe_impl(await self._impl_obj.boundingBox())

    async def screenshot(
        self,
        timeout: int = None,
        type: Literal["jpeg", "png"] = None,
        path: typing.Union[str, pathlib.Path] = None,
        quality: int = None,
        omitBackground: bool = None,
    ) -> bytes:
        """ElementHandle.screenshot

        This method waits for the actionability checks, then scrolls element into view before taking a screenshot. If the element is detached from DOM, the method throws an error.

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
        omitBackground : Optional[bool]
            Hides default white background and allows capturing screenshots with transparency. Not applicable to `jpeg` images. Defaults to `false`.

        Returns
        -------
        bytes
            Promise which resolves to buffer with the captured screenshot.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.screenshot(
                timeout=timeout,
                type=type,
                path=path,
                quality=quality,
                omitBackground=omitBackground,
            )
        )

    async def querySelector(
        self, selector: str
    ) -> typing.Union["ElementHandle", NoneType]:
        """ElementHandle.querySelector

        The method finds an element matching the specified selector in the `ElementHandle`'s subtree. See Working with selectors for more details. If no elements match the selector, the return value resolves to `null`.

        Parameters
        ----------
        selector : str
            A selector to query element for. See working with selectors for more details.

        Returns
        -------
        Optional[ElementHandle]
        """
        return mapping.from_impl_nullable(
            await self._impl_obj.querySelector(selector=selector)
        )

    async def querySelectorAll(self, selector: str) -> typing.List["ElementHandle"]:
        """ElementHandle.querySelectorAll

        The method finds all elements matching the specified selector in the `ElementHandle`s subtree. See Working with selectors for more details. If no elements match the selector, the return value resolves to `[]`.

        Parameters
        ----------
        selector : str
            A selector to query element for. See working with selectors for more details.

        Returns
        -------
        List[ElementHandle]
        """
        return mapping.from_impl_list(
            await self._impl_obj.querySelectorAll(selector=selector)
        )

    async def evalOnSelector(
        self,
        selector: str,
        expression: str,
        arg: typing.Any = None,
        force_expr: bool = None,
    ) -> typing.Any:
        """ElementHandle.evalOnSelector

        The method finds an element matching the specified selector in the `ElementHandle`s subtree and passes it as a first argument to `pageFunction`. See Working with selectors for more details. If no elements match the selector, the method throws an error.
        If `pageFunction` returns a Promise, then `frame.$eval` would wait for the promise to resolve and return its value.
        Examples:

        Parameters
        ----------
        selector : str
            A selector to query element for. See working with selectors for more details.
        expression : str
            Function to be evaluated in browser context
        force_expr : bool
            Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        arg : Optional[Any]
            Optional argument to pass to `pageFunction`

        Returns
        -------
        Any
            Promise which resolves to the return value of `pageFunction`
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.evalOnSelector(
                selector=selector,
                expression=expression,
                arg=mapping.to_impl(arg),
                force_expr=force_expr,
            )
        )

    async def evalOnSelectorAll(
        self,
        selector: str,
        expression: str,
        arg: typing.Any = None,
        force_expr: bool = None,
    ) -> typing.Any:
        """ElementHandle.evalOnSelectorAll

        The method finds all elements matching the specified selector in the `ElementHandle`'s subtree and passes an array of matched elements as a first argument to `pageFunction`. See Working with selectors for more details.
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
            A selector to query element for. See working with selectors for more details.
        expression : str
            Function to be evaluated in browser context
        force_expr : bool
            Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        arg : Optional[Any]
            Optional argument to pass to `pageFunction`

        Returns
        -------
        Any
            Promise which resolves to the return value of `pageFunction`
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.evalOnSelectorAll(
                selector=selector,
                expression=expression,
                arg=mapping.to_impl(arg),
                force_expr=force_expr,
            )
        )

    async def waitForElementState(
        self,
        state: Literal["disabled", "enabled", "hidden", "stable", "visible"],
        timeout: int = None,
    ) -> NoneType:
        """ElementHandle.waitForElementState

        Depending on the `state` parameter, this method waits for one of the actionability checks to pass. This method throws when the element is detached while waiting, unless waiting for the `"hidden"` state.

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
            await self._impl_obj.waitForElementState(state=state, timeout=timeout)
        )

    async def waitForSelector(
        self,
        selector: str,
        state: Literal["attached", "detached", "hidden", "visible"] = None,
        timeout: int = None,
    ) -> typing.Union["ElementHandle", NoneType]:
        """ElementHandle.waitForSelector

        Wait for the `selector` relative to the element handle to satisfy `state` option (either appear/disappear from dom, or become visible/hidden). If at the moment of calling the method `selector` already satisfies the condition, the method will return immediately. If the selector doesn't satisfy the condition for the `timeout` milliseconds, the function will throw.

        **NOTE** This method does not work across navigations, use page.waitForSelector(selector[, options]) instead.

        Parameters
        ----------
        selector : str
            A selector of an element to wait for, relative to the element handle. See working with selectors for more details.
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
            Promise that resolves when element specified by selector satisfies `state` option. Resolves to `null` if waiting for `hidden` or `detached`.
        """
        return mapping.from_impl_nullable(
            await self._impl_obj.waitForSelector(
                selector=selector, state=state, timeout=timeout
            )
        )


mapping.register(ElementHandleImpl, ElementHandle)


class Accessibility(AsyncBase):
    def __init__(self, obj: AccessibilityImpl):
        super().__init__(obj)

    async def snapshot(
        self, interestingOnly: bool = None, root: "ElementHandle" = None
    ) -> typing.Union[typing.Dict, NoneType]:
        """Accessibility.snapshot

        Captures the current state of the accessibility tree. The returned object represents the root accessible node of the page.

        **NOTE** The Chromium accessibility tree contains nodes that go unused on most platforms and by
        most screen readers. Playwright will discard them as well for an easier to process tree,
        unless `interestingOnly` is set to `false`.

        An example of dumping the entire accessibility tree:
        An example of logging the focused node's name:

        Parameters
        ----------
        interestingOnly : Optional[bool]
            Prune uninteresting nodes from the tree. Defaults to `true`.
        root : Optional[ElementHandle]
            The root DOM element for the snapshot. Defaults to the whole page.

        Returns
        -------
        Optional[Dict]
            An AXNode object with the following properties:
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.snapshot(
                interestingOnly=interestingOnly, root=mapping.to_impl(root)
            )
        )


mapping.register(AccessibilityImpl, Accessibility)


class FileChooser(AsyncBase):
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
    def isMultiple(self) -> bool:
        """FileChooser.isMultiple

        Returns whether this file chooser accepts multiple files.

        Returns
        -------
        bool
        """
        return mapping.from_maybe_impl(self._impl_obj.isMultiple)

    async def setFiles(
        self,
        files: typing.Union[
            str, FilePayload, typing.List[str], typing.List[FilePayload]
        ],
        timeout: int = None,
        noWaitAfter: bool = None,
    ) -> NoneType:
        """FileChooser.setFiles

        Sets the value of the file input this chooser is associated with. If some of the `filePaths` are relative paths, then they are resolved relative to the current working directory. For empty array, clears the selected files.

        Parameters
        ----------
        files : Union[str, {"name": str, "mimeType": str, "buffer": bytes}, List[str], List[{"name": str, "mimeType": str, "buffer": bytes}]]
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        noWaitAfter : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.setFiles(
                files=files, timeout=timeout, noWaitAfter=noWaitAfter
            )
        )


mapping.register(FileChooserImpl, FileChooser)


class Frame(AsyncBase):
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

        **NOTE** This value is calculated once when the frame is created, and will not update if the attribute is changed later.

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
    def parentFrame(self) -> typing.Union["Frame", NoneType]:
        """Frame.parentFrame

        Returns
        -------
        Optional[Frame]
            Parent frame, if any. Detached frames and main frames return `null`.
        """
        return mapping.from_impl_nullable(self._impl_obj.parentFrame)

    @property
    def childFrames(self) -> typing.List["Frame"]:
        """Frame.childFrames

        Returns
        -------
        List[Frame]
        """
        return mapping.from_impl_list(self._impl_obj.childFrames)

    async def goto(
        self,
        url: str,
        timeout: int = None,
        waitUntil: Literal["domcontentloaded", "load", "networkidle"] = None,
        referer: str = None,
    ) -> typing.Union["Response", NoneType]:
        """Frame.goto

        `frame.goto` will throw an error if:

        there's an SSL error (e.g. in case of self-signed certificates).
        target URL is invalid.
        the `timeout` is exceeded during navigation.
        the remote server does not respond or is unreachable.
        the main resource failed to load.

        `frame.goto` will not throw an error when any valid HTTP status code is returned by the remote server, including 404 "Not Found" and 500 "Internal Server Error".  The status code for such responses can be retrieved by calling response.status().

        **NOTE** `frame.goto` either throws an error or returns a main resource response. The only exceptions are navigation to `about:blank` or navigation to the same URL with a different hash, which would succeed and return `null`.

        **NOTE** Headless mode doesn't support navigation to a PDF document. See the upstream issue.

        Parameters
        ----------
        url : str
            URL to navigate frame to. The url should include scheme, e.g. `https://`.
        timeout : Optional[int]
            Maximum navigation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultNavigationTimeout(timeout), browserContext.setDefaultTimeout(timeout), page.setDefaultNavigationTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        waitUntil : Optional[Literal['domcontentloaded', 'load', 'networkidle']]
            When to consider navigation succeeded, defaults to `load`. Events can be either:
             - `'domcontentloaded'` - consider navigation to be finished when the `DOMContentLoaded` event is fired.
             - `'load'` - consider navigation to be finished when the `load` event is fired.
             - `'networkidle'` - consider navigation to be finished when there are no network connections for at least `500` ms.
        referer : Optional[str]
            Referer header value. If provided it will take preference over the referer header value set by page.setExtraHTTPHeaders().

        Returns
        -------
        Optional[Response]
            Promise which resolves to the main resource response. In case of multiple redirects, the navigation will resolve with the response of the last redirect.
        """
        return mapping.from_impl_nullable(
            await self._impl_obj.goto(
                url=url, timeout=timeout, waitUntil=waitUntil, referer=referer
            )
        )

    async def waitForNavigation(
        self,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]] = None,
        waitUntil: Literal["domcontentloaded", "load", "networkidle"] = None,
        timeout: int = None,
    ) -> typing.Union["Response", NoneType]:
        """Frame.waitForNavigation

        This resolves when the frame navigates to a new URL. It is useful for when you run code
        which will indirectly cause the frame to navigate. Consider this example:
        **NOTE** Usage of the History API to change the URL is considered a navigation.

        Parameters
        ----------
        url : Union[str, Pattern, typing.Callable[[str], bool], NoneType]
            URL string, URL regex pattern or predicate receiving URL to match while waiting for the navigation.
        waitUntil : Optional[Literal['domcontentloaded', 'load', 'networkidle']]
            When to consider navigation succeeded, defaults to `load`. Events can be either:
             - `'domcontentloaded'` - consider navigation to be finished when the `DOMContentLoaded` event is fired.
             - `'load'` - consider navigation to be finished when the `load` event is fired.
             - `'networkidle'` - consider navigation to be finished when there are no network connections for at least `500` ms.
        timeout : Optional[int]
            Maximum navigation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultNavigationTimeout(timeout), browserContext.setDefaultTimeout(timeout), page.setDefaultNavigationTimeout(timeout) or page.setDefaultTimeout(timeout) methods.

        Returns
        -------
        Optional[Response]
            Promise which resolves to the main resource response. In case of multiple redirects, the navigation will resolve with the response of the last redirect. In case of navigation to a different anchor or navigation due to History API usage, the navigation will resolve with `null`.
        """
        return mapping.from_impl_nullable(
            await self._impl_obj.waitForNavigation(
                url=self._wrap_handler(url), waitUntil=waitUntil, timeout=timeout
            )
        )

    async def waitForLoadState(
        self,
        state: Literal["domcontentloaded", "load", "networkidle"] = None,
        timeout: int = None,
    ) -> NoneType:
        """Frame.waitForLoadState

        This resolves when the frame reaches a required load state, `load` by default. The navigation must have been committed when this method is called. If current document has already reached the required state, resolves immediately.

        Parameters
        ----------
        state : Optional[Literal['domcontentloaded', 'load', 'networkidle']]
            Load state to wait for, defaults to `load`. If the state has been already reached while loading current document, the method resolves immediately.
             - `'load'` - wait for the `load` event to be fired.
             - `'domcontentloaded'` - wait for the `DOMContentLoaded` event to be fired.
             - `'networkidle'` - wait until there are no network connections for at least `500` ms.
        timeout : Optional[int]
            Maximum waiting time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultNavigationTimeout(timeout), browserContext.setDefaultTimeout(timeout), page.setDefaultNavigationTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.waitForLoadState(state=state, timeout=timeout)
        )

    async def frameElement(self) -> "ElementHandle":
        """Frame.frameElement

        This is an inverse of elementHandle.contentFrame(). Note that returned handle actually belongs to the parent frame.
        This method throws an error if the frame has been detached before `frameElement()` returns.

        Returns
        -------
        ElementHandle
            Promise that resolves with a `frame` or `iframe` element handle which corresponds to this frame.
        """
        return mapping.from_impl(await self._impl_obj.frameElement())

    async def evaluate(
        self, expression: str, arg: typing.Any = None, force_expr: bool = None
    ) -> typing.Any:
        """Frame.evaluate

        If the function passed to the `frame.evaluate` returns a Promise, then `frame.evaluate` would wait for the promise to resolve and return its value.
        If the function passed to the `frame.evaluate` returns a non-Serializable value, then `frame.evaluate` resolves to `undefined`. DevTools Protocol also supports transferring some additional values that are not serializable by `JSON`: `-0`, `NaN`, `Infinity`, `-Infinity`, and bigint literals.
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
            Promise which resolves to the return value of `pageFunction`
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.evaluate(
                expression=expression, arg=mapping.to_impl(arg), force_expr=force_expr
            )
        )

    async def evaluateHandle(
        self, expression: str, arg: typing.Any = None, force_expr: bool = None
    ) -> "JSHandle":
        """Frame.evaluateHandle

        The only difference between `frame.evaluate` and `frame.evaluateHandle` is that `frame.evaluateHandle` returns in-page object (JSHandle).
        If the function, passed to the `frame.evaluateHandle`, returns a Promise, then `frame.evaluateHandle` would wait for the promise to resolve and return its value.
        A string can also be passed in instead of a function.
        JSHandle instances can be passed as an argument to the `frame.evaluateHandle`:

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
            Promise which resolves to the return value of `pageFunction` as in-page object (JSHandle)
        """
        return mapping.from_impl(
            await self._impl_obj.evaluateHandle(
                expression=expression, arg=mapping.to_impl(arg), force_expr=force_expr
            )
        )

    async def querySelector(
        self, selector: str
    ) -> typing.Union["ElementHandle", NoneType]:
        """Frame.querySelector

        The method finds an element matching the specified selector within the frame. See Working with selectors for more details. If no elements match the selector, the return value resolves to `null`.

        Parameters
        ----------
        selector : str
            A selector to query frame for. See working with selectors for more details.

        Returns
        -------
        Optional[ElementHandle]
            Promise which resolves to ElementHandle pointing to the frame element.
        """
        return mapping.from_impl_nullable(
            await self._impl_obj.querySelector(selector=selector)
        )

    async def querySelectorAll(self, selector: str) -> typing.List["ElementHandle"]:
        """Frame.querySelectorAll

        The method finds all elements matching the specified selector within the frame. See Working with selectors for more details. If no elements match the selector, the return value resolves to `[]`.

        Parameters
        ----------
        selector : str
            A selector to query frame for. See working with selectors for more details.

        Returns
        -------
        List[ElementHandle]
            Promise which resolves to ElementHandles pointing to the frame elements.
        """
        return mapping.from_impl_list(
            await self._impl_obj.querySelectorAll(selector=selector)
        )

    async def waitForSelector(
        self,
        selector: str,
        timeout: int = None,
        state: Literal["attached", "detached", "hidden", "visible"] = None,
    ) -> typing.Union["ElementHandle", NoneType]:
        """Frame.waitForSelector

        Wait for the `selector` to satisfy `state` option (either appear/disappear from dom, or become visible/hidden). If at the moment of calling the method `selector` already satisfies the condition, the method will return immediately. If the selector doesn't satisfy the condition for the `timeout` milliseconds, the function will throw.
        This method works across navigations:

        Parameters
        ----------
        selector : str
            A selector of an element to wait for. See working with selectors for more details.
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
            Promise which resolves when element specified by selector satisfies `state` option. Resolves to `null` if waiting for `hidden` or `detached`.
        """
        return mapping.from_impl_nullable(
            await self._impl_obj.waitForSelector(
                selector=selector, timeout=timeout, state=state
            )
        )

    async def dispatchEvent(
        self,
        selector: str,
        type: str,
        eventInit: typing.Dict = None,
        timeout: int = None,
    ) -> NoneType:
        """Frame.dispatchEvent

        The snippet below dispatches the `click` event on the element. Regardless of the visibility state of the elment, `click` is dispatched. This is equivalend to calling `element.click()`.
        Under the hood, it creates an instance of an event based on the given `type`, initializes it with `eventInit` properties and dispatches it on the element. Events are `composed`, `cancelable` and bubble by default.
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
            A selector to search for element to use. If there are multiple elements satisfying the selector, the first will be double clicked. See working with selectors for more details.
        type : str
            DOM event type: `"click"`, `"dragstart"`, etc.
        eventInit : Optional[Dict]
            event-specific initialization properties.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.dispatchEvent(
                selector=selector,
                type=type,
                eventInit=mapping.to_impl(eventInit),
                timeout=timeout,
            )
        )

    async def evalOnSelector(
        self,
        selector: str,
        expression: str,
        arg: typing.Any = None,
        force_expr: bool = None,
    ) -> typing.Any:
        """Frame.evalOnSelector

        The method finds an element matching the specified selector within the frame and passes it as a first argument to `pageFunction`. See Working with selectors for more details. If no elements match the selector, the method throws an error.
        If `pageFunction` returns a Promise, then `frame.$eval` would wait for the promise to resolve and return its value.
        Examples:

        Parameters
        ----------
        selector : str
            A selector to query frame for. See working with selectors for more details.
        expression : str
            Function to be evaluated in browser context
        force_expr : bool
            Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        arg : Optional[Any]
            Optional argument to pass to `pageFunction`

        Returns
        -------
        Any
            Promise which resolves to the return value of `pageFunction`
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.evalOnSelector(
                selector=selector,
                expression=expression,
                arg=mapping.to_impl(arg),
                force_expr=force_expr,
            )
        )

    async def evalOnSelectorAll(
        self,
        selector: str,
        expression: str,
        arg: typing.Any = None,
        force_expr: bool = None,
    ) -> typing.Any:
        """Frame.evalOnSelectorAll

        The method finds all elements matching the specified selector within the frame and passes an array of matched elements as a first argument to `pageFunction`. See Working with selectors for more details.
        If `pageFunction` returns a Promise, then `frame.$$eval` would wait for the promise to resolve and return its value.
        Examples:

        Parameters
        ----------
        selector : str
            A selector to query frame for. See working with selectors for more details.
        expression : str
            Function to be evaluated in browser context
        force_expr : bool
            Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        arg : Optional[Any]
            Optional argument to pass to `pageFunction`

        Returns
        -------
        Any
            Promise which resolves to the return value of `pageFunction`
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.evalOnSelectorAll(
                selector=selector,
                expression=expression,
                arg=mapping.to_impl(arg),
                force_expr=force_expr,
            )
        )

    async def content(self) -> str:
        """Frame.content

        Gets the full HTML contents of the frame, including the doctype.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(await self._impl_obj.content())

    async def setContent(
        self,
        html: str,
        timeout: int = None,
        waitUntil: Literal["domcontentloaded", "load", "networkidle"] = None,
    ) -> NoneType:
        """Frame.setContent

        Parameters
        ----------
        html : str
            HTML markup to assign to the page.
        timeout : Optional[int]
            Maximum time in milliseconds for resources to load, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultNavigationTimeout(timeout), browserContext.setDefaultTimeout(timeout), page.setDefaultNavigationTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        waitUntil : Optional[Literal['domcontentloaded', 'load', 'networkidle']]
            When to consider navigation succeeded, defaults to `load`. Events can be either:
             - `'domcontentloaded'` - consider setting content to be finished when the `DOMContentLoaded` event is fired.
             - `'load'` - consider setting content to be finished when the `load` event is fired.
             - `'networkidle'` - consider setting content to be finished when there are no network connections for at least `500` ms.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.setContent(
                html=html, timeout=timeout, waitUntil=waitUntil
            )
        )

    def isDetached(self) -> bool:
        """Frame.isDetached

        Returns `true` if the frame has been detached, or `false` otherwise.

        Returns
        -------
        bool
        """
        return mapping.from_maybe_impl(self._impl_obj.isDetached())

    async def addScriptTag(
        self,
        url: str = None,
        path: typing.Union[str, pathlib.Path] = None,
        content: str = None,
        type: str = None,
    ) -> "ElementHandle":
        """Frame.addScriptTag

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
            which resolves to the added tag when the script's onload fires or when the script content was injected into frame.
        """
        return mapping.from_impl(
            await self._impl_obj.addScriptTag(
                url=url, path=path, content=content, type=type
            )
        )

    async def addStyleTag(
        self,
        url: str = None,
        path: typing.Union[str, pathlib.Path] = None,
        content: str = None,
    ) -> "ElementHandle":
        """Frame.addStyleTag

        Adds a `<link rel="stylesheet">` tag into the page with the desired url or a `<style type="text/css">` tag with the content.

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
            which resolves to the added tag when the stylesheet's onload fires or when the CSS content was injected into frame.
        """
        return mapping.from_impl(
            await self._impl_obj.addStyleTag(url=url, path=path, content=content)
        )

    async def click(
        self,
        selector: str,
        modifiers: typing.Union[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: MousePosition = None,
        delay: int = None,
        button: Literal["left", "middle", "right"] = None,
        clickCount: int = None,
        timeout: int = None,
        force: bool = None,
        noWaitAfter: bool = None,
    ) -> NoneType:
        """Frame.click

        This method clicks an element matching `selector` by performing the following steps:

        Find an element match matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        Wait for actionability checks on the matched element, unless `force` option is set. If the element is detached during the checks, the whole action is retried.
        Scroll the element into view if needed.
        Use page.mouse to click in the center of the element, or the specified `position`.
        Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.

        When all steps combined have not finished during the specified `timeout`, this method rejects with a TimeoutError. Passing zero timeout disables this.

        Parameters
        ----------
        selector : str
            A selector to search for element to click. If there are multiple elements satisfying the selector, the first will be clicked. See working with selectors for more details.
        modifiers : Optional[List[Literal['Alt', 'Control', 'Meta', 'Shift']]]
            Modifier keys to press. Ensures that only these modifiers are pressed during the click, and then restores current modifiers back. If not specified, currently pressed modifiers are used.
        position : Optional[{"x": float, "y": float}]
            A point to click relative to the top-left corner of element padding box. If not specified, clicks to some visible point of the element.
        delay : Optional[int]
            Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        button : Optional[Literal['left', 'middle', 'right']]
            Defaults to `left`.
        clickCount : Optional[int]
            defaults to 1. See UIEvent.detail.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        force : Optional[bool]
            Whether to bypass the actionability checks. Defaults to `false`.
        noWaitAfter : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.click(
                selector=selector,
                modifiers=modifiers,
                position=position,
                delay=delay,
                button=button,
                clickCount=clickCount,
                timeout=timeout,
                force=force,
                noWaitAfter=noWaitAfter,
            )
        )

    async def dblclick(
        self,
        selector: str,
        modifiers: typing.Union[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: MousePosition = None,
        delay: int = None,
        button: Literal["left", "middle", "right"] = None,
        timeout: int = None,
        force: bool = None,
        noWaitAfter: bool = None,
    ) -> NoneType:
        """Frame.dblclick

        This method double clicks an element matching `selector` by performing the following steps:

        Find an element match matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        Wait for actionability checks on the matched element, unless `force` option is set. If the element is detached during the checks, the whole action is retried.
        Scroll the element into view if needed.
        Use page.mouse to double click in the center of the element, or the specified `position`.
        Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set. Note that if the first click of the `dblclick()` triggers a navigation event, this method will reject.

        When all steps combined have not finished during the specified `timeout`, this method rejects with a TimeoutError. Passing zero timeout disables this.

        **NOTE** `frame.dblclick()` dispatches two `click` events and a single `dblclick` event.

        Parameters
        ----------
        selector : str
            A selector to search for element to double click. If there are multiple elements satisfying the selector, the first will be double clicked. See working with selectors for more details.
        modifiers : Optional[List[Literal['Alt', 'Control', 'Meta', 'Shift']]]
            Modifier keys to press. Ensures that only these modifiers are pressed during the double click, and then restores current modifiers back. If not specified, currently pressed modifiers are used.
        position : Optional[{"x": float, "y": float}]
            A point to double click relative to the top-left corner of element padding box. If not specified, double clicks to some visible point of the element.
        delay : Optional[int]
            Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        button : Optional[Literal['left', 'middle', 'right']]
            Defaults to `left`.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        force : Optional[bool]
            Whether to bypass the actionability checks. Defaults to `false`.
        noWaitAfter : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.dblclick(
                selector=selector,
                modifiers=modifiers,
                position=position,
                delay=delay,
                button=button,
                timeout=timeout,
                force=force,
                noWaitAfter=noWaitAfter,
            )
        )

    async def fill(
        self, selector: str, value: str, timeout: int = None, noWaitAfter: bool = None
    ) -> NoneType:
        """Frame.fill

        This method waits for an element matching `selector`, waits for actionability checks, focuses the element, fills it and triggers an `input` event after filling.
        If the element matching `selector` is not an `<input>`, `<textarea>` or `[contenteditable]` element, this method throws an error.
        Note that you can pass an empty string to clear the input field.
        To send fine-grained keyboard events, use `frame.type`.

        Parameters
        ----------
        selector : str
            A selector to query page for. See working with selectors for more details.
        value : str
            Value to fill for the `<input>`, `<textarea>` or `[contenteditable]` element.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        noWaitAfter : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.fill(
                selector=selector, value=value, timeout=timeout, noWaitAfter=noWaitAfter
            )
        )

    async def focus(self, selector: str, timeout: int = None) -> NoneType:
        """Frame.focus

        This method fetches an element with `selector` and focuses it.
        If there's no element matching `selector`, the method waits until a matching element appears in the DOM.

        Parameters
        ----------
        selector : str
            A selector of an element to focus. If there are multiple elements satisfying the selector, the first will be focused. See working with selectors for more details.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.focus(selector=selector, timeout=timeout)
        )

    async def textContent(
        self, selector: str, timeout: int = None
    ) -> typing.Union[str, NoneType]:
        """Frame.textContent

        Resolves to the `element.textContent`.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be picked. See working with selectors for more details.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.

        Returns
        -------
        Optional[str]
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.textContent(selector=selector, timeout=timeout)
        )

    async def innerText(self, selector: str, timeout: int = None) -> str:
        """Frame.innerText

        Resolves to the `element.innerText`.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be picked. See working with selectors for more details.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.innerText(selector=selector, timeout=timeout)
        )

    async def innerHTML(self, selector: str, timeout: int = None) -> str:
        """Frame.innerHTML

        Resolves to the `element.innerHTML`.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be picked. See working with selectors for more details.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.innerHTML(selector=selector, timeout=timeout)
        )

    async def getAttribute(
        self, selector: str, name: str, timeout: int = None
    ) -> typing.Union[str, NoneType]:
        """Frame.getAttribute

        Returns element attribute value.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be picked. See working with selectors for more details.
        name : str
            Attribute name to get the value for.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.

        Returns
        -------
        Optional[str]
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.getAttribute(
                selector=selector, name=name, timeout=timeout
            )
        )

    async def hover(
        self,
        selector: str,
        modifiers: typing.Union[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: MousePosition = None,
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

        When all steps combined have not finished during the specified `timeout`, this method rejects with a TimeoutError. Passing zero timeout disables this.

        Parameters
        ----------
        selector : str
            A selector to search for element to hover. If there are multiple elements satisfying the selector, the first will be hovered. See working with selectors for more details.
        modifiers : Optional[List[Literal['Alt', 'Control', 'Meta', 'Shift']]]
            Modifier keys to press. Ensures that only these modifiers are pressed during the hover, and then restores current modifiers back. If not specified, currently pressed modifiers are used.
        position : Optional[{"x": float, "y": float}]
            A point to hover relative to the top-left corner of element padding box. If not specified, hovers over some visible point of the element.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        force : Optional[bool]
            Whether to bypass the actionability checks. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.hover(
                selector=selector,
                modifiers=modifiers,
                position=position,
                timeout=timeout,
                force=force,
            )
        )

    async def selectOption(
        self,
        selector: str,
        values: typing.Union[
            str,
            "ElementHandle",
            SelectOption,
            typing.List[str],
            typing.List["ElementHandle"],
            typing.List[SelectOption],
        ] = None,
        timeout: int = None,
        noWaitAfter: bool = None,
    ) -> typing.List[str]:
        """Frame.selectOption

        Triggers a `change` and `input` event once all the provided options have been selected.
        If there's no `<select>` element matching `selector`, the method throws an error.

        Parameters
        ----------
        selector : str
            A selector to query frame for. See working with selectors for more details.
        values : Union[str, ElementHandle, {"value": Optional[str], "label": Optional[str], "index": Optional[str]}, List[str], List[ElementHandle], List[{"value": Optional[str], "label": Optional[str], "index": Optional[str]}], NoneType]
            Options to select. If the `<select>` has the `multiple` attribute, all matching options are selected, otherwise only the first option matching one of the passed options is selected. String values are equivalent to `{value:'string'}`. Option is considered matching if all specified properties match.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        noWaitAfter : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.

        Returns
        -------
        List[str]
            An array of option values that have been successfully selected.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.selectOption(
                selector=selector,
                values=mapping.to_impl(values),
                timeout=timeout,
                noWaitAfter=noWaitAfter,
            )
        )

    async def setInputFiles(
        self,
        selector: str,
        files: typing.Union[
            str,
            pathlib.Path,
            FilePayload,
            typing.List[str],
            typing.List[pathlib.Path],
            typing.List[FilePayload],
        ],
        timeout: int = None,
        noWaitAfter: bool = None,
    ) -> NoneType:
        """Frame.setInputFiles

        This method expects `selector` to point to an input element.
        Sets the value of the file input to these file paths or files. If some of the `filePaths` are relative paths, then they are resolved relative to the current working directory. For empty array, clears the selected files.

        Parameters
        ----------
        selector : str
            A selector to search for element to click. If there are multiple elements satisfying the selector, the first will be clicked. See working with selectors for more details.
        files : Union[str, pathlib.Path, {"name": str, "mimeType": str, "buffer": bytes}, List[str], List[pathlib.Path], List[{"name": str, "mimeType": str, "buffer": bytes}]]
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        noWaitAfter : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.setInputFiles(
                selector=selector, files=files, timeout=timeout, noWaitAfter=noWaitAfter
            )
        )

    async def type(
        self,
        selector: str,
        text: str,
        delay: int = None,
        timeout: int = None,
        noWaitAfter: bool = None,
    ) -> NoneType:
        """Frame.type

        Sends a `keydown`, `keypress`/`input`, and `keyup` event for each character in the text. `frame.type` can be used to send fine-grained keyboard events. To fill values in form fields, use `frame.fill`.
        To press a special key, like `Control` or `ArrowDown`, use `keyboard.press`.

        Parameters
        ----------
        selector : str
            A selector of an element to type into. If there are multiple elements satisfying the selector, the first will be used. See working with selectors for more details.
        text : str
            A text to type into a focused element.
        delay : Optional[int]
            Time to wait between key presses in milliseconds. Defaults to 0.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        noWaitAfter : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.type(
                selector=selector,
                text=text,
                delay=delay,
                timeout=timeout,
                noWaitAfter=noWaitAfter,
            )
        )

    async def press(
        self,
        selector: str,
        key: str,
        delay: int = None,
        timeout: int = None,
        noWaitAfter: bool = None,
    ) -> NoneType:
        """Frame.press

        `key` can specify the intended keyboardEvent.key value or a single character to generate the text for. A superset of the `key` values can be found here. Examples of the keys are:
        `F1` - `F12`, `Digit0`- `Digit9`, `KeyA`- `KeyZ`, `Backquote`, `Minus`, `Equal`, `Backslash`, `Backspace`, `Tab`, `Delete`, `Escape`, `ArrowDown`, `End`, `Enter`, `Home`, `Insert`, `PageDown`, `PageUp`, `ArrowRight`, `ArrowUp`, etc.
        Following modification shortcuts are also suported: `Shift`, `Control`, `Alt`, `Meta`, `ShiftLeft`.
        Holding down `Shift` will type the text that corresponds to the `key` in the upper case.
        If `key` is a single character, it is case-sensitive, so the values `a` and `A` will generate different respective texts.
        Shortcuts such as `key: "Control+o"` or `key: "Control+Shift+T"` are supported as well. When speficied with the modifier, modifier is pressed and being held while the subsequent key is being pressed.

        Parameters
        ----------
        selector : str
            A selector of an element to type into. If there are multiple elements satisfying the selector, the first will be used. See working with selectors for more details.
        key : str
            Name of the key to press or a character to generate, such as `ArrowLeft` or `a`.
        delay : Optional[int]
            Time to wait between `keydown` and `keyup` in milliseconds. Defaults to 0.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        noWaitAfter : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.press(
                selector=selector,
                key=key,
                delay=delay,
                timeout=timeout,
                noWaitAfter=noWaitAfter,
            )
        )

    async def check(
        self,
        selector: str,
        timeout: int = None,
        force: bool = None,
        noWaitAfter: bool = None,
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

        When all steps combined have not finished during the specified `timeout`, this method rejects with a TimeoutError. Passing zero timeout disables this.

        Parameters
        ----------
        selector : str
            A selector to search for checkbox to check. If there are multiple elements satisfying the selector, the first will be checked. See working with selectors for more details.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        force : Optional[bool]
            Whether to bypass the actionability checks. Defaults to `false`.
        noWaitAfter : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.check(
                selector=selector, timeout=timeout, force=force, noWaitAfter=noWaitAfter
            )
        )

    async def uncheck(
        self,
        selector: str,
        timeout: int = None,
        force: bool = None,
        noWaitAfter: bool = None,
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

        When all steps combined have not finished during the specified `timeout`, this method rejects with a TimeoutError. Passing zero timeout disables this.

        Parameters
        ----------
        selector : str
            A selector to search for uncheckbox to check. If there are multiple elements satisfying the selector, the first will be checked. See working with selectors for more details.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        force : Optional[bool]
            Whether to bypass the actionability checks. Defaults to `false`.
        noWaitAfter : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.uncheck(
                selector=selector, timeout=timeout, force=force, noWaitAfter=noWaitAfter
            )
        )

    async def waitForTimeout(self, timeout: int) -> NoneType:
        """Frame.waitForTimeout

        Returns a promise that resolves after the timeout.
        Note that `frame.waitForTimeout()` should only be used for debugging. Tests using the timer in production are going to be flaky. Use signals such as network events, selectors becoming visible and others instead.

        Parameters
        ----------
        timeout : int
            A timeout to wait for
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.waitForTimeout(timeout=timeout)
        )

    async def waitForFunction(
        self,
        expression: str,
        arg: typing.Any = None,
        force_expr: bool = None,
        timeout: int = None,
        polling: typing.Union[int, Literal["raf"]] = None,
    ) -> "JSHandle":
        """Frame.waitForFunction

        The `waitForFunction` can be used to observe viewport size change:

        To pass an argument from Node.js to the predicate of `frame.waitForFunction` function:

        Parameters
        ----------
        expression : str
            Function to be evaluated in browser context
        force_expr : bool
            Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        arg : Optional[Any]
            Optional argument to pass to `pageFunction`
        timeout : Optional[int]
            maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        polling : Union[int, 'raf', NoneType]
            If `polling` is `'raf'`, then `pageFunction` is constantly executed in `requestAnimationFrame` callback. If `polling` is a number, then it is treated as an interval in milliseconds at which the function would be executed. Defaults to `raf`.

        Returns
        -------
        JSHandle
            Promise which resolves when the `pageFunction` returns a truthy value. It resolves to a JSHandle of the truthy value.
        """
        return mapping.from_impl(
            await self._impl_obj.waitForFunction(
                expression=expression,
                arg=mapping.to_impl(arg),
                force_expr=force_expr,
                timeout=timeout,
                polling=polling,
            )
        )

    async def title(self) -> str:
        """Frame.title

        Returns
        -------
        str
            The page's title.
        """
        return mapping.from_maybe_impl(await self._impl_obj.title())

    def expect_load_state(
        self,
        state: Literal["domcontentloaded", "load", "networkidle"] = None,
        timeout: int = None,
    ) -> AsyncEventContextManager[typing.Union["Response", NoneType]]:
        return AsyncEventContextManager(self._impl_obj.waitForLoadState(state, timeout))

    def expect_navigation(
        self,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]] = None,
        waitUntil: Literal["domcontentloaded", "load", "networkidle"] = None,
        timeout: int = None,
    ) -> AsyncEventContextManager[typing.Union["Response", NoneType]]:
        return AsyncEventContextManager(
            self._impl_obj.waitForNavigation(url, waitUntil, timeout)
        )


mapping.register(FrameImpl, Frame)


class Worker(AsyncBase):
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

    async def evaluate(
        self, expression: str, arg: typing.Any = None, force_expr: bool = None
    ) -> typing.Any:
        """Worker.evaluate

        If the function passed to the `worker.evaluate` returns a Promise, then `worker.evaluate` would wait for the promise to resolve and return its value.
        If the function passed to the `worker.evaluate` returns a non-Serializable value, then `worker.evaluate` resolves to `undefined`. DevTools Protocol also supports transferring some additional values that are not serializable by `JSON`: `-0`, `NaN`, `Infinity`, `-Infinity`, and bigint literals.

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
            Promise which resolves to the return value of `pageFunction`
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.evaluate(
                expression=expression, arg=mapping.to_impl(arg), force_expr=force_expr
            )
        )

    async def evaluateHandle(
        self, expression: str, arg: typing.Any = None, force_expr: bool = None
    ) -> "JSHandle":
        """Worker.evaluateHandle

        The only difference between `worker.evaluate` and `worker.evaluateHandle` is that `worker.evaluateHandle` returns in-page object (JSHandle).
        If the function passed to the `worker.evaluateHandle` returns a Promise, then `worker.evaluateHandle` would wait for the promise to resolve and return its value.

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
            Promise which resolves to the return value of `pageFunction` as in-page object (JSHandle)
        """
        return mapping.from_impl(
            await self._impl_obj.evaluateHandle(
                expression=expression, arg=mapping.to_impl(arg), force_expr=force_expr
            )
        )


mapping.register(WorkerImpl, Worker)


class Selectors(AsyncBase):
    def __init__(self, obj: SelectorsImpl):
        super().__init__(obj)

    async def register(
        self,
        name: str,
        source: str = None,
        path: typing.Union[str, pathlib.Path] = None,
        contentScript: bool = None,
    ) -> NoneType:
        """Selectors.register

        An example of registering selector engine that queries elements based on a tag name:

        Parameters
        ----------
        name : str
            Name that is used in selectors as a prefix, e.g. `{name: 'foo'}` enables `foo=myselectorbody` selectors. May only contain `[a-zA-Z0-9_]` characters.
        source : Optional[str]
            Script that evaluates to a selector engine instance.
        contentScript : Optional[bool]
            Whether to run this selector engine in isolated JavaScript environment. This environment has access to the same DOM, but not any JavaScript objects from the frame's scripts. Defaults to `false`. Note that running as a content script is not guaranteed when this engine is used together with other registered engines.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.register(
                name=name, source=source, path=path, contentScript=contentScript
            )
        )


mapping.register(SelectorsImpl, Selectors)


class ConsoleMessage(AsyncBase):
    def __init__(self, obj: ConsoleMessageImpl):
        super().__init__(obj)

    @property
    def type(self) -> str:
        """ConsoleMessage.type

        One of the following values: `'log'`, `'debug'`, `'info'`, `'error'`, `'warning'`, `'dir'`, `'dirxml'`, `'table'`, `'trace'`, `'clear'`, `'startGroup'`, `'startGroupCollapsed'`, `'endGroup'`, `'assert'`, `'profile'`, `'profileEnd'`, `'count'`, `'timeEnd'`.

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
    def location(self) -> ConsoleMessageLocation:
        """ConsoleMessage.location

        Returns
        -------
        {"url": str, "lineNumber": int, "columnNumber": int}
        """
        return mapping.from_maybe_impl(self._impl_obj.location)


mapping.register(ConsoleMessageImpl, ConsoleMessage)


class Dialog(AsyncBase):
    def __init__(self, obj: DialogImpl):
        super().__init__(obj)

    @property
    def type(self) -> str:
        """Dialog.type

        Returns
        -------
        str
            Dialog's type, can be one of `alert`, `beforeunload`, `confirm` or `prompt`.
        """
        return mapping.from_maybe_impl(self._impl_obj.type)

    @property
    def message(self) -> str:
        """Dialog.message

        Returns
        -------
        str
            A message displayed in the dialog.
        """
        return mapping.from_maybe_impl(self._impl_obj.message)

    @property
    def defaultValue(self) -> str:
        """Dialog.defaultValue

        Returns
        -------
        str
            If dialog is prompt, returns default prompt value. Otherwise, returns empty string.
        """
        return mapping.from_maybe_impl(self._impl_obj.defaultValue)

    async def accept(self, promptText: str = None) -> NoneType:
        """Dialog.accept

        Parameters
        ----------
        promptText : Optional[str]
            A text to enter in prompt. Does not cause any effects if the dialog's `type` is not prompt.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.accept(promptText=promptText)
        )

    async def dismiss(self) -> NoneType:
        """Dialog.dismiss"""
        return mapping.from_maybe_impl(await self._impl_obj.dismiss())


mapping.register(DialogImpl, Dialog)


class Download(AsyncBase):
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
    def suggestedFilename(self) -> str:
        """Download.suggestedFilename

        Returns suggested filename for this download. It is typically computed by the browser from the `Content-Disposition` response header or the `download` attribute. See the spec on whatwg. Different browsers can use different logic for computing it.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.suggestedFilename)

    async def delete(self) -> NoneType:
        """Download.delete

        Deletes the downloaded file.
        """
        return mapping.from_maybe_impl(await self._impl_obj.delete())

    async def failure(self) -> typing.Union[str, NoneType]:
        """Download.failure

        Returns download error if any.

        Returns
        -------
        Optional[str]
        """
        return mapping.from_maybe_impl(await self._impl_obj.failure())

    async def path(self) -> typing.Union[str, NoneType]:
        """Download.path

        Returns path to the downloaded file in case of successful download.

        Returns
        -------
        Optional[str]
        """
        return mapping.from_maybe_impl(await self._impl_obj.path())

    async def saveAs(self, path: typing.Union[str, pathlib.Path]) -> NoneType:
        """Download.saveAs

        Saves the download to a user-specified path.

        Parameters
        ----------
        path : Union[str, pathlib.Path]
            Path where the download should be saved.
        """
        return mapping.from_maybe_impl(await self._impl_obj.saveAs(path=path))


mapping.register(DownloadImpl, Download)


class Video(AsyncBase):
    def __init__(self, obj: VideoImpl):
        super().__init__(obj)

    async def path(self) -> str:
        """Video.path

        Returns the file system path this video will be recorded to. The video is guaranteed to be written to the filesystem upon closing the browser context.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(await self._impl_obj.path())


mapping.register(VideoImpl, Video)


class BindingCall(AsyncBase):
    def __init__(self, obj: BindingCallImpl):
        super().__init__(obj)

    async def call(self, func: typing.Callable) -> NoneType:
        return mapping.from_maybe_impl(
            await self._impl_obj.call(func=self._wrap_handler(func))
        )


mapping.register(BindingCallImpl, BindingCall)


class Page(AsyncBase):
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
    def context(self) -> "BrowserContext":
        """Page.context

        Get the browser context that the page belongs to.

        Returns
        -------
        BrowserContext
        """
        return mapping.from_impl(self._impl_obj.context)

    @property
    def mainFrame(self) -> "Frame":
        """Page.mainFrame

        Page is guaranteed to have a main frame which persists during navigations.

        Returns
        -------
        Frame
            The page's main frame.
        """
        return mapping.from_impl(self._impl_obj.mainFrame)

    @property
    def frames(self) -> typing.List["Frame"]:
        """Page.frames

        Returns
        -------
        List[Frame]
            An array of all frames attached to the page.
        """
        return mapping.from_impl_list(self._impl_obj.frames)

    @property
    def url(self) -> str:
        """Page.url

        This is a shortcut for page.mainFrame().url()

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(self._impl_obj.url)

    @property
    def workers(self) -> typing.List["Worker"]:
        """Page.workers

        **NOTE** This does not contain ServiceWorkers

        Returns
        -------
        List[Worker]
            This method returns all of the dedicated WebWorkers associated with the page.
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

    def remove_listener(self, event: str, f: typing.Any) -> NoneType:
        return mapping.from_maybe_impl(
            self._impl_obj.remove_listener(event=event, f=mapping.to_impl(f))
        )

    async def opener(self) -> typing.Union["Page", NoneType]:
        """Page.opener

        Returns
        -------
        Optional[Page]
            Promise which resolves to the opener for popup pages and `null` for others. If the opener has been closed already the promise may resolve to `null`.
        """
        return mapping.from_impl_nullable(await self._impl_obj.opener())

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
        url : Union[str, Pattern, typing.Callable[[str], bool], NoneType]
            A glob pattern, regex pattern or predicate receiving frame's `url` as a URL object.

        Returns
        -------
        Optional[Frame]
            frame matching the criteria. Returns `null` if no frame matches.
        """
        return mapping.from_impl_nullable(
            self._impl_obj.frame(name=name, url=self._wrap_handler(url))
        )

    def setDefaultNavigationTimeout(self, timeout: int) -> NoneType:
        """Page.setDefaultNavigationTimeout

        This setting will change the default maximum navigation time for the following methods and related shortcuts:

        page.goBack([options])
        page.goForward([options])
        page.goto(url[, options])
        page.reload([options])
        page.setContent(html[, options])
        page.waitForNavigation([options])

        **NOTE** `page.setDefaultNavigationTimeout` takes priority over `page.setDefaultTimeout`, `browserContext.setDefaultTimeout` and `browserContext.setDefaultNavigationTimeout`.

        Parameters
        ----------
        timeout : int
            Maximum navigation time in milliseconds
        """
        return mapping.from_maybe_impl(
            self._impl_obj.setDefaultNavigationTimeout(timeout=timeout)
        )

    def setDefaultTimeout(self, timeout: int) -> NoneType:
        """Page.setDefaultTimeout

        This setting will change the default maximum time for all the methods accepting `timeout` option.

        **NOTE** `page.setDefaultNavigationTimeout` takes priority over `page.setDefaultTimeout`.

        Parameters
        ----------
        timeout : int
            Maximum time in milliseconds
        """
        return mapping.from_maybe_impl(
            self._impl_obj.setDefaultTimeout(timeout=timeout)
        )

    async def querySelector(
        self, selector: str
    ) -> typing.Union["ElementHandle", NoneType]:
        """Page.querySelector

        The method finds an element matching the specified selector within the page. If no elements match the selector, the return value resolves to `null`.
        Shortcut for page.mainFrame().$(selector).

        Parameters
        ----------
        selector : str
            A selector to query page for. See working with selectors for more details.

        Returns
        -------
        Optional[ElementHandle]
        """
        return mapping.from_impl_nullable(
            await self._impl_obj.querySelector(selector=selector)
        )

    async def querySelectorAll(self, selector: str) -> typing.List["ElementHandle"]:
        """Page.querySelectorAll

        The method finds all elements matching the specified selector within the page. If no elements match the selector, the return value resolves to `[]`.
        Shortcut for page.mainFrame().$$(selector).

        Parameters
        ----------
        selector : str
            A selector to query page for. See working with selectors for more details.

        Returns
        -------
        List[ElementHandle]
        """
        return mapping.from_impl_list(
            await self._impl_obj.querySelectorAll(selector=selector)
        )

    async def waitForSelector(
        self,
        selector: str,
        timeout: int = None,
        state: Literal["attached", "detached", "hidden", "visible"] = None,
    ) -> typing.Union["ElementHandle", NoneType]:
        """Page.waitForSelector

        Wait for the `selector` to satisfy `state` option (either appear/disappear from dom, or become visible/hidden). If at the moment of calling the method `selector` already satisfies the condition, the method will return immediately. If the selector doesn't satisfy the condition for the `timeout` milliseconds, the function will throw.
        This method works across navigations:

        Shortcut for page.mainFrame().waitForSelector(selector[, options]).

        Parameters
        ----------
        selector : str
            A selector of an element to wait for. See working with selectors for more details.
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
            Promise which resolves when element specified by selector satisfies `state` option. Resolves to `null` if waiting for `hidden` or `detached`.
        """
        return mapping.from_impl_nullable(
            await self._impl_obj.waitForSelector(
                selector=selector, timeout=timeout, state=state
            )
        )

    async def dispatchEvent(
        self,
        selector: str,
        type: str,
        eventInit: typing.Dict = None,
        timeout: int = None,
    ) -> NoneType:
        """Page.dispatchEvent

        The snippet below dispatches the `click` event on the element. Regardless of the visibility state of the elment, `click` is dispatched. This is equivalend to calling `element.click()`.
        Under the hood, it creates an instance of an event based on the given `type`, initializes it with `eventInit` properties and dispatches it on the element. Events are `composed`, `cancelable` and bubble by default.
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
            A selector to search for element to use. If there are multiple elements satisfying the selector, the first will be used. See working with selectors for more details.
        type : str
            DOM event type: `"click"`, `"dragstart"`, etc.
        eventInit : Optional[Dict]
            event-specific initialization properties.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.dispatchEvent(
                selector=selector,
                type=type,
                eventInit=mapping.to_impl(eventInit),
                timeout=timeout,
            )
        )

    async def evaluate(
        self, expression: str, arg: typing.Any = None, force_expr: bool = None
    ) -> typing.Any:
        """Page.evaluate

        If the function passed to the `page.evaluate` returns a Promise, then `page.evaluate` would wait for the promise to resolve and return its value.
        If the function passed to the `page.evaluate` returns a non-Serializable value, then `page.evaluate` resolves to `undefined`. DevTools Protocol also supports transferring some additional values that are not serializable by `JSON`: `-0`, `NaN`, `Infinity`, `-Infinity`, and bigint literals.
        Passing argument to `pageFunction`:
        A string can also be passed in instead of a function:
        ElementHandle instances can be passed as an argument to the `page.evaluate`:
        Shortcut for page.mainFrame().evaluate(pageFunction[, arg]).

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
            Promise which resolves to the return value of `pageFunction`
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.evaluate(
                expression=expression, arg=mapping.to_impl(arg), force_expr=force_expr
            )
        )

    async def evaluateHandle(
        self, expression: str, arg: typing.Any = None, force_expr: bool = None
    ) -> "JSHandle":
        """Page.evaluateHandle

        The only difference between `page.evaluate` and `page.evaluateHandle` is that `page.evaluateHandle` returns in-page object (JSHandle).
        If the function passed to the `page.evaluateHandle` returns a Promise, then `page.evaluateHandle` would wait for the promise to resolve and return its value.
        A string can also be passed in instead of a function:
        JSHandle instances can be passed as an argument to the `page.evaluateHandle`:

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
            Promise which resolves to the return value of `pageFunction` as in-page object (JSHandle)
        """
        return mapping.from_impl(
            await self._impl_obj.evaluateHandle(
                expression=expression, arg=mapping.to_impl(arg), force_expr=force_expr
            )
        )

    async def evalOnSelector(
        self,
        selector: str,
        expression: str,
        arg: typing.Any = None,
        force_expr: bool = None,
    ) -> typing.Any:
        """Page.evalOnSelector

        The method finds an element matching the specified selector within the page and passes it as a first argument to `pageFunction`. If no elements match the selector, the method throws an error.
        If `pageFunction` returns a Promise, then `page.$eval` would wait for the promise to resolve and return its value.
        Examples:
        Shortcut for page.mainFrame().$eval(selector, pageFunction).

        Parameters
        ----------
        selector : str
            A selector to query page for. See working with selectors for more details.
        expression : str
            Function to be evaluated in browser context
        force_expr : bool
            Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        arg : Optional[Any]
            Optional argument to pass to `pageFunction`

        Returns
        -------
        Any
            Promise which resolves to the return value of `pageFunction`
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.evalOnSelector(
                selector=selector,
                expression=expression,
                arg=mapping.to_impl(arg),
                force_expr=force_expr,
            )
        )

    async def evalOnSelectorAll(
        self,
        selector: str,
        expression: str,
        arg: typing.Any = None,
        force_expr: bool = None,
    ) -> typing.Any:
        """Page.evalOnSelectorAll

        The method finds all elements matching the specified selector within the page and passes an array of matched elements as a first argument to `pageFunction`.
        If `pageFunction` returns a Promise, then `page.$$eval` would wait for the promise to resolve and return its value.
        Examples:

        Parameters
        ----------
        selector : str
            A selector to query page for. See working with selectors for more details.
        expression : str
            Function to be evaluated in browser context
        force_expr : bool
            Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        arg : Optional[Any]
            Optional argument to pass to `pageFunction`

        Returns
        -------
        Any
            Promise which resolves to the return value of `pageFunction`
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.evalOnSelectorAll(
                selector=selector,
                expression=expression,
                arg=mapping.to_impl(arg),
                force_expr=force_expr,
            )
        )

    async def addScriptTag(
        self,
        url: str = None,
        path: typing.Union[str, pathlib.Path] = None,
        content: str = None,
        type: str = None,
    ) -> "ElementHandle":
        """Page.addScriptTag

        Adds a `<script>` tag into the page with the desired url or content.
        Shortcut for page.mainFrame().addScriptTag(options).

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
            which resolves to the added tag when the script's onload fires or when the script content was injected into frame.
        """
        return mapping.from_impl(
            await self._impl_obj.addScriptTag(
                url=url, path=path, content=content, type=type
            )
        )

    async def addStyleTag(
        self,
        url: str = None,
        path: typing.Union[str, pathlib.Path] = None,
        content: str = None,
    ) -> "ElementHandle":
        """Page.addStyleTag

        Adds a `<link rel="stylesheet">` tag into the page with the desired url or a `<style type="text/css">` tag with the content.
        Shortcut for page.mainFrame().addStyleTag(options).

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
            which resolves to the added tag when the stylesheet's onload fires or when the CSS content was injected into frame.
        """
        return mapping.from_impl(
            await self._impl_obj.addStyleTag(url=url, path=path, content=content)
        )

    async def exposeFunction(self, name: str, binding: typing.Callable) -> NoneType:
        """Page.exposeFunction

        The method adds a function called `name` on the `window` object of every frame in the page.
        When called, the function executes `playwrightFunction` in Node.js and returns a Promise which resolves to the return value of `playwrightFunction`.
        If the `playwrightFunction` returns a Promise, it will be awaited.
        See browserContext.exposeFunction(name, playwrightFunction) for context-wide exposed function.

        **NOTE** Functions installed via `page.exposeFunction` survive navigations.

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
            await self._impl_obj.exposeFunction(
                name=name, binding=self._wrap_handler(binding)
            )
        )

    async def exposeBinding(
        self, name: str, binding: typing.Callable, handle: bool = None
    ) -> NoneType:
        """Page.exposeBinding

        The method adds a function called `name` on the `window` object of every frame in this page.
        When called, the function executes `playwrightBinding` in Node.js and returns a Promise which resolves to the return value of `playwrightBinding`.
        If the `playwrightBinding` returns a Promise, it will be awaited.
        The first argument of the `playwrightBinding` function contains information about the caller:
        `{ browserContext: BrowserContext, page: Page, frame: Frame }`.
        See browserContext.exposeBinding(name, playwrightBinding) for the context-wide version.

        **NOTE** Functions installed via `page.exposeBinding` survive navigations.

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
            await self._impl_obj.exposeBinding(
                name=name, binding=self._wrap_handler(binding), handle=handle
            )
        )

    async def setExtraHTTPHeaders(self, headers: typing.Dict[str, str]) -> NoneType:
        """Page.setExtraHTTPHeaders

        The extra HTTP headers will be sent with every request the page initiates.

        **NOTE** page.setExtraHTTPHeaders does not guarantee the order of headers in the outgoing requests.

        Parameters
        ----------
        headers : Dict[str, str]
            An object containing additional HTTP headers to be sent with every request. All header values must be strings.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.setExtraHTTPHeaders(headers=mapping.to_impl(headers))
        )

    async def content(self) -> str:
        """Page.content

        Gets the full HTML contents of the page, including the doctype.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(await self._impl_obj.content())

    async def setContent(
        self,
        html: str,
        timeout: int = None,
        waitUntil: Literal["domcontentloaded", "load", "networkidle"] = None,
    ) -> NoneType:
        """Page.setContent

        Parameters
        ----------
        html : str
            HTML markup to assign to the page.
        timeout : Optional[int]
            Maximum time in milliseconds for resources to load, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultNavigationTimeout(timeout), browserContext.setDefaultTimeout(timeout), page.setDefaultNavigationTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        waitUntil : Optional[Literal['domcontentloaded', 'load', 'networkidle']]
            When to consider setting markup succeeded, defaults to `load`. Given an array of event strings, setting content is considered to be successful after all events have been fired. Events can be either:
             - `'load'` - consider setting content to be finished when the `load` event is fired.
             - `'domcontentloaded'` - consider setting content to be finished when the `DOMContentLoaded` event is fired.
             - `'networkidle'` - consider setting content to be finished when there are no network connections for at least `500` ms.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.setContent(
                html=html, timeout=timeout, waitUntil=waitUntil
            )
        )

    async def goto(
        self,
        url: str,
        timeout: int = None,
        waitUntil: Literal["domcontentloaded", "load", "networkidle"] = None,
        referer: str = None,
    ) -> typing.Union["Response", NoneType]:
        """Page.goto

        `page.goto` will throw an error if:

        there's an SSL error (e.g. in case of self-signed certificates).
        target URL is invalid.
        the `timeout` is exceeded during navigation.
        the remote server does not respond or is unreachable.
        the main resource failed to load.

        `page.goto` will not throw an error when any valid HTTP status code is returned by the remote server, including 404 "Not Found" and 500 "Internal Server Error".  The status code for such responses can be retrieved by calling response.status().

        **NOTE** `page.goto` either throws an error or returns a main resource response. The only exceptions are navigation to `about:blank` or navigation to the same URL with a different hash, which would succeed and return `null`.

        **NOTE** Headless mode doesn't support navigation to a PDF document. See the upstream issue.

        Shortcut for page.mainFrame().goto(url[, options])

        Parameters
        ----------
        url : str
            URL to navigate page to. The url should include scheme, e.g. `https://`.
        timeout : Optional[int]
            Maximum navigation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultNavigationTimeout(timeout), browserContext.setDefaultTimeout(timeout), page.setDefaultNavigationTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        waitUntil : Optional[Literal['domcontentloaded', 'load', 'networkidle']]
            When to consider navigation succeeded, defaults to `load`. Events can be either:
             - `'domcontentloaded'` - consider navigation to be finished when the `DOMContentLoaded` event is fired.
             - `'load'` - consider navigation to be finished when the `load` event is fired.
             - `'networkidle'` - consider navigation to be finished when there are no network connections for at least `500` ms.
        referer : Optional[str]
            Referer header value. If provided it will take preference over the referer header value set by page.setExtraHTTPHeaders().

        Returns
        -------
        Optional[Response]
            Promise which resolves to the main resource response. In case of multiple redirects, the navigation will resolve with the response of the last redirect.
        """
        return mapping.from_impl_nullable(
            await self._impl_obj.goto(
                url=url, timeout=timeout, waitUntil=waitUntil, referer=referer
            )
        )

    async def reload(
        self,
        timeout: int = None,
        waitUntil: Literal["domcontentloaded", "load", "networkidle"] = None,
    ) -> typing.Union["Response", NoneType]:
        """Page.reload

        Parameters
        ----------
        timeout : Optional[int]
            Maximum navigation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultNavigationTimeout(timeout), browserContext.setDefaultTimeout(timeout), page.setDefaultNavigationTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        waitUntil : Optional[Literal['domcontentloaded', 'load', 'networkidle']]
            When to consider navigation succeeded, defaults to `load`. Events can be either:
             - `'domcontentloaded'` - consider navigation to be finished when the `DOMContentLoaded` event is fired.
             - `'load'` - consider navigation to be finished when the `load` event is fired.
             - `'networkidle'` - consider navigation to be finished when there are no network connections for at least `500` ms.

        Returns
        -------
        Optional[Response]
            Promise which resolves to the main resource response. In case of multiple redirects, the navigation will resolve with the response of the last redirect.
        """
        return mapping.from_impl_nullable(
            await self._impl_obj.reload(timeout=timeout, waitUntil=waitUntil)
        )

    async def waitForLoadState(
        self,
        state: Literal["domcontentloaded", "load", "networkidle"] = None,
        timeout: int = None,
    ) -> NoneType:
        """Page.waitForLoadState

        This resolves when the page reaches a required load state, `load` by default. The navigation must have been committed when this method is called. If current document has already reached the required state, resolves immediately.
        Shortcut for page.mainFrame().waitForLoadState([options]).

        Parameters
        ----------
        state : Optional[Literal['domcontentloaded', 'load', 'networkidle']]
            Load state to wait for, defaults to `load`. If the state has been already reached while loading current document, the method resolves immediately.
             - `'load'` - wait for the `load` event to be fired.
             - `'domcontentloaded'` - wait for the `DOMContentLoaded` event to be fired.
             - `'networkidle'` - wait until there are no network connections for at least `500` ms.
        timeout : Optional[int]
            Maximum waiting time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultNavigationTimeout(timeout), browserContext.setDefaultTimeout(timeout), page.setDefaultNavigationTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.waitForLoadState(state=state, timeout=timeout)
        )

    async def waitForNavigation(
        self,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]] = None,
        waitUntil: Literal["domcontentloaded", "load", "networkidle"] = None,
        timeout: int = None,
    ) -> typing.Union["Response", NoneType]:
        """Page.waitForNavigation

        This resolves when the page navigates to a new URL or reloads. It is useful for when you run code
        which will indirectly cause the page to navigate. e.g. The click target has an `onclick` handler that triggers navigation from a `setTimeout`. Consider this example:
        **NOTE** Usage of the History API to change the URL is considered a navigation.
        Shortcut for page.mainFrame().waitForNavigation(options).

        Parameters
        ----------
        url : Union[str, Pattern, typing.Callable[[str], bool], NoneType]
            A glob pattern, regex pattern or predicate receiving URL to match while waiting for the navigation.
        waitUntil : Optional[Literal['domcontentloaded', 'load', 'networkidle']]
            When to consider navigation succeeded, defaults to `load`. Events can be either:
             - `'domcontentloaded'` - consider navigation to be finished when the `DOMContentLoaded` event is fired.
             - `'load'` - consider navigation to be finished when the `load` event is fired.
             - `'networkidle'` - consider navigation to be finished when there are no network connections for at least `500` ms.
        timeout : Optional[int]
            Maximum navigation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultNavigationTimeout(timeout), browserContext.setDefaultTimeout(timeout), page.setDefaultNavigationTimeout(timeout) or page.setDefaultTimeout(timeout) methods.

        Returns
        -------
        Optional[Response]
            Promise which resolves to the main resource response. In case of multiple redirects, the navigation will resolve with the response of the last redirect. In case of navigation to a different anchor or navigation due to History API usage, the navigation will resolve with `null`.
        """
        return mapping.from_impl_nullable(
            await self._impl_obj.waitForNavigation(
                url=self._wrap_handler(url), waitUntil=waitUntil, timeout=timeout
            )
        )

    async def waitForRequest(
        self,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]] = None,
        predicate: typing.Union[typing.Callable[["Request"], bool]] = None,
        timeout: int = None,
    ) -> "Request":
        """Page.waitForRequest


        Parameters
        ----------
        url : Union[str, Pattern, typing.Callable[[str], bool], NoneType]
            Request URL string, regex or predicate receiving Request object.
        timeout : Optional[int]
            Maximum wait time in milliseconds, defaults to 30 seconds, pass `0` to disable the timeout. The default value can be changed by using the page.setDefaultTimeout(timeout) method.

        Returns
        -------
        Request
            Promise which resolves to the matched request.
        """
        return mapping.from_impl(
            await self._impl_obj.waitForRequest(
                url=self._wrap_handler(url),
                predicate=self._wrap_handler(predicate),
                timeout=timeout,
            )
        )

    async def waitForResponse(
        self,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]] = None,
        predicate: typing.Union[typing.Callable[["Response"], bool]] = None,
        timeout: int = None,
    ) -> "Response":
        """Page.waitForResponse


        Parameters
        ----------
        url : Union[str, Pattern, typing.Callable[[str], bool], NoneType]
            Request URL string, regex or predicate receiving Response object.
        timeout : Optional[int]
            Maximum wait time in milliseconds, defaults to 30 seconds, pass `0` to disable the timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.

        Returns
        -------
        Response
            Promise which resolves to the matched response.
        """
        return mapping.from_impl(
            await self._impl_obj.waitForResponse(
                url=self._wrap_handler(url),
                predicate=self._wrap_handler(predicate),
                timeout=timeout,
            )
        )

    async def waitForEvent(
        self,
        event: str,
        predicate: typing.Union[typing.Callable[[typing.Any], bool]] = None,
        timeout: int = None,
    ) -> typing.Any:
        """Page.waitForEvent

        Waits for event to fire and passes its value into the predicate function. Resolves when the predicate returns truthy value. Will throw an error if the page is closed before the event
        is fired.

        Parameters
        ----------
        event : str
            Event name, same one would pass into `page.on(event)`.

        Returns
        -------
        Any
            Promise which resolves to the event data value.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.waitForEvent(
                event=event, predicate=self._wrap_handler(predicate), timeout=timeout
            )
        )

    async def goBack(
        self,
        timeout: int = None,
        waitUntil: Literal["domcontentloaded", "load", "networkidle"] = None,
    ) -> typing.Union["Response", NoneType]:
        """Page.goBack

        Navigate to the previous page in history.

        Parameters
        ----------
        timeout : Optional[int]
            Maximum navigation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultNavigationTimeout(timeout), browserContext.setDefaultTimeout(timeout), page.setDefaultNavigationTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        waitUntil : Optional[Literal['domcontentloaded', 'load', 'networkidle']]
            When to consider navigation succeeded, defaults to `load`. Events can be either:
             - `'domcontentloaded'` - consider navigation to be finished when the `DOMContentLoaded` event is fired.
             - `'load'` - consider navigation to be finished when the `load` event is fired.
             - `'networkidle'` - consider navigation to be finished when there are no network connections for at least `500` ms.

        Returns
        -------
        Optional[Response]
            Promise which resolves to the main resource response. In case of multiple redirects, the navigation will resolve with the response of the last redirect. If
              can not go back, resolves to `null`.
        """
        return mapping.from_impl_nullable(
            await self._impl_obj.goBack(timeout=timeout, waitUntil=waitUntil)
        )

    async def goForward(
        self,
        timeout: int = None,
        waitUntil: Literal["domcontentloaded", "load", "networkidle"] = None,
    ) -> typing.Union["Response", NoneType]:
        """Page.goForward

        Navigate to the next page in history.

        Parameters
        ----------
        timeout : Optional[int]
            Maximum navigation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultNavigationTimeout(timeout), browserContext.setDefaultTimeout(timeout), page.setDefaultNavigationTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        waitUntil : Optional[Literal['domcontentloaded', 'load', 'networkidle']]
            When to consider navigation succeeded, defaults to `load`. Events can be either:
             - `'domcontentloaded'` - consider navigation to be finished when the `DOMContentLoaded` event is fired.
             - `'load'` - consider navigation to be finished when the `load` event is fired.
             - `'networkidle'` - consider navigation to be finished when there are no network connections for at least `500` ms.

        Returns
        -------
        Optional[Response]
            Promise which resolves to the main resource response. In case of multiple redirects, the navigation will resolve with the response of the last redirect. If
              can not go forward, resolves to `null`.
        """
        return mapping.from_impl_nullable(
            await self._impl_obj.goForward(timeout=timeout, waitUntil=waitUntil)
        )

    async def emulateMedia(
        self,
        media: Literal["print", "screen"] = None,
        colorScheme: Literal["dark", "light", "no-preference"] = None,
    ) -> NoneType:
        """Page.emulateMedia


        Parameters
        ----------
        media : Optional[Literal['print', 'screen']]
            Changes the CSS media type of the page. The only allowed values are `'screen'`, `'print'` and `null`. Passing `null` disables CSS media emulation. Omitting `media` or passing `undefined` does not change the emulated value.
        colorScheme : Optional[Literal['dark', 'light', 'no-preference']]
            Emulates `'prefers-colors-scheme'` media feature, supported values are `'light'`, `'dark'`, `'no-preference'`. Passing `null` disables color scheme emulation. Omitting `colorScheme` or passing `undefined` does not change the emulated value.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.emulateMedia(media=media, colorScheme=colorScheme)
        )

    async def setViewportSize(self, width: int, height: int) -> NoneType:
        """Page.setViewportSize

        In the case of multiple pages in a single browser, each page can have its own viewport size. However, browser.newContext([options]) allows to set viewport size (and more) for all pages in the context at once.
        `page.setViewportSize` will resize the page. A lot of websites don't expect phones to change size, so you should set the viewport size before navigating to the page.

        Parameters
        ----------
        width : int
            page width in pixels. **required**
        height : int
            page height in pixels. **required**
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.setViewportSize(width=width, height=height)
        )

    def viewportSize(self) -> typing.Union[Viewport, NoneType]:
        """Page.viewportSize

        Returns
        -------
        Optional[{"width": int, "height": int}]
        """
        return mapping.from_maybe_impl(self._impl_obj.viewportSize())

    async def bringToFront(self) -> NoneType:
        """Page.bringToFront

        Brings page to front (activates tab).
        """
        return mapping.from_maybe_impl(await self._impl_obj.bringToFront())

    async def addInitScript(
        self, source: str = None, path: typing.Union[str, pathlib.Path] = None
    ) -> NoneType:
        """Page.addInitScript

        Adds a script which would be evaluated in one of the following scenarios:

        Whenever the page is navigated.
        Whenever the child frame is attached or navigated. In this case, the script is evaluated in the context of the newly attached frame.

        The script is evaluated after the document was created but before any of its scripts were run. This is useful to amend  the JavaScript environment, e.g. to seed `Math.random`.
        An example of overriding `Math.random` before the page loads:

        **NOTE** The order of evaluation of multiple scripts installed via browserContext.addInitScript(script[, arg]) and page.addInitScript(script[, arg]) is not defined.

        Parameters
        ----------
        source : Optional[str]
            Script to be evaluated in the page.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.addInitScript(source=source, path=path)
        )

    async def route(
        self,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]],
        handler: typing.Callable[["Route", "Request"], typing.Any],
    ) -> NoneType:
        """Page.route

        Routing provides the capability to modify network requests that are made by a page.
        Once routing is enabled, every request matching the url pattern will stall unless it's continued, fulfilled or aborted.

        **NOTE** The handler will only be called for the first url if the response is a redirect.

        An example of a naïve handler that aborts all image requests:
        or the same snippet using a regex pattern instead:
        Page routes take precedence over browser context routes (set up with browserContext.route(url, handler)) when request matches both handlers.

        **NOTE** Enabling routing disables http cache.

        Parameters
        ----------
        url : Union[str, Pattern, typing.Callable[[str], bool]]
            A glob pattern, regex pattern or predicate receiving URL to match while routing.
        handler : typing.Callable[[playwright.network.Route, playwright.network.Request], typing.Any]
            handler function to route the request.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.route(
                url=self._wrap_handler(url), handler=self._wrap_handler(handler)
            )
        )

    async def unroute(
        self,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]],
        handler: typing.Union[typing.Callable[["Route", "Request"], typing.Any]] = None,
    ) -> NoneType:
        """Page.unroute

        Removes a route created with page.route(url, handler). When `handler` is not specified, removes all routes for the `url`.

        Parameters
        ----------
        url : Union[str, Pattern, typing.Callable[[str], bool]]
            A glob pattern, regex pattern or predicate receiving URL to match while routing.
        handler : Optional[typing.Callable[[playwright.network.Route, playwright.network.Request], typing.Any]]
            Handler function to route the request.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.unroute(
                url=self._wrap_handler(url), handler=self._wrap_handler(handler)
            )
        )

    async def screenshot(
        self,
        timeout: int = None,
        type: Literal["jpeg", "png"] = None,
        path: typing.Union[str, pathlib.Path] = None,
        quality: int = None,
        omitBackground: bool = None,
        fullPage: bool = None,
        clip: FloatRect = None,
    ) -> bytes:
        """Page.screenshot

        **NOTE** Screenshots take at least 1/6 second on Chromium OS X and Chromium Windows. See https://crbug.com/741689 for discussion.

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
        omitBackground : Optional[bool]
            Hides default white background and allows capturing screenshots with transparency. Not applicable to `jpeg` images. Defaults to `false`.
        fullPage : Optional[bool]
            When true, takes a screenshot of the full scrollable page, instead of the currently visible viewport. Defaults to `false`.
        clip : Optional[{"x": float, "y": float, "width": float, "height": float}]
            An object which specifies clipping of the resulting image. Should have the following fields:

        Returns
        -------
        bytes
            Promise which resolves to buffer with the captured screenshot.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.screenshot(
                timeout=timeout,
                type=type,
                path=path,
                quality=quality,
                omitBackground=omitBackground,
                fullPage=fullPage,
                clip=clip,
            )
        )

    async def title(self) -> str:
        """Page.title

        Shortcut for page.mainFrame().title().

        Returns
        -------
        str
            The page's title.
        """
        return mapping.from_maybe_impl(await self._impl_obj.title())

    async def close(self, runBeforeUnload: bool = None) -> NoneType:
        """Page.close

        If `runBeforeUnload` is `false` the result will resolve only after the page has been closed.
        If `runBeforeUnload` is `true` the method will **not** wait for the page to close.
        By default, `page.close()` **does not** run beforeunload handlers.

        **NOTE** if `runBeforeUnload` is passed as true, a `beforeunload` dialog might be summoned
        and should be handled manually via page's 'dialog' event.

        Parameters
        ----------
        runBeforeUnload : Optional[bool]
            Defaults to `false`. Whether to run the
            before unload
            page handlers.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.close(runBeforeUnload=runBeforeUnload)
        )

    def isClosed(self) -> bool:
        """Page.isClosed

        Indicates that the page has been closed.

        Returns
        -------
        bool
        """
        return mapping.from_maybe_impl(self._impl_obj.isClosed())

    async def click(
        self,
        selector: str,
        modifiers: typing.Union[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: MousePosition = None,
        delay: int = None,
        button: Literal["left", "middle", "right"] = None,
        clickCount: int = None,
        timeout: int = None,
        force: bool = None,
        noWaitAfter: bool = None,
    ) -> NoneType:
        """Page.click

        This method clicks an element matching `selector` by performing the following steps:

        Find an element match matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        Wait for actionability checks on the matched element, unless `force` option is set. If the element is detached during the checks, the whole action is retried.
        Scroll the element into view if needed.
        Use page.mouse to click in the center of the element, or the specified `position`.
        Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set.

        When all steps combined have not finished during the specified `timeout`, this method rejects with a TimeoutError. Passing zero timeout disables this.
        Shortcut for page.mainFrame().click(selector[, options]).

        Parameters
        ----------
        selector : str
            A selector to search for element to click. If there are multiple elements satisfying the selector, the first will be clicked. See working with selectors for more details.
        modifiers : Optional[List[Literal['Alt', 'Control', 'Meta', 'Shift']]]
            Modifier keys to press. Ensures that only these modifiers are pressed during the click, and then restores current modifiers back. If not specified, currently pressed modifiers are used.
        position : Optional[{"x": float, "y": float}]
            A point to click relative to the top-left corner of element padding box. If not specified, clicks to some visible point of the element.
        delay : Optional[int]
            Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        button : Optional[Literal['left', 'middle', 'right']]
            Defaults to `left`.
        clickCount : Optional[int]
            defaults to 1. See UIEvent.detail.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        force : Optional[bool]
            Whether to bypass the actionability checks. Defaults to `false`.
        noWaitAfter : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.click(
                selector=selector,
                modifiers=modifiers,
                position=position,
                delay=delay,
                button=button,
                clickCount=clickCount,
                timeout=timeout,
                force=force,
                noWaitAfter=noWaitAfter,
            )
        )

    async def dblclick(
        self,
        selector: str,
        modifiers: typing.Union[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: MousePosition = None,
        delay: int = None,
        button: Literal["left", "middle", "right"] = None,
        timeout: int = None,
        force: bool = None,
        noWaitAfter: bool = None,
    ) -> NoneType:
        """Page.dblclick

        This method double clicks an element matching `selector` by performing the following steps:

        Find an element match matching `selector`. If there is none, wait until a matching element is attached to the DOM.
        Wait for actionability checks on the matched element, unless `force` option is set. If the element is detached during the checks, the whole action is retried.
        Scroll the element into view if needed.
        Use page.mouse to double click in the center of the element, or the specified `position`.
        Wait for initiated navigations to either succeed or fail, unless `noWaitAfter` option is set. Note that if the first click of the `dblclick()` triggers a navigation event, this method will reject.

        When all steps combined have not finished during the specified `timeout`, this method rejects with a TimeoutError. Passing zero timeout disables this.

        **NOTE** `page.dblclick()` dispatches two `click` events and a single `dblclick` event.

        Shortcut for page.mainFrame().dblclick(selector[, options]).

        Parameters
        ----------
        selector : str
            A selector to search for element to double click. If there are multiple elements satisfying the selector, the first will be double clicked. See working with selectors for more details.
        modifiers : Optional[List[Literal['Alt', 'Control', 'Meta', 'Shift']]]
            Modifier keys to press. Ensures that only these modifiers are pressed during the double click, and then restores current modifiers back. If not specified, currently pressed modifiers are used.
        position : Optional[{"x": float, "y": float}]
            A point to double click relative to the top-left corner of element padding box. If not specified, double clicks to some visible point of the element.
        delay : Optional[int]
            Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        button : Optional[Literal['left', 'middle', 'right']]
            Defaults to `left`.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        force : Optional[bool]
            Whether to bypass the actionability checks. Defaults to `false`.
        noWaitAfter : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.dblclick(
                selector=selector,
                modifiers=modifiers,
                position=position,
                delay=delay,
                button=button,
                timeout=timeout,
                force=force,
                noWaitAfter=noWaitAfter,
            )
        )

    async def fill(
        self, selector: str, value: str, timeout: int = None, noWaitAfter: bool = None
    ) -> NoneType:
        """Page.fill

        This method waits for an element matching `selector`, waits for actionability checks, focuses the element, fills it and triggers an `input` event after filling.
        If the element matching `selector` is not an `<input>`, `<textarea>` or `[contenteditable]` element, this method throws an error.
        Note that you can pass an empty string to clear the input field.
        To send fine-grained keyboard events, use `page.type`.
        Shortcut for page.mainFrame().fill()

        Parameters
        ----------
        selector : str
            A selector to query page for. See working with selectors for more details.
        value : str
            Value to fill for the `<input>`, `<textarea>` or `[contenteditable]` element.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        noWaitAfter : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.fill(
                selector=selector, value=value, timeout=timeout, noWaitAfter=noWaitAfter
            )
        )

    async def focus(self, selector: str, timeout: int = None) -> NoneType:
        """Page.focus

        This method fetches an element with `selector` and focuses it.
        If there's no element matching `selector`, the method waits until a matching element appears in the DOM.
        Shortcut for page.mainFrame().focus(selector).

        Parameters
        ----------
        selector : str
            A selector of an element to focus. If there are multiple elements satisfying the selector, the first will be focused. See working with selectors for more details.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.focus(selector=selector, timeout=timeout)
        )

    async def textContent(
        self, selector: str, timeout: int = None
    ) -> typing.Union[str, NoneType]:
        """Page.textContent

        Resolves to the `element.textContent`.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be picked. See working with selectors for more details.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.

        Returns
        -------
        Optional[str]
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.textContent(selector=selector, timeout=timeout)
        )

    async def innerText(self, selector: str, timeout: int = None) -> str:
        """Page.innerText

        Resolves to the `element.innerText`.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be picked. See working with selectors for more details.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.innerText(selector=selector, timeout=timeout)
        )

    async def innerHTML(self, selector: str, timeout: int = None) -> str:
        """Page.innerHTML

        Resolves to the `element.innerHTML`.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be picked. See working with selectors for more details.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.

        Returns
        -------
        str
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.innerHTML(selector=selector, timeout=timeout)
        )

    async def getAttribute(
        self, selector: str, name: str, timeout: int = None
    ) -> typing.Union[str, NoneType]:
        """Page.getAttribute

        Returns element attribute value.

        Parameters
        ----------
        selector : str
            A selector to search for an element. If there are multiple elements satisfying the selector, the first will be picked. See working with selectors for more details.
        name : str
            Attribute name to get the value for.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.

        Returns
        -------
        Optional[str]
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.getAttribute(
                selector=selector, name=name, timeout=timeout
            )
        )

    async def hover(
        self,
        selector: str,
        modifiers: typing.Union[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: MousePosition = None,
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

        When all steps combined have not finished during the specified `timeout`, this method rejects with a TimeoutError. Passing zero timeout disables this.
        Shortcut for page.mainFrame().hover(selector[, options]).

        Parameters
        ----------
        selector : str
            A selector to search for element to hover. If there are multiple elements satisfying the selector, the first will be hovered. See working with selectors for more details.
        modifiers : Optional[List[Literal['Alt', 'Control', 'Meta', 'Shift']]]
            Modifier keys to press. Ensures that only these modifiers are pressed during the hover, and then restores current modifiers back. If not specified, currently pressed modifiers are used.
        position : Optional[{"x": float, "y": float}]
            A point to hover relative to the top-left corner of element padding box. If not specified, hovers over some visible point of the element.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        force : Optional[bool]
            Whether to bypass the actionability checks. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.hover(
                selector=selector,
                modifiers=modifiers,
                position=position,
                timeout=timeout,
                force=force,
            )
        )

    async def selectOption(
        self,
        selector: str,
        values: typing.Union[
            str,
            "ElementHandle",
            SelectOption,
            typing.List[str],
            typing.List["ElementHandle"],
            typing.List[SelectOption],
        ] = None,
        timeout: int = None,
        noWaitAfter: bool = None,
    ) -> typing.List[str]:
        """Page.selectOption

        Triggers a `change` and `input` event once all the provided options have been selected.
        If there's no `<select>` element matching `selector`, the method throws an error.

        Shortcut for page.mainFrame().selectOption()

        Parameters
        ----------
        selector : str
            A selector to query page for. See working with selectors for more details.
        values : Union[str, ElementHandle, {"value": Optional[str], "label": Optional[str], "index": Optional[str]}, List[str], List[ElementHandle], List[{"value": Optional[str], "label": Optional[str], "index": Optional[str]}], NoneType]
            Options to select. If the `<select>` has the `multiple` attribute, all matching options are selected, otherwise only the first option matching one of the passed options is selected. String values are equivalent to `{value:'string'}`. Option is considered matching if all specified properties match.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        noWaitAfter : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.

        Returns
        -------
        List[str]
            An array of option values that have been successfully selected.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.selectOption(
                selector=selector,
                values=mapping.to_impl(values),
                timeout=timeout,
                noWaitAfter=noWaitAfter,
            )
        )

    async def setInputFiles(
        self,
        selector: str,
        files: typing.Union[
            str, FilePayload, typing.List[str], typing.List[FilePayload]
        ],
        timeout: int = None,
        noWaitAfter: bool = None,
    ) -> NoneType:
        """Page.setInputFiles

        This method expects `selector` to point to an input element.
        Sets the value of the file input to these file paths or files. If some of the `filePaths` are relative paths, then they are resolved relative to the current working directory. For empty array, clears the selected files.

        Parameters
        ----------
        selector : str
            A selector to search for element to click. If there are multiple elements satisfying the selector, the first will be clicked. See working with selectors for more details.
        files : Union[str, {"name": str, "mimeType": str, "buffer": bytes}, List[str], List[{"name": str, "mimeType": str, "buffer": bytes}]]
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        noWaitAfter : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.setInputFiles(
                selector=selector, files=files, timeout=timeout, noWaitAfter=noWaitAfter
            )
        )

    async def type(
        self,
        selector: str,
        text: str,
        delay: int = None,
        timeout: int = None,
        noWaitAfter: bool = None,
    ) -> NoneType:
        """Page.type

        Sends a `keydown`, `keypress`/`input`, and `keyup` event for each character in the text. `page.type` can be used to send fine-grained keyboard events. To fill values in form fields, use `page.fill`.
        To press a special key, like `Control` or `ArrowDown`, use `keyboard.press`.
        Shortcut for page.mainFrame().type(selector, text[, options]).

        Parameters
        ----------
        selector : str
            A selector of an element to type into. If there are multiple elements satisfying the selector, the first will be used. See working with selectors for more details.
        text : str
            A text to type into a focused element.
        delay : Optional[int]
            Time to wait between key presses in milliseconds. Defaults to 0.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        noWaitAfter : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.type(
                selector=selector,
                text=text,
                delay=delay,
                timeout=timeout,
                noWaitAfter=noWaitAfter,
            )
        )

    async def press(
        self,
        selector: str,
        key: str,
        delay: int = None,
        timeout: int = None,
        noWaitAfter: bool = None,
    ) -> NoneType:
        """Page.press

        Focuses the element, and then uses `keyboard.down` and `keyboard.up`.
        `key` can specify the intended keyboardEvent.key value or a single character to generate the text for. A superset of the `key` values can be found here. Examples of the keys are:
        `F1` - `F12`, `Digit0`- `Digit9`, `KeyA`- `KeyZ`, `Backquote`, `Minus`, `Equal`, `Backslash`, `Backspace`, `Tab`, `Delete`, `Escape`, `ArrowDown`, `End`, `Enter`, `Home`, `Insert`, `PageDown`, `PageUp`, `ArrowRight`, `ArrowUp`, etc.
        Following modification shortcuts are also suported: `Shift`, `Control`, `Alt`, `Meta`, `ShiftLeft`.
        Holding down `Shift` will type the text that corresponds to the `key` in the upper case.
        If `key` is a single character, it is case-sensitive, so the values `a` and `A` will generate different respective texts.
        Shortcuts such as `key: "Control+o"` or `key: "Control+Shift+T"` are supported as well. When speficied with the modifier, modifier is pressed and being held while the subsequent key is being pressed.

        Parameters
        ----------
        selector : str
            A selector of an element to type into. If there are multiple elements satisfying the selector, the first will be used. See working with selectors for more details.
        key : str
            Name of the key to press or a character to generate, such as `ArrowLeft` or `a`.
        delay : Optional[int]
            Time to wait between `keydown` and `keyup` in milliseconds. Defaults to 0.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        noWaitAfter : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.press(
                selector=selector,
                key=key,
                delay=delay,
                timeout=timeout,
                noWaitAfter=noWaitAfter,
            )
        )

    async def check(
        self,
        selector: str,
        timeout: int = None,
        force: bool = None,
        noWaitAfter: bool = None,
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

        When all steps combined have not finished during the specified `timeout`, this method rejects with a TimeoutError. Passing zero timeout disables this.
        Shortcut for page.mainFrame().check(selector[, options]).

        Parameters
        ----------
        selector : str
            A selector to search for checkbox or radio button to check. If there are multiple elements satisfying the selector, the first will be checked. See working with selectors for more details.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        force : Optional[bool]
            Whether to bypass the actionability checks. Defaults to `false`.
        noWaitAfter : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.check(
                selector=selector, timeout=timeout, force=force, noWaitAfter=noWaitAfter
            )
        )

    async def uncheck(
        self,
        selector: str,
        timeout: int = None,
        force: bool = None,
        noWaitAfter: bool = None,
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

        When all steps combined have not finished during the specified `timeout`, this method rejects with a TimeoutError. Passing zero timeout disables this.
        Shortcut for page.mainFrame().uncheck(selector[, options]).

        Parameters
        ----------
        selector : str
            A selector to search for uncheckbox to check. If there are multiple elements satisfying the selector, the first will be checked. See working with selectors for more details.
        timeout : Optional[int]
            Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or page.setDefaultTimeout(timeout) methods.
        force : Optional[bool]
            Whether to bypass the actionability checks. Defaults to `false`.
        noWaitAfter : Optional[bool]
            Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.uncheck(
                selector=selector, timeout=timeout, force=force, noWaitAfter=noWaitAfter
            )
        )

    async def waitForTimeout(self, timeout: int) -> NoneType:
        """Page.waitForTimeout

        Returns a promise that resolves after the timeout.
        Note that `page.waitForTimeout()` should only be used for debugging. Tests using the timer in production are going to be flaky. Use signals such as network events, selectors becoming visible and others instead.
        Shortcut for page.mainFrame().waitForTimeout(timeout).

        Parameters
        ----------
        timeout : int
            A timeout to wait for
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.waitForTimeout(timeout=timeout)
        )

    async def waitForFunction(
        self,
        expression: str,
        arg: typing.Any = None,
        force_expr: bool = None,
        timeout: int = None,
        polling: typing.Union[int, Literal["raf"]] = None,
    ) -> "JSHandle":
        """Page.waitForFunction

        The `waitForFunction` can be used to observe viewport size change:

        To pass an argument from Node.js to the predicate of `page.waitForFunction` function:
        Shortcut for page.mainFrame().waitForFunction(pageFunction[, arg, options]).

        Parameters
        ----------
        expression : str
            Function to be evaluated in browser context
        force_expr : bool
            Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        arg : Optional[Any]
            Optional argument to pass to `pageFunction`
        timeout : Optional[int]
            maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can be changed by using the page.setDefaultTimeout(timeout) method.
        polling : Union[int, 'raf', NoneType]
            If `polling` is `'raf'`, then `pageFunction` is constantly executed in `requestAnimationFrame` callback. If `polling` is a number, then it is treated as an interval in milliseconds at which the function would be executed. Defaults to `raf`.

        Returns
        -------
        JSHandle
            Promise which resolves when the `pageFunction` returns a truthy value. It resolves to a JSHandle of the truthy value.
        """
        return mapping.from_impl(
            await self._impl_obj.waitForFunction(
                expression=expression,
                arg=mapping.to_impl(arg),
                force_expr=force_expr,
                timeout=timeout,
                polling=polling,
            )
        )

    async def pdf(
        self,
        scale: int = None,
        displayHeaderFooter: bool = None,
        headerTemplate: str = None,
        footerTemplate: str = None,
        printBackground: bool = None,
        landscape: bool = None,
        pageRanges: str = None,
        format: str = None,
        width: typing.Union[str, float] = None,
        height: typing.Union[str, float] = None,
        preferCSSPageSize: bool = None,
        margin: PdfMargins = None,
        path: typing.Union[str, pathlib.Path] = None,
    ) -> bytes:
        """Page.pdf

        **NOTE** Generating a pdf is currently only supported in Chromium headless.

        `page.pdf()` generates a pdf of the page with `print` css media. To generate a pdf with `screen` media, call page.emulateMedia({ media: 'screen' }) before calling `page.pdf()`:

        **NOTE** By default, `page.pdf()` generates a pdf with modified colors for printing. Use the `-webkit-print-color-adjust` property to force rendering of exact colors.

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
        displayHeaderFooter : Optional[bool]
            Display header and footer. Defaults to `false`.
        headerTemplate : Optional[str]
            HTML template for the print header. Should be valid HTML markup with following classes used to inject printing values into them:
             - `'date'` formatted print date
             - `'title'` document title
             - `'url'` document location
             - `'pageNumber'` current page number
             - `'totalPages'` total pages in the document
        footerTemplate : Optional[str]
            HTML template for the print footer. Should use the same format as the `headerTemplate`.
        printBackground : Optional[bool]
            Print background graphics. Defaults to `false`.
        landscape : Optional[bool]
            Paper orientation. Defaults to `false`.
        pageRanges : Optional[str]
            Paper ranges to print, e.g., '1-5, 8, 11-13'. Defaults to the empty string, which means print all pages.
        format : Optional[str]
            Paper format. If set, takes priority over `width` or `height` options. Defaults to 'Letter'.
        width : Union[str, float, NoneType]
            Paper width, accepts values labeled with units.
        height : Union[str, float, NoneType]
            Paper height, accepts values labeled with units.
        preferCSSPageSize : Optional[bool]
            Give any CSS `@page` size declared in the page priority over what is declared in `width` and `height` or `format` options. Defaults to `false`, which will scale the content to fit the paper size.
        margin : Optional[{"top": Union[str, int, NoneType], "right": Union[str, int, NoneType], "bottom": Union[str, int, NoneType], "left": Union[str, int, NoneType]}]
            Paper margins, defaults to none.
        path : Union[str, pathlib.Path, NoneType]
            The file path to save the PDF to. If `path` is a relative path, then it is resolved relative to current working directory. If no path is provided, the PDF won't be saved to the disk.

        Returns
        -------
        bytes
            Promise which resolves with PDF buffer.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.pdf(
                scale=scale,
                displayHeaderFooter=displayHeaderFooter,
                headerTemplate=headerTemplate,
                footerTemplate=footerTemplate,
                printBackground=printBackground,
                landscape=landscape,
                pageRanges=pageRanges,
                format=format,
                width=width,
                height=height,
                preferCSSPageSize=preferCSSPageSize,
                margin=margin,
                path=path,
            )
        )

    def expect_event(
        self,
        event: str,
        predicate: typing.Union[typing.Callable[[typing.Any], bool]] = None,
        timeout: int = None,
    ) -> AsyncEventContextManager:
        return AsyncEventContextManager(
            self._impl_obj.waitForEvent(event, predicate, timeout)
        )

    def expect_console_message(
        self,
        predicate: typing.Union[typing.Callable[["ConsoleMessage"], bool]] = None,
        timeout: int = None,
    ) -> AsyncEventContextManager["ConsoleMessage"]:
        event = "console"
        return AsyncEventContextManager(
            self._impl_obj.waitForEvent(event, predicate, timeout)
        )

    def expect_dialog(
        self,
        predicate: typing.Union[typing.Callable[["Dialog"], bool]] = None,
        timeout: int = None,
    ) -> AsyncEventContextManager["Dialog"]:
        event = "dialog"
        return AsyncEventContextManager(
            self._impl_obj.waitForEvent(event, predicate, timeout)
        )

    def expect_download(
        self,
        predicate: typing.Union[typing.Callable[["Download"], bool]] = None,
        timeout: int = None,
    ) -> AsyncEventContextManager["Download"]:
        event = "download"
        return AsyncEventContextManager(
            self._impl_obj.waitForEvent(event, predicate, timeout)
        )

    def expect_file_chooser(
        self,
        predicate: typing.Union[typing.Callable[["FileChooser"], bool]] = None,
        timeout: int = None,
    ) -> AsyncEventContextManager["FileChooser"]:
        event = "filechooser"
        return AsyncEventContextManager(
            self._impl_obj.waitForEvent(event, predicate, timeout)
        )

    def expect_load_state(
        self,
        state: Literal["domcontentloaded", "load", "networkidle"] = None,
        timeout: int = None,
    ) -> AsyncEventContextManager[typing.Union["Response", NoneType]]:
        return AsyncEventContextManager(self._impl_obj.waitForLoadState(state, timeout))

    def expect_navigation(
        self,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]] = None,
        waitUntil: Literal["domcontentloaded", "load", "networkidle"] = None,
        timeout: int = None,
    ) -> AsyncEventContextManager[typing.Union["Response", NoneType]]:
        return AsyncEventContextManager(
            self._impl_obj.waitForNavigation(url, waitUntil, timeout)
        )

    def expect_popup(
        self,
        predicate: typing.Union[typing.Callable[["Page"], bool]] = None,
        timeout: int = None,
    ) -> AsyncEventContextManager["Page"]:
        event = "popup"
        return AsyncEventContextManager(
            self._impl_obj.waitForEvent(event, predicate, timeout)
        )

    def expect_request(
        self,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]] = None,
        predicate: typing.Union[typing.Callable[["Request"], bool]] = None,
        timeout: int = None,
    ) -> AsyncEventContextManager["Request"]:
        return AsyncEventContextManager(
            self._impl_obj.waitForRequest(url, predicate, timeout)
        )

    def expect_response(
        self,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]] = None,
        predicate: typing.Union[typing.Callable[["Request"], bool]] = None,
        timeout: int = None,
    ) -> AsyncEventContextManager["Response"]:
        return AsyncEventContextManager(
            self._impl_obj.waitForResponse(url, predicate, timeout)
        )

    def expect_worker(
        self,
        predicate: typing.Union[typing.Callable[["Worker"], bool]] = None,
        timeout: int = None,
    ) -> AsyncEventContextManager["Worker"]:
        event = "worker"
        return AsyncEventContextManager(
            self._impl_obj.waitForEvent(event, predicate, timeout)
        )


mapping.register(PageImpl, Page)


class BrowserContext(AsyncBase):
    def __init__(self, obj: BrowserContextImpl):
        super().__init__(obj)

    @property
    def pages(self) -> typing.List["Page"]:
        """BrowserContext.pages

        Returns
        -------
        List[Page]
            All open pages in the context. Non visible pages, such as `"background_page"`, will not be listed here. You can find them using chromiumBrowserContext.backgroundPages().
        """
        return mapping.from_impl_list(self._impl_obj.pages)

    @property
    def browser(self) -> typing.Union["Browser", NoneType]:
        """BrowserContext.browser

        Returns
        -------
        Optional[Browser]
            Returns the browser instance of the context. If it was launched as a persistent context null gets returned.
        """
        return mapping.from_impl_nullable(self._impl_obj.browser)

    def setDefaultNavigationTimeout(self, timeout: int) -> NoneType:
        """BrowserContext.setDefaultNavigationTimeout

        This setting will change the default maximum navigation time for the following methods and related shortcuts:

        page.goBack([options])
        page.goForward([options])
        page.goto(url[, options])
        page.reload([options])
        page.setContent(html[, options])
        page.waitForNavigation([options])

        **NOTE** `page.setDefaultNavigationTimeout` and `page.setDefaultTimeout` take priority over `browserContext.setDefaultNavigationTimeout`.

        Parameters
        ----------
        timeout : int
            Maximum navigation time in milliseconds
        """
        return mapping.from_maybe_impl(
            self._impl_obj.setDefaultNavigationTimeout(timeout=timeout)
        )

    def setDefaultTimeout(self, timeout: int) -> NoneType:
        """BrowserContext.setDefaultTimeout

        This setting will change the default maximum time for all the methods accepting `timeout` option.

        **NOTE** `page.setDefaultNavigationTimeout`, `page.setDefaultTimeout` and `browserContext.setDefaultNavigationTimeout` take priority over `browserContext.setDefaultTimeout`.

        Parameters
        ----------
        timeout : int
            Maximum time in milliseconds
        """
        return mapping.from_maybe_impl(
            self._impl_obj.setDefaultTimeout(timeout=timeout)
        )

    async def newPage(self) -> "Page":
        """BrowserContext.newPage

        Creates a new page in the browser context.

        Returns
        -------
        Page
        """
        return mapping.from_impl(await self._impl_obj.newPage())

    async def cookies(
        self, urls: typing.Union[str, typing.List[str]] = None
    ) -> typing.List[typing.Dict]:
        """BrowserContext.cookies

        If no URLs are specified, this method returns all cookies.
        If URLs are specified, only cookies that affect those URLs are returned.

        Parameters
        ----------
        urls : Union[str, List[str], NoneType]

        Returns
        -------
        List[Dict]
        """
        return mapping.from_maybe_impl(await self._impl_obj.cookies(urls=urls))

    async def addCookies(self, cookies: typing.List[typing.Dict]) -> NoneType:
        """BrowserContext.addCookies


        Parameters
        ----------
        cookies : List[Dict]
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.addCookies(cookies=mapping.to_impl(cookies))
        )

    async def clearCookies(self) -> NoneType:
        """BrowserContext.clearCookies

        Clears context cookies.
        """
        return mapping.from_maybe_impl(await self._impl_obj.clearCookies())

    async def grantPermissions(
        self, permissions: typing.List[str], origin: str = None
    ) -> NoneType:
        """BrowserContext.grantPermissions

        Grants specified permissions to the browser context. Only grants corresponding permissions to the given origin if specified.

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
            await self._impl_obj.grantPermissions(
                permissions=permissions, origin=origin
            )
        )

    async def clearPermissions(self) -> NoneType:
        """BrowserContext.clearPermissions

        Clears all permission overrides for the browser context.
        """
        return mapping.from_maybe_impl(await self._impl_obj.clearPermissions())

    async def setGeolocation(self, geolocation: Geolocation = None) -> NoneType:
        """BrowserContext.setGeolocation

        Sets the context's geolocation. Passing `null` or `undefined` emulates position unavailable.

        **NOTE** Consider using browserContext.grantPermissions to grant permissions for the browser context pages to read its geolocation.

        Parameters
        ----------
        geolocation : Optional[{"latitude": float, "longitude": float, "accuracy": Optional[float]}]
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.setGeolocation(geolocation=geolocation)
        )

    async def setExtraHTTPHeaders(self, headers: typing.Dict[str, str]) -> NoneType:
        """BrowserContext.setExtraHTTPHeaders

        The extra HTTP headers will be sent with every request initiated by any page in the context. These headers are merged with page-specific extra HTTP headers set with page.setExtraHTTPHeaders(). If page overrides a particular header, page-specific header value will be used instead of the browser context header value.

        **NOTE** `browserContext.setExtraHTTPHeaders` does not guarantee the order of headers in the outgoing requests.

        Parameters
        ----------
        headers : Dict[str, str]
            An object containing additional HTTP headers to be sent with every request. All header values must be strings.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.setExtraHTTPHeaders(headers=mapping.to_impl(headers))
        )

    async def setOffline(self, offline: bool) -> NoneType:
        """BrowserContext.setOffline

        Parameters
        ----------
        offline : bool
            Whether to emulate network being offline for the browser context.
        """
        return mapping.from_maybe_impl(await self._impl_obj.setOffline(offline=offline))

    async def addInitScript(
        self, source: str = None, path: typing.Union[str, pathlib.Path] = None
    ) -> NoneType:
        """BrowserContext.addInitScript

        Adds a script which would be evaluated in one of the following scenarios:

        Whenever a page is created in the browser context or is navigated.
        Whenever a child frame is attached or navigated in any page in the browser context. In this case, the script is evaluated in the context of the newly attached frame.

        The script is evaluated after the document was created but before any of its scripts were run. This is useful to amend  the JavaScript environment, e.g. to seed `Math.random`.
        An example of overriding `Math.random` before the page loads:

        **NOTE** The order of evaluation of multiple scripts installed via browserContext.addInitScript(script[, arg]) and page.addInitScript(script[, arg]) is not defined.

        Parameters
        ----------
        source : Optional[str]
            Script to be evaluated in all pages in the browser context.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.addInitScript(source=source, path=path)
        )

    async def exposeBinding(
        self, name: str, binding: typing.Callable, handle: bool = None
    ) -> NoneType:
        """BrowserContext.exposeBinding

        The method adds a function called `name` on the `window` object of every frame in every page in the context.
        When called, the function executes `playwrightBinding` in Node.js and returns a Promise which resolves to the return value of `playwrightBinding`.
        If the `playwrightBinding` returns a Promise, it will be awaited.
        The first argument of the `playwrightBinding` function contains information about the caller:
        `{ browserContext: BrowserContext, page: Page, frame: Frame }`.
        See page.exposeBinding(name, playwrightBinding) for page-only version.
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
            await self._impl_obj.exposeBinding(
                name=name, binding=self._wrap_handler(binding), handle=handle
            )
        )

    async def exposeFunction(self, name: str, binding: typing.Callable) -> NoneType:
        """BrowserContext.exposeFunction

        The method adds a function called `name` on the `window` object of every frame in every page in the context.
        When called, the function executes `playwrightFunction` in Node.js and returns a Promise which resolves to the return value of `playwrightFunction`.
        If the `playwrightFunction` returns a Promise, it will be awaited.
        See page.exposeFunction(name, playwrightFunction) for page-only version.
        An example of adding an `md5` function to all pages in the context:

        Parameters
        ----------
        name : str
            Name of the function on the window object.
        binding : Callable
            Callback function that will be called in the Playwright's context.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.exposeFunction(
                name=name, binding=self._wrap_handler(binding)
            )
        )

    async def route(
        self,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]],
        handler: typing.Callable[["Route", "Request"], typing.Any],
    ) -> NoneType:
        """BrowserContext.route

        Routing provides the capability to modify network requests that are made by any page in the browser context.
        Once route is enabled, every request matching the url pattern will stall unless it's continued, fulfilled or aborted.
        An example of a naïve handler that aborts all image requests:
        or the same snippet using a regex pattern instead:
        Page routes (set up with page.route(url, handler)) take precedence over browser context routes when request matches both handlers.

        **NOTE** Enabling routing disables http cache.

        Parameters
        ----------
        url : Union[str, Pattern, typing.Callable[[str], bool]]
            A glob pattern, regex pattern or predicate receiving URL to match while routing.
        handler : typing.Callable[[playwright.network.Route, playwright.network.Request], typing.Any]
            handler function to route the request.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.route(
                url=self._wrap_handler(url), handler=self._wrap_handler(handler)
            )
        )

    async def unroute(
        self,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]],
        handler: typing.Union[typing.Callable[["Route", "Request"], typing.Any]] = None,
    ) -> NoneType:
        """BrowserContext.unroute

        Removes a route created with browserContext.route(url, handler). When `handler` is not specified, removes all routes for the `url`.

        Parameters
        ----------
        url : Union[str, Pattern, typing.Callable[[str], bool]]
            A glob pattern, regex pattern or predicate receiving URL used to register a routing with browserContext.route(url, handler).
        handler : Optional[typing.Callable[[playwright.network.Route, playwright.network.Request], typing.Any]]
            Handler function used to register a routing with browserContext.route(url, handler).
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.unroute(
                url=self._wrap_handler(url), handler=self._wrap_handler(handler)
            )
        )

    async def waitForEvent(
        self,
        event: str,
        predicate: typing.Union[typing.Callable[[typing.Any], bool]] = None,
        timeout: int = None,
    ) -> typing.Any:
        """BrowserContext.waitForEvent

        Waits for event to fire and passes its value into the predicate function. Resolves when the predicate returns truthy value. Will throw an error if the context closes before the event
        is fired.

        Parameters
        ----------
        event : str
            Event name, same one would pass into `browserContext.on(event)`.

        Returns
        -------
        Any
            Promise which resolves to the event data value.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.waitForEvent(
                event=event, predicate=self._wrap_handler(predicate), timeout=timeout
            )
        )

    async def close(self) -> NoneType:
        """BrowserContext.close

        Closes the browser context. All the pages that belong to the browser context
        will be closed.

        **NOTE** the default browser context cannot be closed.
        """
        return mapping.from_maybe_impl(await self._impl_obj.close())

    def expect_event(
        self,
        event: str,
        predicate: typing.Union[typing.Callable[[typing.Any], bool]] = None,
        timeout: int = None,
    ) -> AsyncEventContextManager:
        return AsyncEventContextManager(
            self._impl_obj.waitForEvent(event, predicate, timeout)
        )

    def expect_page(
        self,
        predicate: typing.Union[typing.Callable[["Page"], bool]] = None,
        timeout: int = None,
    ) -> AsyncEventContextManager["Page"]:
        event = "page"
        return AsyncEventContextManager(
            self._impl_obj.waitForEvent(event, predicate, timeout)
        )


mapping.register(BrowserContextImpl, BrowserContext)


class CDPSession(AsyncBase):
    def __init__(self, obj: CDPSessionImpl):
        super().__init__(obj)

    async def send(self, method: str, params: typing.Dict = None) -> typing.Dict:
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
            await self._impl_obj.send(method=method, params=mapping.to_impl(params))
        )

    async def detach(self) -> NoneType:
        """CDPSession.detach

        Detaches the CDPSession from the target. Once detached, the CDPSession object won't emit any events and can't be used
        to send messages.
        """
        return mapping.from_maybe_impl(await self._impl_obj.detach())


mapping.register(CDPSessionImpl, CDPSession)


class ChromiumBrowserContext(BrowserContext):
    def __init__(self, obj: ChromiumBrowserContextImpl):
        super().__init__(obj)

    def backgroundPages(self) -> typing.List["Page"]:
        """ChromiumBrowserContext.backgroundPages

        Returns
        -------
        List[Page]
            All existing background pages in the context.
        """
        return mapping.from_impl_list(self._impl_obj.backgroundPages())

    def serviceWorkers(self) -> typing.List["Worker"]:
        """ChromiumBrowserContext.serviceWorkers

        Returns
        -------
        List[Worker]
            All existing service workers in the context.
        """
        return mapping.from_impl_list(self._impl_obj.serviceWorkers())

    async def newCDPSession(self, page: "Page") -> "CDPSession":
        """ChromiumBrowserContext.newCDPSession

        Parameters
        ----------
        page : Page
            Page to create new session for.

        Returns
        -------
        CDPSession
            Promise that resolves to the newly created session.
        """
        return mapping.from_impl(
            await self._impl_obj.newCDPSession(page=page._impl_obj)
        )


mapping.register(ChromiumBrowserContextImpl, ChromiumBrowserContext)


class Browser(AsyncBase):
    def __init__(self, obj: BrowserImpl):
        super().__init__(obj)

    @property
    def contexts(self) -> typing.List["BrowserContext"]:
        """Browser.contexts

        Returns an array of all open browser contexts. In a newly created browser, this will return zero
        browser contexts.

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

    def isConnected(self) -> bool:
        """Browser.isConnected

        Indicates that the browser is connected.

        Returns
        -------
        bool
        """
        return mapping.from_maybe_impl(self._impl_obj.isConnected())

    async def newContext(
        self,
        viewport: typing.Union[IntSize, Literal[0]] = None,
        ignoreHTTPSErrors: bool = None,
        javaScriptEnabled: bool = None,
        bypassCSP: bool = None,
        userAgent: str = None,
        locale: str = None,
        timezoneId: str = None,
        geolocation: Geolocation = None,
        permissions: typing.List[str] = None,
        extraHTTPHeaders: typing.Union[typing.Dict[str, str]] = None,
        offline: bool = None,
        httpCredentials: Credentials = None,
        deviceScaleFactor: int = None,
        isMobile: bool = None,
        hasTouch: bool = None,
        colorScheme: Literal["dark", "light", "no-preference"] = None,
        acceptDownloads: bool = None,
        defaultBrowserType: str = None,
        videosPath: str = None,
        videoSize: IntSize = None,
    ) -> "BrowserContext":
        """Browser.newContext

        Creates a new browser context. It won't share cookies/cache with other browser contexts.

        Parameters
        ----------
        viewport : Union[{"width": int, "height": int}, '0', NoneType]
            Sets a consistent viewport for each page. Defaults to an 1280x720 viewport. `null` disables the default viewport.
        ignoreHTTPSErrors : Optional[bool]
            Whether to ignore HTTPS errors during navigation. Defaults to `false`.
        javaScriptEnabled : Optional[bool]
            Whether or not to enable JavaScript in the context. Defaults to true.
        bypassCSP : Optional[bool]
            Toggles bypassing page's Content-Security-Policy.
        userAgent : Optional[str]
            Specific user agent to use in this context.
        locale : Optional[str]
            Specify user locale, for example `en-GB`, `de-DE`, etc. Locale will affect `navigator.language` value, `Accept-Language` request header value as well as number and date formatting rules.
        timezoneId : Optional[str]
            Changes the timezone of the context. See ICU’s `metaZones.txt` for a list of supported timezone IDs.
        geolocation : Optional[{"latitude": float, "longitude": float, "accuracy": Optional[float]}]
        permissions : Optional[List[str]]
            A list of permissions to grant to all pages in this context. See browserContext.grantPermissions for more details.
        extraHTTPHeaders : Optional[Dict[str, str]]
            An object containing additional HTTP headers to be sent with every request. All header values must be strings.
        offline : Optional[bool]
            Whether to emulate network being offline. Defaults to `false`.
        httpCredentials : Optional[{"username": str, "password": str}]
            Credentials for HTTP authentication.
        deviceScaleFactor : Optional[int]
            Specify device scale factor (can be thought of as dpr). Defaults to `1`.
        isMobile : Optional[bool]
            Whether the `meta viewport` tag is taken into account and touch events are enabled. Defaults to `false`. Not supported in Firefox.
        hasTouch : Optional[bool]
            Specifies if viewport supports touch events. Defaults to false.
        colorScheme : Optional[Literal['dark', 'light', 'no-preference']]
            Emulates `'prefers-colors-scheme'` media feature, supported values are `'light'`, `'dark'`, `'no-preference'`. See page.emulateMedia(options) for more details. Defaults to '`light`'.
        acceptDownloads : Optional[bool]
            Whether to automatically download all the attachments. Defaults to `false` where all the downloads are canceled.
        videosPath : Optional[str]
            Enables video recording for all pages to `videosPath` folder. If not specified, videos are not recorded. Make sure to await `browserContext.close` for videos to be saved.
        videoSize : Optional[{"width": int, "height": int}]
            Specifies dimensions of the automatically recorded video. Can only be used if `videosPath` is set. If not specified the size will be equal to `viewport`. If `viewport` is not configured explicitly the video size defaults to 1280x720. Actual picture of the page will be scaled down if necessary to fit specified size.

        Returns
        -------
        BrowserContext
        """
        return mapping.from_impl(
            await self._impl_obj.newContext(
                viewport=viewport,
                ignoreHTTPSErrors=ignoreHTTPSErrors,
                javaScriptEnabled=javaScriptEnabled,
                bypassCSP=bypassCSP,
                userAgent=userAgent,
                locale=locale,
                timezoneId=timezoneId,
                geolocation=geolocation,
                permissions=permissions,
                extraHTTPHeaders=mapping.to_impl(extraHTTPHeaders),
                offline=offline,
                httpCredentials=httpCredentials,
                deviceScaleFactor=deviceScaleFactor,
                isMobile=isMobile,
                hasTouch=hasTouch,
                colorScheme=colorScheme,
                acceptDownloads=acceptDownloads,
                defaultBrowserType=defaultBrowserType,
                videosPath=videosPath,
                videoSize=videoSize,
            )
        )

    async def newPage(
        self,
        viewport: typing.Union[IntSize, Literal[0]] = None,
        ignoreHTTPSErrors: bool = None,
        javaScriptEnabled: bool = None,
        bypassCSP: bool = None,
        userAgent: str = None,
        locale: str = None,
        timezoneId: str = None,
        geolocation: Geolocation = None,
        permissions: typing.List[str] = None,
        extraHTTPHeaders: typing.Union[typing.Dict[str, str]] = None,
        offline: bool = None,
        httpCredentials: Credentials = None,
        deviceScaleFactor: int = None,
        isMobile: bool = None,
        hasTouch: bool = None,
        colorScheme: Literal["dark", "light", "no-preference"] = None,
        acceptDownloads: bool = None,
        defaultBrowserType: str = None,
        videosPath: str = None,
        videoSize: IntSize = None,
    ) -> "Page":
        """Browser.newPage

        Creates a new page in a new browser context. Closing this page will close the context as well.
        This is a convenience API that should only be used for the single-page scenarios and short snippets. Production code and testing frameworks should explicitly create browser.newContext followed by the browserContext.newPage to control their exact life times.

        Parameters
        ----------
        viewport : Union[{"width": int, "height": int}, '0', NoneType]
            Sets a consistent viewport for each page. Defaults to an 1280x720 viewport. `null` disables the default viewport.
        ignoreHTTPSErrors : Optional[bool]
            Whether to ignore HTTPS errors during navigation. Defaults to `false`.
        javaScriptEnabled : Optional[bool]
            Whether or not to enable JavaScript in the context. Defaults to `true`.
        bypassCSP : Optional[bool]
            Toggles bypassing page's Content-Security-Policy.
        userAgent : Optional[str]
            Specific user agent to use in this context.
        locale : Optional[str]
            Specify user locale, for example `en-GB`, `de-DE`, etc. Locale will affect `navigator.language` value, `Accept-Language` request header value as well as number and date formatting rules.
        timezoneId : Optional[str]
            Changes the timezone of the context. See ICU’s `metaZones.txt` for a list of supported timezone IDs.
        geolocation : Optional[{"latitude": float, "longitude": float, "accuracy": Optional[float]}]
        permissions : Optional[List[str]]
            A list of permissions to grant to all pages in this context. See browserContext.grantPermissions for more details.
        extraHTTPHeaders : Optional[Dict[str, str]]
            An object containing additional HTTP headers to be sent with every request. All header values must be strings.
        offline : Optional[bool]
            Whether to emulate network being offline. Defaults to `false`.
        httpCredentials : Optional[{"username": str, "password": str}]
            Credentials for HTTP authentication.
        deviceScaleFactor : Optional[int]
            Specify device scale factor (can be thought of as dpr). Defaults to `1`.
        isMobile : Optional[bool]
            Whether the `meta viewport` tag is taken into account and touch events are enabled. Defaults to `false`. Not supported in Firefox.
        hasTouch : Optional[bool]
            Specifies if viewport supports touch events. Defaults to false.
        colorScheme : Optional[Literal['dark', 'light', 'no-preference']]
            Emulates `'prefers-colors-scheme'` media feature, supported values are `'light'`, `'dark'`, `'no-preference'`. See page.emulateMedia(options) for more details. Defaults to '`light`'.
        acceptDownloads : Optional[bool]
            Whether to automatically download all the attachments. Defaults to `false` where all the downloads are canceled.
        videosPath : Optional[str]
            Enables video recording for all pages to `videosPath` folder. If not specified, videos are not recorded. Make sure to await `page.close` for videos to be saved.
        videoSize : Optional[{"width": int, "height": int}]
            Specifies dimensions of the automatically recorded video. Can only be used if `videosPath` is set. If not specified the size will be equal to `viewport`. If `viewport` is not configured explicitly the video size defaults to 1280x720. Actual picture of the page will be scaled down if necessary to fit specified size.

        Returns
        -------
        Page
        """
        return mapping.from_impl(
            await self._impl_obj.newPage(
                viewport=viewport,
                ignoreHTTPSErrors=ignoreHTTPSErrors,
                javaScriptEnabled=javaScriptEnabled,
                bypassCSP=bypassCSP,
                userAgent=userAgent,
                locale=locale,
                timezoneId=timezoneId,
                geolocation=geolocation,
                permissions=permissions,
                extraHTTPHeaders=mapping.to_impl(extraHTTPHeaders),
                offline=offline,
                httpCredentials=httpCredentials,
                deviceScaleFactor=deviceScaleFactor,
                isMobile=isMobile,
                hasTouch=hasTouch,
                colorScheme=colorScheme,
                acceptDownloads=acceptDownloads,
                defaultBrowserType=defaultBrowserType,
                videosPath=videosPath,
                videoSize=videoSize,
            )
        )

    async def close(self) -> NoneType:
        """Browser.close

        In case this browser is obtained using browserType.launch, closes the browser and all of its pages (if any were opened).
        In case this browser is obtained using browserType.connect, clears all created contexts belonging to this browser and disconnects from the browser server.
        The Browser object itself is considered to be disposed and cannot be used anymore.
        """
        return mapping.from_maybe_impl(await self._impl_obj.close())


mapping.register(BrowserImpl, Browser)


class BrowserType(AsyncBase):
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
    def executablePath(self) -> str:
        """BrowserType.executablePath

        Returns
        -------
        str
            A path where Playwright expects to find a bundled browser executable.
        """
        return mapping.from_maybe_impl(self._impl_obj.executablePath)

    async def launch(
        self,
        executablePath: typing.Union[str, pathlib.Path] = None,
        args: typing.List[str] = None,
        ignoreDefaultArgs: typing.Union[bool, typing.List[str]] = None,
        handleSIGINT: bool = None,
        handleSIGTERM: bool = None,
        handleSIGHUP: bool = None,
        timeout: int = None,
        env: typing.Union[typing.Dict[str, typing.Union[str, int, bool]]] = None,
        headless: bool = None,
        devtools: bool = None,
        proxy: ProxyServer = None,
        downloadsPath: typing.Union[str, pathlib.Path] = None,
        slowMo: int = None,
        chromiumSandbox: bool = None,
        firefoxUserPrefs: typing.Union[
            typing.Dict[str, typing.Union[str, int, bool]]
        ] = None,
    ) -> "Browser":
        """BrowserType.launch

        You can use `ignoreDefaultArgs` to filter out `--mute-audio` from default arguments:

        **Chromium-only** Playwright can also be used to control the Chrome browser, but it works best with the version of Chromium it is bundled with. There is no guarantee it will work with any other version. Use `executablePath` option with extreme caution.
        If Google Chrome (rather than Chromium) is preferred, a Chrome Canary or Dev Channel build is suggested.
        In browserType.launch([options]) above, any mention of Chromium also applies to Chrome.
        See `this article` for a description of the differences between Chromium and Chrome. `This article` describes some differences for Linux users.

        Parameters
        ----------
        executablePath : Union[str, pathlib.Path, NoneType]
            Path to a browser executable to run instead of the bundled one. If `executablePath` is a relative path, then it is resolved relative to current working directory. Note that Playwright only works with the bundled Chromium, Firefox or WebKit, use at your own risk.
        args : Optional[List[str]]
            Additional arguments to pass to the browser instance. The list of Chromium flags can be found here.
        ignoreDefaultArgs : Union[bool, List[str], NoneType]
            If `true`, Playwright does not pass its own configurations args and only uses the ones from `args`. If an array is given, then filters out the given default arguments. Dangerous option; use with care. Defaults to `false`.
        handleSIGINT : Optional[bool]
            Close the browser process on Ctrl-C. Defaults to `true`.
        handleSIGTERM : Optional[bool]
            Close the browser process on SIGTERM. Defaults to `true`.
        handleSIGHUP : Optional[bool]
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
        downloadsPath : Union[str, pathlib.Path, NoneType]
            If specified, accepted downloads are downloaded into this folder. Otherwise, temporary folder is created and is deleted when browser is closed.
        slowMo : Optional[int]
            Slows down Playwright operations by the specified amount of milliseconds. Useful so that you can see what is going on.
        chromiumSandbox : Optional[bool]
            Enable Chromium sandboxing. Defaults to `false`.
        firefoxUserPrefs : Optional[Dict[str, Union[str, int, bool]]]
            Firefox user preferences. Learn more about the Firefox user preferences at `about:config`.

        Returns
        -------
        Browser
            Promise which resolves to browser instance.
        """
        return mapping.from_impl(
            await self._impl_obj.launch(
                executablePath=executablePath,
                args=args,
                ignoreDefaultArgs=ignoreDefaultArgs,
                handleSIGINT=handleSIGINT,
                handleSIGTERM=handleSIGTERM,
                handleSIGHUP=handleSIGHUP,
                timeout=timeout,
                env=mapping.to_impl(env),
                headless=headless,
                devtools=devtools,
                proxy=proxy,
                downloadsPath=downloadsPath,
                slowMo=slowMo,
                chromiumSandbox=chromiumSandbox,
                firefoxUserPrefs=mapping.to_impl(firefoxUserPrefs),
            )
        )

    async def launchPersistentContext(
        self,
        userDataDir: typing.Union[str, pathlib.Path],
        executablePath: typing.Union[str, pathlib.Path] = None,
        args: typing.List[str] = None,
        ignoreDefaultArgs: typing.Union[bool, typing.List[str]] = None,
        handleSIGINT: bool = None,
        handleSIGTERM: bool = None,
        handleSIGHUP: bool = None,
        timeout: int = None,
        env: typing.Union[typing.Dict[str, typing.Union[str, int, bool]]] = None,
        headless: bool = None,
        devtools: bool = None,
        proxy: ProxyServer = None,
        downloadsPath: typing.Union[str, pathlib.Path] = None,
        slowMo: int = None,
        viewport: IntSize = None,
        ignoreHTTPSErrors: bool = None,
        javaScriptEnabled: bool = None,
        bypassCSP: bool = None,
        userAgent: str = None,
        locale: str = None,
        timezoneId: str = None,
        geolocation: Geolocation = None,
        permissions: typing.List[str] = None,
        extraHTTPHeaders: typing.Union[typing.Dict[str, str]] = None,
        offline: bool = None,
        httpCredentials: Credentials = None,
        deviceScaleFactor: int = None,
        isMobile: bool = None,
        hasTouch: bool = None,
        colorScheme: Literal["dark", "light", "no-preference"] = None,
        acceptDownloads: bool = None,
        chromiumSandbox: bool = None,
        videosPath: str = None,
        videoSize: IntSize = None,
    ) -> "BrowserContext":
        """BrowserType.launchPersistentContext

        Launches browser that uses persistent storage located at `userDataDir` and returns the only context. Closing this context will automatically close the browser.

        Parameters
        ----------
        userDataDir : Union[str, pathlib.Path]
            Path to a User Data Directory, which stores browser session data like cookies and local storage. More details for Chromium and Firefox.
        executablePath : Union[str, pathlib.Path, NoneType]
            Path to a browser executable to run instead of the bundled one. If `executablePath` is a relative path, then it is resolved relative to current working directory. **BEWARE**: Playwright is only guaranteed to work with the bundled Chromium, Firefox or WebKit, use at your own risk.
        args : Optional[List[str]]
            Additional arguments to pass to the browser instance. The list of Chromium flags can be found here.
        ignoreDefaultArgs : Union[bool, List[str], NoneType]
            If `true`, then do not use any of the default arguments. If an array is given, then filter out the given default arguments. Dangerous option; use with care. Defaults to `false`.
        handleSIGINT : Optional[bool]
            Close the browser process on Ctrl-C. Defaults to `true`.
        handleSIGTERM : Optional[bool]
            Close the browser process on SIGTERM. Defaults to `true`.
        handleSIGHUP : Optional[bool]
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
        downloadsPath : Union[str, pathlib.Path, NoneType]
            If specified, accepted downloads are downloaded into this folder. Otherwise, temporary folder is created and is deleted when browser is closed.
        slowMo : Optional[int]
            Slows down Playwright operations by the specified amount of milliseconds. Useful so that you can see what is going on. Defaults to 0.
        viewport : Optional[{"width": int, "height": int}]
            Sets a consistent viewport for each page. Defaults to an 1280x720 viewport. `null` disables the default viewport.
        ignoreHTTPSErrors : Optional[bool]
            Whether to ignore HTTPS errors during navigation. Defaults to `false`.
        javaScriptEnabled : Optional[bool]
            Whether or not to enable JavaScript in the context. Defaults to true.
        bypassCSP : Optional[bool]
            Toggles bypassing page's Content-Security-Policy.
        userAgent : Optional[str]
            Specific user agent to use in this context.
        locale : Optional[str]
            Specify user locale, for example `en-GB`, `de-DE`, etc. Locale will affect `navigator.language` value, `Accept-Language` request header value as well as number and date formatting rules.
        timezoneId : Optional[str]
            Changes the timezone of the context. See ICU’s `metaZones.txt` for a list of supported timezone IDs.
        geolocation : Optional[{"latitude": float, "longitude": float, "accuracy": Optional[float]}]
        permissions : Optional[List[str]]
            A list of permissions to grant to all pages in this context. See browserContext.grantPermissions for more details.
        extraHTTPHeaders : Optional[Dict[str, str]]
            An object containing additional HTTP headers to be sent with every request. All header values must be strings.
        offline : Optional[bool]
            Whether to emulate network being offline. Defaults to `false`.
        httpCredentials : Optional[{"username": str, "password": str}]
            Credentials for HTTP authentication.
        deviceScaleFactor : Optional[int]
            Specify device scale factor (can be thought of as dpr). Defaults to `1`.
        isMobile : Optional[bool]
            Whether the `meta viewport` tag is taken into account and touch events are enabled. Defaults to `false`. Not supported in Firefox.
        hasTouch : Optional[bool]
            Specifies if viewport supports touch events. Defaults to false.
        colorScheme : Optional[Literal['dark', 'light', 'no-preference']]
            Emulates `'prefers-colors-scheme'` media feature, supported values are `'light'`, `'dark'`, `'no-preference'`. See page.emulateMedia(options) for more details. Defaults to '`light`'.
        acceptDownloads : Optional[bool]
            Whether to automatically download all the attachments. Defaults to `false` where all the downloads are canceled.
        chromiumSandbox : Optional[bool]
            Enable Chromium sandboxing. Defaults to `true`.
        videosPath : Optional[str]
            Enables video recording for all pages to `videosPath` folder. If not specified, videos are not recorded. Make sure to await `browserContext.close` for videos to be saved.
        videoSize : Optional[{"width": int, "height": int}]
            Specifies dimensions of the automatically recorded video. Can only be used if `videosPath` is set. If not specified the size will be equal to `viewport`. If `viewport` is not configured explicitly the video size defaults to 1280x720. Actual picture of the page will be scaled down if necessary to fit specified size.

        Returns
        -------
        BrowserContext
            Promise that resolves to the persistent browser context instance.
        """
        return mapping.from_impl(
            await self._impl_obj.launchPersistentContext(
                userDataDir=userDataDir,
                executablePath=executablePath,
                args=args,
                ignoreDefaultArgs=ignoreDefaultArgs,
                handleSIGINT=handleSIGINT,
                handleSIGTERM=handleSIGTERM,
                handleSIGHUP=handleSIGHUP,
                timeout=timeout,
                env=mapping.to_impl(env),
                headless=headless,
                devtools=devtools,
                proxy=proxy,
                downloadsPath=downloadsPath,
                slowMo=slowMo,
                viewport=viewport,
                ignoreHTTPSErrors=ignoreHTTPSErrors,
                javaScriptEnabled=javaScriptEnabled,
                bypassCSP=bypassCSP,
                userAgent=userAgent,
                locale=locale,
                timezoneId=timezoneId,
                geolocation=geolocation,
                permissions=permissions,
                extraHTTPHeaders=mapping.to_impl(extraHTTPHeaders),
                offline=offline,
                httpCredentials=httpCredentials,
                deviceScaleFactor=deviceScaleFactor,
                isMobile=isMobile,
                hasTouch=hasTouch,
                colorScheme=colorScheme,
                acceptDownloads=acceptDownloads,
                chromiumSandbox=chromiumSandbox,
                videosPath=videosPath,
                videoSize=videoSize,
            )
        )

    async def connect(
        self, wsEndpoint: str, slowMo: int = None, timeout: int = None
    ) -> "Browser":
        """BrowserType.connect

        This methods attaches Playwright to an existing browser instance.

        Parameters
        ----------
        wsEndpoint : str
            A browser websocket endpoint to connect to. **required**
        slowMo : Optional[int]
            Slows down Playwright operations by the specified amount of milliseconds. Useful so that you can see what is going on. Defaults to 0.
        timeout : Optional[int]
            Maximum time in milliseconds to wait for the connection to be established. Defaults to `30000` (30 seconds). Pass `0` to disable timeout.

        Returns
        -------
        Browser
        """
        return mapping.from_impl(
            await self._impl_obj.connect(
                wsEndpoint=wsEndpoint, slowMo=slowMo, timeout=timeout
            )
        )


mapping.register(BrowserTypeImpl, BrowserType)


class Playwright(AsyncBase):
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
    def devices(self) -> typing.Dict[str, DeviceDescriptor]:
        return mapping.from_maybe_impl(self._impl_obj.devices)

    def stop(self) -> NoneType:
        return mapping.from_maybe_impl(self._impl_obj.stop())


mapping.register(PlaywrightImpl, Playwright)
