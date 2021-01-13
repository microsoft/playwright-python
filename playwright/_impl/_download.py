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

import pathlib
from pathlib import Path
from typing import Dict, Optional, Union

from playwright._impl._connection import ChannelOwner
from playwright._impl._helper import patch_error_message


class Download(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)

    @property
    def url(self) -> str:
        return self._initializer["url"]

    @property
    def suggested_filename(self) -> str:
        return self._initializer["suggestedFilename"]

    async def delete(self) -> None:
        await self._channel.send("delete")

    async def failure(self) -> Optional[str]:
        return patch_error_message(await self._channel.send("failure"))

    async def path(self) -> Optional[pathlib.Path]:
        return pathlib.Path(await self._channel.send("path"))

    async def save_as(self, path: Union[str, Path]) -> None:
        path = str(Path(path))
        return await self._channel.send("saveAs", dict(path=path))
