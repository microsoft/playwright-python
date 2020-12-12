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

import os
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:  # pragma: no cover
    from playwright._page import Page


class Video:
    def __init__(self, page: "Page") -> None:
        self._loop = page._loop
        self._dispatcher_fiber = page._dispatcher_fiber
        self._page = page
        self._path_future = page._loop.create_future()

    async def path(self) -> str:
        return await self._path_future

    def _set_relative_path(self, relative_path: str) -> None:
        self._path_future.set_result(
            os.path.join(
                cast(str, self._page._browser_context._options["recordVideo"]["dir"]),
                relative_path,
            )
        )
