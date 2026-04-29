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
from typing import Any, Dict

from playwright._impl._connection import ChannelOwner
from playwright._impl._helper import locals_to_params


class CDPSession(ChannelOwner):
    Events = SimpleNamespace(
        Event="event",
        Close="close",
    )

    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._channel.on("event", lambda params: self._on_event(params))
        self._channel.on("close", lambda _: self.emit(CDPSession.Events.Close, self))

    def _on_event(self, params: Any) -> None:
        self.emit(params["method"], params.get("params"))
        self.emit(CDPSession.Events.Event, params)

    async def send(self, method: str, params: Dict = None) -> Dict:
        return await self._channel.send("send", None, locals_to_params(locals()))

    async def detach(self) -> None:
        await self._channel.send(
            "detach",
            None,
        )
