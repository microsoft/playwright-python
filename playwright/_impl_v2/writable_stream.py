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

"""Port of packages/playwright-core/src/client/writableStream.ts.

Python: there is no Node Writable. WritableStreamImpl keeps _write() and _final();
the error that they pass to the callback is raised. pipeline() below is the
counterpart of stream.promises.pipeline(fs.createReadStream(path), writable), which
elementHandle.ts uses to upload files. The binary is base64 on the channel.
"""

import asyncio
import base64
from pathlib import Path
from typing import TYPE_CHECKING, Any, Union

from playwright._impl_v2.channel_owner import ChannelOwner, from_channel
from playwright._impl_v2.timeout_settings import NO_TIMEOUT
from playwright._impl_v2.utils.promise import catch

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl_v2.protocol_channels import WritableStreamChannel

# Python: the default highWaterMark of fs.createReadStream().
_READ_STREAM_HIGH_WATER_MARK = 64 * 1024


class WritableStream(ChannelOwner):
    _channel: "WritableStreamChannel"

    @staticmethod
    def from_(Stream: "WritableStreamChannel") -> "WritableStream":
        return from_channel(Stream)

    def __init__(
        self,
        parent: ChannelOwner,
        type: str,
        guid: str,
        initializer: Any,
    ) -> None:
        super().__init__(parent, type, guid, initializer)

    def stream(self) -> "WritableStreamImpl":
        return WritableStreamImpl(self._channel)


class WritableStreamImpl:
    def __init__(self, channel: "WritableStreamChannel") -> None:
        self._channel = channel

    async def _write(self, chunk: Union[bytes, str]) -> None:
        error = await catch(
            self._channel.write(
                # Python: the binary is base64 on the channel.
                binary=base64.b64encode(
                    chunk.encode() if isinstance(chunk, str) else chunk
                ).decode(),
                timeout=NO_TIMEOUT,
            ),
            lambda e: e,
        )
        # Python: callback(error) raises the error.
        if error:
            raise error

    async def _final(self) -> None:
        # Stream might be destroyed after the connection was closed.
        error = await catch(self._channel.close(timeout=NO_TIMEOUT), lambda e: e)
        # Python: callback(error) raises the error.
        if error:
            raise error


# Python only: stream.promises.pipeline(fs.createReadStream(path), writable). The
# file is read in a thread, in chunks of the default highWaterMark; each chunk goes
# to _write(), and _final() runs at the end. An error stops the pipeline, and
# _final() does not run.
async def pipeline(path: Union[str, Path], writable: WritableStreamImpl) -> None:
    loop = asyncio.get_running_loop()
    file = await loop.run_in_executor(None, open, path, "rb")
    try:
        while True:
            chunk = await loop.run_in_executor(
                None, file.read, _READ_STREAM_HIGH_WATER_MARK
            )
            if not chunk:
                break
            await writable._write(chunk)
    finally:
        await loop.run_in_executor(None, file.close)
    await writable._final()
