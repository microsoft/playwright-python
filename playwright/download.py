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

from playwright.connection import ChannelOwner, ConnectionScope
from typing import Dict, Optional


class Download(ChannelOwner):
    def __init__(self, scope: ConnectionScope, guid: str, initializer: Dict) -> None:
        super().__init__(scope, guid, initializer)

    @property
    def url(self) -> str:
        return self._initializer["url"]

    @property
    def suggestedFilename(self) -> str:
        return self._initializer["suggestedFilename"]

    async def delete(self) -> None:
        await self._channel.send("delete")

    async def failure(self) -> Optional[str]:
        return await self._channel.send("failure")

    async def path(self) -> Optional[str]:
        return await self._channel.send("path")
