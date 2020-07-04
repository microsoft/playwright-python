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
from playwright_web.browser import Browser
from playwright_web.browser_context import BrowserContext
from typing import Awaitable, Dict

class BrowserType(ChannelOwner):

  def __init__(self, scope: ConnectionScope, guid: str, initializer: Dict) -> None:
    super().__init__(scope, guid, initializer)

  @property
  def name(self) -> str:
    return self._initializer['name']

  @property
  def executablePath(self) -> str:
    return self._initializer['executablePath']

  async def launch(self, options: Dict = dict()) -> Browser:
    return from_channel(await self._channel.send('launch', dict(options=options)))

  async def launchServer(self, options: Dict = dict()) -> Browser:
    return from_channel(await self._channel.send('launchServer', dict(options=options)))

  async def launchPersistentContext(self, user_data_dir: str, options: Dict = dict()) -> BrowserContext:
    return from_channel(await self._channel.send('launchPersistentContext', dict(userDataDir=user_data_dir, options=options)))

  async def connect(self, options: Dict = dict()) -> Browser:
    return from_channel(await self._channel.send('connect', dict(options=options)))
