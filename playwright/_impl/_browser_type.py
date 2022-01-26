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

import asyncio
import pathlib
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Union, cast

from playwright._impl._api_structures import (
    Geolocation,
    HttpCredentials,
    ProxySettings,
    ViewportSize,
)
from playwright._impl._api_types import Error
from playwright._impl._browser import Browser, normalize_context_params
from playwright._impl._browser_context import BrowserContext
from playwright._impl._connection import (
    ChannelOwner,
    Connection,
    from_channel,
    from_nullable_channel,
)
from playwright._impl._helper import (
    ColorScheme,
    Env,
    ForcedColors,
    ReducedMotion,
    locals_to_params,
)
from playwright._impl._transport import WebSocketTransport
from playwright._impl._wait_helper import throw_on_timeout

if TYPE_CHECKING:
    from playwright._impl._playwright import Playwright


class BrowserType(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        _playwright: "Playwright"

    def __repr__(self) -> str:
        return f"<BrowserType name={self.name} executable_path={self.executable_path}>"

    @property
    def name(self) -> str:
        return self._initializer["name"]

    @property
    def executable_path(self) -> str:
        return self._initializer["executablePath"]

    async def launch(
        self,
        executablePath: Union[str, Path] = None,
        channel: str = None,
        args: List[str] = None,
        ignoreDefaultArgs: Union[bool, List[str]] = None,
        handleSIGINT: bool = None,
        handleSIGTERM: bool = None,
        handleSIGHUP: bool = None,
        timeout: float = None,
        env: Env = None,
        headless: bool = None,
        devtools: bool = None,
        proxy: ProxySettings = None,
        downloadsPath: Union[str, Path] = None,
        slowMo: float = None,
        tracesDir: Union[pathlib.Path, str] = None,
        chromiumSandbox: bool = None,
        firefoxUserPrefs: Dict[str, Union[str, float, bool]] = None,
    ) -> Browser:
        params = locals_to_params(locals())
        normalize_launch_params(params)
        browser = cast(
            Browser, from_channel(await self._channel.send("launch", params))
        )
        browser._local_utils = self._playwright._utils
        return browser

    async def launch_persistent_context(
        self,
        userDataDir: Union[str, Path],
        channel: str = None,
        executablePath: Union[str, Path] = None,
        args: List[str] = None,
        ignoreDefaultArgs: Union[bool, List[str]] = None,
        handleSIGINT: bool = None,
        handleSIGTERM: bool = None,
        handleSIGHUP: bool = None,
        timeout: float = None,
        env: Env = None,
        headless: bool = None,
        devtools: bool = None,
        proxy: ProxySettings = None,
        downloadsPath: Union[str, Path] = None,
        slowMo: float = None,
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
        tracesDir: Union[pathlib.Path, str] = None,
        chromiumSandbox: bool = None,
        recordHarPath: Union[Path, str] = None,
        recordHarOmitContent: bool = None,
        recordVideoDir: Union[Path, str] = None,
        recordVideoSize: ViewportSize = None,
        baseURL: str = None,
        strictSelectors: bool = None,
    ) -> BrowserContext:
        userDataDir = str(Path(userDataDir))
        params = locals_to_params(locals())
        await normalize_context_params(self._connection._is_sync, params)
        normalize_launch_params(params)
        context = cast(
            BrowserContext,
            from_channel(await self._channel.send("launchPersistentContext", params)),
        )
        context._options = params
        context.tracing._local_utils = self._playwright._utils
        return context

    async def connect_over_cdp(
        self,
        endpointURL: str,
        timeout: float = None,
        slow_mo: float = None,
        headers: Dict[str, str] = None,
    ) -> Browser:
        params = locals_to_params(locals())
        response = await self._channel.send_return_as_dict("connectOverCDP", params)
        browser = cast(Browser, from_channel(response["browser"]))
        browser._local_utils = self._playwright._utils

        default_context = cast(
            Optional[BrowserContext],
            from_nullable_channel(response.get("defaultContext")),
        )
        if default_context:
            browser._contexts.append(default_context)
            default_context._browser = browser
        return browser

    async def connect(
        self,
        ws_endpoint: str,
        timeout: float = None,
        slow_mo: float = None,
        headers: Dict[str, str] = None,
    ) -> Browser:
        if timeout is None:
            timeout = 30000

        transport = WebSocketTransport(
            self._connection._loop, ws_endpoint, headers, slow_mo
        )
        connection = Connection(
            self._connection._dispatcher_fiber,
            self._connection._object_factory,
            transport,
            self._connection._loop,
        )
        connection.mark_as_remote()
        connection._is_sync = self._connection._is_sync
        connection._loop.create_task(connection.run())
        playwright_future = connection.playwright_future

        timeout_future = throw_on_timeout(timeout, Error("Connection timed out"))
        done, pending = await asyncio.wait(
            {transport.on_error_future, playwright_future, timeout_future},
            return_when=asyncio.FIRST_COMPLETED,
        )
        if not playwright_future.done():
            playwright_future.cancel()
        if not timeout_future.done():
            timeout_future.cancel()
        playwright: "Playwright" = next(iter(done)).result()
        self._connection._child_ws_connections.append(connection)
        pre_launched_browser = playwright._initializer.get("preLaunchedBrowser")
        assert pre_launched_browser
        browser = cast(Browser, from_channel(pre_launched_browser))
        browser._should_close_connection_on_close = True
        browser._local_utils = self._playwright._utils

        def handle_transport_close() -> None:
            for context in browser.contexts:
                for page in context.pages:
                    page._on_close()
                context._on_close()
            browser._on_close()

        transport.once("close", handle_transport_close)

        return browser


def normalize_launch_params(params: Dict) -> None:
    if "env" in params:
        params["env"] = [
            {"name": name, "value": str(value)}
            for [name, value] in params["env"].items()
        ]
    if "ignoreDefaultArgs" in params:
        if params["ignoreDefaultArgs"] is True:
            params["ignoreAllDefaultArgs"] = True
            del params["ignoreDefaultArgs"]
    if "executablePath" in params:
        params["executablePath"] = str(Path(params["executablePath"]))
    if "downloadsPath" in params:
        params["downloadsPath"] = str(Path(params["downloadsPath"]))
