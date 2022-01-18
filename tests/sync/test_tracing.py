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
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

from playwright.sync_api import Browser, BrowserContext, Page
from tests.server import Server


def test_browser_context_output_trace(
    browser: Browser, server: Server, tmp_path: Path
) -> None:
    context = browser.new_context()
    context.tracing.start(screenshots=True, snapshots=True)
    page = context.new_page()
    page.goto(server.PREFIX + "/grid.html")
    context.tracing.stop(path=tmp_path / "trace.zip")
    assert Path(tmp_path / "trace.zip").exists()


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


def test_should_collect_sources(
    context: BrowserContext, page: Page, server: Server, tmp_path: Path
) -> None:
    context.tracing.start(sources=True)
    page.goto(server.EMPTY_PAGE)
    page.set_content("<button>Click</button>")
    page.click("button")
    path = tmp_path / "trace.zip"
    context.tracing.stop(path=path)

    (resources, events) = parse_trace(path)
    current_file_content = Path(__file__).read_bytes()
    found_current_file = False
    for name, resource in resources.items():
        if resource == current_file_content:
            found_current_file = True
            break
    assert found_current_file


def parse_trace(path: Path) -> Tuple[Dict[str, bytes], List[Any]]:
    resources: Dict[str, bytes] = {}
    with zipfile.ZipFile(path, "r") as zip:
        for name in zip.namelist():
            resources[name] = zip.read(name)
    events: List[Any] = []
    for name in ["trace.trace", "trace.network"]:
        for line in resources[name].decode().splitlines():
            events.append(json.loads(line))
    return (resources, events)
