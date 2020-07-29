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
from playwright.browser_server import BrowserServer as BrowserServerImpl
from playwright.browser_type import BrowserType as BrowserTypeImpl
from playwright.console_message import ConsoleMessage as ConsoleMessageImpl
from playwright.dialog import Dialog as DialogImpl
from playwright.download import Download as DownloadImpl
from playwright.element_handle import ElementHandle as ElementHandleImpl
from playwright.file_chooser import FileChooser as FileChooserImpl
from playwright.frame import Frame as FrameImpl
from playwright.helper import (
    ConsoleMessageLocation,
    DeviceDescriptor,
    Error,
    FilePayload,
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
from playwright.playwright import Playwright as PlaywrightImpl
from playwright.selectors import Selectors as SelectorsImpl
from playwright.worker import Worker as WorkerImpl

NoneType = type(None)


class Request(AsyncBase):
    def __init__(self, obj: RequestImpl):
        super().__init__(obj)

    @property
    def url(self) -> str:
        """
        - returns: <str> URL of the request.
        """
        return mapping.from_maybe_impl(self._impl_obj.url)

    @property
    def resourceType(self) -> str:
        """
        - returns: <str>

        Contains the request's resource type as it was perceived by the rendering engine.
        ResourceType will be one of the following: `document`, `stylesheet`, `image`, `media`, `font`, `script`, `texttrack`, `xhr`, `fetch`, `eventsource`, `websocket`, `manifest`, `other`.
        """
        return mapping.from_maybe_impl(self._impl_obj.resourceType)

    @property
    def method(self) -> str:
        """
        - returns: <str> Request's method (GET, POST, etc.)
        """
        return mapping.from_maybe_impl(self._impl_obj.method)

    @property
    def postData(self) -> typing.Union[str, NoneType]:
        """
        - returns: <Optional[str]> Request's post body, if any.
        """
        return mapping.from_maybe_impl(self._impl_obj.postData)

    @property
    def headers(self) -> typing.Dict[str, str]:
        """
        - returns: <[Dict]<[str], [str]>> An object with HTTP headers associated with the request. All header names are lower-case.
        """
        return mapping.from_maybe_impl(self._impl_obj.headers)

    @property
    def frame(self) -> "Frame":
        """
        - returns: <Frame> A [Frame] that initiated this request.
        """
        return mapping.from_impl(self._impl_obj.frame)

    @property
    def redirectedFrom(self) -> typing.Union["Request", NoneType]:
        """
        - returns: <Optional[Request]> Request that was redirected by the server to this one, if any.

        When the server responds with a redirect, Playwright creates a new [Request] object. The two requests are connected by `redirectedFrom()` and `redirectedTo()` methods. When multiple server redirects has happened, it is possible to construct the whole redirect chain by repeatedly calling `redirectedFrom()`.

        For example, if the website `http://example.com` redirects to `https://example.com`:

        If the website `https://google.com` has no redirects:
        """
        return mapping.from_impl_nullable(self._impl_obj.redirectedFrom)

    @property
    def redirectedTo(self) -> typing.Union["Request", NoneType]:
        """
        - returns: <Optional[Request]> New request issued by the browser if the server responded with redirect.

        This method is the opposite of [request.redirectedFrom()](#requestredirectedfrom):
        """
        return mapping.from_impl_nullable(self._impl_obj.redirectedTo)

    @property
    def failure(self) -> typing.Union[str, NoneType]:
        """
        - returns: <Optional[Dict]> Dict describing request failure, if any
          - `errorText` <str> Human-readable error message, e.g. `'net::ERR_FAILED'`.

        The method returns `null` unless this request has failed, as reported by
        `requestfailed` event.

        Example of logging of all the failed requests:
        """
        return mapping.from_maybe_impl(self._impl_obj.failure)

    async def response(self) -> typing.Union["Response", NoneType]:
        """
        - returns: <Optional[Response]> A matching [Response] object, or `null` if the response was not received due to error.
        """
        return mapping.from_impl_nullable(await self._impl_obj.response())

    def isNavigationRequest(self) -> bool:
        """
        - returns: <bool>

        Whether this request is driving frame's navigation.
        """
        return mapping.from_maybe_impl(self._impl_obj.isNavigationRequest())


mapping.register(RequestImpl, Request)


class Response(AsyncBase):
    def __init__(self, obj: ResponseImpl):
        super().__init__(obj)

    @property
    def url(self) -> str:
        """
        - returns: <str>

        Contains the URL of the response.
        """
        return mapping.from_maybe_impl(self._impl_obj.url)

    @property
    def ok(self) -> bool:
        """
        - returns: <bool>

        Contains a bool stating whether the response was successful (status in the range 200-299) or not.
        """
        return mapping.from_maybe_impl(self._impl_obj.ok)

    @property
    def status(self) -> int:
        """
        - returns: <int>

        Contains the status code of the response (e.g., 200 for a success).
        """
        return mapping.from_maybe_impl(self._impl_obj.status)

    @property
    def statusText(self) -> str:
        """
        - returns: <str>

        Contains the status text of the response (e.g. usually an "OK" for a success).
        """
        return mapping.from_maybe_impl(self._impl_obj.statusText)

    @property
    def headers(self) -> typing.Dict[str, str]:
        """
        - returns: <Dict> An object with HTTP headers associated with the response. All header names are lower-case.
        """
        return mapping.from_maybe_impl(self._impl_obj.headers)

    @property
    def request(self) -> "Request":
        """
        - returns: <Request> A matching [Request] object.
        """
        return mapping.from_impl(self._impl_obj.request)

    @property
    def frame(self) -> "Frame":
        """
        - returns: <Frame> A [Frame] that initiated this response.
        """
        return mapping.from_impl(self._impl_obj.frame)

    async def finished(self) -> typing.Union[Error, NoneType]:
        """
        - returns: <Optional[Error]> Waits for this response to finish, returns failure error if request failed.
        """
        return mapping.from_maybe_impl(await self._impl_obj.finished())

    async def body(self) -> bytes:
        """
        - returns: <bytes> Promise which resolves to a buffer with response body.
        """
        return mapping.from_maybe_impl(await self._impl_obj.body())

    async def text(self) -> str:
        """
        - returns: <str> Promise which resolves to a text representation of response body.
        """
        return mapping.from_maybe_impl(await self._impl_obj.text())

    async def json(self) -> typing.Union[typing.Dict, typing.List]:
        """
        - returns: <Dict> Promise which resolves to a JSON representation of response body.

        This method will throw if the response body is not parsable via `JSON.parse`.
        """
        return mapping.from_maybe_impl(await self._impl_obj.json())


mapping.register(ResponseImpl, Response)


class Route(AsyncBase):
    def __init__(self, obj: RouteImpl):
        super().__init__(obj)

    @property
    def request(self) -> "Request":
        """
        - returns: <Request> A request to be routed.
        """
        return mapping.from_impl(self._impl_obj.request)

    async def abort(self, errorCode: str = "failed") -> NoneType:
        """
        - `errorCode` <str> Optional error code. Defaults to `failed`, could be
          one of the following:
          - `'aborted'` - An operation was aborted (due to user action)
          - `'accessdenied'` - Permission to access a resource, other than the network, was denied
          - `'addressunreachable'` - The IP address is unreachable. This usually means
            that there is no route to the specified host or network.
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
        - returns: <Promise>

        Aborts the route's request.
        """
        return mapping.from_maybe_impl(await self._impl_obj.abort(errorCode=errorCode))

    async def fulfill(
        self,
        status: int = 200,
        headers: typing.Dict[str, str] = {},
        body: typing.Union[str, bytes] = None,
        contentType: str = None,
    ) -> NoneType:
        """
        - `status` <int> Response status code, defaults to `200`.
        - `headers` <[Dict]<[str], [str]>> Optional response headers. Header values will be converted to a str.
        - `contentType` <str> If set, equals to setting `Content-Type` response header.
        - `body` <[str]|[bytes]> Optional response body.
        - `path` <str> Optional file path to respond with. The content type will be inferred from file extension. If `path` is a relative path, then it is resolved relative to [current working directory](https://nodejs.org/api/process.html#process_process_cwd).
        - returns: <Promise>

        Fulfills route's request with given response.

        An example of fulfilling all requests with 404 responses:

        An example of serving static file:
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.fulfill(
                status=status, headers=headers, body=body, contentType=contentType
            )
        )

    async def continue_(
        self,
        method: str = None,
        headers: typing.Union[typing.Dict[str, str]] = None,
        postData: typing.Union[str, bytes] = None,
    ) -> NoneType:
        """
        - `method` <str> If set changes the request method (e.g. GET or POST)
        - `postData` <[str]|[bytes]> If set changes the post data of request
        - `headers` <[Dict]<[str], [str]>> If set changes the request HTTP headers. Header values will be converted to a str.
        - returns: <Promise>

        Continues route's request with optional overrides.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.continue_(
                method=method, headers=headers, postData=postData
            )
        )


mapping.register(RouteImpl, Route)


class Keyboard(AsyncBase):
    def __init__(self, obj: KeyboardImpl):
        super().__init__(obj)

    async def down(self, key: str) -> NoneType:
        """
        - `key` <str> Name of the key to press or a character to generate, such as `ArrowLeft` or `a`.
        - returns: <Promise>

        Dispatches a `keydown` event.

        `key` can specify the intended [keyboardEvent.key](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/key) value or a single character to generate the text for. A superset of the `key` values can be found [here](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/key/Key_Values). Examples of the keys are:

          `F1` - `F12`, `Digit0`- `Digit9`, `KeyA`- `KeyZ`, `Backquote`, `Minus`, `Equal`, `Backslash`, `Backspace`, `Tab`, `Delete`, `Escape`, `ArrowDown`, `End`, `Enter`, `Home`, `Insert`, `PageDown`, `PageUp`, `ArrowRight`, `ArrowUp`, etc.

        Following modification shortcuts are also suported: `Shift`, `Control`, `Alt`, `Meta`, `ShiftLeft`.

        Holding down `Shift` will type the text that corresponds to the `key` in the upper case.

        If `key` is a single character, it is case-sensitive, so the values `a` and `A` will generate different respective texts.

        If `key` is a modifier key, `Shift`, `Meta`, `Control`, or `Alt`, subsequent key presses will be sent with that modifier active. To release the modifier key, use [`keyboard.up`](#keyboardupkey).

        After the key is pressed once, subsequent calls to [`keyboard.down`](#keyboarddownkey) will have [repeat](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/repeat) set to true. To release the key, use [`keyboard.up`](#keyboardupkey).

        > **NOTE** Modifier keys DO influence `keyboard.down`. Holding down `Shift` will type the text in upper case.
        """
        return mapping.from_maybe_impl(await self._impl_obj.down(key=key))

    async def up(self, key: str) -> NoneType:
        """
        - `key` <str> Name of the key to press or a character to generate, such as `ArrowLeft` or `a`.
        - returns: <Promise>

        Dispatches a `keyup` event.
        """
        return mapping.from_maybe_impl(await self._impl_obj.up(key=key))

    async def insertText(self, text: str) -> NoneType:
        """
        - `text` <str> Sets input to the specified text value.
        - returns: <Promise>

        Dispatches only `input` event, does not emit the `keydown`, `keyup` or `keypress` events.

        > **NOTE** Modifier keys DO NOT effect `keyboard.insertText`. Holding down `Shift` will not type the text in upper case.
        """
        return mapping.from_maybe_impl(await self._impl_obj.insertText(text=text))

    async def type(self, text: str, delay: int = None) -> NoneType:
        """
        - `text` <str> A text to type into a focused element.
        - `delay` <int> Time to wait between key presses in milliseconds. Defaults to 0.
        - returns: <Promise>

        Sends a `keydown`, `keypress`/`input`, and `keyup` event for each character in the text.

        To press a special key, like `Control` or `ArrowDown`, use [`keyboard.press`](#keyboardpresskey-options).

        > **NOTE** Modifier keys DO NOT effect `keyboard.type`. Holding down `Shift` will not type the text in upper case.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.type(text=text, delay=delay)
        )

    async def press(self, key: str, delay: int = None) -> NoneType:
        """
        - `key` <str> Name of the key to press or a character to generate, such as `ArrowLeft` or `a`.
        - `delay` <int> Time to wait between `keydown` and `keyup` in milliseconds. Defaults to 0.
        - returns: <Promise>

        `key` can specify the intended [keyboardEvent.key](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/key) value or a single character to generate the text for. A superset of the `key` values can be found [here](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/key/Key_Values). Examples of the keys are:

          `F1` - `F12`, `Digit0`- `Digit9`, `KeyA`- `KeyZ`, `Backquote`, `Minus`, `Equal`, `Backslash`, `Backspace`, `Tab`, `Delete`, `Escape`, `ArrowDown`, `End`, `Enter`, `Home`, `Insert`, `PageDown`, `PageUp`, `ArrowRight`, `ArrowUp`, etc.

        Following modification shortcuts are also suported: `Shift`, `Control`, `Alt`, `Meta`, `ShiftLeft`.

        Holding down `Shift` will type the text that corresponds to the `key` in the upper case.

        If `key` is a single character, it is case-sensitive, so the values `a` and `A` will generate different respective texts.

        Shortcuts such as `key: "Control+o"` or `key: "Control+Shift+T"` are supported as well. When speficied with the modifier, modifier is pressed and being held while the subsequent key is being pressed.
        """
        return mapping.from_maybe_impl(await self._impl_obj.press(key=key, delay=delay))


mapping.register(KeyboardImpl, Keyboard)


class Mouse(AsyncBase):
    def __init__(self, obj: MouseImpl):
        super().__init__(obj)

    async def move(self, x: float, y: float, steps: int = None) -> NoneType:
        """
        - `x` <int>
        - `y` <int>
        - `steps` <int> defaults to 1. Sends intermediate `mousemove` events.
        - returns: <Promise>

        Dispatches a `mousemove` event.
        """
        return mapping.from_maybe_impl(await self._impl_obj.move(x=x, y=y, steps=steps))

    async def down(
        self, button: Literal["left", "right", "middle"] = None, clickCount: int = None
    ) -> NoneType:
        """
        - `button` <"left"|"right"|"middle"> Defaults to `left`.
        - `clickCount` <int> defaults to 1. See [UIEvent.detail].
        - returns: <Promise>

        Dispatches a `mousedown` event.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.down(button=button, clickCount=clickCount)
        )

    async def up(
        self, button: Literal["left", "right", "middle"] = None, clickCount: int = None
    ) -> NoneType:
        """
        - `button` <"left"|"right"|"middle"> Defaults to `left`.
        - `clickCount` <int> defaults to 1. See [UIEvent.detail].
        - returns: <Promise>

        Dispatches a `mouseup` event.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.up(button=button, clickCount=clickCount)
        )

    async def click(
        self,
        x: float,
        y: float,
        delay: int = None,
        button: Literal["left", "right", "middle"] = None,
        clickCount: int = None,
    ) -> NoneType:
        """
        - `x` <int>
        - `y` <int>
        - `button` <"left"|"right"|"middle"> Defaults to `left`.
        - `clickCount` <int> defaults to 1. See [UIEvent.detail].
        - `delay` <int> Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        - returns: <Promise>
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
        button: Literal["left", "right", "middle"] = None,
    ) -> NoneType:
        """
        - `x` <int>
        - `y` <int>
        - `button` <"left"|"right"|"middle"> Defaults to `left`.
        - `delay` <int> Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        - returns: <Promise>
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.dblclick(x=x, y=y, delay=delay, button=button)
        )


mapping.register(MouseImpl, Mouse)


class JSHandle(AsyncBase):
    def __init__(self, obj: JSHandleImpl):
        super().__init__(obj)

    async def evaluate(
        self, expression: str, arg: typing.Any = None, force_expr: bool = False
    ) -> typing.Any:
        """
        - `expression` <[str]> Function to be evaluated in browser context
        - `force_expr` <[bool]> Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        - `arg` <[Serializable]|[JSHandle]> Optional argument to pass to `pageFunction`
        - returns: <Serializable> Promise which resolves to the return value of `pageFunction`

        This method passes this handle as the first argument to `pageFunction`.

        If `pageFunction` returns a [Promise], then `handle.evaluate` would wait for the promise to resolve and return its value.

        Examples:
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.evaluate(
                expression=expression, arg=mapping.to_impl(arg), force_expr=force_expr
            )
        )

    async def evaluateHandle(
        self, expression: str, arg: typing.Any = None, force_expr: bool = False
    ) -> "JSHandle":
        """
        - `expression` <[str]> Function to be evaluated
        - `force_expr` <[bool]> Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        - `arg` <[Serializable]|[JSHandle]> Optional argument to pass to `pageFunction`
        - returns: <JSHandle> Promise which resolves to the return value of `pageFunction` as in-page object (JSHandle)

        This method passes this handle as the first argument to `pageFunction`.

        The only difference between `jsHandle.evaluate` and `jsHandle.evaluateHandle` is that `jsHandle.evaluateHandle` returns in-page object (JSHandle).

        If the function passed to the `jsHandle.evaluateHandle` returns a [Promise], then `jsHandle.evaluateHandle` would wait for the promise to resolve and return its value.

        See [page.evaluateHandle()](#pageevaluatehandlepagefunction-arg) for more details.
        """
        return mapping.from_impl(
            await self._impl_obj.evaluateHandle(
                expression=expression, arg=mapping.to_impl(arg), force_expr=force_expr
            )
        )

    async def getProperty(self, propertyName: str) -> "JSHandle":
        """
        - `propertyName` <str> property to get
        - returns: <JSHandle>

        Fetches a single property from the referenced object.
        """
        return mapping.from_impl(
            await self._impl_obj.getProperty(propertyName=propertyName)
        )

    async def getProperties(self) -> typing.Dict[str, "JSHandle"]:
        """
        - returns: <[Map]<[str], [JSHandle]>>

        The method returns a map with **own property names** as keys and JSHandle instances for the property values.
        """
        return mapping.from_impl_dict(await self._impl_obj.getProperties())

    def asElement(self) -> typing.Union["ElementHandle", NoneType]:
        """
        - returns: <Optional[ElementHandle]>

        Returns either `null` or the object handle itself, if the object handle is an instance of [ElementHandle].
        """
        return mapping.from_impl_nullable(self._impl_obj.asElement())

    async def dispose(self) -> NoneType:
        """
        - returns: <Promise> Promise which resolves when the object handle is successfully disposed.

        The `jsHandle.dispose` method stops referencing the element handle.
        """
        return mapping.from_maybe_impl(await self._impl_obj.dispose())

    async def jsonValue(self) -> typing.Any:
        """
        - returns: <Dict>

        Returns a JSON representation of the object. If the object has a
        [`toJSON`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Dicts/JSON/strify#toJSON()_behavior)
        function, it **will not be called**.

        > **NOTE** The method will return an empty JSON object if the referenced object is not strifiable. It will throw an error if the object has circular references.
        """
        return mapping.from_maybe_impl(await self._impl_obj.jsonValue())


mapping.register(JSHandleImpl, JSHandle)


class ElementHandle(JSHandle):
    def __init__(self, obj: ElementHandleImpl):
        super().__init__(obj)

    def asElement(self) -> typing.Union["ElementHandle", NoneType]:
        """
        - returns: <Optional[ElementHandle]>

        Returns either `null` or the object handle itself, if the object handle is an instance of [ElementHandle].
        """
        return mapping.from_impl_nullable(self._impl_obj.asElement())

    async def ownerFrame(self) -> typing.Union["Frame", NoneType]:
        """
        - returns: <Optional[Frame]> Returns the frame containing the given element.
        """
        return mapping.from_impl_nullable(await self._impl_obj.ownerFrame())

    async def contentFrame(self) -> typing.Union["Frame", NoneType]:
        """
        - returns: <Optional[Frame]> Resolves to the content frame for element handles referencing iframe nodes, or `null` otherwise
        """
        return mapping.from_impl_nullable(await self._impl_obj.contentFrame())

    async def getAttribute(self, name: str) -> str:
        """
        - `name` <str> Attribute name to get the value for.
        - returns: <null|[str]>

        Returns element attribute value.
        """
        return mapping.from_maybe_impl(await self._impl_obj.getAttribute(name=name))

    async def textContent(self) -> str:
        """
        - returns: <null|[str]> Resolves to the `node.textContent`.
        """
        return mapping.from_maybe_impl(await self._impl_obj.textContent())

    async def innerText(self) -> str:
        """
        - returns: <str> Resolves to the `element.innerText`.
        """
        return mapping.from_maybe_impl(await self._impl_obj.innerText())

    async def innerHTML(self) -> str:
        """
        - returns: <str> Resolves to the `element.innerHTML`.
        """
        return mapping.from_maybe_impl(await self._impl_obj.innerHTML())

    async def dispatchEvent(self, type: str, eventInit: typing.Dict = None) -> NoneType:
        """
        - `type` <str> DOM event type: `"click"`, `"dragstart"`, etc.
        - `eventInit` <Dict> event-specific initialization properties.
        - returns: <Promise>

        The snippet below dispatches the `click` event on the element. Regardless of the visibility state of the elment, `click` is dispatched. This is equivalend to calling [`element.click()`](https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/click).

        Under the hood, it creates an instance of an event based on the given `type`, initializes it with `eventInit` properties and dispatches it on the element. Events are `composed`, `cancelable` and bubble by default.

        Since `eventInit` is event-specific, please refer to the events documentation for the lists of initial properties:
        - [DragEvent](https://developer.mozilla.org/en-US/docs/Web/API/DragEvent/DragEvent)
        - [FocusEvent](https://developer.mozilla.org/en-US/docs/Web/API/FocusEvent/FocusEvent)
        - [KeyboardEvent](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/KeyboardEvent)
        - [MouseEvent](https://developer.mozilla.org/en-US/docs/Web/API/MouseEvent/MouseEvent)
        - [PointerEvent](https://developer.mozilla.org/en-US/docs/Web/API/PointerEvent/PointerEvent)
        - [TouchEvent](https://developer.mozilla.org/en-US/docs/Web/API/TouchEvent/TouchEvent)
        - [Event](https://developer.mozilla.org/en-US/docs/Web/API/Event/Event)

         You can also specify `JSHandle` as the property value if you want live objects to be passed into the event:
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.dispatchEvent(type=type, eventInit=eventInit)
        )

    async def scrollIntoViewIfNeeded(self, timeout: int = None) -> NoneType:
        """
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Promise>
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.scrollIntoViewIfNeeded(timeout=timeout)
        )

    async def hover(
        self,
        modifiers: typing.Union[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: typing.Dict = None,
        timeout: int = None,
        force: bool = None,
    ) -> NoneType:
        """
        - `position` <Dict> A point to hover relative to the top-left corner of element padding box. If not specified, hovers over some visible point of the element.
          - x <int>
          - y <int>
        - `modifiers` <[List]<"Alt"|"Control"|"Meta"|"Shift">> Modifier keys to press. Ensures that only these modifiers are pressed during the hover, and then restores current modifiers back. If not specified, currently pressed modifiers are used.
        - `force` <bool> Whether to bypass the [actionability](./actionability.md) checks. Defaults to `false`.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Promise> Promise which resolves when the element is successfully hovered.

        This method scrolls element into view if needed, and then uses [page.mouse](#pagemouse) to hover over the center of the element.
        If the element is detached from DOM, the method throws an error.
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
        position: typing.Dict = None,
        delay: int = None,
        button: Literal["left", "right", "middle"] = None,
        clickCount: int = None,
        timeout: int = None,
        force: bool = None,
        noWaitAfter: bool = None,
    ) -> NoneType:
        """
        - `button` <"left"|"right"|"middle"> Defaults to `left`.
        - `clickCount` <int> defaults to 1. See [UIEvent.detail].
        - `delay` <int> Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        - `position` <Dict> A point to click relative to the top-left corner of element padding box. If not specified, clicks to some visible point of the element.
          - x <int>
          - y <int>
        - `modifiers` <[List]<"Alt"|"Control"|"Meta"|"Shift">> Modifier keys to press. Ensures that only these modifiers are pressed during the click, and then restores current modifiers back. If not specified, currently pressed modifiers are used.
        - `force` <bool> Whether to bypass the [actionability](./actionability.md) checks. Defaults to `false`.
        - `noWaitAfter` <bool> Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Promise> Promise which resolves when the element is successfully clicked. Promise gets rejected if the element is detached from DOM.

        This method scrolls element into view if needed, and then uses [page.mouse](#pagemouse) to click in the center of the element.
        If the element is detached from DOM, the method throws an error.
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
        position: typing.Dict = None,
        delay: int = None,
        button: Literal["left", "right", "middle"] = None,
        timeout: int = None,
        force: bool = None,
        noWaitAfter: bool = None,
    ) -> NoneType:
        """
        - `button` <"left"|"right"|"middle"> Defaults to `left`.
        - `delay` <int> Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        - `position` <Dict> A point to double click relative to the top-left corner of element padding box. If not specified, double clicks to some visible point of the element.
          - x <int>
          - y <int>
        - `modifiers` <[List]<"Alt"|"Control"|"Meta"|"Shift">> Modifier keys to press. Ensures that only these modifiers are pressed during the double click, and then restores current modifiers back. If not specified, currently pressed modifiers are used.
        - `force` <bool> Whether to bypass the [actionability](./actionability.md) checks. Defaults to `false`.
        - `noWaitAfter` <bool> Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Promise> Promise which resolves when the element is successfully double clicked. Promise gets rejected if the element is detached from DOM.

        This method scrolls element into view if needed, and then uses [page.mouse](#pagemouse) to click in the center of the element.
        If the element is detached from DOM, the method throws an error.

        Bear in mind that if the first click of the `dblclick()` triggers a navigation event, there will be an exception.

        > **NOTE** `elementHandle.dblclick()` dispatches two `click` events and a single `dblclick` event.
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
        ],
        timeout: int = None,
        noWaitAfter: bool = None,
    ) -> typing.List[str]:
        """
        - `values` <null|[str]|[ElementHandle]|[List]<str>|[Dict]|[List]<ElementHandle>|[List]<Dict>> Options to select. If the `<select>` has the `multiple` attribute, all matching options are selected, otherwise only the first option matching one of the passed options is selected. String values are equivalent to `{value:'str'}`. Option is considered matching if all specified properties match.
          - `value` <str> Matches by `option.value`.
          - `label` <str> Matches by `option.label`.
          - `index` <int> Matches by the index.
        - `noWaitAfter` <bool> Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <List[str]> An array of option values that have been successfully selected.

        Triggers a `change` and `input` event once all the provided options have been selected.
        If element is not a `<select>` element, the method throws an error.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.selectOption(
                values=mapping.to_impl(values), timeout=timeout, noWaitAfter=noWaitAfter
            )
        )

    async def fill(
        self, value: str, timeout: int = None, noWaitAfter: bool = None
    ) -> NoneType:
        """
        - `value` <str> Value to set for the `<input>`, `<textarea>` or `[contenteditable]` element.
        - `noWaitAfter` <bool> Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Promise>

        This method waits for [actionability](./actionability.md) checks, focuses the element, fills it and triggers an `input` event after filling.
        If the element is not an `<input>`, `<textarea>` or `[contenteditable]` element, this method throws an error.
        Note that you can pass an empty str to clear the input field.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.fill(
                value=value, timeout=timeout, noWaitAfter=noWaitAfter
            )
        )

    async def selectText(self, timeout: int = None) -> NoneType:
        """
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Promise>

        This method waits for [actionability](./actionability.md) checks, then focuses the element and selects all its text content.
        """
        return mapping.from_maybe_impl(await self._impl_obj.selectText(timeout=timeout))

    async def setInputFiles(
        self,
        files: typing.Union[
            str, FilePayload, typing.List[str], typing.List[FilePayload]
        ],
        timeout: int = None,
        noWaitAfter: bool = None,
    ) -> NoneType:
        """
        - `files` <[str]|[List]<str>|[Dict]|[List]<Dict>>
          - `name` <str> [File] name **required**
          - `mimeType` <str> [File] type **required**
          - `buffer` <bytes> File content **required**
        - `noWaitAfter` <bool> Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Promise>

        This method expects `elementHandle` to point to an [input element](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/input).

        Sets the value of the file input to these file paths or files. If some of the `filePaths` are relative paths, then they are resolved relative to the [current working directory](https://nodejs.org/api/process.html#process_process_cwd). For empty array, clears the selected files.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.setInputFiles(
                files=files, timeout=timeout, noWaitAfter=noWaitAfter
            )
        )

    async def focus(self) -> NoneType:
        """
        - returns: <Promise>

        Calls [focus](https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/focus) on the element.
        """
        return mapping.from_maybe_impl(await self._impl_obj.focus())

    async def type(
        self,
        text: str,
        delay: int = None,
        timeout: int = None,
        noWaitAfter: bool = None,
    ) -> NoneType:
        """
        - `text` <str> A text to type into a focused element.
        - `delay` <int> Time to wait between key presses in milliseconds. Defaults to 0.
        - `noWaitAfter` <bool> Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Promise>

        Focuses the element, and then sends a `keydown`, `keypress`/`input`, and `keyup` event for each character in the text.

        To press a special key, like `Control` or `ArrowDown`, use [`elementHandle.press`](#elementhandlepresskey-options).

        An example of typing into a text field and then submitting the form:
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.type(
                text=text, delay=delay, timeout=timeout, noWaitAfter=noWaitAfter
            )
        )

    async def press(
        self, key: str, delay: int = None, timeout: int = None, noWaitAfter: bool = None
    ) -> NoneType:
        """
        - `key` <str> Name of the key to press or a character to generate, such as `ArrowLeft` or `a`.
        - `delay` <int> Time to wait between `keydown` and `keyup` in milliseconds. Defaults to 0.
        - `noWaitAfter` <bool> Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Promise>

        Focuses the element, and then uses [`keyboard.down`](#keyboarddownkey) and [`keyboard.up`](#keyboardupkey).

        `key` can specify the intended [keyboardEvent.key](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/key) value or a single character to generate the text for. A superset of the `key` values can be found [here](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/key/Key_Values). Examples of the keys are:

          `F1` - `F12`, `Digit0`- `Digit9`, `KeyA`- `KeyZ`, `Backquote`, `Minus`, `Equal`, `Backslash`, `Backspace`, `Tab`, `Delete`, `Escape`, `ArrowDown`, `End`, `Enter`, `Home`, `Insert`, `PageDown`, `PageUp`, `ArrowRight`, `ArrowUp`, etc.

        Following modification shortcuts are also suported: `Shift`, `Control`, `Alt`, `Meta`, `ShiftLeft`.

        Holding down `Shift` will type the text that corresponds to the `key` in the upper case.

        If `key` is a single character, it is case-sensitive, so the values `a` and `A` will generate different respective texts.

        Shortcuts such as `key: "Control+o"` or `key: "Control+Shift+T"` are supported as well. When speficied with the modifier, modifier is pressed and being held while the subsequent key is being pressed.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.press(
                key=key, delay=delay, timeout=timeout, noWaitAfter=noWaitAfter
            )
        )

    async def check(
        self, timeout: int = None, force: bool = None, noWaitAfter: bool = None
    ) -> NoneType:
        """
        - `force` <bool> Whether to bypass the [actionability](./actionability.md) checks. Defaults to `false`.
        - `noWaitAfter` <bool> Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Promise> Promise which resolves when the element is successfully checked. Promise gets rejected if the operation fails.

        If element is not already checked, it scrolls it into view if needed, and then uses [elementHandle.click](#elementhandleclickoptions) to click in the center of the element.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.check(
                timeout=timeout, force=force, noWaitAfter=noWaitAfter
            )
        )

    async def uncheck(
        self, timeout: int = None, force: bool = None, noWaitAfter: bool = None
    ) -> NoneType:
        """
        - `force` <bool> Whether to bypass the [actionability](./actionability.md) checks. Defaults to `false`.
        - `noWaitAfter` <bool> Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Promise> Promise which resolves when the element is successfully unchecked. Promise gets rejected if the operation fails.

        If element is not already unchecked, it scrolls it into view if needed, and then uses [elementHandle.click](#elementhandleclickoptions) to click in the center of the element.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.uncheck(
                timeout=timeout, force=force, noWaitAfter=noWaitAfter
            )
        )

    async def boundingBox(self) -> typing.Dict[str, float]:
        """
        - returns: <Optional[Dict]>
          - x <int> the x coordinate of the element in pixels.
          - y <int> the y coordinate of the element in pixels.
          - width <int> the width of the element in pixels.
          - height <int> the height of the element in pixels.

        This method returns the bounding box of the element (relative to the main frame), or `null` if the element is not visible.
        """
        return mapping.from_maybe_impl(await self._impl_obj.boundingBox())

    async def screenshot(
        self,
        timeout: int = None,
        type: Literal["png", "jpeg"] = None,
        path: str = None,
        quality: int = None,
        omitBackground: bool = None,
    ) -> bytes:
        """
        - `path` <str> The file path to save the image to. The screenshot type will be inferred from file extension. If `path` is a relative path, then it is resolved relative to [current working directory](https://nodejs.org/api/process.html#process_process_cwd). If no path is provided, the image won't be saved to the disk.
        - `type` <"png"|"jpeg"> Specify screenshot type, defaults to `png`.
        - `quality` <int> The quality of the image, between 0-100. Not applicable to `png` images.
        - `omitBackground` <bool> Hides default white background and allows capturing screenshots with transparency. Not applicable to `jpeg` images. Defaults to `false`.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <bytes> Promise which resolves to buffer with the captured screenshot.

        This method waits for the [actionability](./actionability.md) checks, then scrolls element into view before taking a screenshot. If the element is detached from DOM, the method throws an error.
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
        """
        - `selector` <str> A selector to query element for. See [working with selectors](#working-with-selectors) for more details.
        - returns: <Optional[ElementHandle]>

        The method finds an element matching the specified selector in the `ElementHandle`'s subtree. See [Working with selectors](#working-with-selectors) for more details. If no elements match the selector, the return value resolves to `null`.
        """
        return mapping.from_impl_nullable(
            await self._impl_obj.querySelector(selector=selector)
        )

    async def querySelectorAll(self, selector: str) -> typing.List["ElementHandle"]:
        """
        - `selector` <str> A selector to query element for. See [working with selectors](#working-with-selectors) for more details.
        - returns: <List[ElementHandle]>

        The method finds all elements matching the specified selector in the `ElementHandle`s subtree. See [Working with selectors](#working-with-selectors) for more details. If no elements match the selector, the return value resolves to `[]`.
        """
        return mapping.from_impl_list(
            await self._impl_obj.querySelectorAll(selector=selector)
        )

    async def evalOnSelector(
        self,
        selector: str,
        expression: str,
        arg: typing.Any = None,
        force_expr: bool = False,
    ) -> typing.Any:
        """
        - `selector` <str> A selector to query element for. See [working with selectors](#working-with-selectors) for more details.
        - `expression` <[str]> Function to be evaluated in browser context
        - `force_expr` <[bool]> Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        - `arg` <[Serializable]|[JSHandle]> Optional argument to pass to `pageFunction`
        - returns: <Serializable> Promise which resolves to the return value of `pageFunction`

        The method finds an element matching the specified selector in the `ElementHandle`s subtree and passes it as a first argument to `pageFunction`. See [Working with selectors](#working-with-selectors) for more details. If no elements match the selector, the method throws an error.

        If `pageFunction` returns a [Promise], then `frame.$eval` would wait for the promise to resolve and return its value.

        Examples:
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
        force_expr: bool = False,
    ) -> typing.Any:
        """
        - `selector` <str> A selector to query element for. See [working with selectors](#working-with-selectors) for more details.
        - `expression` <[str]>\\)> Function to be evaluated in browser context
        - `force_expr` <[bool]> Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        - `arg` <[Serializable]|[JSHandle]> Optional argument to pass to `pageFunction`
        - returns: <Serializable> Promise which resolves to the return value of `pageFunction`

        The method finds all elements matching the specified selector in the `ElementHandle`'s subtree and passes an array of matched elements as a first argument to `pageFunction`. See [Working with selectors](#working-with-selectors) for more details.

        If `pageFunction` returns a [Promise], then `frame.$$eval` would wait for the promise to resolve and return its value.

        Examples:
        <div class="feed">
          <div class="tweet">Hello!</div>
          <div class="tweet">Hi!</div>
        </div>
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.evalOnSelectorAll(
                selector=selector,
                expression=expression,
                arg=mapping.to_impl(arg),
                force_expr=force_expr,
            )
        )


mapping.register(ElementHandleImpl, ElementHandle)


class Accessibility(AsyncBase):
    def __init__(self, obj: AccessibilityImpl):
        super().__init__(obj)

    async def snapshot(
        self, interestingOnly: bool = True, root: "ElementHandle" = None
    ) -> typing.Union[typing.Dict[str, typing.Any], NoneType]:
        """
        - `interestingOnly` <bool> Prune uninteresting nodes from the tree. Defaults to `true`.
        - `root` <ElementHandle> The root DOM element for the snapshot. Defaults to the whole page.
        - returns: <Optional[Dict]> An [AXNode] object with the following properties:
          - `role` <str> The [role](https://www.w3.org/TR/wai-aria/#usage_intro).
          - `name` <str> A human readable name for the node.
          - `value` <[str]|[int]> The current value of the node, if applicable.
          - `description` <str> An additional human readable description of the node, if applicable.
          - `keyshortcuts` <str> Keyboard shortcuts associated with this node, if applicable.
          - `roledescription` <str> A human readable alternative to the role, if applicable.
          - `valuetext` <str> A description of the current value, if applicable.
          - `disabled` <bool> Whether the node is disabled, if applicable.
          - `expanded` <bool> Whether the node is expanded or collapsed, if applicable.
          - `focused` <bool> Whether the node is focused, if applicable.
          - `modal` <bool> Whether the node is [modal](https://en.wikipedia.org/wiki/Modal_window), if applicable.
          - `multiline` <bool> Whether the node text input supports multiline, if applicable.
          - `multiselectable` <bool> Whether more than one child can be selected, if applicable.
          - `readonly` <bool> Whether the node is read only, if applicable.
          - `required` <bool> Whether the node is required, if applicable.
          - `selected` <bool> Whether the node is selected in its parent node, if applicable.
          - `checked` <[bool]|"mixed"> Whether the checkbox is checked, or "mixed", if applicable.
          - `pressed` <[bool]|"mixed"> Whether the toggle button is checked, or "mixed", if applicable.
          - `level` <int> The level of a heading, if applicable.
          - `valuemin` <int> The minimum value in a node, if applicable.
          - `valuemax` <int> The maximum value in a node, if applicable.
          - `autocomplete` <str> What kind of autocomplete is supported by a control, if applicable.
          - `haspopup` <str> What kind of popup is currently being shown for a node, if applicable.
          - `invalid` <str> Whether and in what way this node's value is invalid, if applicable.
          - `orientation` <str> Whether the node is oriented horizontally or vertically, if applicable.
          - `children` <List[Dict]> Child [AXNode]s of this node, if any, if applicable.

        Captures the current state of the accessibility tree. The returned object represents the root accessible node of the page.

        > **NOTE** The Chromium accessibility tree contains nodes that go unused on most platforms and by
        most screen readers. Playwright will discard them as well for an easier to process tree,
        unless `interestingOnly` is set to `false`.

        An example of dumping the entire accessibility tree:

        An example of logging the focused node's name:
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
        """
        - returns: <Page>

        Returns page this file chooser belongs to.
        """
        return mapping.from_impl(self._impl_obj.page)

    @property
    def element(self) -> "ElementHandle":
        """
        - returns: <ElementHandle>

        Returns input element associated with this file chooser.
        """
        return mapping.from_impl(self._impl_obj.element)

    @property
    def isMultiple(self) -> bool:
        """
        - returns: <bool>

        Returns whether this file chooser accepts multiple files.
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
        """
        - `files` <[str]|[List]<str>|[Dict]|[List]<Dict>>
          - `name` <str> [File] name **required**
          - `mimeType` <str> [File] type **required**
          - `buffer` <bytes> File content **required**
        - `noWaitAfter` <bool> Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Promise>

        Sets the value of the file input this chooser is associated with. If some of the `filePaths` are relative paths, then they are resolved relative to the [current working directory](https://nodejs.org/api/process.html#process_process_cwd). For empty array, clears the selected files.
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
    def name(self) -> str:
        """
        - returns: <str>

        Returns frame's name attribute as specified in the tag.

        If the name is empty, returns the id attribute instead.

        > **NOTE** This value is calculated once when the frame is created, and will not update if the attribute is changed later.
        """
        return mapping.from_maybe_impl(self._impl_obj.name)

    @property
    def url(self) -> str:
        """
        - returns: <str>

        Returns frame's url.
        """
        return mapping.from_maybe_impl(self._impl_obj.url)

    @property
    def parentFrame(self) -> typing.Union["Frame", NoneType]:
        """
        - returns: <Optional[Frame]> Parent frame, if any. Detached frames and main frames return `null`.
        """
        return mapping.from_impl_nullable(self._impl_obj.parentFrame)

    @property
    def childFrames(self) -> typing.List["Frame"]:
        """
        - returns: <List[Frame]>
        """
        return mapping.from_impl_list(self._impl_obj.childFrames)

    async def goto(
        self,
        url: str,
        timeout: int = None,
        waitUntil: Literal["load", "domcontentloaded", "networkidle"] = "load",
        referer: str = None,
    ) -> typing.Union["Response", NoneType]:
        """
        - `url` <str> URL to navigate frame to. The url should include scheme, e.g. `https://`.
        - `timeout` <int> Maximum navigation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultNavigationTimeout(timeout)](#browsercontextsetdefaultnavigationtimeouttimeout), [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout), [page.setDefaultNavigationTimeout(timeout)](#pagesetdefaultnavigationtimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - `waitUntil` <"load"|"domcontentloaded"|"networkidle"> When to consider navigation succeeded, defaults to `load`. Events can be either:
          - `'domcontentloaded'` - consider navigation to be finished when the `DOMContentLoaded` event is fired.
          - `'load'` - consider navigation to be finished when the `load` event is fired.
          - `'networkidle'` - consider navigation to be finished when there are no network connections for at least `500` ms.
        - `referer` <str> Referer header value. If provided it will take preference over the referer header value set by [page.setExtraHTTPHeaders()](#pagesetextrahttpheadersheaders).
        - returns: <Optional[Response]> Promise which resolves to the main resource response. In case of multiple redirects, the navigation will resolve with the response of the last redirect.

        `frame.goto` will throw an error if:
        - there's an SSL error (e.g. in case of self-signed certificates).
        - target URL is invalid.
        - the `timeout` is exceeded during navigation.
        - the remote server does not respond or is unreachable.
        - the main resource failed to load.

        `frame.goto` will not throw an error when any valid HTTP status code is returned by the remote server, including 404 "Not Found" and 500 "Internal Server Error".  The status code for such responses can be retrieved by calling [response.status()](#responsestatus).

        > **NOTE** `frame.goto` either throws an error or returns a main resource response. The only exceptions are navigation to `about:blank` or navigation to the same URL with a different hash, which would succeed and return `null`.

        > **NOTE** Headless mode doesn't support navigation to a PDF document. See the [upstream issue](https://bugs.chromium.org/p/chromium/issues/detail?id=761295).
        """
        return mapping.from_impl_nullable(
            await self._impl_obj.goto(
                url=url, timeout=timeout, waitUntil=waitUntil, referer=referer
            )
        )

    async def waitForNavigation(
        self,
        timeout: int = None,
        waitUntil: Literal["load", "domcontentloaded", "networkidle"] = "load",
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]] = None,
    ) -> typing.Union["Response", NoneType]:
        """
        - `timeout` <int> Maximum navigation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultNavigationTimeout(timeout)](#browsercontextsetdefaultnavigationtimeouttimeout), [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout), [page.setDefaultNavigationTimeout(timeout)](#pagesetdefaultnavigationtimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - `url` <[str]|[RegExp]|[Function]> URL str, URL regex pattern or predicate receiving [URL] to match while waiting for the navigation.
        - `waitUntil` <"load"|"domcontentloaded"|"networkidle"> When to consider navigation succeeded, defaults to `load`. Events can be either:
          - `'domcontentloaded'` - consider navigation to be finished when the `DOMContentLoaded` event is fired.
          - `'load'` - consider navigation to be finished when the `load` event is fired.
          - `'networkidle'` - consider navigation to be finished when there are no network connections for at least `500` ms.
        - returns: <Optional[Response]> Promise which resolves to the main resource response. In case of multiple redirects, the navigation will resolve with the response of the last redirect. In case of navigation to a different anchor or navigation due to History API usage, the navigation will resolve with `null`.

        This resolves when the frame navigates to a new URL. It is useful for when you run code
        which will indirectly cause the frame to navigate. Consider this example:

        **NOTE** Usage of the [History API](https://developer.mozilla.org/en-US/docs/Web/API/History_API) to change the URL is considered a navigation.
        """
        return mapping.from_impl_nullable(
            await self._impl_obj.waitForNavigation(
                timeout=timeout, waitUntil=waitUntil, url=self._wrap_handler(url)
            )
        )

    async def waitForLoadState(
        self,
        state: Literal["load", "domcontentloaded", "networkidle"] = "load",
        timeout: int = None,
    ) -> NoneType:
        """
        - `state` <"load"|"domcontentloaded"|"networkidle"> Load state to wait for, defaults to `load`. If the state has been already reached while loading current document, the method resolves immediately.
          - `'load'` - wait for the `load` event to be fired.
          - `'domcontentloaded'` - wait for the `DOMContentLoaded` event to be fired.
          - `'networkidle'` - wait until there are no network connections for at least `500` ms.
        - `timeout` <int> Maximum waiting time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultNavigationTimeout(timeout)](#browsercontextsetdefaultnavigationtimeouttimeout), [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout), [page.setDefaultNavigationTimeout(timeout)](#pagesetdefaultnavigationtimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Promise> Promise which resolves when the required load state has been reached.

        This resolves when the frame reaches a required load state, `load` by default. The navigation must have been committed when this method is called. If current document has already reached the required state, resolves immediately.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.waitForLoadState(state=state, timeout=timeout)
        )

    async def frameElement(self) -> "ElementHandle":
        """
        - returns: <ElementHandle> Promise that resolves with a `frame` or `iframe` element handle which corresponds to this frame.

        This is an inverse of [elementHandle.contentFrame()](#elementhandlecontentframe). Note that returned handle actually belongs to the parent frame.

        This method throws an error if the frame has been detached before `frameElement()` returns.
        """
        return mapping.from_impl(await self._impl_obj.frameElement())

    async def evaluate(
        self, expression: str, arg: typing.Any = None, force_expr: bool = False
    ) -> typing.Any:
        """
        - `expression` <[str]> Function to be evaluated in browser context
        - `force_expr` <[bool]> Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        - `arg` <[Serializable]|[JSHandle]> Optional argument to pass to `pageFunction`
        - returns: <Serializable> Promise which resolves to the return value of `pageFunction`

        If the function passed to the `frame.evaluate` returns a [Promise], then `frame.evaluate` would wait for the promise to resolve and return its value.

        If the function passed to the `frame.evaluate` returns a non-[Serializable] value, then `frame.evaluate` resolves to `undefined`. DevTools Protocol also supports transferring some additional values that are not serializable by `JSON`: `-0`, `NaN`, `Infinity`, `-Infinity`, and bigint literals.

        A str can also be passed in instead of a function.

        [ElementHandle] instances can be passed as an argument to the `frame.evaluate`:
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.evaluate(
                expression=expression, arg=mapping.to_impl(arg), force_expr=force_expr
            )
        )

    async def evaluateHandle(
        self, expression: str, arg: typing.Any = None, force_expr: bool = False
    ) -> "JSHandle":
        """
        - `expression` <[str]> Function to be evaluated in the page context
        - `force_expr` <[bool]> Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        - `arg` <[Serializable]|[JSHandle]> Optional argument to pass to `pageFunction`
        - returns: <JSHandle> Promise which resolves to the return value of `pageFunction` as in-page object (JSHandle)

        The only difference between `frame.evaluate` and `frame.evaluateHandle` is that `frame.evaluateHandle` returns in-page object (JSHandle).

        If the function, passed to the `frame.evaluateHandle`, returns a [Promise], then `frame.evaluateHandle` would wait for the promise to resolve and return its value.

        A str can also be passed in instead of a function.

        [JSHandle] instances can be passed as an argument to the `frame.evaluateHandle`:
        """
        return mapping.from_impl(
            await self._impl_obj.evaluateHandle(
                expression=expression, arg=mapping.to_impl(arg), force_expr=force_expr
            )
        )

    async def querySelector(
        self, selector: str
    ) -> typing.Union["ElementHandle", NoneType]:
        """
        - `selector` <str> A selector to query frame for. See [working with selectors](#working-with-selectors) for more details.
        - returns: <Optional[ElementHandle]> Promise which resolves to ElementHandle pointing to the frame element.

        The method finds an element matching the specified selector within the frame. See [Working with selectors](#working-with-selectors) for more details. If no elements match the selector, the return value resolves to `null`.
        """
        return mapping.from_impl_nullable(
            await self._impl_obj.querySelector(selector=selector)
        )

    async def querySelectorAll(self, selector: str) -> typing.List["ElementHandle"]:
        """
        - `selector` <str> A selector to query frame for. See [working with selectors](#working-with-selectors) for more details.
        - returns: <List[ElementHandle]> Promise which resolves to ElementHandles pointing to the frame elements.

        The method finds all elements matching the specified selector within the frame. See [Working with selectors](#working-with-selectors) for more details. If no elements match the selector, the return value resolves to `[]`.
        """
        return mapping.from_impl_list(
            await self._impl_obj.querySelectorAll(selector=selector)
        )

    async def waitForSelector(
        self,
        selector: str,
        timeout: int = None,
        state: Literal["attached", "detached", "visible", "hidden"] = None,
    ) -> typing.Union["ElementHandle", NoneType]:
        """
        - `selector` <str> A selector of an element to wait for. See [working with selectors](#working-with-selectors) for more details.
        - `state` <"attached"|"detached"|"visible"|"hidden"> Defaults to `'visible'`. Can be either:
          - `'attached'` - wait for element to be present in DOM.
          - `'detached'` - wait for element to not be present in DOM.
          - `'visible'` - wait for element to have non-empty bounding box and no `visibility:hidden`. Note that element without any content or with `display:none` has an empty bounding box and is not considered visible.
          - `'hidden'` - wait for element to be either detached from DOM, or have an empty bounding box or `visibility:hidden`. This is opposite to the `'visible'` option.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Optional[ElementHandle]> Promise which resolves when element specified by selector satisfies `state` option. Resolves to `null` if waiting for `hidden` or `detached`.

        Wait for the `selector` to satisfy `state` option (either appear/disappear from dom, or become visible/hidden). If at the moment of calling the method `selector` already satisfies the condition, the method will return immediately. If the selector doesn't satisfy the condition for the `timeout` milliseconds, the function will throw.

        This method works across navigations:
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
        """
        - `selector` <str> A selector to search for element to use. If there are multiple elements satisfying the selector, the first will be double clicked. See [working with selectors](#working-with-selectors) for more details.
        - `type` <str> DOM event type: `"click"`, `"dragstart"`, etc.
        - `eventInit` <Dict> event-specific initialization properties.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Promise>

        The snippet below dispatches the `click` event on the element. Regardless of the visibility state of the elment, `click` is dispatched. This is equivalend to calling [`element.click()`](https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/click).

        Under the hood, it creates an instance of an event based on the given `type`, initializes it with `eventInit` properties and dispatches it on the element. Events are `composed`, `cancelable` and bubble by default.

        Since `eventInit` is event-specific, please refer to the events documentation for the lists of initial properties:
        - [DragEvent](https://developer.mozilla.org/en-US/docs/Web/API/DragEvent/DragEvent)
        - [FocusEvent](https://developer.mozilla.org/en-US/docs/Web/API/FocusEvent/FocusEvent)
        - [KeyboardEvent](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/KeyboardEvent)
        - [MouseEvent](https://developer.mozilla.org/en-US/docs/Web/API/MouseEvent/MouseEvent)
        - [PointerEvent](https://developer.mozilla.org/en-US/docs/Web/API/PointerEvent/PointerEvent)
        - [TouchEvent](https://developer.mozilla.org/en-US/docs/Web/API/TouchEvent/TouchEvent)
        - [Event](https://developer.mozilla.org/en-US/docs/Web/API/Event/Event)

         You can also specify `JSHandle` as the property value if you want live objects to be passed into the event:
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.dispatchEvent(
                selector=selector, type=type, eventInit=eventInit, timeout=timeout
            )
        )

    async def evalOnSelector(
        self,
        selector: str,
        expression: str,
        arg: typing.Any = None,
        force_expr: bool = False,
    ) -> typing.Any:
        """
        - `selector` <str> A selector to query frame for. See [working with selectors](#working-with-selectors) for more details.
        - `expression` <[str]> Function to be evaluated in browser context
        - `force_expr` <[bool]> Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        - `arg` <[Serializable]|[JSHandle]> Optional argument to pass to `pageFunction`
        - returns: <Serializable> Promise which resolves to the return value of `pageFunction`

        The method finds an element matching the specified selector within the frame and passes it as a first argument to `pageFunction`. See [Working with selectors](#working-with-selectors) for more details. If no elements match the selector, the method throws an error.

        If `pageFunction` returns a [Promise], then `frame.$eval` would wait for the promise to resolve and return its value.

        Examples:
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
        force_expr: bool = False,
    ) -> typing.Any:
        """
        - `selector` <str> A selector to query frame for. See [working with selectors](#working-with-selectors) for more details.
        - `expression` <[str]>\\)> Function to be evaluated in browser context
        - `force_expr` <[bool]> Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        - `arg` <[Serializable]|[JSHandle]> Optional argument to pass to `pageFunction`
        - returns: <Serializable> Promise which resolves to the return value of `pageFunction`

        The method finds all elements matching the specified selector within the frame and passes an array of matched elements as a first argument to `pageFunction`. See [Working with selectors](#working-with-selectors) for more details.

        If `pageFunction` returns a [Promise], then `frame.$$eval` would wait for the promise to resolve and return its value.

        Examples:
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
        """
        - returns: <str>

        Gets the full HTML contents of the frame, including the doctype.
        """
        return mapping.from_maybe_impl(await self._impl_obj.content())

    async def setContent(
        self,
        html: str,
        timeout: int = None,
        waitUntil: Literal["load", "domcontentloaded", "networkidle"] = None,
    ) -> NoneType:
        """
        - `html` <str> HTML markup to assign to the page.
        - `timeout` <int> Maximum time in milliseconds for resources to load, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultNavigationTimeout(timeout)](#browsercontextsetdefaultnavigationtimeouttimeout), [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout), [page.setDefaultNavigationTimeout(timeout)](#pagesetdefaultnavigationtimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - `waitUntil` <"load"|"domcontentloaded"|"networkidle"> When to consider navigation succeeded, defaults to `load`. Events can be either:
          - `'domcontentloaded'` - consider setting content to be finished when the `DOMContentLoaded` event is fired.
          - `'load'` - consider setting content to be finished when the `load` event is fired.
          - `'networkidle'` - consider setting content to be finished when there are no network connections for at least `500` ms.
        - returns: <Promise>
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.setContent(
                html=html, timeout=timeout, waitUntil=waitUntil
            )
        )

    def isDetached(self) -> bool:
        """
        - returns: <bool>

        Returns `true` if the frame has been detached, or `false` otherwise.
        """
        return mapping.from_maybe_impl(self._impl_obj.isDetached())

    async def addScriptTag(
        self, url: str = None, path: str = None, content: str = None, type: str = None
    ) -> "ElementHandle":
        """
        - `url` <str> URL of a script to be added.
        - `path` <str> Path to the JavaScript file to be injected into frame. If `path` is a relative path, then it is resolved relative to [current working directory](https://nodejs.org/api/process.html#process_process_cwd).
        - `content` <str> Raw JavaScript content to be injected into frame.
        - `type` <str> Script type. Use 'module' in order to load a Javascript ES6 module. See [script](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/script) for more details.
        - returns: <ElementHandle> which resolves to the added tag when the script's onload fires or when the script content was injected into frame.

        Adds a `<script>` tag into the page with the desired url or content.
        """
        return mapping.from_impl(
            await self._impl_obj.addScriptTag(
                url=url, path=path, content=content, type=type
            )
        )

    async def addStyleTag(
        self, url: str = None, path: str = None, content: str = None
    ) -> "ElementHandle":
        """
        - `url` <str> URL of the `<link>` tag.
        - `path` <str> Path to the CSS file to be injected into frame. If `path` is a relative path, then it is resolved relative to [current working directory](https://nodejs.org/api/process.html#process_process_cwd).
        - `content` <str> Raw CSS content to be injected into frame.
        - returns: <ElementHandle> which resolves to the added tag when the stylesheet's onload fires or when the CSS content was injected into frame.

        Adds a `<link rel="stylesheet">` tag into the page with the desired url or a `<style type="text/css">` tag with the content.
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
        position: typing.Dict = None,
        delay: int = None,
        button: Literal["left", "right", "middle"] = None,
        clickCount: int = None,
        timeout: int = None,
        force: bool = None,
        noWaitAfter: bool = None,
    ) -> NoneType:
        """
        - `selector` <str> A selector to search for element to click. If there are multiple elements satisfying the selector, the first will be clicked. See [working with selectors](#working-with-selectors) for more details.
        - `button` <"left"|"right"|"middle"> Defaults to `left`.
        - `clickCount` <int> defaults to 1. See [UIEvent.detail].
        - `delay` <int> Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        - `position` <Dict> A point to click relative to the top-left corner of element padding box. If not specified, clicks to some visible point of the element.
          - x <int>
          - y <int>
        - `modifiers` <[List]<"Alt"|"Control"|"Meta"|"Shift">> Modifier keys to press. Ensures that only these modifiers are pressed during the click, and then restores current modifiers back. If not specified, currently pressed modifiers are used.
        - `force` <bool> Whether to bypass the [actionability](./actionability.md) checks. Defaults to `false`.
        - `noWaitAfter` <bool> Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Promise> Promise which resolves when the element matching `selector` is successfully clicked. The Promise will be rejected if there is no element matching `selector`.

        This method fetches an element with `selector`, scrolls it into view if needed, and then uses [page.mouse](#pagemouse) to click in the center of the element.
        If there's no element matching `selector`, the method waits until a matching element appears in the DOM. If the element is detached during the [actionability](./actionability.md) checks, the action is retried.
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
        position: typing.Dict = None,
        delay: int = None,
        button: Literal["left", "right", "middle"] = None,
        timeout: int = None,
        force: bool = None,
    ) -> NoneType:
        """
        - `selector` <str> A selector to search for element to double click. If there are multiple elements satisfying the selector, the first will be double clicked. See [working with selectors](#working-with-selectors) for more details.
        - `button` <"left"|"right"|"middle"> Defaults to `left`.
        - `delay` <int> Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        - `position` <Dict> A point to double click relative to the top-left corner of element padding box. If not specified, double clicks to some visible point of the element.
          - x <int>
          - y <int>
        - `modifiers` <[List]<"Alt"|"Control"|"Meta"|"Shift">> Modifier keys to press. Ensures that only these modifiers are pressed during the double click, and then restores current modifiers back. If not specified, currently pressed modifiers are used.
        - `force` <bool> Whether to bypass the [actionability](./actionability.md) checks. Defaults to `false`.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Promise> Promise which resolves when the element matching `selector` is successfully double clicked. The Promise will be rejected if there is no element matching `selector`.

        This method fetches an element with `selector`, scrolls it into view if needed, and then uses [page.mouse](#pagemouse) to double click in the center of the element.
        If there's no element matching `selector`, the method waits until a matching element appears in the DOM. If the element is detached during the actionability checks, the action is retried.

        Bear in mind that if the first click of the `dblclick()` triggers a navigation event, there will be an exception.

        > **NOTE** `frame.dblclick()` dispatches two `click` events and a single `dblclick` event.
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
            )
        )

    async def fill(
        self, selector: str, value: str, timeout: int = None, noWaitAfter: bool = None
    ) -> NoneType:
        """
        - `selector` <str> A selector to query page for. See [working with selectors](#working-with-selectors) for more details.
        - `value` <str> Value to fill for the `<input>`, `<textarea>` or `[contenteditable]` element.
        - `noWaitAfter` <bool> Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Promise>

        This method waits for an element matching `selector`, waits for [actionability](./actionability.md) checks, focuses the element, fills it and triggers an `input` event after filling.
        If the element matching `selector` is not an `<input>`, `<textarea>` or `[contenteditable]` element, this method throws an error.
        Note that you can pass an empty str to clear the input field.

        To send fine-grained keyboard events, use [`frame.type`](#frametypeselector-text-options).
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.fill(
                selector=selector, value=value, timeout=timeout, noWaitAfter=noWaitAfter
            )
        )

    async def focus(self, selector: str, timeout: int = None) -> NoneType:
        """
        - `selector` <str> A selector of an element to focus. If there are multiple elements satisfying the selector, the first will be focused. See [working with selectors](#working-with-selectors) for more details.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Promise> Promise which resolves when the element matching `selector` is successfully focused. The promise will be rejected if there is no element matching `selector`.

        This method fetches an element with `selector` and focuses it.
        If there's no element matching `selector`, the method waits until a matching element appears in the DOM.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.focus(selector=selector, timeout=timeout)
        )

    async def textContent(self, selector: str, timeout: int = None) -> str:
        """
        - `selector` <str> A selector to search for an element. If there are multiple elements satisfying the selector, the first will be picked. See [working with selectors](#working-with-selectors) for more details.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <null|[str]>

        Resolves to the `element.textContent`.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.textContent(selector=selector, timeout=timeout)
        )

    async def innerText(self, selector: str, timeout: int = None) -> str:
        """
        - `selector` <str> A selector to search for an element. If there are multiple elements satisfying the selector, the first will be picked. See [working with selectors](#working-with-selectors) for more details.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <str>

        Resolves to the `element.innerText`.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.innerText(selector=selector, timeout=timeout)
        )

    async def innerHTML(self, selector: str, timeout: int = None) -> str:
        """
        - `selector` <str> A selector to search for an element. If there are multiple elements satisfying the selector, the first will be picked. See [working with selectors](#working-with-selectors) for more details.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <str>

        Resolves to the `element.innerHTML`.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.innerHTML(selector=selector, timeout=timeout)
        )

    async def getAttribute(self, selector: str, name: str, timeout: int = None) -> str:
        """
        - `selector` <str> A selector to search for an element. If there are multiple elements satisfying the selector, the first will be picked. See [working with selectors](#working-with-selectors) for more details.
        - `name` <str> Attribute name to get the value for.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <null|[str]>

        Returns element attribute value.
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
        position: typing.Dict = None,
        timeout: int = None,
        force: bool = None,
    ) -> NoneType:
        """
        - `selector` <str> A selector to search for element to hover. If there are multiple elements satisfying the selector, the first will be hovered. See [working with selectors](#working-with-selectors) for more details.
        - `position` <Dict> A point to hover relative to the top-left corner of element padding box. If not specified, hovers over some visible point of the element.
          - x <int>
          - y <int>
        - `modifiers` <[List]<"Alt"|"Control"|"Meta"|"Shift">> Modifier keys to press. Ensures that only these modifiers are pressed during the hover, and then restores current modifiers back. If not specified, currently pressed modifiers are used.
        - `force` <bool> Whether to bypass the [actionability](./actionability.md) checks. Defaults to `false`.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Promise> Promise which resolves when the element matching `selector` is successfully hovered. Promise gets rejected if there's no element matching `selector`.

        This method fetches an element with `selector`, scrolls it into view if needed, and then uses [page.mouse](#pagemouse) to hover over the center of the element.
        If there's no element matching `selector`, the method waits until a matching element appears in the DOM. If the element is detached during the [actionability](./actionability.md) checks, the action is retried.
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
        ],
        timeout: int = None,
        noWaitAfter: bool = None,
    ) -> typing.List[str]:
        """
        - `selector` <str> A selector to query frame for. See [working with selectors](#working-with-selectors) for more details.
        - `values` <null|[str]|[ElementHandle]|[List]<str>|[Dict]|[List]<ElementHandle>|[List]<Dict>> Options to select. If the `<select>` has the `multiple` attribute, all matching options are selected, otherwise only the first option matching one of the passed options is selected. String values are equivalent to `{value:'str'}`. Option is considered matching if all specified properties match.
          - `value` <str> Matches by `option.value`.
          - `label` <str> Matches by `option.label`.
          - `index` <int> Matches by the index.
        - `noWaitAfter` <bool> Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <List[str]> An array of option values that have been successfully selected.

        Triggers a `change` and `input` event once all the provided options have been selected.
        If there's no `<select>` element matching `selector`, the method throws an error.
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
        """
        - `selector` <str> A selector to search for element to click. If there are multiple elements satisfying the selector, the first will be clicked. See [working with selectors](#working-with-selectors) for more details.
        - `files` <[str]|[List]<str>|[Dict]|[List]<Dict>>
          - `name` <str> [File] name **required**
          - `mimeType` <str> [File] type **required**
          - `buffer` <bytes> File content **required**
        - `noWaitAfter` <bool> Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Promise>

        This method expects `selector` to point to an [input element](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/input).

        Sets the value of the file input to these file paths or files. If some of the `filePaths` are relative paths, then they are resolved relative to the [current working directory](https://nodejs.org/api/process.html#process_process_cwd). For empty array, clears the selected files.
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
        """
        - `selector` <str> A selector of an element to type into. If there are multiple elements satisfying the selector, the first will be used. See [working with selectors](#working-with-selectors) for more details.
        - `text` <str> A text to type into a focused element.
        - `delay` <int> Time to wait between key presses in milliseconds. Defaults to 0.
        - `noWaitAfter` <bool> Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Promise>

        Sends a `keydown`, `keypress`/`input`, and `keyup` event for each character in the text. `frame.type` can be used to send fine-grained keyboard events. To fill values in form fields, use [`frame.fill`](#framefillselector-value-options).

        To press a special key, like `Control` or `ArrowDown`, use [`keyboard.press`](#keyboardpresskey-options).
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
        """
        - `selector` <str> A selector of an element to type into. If there are multiple elements satisfying the selector, the first will be used. See [working with selectors](#working-with-selectors) for more details.
        - `key` <str> Name of the key to press or a character to generate, such as `ArrowLeft` or `a`.
        - `delay` <int> Time to wait between `keydown` and `keyup` in milliseconds. Defaults to 0.
        - `noWaitAfter` <bool> Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Promise>

        `key` can specify the intended [keyboardEvent.key](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/key) value or a single character to generate the text for. A superset of the `key` values can be found [here](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/key/Key_Values). Examples of the keys are:

          `F1` - `F12`, `Digit0`- `Digit9`, `KeyA`- `KeyZ`, `Backquote`, `Minus`, `Equal`, `Backslash`, `Backspace`, `Tab`, `Delete`, `Escape`, `ArrowDown`, `End`, `Enter`, `Home`, `Insert`, `PageDown`, `PageUp`, `ArrowRight`, `ArrowUp`, etc.

        Following modification shortcuts are also suported: `Shift`, `Control`, `Alt`, `Meta`, `ShiftLeft`.

        Holding down `Shift` will type the text that corresponds to the `key` in the upper case.

        If `key` is a single character, it is case-sensitive, so the values `a` and `A` will generate different respective texts.

        Shortcuts such as `key: "Control+o"` or `key: "Control+Shift+T"` are supported as well. When speficied with the modifier, modifier is pressed and being held while the subsequent key is being pressed.
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
        """
        - `selector` <str> A selector to search for checkbox to check. If there are multiple elements satisfying the selector, the first will be checked. See [working with selectors](#working-with-selectors) for more details.
        - `force` <bool> Whether to bypass the [actionability](./actionability.md) checks. Defaults to `false`.
        - `noWaitAfter` <bool> Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Promise> Promise which resolves when the element matching `selector` is successfully checked. The Promise will be rejected if there is no element matching `selector`.

        This method fetches an element with `selector`, if element is not already checked, it scrolls it into view if needed, and then uses [frame.click](#frameclickselector-options) to click in the center of the element.
        If there's no element matching `selector`, the method waits until a matching element appears in the DOM. If the element is detached during the [actionability](./actionability.md) checks, the action is retried.
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
        """
        - `selector` <str> A selector to search for uncheckbox to check. If there are multiple elements satisfying the selector, the first will be checked. See [working with selectors](#working-with-selectors) for more details.
        - `force` <bool> Whether to bypass the [actionability](./actionability.md) checks. Defaults to `false`.
        - `noWaitAfter` <bool> Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Promise> Promise which resolves when the element matching `selector` is successfully unchecked. The Promise will be rejected if there is no element matching `selector`.

        This method fetches an element with `selector`, if element is not already unchecked, it scrolls it into view if needed, and then uses [frame.click](#frameclickselector-options) to click in the center of the element.
        If there's no element matching `selector`, the method waits until a matching element appears in the DOM. If the element is detached during the [actionability](./actionability.md) checks, the action is retried.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.uncheck(
                selector=selector, timeout=timeout, force=force, noWaitAfter=noWaitAfter
            )
        )

    async def waitForTimeout(self, timeout: int) -> typing.Awaitable[NoneType]:
        """
        - `timeout` <int> A timeout to wait for
        - returns: <Promise>

        Returns a promise that resolves after the timeout.

        Note that `frame.waitForTimeout()` should only be used for debugging. Tests using the timer in production are going to be flaky. Use signals such as network events, selectors becoming visible and others instead.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.waitForTimeout(timeout=timeout)
        )

    async def waitForFunction(
        self,
        expression: str,
        arg: typing.Any = None,
        force_expr: bool = False,
        timeout: int = None,
        polling: typing.Union[int, Literal["raf"]] = None,
    ) -> "JSHandle":
        """
        - `expression` <[str]> Function to be evaluated in browser context
        - `force_expr` <[bool]> Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        - `arg` <[Serializable]|[JSHandle]> Optional argument to pass to `pageFunction`
        - `polling` <[int]|"raf"> If `polling` is `'raf'`, then `pageFunction` is constantly executed in `requestAnimationFrame` callback. If `polling` is a int, then it is treated as an interval in milliseconds at which the function would be executed. Defaults to `raf`.
        - `timeout` <int> maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <JSHandle> Promise which resolves when the `pageFunction` returns a truthy value. It resolves to a JSHandle of the truthy value.

        The `waitForFunction` can be used to observe viewport size change:

        To pass an argument from Node.js to the predicate of `frame.waitForFunction` function:
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
        """
        - returns: <str> The page's title.
        """
        return mapping.from_maybe_impl(await self._impl_obj.title())


mapping.register(FrameImpl, Frame)


class Worker(AsyncBase):
    def __init__(self, obj: WorkerImpl):
        super().__init__(obj)

    @property
    def url(self) -> str:
        """
        - returns: <str>
        """
        return mapping.from_maybe_impl(self._impl_obj.url)

    async def evaluate(
        self, expression: str, arg: typing.Any = None, force_expr: bool = False
    ) -> typing.Any:
        """
        - `expression` <[str]> Function to be evaluated in the worker context
        - `force_expr` <[bool]> Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        - `arg` <[Serializable]|[JSHandle]> Optional argument to pass to `pageFunction`
        - returns: <Serializable> Promise which resolves to the return value of `pageFunction`

        If the function passed to the `worker.evaluate` returns a [Promise], then `worker.evaluate` would wait for the promise to resolve and return its value.

        If the function passed to the `worker.evaluate` returns a non-[Serializable] value, then `worker.evaluate` resolves to `undefined`. DevTools Protocol also supports transferring some additional values that are not serializable by `JSON`: `-0`, `NaN`, `Infinity`, `-Infinity`, and bigint literals.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.evaluate(
                expression=expression, arg=mapping.to_impl(arg), force_expr=force_expr
            )
        )

    async def evaluateHandle(
        self, expression: str, arg: typing.Any = None, force_expr: bool = False
    ) -> "JSHandle":
        """
        - `expression` <[str]> Function to be evaluated in the page context
        - `force_expr` <[bool]> Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        - `arg` <[Serializable]|[JSHandle]> Optional argument to pass to `pageFunction`
        - returns: <JSHandle> Promise which resolves to the return value of `pageFunction` as in-page object (JSHandle)

        The only difference between `worker.evaluate` and `worker.evaluateHandle` is that `worker.evaluateHandle` returns in-page object (JSHandle).

        If the function passed to the `worker.evaluateHandle` returns a [Promise], then `worker.evaluateHandle` would wait for the promise to resolve and return its value.
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
        self, name: str, source: str = "", path: str = None, contentScript: bool = False
    ) -> NoneType:
        """
        - `name` <str> Name that is used in selectors as a prefix, e.g. `{name: 'foo'}` enables `foo=myselectorbody` selectors. May only contain `[a-zA-Z0-9_]` characters.
        - `source` <[function]|[str]|[Dict]> Script that evaluates to a selector engine instance.
          - `path` <str> Path to the JavaScript file. If `path` is a relative path, then it is resolved relative to [current working directory](https://nodejs.org/api/process.html#process_process_cwd).
          - `content` <str> Raw script content.
        - `contentScript` <bool> Whether to run this selector engine in isolated JavaScript environment. This environment has access to the same DOM, but not any JavaScript objects from the frame's scripts. Defaults to `false`. Note that running as a content script is not guaranteed when this engine is used together with other registered engines.
        - returns: <Promise>

        An example of registering selector engine that queries elements based on a tag name:
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
        """
        - returns: <str>

        One of the following values: `'log'`, `'debug'`, `'info'`, `'error'`, `'warning'`, `'dir'`, `'dirxml'`, `'table'`, `'trace'`, `'clear'`, `'startGroup'`, `'startGroupCollapsed'`, `'endGroup'`, `'assert'`, `'profile'`, `'profileEnd'`, `'count'`, `'timeEnd'`.
        """
        return mapping.from_maybe_impl(self._impl_obj.type)

    @property
    def text(self) -> str:
        """
        - returns: <str>
        """
        return mapping.from_maybe_impl(self._impl_obj.text)

    @property
    def args(self) -> typing.List["JSHandle"]:
        """
        - returns: <List[JSHandle]>
        """
        return mapping.from_impl_list(self._impl_obj.args)

    @property
    def location(self) -> ConsoleMessageLocation:
        """
        - returns: <Dict>
          - `url` <str> URL of the resource if available.
          - `lineNumber` <int> 0-based line int in the resource if available.
          - `columnNumber` <int> 0-based column int in the resource if available.
        """
        return mapping.from_maybe_impl(self._impl_obj.location)


mapping.register(ConsoleMessageImpl, ConsoleMessage)


class Dialog(AsyncBase):
    def __init__(self, obj: DialogImpl):
        super().__init__(obj)

    @property
    def type(self) -> str:
        """
        - returns: <str> Dialog's type, can be one of `alert`, `beforeunload`, `confirm` or `prompt`.
        """
        return mapping.from_maybe_impl(self._impl_obj.type)

    @property
    def message(self) -> str:
        """
        - returns: <str> A message displayed in the dialog.
        """
        return mapping.from_maybe_impl(self._impl_obj.message)

    @property
    def defaultValue(self) -> str:
        """
        - returns: <str> If dialog is prompt, returns default prompt value. Otherwise, returns empty str.
        """
        return mapping.from_maybe_impl(self._impl_obj.defaultValue)

    async def accept(self, promptText: str = None) -> NoneType:
        """
        - `promptText` <str> A text to enter in prompt. Does not cause any effects if the dialog's `type` is not prompt.
        - returns: <Promise> Promise which resolves when the dialog has been accepted.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.accept(promptText=promptText)
        )

    async def dismiss(self) -> NoneType:
        """
        - returns: <Promise> Promise which resolves when the dialog has been dismissed.
        """
        return mapping.from_maybe_impl(await self._impl_obj.dismiss())


mapping.register(DialogImpl, Dialog)


class Download(AsyncBase):
    def __init__(self, obj: DownloadImpl):
        super().__init__(obj)

    @property
    def url(self) -> str:
        """
        - returns: <str>

        Returns downloaded url.
        """
        return mapping.from_maybe_impl(self._impl_obj.url)

    @property
    def suggestedFilename(self) -> str:
        """
        - returns: <str>

        Returns suggested filename for this download. It is typically computed by the browser from the [`Content-Disposition`](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Disposition) response header or the `download` attribute. See the spec on [whatwg](https://html.spec.whatwg.org/#downloading-resources). Different browsers can use different logic for computing it.
        """
        return mapping.from_maybe_impl(self._impl_obj.suggestedFilename)

    async def delete(self) -> NoneType:
        """
        - returns: <Promise>

        Deletes the downloaded file.
        """
        return mapping.from_maybe_impl(await self._impl_obj.delete())

    async def failure(self) -> typing.Union[str, NoneType]:
        """
        - returns: <null|[str]>

        Returns download error if any.
        """
        return mapping.from_maybe_impl(await self._impl_obj.failure())

    async def path(self) -> typing.Union[str, NoneType]:
        """
        - returns: <null|[str]>

        Returns path to the downloaded file in case of successful download.
        """
        return mapping.from_maybe_impl(await self._impl_obj.path())


mapping.register(DownloadImpl, Download)


class BindingCall(AsyncBase):
    def __init__(self, obj: BindingCallImpl):
        super().__init__(obj)

    async def call(self, func: typing.Callable[[typing.Dict], typing.Any]) -> NoneType:
        return mapping.from_maybe_impl(
            await self._impl_obj.call(func=self._wrap_handler(func))
        )


mapping.register(BindingCallImpl, BindingCall)


class Page(AsyncBase):
    def __init__(self, obj: PageImpl):
        super().__init__(obj)

    @property
    def accessibility(self) -> "Accessibility":
        """
        - returns: <Accessibility>
        """
        return mapping.from_impl(self._impl_obj.accessibility)

    @property
    def keyboard(self) -> "Keyboard":
        """
        - returns: <Keyboard>
        """
        return mapping.from_impl(self._impl_obj.keyboard)

    @property
    def mouse(self) -> "Mouse":
        """
        - returns: <Mouse>
        """
        return mapping.from_impl(self._impl_obj.mouse)

    @property
    def context(self) -> "BrowserContext":
        """
        - returns: <BrowserContext>

        Get the browser context that the page belongs to.
        """
        return mapping.from_impl(self._impl_obj.context)

    @property
    def mainFrame(self) -> "Frame":
        """
        - returns: <Frame> The page's main frame.

        Page is guaranteed to have a main frame which persists during navigations.
        """
        return mapping.from_impl(self._impl_obj.mainFrame)

    @property
    def frames(self) -> typing.List["Frame"]:
        """
        - returns: <List[Frame]> An array of all frames attached to the page.
        """
        return mapping.from_impl_list(self._impl_obj.frames)

    @property
    def url(self) -> str:
        """
        - returns: <str>

        This is a shortcut for [page.mainFrame().url()](#frameurl)
        """
        return mapping.from_maybe_impl(self._impl_obj.url)

    @property
    def workers(self) -> typing.List["Worker"]:
        """
        - returns: <List[Worker]>
        This method returns all of the dedicated [WebWorkers](https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API) associated with the page.

        > **NOTE** This does not contain ServiceWorkers
        """
        return mapping.from_impl_list(self._impl_obj.workers)

    async def opener(self) -> typing.Union["Page", NoneType]:
        """
        - returns: <Optional[Page]> Promise which resolves to the opener for popup pages and `null` for others. If the opener has been closed already the promise may resolve to `null`.
        """
        return mapping.from_impl_nullable(await self._impl_obj.opener())

    def frame(
        self,
        name: str = None,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]] = None,
    ) -> typing.Union["Frame", NoneType]:
        """
        - `name` <str> frame name specified in the `iframe`'s `name` attribute
        - `url` <[str]|[RegExp]|[Function]> A glob pattern, regex pattern or predicate receiving frame's `url` as a [URL] object.
        - returns: <Optional[Frame]> frame matching the criteria. Returns `null` if no frame matches.

        Returns frame matching the specified criteria. Either `name` or `url` must be specified.
        """
        return mapping.from_impl_nullable(
            self._impl_obj.frame(name=name, url=self._wrap_handler(url))
        )

    def setDefaultNavigationTimeout(self, timeout: int) -> NoneType:
        """
        - `timeout` <int> Maximum navigation time in milliseconds

        This setting will change the default maximum navigation time for the following methods and related shortcuts:
        - [page.goBack([options])](#pagegobackoptions)
        - [page.goForward([options])](#pagegoforwardoptions)
        - [page.goto(url[, options])](#pagegotourl-options)
        - [page.reload([options])](#pagereloadoptions)
        - [page.setContent(html[, options])](#pagesetcontenthtml-options)
        - [page.waitForNavigation([options])](#pagewaitfornavigationoptions)

        > **NOTE** [`page.setDefaultNavigationTimeout`](#pagesetdefaultnavigationtimeouttimeout) takes priority over [`page.setDefaultTimeout`](#pagesetdefaulttimeouttimeout), [`browserContext.setDefaultTimeout`](#browsercontextsetdefaulttimeouttimeout) and [`browserContext.setDefaultNavigationTimeout`](#browsercontextsetdefaultnavigationtimeouttimeout).
        """
        return mapping.from_maybe_impl(
            self._impl_obj.setDefaultNavigationTimeout(timeout=timeout)
        )

    def setDefaultTimeout(self, timeout: int) -> NoneType:
        """
        - `timeout` <int> Maximum time in milliseconds

        This setting will change the default maximum time for all the methods accepting `timeout` option.

        > **NOTE** [`page.setDefaultNavigationTimeout`](#pagesetdefaultnavigationtimeouttimeout) takes priority over [`page.setDefaultTimeout`](#pagesetdefaulttimeouttimeout).
        """
        return mapping.from_maybe_impl(
            self._impl_obj.setDefaultTimeout(timeout=timeout)
        )

    async def querySelector(
        self, selector: str
    ) -> typing.Union["ElementHandle", NoneType]:
        """
        - `selector` <str> A selector to query page for. See [working with selectors](#working-with-selectors) for more details.
        - returns: <Optional[ElementHandle]>

        The method finds an element matching the specified selector within the page. If no elements match the selector, the return value resolves to `null`.
        """
        return mapping.from_impl_nullable(
            await self._impl_obj.querySelector(selector=selector)
        )

    async def querySelectorAll(self, selector: str) -> typing.List["ElementHandle"]:
        """
        - `selector` <str> A selector to query page for. See [working with selectors](#working-with-selectors) for more details.
        - returns: <List[ElementHandle]>

        The method finds all elements matching the specified selector within the page. If no elements match the selector, the return value resolves to `[]`.
        """
        return mapping.from_impl_list(
            await self._impl_obj.querySelectorAll(selector=selector)
        )

    async def waitForSelector(
        self,
        selector: str,
        timeout: int = None,
        state: Literal["attached", "detached", "visible", "hidden"] = None,
    ) -> typing.Union["ElementHandle", NoneType]:
        """
        - `selector` <str> A selector of an element to wait for. See [working with selectors](#working-with-selectors) for more details.
        - `state` <"attached"|"detached"|"visible"|"hidden"> Defaults to `'visible'`. Can be either:
          - `'attached'` - wait for element to be present in DOM.
          - `'detached'` - wait for element to not be present in DOM.
          - `'visible'` - wait for element to have non-empty bounding box and no `visibility:hidden`. Note that element without any content or with `display:none` has an empty bounding box and is not considered visible.
          - `'hidden'` - wait for element to be either detached from DOM, or have an empty bounding box or `visibility:hidden`. This is opposite to the `'visible'` option.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Optional[ElementHandle]> Promise which resolves when element specified by selector satisfies `state` option. Resolves to `null` if waiting for `hidden` or `detached`.

        Wait for the `selector` to satisfy `state` option (either appear/disappear from dom, or become visible/hidden). If at the moment of calling the method `selector` already satisfies the condition, the method will return immediately. If the selector doesn't satisfy the condition for the `timeout` milliseconds, the function will throw.

        This method works across navigations:
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
        """
        - `selector` <str> A selector to search for element to use. If there are multiple elements satisfying the selector, the first will be used. See [working with selectors](#working-with-selectors) for more details.
        - `type` <str> DOM event type: `"click"`, `"dragstart"`, etc.
        - `eventInit` <Dict> event-specific initialization properties.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Promise>

        The snippet below dispatches the `click` event on the element. Regardless of the visibility state of the elment, `click` is dispatched. This is equivalend to calling [`element.click()`](https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/click).

        Under the hood, it creates an instance of an event based on the given `type`, initializes it with `eventInit` properties and dispatches it on the element. Events are `composed`, `cancelable` and bubble by default.

        Since `eventInit` is event-specific, please refer to the events documentation for the lists of initial properties:
        - [DragEvent](https://developer.mozilla.org/en-US/docs/Web/API/DragEvent/DragEvent)
        - [FocusEvent](https://developer.mozilla.org/en-US/docs/Web/API/FocusEvent/FocusEvent)
        - [KeyboardEvent](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/KeyboardEvent)
        - [MouseEvent](https://developer.mozilla.org/en-US/docs/Web/API/MouseEvent/MouseEvent)
        - [PointerEvent](https://developer.mozilla.org/en-US/docs/Web/API/PointerEvent/PointerEvent)
        - [TouchEvent](https://developer.mozilla.org/en-US/docs/Web/API/TouchEvent/TouchEvent)
        - [Event](https://developer.mozilla.org/en-US/docs/Web/API/Event/Event)

         You can also specify `JSHandle` as the property value if you want live objects to be passed into the event:
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.dispatchEvent(
                selector=selector, type=type, eventInit=eventInit, timeout=timeout
            )
        )

    async def evaluate(
        self, expression: str, arg: typing.Any = None, force_expr: bool = False
    ) -> typing.Any:
        """
        - `expression` <[str]> Function to be evaluated in the page context
        - `force_expr` <[bool]> Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        - `arg` <[Serializable]|[JSHandle]> Optional argument to pass to `pageFunction`
        - returns: <Serializable> Promise which resolves to the return value of `pageFunction`

        If the function passed to the `page.evaluate` returns a [Promise], then `page.evaluate` would wait for the promise to resolve and return its value.

        If the function passed to the `page.evaluate` returns a non-[Serializable] value, then `page.evaluate` resolves to `undefined`. DevTools Protocol also supports transferring some additional values that are not serializable by `JSON`: `-0`, `NaN`, `Infinity`, `-Infinity`, and bigint literals.

        Passing argument to `pageFunction`:

        A str can also be passed in instead of a function:

        [ElementHandle] instances can be passed as an argument to the `page.evaluate`:
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.evaluate(
                expression=expression, arg=mapping.to_impl(arg), force_expr=force_expr
            )
        )

    async def evaluateHandle(
        self, expression: str, arg: typing.Any = None, force_expr: bool = False
    ) -> "JSHandle":
        """
        - `expression` <[str]> Function to be evaluated in the page context
        - `force_expr` <[bool]> Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        - `arg` <[Serializable]|[JSHandle]> Optional argument to pass to `pageFunction`
        - returns: <JSHandle> Promise which resolves to the return value of `pageFunction` as in-page object (JSHandle)

        The only difference between `page.evaluate` and `page.evaluateHandle` is that `page.evaluateHandle` returns in-page object (JSHandle).

        If the function passed to the `page.evaluateHandle` returns a [Promise], then `page.evaluateHandle` would wait for the promise to resolve and return its value.

        A str can also be passed in instead of a function:

        [JSHandle] instances can be passed as an argument to the `page.evaluateHandle`:
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
        force_expr: bool = False,
    ) -> typing.Any:
        """
        - `selector` <str> A selector to query page for. See [working with selectors](#working-with-selectors) for more details.
        - `expression` <[str]> Function to be evaluated in browser context
        - `force_expr` <[bool]> Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        - `arg` <[Serializable]|[JSHandle]> Optional argument to pass to `pageFunction`
        - returns: <Serializable> Promise which resolves to the return value of `pageFunction`

        The method finds an element matching the specified selector within the page and passes it as a first argument to `pageFunction`. If no elements match the selector, the method throws an error.

        If `pageFunction` returns a [Promise], then `page.$eval` would wait for the promise to resolve and return its value.

        Examples:
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
        force_expr: bool = False,
    ) -> typing.Any:
        """
        - `selector` <str> A selector to query page for. See [working with selectors](#working-with-selectors) for more details.
        - `expression` <[str]>\\)> Function to be evaluated in browser context
        - `force_expr` <[bool]> Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        - `arg` <[Serializable]|[JSHandle]> Optional argument to pass to `pageFunction`
        - returns: <Serializable> Promise which resolves to the return value of `pageFunction`

        The method finds all elements matching the specified selector within the page and passes an array of matched elements as a first argument to `pageFunction`.

        If `pageFunction` returns a [Promise], then `page.$$eval` would wait for the promise to resolve and return its value.

        Examples:
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
        self, url: str = None, path: str = None, content: str = None, type: str = None
    ) -> "ElementHandle":
        """
        - `url` <str> URL of a script to be added.
        - `path` <str> Path to the JavaScript file to be injected into frame. If `path` is a relative path, then it is resolved relative to [current working directory](https://nodejs.org/api/process.html#process_process_cwd).
        - `content` <str> Raw JavaScript content to be injected into frame.
        - `type` <str> Script type. Use 'module' in order to load a Javascript ES6 module. See [script](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/script) for more details.
        - returns: <ElementHandle> which resolves to the added tag when the script's onload fires or when the script content was injected into frame.

        Adds a `<script>` tag into the page with the desired url or content.
        """
        return mapping.from_impl(
            await self._impl_obj.addScriptTag(
                url=url, path=path, content=content, type=type
            )
        )

    async def addStyleTag(
        self, url: str = None, path: str = None, content: str = None
    ) -> "ElementHandle":
        """
        - `url` <str> URL of the `<link>` tag.
        - `path` <str> Path to the CSS file to be injected into frame. If `path` is a relative path, then it is resolved relative to [current working directory](https://nodejs.org/api/process.html#process_process_cwd).
        - `content` <str> Raw CSS content to be injected into frame.
        - returns: <ElementHandle> which resolves to the added tag when the stylesheet's onload fires or when the CSS content was injected into frame.

        Adds a `<link rel="stylesheet">` tag into the page with the desired url or a `<style type="text/css">` tag with the content.
        """
        return mapping.from_impl(
            await self._impl_obj.addStyleTag(url=url, path=path, content=content)
        )

    async def exposeFunction(
        self, name: str, binding: typing.Callable[..., typing.Any]
    ) -> NoneType:
        """
        - `name` <str> Name of the function on the window object
        - `binding` <function> Callback function which will be called in Playwright's context.
        - returns: <Promise>

        The method adds a function called `name` on the `window` object of every frame in the page.
        When called, the function executes `playwrightFunction` in Node.js and returns a [Promise] which resolves to the return value of `playwrightFunction`.

        If the `playwrightFunction` returns a [Promise], it will be awaited.

        See [browserContext.exposeFunction(name, playwrightFunction)](#browsercontextexposefunctionname-playwrightfunction) for context-wide exposed function.

        > **NOTE** Functions installed via `page.exposeFunction` survive navigations.

        An example of adding an `md5` function to the page:

        An example of adding a `window.readfile` function to the page:
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.exposeFunction(
                name=name, binding=self._wrap_handler(binding)
            )
        )

    async def exposeBinding(
        self, name: str, binding: typing.Callable[[typing.Dict], typing.Any]
    ) -> NoneType:
        """
        - `name` <str> Name of the function on the window object.
        - `binding` <function> Callback function that will be called in the Playwright's context.
        - returns: <Promise>

        The method adds a function called `name` on the `window` object of every frame in this page.
        When called, the function executes `playwrightBinding` in Node.js and returns a [Promise] which resolves to the return value of `playwrightBinding`.
        If the `playwrightBinding` returns a [Promise], it will be awaited.

        The first argument of the `playwrightBinding` function contains information about the caller:
        `{ browserContext: BrowserContext, page: Page, frame: Frame }`.

        See [browserContext.exposeBinding(name, playwrightBinding)](#browsercontextexposebindingname-playwrightbinding) for the context-wide version.

        > **NOTE** Functions installed via `page.exposeBinding` survive navigations.

        An example of exposing page URL to all frames in a page:
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.exposeBinding(
                name=name, binding=self._wrap_handler(binding)
            )
        )

    async def setExtraHTTPHeaders(self, headers: typing.Dict) -> NoneType:
        """
        - `headers` <[Dict]<[str], [str]>> An object containing additional HTTP headers to be sent with every request. All header values must be strs.
        - returns: <Promise>

        The extra HTTP headers will be sent with every request the page initiates.

        > **NOTE** page.setExtraHTTPHeaders does not guarantee the order of headers in the outgoing requests.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.setExtraHTTPHeaders(headers=headers)
        )

    async def content(self) -> str:
        """
        - returns: <str>

        Gets the full HTML contents of the page, including the doctype.
        """
        return mapping.from_maybe_impl(await self._impl_obj.content())

    async def setContent(
        self,
        html: str,
        timeout: int = None,
        waitUntil: Literal["load", "domcontentloaded", "networkidle"] = None,
    ) -> NoneType:
        """
        - `html` <str> HTML markup to assign to the page.
        - `timeout` <int> Maximum time in milliseconds for resources to load, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultNavigationTimeout(timeout)](#browsercontextsetdefaultnavigationtimeouttimeout), [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout), [page.setDefaultNavigationTimeout(timeout)](#pagesetdefaultnavigationtimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - `waitUntil` <"load"|"domcontentloaded"|"networkidle"> When to consider setting markup succeeded, defaults to `load`. Given an array of event strs, setting content is considered to be successful after all events have been fired. Events can be either:
          - `'load'` - consider setting content to be finished when the `load` event is fired.
          - `'domcontentloaded'` - consider setting content to be finished when the `DOMContentLoaded` event is fired.
          - `'networkidle'` - consider setting content to be finished when there are no network connections for at least `500` ms.
        - returns: <Promise>
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
        waitUntil: Literal["load", "domcontentloaded", "networkidle"] = "load",
        referer: str = None,
    ) -> typing.Union["Response", NoneType]:
        """
        - `url` <str> URL to navigate page to. The url should include scheme, e.g. `https://`.
        - `timeout` <int> Maximum navigation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultNavigationTimeout(timeout)](#browsercontextsetdefaultnavigationtimeouttimeout), [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout), [page.setDefaultNavigationTimeout(timeout)](#pagesetdefaultnavigationtimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - `waitUntil` <"load"|"domcontentloaded"|"networkidle"> When to consider navigation succeeded, defaults to `load`. Events can be either:
          - `'domcontentloaded'` - consider navigation to be finished when the `DOMContentLoaded` event is fired.
          - `'load'` - consider navigation to be finished when the `load` event is fired.
          - `'networkidle'` - consider navigation to be finished when there are no network connections for at least `500` ms.
        - `referer` <str> Referer header value. If provided it will take preference over the referer header value set by [page.setExtraHTTPHeaders()](#pagesetextrahttpheadersheaders).
        - returns: <Optional[Response]> Promise which resolves to the main resource response. In case of multiple redirects, the navigation will resolve with the response of the last redirect.

        `page.goto` will throw an error if:
        - there's an SSL error (e.g. in case of self-signed certificates).
        - target URL is invalid.
        - the `timeout` is exceeded during navigation.
        - the remote server does not respond or is unreachable.
        - the main resource failed to load.

        `page.goto` will not throw an error when any valid HTTP status code is returned by the remote server, including 404 "Not Found" and 500 "Internal Server Error".  The status code for such responses can be retrieved by calling [response.status()](#responsestatus).

        > **NOTE** `page.goto` either throws an error or returns a main resource response. The only exceptions are navigation to `about:blank` or navigation to the same URL with a different hash, which would succeed and return `null`.

        > **NOTE** Headless mode doesn't support navigation to a PDF document. See the [upstream issue](https://bugs.chromium.org/p/chromium/issues/detail?id=761295).
        """
        return mapping.from_impl_nullable(
            await self._impl_obj.goto(
                url=url, timeout=timeout, waitUntil=waitUntil, referer=referer
            )
        )

    async def reload(
        self,
        timeout: int = None,
        waitUntil: Literal["load", "domcontentloaded", "networkidle"] = "load",
    ) -> typing.Union["Response", NoneType]:
        """
        - `timeout` <int> Maximum navigation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultNavigationTimeout(timeout)](#browsercontextsetdefaultnavigationtimeouttimeout), [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout), [page.setDefaultNavigationTimeout(timeout)](#pagesetdefaultnavigationtimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - `waitUntil` <"load"|"domcontentloaded"|"networkidle"> When to consider navigation succeeded, defaults to `load`. Events can be either:
          - `'domcontentloaded'` - consider navigation to be finished when the `DOMContentLoaded` event is fired.
          - `'load'` - consider navigation to be finished when the `load` event is fired.
          - `'networkidle'` - consider navigation to be finished when there are no network connections for at least `500` ms.
        - returns: <Optional[Response]> Promise which resolves to the main resource response. In case of multiple redirects, the navigation will resolve with the response of the last redirect.
        """
        return mapping.from_impl_nullable(
            await self._impl_obj.reload(timeout=timeout, waitUntil=waitUntil)
        )

    async def waitForLoadState(
        self,
        state: Literal["load", "domcontentloaded", "networkidle"] = "load",
        timeout: int = None,
    ) -> NoneType:
        """
        - `state` <"load"|"domcontentloaded"|"networkidle"> Load state to wait for, defaults to `load`. If the state has been already reached while loading current document, the method resolves immediately.
          - `'load'` - wait for the `load` event to be fired.
          - `'domcontentloaded'` - wait for the `DOMContentLoaded` event to be fired.
          - `'networkidle'` - wait until there are no network connections for at least `500` ms.
        - `timeout` <int> Maximum waiting time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultNavigationTimeout(timeout)](#browsercontextsetdefaultnavigationtimeouttimeout), [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout), [page.setDefaultNavigationTimeout(timeout)](#pagesetdefaultnavigationtimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Promise> Promise which resolves when the required load state has been reached.

        This resolves when the page reaches a required load state, `load` by default. The navigation must have been committed when this method is called. If current document has already reached the required state, resolves immediately.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.waitForLoadState(state=state, timeout=timeout)
        )

    async def waitForNavigation(
        self,
        timeout: int = None,
        waitUntil: Literal["load", "domcontentloaded", "networkidle"] = "load",
        url: str = None,
    ) -> typing.Union["Response", NoneType]:
        """
        - `timeout` <int> Maximum navigation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultNavigationTimeout(timeout)](#browsercontextsetdefaultnavigationtimeouttimeout), [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout), [page.setDefaultNavigationTimeout(timeout)](#pagesetdefaultnavigationtimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - `url` <[str]|[RegExp]|[Function]> A glob pattern, regex pattern or predicate receiving [URL] to match while waiting for the navigation.
        - `waitUntil` <"load"|"domcontentloaded"|"networkidle"> When to consider navigation succeeded, defaults to `load`. Events can be either:
          - `'domcontentloaded'` - consider navigation to be finished when the `DOMContentLoaded` event is fired.
          - `'load'` - consider navigation to be finished when the `load` event is fired.
          - `'networkidle'` - consider navigation to be finished when there are no network connections for at least `500` ms.
        - returns: <Optional[Response]> Promise which resolves to the main resource response. In case of multiple redirects, the navigation will resolve with the response of the last redirect. In case of navigation to a different anchor or navigation due to History API usage, the navigation will resolve with `null`.

        This resolves when the page navigates to a new URL or reloads. It is useful for when you run code
        which will indirectly cause the page to navigate. Consider this example:

        **NOTE** Usage of the [History API](https://developer.mozilla.org/en-US/docs/Web/API/History_API) to change the URL is considered a navigation.
        """
        return mapping.from_impl_nullable(
            await self._impl_obj.waitForNavigation(
                timeout=timeout, waitUntil=waitUntil, url=url
            )
        )

    async def waitForRequest(
        self,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]] = None,
        predicate: typing.Union[typing.Callable[["Request"], bool]] = None,
        timeout: int = None,
    ) -> typing.Union["Request", NoneType]:
        """
        - `url` <[str]|[RegExp]|[Function]> Request URL str, regex or predicate receiving [Request] object.
        - `timeout` <int> Maximum wait time in milliseconds, defaults to 30 seconds, pass `0` to disable the timeout. The default value can be changed by using the [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) method.
        - returns: <Request> Promise which resolves to the matched request.
        """
        return mapping.from_impl_nullable(
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
    ) -> typing.Union["Response", NoneType]:
        """
        - `url` <[str]|[RegExp]|[Function]> Request URL str, regex or predicate receiving [Response] object.
        - `timeout` <int> Maximum wait time in milliseconds, defaults to 30 seconds, pass `0` to disable the timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Response> Promise which resolves to the matched response.
        """
        return mapping.from_impl_nullable(
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
        """
        - `event` <str> Event name, same one would pass into `page.on(event)`.
          - `predicate` <Function> receives the event data and resolves to truthy value when the waiting should resolve.
          - `timeout` <int> maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Dict> Promise which resolves to the event data value.

        Waits for event to fire and passes its value into the predicate function. Resolves when the predicate returns truthy value. Will throw an error if the page is closed before the event
        is fired.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.waitForEvent(
                event=event, predicate=self._wrap_handler(predicate), timeout=timeout
            )
        )

    async def goBack(
        self,
        timeout: int = None,
        waitUntil: Literal["load", "domcontentloaded", "networkidle"] = None,
    ) -> typing.Union["Response", NoneType]:
        """
        - `timeout` <int> Maximum navigation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultNavigationTimeout(timeout)](#browsercontextsetdefaultnavigationtimeouttimeout), [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout), [page.setDefaultNavigationTimeout(timeout)](#pagesetdefaultnavigationtimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - `waitUntil` <"load"|"domcontentloaded"|"networkidle"> When to consider navigation succeeded, defaults to `load`. Events can be either:
          - `'domcontentloaded'` - consider navigation to be finished when the `DOMContentLoaded` event is fired.
          - `'load'` - consider navigation to be finished when the `load` event is fired.
          - `'networkidle'` - consider navigation to be finished when there are no network connections for at least `500` ms.
        - returns: <Optional[Response]> Promise which resolves to the main resource response. In case of multiple redirects, the navigation will resolve with the response of the last redirect. If
        can not go back, resolves to `null`.

        Navigate to the previous page in history.
        """
        return mapping.from_impl_nullable(
            await self._impl_obj.goBack(timeout=timeout, waitUntil=waitUntil)
        )

    async def goForward(
        self,
        timeout: int = None,
        waitUntil: Literal["load", "domcontentloaded", "networkidle"] = None,
    ) -> typing.Union["Response", NoneType]:
        """
        - `timeout` <int> Maximum navigation time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultNavigationTimeout(timeout)](#browsercontextsetdefaultnavigationtimeouttimeout), [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout), [page.setDefaultNavigationTimeout(timeout)](#pagesetdefaultnavigationtimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - `waitUntil` <"load"|"domcontentloaded"|"networkidle"> When to consider navigation succeeded, defaults to `load`. Events can be either:
          - `'domcontentloaded'` - consider navigation to be finished when the `DOMContentLoaded` event is fired.
          - `'load'` - consider navigation to be finished when the `load` event is fired.
          - `'networkidle'` - consider navigation to be finished when there are no network connections for at least `500` ms.
        - returns: <Optional[Response]> Promise which resolves to the main resource response. In case of multiple redirects, the navigation will resolve with the response of the last redirect. If
        can not go forward, resolves to `null`.

        Navigate to the next page in history.
        """
        return mapping.from_impl_nullable(
            await self._impl_obj.goForward(timeout=timeout, waitUntil=waitUntil)
        )

    async def emulateMedia(
        self,
        media: Literal["screen", "print"] = None,
        colorScheme: Literal["light", "dark", "no-preference"] = None,
    ) -> NoneType:
        """
        - `media` <?"screen"|"print"> Changes the CSS media type of the page. The only allowed values are `'screen'`, `'print'` and `null`. Passing `null` disables CSS media emulation. Omitting `media` or passing `undefined` does not change the emulated value.
        - `colorScheme` <?"dark"|"light"|"no-preference"> Emulates `'prefers-colors-scheme'` media feature, supported values are `'light'`, `'dark'`, `'no-preference'`. Passing `null` disables color scheme emulation. Omitting `colorScheme` or passing `undefined` does not change the emulated value.
        - returns: <Promise>
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.emulateMedia(media=media, colorScheme=colorScheme)
        )

    async def setViewportSize(self, width: int, height: int) -> NoneType:
        """
          - `width` <int> page width in pixels. **required**
          - `height` <int> page height in pixels. **required**
        - returns: <Promise>

        In the case of multiple pages in a single browser, each page can have its own viewport size. However, [browser.newContext([options])](#browsernewcontextoptions) allows to set viewport size (and more) for all pages in the context at once.

        `page.setViewportSize` will resize the page. A lot of websites don't expect phones to change size, so you should set the viewport size before navigating to the page.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.setViewportSize(width=width, height=height)
        )

    def viewportSize(self) -> typing.Union[Viewport, NoneType]:
        """
        - returns: <Optional[Dict]>
          - `width` <int> page width in pixels.
          - `height` <int> page height in pixels.
        """
        return mapping.from_maybe_impl(self._impl_obj.viewportSize())

    async def addInitScript(self, source: str = None, path: str = None) -> NoneType:
        """
        - `source` <[function]|[str]|[Dict]> Script to be evaluated in the page.
          - `path` <str> Path to the JavaScript file. If `path` is a relative path, then it is resolved relative to [current working directory](https://nodejs.org/api/process.html#process_process_cwd).
          - `content` <str> Raw script content.
        - returns: <Promise>

        Adds a script which would be evaluated in one of the following scenarios:
        - Whenever the page is navigated.
        - Whenever the child frame is attached or navigated. In this case, the scritp is evaluated in the context of the newly attached frame.

        The script is evaluated after the document was created but before any of its scripts were run. This is useful to amend  the JavaScript environment, e.g. to seed `Math.random`.

        An example of overriding `Math.random` before the page loads:

        > **NOTE** The order of evaluation of multiple scripts installed via [browserContext.addInitScript(script[, arg])](#browsercontextaddinitscriptscript-arg) and [page.addInitScript(script[, arg])](#pageaddinitscriptscript-arg) is not defined.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.addInitScript(source=source, path=path)
        )

    async def route(
        self,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]],
        handler: typing.Callable[["Route", "Request"], typing.Any],
    ) -> NoneType:
        """
        - `url` <[str]|[RegExp]|[function]\\([URL]\\):[bool]> A glob pattern, regex pattern or predicate receiving [URL] to match while routing.
        - `handler` <[function]\\([Route], [Request]\\)> handler function to route the request.
        - returns: <Promise>.

        Routing provides the capability to modify network requests that are made by a page.

        Once routing is enabled, every request matching the url pattern will stall unless it's continued, fulfilled or aborted.

        An example of a naïve handler that aborts all image requests:

        or the same snippet using a regex pattern instead:

        Page routes take precedence over browser context routes (set up with [browserContext.route(url, handler)](#browsercontextrouteurl-handler)) when request matches both handlers.

        > **NOTE** Enabling routing disables http cache.
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
        """
        - `url` <[str]|[RegExp]|[function]\\([URL]\\):[bool]> A glob pattern, regex pattern or predicate receiving [URL] to match while routing.
        - `handler` <[function]\\([Route], [Request]\\)> Handler function to route the request.
        - returns: <Promise>

        Removes a route created with [page.route(url, handler)](#pagerouteurl-handler). When `handler` is not specified, removes all routes for the `url`.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.unroute(
                url=self._wrap_handler(url), handler=self._wrap_handler(handler)
            )
        )

    async def screenshot(
        self,
        timeout: int = None,
        type: Literal["png", "jpeg"] = None,
        path: str = None,
        quality: int = None,
        omitBackground: bool = None,
        fullPage: bool = None,
        clip: typing.Dict = None,
    ) -> bytes:
        """
        - `path` <str> The file path to save the image to. The screenshot type will be inferred from file extension. If `path` is a relative path, then it is resolved relative to [current working directory](https://nodejs.org/api/process.html#process_process_cwd). If no path is provided, the image won't be saved to the disk.
        - `type` <"png"|"jpeg"> Specify screenshot type, defaults to `png`.
        - `quality` <int> The quality of the image, between 0-100. Not applicable to `png` images.
        - `fullPage` <bool> When true, takes a screenshot of the full scrollable page, instead of the currently visibvle viewport. Defaults to `false`.
        - `clip` <Dict> An object which specifies clipping of the resulting image. Should have the following fields:
          - `x` <int> x-coordinate of top-left corner of clip area
          - `y` <int> y-coordinate of top-left corner of clip area
          - `width` <int> width of clipping area
          - `height` <int> height of clipping area
        - `omitBackground` <bool> Hides default white background and allows capturing screenshots with transparency. Not applicable to `jpeg` images. Defaults to `false`.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <bytes> Promise which resolves to buffer with the captured screenshot.

        > **NOTE** Screenshots take at least 1/6 second on Chromium OS X and Chromium Windows. See https://crbug.com/741689 for discussion.
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
        """
        - returns: <str> The page's title.
        """
        return mapping.from_maybe_impl(await self._impl_obj.title())

    async def close(self, runBeforeUnload: bool = None) -> NoneType:
        """
        - `runBeforeUnload` <bool> Defaults to `false`. Whether to run the
          [before unload](https://developer.mozilla.org/en-US/docs/Web/Events/beforeunload)
          page handlers.
        - returns: <Promise>

        By default, `page.close()` **does not** run beforeunload handlers.

        > **NOTE** if `runBeforeUnload` is passed as true, a `beforeunload` dialog might be summoned
        > and should be handled manually via page's ['dialog'](#event-dialog) event.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.close(runBeforeUnload=runBeforeUnload)
        )

    def isClosed(self) -> bool:
        """
        - returns: <bool>

        Indicates that the page has been closed.
        """
        return mapping.from_maybe_impl(self._impl_obj.isClosed())

    async def click(
        self,
        selector: str,
        modifiers: typing.Union[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: typing.Dict = None,
        delay: int = None,
        button: Literal["left", "right", "middle"] = None,
        clickCount: int = None,
        timeout: int = None,
        force: bool = None,
        noWaitAfter: bool = None,
    ) -> NoneType:
        """
        - `selector` <str> A selector to search for element to click. If there are multiple elements satisfying the selector, the first will be clicked. See [working with selectors](#working-with-selectors) for more details.
        - `button` <"left"|"right"|"middle"> Defaults to `left`.
        - `clickCount` <int> defaults to 1. See [UIEvent.detail].
        - `delay` <int> Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        - `position` <Dict> A point to click relative to the top-left corner of element padding box. If not specified, clicks to some visible point of the element.
          - x <int>
          - y <int>
        - `modifiers` <[List]<"Alt"|"Control"|"Meta"|"Shift">> Modifier keys to press. Ensures that only these modifiers are pressed during the click, and then restores current modifiers back. If not specified, currently pressed modifiers are used.
        - `force` <bool> Whether to bypass the [actionability](./actionability.md) checks. Defaults to `false`.
        - `noWaitAfter` <bool> Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Promise> Promise which resolves when the element matching `selector` is successfully clicked. The Promise will be rejected if there is no element matching `selector`.

        This method fetches an element with `selector`, scrolls it into view if needed, and then uses [page.mouse](#pagemouse) to click in the center of the element.
        If there's no element matching `selector`, the method waits until a matching element appears in the DOM. If the element is detached during the [actionability](./actionability.md) checks, the action is retried.
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
        position: typing.Dict = None,
        delay: int = None,
        button: Literal["left", "right", "middle"] = None,
        timeout: int = None,
        force: bool = None,
    ) -> NoneType:
        """
        - `selector` <str> A selector to search for element to double click. If there are multiple elements satisfying the selector, the first will be double clicked. See [working with selectors](#working-with-selectors) for more details.
        - `button` <"left"|"right"|"middle"> Defaults to `left`.
        - `delay` <int> Time to wait between `mousedown` and `mouseup` in milliseconds. Defaults to 0.
        - `position` <Dict> A point to double click relative to the top-left corner of element padding box. If not specified, double clicks to some visible point of the element.
          - x <int>
          - y <int>
        - `modifiers` <[List]<"Alt"|"Control"|"Meta"|"Shift">> Modifier keys to press. Ensures that only these modifiers are pressed during the double click, and then restores current modifiers back. If not specified, currently pressed modifiers are used.
        - `force` <bool> Whether to bypass the [actionability](./actionability.md) checks. Defaults to `false`.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Promise> Promise which resolves when the element matching `selector` is successfully double clicked. The Promise will be rejected if there is no element matching `selector`.

        This method fetches an element with `selector`, scrolls it into view if needed, and then uses [page.mouse](#pagemouse) to double click in the center of the element.
        If there's no element matching `selector`, the method waits until a matching element appears in the DOM. If the element is detached during the [actionability](./actionability.md) checks, the action is retried.

        Bear in mind that if the first click of the `dblclick()` triggers a navigation event, there will be an exception.

        > **NOTE** `page.dblclick()` dispatches two `click` events and a single `dblclick` event.
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
            )
        )

    async def fill(
        self, selector: str, value: str, timeout: int = None, noWaitAfter: bool = None
    ) -> NoneType:
        """
        - `selector` <str> A selector to query page for. See [working with selectors](#working-with-selectors) for more details.
        - `value` <str> Value to fill for the `<input>`, `<textarea>` or `[contenteditable]` element.
        - `noWaitAfter` <bool> Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Promise>

        This method waits for an element matching `selector`, waits for [actionability](./actionability.md) checks, focuses the element, fills it and triggers an `input` event after filling.
        If the element matching `selector` is not an `<input>`, `<textarea>` or `[contenteditable]` element, this method throws an error.
        Note that you can pass an empty str to clear the input field.

        To send fine-grained keyboard events, use [`page.type`](#pagetypeselector-text-options).
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.fill(
                selector=selector, value=value, timeout=timeout, noWaitAfter=noWaitAfter
            )
        )

    async def focus(self, selector: str, timeout: int = None) -> NoneType:
        """
        - `selector` <str> A selector of an element to focus. If there are multiple elements satisfying the selector, the first will be focused. See [working with selectors](#working-with-selectors) for more details.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Promise> Promise which resolves when the element matching `selector` is successfully focused. The promise will be rejected if there is no element matching `selector`.

        This method fetches an element with `selector` and focuses it.
        If there's no element matching `selector`, the method waits until a matching element appears in the DOM.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.focus(selector=selector, timeout=timeout)
        )

    async def textContent(self, selector: str, timeout: int = None) -> str:
        """
        - `selector` <str> A selector to search for an element. If there are multiple elements satisfying the selector, the first will be picked. See [working with selectors](#working-with-selectors) for more details.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <null|[str]>

        Resolves to the `element.textContent`.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.textContent(selector=selector, timeout=timeout)
        )

    async def innerText(self, selector: str, timeout: int = None) -> str:
        """
        - `selector` <str> A selector to search for an element. If there are multiple elements satisfying the selector, the first will be picked. See [working with selectors](#working-with-selectors) for more details.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <str>

        Resolves to the `element.innerText`.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.innerText(selector=selector, timeout=timeout)
        )

    async def innerHTML(self, selector: str, timeout: int = None) -> str:
        """
        - `selector` <str> A selector to search for an element. If there are multiple elements satisfying the selector, the first will be picked. See [working with selectors](#working-with-selectors) for more details.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <str>

        Resolves to the `element.innerHTML`.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.innerHTML(selector=selector, timeout=timeout)
        )

    async def getAttribute(self, selector: str, name: str, timeout: int = None) -> str:
        """
        - `selector` <str> A selector to search for an element. If there are multiple elements satisfying the selector, the first will be picked. See [working with selectors](#working-with-selectors) for more details.
        - `name` <str> Attribute name to get the value for.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <null|[str]>

        Returns element attribute value.
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
        position: typing.Dict = None,
        timeout: int = None,
        force: bool = None,
    ) -> NoneType:
        """
        - `selector` <str> A selector to search for element to hover. If there are multiple elements satisfying the selector, the first will be hovered. See [working with selectors](#working-with-selectors) for more details.
        - `position` <Dict> A point to hover relative to the top-left corner of element padding box. If not specified, hovers over some visible point of the element.
          - x <int>
          - y <int>
        - `modifiers` <[List]<"Alt"|"Control"|"Meta"|"Shift">> Modifier keys to press. Ensures that only these modifiers are pressed during the hover, and then restores current modifiers back. If not specified, currently pressed modifiers are used.
        - `force` <bool> Whether to bypass the [actionability](./actionability.md) checks. Defaults to `false`.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Promise> Promise which resolves when the element matching `selector` is successfully hovered. Promise gets rejected if there's no element matching `selector`.

        This method fetches an element with `selector`, scrolls it into view if needed, and then uses [page.mouse](#pagemouse) to hover over the center of the element.
        If there's no element matching `selector`, the method waits until a matching element appears in the DOM. If the element is detached during the [actionability](./actionability.md) checks, the action is retried.
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
        ],
        timeout: int = None,
        noWaitAfter: bool = None,
    ) -> typing.List[str]:
        """
        - `selector` <str> A selector to query page for. See [working with selectors](#working-with-selectors) for more details.
        - `values` <null|[str]|[ElementHandle]|[List]<str>|[Dict]|[List]<ElementHandle>|[List]<Dict>> Options to select. If the `<select>` has the `multiple` attribute, all matching options are selected, otherwise only the first option matching one of the passed options is selected. String values are equivalent to `{value:'str'}`. Option is considered matching if all specified properties match.
          - `value` <str> Matches by `option.value`.
          - `label` <str> Matches by `option.label`.
          - `index` <int> Matches by the index.
        - `noWaitAfter` <bool> Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <List[str]> An array of option values that have been successfully selected.

        Triggers a `change` and `input` event once all the provided options have been selected.
        If there's no `<select>` element matching `selector`, the method throws an error.
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
        """
        - `selector` <str> A selector to search for element to click. If there are multiple elements satisfying the selector, the first will be clicked. See [working with selectors](#working-with-selectors) for more details.
        - `files` <[str]|[List]<str>|[Dict]|[List]<Dict>>
          - `name` <str> [File] name **required**
          - `mimeType` <str> [File] type **required**
          - `buffer` <bytes> File content **required**
        - `noWaitAfter` <bool> Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Promise>

        This method expects `selector` to point to an [input element](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/input).

        Sets the value of the file input to these file paths or files. If some of the `filePaths` are relative paths, then they are resolved relative to the [current working directory](https://nodejs.org/api/process.html#process_process_cwd). For empty array, clears the selected files.
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
        """
        - `selector` <str> A selector of an element to type into. If there are multiple elements satisfying the selector, the first will be used. See [working with selectors](#working-with-selectors) for more details.
        - `text` <str> A text to type into a focused element.
        - `delay` <int> Time to wait between key presses in milliseconds. Defaults to 0.
        - `noWaitAfter` <bool> Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Promise>

        Sends a `keydown`, `keypress`/`input`, and `keyup` event for each character in the text. `page.type` can be used to send fine-grained keyboard events. To fill values in form fields, use [`page.fill`](#pagefillselector-value-options).

        To press a special key, like `Control` or `ArrowDown`, use [`keyboard.press`](#keyboardpresskey-options).
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
        """
        - `selector` <str> A selector of an element to type into. If there are multiple elements satisfying the selector, the first will be used. See [working with selectors](#working-with-selectors) for more details.
        - `key` <str> Name of the key to press or a character to generate, such as `ArrowLeft` or `a`.
        - `delay` <int> Time to wait between `keydown` and `keyup` in milliseconds. Defaults to 0.
        - `noWaitAfter` <bool> Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Promise>

        Focuses the element, and then uses [`keyboard.down`](#keyboarddownkey) and [`keyboard.up`](#keyboardupkey).

        `key` can specify the intended [keyboardEvent.key](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/key) value or a single character to generate the text for. A superset of the `key` values can be found [here](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/key/Key_Values). Examples of the keys are:

          `F1` - `F12`, `Digit0`- `Digit9`, `KeyA`- `KeyZ`, `Backquote`, `Minus`, `Equal`, `Backslash`, `Backspace`, `Tab`, `Delete`, `Escape`, `ArrowDown`, `End`, `Enter`, `Home`, `Insert`, `PageDown`, `PageUp`, `ArrowRight`, `ArrowUp`, etc.

        Following modification shortcuts are also suported: `Shift`, `Control`, `Alt`, `Meta`, `ShiftLeft`.

        Holding down `Shift` will type the text that corresponds to the `key` in the upper case.

        If `key` is a single character, it is case-sensitive, so the values `a` and `A` will generate different respective texts.

        Shortcuts such as `key: "Control+o"` or `key: "Control+Shift+T"` are supported as well. When speficied with the modifier, modifier is pressed and being held while the subsequent key is being pressed.
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
        """
        - `selector` <str> A selector to search for checkbox or radio button to check. If there are multiple elements satisfying the selector, the first will be checked. See [working with selectors](#working-with-selectors) for more details.
        - `force` <bool> Whether to bypass the [actionability](./actionability.md) checks. Defaults to `false`.
        - `noWaitAfter` <bool> Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Promise> Promise which resolves when the element matching `selector` is successfully checked. The Promise will be rejected if there is no element matching `selector`.

        This method fetches an element with `selector`, if element is not already checked, it scrolls it into view if needed, and then uses [page.click](#pageclickselector-options) to click in the center of the element.
        If there's no element matching `selector`, the method waits until a matching element appears in the DOM. If the element is detached during the [actionability](./actionability.md) checks, the action is retried.
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
        """
        - `selector` <str> A selector to search for uncheckbox to check. If there are multiple elements satisfying the selector, the first will be checked. See [working with selectors](#working-with-selectors) for more details.
        - `force` <bool> Whether to bypass the [actionability](./actionability.md) checks. Defaults to `false`.
        - `noWaitAfter` <bool> Actions that initiate navigations are waiting for these navigations to happen and for pages to start loading. You can opt out of waiting via setting this flag. You would only need this option in the exceptional cases such as navigating to inaccessible pages. Defaults to `false`.
        - `timeout` <int> Maximum time in milliseconds, defaults to 30 seconds, pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout) or [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) methods.
        - returns: <Promise> Promise which resolves when the element matching `selector` is successfully unchecked. The Promise will be rejected if there is no element matching `selector`.

        This method fetches an element with `selector`, if element is not already unchecked, it scrolls it into view if needed, and then uses [page.click](#pageclickselector-options) to click in the center of the element.
        If there's no element matching `selector`, the method waits until a matching element appears in the DOM. If the element is detached during the [actionability](./actionability.md) checks, the action is retried.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.uncheck(
                selector=selector, timeout=timeout, force=force, noWaitAfter=noWaitAfter
            )
        )

    async def waitForTimeout(self, timeout: int) -> typing.Awaitable[NoneType]:
        """
        - `timeout` <int> A timeout to wait for
        - returns: <Promise>

        Returns a promise that resolves after the timeout.

        Note that `page.waitForTimeout()` should only be used for debugging. Tests using the timer in production are going to be flaky. Use signals such as network events, selectors becoming visible and others instead.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.waitForTimeout(timeout=timeout)
        )

    async def waitForFunction(
        self,
        expression: str,
        arg: typing.Any = None,
        force_expr: bool = False,
        timeout: int = None,
        polling: typing.Union[int, Literal["raf"]] = None,
    ) -> "JSHandle":
        """
        - `expression` <[str]> Function to be evaluated in browser context
        - `force_expr` <[bool]> Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function
        - `arg` <[Serializable]|[JSHandle]> Optional argument to pass to `pageFunction`
        - `polling` <[int]|"raf"> If `polling` is `'raf'`, then `pageFunction` is constantly executed in `requestAnimationFrame` callback. If `polling` is a int, then it is treated as an interval in milliseconds at which the function would be executed. Defaults to `raf`.
        - `timeout` <int> maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can be changed by using the [page.setDefaultTimeout(timeout)](#pagesetdefaulttimeouttimeout) method.
        - returns: <JSHandle> Promise which resolves when the `pageFunction` returns a truthy value. It resolves to a JSHandle of the truthy value.

        The `waitForFunction` can be used to observe viewport size change:

        To pass an argument from Node.js to the predicate of `page.waitForFunction` function:
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
        margin: typing.Dict = None,
        path: str = None,
    ) -> bytes:
        """
        - `path` <str> The file path to save the PDF to. If `path` is a relative path, then it is resolved relative to [current working directory](https://nodejs.org/api/process.html#process_process_cwd). If no path is provided, the PDF won't be saved to the disk.
        - `scale` <int> Scale of the webpage rendering. Defaults to `1`. Scale amount must be between 0.1 and 2.
        - `displayHeaderFooter` <bool> Display header and footer. Defaults to `false`.
        - `headerTemplate` <str> HTML template for the print header. Should be valid HTML markup with following classes used to inject printing values into them:
          - `'date'` formatted print date
          - `'title'` document title
          - `'url'` document location
          - `'pageNumber'` current page int
          - `'totalPages'` total pages in the document
        - `footerTemplate` <str> HTML template for the print footer. Should use the same format as the `headerTemplate`.
        - `printBackground` <bool> Print background graphics. Defaults to `false`.
        - `landscape` <bool> Paper orientation. Defaults to `false`.
        - `pageRanges` <str> Paper ranges to print, e.g., '1-5, 8, 11-13'. Defaults to the empty str, which means print all pages.
        - `format` <str> Paper format. If set, takes priority over `width` or `height` options. Defaults to 'Letter'.
        - `width` <[str]|[int]> Paper width, accepts values labeled with units.
        - `height` <[str]|[int]> Paper height, accepts values labeled with units.
        - `margin` <Dict> Paper margins, defaults to none.
          - `top` <[str]|[int]> Top margin, accepts values labeled with units. Defaults to `0`.
          - `right` <[str]|[int]> Right margin, accepts values labeled with units. Defaults to `0`.
          - `bottom` <[str]|[int]> Bottom margin, accepts values labeled with units. Defaults to `0`.
          - `left` <[str]|[int]> Left margin, accepts values labeled with units. Defaults to `0`.
        - `preferCSSPageSize` <bool> Give any CSS `@page` size declared in the page priority over what is declared in `width` and `height` or `format` options. Defaults to `false`, which will scale the content to fit the paper size.
        - returns: <bytes> Promise which resolves with PDF buffer.

        > **NOTE** Generating a pdf is currently only supported in Chromium headless.

        `page.pdf()` generates a pdf of the page with `print` css media. To generate a pdf with `screen` media, call [page.emulateMedia({ media: 'screen' })](#pageemulatemediaoptions) before calling `page.pdf()`:

        > **NOTE** By default, `page.pdf()` generates a pdf with modified colors for printing. Use the [`-webkit-print-color-adjust`](https://developer.mozilla.org/en-US/docs/Web/CSS/-webkit-print-color-adjust) property to force rendering of exact colors.

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

        > **NOTE** `headerTemplate` and `footerTemplate` markup have the following limitations:
        > 1. Script tags inside templates are not evaluated.
        > 2. Page styles are not visible inside templates.
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

    def expect_console_message(
        self,
        predicate: typing.Union[typing.Callable[["ConsoleMessage"], bool]] = None,
        timeout: int = None,
    ) -> AsyncEventContextManager["ConsoleMessage"]:
        return AsyncEventContextManager(self, "console", predicate, timeout)

    def expect_dialog(
        self,
        predicate: typing.Union[typing.Callable[["Dialog"], bool]] = None,
        timeout: int = None,
    ) -> AsyncEventContextManager["Dialog"]:
        return AsyncEventContextManager(self, "dialog", predicate, timeout)

    def expect_download(
        self,
        predicate: typing.Union[typing.Callable[["Download"], bool]] = None,
        timeout: int = None,
    ) -> AsyncEventContextManager["Download"]:
        return AsyncEventContextManager(self, "download", predicate, timeout)

    def expect_file_chooser(
        self,
        predicate: typing.Union[typing.Callable[["FileChooser"], bool]] = None,
        timeout: int = None,
    ) -> AsyncEventContextManager["FileChooser"]:
        return AsyncEventContextManager(self, "filechooser", predicate, timeout)

    def expect_request(
        self,
        predicate: typing.Union[typing.Callable[["Request"], bool]] = None,
        timeout: int = None,
    ) -> AsyncEventContextManager["Request"]:
        return AsyncEventContextManager(self, "request", predicate, timeout)

    def expect_response(
        self,
        predicate: typing.Union[typing.Callable[["Response"], bool]] = None,
        timeout: int = None,
    ) -> AsyncEventContextManager["Response"]:
        return AsyncEventContextManager(self, "response", predicate, timeout)

    def expect_popup(
        self,
        predicate: typing.Union[typing.Callable[["Page"], bool]] = None,
        timeout: int = None,
    ) -> AsyncEventContextManager["Page"]:
        return AsyncEventContextManager(self, "popup", predicate, timeout)

    def expect_worker(
        self,
        predicate: typing.Union[typing.Callable[["Worker"], bool]] = None,
        timeout: int = None,
    ) -> AsyncEventContextManager["Worker"]:
        return AsyncEventContextManager(self, "worker", predicate, timeout)


mapping.register(PageImpl, Page)


class BrowserContext(AsyncBase):
    def __init__(self, obj: BrowserContextImpl):
        super().__init__(obj)

    @property
    def pages(self) -> typing.List["Page"]:
        """
        - returns: <List[Page]> All open pages in the context. Non visible pages, such as `"background_page"`, will not be listed here. You can find them using [chromiumBrowserContext.backgroundPages()](#chromiumbrowsercontextbackgroundpages).
        """
        return mapping.from_impl_list(self._impl_obj.pages)

    def setDefaultNavigationTimeout(self, timeout: int) -> NoneType:
        """
        - `timeout` <int> Maximum navigation time in milliseconds

        This setting will change the default maximum navigation time for the following methods and related shortcuts:
        - [page.goBack([options])](#pagegobackoptions)
        - [page.goForward([options])](#pagegoforwardoptions)
        - [page.goto(url[, options])](#pagegotourl-options)
        - [page.reload([options])](#pagereloadoptions)
        - [page.setContent(html[, options])](#pagesetcontenthtml-options)
        - [page.waitForNavigation([options])](#pagewaitfornavigationoptions)

        > **NOTE** [`page.setDefaultNavigationTimeout`](#pagesetdefaultnavigationtimeouttimeout) and [`page.setDefaultTimeout`](#pagesetdefaulttimeouttimeout) take priority over [`browserContext.setDefaultNavigationTimeout`](#browsercontextsetdefaultnavigationtimeouttimeout).
        """
        return mapping.from_maybe_impl(
            self._impl_obj.setDefaultNavigationTimeout(timeout=timeout)
        )

    def setDefaultTimeout(self, timeout: int) -> NoneType:
        """
        - `timeout` <int> Maximum time in milliseconds

        This setting will change the default maximum time for all the methods accepting `timeout` option.

        > **NOTE** [`page.setDefaultNavigationTimeout`](#pagesetdefaultnavigationtimeouttimeout), [`page.setDefaultTimeout`](#pagesetdefaulttimeouttimeout) and [`browserContext.setDefaultNavigationTimeout`](#browsercontextsetdefaultnavigationtimeouttimeout) take priority over [`browserContext.setDefaultTimeout`](#browsercontextsetdefaulttimeouttimeout).
        """
        return mapping.from_maybe_impl(
            self._impl_obj.setDefaultTimeout(timeout=timeout)
        )

    async def newPage(self) -> "Page":
        """
        - returns: <Page>

        Creates a new page in the browser context.
        """
        return mapping.from_impl(await self._impl_obj.newPage())

    async def cookies(
        self, urls: typing.Union[str, typing.List[str]]
    ) -> typing.List[typing.List[typing.Dict[str, typing.Union[str, int, bool]]]]:
        """
        - `urls` <[str]|[List]<str>>
        - returns: <List[Dict]>
          - `name` <str>
          - `value` <str>
          - `domain` <str>
          - `path` <str>
          - `expires` <int> Unix time in seconds.
          - `httpOnly` <bool>
          - `secure` <bool>
          - `sameSite` <"Strict"|"Lax"|"None">

        If no URLs are specified, this method returns all cookies.
        If URLs are specified, only cookies that affect those URLs are returned.
        """
        return mapping.from_maybe_impl(await self._impl_obj.cookies(urls=urls))

    async def addCookies(
        self,
        cookies: typing.List[
            typing.List[typing.Dict[str, typing.Union[str, int, bool]]]
        ],
    ) -> NoneType:
        """
        - `cookies` <List[Dict]>
          - `name` <str> **required**
          - `value` <str> **required**
          - `url` <str> either url or domain / path are required
          - `domain` <str> either url or domain / path are required
          - `path` <str> either url or domain / path are required
          - `expires` <int> Unix time in seconds.
          - `httpOnly` <bool>
          - `secure` <bool>
          - `sameSite` <"Strict"|"Lax"|"None">
        - returns: <Promise>
        """
        return mapping.from_maybe_impl(await self._impl_obj.addCookies(cookies=cookies))

    async def clearCookies(self) -> NoneType:
        """
        - returns: <Promise>

        Clears context cookies.
        """
        return mapping.from_maybe_impl(await self._impl_obj.clearCookies())

    async def grantPermissions(
        self, permissions: typing.List[str], origin: str = None
    ) -> NoneType:
        """
        - `permissions` <List[str]> A permission or an array of permissions to grant. Permissions can be one of the following values:
            - `'*'`
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
        - `origin` <str> The [origin] to grant permissions to, e.g. "https://example.com".
        - returns: <Promise>

        Grants specified permissions to the browser context. Only grants corresponding permissions to the given origin if specified.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.grantPermissions(
                permissions=permissions, origin=origin
            )
        )

    async def clearPermissions(self) -> NoneType:
        """
        - returns: <Promise>

        Clears all permission overrides for the browser context.
        """
        return mapping.from_maybe_impl(await self._impl_obj.clearPermissions())

    async def setGeolocation(self, geolocation: typing.Dict) -> NoneType:
        """
        - `geolocation` <Optional[Dict]>
          - `latitude` <int> Latitude between -90 and 90. **required**
          - `longitude` <int> Longitude between -180 and 180. **required**
          - `accuracy` <int> Non-negative accuracy value. Defaults to `0`.
        - returns: <Promise>

        Sets the context's geolocation. Passing `null` or `undefined` emulates position unavailable.

        > **NOTE** Consider using [browserContext.grantPermissions](#browsercontextgrantpermissionspermissions-options) to grant permissions for the browser context pages to read its geolocation.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.setGeolocation(geolocation=geolocation)
        )

    async def setExtraHTTPHeaders(self, headers: typing.Dict) -> NoneType:
        """
        - `headers` <[Dict]<[str], [str]>> An object containing additional HTTP headers to be sent with every request. All header values must be strs.
        - returns: <Promise>

        The extra HTTP headers will be sent with every request initiated by any page in the context. These headers are merged with page-specific extra HTTP headers set with [page.setExtraHTTPHeaders()](#pagesetextrahttpheadersheaders). If page overrides a particular header, page-specific header value will be used instead of the browser context header value.

        > **NOTE** `browserContext.setExtraHTTPHeaders` does not guarantee the order of headers in the outgoing requests.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.setExtraHTTPHeaders(headers=headers)
        )

    async def setOffline(self, offline: bool) -> NoneType:
        """
        - `offline` <bool> Whether to emulate network being offline for the browser context.
        - returns: <Promise>
        """
        return mapping.from_maybe_impl(await self._impl_obj.setOffline(offline=offline))

    async def addInitScript(self, source: str = None, path: str = None) -> NoneType:
        """
        - `source` <[function]|[str]|[Dict]> Script to be evaluated in all pages in the browser context.
          - `path` <str> Path to the JavaScript file. If `path` is a relative path, then it is resolved relative to [current working directory](https://nodejs.org/api/process.html#process_process_cwd).
          - `content` <str> Raw script content.
        - returns: <Promise>

        Adds a script which would be evaluated in one of the following scenarios:
        - Whenever a page is created in the browser context or is navigated.
        - Whenever a child frame is attached or navigated in any page in the browser context. In this case, the script is evaluated in the context of the newly attached frame.

        The script is evaluated after the document was created but before any of its scripts were run. This is useful to amend  the JavaScript environment, e.g. to seed `Math.random`.

        An example of overriding `Math.random` before the page loads:

        > **NOTE** The order of evaluation of multiple scripts installed via [browserContext.addInitScript(script[, arg])](#browsercontextaddinitscriptscript-arg) and [page.addInitScript(script[, arg])](#pageaddinitscriptscript-arg) is not defined.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.addInitScript(source=source, path=path)
        )

    async def exposeBinding(
        self, name: str, binding: typing.Callable[[typing.Dict], typing.Any]
    ) -> NoneType:
        """
        - `name` <str> Name of the function on the window object.
        - `binding` <function> Callback function that will be called in the Playwright's context.
        - returns: <Promise>

        The method adds a function called `name` on the `window` object of every frame in every page in the context.
        When called, the function executes `playwrightBinding` in Node.js and returns a [Promise] which resolves to the return value of `playwrightBinding`.
        If the `playwrightBinding` returns a [Promise], it will be awaited.

        The first argument of the `playwrightBinding` function contains information about the caller:
        `{ browserContext: BrowserContext, page: Page, frame: Frame }`.

        See [page.exposeBinding(name, playwrightBinding)](#pageexposebindingname-playwrightbinding) for page-only version.

        An example of exposing page URL to all frames in all pages in the context:
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.exposeBinding(
                name=name, binding=self._wrap_handler(binding)
            )
        )

    async def exposeFunction(
        self, name: str, binding: typing.Callable[..., typing.Any]
    ) -> NoneType:
        """
        - `name` <str> Name of the function on the window object.
        - `binding` <function> Callback function that will be called in the Playwright's context.
        - returns: <Promise>

        The method adds a function called `name` on the `window` object of every frame in every page in the context.
        When called, the function executes `playwrightFunction` in Node.js and returns a [Promise] which resolves to the return value of `playwrightFunction`.

        If the `playwrightFunction` returns a [Promise], it will be awaited.

        See [page.exposeFunction(name, playwrightFunction)](#pageexposefunctionname-playwrightfunction) for page-only version.

        An example of adding an `md5` function to all pages in the context:
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
        """
        - `url` <[str]|[RegExp]|[function]\\([URL]\\):[bool]> A glob pattern, regex pattern or predicate receiving [URL] to match while routing.
        - `handler` <[function]\\([Route], [Request]\\)> handler function to route the request.
        - returns: <Promise>

        Routing provides the capability to modify network requests that are made by any page in the browser context.
        Once route is enabled, every request matching the url pattern will stall unless it's continued, fulfilled or aborted.

        An example of a naïve handler that aborts all image requests:

        or the same snippet using a regex pattern instead:

        Page routes (set up with [page.route(url, handler)](#pagerouteurl-handler)) take precedence over browser context routes when request matches both handlers.

        > **NOTE** Enabling routing disables http cache.
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
        """
        - `url` <[str]|[RegExp]|[function]\\([URL]\\):[bool]> A glob pattern, regex pattern or predicate receiving [URL] used to register a routing with [browserContext.route(url, handler)](#browsercontextrouteurl-handler).
        - `handler` <[function]\\([Route], [Request]\\)> Handler function used to register a routing with [browserContext.route(url, handler)](#browsercontextrouteurl-handler).
        - returns: <Promise>

        Removes a route created with [browserContext.route(url, handler)](#browsercontextrouteurl-handler). When `handler` is not specified, removes all routes for the `url`.
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
        """
        - `event` <str> Event name, same one would pass into `browserContext.on(event)`.
          - `predicate` <Function> receives the event data and resolves to truthy value when the waiting should resolve.
          - `timeout` <int> maximum time to wait for in milliseconds. Defaults to `30000` (30 seconds). Pass `0` to disable timeout. The default value can be changed by using the [browserContext.setDefaultTimeout(timeout)](#browsercontextsetdefaulttimeouttimeout).
        - returns: <Dict> Promise which resolves to the event data value.

        Waits for event to fire and passes its value into the predicate function. Resolves when the predicate returns truthy value. Will throw an error if the context closes before the event
        is fired.
        """
        return mapping.from_maybe_impl(
            await self._impl_obj.waitForEvent(
                event=event, predicate=self._wrap_handler(predicate), timeout=timeout
            )
        )

    async def close(self) -> NoneType:
        """
        - returns: <Promise>

        Closes the browser context. All the pages that belong to the browser context
        will be closed.

        > **NOTE** the default browser context cannot be closed.
        """
        return mapping.from_maybe_impl(await self._impl_obj.close())

    def expect_page(
        self,
        predicate: typing.Union[typing.Callable[["Page"], bool]] = None,
        timeout: int = None,
    ) -> AsyncEventContextManager["Page"]:
        return AsyncEventContextManager(self, "page", predicate, timeout)


mapping.register(BrowserContextImpl, BrowserContext)


class Browser(AsyncBase):
    def __init__(self, obj: BrowserImpl):
        super().__init__(obj)

    @property
    def contexts(self) -> typing.List["BrowserContext"]:
        """
        - returns: <List[BrowserContext]>

        Returns an array of all open browser contexts. In a newly created browser, this will return zero
        browser contexts.
        """
        return mapping.from_impl_list(self._impl_obj.contexts)

    def isConnected(self) -> bool:
        """
        - returns: <bool>

        Indicates that the browser is connected.
        """
        return mapping.from_maybe_impl(self._impl_obj.isConnected())

    async def newContext(
        self,
        viewport: typing.Union[typing.Dict, Literal[0]] = None,
        ignoreHTTPSErrors: bool = None,
        javaScriptEnabled: bool = None,
        bypassCSP: bool = None,
        userAgent: str = None,
        locale: str = None,
        timezoneId: str = None,
        geolocation: typing.Dict = None,
        permissions: typing.List[str] = None,
        extraHTTPHeaders: typing.Union[typing.Dict[str, str]] = None,
        offline: bool = None,
        httpCredentials: typing.Dict = None,
        deviceScaleFactor: int = None,
        isMobile: bool = None,
        hasTouch: bool = None,
        colorScheme: Literal["light", "dark", "no-preference"] = None,
        acceptDownloads: bool = None,
    ) -> "BrowserContext":
        """
        - `acceptDownloads` <bool> Whether to automatically download all the attachments. Defaults to `false` where all the downloads are canceled.
        - `ignoreHTTPSErrors` <bool> Whether to ignore HTTPS errors during navigation. Defaults to `false`.
        - `bypassCSP` <bool> Toggles bypassing page's Content-Security-Policy.
        - `viewport` <Optional[Dict]> Sets a consistent viewport for each page. Defaults to an 1280x720 viewport. `null` disables the default viewport.
          - `width` <int> page width in pixels.
          - `height` <int> page height in pixels.
        - `userAgent` <str> Specific user agent to use in this context.
        - `deviceScaleFactor` <int> Specify device scale factor (can be thought of as dpr). Defaults to `1`.
        - `isMobile` <bool> Whether the `meta viewport` tag is taken into account and touch events are enabled. Defaults to `false`. Not supported in Firefox.
        - `hasTouch` <bool> Specifies if viewport supports touch events. Defaults to false.
        - `javaScriptEnabled` <bool> Whether or not to enable JavaScript in the context. Defaults to true.
        - `timezoneId` <str> Changes the timezone of the context. See [ICU’s `metaZones.txt`](https://cs.chromium.org/chromium/src/third_party/icu/source/data/misc/metaZones.txt?rcl=faee8bc70570192d82d2978a71e2a615788597d1) for a list of supported timezone IDs.
        - `geolocation` <Dict>
          - `latitude` <int> Latitude between -90 and 90.
          - `longitude` <int> Longitude between -180 and 180.
          - `accuracy` <int> Non-negative accuracy value. Defaults to `0`.
        - `locale` <str> Specify user locale, for example `en-GB`, `de-DE`, etc. Locale will affect `navigator.language` value, `Accept-Language` request header value as well as int and date formatting rules.
        - `permissions` <List[str]> A list of permissions to grant to all pages in this context. See [browserContext.grantPermissions](#browsercontextgrantpermissionspermissions-options) for more details.
        - `extraHTTPHeaders` <[Dict]<[str], [str]>> An object containing additional HTTP headers to be sent with every request. All header values must be strs.
        - `offline` <bool> Whether to emulate network being offline. Defaults to `false`.
        - `httpCredentials` <Dict> Credentials for [HTTP authentication](https://developer.mozilla.org/en-US/docs/Web/HTTP/Authentication).
          - `username` <str>
          - `password` <str>
        - `colorScheme` <"dark"|"light"|"no-preference"> Emulates `'prefers-colors-scheme'` media feature, supported values are `'light'`, `'dark'`, `'no-preference'`. See [page.emulateMedia(options)](#pageemulatemediaoptions) for more details. Defaults to '`light`'.
        - `logger` <Logger> Logger sink for Playwright logging.
        - returns: <BrowserContext>

        Creates a new browser context. It won't share cookies/cache with other browser contexts.
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
                extraHTTPHeaders=extraHTTPHeaders,
                offline=offline,
                httpCredentials=httpCredentials,
                deviceScaleFactor=deviceScaleFactor,
                isMobile=isMobile,
                hasTouch=hasTouch,
                colorScheme=colorScheme,
                acceptDownloads=acceptDownloads,
            )
        )

    async def newPage(
        self,
        viewport: typing.Union[typing.Dict, Literal[0]] = None,
        ignoreHTTPSErrors: bool = None,
        javaScriptEnabled: bool = None,
        bypassCSP: bool = None,
        userAgent: str = None,
        locale: str = None,
        timezoneId: str = None,
        geolocation: typing.Dict = None,
        permissions: typing.List[str] = None,
        extraHTTPHeaders: typing.Union[typing.Dict[str, str]] = None,
        offline: bool = None,
        httpCredentials: typing.Dict = None,
        deviceScaleFactor: int = None,
        isMobile: bool = None,
        hasTouch: bool = None,
        colorScheme: Literal["light", "dark", "no-preference"] = None,
        acceptDownloads: bool = None,
    ) -> "Page":
        """
        - `acceptDownloads` <bool> Whether to automatically download all the attachments. Defaults to `false` where all the downloads are canceled.
        - `ignoreHTTPSErrors` <bool> Whether to ignore HTTPS errors during navigation. Defaults to `false`.
        - `bypassCSP` <bool> Toggles bypassing page's Content-Security-Policy.
        - `viewport` <Optional[Dict]> Sets a consistent viewport for each page. Defaults to an 1280x720 viewport. `null` disables the default viewport.
          - `width` <int> page width in pixels.
          - `height` <int> page height in pixels.
        - `userAgent` <str> Specific user agent to use in this context.
        - `deviceScaleFactor` <int> Specify device scale factor (can be thought of as dpr). Defaults to `1`.
        - `isMobile` <bool> Whether the `meta viewport` tag is taken into account and touch events are enabled. Defaults to `false`. Not supported in Firefox.
        - `hasTouch` <bool> Specifies if viewport supports touch events. Defaults to false.
        - `javaScriptEnabled` <bool> Whether or not to enable JavaScript in the context. Defaults to `true`.
        - `timezoneId` <str> Changes the timezone of the context. See [ICU’s `metaZones.txt`](https://cs.chromium.org/chromium/src/third_party/icu/source/data/misc/metaZones.txt?rcl=faee8bc70570192d82d2978a71e2a615788597d1) for a list of supported timezone IDs.
        - `geolocation` <Dict>
          - `latitude` <int> Latitude between -90 and 90.
          - `longitude` <int> Longitude between -180 and 180.
          - `accuracy` <int> Non-negative accuracy value. Defaults to `0`.
        - `locale` <str> Specify user locale, for example `en-GB`, `de-DE`, etc. Locale will affect `navigator.language` value, `Accept-Language` request header value as well as int and date formatting rules.
        - `permissions` <List[str]> A list of permissions to grant to all pages in this context. See [browserContext.grantPermissions](#browsercontextgrantpermissionspermissions-options) for more details.
        - `extraHTTPHeaders` <[Dict]<[str], [str]>> An object containing additional HTTP headers to be sent with every request. All header values must be strs.
        - `offline` <bool> Whether to emulate network being offline. Defaults to `false`.
        - `httpCredentials` <Dict> Credentials for [HTTP authentication](https://developer.mozilla.org/en-US/docs/Web/HTTP/Authentication).
          - `username` <str>
          - `password` <str>
        - `colorScheme` <"dark"|"light"|"no-preference"> Emulates `'prefers-colors-scheme'` media feature, supported values are `'light'`, `'dark'`, `'no-preference'`. See [page.emulateMedia(options)](#pageemulatemediaoptions) for more details. Defaults to '`light`'.
        - `logger` <Logger> Logger sink for Playwright logging.
        - returns: <Page>

        Creates a new page in a new browser context. Closing this page will close the context as well.

        This is a convenience API that should only be used for the single-page scenarios and short snippets. Production code and testing frameworks should explicitly create [browser.newContext](#browsernewcontextoptions) followed by the [browserContext.newPage](#browsercontextnewpage) to control their exact life times.
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
                extraHTTPHeaders=extraHTTPHeaders,
                offline=offline,
                httpCredentials=httpCredentials,
                deviceScaleFactor=deviceScaleFactor,
                isMobile=isMobile,
                hasTouch=hasTouch,
                colorScheme=colorScheme,
                acceptDownloads=acceptDownloads,
            )
        )

    async def close(self) -> NoneType:
        """
        - returns: <Promise>

        In case this browser is obtained using [browserType.launch](#browsertypelaunchoptions), closes the browser and all of its pages (if any were opened).

        In case this browser is obtained using [browserType.connect](#browsertypeconnectoptions), clears all created contexts belonging to this browser and disconnects from the browser server.

        The [Browser] object itself is considered to be disposed and cannot be used anymore.
        """
        return mapping.from_maybe_impl(await self._impl_obj.close())


mapping.register(BrowserImpl, Browser)


class BrowserServer(AsyncBase):
    def __init__(self, obj: BrowserServerImpl):
        super().__init__(obj)

    @property
    def pid(self) -> str:
        return mapping.from_maybe_impl(self._impl_obj.pid)

    @property
    def wsEndpoint(self) -> str:
        """
        - returns: <str> Browser websocket url.

        Browser websocket endpoint which can be used as an argument to [browserType.connect(options)](#browsertypeconnectoptions) to establish connection to the browser.
        """
        return mapping.from_maybe_impl(self._impl_obj.wsEndpoint)

    async def kill(self) -> NoneType:
        """
        - returns: <Promise>

        Kills the browser process and waits for the process to exit.
        """
        return mapping.from_maybe_impl(await self._impl_obj.kill())

    async def close(self) -> NoneType:
        """
        - returns: <Promise>

        Closes the browser gracefully and makes sure the process is terminated.
        """
        return mapping.from_maybe_impl(await self._impl_obj.close())


mapping.register(BrowserServerImpl, BrowserServer)


class BrowserType(AsyncBase):
    def __init__(self, obj: BrowserTypeImpl):
        super().__init__(obj)

    @property
    def name(self) -> str:
        """
        - returns: <str>

        Returns browser name. For example: `'chromium'`, `'webkit'` or `'firefox'`.
        """
        return mapping.from_maybe_impl(self._impl_obj.name)

    @property
    def executablePath(self) -> str:
        """
        - returns: <str> A path where Playwright expects to find a bundled browser executable.
        """
        return mapping.from_maybe_impl(self._impl_obj.executablePath)

    async def launch(
        self,
        executablePath: str = None,
        args: typing.List[str] = None,
        ignoreDefaultArgs: typing.List[str] = None,
        handleSIGINT: bool = None,
        handleSIGTERM: bool = None,
        handleSIGHUP: bool = None,
        timeout: int = None,
        env: typing.Dict = None,
        headless: bool = None,
        devtools: bool = None,
        proxy: typing.Dict = None,
        downloadsPath: str = None,
        slowMo: int = None,
        chromiumSandbox: bool = None,
    ) -> "Browser":
        """
        - `headless` <bool> Whether to run browser in headless mode. More details for [Chromium](https://developers.google.com/web/updates/2017/04/headless-chrome) and [Firefox](https://developer.mozilla.org/en-US/docs/Mozilla/Firefox/Headless_mode). Defaults to `true` unless the `devtools` option is `true`.
        - `executablePath` <str> Path to a browser executable to run instead of the bundled one. If `executablePath` is a relative path, then it is resolved relative to [current working directory](https://nodejs.org/api/process.html#process_process_cwd). Note that Playwright only works with the bundled Chromium, Firefox or WebKit, use at your own risk.
        - `args` <List[str]> Additional arguments to pass to the browser instance. The list of Chromium flags can be found [here](http://peter.sh/experiments/chromium-command-line-switches/).
        - `ignoreDefaultArgs` <[bool]|[List]<str>> If `true`, Playwright does not pass its own configurations args and only uses the ones from `args`. If an array is given, then filters out the given default arguments. Dangerous option; use with care. Defaults to `false`.
        - `proxy` <Dict> Network proxy settings.
          - `server` <str> Proxy to be used for all requests. HTTP and SOCKS proxies are supported, for example `http://myproxy.com:3128` or `socks5://myproxy.com:3128`. Short form `myproxy.com:3128` is considered an HTTP proxy.
          - `bypass` <str> Optional coma-separated domains to bypass proxy, for example `".com, chromium.org, .domain.com"`.
          - `username` <str> Optional username to use if HTTP proxy requires authentication.
          - `password` <str> Optional password to use if HTTP proxy requires authentication.
        - `downloadsPath` <str> If specified, accepted downloads are downloaded into this folder. Otherwise, temporary folder is created and is deleted when browser is closed.
        - `chromiumSandbox` <bool> Enable Chromium sandboxing. Defaults to `true`.
        - `handleSIGINT` <bool> Close the browser process on Ctrl-C. Defaults to `true`.
        - `handleSIGTERM` <bool> Close the browser process on SIGTERM. Defaults to `true`.
        - `handleSIGHUP` <bool> Close the browser process on SIGHUP. Defaults to `true`.
        - `timeout` <int> Maximum time in milliseconds to wait for the browser instance to start. Defaults to `30000` (30 seconds). Pass `0` to disable timeout.
        - `env` <[Dict]<[str], [str]|[int]|[bool]>> Specify environment variables that will be visible to the browser. Defaults to `process.env`.
        - `devtools` <bool> **Chromium-only** Whether to auto-open a Developer Tools panel for each tab. If this option is `true`, the `headless` option will be set `false`.
        - `slowMo` <int> Slows down Playwright operations by the specified amount of milliseconds. Useful so that you can see what is going on.
        - returns: <Browser> Promise which resolves to browser instance.

        You can use `ignoreDefaultArgs` to filter out `--mute-audio` from default arguments:

        > **Chromium-only** Playwright can also be used to control the Chrome browser, but it works best with the version of Chromium it is bundled with. There is no guarantee it will work with any other version. Use `executablePath` option with extreme caution.
        >
        > If Google Chrome (rather than Chromium) is preferred, a [Chrome Canary](https://www.google.com/chrome/browser/canary.html) or [Dev Channel](https://www.chromium.org/getting-involved/dev-channel) build is suggested.
        >
        > In [browserType.launch([options])](#browsertypelaunchoptions) above, any mention of Chromium also applies to Chrome.
        >
        > See [`this article`](https://www.howtogeek.com/202825/what%E2%80%99s-the-difference-between-chromium-and-chrome/) for a description of the differences between Chromium and Chrome. [`This article`](https://chromium.googlesource.com/chromium/src/+/lkgr/docs/chromium_browser_vs_google_chrome.md) describes some differences for Linux users.
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
                env=env,
                headless=headless,
                devtools=devtools,
                proxy=proxy,
                downloadsPath=downloadsPath,
                slowMo=slowMo,
                chromiumSandbox=chromiumSandbox,
            )
        )

    async def launchServer(
        self,
        executablePath: str = None,
        args: typing.List[str] = None,
        ignoreDefaultArgs: typing.List[str] = None,
        handleSIGINT: bool = None,
        handleSIGTERM: bool = None,
        handleSIGHUP: bool = None,
        timeout: int = None,
        env: typing.Dict = None,
        headless: bool = None,
        devtools: bool = None,
        proxy: typing.Dict = None,
        downloadsPath: str = None,
        port: int = None,
        chromiumSandbox: bool = None,
    ) -> "Browser":
        """
        - `headless` <bool> Whether to run browser in headless mode. More details for [Chromium](https://developers.google.com/web/updates/2017/04/headless-chrome) and [Firefox](https://developer.mozilla.org/en-US/docs/Mozilla/Firefox/Headless_mode). Defaults to `true` unless the `devtools` option is `true`.
        - `port` <int> Port to use for the web socket. Defaults to 0 that picks any available port.
        - `executablePath` <str> Path to a browser executable to run instead of the bundled one. If `executablePath` is a relative path, then it is resolved relative to [current working directory](https://nodejs.org/api/process.html#process_process_cwd). **BEWARE**: Playwright is only guaranteed to work with the bundled Chromium, Firefox or WebKit, use at your own risk.
        - `args` <List[str]> Additional arguments to pass to the browser instance. The list of Chromium flags can be found [here](http://peter.sh/experiments/chromium-command-line-switches/).
        - `ignoreDefaultArgs` <[bool]|[List]<str>> If `true`, then do not use any of the default arguments. If an array is given, then filter out the given default arguments. Dangerous option; use with care. Defaults to `false`.
        - `proxy` <Dict> Network proxy settings.
          - `server` <str> Proxy to be used for all requests. HTTP and SOCKS proxies are supported, for example `http://myproxy.com:3128` or `socks5://myproxy.com:3128`. Short form `myproxy.com:3128` is considered an HTTP proxy.
          - `bypass` <str> Optional coma-separated domains to bypass proxy, for example `".com, chromium.org, .domain.com"`.
          - `username` <str> Optional username to use if HTTP proxy requires authentication.
          - `password` <str> Optional password to use if HTTP proxy requires authentication.
        - `downloadsPath` <str> If specified, accepted downloads are downloaded into this folder. Otherwise, temporary folder is created and is deleted when browser is closed.
        - `chromiumSandbox` <bool> Enable Chromium sandboxing. Defaults to `true`.
        - `handleSIGINT` <bool> Close the browser process on Ctrl-C. Defaults to `true`.
        - `handleSIGTERM` <bool> Close the browser process on SIGTERM. Defaults to `true`.
        - `handleSIGHUP` <bool> Close the browser process on SIGHUP. Defaults to `true`.
        - `timeout` <int> Maximum time in milliseconds to wait for the browser instance to start. Defaults to `30000` (30 seconds). Pass `0` to disable timeout.
        - `env` <[Dict]<[str], [str]|[int]|[bool]>> Specify environment variables that will be visible to the browser. Defaults to `process.env`.
        - `devtools` <bool> **Chromium-only** Whether to auto-open a Developer Tools panel for each tab. If this option is `true`, the `headless` option will be set `false`.
        - returns: <BrowserServer> Promise which resolves to the browser app instance.

        Launches browser server that client can connect to. An example of launching a browser executable and connecting to it later:
        """
        return mapping.from_impl(
            await self._impl_obj.launchServer(
                executablePath=executablePath,
                args=args,
                ignoreDefaultArgs=ignoreDefaultArgs,
                handleSIGINT=handleSIGINT,
                handleSIGTERM=handleSIGTERM,
                handleSIGHUP=handleSIGHUP,
                timeout=timeout,
                env=env,
                headless=headless,
                devtools=devtools,
                proxy=proxy,
                downloadsPath=downloadsPath,
                port=port,
                chromiumSandbox=chromiumSandbox,
            )
        )

    async def launchPersistentContext(
        self,
        userDataDir: str,
        executablePath: str = None,
        args: typing.List[str] = None,
        ignoreDefaultArgs: typing.List[str] = None,
        handleSIGINT: bool = None,
        handleSIGTERM: bool = None,
        handleSIGHUP: bool = None,
        timeout: int = None,
        env: typing.Dict = None,
        headless: bool = None,
        devtools: bool = None,
        proxy: typing.Dict = None,
        downloadsPath: str = None,
        slowMo: int = None,
        viewport: typing.Dict = None,
        ignoreHTTPSErrors: bool = None,
        javaScriptEnabled: bool = None,
        bypassCSP: bool = None,
        userAgent: str = None,
        locale: str = None,
        timezoneId: str = None,
        geolocation: typing.Dict = None,
        permissions: typing.List[str] = None,
        extraHTTPHeaders: typing.Union[typing.Dict[str, str]] = None,
        offline: bool = None,
        httpCredentials: typing.Dict = None,
        deviceScaleFactor: int = None,
        isMobile: bool = None,
        hasTouch: bool = None,
        colorScheme: Literal["light", "dark", "no-preference"] = None,
        acceptDownloads: bool = None,
    ) -> "BrowserContext":
        """
         - `userDataDir` <str> Path to a User Data Directory, which stores browser session data like cookies and local storage. More details for [Chromium](https://chromium.googlesource.com/chromium/src/+/master/docs/user_data_dir.md) and [Firefox](https://developer.mozilla.org/en-US/docs/Mozilla/Command_Line_Options#User_Profile).
        - `headless` <bool> Whether to run browser in headless mode. More details for [Chromium](https://developers.google.com/web/updates/2017/04/headless-chrome) and [Firefox](https://developer.mozilla.org/en-US/docs/Mozilla/Firefox/Headless_mode). Defaults to `true` unless the `devtools` option is `true`.
        - `executablePath` <str> Path to a browser executable to run instead of the bundled one. If `executablePath` is a relative path, then it is resolved relative to [current working directory](https://nodejs.org/api/process.html#process_process_cwd). **BEWARE**: Playwright is only guaranteed to work with the bundled Chromium, Firefox or WebKit, use at your own risk.
        - `args` <List[str]> Additional arguments to pass to the browser instance. The list of Chromium flags can be found [here](http://peter.sh/experiments/chromium-command-line-switches/).
        - `ignoreDefaultArgs` <[bool]|[List]<str>> If `true`, then do not use any of the default arguments. If an array is given, then filter out the given default arguments. Dangerous option; use with care. Defaults to `false`.
        - `proxy` <Dict> Network proxy settings.
          - `server` <str> Proxy to be used for all requests. HTTP and SOCKS proxies are supported, for example `http://myproxy.com:3128` or `socks5://myproxy.com:3128`. Short form `myproxy.com:3128` is considered an HTTP proxy.
          - `bypass` <str> Optional coma-separated domains to bypass proxy, for example `".com, chromium.org, .domain.com"`.
          - `username` <str> Optional username to use if HTTP proxy requires authentication.
          - `password` <str> Optional password to use if HTTP proxy requires authentication.
        - `acceptDownloads` <bool> Whether to automatically download all the attachments. Defaults to `false` where all the downloads are canceled.
        - `downloadsPath` <str> If specified, accepted downloads are downloaded into this folder. Otherwise, temporary folder is created and is deleted when browser is closed.
        - `handleSIGINT` <bool> Close the browser process on Ctrl-C. Defaults to `true`.
        - `handleSIGTERM` <bool> Close the browser process on SIGTERM. Defaults to `true`.
        - `handleSIGHUP` <bool> Close the browser process on SIGHUP. Defaults to `true`.
        - `timeout` <int> Maximum time in milliseconds to wait for the browser instance to start. Defaults to `30000` (30 seconds). Pass `0` to disable timeout.
        - `env` <[Dict]<[str], [str]|[int]|[bool]>> Specify environment variables that will be visible to the browser. Defaults to `process.env`.
        - `devtools` <bool> **Chromium-only** Whether to auto-open a Developer Tools panel for each tab. If this option is `true`, the `headless` option will be set `false`.
        - `slowMo` <int> Slows down Playwright operations by the specified amount of milliseconds. Useful so that you can see what is going on. Defaults to 0.
        - `ignoreHTTPSErrors` <bool> Whether to ignore HTTPS errors during navigation. Defaults to `false`.
        - `bypassCSP` <bool> Toggles bypassing page's Content-Security-Policy.
        - `viewport` <Optional[Dict]> Sets a consistent viewport for each page. Defaults to an 1280x720 viewport. `null` disables the default viewport.
          - `width` <int> page width in pixels.
          - `height` <int> page height in pixels.
        - `userAgent` <str> Specific user agent to use in this context.
        - `deviceScaleFactor` <int> Specify device scale factor (can be thought of as dpr). Defaults to `1`.
        - `isMobile` <bool> Whether the `meta viewport` tag is taken into account and touch events are enabled. Defaults to `false`. Not supported in Firefox.
        - `hasTouch` <bool> Specifies if viewport supports touch events. Defaults to false.
        - `javaScriptEnabled` <bool> Whether or not to enable JavaScript in the context. Defaults to true.
        - `timezoneId` <str> Changes the timezone of the context. See [ICU’s `metaZones.txt`](https://cs.chromium.org/chromium/src/third_party/icu/source/data/misc/metaZones.txt?rcl=faee8bc70570192d82d2978a71e2a615788597d1) for a list of supported timezone IDs.
        - `geolocation` <Dict>
          - `latitude` <int> Latitude between -90 and 90.
          - `longitude` <int> Longitude between -180 and 180.
          - `accuracy` <int> Non-negative accuracy value. Defaults to `0`.
        - `locale` <str> Specify user locale, for example `en-GB`, `de-DE`, etc. Locale will affect `navigator.language` value, `Accept-Language` request header value as well as int and date formatting rules.
        - `permissions` <List[str]> A list of permissions to grant to all pages in this context. See [browserContext.grantPermissions](#browsercontextgrantpermissionspermissions-options) for more details.
        - `extraHTTPHeaders` <[Dict]<[str], [str]>> An object containing additional HTTP headers to be sent with every request. All header values must be strs.
        - `offline` <bool> Whether to emulate network being offline. Defaults to `false`.
        - `httpCredentials` <Dict> Credentials for [HTTP authentication](https://developer.mozilla.org/en-US/docs/Web/HTTP/Authentication).
          - `username` <str>
          - `password` <str>
        - `colorScheme` <"dark"|"light"|"no-preference"> Emulates `'prefers-colors-scheme'` media feature, supported values are `'light'`, `'dark'`, `'no-preference'`. See [page.emulateMedia(options)](#pageemulatemediaoptions) for more details. Defaults to '`light`'.
        - returns: <BrowserContext> Promise that resolves to the persistent browser context instance.

        Launches browser that uses persistent storage located at `userDataDir` and returns the only context. Closing this context will automatically close the browser.
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
                env=env,
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
                extraHTTPHeaders=extraHTTPHeaders,
                offline=offline,
                httpCredentials=httpCredentials,
                deviceScaleFactor=deviceScaleFactor,
                isMobile=isMobile,
                hasTouch=hasTouch,
                colorScheme=colorScheme,
                acceptDownloads=acceptDownloads,
            )
        )

    async def connect(
        self, wsEndpoint: str = None, slowMo: int = None, timeout: int = None
    ) -> "Browser":
        """
        - `wsEndpoint` <str> A browser websocket endpoint to connect to. **required**
        - `slowMo` <int> Slows down Playwright operations by the specified amount of milliseconds. Useful so that you can see what is going on. Defaults to 0.
        - `timeout` <int> Maximum time in milliseconds to wait for the connection to be established. Defaults to `30000` (30 seconds). Pass `0` to disable timeout.
        - returns: <Browser>

        This methods attaches Playwright to an existing browser instance.
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
        """
        - returns: <BrowserType>

        This object can be used to launch or connect to Chromium, returning instances of [ChromiumBrowser].
        """
        return mapping.from_impl(self._impl_obj.chromium)

    @property
    def firefox(self) -> "BrowserType":
        """
        - returns: <BrowserType>

        This object can be used to launch or connect to Firefox, returning instances of [FirefoxBrowser].
        """
        return mapping.from_impl(self._impl_obj.firefox)

    @property
    def webkit(self) -> "BrowserType":
        """
        - returns: <BrowserType>

        This object can be used to launch or connect to WebKit, returning instances of [WebKitBrowser].
        """
        return mapping.from_impl(self._impl_obj.webkit)

    @property
    def selectors(self) -> "Selectors":
        """
        - returns: <Selectors>

        Selectors can be used to install custom selector engines. See [Working with selectors](#working-with-selectors) for more information.
        """
        return mapping.from_impl(self._impl_obj.selectors)

    @property
    def devices(self) -> typing.Dict[str, DeviceDescriptor]:
        """
        - returns: <Dict>

        Returns a list of devices to be used with [`browser.newContext([options])`](#browsernewcontextoptions) or [`browser.newPage([options])`](#browsernewpageoptions). Actual list of devices can be found in [src/deviceDescriptors.ts](https://github.com/Microsoft/playwright/blob/master/src/deviceDescriptors.ts).
        """
        return mapping.from_maybe_impl(self._impl_obj.devices)


mapping.register(PlaywrightImpl, Playwright)
