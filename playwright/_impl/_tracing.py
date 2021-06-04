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
from typing import TYPE_CHECKING, Union, cast

from playwright._impl._artifact import Artifact
from playwright._impl._connection import from_channel
from playwright._impl._helper import locals_to_params

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._browser_context import BrowserContext


class Tracing:
    def __init__(self, context: "BrowserContext") -> None:
        self._context = context
        self._channel = context._channel
        self._loop = context._loop
        self._dispatcher_fiber = context._channel._connection._dispatcher_fiber

    async def start(
        self, name: str = None, snapshots: bool = None, screenshots: bool = None
    ) -> None:
        params = locals_to_params(locals())
        await self._channel.send("tracingStart", params)

    async def stop(self, path: Union[pathlib.Path, str] = None) -> None:
        await self._channel.send("tracingStop")
        if path:
            artifact = cast(
                Artifact, from_channel(await self._channel.send("tracingExport"))
            )
            if self._context._browser:
                artifact._is_remote = self._context._browser._is_remote
            await artifact.save_as(path)
            await artifact.delete()
