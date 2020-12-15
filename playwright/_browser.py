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

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Dict, List, Union

from playwright._browser_context import BrowserContext
from playwright._connection import ChannelOwner, from_channel
from playwright._helper import ColorScheme, is_safe_close_error, locals_to_params
from playwright._network import serialize_headers
from playwright._page import Page
from playwright._types import (
    Credentials,
    Geolocation,
    IntSize,
    ProxyServer,
    RecordHarOptions,
    RecordVideoOptions,
    StorageState,
)

if sys.version_info >= (3, 8):  # pragma: no cover
    from typing import Literal
else:  # pragma: no cover
    from typing_extensions import Literal

if TYPE_CHECKING:  # pragma: no cover
    from playwright._browser_type import BrowserType


class Browser(ChannelOwner):

    Events = SimpleNamespace(
        Disconnected="disconnected",
    )

    def __init__(
        self, parent: "BrowserType", type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._browser_type = parent
        self._is_connected = True
        self._is_closed_or_closing = False

        self._contexts: List[BrowserContext] = []
        self._channel.on("close", lambda _: self._on_close())

    def _on_close(self) -> None:
        self._is_connected = False
        self.emit(Browser.Events.Disconnected)
        self._is_closed_or_closing = True

    @property
    def contexts(self) -> List[BrowserContext]:
        return self._contexts.copy()

    def isConnected(self) -> bool:
        return self._is_connected

    async def newContext(
        self,
        viewport: Union[IntSize, Literal[0]] = None,
        ignoreHTTPSErrors: bool = None,
        javaScriptEnabled: bool = None,
        bypassCSP: bool = None,
        userAgent: str = None,
        locale: str = None,
        timezoneId: str = None,
        geolocation: Geolocation = None,
        permissions: List[str] = None,
        extraHTTPHeaders: Dict[str, str] = None,
        offline: bool = None,
        httpCredentials: Credentials = None,
        deviceScaleFactor: int = None,
        isMobile: bool = None,
        hasTouch: bool = None,
        colorScheme: ColorScheme = None,
        acceptDownloads: bool = None,
        defaultBrowserType: str = None,
        proxy: ProxyServer = None,
        videosPath: str = None,
        videoSize: IntSize = None,
        recordHar: RecordHarOptions = None,
        recordVideo: RecordVideoOptions = None,
        storageState: Union[StorageState, str, Path] = None,
    ) -> BrowserContext:
        params = locals_to_params(locals())
        # Python is strict in which variables gets passed to methods. We get this
        # value from the device descriptors, thats why we have to strip it out.
        if defaultBrowserType in params:
            del params["defaultBrowserType"]
        if storageState:
            if not isinstance(storageState, dict):
                with open(storageState, "r") as f:
                    params["storageState"] = json.load(f)
        if viewport == 0:
            del params["viewport"]
            params["noDefaultViewport"] = True
        if extraHTTPHeaders:
            params["extraHTTPHeaders"] = serialize_headers(extraHTTPHeaders)
        if not recordVideo and videosPath:
            params["recordVideo"] = {"dir": videosPath}
            if videoSize:
                params["recordVideo"]["size"] = videoSize

        channel = await self._channel.send("newContext", params)
        context = from_channel(channel)
        self._contexts.append(context)
        context._browser = self
        context._options = params
        return context

    async def newPage(
        self,
        viewport: Union[IntSize, Literal[0]] = None,
        ignoreHTTPSErrors: bool = None,
        javaScriptEnabled: bool = None,
        bypassCSP: bool = None,
        userAgent: str = None,
        locale: str = None,
        timezoneId: str = None,
        geolocation: Geolocation = None,
        permissions: List[str] = None,
        extraHTTPHeaders: Dict[str, str] = None,
        offline: bool = None,
        httpCredentials: Credentials = None,
        deviceScaleFactor: int = None,
        isMobile: bool = None,
        hasTouch: bool = None,
        colorScheme: ColorScheme = None,
        acceptDownloads: bool = None,
        defaultBrowserType: str = None,
        proxy: ProxyServer = None,
        videosPath: str = None,
        videoSize: IntSize = None,
        recordHar: RecordHarOptions = None,
        recordVideo: RecordVideoOptions = None,
        storageState: Union[StorageState, str, Path] = None,
    ) -> Page:
        params = locals_to_params(locals())
        # Python is strict in which variables gets passed to methods. We get this
        # value from the device descriptors, thats why we have to strip it out.
        if defaultBrowserType:
            del params["defaultBrowserType"]
        if storageState:
            if not isinstance(storageState, dict):
                with open(storageState, "r") as f:
                    params["storageState"] = json.load(f)
        context = await self.newContext(**params)
        page = await context.newPage()
        page._owned_context = context
        context._owner_page = page
        return page

    async def close(self) -> None:
        if self._is_closed_or_closing:
            return
        self._is_closed_or_closing = True
        try:
            await self._channel.send("close")
        except Exception as e:
            if not is_safe_close_error(e):
                raise e

    @property
    def version(self) -> str:
        return self._initializer["version"]
