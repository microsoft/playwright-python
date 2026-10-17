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

"""Port of tests/library/browsertype-basic.spec.ts."""

import os
from typing import Dict, Optional

import pytest

from playwright.sync_api import BrowserType, Error


def test_BT_001_browser_type_executable_path_should_work(
    browser_type: BrowserType, browser_channel: Optional[str], launch_arguments: Dict
) -> None:
    if browser_channel:
        pytest.skip("We skip browser download when testing a channel")
    if launch_arguments.get("executable_path"):
        pytest.skip("Skip with custom executable path")

    executable_path = browser_type.executable_path
    assert os.path.exists(executable_path) is True


def test_BT_002_browser_type_name_should_work(
    browser_type: BrowserType, browser_name: str
) -> None:
    assert browser_type.name == browser_name


@pytest.mark.xfail(
    reason="python: connect_over_cdp() has no client check; the driver's error says 'CDP connections are only supported by Chromium'",
    strict=True,
)
def test_BT_003_should_throw_when_trying_to_connect_with_not_chromium(
    browser_type: BrowserType, browser_name: str
) -> None:
    if browser_name == "chromium" or browser_name == "webkit":
        pytest.skip()

    with pytest.raises(Error) as exc_info:
        browser_type.connect_over_cdp("ws://foo")
    assert (
        exc_info.value.message
        == "Connecting over CDP is only supported in Chromium and WebKit."
    )
