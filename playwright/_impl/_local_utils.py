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

import base64
from typing import TYPE_CHECKING, Dict, List, Literal, Optional, Sequence, cast

from playwright._impl._connection import ChannelOwner, StackFrame
from playwright._impl._internal_structures import HeadersArray

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl import _protocol_types as channels
    from playwright._impl._protocol_channels import LocalUtilsChannel


class LocalUtils(ChannelOwner):
    _channel: "LocalUtilsChannel"

    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self.devices = {
            device["name"]: parse_device_descriptor(device["descriptor"])
            for device in initializer["deviceDescriptors"]
        }

    async def zip(
        self,
        zip_file: str,
        entries: Sequence["channels.NameValue"],
        stacks_id: Optional[str],
        mode: Literal["write", "append"],
        include_sources: bool,
        additional_sources: Optional[Sequence[str]],
    ) -> None:
        await self._channel.zip(
            zipFile=zip_file,
            entries=entries,
            stacksId=stacks_id,
            mode=mode,
            includeSources=include_sources,
            additionalSources=additional_sources,
        )

    async def har_open(self, file: str) -> "channels.LocalUtilsHarOpenResult":
        return await self._channel.harOpen(file=file)

    async def har_lookup(
        self,
        har_id: str,
        url: str,
        method: str,
        headers: HeadersArray,
        is_navigation_request: bool,
        post_data: Optional[bytes],
    ) -> "channels.LocalUtilsHarLookupResult":
        return await self._channel.harLookup(
            harId=har_id,
            url=url,
            method=method,
            headers=headers,
            postData=(
                base64.b64encode(post_data).decode() if post_data is not None else None
            ),
            isNavigationRequest=is_navigation_request,
        )

    async def har_close(self, har_id: str) -> None:
        await self._channel.harClose(harId=har_id)

    async def har_unzip(
        self, zip_file: str, har_file: str, resources_dir: Optional[str]
    ) -> None:
        await self._channel.harUnzip(
            zipFile=zip_file, harFile=har_file, resourcesDir=resources_dir
        )

    async def tracing_started(
        self, traces_dir: Optional[str], trace_name: str, live: bool
    ) -> "channels.LocalUtilsTracingStartedResult":
        return await self._channel.tracingStarted(
            tracesDir=traces_dir, traceName=trace_name, live=live
        )

    async def trace_discarded(self, stacks_id: str) -> None:
        await self._channel.traceDiscarded(stacksId=stacks_id)

    def add_stack_to_tracing_no_reply(self, id: str, frames: List[StackFrame]) -> None:
        call_data: channels.ClientSideCallMetadata = {
            # The client always sets "function" in its frames.
            "stack": cast("List[channels.StackFrame]", frames),
            "id": id,
        }
        self._channel.send_no_reply(
            "addStackToTracingNoReply", {"callData": call_data}, is_internal=True
        )


def parse_device_descriptor(dict: Dict) -> Dict:
    result = {
        "user_agent": dict["userAgent"],
        "viewport": dict["viewport"],
        "device_scale_factor": dict["deviceScaleFactor"],
        "is_mobile": dict["isMobile"],
        "has_touch": dict["hasTouch"],
        "default_browser_type": dict["defaultBrowserType"],
    }
    # "screen" is optional in the protocol.
    if dict.get("screen"):
        result["screen"] = dict["screen"]
    return result
