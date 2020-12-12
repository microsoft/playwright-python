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
from pathlib import Path
from typing import Dict, List, Union

from playwright._browser import Browser
from playwright._browser_context import BrowserContext
from playwright._connection import ChannelOwner, from_channel
from playwright._helper import ColorScheme, Env, locals_to_params, not_installed_error
from playwright._network import serialize_headers
from playwright._types import (
    Credentials,
    Geolocation,
    IntSize,
    ProxyServer,
    RecordHarOptions,
    RecordVideoOptions,
)

if sys.version_info >= (3, 8):  # pragma: no cover
    from typing import Literal
else:  # pragma: no cover
    from typing_extensions import Literal


class BrowserType(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)

    @property
    def name(self) -> str:
        return self._initializer["name"]

    @property
    def executablePath(self) -> str:
        return self._initializer["executablePath"]

    async def launch(
        self,
        executablePath: Union[str, Path] = None,
        args: List[str] = None,
        ignoreDefaultArgs: Union[bool, List[str]] = None,
        handleSIGINT: bool = None,
        handleSIGTERM: bool = None,
        handleSIGHUP: bool = None,
        timeout: int = None,
        env: Env = None,
        headless: bool = None,
        devtools: bool = None,
        proxy: ProxyServer = None,
        downloadsPath: Union[str, Path] = None,
        slowMo: int = None,
        chromiumSandbox: bool = None,
        firefoxUserPrefs: Dict[str, Union[str, int, bool]] = None,
    ) -> Browser:
        params = locals_to_params(locals())
        normalize_launch_params(params)
        try:
            return from_channel(await self._channel.send("launch", params))
        except Exception as e:
            if f"{self.name}-" in str(e):
                raise not_installed_error(f'"{self.name}" browser was not found.')
            raise e

    async def launchPersistentContext(
        self,
        userDataDir: Union[str, Path],
        executablePath: Union[str, Path] = None,
        args: List[str] = None,
        ignoreDefaultArgs: Union[bool, List[str]] = None,
        handleSIGINT: bool = None,
        handleSIGTERM: bool = None,
        handleSIGHUP: bool = None,
        timeout: int = None,
        env: Env = None,
        headless: bool = None,
        devtools: bool = None,
        proxy: ProxyServer = None,
        downloadsPath: Union[str, Path] = None,
        slowMo: int = None,
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
        chromiumSandbox: bool = None,
        videosPath: str = None,
        videoSize: IntSize = None,
        recordHar: RecordHarOptions = None,
        recordVideo: RecordVideoOptions = None,
    ) -> BrowserContext:
        userDataDir = str(Path(userDataDir))
        params = locals_to_params(locals())
        if viewport == 0:
            del params["viewport"]
            params["noDefaultViewport"] = True
        if extraHTTPHeaders:
            params["extraHTTPHeaders"] = serialize_headers(extraHTTPHeaders)
        if not recordVideo and videosPath:
            params["recordVideo"] = {"dir": videosPath}
            if videoSize:
                params["recordVideo"]["size"] = videoSize
        normalize_launch_params(params)
        try:
            context = from_channel(
                await self._channel.send("launchPersistentContext", params)
            )
            context._options = params
            return context
        except Exception as e:
            if f"{self.name}-" in str(e):
                raise not_installed_error(f'"{self.name}" browser was not found.')
            raise e


def normalize_launch_params(params: Dict) -> None:
    if "env" in params:
        params["env"] = {name: str(value) for [name, value] in params["env"].items()}
    if "ignoreDefaultArgs" in params:
        if params["ignoreDefaultArgs"] is True:
            params["ignoreAllDefaultArgs"] = True
            del params["ignoreDefaultArgs"]
    if "executablePath" in params:
        params["executablePath"] = str(Path(params["executablePath"]))
    if "downloadsPath" in params:
        params["downloadsPath"] = str(Path(params["downloadsPath"]))
