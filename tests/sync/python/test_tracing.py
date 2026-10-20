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

import re
import threading
from pathlib import Path
from typing import Callable, ContextManager

from playwright.sync_api import BrowserContext, Page, Response, expect
from tests.server import Server

from ..conftest import TraceViewerPage


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
                re.compile(r"Navigate.*/empty\.html"),
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
                re.compile(r"Navigate.*/grid\.html"),
                re.compile(r"Close"),
            ]
        )
