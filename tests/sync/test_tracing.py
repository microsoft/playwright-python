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
import threading
from pathlib import Path
from typing import Callable, ContextManager

from playwright.sync_api import (
    Browser,
    BrowserContext,
    BrowserType,
    Page,
    Response,
    expect,
)
from tests.server import Server

from .conftest import TraceViewerPage


def test_browser_context_output_trace(
    browser: Browser, server: Server, tmp_path: Path
) -> None:
    context = browser.new_context()
    context.tracing.start(screenshots=True, snapshots=True)
    page = context.new_page()
    page.goto(server.PREFIX + "/grid.html")
    context.tracing.stop(path=tmp_path / "trace.zip")
    assert Path(tmp_path / "trace.zip").exists()
    context.close()


def test_start_stop(browser: Browser) -> None:
    context = browser.new_context()
    context.tracing.start()
    context.tracing.stop()
    context.close()


def test_browser_context_should_not_throw_when_stopping_without_start_but_not_exporting(
    context: BrowserContext,
) -> None:
    context.tracing.stop()


def test_browser_context_output_trace_chunk(
    browser: Browser, server: Server, tmp_path: Path
) -> None:
    context = browser.new_context()
    context.tracing.start(screenshots=True, snapshots=True)
    page = context.new_page()
    page.goto(server.PREFIX + "/grid.html")
    button = page.locator(".box").first

    context.tracing.start_chunk(title="foo")
    button.click()
    context.tracing.stop_chunk(path=tmp_path / "trace1.zip")
    assert Path(tmp_path / "trace1.zip").exists()

    context.tracing.start_chunk(title="foo")
    button.click()
    context.tracing.stop_chunk(path=tmp_path / "trace2.zip")
    assert Path(tmp_path / "trace2.zip").exists()
    context.close()


def test_should_collect_sources(
    context: BrowserContext,
    page: Page,
    server: Server,
    tmp_path: Path,
    show_trace_viewer: Callable[[Path], ContextManager[TraceViewerPage]],
) -> None:
    context.tracing.start(sources=True)
    page.goto(server.EMPTY_PAGE)
    page.set_content("<button>Click</button>")

    def my_method_outer() -> None:
        def my_method_inner() -> None:
            page.get_by_text("Click").click()

        my_method_inner()

    my_method_outer()
    path = tmp_path / "trace.zip"
    context.tracing.stop(path=path)

    with show_trace_viewer(path) as trace_viewer:
        expect(trace_viewer.action_titles).to_have_text(
            [
                re.compile(r'Navigate to "/empty\.html"'),
                re.compile(r"Set content"),
                re.compile(r"Click"),
            ]
        )
        trace_viewer.show_source_tab()
        # Check that stack frames are shown (they might be anonymous in Python)
        expect(trace_viewer.stack_frames).to_contain_text(
            [
                re.compile(r"my_method_inner"),
                re.compile(r"my_method_outer"),
                re.compile(r"test_should_collect_sources"),
            ]
        )

        trace_viewer.select_action("Set content")
        # Check that the source file is shown
        expect(trace_viewer.page.locator(".source-tab-file-name")).to_have_attribute(
            "title", re.compile(r".*test_.*\.py")
        )
        expect(trace_viewer.page.locator(".source-line-running")).to_contain_text(
            'page.set_content("<button>Click</button>")'
        )


def test_should_collect_trace_with_resources_but_no_js(
    context: BrowserContext,
    page: Page,
    server: Server,
    tmp_path: Path,
    show_trace_viewer: Callable[[Path], ContextManager[TraceViewerPage]],
) -> None:
    context.tracing.start(screenshots=True, snapshots=True)
    page.goto(server.PREFIX + "/frames/frame.html")
    page.set_content("<button>Click</button>")
    page.click('"Click"')
    page.mouse.move(20, 20)
    page.mouse.dblclick(30, 30)
    page.request.get(server.EMPTY_PAGE)
    page.keyboard.insert_text("abc")
    page.wait_for_timeout(2000)  # Give it some time to produce screenshots.
    page.route("**/empty.html", lambda route: route.continue_())
    page.goto(server.EMPTY_PAGE)
    page.goto(server.PREFIX + "/one-style.html")
    page.close()
    trace_file_path = tmp_path / "trace.zip"
    context.tracing.stop(path=trace_file_path)

    with show_trace_viewer(trace_file_path) as trace_viewer:
        expect(trace_viewer.action_titles).to_have_text(
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

        trace_viewer.select_action("Set content")
        expect(trace_viewer.page.locator(".browser-frame-address-bar")).to_have_text(
            server.PREFIX + "/frames/frame.html"
        )
        frame = trace_viewer.snapshot_frame("Set content", 0, False)
        expect(frame.locator("button")).to_have_text("Click")


def test_should_correctly_determine_sync_apiname(
    context: BrowserContext,
    page: Page,
    server: Server,
    tmp_path: Path,
    show_trace_viewer: Callable,
) -> None:
    context.tracing.start(screenshots=True, snapshots=True)

    received_response = threading.Event()

    def _handle_response(response: Response) -> None:
        response.request.all_headers()
        response.text()
        received_response.set()

    page.once("response", _handle_response)
    page.goto(server.PREFIX + "/grid.html")
    received_response.wait()

    page.close()
    trace_file_path = tmp_path / "trace.zip"
    context.tracing.stop(path=trace_file_path)

    with show_trace_viewer(trace_file_path) as trace_viewer:
        expect(trace_viewer.action_titles).to_have_text(
            [
                re.compile(r'Navigate to "/grid\.html"'),
                re.compile(r"Close"),
            ]
        )


def test_should_collect_two_traces(
    context: BrowserContext,
    page: Page,
    server: Server,
    tmp_path: Path,
    show_trace_viewer: Callable[[Path], ContextManager[TraceViewerPage]],
) -> None:
    context.tracing.start(screenshots=True, snapshots=True)
    page.goto(server.EMPTY_PAGE)
    page.set_content("<button>Click</button>")
    page.click('"Click"')
    tracing1_path = tmp_path / "trace1.zip"
    context.tracing.stop(path=tracing1_path)

    context.tracing.start(screenshots=True, snapshots=True)
    page.dblclick('"Click"')
    page.close()
    tracing2_path = tmp_path / "trace2.zip"
    context.tracing.stop(path=tracing2_path)

    with show_trace_viewer(tracing1_path) as trace_viewer:
        expect(trace_viewer.action_titles).to_have_text(
            [
                re.compile(r'Navigate to "/empty\.html"'),
                re.compile(r"Set content"),
                re.compile(r"Click"),
            ]
        )

    with show_trace_viewer(tracing2_path) as trace_viewer:
        expect(trace_viewer.action_titles).to_have_text(
            [
                re.compile(r"Double click"),
                re.compile(r"Close"),
            ]
        )


def test_should_work_with_playwright_context_managers(
    context: BrowserContext,
    page: Page,
    server: Server,
    tmp_path: Path,
    show_trace_viewer: Callable[[Path], ContextManager[TraceViewerPage]],
) -> None:
    context.tracing.start(screenshots=True, snapshots=True)
    page.goto(server.EMPTY_PAGE)
    page.set_content("<button>Click</button>")
    with page.expect_console_message() as message_info:
        page.evaluate('() => console.log("hello")')
        page.click('"Click"')
    assert (message_info.value).text == "hello"

    with page.expect_popup():
        page.evaluate("window._popup = window.open(document.location.href)")
    trace_file_path = tmp_path / "trace.zip"
    context.tracing.stop(path=trace_file_path)

    with show_trace_viewer(trace_file_path) as trace_viewer:
        expect(trace_viewer.action_titles).to_have_text(
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


def test_should_display_wait_for_load_state_even_if_did_not_wait_for_it(
    context: BrowserContext,
    page: Page,
    server: Server,
    tmp_path: Path,
    show_trace_viewer: Callable[[Path], ContextManager[TraceViewerPage]],
) -> None:
    context.tracing.start(screenshots=True, snapshots=True)

    page.goto(server.EMPTY_PAGE)
    page.wait_for_load_state("load")
    page.wait_for_load_state("load")

    trace_file_path = tmp_path / "trace.zip"
    context.tracing.stop(path=trace_file_path)

    with show_trace_viewer(trace_file_path) as trace_viewer:
        expect(trace_viewer.action_titles).to_have_text(
            [
                re.compile(r'Navigate to "/empty\.html"'),
                re.compile(r'Wait for event "frame\.wait_for_load_state"'),
                re.compile(r'Wait for event "frame\.wait_for_load_state"'),
            ]
        )


def test_should_respect_traces_dir_and_name(
    browser_type: BrowserType,
    server: Server,
    tmp_path: Path,
    launch_arguments: dict,
    show_trace_viewer: Callable[[Path], ContextManager[TraceViewerPage]],
) -> None:
    traces_dir = tmp_path / "traces"
    browser = browser_type.launch(traces_dir=traces_dir, **launch_arguments)
    context = browser.new_context()
    page = context.new_page()

    context.tracing.start(name="name1", snapshots=True)
    page.goto(server.PREFIX + "/one-style.html")
    context.tracing.stop_chunk(path=tmp_path / "trace1.zip")
    assert (traces_dir / "name1.trace").exists()
    assert (traces_dir / "name1.network").exists()

    context.tracing.start_chunk(name="name2")
    page.goto(server.PREFIX + "/har.html")
    context.tracing.stop(path=tmp_path / "trace2.zip")
    assert (traces_dir / "name2.trace").exists()
    assert (traces_dir / "name2.network").exists()

    browser.close()

    with show_trace_viewer(tmp_path / "trace1.zip") as trace_viewer:
        expect(trace_viewer.action_titles).to_have_text(
            [
                re.compile(r'Navigate to "/one-style\.html"'),
            ]
        )
        frame = trace_viewer.snapshot_frame('Navigate to "/one-style.html"', 0, False)
        expect(frame.locator("body")).to_have_css(
            "background-color", "rgb(255, 192, 203)"
        )
        expect(frame.locator("body")).to_have_text("hello, world!")

    with show_trace_viewer(tmp_path / "trace2.zip") as trace_viewer:
        expect(trace_viewer.action_titles).to_have_text(
            [
                re.compile(r'Navigate to "/har\.html"'),
            ]
        )
        frame = trace_viewer.snapshot_frame('Navigate to "/har.html"', 0, False)
        expect(frame.locator("body")).to_have_css(
            "background-color", "rgb(255, 192, 203)"
        )
        expect(frame.locator("body")).to_have_text("hello, world!")


def test_should_show_tracing_group_in_action_list(
    context: BrowserContext,
    tmp_path: Path,
    show_trace_viewer: Callable[[Path], ContextManager[TraceViewerPage]],
) -> None:
    context.tracing.start()
    page = context.new_page()

    context.tracing.group("outer group")
    page.goto("data:text/html,<!DOCTYPE html><body><div>Hello world</div></body>")
    context.tracing.group("inner group 1")
    page.locator("body").click()
    context.tracing.group_end()
    context.tracing.group("inner group 2")
    page.get_by_text("Hello").is_visible()
    context.tracing.group_end()
    context.tracing.group_end()

    trace_path = tmp_path / "trace.zip"
    context.tracing.stop(path=trace_path)

    with show_trace_viewer(trace_path) as trace_viewer:
        trace_viewer.expand_action("inner group 1")
        expect(trace_viewer.action_titles).to_have_text(
            [
                re.compile(r"Create page"),
                re.compile(r"outer group"),
                re.compile(r"Navigate to \"data:\""),
                re.compile(r"inner group 1"),
                re.compile(r"Click"),
                re.compile(r"inner group 2"),
            ]
        )
