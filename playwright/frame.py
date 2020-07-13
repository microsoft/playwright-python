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
import sys
from playwright.connection import (
    ChannelOwner,
    ConnectionScope,
    from_channel,
    from_nullable_channel,
)
from playwright.element_handle import (
    ElementHandle,
    convertSelectOptionValues,
    ValuesToSelect,
)
from playwright.helper import (
    FilePayload,
    is_function_body,
    locals_to_params,
    KeyboardModifier,
    MouseButton,
    DocumentLoadState,
)
from playwright.js_handle import JSHandle, parse_result, serialize_argument
from playwright.network import Response
from playwright.serializers import normalize_file_payloads
from typing import Any, Awaitable, Dict, List, Optional, Union, TYPE_CHECKING, cast

if sys.version_info >= (3, 8):  # pragma: no cover
    from typing import Literal
else:  # pragma: no cover
    from typing_extensions import Literal

if TYPE_CHECKING:  # pragma: no cover
    from playwright.page import Page


class Frame(ChannelOwner):
    def __init__(self, scope: ConnectionScope, guid: str, initializer: Dict) -> None:
        super().__init__(scope, guid, initializer)
        self._parent_frame = from_nullable_channel(initializer["parentFrame"])
        if self._parent_frame:
            self._parent_frame._child_frames.append(self)
        self._name = initializer["name"]
        self._url = initializer["url"]
        self._detached = False
        self._child_frames: List[Frame] = list()
        self._page: Optional["Page"]

    async def goto(
        self,
        url: str,
        timeout: int = None,
        waitUntil: DocumentLoadState = None,
        referer: str = None,
    ) -> Optional[Response]:
        return cast(
            Optional[Response],
            from_nullable_channel(
                await self._channel.send("goto", locals_to_params(locals()))
            ),
        )

    async def waitForNavigation(
        self,
        timeout: int = None,
        waitUntil: DocumentLoadState = None,
        url: str = None,  # TODO: add url, callback
    ) -> Optional[Response]:
        return cast(
            Optional[Response],
            from_nullable_channel(
                await self._channel.send(
                    "waitForNavigation", locals_to_params(locals())
                )
            ),
        )

    async def waitForLoadState(self, state: str = "load", timeout: int = None) -> None:
        await self._channel.send("waitForLoadState", locals_to_params(locals()))

    async def frameElement(self) -> ElementHandle:
        return from_channel(await self._channel.send("frameElement"))

    async def evaluate(
        self, expression: str, arg: Any = None, force_expr: bool = False
    ) -> Any:
        if not is_function_body(expression):
            force_expr = True
        return parse_result(
            await self._channel.send(
                "evaluateExpression",
                dict(
                    expression=expression,
                    isFunction=not (force_expr),
                    arg=serialize_argument(arg),
                ),
            )
        )

    async def evaluateHandle(
        self, expression: str, arg: Any = None, force_expr: bool = False
    ) -> JSHandle:
        if not is_function_body(expression):
            force_expr = True
        return from_channel(
            await self._channel.send(
                "evaluateExpressionHandle",
                dict(
                    expression=expression,
                    isFunction=not (force_expr),
                    arg=serialize_argument(arg),
                ),
            )
        )

    async def querySelector(self, selector: str) -> Optional[ElementHandle]:
        return from_nullable_channel(
            await self._channel.send("querySelector", dict(selector=selector))
        )

    async def waitForSelector(
        self,
        selector: str,
        timeout: int = None,
        state: Literal["attached", "detached", "visible", "hidden"] = None,
    ) -> Optional[ElementHandle]:
        return from_nullable_channel(
            await self._channel.send("waitForSelector", locals_to_params(locals()))
        )

    async def dispatchEvent(
        self, selector: str, type: str, eventInit: Dict = None, timeout: int = None
    ) -> None:
        await self._channel.send(
            "dispatchEvent", dict(selector=selector, type=type, eventInit=eventInit)
        )

    async def evalOnSelector(
        self, selector: str, expression: str, arg: Any = None, force_expr: bool = False
    ) -> Any:
        return parse_result(
            await self._channel.send(
                "evalOnSelector",
                dict(
                    selector=selector,
                    expression=expression,
                    isFunction=not (force_expr),
                    arg=serialize_argument(arg),
                ),
            )
        )

    async def evalOnSelectorAll(
        self, selector: str, expression: str, arg: Any = None, force_expr: bool = False
    ) -> Any:
        return parse_result(
            await self._channel.send(
                "evalOnSelectorAll",
                dict(
                    selector=selector,
                    expression=expression,
                    isFunction=not (force_expr),
                    arg=serialize_argument(arg),
                ),
            )
        )

    async def content(self) -> str:
        return await self._channel.send("content")

    async def setContent(
        self, html: str, timeout: int = None, waitUntil: DocumentLoadState = None,
    ) -> None:
        await self._channel.send("setContent", locals_to_params(locals()))

    @property
    def name(self) -> str:
        return self._name or ""

    @property
    def url(self) -> str:
        return self._url or ""

    @property
    def parentFrame(self) -> Optional["Frame"]:
        return self._parent_frame

    @property
    def childFrames(self) -> List["Frame"]:
        return self._child_frames.copy()

    def isDetached(self) -> bool:
        return self._detached

    async def addScriptTag(
        self, url: str = None, path: str = None, content: str = None, type: str = None,
    ) -> ElementHandle:
        return from_channel(
            await self._channel.send("addScriptTag", locals_to_params(locals()))
        )

    async def addStyleTag(
        self, url: str = None, path: str = None, content: str = None
    ) -> ElementHandle:
        return from_channel(
            await self._channel.send("addStyleTag", locals_to_params(locals()))
        )

    async def click(
        self,
        selector: str,
        modifiers: List[KeyboardModifier] = None,
        position: Dict = None,
        delay: int = None,
        button: MouseButton = None,
        clickCount: int = None,
        timeout: int = None,
        force: bool = None,
        noWaitAfter: bool = None,
    ) -> None:
        await self._channel.send("click", locals_to_params(locals()))

    async def dblclick(
        self,
        selector: str,
        modifiers: List[KeyboardModifier] = None,
        position: Dict = None,
        delay: int = None,
        button: MouseButton = None,
        timeout: int = None,
        force: bool = None,
    ) -> None:
        await self._channel.send("dblclick", locals_to_params(locals()))

    async def fill(
        self, selector: str, value: str, timeout: int = None, noWaitAfter: bool = None
    ) -> None:
        await self._channel.send("fill", locals_to_params(locals()))

    async def focus(self, selector: str, timeout: int = None) -> None:
        await self._channel.send("focus", locals_to_params(locals()))

    async def textContent(self, selector: str, timeout: int = None) -> str:
        return await self._channel.send("textContent", locals_to_params(locals()))

    async def innerText(self, selector: str, timeout: int = None) -> str:
        return await self._channel.send("innerText", locals_to_params(locals()))

    async def innerHTML(self, selector: str, timeout: int = None) -> str:
        return await self._channel.send("innerHTML", locals_to_params(locals()))

    async def getAttribute(self, selector: str, name: str, timeout: int = None) -> str:
        return await self._channel.send("getAttribute", locals_to_params(locals()))

    async def hover(
        self,
        selector: str,
        modifiers: List[KeyboardModifier] = None,
        position: Dict = None,
        timeout: int = None,
        force: bool = None,
    ) -> None:
        await self._channel.send("hover", locals_to_params(locals()))

    async def selectOption(
        self,
        selector: str,
        values: ValuesToSelect,
        timeout: int = None,
        noWaitAfter: bool = None,
    ) -> None:
        return await self._channel.send(
            "selectOption",
            dict(
                selector=selector,
                values=convertSelectOptionValues(values),
                timeout=timeout,
                noWaitAfter=noWaitAfter,
            ),
        )

    async def setInputFiles(
        self,
        selector: str,
        files: Union[str, FilePayload, List[Union[str, FilePayload]]],
        timeout: int = None,
        noWaitAfter: bool = None,
    ) -> None:
        params = locals_to_params(locals())
        params["files"] = normalize_file_payloads(files)
        await self._channel.send("setInputFiles", params)

    async def type(
        self,
        selector: str,
        text: str,
        delay: int = None,
        timeout: int = None,
        noWaitAfter: bool = None,
    ) -> None:
        await self._channel.send("type", locals_to_params(locals()))

    async def press(
        self,
        selector: str,
        key: str,
        delay: int = None,
        timeout: int = None,
        noWaitAfter: bool = None,
    ) -> None:
        await self._channel.send("press", locals_to_params(locals()))

    async def check(
        self,
        selector: str,
        timeout: int = None,
        force: bool = None,
        noWaitAfter: bool = None,
    ) -> None:
        await self._channel.send("check", locals_to_params(locals()))

    async def uncheck(
        self,
        selector: str,
        timeout: int = None,
        force: bool = None,
        noWaitAfter: bool = None,
    ) -> None:
        await self._channel.send("uncheck", locals_to_params(locals()))

    async def waitForTimeout(self, timeout: int) -> Awaitable[None]:
        return self._scope._loop.create_task(asyncio.sleep(timeout / 1000))

    async def waitForFunction(
        self,
        expression: str,
        arg: Any = None,
        force_expr: bool = False,
        timeout: int = None,
        polling: Union[int, Literal["raf"]] = None,
    ) -> JSHandle:
        if not is_function_body(expression):
            force_expr = True
        params = locals_to_params(locals())
        params["isFunction"] = not (force_expr)
        params["arg"] = serialize_argument(arg)
        return from_channel(await self._channel.send("waitForFunction", params))

    async def title(self) -> str:
        return await self._channel.send("title")
