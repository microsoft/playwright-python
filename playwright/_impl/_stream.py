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
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Union

from playwright._impl._connection import ChannelOwner

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._protocol_channels import StreamChannel


class Stream(ChannelOwner):
    _channel: "StreamChannel"

    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)

    # stream().pipe(fs.createWriteStream(path)) in Artifact.saveAs() in
    # packages/playwright-core/src/client/artifact.ts.
    async def save_as(self, path: Union[str, Path]) -> None:
        file = await self._loop.run_in_executor(None, lambda: open(path, "wb"))
        try:
            while True:
                chunk = await self._read()
                if not chunk:
                    break
                await self._loop.run_in_executor(None, lambda: file.write(chunk))
        finally:
            await self._loop.run_in_executor(None, lambda: file.close())
            await self._destroy()

    # Reads stream() to the end, as Artifact.readIntoBuffer() in
    # packages/playwright-core/src/client/artifact.ts.
    async def read_all(self) -> bytes:
        chunks: List[bytes] = []
        try:
            while True:
                chunk = await self._read()
                if not chunk:
                    break
                chunks.append(chunk)
        finally:
            await self._destroy()
        return b"".join(chunks)

    # Port of ReadableStreamImpl._read() in packages/playwright-core/src/client/stream.ts.
    async def _read(self) -> bytes:
        result = await self._channel.read(size=1024 * 1024)
        return base64.b64decode(result["binary"])

    # Port of ReadableStreamImpl._destroy() in packages/playwright-core/src/client/stream.ts.
    async def _destroy(self) -> None:
        # Stream might be destroyed after the connection was closed.
        try:
            await self._channel.close()
        except Exception:
            pass
