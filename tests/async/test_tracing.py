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

from playwright.async_api import BrowserType


async def test_browser_context_output_trace(
    browser_type: BrowserType, server, tmp_path: Path, launch_arguments
):
    browser = await browser_type.launch(
        trace_dir=tmp_path / "traces", **launch_arguments
    )
    context = await browser.new_context()
    await context.tracing.start(name="trace", screenshots=True, snapshots=True)
    page = await context.new_page()
    await page.goto(server.PREFIX + "/grid.html")
    await context.tracing.stop()
    await page.wait_for_timeout(1000)
    await context.tracing.export(Path(tmp_path / "traces" / "trace.zip").resolve())
    assert Path(tmp_path / "traces" / "trace.zip").exists()
    assert Path(tmp_path / "traces" / "resources").exists()
