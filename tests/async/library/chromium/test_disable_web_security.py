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

"""Port of tests/library/chromium/disable-web-security.spec.ts."""

import re
from typing import AsyncGenerator, Dict

import pytest

from playwright.async_api import Browser, BrowserType, Page, expect
from tests.server import Server, TestServerRequest

pytestmark = pytest.mark.only_browser("chromium")


@pytest.fixture(scope="module")
async def browser(
    browser_name: str, browser_type: BrowserType, launch_arguments: Dict
) -> AsyncGenerator[Browser, None]:
    # Port of it.use({ launchOptions: { args: ['--disable-web-security'] } }).
    if browser_name != "chromium":
        pytest.skip("chromium only")
    browser = await browser_type.launch(
        **launch_arguments, args=["--disable-web-security"]
    )
    yield browser
    await browser.close()


def set_routes(server: Server) -> None:
    def handle_main(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("Content-Type", "text/html")
        request.write(
            f'<a href="{server.PREFIX}/target.html" target="_blank">Click me</a>'.encode()
        )
        request.finish()

    def handle_target(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("Content-Type", "text/html")
        request.write(b"<html></html>")
        request.finish()

    server.set_route("/main.html", handle_main)
    server.set_route("/target.html", handle_target)


async def test_CR_045_test_utility_world_in_popup_w_disable_web_security(
    page: Page, server: Server
) -> None:
    set_routes(server)

    await page.goto(server.PREFIX + "/main.html")
    async with page.context.expect_page() as page1_info:
        await page.get_by_role("link", name="Click me").click()
    page1 = await page1_info.value
    await expect(page1).to_have_url(re.compile(r"target"))


async def test_CR_046_test_init_script_w_disable_web_security(
    page: Page, server: Server
) -> None:
    set_routes(server)

    await page.context.add_init_script("window.injected = 123")
    await page.goto(server.PREFIX + "/main.html")
    async with page.context.expect_page() as page1_info:
        await page.get_by_role("link", name="Click me").click()
    page1 = await page1_info.value
    value = await page1.evaluate("window.injected")
    assert value == 123
