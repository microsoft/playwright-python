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

from typing import TYPE_CHECKING, List, Optional

from playwright._impl._api_structures import VirtualCredential

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._browser_context import BrowserContext


class Credentials:
    def __init__(self, browser_context: "BrowserContext") -> None:
        self._browser_context = browser_context
        self._loop = browser_context._loop
        self._dispatcher_fiber = browser_context._dispatcher_fiber

    async def install(self) -> None:
        await self._browser_context._channel.credentialsInstall()

    async def create(
        self,
        rp_id: str,
        id: Optional[str],
        user_handle: Optional[str],
        private_key: Optional[str],
        public_key: Optional[str],
        sign_count: Optional[int],
    ) -> VirtualCredential:
        result = await self._browser_context._channel.credentialsCreate(
            rpId=rp_id,
            id=id,
            userHandle=user_handle,
            privateKey=private_key,
            publicKey=public_key,
            signCount=sign_count,
        )
        return result["credential"]

    async def delete(self, id: str) -> None:
        await self._browser_context._channel.credentialsDelete(id=id)

    async def get(
        self,
        rp_id: Optional[str],
        id: Optional[str],
    ) -> List[VirtualCredential]:
        result = await self._browser_context._channel.credentialsGet(rpId=rp_id, id=id)
        return result["credentials"]
