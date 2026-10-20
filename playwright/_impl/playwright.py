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

"""Port of packages/playwright-core/src/client/playwright.ts.

Python: _android and _electron are not ported (Android and Electron are JavaScript
only), and errors = { TimeoutError } is not ported: the API exports the error
classes.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

from playwright._impl.browser import Browser
from playwright._impl.browser_type import BrowserType
from playwright._impl.channel_owner import ChannelOwner
from playwright._impl.fetch import APIRequest
from playwright._impl.selectors import Selectors

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl import protocol_types as channels
    from playwright._impl.browser_context import BrowserContext
    from playwright._impl.page import Page
    from playwright._impl.protocol_channels import PlaywrightChannel


class Playwright(ChannelOwner):
    _channel: "PlaywrightChannel"

    def __init__(
        self,
        parent: ChannelOwner,
        type: str,
        guid: str,
        initializer: "channels.PlaywrightInitializer",
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self.request = APIRequest(self)
        self.chromium: BrowserType = BrowserType.from_(initializer["chromium"])
        self.chromium._playwright = self
        self.firefox: BrowserType = BrowserType.from_(initializer["firefox"])
        self.firefox._playwright = self
        self.webkit: BrowserType = BrowserType.from_(initializer["webkit"])
        self.webkit._playwright = self
        local_utils = self._connection.local_utils()
        self.devices: Dict[str, Any] = local_utils.devices if local_utils else {}
        self.selectors = Selectors(self)

        # Instrumentation.
        self._default_launch_options: Optional[Dict[str, Any]] = None
        self._default_context_timeout: Optional[float] = None
        self._default_context_navigation_timeout: Optional[float] = None

    @staticmethod
    def from_(channel: "PlaywrightChannel") -> "Playwright":
        return cast("Playwright", channel._object)

    def _browser_types(self) -> List[BrowserType]:
        return [self.chromium, self.firefox, self.webkit]

    def _pre_launched_browser(self) -> Browser:
        browser = Browser.from_(self._initializer["preLaunchedBrowser"])
        browser._connect_to_browser_type(self[browser._name], {}, None)
        return browser

    def _all_contexts(self) -> List["BrowserContext"]:
        return [
            context
            for type in self._browser_types()
            for context in list(type._contexts)
        ]

    def _all_pages(self) -> List["Page"]:
        return [page for context in self._all_contexts() for page in context.pages]

    # Python only: the members of the Python API that upstream does not have.

    def __getitem__(self, value: str) -> BrowserType:
        if value == "chromium":
            return self.chromium
        elif value == "firefox":
            return self.firefox
        elif value == "webkit":
            return self.webkit
        raise ValueError("Invalid browser " + value)

    async def stop(self) -> None:
        # Python: the context manager replaces it.
        pass
