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
from playwright_web.helper import parse_error
from playwright_web.transport import Transport
from pyee import BaseEventEmitter
from types import SimpleNamespace
from typing import Any, Awaitable, Dict, List, Optional


class Channel(BaseEventEmitter):
  def __init__(self, scope: 'ConnectionScope', guid: str) -> None:
    super().__init__()
    self._scope = scope
    self._guid = guid
    self._object = None

  async def send(self, method: str, params: dict = None) -> Any:
    if params == None:
      params = dict()
    return await self._scope.send_message_to_server(self._guid, method, params)

  def _on_message(self, method: str, params: Dict):
    self.emit(method, params)


class ChannelOwner(BaseEventEmitter):
  def __init__(self, scope: 'ConnectionScope', guid: str, initializer: Dict, is_scope = False) -> None:
    super().__init__()
    self._guid = guid
    self._scope = scope.create_child(guid) if is_scope else scope
    self._channel = Channel(self._scope, guid)
    self._channel._object = self
    self._initializer = initializer


class ConnectionScope:
  def __init__(self, connection: 'Connection', guid: str, parent: Optional['ConnectionScope']) -> None:
    self._connection = connection
    self._loop = connection._loop
    self._guid = guid
    self._children: List['ConnectionScope'] = list()
    self._objects: Dict[str, ChannelOwner] = dict()
    self._parent = parent

  def create_child(self, guid: str) -> 'ConnectionScope':
    scope = self._connection.create_scope(guid, self)
    self._children.append(scope)
    return scope

  def dispose(self):
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

  async def send_message_to_server(self,guid: str, method: str, params: Dict) -> Any:
    return await self._connection._send_message_to_server(dict(guid=guid, method=method, params=params))

  def create_remote_object(self, type: str, guid: str, initializer: Dict) -> Any:
    result: ChannelOwner
    initializer = self._connection._replace_guids_with_channels(initializer)
    result = self._connection._object_factory(self, type, guid, initializer)
    self._connection._objects[guid] = result
    self._objects[guid] = result
    if guid in self._connection._waiting_for_object:
      self._connection._waiting_for_object.pop(guid).set_result(result)
    return result


class Connection:
  def __init__(self, input: asyncio.StreamReader, output: asyncio.StreamWriter, object_factory: Any, loop: asyncio.AbstractEventLoop) -> None:
    self._transport = Transport(input, output, loop)
    self._transport.on_message = lambda msg: self._dispatch(msg)
    self._waiting_for_object: Dict[str, Any] = dict()
    self._last_id = 0
    self._loop = loop
    self._objects: Dict[str, ChannelOwner] = dict()
    self._scopes: Dict[str, ConnectionScope] = dict()
    self._callbacks: Dict[int, asyncio.Future] = dict()
    self._root_scope = self.create_scope('', None)
    self._object_factory = object_factory

  async def wait_for_object_with_known_name(self, guid: str) -> Any:
    if guid in self._objects:
      return self._objects[guid]
    callback = self._loop.create_future()
    self._waiting_for_object[guid] = callback
    return await callback

  async def _send_message_to_server(self, message: Dict) -> Any:
    self._last_id += 1
    id = self._last_id
    converted = { **message, 'id': id }
    self._transport.send(converted)
    callback = self._loop.create_future()
    self._callbacks[id] = callback
    return await callback

  def _dispatch(self, msg: Dict):
    guid = msg.get('guid')

    if msg.get('id'):
      callback = self._callbacks.pop(msg.get('id'))
      if msg.get('error'):
        callback.set_exception(parse_error(msg.get('error')))
      else:
        result = self._replace_guids_with_channels(msg.get('result'))
        callback.set_result(result)
      return

    method = msg.get('method')
    params = msg.get('params')
    if method == '__create__':
      scope = self._scopes[guid]
      scope.create_remote_object(params['type'], params['guid'], params['initializer'])
      return

    object = self._objects[guid]
    object._channel.emit(method, self._replace_guids_with_channels(params))

  def _replace_channels_with_guids(self, payload: Any) -> Any:
    if payload == None:
      return payload
    if isinstance(payload, list):
      return list(map(lambda p: self._replace_channels_with_guids(p), payload))
    if isinstance(payload, ChannelOwner):
      return dict(guid=payload._object.guid)
    if isinstance(payload, dict):
      result = dict()
      for key in payload:
        result[key] = self._replace_channels_with_guids(payload[key])
      return result
    return payload

  def _replace_guids_with_channels(self, payload: Any) -> Any:
    if payload == None:
      return payload
    if isinstance(payload, list):
      return list(map(lambda p: self._replace_guids_with_channels(p), payload))
    if isinstance(payload, dict):
      if payload.get('guid') in self._objects:
        return self._objects[payload.get('guid')]._channel
      result = dict()
      for key in payload:
        result[key] = self._replace_guids_with_channels(payload[key])
      return result
    return payload

  def create_scope(self, guid: str, parent: Optional[ConnectionScope]) -> ConnectionScope:
    scope = ConnectionScope(self, guid, parent)
    self._scopes[guid] = scope
    return scope

def from_channel(channel: Channel) -> Any:
  return channel._object

def from_nullable_channel(channel: Optional[Channel]) -> Optional[Any]:
  return channel._object if channel else None
