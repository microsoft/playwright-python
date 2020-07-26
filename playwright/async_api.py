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
        return mapping.from_maybe_impl(self._impl_obj.url)

    @property
    def resourceType(self) -> str:
        return mapping.from_maybe_impl(self._impl_obj.resourceType)

    @property
    def method(self) -> str:
        return mapping.from_maybe_impl(self._impl_obj.method)

    @property
    def postData(self) -> typing.Union[str, NoneType]:
        return mapping.from_maybe_impl(self._impl_obj.postData)

    @property
    def headers(self) -> typing.Dict[str, str]:
        return mapping.from_maybe_impl(self._impl_obj.headers)

    @property
    def frame(self) -> "Frame":
        return mapping.from_impl(self._impl_obj.frame)

    @property
    def redirectedFrom(self) -> typing.Union["Request", NoneType]:
        return mapping.from_impl_nullable(self._impl_obj.redirectedFrom)

    @property
    def redirectedTo(self) -> typing.Union["Request", NoneType]:
        return mapping.from_impl_nullable(self._impl_obj.redirectedTo)

    @property
    def failure(self) -> typing.Union[str, NoneType]:
        return mapping.from_maybe_impl(self._impl_obj.failure)

    async def response(self) -> typing.Union["Response", NoneType]:
        return mapping.from_impl_nullable(await self._impl_obj.response())

    def isNavigationRequest(self) -> bool:
        return mapping.from_maybe_impl(self._impl_obj.isNavigationRequest())


mapping.register(RequestImpl, Request)


class Response(AsyncBase):
    def __init__(self, obj: ResponseImpl):
        super().__init__(obj)

    @property
    def url(self) -> str:
        return mapping.from_maybe_impl(self._impl_obj.url)

    @property
    def ok(self) -> bool:
        return mapping.from_maybe_impl(self._impl_obj.ok)

    @property
    def status(self) -> int:
        return mapping.from_maybe_impl(self._impl_obj.status)

    @property
    def statusText(self) -> str:
        return mapping.from_maybe_impl(self._impl_obj.statusText)

    @property
    def headers(self) -> typing.Dict[str, str]:
        return mapping.from_maybe_impl(self._impl_obj.headers)

    @property
    def request(self) -> "Request":
        return mapping.from_impl(self._impl_obj.request)

    @property
    def frame(self) -> "Frame":
        return mapping.from_impl(self._impl_obj.frame)

    async def finished(self) -> typing.Union[Error, NoneType]:
        return mapping.from_maybe_impl(await self._impl_obj.finished())

    async def body(self) -> bytes:
        return mapping.from_maybe_impl(await self._impl_obj.body())

    async def text(self) -> str:
        return mapping.from_maybe_impl(await self._impl_obj.text())

    async def json(self) -> typing.Union[typing.Dict, typing.List]:
        return mapping.from_maybe_impl(await self._impl_obj.json())


mapping.register(ResponseImpl, Response)


class Route(AsyncBase):
    def __init__(self, obj: RouteImpl):
        super().__init__(obj)

    @property
    def request(self) -> "Request":
        return mapping.from_impl(self._impl_obj.request)

    async def abort(self, error_code: str = "failed") -> NoneType:
        return mapping.from_maybe_impl(
            await self._impl_obj.abort(error_code=error_code)
        )

    async def fulfill(
        self,
        status: int = 200,
        headers: typing.Dict[str, str] = {},
        body: typing.Union[str, bytes] = None,
        contentType: str = None,
    ) -> NoneType:
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
        return mapping.from_maybe_impl(await self._impl_obj.down(key=key))

    async def up(self, key: str) -> NoneType:
        return mapping.from_maybe_impl(await self._impl_obj.up(key=key))

    async def insertText(self, text: str) -> NoneType:
        return mapping.from_maybe_impl(await self._impl_obj.insertText(text=text))

    async def type(self, text: str, delay: int = None) -> NoneType:
        return mapping.from_maybe_impl(
            await self._impl_obj.type(text=text, delay=delay)
        )

    async def press(self, key: str, delay: int = None) -> NoneType:
        return mapping.from_maybe_impl(await self._impl_obj.press(key=key, delay=delay))


mapping.register(KeyboardImpl, Keyboard)


class Mouse(AsyncBase):
    def __init__(self, obj: MouseImpl):
        super().__init__(obj)

    async def move(self, x: float, y: float, steps: int = None) -> NoneType:
        return mapping.from_maybe_impl(await self._impl_obj.move(x=x, y=y, steps=steps))

    async def down(
        self, button: Literal["left", "right", "middle"] = None, clickCount: int = None
    ) -> NoneType:
        return mapping.from_maybe_impl(
            await self._impl_obj.down(button=button, clickCount=clickCount)
        )

    async def up(
        self, button: Literal["left", "right", "middle"] = None, clickCount: int = None
    ) -> NoneType:
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
        return mapping.from_maybe_impl(
            await self._impl_obj.evaluate(
                expression=expression, arg=mapping.to_impl(arg), force_expr=force_expr
            )
        )

    async def evaluateHandle(
        self, expression: str, arg: typing.Any = None, force_expr: bool = False
    ) -> "JSHandle":
        return mapping.from_impl(
            await self._impl_obj.evaluateHandle(
                expression=expression, arg=mapping.to_impl(arg), force_expr=force_expr
            )
        )

    async def getProperty(self, name: str) -> "JSHandle":
        return mapping.from_impl(await self._impl_obj.getProperty(name=name))

    async def getProperties(self) -> typing.Dict[str, "JSHandle"]:
        return mapping.from_impl_dict(await self._impl_obj.getProperties())

    def asElement(self) -> typing.Union["ElementHandle", NoneType]:
        return mapping.from_impl_nullable(self._impl_obj.asElement())

    async def dispose(self) -> NoneType:
        return mapping.from_maybe_impl(await self._impl_obj.dispose())

    async def jsonValue(self) -> typing.Any:
        return mapping.from_maybe_impl(await self._impl_obj.jsonValue())


mapping.register(JSHandleImpl, JSHandle)


class ElementHandle(JSHandle):
    def __init__(self, obj: ElementHandleImpl):
        super().__init__(obj)

    def asElement(self) -> typing.Union["ElementHandle", NoneType]:
        return mapping.from_impl_nullable(self._impl_obj.asElement())

    async def ownerFrame(self) -> typing.Union["Frame", NoneType]:
        return mapping.from_impl_nullable(await self._impl_obj.ownerFrame())

    async def contentFrame(self) -> typing.Union["Frame", NoneType]:
        return mapping.from_impl_nullable(await self._impl_obj.contentFrame())

    async def getAttribute(self, name: str) -> str:
        return mapping.from_maybe_impl(await self._impl_obj.getAttribute(name=name))

    async def textContent(self) -> str:
        return mapping.from_maybe_impl(await self._impl_obj.textContent())

    async def innerText(self) -> str:
        return mapping.from_maybe_impl(await self._impl_obj.innerText())

    async def innerHTML(self) -> str:
        return mapping.from_maybe_impl(await self._impl_obj.innerHTML())

    async def dispatchEvent(self, type: str, eventInit: typing.Dict = None) -> NoneType:
        return mapping.from_maybe_impl(
            await self._impl_obj.dispatchEvent(type=type, eventInit=eventInit)
        )

    async def scrollIntoViewIfNeeded(self, timeout: int = None) -> NoneType:
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
        return mapping.from_maybe_impl(
            await self._impl_obj.selectOption(
                values=mapping.to_impl(values), timeout=timeout, noWaitAfter=noWaitAfter
            )
        )

    async def fill(
        self, value: str, timeout: int = None, noWaitAfter: bool = None
    ) -> NoneType:
        return mapping.from_maybe_impl(
            await self._impl_obj.fill(
                value=value, timeout=timeout, noWaitAfter=noWaitAfter
            )
        )

    async def selectText(self, timeout: int = None) -> NoneType:
        return mapping.from_maybe_impl(await self._impl_obj.selectText(timeout=timeout))

    async def setInputFiles(
        self,
        files: typing.Union[
            str, FilePayload, typing.List[str], typing.List[FilePayload]
        ],
        timeout: int = None,
        noWaitAfter: bool = None,
    ) -> NoneType:
        return mapping.from_maybe_impl(
            await self._impl_obj.setInputFiles(
                files=files, timeout=timeout, noWaitAfter=noWaitAfter
            )
        )

    async def focus(self) -> NoneType:
        return mapping.from_maybe_impl(await self._impl_obj.focus())

    async def type(
        self,
        text: str,
        delay: int = None,
        timeout: int = None,
        noWaitAfter: bool = None,
    ) -> NoneType:
        return mapping.from_maybe_impl(
            await self._impl_obj.type(
                text=text, delay=delay, timeout=timeout, noWaitAfter=noWaitAfter
            )
        )

    async def press(
        self, key: str, delay: int = None, timeout: int = None, noWaitAfter: bool = None
    ) -> NoneType:
        return mapping.from_maybe_impl(
            await self._impl_obj.press(
                key=key, delay=delay, timeout=timeout, noWaitAfter=noWaitAfter
            )
        )

    async def check(
        self, timeout: int = None, force: bool = None, noWaitAfter: bool = None
    ) -> NoneType:
        return mapping.from_maybe_impl(
            await self._impl_obj.check(
                timeout=timeout, force=force, noWaitAfter=noWaitAfter
            )
        )

    async def uncheck(
        self, timeout: int = None, force: bool = None, noWaitAfter: bool = None
    ) -> NoneType:
        return mapping.from_maybe_impl(
            await self._impl_obj.uncheck(
                timeout=timeout, force=force, noWaitAfter=noWaitAfter
            )
        )

    async def boundingBox(self) -> typing.Dict[str, float]:
        return mapping.from_maybe_impl(await self._impl_obj.boundingBox())

    async def screenshot(
        self,
        timeout: int = None,
        type: Literal["png", "jpeg"] = None,
        path: str = None,
        quality: int = None,
        omitBackground: bool = None,
    ) -> bytes:
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
        return mapping.from_impl_nullable(
            await self._impl_obj.querySelector(selector=selector)
        )

    async def querySelectorAll(self, selector: str) -> typing.List["ElementHandle"]:
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
        return mapping.from_impl(self._impl_obj.page)

    @property
    def element(self) -> "ElementHandle":
        return mapping.from_impl(self._impl_obj.element)

    @property
    def isMultiple(self) -> bool:
        return mapping.from_maybe_impl(self._impl_obj.isMultiple)

    async def setFiles(
        self,
        files: typing.Union[
            str, FilePayload, typing.List[str], typing.List[FilePayload]
        ],
        timeout: int = None,
        noWaitAfter: bool = None,
    ) -> NoneType:
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
        return mapping.from_maybe_impl(self._impl_obj.name)

    @property
    def url(self) -> str:
        return mapping.from_maybe_impl(self._impl_obj.url)

    @property
    def parentFrame(self) -> typing.Union["Frame", NoneType]:
        return mapping.from_impl_nullable(self._impl_obj.parentFrame)

    @property
    def childFrames(self) -> typing.List["Frame"]:
        return mapping.from_impl_list(self._impl_obj.childFrames)

    async def goto(
        self,
        url: str,
        timeout: int = None,
        waitUntil: Literal["load", "domcontentloaded", "networkidle"] = "load",
        referer: str = None,
    ) -> typing.Union["Response", NoneType]:
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
        return mapping.from_maybe_impl(
            await self._impl_obj.waitForLoadState(state=state, timeout=timeout)
        )

    async def frameElement(self) -> "ElementHandle":
        return mapping.from_impl(await self._impl_obj.frameElement())

    async def evaluate(
        self, expression: str, arg: typing.Any = None, force_expr: bool = False
    ) -> typing.Any:
        return mapping.from_maybe_impl(
            await self._impl_obj.evaluate(
                expression=expression, arg=mapping.to_impl(arg), force_expr=force_expr
            )
        )

    async def evaluateHandle(
        self, expression: str, arg: typing.Any = None, force_expr: bool = False
    ) -> "JSHandle":
        return mapping.from_impl(
            await self._impl_obj.evaluateHandle(
                expression=expression, arg=mapping.to_impl(arg), force_expr=force_expr
            )
        )

    async def querySelector(
        self, selector: str
    ) -> typing.Union["ElementHandle", NoneType]:
        return mapping.from_impl_nullable(
            await self._impl_obj.querySelector(selector=selector)
        )

    async def querySelectorAll(self, selector: str) -> typing.List["ElementHandle"]:
        return mapping.from_impl_list(
            await self._impl_obj.querySelectorAll(selector=selector)
        )

    async def waitForSelector(
        self,
        selector: str,
        timeout: int = None,
        state: Literal["attached", "detached", "visible", "hidden"] = None,
    ) -> typing.Union["ElementHandle", NoneType]:
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
        return mapping.from_maybe_impl(
            await self._impl_obj.evalOnSelectorAll(
                selector=selector,
                expression=expression,
                arg=mapping.to_impl(arg),
                force_expr=force_expr,
            )
        )

    async def content(self) -> str:
        return mapping.from_maybe_impl(await self._impl_obj.content())

    async def setContent(
        self,
        html: str,
        timeout: int = None,
        waitUntil: Literal["load", "domcontentloaded", "networkidle"] = None,
    ) -> NoneType:
        return mapping.from_maybe_impl(
            await self._impl_obj.setContent(
                html=html, timeout=timeout, waitUntil=waitUntil
            )
        )

    def isDetached(self) -> bool:
        return mapping.from_maybe_impl(self._impl_obj.isDetached())

    async def addScriptTag(
        self, url: str = None, path: str = None, content: str = None, type: str = None
    ) -> "ElementHandle":
        return mapping.from_impl(
            await self._impl_obj.addScriptTag(
                url=url, path=path, content=content, type=type
            )
        )

    async def addStyleTag(
        self, url: str = None, path: str = None, content: str = None
    ) -> "ElementHandle":
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
        return mapping.from_maybe_impl(
            await self._impl_obj.fill(
                selector=selector, value=value, timeout=timeout, noWaitAfter=noWaitAfter
            )
        )

    async def focus(self, selector: str, timeout: int = None) -> NoneType:
        return mapping.from_maybe_impl(
            await self._impl_obj.focus(selector=selector, timeout=timeout)
        )

    async def textContent(self, selector: str, timeout: int = None) -> str:
        return mapping.from_maybe_impl(
            await self._impl_obj.textContent(selector=selector, timeout=timeout)
        )

    async def innerText(self, selector: str, timeout: int = None) -> str:
        return mapping.from_maybe_impl(
            await self._impl_obj.innerText(selector=selector, timeout=timeout)
        )

    async def innerHTML(self, selector: str, timeout: int = None) -> str:
        return mapping.from_maybe_impl(
            await self._impl_obj.innerHTML(selector=selector, timeout=timeout)
        )

    async def getAttribute(self, selector: str, name: str, timeout: int = None) -> str:
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
        return mapping.from_maybe_impl(
            await self._impl_obj.uncheck(
                selector=selector, timeout=timeout, force=force, noWaitAfter=noWaitAfter
            )
        )

    async def waitForTimeout(self, timeout: int) -> typing.Awaitable[NoneType]:
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
        return mapping.from_maybe_impl(await self._impl_obj.title())


mapping.register(FrameImpl, Frame)


class Worker(AsyncBase):
    def __init__(self, obj: WorkerImpl):
        super().__init__(obj)

    @property
    def url(self) -> str:
        return mapping.from_maybe_impl(self._impl_obj.url)

    async def evaluate(
        self, expression: str, arg: typing.Any = None, force_expr: bool = False
    ) -> typing.Any:
        return mapping.from_maybe_impl(
            await self._impl_obj.evaluate(
                expression=expression, arg=mapping.to_impl(arg), force_expr=force_expr
            )
        )

    async def evaluateHandle(
        self, expression: str, arg: typing.Any = None, force_expr: bool = False
    ) -> "JSHandle":
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
        return mapping.from_maybe_impl(self._impl_obj.type)

    @property
    def text(self) -> str:
        return mapping.from_maybe_impl(self._impl_obj.text)

    @property
    def args(self) -> typing.List["JSHandle"]:
        return mapping.from_impl_list(self._impl_obj.args)

    @property
    def location(self) -> ConsoleMessageLocation:
        return mapping.from_maybe_impl(self._impl_obj.location)


mapping.register(ConsoleMessageImpl, ConsoleMessage)


class Dialog(AsyncBase):
    def __init__(self, obj: DialogImpl):
        super().__init__(obj)

    @property
    def type(self) -> str:
        return mapping.from_maybe_impl(self._impl_obj.type)

    @property
    def message(self) -> str:
        return mapping.from_maybe_impl(self._impl_obj.message)

    @property
    def defaultValue(self) -> str:
        return mapping.from_maybe_impl(self._impl_obj.defaultValue)

    async def accept(self, prompt_text: str = None) -> NoneType:
        return mapping.from_maybe_impl(
            await self._impl_obj.accept(prompt_text=prompt_text)
        )

    async def dismiss(self) -> NoneType:
        return mapping.from_maybe_impl(await self._impl_obj.dismiss())


mapping.register(DialogImpl, Dialog)


class Download(AsyncBase):
    def __init__(self, obj: DownloadImpl):
        super().__init__(obj)

    @property
    def url(self) -> str:
        return mapping.from_maybe_impl(self._impl_obj.url)

    @property
    def suggestedFilename(self) -> str:
        return mapping.from_maybe_impl(self._impl_obj.suggestedFilename)

    async def delete(self) -> NoneType:
        return mapping.from_maybe_impl(await self._impl_obj.delete())

    async def failure(self) -> typing.Union[str, NoneType]:
        return mapping.from_maybe_impl(await self._impl_obj.failure())

    async def path(self) -> typing.Union[str, NoneType]:
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
        return mapping.from_impl(self._impl_obj.accessibility)

    @property
    def keyboard(self) -> "Keyboard":
        return mapping.from_impl(self._impl_obj.keyboard)

    @property
    def mouse(self) -> "Mouse":
        return mapping.from_impl(self._impl_obj.mouse)

    @property
    def context(self) -> "BrowserContext":
        return mapping.from_impl(self._impl_obj.context)

    @property
    def mainFrame(self) -> "Frame":
        return mapping.from_impl(self._impl_obj.mainFrame)

    @property
    def frames(self) -> typing.List["Frame"]:
        return mapping.from_impl_list(self._impl_obj.frames)

    @property
    def url(self) -> str:
        return mapping.from_maybe_impl(self._impl_obj.url)

    @property
    def workers(self) -> typing.List["Worker"]:
        return mapping.from_impl_list(self._impl_obj.workers)

    async def opener(self) -> typing.Union["Page", NoneType]:
        return mapping.from_impl_nullable(await self._impl_obj.opener())

    def frame(
        self,
        name: str = None,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]] = None,
    ) -> typing.Union["Frame", NoneType]:
        return mapping.from_impl_nullable(
            self._impl_obj.frame(name=name, url=self._wrap_handler(url))
        )

    def setDefaultNavigationTimeout(self, timeout: int) -> NoneType:
        return mapping.from_maybe_impl(
            self._impl_obj.setDefaultNavigationTimeout(timeout=timeout)
        )

    def setDefaultTimeout(self, timeout: int) -> NoneType:
        return mapping.from_maybe_impl(
            self._impl_obj.setDefaultTimeout(timeout=timeout)
        )

    async def querySelector(
        self, selector: str
    ) -> typing.Union["ElementHandle", NoneType]:
        return mapping.from_impl_nullable(
            await self._impl_obj.querySelector(selector=selector)
        )

    async def querySelectorAll(self, selector: str) -> typing.List["ElementHandle"]:
        return mapping.from_impl_list(
            await self._impl_obj.querySelectorAll(selector=selector)
        )

    async def waitForSelector(
        self,
        selector: str,
        timeout: int = None,
        state: Literal["attached", "detached", "visible", "hidden"] = None,
    ) -> typing.Union["ElementHandle", NoneType]:
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
        return mapping.from_maybe_impl(
            await self._impl_obj.dispatchEvent(
                selector=selector, type=type, eventInit=eventInit, timeout=timeout
            )
        )

    async def evaluate(
        self, expression: str, arg: typing.Any = None, force_expr: bool = False
    ) -> typing.Any:
        return mapping.from_maybe_impl(
            await self._impl_obj.evaluate(
                expression=expression, arg=mapping.to_impl(arg), force_expr=force_expr
            )
        )

    async def evaluateHandle(
        self, expression: str, arg: typing.Any = None, force_expr: bool = False
    ) -> "JSHandle":
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
        return mapping.from_impl(
            await self._impl_obj.addScriptTag(
                url=url, path=path, content=content, type=type
            )
        )

    async def addStyleTag(
        self, url: str = None, path: str = None, content: str = None
    ) -> "ElementHandle":
        return mapping.from_impl(
            await self._impl_obj.addStyleTag(url=url, path=path, content=content)
        )

    async def exposeFunction(
        self, name: str, binding: typing.Callable[..., typing.Any]
    ) -> NoneType:
        return mapping.from_maybe_impl(
            await self._impl_obj.exposeFunction(
                name=name, binding=self._wrap_handler(binding)
            )
        )

    async def exposeBinding(
        self, name: str, binding: typing.Callable[[typing.Dict], typing.Any]
    ) -> NoneType:
        return mapping.from_maybe_impl(
            await self._impl_obj.exposeBinding(
                name=name, binding=self._wrap_handler(binding)
            )
        )

    async def setExtraHTTPHeaders(self, headers: typing.Dict) -> NoneType:
        return mapping.from_maybe_impl(
            await self._impl_obj.setExtraHTTPHeaders(headers=headers)
        )

    async def content(self) -> str:
        return mapping.from_maybe_impl(await self._impl_obj.content())

    async def setContent(
        self,
        html: str,
        timeout: int = None,
        waitUntil: Literal["load", "domcontentloaded", "networkidle"] = None,
    ) -> NoneType:
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
        return mapping.from_impl_nullable(
            await self._impl_obj.reload(timeout=timeout, waitUntil=waitUntil)
        )

    async def waitForLoadState(
        self,
        state: Literal["load", "domcontentloaded", "networkidle"] = "load",
        timeout: int = None,
    ) -> NoneType:
        return mapping.from_maybe_impl(
            await self._impl_obj.waitForLoadState(state=state, timeout=timeout)
        )

    async def waitForNavigation(
        self,
        timeout: int = None,
        waitUntil: Literal["load", "domcontentloaded", "networkidle"] = "load",
        url: str = None,
    ) -> typing.Union["Response", NoneType]:
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
        return mapping.from_impl_nullable(
            await self._impl_obj.goBack(timeout=timeout, waitUntil=waitUntil)
        )

    async def goForward(
        self,
        timeout: int = None,
        waitUntil: Literal["load", "domcontentloaded", "networkidle"] = None,
    ) -> typing.Union["Response", NoneType]:
        return mapping.from_impl_nullable(
            await self._impl_obj.goForward(timeout=timeout, waitUntil=waitUntil)
        )

    async def emulateMedia(
        self,
        media: Literal["screen", "print"] = None,
        colorScheme: Literal["light", "dark", "no-preference"] = None,
    ) -> NoneType:
        return mapping.from_maybe_impl(
            await self._impl_obj.emulateMedia(media=media, colorScheme=colorScheme)
        )

    async def setViewportSize(self, width: int, height: int) -> NoneType:
        return mapping.from_maybe_impl(
            await self._impl_obj.setViewportSize(width=width, height=height)
        )

    def viewportSize(self) -> typing.Union[Viewport, NoneType]:
        return mapping.from_maybe_impl(self._impl_obj.viewportSize())

    async def addInitScript(self, source: str = None, path: str = None) -> NoneType:
        return mapping.from_maybe_impl(
            await self._impl_obj.addInitScript(source=source, path=path)
        )

    async def route(
        self,
        url: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]],
        handler: typing.Callable[["Route", "Request"], typing.Any],
    ) -> NoneType:
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
        return mapping.from_maybe_impl(await self._impl_obj.title())

    async def close(self, runBeforeUnload: bool = None) -> NoneType:
        return mapping.from_maybe_impl(
            await self._impl_obj.close(runBeforeUnload=runBeforeUnload)
        )

    def isClosed(self) -> bool:
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
        return mapping.from_maybe_impl(
            await self._impl_obj.fill(
                selector=selector, value=value, timeout=timeout, noWaitAfter=noWaitAfter
            )
        )

    async def focus(self, selector: str, timeout: int = None) -> NoneType:
        return mapping.from_maybe_impl(
            await self._impl_obj.focus(selector=selector, timeout=timeout)
        )

    async def textContent(self, selector: str, timeout: int = None) -> str:
        return mapping.from_maybe_impl(
            await self._impl_obj.textContent(selector=selector, timeout=timeout)
        )

    async def innerText(self, selector: str, timeout: int = None) -> str:
        return mapping.from_maybe_impl(
            await self._impl_obj.innerText(selector=selector, timeout=timeout)
        )

    async def innerHTML(self, selector: str, timeout: int = None) -> str:
        return mapping.from_maybe_impl(
            await self._impl_obj.innerHTML(selector=selector, timeout=timeout)
        )

    async def getAttribute(self, selector: str, name: str, timeout: int = None) -> str:
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
        return mapping.from_maybe_impl(
            await self._impl_obj.uncheck(
                selector=selector, timeout=timeout, force=force, noWaitAfter=noWaitAfter
            )
        )

    async def waitForTimeout(self, timeout: int) -> typing.Awaitable[NoneType]:
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
        return mapping.from_impl_list(self._impl_obj.pages)

    def setDefaultNavigationTimeout(self, timeout: int) -> NoneType:
        return mapping.from_maybe_impl(
            self._impl_obj.setDefaultNavigationTimeout(timeout=timeout)
        )

    def setDefaultTimeout(self, timeout: int) -> NoneType:
        return mapping.from_maybe_impl(
            self._impl_obj.setDefaultTimeout(timeout=timeout)
        )

    async def newPage(self) -> "Page":
        return mapping.from_impl(await self._impl_obj.newPage())

    async def cookies(
        self, urls: typing.Union[str, typing.List[str]]
    ) -> typing.List[typing.List[typing.Dict[str, typing.Union[str, int, bool]]]]:
        return mapping.from_maybe_impl(await self._impl_obj.cookies(urls=urls))

    async def addCookies(
        self,
        cookies: typing.List[
            typing.List[typing.Dict[str, typing.Union[str, int, bool]]]
        ],
    ) -> NoneType:
        return mapping.from_maybe_impl(await self._impl_obj.addCookies(cookies=cookies))

    async def clearCookies(self) -> NoneType:
        return mapping.from_maybe_impl(await self._impl_obj.clearCookies())

    async def grantPermissions(
        self, permissions: typing.List[str], origin: str = None
    ) -> NoneType:
        return mapping.from_maybe_impl(
            await self._impl_obj.grantPermissions(
                permissions=permissions, origin=origin
            )
        )

    async def clearPermissions(self) -> NoneType:
        return mapping.from_maybe_impl(await self._impl_obj.clearPermissions())

    async def setGeolocation(self, geolocation: typing.Dict) -> NoneType:
        return mapping.from_maybe_impl(
            await self._impl_obj.setGeolocation(geolocation=geolocation)
        )

    async def setExtraHTTPHeaders(self, headers: typing.Dict) -> NoneType:
        return mapping.from_maybe_impl(
            await self._impl_obj.setExtraHTTPHeaders(headers=headers)
        )

    async def setOffline(self, offline: bool) -> NoneType:
        return mapping.from_maybe_impl(await self._impl_obj.setOffline(offline=offline))

    async def addInitScript(self, source: str = None, path: str = None) -> NoneType:
        return mapping.from_maybe_impl(
            await self._impl_obj.addInitScript(source=source, path=path)
        )

    async def exposeBinding(
        self, name: str, binding: typing.Callable[[typing.Dict], typing.Any]
    ) -> NoneType:
        return mapping.from_maybe_impl(
            await self._impl_obj.exposeBinding(
                name=name, binding=self._wrap_handler(binding)
            )
        )

    async def exposeFunction(
        self, name: str, binding: typing.Callable[..., typing.Any]
    ) -> NoneType:
        return mapping.from_maybe_impl(
            await self._impl_obj.exposeFunction(
                name=name, binding=self._wrap_handler(binding)
            )
        )

    async def route(
        self,
        match: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]],
        handler: typing.Callable[["Route", "Request"], typing.Any],
    ) -> NoneType:
        return mapping.from_maybe_impl(
            await self._impl_obj.route(
                match=self._wrap_handler(match), handler=self._wrap_handler(handler)
            )
        )

    async def unroute(
        self,
        match: typing.Union[str, typing.Pattern, typing.Callable[[str], bool]],
        handler: typing.Union[typing.Callable[["Route", "Request"], typing.Any]] = None,
    ) -> NoneType:
        return mapping.from_maybe_impl(
            await self._impl_obj.unroute(
                match=self._wrap_handler(match), handler=self._wrap_handler(handler)
            )
        )

    async def waitForEvent(
        self,
        event: str,
        predicate: typing.Union[typing.Callable[[typing.Any], bool]] = None,
        timeout: int = None,
    ) -> typing.Any:
        return mapping.from_maybe_impl(
            await self._impl_obj.waitForEvent(
                event=event, predicate=self._wrap_handler(predicate), timeout=timeout
            )
        )

    async def close(self) -> NoneType:
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
        return mapping.from_impl_list(self._impl_obj.contexts)

    def isConnected(self) -> bool:
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
        return mapping.from_maybe_impl(self._impl_obj.wsEndpoint)

    async def kill(self) -> NoneType:
        return mapping.from_maybe_impl(await self._impl_obj.kill())

    async def close(self) -> NoneType:
        return mapping.from_maybe_impl(await self._impl_obj.close())


mapping.register(BrowserServerImpl, BrowserServer)


class BrowserType(AsyncBase):
    def __init__(self, obj: BrowserTypeImpl):
        super().__init__(obj)

    @property
    def name(self) -> str:
        return mapping.from_maybe_impl(self._impl_obj.name)

    @property
    def executablePath(self) -> str:
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


mapping.register(PlaywrightImpl, Playwright)
