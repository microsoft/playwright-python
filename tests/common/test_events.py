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

from playwright.sync_api import sync_playwright
from tests.server import Server


def test_events(browser_name: str, launch_arguments: Dict, server: Server) -> None:
    with pytest.raises(Exception, match="fail"):

        def fail() -> None:
            raise Exception("fail")

        with sync_playwright() as p:
            with p[browser_name].launch(**launch_arguments) as browser:
                with browser.new_page() as page:
                    page.on("response", lambda _: fail())
                    page.goto(server.PREFIX + "/grid.html")
