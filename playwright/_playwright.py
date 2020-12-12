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

from playwright._browser_type import BrowserType
from playwright._connection import ChannelOwner, from_channel
from playwright._selectors import Selectors
from playwright._types import DeviceDescriptor


class Playwright(ChannelOwner):
    chromium: BrowserType
    firefox: BrowserType
    webkit: BrowserType
    selectors: Selectors
    devices: Dict[str, DeviceDescriptor]

    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self.chromium = from_channel(initializer["chromium"])
        self.firefox = from_channel(initializer["firefox"])
        self.webkit = from_channel(initializer["webkit"])
        self.selectors = from_channel(initializer["selectors"])
        self.devices = {
            device["name"]: device["descriptor"]
            for device in initializer["deviceDescriptors"]
        }

    def stop(self) -> None:
        pass
