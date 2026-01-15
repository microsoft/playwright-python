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

from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from playwright._impl._connection import ChannelOwner, from_channel
from playwright._impl._helper import locals_to_params


class PageAgent(ChannelOwner):
    Events = SimpleNamespace(
        Turn="turn",
    )

    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._channel.on(
            "turn", lambda params: self.emit(PageAgent.Events.Turn, params)
        )

    async def expect(
        self,
        expectation: str,
        cacheKey: str = None,
        maxTokens: int = None,
        maxTurns: int = None,
        timeout: float = None,
    ) -> None:
        await self._channel.send("expect", None, locals_to_params(locals()))

    async def perform(
        self,
        task: str,
        cacheKey: str = None,
        maxTokens: int = None,
        maxTurns: int = None,
        timeout: float = None,
    ) -> Dict[str, Any]:
        return await self._channel.send_return_as_dict(
            "perform", None, locals_to_params(locals())
        )

    async def extract(
        self,
        query: str,
        schema: Dict[str, Any],
        cacheKey: str = None,
        maxTokens: int = None,
        maxTurns: int = None,
        timeout: float = None,
    ) -> Dict[str, Any]:
        # TODO: implement pydantic
        return await self._channel.send_return_as_dict(
            "extract", None, locals_to_params(locals())
        )

    async def dispose(self) -> None:
        await self._channel.send("dispose", None)
