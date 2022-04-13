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
import os
from typing import Dict

# COPY_BUFSIZE is taken from shutil.py in the standard library
_WINDOWS = os.name == 'nt'
COPY_BUFSIZE = 1024 * 1024 if _WINDOWS else 64 * 1024

from playwright._impl._connection import ChannelOwner


class WriteableStream(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)

    @staticmethod
    async def copy(path: os.PathLike, stream: 'WriteableStream'):
        with open(path, 'rb') as f:
            while True:
                data = f.read(COPY_BUFSIZE)
                if not data:
                    break
                await stream.send("write", {"binary": base64.b64encode(data).decode()})
        await stream.send('close')
