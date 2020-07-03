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

from playwright_web.connection import Channel
from typing import Awaitable, Dict

class Keyboard:
  def __init__(self, channel: Channel) -> None:
    self._channel = channel

  async def down(self, key: str) -> None:
    await self._channel.send('keyboardDown', { key })

  async def up(self, key: str) -> None:
    await self._channel.send('keyboardUp', { key })

  async def insertText(self, text: str) -> None:
    await self._channel.send('keyboardInsertText', dict(text=text))

  async def type(self, text: str, options: Dict = dict()) -> None:
    await self._channel.send('keyboardType', dict(text=text, options=options))

  async def press(self, key: str, options: Dict = dict()) -> None:
    await self._channel.send('keyboardPress', dict(key=key, options=options))

class Mouse:
  def __init__(self, channel: Channel) -> None:
    self._channel = channel

  async def move(self, x: float, y: float, options: Dict = dict()) -> None:
    await self._channel.send('mouseMove', dict(x=x, y=y, options=options))

  async def down(self, options: Dict = dict()) -> None:
    await self._channel.send('mouseDown', dict(options=options))

  async def up(self, options: Dict = dict()) -> None:
    await self._channel.send('mouseUp', dict(options=options))

  async def click(self, x: float, y: float, options: Dict = dict()) -> None:
    await self._channel.send('mouseClick', dict(x=x, y=y, options=options))

  async def dblclick(self, x: float, y: float, options: Dict = dict()) -> None:
    if not options:
      options = dict()
    await self.click(x, y, { **options, 'clickCount': 2 })
