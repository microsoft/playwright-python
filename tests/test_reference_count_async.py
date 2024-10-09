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

import gc
from collections import defaultdict
from typing import Any

import objgraph
import pytest

from playwright.async_api import async_playwright
from tests.server import Server


@pytest.mark.asyncio
async def test_memory_objects(server: Server, browser_name: str) -> None:
    async with async_playwright() as p:
        browser = await p[browser_name].launch()
        page = await browser.new_page()
        await page.goto(server.EMPTY_PAGE)

        page.on("dialog", lambda dialog: dialog.dismiss())
        for _ in range(100):
            await page.evaluate("""async () => alert()""")

        await page.route("**/*", lambda route, _: route.fulfill(body="OK"))

        def handle_network_response_received(event: Any) -> None:
            event["__pw__is_last_network_response_received_event"] = True

        if browser_name == "chromium":
            # https://github.com/microsoft/playwright-python/issues/1602
            client = await page.context.new_cdp_session(page)
            await client.send("Network.enable")

            client.on(
                "Network.responseReceived",
                handle_network_response_received,
            )

        for _ in range(100):
            response = await page.evaluate("""async () => (await fetch("/")).text()""")
            assert response == "OK"

        await browser.close()

    gc.collect()

    pw_objects: defaultdict = defaultdict(int)
    for o in objgraph.by_type("dict"):
        assert isinstance(o, dict)
        name = o.get("_type")
        # https://github.com/microsoft/playwright-python/issues/1602
        if o.get("__pw__is_last_network_response_received_event", False):
            assert False
        if not name:
            continue
        pw_objects[name] += 1

    assert "Dialog" not in pw_objects
    assert "Request" not in pw_objects
    assert "Route" not in pw_objects
