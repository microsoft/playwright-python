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

"""Port of packages/playwright-core/src/client/webStorage.ts.

Python: WebStorage is not a ChannelOwner, so it keeps the event loop of its page for
the generated API.
"""

from typing import TYPE_CHECKING, List, Literal, Optional

from playwright._impl._api_structures import WebStorageItem
from playwright._impl_v2.timeout_settings import NO_TIMEOUT

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl_v2.page import Page


class WebStorage:
    def __init__(self, page: "Page", kind: Literal["local", "session"]) -> None:
        self._page = page
        self._kind: Literal["local", "session"] = kind
        # Python: the generated API reads the event loop of each object.
        self._loop = page._loop

    async def items(self) -> List[WebStorageItem]:
        items = (
            await self._page._channel.webStorageItems(
                kind=self._kind, timeout=NO_TIMEOUT
            )
        )["items"]
        return items

    async def get_item(self, name: str) -> Optional[str]:
        value = (
            await self._page._channel.webStorageGetItem(
                kind=self._kind, name=name, timeout=NO_TIMEOUT
            )
        )["value"]
        # Python: an absent value is None already, so `value ?? null` is value.
        return value

    async def set_item(self, name: str, value: str) -> None:
        await self._page._channel.webStorageSetItem(
            kind=self._kind, name=name, value=value, timeout=NO_TIMEOUT
        )

    async def remove_item(self, name: str) -> None:
        await self._page._channel.webStorageRemoveItem(
            kind=self._kind, name=name, timeout=NO_TIMEOUT
        )

    async def clear(self) -> None:
        await self._page._channel.webStorageClear(kind=self._kind, timeout=NO_TIMEOUT)
