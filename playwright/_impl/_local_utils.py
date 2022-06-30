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
from typing import Dict, List, Optional, cast

from playwright._impl._api_structures import HeadersArray, NameValue
from playwright._impl._connection import ChannelOwner
from playwright._impl._helper import HarLookupResult, locals_to_params


class LocalUtils(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)

    async def zip(self, zip_file: str, entries: List[NameValue]) -> None:
        await self._channel.send("zip", {"zipFile": zip_file, "entries": entries})

    async def har_open(self, file: str) -> None:
        params = locals_to_params(locals())
        await self._channel.send("harOpen", params)

    async def har_lookup(
        self,
        harId: str,
        url: str,
        method: str,
        headers: HeadersArray,
        isNavigationRequest: bool,
        postData: Optional[bytes] = None,
    ) -> HarLookupResult:
        params = locals_to_params(locals())
        if "postData" in params:
            params["postData"] = base64.b64encode(params["postData"]).decode()
        return cast(
            HarLookupResult,
            await self._channel.send_return_as_dict("harLookup", params),
        )

    async def har_close(self, harId: str) -> None:
        params = locals_to_params(locals())
        await self._channel.send("harClose", params)

    async def har_unzip(self, zipFile: str, harFile: str) -> None:
        params = locals_to_params(locals())
        await self._channel.send("harUnzip", params)
