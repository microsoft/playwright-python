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

"""Port of tests/library/browser-server.spec.ts."""

import json
import os
import re
import sys
import threading
from pathlib import Path
from typing import Callable, Dict, List

import pytest

from playwright.sync_api import Browser, BrowserType, sync_playwright


@pytest.fixture
def registry_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Port of the beforeEach hook: the server registry is in the test's output folder."""
    registry = tmp_path / "registry"
    monkeypatch.setenv("PWTEST_SERVER_REGISTRY", str(registry))
    return registry


def run_with_new_playwright(
    browser_name: str,
    launch_arguments: Dict,
    body: Callable[[BrowserType, Browser], None],
) -> None:
    """Runs body with the browser_type and browser of a new Playwright.

    The driver reads PWTEST_SERVER_REGISTRY from its environment when it starts, so
    the test can not use the driver of the session. The sync API can not start a
    second Playwright on the thread of the first one, so body runs on a new thread.
    """
    errors: List[BaseException] = []

    def run() -> None:
        try:
            with sync_playwright() as playwright:
                browser_type = playwright[browser_name]
                browser = browser_type.launch(**launch_arguments)
                try:
                    body(browser_type, browser)
                finally:
                    browser.close()
        except BaseException as error:
            errors.append(error)

    thread = threading.Thread(target=run)
    thread.start()
    thread.join()
    if errors:
        raise errors[0]


def test_BR_008_should_start_and_stop_pipe_server(
    browser_name: str, launch_arguments: Dict, registry_dir: Path
) -> None:
    def body(browser_type: BrowserType, browser: Browser) -> None:
        server_info = browser.bind("default")
        assert re.search(r"browser-", server_info["endpoint"])

        browser2 = browser_type.connect(server_info["endpoint"])
        page = browser2.new_page()
        page.goto("data:text/html,<h1>Hello via pipe</h1>")
        assert page.locator("h1").text_content() == "Hello via pipe"
        page.close()
        browser2.close()
        browser.unbind()

    run_with_new_playwright(browser_name, launch_arguments, body)


def test_BR_009_should_write_descriptor_on_start_and_remove_on_stop(
    browser_name: str, launch_arguments: Dict, registry_dir: Path
) -> None:
    def body(browser_type: BrowserType, browser: Browser) -> None:
        # Upstream also passes { wsPath: 'test' }, an option that bind() does not have.
        server_info = browser.bind("my-title")

        file_name = os.listdir(registry_dir)[0]
        file = registry_dir / file_name

        descriptor = json.loads(file.read_text(encoding="utf-8"))
        assert descriptor["title"] == "my-title"
        assert descriptor["playwrightVersion"]
        assert descriptor["playwrightLib"]
        assert descriptor["browser"]["browserName"]
        assert descriptor["endpoint"] == server_info["endpoint"]

        if sys.platform != "win32":
            assert os.path.exists(server_info["endpoint"]) is True

        browser.unbind()
        assert os.path.exists(file) is False
        if sys.platform != "win32":
            assert os.path.exists(server_info["endpoint"]) is False

    run_with_new_playwright(browser_name, launch_arguments, body)


def test_BR_010_should_start_ws_server_with_host_port_and_produce_well_formed_endpoint(
    browser_name: str, launch_arguments: Dict, registry_dir: Path
) -> None:
    def body(browser_type: BrowserType, browser: Browser) -> None:
        server_info = browser.bind("default", host="localhost", port=0)
        assert re.match(
            r"^ws://(127\.0\.0\.1|\[::1\]):\d+/[a-f0-9]+$", server_info["endpoint"]
        )

        browser2 = browser_type.connect(server_info["endpoint"])
        page = browser2.new_page()
        page.goto("data:text/html,<h1>Hello via ws</h1>")
        assert page.locator("h1").text_content() == "Hello via ws"
        page.close()
        browser2.close()
        browser.unbind()

    run_with_new_playwright(browser_name, launch_arguments, body)
