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

import re

import pytest

from playwright.async_api import Browser, BrowserType, Error


async def test_should_create_new_page(browser: Browser) -> None:
    page1 = await browser.new_page()
    assert len(browser.contexts) == 1

    page2 = await browser.new_page()
    assert len(browser.contexts) == 2

    await page1.close()
    assert len(browser.contexts) == 1

    await page2.close()
    assert len(browser.contexts) == 0


async def test_should_throw_upon_second_create_new_page(browser: Browser) -> None:
    page = await browser.new_page()
    with pytest.raises(Error) as exc:
        await page.context.new_page()
    await page.close()
    assert "Please use browser.new_context()" in exc.value.message


async def test_version_should_work(browser: Browser, is_chromium: bool) -> None:
    version = browser.version
    if is_chromium:
        assert re.match(r"^\d+\.\d+\.\d+\.\d+$", version)
    else:
        assert re.match(r"^\d+\.\d+", version)


async def test_should_return_browser_type(
    browser: Browser, browser_type: BrowserType
) -> None:
    assert browser.browser_type is browser_type
