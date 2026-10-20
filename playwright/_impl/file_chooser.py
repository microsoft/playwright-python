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

"""Port of packages/playwright-core/src/client/fileChooser.ts.

Python: element and page are properties, as the generated API reads them, and
set_files() takes the options as parameters. The object keeps the event loop of the
page, as the generated API reads the loop of each object.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Optional, Sequence, Union

from playwright._impl._api_structures import FilePayload

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl.element_handle import ElementHandle
    from playwright._impl.page import Page


class FileChooser:
    def __init__(
        self, page: "Page", element_handle: "ElementHandle", is_multiple: bool
    ) -> None:
        self._page = page
        self._element_handle = element_handle
        self._is_multiple = is_multiple
        # Python: the generated API reads the event loop and the dispatcher fiber of
        # each object.
        self._loop = page._loop
        self._dispatcher_fiber = page._dispatcher_fiber

    @property
    def element(self) -> "ElementHandle":
        return self._element_handle

    def is_multiple(self) -> bool:
        return self._is_multiple

    @property
    def page(self) -> "Page":
        return self._page

    async def set_files(
        self,
        files: Union[
            str, Path, FilePayload, Sequence[Union[str, Path]], Sequence[FilePayload]
        ],
        timeout: Optional[float],
        no_wait_after: Optional[bool],
    ) -> None:
        return await self._element_handle.set_input_files(
            files=files, timeout=timeout, no_wait_after=no_wait_after
        )

    # Python only: the members of the Python API that upstream does not have.

    def __repr__(self) -> str:
        return f"<FileChooser page={self._page} element={self._element_handle}>"
