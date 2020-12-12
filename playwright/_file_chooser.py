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

from typing import TYPE_CHECKING, List, Union

from playwright._types import FilePayload

if TYPE_CHECKING:  # pragma: no cover
    from playwright._element_handle import ElementHandle
    from playwright._page import Page


class FileChooser:
    def __init__(
        self, page: "Page", element_handle: "ElementHandle", is_multiple: bool
    ) -> None:
        self._page = page
        self._loop = page._loop
        self._dispatcher_fiber = page._dispatcher_fiber
        self._element_handle = element_handle
        self._is_multiple = is_multiple

    @property
    def page(self) -> "Page":
        return self._page

    @property
    def element(self) -> "ElementHandle":
        return self._element_handle

    @property
    def isMultiple(self) -> bool:
        return self._is_multiple

    async def setFiles(
        self,
        files: Union[str, FilePayload, List[str], List[FilePayload]],
        timeout: int = None,
        noWaitAfter: bool = None,
    ) -> None:
        await self._element_handle.setInputFiles(files, timeout, noWaitAfter)
