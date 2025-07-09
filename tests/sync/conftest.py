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
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List

import pytest
from greenlet import greenlet

from playwright._impl._driver import compute_driver_executable
from playwright.sync_api import (
    Browser,
    BrowserContext,
    BrowserType,
    FrameLocator,
    Locator,
    Page,
    Playwright,
    Selectors,
    sync_playwright,
)
from tests.server import HTTPServer

from .utils import Utils
from .utils import utils as utils_object


@pytest.fixture
def utils() -> Generator[Utils, None, None]:
    yield utils_object


@pytest.fixture(scope="session")
def playwright() -> Generator[Playwright, None, None]:
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser_type(
    playwright: Playwright, browser_name: str
) -> Generator[BrowserType, None, None]:
    browser_type = None
    if browser_name == "chromium":
        browser_type = playwright.chromium
    elif browser_name == "firefox":
        browser_type = playwright.firefox
    elif browser_name == "webkit":
        browser_type = playwright.webkit
    assert browser_type, f"Unkown browser name '{browser_name}'"
    yield browser_type


@pytest.fixture(scope="session")
def browser(
    browser_type: BrowserType, launch_arguments: Dict
) -> Generator[Browser, None, None]:
    browser = browser_type.launch(**launch_arguments)
    yield browser
    browser.close()


@pytest.fixture
def context(browser: Browser) -> Generator[BrowserContext, None, None]:
    context = browser.new_context()
    yield context
    context.close()


@pytest.fixture
def page(context: BrowserContext) -> Generator[Page, None, None]:
    page = context.new_page()
    yield page
    page.close()


@pytest.fixture(scope="session")
def selectors(playwright: Playwright) -> Selectors:
    return playwright.selectors


@pytest.fixture(scope="session")
def sync_gather(playwright: Playwright) -> Generator[Callable, None, None]:
    def _sync_gather_impl(*actions: Callable) -> List[Any]:
        g_self = greenlet.getcurrent()
        results: Dict[Callable, Any] = {}
        exceptions: List[Exception] = []

        def action_wrapper(action: Callable) -> Callable:
            def body() -> Any:
                try:
                    results[action] = action()
                except Exception as e:
                    results[action] = e
                    exceptions.append(e)
                g_self.switch()

            return body

        async def task() -> None:
            for action in actions:
                g = greenlet(action_wrapper(action))
                g.switch()

        asyncio.create_task(task())

        while len(results) < len(actions):
            playwright._dispatcher_fiber.switch()

        if exceptions:
            raise exceptions[0]

        return list(map(lambda action: results[action], actions))

    yield _sync_gather_impl


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
        return self.page.get_by_role("list", name="Stack trace").get_by_role("listitem")

    def select_action(self, title: str, ordinal: int = 0) -> None:
        self.page.locator(".action-title", has_text=title).nth(ordinal).click()

    def select_snapshot(self, name: str) -> None:
        self.page.click(f'.snapshot-tab .tabbed-pane-tab-label:has-text("{name}")')

    def snapshot_frame(
        self, action_name: str, ordinal: int = 0, has_subframe: bool = False
    ) -> FrameLocator:
        self.select_action(action_name, ordinal)
        expected_frames = 4 if has_subframe else 3
        while len(self.page.frames) < expected_frames:
            self.page.wait_for_event("frameattached")
        return self.page.frame_locator("iframe.snapshot-visible[name=snapshot]")

    def show_source_tab(self) -> None:
        self.page.click("text='Source'")

    def expand_action(self, title: str, ordinal: int = 0) -> None:
        self.actions_tree.locator(".tree-view-entry", has_text=title).nth(
            ordinal
        ).locator(".codicon-chevron-right").click()


@pytest.fixture
def show_trace_viewer(browser: Browser) -> Generator[Callable, None, None]:
    """Fixture that provides a function to show trace viewer for a trace file."""

    @contextmanager
    def _show_trace_viewer(
        trace_path: Path,
    ) -> Generator[TraceViewerPage, None, None]:
        trace_viewer_path = (
            Path(compute_driver_executable()[0]) / "../package/lib/vite/traceViewer"
        ).resolve()

        server = HTTPServer()
        server.start(trace_viewer_path)
        server.set_route("/trace.zip", lambda request: request.serve_file(trace_path))

        page = browser.new_page()

        try:
            page.goto(f"{server.PREFIX}/index.html?trace={server.PREFIX}/trace.zip")
            yield TraceViewerPage(page)
        finally:
            page.close()
            server.stop()

    yield _show_trace_viewer
