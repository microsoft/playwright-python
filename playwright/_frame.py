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
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Union, cast

from pyee import EventEmitter

from playwright._connection import ChannelOwner, from_channel, from_nullable_channel
from playwright._element_handle import (
    ElementHandle,
    ValuesToSelect,
    convert_select_option_values,
    normalize_file_payloads,
)
from playwright._event_context_manager import EventContextManagerImpl
from playwright._helper import (
    DocumentLoadState,
    FrameNavigatedEvent,
    KeyboardModifier,
    MouseButton,
    URLMatch,
    URLMatcher,
    is_function_body,
    locals_to_params,
    monotonic_time,
)
from playwright._js_handle import (
    JSHandle,
    Serializable,
    parse_result,
    serialize_argument,
)
from playwright._network import Response
from playwright._types import Error, FilePayload, MousePosition
from playwright._wait_helper import WaitHelper

if sys.version_info >= (3, 8):  # pragma: no cover
    from typing import Literal
else:  # pragma: no cover
    from typing_extensions import Literal

if TYPE_CHECKING:  # pragma: no cover
    from playwright._page import Page


class Frame(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._parent_frame = from_nullable_channel(initializer.get("parentFrame"))
        if self._parent_frame:
            self._parent_frame._child_frames.append(self)
        self._name = initializer["name"]
        self._url = initializer["url"]
        self._detached = False
        self._child_frames: List[Frame] = []
        self._page: "Page"
        self._load_states: Set[str] = set(initializer["loadStates"])
        self._event_emitter = EventEmitter()
        self._channel.on(
            "loadstate",
            lambda params: self._on_load_state(params.get("add"), params.get("remove")),
        )
        self._channel.on(
            "navigated",
            lambda params: self._on_frame_navigated(params),
        )

    def _on_load_state(
        self, add: DocumentLoadState = None, remove: DocumentLoadState = None
    ) -> None:
        if add:
            self._load_states.add(add)
            self._event_emitter.emit("loadstate", add)
        elif remove and remove in self._load_states:
            self._load_states.remove(remove)

    def _on_frame_navigated(self, event: FrameNavigatedEvent) -> None:
        self._url = event["url"]
        self._name = event["name"]
        self._event_emitter.emit("navigated", event)
        if "error" not in event and hasattr(self, "_page") and self._page:
            self._page.emit("framenavigated", self)

    @property
    def page(self) -> "Page":
        return self._page

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

    def _setup_navigation_wait_helper(self, timeout: int = None) -> WaitHelper:
        wait_helper = WaitHelper(self._loop)
        wait_helper.reject_on_event(
            self._page, "close", Error("Navigation failed because page was closed!")
        )
        wait_helper.reject_on_event(
            self._page, "crash", Error("Navigation failed because page crashed!")
        )
        wait_helper.reject_on_event(
            self._page,
            "framedetached",
            Error("Navigating frame was detached!"),
            lambda frame: frame == self,
        )
        if timeout is None:
            timeout = self._page._timeout_settings.navigation_timeout()
        wait_helper.reject_on_timeout(timeout, f"Timeout {timeout}ms exceeded.")
        return wait_helper

    async def waitForNavigation(
        self,
        url: URLMatch = None,
        waitUntil: DocumentLoadState = None,
        timeout: int = None,
    ) -> Optional[Response]:
        if not waitUntil:
            waitUntil = "load"

        if timeout is None:
            timeout = self._page._timeout_settings.navigation_timeout()
        deadline = monotonic_time() + timeout
        wait_helper = self._setup_navigation_wait_helper(timeout)
        matcher = URLMatcher(url) if url else None

        def predicate(event: Any) -> bool:
            # Any failed navigation results in a rejection.
            if event.get("error"):
                return True
            return not matcher or matcher.matches(event["url"])

        event = await wait_helper.wait_for_event(
            self._event_emitter,
            "navigated",
            predicate=predicate,
        )
        if "error" in event:
            raise Error(event["error"])

        if waitUntil not in self._load_states:
            timeout = deadline - monotonic_time()
            if timeout > 0:
                await self.waitForLoadState(state=waitUntil, timeout=timeout)

        if "newDocument" in event and "request" in event["newDocument"]:
            request = from_channel(event["newDocument"]["request"])
            return await request.response()
        return None

    async def waitForLoadState(
        self, state: DocumentLoadState = None, timeout: int = None
    ) -> None:
        if not state:
            state = "load"
        if state not in ("load", "domcontentloaded", "networkidle"):
            raise Error("state: expected one of (load|domcontentloaded|networkidle)")
        if state in self._load_states:
            return
        wait_helper = self._setup_navigation_wait_helper(timeout)
        await wait_helper.wait_for_event(
            self._event_emitter, "loadstate", lambda s: s == state
        )

    async def frameElement(self) -> ElementHandle:
        return from_channel(await self._channel.send("frameElement"))

    async def evaluate(
        self, expression: str, arg: Serializable = None, force_expr: bool = None
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
        self, expression: str, arg: Serializable = None, force_expr: bool = None
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

    async def querySelectorAll(self, selector: str) -> List[ElementHandle]:
        return list(
            map(
                cast(ElementHandle, from_channel),
                await self._channel.send("querySelectorAll", dict(selector=selector)),
            )
        )

    async def waitForSelector(
        self,
        selector: str,
        timeout: int = None,
        state: Literal["attached", "detached", "hidden", "visible"] = None,
    ) -> Optional[ElementHandle]:
        return from_nullable_channel(
            await self._channel.send("waitForSelector", locals_to_params(locals()))
        )

    async def dispatchEvent(
        self, selector: str, type: str, eventInit: Dict = None, timeout: int = None
    ) -> None:
        await self._channel.send(
            "dispatchEvent",
            dict(selector=selector, type=type, eventInit=serialize_argument(eventInit)),
        )

    async def evalOnSelector(
        self,
        selector: str,
        expression: str,
        arg: Serializable = None,
        force_expr: bool = None,
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
        self,
        selector: str,
        expression: str,
        arg: Serializable = None,
        force_expr: bool = None,
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
        self,
        html: str,
        timeout: int = None,
        waitUntil: DocumentLoadState = None,
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
        self,
        url: str = None,
        path: Union[str, Path] = None,
        content: str = None,
        type: str = None,
    ) -> ElementHandle:
        params = locals_to_params(locals())
        if path:
            with open(path, "r") as file:
                params["content"] = file.read() + "\n//# sourceURL=" + str(Path(path))
                del params["path"]
        return from_channel(await self._channel.send("addScriptTag", params))

    async def addStyleTag(
        self, url: str = None, path: Union[str, Path] = None, content: str = None
    ) -> ElementHandle:
        params = locals_to_params(locals())
        if path:
            with open(path, "r") as file:
                params["content"] = (
                    file.read() + "\n/*# sourceURL=" + str(Path(path)) + "*/"
                )
                del params["path"]
        return from_channel(await self._channel.send("addStyleTag", params))

    async def click(
        self,
        selector: str,
        modifiers: List[KeyboardModifier] = None,
        position: MousePosition = None,
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
        position: MousePosition = None,
        delay: int = None,
        button: MouseButton = None,
        timeout: int = None,
        force: bool = None,
        noWaitAfter: bool = None,
    ) -> None:
        await self._channel.send("dblclick", locals_to_params(locals()))

    async def tap(
        self,
        selector: str,
        modifiers: List[KeyboardModifier] = None,
        position: MousePosition = None,
        timeout: int = None,
        force: bool = None,
        noWaitAfter: bool = None,
    ) -> None:
        await self._channel.send("tap", locals_to_params(locals()))

    async def fill(
        self, selector: str, value: str, timeout: int = None, noWaitAfter: bool = None
    ) -> None:
        await self._channel.send("fill", locals_to_params(locals()))

    async def focus(self, selector: str, timeout: int = None) -> None:
        await self._channel.send("focus", locals_to_params(locals()))

    async def textContent(self, selector: str, timeout: int = None) -> Optional[str]:
        return await self._channel.send("textContent", locals_to_params(locals()))

    async def innerText(self, selector: str, timeout: int = None) -> str:
        return await self._channel.send("innerText", locals_to_params(locals()))

    async def innerHTML(self, selector: str, timeout: int = None) -> str:
        return await self._channel.send("innerHTML", locals_to_params(locals()))

    async def getAttribute(
        self, selector: str, name: str, timeout: int = None
    ) -> Optional[str]:
        return await self._channel.send("getAttribute", locals_to_params(locals()))

    async def hover(
        self,
        selector: str,
        modifiers: List[KeyboardModifier] = None,
        position: MousePosition = None,
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
    ) -> List[str]:
        params = locals_to_params(locals())
        if "values" in params:
            values = params.pop("values")
            params = dict(**params, **convert_select_option_values(values))
        return await self._channel.send("selectOption", params)

    async def setInputFiles(
        self,
        selector: str,
        files: Union[str, Path, FilePayload, List[str], List[Path], List[FilePayload]],
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

    async def waitForTimeout(self, timeout: int) -> None:
        await self._connection._loop.create_task(asyncio.sleep(timeout / 1000))

    async def waitForFunction(
        self,
        expression: str,
        arg: Serializable = None,
        force_expr: bool = None,
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

    def expect_load_state(
        self,
        state: DocumentLoadState = None,
        timeout: int = None,
    ) -> EventContextManagerImpl[Optional[Response]]:
        return EventContextManagerImpl(self.waitForLoadState(state, timeout))

    def expect_navigation(
        self,
        url: URLMatch = None,
        waitUntil: DocumentLoadState = None,
        timeout: int = None,
    ) -> EventContextManagerImpl[Optional[Response]]:
        return EventContextManagerImpl(self.waitForNavigation(url, waitUntil, timeout))
