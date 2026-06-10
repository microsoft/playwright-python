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

from typing import TYPE_CHECKING, List

from playwright._impl._api_structures import VirtualCredential
from playwright._impl._helper import locals_to_params

if TYPE_CHECKING:
    from playwright._impl._browser_context import BrowserContext


class Credentials:
    def __init__(self, browser_context: "BrowserContext") -> None:
        self._browser_context = browser_context
        self._loop = browser_context._loop
        self._dispatcher_fiber = browser_context._dispatcher_fiber

    async def install(self) -> None:
        await self._browser_context._channel.send("credentialsInstall", None)

    async def create(
        self,
        rpId: str,
        id: str = None,
        userHandle: str = None,
        privateKey: str = None,
        publicKey: str = None,
    ) -> VirtualCredential:
        result = await self._browser_context._channel.send_return_as_dict(
            "credentialsCreate", None, locals_to_params(locals())
        )
        return (result or {})["credential"]

    async def delete(self, id: str) -> None:
        await self._browser_context._channel.send("credentialsDelete", None, {"id": id})

    async def get(
        self,
        rpId: str = None,
        id: str = None,
    ) -> List[VirtualCredential]:
        result = await self._browser_context._channel.send_return_as_dict(
            "credentialsGet", None, locals_to_params(locals())
        )
        return (result or {}).get("credentials", [])
