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

from playwright.async_api import async_playwright

from .utils import utils as utils_object


@pytest.fixture
def utils():
    yield utils_object


# Will mark all the tests as async
def pytest_collection_modifyitems(items):
    for item in items:
        item.add_marker(pytest.mark.asyncio)


@pytest.fixture(scope="session")
async def playwright():
    async with async_playwright() as playwright_object:
        yield playwright_object


@pytest.fixture(scope="session")
def browser_type(playwright, browser_name: str):
    if browser_name == "chromium":
        return playwright.chromium
    if browser_name == "firefox":
        return playwright.firefox
    if browser_name == "webkit":
        return playwright.webkit


@pytest.fixture(scope="session")
async def browser_factory(launch_arguments, browser_type):
    browsers = []

    async def launch(**kwargs):
        browser = await browser_type.launch(**launch_arguments, **kwargs)
        browsers.append(browser)
        return browser

    yield launch
    for browser in browsers:
        await browser.close()


@pytest.fixture(scope="session")
async def browser(browser_factory):
    browser = await browser_factory()
    yield browser
    await browser.close()


@pytest.fixture
async def context_factory(browser):
    contexts = []

    async def launch(**kwargs):
        context = await browser.new_context(**kwargs)
        contexts.append(context)
        return context

    yield launch
    for context in contexts:
        await context.close()


@pytest.fixture
async def context(context_factory):
    context = await context_factory()
    yield context
    await context.close()


@pytest.fixture
async def page(context):
    page = await context.new_page()
    yield page
    await page.close()


@pytest.fixture(scope="session")
def selectors(playwright):
    return playwright.selectors
