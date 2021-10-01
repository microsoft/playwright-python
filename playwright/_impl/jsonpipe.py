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

from typing import Dict

from ._connection import ChannelOwner
from ._helper import locals_to_params


class JsonPipe(ChannelOwner):
    def __init__(
        self, parent: "ChannelOwner", type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._channel.on("message", lambda msg: self.emit("message", msg["message"]))
        self._channel.on("closed", lambda _: self.emit("closed"))

    async def send(self, message: Dict) -> None:
        await self._channel.send("send", locals_to_params(locals()))

    async def close(self) -> None:
        await self._channel.send("close")
