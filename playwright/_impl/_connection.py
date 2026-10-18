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
import collections.abc
import contextvars
import functools
import inspect
import os
import random
import site
import string
import sys
import sysconfig
import traceback
from pathlib import Path
from types import FrameType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    TypedDict,
    TypeVar,
    Union,
    cast,
    overload,
)

from pyee import EventEmitter
from pyee.asyncio import AsyncIOEventEmitter

import playwright
import playwright._impl._impl_to_api_mapping
from playwright._impl._channel import Channel
from playwright._impl._errors import (
    Error,
    TargetClosedError,
    parse_error,
    rewrite_error_message,
)
from playwright._impl._event_context_manager import EventContextManagerImpl
from playwright._impl._greenlets import EventGreenlet
from playwright._impl._helper import (
    ParsedMessagePayload,
)
from playwright._impl._protocol import ERROR_DETAILS, EXTENDS
from playwright._impl._protocol_channels import CHANNEL_CLASSES
from playwright._impl._protocol_check import check_message, is_enabled
from playwright._impl._transport import Transport

if TYPE_CHECKING:
    from playwright._impl._local_utils import LocalUtils
    from playwright._impl._playwright import Playwright
    from playwright._impl._protocol_channels import RootChannel

_PLAYWRIGHT_MODULE_PATH = os.path.join(str(Path(playwright.__file__).parents[0]), "")


def _non_user_code_dirs() -> Tuple[str, ...]:
    # The directories of the Python standard library (asyncio, threading, ...), of the
    # installed packages (pytest, pluggy, greenlet, pyee, ...) and of their launcher
    # scripts. The Python counterpart of the node internals and of the test runner's
    # boxed stack prefixes that filterStackFile() in packages/utils/stackTrace.ts drops.
    paths = sysconfig.get_paths()
    dirs = {
        paths.get(name)
        for name in ("stdlib", "platstdlib", "purelib", "platlib", "scripts")
    }
    if hasattr(site, "getsitepackages"):
        dirs.update(site.getsitepackages())
    if hasattr(site, "getusersitepackages"):
        dirs.add(site.getusersitepackages())
    dirs.update(
        entry
        for entry in sys.path
        if os.path.basename(entry) in ("site-packages", "dist-packages")
    )
    result = set()
    for dir in dirs:
        if not dir:
            continue
        for variant in (dir, os.path.realpath(dir)):
            result.add(os.path.join(os.path.normcase(os.path.abspath(variant)), ""))
    return tuple(result)


_NON_USER_CODE_DIRS = _non_user_code_dirs()


@functools.lru_cache(maxsize=None)
def _is_user_file(filename: str) -> bool:
    # Port of filterStackFile() in packages/utils/stackTrace.ts.
    if filename.startswith(_PLAYWRIGHT_MODULE_PATH):
        return False
    # Code without a source file: frozen modules of the standard library (runpy,
    # importlib), and code that exec() runs, such as the pytest-xdist workers.
    if filename.startswith("<") and filename.endswith(">"):
        return False
    return not os.path.normcase(filename).startswith(_NON_USER_CODE_DIRS)


# The event loop runs each task step and callback from Handle._run(). The frames below
# it run the event loop and did not call the task, like in the Node.js event loop. So an
# action in a task that asyncio.create_task() started does not get the location of the
# asyncio.run() call.
_EVENT_LOOP_CALLBACK_CODE = asyncio.events.Handle._run.__code__


class ChannelOwner(AsyncIOEventEmitter):
    def __init__(
        self,
        parent: Union["ChannelOwner", "Connection"],
        type: str,
        guid: str,
        initializer: Dict,
    ) -> None:
        super().__init__(loop=parent._loop)
        self._loop: asyncio.AbstractEventLoop = parent._loop
        self._dispatcher_fiber: Any = parent._dispatcher_fiber
        self._type = type
        self._guid: str = guid
        self._connection: Connection = (
            parent._connection if isinstance(parent, ChannelOwner) else parent
        )
        self._parent: Optional[ChannelOwner] = (
            parent if isinstance(parent, ChannelOwner) else None
        )
        self._objects: Dict[str, "ChannelOwner"] = {}
        self._event_to_subscription_mapping: Dict[str, str] = {}
        self._was_collected = False

        self._connection._objects[guid] = self
        if self._parent:
            self._parent._objects[guid] = self

        self._channel: Channel = CHANNEL_CLASSES.get(type, Channel)(
            self._connection, self
        )
        self._initializer = initializer

    async def _wrap_api_call(
        self, cb: Callable[[], Any], is_internal: bool = False, title: str = None
    ) -> Any:
        return await self._connection.wrap_api_call(cb, is_internal, title)

    def _dispose(self, reason: Optional[str]) -> None:
        # Clean up from parent and connection.
        if self._parent:
            del self._parent._objects[self._guid]
        del self._connection._objects[self._guid]
        self._was_collected = reason == "gc"

        # Dispose all children.
        for object in list(self._objects.values()):
            object._dispose(reason)
        self._objects.clear()

    def _adopt(self, child: "ChannelOwner") -> None:
        del cast("ChannelOwner", child._parent)._objects[child._guid]
        self._objects[child._guid] = child
        child._parent = self

    def _set_event_to_subscription_mapping(self, mapping: Dict[str, str]) -> None:
        self._event_to_subscription_mapping = mapping

    def _update_subscription(self, event: str, enabled: bool) -> None:
        protocol_event = self._event_to_subscription_mapping.get(event)
        if protocol_event:
            try:
                self._channel.send_no_reply(
                    "updateSubscription",
                    {"event": protocol_event, "enabled": enabled},
                    is_internal=True,
                )
            except Exception:
                pass

    # The overrides of on(), addListener() and prependListener() in channelOwner.ts:
    # pyee adds every listener, once() too, through _add_event_handler().
    def _add_event_handler(self, event: str, k: Any, v: Any) -> None:
        if not self.listeners(event):
            self._update_subscription(event, True)
        super()._add_event_handler(event, k, v)

    # The overrides of off() and removeListener() in channelOwner.ts: pyee removes
    # every listener, a once() listener that fired too, through _remove_listener().
    def _remove_listener(self, event: str, f: Any) -> None:
        if f not in self.listeners(event):
            return
        super()._remove_listener(event, f)
        if not self.listeners(event):
            self._update_subscription(event, False)


class ProtocolCallback:
    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        id: str,
        type: str,
        method: str,
        no_reply: bool = False,
    ) -> None:
        self.id = id
        self.type = type
        self.method = method
        self.stack_trace: "RawStack"
        self.no_reply = no_reply
        self.future = loop.create_future()
        if no_reply:
            self.future.set_result(None)
        # The outer task can get cancelled by the user, this forwards the cancellation to the inner task.
        current_task = asyncio.current_task()

        def cb(task: asyncio.Task) -> None:
            if current_task:
                current_task.remove_done_callback(cb)
            if task.cancelled():
                self.future.cancel()

        if current_task:
            current_task.add_done_callback(cb)
            self.future.add_done_callback(
                lambda _: (
                    current_task.remove_done_callback(cb) if current_task else None
                )
            )


ChannelOwnerFactory = Callable[[ChannelOwner, str, str, Dict], ChannelOwner]


def _declares_error_details(type: str, method: str) -> bool:
    # maybeFindValidator(type, method, "ErrorDetails") in client/connection.ts: a
    # derived interface has the commands of its base.
    interface: Optional[str] = type
    while interface:
        if method in ERROR_DETAILS.get(interface, {}):
            return True
        interface = EXTENDS.get(interface)
    return False


class Root(ChannelOwner):
    _channel: "RootChannel"

    def __init__(self, connection: "Connection") -> None:
        super().__init__(connection, "Root", "", {})

    async def initialize(self) -> "Playwright":
        result = await self._channel.initialize(sdkLanguage="python")
        return from_channel(result["playwright"])


class DummyChannelOwner(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)


class Connection(EventEmitter):
    def __init__(
        self,
        dispatcher_fiber: Any,
        transport: Transport,
        loop: asyncio.AbstractEventLoop,
        local_utils: Optional["LocalUtils"] = None,
    ) -> None:
        super().__init__()
        self._dispatcher_fiber = dispatcher_fiber
        self._transport = transport
        self._transport.on_message = lambda msg: self.dispatch(msg)
        self._next_call_id = _create_call_id_generator()
        self._objects: Dict[str, ChannelOwner] = {}
        self._callbacks: Dict[str, ProtocolCallback] = {}
        self._object_factories: Dict[str, ChannelOwnerFactory] = {}
        self._is_sync = False
        self._child_ws_connections: List["Connection"] = []
        self._loop = loop
        self.playwright_future: asyncio.Future["Playwright"] = loop.create_future()
        self._error: Optional[BaseException] = None
        self.is_remote = False
        self._init_task: Optional[asyncio.Task] = None
        self._api_zone: contextvars.ContextVar[Optional[ApiZone]] = (
            contextvars.ContextVar("ApiZone", default=None)
        )
        self._local_utils: Optional["LocalUtils"] = local_utils
        self._tracing_count = 0
        self._closed_error: Optional[Exception] = None
        self._check_protocol = is_enabled()
        # The factories are in their own module: this module can not import the
        # classes that derive from ChannelOwner.
        from playwright._impl._object_factory import object_factories

        self.register_object_factories(object_factories)

    def register_object_factories(
        self, factories: Dict[str, "ChannelOwnerFactory"]
    ) -> None:
        for type, factory in factories.items():
            self._object_factories[type] = factory

    @property
    def local_utils(self) -> "LocalUtils":
        assert self._local_utils
        return self._local_utils

    def mark_as_remote(self) -> None:
        self.is_remote = True

    async def run_as_sync(self) -> None:
        self._is_sync = True
        await self.run()

    async def run(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._root_object = Root(self)

        async def init() -> None:
            try:
                result = await self._root_object.initialize()
                if not self.playwright_future.done():
                    self.playwright_future.set_result(result)
            except Exception as exc:
                # No re-raise: callers observe playwright_future; a task
                # exception would log "never retrieved". Skip set_* if async
                # __aenter__ already cancelled the future after a transport error.
                if not self.playwright_future.done():
                    self.playwright_future.set_exception(exc)

        await self._transport.connect()
        self._init_task = self._loop.create_task(init())
        await self._transport.run()

    def stop_sync(self) -> None:
        self._transport.request_stop()
        self._dispatcher_fiber.switch()
        self._loop.run_until_complete(self._transport.wait_until_stopped())
        self.close()

    async def stop_async(self) -> None:
        self._transport.request_stop()
        await self._transport.wait_until_stopped()
        self.close()

    def close(self, cause: str = None) -> None:
        if self._closed_error:
            return
        self._closed_error = TargetClosedError(cause)
        if self._init_task and not self._init_task.done():
            self._init_task.cancel()
        for ws_connection in self._child_ws_connections:
            ws_connection.close(cause)
            ws_connection._transport.dispose()
        for callback in self._callbacks.values():
            # To prevent 'Future exception was never retrieved' we ignore all callbacks that are no_reply.
            if callback.no_reply:
                continue
            if callback.future.cancelled():
                continue
            callback.future.set_exception(self._closed_error)
        self._callbacks.clear()
        # Upstream rejects the initialize call with the other callbacks.
        if not self.playwright_future.done():
            self.playwright_future.set_exception(self._closed_error)
        self.emit("close")

    def set_is_tracing(self, is_tracing: bool) -> None:
        if is_tracing:
            self._tracing_count += 1
        else:
            self._tracing_count -= 1

    def _send_message_to_server(
        self,
        object: ChannelOwner,
        method: str,
        params: Dict,
        timeout: float,
        no_reply: bool = False,
    ) -> Optional[ProtocolCallback]:
        # Fire-and-forget: the server intentionally never replies to __waitInfo__,
        # so silently drop it after the connection is closed or the object was collected.
        if method == "__waitInfo__" and (self._closed_error or object._was_collected):
            return None
        if self._closed_error:
            raise self._closed_error
        if object._was_collected:
            raise Error(
                "The object has been collected to prevent unbounded heap growth."
            )
        id = self._next_call_id()
        # The channel proxy in client/channelOwner.ts reports the first message of an
        # API call with the title and the location of the call; the other messages,
        # and the messages of an internal call, are internal.
        zone = cast(ApiZone, self._api_zone.get())
        frames: Optional[List[StackFrame]] = None
        metadata: Dict[str, Any] = {"internal": True, "timeout": timeout}
        if not zone["internal"] and not zone["reported"]:
            zone["reported"] = True
            frames = zone["frames"]
            metadata = {"internal": False, "timeout": timeout}
            if zone["title"]:
                metadata["title"] = zone["title"]
            if frames:
                metadata["location"] = {
                    "file": frames[0]["file"],
                    "line": frames[0]["line"],
                    "column": frames[0]["column"],
                }
        message = {
            "id": id,
            "guid": object._guid,
            "method": method,
            "params": self._replace_channels_with_guids(params),
            "metadata": metadata,
        }
        if self._check_protocol:
            check_message(
                object._type,
                method,
                message["params"],
                metadata,
                self._type_of_guid,
            )
        if (
            self._tracing_count
            and frames is not None
            and object._type != "LocalUtils"
            and self._local_utils
        ):
            self._local_utils.add_stack_to_tracing_no_reply(id, frames)

        self._transport.send(message)
        # Fire-and-forget: the server intentionally never replies to __waitInfo__.
        if method == "__waitInfo__":
            return None
        callback = ProtocolCallback(
            self._loop, id, object._type, method, no_reply=no_reply
        )
        task = asyncio.current_task(self._loop)
        callback.stack_trace = cast(
            RawStack,
            getattr(task, "__pw_stack_trace__", None) or _extract_stack(limit=10),
        )
        self._callbacks[id] = callback
        return callback

    def _type_of_guid(self, guid: str) -> Optional[str]:
        object = self._objects.get(guid)
        return object._type if object else None

    async def _abort(
        self, object: ChannelOwner, callback: ProtocolCallback, reason: str
    ) -> None:
        try:
            self._transport.send(
                {
                    "guid": object._guid,
                    "method": "__abort__",
                    "params": {"id": callback.id, "reason": reason},
                }
            )
        except (Error, OSError):
            pass
        try:
            done, _ = await asyncio.wait(
                {
                    self._transport.on_error_future,
                    callback.future,
                },
                return_when=asyncio.FIRST_COMPLETED,
            )
        finally:
            if not callback.future.done():
                callback.future.cancel()
        for future in done:
            if not future.cancelled():
                future.exception()

    def dispatch(self, msg: ParsedMessagePayload) -> None:
        if self._closed_error:
            return
        id = msg.get("id")
        if id:
            callback = self._callbacks.get(id)
            if not callback:
                raise Exception(f"Cannot find command to respond: {id}")
            del self._callbacks[id]
            if callback.future.cancelled():
                return
            # The caller of a message without a reply ignores its result and its error,
            # as upstream's .catch(() => {}); so do not set an error that no one retrieves.
            if callback.no_reply:
                return
            error = msg.get("error")
            if error and not msg.get("result"):
                parsed_error = parse_error(error)
                log = msg.get("log")
                parsed_error._log = log or []
                parsed_error = cast(
                    Error,
                    rewrite_error_message(
                        parsed_error, str(parsed_error) + format_call_log(log)
                    ),
                )
                if _declares_error_details(callback.type, callback.method):
                    error_details = msg.get("errorDetails")
                    parsed_error._details = self._replace_guids_with_channels(
                        error_details if error_details is not None else {}
                    )
                parsed_error._stack = _format_stack(callback.stack_trace)
                callback.future.set_exception(parsed_error)
            else:
                result = self._replace_guids_with_channels(msg.get("result"))
                callback.future.set_result(result)
            return

        guid = msg["guid"]
        method = msg["method"]
        params = msg.get("params")
        if method == "__create__":
            assert params
            self._create_remote_object(
                guid, params["type"], params["guid"], params["initializer"]
            )
            return

        object = self._objects.get(guid)
        if not object:
            raise Exception(f'Cannot find object to "{method}": {guid}')

        if method == "__adopt__":
            child_guid = cast(Dict[str, str], params)["guid"]
            child = self._objects.get(child_guid)
            if not child:
                raise Exception(f"Unknown new child: {child_guid}")
            object._adopt(child)
            return

        if method == "__dispose__":
            assert isinstance(params, dict)
            object._dispose(cast(Optional[str], params.get("reason")))
            return

        should_replace_guids_with_channels = "jsonPipe@" not in guid
        try:
            if self._is_sync:
                for listener in object._channel._emitter.listeners(method):
                    # Event handlers like route/locatorHandlerTriggered require us to perform async work.
                    # In order to report their potential errors to the user, we need to catch it and store it in the connection
                    def _done_callback(future: asyncio.Future) -> None:
                        exc = future.exception()
                        if exc:
                            self._on_event_listener_error(exc)

                    def _listener_with_error_handler_attached(params: Any) -> None:
                        potential_future = listener(params)
                        if asyncio.isfuture(potential_future):
                            potential_future.add_done_callback(_done_callback)

                    # Each event handler is a potentilly blocking context, create a fiber for each
                    # and switch to them in order, until they block inside and pass control to each
                    # other and then eventually back to dispatcher as listener functions return.
                    g = EventGreenlet(_listener_with_error_handler_attached)
                    if should_replace_guids_with_channels:
                        g.switch(self._replace_guids_with_channels(params))
                    else:
                        g.switch(params)
            else:
                if should_replace_guids_with_channels:
                    object._channel._emitter.emit(
                        method, self._replace_guids_with_channels(params)
                    )
                else:
                    object._channel._emitter.emit(method, params)
        except BaseException as exc:
            self._on_event_listener_error(exc)

    def _on_event_listener_error(self, exc: BaseException) -> None:
        print("Error occurred in event listener", file=sys.stderr)
        traceback.print_exception(type(exc), exc, exc.__traceback__, file=sys.stderr)
        # Save the error to throw at the next API call. This "replicates" unhandled rejection in Node.js.
        self._error = exc

    def _create_remote_object(
        self, parent_guid: str, type: str, guid: str, initializer: Dict
    ) -> ChannelOwner:
        parent = self._objects.get(parent_guid)
        if not parent:
            raise Exception(f"Cannot find parent object {parent_guid} to create {guid}")
        initializer = self._replace_guids_with_channels(initializer)
        factory = self._object_factories.get(type)
        if not factory:
            raise Exception("Missing type " + type)
        return factory(parent, type, guid, initializer)

    def _replace_channels_with_guids(
        self,
        payload: Any,
    ) -> Any:
        if payload is None:
            return payload
        if isinstance(payload, Path):
            return str(payload)
        if isinstance(payload, collections.abc.Sequence) and not isinstance(
            payload, str
        ):
            return list(map(self._replace_channels_with_guids, payload))
        if isinstance(payload, Channel):
            return dict(guid=payload._guid)
        if isinstance(payload, dict):
            result = {}
            for key, value in payload.items():
                result[key] = self._replace_channels_with_guids(value)
            return result
        return payload

    def _replace_guids_with_channels(self, payload: Any) -> Any:
        if payload is None:
            return payload
        if isinstance(payload, list):
            return list(map(self._replace_guids_with_channels, payload))
        if isinstance(payload, dict):
            if payload.get("guid") in self._objects:
                return self._objects[payload["guid"]]._channel
            result = {}
            for key, value in payload.items():
                result[key] = self._replace_guids_with_channels(value)
            return result
        return payload

    async def wrap_api_call(
        self, cb: Callable[[], Any], is_internal: bool = False, title: str = None
    ) -> Any:
        # Port of ChannelOwner._wrapApiCall() in client/channelOwner.ts.
        outer_zone = self._api_zone.get()
        if outer_zone:
            _adopt_title(outer_zone, title)
            return await cb()
        task = asyncio.current_task(self._loop)
        zone = _create_api_zone(
            getattr(task, "__pw_stack__", None) or _capture_stack_trace(),
            is_internal,
            title,
        )
        self._api_zone.set(zone)
        try:
            return await cb()
        except Exception as error:
            raise _api_call_error(zone, error) from None
        finally:
            self._api_zone.set(None)

    def wrap_api_call_sync(
        self, cb: Callable[[], Any], is_internal: bool = False, title: str = None
    ) -> Any:
        outer_zone = self._api_zone.get()
        if outer_zone:
            _adopt_title(outer_zone, title)
            return cb()
        task = asyncio.current_task(self._loop)
        zone = _create_api_zone(
            getattr(task, "__pw_stack__", None) or _capture_stack_trace(),
            is_internal,
            title,
        )
        self._api_zone.set(zone)
        try:
            return cb()
        except Exception as error:
            raise _api_call_error(zone, error) from None
        finally:
            self._api_zone.set(None)

    def wrap_api_call_event(
        self, cb: Callable[[], EventContextManagerImpl], title: str = None
    ) -> EventContextManagerImpl:
        """wrap_api_call_sync() for an expect_*() method.

        The wait settles after the method returns, so the method records its API
        name on the future, and event_future_error() adds it to the error.
        """
        if self._api_zone.get():
            return cb()
        api_name = ""

        def inner() -> EventContextManagerImpl:
            nonlocal api_name
            api_name = cast(ApiZone, self._api_zone.get())["apiName"]
            return cb()

        result = self.wrap_api_call_sync(inner, title=title)
        if api_name:
            setattr(result.future, "__pw_api_name__", api_name)
        return result


def event_future_error(future: asyncio.Future, error: Exception) -> Exception:
    """The error of the future of an expect_*() method, with the API name prefix."""
    api_name = getattr(future, "__pw_api_name__", None)
    if not api_name:
        return error
    return rewrite_error_message(error, f"{api_name}: {error}")


ApiCallMethod = TypeVar("ApiCallMethod", bound=Callable[..., Any])


@overload
def api_call(method: ApiCallMethod) -> ApiCallMethod: ...


@overload
def api_call(
    *, title: Optional[str] = None
) -> Callable[[ApiCallMethod], ApiCallMethod]: ...


def api_call(
    method: Optional[ApiCallMethod] = None, *, title: Optional[str] = None
) -> Any:
    """Port of the apiCall() decorator in packages/playwright-core/src/client/channelOwner.ts.

    For a method that does its work on the client: its errors get the API name
    prefix ("Page.wait_for_url: ..."), as the errors of the protocol calls do.
    `@api_call(title=...)` titles the call, as `@apiCall({ title })` does.
    """

    def decorator(method: ApiCallMethod) -> ApiCallMethod:
        if inspect.iscoroutinefunction(method):

            @functools.wraps(method)
            async def async_wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
                # Like apiCall(), which calls this._wrapApiCall(): a ChannelOwner, or
                # an object that delegates to its owner (Locator, Mouse, Screencast).
                return await self._wrap_api_call(
                    lambda: method(self, *args, **kwargs), title=title
                )

            return cast(ApiCallMethod, async_wrapper)

        @functools.wraps(method)
        def event_wrapper(self: "ChannelOwner", *args: Any, **kwargs: Any) -> Any:
            return self._connection.wrap_api_call_event(
                lambda: method(self, *args, **kwargs), title=title
            )

        return cast(ApiCallMethod, event_wrapper)

    if method is None:
        return decorator
    return decorator(method)


def internal(method: ApiCallMethod) -> ApiCallMethod:
    """Port of the @internal decorator in client/channelOwner.ts: the method runs in an
    internal API zone, which is not reported as an API call."""

    @functools.wraps(method)
    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        return await self._wrap_api_call(
            lambda: method(self, *args, **kwargs), is_internal=True
        )

    return cast(ApiCallMethod, wrapper)


def from_channel(channel: Channel) -> Any:
    return channel._object


def from_nullable_channel(channel: Optional[Channel]) -> Optional[Any]:
    return channel._object if channel else None


class StackFrame(TypedDict):
    file: str
    line: int
    column: int
    function: Optional[str]


class ParsedStackTrace(TypedDict):
    frames: List[StackFrame]
    apiName: str


def _adopt_title(zone: "ApiZone", title: Optional[str]) -> None:
    # Python only: a method that waits after it returns, such as wait_for_url() around
    # expect_navigation(), opens its zone first. Its inner @api_call titles the call,
    # as the decorated inner call (waitForNavigation()) does upstream.
    if title and not zone["title"] and not zone["internal"] and not zone["reported"]:
        zone["title"] = title


class ApiZone(TypedDict):
    # Port of ApiZone in client/channelOwner.ts.
    apiName: str
    frames: List[StackFrame]
    title: Optional[str]
    internal: bool
    reported: bool


# The (file, line, function) of each frame, the outermost first.
RawStack = List[Tuple[str, int, str]]


def _extract_stack(limit: int) -> RawStack:
    # Like traceback.extract_stack(), but cheaper: every message records the stack of
    # its call for the error, and the time it takes delays the next message.
    stack: RawStack = []
    frame: Optional[FrameType] = sys._getframe(1)
    while frame and len(stack) < limit:
        stack.append((frame.f_code.co_filename, frame.f_lineno, frame.f_code.co_name))
        frame = frame.f_back
    stack.reverse()
    return stack


def _format_stack(stack: RawStack) -> str:
    return "".join(
        traceback.StackSummary.from_list(
            [(file, line, name, None) for file, line, name in stack]
        ).format()
    )


def _capture_stack_trace() -> ParsedStackTrace:
    # Port of captureLibraryStackTrace() in packages/playwright-core/src/client/clientStackTrace.ts.
    frame = inspect.currentframe()
    # Skip this helper and the caller that only captures the stack.
    frame = frame.f_back.f_back if frame and frame.f_back else None
    last_internal_api_name = ""
    api_name = ""
    parsed_frames: List[StackFrame] = []
    while frame:
        code = frame.f_code
        if code is _EVENT_LOOP_CALLBACK_CODE:
            break
        filename = code.co_filename
        # Sync and Async implementations can have event handlers. When these are sync, they
        # get evaluated in the context of the event loop, so they contain the stack trace of when
        # the message was received. _impl_to_api_mapping is glue between the user-code and internal
        # code to translate impl classes to api classes. We want to ignore these frames.
        if playwright._impl._impl_to_api_mapping.__file__ == filename:
            frame = frame.f_back
            continue
        is_playwright_internal = filename.startswith(_PLAYWRIGHT_MODULE_PATH)

        method_name = ""
        if "self" in frame.f_locals:
            method_name = frame.f_locals["self"].__class__.__name__ + "."
        method_name += code.co_name

        # Keep only the user's frames, as the inspector and the trace viewer show them.
        if _is_user_file(filename):
            parsed_frames.append(
                {
                    "file": filename,
                    "line": frame.f_lineno,
                    "column": 0,
                    "function": method_name,
                }
            )
        # The deepest transition from non-library code into library code is the API entry.
        if is_playwright_internal:
            last_internal_api_name = method_name
        elif last_internal_api_name:
            api_name = api_name or last_internal_api_name
            last_internal_api_name = ""
        frame = frame.f_back
    if not api_name:
        api_name = last_internal_api_name

    return {
        "frames": parsed_frames,
        "apiName": api_name,
    }


def _create_api_zone(
    stack_trace: ParsedStackTrace, internal: bool, title: Optional[str]
) -> ApiZone:
    # The zone that ChannelOwner._wrapApiCall() in client/channelOwner.ts creates.
    api_name = stack_trace["apiName"]
    if api_name.startswith("_") or "._" in api_name:
        api_name = title if title is not None else api_name
    return {
        "apiName": api_name,
        "frames": stack_trace["frames"],
        "title": title,
        "internal": internal,
        "reported": False,
    }


def _api_call_error(zone: ApiZone, error: Exception) -> Exception:
    # The error of an API call, as ChannelOwner._wrapApiCall() rewrites it.
    api_name = zone["apiName"]
    if api_name and "<lambda>" not in api_name:
        return rewrite_error_message(error, f"{api_name}: {error}")
    return error


def format_call_log(log: Optional[List[str]]) -> str:
    if not log or not any(log):
        return ""
    return "\nCall log:\n" + "\n".join(log) + "\n"


# Port of createCallIdGenerator() in packages/isomorphic/trace/traceUtils.ts: the
# ordinal is shared, and each connection has its own prefix to avoid id clashes in
# a trace.
_last_id_ordinal = 0


def _create_call_id_generator() -> Callable[[], str]:
    prefix = "".join(random.choices(string.ascii_lowercase, k=4))

    def next_call_id() -> str:
        global _last_id_ordinal
        _last_id_ordinal += 1
        return f"{prefix}@{_last_id_ordinal}"

    return next_call_id
