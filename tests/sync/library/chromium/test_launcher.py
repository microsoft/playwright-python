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

"""Port of tests/library/chromium/launcher.spec.ts."""

from typing import Any, Dict, List

import pytest

from playwright.sync_api import BrowserType
from tests.helpers.remote_server import RemoteServer

pytestmark = pytest.mark.only_browser("chromium")


def test_CR_033_should_throw_with_remote_debugging_pipe_argument(
    browser_name: str, launch_arguments: Dict
) -> None:
    options: Dict[str, Any] = {**launch_arguments}
    options["args"] = ["--remote-debugging-pipe"] + options.get("args", [])
    # browserType.launchServer() is not in the Python API: RemoteServer runs it in
    # the driver's Node.js and fails with its output when the launch fails.
    with pytest.raises(Exception) as exc_info:
        RemoteServer(browser_name, options)
    assert "Playwright manages remote debugging connection itself" in str(
        exc_info.value
    )


def test_CR_034_should_not_throw_with_remote_debugging_port_argument(
    browser_name: str, launch_arguments: Dict
) -> None:
    options: Dict[str, Any] = {**launch_arguments}
    options["args"] = ["--remote-debugging-port=0"] + options.get("args", [])
    browser = RemoteServer(browser_name, options)
    browser.close()


def test_CR_035_should_not_create_pages_automatically(
    browser_type: BrowserType, launch_arguments: Dict
) -> None:
    browser = browser_type.launch(**launch_arguments)
    browser_session = browser.new_browser_cdp_session()
    targets: List[Any] = []

    def on_target_created(event: Dict) -> None:
        if event["targetInfo"]["type"] != "browser":
            targets.append(event["targetInfo"])

    browser_session.on("Target.targetCreated", on_target_created)
    browser_session.send("Target.setDiscoverTargets", {"discover": True})
    browser.new_context()
    browser.close()
    assert len(targets) == 0
