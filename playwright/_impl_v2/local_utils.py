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

"""Port of packages/playwright-core/src/client/localUtils.ts.

Python: the methods take the params object of the protocol command, as upstream
does, and spread it into the typed channel call.
"""

import asyncio
from typing import TYPE_CHECKING, Any, Dict

from playwright._impl_v2.channel_owner import ChannelOwner
from playwright._impl_v2.timeout_settings import NO_TIMEOUT

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl_v2 import protocol_types as channels
    from playwright._impl_v2.protocol_channels import LocalUtilsChannel

DeviceDescriptor = Dict[str, Any]
Devices = Dict[str, DeviceDescriptor]


class LocalUtils(ChannelOwner):
    _channel: "LocalUtilsChannel"

    def __init__(
        self,
        parent: ChannelOwner,
        type: str,
        guid: str,
        initializer: "channels.LocalUtilsInitializer",
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self.devices: Devices = {}
        for device in initializer["deviceDescriptors"]:
            self.devices[device["name"]] = dict(device["descriptor"])

    async def zip(self, params: Dict[str, Any]) -> None:
        return await self._channel.zip(
            zipFile=params["zipFile"],
            entries=params["entries"],
            stacksId=params.get("stacksId"),
            mode=params["mode"],
            includeSources=params["includeSources"],
            additionalSources=params.get("additionalSources"),
            timeout=NO_TIMEOUT,
        )

    async def har_open(
        self, params: Dict[str, Any]
    ) -> "channels.LocalUtilsHarOpenResult":
        return await self._channel.harOpen(file=params["file"], timeout=NO_TIMEOUT)

    async def har_lookup(
        self, params: Dict[str, Any]
    ) -> "channels.LocalUtilsHarLookupResult":
        return await self._channel.harLookup(
            harId=params["harId"],
            url=params["url"],
            method=params["method"],
            headers=params["headers"],
            postData=params.get("postData"),
            isNavigationRequest=params["isNavigationRequest"],
            timeout=NO_TIMEOUT,
        )

    async def har_close(self, params: Dict[str, Any]) -> None:
        return await self._channel.harClose(harId=params["harId"], timeout=NO_TIMEOUT)

    async def har_unzip(self, params: Dict[str, Any]) -> None:
        return await self._channel.harUnzip(
            zipFile=params["zipFile"],
            harFile=params["harFile"],
            resourcesDir=params.get("resourcesDir"),
            timeout=NO_TIMEOUT,
        )

    async def tracing_started(
        self, params: Dict[str, Any]
    ) -> "channels.LocalUtilsTracingStartedResult":
        return await self._channel.tracingStarted(
            tracesDir=params.get("tracesDir"),
            traceName=params["traceName"],
            live=params.get("live"),
            timeout=NO_TIMEOUT,
        )

    async def trace_discarded(self, params: Dict[str, Any]) -> None:
        return await self._channel.traceDiscarded(
            stacksId=params["stacksId"], timeout=NO_TIMEOUT
        )

    def add_stack_to_tracing_no_reply(
        self, params: Dict[str, Any]
    ) -> "asyncio.Future[None]":
        # Python: not an async def, so that the message goes out at once, as the
        # caller in connection.ts does not await it.
        return self._channel.addStackToTracingNoReply(
            callData=params["callData"], timeout=NO_TIMEOUT
        )
