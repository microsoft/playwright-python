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

import base64
import json
import os


def test_should_work(browser, server, tmpdir):
    path = os.path.join(tmpdir, "log.har")
    context = browser.new_context(record_har_path=path)
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)
    context.close()
    with open(path) as f:
        data = json.load(f)
        assert "log" in data


def test_should_omit_content(browser, server, tmpdir):
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


def test_should_include_content(browser, server, tmpdir):
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
        assert content1["encoding"] == "base64"
        assert content1["mimeType"] == "text/html"
        s = base64.b64decode(content1["text"]).decode()
        assert "HAR Page" in s
