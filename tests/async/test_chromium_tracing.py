# Copyright (c) Microsoft Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License")
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

import json
import os
from pathlib import Path

import pytest

from playwright.async_api import Browser, Page


@pytest.mark.only_browser("chromium")
async def test_should_output_a_trace(
    browser: Browser, page: Page, server, tmpdir: Path
):
    output_file = tmpdir / "trace.json"
    await browser.start_tracing(page=page, screenshots=True, path=output_file)
    await page.goto(server.PREFIX + "/grid.html")
    await browser.stop_tracing()
    assert os.path.getsize(output_file) > 0


@pytest.mark.only_browser("chromium")
async def test_should_create_directories_as_needed(
    browser: Browser, page: Page, server, tmpdir
):
    output_file = tmpdir / "these" / "are" / "directories" / "trace.json"
    await browser.start_tracing(page=page, screenshots=True, path=output_file)
    await page.goto(server.PREFIX + "/grid.html")
    await browser.stop_tracing()
    assert os.path.getsize(output_file) > 0


@pytest.mark.only_browser("chromium")
async def test_should_run_with_custom_categories_if_provided(
    browser: Browser, page: Page, tmpdir: Path
):
    output_file = tmpdir / "trace.json"
    await browser.start_tracing(
        page=page,
        screenshots=True,
        path=output_file,
        categories=["disabled-by-default-v8.cpu_profiler.hires"],
    )
    await browser.stop_tracing()
    with open(output_file, mode="r") as of:
        trace_json = json.load(of)
        assert (
            "disabled-by-default-v8.cpu_profiler.hires"
            in trace_json["metadata"]["trace-config"]
        )


@pytest.mark.only_browser("chromium")
async def test_should_throw_if_tracing_on_two_pages(
    browser: Browser, page: Page, tmpdir: Path
):
    output_file_1 = tmpdir / "trace1.json"
    await browser.start_tracing(page=page, screenshots=True, path=output_file_1)
    output_file_2 = tmpdir / "trace2.json"
    with pytest.raises(Exception):
        await browser.start_tracing(page=page, screenshots=True, path=output_file_2)
    await browser.stop_tracing()


@pytest.mark.only_browser("chromium")
async def test_should_return_a_buffer(
    browser: Browser, page: Page, server, tmpdir: Path
):
    output_file = tmpdir / "trace.json"
    await browser.start_tracing(page=page, path=output_file, screenshots=True)
    await page.goto(server.PREFIX + "/grid.html")
    value = await browser.stop_tracing()
    with open(output_file, mode="r") as trace_file:
        assert trace_file.read() == value.decode()


@pytest.mark.only_browser("chromium")
async def test_should_work_without_options(browser: Browser, page: Page, server):
    await browser.start_tracing()
    await page.goto(server.PREFIX + "/grid.html")
    trace = await browser.stop_tracing()
    assert trace


@pytest.mark.only_browser("chromium")
async def test_should_support_a_buffer_without_a_path(
    browser: Browser, page: Page, server
):
    await browser.start_tracing(page=page, screenshots=True)
    await page.goto(server.PREFIX + "/grid.html")
    trace = await browser.stop_tracing()
    assert "screenshot" in trace.decode()
