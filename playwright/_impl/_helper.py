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
import math
import os
import re
import time
import traceback
from pathlib import Path
from types import TracebackType
from typing import (
    TYPE_CHECKING,
    Any,
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
)
from urllib.parse import urljoin

from playwright._impl._api_structures import NameValue
from playwright._impl._errors import (
    Error,
    TargetClosedError,
    TimeoutError,
    is_target_closed_error,
    rewrite_error,
)
from playwright._impl._glob import glob_to_regex
from playwright._impl._greenlets import RouteGreenlet
from playwright._impl._str_utils import escape_regex_flags

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._api_structures import HeadersArray
    from playwright._impl._network import Request, Response, Route, WebSocketRoute

URLMatch = Union[str, Pattern[str], Callable[[str], bool]]
URLMatchRequest = Union[str, Pattern[str], Callable[["Request"], bool]]
URLMatchResponse = Union[str, Pattern[str], Callable[["Response"], bool]]
RouteHandlerCallback = Union[
    Callable[["Route"], Any], Callable[["Route", "Request"], Any]
]
WebSocketRouteHandlerCallback = Callable[["WebSocketRoute"], Any]

ColorScheme = Literal["dark", "light", "no-preference", "null"]
ForcedColors = Literal["active", "none", "null"]
ReducedMotion = Literal["no-preference", "null", "reduce"]
DocumentLoadState = Literal["commit", "domcontentloaded", "load", "networkidle"]
KeyboardModifier = Literal["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]
MouseButton = Literal["left", "middle", "right"]
ServiceWorkersPolicy = Literal["allow", "block"]
HarMode = Literal["full", "minimal"]
HarContentPolicy = Literal["attach", "embed", "omit"]
RouteFromHarNotFoundPolicy = Literal["abort", "fallback"]


class ErrorPayload(TypedDict, total=False):
    message: str
    name: str
    stack: str
    value: Optional[Any]


class HarRecordingMetadata(TypedDict, total=False):
    path: str
    content: Optional[HarContentPolicy]


def prepare_record_har_options(params: Dict) -> Dict[str, Any]:
    out_params: Dict[str, Any] = {"path": str(params["recordHarPath"])}
    if "recordHarUrlFilter" in params:
        opt = params["recordHarUrlFilter"]
        if isinstance(opt, str):
            out_params["urlGlob"] = opt
        if isinstance(opt, Pattern):
            out_params["urlRegexSource"] = opt.pattern
            out_params["urlRegexFlags"] = escape_regex_flags(opt)
        del params["recordHarUrlFilter"]
    if "recordHarMode" in params:
        out_params["mode"] = params["recordHarMode"]
        del params["recordHarMode"]

    new_content_api = None
    old_content_api = None
    if "recordHarContent" in params:
        new_content_api = params["recordHarContent"]
        del params["recordHarContent"]
    if "recordHarOmitContent" in params:
        old_content_api = params["recordHarOmitContent"]
        del params["recordHarOmitContent"]
    content = new_content_api or ("omit" if old_content_api else None)
    if content:
        out_params["content"] = content

    return out_params


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


Env = Dict[str, Union[str, float, bool]]


class URLMatcher:
    def __init__(self, base_url: Union[str, None], match: URLMatch) -> None:
        self._callback: Optional[Callable[[str], bool]] = None
        self._regex_obj: Optional[Pattern[str]] = None
        if isinstance(match, str):
            if base_url and not match.startswith("*"):
                match = urljoin(base_url, match)
            regex = glob_to_regex(match)
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


class HarLookupResult(TypedDict, total=False):
    action: Literal["error", "redirect", "fulfill", "noentry"]
    message: Optional[str]
    redirectURL: Optional[str]
    status: Optional[int]
    headers: Optional["HeadersArray"]
    body: Optional[str]


class TimeoutSettings:
    def __init__(self, parent: Optional["TimeoutSettings"]) -> None:
        self._parent = parent
        self._default_timeout: Optional[float] = None
        self._default_navigation_timeout: Optional[float] = None

    def set_default_timeout(self, timeout: Optional[float]) -> None:
        self._default_timeout = timeout

    def timeout(self, timeout: float = None) -> float:
        if timeout is not None:
            return timeout
        if self._default_timeout is not None:
            return self._default_timeout
        if self._parent:
            return self._parent.timeout()
        return 30000

    def set_default_navigation_timeout(
        self, navigation_timeout: Optional[float]
    ) -> None:
        self._default_navigation_timeout = navigation_timeout

    def default_navigation_timeout(self) -> Optional[float]:
        return self._default_navigation_timeout

    def default_timeout(self) -> Optional[float]:
        return self._default_timeout

    def navigation_timeout(self) -> float:
        if self._default_navigation_timeout is not None:
            return self._default_navigation_timeout
        if self._parent:
            return self._parent.navigation_timeout()
        return 30000


def serialize_error(ex: Exception, tb: Optional[TracebackType]) -> ErrorPayload:
    return ErrorPayload(
        message=str(ex), name="Error", stack="".join(traceback.format_tb(tb))
    )


def parse_error(error: ErrorPayload, log: Optional[str] = None) -> Error:
    base_error_class = Error
    if error.get("name") == "TimeoutError":
        base_error_class = TimeoutError
    if error.get("name") == "TargetClosedError":
        base_error_class = TargetClosedError
    if not log:
        log = ""
    exc = base_error_class(patch_error_message(error["message"]) + log)
    exc._name = error["name"]
    exc._stack = error["stack"]
    return exc


def patch_error_message(message: str) -> str:
    match = re.match(r"(\w+)(: expected .*)", message)
    if match:
        message = to_snake_case(match.group(1)) + match.group(2)
    message = message.replace(
        "Pass { acceptDownloads: true }", "Pass 'accept_downloads=True'"
    )
    return message


def locals_to_params(args: Dict) -> Dict:
    copy = {}
    for key in args:
        if key == "self":
            continue
        if args[key] is not None:
            copy[key] = (
                args[key]
                if not isinstance(args[key], Dict)
                else locals_to_params(args[key])
            )
    return copy


def monotonic_time() -> int:
    return math.floor(time.monotonic() * 1000)


class RouteHandlerInvocation:
    complete: "asyncio.Future"
    route: "Route"

    def __init__(self, complete: "asyncio.Future", route: "Route") -> None:
        self.complete = complete
        self.route = route


class RouteHandler:
    def __init__(
        self,
        matcher: URLMatcher,
        handler: RouteHandlerCallback,
        is_sync: bool,
        times: Optional[int] = None,
    ):
        self.matcher = matcher
        self.handler = handler
        self._times = times if times else math.inf
        self._handled_count = 0
        self._is_sync = is_sync
        self._ignore_exception = False
        self._active_invocations: Set[RouteHandlerInvocation] = set()

    def matches(self, request_url: str) -> bool:
        return self.matcher.matches(request_url)

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
    ) -> List[Dict[str, str]]:
        patterns = []
        all = False
        for handler in handlers:
            if isinstance(handler.matcher.match, str):
                patterns.append({"glob": handler.matcher.match})
            elif isinstance(handler.matcher._regex_obj, re.Pattern):
                patterns.append(
                    {
                        "regexSource": handler.matcher._regex_obj.pattern,
                        "regexFlags": escape_regex_flags(handler.matcher._regex_obj),
                    }
                )
            else:
                all = True
        if all:
            return [{"glob": "**/*"}]
        return patterns


to_snake_case_regex = re.compile("((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))")


def to_snake_case(name: str) -> str:
    return to_snake_case_regex.sub(r"_\1", name).lower()


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


def object_to_array(obj: Optional[Dict]) -> Optional[List[NameValue]]:
    if not obj:
        return None
    result = []
    for key, value in obj.items():
        result.append(NameValue(name=key, value=str(value)))
    return result


def is_file_payload(value: Optional[Any]) -> bool:
    return (
        isinstance(value, dict)
        and "name" in value
        and "mimeType" in value
        and "buffer" in value
    )


TEXTUAL_MIME_TYPE = re.compile(
    r"^(text\/.*?|application\/(json|(x-)?javascript|xml.*?|ecmascript|graphql|x-www-form-urlencoded)|image\/svg(\+xml)?|application\/.*?(\+json|\+xml))(;\s*charset=.*)?$"
)


def is_textual_mime_type(mime_type: str) -> bool:
    return bool(TEXTUAL_MIME_TYPE.match(mime_type))
