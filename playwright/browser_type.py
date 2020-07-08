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

from playwright.connection import Channel, ChannelOwner, ConnectionScope, from_channel
from playwright.browser import Browser
from playwright.browser_context import BrowserContext
from playwright.helper import locals_to_params
from typing import Awaitable, Dict, List

class BrowserType(ChannelOwner):

  def __init__(self, scope: ConnectionScope, guid: str, initializer: Dict) -> None:
    super().__init__(scope, guid, initializer)

  @property
  def name(self) -> str:
    return self._initializer['name']

  @property
  def executablePath(self) -> str:
    return self._initializer['executablePath']

  async def launch(self,
      executablePath: str = None,
      args: List[str] = None,
      ignoreDefaultArgs: List[str] = None,
      handleSIGINT: bool = None,
      handleSIGTERM: bool = None,
      handleSIGHUP: bool = None,
      timeout: int = None,
      env: Dict = None,
      headless: bool = None,
      devtools: bool = None,
      proxy: Dict = None,
      downloadsPath: str = None,
      slowMo: int = None) -> Browser:
    return from_channel(await self._channel.send('launch', locals_to_params(locals())))

  async def launchServer(self,
      executablePath: str = None,
      args: List[str] = None,
      ignoreDefaultArgs: List[str] = None,
      handleSIGINT: bool = None,
      handleSIGTERM: bool = None,
      handleSIGHUP: bool = None,
      timeout: int = None,
      env: Dict = None,
      headless: bool = None,
      devtools: bool = None,
      proxy: Dict = None,
      downloadsPath: str = None,
      port: int = None) -> Browser:
    return from_channel(await self._channel.send('launchServer', locals_to_params(locals())))

  async def launchPersistentContext(self,
      userDataDir: str,
      executablePath: str = None,
      args: List[str] = None,
      ignoreDefaultArgs: List[str] = None,
      handleSIGINT: bool = None,
      handleSIGTERM: bool = None,
      handleSIGHUP: bool = None,
      timeout: int = None,
      env: Dict = None,
      headless: bool = None,
      devtools: bool = None,
      proxy: Dict = None,
      downloadsPath: str = None,
      slowMo: int = None,
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
      colorScheme: str = None, #Literal['dark', 'light', 'no-preference'] = None,
      acceptDownloads: bool = None) -> BrowserContext:
    return from_channel(await self._channel.send('launchPersistentContext', locals_to_params(locals())))

  async def connect(
      self,
      wsEndpoint: str = None,
      slowMo: int = None,
      timeout: int = None) -> Browser:
    return from_channel(await self._channel.send('connect', locals_to_params(locals())))
