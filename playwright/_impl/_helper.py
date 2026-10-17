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
import math
import os
import re
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
    Set,
    TypedDict,
    TypeVar,
    Union,
    cast,
    overload,
)

from playwright._impl._errors import is_target_closed_error, rewrite_error
from playwright._impl._greenlets import RouteGreenlet
from playwright._impl._str_utils import escape_regex_flags
from playwright._impl._url_match import (
    URLMatch,
    resolve_glob_to_regex_pattern,
    url_matches,
)

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl import _protocol_types as channels
    from playwright._impl._network import Request, Response, Route, WebSocketRoute

URLMatchRequest = Union[
    str, Pattern[str], Callable[["Request"], Union[bool, Awaitable[bool]]]
]
URLMatchResponse = Union[
    str, Pattern[str], Callable[["Response"], Union[bool, Awaitable[bool]]]
]
RouteHandlerCallback = Union[
    Callable[["Route"], Any], Callable[["Route", "Request"], Any]
]
WebSocketRouteHandlerCallback = Callable[["WebSocketRoute"], Any]

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
RouteFromHarNotFoundPolicy = Literal["abort", "fallback"]


class HarRecordingMetadata(TypedDict, total=False):
    path: str
    content: Optional[HarContentPolicy]


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


def create_task_and_ignore_exception(
    loop: asyncio.AbstractEventLoop, coro: Awaitable[Any]
) -> None:
    async def _ignore_exception() -> None:
        try:
            await coro
        except Exception:
            pass

    loop.create_task(_ignore_exception())


class RouteHandlerInvocation:
    complete: "asyncio.Future"
    route: "Route"

    def __init__(self, complete: "asyncio.Future", route: "Route") -> None:
        self.complete = complete
        self.route = route


class RouteHandler:
    def __init__(
        self,
        base_url: Optional[str],
        url: URLMatch,
        handler: RouteHandlerCallback,
        is_sync: bool,
        times: Optional[int] = None,
    ):
        self._base_url = base_url
        self.url = url
        self.handler = handler
        self._times = times if times else math.inf
        self._handled_count = 0
        self._is_sync = is_sync
        self._ignore_exception = False
        self._active_invocations: Set[RouteHandlerInvocation] = set()
        # Eagerly validate string globs so that invalid patterns throw at the call site
        # (e.g. page.route()) rather than silently aborting requests later.
        if isinstance(url, str):
            resolve_glob_to_regex_pattern(base_url, url)

    def matches(self, request_url: str) -> bool:
        return url_matches(self._base_url, request_url, self.url)

    async def handle(self, route: "Route") -> bool:
        handler_invocation = RouteHandlerInvocation(
            asyncio.get_running_loop().create_future(), route
        )
        self._active_invocations.add(handler_invocation)
        try:
            return await self._handle_internal(route)
        except Exception as e:
            # If the handler was stopped (without waiting for completion), we ignore all exceptions.
            if self._ignore_exception:
                return False
            if is_target_closed_error(e):
                # We are failing in the handler because the target has closed.
                # Give user a hint!
                optional_async_prefix = "await " if not self._is_sync else ""
                raise rewrite_error(
                    e,
                    f"\"{str(e)}\" while running route callback.\nConsider awaiting `{optional_async_prefix}page.unroute_all(behavior='ignoreErrors')`\nbefore the end of the test to ignore remaining routes in flight.",
                )
            raise e
        finally:
            handler_invocation.complete.set_result(None)
            self._active_invocations.remove(handler_invocation)

    async def _handle_internal(self, route: "Route") -> bool:
        handled_future = route._start_handling()

        self._handled_count += 1
        if self._is_sync:
            handler_finished_future = route._loop.create_future()

            def _handler() -> None:
                try:
                    self.handler(route, route.request)  # type: ignore
                    handler_finished_future.set_result(None)
                except Exception as e:
                    handler_finished_future.set_exception(e)

            # As with event handlers, each route handler is a potentially blocking context
            # so it needs a fiber.
            g = RouteGreenlet(_handler)
            g.switch()
            await handler_finished_future
        else:
            coro_or_future = self.handler(route, route.request)  # type: ignore
            if coro_or_future:
                # separate task so that we get a proper stack trace for exceptions / tracing api_name extraction
                await asyncio.ensure_future(coro_or_future)
        return await handled_future

    async def stop(self, behavior: Literal["ignoreErrors", "wait"]) -> None:
        # When a handler is manually unrouted or its page/context is closed we either
        # - wait for the current handler invocations to finish
        # - or do not wait, if the user opted out of it, but swallow all exceptions
        #   that happen after the unroute/close.
        if behavior == "ignoreErrors":
            self._ignore_exception = True
        else:
            tasks = []
            for activation in self._active_invocations:
                if not activation.route._did_throw:
                    tasks.append(activation.complete)
            await asyncio.gather(*tasks)

    @property
    def will_expire(self) -> bool:
        return self._handled_count + 1 >= self._times

    @staticmethod
    def prepare_interception_patterns(
        handlers: List["RouteHandler"],
    ) -> List["channels.BrowserContextSetNetworkInterceptionPatternsParamsPatterns"]:
        patterns: List[
            "channels.BrowserContextSetNetworkInterceptionPatternsParamsPatterns"
        ] = []
        all = False
        for handler in handlers:
            if isinstance(handler.url, str):
                patterns.append({"glob": handler.url})
            elif isinstance(handler.url, re.Pattern):
                patterns.append(
                    {
                        "regexSource": handler.url.pattern,
                        "regexFlags": escape_regex_flags(handler.url),
                    }
                )
            else:
                all = True
        if all:
            return [{"glob": "**/*"}]
        return patterns


def make_dirs_for_file(path: Union[Path, str]) -> None:
    if not os.path.isabs(path):
        path = Path.cwd() / path
    os.makedirs(os.path.dirname(path), exist_ok=True)


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


def is_file_payload(value: Optional[Any]) -> bool:
    return (
        isinstance(value, dict)
        and "name" in value
        and "mimeType" in value
        and "buffer" in value
    )


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
