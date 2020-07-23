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
import sys
import traceback
from typing import Any, Dict, List, Optional

from pyee import BaseEventEmitter

from playwright.helper import ParsedMessagePayload, parse_error
from playwright.transport import Transport


class Channel(BaseEventEmitter):
    def __init__(self, scope: "ConnectionScope", guid: str) -> None:
        super().__init__()
        self._scope: ConnectionScope = scope
        self._guid = guid
        self._object: Optional[ChannelOwner] = None

    async def send(self, method: str, params: dict = None) -> Any:
        if params is None:
            params = dict()
        result = await self._scope.send_message_to_server(self._guid, method, params)
        # Protocol now has named return values, assume result is one level deeper unless
        # there is explicit ambiguity.
        if isinstance(result, dict) and len(result) == 1:
            key = next(iter(result))
            return result[key]
        return result


class ChannelOwner(BaseEventEmitter):
    def __init__(
        self,
        scope: "ConnectionScope",
        guid: str,
        initializer: Dict,
        is_scope: bool = False,
    ) -> None:
        super().__init__()
        self._sync_owner: Any = None
        self._guid = guid
        self._scope = scope.create_child(guid) if is_scope else scope
        self._channel = Channel(self._scope, guid)
        self._channel._object = self
        self._initializer = initializer


class ConnectionScope:
    def __init__(
        self, connection: "Connection", guid: str, parent: Optional["ConnectionScope"]
    ) -> None:
        self._connection = connection
        self._loop = connection._loop
        self._guid = guid
        self._children: List["ConnectionScope"] = list()
        self._objects: Dict[str, ChannelOwner] = dict()
        self._parent = parent

    def create_child(self, guid: str) -> "ConnectionScope":
        scope = self._connection.create_scope(guid, self)
        self._children.append(scope)
        return scope

    def dispose(self) -> None:
        # Take care of hierarchy.
        for child in self._children:
            child.dispose()
        self._children.clear()

        # Delete self from scopes and objects.
        self._connection._scopes.pop(self._guid)
        self._connection._objects.pop(self._guid)

        # Delete all of the objects from connection.
        for guid in self._objects:
            self._connection._objects.pop(guid)

        # Clean up from parent.
        if self._parent:
            self._parent._objects.pop(self._guid)
            self._parent._children.remove(self)

    async def send_message_to_server(self, guid: str, method: str, params: Dict) -> Any:
        return await self._connection._send_message_to_server(guid, method, params)

    def create_remote_object(self, type: str, guid: str, initializer: Dict) -> Any:
        result: ChannelOwner
        initializer = self._connection._replace_guids_with_channels(initializer)
        result = self._connection._object_factory(self, type, guid, initializer)
        self._connection._objects[guid] = result
        self._objects[guid] = result
        if guid in self._connection._waiting_for_object:
            self._connection._waiting_for_object.pop(guid).set_result(result)
        return result


class ProtocolCallback:
    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self.stack_trace = "".join(traceback.format_stack()[-10:])
        self.future = loop.create_future()


class Connection:
    def __init__(
        self,
        input: asyncio.StreamReader,
        output: asyncio.StreamWriter,
        object_factory: Any,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self._transport = Transport(input, output, loop)
        self._transport.on_message = lambda msg: self._dispatch(msg)
        self._waiting_for_object: Dict[str, Any] = dict()
        self._last_id = 0
        self._loop = loop
        self._objects: Dict[str, ChannelOwner] = dict()
        self._scopes: Dict[str, ConnectionScope] = dict()
        self._callbacks: Dict[int, ProtocolCallback] = dict()
        self._root_scope = self.create_scope("", None)
        self._object_factory = object_factory

    async def wait_for_object_with_known_name(self, guid: str) -> Any:
        if guid in self._objects:
            return self._objects[guid]
        callback = self._loop.create_future()
        self._waiting_for_object[guid] = callback
        return await callback

    async def _send_message_to_server(
        self, guid: str, method: str, params: Dict
    ) -> Any:
        self._last_id += 1
        id = self._last_id
        message = dict(
            id=id,
            guid=guid,
            method=method,
            params=self._replace_channels_with_guids(params),
        )
        self._transport.send(message)
        callback = ProtocolCallback(self._loop)
        self._callbacks[id] = callback
        return await callback.future

    def _dispatch(self, msg: ParsedMessagePayload) -> None:

        id = msg.get("id")
        if id:
            callback = self._callbacks.pop(id)
            error = msg.get("error")
            if error:
                parsed_error = parse_error(error)
                parsed_error.stack = callback.stack_trace
                callback.future.set_exception(parsed_error)
            else:
                result = self._replace_guids_with_channels(msg.get("result"))
                callback.future.set_result(result)
            return

        guid = msg["guid"]
        method = msg.get("method")
        params = msg["params"]
        if method == "__create__":
            scope = self._scopes[guid]
            scope.create_remote_object(
                params["type"], params["guid"], params["initializer"]
            )
            return

        object = self._objects[guid]
        try:
            object._channel.emit(method, self._replace_guids_with_channels(params))
        except Exception:
            print(
                "Error dispatching the event",
                "".join(traceback.format_exception(*sys.exc_info())),
            )

    def _replace_channels_with_guids(self, payload: Any) -> Any:
        if payload is None:
            return payload
        if isinstance(payload, list):
            return list(map(lambda p: self._replace_channels_with_guids(p), payload))
        if isinstance(payload, Channel):
            return dict(guid=payload._guid)
        if isinstance(payload, dict):
            result = dict()
            for key in payload:
                result[key] = self._replace_channels_with_guids(payload[key])
            return result
        return payload

    def _replace_guids_with_channels(self, payload: Any) -> Any:
        if payload is None:
            return payload
        if isinstance(payload, list):
            return list(map(lambda p: self._replace_guids_with_channels(p), payload))
        if isinstance(payload, dict):
            if payload.get("guid") in self._objects:
                return self._objects[payload["guid"]]._channel
            result = dict()
            for key in payload:
                result[key] = self._replace_guids_with_channels(payload[key])
            return result
        return payload

    def create_scope(
        self, guid: str, parent: Optional[ConnectionScope]
    ) -> ConnectionScope:
        scope = ConnectionScope(self, guid, parent)
        self._scopes[guid] = scope
        return scope


def from_channel(channel: Channel) -> Any:
    return channel._object


def from_nullable_channel(channel: Optional[Channel]) -> Optional[Any]:
    return channel._object if channel else None
