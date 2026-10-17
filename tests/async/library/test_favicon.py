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

"""Port of tests/library/favicon.spec.ts."""

import asyncio
import time
from pathlib import Path

import pytest

from playwright.async_api import Page
from tests.server import Server, TestServerRequest


async def test_FA_001_should_load_svg_favicon_with_prefer_color_scheme(
    page: Page, server: Server, browser_name: str, headless: bool, assetdir: Path
) -> None:
    if headless and browser_name != "firefox":
        pytest.skip("headless browsers, except firefox, do not request favicons")
    if not headless and browser_name == "webkit":
        pytest.skip("headed webkit does not have a favicon feature")

    # Browsers aggressively cache favicons, so force bust with the
    # `d` parameter to make iterating on this test more predictable and isolated.
    favicon = f"/favicon.svg?d={int(time.time() * 1000)}"
    server.set_route(
        favicon,
        lambda request: request.serve_file(
            assetdir / "media-query-prefers-color-scheme.svg"
        ),
    )

    def handle_page(request: TestServerRequest) -> None:
        request.write(
            f"""
      <!DOCTYPE html>
      <html>
        <head>
          <meta charset="utf-8">
          <link rel="icon" type="image/svg+xml" href="{favicon}">
          <title>SVG Favicon Test</title>
        </head>
        <body>
          favicons
        </body>
      </html>
""".encode()
        )
        request.finish()

    server.set_route("/page.html", handle_page)

    await asyncio.gather(
        server.wait_for_request(favicon),
        page.goto(server.PREFIX + "/page.html"),
    )

    # Add artificial delay since, just because we saw the request for the favicon,
    # it does not mean the browser has processed it. There's not a great way to
    # hook into something like "favicon is fully displayed" event, so hopefully
    # 500ms is enough, but not too much!
    await page.wait_for_timeout(500)
    # Text still being around ensures we haven't actually lost our browser to a crash.
    await page.wait_for_selector("text=favicons")
