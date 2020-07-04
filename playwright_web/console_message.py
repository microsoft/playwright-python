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
from playwright_web.helper import ConsoleMessageLocation
from playwright_web.js_handle import JSHandle
from typing import Dict, List

class ConsoleMessage(ChannelOwner):

  def __init__(self, scope: ConnectionScope, guid: str, initializer: Dict) -> None:
    super().__init__(scope, guid, initializer)

  @property
  def type(self) -> str:
    return self._initializer['type']

  @property
  def text(self) -> str:
    return self._initializer['text']

  @property
  def defaultValue(self) -> str:
    return self._initializer['defaultValue']

  @property
  def args(self) -> List[JSHandle]:
    return list(map(from_channel, self._initializer['args']))

  @property
  def location(self) -> ConsoleMessageLocation:
    return self._initializer['location']

  async def accept(self, prompt_text: str = None) -> None:
    await self._channel.send('accept', dict(promptText=prompt_text))

  async def dismiss(self) -> None:
    await self._channel.send('dismiss')
