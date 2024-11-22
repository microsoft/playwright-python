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

import pytest

from playwright.sync_api import Browser, Page, Playwright, Route
from tests.server import Server


def test_response_server_addr(page: Page, server: Server) -> None:
    response = page.goto(server.EMPTY_PAGE)
    assert response
    server_addr = response.server_addr()
    assert server_addr
    assert server_addr["port"] == server.PORT
    assert server_addr["ipAddress"] in ["127.0.0.1", "[::1]"]


def test_response_security_details(
    browser: Browser,
    https_server: Server,
    browser_name: str,
    is_win: bool,
    is_linux: bool,
) -> None:
    if (browser_name == "webkit" and is_linux) or (browser_name == "webkit" and is_win):
        pytest.skip("https://github.com/microsoft/playwright/issues/6759")
    page = browser.new_page(ignore_https_errors=True)
    response = page.goto(https_server.EMPTY_PAGE)
    assert response
    response.finished()
    security_details = response.security_details()
    assert security_details
    if browser_name == "webkit" and is_win:
        assert security_details == {
            "subjectName": "puppeteer-tests",
            "validFrom": 1550084863,
            "validTo": -1,
        }
    elif browser_name == "webkit":
        assert security_details == {
            "protocol": "TLS 1.3",
            "subjectName": "puppeteer-tests",
            "validFrom": 1550084863,
            "validTo": 33086084863,
        }
    else:
        assert security_details == {
            "issuer": "puppeteer-tests",
            "protocol": "TLS 1.3",
            "subjectName": "puppeteer-tests",
            "validFrom": 1550084863,
            "validTo": 33086084863,
        }
    page.close()


def test_response_security_details_none_without_https(
    page: Page, server: Server
) -> None:
    response = page.goto(server.EMPTY_PAGE)
    assert response
    security_details = response.security_details()
    assert security_details is None


def test_should_fulfill_with_global_fetch_result(
    page: Page, playwright: Playwright, server: Server
) -> None:
    def handle_request(route: Route) -> None:
        request = playwright.request.new_context()
        response = request.get(server.PREFIX + "/simple.json")
        route.fulfill(response=response)
        request.dispose()

    page.route("**/*", handle_request)

    response = page.goto(server.EMPTY_PAGE)
    assert response
    assert response.status == 200
    assert response.json() == {"foo": "bar"}


def test_should_report_if_request_was_from_service_worker(
    page: Page, server: Server
) -> None:
    response = page.goto(server.PREFIX + "/serviceworkers/fetch/sw.html")
    assert response
    assert not response.from_service_worker
    page.evaluate("() => window.activationPromise")
    with page.expect_response("**/example.txt") as response_info:
        page.evaluate("() => fetch('/example.txt')")
    assert response_info.value.from_service_worker
