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

from playwright_web.connection import Channel, ChannelOwner, ConnectionScope, from_channel
from playwright_web.helper import ConsoleMessageLocation, Error
from typing import Any, Dict, List, Optional

class JSHandle(ChannelOwner):

  def __init__(self, scope: ConnectionScope, guid: str, initializer: Dict) -> None:
    super().__init__(scope, guid, initializer)
    self._preview = self._initializer['preview']
    self._channel.on('previewUpdated', lambda preview: self._on_preview_updated(preview))

  def _on_preview_updated(self, preview: str) -> None:
    self._preview = preview

  async def evaluate(self, expression: str, is_function: bool, arg: Any) -> Any:
    return parseResult(await self._channel.send('evaluateExpression', dict(expression=expression, isFunction=is_function, arg=serializeArgument(arg))))

  async def evaluateHandle(self, expression: str, is_function: bool, arg: Any) -> 'JSHandle':
    return from_channel(await self._channel.send('evaluateExpression', dict(expression=expression, isFunction=is_function, arg=serializeArgument(arg))))

  async def getProperty(self, name: str) -> 'JSHandle':
    return from_channel(await self._channel.send('getProperty', dict(name=name)))

  async def getProperties(self) -> Dict[str, 'JSHandle']:
    map = dict()
    for property in await self._channel.send('getPropertyList'):
      map[property['name']] = from_channel(property['value'])
    return map

  async def asElement(self) -> Optional['ElementHandle']:
    return None

  async def dispose(self) -> None:
    await self._channel.send('dismiss')

  async def jsonValue(self) -> Any:
    return parseResult(await self._channel.send('jsonValue'))

  def toString(self) -> str:
    return self._preview


def is_primitive_value(value: Any):
  return value == None or isinstance(value, bool) or isinstance(value, int) or isinstance(value, float) or isinstance(value, str)

def serializeValue(value: Any, handles: List[JSHandle], depth: int) -> Any:
  if isinstance(value, JSHandle):
    h = len(handles)
    handles.add(value)
    return dict(h=h)
  if depth > 100:
    raise Error('Maximum argument depth exceeded')
  if value == float('inf'):
    return dict(v='Infinity')
  if value == float('-inf'):
    return dict(v='-Infinity')
  if value == float('-0'):
    return dict(v='-0')
  if is_primitive_value(value):
    return value

  if isinstance(value, list):
    result = map(lambda a: serializeValue(a, handles, depth + 1), value)
    return dict(a=result)

  if isinstance(value, dict):
    result = dict()
    for name in value:
      result[name] = serializeValue(value[name], handles, depth + 1)
    return dict(o=result)
  return None

def serializeArgument(arg: Any) -> Any:
  guids = list()
  value = serializeValue(arg, guids, 0)
  return dict(value=value, guids=guids)

def parseValue(value: Any, handles: List[JSHandle]) -> Any:
  if value == None:
    return None
  if isinstance(value, dict):
    if 'v' in value:
      v = value['v']
      if v == 'Infinity':
        return float('inf')
      if v == '-Infinity':
        return float('-inf')
      if v == '-0':
        return float('-0')
      return None

    if 'a' in value:
      return map(lambda e: parseValue(e, handles), value['a'])

    if 'o' in value:
      o = value['o']
      result = dict()
      for name in o:
        result[name] = parseValue(o[name], handles)
      return result

    if 'h' in value:
      return handles[value['h']]
  return value

def parseResult(result: Any) -> Any:
  return parseValue(result['value'], result['handles'])
