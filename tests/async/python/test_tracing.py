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


"""Python only: tests of behaviors that no upstream test covers."""

import asyncio
import re
from pathlib import Path
from typing import AsyncContextManager, Callable

from playwright.async_api import BrowserContext, Page, Response, expect
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


async def test_should_collect_sources(
    context: BrowserContext,
    page: Page,
    server: Server,
    tmp_path: Path,
    show_trace_viewer: Callable[[Path], AsyncContextManager[TraceViewerPage]],
) -> None:
    await context.tracing.start(sources=True)
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<button>Click</button>")

    async def my_method_outer() -> None:
        async def my_method_inner() -> None:
            await page.get_by_text("Click").click()

        await my_method_inner()

    await my_method_outer()
    path = tmp_path / "trace.zip"
    await context.tracing.stop(path=path)

    async with show_trace_viewer(path) as trace_viewer:
        await expect(trace_viewer.action_titles).to_have_text(
            [
                re.compile(r"Navigate.*/empty\.html"),
                re.compile(r"Set content"),
                re.compile(r"Click"),
            ]
        )
        await trace_viewer.show_source_tab()
        # Check that stack frames are shown (they might be anonymous in Python)
        await expect(trace_viewer.stack_frames).to_contain_text(
            [
                re.compile(r"my_method_inner"),
                re.compile(r"my_method_outer"),
                re.compile(r"test_should_collect_sources"),
            ]
        )

        await trace_viewer.select_action("Set content")
        # Check that the source file is shown
        await expect(
            trace_viewer.page.locator(".source-tab-file-name")
        ).to_have_attribute("title", re.compile(r".*test_.*\.py"))
        await expect(trace_viewer.page.locator(".source-line-running")).to_contain_text(
            'page.set_content("<button>Click</button>")'
        )


async def test_should_correctly_determine_sync_apiname(
    context: BrowserContext,
    page: Page,
    server: Server,
    tmp_path: Path,
    show_trace_viewer: Callable,
) -> None:
    await context.tracing.start(screenshots=True, snapshots=True)

    received_response: "asyncio.Future[None]" = asyncio.Future()

    async def _handle_response(response: Response) -> None:
        await response.request.all_headers()
        await response.text()
        received_response.set_result(None)

    page.once("response", _handle_response)
    await page.goto(server.PREFIX + "/grid.html")
    await received_response
    await page.close()
    trace_file_path = tmp_path / "trace.zip"
    await context.tracing.stop(path=trace_file_path)

    async with show_trace_viewer(trace_file_path) as trace_viewer:
        await expect(trace_viewer.action_titles).to_have_text(
            [
                re.compile(r"Navigate.*/grid\.html"),
                re.compile(r"Close"),
            ]
        )


async def test_should_show_tracing_group_in_action_list(
    context: BrowserContext,
    tmp_path: Path,
    show_trace_viewer: Callable[[Path], AsyncContextManager[TraceViewerPage]],
) -> None:
    await context.tracing.start()
    page = await context.new_page()

    await context.tracing.group("outer group")
    await page.goto("data:text/html,<!DOCTYPE html><body><div>Hello world</div></body>")
    await context.tracing.group("inner group 1")
    await page.locator("body").click()
    await context.tracing.group_end()
    await context.tracing.group("inner group 2")
    await page.get_by_text("Hello").is_visible()
    await context.tracing.group_end()
    await context.tracing.group_end()

    trace_path = tmp_path / "trace.zip"
    await context.tracing.stop(path=trace_path)

    async with show_trace_viewer(trace_path) as trace_viewer:
        await trace_viewer.expand_action("inner group 1")
        await expect(trace_viewer.action_titles).to_have_text(
            [
                re.compile(r"Create page"),
                re.compile(r"outer group"),
                re.compile(r"Navigate.*data:"),
                re.compile(r"inner group 1"),
                re.compile(r"Click"),
                re.compile(r"inner group 2"),
            ]
        )
