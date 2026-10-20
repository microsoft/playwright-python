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

"""Port of packages/playwright-core/src/client/video.ts.

Python: path() returns a pathlib.Path, and the message of the remote path error
names save_as(). The check of the sync API in save_as() (the page must be closed
first) is not ported: there is no sync code here.
"""

import pathlib
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Union

from playwright._impl_v2.errors import Error
from playwright._impl_v2.event_emitter import EventEmitter

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl_v2.artifact import Artifact
    from playwright._impl_v2.connection import Connection


class Video(EventEmitter):
    def __init__(
        self, connection: "Connection", artifact: Optional["Artifact"]
    ) -> None:
        super().__init__()
        self._is_remote = connection.is_remote()
        self._artifact = artifact
        # Python: the generated API reads the event loop of each object.
        self._loop = connection._loop

    async def path(self) -> pathlib.Path:
        if self._is_remote:
            # Python: the message names the Python method, save_as().
            raise Error(
                "Path is not available when connecting remotely. Use save_as() to save a local copy."
            )
        if not self._artifact:
            raise Error("Video recording has not been started.")
        # Python: the API returns a pathlib.Path.
        return pathlib.Path(self._artifact._initializer["absolutePath"])

    async def save_as(self, path: Union[str, Path]) -> None:
        if not self._artifact:
            raise Error("Video recording has not been started.")
        return await self._artifact.save_as(path=path)

    async def delete(self) -> None:
        if self._artifact:
            await self._artifact.delete()
