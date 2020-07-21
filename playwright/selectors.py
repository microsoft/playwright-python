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

from typing import Dict, Optional

from playwright.connection import ChannelOwner, ConnectionScope
from playwright.element_handle import ElementHandle


class Selectors(ChannelOwner):
    def __init__(self, scope: ConnectionScope, guid: str, initializer: Dict) -> None:
        super().__init__(scope, guid, initializer)

    async def register(
        self, name: str, source: str = "", path: str = None, contentScript: bool = False
    ) -> None:
        if path:
            with open(path, "r") as file:
                source = file.read()
        await self._channel.send(
            "register",
            dict(name=name, source=source, options={"contentScript": contentScript}),
        )

    async def _createSelector(self, name: str, handle: ElementHandle) -> Optional[str]:
        return await self._channel.send(
            "createSelector", dict(name=name, handle=handle._channel)
        )
