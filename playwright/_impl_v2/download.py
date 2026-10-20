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

"""Port of packages/playwright-core/src/client/download.ts.

Python: page, url and suggested_filename are properties, as the generated API reads
them. path() returns a pathlib.Path. createReadStream() is not ported: the Python
API has no Node streams.
"""

import pathlib
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Union

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl_v2.artifact import Artifact
    from playwright._impl_v2.page import Page


class Download:
    def __init__(
        self, page: "Page", url: str, suggested_filename: str, artifact: "Artifact"
    ) -> None:
        self._page = page
        self._url = url
        self._suggested_filename = suggested_filename
        self._artifact = artifact
        # Python: the generated API reads the event loop of each object.
        self._loop = page._loop

    @property
    def page(self) -> "Page":
        return self._page

    @property
    def url(self) -> str:
        return self._url

    @property
    def suggested_filename(self) -> str:
        return self._suggested_filename

    async def path(self) -> pathlib.Path:
        # Python: the API returns a pathlib.Path.
        return pathlib.Path(await self._artifact.path_after_finished())

    async def save_as(self, path: Union[str, Path]) -> None:
        return await self._artifact.save_as(path=path)

    async def failure(self) -> Optional[str]:
        return await self._artifact.failure()

    # Not ported: createReadStream(), a Node stream; the Python API does not have it.

    async def cancel(self) -> None:
        return await self._artifact.cancel()

    async def delete(self) -> None:
        return await self._artifact.delete()

    # Python only: the members of the Python API that upstream does not have.

    def __repr__(self) -> str:
        return f"<Download url={self.url!r} suggested_filename={self.suggested_filename!r}>"
