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

from typing import Dict

from playwright.browser_type import BrowserType
from playwright.connection import ChannelOwner, ConnectionScope, from_channel
from playwright.helper import Devices
from playwright.selectors import Selectors


class Playwright(ChannelOwner):
    def __init__(self, scope: ConnectionScope, guid: str, initializer: Dict) -> None:
        super().__init__(scope, guid, initializer)
        self._chromium = from_channel(initializer["chromium"])
        self._firefox = from_channel(initializer["firefox"])
        self._webkit = from_channel(initializer["webkit"])
        self._selectors = from_channel(initializer["selectors"])
        self._devices = {
            device["name"]: device["descriptor"]
            for device in initializer["deviceDescriptors"]
        }

    @property
    def chromium(self) -> BrowserType:
        return self._chromium

    @property
    def firefox(self) -> BrowserType:
        return self._firefox

    @property
    def webkit(self) -> BrowserType:
        return self._webkit

    @property
    def selectors(self) -> Selectors:
        return self._selectors

    @property
    def devices(self) -> Devices:
        return self._devices
