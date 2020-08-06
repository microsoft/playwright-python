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
import base64
import io
from typing import Dict, Optional

from playwright.connection import ChannelOwner


class StreamIO(io.RawIOBase):
    def __init__(self, channel: ChannelOwner, loop) -> None:
        self._channel = channel
        self._loop = loop


    async def read(self, size: int = None) -> Optional[bytes]: # type: ignore
        if not size:
            size = 16384
        result = await self._channel.send("read", dict(size=size))
        return base64.b64decode(result)


class Stream(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._loop = parent._loop

    async def stream(self,) -> StreamIO:
        return StreamIO(self._channel, self._loop)
