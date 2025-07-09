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
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, Generator

import pytest

from playwright._impl._driver import compute_driver_executable
from playwright.async_api import (
    Browser,
    BrowserContext,
    BrowserType,
    FrameLocator,
    Locator,
    Page,
    Playwright,
    Selectors,
    async_playwright,
)
from tests.server import HTTPServer

from .utils import Utils
from .utils import utils as utils_object


@pytest.fixture
def utils() -> Generator[Utils, None, None]:
    yield utils_object


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


class TraceViewerPage:
    def __init__(self, page: Page):
        self.page = page

    @property
    def actions_tree(self) -> Locator:
        return self.page.get_by_test_id("actions-tree")

    @property
    def action_titles(self) -> Locator:
        return self.page.locator(".action-title")

    @property
    def stack_frames(self) -> Locator:
        return self.page.get_by_role("list", name="Stack Trace").get_by_role("listitem")

    async def select_action(self, title: str, ordinal: int = 0) -> None:
        await self.page.locator(".action-title", has_text=title).nth(ordinal).click()

    async def select_snapshot(self, name: str) -> None:
        await self.page.click(
            f'.snapshot-tab .tabbed-pane-tab-label:has-text("{name}")'
        )

    async def snapshot_frame(
        self, action_name: str, ordinal: int = 0, has_subframe: bool = False
    ) -> FrameLocator:
        await self.select_action(action_name, ordinal)
        expected_frames = 4 if has_subframe else 3
        while len(self.page.frames) < expected_frames:
            await self.page.wait_for_event("frameattached")
        return self.page.frame_locator("iframe.snapshot-visible[name=snapshot]")

    async def show_source_tab(self) -> None:
        await self.page.click("text='Source'")

    async def expand_action(self, title: str, ordinal: int = 0) -> None:
        await self.actions_tree.locator(".tree-view-entry", has_text=title).nth(
            ordinal
        ).locator(".codicon-chevron-right").click()


@pytest.fixture
async def show_trace_viewer(browser: Browser) -> AsyncGenerator[Callable, None]:
    """Fixture that provides a function to show trace viewer for a trace file."""

    @asynccontextmanager
    async def _show_trace_viewer(
        trace_path: Path,
    ) -> AsyncGenerator[TraceViewerPage, None]:
        trace_viewer_path = (
            Path(compute_driver_executable()[0]) / "../package/lib/vite/traceViewer"
        ).resolve()

        server = HTTPServer()
        server.start(trace_viewer_path)
        server.set_route("/trace.zip", lambda request: request.serve_file(trace_path))

        page = await browser.new_page()

        try:
            await page.goto(
                f"{server.PREFIX}/index.html?trace={server.PREFIX}/trace.zip"
            )
            yield TraceViewerPage(page)
        finally:
            await page.close()
            server.stop()

    yield _show_trace_viewer
