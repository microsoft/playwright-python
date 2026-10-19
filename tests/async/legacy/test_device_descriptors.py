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

import pytest

from playwright.async_api import Playwright


@pytest.mark.only_browser("chromium")
async def test_should_work(playwright: Playwright, launch_arguments: Dict) -> None:
    device_descriptor = playwright.devices["Pixel 2"]
    device_type = device_descriptor["default_browser_type"]
    browser = await playwright[device_type].launch(**launch_arguments)
    context = await browser.new_context(
        **device_descriptor,
    )
    page = await context.new_page()
    assert device_descriptor["default_browser_type"] == "chromium"
    assert browser.browser_type.name == "chromium"

    assert "Pixel 2" in device_descriptor["user_agent"]
    assert "Pixel 2" in await page.evaluate("navigator.userAgent")

    assert device_descriptor["device_scale_factor"] > 2
    assert await page.evaluate("window.devicePixelRatio") > 2

    assert device_descriptor["viewport"]["height"] > 700
    assert device_descriptor["viewport"]["height"] < 800
    inner_height = await page.evaluate("window.screen.availHeight")
    assert inner_height > 700
    assert inner_height < 800

    assert device_descriptor["viewport"]["width"] > 400
    assert device_descriptor["viewport"]["width"] < 500
    inner_width = await page.evaluate("window.screen.availWidth")
    assert inner_width > 400
    assert inner_width < 500

    assert device_descriptor["has_touch"]
    assert device_descriptor["is_mobile"]

    await browser.close()
