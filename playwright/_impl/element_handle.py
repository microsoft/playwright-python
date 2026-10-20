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

"""Port of packages/playwright-core/src/client/elementHandle.ts.

Python: the JS methods spread their options object into the params of the channel
call, and the validator drops the options that the command does not take (the
deprecated noWaitAfter of most actions). Here each parameter of the command is
passed by name, and the others are not passed.

Python: binary values are base64 strings on the channel: the screenshot is decoded,
and the buffers of the file payloads are encoded.

Python: the Python API passes the options of selectOption() as value=, index=,
label= and element= (langs: python in the docs), and a file of setInputFiles() can
be a pathlib.Path.
"""

import asyncio
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
from playwright._impl.channel_owner import ApiCallOptions, ChannelOwner, from_channel
from playwright._impl.errors import Error
from playwright._impl.file_utils import file_upload_size_limit, mkdir_if_needed
from playwright._impl.isomorphic.mime_type import get_mime_type_for_path
from playwright._impl.js_handle import (
    JSHandle,
    Serializable,
    parse_result,
    serialize_argument,
)
from playwright._impl.timeout_settings import NO_TIMEOUT
from playwright._impl.writable_stream import WritableStream, pipeline

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl import protocol_types as channels
    from playwright._impl.browser_context import BrowserContext
    from playwright._impl.frame import Frame
    from playwright._impl.locator import Locator
    from playwright._impl.protocol_channels import (
        ElementHandleChannel,
        JSHandleChannel,
        WritableStreamChannel,
    )

# Python: the types of the Python API options, as the docs define them.
KeyboardModifier = Literal["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]
MouseButton = Literal["left", "middle", "right"]


class ElementHandle(JSHandle):
    _element_channel: "ElementHandleChannel"

    @staticmethod
    def from_(
        # Python: the type of JSHandle.from_(), as an override must take it;
        # upstream narrows it to ElementHandleChannel.
        handle: "JSHandleChannel",
    ) -> "ElementHandle":
        return from_channel(handle)

    @staticmethod
    def from_nullable(
        handle: Optional["ElementHandleChannel"],
    ) -> Optional["ElementHandle"]:
        return ElementHandle.from_(handle) if handle else None

    def __init__(
        self,
        parent: ChannelOwner,
        type: str,
        guid: str,
        initializer: "channels.JSHandleInitializer",
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._frame = cast("Frame", parent)
        self._element_channel = cast("ElementHandleChannel", self._channel)

    def as_element(self) -> Optional["ElementHandle"]:
        return self

    async def owner_frame(self) -> Optional["Frame"]:
        # Python: imported here, to avoid an import cycle.
        from playwright._impl.frame import Frame

        return Frame.from_nullable(
            (await self._element_channel.ownerFrame(timeout=NO_TIMEOUT))["frame"]
        )

    async def content_frame(self) -> Optional["Frame"]:
        # Python: imported here, to avoid an import cycle.
        from playwright._impl.frame import Frame

        return Frame.from_nullable(
            (await self._element_channel.contentFrame(timeout=NO_TIMEOUT))["frame"]
        )

    async def get_attribute(self, name: str) -> Optional[str]:
        value = (
            await self._element_channel.getAttribute(name=name, timeout=NO_TIMEOUT)
        )["value"]
        # Python: an undefined value is None, as null is.
        return value

    async def input_value(self, timeout: Optional[float]) -> str:
        # Python: the Python API passes the deprecated timeout, which is ignored.
        return (await self._element_channel.inputValue(timeout=NO_TIMEOUT))["value"]

    async def text_content(self) -> Optional[str]:
        value = (await self._element_channel.textContent(timeout=NO_TIMEOUT))["value"]
        # Python: an undefined value is None, as null is.
        return value

    async def inner_text(self) -> str:
        return (await self._element_channel.innerText(timeout=NO_TIMEOUT))["value"]

    async def inner_html(self) -> str:
        return (await self._element_channel.innerHTML(timeout=NO_TIMEOUT))["value"]

    async def is_checked(self) -> bool:
        return (await self._element_channel.isChecked(timeout=NO_TIMEOUT))["value"]

    async def is_disabled(self) -> bool:
        return (await self._element_channel.isDisabled(timeout=NO_TIMEOUT))["value"]

    async def is_editable(self) -> bool:
        return (await self._element_channel.isEditable(timeout=NO_TIMEOUT))["value"]

    async def is_enabled(self) -> bool:
        return (await self._element_channel.isEnabled(timeout=NO_TIMEOUT))["value"]

    async def is_hidden(self) -> bool:
        return (await self._element_channel.isHidden(timeout=NO_TIMEOUT))["value"]

    async def is_visible(self) -> bool:
        return (await self._element_channel.isVisible(timeout=NO_TIMEOUT))["value"]

    async def dispatch_event(self, type: str, event_init: Optional[Dict]) -> None:
        # Python: None is the default {} of eventInit.
        if event_init is None:
            event_init = {}
        await self._element_channel.dispatchEvent(
            type=type, eventInit=serialize_argument(event_init), timeout=NO_TIMEOUT
        )

    async def scroll_into_view_if_needed(self, timeout: Optional[float]) -> None:
        await self._element_channel.scrollIntoViewIfNeeded(
            timeout=self._frame._timeout(timeout)
        )

    async def hover(
        self,
        modifiers: Optional[Sequence[KeyboardModifier]],
        position: Optional[Position],
        timeout: Optional[float],
        no_wait_after: Optional[bool],
        force: Optional[bool],
        trial: Optional[bool],
        scroll: Optional[Literal["auto", "none"]],
    ) -> None:
        await self._element_channel.hover(
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
        return await self._element_channel.click(
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
        no_wait_after: Optional[bool],
        trial: Optional[bool],
        steps: Optional[int],
        scroll: Optional[Literal["auto", "none"]],
    ) -> None:
        return await self._element_channel.dblclick(
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
        no_wait_after: Optional[bool],
        trial: Optional[bool],
        scroll: Optional[Literal["auto", "none"]],
    ) -> None:
        return await self._element_channel.tap(
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
        no_wait_after: Optional[bool],
    ) -> List[str]:
        converted = convert_select_option_values(value, index, label, element)
        result = await self._element_channel.selectOption(
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
        no_wait_after: Optional[bool],
        force: Optional[bool],
    ) -> None:
        return await self._element_channel.fill(
            value=value, force=force, timeout=self._frame._timeout(timeout)
        )

    async def select_text(
        self, force: Optional[bool], timeout: Optional[float]
    ) -> None:
        await self._element_channel.selectText(
            force=force, timeout=self._frame._timeout(timeout)
        )

    async def set_input_files(
        self,
        files: Union[
            str, Path, FilePayload, Sequence[Union[str, Path]], Sequence[FilePayload]
        ],
        timeout: Optional[float],
        no_wait_after: Optional[bool],
    ) -> None:
        frame = await self.owner_frame()
        if not frame:
            raise Error("Cannot set input files to detached element")
        converted = await convert_input_files(files, frame.page.context)
        await self._element_channel.setInputFiles(
            payloads=converted.get("payloads"),
            localDirectory=converted.get("localDirectory"),
            directoryStream=converted.get("directoryStream"),
            localPaths=converted.get("localPaths"),
            streams=converted.get("streams"),
            timeout=self._frame._timeout(timeout),
        )

    async def focus(self) -> None:
        await self._element_channel.focus(timeout=NO_TIMEOUT)

    async def type(
        self,
        text: str,
        delay: Optional[float],
        timeout: Optional[float],
        no_wait_after: Optional[bool],
    ) -> None:
        await self._element_channel.type(
            text=text, delay=delay, timeout=self._frame._timeout(timeout)
        )

    async def press(
        self,
        key: str,
        delay: Optional[float],
        timeout: Optional[float],
        no_wait_after: Optional[bool],
    ) -> None:
        await self._element_channel.press(
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
        no_wait_after: Optional[bool],
        trial: Optional[bool],
        scroll: Optional[Literal["auto", "none"]],
    ) -> None:
        return await self._element_channel.check(
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
        no_wait_after: Optional[bool],
        trial: Optional[bool],
        scroll: Optional[Literal["auto", "none"]],
    ) -> None:
        return await self._element_channel.uncheck(
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
        value = (await self._element_channel.boundingBox(timeout=NO_TIMEOUT))["value"]
        # Python: an undefined value is None, as null is.
        return value

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
        # Python: the options are separate parameters; copy is the type and the mask
        # of the params.
        copy_type = type
        copy_mask: Optional[List["channels.ElementHandleScreenshotParamsMask"]] = None
        if not copy_type:
            copy_type = determine_screenshot_type(path, type)
        # Python: an empty list is a mask, as an empty array is truthy.
        if mask is not None:
            copy_mask = [
                {
                    "frame": locator._frame._channel,
                    "selector": locator._selector,
                }
                for locator in mask
            ]
        result = await self._element_channel.screenshot(
            type=copy_type,
            quality=quality,
            omitBackground=omit_background,
            caret=caret,
            animations=animations,
            scale=scale,
            mask=copy_mask,
            maskColor=mask_color,
            style=style,
            timeout=self._frame._timeout(timeout),
        )
        # Python: the binary is base64 on the channel.
        binary = base64.b64decode(result["binary"])
        if path:
            await mkdir_if_needed(path)
            await _write_file(path, binary)
        return binary

    async def query_selector(self, selector: str) -> Optional["ElementHandle"]:
        return ElementHandle.from_nullable(
            (
                await self._element_channel.querySelector(
                    selector=selector, strict=None, timeout=NO_TIMEOUT
                )
            )["element"]
        )

    async def query_selector_all(self, selector: str) -> List["ElementHandle"]:
        result = await self._element_channel.querySelectorAll(
            selector=selector, timeout=NO_TIMEOUT
        )
        return [ElementHandle.from_(h) for h in result["elements"]]

    async def eval_on_selector(
        self, selector: str, expression: str, arg: Serializable
    ) -> Any:
        result = await self._element_channel.evalOnSelector(
            selector=selector,
            strict=None,
            expression=expression,
            # Python: undefined; see the docstring of js_handle.py.
            isFunction=None,
            arg=serialize_argument(arg),
            timeout=NO_TIMEOUT,
        )
        return parse_result(result["value"])

    async def eval_on_selector_all(
        self, selector: str, expression: str, arg: Serializable
    ) -> Any:
        result = await self._element_channel.evalOnSelectorAll(
            selector=selector,
            expression=expression,
            # Python: undefined; see the docstring of js_handle.py.
            isFunction=None,
            arg=serialize_argument(arg),
            timeout=NO_TIMEOUT,
        )
        return parse_result(result["value"])

    async def wait_for_element_state(
        self,
        state: Literal[
            "disabled", "editable", "enabled", "hidden", "stable", "visible"
        ],
        timeout: Optional[float],
    ) -> None:
        return await self._element_channel.waitForElementState(
            state=state, timeout=self._frame._timeout(timeout)
        )

    async def wait_for_selector(
        self,
        selector: str,
        state: Optional[Literal["attached", "detached", "hidden", "visible"]],
        timeout: Optional[float],
        strict: Optional[bool],
    ) -> Optional["ElementHandle"]:
        result = await self._element_channel.waitForSelector(
            selector=selector,
            strict=strict,
            state=state,
            timeout=self._frame._timeout(timeout),
        )
        return ElementHandle.from_nullable(result["element"])


class SelectOptionValues(TypedDict, total=False):
    elements: List["ElementHandleChannel"]
    options: List["channels.ElementHandleSelectOptionParamsOptions"]


def convert_select_option_values(
    value: Optional[Union[str, Sequence[str]]],
    index: Optional[Union[int, Sequence[int]]],
    label: Optional[Union[str, Sequence[str]]],
    element: Optional[Union["ElementHandle", Sequence["ElementHandle"]]],
) -> SelectOptionValues:
    # Python: the Python API passes the options as value=, index=, label= and
    # element=, each one a value or a list, not as one value or list of strings,
    # objects or handles. A value matches the value or the label, as a string of
    # upstream does; an index and a label are the objects { index } and { label }.
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
    # Python: assert() of isomorphic/assert.ts throws an Error.
    for i, option in enumerate(options):
        if None in option.values():
            raise Error(f"options[{i}]: expected object, got null")
    for i, handle in enumerate(elements):
        if handle is None:
            raise Error(f"options[{i}]: expected object, got null")
    result: SelectOptionValues = {}
    if elements:
        result["elements"] = [handle._element_channel for handle in elements]
    if options:
        result["options"] = options
    return result


# Python only: wraps a single value of any type in a list, as upstream does with
# `if (!Array.isArray(values)) values = [values]`. The driver checks the type.
def _to_list(value: Any) -> List[Any]:
    if isinstance(value, str) or not isinstance(value, collections.abc.Iterable):
        return [value]
    return list(value)


class SetInputFilesFiles(TypedDict, total=False):
    payloads: Optional[List["channels.ElementHandleSetInputFilesParamsPayloads"]]
    localPaths: Optional[List[str]]
    localDirectory: Optional[str]
    streams: Optional[List["WritableStreamChannel"]]
    directoryStream: Optional["WritableStreamChannel"]


def file_payload_exceeds_size_limit(payloads: Sequence[FilePayload]) -> bool:
    return (
        sum(len(item["buffer"]) if item.get("buffer") else 0 for item in payloads)
        >= file_upload_size_limit
    )


async def resolve_paths_and_directory_for_input_files(
    items: Sequence[Union[str, Path]],
) -> Tuple[Optional[List[str]], Optional[str]]:
    local_paths: Optional[List[str]] = None
    local_directory: Optional[str] = None
    for item in items:
        # Python: os.stat() is fs.promises.stat(); it is quick, so it runs in the
        # event loop, not in a thread. It raises FileNotFoundError for a path that
        # does not exist, as fs.promises.stat() rejects with ENOENT.
        item_stat = os.stat(item)
        if stat.S_ISDIR(item_stat.st_mode):
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
    # Python: a list or a tuple is the array; a str, a Path or a FilePayload is one
    # item.
    items: List[Any] = (
        list(files)
        if isinstance(files, collections.abc.Sequence) and not isinstance(files, str)
        else [files]
    )

    # Python: a path is a str or a pathlib.Path.
    if any(isinstance(item, (str, Path)) for item in items):
        if not all(isinstance(item, (str, Path)) for item in items):
            raise Error("File paths cannot be mixed with buffers")

        local_paths, local_directory = (
            await resolve_paths_and_directory_for_input_files(items)
        )

        if context._connection.is_remote():
            files_to_stream = (
                _read_dir_files(local_directory)
                if local_directory
                else cast(List[str], local_paths)
            )

            async def create_temp_files() -> (
                "channels.BrowserContextCreateTempFilesResult"
            ):
                return await context._channel.createTempFiles(
                    rootDirName=(
                        os.path.basename(local_directory) if local_directory else None
                    ),
                    # Python: os.stat() is synchronous, so the items are not built
                    # in parallel (Promise.all).
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
                    timeout=NO_TIMEOUT,
                )

            result = await context._wrap_api_call(
                lambda _: create_temp_files(), ApiCallOptions(internal=True)
            )
            writable_streams = result["writableStreams"]
            root_dir = result["rootDir"]
            for i in range(len(files_to_stream)):
                writable = WritableStream.from_(writable_streams[i])
                await pipeline(files_to_stream[i], writable.stream())
            return {
                "directoryStream": root_dir,
                "streams": None if local_directory else writable_streams,
            }
        return {
            "localPaths": local_paths,
            "localDirectory": local_directory,
        }

    payloads = cast(List[FilePayload], items)
    if file_payload_exceeds_size_limit(payloads):
        raise Error(
            "Cannot set buffer larger than 50Mb, please write it to a file and pass its path instead."
        )
    # Python: the buffer is base64 on the channel.
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
    type: Optional[Literal["jpeg", "png", "webp"]],
) -> Optional[Literal["jpeg", "png", "webp"]]:
    # Python: the options { path, type } are separate parameters.
    if path:
        mime_type = get_mime_type_for_path(str(path))
        if mime_type == "image/png":
            return "png"
        elif mime_type == "image/jpeg":
            return "jpeg"
        elif mime_type == "image/webp":
            return "webp"
        # Python: a template literal prints null as "null".
        raise Error(f'path: unsupported mime type "{mime_type or "null"}"')
    return type


# Python only: fs.promises.readdir(directory, { withFileTypes: true, recursive: true })
# filtered with isFile(): the regular files under the directory, not the links.
def _read_dir_files(directory: str) -> List[str]:
    result: List[str] = []
    for root, _, names in os.walk(directory):
        for name in names:
            file = os.path.join(root, name)
            if os.path.isfile(file) and not os.path.islink(file):
                result.append(file)
    return result


# Python only: fs.promises.writeFile(path, binary), in a thread.
async def _write_file(path: Union[str, Path], binary: bytes) -> None:
    def write() -> None:
        with open(path, "wb") as file:
            file.write(binary)

    await asyncio.get_running_loop().run_in_executor(None, write)
