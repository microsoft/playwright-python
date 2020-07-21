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

from typing import Any, Dict

from playwright.connection import Channel
from playwright.element_handle import ElementHandle


class Accessibility:
    def __init__(self, channel: Channel) -> None:
        self._channel = channel
        self._sync_owner: Any = None

    async def snapshot(
        self, interestingOnly: bool = True, root: ElementHandle = None
    ) -> Dict:
        root = root._channel if root else None
        return await self._channel.send(
            "accessibilitySnapshot", dict(root=root, interestingOnly=interestingOnly)
        )
