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

"""Port of packages/playwright-core/src/client/jsonPipe.ts."""

from typing import TYPE_CHECKING, Dict

from playwright._impl._connection import ChannelOwner

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._protocol_channels import JsonPipeChannel


class JsonPipe(ChannelOwner):
    _channel: "JsonPipeChannel"

    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)

    def channel(self) -> "JsonPipeChannel":
        return self._channel
