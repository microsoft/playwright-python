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
from typing import Any, Dict, Literal, Optional, Pattern, Union, cast

from playwright._impl._api_structures import TracingGroupLocation
from playwright._impl._artifact import Artifact
from playwright._impl._connection import (
    ChannelOwner,
    from_channel,
    from_nullable_channel,
)
from playwright._impl._disposable import DisposableStub
from playwright._impl._helper import Error, locals_to_params


class Tracing(ChannelOwner):
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
        name: str = None,
        title: str = None,
        snapshots: bool = None,
        screenshots: bool = None,
        sources: bool = None,
        live: bool = None,
    ) -> None:
        params = locals_to_params(locals())
        self._include_sources = bool(sources)
        self._is_live = bool(live)

        await self._channel.send(
            "tracingStart",
            None,
            {
                "name": name,
                "snapshots": snapshots,
                "screenshots": screenshots,
                "live": live,
            },
        )
        trace_name = await self._channel.send(
            "tracingStartChunk", None, {"title": title, "name": name}
        )
        await self._start_collecting_stacks(trace_name)

    async def start_chunk(self, title: str = None, name: str = None) -> None:
        params = locals_to_params(locals())
        trace_name = await self._channel.send("tracingStartChunk", None, params)
        await self._start_collecting_stacks(trace_name)

    async def _start_collecting_stacks(self, trace_name: str) -> None:
        if not self._is_tracing:
            self._is_tracing = True
            self._connection.set_is_tracing(True)
        self._stacks_id = await self._connection.local_utils.tracing_started(
            self._traces_dir, trace_name, self._is_live
        )

    async def stop_chunk(self, path: Union[pathlib.Path, str] = None) -> None:
        await self._do_stop_chunk(path)

    async def stop(self, path: Union[pathlib.Path, str] = None) -> None:
        await self._do_stop_chunk(path)
        await self._channel.send(
            "tracingStop",
            None,
        )

    async def _do_stop_chunk(self, file_path: Union[pathlib.Path, str] = None) -> None:
        self._reset_stack_counter()

        if not file_path:
            # Not interested in any artifacts
            await self._channel.send("tracingStopChunk", None, {"mode": "discard"})
            if self._stacks_id:
                await self._connection.local_utils.trace_discarded(self._stacks_id)
            return

        is_local = not self._connection.is_remote

        if is_local:
            result = await self._channel.send_return_as_dict(
                "tracingStopChunk", None, {"mode": "entries"}
            )
            await self._connection.local_utils.zip(
                {
                    "zipFile": str(file_path),
                    "entries": result["entries"],
                    "stacksId": self._stacks_id,
                    "mode": "write",
                    "includeSources": self._include_sources,
                }
            )
            return

        result = await self._channel.send_return_as_dict(
            "tracingStopChunk",
            None,
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
            if self._stacks_id:
                await self._connection.local_utils.trace_discarded(self._stacks_id)
            return

        # Save trace to the final local file.
        await artifact.save_as(file_path)
        await artifact.delete()

        await self._connection.local_utils.zip(
            {
                "zipFile": str(file_path),
                "entries": [],
                "stacksId": self._stacks_id,
                "mode": "append",
                "includeSources": self._include_sources,
            }
        )

    def _reset_stack_counter(self) -> None:
        if self._is_tracing:
            self._is_tracing = False
            self._connection.set_is_tracing(False)

    async def group(
        self, name: str, location: TracingGroupLocation = None
    ) -> DisposableStub:
        await self._channel.send("tracingGroup", None, locals_to_params(locals()))
        return DisposableStub(lambda: self.group_end(), self)

    async def group_end(self) -> None:
        await self._channel.send(
            "tracingGroupEnd",
            None,
        )

    async def start_har(
        self,
        path: Union[pathlib.Path, str],
        content: Literal["attach", "embed", "omit"] = None,
        mode: Literal["full", "minimal"] = None,
        urlFilter: Union[str, Pattern[str]] = None,
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
            url=urlFilter,
            update_content=content or default_content,
            update_mode=mode or "full",
        )
        return DisposableStub(lambda: self.stop_har(), self)

    async def _record_into_har(
        self,
        har: Union[pathlib.Path, str],
        page: Optional[ChannelOwner],
        url: Union[str, Pattern[str]] = None,
        update_content: Literal["attach", "embed", "omit"] = None,
        update_mode: Literal["full", "minimal"] = None,
        resourcesDir: Optional[str] = None,
    ) -> str:
        is_zip = str(har).endswith(".zip")
        url_glob: Optional[str] = None
        url_regex_source: Optional[str] = None
        url_regex_flags: Optional[str] = None
        if isinstance(url, str):
            url_glob = url
        elif url is not None:
            url_regex_source = url.pattern
            url_regex_flags = "".join(
                flag
                for flag, mask in (("i", 2), ("m", 8), ("s", 16))
                if url.flags & mask
            )
        options: Dict[str, object] = {
            "content": update_content or "attach",
            "mode": update_mode or "minimal",
            "harPath": None if is_zip else str(har),
        }
        if url_glob is not None:
            options["urlGlob"] = url_glob
        if url_regex_source is not None:
            options["urlRegexSource"] = url_regex_source
        if url_regex_flags is not None:
            options["urlRegexFlags"] = url_regex_flags
        if resourcesDir is not None:
            options["resourcesDir"] = resourcesDir
        params: Dict[str, Any] = {"options": options}
        if page is not None:
            params["page"] = page._channel
        result = await self._channel.send_return_as_dict("harStart", None, params)
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
        params = self._har_recorders.pop(har_id, None)
        if not params:
            return
        is_local = not self._connection.is_remote
        is_zip = params["path"].endswith(".zip")

        if is_local:
            result = await self._channel.send_return_as_dict(
                "harExport", None, {"harId": har_id, "mode": "entries"}
            )
            if not is_zip:
                # Server wrote HAR and resources to the user's chosen paths.
                return
            await self._connection.local_utils.zip(
                {
                    "zipFile": params["path"],
                    "entries": result["entries"],
                    "mode": "write",
                    "includeSources": False,
                }
            )
            return

        result = await self._channel.send_return_as_dict(
            "harExport", None, {"harId": har_id, "mode": "archive"}
        )
        artifact = cast(Artifact, from_channel(result["artifact"]))
        if is_zip:
            await artifact.save_as(params["path"])
            await artifact.delete()
            return
        # Uncompressed har is not supported in thin clients
        await artifact.save_as(params["path"] + ".tmp")
        await artifact.delete()
