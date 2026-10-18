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

"""Port of packages/playwright-core/src/client/elementHandle.ts."""

import base64
import collections.abc
import os
import stat
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Literal,
    Optional,
    Sequence,
    Tuple,
    TypedDict,
    Union,
    cast,
)

from playwright._impl._api_structures import FilePayload, FloatRect, Position
from playwright._impl._connection import (
    ChannelOwner,
    from_channel,
    from_nullable_channel,
)
from playwright._impl._errors import Error
from playwright._impl._file_utils import file_upload_size_limit, mkdir_if_needed
from playwright._impl._helper import (
    KeyboardModifier,
    MouseButton,
    async_writefile,
)
from playwright._impl._js_handle import (
    JSHandle,
    Serializable,
    parse_result,
    serialize_argument,
)
from playwright._impl._mime_type import get_mime_type_for_path
from playwright._impl._writable_stream import WritableStream

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl import _protocol_types as channels
    from playwright._impl._browser_context import BrowserContext
    from playwright._impl._frame import Frame
    from playwright._impl._locator import Locator
    from playwright._impl._protocol_channels import (
        ElementHandleChannel,
        WritableStreamChannel,
    )


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

    async def input_value(
        self, timeout: Optional[float]  # Deprecated; ignored.
    ) -> str:
        return (await self._channel.inputValue())["value"]

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
            type=type,
            eventInit=serialize_argument({} if event_init is None else event_init),
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
        if not type:
            type = determine_screenshot_type(path, type)
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
        binary = base64.b64decode(result["binary"])
        if path:
            mkdir_if_needed(path)
            await async_writefile(path, binary)
        return binary

    async def query_selector(self, selector: str) -> Optional["ElementHandle"]:
        result = await self._channel.querySelector(selector=selector, strict=None)
        return from_nullable_channel(result["element"])

    async def query_selector_all(self, selector: str) -> List["ElementHandle"]:
        result = await self._channel.querySelectorAll(selector=selector)
        return [from_channel(element) for element in result["elements"]]

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


class SelectOptionValues(TypedDict, total=False):
    elements: List["ElementHandleChannel"]
    options: List["channels.ElementHandleSelectOptionParamsOptions"]


def convert_select_option_values(
    value: Optional[Union[str, Sequence[str]]],
    index: Optional[Union[int, Sequence[int]]],
    label: Optional[Union[str, Sequence[str]]],
    element: Optional[Union["ElementHandle", Sequence["ElementHandle"]]],
) -> SelectOptionValues:
    # Port of convertSelectOptionValues() in elementHandle.ts. Python passes the
    # values as value=, index=, label= and element=, not as one list of strings,
    # objects or handles.
    options: List[Any] = []
    if value is not None:
        options += [{"valueOrLabel": item} for item in _to_list(value)]
    if index is not None:
        options += [{"index": item} for item in _to_list(index)]
    if label is not None:
        options += [{"label": item} for item in _to_list(label)]
    elements = _to_list(element) if element is not None else []
    if not options and not elements:
        return {}
    for i, option in enumerate(options):
        if None in option.values():
            raise Error(f"options[{i}]: expected object, got null")
    for i, handle in enumerate(elements):
        if handle is None:
            raise Error(f"options[{i}]: expected object, got null")
    result: SelectOptionValues = {}
    if elements:
        result["elements"] = [handle._channel for handle in elements]
    if options:
        result["options"] = options
    return result


# Like convertSelectOptionValues() in elementHandle.ts, wraps a single value of
# any type in a list. The driver checks the type.
def _to_list(value: Any) -> List[Any]:
    if isinstance(value, str) or not isinstance(value, collections.abc.Iterable):
        return [value]
    return list(value)


class SetInputFilesFiles(TypedDict, total=False):
    payloads: List["channels.ElementHandleSetInputFilesParamsPayloads"]
    localPaths: List[str]
    localDirectory: str
    streams: List["WritableStreamChannel"]
    directoryStream: "WritableStreamChannel"


def _file_payload_exceeds_size_limit(payloads: Sequence[FilePayload]) -> bool:
    return (
        sum(len(item["buffer"]) if item.get("buffer") else 0 for item in payloads)
        >= file_upload_size_limit
    )


def _resolve_paths_and_directory_for_input_files(
    items: Sequence[Union[str, Path]],
) -> Tuple[Optional[List[str]], Optional[str]]:
    local_paths: Optional[List[str]] = None
    local_directory: Optional[str] = None
    for item in items:
        # Raises FileNotFoundError for a path that does not exist.
        if stat.S_ISDIR(os.stat(item).st_mode):
            if local_directory:
                raise Error("Multiple directories are not supported")
            local_directory = os.path.abspath(item)
        else:
            local_paths = local_paths or []
            local_paths.append(os.path.abspath(item))
    if local_paths and local_directory:
        raise Error("File paths must be all files or a single directory")
    return (local_paths, local_directory)


async def convert_input_files(
    files: Union[
        str, Path, FilePayload, Sequence[Union[str, Path]], Sequence[FilePayload]
    ],
    context: "BrowserContext",
) -> SetInputFilesFiles:
    items: List[Any] = (
        list(files)
        if isinstance(files, collections.abc.Sequence) and not isinstance(files, str)
        else [files]
    )

    if any(isinstance(item, (str, Path)) for item in items):
        if not all(isinstance(item, (str, Path)) for item in items):
            raise Error("File paths cannot be mixed with buffers")

        local_paths, local_directory = _resolve_paths_and_directory_for_input_files(
            items
        )

        if context._connection.is_remote:
            files_to_stream = (
                [
                    os.path.join(root, name)
                    for root, _, names in os.walk(local_directory)
                    for name in names
                ]
                if local_directory
                else cast(List[str], local_paths)
            )
            result = await context._wrap_api_call(
                lambda: context._channel.createTempFiles(
                    rootDirName=(
                        os.path.basename(local_directory) if local_directory else None
                    ),
                    items=[
                        {
                            "name": (
                                os.path.relpath(file, local_directory)
                                if local_directory
                                else os.path.basename(file)
                            ),
                            "lastModifiedMs": os.stat(file).st_mtime * 1000,
                        }
                        for file in files_to_stream
                    ],
                ),
                True,
            )
            writable_streams = result["writableStreams"]
            for i, file in enumerate(files_to_stream):
                writable: WritableStream = from_channel(writable_streams[i])
                await writable.copy(file)
            converted: SetInputFilesFiles = {}
            if result["rootDir"]:
                converted["directoryStream"] = result["rootDir"]
            if not local_directory:
                converted["streams"] = writable_streams
            return converted
        converted = {}
        if local_paths:
            converted["localPaths"] = local_paths
        if local_directory:
            converted["localDirectory"] = local_directory
        return converted

    payloads = cast(List[FilePayload], items)
    if _file_payload_exceeds_size_limit(payloads):
        raise Error(
            "Cannot set buffer larger than 50Mb, please write it to a file and pass its path instead."
        )
    return {
        "payloads": [
            {
                "name": item["name"],
                "mimeType": item["mimeType"],
                "buffer": base64.b64encode(item["buffer"]).decode(),
            }
            for item in payloads
        ]
    }


def determine_screenshot_type(
    path: Optional[Union[str, Path]],
    type: Optional[Literal["jpeg", "png", "webp"]] = None,
) -> Optional[Literal["jpeg", "png", "webp"]]:
    # Port of determineScreenshotType() in elementHandle.ts. It uses the
    # extension map of mimeType.ts, not mimetypes.guess_type, whose result is
    # OS-dependent (e.g. Windows does not register image/webp).
    if path:
        mime_type = get_mime_type_for_path(str(path))
        if mime_type == "image/png":
            return "png"
        if mime_type == "image/jpeg":
            return "jpeg"
        if mime_type == "image/webp":
            return "webp"
        # JavaScript prints null as "null".
        raise Error(f'path: unsupported mime type "{mime_type or "null"}"')
    return type
