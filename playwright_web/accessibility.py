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
from typing import Dict

class Accessibility:

  def __init__(self, channel: Channel) -> None:
    self._channel = channel

  async def snapshot(self, **options) -> Dict:
    root = options['root']._channel if 'root' in options else None
    return await self._channel.send('snapshot', dict(root=root, **options))
