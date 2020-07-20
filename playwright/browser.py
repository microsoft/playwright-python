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

import sys
from types import SimpleNamespace
from typing import Dict, List, Union

from playwright.browser_context import BrowserContext
from playwright.connection import ChannelOwner, ConnectionScope, from_channel
from playwright.helper import ColorScheme, locals_to_params
from playwright.network import serialize_headers
from playwright.page import Page

if sys.version_info >= (3, 8):  # pragma: no cover
    from typing import Literal
else:  # pragma: no cover
    from typing_extensions import Literal


class Browser(ChannelOwner):

    Events = SimpleNamespace(Disconnected="disconnected",)

    def __init__(self, scope: ConnectionScope, guid: str, initializer: Dict) -> None:
        super().__init__(scope, guid, initializer, True)
        self._is_connected = True
        self._is_closed_or_closing = False

        self._contexts: List[BrowserContext] = list()
        self._channel.on("close", lambda _: self._on_close())

    def _on_close(self) -> None:
        self._is_connected = False
        self.emit(Browser.Events.Disconnected)
        self._is_closed_or_closing = True
        self._scope.dispose()

    @property
    def contexts(self) -> List[BrowserContext]:
        return self._contexts.copy()

    def isConnected(self) -> bool:
        return self._is_connected

    async def newContext(
        self,
        viewport: Union[Dict, Literal[0]] = None,
        ignoreHTTPSErrors: bool = None,
        javaScriptEnabled: bool = None,
        bypassCSP: bool = None,
        userAgent: str = None,
        locale: str = None,
        timezoneId: str = None,
        geolocation: Dict = None,
        permissions: List[str] = None,
        extraHTTPHeaders: Dict[str, str] = None,
        offline: bool = None,
        httpCredentials: Dict = None,
        deviceScaleFactor: int = None,
        isMobile: bool = None,
        hasTouch: bool = None,
        colorScheme: ColorScheme = None,
        acceptDownloads: bool = None,
    ) -> BrowserContext:
        params = locals_to_params(locals())
        if viewport == 0:
            params["viewport"] = None
        if extraHTTPHeaders:
            params["extraHTTPHeaders"] = serialize_headers(extraHTTPHeaders)
        channel = await self._channel.send("newContext", params)
        context = from_channel(channel)
        self._contexts.append(context)
        context._browser = self
        return context

    async def newPage(
        self,
        viewport: Dict = None,
        ignoreHTTPSErrors: bool = None,
        javaScriptEnabled: bool = None,
        bypassCSP: bool = None,
        userAgent: str = None,
        locale: str = None,
        timezoneId: str = None,
        geolocation: Dict = None,
        permissions: List[str] = None,
        extraHTTPHeaders: Dict[str, str] = None,
        offline: bool = None,
        httpCredentials: Dict = None,
        deviceScaleFactor: int = None,
        isMobile: bool = None,
        hasTouch: bool = None,
        colorScheme: ColorScheme = None,
        acceptDownloads: bool = None,
    ) -> Page:
        params = locals_to_params(locals())
        context = await self.newContext(**params)
        page = await context.newPage()
        page._owned_context = context
        context._owner_page = page
        return page

    async def close(self) -> None:
        if self._is_closed_or_closing:
            return
        self._is_closed_or_closing = True
        await self._channel.send("close")
