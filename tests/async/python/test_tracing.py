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


"""Python only: tests of v2 (playwright/_impl_v2) that no upstream test covers.

The v1 tests of the same behaviors are in tests/async/legacy, marked @only_v1.
"""

import re
from pathlib import Path
from typing import AsyncContextManager, Callable

from playwright.async_api import BrowserContext, Page, expect
from tests.server import Server

from ..conftest import TraceViewerPage


async def test_should_work_with_playwright_context_managers(
    context: BrowserContext,
    page: Page,
    server: Server,
    tmp_path: Path,
    show_trace_viewer: Callable[[Path], AsyncContextManager[TraceViewerPage]],
) -> None:
    await context.tracing.start(screenshots=True, snapshots=True)
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<button>Click</button>")
    async with page.expect_console_message() as message_info:
        await page.evaluate('() => console.log("hello")')
        await page.click('"Click"')
    assert (await message_info.value).text == "hello"

    async with page.expect_popup():
        await page.evaluate("window._popup = window.open(document.location.href)")
    trace_file_path = tmp_path / "trace.zip"
    await context.tracing.stop(path=trace_file_path)

    async with show_trace_viewer(trace_file_path) as trace_viewer:
        await expect(trace_viewer.action_titles).to_have_text(
            [
                re.compile(r"Navigate.*/empty\.html"),
                re.compile(r"Set content"),
                re.compile(r'Wait for event "console"'),
                re.compile(r"Evaluate"),
                re.compile(r"Click"),
                re.compile(r'Wait for event "popup"'),
                re.compile(r"Evaluate"),
            ]
        )


async def test_should_display_wait_for_load_state_even_if_did_not_wait_for_it(
    context: BrowserContext,
    page: Page,
    server: Server,
    tmp_path: Path,
    show_trace_viewer: Callable[[Path], AsyncContextManager[TraceViewerPage]],
) -> None:
    await context.tracing.start(screenshots=True, snapshots=True)

    await page.goto(server.EMPTY_PAGE)
    await page.wait_for_load_state("load")
    await page.wait_for_load_state("load")

    trace_file_path = tmp_path / "trace.zip"
    await context.tracing.stop(path=trace_file_path)

    async with show_trace_viewer(trace_file_path) as trace_viewer:
        await expect(trace_viewer.action_titles).to_have_text(
            [
                re.compile(r"Navigate.*/empty\.html"),
                re.compile(r"Wait for load state"),
                re.compile(r"Wait for load state"),
            ]
        )
