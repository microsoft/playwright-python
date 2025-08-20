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
import re
from pathlib import Path
from typing import AsyncContextManager, Callable

from playwright.async_api import (
    Browser,
    BrowserContext,
    BrowserType,
    Page,
    Response,
    expect,
)
from tests.server import Server

from .conftest import TraceViewerPage


async def test_browser_context_output_trace(
    browser: Browser, server: Server, tmp_path: Path
) -> None:
    context = await browser.new_context()
    await context.tracing.start(screenshots=True, snapshots=True)
    page = await context.new_page()
    await page.goto(server.PREFIX + "/grid.html")
    await context.tracing.stop(path=tmp_path / "trace.zip")
    assert Path(tmp_path / "trace.zip").exists()


async def test_start_stop(browser: Browser) -> None:
    context = await browser.new_context()
    await context.tracing.start()
    await context.tracing.stop()
    await context.close()


async def test_browser_context_should_not_throw_when_stopping_without_start_but_not_exporting(
    context: BrowserContext,
) -> None:
    await context.tracing.stop()


async def test_browser_context_output_trace_chunk(
    browser: Browser, server: Server, tmp_path: Path
) -> None:
    context = await browser.new_context()
    await context.tracing.start(screenshots=True, snapshots=True)
    page = await context.new_page()
    await page.goto(server.PREFIX + "/grid.html")
    button = page.locator(".box").first

    await context.tracing.start_chunk(title="foo")
    await button.click()
    await context.tracing.stop_chunk(path=tmp_path / "trace1.zip")
    assert Path(tmp_path / "trace1.zip").exists()

    await context.tracing.start_chunk(title="foo")
    await button.click()
    await context.tracing.stop_chunk(path=tmp_path / "trace2.zip")
    assert Path(tmp_path / "trace2.zip").exists()


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
                re.compile(r'Navigate to "/empty\.html"'),
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


async def test_should_collect_trace_with_resources_but_no_js(
    context: BrowserContext,
    page: Page,
    server: Server,
    tmp_path: Path,
    show_trace_viewer: Callable[[Path], AsyncContextManager[TraceViewerPage]],
) -> None:
    await context.tracing.start(screenshots=True, snapshots=True)
    await page.goto(server.PREFIX + "/frames/frame.html")
    await page.set_content("<button>Click</button>")
    await page.click('"Click"')
    await page.mouse.move(20, 20)
    await page.mouse.dblclick(30, 30)
    await page.request.get(server.EMPTY_PAGE)
    await page.keyboard.insert_text("abc")
    await page.wait_for_timeout(2000)  # Give it some time to produce screenshots.
    await page.route("**/empty.html", lambda route: route.continue_())
    await page.goto(server.EMPTY_PAGE)
    await page.goto(server.PREFIX + "/one-style.html")
    await page.close()
    trace_file_path = tmp_path / "trace.zip"
    await context.tracing.stop(path=trace_file_path)

    async with show_trace_viewer(trace_file_path) as trace_viewer:
        await expect(trace_viewer.action_titles).to_have_text(
            [
                re.compile(r'Navigate to "/frames/frame\.html"'),
                re.compile(r"Set content"),
                re.compile(r"Click"),
                re.compile(r"Mouse move"),
                re.compile(r"Double click"),
                re.compile(r"GET \"/empty\.html\""),
                re.compile(r'Insert "abc"'),
                re.compile(r"Wait for timeout"),
                re.compile(r'Navigate to "/empty\.html"'),
                re.compile(r'Navigate to "/one-style\.html"'),
                re.compile(r"Close"),
            ]
        )

        await trace_viewer.select_action("Set content")
        await expect(
            trace_viewer.page.locator(".browser-frame-address-bar")
        ).to_have_text(server.PREFIX + "/frames/frame.html")
        frame = await trace_viewer.snapshot_frame("Set content", 0, False)
        await expect(frame.locator("button")).to_have_text("Click")


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
                re.compile(r'Navigate to "/grid\.html"'),
                re.compile(r"Close"),
            ]
        )


async def test_should_collect_two_traces(
    context: BrowserContext,
    page: Page,
    server: Server,
    tmp_path: Path,
    show_trace_viewer: Callable[[Path], AsyncContextManager[TraceViewerPage]],
) -> None:
    await context.tracing.start(screenshots=True, snapshots=True)
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<button>Click</button>")
    await page.click('"Click"')
    tracing1_path = tmp_path / "trace1.zip"
    await context.tracing.stop(path=tracing1_path)

    await context.tracing.start(screenshots=True, snapshots=True)
    await page.dblclick('"Click"')
    await page.close()
    tracing2_path = tmp_path / "trace2.zip"
    await context.tracing.stop(path=tracing2_path)

    async with show_trace_viewer(tracing1_path) as trace_viewer:
        await expect(trace_viewer.action_titles).to_have_text(
            [
                re.compile(r'Navigate to "/empty\.html"'),
                re.compile(r"Set content"),
                re.compile(r"Click"),
            ]
        )

    async with show_trace_viewer(tracing2_path) as trace_viewer:
        await expect(trace_viewer.action_titles).to_have_text(
            [
                re.compile(r"Double click"),
                re.compile(r"Close"),
            ]
        )


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
                re.compile(r'Navigate to "/empty\.html"'),
                re.compile(r"Set content"),
                re.compile(r'Wait for event "page\.expect_event\(console\)"'),
                re.compile(r"Evaluate"),
                re.compile(r"Click"),
                re.compile(r'Wait for event "page\.expect_event\(popup\)"'),
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
                re.compile(r'Navigate to "/empty\.html"'),
                re.compile(r'Wait for event "frame\.wait_for_load_state"'),
                re.compile(r'Wait for event "frame\.wait_for_load_state"'),
            ]
        )


async def test_should_respect_traces_dir_and_name(
    browser_type: BrowserType,
    server: Server,
    tmp_path: Path,
    launch_arguments: dict,
    show_trace_viewer: Callable[[Path], AsyncContextManager[TraceViewerPage]],
) -> None:
    traces_dir = tmp_path / "traces"
    browser = await browser_type.launch(traces_dir=traces_dir, **launch_arguments)
    context = await browser.new_context()
    page = await context.new_page()

    await context.tracing.start(name="name1", snapshots=True)
    await page.goto(server.PREFIX + "/one-style.html")
    await context.tracing.stop_chunk(path=tmp_path / "trace1.zip")
    assert (traces_dir / "name1.trace").exists()
    assert (traces_dir / "name1.network").exists()

    await context.tracing.start_chunk(name="name2")
    await page.goto(server.PREFIX + "/har.html")
    await context.tracing.stop(path=tmp_path / "trace2.zip")
    assert (traces_dir / "name2.trace").exists()
    assert (traces_dir / "name2.network").exists()

    await browser.close()

    async with show_trace_viewer(tmp_path / "trace1.zip") as trace_viewer:
        await expect(trace_viewer.action_titles).to_have_text(
            [
                re.compile('Navigate to "/one-style\\.html"'),
            ]
        )
        frame = await trace_viewer.snapshot_frame(
            'Navigate to "/one-style.html"', 0, False
        )
        await expect(frame.locator("body")).to_have_css(
            "background-color", "rgb(255, 192, 203)"
        )
        await expect(frame.locator("body")).to_have_text("hello, world!")

    async with show_trace_viewer(tmp_path / "trace2.zip") as trace_viewer:
        await expect(trace_viewer.action_titles).to_have_text(
            [
                re.compile(r'Navigate to "/har\.html"'),
            ]
        )
        frame = await trace_viewer.snapshot_frame('Navigate to "/har.html"', 0, False)
        await expect(frame.locator("body")).to_have_css(
            "background-color", "rgb(255, 192, 203)"
        )
        await expect(frame.locator("body")).to_have_text("hello, world!")


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
                re.compile(r"Navigate to \"data:\""),
                re.compile(r"inner group 1"),
                re.compile(r"Click"),
                re.compile(r"inner group 2"),
            ]
        )
