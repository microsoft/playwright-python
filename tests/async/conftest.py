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

import asyncio
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, Generator, List

import pytest
from pytest_asyncio import is_async_test

from playwright.async_api import (
    Browser,
    BrowserContext,
    BrowserType,
    Page,
    Playwright,
    Selectors,
    async_playwright,
)

from .utils import Utils
from .utils import utils as utils_object


@pytest.fixture
def utils() -> Generator[Utils, None, None]:
    yield utils_object


# Will mark all the tests as async
def pytest_collection_modifyitems(items: List[pytest.Item]) -> None:
    pytest_asyncio_tests = (item for item in items if is_async_test(item))
    session_scope_marker = pytest.mark.asyncio(loop_scope="session")
    for async_test in pytest_asyncio_tests:
        async_test.add_marker(session_scope_marker, append=False)


@pytest.fixture(scope="session")
async def playwright() -> AsyncGenerator[Playwright, None]:
    async with async_playwright() as playwright_object:
        yield playwright_object


@pytest.fixture(scope="session")
def browser_type(playwright: Playwright, browser_name: str) -> BrowserType:
    if browser_name == "chromium":
        return playwright.chromium
    if browser_name == "firefox":
        return playwright.firefox
    if browser_name == "webkit":
        return playwright.webkit
    raise Exception(f"Invalid browser_name: {browser_name}")


@pytest.fixture(scope="session")
async def browser_factory(
    launch_arguments: Dict, browser_type: BrowserType
) -> AsyncGenerator[Callable[..., Awaitable[Browser]], None]:
    browsers = []

    async def launch(**kwargs: Any) -> Browser:
        browser = await browser_type.launch(**launch_arguments, **kwargs)
        browsers.append(browser)
        return browser

    yield launch
    for browser in browsers:
        await browser.close()


@pytest.fixture(scope="session")
async def browser(
    browser_factory: "Callable[..., asyncio.Future[Browser]]",
) -> AsyncGenerator[Browser, None]:
    browser = await browser_factory()
    yield browser
    await browser.close()


@pytest.fixture(scope="session")
def browser_version(browser: Browser) -> str:
    return browser.version


@pytest.fixture
async def context_factory(
    browser: Browser,
) -> AsyncGenerator["Callable[..., Awaitable[BrowserContext]]", None]:
    contexts = []

    async def launch(**kwargs: Any) -> BrowserContext:
        context = await browser.new_context(**kwargs)
        contexts.append(context)
        return context

    yield launch
    for context in contexts:
        await context.close()


@pytest.fixture(scope="session")
def default_same_site_cookie_value(browser_name: str, is_linux: bool) -> str:
    if browser_name == "chromium":
        return "Lax"
    if browser_name == "firefox":
        return "None"
    if browser_name == "webkit" and is_linux:
        return "Lax"
    if browser_name == "webkit" and not is_linux:
        return "None"
    raise Exception(f"Invalid browser_name: {browser_name}")


@pytest.fixture
async def context(
    context_factory: "Callable[..., asyncio.Future[BrowserContext]]",
) -> AsyncGenerator[BrowserContext, None]:
    context = await context_factory()
    yield context
    await context.close()


@pytest.fixture
async def page(context: BrowserContext) -> AsyncGenerator[Page, None]:
    page = await context.new_page()
    yield page
    await page.close()


@pytest.fixture(scope="session")
def selectors(playwright: Playwright) -> Selectors:
    return playwright.selectors
