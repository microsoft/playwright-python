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
import os
from pathlib import Path
from typing import TYPE_CHECKING, List, Union

from playwright._impl._api_structures import FilePayload
from playwright._impl._helper import async_readfile

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._element_handle import ElementHandle
    from playwright._impl._page import Page


class FileChooser:
    def __init__(
        self, page: "Page", element_handle: "ElementHandle", is_multiple: bool
    ) -> None:
        self._page = page
        self._loop = page._loop
        self._dispatcher_fiber = page._dispatcher_fiber
        self._element_handle = element_handle
        self._is_multiple = is_multiple

    def __repr__(self) -> str:
        return f"<FileChooser page={self._page} element={self._element_handle}>"

    @property
    def page(self) -> "Page":
        return self._page

    @property
    def element(self) -> "ElementHandle":
        return self._element_handle

    def is_multiple(self) -> bool:
        return self._is_multiple

    async def set_files(
        self,
        files: Union[str, Path, FilePayload, List[Union[str, Path]], List[FilePayload]],
        timeout: float = None,
        noWaitAfter: bool = None,
    ) -> None:
        await self._element_handle.set_input_files(files, timeout, noWaitAfter)


async def normalize_file_payloads(
    files: Union[str, Path, FilePayload, List[Union[str, Path]], List[FilePayload]]
) -> List:
    file_list = files if isinstance(files, list) else [files]
    file_payloads: List = []
    for item in file_list:
        if isinstance(item, (str, Path)):
            file_payloads.append(
                {
                    "name": os.path.basename(item),
                    "buffer": base64.b64encode(await async_readfile(item)).decode(),
                }
            )
        else:
            file_payloads.append(
                {
                    "name": item["name"],
                    "mimeType": item["mimeType"],
                    "buffer": base64.b64encode(item["buffer"]).decode(),
                }
            )

    return file_payloads
