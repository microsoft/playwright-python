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

"""Port of packages/playwright-core/src/client/stream.ts.

Python: there is no Node Readable. ReadableStreamImpl keeps _read() and _destroy(),
and it is an async iterator in place of the Readable machinery: each chunk is a
'data' event, the end of the iteration is the 'end' event, and the stream is
destroyed after its end (autoDestroy) or when a read fails. A read that fails
raises to the reader; upstream, the rejection of the async _read() is unhandled.
The binary is base64 on the channel.
"""

import base64
from typing import TYPE_CHECKING, Any, Optional

from playwright._impl.channel_owner import ChannelOwner, from_channel
from playwright._impl.timeout_settings import NO_TIMEOUT
from playwright._impl.utils.tasks import fire_and_forget

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl.protocol_channels import StreamChannel


class Stream(ChannelOwner):
    _channel: "StreamChannel"

    @staticmethod
    def from_(Stream: "StreamChannel") -> "Stream":
        return from_channel(Stream)

    def __init__(
        self,
        parent: ChannelOwner,
        type: str,
        guid: str,
        initializer: Any,
    ) -> None:
        super().__init__(parent, type, guid, initializer)

    def stream(self) -> "ReadableStreamImpl":
        return ReadableStreamImpl(self._channel)


class ReadableStreamImpl:
    def __init__(self, channel: "StreamChannel") -> None:
        self._channel = channel
        # Python: the destroyed state that Readable keeps.
        self._destroyed = False

    async def _read(self) -> Optional[bytes]:
        result = await self._channel.read(size=1024 * 1024, timeout=NO_TIMEOUT)
        # Python: the binary is base64 on the channel.
        binary = base64.b64decode(result["binary"])
        # Python: this.push(chunk) returns the chunk, and this.push(null) returns None.
        if len(binary):
            return binary
        else:
            return None

    def _destroy(self) -> None:
        # Stream might be destroyed after the connection was closed.
        fire_and_forget(self._channel.close(timeout=NO_TIMEOUT))

    # Python only: the parts of Readable that the client uses.

    def destroy(self) -> None:
        if self._destroyed:
            return
        self._destroyed = True
        self._destroy()

    def __aiter__(self) -> "ReadableStreamImpl":
        return self

    async def __anext__(self) -> bytes:
        if self._destroyed:
            raise StopAsyncIteration
        try:
            chunk = await self._read()
        except Exception:
            self.destroy()
            raise
        if chunk is None:
            # Python: autoDestroy destroys the stream after its end.
            self.destroy()
            raise StopAsyncIteration
        return chunk
