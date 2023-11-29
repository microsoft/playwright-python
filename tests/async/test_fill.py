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

from playwright.async_api import Page
from tests.server import Server


async def test_fill_textarea(page: Page, server: Server) -> None:
    await page.goto(f"{server.PREFIX}/input/textarea.html")
    await page.fill("textarea", "some value")
    assert await page.evaluate("result") == "some value"


#


async def test_fill_input(page: Page, server: Server) -> None:
    await page.goto(f"{server.PREFIX}/input/textarea.html")
    await page.fill("input", "some value")
    assert await page.evaluate("result") == "some value"
