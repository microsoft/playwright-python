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

"""Port of tests/library/browsercontext-add-init-script.spec.ts."""

import time
from pathlib import Path
from typing import Any, Callable, List

from playwright.sync_api import BrowserContext, Page
from tests.server import Server


def poll_until_equal(
    page: Page, actual: Callable[[], Any], expected: Any, timeout: float = 5000
) -> None:
    """Waits like `await promise`: until the callback was called."""
    deadline = time.monotonic() + timeout / 1000
    while actual() != expected and time.monotonic() < deadline:
        page.wait_for_timeout(100)
    assert actual() == expected


def test_IS_024_should_work_with_browser_context_scripts_smoke(
    context: BrowserContext, server: Server
) -> None:
    context.add_init_script("window['temp'] = 123")
    page = context.new_page()
    page.add_init_script("window['injected'] = window['temp']")
    page.goto(server.PREFIX + "/tamperable.html")
    assert page.evaluate("() => window['result']") == 123


def test_IS_025_should_work_without_navigation_after_all_bindings(
    context: BrowserContext,
) -> None:
    calls: List[Any] = []
    context.expose_function("woof", lambda arg: calls.append(arg))

    context.add_init_script(
        """
        window['woof']('hey');
        window['temp'] = 123;
        """
    )
    page = context.new_page()

    assert page.evaluate("() => window['temp']") == 123
    poll_until_equal(page, lambda: calls, ["hey"])


def test_IS_026_should_work_without_navigation_in_popup(
    context: BrowserContext,
) -> None:
    context.add_init_script("window['temp'] = 123")
    page = context.new_page()
    with page.expect_popup() as popup_info:
        page.evaluate("() => window['win'] = window.open()")
    popup = popup_info.value
    assert popup.evaluate("() => window['temp']") == 123


def test_IS_027_should_work_with_browser_context_scripts_with_a_path(
    context: BrowserContext, server: Server, assetdir: Path
) -> None:
    context.add_init_script(path=assetdir / "injectedfile.js")
    page = context.new_page()
    page.goto(server.PREFIX + "/tamperable.html")
    assert page.evaluate("() => window['result']") == 123


def test_IS_028_should_work_with_browser_context_scripts_for_already_created_pages(
    context: BrowserContext, server: Server
) -> None:
    page = context.new_page()
    context.add_init_script("window['temp'] = 123")
    page.add_init_script("window['injected'] = window['temp']")
    page.goto(server.PREFIX + "/tamperable.html")
    assert page.evaluate("() => window['result']") == 123


def test_IS_029_should_remove_context_init_script_after_dispose(
    context: BrowserContext, server: Server
) -> None:
    disposable = context.add_init_script("window['temp'] = 123")
    page = context.new_page()
    page.goto(server.PREFIX + "/tamperable.html")
    assert page.evaluate("() => window['temp']") == 123

    disposable.close()
    page.goto(server.PREFIX + "/tamperable.html")
    assert page.evaluate("() => window['temp']") is None


def test_IS_030_should_remove_context_init_script_and_keep_working_in_new_pages(
    context: BrowserContext, server: Server
) -> None:
    disposable = context.add_init_script("window['temp'] = 123")
    disposable.close()
    page = context.new_page()
    page.goto(server.PREFIX + "/tamperable.html")
    assert page.evaluate("() => window['temp']") is None


def test_IS_035_init_script_should_run_only_once_in_popup(
    context: BrowserContext,
) -> None:
    context.add_init_script("window['callCount'] = (window['callCount'] || 0) + 1;")
    page = context.new_page()
    with page.expect_popup() as popup_info:
        page.evaluate("() => window.open('about:blank')")
    popup = popup_info.value
    assert popup.evaluate("callCount") == 1
