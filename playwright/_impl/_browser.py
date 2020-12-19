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
from typing import TYPE_CHECKING, Dict, List, Tuple, Union

from playwright._impl._api_structures import StorageState
from playwright._impl._api_types import Geolocation, ProxySettings
from playwright._impl._browser_context import BrowserContext
from playwright._impl._connection import ChannelOwner, from_channel
from playwright._impl._helper import ColorScheme, is_safe_close_error, locals_to_params
from playwright._impl._network import serialize_headers
from playwright._impl._page import Page

if sys.version_info >= (3, 8):  # pragma: no cover
    from typing import Literal
else:  # pragma: no cover
    from typing_extensions import Literal

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._browser_type import BrowserType


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
        viewport: Union[Tuple[int, int], Literal[0]] = None,
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
        httpCredentials: Tuple[str, str] = None,
        deviceScaleFactor: int = None,
        isMobile: bool = None,
        hasTouch: bool = None,
        colorScheme: ColorScheme = None,
        acceptDownloads: bool = None,
        defaultBrowserType: str = None,
        proxy: ProxySettings = None,
        recordHarPath: Union[Path, str] = None,
        recordHarOmitContent: bool = None,
        recordVideoDir: Union[Path, str] = None,
        recordVideoSize: Tuple[int, int] = None,
        storageState: Union[StorageState, str, Path] = None,
    ) -> BrowserContext:
        params = locals_to_params(locals())
        normalize_context_params(params)

        channel = await self._channel.send("newContext", params)
        context = from_channel(channel)
        self._contexts.append(context)
        context._browser = self
        context._options = params
        return context

    async def newPage(
        self,
        viewport: Union[Tuple[int, int], Literal[0]] = None,
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
        httpCredentials: Tuple[str, str] = None,
        deviceScaleFactor: int = None,
        isMobile: bool = None,
        hasTouch: bool = None,
        colorScheme: ColorScheme = None,
        acceptDownloads: bool = None,
        defaultBrowserType: str = None,
        proxy: ProxySettings = None,
        recordHarPath: Union[Path, str] = None,
        recordHarOmitContent: bool = None,
        recordVideoDir: Union[Path, str] = None,
        recordVideoSize: Tuple[int, int] = None,
        storageState: Union[StorageState, str, Path] = None,
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
        try:
            await self._channel.send("close")
        except Exception as e:
            if not is_safe_close_error(e):
                raise e

    @property
    def version(self) -> str:
        return self._initializer["version"]


def normalize_context_params(params: Dict) -> None:
    if "viewport" in params and params["viewport"] == 0:
        del params["viewport"]
        params["noDefaultViewport"] = True
    if "defaultBrowserType" in params:
        del params["defaultBrowserType"]
    if "extraHTTPHeaders" in params:
        params["extraHTTPHeaders"] = serialize_headers(params["extraHTTPHeaders"])
    if "recordHarPath" in params:
        params["recordHar"] = {"path": str(params["recordHarPath"])}
        if "recordHarOmitContent" in params:
            params["recordHar"]["omitContent"] = True
            del params["recordHarOmitContent"]
        del params["recordHarPath"]
    if "recordVideoDir" in params:
        params["recordVideo"] = {"dir": str(params["recordVideoDir"])}
        if "recordVideoSize" in params:
            params["recordVideo"]["size"] = {
                "width": params["recordVideoSize"][0],
                "height": params["recordVideoSize"][1],
            }
            del params["recordVideoSize"]
        del params["recordVideoDir"]
    if "storageState" in params:
        storageState = params["storageState"]
        if not isinstance(storageState, dict):
            with open(storageState, "r") as f:
                params["storageState"] = json.load(f)
