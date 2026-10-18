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

import asyncio
import pathlib
from typing import (
    TYPE_CHECKING,
    Dict,
    List,
    Literal,
    Optional,
    Pattern,
    Sequence,
    Set,
    Union,
    cast,
)

from playwright._impl._api_structures import Location
from playwright._impl._artifact import Artifact
from playwright._impl._connection import (
    ChannelOwner,
    api_call,
    from_channel,
    from_nullable_channel,
    internal,
)
from playwright._impl._disposable import DisposableStub
from playwright._impl._errors import Error
from playwright._impl._str_utils import escape_regex_flags

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl import _protocol_types as channels
    from playwright._impl._page import Page
    from playwright._impl._protocol_channels import ArtifactChannel, TracingChannel


class Tracing(ChannelOwner):
    _channel: "TracingChannel"

    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._include_sources: bool = False
        self._additional_sources: Set[str] = set()
        self._is_live: bool = False
        self._stacks_id: Optional[str] = None
        self._is_tracing: bool = False
        self._traces_dir: Optional[str] = None
        self._har_id: Optional[str] = None
        # Maps the HAR id to the path of the HAR file.
        self._har_recorders: Dict[str, str] = {}

    @api_call
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
        await self._start_collecting_stacks(result["traceName"], self._is_live)
        return DisposableStub(lambda: self.stop(path=None), self)

    @api_call
    async def start_chunk(
        self, name: Optional[str], title: Optional[str]
    ) -> DisposableStub:
        result = await self._channel.tracingStartChunk(name=name, title=title)
        await self._start_collecting_stacks(result["traceName"], self._is_live)
        return DisposableStub(lambda: self.stop_chunk(path=None), self)

    async def group(self, name: str, location: Optional[Location]) -> DisposableStub:
        if location:
            self._additional_sources.add(location["file"])
        await self._channel.tracingGroup(
            name=name,
            location=cast(
                "Optional[channels.TracingTracingGroupParamsLocation]", location
            ),
        )
        return DisposableStub(lambda: self.group_end(), self)

    async def group_end(self) -> None:
        await self._channel.tracingGroupEnd()

    async def _start_collecting_stacks(self, trace_name: str, live: bool) -> None:
        if not self._is_tracing:
            self._is_tracing = True
            self._connection.set_is_tracing(True)
        result = await self._connection.local_utils.tracing_started(
            traces_dir=self._traces_dir, trace_name=trace_name, live=live
        )
        self._stacks_id = result["stacksId"]

    @api_call
    async def stop_chunk(self, path: Optional[Union[pathlib.Path, str]]) -> None:
        await self._do_stop_chunk(path)

    @api_call
    async def stop(self, path: Optional[Union[pathlib.Path, str]]) -> None:
        # Port of stop() in packages/playwright-core/src/client/tracing.ts: tracing stops
        # even when saving the chunk fails, so that it can start again.
        error: Optional[Exception] = None
        try:
            await self._do_stop_chunk(path)
        except Exception as e:
            error = e
        await self._channel.tracingStop()
        if error:
            raise error

    @api_call
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

    @api_call
    async def stop_har(self) -> None:
        har_id = self._har_id
        if not har_id:
            raise Error("HAR recording has not been started")
        self._har_id = None
        await self._export_har(har_id)

    async def _record_into_har(
        self,
        har: Union[pathlib.Path, str],
        page: Optional["Page"],
        url: Optional[Union[str, Pattern[str]]],
        update_content: Optional[Literal["attach", "embed", "omit"]],
        update_mode: Optional[Literal["full", "minimal"]],
    ) -> str:
        is_zip = str(har).endswith(".zip")
        options: channels.RecordHarOptions = {
            "content": update_content or "attach",
            "mode": update_mode or "minimal",
        }
        if isinstance(url, str):
            options["urlGlob"] = url
        if isinstance(url, Pattern):
            options["urlRegexSource"] = url.pattern
            options["urlRegexFlags"] = escape_regex_flags(url)
        if not is_zip:
            options["harPath"] = str(har)
        result = await self._channel.harStart(
            page=page._channel if page is not None else None, options=options
        )
        har_id = result["harId"]
        self._har_recorders[har_id] = str(har)
        return har_id

    async def _export_har(self, har_id: str) -> None:
        har_path = self._har_recorders.get(har_id)
        if not har_path:
            return
        del self._har_recorders[har_id]
        is_local = not self._connection.is_remote
        is_zip = har_path.endswith(".zip")

        if is_local:
            result = await self._channel.harExport(harId=har_id, mode="entries")
            if not is_zip:
                # Server wrote HAR and resources to the user's chosen paths.
                return
            await self._connection.local_utils.zip(
                zip_file=har_path,
                entries=cast("List[channels.NameValue]", result["entries"]),
                stacks_id=None,
                mode="write",
                include_sources=False,
                additional_sources=[],
            )
            return

        result = await self._channel.harExport(harId=har_id, mode="archive")
        artifact = cast(
            Artifact, from_channel(cast("ArtifactChannel", result["artifact"]))
        )
        if is_zip:
            await artifact.save_as(har_path)
            await artifact.delete()
            return
        await artifact.save_as(har_path + ".tmp")
        await self._connection.local_utils.har_unzip(
            zip_file=har_path + ".tmp", har_file=har_path, resources_dir=None
        )
        await artifact.delete()

    @internal
    async def _export_all_hars(self) -> None:
        await asyncio.gather(
            *[self._export_har(har_id) for har_id in self._har_recorders]
        )

    async def _do_stop_chunk(
        self, file_path: Optional[Union[pathlib.Path, str]]
    ) -> None:
        # Port of _doStopChunk() in packages/playwright-core/src/client/tracing.ts.
        self._reset_stack_counter()

        additional_sources = list(self._additional_sources)
        self._additional_sources.clear()
        stacks_id = self._stacks_id
        self._stacks_id = None

        try:
            await self._save_chunk(file_path, stacks_id, additional_sources)
        except Exception:
            # Release the stack session even on failure, otherwise later traces keep
            # appending to it.
            if stacks_id:
                try:
                    await self._connection.local_utils.trace_discarded(
                        stacks_id=stacks_id
                    )
                except Exception:
                    pass
            raise

    async def _save_chunk(
        self,
        file_path: Optional[Union[pathlib.Path, str]],
        stacks_id: Optional[str],
        additional_sources: Sequence[str],
    ) -> None:
        if not file_path:
            # Not interested in artifacts.
            await self._channel.tracingStopChunk(mode="discard")
            if stacks_id:
                await self._connection.local_utils.trace_discarded(stacks_id=stacks_id)
            return

        is_local = not self._connection.is_remote

        if is_local:
            result = await self._channel.tracingStopChunk(mode="entries")
            await self._connection.local_utils.zip(
                zip_file=str(file_path),
                entries=cast("List[channels.NameValue]", result["entries"]),
                stacks_id=stacks_id,
                mode="write",
                include_sources=self._include_sources,
                additional_sources=additional_sources,
            )
            return

        result = await self._channel.tracingStopChunk(mode="archive")

        artifact = cast(Optional[Artifact], from_nullable_channel(result["artifact"]))

        # The artifact may be missing if the browser closed while stopping tracing.
        if not artifact:
            if stacks_id:
                await self._connection.local_utils.trace_discarded(stacks_id=stacks_id)
            return

        # Save trace to the final local file.
        try:
            await artifact.save_as(file_path)
        except Exception:
            # Delete the artifact best-effort, the save error is the one to surface.
            try:
                await artifact.delete()
            except Exception:
                pass
            raise
        await artifact.delete()

        await self._connection.local_utils.zip(
            zip_file=str(file_path),
            entries=[],
            stacks_id=stacks_id,
            mode="append",
            include_sources=self._include_sources,
            additional_sources=additional_sources,
        )

    def _reset_stack_counter(self) -> None:
        if self._is_tracing:
            self._is_tracing = False
            self._connection.set_is_tracing(False)
