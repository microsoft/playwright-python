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

import base64
from playwright_web.connection import Channel, ChannelOwner, ConnectionScope, from_nullable_channel
from playwright_web.helper import ConsoleMessageLocation, FilePayload, SelectOption
from playwright_web.js_handle import parse_result, serialize_argument, JSHandle
from typing import Any, Dict, List, Optional, Union

class ElementHandle(JSHandle):

  def __init__(self, scope: ConnectionScope, guid: str, initializer: Dict) -> None:
    super().__init__(scope, guid, initializer)

  def asElement(self) -> Optional['ElementHandle']:
    return self

  async def ownerFrame(self) -> Optional['Frame']:
    return from_nullable_channel(await self._channel.send('ownerFrame'))

  async def contentFrame(self) -> Optional['Frame']:
    return from_nullable_channel(await self._channel.send('contentFrame'))

  async def getAttribute(self, name: str) -> str:
    return await self._channel.send('getAttribute', dict(name=name))

  async def textContent(self) -> str:
    return await self._channel.send('textContent')

  async def innerText(self) -> str:
    return await self._channel.send('innerText')

  async def innerHTML(self) -> str:
    return await self._channel.send('innerHTML')

  async def dispatchEvent(self, type: str, eventInit: Dict = None) -> None:
    await self._channel.send('dispatchEvent', dict(type=type, eventInit=eventInit))

  async def scrollIntoViewIfNeeded(self, **options) -> None:
    await self._channel.send('scrollIntoViewIfNeeded', options)

  async def hover(self, **options) -> None:
    await self._channel.send('hover', options)

  async def click(self, **options) -> None:
    await self._channel.send('click', options)

  async def dblclick(self, **options) -> None:
    await self._channel.send('dblclick', options)

  async def selectOption(self, values: 'ValuesToSelect', **options) -> None:
    await self._channel.send('selectOption', dict(values=convertSelectOptionValues(values), **options))

  async def fill(self, value: str, **options) -> None:
    await self._channel.send('dblclick', dict(value=value, **options))

  async def selectText(self, **options) -> None:
    await self._channel.send('selectText', options)

  async def setInputFiles(self, files: Union[str, FilePayload, List[str], List[FilePayload]], **options) -> None:
    await self._channel.send('setInputFiles', dict(files=files, **options))

  async def focus(self) -> None:
    await self._channel.send('focus')

  async def type(self, text: str, **options) -> None:
    await self._channel.send('text', dict(text=text, **options))

  async def press(self, key: str, **options) -> None:
    await self._channel.send('press', dict(key=key, **options))

  async def check(self, **options) -> None:
    await self._channel.send('check', options)

  async def uncheck(self, **options) -> None:
    await self._channel.send('uncheck', options)

  async def boundingBox(self) -> Dict[str, float]:
    return await self._channel.send('boundingBox')

  async def screenshot(self, **options) -> bytes:
    binary = await self._channel.send('screenshot', options)
    return base64.b64decode(binary)

  async def querySelector(self, selector: str) -> Optional['ElementHandle']:
    return from_nullable_channel(await self._channel.send('querySelector', dict(selector=selector)))

  async def querySelectorAll(self, selector: str) -> List['ElementHandle']:
    return list(map(from_nullable_channel, await self._channel.send('querySelectorAll', dict(selector=selector))))

  async def evalOnSelector(self, selector: str, expression: str, arg: Any = None, force_expr: bool = False) -> Any:
    return parse_result(await self._channel.send('evalOnSelector', dict(selector=selector, expression=expression, isFunction=not(force_expr), arg=serialize_argument(arg))))

  async def evalOnSelectorAll(self, selector: str, expression: str, arg: Any = None, force_expr: bool = False) -> Any:
    return parse_result(await self._channel.send('evalOnSelectorAll', dict(selector=selector, expression=expression, isFunction=not(force_expr), arg=serialize_argument(arg))))


ValuesToSelect = Union[str, ElementHandle, SelectOption, List[str], List[ElementHandle], List[SelectOption], None]


def convertSelectOptionValues(arg: ValuesToSelect) -> Any:
  if isinstance(arg, ElementHandle):
    return arg._channel
  if isinstance(arg, list) and len(arg) and isinstance(arg[0], ElementHandle):
    return list(map(lambda e: e._channel, arg))
  return arg
