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

"""Port of tests/library/browser.spec.ts."""

import asyncio
import re
from typing import Dict, List

import pytest

from playwright.async_api import Browser, BrowserContext, BrowserType, Error
from tests.utils import TARGET_CLOSED_ERROR_MESSAGE


async def test_BR_001_should_return_browser_type(
    browser: Browser, browser_type: BrowserType
) -> None:
    assert browser.browser_type is browser_type


async def test_BR_002_should_create_new_page_smoke(browser: Browser) -> None:
    page1 = await browser.new_page()
    assert len(browser.contexts) == 1

    page2 = await browser.new_page()
    assert len(browser.contexts) == 2

    await page1.close()
    assert len(browser.contexts) == 1

    await page2.close()
    assert len(browser.contexts) == 0


async def test_BR_003_should_throw_upon_second_create_new_page(
    browser: Browser,
) -> None:
    page = await browser.new_page()
    with pytest.raises(Error) as exc_info:
        await page.context.new_page()
    await page.close()
    assert "Please use browser.new_context()" in exc_info.value.message


async def test_BR_004_version_should_work(browser: Browser, browser_name: str) -> None:
    version = browser.version
    if browser_name == "chromium":
        assert re.match(r"^\d+\.\d+\.\d+\.\d+$", version)
    else:
        assert re.match(r"^\d+\.\d+", version)


async def test_BR_005_should_dispatch_page_on_close_upon_browser_close_and_reject_evaluate(
    browser_type: BrowserType, launch_arguments: Dict
) -> None:
    browser = await browser_type.launch(**launch_arguments)
    page = await browser.new_page()
    closed: List[bool] = []
    page.on("close", lambda _: closed.append(True))
    promise = asyncio.create_task(page.evaluate("() => new Promise(() => {})"))
    await browser.close()
    assert closed == [True]
    with pytest.raises(Error) as exc_info:
        await promise
    assert TARGET_CLOSED_ERROR_MESSAGE in exc_info.value.message


async def test_BR_006_should_fire_context_event_on_new_context(
    browser: Browser,
) -> None:
    events: List[BrowserContext] = []
    browser.on("context", lambda ctx: events.append(ctx))
    context = await browser.new_context()
    assert events == [context]
    await context.close()
