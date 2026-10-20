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

"""Port of packages/playwright-core/src/client/tracing.ts.

Python: the snapshots option of start() is three options, snapshots (dom),
aria_snapshots and screen_snapshots, as the object form is not in the Python API.
The _coverage option of start() and the resourcesDir option of start_har() are
JavaScript only. A path can be a pathlib.Path, and a regular expression is a
re.Pattern, whose flags are sent in the JS letters.
"""

import asyncio
import re
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Literal,
    Optional,
    Pattern,
    Sequence,
    Set,
    TypedDict,
    Union,
    cast,
)

from playwright._impl._api_structures import Location
from playwright._impl._errors import Error
from playwright._impl_v2.artifact import Artifact
from playwright._impl_v2.channel_owner import (
    ChannelOwner,
    api_call,
    from_channel,
    internal,
)
from playwright._impl_v2.disposable import DisposableStub
from playwright._impl_v2.isomorphic.string_utils import escape_regex_flags
from playwright._impl_v2.timeout_settings import NO_TIMEOUT

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl_v2 import protocol_types as channels
    from playwright._impl_v2.local_utils import LocalUtils
    from playwright._impl_v2.page import Page
    from playwright._impl_v2.protocol_channels import ArtifactChannel, TracingChannel


class _HarRecorder(TypedDict):
    # Python: the { path, resourcesDir } object of _harRecorders, without the
    # resourcesDir option, which is JavaScript only.
    path: str


class Tracing(ChannelOwner):
    _channel: "TracingChannel"

    @staticmethod
    def from_(channel: "TracingChannel") -> "Tracing":
        return from_channel(channel)

    def __init__(
        self,
        parent: ChannelOwner,
        type: str,
        guid: str,
        initializer: Any,
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._include_sources = False
        self._additional_sources: Set[str] = set()
        self._is_live = False
        self._traces_dir: Optional[str] = None
        self._stacks_id: Optional[str] = None
        self._is_tracing = False
        self._har_id: Optional[str] = None
        self._har_recorders: Dict[str, _HarRecorder] = {}

    @api_call()
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
        # Python: the { dom, aria, screen } object is the options snapshots,
        # aria_snapshots and screen_snapshots.
        await self._channel.tracingStart(
            name=name,
            snapshotDom=snapshots,
            snapshotAria=aria_snapshots,
            snapshotScreen=screen_snapshots,
            screencast=screenshots,
            # Python: the _coverage option is JavaScript only.
            coverage=None,
            live=live,
            timeout=NO_TIMEOUT,
        )
        trace_name = (
            await self._channel.tracingStartChunk(
                name=name, title=title, timeout=NO_TIMEOUT
            )
        )["traceName"]
        await self._start_collecting_stacks(trace_name, self._is_live)
        return DisposableStub(lambda: self.stop(path=None))

    @api_call()
    async def start_chunk(
        self, name: Optional[str], title: Optional[str]
    ) -> DisposableStub:
        trace_name = (
            await self._channel.tracingStartChunk(
                name=name, title=title, timeout=NO_TIMEOUT
            )
        )["traceName"]
        await self._start_collecting_stacks(trace_name, self._is_live)
        return DisposableStub(lambda: self.stop_chunk(path=None))

    async def group(self, name: str, location: Optional[Location]) -> DisposableStub:
        if location:
            self._additional_sources.add(location["file"])
        await self._channel.tracingGroup(
            name=name,
            location=cast(
                "Optional[channels.TracingTracingGroupParamsLocation]", location
            ),
            timeout=NO_TIMEOUT,
        )
        return DisposableStub(lambda: self.group_end())

    async def group_end(self) -> None:
        await self._channel.tracingGroupEnd(timeout=NO_TIMEOUT)

    async def _start_collecting_stacks(self, trace_name: str, live: bool) -> None:
        if not self._is_tracing:
            self._is_tracing = True
            self._connection.set_is_tracing(True)
        local_utils = self._connection.local_utils()
        result = (
            await local_utils.tracing_started(
                {"tracesDir": self._traces_dir, "traceName": trace_name, "live": live}
            )
            if local_utils
            else None
        )
        self._stacks_id = result["stacksId"] if result else None

    @api_call()
    async def stop_chunk(self, path: Optional[Union[str, Path]]) -> None:
        await self._do_stop_chunk(path)

    @api_call()
    async def stop(self, path: Optional[Union[str, Path]]) -> None:
        try:
            await self._do_stop_chunk(path)
            error: Optional[Exception] = None
        except Exception as e:
            error = e
        await self._channel.tracingStop(timeout=NO_TIMEOUT)
        if error:
            raise error

    @api_call()
    async def start_har(
        self,
        path: Union[str, Path],
        content: Optional[Literal["attach", "embed", "omit"]],
        mode: Optional[Literal["full", "minimal"]],
        url_filter: Optional[Union[str, Pattern[str]]],
    ) -> DisposableStub:
        if self._har_id:
            raise Error("HAR recording has already been started")
        # Not ported: the check of the resourcesDir option against a .zip har file;
        # the option is JavaScript only.
        default_content: Literal["attach", "embed"] = (
            "attach" if str(path).endswith(".zip") else "embed"
        )
        self._har_id = await self._record_into_har(
            har=path,
            page=None,
            url=url_filter,
            update_content=content if content is not None else default_content,
            update_mode=mode if mode is not None else "full",
        )
        return DisposableStub(lambda: self.stop_har())

    @api_call()
    async def stop_har(self) -> None:
        har_id = self._har_id
        if not har_id:
            raise Error("HAR recording has not been started")
        self._har_id = None
        await self._export_har(har_id)

    async def _record_into_har(
        self,
        har: Union[str, Path],
        page: Optional["Page"],
        url: Optional[Union[str, Pattern[str]]],
        update_content: Optional[Literal["attach", "embed", "omit"]],
        update_mode: Optional[Literal["minimal", "full"]],
    ) -> str:
        # Not ported: the resourcesDir option; it is JavaScript only.
        # Python: the path can be a pathlib.Path.
        har = str(har)
        is_zip = har.endswith(".zip")
        options: Dict[str, Any] = {
            "content": update_content if update_content is not None else "attach",
            "urlGlob": url if isinstance(url, str) else None,
            "urlRegexSource": url.pattern if isinstance(url, re.Pattern) else None,
            # Python: the flags of a re.Pattern, in the JS letters.
            "urlRegexFlags": (
                escape_regex_flags(url) if isinstance(url, re.Pattern) else None
            ),
            "mode": update_mode if update_mode is not None else "minimal",
            "harPath": None if is_zip else har,
        }
        har_id = (
            await self._channel.harStart(
                page=page._channel if page else None,
                options=cast("channels.RecordHarOptions", options),
                timeout=NO_TIMEOUT,
            )
        )["harId"]
        self._har_recorders[har_id] = {"path": har}
        return har_id

    async def _export_har(self, har_id: str) -> None:
        har_params = self._har_recorders.get(har_id)
        if not har_params:
            return
        del self._har_recorders[har_id]
        is_local = not self._connection.is_remote()
        is_zip = har_params["path"].endswith(".zip")

        if is_local:
            entries = (
                await self._channel.harExport(
                    harId=har_id, mode="entries", timeout=NO_TIMEOUT
                )
            )["entries"]
            if not is_zip:
                # Server wrote HAR and resources to the user's chosen paths.
                return
            local_utils = self._connection.local_utils()
            if not local_utils:
                raise Error("Cannot save zipped HAR in thin clients")
            await local_utils.zip(
                {
                    "zipFile": har_params["path"],
                    "entries": entries,
                    "mode": "write",
                    "includeSources": False,
                    "additionalSources": [],
                }
            )
            return

        artifact_channel = (
            await self._channel.harExport(
                harId=har_id, mode="archive", timeout=NO_TIMEOUT
            )
        )["artifact"]
        artifact = Artifact.from_(cast("ArtifactChannel", artifact_channel))
        if is_zip:
            await artifact.save_as(path=har_params["path"])
            await artifact.delete()
            return
        local_utils = self._connection.local_utils()
        if not local_utils:
            raise Error("Uncompressed har is not supported in thin clients")
        await artifact.save_as(path=har_params["path"] + ".tmp")
        await local_utils.har_unzip(
            {
                "zipFile": har_params["path"] + ".tmp",
                "harFile": har_params["path"],
                # Not ported: resourcesDir, a JavaScript only option.
            }
        )
        await artifact.delete()

    @internal
    async def _export_all_hars(self) -> None:
        await asyncio.gather(
            *[self._export_har(har_id) for har_id in list(self._har_recorders)]
        )

    async def _do_stop_chunk(self, file_path: Optional[Union[str, Path]]) -> None:
        self._reset_stack_counter()

        additional_sources = list(self._additional_sources)
        self._additional_sources.clear()
        stacks_id = self._stacks_id
        self._stacks_id = None

        try:
            await self._save_chunk(file_path, stacks_id, additional_sources)
        except Exception:
            # Release the stack session even on failure, otherwise later traces keep appending to it.
            if stacks_id:
                local_utils = self._connection.local_utils()
                if local_utils:
                    try:
                        await local_utils.trace_discarded({"stacksId": stacks_id})
                    except Exception:
                        pass
            raise

    async def _save_chunk(
        self,
        file_path: Optional[Union[str, Path]],
        stacks_id: Optional[str],
        additional_sources: Sequence[str],
    ) -> None:
        if not file_path:
            # Not interested in artifacts.
            await self._channel.tracingStopChunk(mode="discard", timeout=NO_TIMEOUT)
            if stacks_id:
                await cast(
                    "LocalUtils", self._connection.local_utils()
                ).trace_discarded({"stacksId": stacks_id})
            return

        local_utils = self._connection.local_utils()
        if not local_utils:
            raise Error("Cannot save trace in thin clients")

        is_local = not self._connection.is_remote()

        if is_local:
            result = await self._channel.tracingStopChunk(
                mode="entries", timeout=NO_TIMEOUT
            )
            await local_utils.zip(
                {
                    # Python: the path can be a pathlib.Path.
                    "zipFile": str(file_path),
                    "entries": result["entries"],
                    "mode": "write",
                    "stacksId": stacks_id,
                    "includeSources": self._include_sources,
                    "additionalSources": additional_sources,
                }
            )
            return

        result = await self._channel.tracingStopChunk(
            mode="archive", timeout=NO_TIMEOUT
        )

        # The artifact may be missing if the browser closed while stopping tracing.
        if not result["artifact"]:
            if stacks_id:
                await local_utils.trace_discarded({"stacksId": stacks_id})
            return

        # Save trace to the final local file.
        artifact = Artifact.from_(result["artifact"])
        try:
            await artifact.save_as(path=file_path)
        except Exception:
            # Delete the artifact best-effort, the save error is the one to surface.
            try:
                await artifact.delete()
            except Exception:
                pass
            raise
        await artifact.delete()

        await local_utils.zip(
            {
                # Python: the path can be a pathlib.Path.
                "zipFile": str(file_path),
                "entries": [],
                "mode": "append",
                "stacksId": stacks_id,
                "includeSources": self._include_sources,
                "additionalSources": additional_sources,
            }
        )

    def _reset_stack_counter(self) -> None:
        if self._is_tracing:
            self._is_tracing = False
            self._connection.set_is_tracing(False)
