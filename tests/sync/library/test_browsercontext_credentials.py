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

"""Port of tests/library/browsercontext-credentials.spec.ts."""

from urllib.parse import urlparse

import pytest

from playwright.sync_api import Browser, Error, Page
from tests.server import Server, TestServerRequest
from tests.utils import must


@pytest.fixture
def fails_on_401(browser_name: str, is_headless_shell: bool) -> bool:
    return browser_name == "chromium" and not is_headless_shell


def expect_auth_failure(page: Page, url: str, fails_on_401: bool) -> None:
    """The navigation fails, or answers 401, as `page.goto(url).catch(e => e)` checks."""
    if fails_on_401:
        with pytest.raises(Error) as exc_info:
            page.goto(url)
        assert "net::ERR_INVALID_AUTH_CREDENTIALS" in exc_info.value.message
    else:
        response = page.goto(url)
        assert must(response).status == 401


def test_AU_001_should_fail_without_credentials(
    browser: Browser, server: Server, fails_on_401: bool
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    context = browser.new_context()
    page = context.new_page()
    expect_auth_failure(page, server.EMPTY_PAGE, fails_on_401)
    context.close()


def test_AU_004_should_work_with_correct_credentials_smoke(
    browser: Browser, server: Server
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    context = browser.new_context(
        http_credentials={"username": "user", "password": "pass"}
    )
    page = context.new_page()
    response = page.goto(server.EMPTY_PAGE)
    assert must(response).status == 200
    context.close()


def test_AU_005_should_fail_with_wrong_credentials(
    browser: Browser, server: Server
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    context = browser.new_context(
        http_credentials={"username": "foo", "password": "bar"}
    )
    page = context.new_page()
    response = page.goto(server.EMPTY_PAGE)
    assert must(response).status == 401
    context.close()


def test_AU_006_should_return_resource_body(browser: Browser, server: Server) -> None:
    server.set_auth("/playground.html", "user", "pass")
    context = browser.new_context(
        http_credentials={"username": "user", "password": "pass"}
    )
    page = context.new_page()
    response = must(page.goto(server.PREFIX + "/playground.html"))
    assert response.status == 200
    assert page.title() == "Playground"
    assert "Playground" in (response.body()).decode()
    context.close()


def test_AU_007_should_work_with_a_single_credential_in_an_array(
    browser: Browser, server: Server
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    context = browser.new_context(
        http_credentials=[{"username": "user", "password": "pass"}]
    )
    page = context.new_page()
    response = page.goto(server.EMPTY_PAGE)
    assert must(response).status == 200
    context.close()


def test_AU_008_should_work_with_multiple_credentials_for_different_origins(
    browser: Browser, server: Server
) -> None:
    server.set_auth("/empty.html", "user1", "pass1")
    context = browser.new_context(
        http_credentials=[
            {"username": "user1", "password": "pass1", "origin": server.PREFIX},
            {
                "username": "user2",
                "password": "pass2",
                "origin": server.CROSS_PROCESS_PREFIX,
            },
        ]
    )
    page = context.new_page()
    response1 = page.goto(server.EMPTY_PAGE)
    assert must(response1).status == 200
    # Wrong credentials are picked for the other origin.
    response2 = page.goto(server.CROSS_PROCESS_PREFIX + "/empty.html")
    assert must(response2).status == 401
    context.close()


def test_AU_009_should_fall_back_to_credentials_without_origin(
    browser: Browser, server: Server
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    context = browser.new_context(
        http_credentials=[
            {
                "username": "user2",
                "password": "pass2",
                "origin": server.CROSS_PROCESS_PREFIX,
            },
            {"username": "user", "password": "pass"},
        ]
    )
    page = context.new_page()
    response1 = page.goto(server.EMPTY_PAGE)
    assert must(response1).status == 200
    # First matching entry has wrong credentials for this origin.
    response2 = page.goto(server.CROSS_PROCESS_PREFIX + "/empty.html")
    assert must(response2).status == 401
    context.close()


def test_AU_010_should_use_the_first_matching_credential(
    browser: Browser, server: Server
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    context = browser.new_context(
        http_credentials=[
            {"username": "wrong", "password": "wrong"},
            {"username": "user", "password": "pass", "origin": server.PREFIX},
        ]
    )
    page = context.new_page()
    response = page.goto(server.EMPTY_PAGE)
    assert must(response).status == 401
    context.close()


def test_AU_011_should_work_with_correct_credentials_and_matching_origin(
    browser: Browser, server: Server
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    context = browser.new_context(
        http_credentials={
            "username": "user",
            "password": "pass",
            "origin": server.PREFIX,
        }
    )
    page = context.new_page()
    response = page.goto(server.EMPTY_PAGE)
    assert must(response).status == 200
    context.close()


def test_AU_012_should_work_with_correct_credentials_and_matching_origin_case_insensitive(
    browser: Browser, server: Server
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    context = browser.new_context(
        http_credentials={
            "username": "user",
            "password": "pass",
            "origin": server.PREFIX.upper(),
        }
    )
    page = context.new_page()
    response = page.goto(server.EMPTY_PAGE)
    assert must(response).status == 200
    context.close()


def test_AU_013_should_fail_with_correct_credentials_and_mismatching_scheme(
    browser: Browser, server: Server, fails_on_401: bool
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    context = browser.new_context(
        http_credentials={
            "username": "user",
            "password": "pass",
            "origin": server.PREFIX.replace("http://", "https://"),
        }
    )
    page = context.new_page()
    expect_auth_failure(page, server.EMPTY_PAGE, fails_on_401)
    context.close()


def test_AU_014_should_fail_with_correct_credentials_and_mismatching_hostname(
    browser: Browser, server: Server, fails_on_401: bool
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    hostname = must(urlparse(server.PREFIX).hostname)
    origin = server.PREFIX.replace(hostname, "mismatching-hostname")
    context = browser.new_context(
        http_credentials={"username": "user", "password": "pass", "origin": origin}
    )
    page = context.new_page()
    expect_auth_failure(page, server.EMPTY_PAGE, fails_on_401)
    context.close()


def test_AU_015_should_fail_with_correct_credentials_and_mismatching_port(
    browser: Browser, server: Server, fails_on_401: bool
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    origin = server.PREFIX.replace(str(server.PORT), str(server.PORT + 1))
    context = browser.new_context(
        http_credentials={"username": "user", "password": "pass", "origin": origin}
    )
    page = context.new_page()
    expect_auth_failure(page, server.EMPTY_PAGE, fails_on_401)
    context.close()


def test_AU_016_should_not_override_authorization_header_set_by_the_page(
    browser: Browser, server: Server
) -> None:
    server.set_auth("/empty.html", "user", "pass")

    def handle_echo_auth(request: TestServerRequest) -> None:
        request.write((request.getHeader("authorization") or "<none>").encode())
        request.finish()

    server.set_route("/echo-auth", handle_echo_auth)
    context = browser.new_context(
        http_credentials={"username": "user", "password": "pass"}
    )
    page = context.new_page()
    response = page.goto(server.EMPTY_PAGE)
    assert must(response).status == 200
    received = page.evaluate(
        """async () => {
      const response = await fetch('/echo-auth', { headers: { 'Authorization': 'Bearer my-own-app-token' } });
      return await response.text();
    }"""
    )
    assert received == "Bearer my-own-app-token"
    context.close()
