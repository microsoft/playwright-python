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

"""Port of packages/playwright-core/src/client/webError.ts.

Python: page, error and location are properties, as the generated API reads them.
The object keeps the event loop, as the generated API reads the loop of each object.
"""

import asyncio
from typing import TYPE_CHECKING, Optional

from playwright._impl._errors import Error

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl_v2 import protocol_types as channels
    from playwright._impl_v2.page import Page

    WebErrorLocation = channels.BrowserContextPageErrorEventLocation


class WebError:
    def __init__(
        self,
        page: Optional["Page"],
        error: Error,
        location: "WebErrorLocation",
    ) -> None:
        self._page = page
        self._error = error
        self._location = location
        # Python: the generated API reads the event loop of each object. A web error
        # is created in an event of the connection, so the loop is running.
        self._loop = asyncio.get_running_loop()

    @property
    def page(self) -> Optional["Page"]:
        return self._page

    @property
    def error(self) -> Error:
        return self._error

    @property
    def location(self) -> "WebErrorLocation":
        return self._location
