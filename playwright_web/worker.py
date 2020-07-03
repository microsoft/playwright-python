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
from playwright_web.js_handle import JSHandle, parseResult, serializeArgument
from typing import Any, Dict

class Worker(ChannelOwner):

  def __init__(self, scope: ConnectionScope, guid: str, initializer: Dict) -> None:
    super().__init__(scope, guid, initializer)

  @property
  def url(self) -> str:
    return self._initializer['url']

  async def evaluate(self, expression: str, is_function: bool, arg: Any) -> Any:
    return parseResult(await self._channel.send('evaluateExpression', dict(expression=expression, isFunction=is_function, arg=serializeArgument(arg))))

  async def evaluateHandle(self, expression: str, is_function: bool, arg: Any) -> JSHandle:
    return from_channel(await self._channel.send('evaluateExpressionHandle', dict(expression=expression, isFunction=is_function, arg=serializeArgument(arg))))
