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

"""Port of packages/playwright-core/src/client/debugger.ts.

Python: paused_details is a property, as the Python API reads it.
"""

from typing import TYPE_CHECKING, Any, Optional, cast

from playwright._impl._api_structures import DebuggerLocation
from playwright._impl_v2.channel_owner import ChannelOwner, from_channel
from playwright._impl_v2.events import Events
from playwright._impl_v2.timeout_settings import NO_TIMEOUT

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl_v2 import protocol_types as channels
    from playwright._impl_v2.protocol_channels import DebuggerChannel

    PausedDetails = channels.DebuggerPausedStateChangedEventPausedDetails


class Debugger(ChannelOwner):
    _channel: "DebuggerChannel"

    @staticmethod
    def from_(channel: "DebuggerChannel") -> "Debugger":
        return from_channel(channel)

    def __init__(
        self,
        parent: ChannelOwner,
        type: str,
        guid: str,
        initializer: Any,
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._paused_details: Optional["PausedDetails"] = None

        def on_paused_state_changed(
            event: "channels.DebuggerPausedStateChangedEvent",
        ) -> None:
            # Python: an absent field is None, as `pausedDetails ?? null`.
            self._paused_details = event["pausedDetails"]
            self.emit(Events.Debugger.PausedStateChanged)

        self._channel.onPausedStateChanged(on_paused_state_changed)
        self._channel.onApiCallsUpdated(
            lambda event: self.emit(Events.Debugger.ApiCallsUpdated, event["apiCalls"])
        )

    async def _enable(self) -> None:
        await self._channel.enable(timeout=NO_TIMEOUT)

    async def request_pause(self) -> None:
        await self._channel.requestPause(timeout=NO_TIMEOUT)

    async def resume(self) -> None:
        await self._channel.resume(timeout=NO_TIMEOUT)

    async def next(self) -> None:
        await self._channel.next(timeout=NO_TIMEOUT)

    async def run_to(self, location: DebuggerLocation) -> None:
        # Python: the cast is for mypy; the API and protocol dicts have the same keys.
        await self._channel.runTo(location=cast(Any, location), timeout=NO_TIMEOUT)

    @property
    def paused_details(self) -> Optional["PausedDetails"]:
        # Python: a property, as the Python API reads it.
        return self._paused_details
