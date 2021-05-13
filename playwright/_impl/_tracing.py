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
from typing import TYPE_CHECKING, Union

from playwright._impl._helper import locals_to_params

if TYPE_CHECKING:
    from playwright._impl._browser_context import BrowserContext


class Tracing:
    def __init__(self, channel: "BrowserContext") -> None:
        self._channel = channel._channel  # type: ignore
        self._loop = channel._loop
        self._dispatcher_fiber = channel._dispatcher_fiber

    async def start(
        self, name: str = None, snapshots: bool = None, screenshots: bool = None
    ) -> None:
        params = locals_to_params(locals())
        await self._channel.send("tracingStart", params)

    async def stop(self) -> None:
        await self._channel.send("tracingStop")

    async def export(self, path: Union[pathlib.Path, str]) -> None:
        await self._channel.send("tracingExport", {"path": str(path)})
