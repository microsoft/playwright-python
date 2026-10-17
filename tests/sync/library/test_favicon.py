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

import time
from pathlib import Path

import pytest

from playwright.sync_api import Page
from tests.server import ExpectResponse, Server, TestServerRequest


def wait_for_server_request(
    page: Page, request_info: ExpectResponse[TestServerRequest]
) -> TestServerRequest:
    """Waits until the test server gets the request of server.expect_request()."""
    while True:
        try:
            return request_info.value
        except ValueError:
            page.wait_for_timeout(10)


def test_FA_001_should_load_svg_favicon_with_prefer_color_scheme(
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

    with server.expect_request(favicon) as request_info:
        page.goto(server.PREFIX + "/page.html")
    wait_for_server_request(page, request_info)

    # Add artificial delay since, just because we saw the request for the favicon,
    # it does not mean the browser has processed it. There's not a great way to
    # hook into something like "favicon is fully displayed" event, so hopefully
    # 500ms is enough, but not too much!
    page.wait_for_timeout(500)
    # Text still being around ensures we haven't actually lost our browser to a crash.
    page.wait_for_selector("text=favicons")
