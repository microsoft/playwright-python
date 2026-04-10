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

from playwright._impl._artifact import Artifact
from playwright._impl._helper import Error

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._connection import Connection
    from playwright._impl._page import Page


class Video:
    def __init__(
        self, page: "Page", connection: "Connection", artifact: Artifact = None
    ) -> None:
        self._loop = page._loop
        self._dispatcher_fiber = page._dispatcher_fiber
        self._page = page
        self._artifact = artifact
        self._is_remote = connection.is_remote

    def __repr__(self) -> str:
        return f"<Video page={self._page}>"

    async def path(self) -> pathlib.Path:
        if self._is_remote:
            raise Error(
                "Path is not available when using browserType.connect(). Use save_as() to save a local copy."
            )
        if not self._artifact:
            raise Error("Video recording has not been started.")
        return pathlib.Path(self._artifact.absolute_path)

    async def save_as(self, path: Union[str, pathlib.Path]) -> None:
        if not self._artifact:
            raise Error("Video recording has not been started.")
        await self._artifact.save_as(path)

    async def delete(self) -> None:
        if self._artifact:
            await self._artifact.delete()
