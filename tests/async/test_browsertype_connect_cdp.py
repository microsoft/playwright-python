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
import requests

from playwright.async_api import BrowserType
from tests.server import Server, find_free_port

pytestmark = pytest.mark.only_browser("chromium")


async def test_connect_to_an_existing_cdp_session(
    launch_arguments: Dict, browser_type: BrowserType
):
    port = find_free_port()
    browser_server = await browser_type.launch(
        **launch_arguments, args=[f"--remote-debugging-port={port}"]
    )
    cdp_browser = await browser_type.connect_over_cdp(f"http://localhost:{port}")
    assert len(cdp_browser.contexts) == 1
    await cdp_browser.close()
    await browser_server.close()


async def test_connect_to_an_existing_cdp_session_twice(
    launch_arguments: Dict, browser_type: BrowserType, server: Server
):
    port = find_free_port()
    browser_server = await browser_type.launch(
        **launch_arguments, args=[f"--remote-debugging-port={port}"]
    )
    endpoint_url = f"http://localhost:{port}"
    cdp_browser1 = await browser_type.connect_over_cdp(endpoint_url)
    cdp_browser2 = await browser_type.connect_over_cdp(endpoint_url)
    assert len(cdp_browser1.contexts) == 1
    page1 = await cdp_browser1.contexts[0].new_page()
    await page1.goto(server.EMPTY_PAGE)

    assert len(cdp_browser2.contexts) == 1
    page2 = await cdp_browser2.contexts[0].new_page()
    await page2.goto(server.EMPTY_PAGE)

    assert len(cdp_browser1.contexts[0].pages) == 2
    assert len(cdp_browser2.contexts[0].pages) == 2

    await cdp_browser1.close()
    await cdp_browser2.close()
    await browser_server.close()


def _ws_endpoint_from_url(url: str) -> str:
    response = requests.get(url)
    assert response.ok
    response_body = response.json()
    return response_body["webSocketDebuggerUrl"]


async def test_conect_over_a_ws_endpoint(
    launch_arguments: Dict, browser_type: BrowserType, server: Server
):
    port = find_free_port()
    browser_server = await browser_type.launch(
        **launch_arguments, args=[f"--remote-debugging-port={port}"]
    )
    ws_endpoint = _ws_endpoint_from_url(f"http://localhost:{port}/json/version/")

    cdp_browser1 = await browser_type.connect_over_cdp(ws_endpoint)
    assert len(cdp_browser1.contexts) == 1
    await cdp_browser1.close()

    cdp_browser2 = await browser_type.connect_over_cdp(ws_endpoint)
    assert len(cdp_browser2.contexts) == 1
    await cdp_browser2.close()
    await browser_server.close()
