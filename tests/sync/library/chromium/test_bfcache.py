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

"""Port of tests/library/chromium/bfcache.spec.ts."""

from typing import Dict, Generator

import pytest

from playwright.sync_api import Browser, BrowserType, Page
from tests.server import Server

pytestmark = pytest.mark.only_browser("chromium")


@pytest.fixture(scope="module")
def browser(
    browser_name: str, browser_type: BrowserType, launch_arguments: Dict
) -> Generator[Browser, None, None]:
    # Port of test.use({ launchOptions: { ignoreDefaultArgs: ['--disable-back-forward-cache'] } }).
    if browser_name != "chromium":
        pytest.skip("chromium only")
    browser = browser_type.launch(
        **launch_arguments, ignore_default_args=["--disable-back-forward-cache"]
    )
    yield browser
    browser.close()


def test_CR_042_bindings_should_work_after_restoring_from_bfcache(
    page: Page, server: Server
) -> None:
    page.expose_function("add", lambda a, b: a + b)

    page.goto(server.PREFIX + "/cached/bfcached.html")
    assert page.evaluate("window.add(1, 2)") == 3

    page.set_content("<a href='about:blank'}>click me</a>")
    page.click("a")

    page.go_back(wait_until="commit")
    page.evaluate("window.didShow")
    assert page.evaluate("window.add(2, 3)") == 5
