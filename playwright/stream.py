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
import io
from typing import Dict, Optional

from playwright.connection import ChannelOwner


class Stream(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)

    async def stream(self, fp: io.BytesIO, size: Optional[int]) -> io.BytesIO:
        if not fp:
            fp = io.BytesIO()
        if not size:
            size = 16384  # default 16kb in Node.js

        while True:
            result = await self._channel.send("read", dict(size=size))
            if not result:
                fp.seek(0)
                return fp
            fp.write(base64.b64decode(result))
