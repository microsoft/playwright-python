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
import os
import tempfile
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


@pytest.mark.asyncio
async def test_tracing_should_not_leak_protocol_callbacks(browser_name: str) -> None:
    """
    Regression test for https://github.com/microsoft/playwright-python/issues/2977

    This test ensures that ProtocolCallback objects don't accumulate when tracing is enabled.
    The memory leak occurred because no_reply callbacks were created with circular references
    but never cleaned up.
    """

    def count_protocol_callbacks() -> int:
        """Count ProtocolCallback objects in memory."""
        gc.collect()
        count = 0
        for obj in gc.get_objects():
            if (
                hasattr(obj, "__class__")
                and obj.__class__.__name__ == "ProtocolCallback"
            ):
                count += 1
        return count

    with tempfile.TemporaryDirectory() as temp_dir:
        trace_file = os.path.join(temp_dir, "test_trace.zip")

        async with async_playwright() as p:
            browser = await p[browser_name].launch()
            context = await browser.new_context()

            # Start tracing to trigger the creation of no_reply callbacks
            await context.tracing.start(screenshots=True, snapshots=True)

            initial_count = count_protocol_callbacks()

            # Perform operations that would create tracing callbacks
            for _ in range(3):
                page = await context.new_page()
                await page.goto("data:text/html,<h1>Test Page</h1>")
                await page.wait_for_load_state("networkidle")
                await page.evaluate(
                    "document.querySelector('h1').textContent = 'Modified'"
                )
                await page.close()

            # Stop tracing
            await context.tracing.stop(path=trace_file)
            await browser.close()

    # Force garbage collection and check callback count
    gc.collect()
    final_count = count_protocol_callbacks()

    # The key assertion: callback count should not have increased significantly
    # Allow for a small number of legitimate callbacks but ensure no major leak
    assert (
        final_count - initial_count <= 5
    ), f"ProtocolCallback leak detected: initial={initial_count}, final={final_count}, leaked={final_count - initial_count}"
