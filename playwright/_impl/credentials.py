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

"""Port of packages/playwright-core/src/client/credentials.ts.

Python: Credentials is not a ChannelOwner; it keeps the event loop of its browser
context for the generated API. The options of create() and get() are the keyword
arguments of the Python API.
"""

from typing import TYPE_CHECKING, List, Optional

from playwright._impl._api_structures import VirtualCredential
from playwright._impl.timeout_settings import NO_TIMEOUT

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl.browser_context import BrowserContext


class Credentials:
    def __init__(self, browser_context: "BrowserContext") -> None:
        self._browser_context = browser_context
        # Python: the generated API reads the event loop and the dispatcher fiber of
        # each object.
        self._loop = browser_context._loop
        self._dispatcher_fiber = browser_context._dispatcher_fiber

    async def install(self) -> None:
        await self._browser_context._channel.credentialsInstall(timeout=NO_TIMEOUT)

    async def create(
        self,
        rp_id: str,
        id: Optional[str],
        user_handle: Optional[str],
        private_key: Optional[str],
        public_key: Optional[str],
        sign_count: Optional[int],
    ) -> VirtualCredential:
        credential = (
            await self._browser_context._channel.credentialsCreate(
                id=id,
                userHandle=user_handle,
                privateKey=private_key,
                publicKey=public_key,
                signCount=sign_count,
                rpId=rp_id,
                timeout=NO_TIMEOUT,
            )
        )["credential"]
        return credential

    async def get(
        self, rp_id: Optional[str], id: Optional[str]
    ) -> List[VirtualCredential]:
        credentials = (
            await self._browser_context._channel.credentialsGet(
                rpId=rp_id, id=id, timeout=NO_TIMEOUT
            )
        )["credentials"]
        return credentials

    async def delete(self, id: str) -> None:
        await self._browser_context._channel.credentialsDelete(
            id=id, timeout=NO_TIMEOUT
        )
