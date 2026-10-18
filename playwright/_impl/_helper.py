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
import datetime
import json
import os
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Pattern,
    TypedDict,
    TypeVar,
    Union,
    cast,
    overload,
)

from playwright._impl._errors import Error
from playwright._impl._str_utils import js_string

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl import _protocol_types as channels
    from playwright._impl._network import Request, Response

URLMatchRequest = Union[
    str, Pattern[str], Callable[["Request"], Union[bool, Awaitable[bool]]]
]
URLMatchResponse = Union[
    str, Pattern[str], Callable[["Response"], Union[bool, Awaitable[bool]]]
]

ColorScheme = Literal["dark", "light", "no-preference", "null"]
ForcedColors = Literal["active", "none", "null"]
Contrast = Literal["more", "no-preference", "null"]
ReducedMotion = Literal["no-preference", "null", "reduce"]
DocumentLoadState = Literal["commit", "domcontentloaded", "load", "networkidle"]
KeyboardModifier = Literal["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]
MouseButton = Literal["left", "middle", "right"]
ServiceWorkersPolicy = Literal["allow", "block"]
HarMode = Literal["full", "minimal"]
HarContentPolicy = Literal["attach", "embed", "omit"]


class ParsedMessageParams(TypedDict):
    type: str
    guid: str
    initializer: Dict


class ParsedMessagePayload(TypedDict, total=False):
    id: str
    guid: str
    method: str
    params: ParsedMessageParams
    result: Any
    error: "channels.SerializedError"
    errorDetails: Any
    log: List[str]


Env = Dict[str, Union[str, float, bool]]


def env_object_to_array(env: Env) -> List["channels.NameValue"]:
    # Port of envObjectToArray() in client/clientHelper.ts.
    return [
        {"name": name, "value": js_string(value)}
        for name, value in env.items()
        if value is not None
    ]


async def evaluation_script(
    script: Optional[str],
    path: Optional[Union[str, Path]],
    add_source_url: bool = True,
) -> str:
    # Port of evaluationScript() in client/clientHelper.ts, for the `script` and
    # `path` options of the Python API.
    if isinstance(script, str):
        return script
    if path is not None:
        source = (await async_readfile(path)).decode()
        if add_source_url:
            source = add_source_url_to_script(source, path)
        return source
    raise Error("Either path or script parameter must be present")


def add_source_url_to_script(source: str, path: Union[str, Path]) -> str:
    # Port of addSourceUrlToScript() in client/clientHelper.ts.
    return source + "\n//# sourceURL=" + str(path).replace("\n", "")


# Port of debugMode() in packages/utils/debug.ts.
_debug_mode = os.environ.get("PWDEBUG") or ""


def debug_mode() -> str:
    if _debug_mode == "console":
        return "console"
    if _debug_mode == "0" or _debug_mode == "false":
        return ""
    return "inspector" if _debug_mode else ""


def create_task_and_ignore_exception(
    loop: asyncio.AbstractEventLoop, coro: Awaitable[Any]
) -> None:
    async def _ignore_exception() -> None:
        try:
            await coro
        except Exception:
            pass

    loop.create_task(_ignore_exception())


# Port of fileUploadSizeLimit in client/fileUtils.ts.


async def async_writefile(file: Union[str, Path], data: Union[str, bytes]) -> None:
    def inner() -> None:
        with open(file, "w" if isinstance(data, str) else "wb") as fh:
            fh.write(data)

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, inner)


async def async_readfile(file: Union[str, Path]) -> bytes:
    def inner() -> bytes:
        with open(file, "rb") as fh:
            return fh.read()

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, inner)


T = TypeVar("T")


def to_impl(obj: T) -> T:
    if hasattr(obj, "_impl_obj"):
        return cast(Any, obj)._impl_obj
    return obj


@overload
def to_milliseconds(value: Union[float, datetime.timedelta]) -> float: ...


@overload
def to_milliseconds(value: None) -> None: ...


@overload
def to_milliseconds(
    value: Union[float, datetime.timedelta, None],
) -> Optional[float]: ...


def to_milliseconds(
    value: Union[float, datetime.timedelta, None],
) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, datetime.timedelta):
        return value / datetime.timedelta(milliseconds=1)
    return value


def json_stringify(value: Any, indent: Optional[int] = None) -> str:
    # Writes the same text as JSON.stringify(value, undefined, indent) in JavaScript:
    # no spaces without an indent, and no escapes for non-ASCII characters. NaN and
    # Infinity are not valid JSON.
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        indent=indent,
        separators=(",", ":") if indent is None else None,
    )
