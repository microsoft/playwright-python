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

"""Port of packages/playwright-core/src/client/artifact.ts.

Python: there are no Node streams. create_read_stream() returns the async iterator
of stream.py; save_as() writes its chunks to the file in a thread, in place of
pipe(fs.createWriteStream(path)), and read_into_buffer() joins them, in place of the
'data' and 'end' events. A read or write error raises; upstream, an error of the
readable leaves the promise of saveAs() pending. A path can be a pathlib.Path.
"""

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Union

from playwright._impl.channel_owner import ChannelOwner, from_channel
from playwright._impl.errors import Error, patch_error_message
from playwright._impl.file_utils import mkdir_if_needed
from playwright._impl.stream import ReadableStreamImpl, Stream
from playwright._impl.timeout_settings import NO_TIMEOUT

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl.protocol_channels import ArtifactChannel


class Artifact(ChannelOwner):
    _channel: "ArtifactChannel"

    @staticmethod
    def from_(channel: "ArtifactChannel") -> "Artifact":
        return from_channel(channel)

    async def path_after_finished(self) -> str:
        if self._connection.is_remote():
            # Python: the message names the Python method, save_as().
            raise Error(
                "Path is not available when connecting remotely. Use save_as() to save a local copy."
            )
        return (await self._channel.pathAfterFinished(timeout=NO_TIMEOUT))["value"]

    async def save_as(self, path: Union[str, Path]) -> None:
        if not self._connection.is_remote():
            # Python: the driver is another process; the path is resolved against
            # the current directory of this one.
            await self._channel.saveAs(
                path=str(Path(path).absolute()), timeout=NO_TIMEOUT
            )
            return

        result = await self._channel.saveAsStream(timeout=NO_TIMEOUT)
        stream = Stream.from_(result["stream"])
        await mkdir_if_needed(path)
        # Python: stream.stream().pipe(fs.createWriteStream(path)), resolved on
        # 'finish' and rejected on 'error': the chunks are written in a thread.
        loop = asyncio.get_running_loop()
        file = await loop.run_in_executor(None, open, path, "wb")
        try:
            async for chunk in stream.stream():
                await loop.run_in_executor(None, file.write, chunk)
        finally:
            await loop.run_in_executor(None, file.close)

    async def failure(self) -> Optional[str]:
        error = (await self._channel.failure(timeout=NO_TIMEOUT))["error"]
        # Python: the message names the Python options (accept_downloads=True).
        return patch_error_message(error) if error else None

    async def create_read_stream(self) -> ReadableStreamImpl:
        result = await self._channel.stream(timeout=NO_TIMEOUT)
        stream = Stream.from_(result["stream"])
        return stream.stream()

    async def read_into_buffer(self) -> bytes:
        stream = await self.create_read_stream()
        # Python: each chunk of the iteration is a 'data' event, and its end is 'end'.
        chunks: List[bytes] = []
        async for chunk in stream:
            chunks.append(chunk)
        return b"".join(chunks)

    async def cancel(self) -> None:
        return await self._channel.cancel(timeout=NO_TIMEOUT)

    async def delete(self) -> None:
        return await self._channel.delete(timeout=NO_TIMEOUT)
