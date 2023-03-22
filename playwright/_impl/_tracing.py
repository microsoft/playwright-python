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
from typing import Any, Dict, List, Optional, Union, cast

from playwright._impl._artifact import Artifact
from playwright._impl._connection import ChannelOwner, from_nullable_channel, filter_none
from playwright._impl._helper import locals_to_params


class Tracing(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._include_sources: bool = False
        self._metadata_collector: List[Dict[str, Any]] = []

    async def start(
        self,
        name: str = None,
        title: str = None,
        snapshots: bool = None,
        screenshots: bool = None,
        sources: bool = None,
    ) -> None:
        params = locals_to_params(locals())
        self._include_sources = bool(sources)
        await self._channel.send("tracingStart", params)
        await self._channel.send(
            "tracingStartChunk", filter_none({"title": title, "name": name})
        )
        self._metadata_collector = []
        self._connection.start_collecting_call_metadata(self._metadata_collector)

    async def start_chunk(self, title: str = None, name: str = None) -> None:
        params = locals_to_params(locals())
        await self._channel.send("tracingStartChunk", params)
        self._metadata_collector = []
        self._connection.start_collecting_call_metadata(self._metadata_collector)

    async def stop_chunk(self, path: Union[pathlib.Path, str] = None) -> None:
        await self._do_stop_chunk(path)

    async def stop(self, path: Union[pathlib.Path, str] = None) -> None:
        await self._do_stop_chunk(path)
        await self._channel.send("tracingStop")

    async def _do_stop_chunk(self, file_path: Union[pathlib.Path, str] = None) -> None:
        if self._metadata_collector:
            self._connection.stop_collecting_call_metadata(self._metadata_collector)
        metadata = self._metadata_collector
        self._metadata_collector = []

        if not file_path:
            await self._channel.send("tracingStopChunk", {"mode": "discard"})
            # Not interested in any artifacts
            return

        is_local = not self._connection.is_remote

        if is_local:
            result = await self._channel.send_return_as_dict(
                "tracingStopChunk", {"mode": "entries"}
            )
            await self._connection.local_utils.zip(
                {
                    "zipFile": str(file_path),
                    "entries": result["entries"],
                    "metadata": metadata,
                    "mode": "write",
                    "includeSources": self._include_sources,
                }
            )
            return

        result = await self._channel.send_return_as_dict(
            "tracingStopChunk",
            {
                "mode": "archive",
            },
        )

        artifact = cast(
            Optional[Artifact],
            from_nullable_channel(result.get("artifact")),
        )

        # The artifact may be missing if the browser closed while stopping tracing.
        if not artifact:
            return

        # Save trace to the final local file.
        await artifact.save_as(file_path)
        await artifact.delete()

        # Add local sources to the remote trace if necessary.
        if len(metadata) > 0:
            await self._connection.local_utils.zip(
                {
                    "zipFile": str(file_path),
                    "entries": [],
                    "metadata": metadata,
                    "mode": "append",
                    "includeSources": self._include_sources,
                }
            )
