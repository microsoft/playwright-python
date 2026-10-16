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
from typing import TYPE_CHECKING, Dict, Optional

from playwright._impl._connection import ChannelOwner

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl import _protocol_types as channels
    from playwright._impl._protocol_channels import CDPSessionChannel


class CDPSession(ChannelOwner):
    _channel: "CDPSessionChannel"

    Events = SimpleNamespace(
        Event="event",
        Close="close",
    )

    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._channel.onEvent(self._on_event)
        self._channel.onClose(lambda: self.emit(CDPSession.Events.Close, self))

    def _on_event(self, event: "channels.CDPSessionEventEvent") -> None:
        self.emit(event["method"], event["params"])
        self.emit(
            CDPSession.Events.Event,
            {key: value for key, value in event.items() if value is not None},
        )

    async def send(self, method: str, params: Optional[Dict]) -> Dict:
        return (await self._channel.send(method=method, params=params))["result"]

    async def detach(self) -> None:
        await self._channel.detach()
