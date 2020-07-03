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

from playwright_web.browser_context import BrowserContext
from playwright_web.connection import Channel, ChannelOwner, ConnectionScope, from_channel
from playwright_web.page import Page
from types import SimpleNamespace
from typing import Dict, List, Optional

class Browser(ChannelOwner):

  Events = SimpleNamespace(
    Disconnected='disconnected',
  )

  def __init__(self, scope: ConnectionScope, guid: str, initializer: Dict) -> None:
    super().__init__(scope, guid, initializer, True)
    self._is_connected = True
    self._is_closed_or_closing = False

    self._contexts: List[BrowserContext] = list()
    self._channel.on('close', lambda _: self._on_close())
    self._channel.on('contextClosed', lambda context: self._contexts.remove(context))

  def _on_close(self) -> None:
    self._is_connected = False
    self.emit(Browser.Events.Disconnected)
    self._is_closed_or_closing = True
    self._scope.dispose()

  @property
  def contexts(self) -> List[BrowserContext]:
    return self._contexts.copy()

  def isConnected(self) -> bool:
    return self._is_connected

  async def newContext(self, options: Dict = dict()) -> BrowserContext:
    channel = await self._channel.send('newContext', dict(options=options))
    context = from_channel(channel)
    self._contexts.append(context)
    context._browser = self
    return context

  async def newPage(self, options: Dict = dict()) -> Page:
    context = await self.newContext(options)
    page = await context.newPage()
    page._owned_context = context
    context._owner_page = page
    return page

  async def close(self) -> None:
    if self._is_closed_or_closing:
      return
    self._is_closed_or_closing = True
    await self._channel.send('close')
