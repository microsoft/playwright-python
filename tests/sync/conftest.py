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
from typing import Any, Callable, Dict, Generator, List, Tuple

import pytest
from greenlet import greenlet

from playwright._impl._driver import compute_driver_executable
from playwright.sync_api import (
    Browser,
    BrowserContext,
    BrowserType,
    Error,
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
def browser_factory(
    launch_arguments: Dict, browser_type: BrowserType
) -> Generator[Callable[..., Browser], None, None]:
    browsers: List[Browser] = []

    def launch(**kwargs: Any) -> Browser:
        browser = browser_type.launch(**launch_arguments, **kwargs)
        browsers.append(browser)
        return browser

    yield launch
    for browser in browsers:
        browser.close()


@pytest.fixture(scope="session")
def browser(
    browser_type: BrowserType, launch_arguments: Dict
) -> Generator[Browser, None, None]:
    browser = browser_type.launch(**launch_arguments)
    yield browser
    browser.close()


@pytest.fixture(scope="session")
def browser_version(browser: Browser) -> str:
    return browser.version


@pytest.fixture(scope="session")
def browser_major_version(browser_version: str) -> int:
    return int(browser_version.split(".")[0])


@pytest.fixture
def context_factory(
    browser: Browser,
) -> Generator[Callable[..., BrowserContext], None, None]:
    contexts: List[BrowserContext] = []

    def launch(**kwargs: Any) -> BrowserContext:
        context = browser.new_context(**kwargs)
        contexts.append(context)
        return context

    yield launch
    for context in contexts:
        context.close()


@pytest.fixture
def launch_persistent(
    browser_type: BrowserType,
    launch_arguments: Dict,
    create_user_data_dir: Callable[[], Path],
) -> Generator[Callable[..., Tuple[BrowserContext, Page]], None, None]:
    """Launches one persistent context and returns it with its first page.

    Port of launchPersistent in tests/config/browserTest.ts.
    """
    contexts: List[BrowserContext] = []

    def launch(**kwargs: Any) -> Tuple[BrowserContext, Page]:
        if contexts:
            raise Exception("can only launch one persistent context")
        context = browser_type.launch_persistent_context(
            create_user_data_dir(), **{**launch_arguments, **kwargs}
        )
        contexts.append(context)
        return context, context.pages[0]

    yield launch
    for context in contexts:
        context.close()


@pytest.fixture
def context(
    context_factory: Callable[..., BrowserContext],
) -> Generator[BrowserContext, None, None]:
    context = context_factory()
    yield context
    context.close()


@pytest.fixture
def page(context: BrowserContext) -> Page:
    return context.new_page()


@pytest.fixture(autouse=True)
def close_leaked_contexts(
    request: pytest.FixtureRequest,
) -> Generator[None, None, None]:
    """Closes the contexts that a test left open in the shared browser.

    Some tests count browser.contexts; a context that an earlier test did not close
    would make them depend on the test order.
    """
    browser = (
        request.getfixturevalue("browser")
        if "browser" in request.fixturenames
        else None
    )
    yield
    if browser is None:
        return
    for context in browser.contexts:
        try:
            context.close()
        except Error:
            pass


@pytest.fixture(scope="session")
def selectors(playwright: Playwright) -> Selectors:
    return playwright.selectors


@pytest.fixture(scope="session")
def sync_gather(playwright: Playwright) -> Generator[Callable, None, None]:
    def _sync_gather_impl(*actions: Callable) -> List[Any]:
        g_self = greenlet.getcurrent()
        # Keyed by position: the same callable may be passed more than once.
        results: Dict[int, Any] = {}
        exceptions: List[Exception] = []

        def action_wrapper(index: int, action: Callable) -> Callable:
            def body() -> Any:
                try:
                    results[index] = action()
                except Exception as e:
                    results[index] = e
                    exceptions.append(e)
                g_self.switch()

            return body

        async def task() -> None:
            for index, action in enumerate(actions):
                g = greenlet(action_wrapper(index, action))
                g.switch()

        asyncio.create_task(task())

        while len(results) < len(actions):
            playwright._dispatcher_fiber.switch()

        if exceptions:
            raise exceptions[0]

        return [results[index] for index in range(len(actions))]

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
        return self.page.get_by_role("listbox", name="Stack trace").get_by_role(
            "option"
        )

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
