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

from pathlib import Path
from typing import Any, Dict, Union

from playwright._impl._api_types import Error
from playwright._impl._connection import ChannelOwner
from playwright._impl._helper import async_readfile


class Selectors(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)

    async def register(
        self,
        name: str,
        script: str = None,
        path: Union[str, Path] = None,
        contentScript: bool = None,
    ) -> None:
        if not script and not path:
            raise Error("Either source or path should be specified")
        if path:
            script = (await async_readfile(path)).decode()
        params: Dict[str, Any] = dict(name=name, source=script)
        if contentScript:
            params["contentScript"] = True
        await self._channel.send("register", params)
