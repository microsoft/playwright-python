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

import pytest


@pytest.mark.only_browser("chromium")
async def test_issue_189(browser_type):
    browser = await browser_type.launch(ignore_default_args=["--mute-audio"])
    page = await browser.new_page()
    assert await page.evaluate("1 + 1") == 2
    await browser.close()


@pytest.mark.only_browser("chromium")
async def test_issue_195(playwright, browser):
    iphone_11 = playwright.devices["iPhone 11"]
    context = await browser.new_context(**iphone_11.__dict__)
    await context.close()
