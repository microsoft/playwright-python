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

from pathlib import Path
from typing import Optional

from playwright.async_api import BrowserContext, Error, Page


async def test_add_init_script_evaluate_before_anything_else_on_the_page(
    page: Page,
) -> None:
    await page.add_init_script("window.injected = 123")
    await page.goto("data:text/html,<script>window.result = window.injected</script>")
    assert await page.evaluate("window.result") == 123


async def test_add_init_script_work_with_a_path(page: Page, assetdir: Path) -> None:
    await page.add_init_script(path=assetdir / "injectedfile.js")
    await page.goto("data:text/html,<script>window.result = window.injected</script>")
    assert await page.evaluate("window.result") == 123


async def test_add_init_script_work_with_content(page: Page) -> None:
    await page.add_init_script("window.injected = 123")
    await page.goto("data:text/html,<script>window.result = window.injected</script>")
    assert await page.evaluate("window.result") == 123


async def test_add_init_script_throw_without_path_and_content(page: Page) -> None:
    error: Optional[Error] = None
    try:
        await page.add_init_script({"foo": "bar"})  # type: ignore
    except Error as e:
        error = e
    assert error
    assert error.message == "Either path or script parameter must be specified"


async def test_add_init_script_work_with_browser_context_scripts(
    page: Page, context: BrowserContext
) -> None:
    await context.add_init_script("window.temp = 123")
    page = await context.new_page()
    await page.add_init_script("window.injected = window.temp")
    await page.goto("data:text/html,<script>window.result = window.injected</script>")
    assert await page.evaluate("window.result") == 123


async def test_add_init_script_work_with_browser_context_scripts_with_a_path(
    page: Page, context: BrowserContext, assetdir: Path
) -> None:
    await context.add_init_script(path=assetdir / "injectedfile.js")
    page = await context.new_page()
    await page.goto("data:text/html,<script>window.result = window.injected</script>")
    assert await page.evaluate("window.result") == 123


async def test_add_init_script_work_with_browser_context_scripts_for_already_created_pages(
    page: Page, context: BrowserContext
) -> None:
    await context.add_init_script("window.temp = 123")
    await page.add_init_script("window.injected = window.temp")
    await page.goto("data:text/html,<script>window.result = window.injected</script>")
    assert await page.evaluate("window.result") == 123


async def test_add_init_script_support_multiple_scripts(page: Page) -> None:
    await page.add_init_script("window.script1 = 1")
    await page.add_init_script("window.script2 = 2")
    await page.goto("data:text/html,<script>window.result = window.injected</script>")
    assert await page.evaluate("window.script1") == 1
    assert await page.evaluate("window.script2") == 2


async def test_should_work_with_trailing_comments(page: Page) -> None:
    await page.add_init_script("// comment")
    await page.add_init_script("window.secret = 42;")
    await page.goto("data:text/html,<html></html>")
    assert await page.evaluate("secret") == 42
