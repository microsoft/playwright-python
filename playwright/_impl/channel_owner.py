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

"""Port of packages/playwright-core/src/client/channelOwner.ts.

Python: the channel proxy is Channel, the base of the typed channels that
protocol_channels.py generates from the protocol spec. Binary values stay base64
strings on the channel (the "base64" mode of the validator).
"""

import asyncio
import functools
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Literal,
    Mapping,
    Optional,
    Tuple,
    TypeVar,
    Union,
)

from playwright._impl.client_stack_trace import capture_library_stack_trace
from playwright._impl.errors import Error, patch_error_message
from playwright._impl.event_emitter import EventEmitter
from playwright._impl.protocol.validator import (
    ValidationError,
    ValidatorContext,
    maybe_find_validator,
)
from playwright._impl.utils.debug import is_under_test
from playwright._impl.utils.debug_logger import debug_logger
from playwright._impl.utils.stack_trace import (
    StackFrame,
    rewrite_error_message,
    show_internal_stack_frames,
    stringify_stack_frames,
)
from playwright._impl.utils.tasks import failed, fire_and_forget
from playwright._impl.utils.zones import current_zone

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl.client_instrumentation import ClientInstrumentation
    from playwright._impl.connection import Connection

R = TypeVar("R")

Listener = Callable[..., Any]


class ApiZone:
    def __init__(
        self,
        api_name: str,
        frames: List[StackFrame],
        title: Optional[str],
        internal: bool,
    ) -> None:
        self.api_name = api_name
        self.frames = frames
        self.title = title
        self.internal = internal
        self.reported = False
        self.user_data: Any = None
        self.call_id: Optional[str] = None
        self.error: Optional[Exception] = None

    def options(self) -> Dict[str, Any]:
        # Python: `{ ...apiZone }` in the options of sendMessageToServer().
        return {
            "api_name": self.api_name,
            "title": self.title,
            "internal": self.internal,
            "frames": self.frames,
            "call_id": self.call_id,
        }


class ApiCallOptions:
    def __init__(self, title: Optional[str] = None, internal: bool = False) -> None:
        self.title = title
        self.internal = internal


class Channel(EventEmitter):
    """The channel proxy that ChannelOwner._createChannel() creates."""

    def __init__(self, object: "ChannelOwner") -> None:
        super().__init__()
        self._object = object
        # (event, handler) -> the listeners registered for it, in order.
        self._event_listeners: Dict[Tuple[str, Any], List[Listener]] = {}

    def _report_unhandled_error(self, error: BaseException) -> None:
        self._object._connection._on_event_listener_error(error)

    def _call(
        self,
        method: str,
        params: Mapping[str, Any],
        timeout: float,
        mapper: Optional[Callable[[Any], Any]],
        is_internal: bool = False,
    ) -> Awaitable[Any]:
        owner = self._object

        validator = maybe_find_validator(owner._type, method, "Params")
        assert validator

        def func(api_zone: ApiZone) -> Awaitable[Any]:
            try:
                validated_params = validator(
                    params, "", owner._validator_to_wire_context()
                )
            except ValidationError as e:
                # Python: the messages name the Python options.
                raise ValidationError(patch_error_message(e.message)) from None
            if not api_zone.internal and not api_zone.reported:
                # Reporting/tracing/logging this api call for the first time.
                api_zone.reported = True
                owner._instrumentation.on_api_call_begin(
                    api_zone, {"type": owner._type, "method": method, "params": params}
                )
                log_api_call(owner._logger, f"=> {api_zone.api_name} started")
                return owner._connection.send_message_to_server(
                    owner,
                    method,
                    validated_params,
                    {**api_zone.options(), "timeout": timeout},
                )
            # Since this api call is either internal, or has already been reported/traced once,
            # passing as internal.
            return owner._connection.send_message_to_server(
                owner, method, validated_params, {"internal": True, "timeout": timeout}
            )

        # Python: a channel call never raises at the call; the awaitable raises, as a
        # rejected promise does. A validation error is raised as it is, without the
        # API name in front of it (upstream adds it): the message names the Python
        # option, which is enough.
        try:
            result = owner._wrap_api_call(func, ApiCallOptions(internal=is_internal))
        except Exception as e:
            return failed(e)
        if mapper is None:
            return result
        return _mapped(result, mapper)

    # Python: the generated on<Event> and off<Event> methods register here. A handler
    # can be registered more than once, as on an EventEmitter; each off<Event> call
    # removes one registration.
    def _add_event_listener(
        self, event: str, handler: Any, listener: Callable[[Any], Any]
    ) -> None:
        self._event_listeners.setdefault((event, handler), []).append(listener)
        self.on(event, listener)

    def _remove_event_listener(self, event: str, handler: Any) -> None:
        listeners = self._event_listeners.get((event, handler))
        if not listeners:
            return
        listener = listeners.pop()
        if not listeners:
            del self._event_listeners[(event, handler)]
        self.remove_listener(event, listener)


class ChannelOwner(EventEmitter):
    _connection: "Connection"

    def __init__(
        self,
        parent: Any,
        type: str,
        guid: str,
        initializer: Any,
    ) -> None:
        connection: "Connection" = (
            parent._connection if isinstance(parent, ChannelOwner) else parent
        )
        super().__init__()
        self.set_max_listeners(0)
        self._connection = connection
        # Python: the generated API reads the event loop and the dispatcher fiber of
        # each object: the greenlet that runs the loop under the sync API, None under
        # the async API (playwright/sync_api/_context_manager.py).
        self._loop: asyncio.AbstractEventLoop = connection._loop
        self._dispatcher_fiber: Any = connection._dispatcher_fiber
        self._type = type
        self._guid = guid
        self._parent: Optional[ChannelOwner] = (
            parent if isinstance(parent, ChannelOwner) else None
        )
        self._objects: Dict[str, ChannelOwner] = {}
        self._instrumentation: "ClientInstrumentation" = (
            self._connection._instrumentation
        )
        self._event_to_subscription_mapping: Dict[str, str] = {}
        self._was_collected = False
        self._logger: Any = None

        self._connection._objects[guid] = self
        if self._parent:
            self._parent._objects[guid] = self
            self._logger = self._parent._logger

        self._channel: Any = self._create_channel()
        self._initializer = initializer

    def _report_unhandled_error(self, error: BaseException) -> None:
        self._connection._on_event_listener_error(error)

    def _set_event_to_subscription_mapping(self, mapping: Dict[str, str]) -> None:
        self._event_to_subscription_mapping = mapping

    def _update_subscription(self, event: str, enabled: bool) -> None:
        protocol_event = self._event_to_subscription_mapping.get(str(event))
        if protocol_event:
            # Python: .catch(() => {}).
            fire_and_forget(
                self._channel.updateSubscription(event=protocol_event, enabled=enabled)
            )

    def on(self, type: str, listener: Listener) -> "ChannelOwner":
        if not self.listener_count(type):
            self._update_subscription(type, True)
        super().on(type, listener)
        return self

    def add_listener(self, type: str, listener: Listener) -> "ChannelOwner":
        if not self.listener_count(type):
            self._update_subscription(type, True)
        super().add_listener(type, listener)
        return self

    def prepend_listener(self, type: str, listener: Listener) -> "ChannelOwner":
        if not self.listener_count(type):
            self._update_subscription(type, True)
        super().prepend_listener(type, listener)
        return self

    def off(self, type: str, listener: Listener) -> "ChannelOwner":
        super().off(type, listener)
        if not self.listener_count(type):
            self._update_subscription(type, False)
        return self

    def remove_listener(self, type: str, listener: Listener) -> "ChannelOwner":
        super().remove_listener(type, listener)
        if not self.listener_count(type):
            self._update_subscription(type, False)
        return self

    def _adopt(self, child: "ChannelOwner") -> None:
        assert child._parent
        child._parent._objects.pop(child._guid, None)
        self._objects[child._guid] = child
        child._parent = self

    def _parent_of_type(self, type: str) -> Optional["ChannelOwner"]:
        parent = self._parent
        while parent:
            if parent._type == type:
                return parent
            parent = parent._parent
        return None

    def _dispose(self, reason: Optional[str]) -> None:
        # Clean up from parent and connection.
        if self._parent:
            self._parent._objects.pop(self._guid, None)
        self._connection._objects.pop(self._guid, None)
        self._was_collected = reason == "gc"

        # Dispose all children.
        for object in list(self._objects.values()):
            object._dispose(reason)
        self._objects.clear()

    def _debug_scope_state(self) -> Any:
        return {
            "_guid": self._guid,
            "objects": [o._debug_scope_state() for o in self._objects.values()],
        }

    def _validator_to_wire_context(self) -> ValidatorContext:
        return ValidatorContext(
            t_channel_impl=t_channel_impl_to_wire,
            # Python: binary values are base64 strings on both sides.
            binary="buffer" if self._connection.raw_buffers() else "base64",
            is_under_test=is_under_test,
        )

    def _create_channel(self) -> Any:
        from playwright._impl.protocol_channels import CHANNEL_CLASSES

        channel_class = CHANNEL_CLASSES.get(self._type, Channel)
        return channel_class(self)

    def _wrap_api_call(
        self,
        func: Callable[[ApiZone], Awaitable[R]],
        options: Optional[ApiCallOptions] = None,
    ) -> Awaitable[R]:
        # Python: not an async def. A JS async function runs at once up to its first
        # await, so a channel call in func sends its message when _wrap_api_call()
        # is called; here func is called at once, too.
        logger = self._logger
        existing_api_zone: Optional[ApiZone] = current_zone().data("apiZone")
        if existing_api_zone:
            return func(existing_api_zone)

        stack_trace = capture_library_stack_trace()
        api_name = stack_trace["apiName"]
        if api_name.startswith("_") or "._" in api_name:
            api_name = (
                options.title if options and options.title is not None else api_name
            )
        api_zone = ApiZone(
            api_name=api_name,
            frames=stack_trace["frames"],
            title=options.title if options else None,
            internal=options.internal if options else False,
        )
        zone = current_zone().with_("apiZone", api_zone)
        # Python: func runs now, up to its first await. An error that it raises here
        # is raised as it is, without the API name and the logging below; upstream
        # has it as a rejected promise, which the catch below decorates.
        awaitable = zone.run(lambda: func(api_zone))

        async def finish() -> R:
            try:
                result = await zone.run_async(lambda: awaitable)
                if not (options and options.internal):
                    log_api_call(logger, f"<= {api_zone.api_name} succeeded")
                    self._instrumentation.on_api_call_end(api_zone)
                return result
            except asyncio.CancelledError:
                # Python: the task that awaits the call was cancelled, and the call
                # is aborted; upstream sees an AbortError.
                if not (options and options.internal):
                    log_api_call(logger, f"<= {api_zone.api_name} failed")
                    self._instrumentation.on_api_call_end(api_zone)
                raise
            except Exception as e:
                stack = getattr(e, "_stack", None)
                inner_error = (
                    "\n<inner error>\n" + stack
                    if (show_internal_stack_frames() or is_under_test()) and stack
                    else ""
                )
                # Python: a lambda is the anonymous function.
                if (
                    api_zone.api_name
                    and "<anonymous>" not in api_zone.api_name
                    and "<lambda>" not in api_zone.api_name
                ):
                    e = rewrite_error_message(e, api_zone.api_name + ": " + str(e))
                stack_frames = (
                    "\n" + "\n".join(stringify_stack_frames(stack_trace["frames"]))
                ) + inner_error
                if isinstance(e, Error):
                    e._stack = str(e) + stack_frames if stack_frames.strip() else ""
                if not (options and options.internal):
                    api_zone.error = e
                    log_api_call(logger, f"<= {api_zone.api_name} failed")
                    self._instrumentation.on_api_call_end(api_zone)
                raise e from None

        return finish()

    def __repr__(self) -> str:
        # Python: toJSON() keeps printers off the object graph; repr() does the same.
        return f"<{type(self).__name__} type={self._type} guid={self._guid}>"


async def _mapped(awaitable: Awaitable[Any], mapper: Callable[[Any], Any]) -> Any:
    # Python: the result of a channel call, mapped by the generated channel method.
    return mapper(await awaitable)


def api_call(
    title: Optional[str] = None,
) -> Callable[[Callable[..., Awaitable[R]]], Callable[..., Awaitable[R]]]:
    """Port of the @apiCall() decorator."""
    return _wrap_api_call_decorator(ApiCallOptions(title=title))


def internal(method: Callable[..., Awaitable[R]]) -> Callable[..., Awaitable[R]]:
    """Port of the @internal decorator."""
    return _wrap_api_call_decorator(ApiCallOptions(internal=True))(method)


def _wrap_api_call_decorator(
    options: ApiCallOptions,
) -> Callable[[Callable[..., Awaitable[R]]], Callable[..., Awaitable[R]]]:
    def decorator(method: Callable[..., Awaitable[R]]) -> Callable[..., Awaitable[R]]:
        # Python: the API name comes from the frame of the generated API that the
        # user code called, so the name of the wrapper does not matter.
        @functools.wraps(method)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Awaitable[R]:
            return self._wrap_api_call(
                lambda api_zone: method(self, *args, **kwargs), options
            )

        return wrapper

    return decorator


def log_api_call(logger: Any, message: str) -> None:
    # Python: there is no `logger` launch option, so logger is always None.
    if logger and logger.is_enabled("api", "info"):
        logger.log("api", "info", message, [], {"color": "cyan"})
    debug_logger.log("api", message)


def t_channel_impl_to_wire(
    names: Union[Literal["*"], List[str]],
    arg: Any,
    path: str,
    context: ValidatorContext,
) -> Any:
    object = getattr(arg, "_object", None)
    if isinstance(object, ChannelOwner) and (names == "*" or object._type in names):
        return {"guid": object._guid}
    raise ValidationError(
        f"{path}: expected channel {names if names == '*' else ','.join(names)}"
    )


def from_channel(channel: Any) -> Any:
    """`(channel as any)._object`: the object of a channel."""
    return channel._object


def from_nullable_channel(channel: Any) -> Any:
    return channel._object if channel else None
