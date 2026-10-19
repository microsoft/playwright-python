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

"""Port of tests/page/page-add-init-script.spec.ts."""

from pathlib import Path
from typing import List

import pytest

from playwright.async_api import ConsoleMessage, Error, Page
from tests.server import Server


async def test_IS_001_should_evaluate_before_anything_else_on_the_page(
    page: Page, server: Server
) -> None:
    await page.add_init_script("window['injected'] = 123;")
    await page.goto(server.PREFIX + "/tamperable.html")
    assert await page.evaluate("() => window['result']") == 123


async def test_IS_002_should_work_with_a_path(
    page: Page, server: Server, assetdir: Path
) -> None:
    await page.add_init_script(path=assetdir / "injectedfile.js")
    await page.goto(server.PREFIX + "/tamperable.html")
    assert await page.evaluate("() => window['result']") == 123


async def test_IS_003_should_work_with_content_smoke(
    page: Page, server: Server
) -> None:
    await page.add_init_script('window["injected"] = 123')
    await page.goto(server.PREFIX + "/tamperable.html")
    assert await page.evaluate("() => window['result']") == 123


async def test_IS_004_should_throw_without_path_and_content(page: Page) -> None:
    with pytest.raises(Error) as exc_info:
        await page.add_init_script()
    # The Python option for the content is `script`, not `content`.
    assert "Either path or script parameter must be present" in (exc_info.value.message)


async def test_IS_005_should_work_with_trailing_comments(
    page: Page, assetdir: Path
) -> None:
    await page.add_init_script("// comment")
    await page.add_init_script("window.secret = 42;")
    await page.goto("data:text/html,<html></html>")
    assert await page.evaluate("secret") == 42


async def test_IS_006_should_support_multiple_scripts(
    page: Page, server: Server
) -> None:
    await page.add_init_script("window['script1'] = 1;")
    await page.add_init_script("window['script2'] = 2;")
    await page.goto(server.PREFIX + "/tamperable.html")
    assert await page.evaluate("() => window['script1']") == 1
    assert await page.evaluate("() => window['script2']") == 2


async def test_IS_007_should_work_with_csp(page: Page, server: Server) -> None:
    server.set_csp("/empty.html", "script-src " + server.PREFIX)
    await page.add_init_script("window['injected'] = 123;")
    await page.goto(server.PREFIX + "/empty.html")
    assert await page.evaluate("() => window['injected']") == 123

    # Make sure CSP works.
    try:
        await page.add_script_tag(content="window.e = 10;")
    except Error:
        pass
    assert await page.evaluate("() => window['e']") is None


async def test_IS_008_should_work_after_a_cross_origin_navigation(
    page: Page, server: Server
) -> None:
    await page.goto(server.CROSS_PROCESS_PREFIX)
    await page.add_init_script("window['injected'] = 123;")
    await page.goto(server.PREFIX + "/tamperable.html")
    assert await page.evaluate("() => window['result']") == 123


async def test_IS_009_should_remove_init_script_after_dispose(
    page: Page, server: Server
) -> None:
    disposable = await page.add_init_script("window['injected'] = 123;")
    await page.goto(server.PREFIX + "/tamperable.html")
    assert await page.evaluate("() => window['result']") == 123

    await disposable.close()
    await page.goto(server.PREFIX + "/tamperable.html")
    assert await page.evaluate("() => window['result']") is None


async def test_IS_010_should_remove_one_of_multiple_init_scripts_after_dispose(
    page: Page, server: Server
) -> None:
    disposable1 = await page.add_init_script("window['script1'] = 1;")
    await page.add_init_script("window['script2'] = 2;")
    await page.goto(server.PREFIX + "/tamperable.html")
    assert await page.evaluate("() => window['script1']") == 1
    assert await page.evaluate("() => window['script2']") == 2

    await disposable1.close()
    await page.goto(server.PREFIX + "/tamperable.html")
    assert await page.evaluate("() => window['script1']") is None
    assert await page.evaluate("() => window['script2']") == 2


async def test_IS_011_init_script_should_run_only_once_in_iframe(
    page: Page, server: Server, browser_name: str
) -> None:
    messages: List[str] = []

    def on_console(event: ConsoleMessage) -> None:
        if event.text.startswith("init script:"):
            messages.append(event.text)

    page.on("console", on_console)
    await page.add_init_script(
        "console.log('init script:', location.pathname || 'no url yet')"
    )
    await page.goto(server.PREFIX + "/frames/one-frame.html")
    assert messages == [
        "init script: /frames/one-frame.html",
        "init script: "
        + ("no url yet" if browser_name == "firefox" else "/frames/frame.html"),
    ]
