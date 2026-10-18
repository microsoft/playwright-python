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
from typing import TYPE_CHECKING, Dict, Optional, cast

from playwright._impl._api_structures import DebuggerLocation, DebuggerPausedDetails
from playwright._impl._connection import ChannelOwner

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl import _protocol_types as channels
    from playwright._impl._protocol_channels import DebuggerChannel


class Debugger(ChannelOwner):
    _channel: "DebuggerChannel"

    Events = SimpleNamespace(
        PausedStateChanged="pausedstatechanged",
        ApiCallsUpdated="apicallsupdated",
    )

    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._paused_details: Optional[DebuggerPausedDetails] = None
        self._channel.onPausedStateChanged(self._on_paused_state_changed)
        self._channel.onApiCallsUpdated(
            lambda event: self.emit(Debugger.Events.ApiCallsUpdated, event["apiCalls"])
        )

    def _on_paused_state_changed(
        self, event: "channels.DebuggerPausedStateChangedEvent"
    ) -> None:
        self._paused_details = cast(
            Optional[DebuggerPausedDetails], event["pausedDetails"]
        )
        self.emit(Debugger.Events.PausedStateChanged)

    async def _enable(self) -> None:
        await self._channel.enable()

    async def request_pause(self) -> None:
        await self._channel.requestPause()

    async def resume(self) -> None:
        await self._channel.resume()

    async def next(self) -> None:
        await self._channel.next()

    async def run_to(self, location: DebuggerLocation) -> None:
        await self._channel.runTo(
            location=cast("channels.DebuggerRunToParamsLocation", location)
        )

    @property
    def paused_details(self) -> Optional[DebuggerPausedDetails]:
        return self._paused_details
