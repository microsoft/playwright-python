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

"""Port of packages/playwright-core/src/client/cdpSession.ts.

Python: the 'event' payload has every field; an absent `params` is None. send()
takes no `signal`.
"""

from typing import TYPE_CHECKING, Any, Dict, Optional

from playwright._impl.channel_owner import ChannelOwner, from_channel
from playwright._impl.timeout_settings import NO_TIMEOUT

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl import protocol_types as channels
    from playwright._impl.protocol_channels import CDPSessionChannel


class CDPSession(ChannelOwner):
    _channel: "CDPSessionChannel"

    @staticmethod
    def from_(cdp_session: "CDPSessionChannel") -> "CDPSession":
        return from_channel(cdp_session)

    def __init__(
        self,
        parent: ChannelOwner,
        type: str,
        guid: str,
        initializer: Any,
    ) -> None:
        super().__init__(parent, type, guid, initializer)

        def on_event(event: "channels.CDPSessionEventEvent") -> None:
            self.emit(event["method"], event["params"])
            self.emit("event", event)

        self._channel.onEvent(on_event)

        self._channel.onClose(lambda: self.emit("close", self))

        # Not ported: `this.on = super.on` and the same for addListener, off,
        # removeListener and once. It gives the methods the types of api.CDPSession;
        # CDPSession inherits the same methods from ChannelOwner.

    async def send(
        self, method: str, params: Optional[Dict], timeout: Optional[float]
    ) -> Any:
        # Not ported: the `signal` option.
        result = await self._channel.send(
            method=method, params=params, timeout=timeout if timeout is not None else 0
        )
        return result["result"]

    async def detach(self) -> None:
        return await self._channel.detach(timeout=NO_TIMEOUT)
