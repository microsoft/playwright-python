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

"""Port of tests/library/browsercontext-user-agent.spec.ts."""

import asyncio
from typing import Any, Awaitable, Callable, Dict

import pytest

from playwright.async_api import Browser, BrowserContext, Error, Playwright
from tests.server import Server, TestServerRequest
from tests.utils import chromium_version_less_than, must

from ..utils import Utils


async def test_UA_001_should_work(browser: Browser, server: Server) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    assert "Mozilla" in await page.evaluate("() => navigator.userAgent")
    await context.close()

    context = await browser.new_context(user_agent="foobar")
    page = await context.new_page()
    with server.expect_request("/empty.html") as request_info:
        await page.goto(server.EMPTY_PAGE)
    request = request_info.value
    assert request.getHeader("user-agent") == "foobar"
    await context.close()


async def test_UA_002_should_work_for_subframes(
    browser: Browser, server: Server, utils: Utils
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    assert "Mozilla" in await page.evaluate("() => navigator.userAgent")
    await context.close()

    context = await browser.new_context(user_agent="foobar")
    page = await context.new_page()
    with server.expect_request("/empty.html") as request_info:
        await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    request = request_info.value
    assert request.getHeader("user-agent") == "foobar"
    await context.close()


async def test_UA_003_should_emulate_device_user_agent(
    browser: Browser, server: Server, playwright: Playwright
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(server.PREFIX + "/mobile.html")
    assert "iPhone" not in await page.evaluate("() => navigator.userAgent")
    await context.close()

    context = await browser.new_context(
        user_agent=playwright.devices["iPhone 6"]["user_agent"]
    )
    page = await context.new_page()
    await page.goto(server.PREFIX + "/mobile.html")
    assert "iPhone" in await page.evaluate("() => navigator.userAgent")
    await context.close()


async def test_UA_004_should_make_a_copy_of_default_options(
    browser: Browser, server: Server
) -> None:
    options: Dict[str, Any] = {"user_agent": "foobar"}
    context = await browser.new_context(**options)
    options["user_agent"] = "wrong"
    page = await context.new_page()
    with server.expect_request("/empty.html") as request_info:
        await page.goto(server.EMPTY_PAGE)
    request = request_info.value
    assert request.getHeader("user-agent") == "foobar"
    await context.close()


async def test_UA_005_custom_user_agent_for_download(
    server: Server,
    context_factory: Callable[..., Awaitable[BrowserContext]],
    browser_version: str,
    browser_name: str,
) -> None:
    if browser_name == "chromium" and chromium_version_less_than(
        browser_version, "116.0.0.0"
    ):
        pytest.skip("https://chromium-review.googlesource.com/c/chromium/src/+/4554578")

    def handle(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "application/octet-stream")
        request.setHeader("Content-Disposition", "attachment")
        request.write(b"Hello world")
        request.finish()

    server.set_route("/download", handle)

    context = await context_factory(user_agent="MyCustomUA")
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        '<a id="download" download="name" href="/download">Download</a>'
    )
    server_request = asyncio.create_task(server.wait_for_request("/download"))
    try:
        await page.click("#download")
    except Error:
        pass
    req = await server_request
    assert req.getHeader("user-agent") == "MyCustomUA"


async def test_UA_006_should_work_for_navigator_user_agent_data_and_sec_ch_ua_headers(
    playwright: Playwright, browser_name: str, browser: Browser, server: Server
) -> None:
    if browser_name != "chromium":
        pytest.skip("This API is Chromium-only")

    context = await browser.new_context()
    page = await context.new_page()
    with server.expect_request("/empty.html") as request_info:
        await page.goto(server.EMPTY_PAGE)
    request = request_info.value
    assert '"Chromium"' in must(request.getHeader("sec-ch-ua"))
    assert request.getHeader("sec-ch-ua-mobile") == "?0"
    assert request.getHeader("sec-ch-ua-platform")
    user_agent_data = await page.evaluate(
        "() => window.navigator.userAgentData.toJSON()"
    )
    assert user_agent_data["mobile"] is False
    await context.close()

    context = await browser.new_context(**playwright.devices["Pixel 7"])
    page = await context.new_page()
    with server.expect_request("/empty.html") as request_info:
        await page.goto(server.EMPTY_PAGE)
    request = request_info.value
    assert '"Chromium"' in must(request.getHeader("sec-ch-ua"))
    assert request.getHeader("sec-ch-ua-mobile") == "?1"
    assert request.getHeader("sec-ch-ua-platform") == '"Android"'
    user_agent_data = await page.evaluate(
        "() => window.navigator.userAgentData.toJSON()"
    )
    assert user_agent_data["mobile"] is True
    assert user_agent_data["platform"] == "Android"
    await context.close()
