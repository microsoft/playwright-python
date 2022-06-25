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

import json
import os
import re

from playwright.async_api import Browser
from tests.server import Server


async def test_should_work(browser, server, tmpdir):
    path = os.path.join(tmpdir, "log.har")
    context = await browser.new_context(record_har_path=path)
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    await context.close()
    with open(path) as f:
        data = json.load(f)
        assert "log" in data


async def test_should_omit_content(browser, server, tmpdir):
    path = os.path.join(tmpdir, "log.har")
    context = await browser.new_context(
        record_har_path=path, record_har_omit_content=True
    )
    page = await context.new_page()
    await page.goto(server.PREFIX + "/har.html")
    await context.close()
    with open(path) as f:
        data = json.load(f)
        assert "log" in data
        log = data["log"]
        content1 = log["entries"][0]["response"]["content"]
        assert "text" in content1
        assert "encoding" not in content1


async def test_should_not_omit_content(browser, server, tmpdir):
    path = os.path.join(tmpdir, "log.har")
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


async def test_should_include_content(browser, server, tmpdir):
    path = os.path.join(tmpdir, "log.har")
    context = await browser.new_context(record_har_path=path)
    page = await context.new_page()
    await page.goto(server.PREFIX + "/har.html")
    await context.close()
    with open(path) as f:
        data = json.load(f)
        assert "log" in data
        log = data["log"]

        content1 = log["entries"][0]["response"]["content"]
        assert content1["mimeType"] == "text/html; charset=utf-8"
        assert "HAR Page" in content1["text"]


async def test_should_filter_by_glob(
    browser: Browser, server: Server, tmpdir: str
) -> None:
    path = os.path.join(tmpdir, "log.har")
    context = await browser.new_context(
        base_url=server.PREFIX,
        record_har_path=path,
        record_har_url_filter="/*.css",
        ignore_https_errors=True,
    )
    page = await context.new_page()
    await page.goto(server.PREFIX + "/har.html")
    await context.close()
    with open(path) as f:
        data = json.load(f)
        assert "log" in data
        log = data["log"]
        assert len(log["entries"]) == 1
        assert log["entries"][0]["request"]["url"].endswith("one-style.css")


async def test_should_filter_by_regexp(
    browser: Browser, server: Server, tmpdir: str
) -> None:
    path = os.path.join(tmpdir, "log.har")
    context = await browser.new_context(
        base_url=server.PREFIX,
        record_har_path=path,
        record_har_url_filter=re.compile("HAR.X?HTML", re.I),
        ignore_https_errors=True,
    )
    page = await context.new_page()
    await page.goto(server.PREFIX + "/har.html")
    await context.close()
    with open(path) as f:
        data = json.load(f)
        assert "log" in data
        log = data["log"]
        assert len(log["entries"]) == 1
        assert log["entries"][0]["request"]["url"].endswith("har.html")
