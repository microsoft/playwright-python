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

from playwright.sync_api import Page
from tests.server import Server


def test_fill_textarea(page: Page, server: Server) -> None:
    page.goto(f"{server.PREFIX}/input/textarea.html")
    page.fill("textarea", "some value")
    assert page.evaluate("result") == "some value"


def test_fill_input(page: Page, server: Server) -> None:
    page.goto(f"{server.PREFIX}/input/textarea.html")
    page.fill("input", "some value")
    assert page.evaluate("result") == "some value"
