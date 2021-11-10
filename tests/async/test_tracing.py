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

from pathlib import Path

from playwright.async_api import Browser, BrowserContext
from tests.server import Server


async def test_browser_context_output_trace(
    browser: Browser, server: Server, tmp_path: Path
):
    context = await browser.new_context()
    await context.tracing.start(screenshots=True, snapshots=True)
    page = await context.new_page()
    await page.goto(server.PREFIX + "/grid.html")
    await context.tracing.stop(path=tmp_path / "trace.zip")
    assert Path(tmp_path / "trace.zip").exists()


async def test_browser_context_should_not_throw_when_stopping_without_start_but_not_exporting(
    context: BrowserContext, server: Server, tmp_path: Path
):
    await context.tracing.stop()


async def test_browser_context_output_trace_chunk(
    browser: Browser, server: Server, tmp_path: Path
):
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
