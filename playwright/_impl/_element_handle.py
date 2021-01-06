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

import base64
import sys
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
    cast,
)

from playwright._impl._api_types import FilePayload, FloatRect, filter_out_none
from playwright._impl._connection import ChannelOwner, from_nullable_channel
from playwright._impl._file_chooser import normalize_file_payloads
from playwright._impl._helper import KeyboardModifier, MouseButton, locals_to_params
from playwright._impl._js_handle import (
    JSHandle,
    Serializable,
    parse_result,
    serialize_argument,
)

if sys.version_info >= (3, 8):  # pragma: no cover
    from typing import Literal
else:  # pragma: no cover
    from typing_extensions import Literal

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._frame import Frame


class ElementHandle(JSHandle):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)

    async def _createSelectorForTest(self, name: str) -> Optional[str]:
        return await self._channel.send("createSelectorForTest", dict(name=name))

    def asElement(self) -> Optional["ElementHandle"]:
        return self

    async def ownerFrame(self) -> Optional["Frame"]:
        return from_nullable_channel(await self._channel.send("ownerFrame"))

    async def contentFrame(self) -> Optional["Frame"]:
        return from_nullable_channel(await self._channel.send("contentFrame"))

    async def getAttribute(self, name: str) -> Optional[str]:
        return await self._channel.send("getAttribute", dict(name=name))

    async def textContent(self) -> Optional[str]:
        return await self._channel.send("textContent")

    async def innerText(self) -> str:
        return await self._channel.send("innerText")

    async def innerHTML(self) -> str:
        return await self._channel.send("innerHTML")

    async def dispatchEvent(self, type: str, eventInit: Dict = None) -> None:
        await self._channel.send(
            "dispatchEvent", dict(type=type, eventInit=serialize_argument(eventInit))
        )

    async def scrollIntoViewIfNeeded(self, timeout: float = None) -> None:
        await self._channel.send("scrollIntoViewIfNeeded", locals_to_params(locals()))

    async def hover(
        self,
        modifiers: List[KeyboardModifier] = None,
        position: Tuple[float, float] = None,
        timeout: float = None,
        force: bool = None,
    ) -> None:
        await self._channel.send("hover", locals_to_params(locals()))

    async def click(
        self,
        modifiers: List[KeyboardModifier] = None,
        position: Tuple[float, float] = None,
        delay: float = None,
        button: MouseButton = None,
        clickCount: int = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
    ) -> None:
        await self._channel.send("click", locals_to_params(locals()))

    async def dblclick(
        self,
        modifiers: List[KeyboardModifier] = None,
        position: Tuple[float, float] = None,
        delay: float = None,
        button: MouseButton = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
    ) -> None:
        await self._channel.send("dblclick", locals_to_params(locals()))

    async def selectOption(
        self,
        value: Union[str, List[str]] = None,
        index: Union[int, List[int]] = None,
        label: Union[str, List[str]] = None,
        element: Union["ElementHandle", List["ElementHandle"]] = None,
        timeout: float = None,
        noWaitAfter: bool = None,
    ) -> List[str]:
        params = locals_to_params(
            dict(
                timeout=timeout,
                noWaitAfter=noWaitAfter,
                **convert_select_option_values(value, index, label, element)
            )
        )
        return await self._channel.send("selectOption", params)

    async def tap(
        self,
        modifiers: List[KeyboardModifier] = None,
        position: Tuple[float, float] = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
    ) -> None:
        await self._channel.send("tap", locals_to_params(locals()))

    async def fill(
        self, value: str, timeout: float = None, noWaitAfter: bool = None
    ) -> None:
        await self._channel.send("fill", locals_to_params(locals()))

    async def selectText(self, timeout: float = None) -> None:
        await self._channel.send("selectText", locals_to_params(locals()))

    async def setInputFiles(
        self,
        files: Union[str, Path, FilePayload, List[str], List[Path], List[FilePayload]],
        timeout: float = None,
        noWaitAfter: bool = None,
    ) -> None:
        params = locals_to_params(locals())
        params["files"] = normalize_file_payloads(files)
        await self._channel.send("setInputFiles", params)

    async def focus(self) -> None:
        await self._channel.send("focus")

    async def type(
        self,
        text: str,
        delay: float = None,
        timeout: float = None,
        noWaitAfter: bool = None,
    ) -> None:
        await self._channel.send("type", locals_to_params(locals()))

    async def press(
        self,
        key: str,
        delay: float = None,
        timeout: float = None,
        noWaitAfter: bool = None,
    ) -> None:
        await self._channel.send("press", locals_to_params(locals()))

    async def check(
        self, timeout: float = None, force: bool = None, noWaitAfter: bool = None
    ) -> None:
        await self._channel.send("check", locals_to_params(locals()))

    async def uncheck(
        self, timeout: float = None, force: bool = None, noWaitAfter: bool = None
    ) -> None:
        await self._channel.send("uncheck", locals_to_params(locals()))

    async def boundingBox(self) -> Optional[FloatRect]:
        bb = await self._channel.send("boundingBox")
        return FloatRect._parse(bb)

    async def screenshot(
        self,
        timeout: float = None,
        type: Literal["jpeg", "png"] = None,
        path: Union[str, Path] = None,
        quality: int = None,
        omitBackground: bool = None,
    ) -> bytes:
        params = locals_to_params(locals())
        if "path" in params:
            del params["path"]
        encoded_binary = await self._channel.send("screenshot", params)
        decoded_binary = base64.b64decode(encoded_binary)
        if path:
            with open(path, "wb") as fd:
                fd.write(decoded_binary)
        return decoded_binary

    async def querySelector(self, selector: str) -> Optional["ElementHandle"]:
        return from_nullable_channel(
            await self._channel.send("querySelector", dict(selector=selector))
        )

    async def querySelectorAll(self, selector: str) -> List["ElementHandle"]:
        return list(
            map(
                cast(Callable[[Any], Any], from_nullable_channel),
                await self._channel.send("querySelectorAll", dict(selector=selector)),
            )
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

    async def waitForElementState(
        self,
        state: Literal["disabled", "enabled", "hidden", "stable", "visible"],
        timeout: float = None,
    ) -> None:
        await self._channel.send("waitForElementState", locals_to_params(locals()))

    async def waitForSelector(
        self,
        selector: str,
        state: Literal["attached", "detached", "hidden", "visible"] = None,
        timeout: float = None,
    ) -> Optional["ElementHandle"]:
        return from_nullable_channel(
            await self._channel.send("waitForSelector", locals_to_params(locals()))
        )


def convert_select_option_values(
    value: Union[str, List[str]] = None,
    index: Union[int, List[int]] = None,
    label: Union[str, List[str]] = None,
    element: Union["ElementHandle", List["ElementHandle"]] = None,
) -> Any:
    if value is None and index is None and label is None and element is None:
        return {}

    options: Any = None
    elements: Any = None
    if value:
        if not isinstance(value, list):
            value = [value]
        options = (options or []) + list(map(lambda e: dict(value=e), value))
    if index:
        if not isinstance(index, list):
            index = [index]
        options = (options or []) + list(map(lambda e: dict(index=e), index))
    if label:
        if not isinstance(label, list):
            label = [label]
        options = (options or []) + list(map(lambda e: dict(label=e), label))
    if element:
        if not isinstance(element, list):
            element = [element]
        elements = list(map(lambda e: e._channel, element))

    return filter_out_none(dict(options=options, elements=elements))
