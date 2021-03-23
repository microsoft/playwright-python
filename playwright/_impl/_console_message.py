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

from typing import Dict, List

from playwright._impl._api_structures import SourceLocation
from playwright._impl._connection import ChannelOwner, from_channel
from playwright._impl._js_handle import JSHandle


class ConsoleMessage(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)

    def __repr__(self) -> str:
        return f"<ConsoleMessage type={self.type} text={self.text}>"

    def __str__(self) -> str:
        return self.text

    @property
    def type(self) -> str:
        return self._initializer["type"]

    @property
    def text(self) -> str:
        return self._initializer["text"]

    @property
    def args(self) -> List[JSHandle]:
        return list(map(from_channel, self._initializer["args"]))

    @property
    def location(self) -> SourceLocation:
        return self._initializer["location"]
