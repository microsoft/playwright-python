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
from typing import TYPE_CHECKING, Dict, Literal, Optional, Pattern, Union, cast

from playwright._impl._api_structures import Location
from playwright._impl._artifact import Artifact
from playwright._impl._connection import (
    ChannelOwner,
    from_channel,
    from_nullable_channel,
)
from playwright._impl._disposable import DisposableStub
from playwright._impl._errors import Error

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl import _protocol_types as channels
    from playwright._impl._page import Page
    from playwright._impl._protocol_channels import TracingChannel


class Tracing(ChannelOwner):
    _channel: "TracingChannel"

    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._include_sources: bool = False
        self._is_live: bool = False
        self._stacks_id: Optional[str] = None
        self._is_tracing: bool = False
        self._traces_dir: Optional[str] = None
        self._har_id: Optional[str] = None
        self._har_recorders: Dict[str, Dict[str, str]] = {}

    async def start(
        self,
        name: Optional[str],
        title: Optional[str],
        snapshots: Optional[bool],
        aria_snapshots: Optional[bool],
        screen_snapshots: Optional[bool],
        screenshots: Optional[bool],
        sources: Optional[bool],
        live: Optional[bool],
    ) -> DisposableStub:
        self._include_sources = bool(sources)
        self._is_live = bool(live)

        await self._channel.tracingStart(
            name=name,
            snapshotDom=snapshots,
            snapshotAria=aria_snapshots,
            snapshotScreen=screen_snapshots,
            screencast=screenshots,
            coverage=None,
            live=live,
        )
        result = await self._channel.tracingStartChunk(name=name, title=title)
        await self._start_collecting_stacks(result["traceName"])
        return DisposableStub(lambda: self.stop(path=None), self)

    async def start_chunk(
        self, name: Optional[str], title: Optional[str]
    ) -> DisposableStub:
        result = await self._channel.tracingStartChunk(name=name, title=title)
        await self._start_collecting_stacks(result["traceName"])
        return DisposableStub(lambda: self.stop_chunk(path=None), self)

    async def _start_collecting_stacks(self, trace_name: str) -> None:
        if not self._is_tracing:
            self._is_tracing = True
            self._connection.set_is_tracing(True)
        self._stacks_id = await self._connection.local_utils.tracing_started(
            traces_dir=self._traces_dir, trace_name=trace_name, live=self._is_live
        )

    async def stop_chunk(self, path: Optional[Union[pathlib.Path, str]]) -> None:
        await self._do_stop_chunk(path)

    async def stop(self, path: Optional[Union[pathlib.Path, str]]) -> None:
        await self._do_stop_chunk(path)
        await self._channel.tracingStop()

    async def _do_stop_chunk(
        self, file_path: Optional[Union[pathlib.Path, str]]
    ) -> None:
        self._reset_stack_counter()

        if not file_path:
            # Not interested in any artifacts
            await self._channel.tracingStopChunk(mode="discard")
            if self._stacks_id:
                await self._connection.local_utils.trace_discarded(
                    stacks_id=self._stacks_id
                )
            return

        is_local = not self._connection.is_remote

        if is_local:
            result = await self._channel.tracingStopChunk(mode="entries")
            assert result["entries"] is not None
            await self._connection.local_utils.zip(
                zip_file=str(file_path),
                entries=result["entries"],
                stacks_id=self._stacks_id,
                mode="write",
                include_sources=self._include_sources,
                additional_sources=None,
            )
            return

        result = await self._channel.tracingStopChunk(mode="archive")

        artifact = cast(Optional[Artifact], from_nullable_channel(result["artifact"]))

        # The artifact may be missing if the browser closed while stopping tracing.
        if not artifact:
            if self._stacks_id:
                await self._connection.local_utils.trace_discarded(
                    stacks_id=self._stacks_id
                )
            return

        # Save trace to the final local file.
        await artifact.save_as(file_path)
        await artifact.delete()

        await self._connection.local_utils.zip(
            zip_file=str(file_path),
            entries=[],
            stacks_id=self._stacks_id,
            mode="append",
            include_sources=self._include_sources,
            additional_sources=None,
        )

    def _reset_stack_counter(self) -> None:
        if self._is_tracing:
            self._is_tracing = False
            self._connection.set_is_tracing(False)

    async def group(self, name: str, location: Optional[Location]) -> DisposableStub:
        await self._channel.tracingGroup(
            name=name,
            location=cast(
                "Optional[channels.TracingTracingGroupParamsLocation]", location
            ),
        )
        return DisposableStub(lambda: self.group_end(), self)

    async def group_end(self) -> None:
        await self._channel.tracingGroupEnd()

    async def start_har(
        self,
        path: Union[pathlib.Path, str],
        content: Optional[Literal["attach", "embed", "omit"]],
        mode: Optional[Literal["full", "minimal"]],
        url_filter: Optional[Union[str, Pattern[str]]],
    ) -> DisposableStub:
        if self._har_id:
            raise Error("HAR recording has already been started")
        is_zip = str(path).endswith(".zip")
        default_content: Literal["attach", "embed", "omit"] = (
            "attach" if is_zip else "embed"
        )
        self._har_id = await self._record_into_har(
            har=path,
            page=None,
            url=url_filter,
            update_content=content or default_content,
            update_mode=mode or "full",
        )
        return DisposableStub(lambda: self.stop_har(), self)

    async def _record_into_har(
        self,
        har: Union[pathlib.Path, str],
        page: Optional["Page"],
        url: Union[str, Pattern[str]] = None,
        update_content: Literal["attach", "embed", "omit"] = None,
        update_mode: Literal["full", "minimal"] = None,
        resourcesDir: Optional[str] = None,
    ) -> str:
        is_zip = str(har).endswith(".zip")
        options: channels.RecordHarOptions = {
            "content": update_content or "attach",
            "mode": update_mode or "minimal",
        }
        if not is_zip:
            options["harPath"] = str(har)
        if isinstance(url, str):
            options["urlGlob"] = url
        elif url is not None:
            options["urlRegexSource"] = url.pattern
            options["urlRegexFlags"] = "".join(
                flag
                for flag, mask in (("i", 2), ("m", 8), ("s", 16))
                if url.flags & mask
            )
        if resourcesDir is not None:
            options["resourcesDir"] = resourcesDir
        result = await self._channel.harStart(
            page=page._channel if page is not None else None, options=options
        )
        har_id = result["harId"]
        self._har_recorders[har_id] = {"path": str(har)}
        return har_id

    async def _export_all_hars(self) -> None:
        for har_id in list(self._har_recorders.keys()):
            await self._export_har(har_id)
        self._har_id = None

    async def stop_har(self) -> None:
        har_id = self._har_id
        if not har_id:
            return
        self._har_id = None
        await self._export_har(har_id)

    async def _export_har(self, har_id: str) -> None:
        recorder = self._har_recorders.pop(har_id, None)
        if not recorder:
            return
        is_local = not self._connection.is_remote
        is_zip = recorder["path"].endswith(".zip")

        if is_local:
            result = await self._channel.harExport(harId=har_id, mode="entries")
            if not is_zip:
                # Server wrote HAR and resources to the user's chosen paths.
                return
            assert result["entries"] is not None
            await self._connection.local_utils.zip(
                zip_file=recorder["path"],
                entries=result["entries"],
                stacks_id=None,
                mode="write",
                include_sources=False,
                additional_sources=None,
            )
            return

        result = await self._channel.harExport(harId=har_id, mode="archive")
        assert result["artifact"]
        artifact = cast(Artifact, from_channel(result["artifact"]))
        if is_zip:
            await artifact.save_as(recorder["path"])
            await artifact.delete()
            return
        # Uncompressed har is not supported in thin clients
        await artifact.save_as(recorder["path"] + ".tmp")
        await artifact.delete()
