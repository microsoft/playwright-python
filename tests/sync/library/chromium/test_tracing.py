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

"""Port of tests/library/chromium/tracing.spec.ts."""

import json
import warnings
from pathlib import Path
from typing import Optional

import pytest

from playwright.sync_api import Browser, Error
from tests.server import Server

from ...utils import Utils

pytestmark = pytest.mark.only_browser("chromium")


def test_TR_043_should_output_a_trace(
    browser: Browser, server: Server, tmp_path: Path
) -> None:
    # Upstream listens to Node.js process warnings; the Python client reports
    # warnings through the warnings module.
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        page = browser.new_page()
        output_trace_file = tmp_path / "trace.json"
        browser.start_tracing(page=page, screenshots=True, path=output_trace_file)
        for _ in range(11):
            page.goto(server.PREFIX + "/grid.html")
        browser.stop_tracing()
        assert output_trace_file.exists() is True
        page.close()

    assert [str(warning.message) for warning in caught] == []


def test_TR_044_should_create_directories_as_needed(
    browser: Browser, server: Server, tmp_path: Path
) -> None:
    page = browser.new_page()
    file_path = tmp_path / "these" / "are" / "directories" / "trace.json"
    browser.start_tracing(page=page, screenshots=True, path=file_path)
    page.goto(server.PREFIX + "/grid.html")
    browser.stop_tracing()
    assert file_path.exists() is True
    page.close()


def test_TR_045_should_run_with_custom_categories_if_provided(
    browser: Browser, tmp_path: Path, utils: Utils
) -> None:
    page = browser.new_page()
    output_trace_file = tmp_path / "trace.json"
    browser.start_tracing(
        page=page, path=output_trace_file, categories=["disabled-by-default-cc.debug"]
    )
    utils.rafraf(page)
    browser.stop_tracing()

    trace_json = json.loads(output_trace_file.read_text())
    # NOTE: trace-config is deprecated as per http://crrev.com/c/6628182
    assert (
        "disabled-by-default-cc.debug"
        in (trace_json["metadata"].get("trace-config") or "")
        or len(
            [
                event
                for event in trace_json["traceEvents"]
                if event.get("cat") == "disabled-by-default-cc.debug"
            ]
        )
        > 0
    ) is True
    page.close()


def test_TR_046_should_throw_if_tracing_on_two_pages(
    browser: Browser, tmp_path: Path
) -> None:
    page = browser.new_page()
    output_trace_file = tmp_path / "trace.json"
    browser.start_tracing(page=page, path=output_trace_file)
    new_page = browser.new_page()
    error: Optional[Error] = None
    try:
        browser.start_tracing(page=new_page, path=output_trace_file)
    except Error as e:
        error = e
    new_page.close()
    assert error
    browser.stop_tracing()
    page.close()


def test_TR_047_should_return_a_buffer(
    browser: Browser, server: Server, tmp_path: Path
) -> None:
    page = browser.new_page()
    output_trace_file = tmp_path / "trace.json"
    browser.start_tracing(page=page, screenshots=True, path=output_trace_file)
    page.goto(server.PREFIX + "/grid.html")
    trace = browser.stop_tracing()
    buf = output_trace_file.read_bytes()
    assert trace.decode() == buf.decode()
    page.close()


def test_TR_048_should_work_without_options(browser: Browser, server: Server) -> None:
    page = browser.new_page()
    browser.start_tracing(page=page)
    page.goto(server.PREFIX + "/grid.html")
    trace = browser.stop_tracing()
    assert trace
    page.close()


def test_TR_049_should_support_a_buffer_without_a_path(
    browser: Browser, server: Server, utils: Utils
) -> None:
    page = browser.new_page()
    browser.start_tracing(page=page, screenshots=True)
    page.goto(server.PREFIX + "/grid.html")
    utils.rafraf(page, 100)
    trace = browser.stop_tracing()
    assert ("screenshot" in trace.decode()) is True
    page.close()
