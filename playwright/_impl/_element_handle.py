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
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Union, cast

from playwright._impl._api_structures import FilePayload, FloatRect, Position
from playwright._impl._connection import (
    ChannelOwner,
    filter_none,
    from_nullable_channel,
)
from playwright._impl._helper import (
    Error,
    KeyboardModifier,
    MouseButton,
    async_writefile,
    locals_to_params,
    make_dirs_for_file,
)
from playwright._impl._js_handle import (
    JSHandle,
    Serializable,
    parse_result,
    serialize_argument,
)
from playwright._impl._set_input_files_helpers import convert_input_files

if sys.version_info >= (3, 8):  # pragma: no cover
    from typing import Literal
else:  # pragma: no cover
    from typing_extensions import Literal

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._frame import Frame
    from playwright._impl._locator import Locator


class ElementHandle(JSHandle):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)

    async def _createSelectorForTest(self, name: str) -> Optional[str]:
        return await self._channel.send("createSelectorForTest", dict(name=name))

    def as_element(self) -> Optional["ElementHandle"]:
        return self

    async def owner_frame(self) -> Optional["Frame"]:
        return from_nullable_channel(await self._channel.send("ownerFrame"))

    async def content_frame(self) -> Optional["Frame"]:
        return from_nullable_channel(await self._channel.send("contentFrame"))

    async def get_attribute(self, name: str) -> Optional[str]:
        return await self._channel.send("getAttribute", dict(name=name))

    async def text_content(self) -> Optional[str]:
        return await self._channel.send("textContent")

    async def inner_text(self) -> str:
        return await self._channel.send("innerText")

    async def inner_html(self) -> str:
        return await self._channel.send("innerHTML")

    async def is_checked(self) -> bool:
        return await self._channel.send("isChecked")

    async def is_disabled(self) -> bool:
        return await self._channel.send("isDisabled")

    async def is_editable(self) -> bool:
        return await self._channel.send("isEditable")

    async def is_enabled(self) -> bool:
        return await self._channel.send("isEnabled")

    async def is_hidden(self) -> bool:
        return await self._channel.send("isHidden")

    async def is_visible(self) -> bool:
        return await self._channel.send("isVisible")

    async def dispatch_event(self, type: str, eventInit: Dict = None) -> None:
        await self._channel.send(
            "dispatchEvent", dict(type=type, eventInit=serialize_argument(eventInit))
        )

    async def scroll_into_view_if_needed(self, timeout: float = None) -> None:
        await self._channel.send("scrollIntoViewIfNeeded", locals_to_params(locals()))

    async def hover(
        self,
        modifiers: List[KeyboardModifier] = None,
        position: Position = None,
        timeout: float = None,
        noWaitAfter: bool = None,
        force: bool = None,
        trial: bool = None,
    ) -> None:
        await self._channel.send("hover", locals_to_params(locals()))

    async def click(
        self,
        modifiers: List[KeyboardModifier] = None,
        position: Position = None,
        delay: float = None,
        button: MouseButton = None,
        clickCount: int = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        trial: bool = None,
    ) -> None:
        await self._channel.send("click", locals_to_params(locals()))

    async def dblclick(
        self,
        modifiers: List[KeyboardModifier] = None,
        position: Position = None,
        delay: float = None,
        button: MouseButton = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        trial: bool = None,
    ) -> None:
        await self._channel.send("dblclick", locals_to_params(locals()))

    async def select_option(
        self,
        value: Union[str, List[str]] = None,
        index: Union[int, List[int]] = None,
        label: Union[str, List[str]] = None,
        element: Union["ElementHandle", List["ElementHandle"]] = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
    ) -> List[str]:
        params = locals_to_params(
            dict(
                timeout=timeout,
                noWaitAfter=noWaitAfter,
                force=force,
                **convert_select_option_values(value, index, label, element)
            )
        )
        return await self._channel.send("selectOption", params)

    async def tap(
        self,
        modifiers: List[KeyboardModifier] = None,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        trial: bool = None,
    ) -> None:
        await self._channel.send("tap", locals_to_params(locals()))

    async def fill(
        self,
        value: str,
        timeout: float = None,
        noWaitAfter: bool = None,
        force: bool = None,
    ) -> None:
        await self._channel.send("fill", locals_to_params(locals()))

    async def select_text(self, force: bool = None, timeout: float = None) -> None:
        await self._channel.send("selectText", locals_to_params(locals()))

    async def input_value(self, timeout: float = None) -> str:
        return await self._channel.send("inputValue", locals_to_params(locals()))

    async def set_input_files(
        self,
        files: Union[str, Path, FilePayload, List[Union[str, Path]], List[FilePayload]],
        timeout: float = None,
        noWaitAfter: bool = None,
    ) -> None:
        frame = await self.owner_frame()
        if not frame:
            raise Error("Cannot set input files to detached element")
        converted = await convert_input_files(files, frame.page.context)
        await self._channel.send(
            "setInputFiles",
            {
                **filter_none({"timeout": timeout, "noWaitAfter": noWaitAfter}),
                **converted,
            },
        )

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

    async def set_checked(
        self,
        checked: bool,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        trial: bool = None,
    ) -> None:
        if checked:
            await self.check(
                position=position,
                timeout=timeout,
                force=force,
                noWaitAfter=noWaitAfter,
                trial=trial,
            )
        else:
            await self.uncheck(
                position=position,
                timeout=timeout,
                force=force,
                noWaitAfter=noWaitAfter,
                trial=trial,
            )

    async def check(
        self,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        trial: bool = None,
    ) -> None:
        await self._channel.send("check", locals_to_params(locals()))

    async def uncheck(
        self,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        trial: bool = None,
    ) -> None:
        await self._channel.send("uncheck", locals_to_params(locals()))

    async def bounding_box(self) -> Optional[FloatRect]:
        return await self._channel.send("boundingBox")

    async def screenshot(
        self,
        timeout: float = None,
        type: Literal["jpeg", "png"] = None,
        path: Union[str, Path] = None,
        quality: int = None,
        omitBackground: bool = None,
        animations: Literal["allow", "disabled"] = None,
        caret: Literal["hide", "initial"] = None,
        scale: Literal["css", "device"] = None,
        mask: List["Locator"] = None,
        mask_color: str = None,
    ) -> bytes:
        params = locals_to_params(locals())
        if "path" in params:
            del params["path"]
        if "mask" in params:
            params["mask"] = list(
                map(
                    lambda locator: (
                        {
                            "frame": locator._frame._channel,
                            "selector": locator._selector,
                        }
                    ),
                    params["mask"],
                )
            )
        encoded_binary = await self._channel.send("screenshot", params)
        decoded_binary = base64.b64decode(encoded_binary)
        if path:
            make_dirs_for_file(path)
            await async_writefile(path, decoded_binary)
        return decoded_binary

    async def query_selector(self, selector: str) -> Optional["ElementHandle"]:
        return from_nullable_channel(
            await self._channel.send("querySelector", dict(selector=selector))
        )

    async def query_selector_all(self, selector: str) -> List["ElementHandle"]:
        return list(
            map(
                cast(Callable[[Any], Any], from_nullable_channel),
                await self._channel.send("querySelectorAll", dict(selector=selector)),
            )
        )

    async def eval_on_selector(
        self,
        selector: str,
        expression: str,
        arg: Serializable = None,
    ) -> Any:
        return parse_result(
            await self._channel.send(
                "evalOnSelector",
                dict(
                    selector=selector,
                    expression=expression,
                    arg=serialize_argument(arg),
                ),
            )
        )

    async def eval_on_selector_all(
        self,
        selector: str,
        expression: str,
        arg: Serializable = None,
    ) -> Any:
        return parse_result(
            await self._channel.send(
                "evalOnSelectorAll",
                dict(
                    selector=selector,
                    expression=expression,
                    arg=serialize_argument(arg),
                ),
            )
        )

    async def wait_for_element_state(
        self,
        state: Literal[
            "disabled", "editable", "enabled", "hidden", "stable", "visible"
        ],
        timeout: float = None,
    ) -> None:
        await self._channel.send("waitForElementState", locals_to_params(locals()))

    async def wait_for_selector(
        self,
        selector: str,
        state: Literal["attached", "detached", "hidden", "visible"] = None,
        timeout: float = None,
        strict: bool = None,
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
        options = (options or []) + list(map(lambda e: dict(valueOrLabel=e), value))
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

    return filter_none(dict(options=options, elements=elements))
