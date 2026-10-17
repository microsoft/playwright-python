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

from typing import Any, Callable, Dict

import pytest

from playwright.sync_api import Browser, BrowserContext, Error, Page, Playwright
from tests.server import ExpectResponse, Server, TestServerRequest
from tests.utils import chromium_version_less_than, must

from ..utils import Utils


def wait_for_server_request(
    page: Page, request_info: ExpectResponse[TestServerRequest]
) -> TestServerRequest:
    """Waits until the test server gets the request of server.expect_request()."""
    while True:
        try:
            return request_info.value
        except ValueError:
            page.wait_for_timeout(10)


def test_UA_001_should_work(browser: Browser, server: Server) -> None:
    context = browser.new_context()
    page = context.new_page()
    assert "Mozilla" in page.evaluate("() => navigator.userAgent")
    context.close()

    context = browser.new_context(user_agent="foobar")
    page = context.new_page()
    with server.expect_request("/empty.html") as request_info:
        page.goto(server.EMPTY_PAGE)
    request = request_info.value
    assert request.getHeader("user-agent") == "foobar"
    context.close()


def test_UA_002_should_work_for_subframes(
    browser: Browser, server: Server, utils: Utils
) -> None:
    context = browser.new_context()
    page = context.new_page()
    assert "Mozilla" in page.evaluate("() => navigator.userAgent")
    context.close()

    context = browser.new_context(user_agent="foobar")
    page = context.new_page()
    with server.expect_request("/empty.html") as request_info:
        utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    request = request_info.value
    assert request.getHeader("user-agent") == "foobar"
    context.close()


def test_UA_003_should_emulate_device_user_agent(
    browser: Browser, server: Server, playwright: Playwright
) -> None:
    context = browser.new_context()
    page = context.new_page()
    page.goto(server.PREFIX + "/mobile.html")
    assert "iPhone" not in page.evaluate("() => navigator.userAgent")
    context.close()

    context = browser.new_context(
        user_agent=playwright.devices["iPhone 6"]["user_agent"]
    )
    page = context.new_page()
    page.goto(server.PREFIX + "/mobile.html")
    assert "iPhone" in page.evaluate("() => navigator.userAgent")
    context.close()


def test_UA_004_should_make_a_copy_of_default_options(
    browser: Browser, server: Server
) -> None:
    options: Dict[str, Any] = {"user_agent": "foobar"}
    context = browser.new_context(**options)
    options["user_agent"] = "wrong"
    page = context.new_page()
    with server.expect_request("/empty.html") as request_info:
        page.goto(server.EMPTY_PAGE)
    request = request_info.value
    assert request.getHeader("user-agent") == "foobar"
    context.close()


def test_UA_005_custom_user_agent_for_download(
    server: Server,
    context_factory: Callable[..., BrowserContext],
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

    context = context_factory(user_agent="MyCustomUA")
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)
    page.set_content('<a id="download" download="name" href="/download">Download</a>')
    with server.expect_request("/download") as server_request:
        try:
            page.click("#download")
        except Error:
            pass
    req = wait_for_server_request(page, server_request)
    assert req.getHeader("user-agent") == "MyCustomUA"


def test_UA_006_should_work_for_navigator_user_agent_data_and_sec_ch_ua_headers(
    playwright: Playwright, browser_name: str, browser: Browser, server: Server
) -> None:
    if browser_name != "chromium":
        pytest.skip("This API is Chromium-only")

    context = browser.new_context()
    page = context.new_page()
    with server.expect_request("/empty.html") as request_info:
        page.goto(server.EMPTY_PAGE)
    request = request_info.value
    assert '"Chromium"' in must(request.getHeader("sec-ch-ua"))
    assert request.getHeader("sec-ch-ua-mobile") == "?0"
    assert request.getHeader("sec-ch-ua-platform")
    user_agent_data = page.evaluate("() => window.navigator.userAgentData.toJSON()")
    assert user_agent_data["mobile"] is False
    context.close()

    context = browser.new_context(**playwright.devices["Pixel 7"])
    page = context.new_page()
    with server.expect_request("/empty.html") as request_info:
        page.goto(server.EMPTY_PAGE)
    request = request_info.value
    assert '"Chromium"' in must(request.getHeader("sec-ch-ua"))
    assert request.getHeader("sec-ch-ua-mobile") == "?1"
    assert request.getHeader("sec-ch-ua-platform") == '"Android"'
    user_agent_data = page.evaluate("() => window.navigator.userAgentData.toJSON()")
    assert user_agent_data["mobile"] is True
    assert user_agent_data["platform"] == "Android"
    context.close()
