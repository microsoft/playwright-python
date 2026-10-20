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

"""Port of tests/page/page-event-load.spec.ts."""

from typing import List

import pytest

from playwright.async_api import Page, TimeoutError, expect
from tests.server import Server, TestServerRequest


async def test_NA_087_should_fire_once(
    page: Page, server: Server, browser_name: str
) -> None:
    if browser_name == "firefox":
        pytest.skip("fixme: Firefox sometimes double fires.")

    count: List[int] = []
    page.on("load", lambda _: count.append(1))
    await page.goto(server.PREFIX + "/one-style.html")
    await page.wait_for_timeout(1000)
    assert len(count) == 1


async def test_NA_088_should_fire_once_with_iframe_navigation(
    page: Page, server: Server, browser_name: str
) -> None:
    if browser_name == "firefox":
        pytest.skip("fixme: Firefox sometimes double fires.")

    request_count: List[int] = []

    def handle_tracker(request: TestServerRequest) -> None:
        request_count.append(1)
        request.write(f"request count: {len(request_count)}".encode())
        request.finish()

    server.set_route("/tracker", handle_tracker)

    def handle_home(request: TestServerRequest) -> None:
        request.write(
            b"""
      <!DOCTYPE html>
      <html>
        <head>
        </head>
        <body>
          <script>
            window.eventLog = [];
            window.addEventListener('load', () => {
              window.eventLog.push('load');
            });
          </script>
          <form id="trackerForm" action="/tracker" method="post" target="tracker">
            <input type="submit">
          </form>
          <iframe name="tracker" src="/tracker">
        </body>
      </html>
    """
        )
        request.finish()

    server.set_route("/home", handle_home)
    count: List[int] = []
    page.on("load", lambda _: count.append(1))
    await page.goto(server.PREFIX + "/home")
    tracking_frame = page.frame_locator("[name=tracker]")
    await expect(tracking_frame.locator(":scope")).to_contain_text("request count: 1")
    # Port of Promise.race([waitForEvent('load'), waitForTimeout(1000)]): the race
    # must end with the timeout.
    with pytest.raises(TimeoutError):
        async with page.expect_event("load", timeout=1000):
            await page.locator("input[type=submit]").click()
    assert len(count) == 1
    assert await page.evaluate("() => window['eventLog']") == ["load"]
