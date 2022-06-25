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
import zipfile
from pathlib import Path

from playwright.sync_api import Browser
from tests.server import Server


def test_should_work(browser: Browser, server: Server, tmpdir: Path) -> None:
    path = os.path.join(tmpdir, "log.har")
    context = browser.new_context(record_har_path=path)
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)
    context.close()
    with open(path) as f:
        data = json.load(f)
        assert "log" in data


def test_should_omit_content(browser: Browser, server: Server, tmpdir: Path) -> None:
    path = os.path.join(tmpdir, "log.har")
    context = browser.new_context(record_har_path=path, record_har_content="omit")
    page = context.new_page()
    page.goto(server.PREFIX + "/har.html")
    context.close()
    with open(path) as f:
        data = json.load(f)
        assert "log" in data
        log = data["log"]

        content1 = log["entries"][0]["response"]["content"]
        assert "text" not in content1
        assert "encoding" not in content1


def test_should_omit_content_legacy(
    browser: Browser, server: Server, tmpdir: Path
) -> None:
    path = os.path.join(tmpdir, "log.har")
    context = browser.new_context(record_har_path=path, record_har_omit_content=True)
    page = context.new_page()
    page.goto(server.PREFIX + "/har.html")
    context.close()
    with open(path) as f:
        data = json.load(f)
        assert "log" in data
        log = data["log"]

        content1 = log["entries"][0]["response"]["content"]
        assert "text" not in content1
        assert "encoding" not in content1


def test_should_attach_content(browser: Browser, server: Server, tmpdir: Path) -> None:
    path = os.path.join(tmpdir, "log.har.zip")
    context = browser.new_context(
        record_har_path=path,
        record_har_content="attach",
    )
    page = context.new_page()
    page.goto(server.PREFIX + "/har.html")
    page.evaluate("() => fetch('/pptr.png').then(r => r.arrayBuffer())")
    context.close()
    with zipfile.ZipFile(path) as z:
        with z.open("har.har") as har:
            entries = json.load(har)["log"]["entries"]

            assert "encoding" not in entries[0]["response"]["content"]
            assert (
                entries[0]["response"]["content"]["mimeType"]
                == "text/html; charset=utf-8"
            )
            assert (
                "75841480e2606c03389077304342fac2c58ccb1b"
                in entries[0]["response"]["content"]["_file"]
            )
            assert entries[0]["response"]["content"]["size"] >= 96
            assert entries[0]["response"]["content"]["compression"] == 0

            assert "encoding" not in entries[1]["response"]["content"]
            assert (
                entries[1]["response"]["content"]["mimeType"]
                == "text/css; charset=utf-8"
            )
            assert (
                "79f739d7bc88e80f55b9891a22bf13a2b4e18adb"
                in entries[1]["response"]["content"]["_file"]
            )
            assert entries[1]["response"]["content"]["size"] >= 37
            assert entries[1]["response"]["content"]["compression"] == 0

            assert "encoding" not in entries[2]["response"]["content"]
            assert entries[2]["response"]["content"]["mimeType"] == "image/png"
            assert (
                "a4c3a18f0bb83f5d9fe7ce561e065c36205762fa"
                in entries[2]["response"]["content"]["_file"]
            )
            assert entries[2]["response"]["content"]["size"] >= 6000
            assert entries[2]["response"]["content"]["compression"] == 0

            with z.open("75841480e2606c03389077304342fac2c58ccb1b.html") as f:
                assert b"HAR Page" in f.read()

            with z.open("79f739d7bc88e80f55b9891a22bf13a2b4e18adb.css") as f:
                assert b"pink" in f.read()

            with z.open("a4c3a18f0bb83f5d9fe7ce561e065c36205762fa.png") as f:
                assert len(f.read()) == entries[2]["response"]["content"]["size"]


def test_should_include_content(browser: Browser, server: Server, tmpdir: Path) -> None:
    path = os.path.join(tmpdir, "log.har")
    context = browser.new_context(record_har_path=path)
    page = context.new_page()
    page.goto(server.PREFIX + "/har.html")
    context.close()
    with open(path) as f:
        data = json.load(f)
        assert "log" in data
        log = data["log"]

        content1 = log["entries"][0]["response"]["content"]
        assert content1["mimeType"] == "text/html; charset=utf-8"
        assert "HAR Page" in content1["text"]


def test_should_default_to_full_mode(
    browser: Browser, server: Server, tmpdir: Path
) -> None:
    path = os.path.join(tmpdir, "log.har")
    context = browser.new_context(
        record_har_path=path,
    )
    page = context.new_page()
    page.goto(server.PREFIX + "/har.html")
    context.close()
    with open(path) as f:
        data = json.load(f)
        assert "log" in data
        log = data["log"]
        assert log["entries"][0]["request"]["bodySize"] >= 0


def test_should_support_minimal_mode(
    browser: Browser, server: Server, tmpdir: Path
) -> None:
    path = os.path.join(tmpdir, "log.har")
    context = browser.new_context(
        record_har_path=path,
        record_har_mode="minimal",
    )
    page = context.new_page()
    page.goto(server.PREFIX + "/har.html")
    context.close()
    with open(path) as f:
        data = json.load(f)
        assert "log" in data
        log = data["log"]
        assert log["entries"][0]["request"]["bodySize"] == -1


def test_should_filter_by_glob(browser: Browser, server: Server, tmpdir: str) -> None:
    path = os.path.join(tmpdir, "log.har")
    context = browser.new_context(
        base_url=server.PREFIX,
        record_har_path=path,
        record_har_url_filter="/*.css",
        ignore_https_errors=True,
    )
    page = context.new_page()
    page.goto(server.PREFIX + "/har.html")
    context.close()
    with open(path) as f:
        data = json.load(f)
        assert "log" in data
        log = data["log"]
        assert len(log["entries"]) == 1
        assert log["entries"][0]["request"]["url"].endswith("one-style.css")


def test_should_filter_by_regexp(browser: Browser, server: Server, tmpdir: str) -> None:
    path = os.path.join(tmpdir, "log.har")
    context = browser.new_context(
        base_url=server.PREFIX,
        record_har_path=path,
        record_har_url_filter=re.compile("HAR.X?HTML", re.I),
        ignore_https_errors=True,
    )
    page = context.new_page()
    page.goto(server.PREFIX + "/har.html")
    context.close()
    with open(path) as f:
        data = json.load(f)
        assert "log" in data
        log = data["log"]
        assert len(log["entries"]) == 1
        assert log["entries"][0]["request"]["url"].endswith("har.html")
