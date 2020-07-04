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
from playwright_web.connection import Channel, ChannelOwner, ConnectionScope, from_channel, from_nullable_channel
from playwright_web.element_handle import ElementHandle, convertSelectOptionValues, ValuesToSelect
from playwright_web.helper import ConsoleMessageLocation, FilePayload, SelectOption
from playwright_web.js_handle import JSHandle, parseResult, serializeArgument
from playwright_web.network import Request, Response, Route
from typing import Any, Awaitable, Dict, List, Optional, Union

class Frame(ChannelOwner):

  def __init__(self, scope: ConnectionScope, guid: str, initializer: Dict) -> None:
    super().__init__(scope, guid, initializer)
    self._parent_frame = from_nullable_channel(initializer['parentFrame'])
    if self._parent_frame:
      self._parent_frame._child_frames.append(self)
    self._name = initializer['name']
    self._url = initializer['url']
    self._detached = False
    self._child_frames: List[Frame] = list()
    self._page: Optional['Page']

  async def goto(self, url: str, options: Dict = dict()) -> Optional[Response]:
    return from_nullable_channel(await self._channel.send('goto', dict(url=url, options=options)))

  async def waitForNavigation(self, options: Dict = dict()) -> Optional[Response]:
    return from_nullable_channel(await self._channel.send('waitForNavigation', dict(options=options)))

  async def waitForLoadState(self, state: str = 'load', options: Dict = dict()) -> None:
    await self._channel.send('waitForLoadState', dict(state=state, options=options))

  async def frameElement(self) -> ElementHandle:
    return from_channel(await self._channel.send('frameElement'))

  async def evaluate(self, expression: str, is_function: bool = False, arg: Any = None) -> Any:
    return parseResult(await self._channel.send('evaluateExpression', dict(expression=expression, isFunction=is_function, arg=serializeArgument(arg))))

  async def evaluateHandle(self, expression: str, is_function: bool = False, arg: Any = None) -> JSHandle:
    return from_channel(await self._channel.send('evaluateExpression', dict(expression=expression, isFunction=is_function, arg=serializeArgument(arg))))

  async def querySelector(self, selector: str) -> Optional[ElementHandle]:
    return from_nullable_channel(await self._channel.send('querySelector', dict(selector=selector)))

  async def waitForSelector(self, selector: str, options: Dict = dict()) -> Optional[ElementHandle]:
    return from_nullable_channel(await self._channel.send('waitForSelector', dict(selector=selector, options=options)))

  async def dispatchEvent(self, selector: str, type: str, eventInit: Dict = None) -> None:
    await self._channel.send('dispatchEvent', dict(selector=selector, type=type, eventInit=eventInit))

  async def evalOnSelector(self, selector: str, expression: str, is_function: bool = False, arg: Any = None) -> Any:
    return parseResult(await self._channel.send('evalOnSelector', dict(selector=selector, expression=expression, isFunction=is_function, arg=serializeArgument(arg))))

  async def evalOnSelectorAll(self, selector: str, expression: str, is_function: bool = False, arg: Any = None) -> Any:
    return parseResult(await self._channel.send('evalOnSelectorAll', dict(selector=selector, expression=expression, isFunction=is_function, arg=serializeArgument(arg))))

  async def content(self) -> str:
    return await self._channel.send('content')

  async def setContent(self, html: str, options: Dict = dict()) -> None:
    await self._channel.send('setContent', dict(html=html, options=options))

  @property
  def name(self) -> str:
    return self._name or ''

  @property
  def url(self) -> str:
    return self._url or ''

  @property
  def parentFrame(self) -> Optional['Frame']:
    return self._parent_frame

  @property
  def childFrames(self) -> List['Frame']:
    return self._child_frames.copy()

  def isDetached(self) -> bool:
    return self._detached

  async def addScriptTag(self, options: Dict = dict()) -> ElementHandle:
    return from_channel(await self._channel.send('addScriptTag', dict(options=options)))

  async def addStyleTag(self, options: Dict = dict()) -> ElementHandle:
    return from_channel(await self._channel.send('addStyleTag', dict(options=options)))

  async def click(self, selector: str, options: Dict = dict()) -> None:
    await self._channel.send('click', dict(selector=selector, options=options))

  async def dblclick(self, selector: str, options: Dict = dict()) -> None:
    await self._channel.send('dblclick', dict(selector=selector, options=options))

  async def fill(self, selector: str, value: str, options: Dict = dict()) -> None:
    await self._channel.send('fill', dict(selector=selector, value=value, options=options))

  async def focus(self, selector: str, options: Dict = dict()) -> None:
    await self._channel.send('focus', dict(selector=selector, options=options))

  async def textContent(self, selector: str, options: Dict = dict()) -> str:
    return await self._channel.send('textContent', dict(selector=selector, options=options))

  async def innerText(self, selector: str, options: Dict = dict()) -> str:
    return await self._channel.send('innerText', dict(selector=selector, options=options))

  async def innerHTML(self, selector: str, options: Dict = dict()) -> str:
    return await self._channel.send('innerHTML', dict(selector=selector, options=options))

  async def getAttribute(self, selector: str, name: str, options: Dict = dict()) -> str:
    await self._channel.send('getAttribute', dict(selector=selector, name=name, options=options))

  async def hover(self, selector: str, options: Dict = dict()) -> None:
    await self._channel.send('hover', dict(selector=selector, options=options))

  async def selectOption(self, selector: str, values: ValuesToSelect, options: Dict = dict()) -> None:
    await self._channel.send('selectOption', dict(selector=selector, values=convertSelectOptionValues(values), options=options))

  async def setInputFiles(self, selector: str, files: Union[str, FilePayload, List[str], List[FilePayload]], options: Dict = dict()) -> None:
    await self._channel.send('setInputFiles', dict(selector=selector, files=files, options=options))

  async def type(self, selector: str, text: str, options: Dict = dict()) -> None:
    await self._channel.send('type', dict(selector=selector, text=text, options=options))

  async def press(self, selector: str, key: str, options: Dict = dict()) -> None:
    await self._channel.send('press', dict(selector=selector, key=key, options=options))

  async def check(self, selector: str, options: Dict = dict()) -> None:
    await self._channel.send('check', dict(selector=selector, options=options))

  async def uncheck(self, selector: str, options: Dict = dict()) -> None:
    await self._channel.send('uncheck', dict(selector=selector, options=options))

  async def waitForTimeout(self, timeout: int) -> Awaitable[None]:
    return self._scope._loop.create_task(asyncio.sleep(timeout / 1000))

  async def waitForFunction(self, expression: str, is_function: bool = False, arg: Any = None, options: Dict = dict()) -> JSHandle:
    return from_channel(await self._channel.send('waitForFunction', dict(expression=expression, isFunction=is_function, arg=serializeArgument(arg))))

  async def title(self) -> str:
    return await self._channel.send('title')
