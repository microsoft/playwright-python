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

"""Port of tests/library/launcher.spec.ts."""

import os
import re
from typing import Dict, Optional

import pytest

from playwright.async_api import BrowserType, Error, Playwright


async def test_BT_019_should_have_a_devices_object(playwright: Playwright) -> None:
    assert playwright.devices["iPhone 6"]
    assert playwright.devices["iPhone 6"]["default_browser_type"] == "webkit"


async def test_BT_021_should_throw_a_friendly_error_if_its_headed_and_there_is_no_xserver_on_linux_running(
    browser_type: BrowserType,
    launch_arguments: Dict,
    platform: str,
    browser_channel: Optional[str],
) -> None:
    if platform != "linux":
        pytest.skip()
    if browser_channel == "chromium-headless-shell":
        pytest.skip("shell is never headed")

    env = {name: value for name, value in os.environ.items() if name != "DISPLAY"}
    with pytest.raises(Error) as exc_info:
        await browser_type.launch(**{**launch_arguments, "headless": False, "env": env})
    assert re.search(
        r"Looks like you launched a headed browser without having a XServer running.",
        exc_info.value.message,
    )
    assert re.search(r"xvfb-run", exc_info.value.message)
