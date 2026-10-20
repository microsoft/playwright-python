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

"""Port of packages/playwright-core/src/client/connection.ts.

Python: binary values stay base64 strings (the "base64" mode of the validator).
With PW_CHECK_PROTOCOL=1, each message that the client sends is also checked
against the protocol spec, for the tests.
"""

import asyncio
import json
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Union,
    cast,
)

from playwright._impl._errors import Error
from playwright._impl._protocol_check import check_message
from playwright._impl._protocol_check import is_enabled as is_protocol_check_enabled
from playwright._impl_v2.channel_owner import ChannelOwner
from playwright._impl_v2.client_instrumentation import (
    ClientInstrumentation,
    create_instrumentation,
)
from playwright._impl_v2.errors import PlaywrightError, TargetClosedError, parse_error
from playwright._impl_v2.event_emitter import EventEmitter
from playwright._impl_v2.isomorphic.trace_utils import create_call_id_generator
from playwright._impl_v2.protocol.validator import (
    ValidationError,
    ValidatorContext,
    find_validator,
    maybe_find_validator,
)
from playwright._impl_v2.timeout_settings import NO_TIMEOUT
from playwright._impl_v2.utils.debug import is_under_test
from playwright._impl_v2.utils.debug_logger import debug_logger
from playwright._impl_v2.utils.promise import ignore_unhandled, resolved
from playwright._impl_v2.utils.stack_trace import rewrite_error_message
from playwright._impl_v2.utils.zones import empty_zone

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl_v2.local_utils import LocalUtils
    from playwright._impl_v2.playwright import Playwright


class Root(ChannelOwner):
    def __init__(self, connection: "Connection") -> None:
        super().__init__(connection, "Root", "", {})

    async def initialize(self) -> "Playwright":
        from playwright._impl_v2.playwright import Playwright

        return Playwright.from_(
            (
                await self._channel.initialize(
                    # Python: the SDK language of this client.
                    sdkLanguage="python",
                    timeout=NO_TIMEOUT,
                )
            )["playwright"]
        )


class DummyChannelOwner(ChannelOwner):
    pass


ChannelOwnerFactory = Callable[[ChannelOwner, str, str, Any], ChannelOwner]


class _Callback:
    def __init__(
        self,
        future: "asyncio.Future[Any]",
        title: Optional[str],
        type: str,
        method: str,
    ) -> None:
        self.future = future
        self.title = title
        self.type = type
        self.method = method

    def resolve(self, value: Any) -> None:
        # Python: the future is cancelled when the call was aborted.
        if not self.future.done():
            self.future.set_result(value)

    def reject(self, error: BaseException) -> None:
        if not self.future.done():
            self.future.set_exception(error)


class Connection(EventEmitter):
    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        local_utils: Optional["LocalUtils"] = None,
        instrumentation: Optional[ClientInstrumentation] = None,
        headers: Optional[List[Dict[str, str]]] = None,
    ) -> None:
        super().__init__()
        # Python: the event loop that this connection and its objects run in.
        self._loop = loop
        self._objects: Dict[str, ChannelOwner] = {}
        self.onmessage: Callable[[Dict[str, Any]], None] = lambda message: None
        self._next_call_id = create_call_id_generator()
        self._callbacks: Dict[str, _Callback] = {}
        self._closed_error: Optional[Exception] = None
        self._is_remote = False
        self._raw_buffers = False
        # Some connections allow resolving in-process dispatchers.
        self.to_impl: Optional[Callable[[Any], Any]] = None
        self._tracing_count = 0
        # Python: PW_CHECK_PROTOCOL=1 checks each message against the protocol spec.
        self._check_protocol = is_protocol_check_enabled()
        self._object_factories: Dict[str, ChannelOwnerFactory] = {}
        self._instrumentation = instrumentation or create_instrumentation()
        self._local_utils = local_utils
        self._root_object = Root(self)
        # Used from @playwright/test fixtures -> TODO remove?
        self.headers = headers or []
        self.register_object_factories(_object_factories(self))

    def register_object_factories(
        self, factories: Dict[str, ChannelOwnerFactory]
    ) -> None:
        for type, factory in factories.items():
            self._object_factories[type] = factory

    def mark_as_remote(self) -> None:
        self._is_remote = True

    def is_remote(self) -> bool:
        return self._is_remote

    def use_raw_buffers(self) -> None:
        self._raw_buffers = True

    def raw_buffers(self) -> bool:
        return self._raw_buffers

    def local_utils(self) -> Optional["LocalUtils"]:
        return self._local_utils

    async def initialize_playwright(self) -> "Playwright":
        return await self._root_object.initialize()

    def get_object_with_known_name(self, guid: str) -> Any:
        return self._objects[guid]

    def set_is_tracing(self, is_tracing: bool) -> None:
        if is_tracing:
            self._tracing_count += 1
        else:
            self._tracing_count -= 1

    def send_message_to_server(
        self,
        object: ChannelOwner,
        method: str,
        params: Any,
        options: Dict[str, Any],
    ) -> "asyncio.Future[Any]":
        # Python: not an async def. The message goes out when this is called, and the
        # result is the future of the reply. A raise is the rejection of the promise.

        # Fire-and-forget: server intentionally never replies to __waitInfo__,
        # so silently drop it after the connection is closed or the object was collected.
        if method == "__waitInfo__" and (self._closed_error or object._was_collected):
            return resolved(None)
        if self._closed_error:
            raise self._closed_error
        if object._was_collected:
            raise Error(
                "The object has been collected to prevent unbounded heap growth."
            )

        # Python: there is no AbortSignal; see the cancellation below.

        guid = object._guid
        type = object._type
        id = options.get("call_id") or self._next_call_id()
        message = {"id": id, "guid": guid, "method": method, "params": params}
        if debug_logger.is_enabled("channel"):
            # Do not include metadata in debug logs to avoid noise.
            debug_logger.log("channel", "SEND> " + json.dumps(message))
        frames = options.get("frames")
        location = (
            {
                "file": frames[0]["file"],
                "line": frames[0]["line"],
                "column": frames[0]["column"],
            }
            if frames
            else None
        )
        metadata = _without_none(
            {
                "title": options.get("title"),
                "location": location,
                "internal": options.get("internal"),
                "timeout": options.get("timeout"),
            }
        )
        if self._tracing_count and frames is not None and type != "LocalUtils":
            if self._local_utils:
                ignore_unhandled(
                    self._local_utils.add_stack_to_tracing_no_reply(
                        {"callData": {"stack": frames or [], "id": id}}
                    )
                )
        if self._check_protocol:
            check_message(type, method, params, metadata, self._type_of_guid)
        # We need to exit zones before calling into the server, otherwise
        # when we receive events from the server, we would be in an API zone.
        empty_zone.run(lambda: self.onmessage({**message, "metadata": metadata}))
        # Fire-and-forget: server intentionally never replies to __waitInfo__.
        if method == "__waitInfo__":
            return resolved(None)
        future = self._loop.create_future()
        self._callbacks[id] = _Callback(future, options.get("title"), type, method)

        # Python: cancelling the task that awaits the call aborts it, as an aborted
        # signal does upstream.
        def on_done(f: "asyncio.Future[Any]") -> None:
            if f.cancelled() and id in self._callbacks and not self._closed_error:
                empty_zone.run(
                    lambda: self.onmessage(
                        {
                            "guid": guid,
                            "method": "__abort__",
                            "params": {"id": id, "reason": "The operation was aborted"},
                        }
                    )
                )

        future.add_done_callback(on_done)
        return future

    def _type_of_guid(self, guid: str) -> Optional[str]:
        # Python: for the protocol check.
        object = self._objects.get(guid)
        return object._type if object else None

    def dispatch(self, message: Dict[str, Any]) -> None:
        if self._closed_error:
            return

        id = message.get("id")
        guid = message.get("guid")
        method = message.get("method")
        params = message.get("params")
        result = message.get("result")
        error = message.get("error")
        error_details = message.get("errorDetails")
        log = message.get("log")
        if id:
            if debug_logger.is_enabled("channel"):
                debug_logger.log("channel", "<RECV " + json.dumps(message))
            callback = self._callbacks.get(id)
            if not callback:
                raise Error(f"Cannot find command to respond: {id}")
            del self._callbacks[id]
            if error and not result:
                parsed_error = parse_error(error)
                parsed_error._log = log or []
                parsed_error = cast(
                    PlaywrightError,
                    rewrite_error_message(
                        parsed_error, parsed_error.message + format_call_log(log)
                    ),
                )
                details_validator = maybe_find_validator(
                    callback.type, callback.method, "ErrorDetails"
                )
                if details_validator:
                    parsed_error._details = details_validator(
                        error_details or {}, "", self._validator_from_wire_context()
                    )
                callback.reject(parsed_error)
            else:
                validator = find_validator(callback.type, callback.method, "Result")
                callback.resolve(
                    validator(result, "", self._validator_from_wire_context())
                )
            return

        if debug_logger.is_enabled("channel"):
            debug_logger.log("channel", "<EVENT " + json.dumps(message))
        if method == "__create__":
            assert params is not None
            self._create_remote_object(
                guid, params["type"], params["guid"], params["initializer"]
            )
            return

        object = self._objects.get(guid or "")
        if not object:
            raise Error(f'Cannot find object to "{method}": {guid}')

        if method == "__adopt__":
            assert params is not None
            child = self._objects.get(params["guid"])
            if not child:
                raise Error(f"Unknown new child: {params['guid']}")
            object._adopt(child)
            return

        if method == "__dispose__":
            object._dispose((params or {}).get("reason"))
            return

        validator = find_validator(object._type, method or "", "Event")
        object._channel.emit(
            method, validator(params, "", self._validator_from_wire_context())
        )

    def close(self, cause: Optional[str] = None) -> None:
        if self._closed_error:
            return
        self._closed_error = TargetClosedError(cause)
        for callback in self._callbacks.values():
            callback.reject(self._closed_error)
        self._callbacks.clear()
        self.emit("close")

    def _validator_from_wire_context(self) -> ValidatorContext:
        return ValidatorContext(
            t_channel_impl=self._t_channel_impl_from_wire,
            # Python: binary values are base64 strings on both sides.
            binary="buffer" if self._raw_buffers else "base64",
            is_under_test=is_under_test,
        )

    def _t_channel_impl_from_wire(
        self,
        names: Union[Literal["*"], List[str]],
        arg: Any,
        path: str,
        context: ValidatorContext,
    ) -> Any:
        if arg and isinstance(arg, dict) and isinstance(arg.get("guid"), str):
            object = self._objects.get(arg["guid"])
            if not object:
                raise Error(
                    f"Object with guid {arg['guid']} was not bound in the connection"
                )
            if names != "*" and object._type not in names:
                raise ValidationError(f"{path}: expected channel {_names(names)}")
            return object._channel
        raise ValidationError(f"{path}: expected channel {_names(names)}")

    def _create_remote_object(
        self, parent_guid: Any, type: str, guid: str, initializer: Any
    ) -> Any:
        parent = self._objects.get(parent_guid)
        if not parent:
            raise Error(f"Cannot find parent object {parent_guid} to create {guid}")
        validator = find_validator(type, "", "Initializer")
        initializer = validator(initializer, "", self._validator_from_wire_context())
        factory = self._object_factories.get(type)
        if not factory:
            raise Error("Missing type " + type)
        return factory(parent, type, guid, initializer)


def _object_factories(connection: Connection) -> Dict[str, ChannelOwnerFactory]:
    # Python: imported here, as the modules of the objects import this one.
    from playwright._impl_v2.artifact import Artifact
    from playwright._impl_v2.browser import Browser
    from playwright._impl_v2.browser_context import BrowserContext
    from playwright._impl_v2.browser_type import BrowserType
    from playwright._impl_v2.cdp_session import CDPSession
    from playwright._impl_v2.debugger import Debugger
    from playwright._impl_v2.dialog import Dialog
    from playwright._impl_v2.disposable import DisposableObject
    from playwright._impl_v2.element_handle import ElementHandle
    from playwright._impl_v2.fetch import APIRequestContext
    from playwright._impl_v2.frame import Frame
    from playwright._impl_v2.js_handle import JSHandle
    from playwright._impl_v2.json_pipe import JsonPipe
    from playwright._impl_v2.local_utils import LocalUtils
    from playwright._impl_v2.network import (
        Request,
        Response,
        Route,
        WebSocket,
        WebSocketRoute,
    )
    from playwright._impl_v2.page import BindingCall, Page
    from playwright._impl_v2.playwright import Playwright
    from playwright._impl_v2.stream import Stream
    from playwright._impl_v2.tracing import Tracing
    from playwright._impl_v2.worker import Worker
    from playwright._impl_v2.writable_stream import WritableStream

    def local_utils(
        parent: ChannelOwner, type: str, guid: str, init: Any
    ) -> ChannelOwner:
        result = LocalUtils(parent, type, guid, init)
        if not connection._local_utils:
            connection._local_utils = result
        return result

    return {
        # Python: Android and Electron are JavaScript only; their objects are dummies.
        "Android": DummyChannelOwner,
        "AndroidDevice": DummyChannelOwner,
        "AndroidSocket": DummyChannelOwner,
        "APIRequestContext": APIRequestContext,
        "Artifact": Artifact,
        "BindingCall": BindingCall,
        "Browser": Browser,
        "BrowserContext": BrowserContext,
        "BrowserType": BrowserType,
        "CDPSession": CDPSession,
        "Debugger": Debugger,
        "Dialog": Dialog,
        "Disposable": DisposableObject,
        "Electron": DummyChannelOwner,
        "ElectronApplication": DummyChannelOwner,
        "ElementHandle": ElementHandle,
        "Frame": Frame,
        "JSHandle": JSHandle,
        "JsonPipe": JsonPipe,
        "LocalUtils": local_utils,
        "Page": Page,
        "Playwright": Playwright,
        "Request": Request,
        "Response": Response,
        "Route": Route,
        "Stream": Stream,
        "SocksSupport": DummyChannelOwner,
        "Tracing": Tracing,
        "WebSocket": WebSocket,
        "WebSocketRoute": WebSocketRoute,
        "Worker": Worker,
        "WritableStream": WritableStream,
    }


def format_call_log(log: Optional[List[str]]) -> str:
    if not log or not any(log):
        return ""
    # Python: no colors.dim().
    return "\nCall log:\n" + "\n".join(log) + "\n"


def _without_none(d: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


def _names(names: Union[Literal["*"], List[str]]) -> str:
    # Python: names.toString().
    return names if isinstance(names, str) else ",".join(names)
