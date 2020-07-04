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

from playwright_web.connection import Channel, ChannelOwner, ConnectionScope
from types import SimpleNamespace
from typing import Dict

class BrowserServer(ChannelOwner):

  Events = SimpleNamespace(
    Close='close',
  )

  def __init__(self, scope: ConnectionScope, guid: str, initializer: Dict) -> None:
    super().__init__(scope, guid, initializer)
    self._channel.on('close', lambda _: self.emit(BrowserServer.Events.Close))

  @property
  def pid(self) -> str:
    return self._initializer['pid']

  @property
  def wsEndpoint(self) -> str:
    return self._initializer['wsEndpoint']

  async def kill(self) -> None:
    await self._channel.send('kill')

  async def close(self) -> None:
    await self._channel.send('close')
