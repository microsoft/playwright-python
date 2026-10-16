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

from typing import TYPE_CHECKING, List, Literal, Optional

from playwright._impl._api_structures import WebStorageItem

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._page import Page


WebStorageKind = Literal["local", "session"]


class WebStorage:
    def __init__(self, page: "Page", kind: WebStorageKind) -> None:
        self._page = page
        self._kind: WebStorageKind = kind
        self._loop = page._loop
        self._dispatcher_fiber = page._dispatcher_fiber

    async def items(self) -> List[WebStorageItem]:
        result = await self._page._channel.webStorageItems(kind=self._kind)
        return result["items"]

    async def get_item(self, name: str) -> Optional[str]:
        result = await self._page._channel.webStorageGetItem(kind=self._kind, name=name)
        return result["value"]

    async def set_item(self, name: str, value: str) -> None:
        await self._page._channel.webStorageSetItem(
            kind=self._kind, name=name, value=value
        )

    async def remove_item(self, name: str) -> None:
        await self._page._channel.webStorageRemoveItem(kind=self._kind, name=name)

    async def clear(self) -> None:
        await self._page._channel.webStorageClear(kind=self._kind)
