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

import json
import os
from pathlib import Path

from playwright.async_api import Browser
from tests.server import Server


async def test_should_not_omit_content(
    browser: Browser, server: Server, tmp_path: Path
) -> None:
    path = os.path.join(tmp_path, "log.har")
    context = await browser.new_context(
        record_har_path=path, record_har_omit_content=False
    )
    page = await context.new_page()
    await page.goto(server.PREFIX + "/har.html")
    await context.close()
    with open(path) as f:
        data = json.load(f)
        content1 = data["log"]["entries"][0]["response"]["content"]
        assert "text" in content1


async def test_should_support_minimal_mode(
    browser: Browser, server: Server, tmp_path: Path
) -> None:
    path = os.path.join(tmp_path, "log.har")
    context = await browser.new_context(
        record_har_path=path,
        record_har_mode="minimal",
    )
    page = await context.new_page()
    await page.goto(server.PREFIX + "/har.html")
    await context.close()
    with open(path) as f:
        data = json.load(f)
        assert "log" in data
        log = data["log"]
        assert log["entries"][0]["request"]["bodySize"] == -1
