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
import json
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Dict, List, Pattern, Union, cast

from playwright._impl._api_structures import (
    Geolocation,
    HttpCredentials,
    ProxySettings,
    StorageState,
    ViewportSize,
)
from playwright._impl._browser_context import BrowserContext
from playwright._impl._cdp_session import CDPSession
from playwright._impl._connection import ChannelOwner, from_channel
from playwright._impl._helper import (
    BROWSER_CLOSED_ERROR,
    ColorScheme,
    ForcedColors,
    HarContentPolicy,
    HarMode,
    ReducedMotion,
    ServiceWorkersPolicy,
    async_readfile,
    is_safe_close_error,
    locals_to_params,
    prepare_record_har_options,
)
from playwright._impl._network import serialize_headers
from playwright._impl._page import Page

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
        self._should_close_connection_on_close = False

        self._contexts: List[BrowserContext] = []
        self._channel.on("close", lambda _: self._on_close())

    def __repr__(self) -> str:
        return f"<Browser type={self._browser_type} version={self.version}>"

    def _on_close(self) -> None:
        self._is_connected = False
        self.emit(Browser.Events.Disconnected, self)
        self._is_closed_or_closing = True

    @property
    def contexts(self) -> List[BrowserContext]:
        return self._contexts.copy()

    @property
    def browser_type(self) -> "BrowserType":
        return self._browser_type

    def is_connected(self) -> bool:
        return self._is_connected

    async def new_context(
        self,
        viewport: ViewportSize = None,
        screen: ViewportSize = None,
        noViewport: bool = None,
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
        httpCredentials: HttpCredentials = None,
        deviceScaleFactor: float = None,
        isMobile: bool = None,
        hasTouch: bool = None,
        colorScheme: ColorScheme = None,
        reducedMotion: ReducedMotion = None,
        forcedColors: ForcedColors = None,
        acceptDownloads: bool = None,
        defaultBrowserType: str = None,
        proxy: ProxySettings = None,
        recordHarPath: Union[Path, str] = None,
        recordHarOmitContent: bool = None,
        recordVideoDir: Union[Path, str] = None,
        recordVideoSize: ViewportSize = None,
        storageState: Union[StorageState, str, Path] = None,
        baseURL: str = None,
        strictSelectors: bool = None,
        serviceWorkers: ServiceWorkersPolicy = None,
        recordHarUrlFilter: Union[Pattern[str], str] = None,
        recordHarMode: HarMode = None,
        recordHarContent: HarContentPolicy = None,
    ) -> BrowserContext:
        params = locals_to_params(locals())
        await prepare_browser_context_params(params)

        channel = await self._channel.send("newContext", params)
        context = cast(BrowserContext, from_channel(channel))
        self._browser_type._did_create_context(context, params, {})
        return context

    async def new_page(
        self,
        viewport: ViewportSize = None,
        screen: ViewportSize = None,
        noViewport: bool = None,
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
        httpCredentials: HttpCredentials = None,
        deviceScaleFactor: float = None,
        isMobile: bool = None,
        hasTouch: bool = None,
        colorScheme: ColorScheme = None,
        forcedColors: ForcedColors = None,
        reducedMotion: ReducedMotion = None,
        acceptDownloads: bool = None,
        defaultBrowserType: str = None,
        proxy: ProxySettings = None,
        recordHarPath: Union[Path, str] = None,
        recordHarOmitContent: bool = None,
        recordVideoDir: Union[Path, str] = None,
        recordVideoSize: ViewportSize = None,
        storageState: Union[StorageState, str, Path] = None,
        baseURL: str = None,
        strictSelectors: bool = None,
        serviceWorkers: ServiceWorkersPolicy = None,
        recordHarUrlFilter: Union[Pattern[str], str] = None,
        recordHarMode: HarMode = None,
        recordHarContent: HarContentPolicy = None,
    ) -> Page:
        params = locals_to_params(locals())

        async def inner() -> Page:
            context = await self.new_context(**params)
            page = await context.new_page()
            page._owned_context = context
            context._owner_page = page
            return page

        return await self._connection.wrap_api_call(inner)

    async def close(self) -> None:
        if self._is_closed_or_closing:
            return
        self._is_closed_or_closing = True
        try:
            await self._channel.send("close")
        except Exception as e:
            if not is_safe_close_error(e):
                raise e
        if self._should_close_connection_on_close:
            await self._connection.stop_async(BROWSER_CLOSED_ERROR)

    @property
    def version(self) -> str:
        return self._initializer["version"]

    async def new_browser_cdp_session(self) -> CDPSession:
        return from_channel(await self._channel.send("newBrowserCDPSession"))

    async def start_tracing(
        self,
        page: Page = None,
        path: Union[str, Path] = None,
        screenshots: bool = None,
        categories: List[str] = None,
    ) -> None:
        params = locals_to_params(locals())
        if page:
            params["page"] = page._channel
        if path:
            params["path"] = str(path)
        await self._channel.send("startTracing", params)

    async def stop_tracing(self) -> bytes:
        encoded_binary = await self._channel.send("stopTracing")
        return base64.b64decode(encoded_binary)


async def prepare_browser_context_params(params: Dict) -> None:
    if params.get("noViewport"):
        del params["noViewport"]
        params["noDefaultViewport"] = True
    if "defaultBrowserType" in params:
        del params["defaultBrowserType"]
    if "extraHTTPHeaders" in params:
        params["extraHTTPHeaders"] = serialize_headers(params["extraHTTPHeaders"])
    if "recordHarPath" in params:
        params["recordHar"] = prepare_record_har_options(params)
        del params["recordHarPath"]
    if "recordVideoDir" in params:
        params["recordVideo"] = {"dir": str(params["recordVideoDir"])}
        if "recordVideoSize" in params:
            params["recordVideo"]["size"] = params["recordVideoSize"]
            del params["recordVideoSize"]
        del params["recordVideoDir"]
    if "storageState" in params:
        storageState = params["storageState"]
        if not isinstance(storageState, dict):
            params["storageState"] = json.loads(
                (await async_readfile(storageState)).decode()
            )
    if params.get("colorScheme", None) == "null":
        params["colorScheme"] = "no-override"
    if params.get("reducedMotion", None) == "null":
        params["reducedMotion"] = "no-override"
    if params.get("forcedColors", None) == "null":
        params["forcedColors"] = "no-override"
