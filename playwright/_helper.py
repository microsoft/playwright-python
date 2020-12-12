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
import fnmatch
import math
import re
import sys
import time
import traceback
from types import TracebackType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Pattern,
    Union,
    cast,
)

from playwright._types import Error, TimeoutError

if sys.version_info >= (3, 8):  # pragma: no cover
    from typing import Literal, TypedDict
else:  # pragma: no cover
    from typing_extensions import Literal, TypedDict


if TYPE_CHECKING:  # pragma: no cover
    from playwright._network import Request, Route

URLMatch = Union[str, Pattern, Callable[[str], bool]]
RouteHandler = Callable[["Route", "Request"], Any]

ColorScheme = Literal["dark", "light", "no-preference"]
DocumentLoadState = Literal["domcontentloaded", "load", "networkidle"]
KeyboardModifier = Literal["Alt", "Control", "Meta", "Shift"]
MouseButton = Literal["left", "middle", "right"]


class SetFilePayload(TypedDict):
    name: str
    mimeType: str
    buffer: str


class ErrorPayload(TypedDict, total=False):
    message: str
    name: str
    stack: str
    value: Any


class Header(TypedDict):
    name: str
    value: str


class ContinueParameters(TypedDict, total=False):
    url: Optional[str]
    method: Optional[str]
    headers: Optional[List[Header]]
    postData: Optional[str]


class ParsedMessageParams(TypedDict):
    type: str
    guid: str
    initializer: Dict


class ParsedMessagePayload(TypedDict, total=False):
    id: int
    guid: str
    method: str
    params: ParsedMessageParams
    result: Any
    error: ErrorPayload


class Document(TypedDict):
    request: Optional[Any]


class FrameNavigatedEvent(TypedDict):
    url: str
    name: str
    newDocument: Optional[Document]
    error: Optional[str]


Env = Dict[str, Union[str, int, bool]]


class URLMatcher:
    def __init__(self, match: URLMatch) -> None:
        self._callback: Optional[Callable[[str], bool]] = None
        self._regex_obj: Optional[Pattern] = None
        if isinstance(match, str):
            regex = fnmatch.translate(match)
            self._regex_obj = re.compile(regex)
        elif isinstance(match, Pattern):
            self._regex_obj = match
        else:
            self._callback = match
        self.match = match

    def matches(self, url: str) -> bool:
        if self._callback:
            return self._callback(url)
        if self._regex_obj:
            return cast(bool, self._regex_obj.search(url))
        return False


class TimeoutSettings:
    def __init__(self, parent: Optional["TimeoutSettings"]) -> None:
        self._parent = parent
        self._timeout = 30000
        self._navigation_timeout = 30000

    def set_timeout(self, timeout: int) -> None:
        self._timeout = timeout

    def timeout(self) -> int:
        if self._timeout is not None:
            return self._timeout
        if self._parent:
            return self._parent.timeout()
        return 30000

    def set_navigation_timeout(self, navigation_timeout: int) -> None:
        self._navigation_timeout = navigation_timeout

    def navigation_timeout(self) -> int:
        if self._navigation_timeout is not None:
            return self._navigation_timeout
        if self._parent:
            return self._parent.navigation_timeout()
        return 30000


def serialize_error(ex: Exception, tb: Optional[TracebackType]) -> ErrorPayload:
    return dict(message=str(ex), stack="".join(traceback.format_tb(tb)))


def parse_error(error: ErrorPayload) -> Error:
    base_error_class = Error
    if error.get("name") == "TimeoutError":
        base_error_class = TimeoutError
    return base_error_class(error["message"], error["stack"])


def is_function_body(expression: str) -> bool:
    expression = expression.strip()
    return (
        expression.startswith("function")
        or expression.startswith("async ")
        or "=>" in expression
    )


def locals_to_params(args: Dict) -> Dict:
    copy = {}
    for key in args:
        if key == "self":
            continue
        if args[key] is not None:
            copy[key] = args[key]
    return copy


def monotonic_time() -> int:
    return math.floor(time.monotonic() * 1000)


class PendingWaitEvent:
    def __init__(
        self, event: str, future: asyncio.Future, timeout_future: asyncio.Future
    ):
        self.event = event
        self.future = future
        self.timeout_future = timeout_future

    def reject(self, is_crash: bool, target: str) -> None:
        self.timeout_future.cancel()
        if self.event == "close" and not is_crash:
            return
        if self.event == "crash" and is_crash:
            return
        self.future.set_exception(
            Error(f"{target} crashed" if is_crash else f"{target} closed")
        )


class RouteHandlerEntry:
    def __init__(self, matcher: URLMatcher, handler: RouteHandler):
        self.matcher = matcher
        self.handler = handler


def is_safe_close_error(error: Exception) -> bool:
    message = str(error)
    return message.endswith("Browser has been closed") or message.endswith(
        "Target page, context or browser has been closed"
    )


def not_installed_error(message: str) -> Exception:
    return Exception(
        f"""
================================================================================
{message}
Please complete Playwright installation via running

    "python -m playwright install"

================================================================================
"""
    )
