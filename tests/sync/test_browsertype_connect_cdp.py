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

from typing import Dict

import pytest

from playwright.sync_api import BrowserType
from tests.server import find_free_port

pytestmark = pytest.mark.only_browser("chromium")


def test_connect_to_an_existing_cdp_session(
    launch_arguments: Dict, browser_type: BrowserType
):
    port = find_free_port()
    browser_server = browser_type.launch(
        **launch_arguments, args=[f"--remote-debugging-port={port}"]
    )
    cdp_browser = browser_type.connect_over_cdp(f"http://localhost:{port}")
    assert len(cdp_browser.contexts) == 1
    cdp_browser.close()
    browser_server.close()
