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
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Union, cast

from playwright._impl._connection import ChannelOwner, from_channel
from playwright._impl._errors import Error, patch_error_message
from playwright._impl._file_utils import mkdir_if_needed
from playwright._impl._stream import Stream

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._protocol_channels import ArtifactChannel


class Artifact(ChannelOwner):
    _channel: "ArtifactChannel"

    async def path_after_finished(self) -> pathlib.Path:
        if self._connection.is_remote:
            raise Error(
                "Path is not available when connecting remotely. Use save_as() to save a local copy."
            )
        path = (await self._channel.pathAfterFinished())["value"]
        return pathlib.Path(path)

    async def save_as(self, path: Union[str, Path]) -> None:
        if not self._connection.is_remote:
            # The driver is another process: resolve the path against the current
            # directory of this process.
            await self._channel.saveAs(path=str(Path(path).absolute()))
            return

        result = await self._channel.saveAsStream()
        stream = cast(Stream, from_channel(result["stream"]))
        mkdir_if_needed(path)
        await stream.save_as(path)

    async def failure(self) -> Optional[str]:
        reason = (await self._channel.failure())["error"]
        return patch_error_message(reason) if reason else None

    async def read_into_buffer(self) -> bytes:
        stream = cast(Stream, from_channel((await self._channel.stream())["stream"]))
        return await stream.read_all()

    async def cancel(self) -> None:  # pyright: ignore[reportIncompatibleMethodOverride]
        await self._channel.cancel()

    async def delete(self) -> None:
        await self._channel.delete()
