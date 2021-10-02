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
import inspect
import sys
import traceback
from pathlib import Path
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Optional, Union

from greenlet import greenlet
from pyee import AsyncIOEventEmitter

from playwright._impl._helper import ParsedMessagePayload, parse_error

if TYPE_CHECKING:
    from playwright._impl._playwright import Playwright


class Channel(AsyncIOEventEmitter):
    def __init__(self, connection: "Connection", guid: str) -> None:
        super().__init__()
        self._connection: Connection = connection
        self._guid = guid
        self._object: Optional[ChannelOwner] = None

    async def send(self, method: str, params: Dict = None) -> Any:
        return await self.inner_send(method, params, False)

    async def send_return_as_dict(self, method: str, params: Dict = None) -> Any:
        return await self.inner_send(method, params, True)

    async def inner_send(
        self, method: str, params: Optional[Dict], return_as_dict: bool
    ) -> Any:
        if params is None:
            params = {}
        callback = self._connection._send_message_to_server(self._guid, method, params)
        if self._connection._error:
            error = self._connection._error
            self._connection._error = None
            raise error
        result = await callback.future
        # Protocol now has named return values, assume result is one level deeper unless
        # there is explicit ambiguity.
        if not result:
            return None
        assert isinstance(result, dict)
        if return_as_dict:
            return result
        if len(result) == 0:
            return None
        assert len(result) == 1
        key = next(iter(result))
        return result[key]

    def send_no_reply(self, method: str, params: Dict = None) -> None:
        if params is None:
            params = {}
        self._connection._send_message_to_server(self._guid, method, params)


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
        self._guid = guid
        self._connection: Connection = (
            parent._connection if isinstance(parent, ChannelOwner) else parent
        )
        self._parent: Optional[ChannelOwner] = (
            parent if isinstance(parent, ChannelOwner) else None
        )
        self._objects: Dict[str, "ChannelOwner"] = {}
        self._channel = Channel(self._connection, guid)
        self._channel._object = self
        self._initializer = initializer

        self._connection._objects[guid] = self
        if self._parent:
            self._parent._objects[guid] = self

    def _dispose(self) -> None:
        # Clean up from parent and connection.
        if self._parent:
            del self._parent._objects[self._guid]
        del self._connection._objects[self._guid]

        # Dispose all children.
        for object in list(self._objects.values()):
            object._dispose()
        self._objects.clear()


class ProtocolCallback:
    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self.stack_trace: traceback.StackSummary = traceback.StackSummary()
        self.future = loop.create_future()


class RootChannelOwner(ChannelOwner):
    def __init__(self, connection: "Connection") -> None:
        super().__init__(connection, "Root", "", {})

    async def initialize(self) -> "Playwright":
        return from_channel(
            await self._channel.send(
                "initialize",
                {
                    "sdkLanguage": "python",
                },
            )
        )


class Connection:
    def __init__(
        self,
        dispatcher_fiber: Any,
        loop: asyncio.AbstractEventLoop,
        on_close: Callable[[], Awaitable[None]] = None,
    ) -> None:
        self._loop = loop
        self._dispatcher_fiber = dispatcher_fiber
        self._waiting_for_object: Dict[str, Callable[[ChannelOwner], None]] = {}
        self._last_id = 0
        self._objects: Dict[str, ChannelOwner] = {}
        self._callbacks: Dict[int, ProtocolCallback] = {}
        self._is_sync = False
        self._child_ws_connections: List["Connection"] = []
        self.playwright_future: asyncio.Future["Playwright"] = asyncio.Future()
        self.on_message: Callable[[Dict], Union[Awaitable[None], None]]
        self.on_close = on_close
        self._error: Optional[BaseException] = None

    async def run_as_sync(self) -> None:
        self._is_sync = True
        await self.run()

    async def run(self) -> None:
        self._root_object = RootChannelOwner(self)

        async def init() -> None:
            self.playwright_future.set_result(await self._root_object.initialize())

        asyncio.create_task(init())

    def call_on_object_with_known_name(
        self, guid: str, callback: Callable[[ChannelOwner], None]
    ) -> None:
        self._waiting_for_object[guid] = callback

    def _send_message_to_server(
        self, guid: str, method: str, params: Dict
    ) -> ProtocolCallback:
        self._last_id += 1
        id = self._last_id
        callback = ProtocolCallback(self._loop)
        task = asyncio.current_task(self._loop)
        callback.stack_trace = getattr(task, "__pw_stack_trace__", None)
        if not callback.stack_trace:
            callback.stack_trace = traceback.extract_stack()

        metadata = {"stack": serialize_call_stack(callback.stack_trace)}
        api_name = getattr(task, "__pw_api_name__", None)
        if api_name:
            metadata["apiName"] = api_name

        message = {
            "id": id,
            "guid": guid,
            "method": method,
            "params": self._replace_channels_with_guids(params),
            "metadata": metadata,
        }

        result = self.on_message(message)
        if result is not None and inspect.iscoroutine(result):
            task = asyncio.create_task(result)

            @task.add_done_callback
            def task_callback(task: asyncio.Task) -> None:
                exc = task.exception()
                if exc:
                    callback.future.set_exception(exc)

        self._callbacks[id] = callback
        return callback

    def dispatch(self, msg: ParsedMessagePayload) -> None:
        id = msg.get("id")
        if id:
            callback = self._callbacks.pop(id)
            if callback.future.cancelled():
                return
            error = msg.get("error")
            if error:
                parsed_error = parse_error(error["error"])  # type: ignore
                parsed_error.stack = "".join(
                    traceback.format_list(callback.stack_trace)[-10:]
                )
                callback.future.set_exception(parsed_error)
            else:
                result = self._replace_guids_with_channels(msg.get("result"))
                callback.future.set_result(result)
            return

        guid = msg["guid"]
        method = msg.get("method")
        params = msg.get("params")
        if method == "__create__":
            assert params
            parent = self._objects[guid]
            self._create_remote_object(
                parent, params["type"], params["guid"], params["initializer"]
            )
            return
        if method == "__dispose__":
            self._objects[guid]._dispose()
            return
        object = self._objects[guid]
        try:
            params = (
                params
                if object._type == "JsonPipe"
                else self._replace_guids_with_channels(params)
            )
            if self._is_sync:
                for listener in object._channel.listeners(method):
                    g = greenlet(listener)
                    g.switch(params)
            else:
                object._channel.emit(method, params)
        except BaseException as exc:
            print("Error occured in event listener", file=sys.stderr)
            traceback.print_exc()
            self._error = exc

    def _create_remote_object(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> ChannelOwner:
        from ._object_factory import create_remote_object

        initializer = self._replace_guids_with_channels(initializer)
        result = create_remote_object(parent, type, guid, initializer)
        if guid in self._waiting_for_object:
            self._waiting_for_object.pop(guid)(result)
        return result

    def _replace_channels_with_guids(self, payload: Any) -> Any:
        if payload is None:
            return payload
        if isinstance(payload, Path):
            return str(payload)
        if isinstance(payload, list):
            return list(map(lambda p: self._replace_channels_with_guids(p), payload))
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

    async def stop(self) -> None:
        if self.on_close:
            await self.on_close()


def from_channel(channel: Channel) -> Any:
    return channel._object


def from_nullable_channel(channel: Optional[Channel]) -> Optional[Any]:
    return channel._object if channel else None


def serialize_call_stack(stack_trace: traceback.StackSummary) -> List[Dict]:
    stack: List[Dict] = []
    for frame in stack_trace:
        if "_generated.py" in frame.filename:
            break
        stack.append(
            {"file": frame.filename, "line": frame.lineno, "function": frame.name}
        )
    stack.reverse()
    return stack
