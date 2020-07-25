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

from playwright.sync_base import EventContextManager, SyncBase, mapping

if sys.version_info >= (3, 8):  # pragma: no cover
    from typing import Literal
else:  # pragma: no cover
    from typing_extensions import Literal

from playwright.accessibility import Accessibility as AccessibilityAsync
from playwright.browser import Browser as BrowserAsync
from playwright.browser_context import BrowserContext as BrowserContextAsync
from playwright.browser_server import BrowserServer as BrowserServerAsync
from playwright.browser_type import BrowserType as BrowserTypeAsync
from playwright.console_message import ConsoleMessage as ConsoleMessageAsync
from playwright.dialog import Dialog as DialogAsync
from playwright.download import Download as DownloadAsync
from playwright.element_handle import ElementHandle as ElementHandleAsync
from playwright.file_chooser import FileChooser as FileChooserAsync
from playwright.frame import Frame as FrameAsync
from playwright.helper import (
    ConsoleMessageLocation,
    DeviceDescriptor,
    Error,
    FilePayload,
    SelectOption,
    Viewport,
)
from playwright.input import Keyboard as KeyboardAsync
from playwright.input import Mouse as MouseAsync
from playwright.js_handle import JSHandle as JSHandleAsync
from playwright.network import Request as RequestAsync
from playwright.network import Response as ResponseAsync
from playwright.network import Route as RouteAsync
from playwright.page import BindingCall as BindingCallAsync
from playwright.page import Page as PageAsync
from playwright.playwright import Playwright as PlaywrightAsync
from playwright.selectors import Selectors as SelectorsAsync
from playwright.worker import Worker as WorkerAsync

NoneType = type(None)


class Request(SyncBase):
    def __init__(self, obj: RequestAsync):
        super().__init__(obj)

    def as_async(self) -> RequestAsync:
        return self._async_obj

    @classmethod
    def _from_async(cls, obj: RequestAsync) -> "Request":
        if not obj._sync_owner:
            obj._sync_owner = cls(obj)
        return obj._sync_owner

    @classmethod
    def _from_async_nullable(
        cls, obj: RequestAsync = None
    ) -> typing.Optional["Request"]:
        return Request._from_async(obj) if obj else None

    @classmethod
    def _from_async_list(
        cls, items: typing.List[RequestAsync]
    ) -> typing.List["Request"]:
        return list(map(lambda a: Request._from_async(a), items))

    @classmethod
    def _from_async_dict(
        cls, map: typing.Dict[str, RequestAsync]
    ) -> typing.Dict[str, "Request"]:
        return {name: Request._from_async(value) for name, value in map.items()}

    @property
    def url(self) -> str:
        return self._async_obj.url

    @property
    def resourceType(self) -> str:
        return self._async_obj.resourceType

    @property
    def method(self) -> str:
        return self._async_obj.method

    @property
    def postData(self) -> typing.Union[str, NoneType]:
        return self._async_obj.postData

    @property
    def headers(self) -> typing.Dict[str, str]:
        return self._async_obj.headers

    @property
    def frame(self) -> "Frame":
        return Frame._from_async(self._async_obj.frame)

    @property
    def redirectedFrom(self) -> typing.Union["Request", NoneType]:
        return Request._from_async_nullable(self._async_obj.redirectedFrom)

    @property
    def redirectedTo(self) -> typing.Union["Request", NoneType]:
        return Request._from_async_nullable(self._async_obj.redirectedTo)

    @property
    def failure(self) -> typing.Union[str, NoneType]:
        return self._async_obj.failure

    def response(self) -> typing.Union["Response", NoneType]:
        return Response._from_async_nullable(self._sync(self._async_obj.response()))

    def isNavigationRequest(self) -> bool:
        return self._sync(self._async_obj.isNavigationRequest())


mapping.register(RequestAsync, Request)


class Response(SyncBase):
    def __init__(self, obj: ResponseAsync):
        super().__init__(obj)

    def as_async(self) -> ResponseAsync:
        return self._async_obj

    @classmethod
    def _from_async(cls, obj: ResponseAsync) -> "Response":
        if not obj._sync_owner:
            obj._sync_owner = cls(obj)
        return obj._sync_owner

    @classmethod
    def _from_async_nullable(
        cls, obj: ResponseAsync = None
    ) -> typing.Optional["Response"]:
        return Response._from_async(obj) if obj else None

    @classmethod
    def _from_async_list(
        cls, items: typing.List[ResponseAsync]
    ) -> typing.List["Response"]:
        return list(map(lambda a: Response._from_async(a), items))

    @classmethod
    def _from_async_dict(
        cls, map: typing.Dict[str, ResponseAsync]
    ) -> typing.Dict[str, "Response"]:
        return {name: Response._from_async(value) for name, value in map.items()}

    @property
    def url(self) -> str:
        return self._async_obj.url

    @property
    def ok(self) -> bool:
        return self._async_obj.ok

    @property
    def status(self) -> int:
        return self._async_obj.status

    @property
    def statusText(self) -> str:
        return self._async_obj.statusText

    @property
    def headers(self) -> typing.Dict[str, str]:
        return self._async_obj.headers

    @property
    def request(self) -> "Request":
        return Request._from_async(self._async_obj.request)

    @property
    def frame(self) -> "Frame":
        return Frame._from_async(self._async_obj.frame)

    def finished(self) -> typing.Union[Error, NoneType]:
        return self._sync(self._async_obj.finished())

    def body(self) -> bytes:
        return self._sync(self._async_obj.body())

    def text(self) -> str:
        return self._sync(self._async_obj.text())

    def json(self) -> typing.Union[typing.Dict, typing.List]:
        return self._sync(self._async_obj.json())


mapping.register(ResponseAsync, Response)


class Route(SyncBase):
    def __init__(self, obj: RouteAsync):
        super().__init__(obj)

    def as_async(self) -> RouteAsync:
        return self._async_obj

    @classmethod
    def _from_async(cls, obj: RouteAsync) -> "Route":
        if not obj._sync_owner:
            obj._sync_owner = cls(obj)
        return obj._sync_owner

    @classmethod
    def _from_async_nullable(cls, obj: RouteAsync = None) -> typing.Optional["Route"]:
        return Route._from_async(obj) if obj else None

    @classmethod
    def _from_async_list(cls, items: typing.List[RouteAsync]) -> typing.List["Route"]:
        return list(map(lambda a: Route._from_async(a), items))

    @classmethod
    def _from_async_dict(
        cls, map: typing.Dict[str, RouteAsync]
    ) -> typing.Dict[str, "Route"]:
        return {name: Route._from_async(value) for name, value in map.items()}

    @property
    def request(self) -> "Request":
        return Request._from_async(self._async_obj.request)

    def abort(self, error_code: str = "failed") -> NoneType:
        return self._sync(self._async_obj.abort(error_code=error_code))

    def fulfill(
        self,
        status: int = 200,
        headers: typing.Dict[str, str] = {},
        body: typing.Union[str, bytes] = None,
        contentType: str = None,
    ) -> NoneType:
        return self._sync(
            self._async_obj.fulfill(
                status=status, headers=headers, body=body, contentType=contentType
            )
        )

    def continue_(
        self,
        method: str = None,
        headers: typing.Union[typing.Dict[str, str]] = None,
        postData: typing.Union[str, bytes] = None,
    ) -> NoneType:
        return self._sync(
            self._async_obj.continue_(method=method, headers=headers, postData=postData)
        )


mapping.register(RouteAsync, Route)


class Keyboard(SyncBase):
    def __init__(self, obj: KeyboardAsync):
        super().__init__(obj)

    def as_async(self) -> KeyboardAsync:
        return self._async_obj

    @classmethod
    def _from_async(cls, obj: KeyboardAsync) -> "Keyboard":
        if not obj._sync_owner:
            obj._sync_owner = cls(obj)
        return obj._sync_owner

    @classmethod
    def _from_async_nullable(
        cls, obj: KeyboardAsync = None
    ) -> typing.Optional["Keyboard"]:
        return Keyboard._from_async(obj) if obj else None

    @classmethod
    def _from_async_list(
        cls, items: typing.List[KeyboardAsync]
    ) -> typing.List["Keyboard"]:
        return list(map(lambda a: Keyboard._from_async(a), items))

    @classmethod
    def _from_async_dict(
        cls, map: typing.Dict[str, KeyboardAsync]
    ) -> typing.Dict[str, "Keyboard"]:
        return {name: Keyboard._from_async(value) for name, value in map.items()}

    def down(self, key: str) -> NoneType:
        return self._sync(self._async_obj.down(key=key))

    def up(self, key: str) -> NoneType:
        return self._sync(self._async_obj.up(key=key))

    def insertText(self, text: str) -> NoneType:
        return self._sync(self._async_obj.insertText(text=text))

    def type(self, text: str, delay: int = None) -> NoneType:
        return self._sync(self._async_obj.type(text=text, delay=delay))

    def press(self, key: str, delay: int = None) -> NoneType:
        return self._sync(self._async_obj.press(key=key, delay=delay))


mapping.register(KeyboardAsync, Keyboard)


class Mouse(SyncBase):
    def __init__(self, obj: MouseAsync):
        super().__init__(obj)

    def as_async(self) -> MouseAsync:
        return self._async_obj

    @classmethod
    def _from_async(cls, obj: MouseAsync) -> "Mouse":
        if not obj._sync_owner:
            obj._sync_owner = cls(obj)
        return obj._sync_owner

    @classmethod
    def _from_async_nullable(cls, obj: MouseAsync = None) -> typing.Optional["Mouse"]:
        return Mouse._from_async(obj) if obj else None

    @classmethod
    def _from_async_list(cls, items: typing.List[MouseAsync]) -> typing.List["Mouse"]:
        return list(map(lambda a: Mouse._from_async(a), items))

    @classmethod
    def _from_async_dict(
        cls, map: typing.Dict[str, MouseAsync]
    ) -> typing.Dict[str, "Mouse"]:
        return {name: Mouse._from_async(value) for name, value in map.items()}

    def move(self, x: float, y: float, steps: int = None) -> NoneType:
        return self._sync(self._async_obj.move(x=x, y=y, steps=steps))

    def down(
        self, button: Literal["left", "right", "middle"] = None, clickCount: int = None
    ) -> NoneType:
        return self._sync(self._async_obj.down(button=button, clickCount=clickCount))

    def up(
        self, button: Literal["left", "right", "middle"] = None, clickCount: int = None
    ) -> NoneType:
        return self._sync(self._async_obj.up(button=button, clickCount=clickCount))

    def click(
        self,
        x: float,
        y: float,
        delay: int = None,
        button: Literal["left", "right", "middle"] = None,
        clickCount: int = None,
    ) -> NoneType:
        return self._sync(
            self._async_obj.click(
                x=x, y=y, delay=delay, button=button, clickCount=clickCount
            )
        )

    def dblclick(
        self,
        x: float,
        y: float,
        delay: int = None,
        button: Literal["left", "right", "middle"] = None,
    ) -> NoneType:
        return self._sync(
            self._async_obj.dblclick(x=x, y=y, delay=delay, button=button)
        )


mapping.register(MouseAsync, Mouse)


class JSHandle(SyncBase):
    def __init__(self, obj: JSHandleAsync):
        super().__init__(obj)

    def as_async(self) -> JSHandleAsync:
        return self._async_obj

    @classmethod
    def _from_async(cls, obj: JSHandleAsync) -> "JSHandle":
        if not obj._sync_owner:
            obj._sync_owner = cls(obj)
        return obj._sync_owner

    @classmethod
    def _from_async_nullable(
        cls, obj: JSHandleAsync = None
    ) -> typing.Optional["JSHandle"]:
        return JSHandle._from_async(obj) if obj else None

    @classmethod
    def _from_async_list(
        cls, items: typing.List[JSHandleAsync]
    ) -> typing.List["JSHandle"]:
        return list(map(lambda a: JSHandle._from_async(a), items))

    @classmethod
    def _from_async_dict(
        cls, map: typing.Dict[str, JSHandleAsync]
    ) -> typing.Dict[str, "JSHandle"]:
        return {name: JSHandle._from_async(value) for name, value in map.items()}

    def evaluate(
        self, expression: str, arg: typing.Any = None, force_expr: bool = False
    ) -> typing.Any:
        return self._sync(
            self._async_obj.evaluate(
                expression=expression, arg=arg, force_expr=force_expr
            )
        )

    def evaluateHandle(
        self, expression: str, arg: typing.Any = None, force_expr: bool = False
    ) -> "JSHandle":
        return JSHandle._from_async(
            self._sync(
                self._async_obj.evaluateHandle(
                    expression=expression, arg=arg, force_expr=force_expr
                )
            )
        )

    def getProperty(self, name: str) -> "JSHandle":
        return JSHandle._from_async(self._sync(self._async_obj.getProperty(name=name)))

    def getProperties(self) -> typing.Dict[str, "JSHandle"]:
        return JSHandle._from_async_dict(self._sync(self._async_obj.getProperties()))

    def asElement(self) -> typing.Union["ElementHandle", NoneType]:
        return ElementHandle._from_async_nullable(
            self._sync(self._async_obj.asElement())
        )

    def dispose(self) -> NoneType:
        return self._sync(self._async_obj.dispose())

    def jsonValue(self) -> typing.Any:
        return self._sync(self._async_obj.jsonValue())


mapping.register(JSHandleAsync, JSHandle)


class ElementHandle(SyncBase):
    def __init__(self, obj: ElementHandleAsync):
        super().__init__(obj)

    def as_async(self) -> ElementHandleAsync:
        return self._async_obj

    @classmethod
    def _from_async(cls, obj: ElementHandleAsync) -> "ElementHandle":
        if not obj._sync_owner:
            obj._sync_owner = cls(obj)
        return obj._sync_owner

    @classmethod
    def _from_async_nullable(
        cls, obj: ElementHandleAsync = None
    ) -> typing.Optional["ElementHandle"]:
        return ElementHandle._from_async(obj) if obj else None

    @classmethod
    def _from_async_list(
        cls, items: typing.List[ElementHandleAsync]
    ) -> typing.List["ElementHandle"]:
        return list(map(lambda a: ElementHandle._from_async(a), items))

    @classmethod
    def _from_async_dict(
        cls, map: typing.Dict[str, ElementHandleAsync]
    ) -> typing.Dict[str, "ElementHandle"]:
        return {name: ElementHandle._from_async(value) for name, value in map.items()}

    def asElement(self) -> typing.Union["ElementHandle", NoneType]:
        return ElementHandle._from_async_nullable(
            self._sync(self._async_obj.asElement())
        )

    def ownerFrame(self) -> typing.Union["Frame", NoneType]:
        return Frame._from_async_nullable(self._sync(self._async_obj.ownerFrame()))

    def contentFrame(self) -> typing.Union["Frame", NoneType]:
        return Frame._from_async_nullable(self._sync(self._async_obj.contentFrame()))

    def getAttribute(self, name: str) -> str:
        return self._sync(self._async_obj.getAttribute(name=name))

    def textContent(self) -> str:
        return self._sync(self._async_obj.textContent())

    def innerText(self) -> str:
        return self._sync(self._async_obj.innerText())

    def innerHTML(self) -> str:
        return self._sync(self._async_obj.innerHTML())

    def dispatchEvent(self, type: str, eventInit: typing.Dict = None) -> NoneType:
        return self._sync(self._async_obj.dispatchEvent(type=type, eventInit=eventInit))

    def scrollIntoViewIfNeeded(self, timeout: int = None) -> NoneType:
        return self._sync(self._async_obj.scrollIntoViewIfNeeded(timeout=timeout))

    def hover(
        self,
        modifiers: typing.Union[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: typing.Dict = None,
        timeout: int = None,
        force: bool = None,
    ) -> NoneType:
        return self._sync(
            self._async_obj.hover(
                modifiers=modifiers, position=position, timeout=timeout, force=force
            )
        )

    def click(
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
        return self._sync(
            self._async_obj.click(
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

    def dblclick(
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
        return self._sync(
            self._async_obj.dblclick(
                modifiers=modifiers,
                position=position,
                delay=delay,
                button=button,
                timeout=timeout,
                force=force,
                noWaitAfter=noWaitAfter,
            )
        )

    def selectOption(
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
        return self._sync(
            self._async_obj.selectOption(
                values=values, timeout=timeout, noWaitAfter=noWaitAfter
            )
        )

    def fill(
        self, value: str, timeout: int = None, noWaitAfter: bool = None
    ) -> NoneType:
        return self._sync(
            self._async_obj.fill(value=value, timeout=timeout, noWaitAfter=noWaitAfter)
        )

    def selectText(self, timeout: int = None) -> NoneType:
        return self._sync(self._async_obj.selectText(timeout=timeout))

    def setInputFiles(
        self,
        files: typing.Union[
            str, FilePayload, typing.List[str], typing.List[FilePayload]
        ],
        timeout: int = None,
        noWaitAfter: bool = None,
    ) -> NoneType:
        return self._sync(
            self._async_obj.setInputFiles(
                files=files, timeout=timeout, noWaitAfter=noWaitAfter
            )
        )

    def focus(self) -> NoneType:
        return self._sync(self._async_obj.focus())

    def type(
        self,
        text: str,
        delay: int = None,
        timeout: int = None,
        noWaitAfter: bool = None,
    ) -> NoneType:
        return self._sync(
            self._async_obj.type(
                text=text, delay=delay, timeout=timeout, noWaitAfter=noWaitAfter
            )
        )

    def press(
        self, key: str, delay: int = None, timeout: int = None, noWaitAfter: bool = None
    ) -> NoneType:
        return self._sync(
            self._async_obj.press(
                key=key, delay=delay, timeout=timeout, noWaitAfter=noWaitAfter
            )
        )

    def check(
        self, timeout: int = None, force: bool = None, noWaitAfter: bool = None
    ) -> NoneType:
        return self._sync(
            self._async_obj.check(timeout=timeout, force=force, noWaitAfter=noWaitAfter)
        )

    def uncheck(
        self, timeout: int = None, force: bool = None, noWaitAfter: bool = None
    ) -> NoneType:
        return self._sync(
            self._async_obj.uncheck(
                timeout=timeout, force=force, noWaitAfter=noWaitAfter
            )
        )

    def boundingBox(self) -> typing.Dict[str, float]:
        return self._sync(self._async_obj.boundingBox())

    def screenshot(
        self,
        timeout: int = None,
        type: Literal["png", "jpeg"] = None,
        path: str = None,
        quality: int = None,
        omitBackground: bool = None,
    ) -> bytes:
        return self._sync(
            self._async_obj.screenshot(
                timeout=timeout,
                type=type,
                path=path,
                quality=quality,
                omitBackground=omitBackground,
            )
        )

    def querySelector(self, selector: str) -> typing.Union["ElementHandle", NoneType]:
        return ElementHandle._from_async_nullable(
            self._sync(self._async_obj.querySelector(selector=selector))
        )

    def querySelectorAll(self, selector: str) -> typing.List["ElementHandle"]:
        return ElementHandle._from_async_list(
            self._sync(self._async_obj.querySelectorAll(selector=selector))
        )

    def evalOnSelector(
        self,
        selector: str,
        expression: str,
        arg: typing.Any = None,
        force_expr: bool = False,
    ) -> typing.Any:
        return self._sync(
            self._async_obj.evalOnSelector(
                selector=selector, expression=expression, arg=arg, force_expr=force_expr
            )
        )

    def evalOnSelectorAll(
        self,
        selector: str,
        expression: str,
        arg: typing.Any = None,
        force_expr: bool = False,
    ) -> typing.Any:
        return self._sync(
            self._async_obj.evalOnSelectorAll(
                selector=selector, expression=expression, arg=arg, force_expr=force_expr
            )
        )


mapping.register(ElementHandleAsync, ElementHandle)


class Accessibility(SyncBase):
    def __init__(self, obj: AccessibilityAsync):
        super().__init__(obj)

    def as_async(self) -> AccessibilityAsync:
        return self._async_obj

    @classmethod
    def _from_async(cls, obj: AccessibilityAsync) -> "Accessibility":
        if not obj._sync_owner:
            obj._sync_owner = cls(obj)
        return obj._sync_owner

    @classmethod
    def _from_async_nullable(
        cls, obj: AccessibilityAsync = None
    ) -> typing.Optional["Accessibility"]:
        return Accessibility._from_async(obj) if obj else None

    @classmethod
    def _from_async_list(
        cls, items: typing.List[AccessibilityAsync]
    ) -> typing.List["Accessibility"]:
        return list(map(lambda a: Accessibility._from_async(a), items))

    @classmethod
    def _from_async_dict(
        cls, map: typing.Dict[str, AccessibilityAsync]
    ) -> typing.Dict[str, "Accessibility"]:
        return {name: Accessibility._from_async(value) for name, value in map.items()}

    def snapshot(
        self, interestingOnly: bool = True, root: "ElementHandle" = None
    ) -> typing.Union[typing.Dict[str, typing.Any], NoneType]:
        return self._sync(
            self._async_obj.snapshot(interestingOnly=interestingOnly, root=root)
        )


mapping.register(AccessibilityAsync, Accessibility)


class FileChooser(SyncBase):
    def __init__(self, obj: FileChooserAsync):
        super().__init__(obj)

    def as_async(self) -> FileChooserAsync:
        return self._async_obj

    @classmethod
    def _from_async(cls, obj: FileChooserAsync) -> "FileChooser":
        if not obj._sync_owner:
            obj._sync_owner = cls(obj)
        return obj._sync_owner

    @classmethod
    def _from_async_nullable(
        cls, obj: FileChooserAsync = None
    ) -> typing.Optional["FileChooser"]:
        return FileChooser._from_async(obj) if obj else None

    @classmethod
    def _from_async_list(
        cls, items: typing.List[FileChooserAsync]
    ) -> typing.List["FileChooser"]:
        return list(map(lambda a: FileChooser._from_async(a), items))

    @classmethod
    def _from_async_dict(
        cls, map: typing.Dict[str, FileChooserAsync]
    ) -> typing.Dict[str, "FileChooser"]:
        return {name: FileChooser._from_async(value) for name, value in map.items()}

    @property
    def page(self) -> "Page":
        return Page._from_async(self._async_obj.page)

    @property
    def element(self) -> "ElementHandle":
        return ElementHandle._from_async(self._async_obj.element)

    @property
    def isMultiple(self) -> bool:
        return self._async_obj.isMultiple

    def setFiles(
        self,
        files: typing.Union[
            str, FilePayload, typing.List[str], typing.List[FilePayload]
        ],
        timeout: int = None,
        noWaitAfter: bool = None,
    ) -> NoneType:
        return self._sync(
            self._async_obj.setFiles(
                files=files, timeout=timeout, noWaitAfter=noWaitAfter
            )
        )


mapping.register(FileChooserAsync, FileChooser)


class Frame(SyncBase):
    def __init__(self, obj: FrameAsync):
        super().__init__(obj)

    def as_async(self) -> FrameAsync:
        return self._async_obj

    @classmethod
    def _from_async(cls, obj: FrameAsync) -> "Frame":
        if not obj._sync_owner:
            obj._sync_owner = cls(obj)
        return obj._sync_owner

    @classmethod
    def _from_async_nullable(cls, obj: FrameAsync = None) -> typing.Optional["Frame"]:
        return Frame._from_async(obj) if obj else None

    @classmethod
    def _from_async_list(cls, items: typing.List[FrameAsync]) -> typing.List["Frame"]:
        return list(map(lambda a: Frame._from_async(a), items))

    @classmethod
    def _from_async_dict(
        cls, map: typing.Dict[str, FrameAsync]
    ) -> typing.Dict[str, "Frame"]:
        return {name: Frame._from_async(value) for name, value in map.items()}

    @property
    def name(self) -> str:
        return self._async_obj.name

    @property
    def url(self) -> str:
        return self._async_obj.url

    @property
    def parentFrame(self) -> typing.Union["Frame", NoneType]:
        return Frame._from_async_nullable(self._async_obj.parentFrame)

    @property
    def childFrames(self) -> typing.List["Frame"]:
        return Frame._from_async_list(self._async_obj.childFrames)

    def goto(
        self,
        url: str,
        timeout: int = None,
        waitUntil: Literal["load", "domcontentloaded", "networkidle"] = "load",
        referer: str = None,
    ) -> typing.Union["Response", NoneType]:
        return Response._from_async_nullable(
            self._sync(
                self._async_obj.goto(
                    url=url, timeout=timeout, waitUntil=waitUntil, referer=referer
                )
            )
        )

    def waitForNavigation(
        self,
        timeout: int = None,
        waitUntil: Literal["load", "domcontentloaded", "networkidle"] = "load",
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]] = None,
    ) -> typing.Union["Response", NoneType]:
        return Response._from_async_nullable(
            self._sync(
                self._async_obj.waitForNavigation(
                    timeout=timeout, waitUntil=waitUntil, url=url
                )
            )
        )

    def waitForLoadState(
        self,
        state: Literal["load", "domcontentloaded", "networkidle"] = "load",
        timeout: int = None,
    ) -> NoneType:
        return self._sync(
            self._async_obj.waitForLoadState(state=state, timeout=timeout)
        )

    def frameElement(self) -> "ElementHandle":
        return ElementHandle._from_async(self._sync(self._async_obj.frameElement()))

    def evaluate(
        self, expression: str, arg: typing.Any = None, force_expr: bool = False
    ) -> typing.Any:
        return self._sync(
            self._async_obj.evaluate(
                expression=expression, arg=arg, force_expr=force_expr
            )
        )

    def evaluateHandle(
        self, expression: str, arg: typing.Any = None, force_expr: bool = False
    ) -> "JSHandle":
        return JSHandle._from_async(
            self._sync(
                self._async_obj.evaluateHandle(
                    expression=expression, arg=arg, force_expr=force_expr
                )
            )
        )

    def querySelector(self, selector: str) -> typing.Union["ElementHandle", NoneType]:
        return ElementHandle._from_async_nullable(
            self._sync(self._async_obj.querySelector(selector=selector))
        )

    def querySelectorAll(self, selector: str) -> typing.List["ElementHandle"]:
        return ElementHandle._from_async_list(
            self._sync(self._async_obj.querySelectorAll(selector=selector))
        )

    def waitForSelector(
        self,
        selector: str,
        timeout: int = None,
        state: Literal["attached", "detached", "visible", "hidden"] = None,
    ) -> typing.Union["ElementHandle", NoneType]:
        return ElementHandle._from_async_nullable(
            self._sync(
                self._async_obj.waitForSelector(
                    selector=selector, timeout=timeout, state=state
                )
            )
        )

    def dispatchEvent(
        self,
        selector: str,
        type: str,
        eventInit: typing.Dict = None,
        timeout: int = None,
    ) -> NoneType:
        return self._sync(
            self._async_obj.dispatchEvent(
                selector=selector, type=type, eventInit=eventInit, timeout=timeout
            )
        )

    def evalOnSelector(
        self,
        selector: str,
        expression: str,
        arg: typing.Any = None,
        force_expr: bool = False,
    ) -> typing.Any:
        return self._sync(
            self._async_obj.evalOnSelector(
                selector=selector, expression=expression, arg=arg, force_expr=force_expr
            )
        )

    def evalOnSelectorAll(
        self,
        selector: str,
        expression: str,
        arg: typing.Any = None,
        force_expr: bool = False,
    ) -> typing.Any:
        return self._sync(
            self._async_obj.evalOnSelectorAll(
                selector=selector, expression=expression, arg=arg, force_expr=force_expr
            )
        )

    def content(self) -> str:
        return self._sync(self._async_obj.content())

    def setContent(
        self,
        html: str,
        timeout: int = None,
        waitUntil: Literal["load", "domcontentloaded", "networkidle"] = None,
    ) -> NoneType:
        return self._sync(
            self._async_obj.setContent(html=html, timeout=timeout, waitUntil=waitUntil)
        )

    def isDetached(self) -> bool:
        return self._sync(self._async_obj.isDetached())

    def addScriptTag(
        self, url: str = None, path: str = None, content: str = None, type: str = None
    ) -> "ElementHandle":
        return ElementHandle._from_async(
            self._sync(
                self._async_obj.addScriptTag(
                    url=url, path=path, content=content, type=type
                )
            )
        )

    def addStyleTag(
        self, url: str = None, path: str = None, content: str = None
    ) -> "ElementHandle":
        return ElementHandle._from_async(
            self._sync(self._async_obj.addStyleTag(url=url, path=path, content=content))
        )

    def click(
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
        return self._sync(
            self._async_obj.click(
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

    def dblclick(
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
        return self._sync(
            self._async_obj.dblclick(
                selector=selector,
                modifiers=modifiers,
                position=position,
                delay=delay,
                button=button,
                timeout=timeout,
                force=force,
            )
        )

    def fill(
        self, selector: str, value: str, timeout: int = None, noWaitAfter: bool = None
    ) -> NoneType:
        return self._sync(
            self._async_obj.fill(
                selector=selector, value=value, timeout=timeout, noWaitAfter=noWaitAfter
            )
        )

    def focus(self, selector: str, timeout: int = None) -> NoneType:
        return self._sync(self._async_obj.focus(selector=selector, timeout=timeout))

    def textContent(self, selector: str, timeout: int = None) -> str:
        return self._sync(
            self._async_obj.textContent(selector=selector, timeout=timeout)
        )

    def innerText(self, selector: str, timeout: int = None) -> str:
        return self._sync(self._async_obj.innerText(selector=selector, timeout=timeout))

    def innerHTML(self, selector: str, timeout: int = None) -> str:
        return self._sync(self._async_obj.innerHTML(selector=selector, timeout=timeout))

    def getAttribute(self, selector: str, name: str, timeout: int = None) -> str:
        return self._sync(
            self._async_obj.getAttribute(selector=selector, name=name, timeout=timeout)
        )

    def hover(
        self,
        selector: str,
        modifiers: typing.Union[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: typing.Dict = None,
        timeout: int = None,
        force: bool = None,
    ) -> NoneType:
        return self._sync(
            self._async_obj.hover(
                selector=selector,
                modifiers=modifiers,
                position=position,
                timeout=timeout,
                force=force,
            )
        )

    def selectOption(
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
        return self._sync(
            self._async_obj.selectOption(
                selector=selector,
                values=values,
                timeout=timeout,
                noWaitAfter=noWaitAfter,
            )
        )

    def setInputFiles(
        self,
        selector: str,
        files: typing.Union[
            str, FilePayload, typing.List[str], typing.List[FilePayload]
        ],
        timeout: int = None,
        noWaitAfter: bool = None,
    ) -> NoneType:
        return self._sync(
            self._async_obj.setInputFiles(
                selector=selector, files=files, timeout=timeout, noWaitAfter=noWaitAfter
            )
        )

    def type(
        self,
        selector: str,
        text: str,
        delay: int = None,
        timeout: int = None,
        noWaitAfter: bool = None,
    ) -> NoneType:
        return self._sync(
            self._async_obj.type(
                selector=selector,
                text=text,
                delay=delay,
                timeout=timeout,
                noWaitAfter=noWaitAfter,
            )
        )

    def press(
        self,
        selector: str,
        key: str,
        delay: int = None,
        timeout: int = None,
        noWaitAfter: bool = None,
    ) -> NoneType:
        return self._sync(
            self._async_obj.press(
                selector=selector,
                key=key,
                delay=delay,
                timeout=timeout,
                noWaitAfter=noWaitAfter,
            )
        )

    def check(
        self,
        selector: str,
        timeout: int = None,
        force: bool = None,
        noWaitAfter: bool = None,
    ) -> NoneType:
        return self._sync(
            self._async_obj.check(
                selector=selector, timeout=timeout, force=force, noWaitAfter=noWaitAfter
            )
        )

    def uncheck(
        self,
        selector: str,
        timeout: int = None,
        force: bool = None,
        noWaitAfter: bool = None,
    ) -> NoneType:
        return self._sync(
            self._async_obj.uncheck(
                selector=selector, timeout=timeout, force=force, noWaitAfter=noWaitAfter
            )
        )

    def waitForTimeout(self, timeout: int) -> typing.Awaitable[NoneType]:
        return self._sync(self._async_obj.waitForTimeout(timeout=timeout))

    def waitForFunction(
        self,
        expression: str,
        arg: typing.Any = None,
        force_expr: bool = False,
        timeout: int = None,
        polling: typing.Union[int, Literal["raf"]] = None,
    ) -> "JSHandle":
        return JSHandle._from_async(
            self._sync(
                self._async_obj.waitForFunction(
                    expression=expression,
                    arg=arg,
                    force_expr=force_expr,
                    timeout=timeout,
                    polling=polling,
                )
            )
        )

    def title(self) -> str:
        return self._sync(self._async_obj.title())


mapping.register(FrameAsync, Frame)


class Worker(SyncBase):
    def __init__(self, obj: WorkerAsync):
        super().__init__(obj)

    def as_async(self) -> WorkerAsync:
        return self._async_obj

    @classmethod
    def _from_async(cls, obj: WorkerAsync) -> "Worker":
        if not obj._sync_owner:
            obj._sync_owner = cls(obj)
        return obj._sync_owner

    @classmethod
    def _from_async_nullable(cls, obj: WorkerAsync = None) -> typing.Optional["Worker"]:
        return Worker._from_async(obj) if obj else None

    @classmethod
    def _from_async_list(cls, items: typing.List[WorkerAsync]) -> typing.List["Worker"]:
        return list(map(lambda a: Worker._from_async(a), items))

    @classmethod
    def _from_async_dict(
        cls, map: typing.Dict[str, WorkerAsync]
    ) -> typing.Dict[str, "Worker"]:
        return {name: Worker._from_async(value) for name, value in map.items()}

    @property
    def url(self) -> str:
        return self._async_obj.url

    def evaluate(
        self, expression: str, arg: typing.Any = None, force_expr: bool = False
    ) -> typing.Any:
        return self._sync(
            self._async_obj.evaluate(
                expression=expression, arg=arg, force_expr=force_expr
            )
        )

    def evaluateHandle(
        self, expression: str, arg: typing.Any = None, force_expr: bool = False
    ) -> "JSHandle":
        return JSHandle._from_async(
            self._sync(
                self._async_obj.evaluateHandle(
                    expression=expression, arg=arg, force_expr=force_expr
                )
            )
        )


mapping.register(WorkerAsync, Worker)


class Selectors(SyncBase):
    def __init__(self, obj: SelectorsAsync):
        super().__init__(obj)

    def as_async(self) -> SelectorsAsync:
        return self._async_obj

    @classmethod
    def _from_async(cls, obj: SelectorsAsync) -> "Selectors":
        if not obj._sync_owner:
            obj._sync_owner = cls(obj)
        return obj._sync_owner

    @classmethod
    def _from_async_nullable(
        cls, obj: SelectorsAsync = None
    ) -> typing.Optional["Selectors"]:
        return Selectors._from_async(obj) if obj else None

    @classmethod
    def _from_async_list(
        cls, items: typing.List[SelectorsAsync]
    ) -> typing.List["Selectors"]:
        return list(map(lambda a: Selectors._from_async(a), items))

    @classmethod
    def _from_async_dict(
        cls, map: typing.Dict[str, SelectorsAsync]
    ) -> typing.Dict[str, "Selectors"]:
        return {name: Selectors._from_async(value) for name, value in map.items()}

    def register(
        self, name: str, source: str = "", path: str = None, contentScript: bool = False
    ) -> NoneType:
        return self._sync(
            self._async_obj.register(
                name=name, source=source, path=path, contentScript=contentScript
            )
        )


mapping.register(SelectorsAsync, Selectors)


class ConsoleMessage(SyncBase):
    def __init__(self, obj: ConsoleMessageAsync):
        super().__init__(obj)

    def as_async(self) -> ConsoleMessageAsync:
        return self._async_obj

    @classmethod
    def _from_async(cls, obj: ConsoleMessageAsync) -> "ConsoleMessage":
        if not obj._sync_owner:
            obj._sync_owner = cls(obj)
        return obj._sync_owner

    @classmethod
    def _from_async_nullable(
        cls, obj: ConsoleMessageAsync = None
    ) -> typing.Optional["ConsoleMessage"]:
        return ConsoleMessage._from_async(obj) if obj else None

    @classmethod
    def _from_async_list(
        cls, items: typing.List[ConsoleMessageAsync]
    ) -> typing.List["ConsoleMessage"]:
        return list(map(lambda a: ConsoleMessage._from_async(a), items))

    @classmethod
    def _from_async_dict(
        cls, map: typing.Dict[str, ConsoleMessageAsync]
    ) -> typing.Dict[str, "ConsoleMessage"]:
        return {name: ConsoleMessage._from_async(value) for name, value in map.items()}

    @property
    def type(self) -> str:
        return self._async_obj.type

    @property
    def text(self) -> str:
        return self._async_obj.text

    @property
    def args(self) -> typing.List["JSHandle"]:
        return JSHandle._from_async_list(self._async_obj.args)

    @property
    def location(self) -> ConsoleMessageLocation:
        return self._async_obj.location


mapping.register(ConsoleMessageAsync, ConsoleMessage)


class Dialog(SyncBase):
    def __init__(self, obj: DialogAsync):
        super().__init__(obj)

    def as_async(self) -> DialogAsync:
        return self._async_obj

    @classmethod
    def _from_async(cls, obj: DialogAsync) -> "Dialog":
        if not obj._sync_owner:
            obj._sync_owner = cls(obj)
        return obj._sync_owner

    @classmethod
    def _from_async_nullable(cls, obj: DialogAsync = None) -> typing.Optional["Dialog"]:
        return Dialog._from_async(obj) if obj else None

    @classmethod
    def _from_async_list(cls, items: typing.List[DialogAsync]) -> typing.List["Dialog"]:
        return list(map(lambda a: Dialog._from_async(a), items))

    @classmethod
    def _from_async_dict(
        cls, map: typing.Dict[str, DialogAsync]
    ) -> typing.Dict[str, "Dialog"]:
        return {name: Dialog._from_async(value) for name, value in map.items()}

    @property
    def type(self) -> str:
        return self._async_obj.type

    @property
    def message(self) -> str:
        return self._async_obj.message

    @property
    def defaultValue(self) -> str:
        return self._async_obj.defaultValue

    def accept(self, prompt_text: str = None) -> NoneType:
        return self._sync(self._async_obj.accept(prompt_text=prompt_text))

    def dismiss(self) -> NoneType:
        return self._sync(self._async_obj.dismiss())


mapping.register(DialogAsync, Dialog)


class Download(SyncBase):
    def __init__(self, obj: DownloadAsync):
        super().__init__(obj)

    def as_async(self) -> DownloadAsync:
        return self._async_obj

    @classmethod
    def _from_async(cls, obj: DownloadAsync) -> "Download":
        if not obj._sync_owner:
            obj._sync_owner = cls(obj)
        return obj._sync_owner

    @classmethod
    def _from_async_nullable(
        cls, obj: DownloadAsync = None
    ) -> typing.Optional["Download"]:
        return Download._from_async(obj) if obj else None

    @classmethod
    def _from_async_list(
        cls, items: typing.List[DownloadAsync]
    ) -> typing.List["Download"]:
        return list(map(lambda a: Download._from_async(a), items))

    @classmethod
    def _from_async_dict(
        cls, map: typing.Dict[str, DownloadAsync]
    ) -> typing.Dict[str, "Download"]:
        return {name: Download._from_async(value) for name, value in map.items()}

    @property
    def url(self) -> str:
        return self._async_obj.url

    @property
    def suggestedFilename(self) -> str:
        return self._async_obj.suggestedFilename

    def delete(self) -> NoneType:
        return self._sync(self._async_obj.delete())

    def failure(self) -> typing.Union[str, NoneType]:
        return self._sync(self._async_obj.failure())

    def path(self) -> typing.Union[str, NoneType]:
        return self._sync(self._async_obj.path())


mapping.register(DownloadAsync, Download)


class BindingCall(SyncBase):
    def __init__(self, obj: BindingCallAsync):
        super().__init__(obj)

    def as_async(self) -> BindingCallAsync:
        return self._async_obj

    @classmethod
    def _from_async(cls, obj: BindingCallAsync) -> "BindingCall":
        if not obj._sync_owner:
            obj._sync_owner = cls(obj)
        return obj._sync_owner

    @classmethod
    def _from_async_nullable(
        cls, obj: BindingCallAsync = None
    ) -> typing.Optional["BindingCall"]:
        return BindingCall._from_async(obj) if obj else None

    @classmethod
    def _from_async_list(
        cls, items: typing.List[BindingCallAsync]
    ) -> typing.List["BindingCall"]:
        return list(map(lambda a: BindingCall._from_async(a), items))

    @classmethod
    def _from_async_dict(
        cls, map: typing.Dict[str, BindingCallAsync]
    ) -> typing.Dict[str, "BindingCall"]:
        return {name: BindingCall._from_async(value) for name, value in map.items()}

    def call(self, func: typing.Callable[[typing.Dict], typing.Any]) -> NoneType:
        return self._sync(self._async_obj.call(func=func))


mapping.register(BindingCallAsync, BindingCall)


class Page(SyncBase):
    def __init__(self, obj: PageAsync):
        super().__init__(obj)

    def as_async(self) -> PageAsync:
        return self._async_obj

    @classmethod
    def _from_async(cls, obj: PageAsync) -> "Page":
        if not obj._sync_owner:
            obj._sync_owner = cls(obj)
        return obj._sync_owner

    @classmethod
    def _from_async_nullable(cls, obj: PageAsync = None) -> typing.Optional["Page"]:
        return Page._from_async(obj) if obj else None

    @classmethod
    def _from_async_list(cls, items: typing.List[PageAsync]) -> typing.List["Page"]:
        return list(map(lambda a: Page._from_async(a), items))

    @classmethod
    def _from_async_dict(
        cls, map: typing.Dict[str, PageAsync]
    ) -> typing.Dict[str, "Page"]:
        return {name: Page._from_async(value) for name, value in map.items()}

    @property
    def accessibility(self) -> "Accessibility":
        return Accessibility._from_async(self._async_obj.accessibility)

    @property
    def keyboard(self) -> "Keyboard":
        return Keyboard._from_async(self._async_obj.keyboard)

    @property
    def mouse(self) -> "Mouse":
        return Mouse._from_async(self._async_obj.mouse)

    @property
    def context(self) -> "BrowserContext":
        return BrowserContext._from_async(self._async_obj.context)

    @property
    def mainFrame(self) -> "Frame":
        return Frame._from_async(self._async_obj.mainFrame)

    @property
    def frames(self) -> typing.List["Frame"]:
        return Frame._from_async_list(self._async_obj.frames)

    @property
    def url(self) -> str:
        return self._async_obj.url

    @property
    def workers(self) -> typing.List["Worker"]:
        return Worker._from_async_list(self._async_obj.workers)

    def opener(self) -> typing.Union["Page", NoneType]:
        return Page._from_async_nullable(self._sync(self._async_obj.opener()))

    def frame(
        self,
        name: str = None,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]] = None,
    ) -> typing.Union["Frame", NoneType]:
        return Frame._from_async_nullable(
            self._sync(self._async_obj.frame(name=name, url=url))
        )

    def setDefaultNavigationTimeout(self, timeout: int) -> NoneType:
        return self._sync(self._async_obj.setDefaultNavigationTimeout(timeout=timeout))

    def setDefaultTimeout(self, timeout: int) -> NoneType:
        return self._sync(self._async_obj.setDefaultTimeout(timeout=timeout))

    def querySelector(self, selector: str) -> typing.Union["ElementHandle", NoneType]:
        return ElementHandle._from_async_nullable(
            self._sync(self._async_obj.querySelector(selector=selector))
        )

    def querySelectorAll(self, selector: str) -> typing.List["ElementHandle"]:
        return ElementHandle._from_async_list(
            self._sync(self._async_obj.querySelectorAll(selector=selector))
        )

    def waitForSelector(
        self,
        selector: str,
        timeout: int = None,
        state: Literal["attached", "detached", "visible", "hidden"] = None,
    ) -> typing.Union["ElementHandle", NoneType]:
        return ElementHandle._from_async_nullable(
            self._sync(
                self._async_obj.waitForSelector(
                    selector=selector, timeout=timeout, state=state
                )
            )
        )

    def dispatchEvent(
        self,
        selector: str,
        type: str,
        eventInit: typing.Dict = None,
        timeout: int = None,
    ) -> NoneType:
        return self._sync(
            self._async_obj.dispatchEvent(
                selector=selector, type=type, eventInit=eventInit, timeout=timeout
            )
        )

    def evaluate(
        self, expression: str, arg: typing.Any = None, force_expr: bool = False
    ) -> typing.Any:
        return self._sync(
            self._async_obj.evaluate(
                expression=expression, arg=arg, force_expr=force_expr
            )
        )

    def evaluateHandle(
        self, expression: str, arg: typing.Any = None, force_expr: bool = False
    ) -> "JSHandle":
        return JSHandle._from_async(
            self._sync(
                self._async_obj.evaluateHandle(
                    expression=expression, arg=arg, force_expr=force_expr
                )
            )
        )

    def evalOnSelector(
        self,
        selector: str,
        expression: str,
        arg: typing.Any = None,
        force_expr: bool = False,
    ) -> typing.Any:
        return self._sync(
            self._async_obj.evalOnSelector(
                selector=selector, expression=expression, arg=arg, force_expr=force_expr
            )
        )

    def evalOnSelectorAll(
        self,
        selector: str,
        expression: str,
        arg: typing.Any = None,
        force_expr: bool = False,
    ) -> typing.Any:
        return self._sync(
            self._async_obj.evalOnSelectorAll(
                selector=selector, expression=expression, arg=arg, force_expr=force_expr
            )
        )

    def addScriptTag(
        self, url: str = None, path: str = None, content: str = None, type: str = None
    ) -> "ElementHandle":
        return ElementHandle._from_async(
            self._sync(
                self._async_obj.addScriptTag(
                    url=url, path=path, content=content, type=type
                )
            )
        )

    def addStyleTag(
        self, url: str = None, path: str = None, content: str = None
    ) -> "ElementHandle":
        return ElementHandle._from_async(
            self._sync(self._async_obj.addStyleTag(url=url, path=path, content=content))
        )

    def exposeFunction(
        self, name: str, binding: typing.Callable[..., typing.Any]
    ) -> NoneType:
        return self._sync(self._async_obj.exposeFunction(name=name, binding=binding))

    def exposeBinding(
        self, name: str, binding: typing.Callable[[typing.Dict], typing.Any]
    ) -> NoneType:
        return self._sync(self._async_obj.exposeBinding(name=name, binding=binding))

    def setExtraHTTPHeaders(self, headers: typing.Dict) -> NoneType:
        return self._sync(self._async_obj.setExtraHTTPHeaders(headers=headers))

    def content(self) -> str:
        return self._sync(self._async_obj.content())

    def setContent(
        self,
        html: str,
        timeout: int = None,
        waitUntil: Literal["load", "domcontentloaded", "networkidle"] = None,
    ) -> NoneType:
        return self._sync(
            self._async_obj.setContent(html=html, timeout=timeout, waitUntil=waitUntil)
        )

    def goto(
        self,
        url: str,
        timeout: int = None,
        waitUntil: Literal["load", "domcontentloaded", "networkidle"] = "load",
        referer: str = None,
    ) -> typing.Union["Response", NoneType]:
        return Response._from_async_nullable(
            self._sync(
                self._async_obj.goto(
                    url=url, timeout=timeout, waitUntil=waitUntil, referer=referer
                )
            )
        )

    def reload(
        self,
        timeout: int = None,
        waitUntil: Literal["load", "domcontentloaded", "networkidle"] = "load",
    ) -> typing.Union["Response", NoneType]:
        return Response._from_async_nullable(
            self._sync(self._async_obj.reload(timeout=timeout, waitUntil=waitUntil))
        )

    def waitForLoadState(
        self,
        state: Literal["load", "domcontentloaded", "networkidle"] = "load",
        timeout: int = None,
    ) -> NoneType:
        return self._sync(
            self._async_obj.waitForLoadState(state=state, timeout=timeout)
        )

    def waitForNavigation(
        self,
        timeout: int = None,
        waitUntil: Literal["load", "domcontentloaded", "networkidle"] = "load",
        url: str = None,
    ) -> typing.Union["Response", NoneType]:
        return Response._from_async_nullable(
            self._sync(
                self._async_obj.waitForNavigation(
                    timeout=timeout, waitUntil=waitUntil, url=url
                )
            )
        )

    def waitForRequest(
        self,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]] = None,
        predicate: typing.Union[typing.Callable[["Request"], bool]] = None,
        timeout: int = None,
    ) -> typing.Union["Request", NoneType]:
        return Request._from_async_nullable(
            self._sync(
                self._async_obj.waitForRequest(
                    url=url, predicate=predicate, timeout=timeout
                )
            )
        )

    def waitForResponse(
        self,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]] = None,
        predicate: typing.Union[typing.Callable[["Response"], bool]] = None,
        timeout: int = None,
    ) -> typing.Union["Response", NoneType]:
        return Response._from_async_nullable(
            self._sync(
                self._async_obj.waitForResponse(
                    url=url, predicate=predicate, timeout=timeout
                )
            )
        )

    def waitForEvent(
        self,
        event: str,
        predicate: typing.Union[typing.Callable[[typing.Any], bool]] = None,
        timeout: int = None,
    ) -> typing.Any:
        return self._sync(
            self._async_obj.waitForEvent(
                event=event, predicate=predicate, timeout=timeout
            )
        )

    def goBack(
        self,
        timeout: int = None,
        waitUntil: Literal["load", "domcontentloaded", "networkidle"] = None,
    ) -> typing.Union["Response", NoneType]:
        return Response._from_async_nullable(
            self._sync(self._async_obj.goBack(timeout=timeout, waitUntil=waitUntil))
        )

    def goForward(
        self,
        timeout: int = None,
        waitUntil: Literal["load", "domcontentloaded", "networkidle"] = None,
    ) -> typing.Union["Response", NoneType]:
        return Response._from_async_nullable(
            self._sync(self._async_obj.goForward(timeout=timeout, waitUntil=waitUntil))
        )

    def emulateMedia(
        self,
        media: Literal["screen", "print"] = None,
        colorScheme: Literal["light", "dark", "no-preference"] = None,
    ) -> NoneType:
        return self._sync(
            self._async_obj.emulateMedia(media=media, colorScheme=colorScheme)
        )

    def setViewportSize(self, width: int, height: int) -> NoneType:
        return self._sync(self._async_obj.setViewportSize(width=width, height=height))

    def viewportSize(self) -> typing.Union[Viewport, NoneType]:
        return self._sync(self._async_obj.viewportSize())

    def addInitScript(self, source: str = None, path: str = None) -> NoneType:
        return self._sync(self._async_obj.addInitScript(source=source, path=path))

    def route(
        self,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]],
        handler: typing.Callable[["Route", "Request"], typing.Any],
    ) -> NoneType:
        return self._sync(self._async_obj.route(url=url, handler=handler))

    def unroute(
        self,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]],
        handler: typing.Union[typing.Callable[["Route", "Request"], typing.Any]] = None,
    ) -> NoneType:
        return self._sync(self._async_obj.unroute(url=url, handler=handler))

    def screenshot(
        self,
        timeout: int = None,
        type: Literal["png", "jpeg"] = None,
        path: str = None,
        quality: int = None,
        omitBackground: bool = None,
        fullPage: bool = None,
        clip: typing.Dict = None,
    ) -> bytes:
        return self._sync(
            self._async_obj.screenshot(
                timeout=timeout,
                type=type,
                path=path,
                quality=quality,
                omitBackground=omitBackground,
                fullPage=fullPage,
                clip=clip,
            )
        )

    def title(self) -> str:
        return self._sync(self._async_obj.title())

    def close(self, runBeforeUnload: bool = None) -> NoneType:
        return self._sync(self._async_obj.close(runBeforeUnload=runBeforeUnload))

    def isClosed(self) -> bool:
        return self._sync(self._async_obj.isClosed())

    def click(
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
        return self._sync(
            self._async_obj.click(
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

    def dblclick(
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
        return self._sync(
            self._async_obj.dblclick(
                selector=selector,
                modifiers=modifiers,
                position=position,
                delay=delay,
                button=button,
                timeout=timeout,
                force=force,
            )
        )

    def fill(
        self, selector: str, value: str, timeout: int = None, noWaitAfter: bool = None
    ) -> NoneType:
        return self._sync(
            self._async_obj.fill(
                selector=selector, value=value, timeout=timeout, noWaitAfter=noWaitAfter
            )
        )

    def focus(self, selector: str, timeout: int = None) -> NoneType:
        return self._sync(self._async_obj.focus(selector=selector, timeout=timeout))

    def textContent(self, selector: str, timeout: int = None) -> str:
        return self._sync(
            self._async_obj.textContent(selector=selector, timeout=timeout)
        )

    def innerText(self, selector: str, timeout: int = None) -> str:
        return self._sync(self._async_obj.innerText(selector=selector, timeout=timeout))

    def innerHTML(self, selector: str, timeout: int = None) -> str:
        return self._sync(self._async_obj.innerHTML(selector=selector, timeout=timeout))

    def getAttribute(self, selector: str, name: str, timeout: int = None) -> str:
        return self._sync(
            self._async_obj.getAttribute(selector=selector, name=name, timeout=timeout)
        )

    def hover(
        self,
        selector: str,
        modifiers: typing.Union[
            typing.List[Literal["Alt", "Control", "Meta", "Shift"]]
        ] = None,
        position: typing.Dict = None,
        timeout: int = None,
        force: bool = None,
    ) -> NoneType:
        return self._sync(
            self._async_obj.hover(
                selector=selector,
                modifiers=modifiers,
                position=position,
                timeout=timeout,
                force=force,
            )
        )

    def selectOption(
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
        return self._sync(
            self._async_obj.selectOption(
                selector=selector,
                values=values,
                timeout=timeout,
                noWaitAfter=noWaitAfter,
            )
        )

    def setInputFiles(
        self,
        selector: str,
        files: typing.Union[
            str, FilePayload, typing.List[str], typing.List[FilePayload]
        ],
        timeout: int = None,
        noWaitAfter: bool = None,
    ) -> NoneType:
        return self._sync(
            self._async_obj.setInputFiles(
                selector=selector, files=files, timeout=timeout, noWaitAfter=noWaitAfter
            )
        )

    def type(
        self,
        selector: str,
        text: str,
        delay: int = None,
        timeout: int = None,
        noWaitAfter: bool = None,
    ) -> NoneType:
        return self._sync(
            self._async_obj.type(
                selector=selector,
                text=text,
                delay=delay,
                timeout=timeout,
                noWaitAfter=noWaitAfter,
            )
        )

    def press(
        self,
        selector: str,
        key: str,
        delay: int = None,
        timeout: int = None,
        noWaitAfter: bool = None,
    ) -> NoneType:
        return self._sync(
            self._async_obj.press(
                selector=selector,
                key=key,
                delay=delay,
                timeout=timeout,
                noWaitAfter=noWaitAfter,
            )
        )

    def check(
        self,
        selector: str,
        timeout: int = None,
        force: bool = None,
        noWaitAfter: bool = None,
    ) -> NoneType:
        return self._sync(
            self._async_obj.check(
                selector=selector, timeout=timeout, force=force, noWaitAfter=noWaitAfter
            )
        )

    def uncheck(
        self,
        selector: str,
        timeout: int = None,
        force: bool = None,
        noWaitAfter: bool = None,
    ) -> NoneType:
        return self._sync(
            self._async_obj.uncheck(
                selector=selector, timeout=timeout, force=force, noWaitAfter=noWaitAfter
            )
        )

    def waitForTimeout(self, timeout: int) -> typing.Awaitable[NoneType]:
        return self._sync(self._async_obj.waitForTimeout(timeout=timeout))

    def waitForFunction(
        self,
        expression: str,
        arg: typing.Any = None,
        force_expr: bool = False,
        timeout: int = None,
        polling: typing.Union[int, Literal["raf"]] = None,
    ) -> "JSHandle":
        return JSHandle._from_async(
            self._sync(
                self._async_obj.waitForFunction(
                    expression=expression,
                    arg=arg,
                    force_expr=force_expr,
                    timeout=timeout,
                    polling=polling,
                )
            )
        )

    def pdf(
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
        return self._sync(
            self._async_obj.pdf(
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
    ) -> EventContextManager["ConsoleMessage"]:
        return EventContextManager(self, "console", predicate, timeout)

    def expect_dialog(
        self,
        predicate: typing.Union[typing.Callable[["Dialog"], bool]] = None,
        timeout: int = None,
    ) -> EventContextManager["Dialog"]:
        return EventContextManager(self, "dialog", predicate, timeout)

    def expect_download(
        self,
        predicate: typing.Union[typing.Callable[["Download"], bool]] = None,
        timeout: int = None,
    ) -> EventContextManager["Download"]:
        return EventContextManager(self, "download", predicate, timeout)

    def expect_file_chooser(
        self,
        predicate: typing.Union[typing.Callable[["FileChooser"], bool]] = None,
        timeout: int = None,
    ) -> EventContextManager["FileChooser"]:
        return EventContextManager(self, "filechooser", predicate, timeout)

    def expect_request(
        self,
        predicate: typing.Union[typing.Callable[["Request"], bool]] = None,
        timeout: int = None,
    ) -> EventContextManager["Request"]:
        return EventContextManager(self, "request", predicate, timeout)

    def expect_response(
        self,
        predicate: typing.Union[typing.Callable[["Response"], bool]] = None,
        timeout: int = None,
    ) -> EventContextManager["Response"]:
        return EventContextManager(self, "response", predicate, timeout)

    def expect_popup(
        self,
        predicate: typing.Union[typing.Callable[["Page"], bool]] = None,
        timeout: int = None,
    ) -> EventContextManager["Page"]:
        return EventContextManager(self, "popup", predicate, timeout)

    def expect_worker(
        self,
        predicate: typing.Union[typing.Callable[["Worker"], bool]] = None,
        timeout: int = None,
    ) -> EventContextManager["Worker"]:
        return EventContextManager(self, "worker", predicate, timeout)


mapping.register(PageAsync, Page)


class BrowserContext(SyncBase):
    def __init__(self, obj: BrowserContextAsync):
        super().__init__(obj)

    def as_async(self) -> BrowserContextAsync:
        return self._async_obj

    @classmethod
    def _from_async(cls, obj: BrowserContextAsync) -> "BrowserContext":
        if not obj._sync_owner:
            obj._sync_owner = cls(obj)
        return obj._sync_owner

    @classmethod
    def _from_async_nullable(
        cls, obj: BrowserContextAsync = None
    ) -> typing.Optional["BrowserContext"]:
        return BrowserContext._from_async(obj) if obj else None

    @classmethod
    def _from_async_list(
        cls, items: typing.List[BrowserContextAsync]
    ) -> typing.List["BrowserContext"]:
        return list(map(lambda a: BrowserContext._from_async(a), items))

    @classmethod
    def _from_async_dict(
        cls, map: typing.Dict[str, BrowserContextAsync]
    ) -> typing.Dict[str, "BrowserContext"]:
        return {name: BrowserContext._from_async(value) for name, value in map.items()}

    @property
    def pages(self) -> typing.List["Page"]:
        return Page._from_async_list(self._async_obj.pages)

    def setDefaultNavigationTimeout(self, timeout: int) -> NoneType:
        return self._sync(self._async_obj.setDefaultNavigationTimeout(timeout=timeout))

    def setDefaultTimeout(self, timeout: int) -> NoneType:
        return self._sync(self._async_obj.setDefaultTimeout(timeout=timeout))

    def newPage(self) -> "Page":
        return Page._from_async(self._sync(self._async_obj.newPage()))

    def cookies(
        self, urls: typing.Union[str, typing.List[str]]
    ) -> typing.List[typing.List[typing.Dict[str, typing.Union[str, int, bool]]]]:
        return self._sync(self._async_obj.cookies(urls=urls))

    def addCookies(
        self,
        cookies: typing.List[
            typing.List[typing.Dict[str, typing.Union[str, int, bool]]]
        ],
    ) -> NoneType:
        return self._sync(self._async_obj.addCookies(cookies=cookies))

    def clearCookies(self) -> NoneType:
        return self._sync(self._async_obj.clearCookies())

    def grantPermissions(
        self, permissions: typing.List[str], origin: str = None
    ) -> NoneType:
        return self._sync(
            self._async_obj.grantPermissions(permissions=permissions, origin=origin)
        )

    def clearPermissions(self) -> NoneType:
        return self._sync(self._async_obj.clearPermissions())

    def setGeolocation(self, geolocation: typing.Dict) -> NoneType:
        return self._sync(self._async_obj.setGeolocation(geolocation=geolocation))

    def setExtraHTTPHeaders(self, headers: typing.Dict) -> NoneType:
        return self._sync(self._async_obj.setExtraHTTPHeaders(headers=headers))

    def setOffline(self, offline: bool) -> NoneType:
        return self._sync(self._async_obj.setOffline(offline=offline))

    def addInitScript(self, source: str = None, path: str = None) -> NoneType:
        return self._sync(self._async_obj.addInitScript(source=source, path=path))

    def exposeBinding(
        self, name: str, binding: typing.Callable[[typing.Dict], typing.Any]
    ) -> NoneType:
        return self._sync(self._async_obj.exposeBinding(name=name, binding=binding))

    def exposeFunction(
        self, name: str, binding: typing.Callable[..., typing.Any]
    ) -> NoneType:
        return self._sync(self._async_obj.exposeFunction(name=name, binding=binding))

    def route(
        self,
        match: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]],
        handler: typing.Callable[["Route", "Request"], typing.Any],
    ) -> NoneType:
        return self._sync(self._async_obj.route(match=match, handler=handler))

    def unroute(
        self,
        match: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]],
        handler: typing.Union[typing.Callable[["Route", "Request"], typing.Any]] = None,
    ) -> NoneType:
        return self._sync(self._async_obj.unroute(match=match, handler=handler))

    def waitForEvent(
        self,
        event: str,
        predicate: typing.Union[typing.Callable[[typing.Any], bool]] = None,
        timeout: int = None,
    ) -> typing.Any:
        return self._sync(
            self._async_obj.waitForEvent(
                event=event, predicate=predicate, timeout=timeout
            )
        )

    def close(self) -> NoneType:
        return self._sync(self._async_obj.close())

    def expect_page(
        self,
        predicate: typing.Union[typing.Callable[["Page"], bool]] = None,
        timeout: int = None,
    ) -> EventContextManager["Page"]:
        return EventContextManager(self, "page", predicate, timeout)


mapping.register(BrowserContextAsync, BrowserContext)


class Browser(SyncBase):
    def __init__(self, obj: BrowserAsync):
        super().__init__(obj)

    def as_async(self) -> BrowserAsync:
        return self._async_obj

    @classmethod
    def _from_async(cls, obj: BrowserAsync) -> "Browser":
        if not obj._sync_owner:
            obj._sync_owner = cls(obj)
        return obj._sync_owner

    @classmethod
    def _from_async_nullable(
        cls, obj: BrowserAsync = None
    ) -> typing.Optional["Browser"]:
        return Browser._from_async(obj) if obj else None

    @classmethod
    def _from_async_list(
        cls, items: typing.List[BrowserAsync]
    ) -> typing.List["Browser"]:
        return list(map(lambda a: Browser._from_async(a), items))

    @classmethod
    def _from_async_dict(
        cls, map: typing.Dict[str, BrowserAsync]
    ) -> typing.Dict[str, "Browser"]:
        return {name: Browser._from_async(value) for name, value in map.items()}

    @property
    def contexts(self) -> typing.List["BrowserContext"]:
        return BrowserContext._from_async_list(self._async_obj.contexts)

    def isConnected(self) -> bool:
        return self._sync(self._async_obj.isConnected())

    def newContext(
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
        return BrowserContext._from_async(
            self._sync(
                self._async_obj.newContext(
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
        )

    def newPage(
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
        return Page._from_async(
            self._sync(
                self._async_obj.newPage(
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
        )

    def close(self) -> NoneType:
        return self._sync(self._async_obj.close())


mapping.register(BrowserAsync, Browser)


class BrowserServer(SyncBase):
    def __init__(self, obj: BrowserServerAsync):
        super().__init__(obj)

    def as_async(self) -> BrowserServerAsync:
        return self._async_obj

    @classmethod
    def _from_async(cls, obj: BrowserServerAsync) -> "BrowserServer":
        if not obj._sync_owner:
            obj._sync_owner = cls(obj)
        return obj._sync_owner

    @classmethod
    def _from_async_nullable(
        cls, obj: BrowserServerAsync = None
    ) -> typing.Optional["BrowserServer"]:
        return BrowserServer._from_async(obj) if obj else None

    @classmethod
    def _from_async_list(
        cls, items: typing.List[BrowserServerAsync]
    ) -> typing.List["BrowserServer"]:
        return list(map(lambda a: BrowserServer._from_async(a), items))

    @classmethod
    def _from_async_dict(
        cls, map: typing.Dict[str, BrowserServerAsync]
    ) -> typing.Dict[str, "BrowserServer"]:
        return {name: BrowserServer._from_async(value) for name, value in map.items()}

    @property
    def pid(self) -> str:
        return self._async_obj.pid

    @property
    def wsEndpoint(self) -> str:
        return self._async_obj.wsEndpoint

    def kill(self) -> NoneType:
        return self._sync(self._async_obj.kill())

    def close(self) -> NoneType:
        return self._sync(self._async_obj.close())


mapping.register(BrowserServerAsync, BrowserServer)


class BrowserType(SyncBase):
    def __init__(self, obj: BrowserTypeAsync):
        super().__init__(obj)

    def as_async(self) -> BrowserTypeAsync:
        return self._async_obj

    @classmethod
    def _from_async(cls, obj: BrowserTypeAsync) -> "BrowserType":
        if not obj._sync_owner:
            obj._sync_owner = cls(obj)
        return obj._sync_owner

    @classmethod
    def _from_async_nullable(
        cls, obj: BrowserTypeAsync = None
    ) -> typing.Optional["BrowserType"]:
        return BrowserType._from_async(obj) if obj else None

    @classmethod
    def _from_async_list(
        cls, items: typing.List[BrowserTypeAsync]
    ) -> typing.List["BrowserType"]:
        return list(map(lambda a: BrowserType._from_async(a), items))

    @classmethod
    def _from_async_dict(
        cls, map: typing.Dict[str, BrowserTypeAsync]
    ) -> typing.Dict[str, "BrowserType"]:
        return {name: BrowserType._from_async(value) for name, value in map.items()}

    @property
    def name(self) -> str:
        return self._async_obj.name

    @property
    def executablePath(self) -> str:
        return self._async_obj.executablePath

    def launch(
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
    ) -> "Browser":
        return Browser._from_async(
            self._sync(
                self._async_obj.launch(
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
                )
            )
        )

    def launchServer(
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
    ) -> "Browser":
        return Browser._from_async(
            self._sync(
                self._async_obj.launchServer(
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
                )
            )
        )

    def launchPersistentContext(
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
        return BrowserContext._from_async(
            self._sync(
                self._async_obj.launchPersistentContext(
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
        )

    def connect(
        self, wsEndpoint: str = None, slowMo: int = None, timeout: int = None
    ) -> "Browser":
        return Browser._from_async(
            self._sync(
                self._async_obj.connect(
                    wsEndpoint=wsEndpoint, slowMo=slowMo, timeout=timeout
                )
            )
        )


mapping.register(BrowserTypeAsync, BrowserType)


class Playwright(SyncBase):
    def __init__(self, obj: PlaywrightAsync):
        super().__init__(obj)

    def as_async(self) -> PlaywrightAsync:
        return self._async_obj

    @classmethod
    def _from_async(cls, obj: PlaywrightAsync) -> "Playwright":
        if not obj._sync_owner:
            obj._sync_owner = cls(obj)
        return obj._sync_owner

    @classmethod
    def _from_async_nullable(
        cls, obj: PlaywrightAsync = None
    ) -> typing.Optional["Playwright"]:
        return Playwright._from_async(obj) if obj else None

    @classmethod
    def _from_async_list(
        cls, items: typing.List[PlaywrightAsync]
    ) -> typing.List["Playwright"]:
        return list(map(lambda a: Playwright._from_async(a), items))

    @classmethod
    def _from_async_dict(
        cls, map: typing.Dict[str, PlaywrightAsync]
    ) -> typing.Dict[str, "Playwright"]:
        return {name: Playwright._from_async(value) for name, value in map.items()}

    @property
    def chromium(self) -> "BrowserType":
        return BrowserType._from_async(self._async_obj.chromium)

    @property
    def firefox(self) -> "BrowserType":
        return BrowserType._from_async(self._async_obj.firefox)

    @property
    def webkit(self) -> "BrowserType":
        return BrowserType._from_async(self._async_obj.webkit)

    @property
    def selectors(self) -> "Selectors":
        return Selectors._from_async(self._async_obj.selectors)

    @property
    def devices(self) -> typing.Dict[str, DeviceDescriptor]:
        return self._async_obj.devices


mapping.register(PlaywrightAsync, Playwright)
