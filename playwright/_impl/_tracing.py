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

import pathlib
from typing import Dict, Optional, Union, cast

from playwright._impl._artifact import Artifact
from playwright._impl._connection import ChannelOwner, from_nullable_channel
from playwright._impl._helper import locals_to_params
from playwright._impl._local_utils import LocalUtils


class Tracing(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        _local_utils: LocalUtils

    async def start(
        self,
        name: str = None,
        title: str = None,
        snapshots: bool = None,
        screenshots: bool = None,
        sources: bool = None,
    ) -> None:
        params = locals_to_params(locals())
        await self._channel.send("tracingStart", params)
        await self.start_chunk(title)

    async def start_chunk(self, title: str = None) -> None:
        params = locals_to_params(locals())
        await self._channel.send("tracingStartChunk", params)

    async def stop_chunk(self, path: Union[pathlib.Path, str] = None) -> None:
        await self._do_stop_chunk(path)

    async def stop(self, path: Union[pathlib.Path, str] = None) -> None:
        await self._do_stop_chunk(path)
        await self._channel.send("tracingStop")

    async def _do_stop_chunk(self, file_path: Union[pathlib.Path, str] = None) -> None:
        is_local = not self._connection.is_remote

        mode = "doNotSave"
        if file_path:
            if is_local:
                mode = "compressTraceAndSources"
            else:
                mode = "compressTrace"

        result = await self._channel.send_return_as_dict(
            "tracingStopChunk",
            {
                "mode": mode,
            },
        )
        if not file_path:
            # Not interested in artifacts.
            return

        artifact = cast(
            Optional[Artifact],
            from_nullable_channel(result.get("artifact")),
        )

        if not artifact:
            # The artifact may be missing if the browser closed while stopping tracing.
            return

        # Save trace to the final local file.
        await artifact.save_as(file_path)
        await artifact.delete()

        # Add local sources to the remote trace if necessary.
        if result.get("sourceEntries", []):
            await self._local_utils.zip(file_path, result["sourceEntries"])
