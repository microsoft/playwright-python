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
import collections.abc
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Sequence,
    Union,
    cast,
)

from playwright._impl._api_structures import FilePayload, FloatRect, Position
from playwright._impl._connection import ChannelOwner, from_nullable_channel
from playwright._impl._errors import Error
from playwright._impl._helper import (
    KeyboardModifier,
    MouseButton,
    async_writefile,
    make_dirs_for_file,
)
from playwright._impl._js_handle import (
    JSHandle,
    Serializable,
    parse_result,
    serialize_argument,
)
from playwright._impl._mime_type import get_mime_type_for_path
from playwright._impl._set_input_files_helpers import convert_input_files

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._frame import Frame
    from playwright._impl._locator import Locator
    from playwright._impl._protocol_channels import ElementHandleChannel


class ElementHandle(JSHandle):
    _channel: "ElementHandleChannel"

    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._frame = cast("Frame", parent)

    def as_element(self) -> Optional["ElementHandle"]:
        return self

    async def owner_frame(self) -> Optional["Frame"]:
        return from_nullable_channel((await self._channel.ownerFrame())["frame"])

    async def content_frame(self) -> Optional["Frame"]:
        return from_nullable_channel((await self._channel.contentFrame())["frame"])

    async def get_attribute(self, name: str) -> Optional[str]:
        return (await self._channel.getAttribute(name=name))["value"]

    async def text_content(self) -> Optional[str]:
        return (await self._channel.textContent())["value"]

    async def inner_text(self) -> str:
        return (await self._channel.innerText())["value"]

    async def inner_html(self) -> str:
        return (await self._channel.innerHTML())["value"]

    async def is_checked(self) -> bool:
        return (await self._channel.isChecked())["value"]

    async def is_disabled(self) -> bool:
        return (await self._channel.isDisabled())["value"]

    async def is_editable(self) -> bool:
        return (await self._channel.isEditable())["value"]

    async def is_enabled(self) -> bool:
        return (await self._channel.isEnabled())["value"]

    async def is_hidden(self) -> bool:
        return (await self._channel.isHidden())["value"]

    async def is_visible(self) -> bool:
        return (await self._channel.isVisible())["value"]

    async def dispatch_event(self, type: str, event_init: Optional[Dict]) -> None:
        await self._channel.dispatchEvent(
            type=type, eventInit=serialize_argument(event_init)
        )

    async def scroll_into_view_if_needed(self, timeout: Optional[float]) -> None:
        await self._channel.scrollIntoViewIfNeeded(
            timeout=self._frame._timeout(timeout)
        )

    async def hover(
        self,
        modifiers: Optional[Sequence[KeyboardModifier]],
        position: Optional[Position],
        timeout: Optional[float],
        no_wait_after: Optional[bool],  # Deprecated; does nothing.
        force: Optional[bool],
        trial: Optional[bool],
        scroll: Optional[Literal["auto", "none"]],
    ) -> None:
        await self._channel.hover(
            force=force,
            scroll=scroll,
            modifiers=modifiers,
            position=position,
            trial=trial,
            timeout=self._frame._timeout(timeout),
        )

    async def click(
        self,
        modifiers: Optional[Sequence[KeyboardModifier]],
        position: Optional[Position],
        delay: Optional[float],
        button: Optional[MouseButton],
        click_count: Optional[int],
        timeout: Optional[float],
        force: Optional[bool],
        no_wait_after: Optional[bool],
        trial: Optional[bool],
        steps: Optional[int],
        scroll: Optional[Literal["auto", "none"]],
    ) -> None:
        await self._channel.click(
            force=force,
            scroll=scroll,
            noWaitAfter=no_wait_after,
            modifiers=modifiers,
            position=position,
            delay=delay,
            button=button,
            clickCount=click_count,
            trial=trial,
            steps=steps,
            timeout=self._frame._timeout(timeout),
        )

    async def dblclick(
        self,
        modifiers: Optional[Sequence[KeyboardModifier]],
        position: Optional[Position],
        delay: Optional[float],
        button: Optional[MouseButton],
        timeout: Optional[float],
        force: Optional[bool],
        no_wait_after: Optional[bool],  # Deprecated; does nothing.
        trial: Optional[bool],
        steps: Optional[int],
        scroll: Optional[Literal["auto", "none"]],
    ) -> None:
        await self._channel.dblclick(
            force=force,
            scroll=scroll,
            modifiers=modifiers,
            position=position,
            delay=delay,
            button=button,
            trial=trial,
            steps=steps,
            timeout=self._frame._timeout(timeout),
        )

    async def select_option(
        self,
        value: Optional[Union[str, Sequence[str]]],
        index: Optional[Union[int, Sequence[int]]],
        label: Optional[Union[str, Sequence[str]]],
        element: Optional[Union["ElementHandle", Sequence["ElementHandle"]]],
        timeout: Optional[float],
        force: Optional[bool],
        no_wait_after: Optional[bool],  # Deprecated; does nothing.
    ) -> List[str]:
        converted = convert_select_option_values(value, index, label, element)
        result = await self._channel.selectOption(
            elements=converted.get("elements"),
            options=converted.get("options"),
            force=force,
            timeout=self._frame._timeout(timeout),
        )
        return result["values"]

    async def tap(
        self,
        modifiers: Optional[Sequence[KeyboardModifier]],
        position: Optional[Position],
        timeout: Optional[float],
        force: Optional[bool],
        no_wait_after: Optional[bool],  # Deprecated; does nothing.
        trial: Optional[bool],
        scroll: Optional[Literal["auto", "none"]],
    ) -> None:
        await self._channel.tap(
            force=force,
            scroll=scroll,
            modifiers=modifiers,
            position=position,
            trial=trial,
            timeout=self._frame._timeout(timeout),
        )

    async def fill(
        self,
        value: str,
        timeout: Optional[float],
        no_wait_after: Optional[bool],  # Deprecated; does nothing.
        force: Optional[bool],
    ) -> None:
        await self._channel.fill(
            value=value, force=force, timeout=self._frame._timeout(timeout)
        )

    async def select_text(
        self, force: Optional[bool], timeout: Optional[float]
    ) -> None:
        await self._channel.selectText(
            force=force, timeout=self._frame._timeout(timeout)
        )

    async def input_value(self, timeout: Optional[float]) -> str:
        result = await self._channel.inputValue(timeout=self._frame._timeout(timeout))
        return result["value"]

    async def set_input_files(
        self,
        files: Union[
            str, Path, FilePayload, Sequence[Union[str, Path]], Sequence[FilePayload]
        ],
        timeout: Optional[float],
        no_wait_after: Optional[bool],  # Deprecated; does nothing.
    ) -> None:
        frame = await self.owner_frame()
        if not frame:
            raise Error("Cannot set input files to detached element")
        converted = await convert_input_files(files, frame.page.context)
        await self._channel.setInputFiles(
            payloads=converted.get("payloads"),
            localDirectory=converted.get("localDirectory"),
            directoryStream=converted.get("directoryStream"),
            localPaths=converted.get("localPaths"),
            streams=converted.get("streams"),
            timeout=self._frame._timeout(timeout),
        )

    async def focus(self) -> None:
        await self._channel.focus()

    async def type(
        self,
        text: str,
        delay: Optional[float],
        timeout: Optional[float],
        no_wait_after: Optional[bool],  # Deprecated; does nothing.
    ) -> None:
        await self._channel.type(
            text=text, delay=delay, timeout=self._frame._timeout(timeout)
        )

    async def press(
        self,
        key: str,
        delay: Optional[float],
        timeout: Optional[float],
        no_wait_after: Optional[bool],
    ) -> None:
        await self._channel.press(
            key=key,
            delay=delay,
            noWaitAfter=no_wait_after,
            timeout=self._frame._timeout(timeout),
        )

    async def set_checked(
        self,
        checked: bool,
        position: Optional[Position],
        timeout: Optional[float],
        force: Optional[bool],
        no_wait_after: Optional[bool],
        trial: Optional[bool],
        scroll: Optional[Literal["auto", "none"]],
    ) -> None:
        if checked:
            await self.check(
                position=position,
                timeout=timeout,
                force=force,
                no_wait_after=no_wait_after,
                trial=trial,
                scroll=scroll,
            )
        else:
            await self.uncheck(
                position=position,
                timeout=timeout,
                force=force,
                no_wait_after=no_wait_after,
                trial=trial,
                scroll=scroll,
            )

    async def check(
        self,
        position: Optional[Position],
        timeout: Optional[float],
        force: Optional[bool],
        no_wait_after: Optional[bool],  # Deprecated; does nothing.
        trial: Optional[bool],
        scroll: Optional[Literal["auto", "none"]],
    ) -> None:
        await self._channel.check(
            force=force,
            scroll=scroll,
            position=position,
            trial=trial,
            timeout=self._frame._timeout(timeout),
        )

    async def uncheck(
        self,
        position: Optional[Position],
        timeout: Optional[float],
        force: Optional[bool],
        no_wait_after: Optional[bool],  # Deprecated; does nothing.
        trial: Optional[bool],
        scroll: Optional[Literal["auto", "none"]],
    ) -> None:
        await self._channel.uncheck(
            force=force,
            scroll=scroll,
            position=position,
            trial=trial,
            timeout=self._frame._timeout(timeout),
        )

    async def bounding_box(self) -> Optional[FloatRect]:
        return (await self._channel.boundingBox())["value"]

    async def screenshot(
        self,
        timeout: Optional[float],
        type: Optional[Literal["jpeg", "png", "webp"]],
        path: Optional[Union[str, Path]],
        quality: Optional[int],
        omit_background: Optional[bool],
        animations: Optional[Literal["allow", "disabled"]],
        caret: Optional[Literal["hide", "initial"]],
        scale: Optional[Literal["css", "device"]],
        mask: Optional[Sequence["Locator"]],
        mask_color: Optional[str],
        style: Optional[str],
    ) -> bytes:
        if path is not None and type is None:
            type = determine_screenshot_type(path)
        result = await self._channel.screenshot(
            type=type,
            quality=quality,
            omitBackground=omit_background,
            caret=caret,
            animations=animations,
            scale=scale,
            mask=(
                [
                    {"frame": locator._frame._channel, "selector": locator._selector}
                    for locator in mask
                ]
                if mask is not None
                else None
            ),
            maskColor=mask_color,
            style=style,
            timeout=self._frame._timeout(timeout),
        )
        decoded_binary = base64.b64decode(result["binary"])
        if path:
            make_dirs_for_file(path)
            await async_writefile(path, decoded_binary)
        return decoded_binary

    async def query_selector(self, selector: str) -> Optional["ElementHandle"]:
        result = await self._channel.querySelector(selector=selector, strict=None)
        return from_nullable_channel(result["element"])

    async def query_selector_all(self, selector: str) -> List["ElementHandle"]:
        result = await self._channel.querySelectorAll(selector=selector)
        return list(
            map(
                cast(Callable[[Any], Any], from_nullable_channel),
                result["elements"],
            )
        )

    async def eval_on_selector(
        self,
        selector: str,
        expression: str,
        arg: Serializable,
    ) -> Any:
        result = await self._channel.evalOnSelector(
            selector=selector,
            strict=None,
            expression=expression,
            isFunction=None,
            arg=serialize_argument(arg),
        )
        return parse_result(result["value"])

    async def eval_on_selector_all(
        self,
        selector: str,
        expression: str,
        arg: Serializable,
    ) -> Any:
        result = await self._channel.evalOnSelectorAll(
            selector=selector,
            expression=expression,
            isFunction=None,
            arg=serialize_argument(arg),
        )
        return parse_result(result["value"])

    async def wait_for_element_state(
        self,
        state: Literal[
            "disabled", "editable", "enabled", "hidden", "stable", "visible"
        ],
        timeout: Optional[float],
    ) -> None:
        await self._channel.waitForElementState(
            state=state, timeout=self._frame._timeout(timeout)
        )

    async def wait_for_selector(
        self,
        selector: str,
        state: Optional[Literal["attached", "detached", "hidden", "visible"]],
        timeout: Optional[float],
        strict: Optional[bool],
    ) -> Optional["ElementHandle"]:
        result = await self._channel.waitForSelector(
            selector=selector,
            strict=strict,
            state=state,
            timeout=self._frame._timeout(timeout),
        )
        return from_nullable_channel(result["element"])


def convert_select_option_values(
    value: Union[str, Sequence[str]] = None,
    index: Union[int, Sequence[int]] = None,
    label: Union[str, Sequence[str]] = None,
    element: Union["ElementHandle", Sequence["ElementHandle"]] = None,
) -> Any:
    if value is None and index is None and label is None and element is None:
        return {}

    options: Any = None
    elements: Any = None
    if value is not None:
        options = (options or []) + [dict(valueOrLabel=e) for e in _to_list(value)]
    if index is not None:
        options = (options or []) + [dict(index=e) for e in _to_list(index)]
    if label is not None:
        options = (options or []) + [dict(label=e) for e in _to_list(label)]
    for i, option in enumerate(options or []):
        if None in option.values():
            raise Error(f"options[{i}]: expected object, got null")
    if element:
        if isinstance(element, ElementHandle):
            element = [element]
        elements = list(map(lambda e: e._channel, element))

    return dict(options=options, elements=elements)


# Like convertSelectOptionValues() in packages/playwright-core/src/client/elementHandle.ts,
# wraps a single value of any type in a list. The driver checks the type.
def _to_list(value: Any) -> List[Any]:
    if isinstance(value, str) or not isinstance(value, collections.abc.Iterable):
        return [value]
    return list(value)


def determine_screenshot_type(path: Union[str, Path]) -> Literal["jpeg", "png", "webp"]:
    # Port of determineScreenshotType() in elementHandle.ts. It uses the
    # extension map of mimeType.ts, not mimetypes.guess_type, whose result is
    # OS-dependent (e.g. Windows does not register image/webp).
    mime_type = get_mime_type_for_path(str(path))
    if mime_type == "image/png":
        return "png"
    if mime_type == "image/jpeg":
        return "jpeg"
    if mime_type == "image/webp":
        return "webp"
    # JavaScript prints null as "null".
    raise Error(f'path: unsupported mime type "{mime_type or "null"}"')
