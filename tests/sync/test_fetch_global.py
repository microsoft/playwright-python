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

import json
from pathlib import Path
from urllib.parse import urlparse

import pytest

from playwright.sync_api import APIResponse, Error, Playwright, StorageState
from tests.server import Server


@pytest.mark.parametrize(
    "method", ["fetch", "delete", "get", "head", "patch", "post", "put"]
)
def test_should_work(playwright: Playwright, method: str, server: Server) -> None:
    request = playwright.request.new_context()
    response: APIResponse = getattr(request, method)(server.PREFIX + "/simple.json")
    assert response.status == 200
    assert response.status_text == "OK"
    assert response.ok is True
    assert response.url == server.PREFIX + "/simple.json"
    assert response.headers["content-type"] == "application/json"
    assert {
        "name": "Content-Type",
        "value": "application/json",
    } in response.headers_array
    assert response.text() == ("" if method == "head" else '{"foo": "bar"}\n')


def test_should_dispose_global_request(playwright: Playwright, server: Server) -> None:
    request = playwright.request.new_context()
    response = request.get(server.PREFIX + "/simple.json")
    assert response.json() == {"foo": "bar"}
    response.dispose()
    with pytest.raises(Error, match="Response has been disposed"):
        response.body()


def test_should_support_global_user_agent_option(
    playwright: Playwright, server: Server
) -> None:
    request = playwright.request.new_context(user_agent="My Agent")
    response = request.get(server.PREFIX + "/empty.html")
    with server.expect_request("/empty.html") as server_req:
        request.get(server.EMPTY_PAGE)
    assert response.ok is True
    assert response.url == server.EMPTY_PAGE

    assert server_req.value.getHeader("user-agent") == "My Agent"


def test_should_support_global_timeout_option(
    playwright: Playwright, server: Server
) -> None:
    request = playwright.request.new_context(timeout=100)
    server.set_route("/empty.html", lambda req: None)
    with pytest.raises(Error, match="Request timed out after 100ms"):
        request.get(server.EMPTY_PAGE)


def test_should_propagate_extra_http_headers_with_redirects(
    playwright: Playwright, server: Server
) -> None:
    server.set_redirect("/a/redirect1", "/b/c/redirect2")
    server.set_redirect("/b/c/redirect2", "/simple.json")
    request = playwright.request.new_context(extra_http_headers={"My-Secret": "Value"})
    with server.expect_request("/a/redirect1") as server_req1:
        with server.expect_request("/b/c/redirect2") as server_req2:
            with server.expect_request("/simple.json") as server_req3:
                request.get(f"{server.PREFIX}/a/redirect1")
    assert server_req1.value.getHeader("my-secret") == "Value"
    assert server_req2.value.getHeader("my-secret") == "Value"
    assert server_req3.value.getHeader("my-secret") == "Value"


def test_should_support_global_http_credentials_option(
    playwright: Playwright, server: Server
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    request1 = playwright.request.new_context()
    response1 = request1.get(server.EMPTY_PAGE)
    assert response1.status == 401
    response1.dispose()

    request2 = playwright.request.new_context(
        http_credentials={"username": "user", "password": "pass"}
    )
    response2 = request2.get(server.EMPTY_PAGE)
    assert response2.status == 200
    assert response2.ok is True
    response2.dispose()


def test_should_return_error_with_wrong_credentials(
    playwright: Playwright, server: Server
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    request = playwright.request.new_context(
        http_credentials={"username": "user", "password": "wrong"}
    )
    response = request.get(server.EMPTY_PAGE)
    assert response.status == 401
    assert response.ok is False


def test_should_work_with_correct_credentials_and_matching_origin(
    playwright: Playwright, server: Server
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    request = playwright.request.new_context(
        http_credentials={
            "username": "user",
            "password": "pass",
            "origin": server.PREFIX,
        }
    )
    response = request.get(server.EMPTY_PAGE)
    assert response.status == 200
    response.dispose()


def test_should_work_with_correct_credentials_and_matching_origin_case_insensitive(
    playwright: Playwright, server: Server
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    request = playwright.request.new_context(
        http_credentials={
            "username": "user",
            "password": "pass",
            "origin": server.PREFIX.upper(),
        }
    )
    response = request.get(server.EMPTY_PAGE)
    assert response.status == 200
    response.dispose()


def test_should_return_error_with_correct_credentials_and_mismatching_scheme(
    playwright: Playwright, server: Server
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    request = playwright.request.new_context(
        http_credentials={
            "username": "user",
            "password": "pass",
            "origin": server.PREFIX.replace("http://", "https://"),
        }
    )
    response = request.get(server.EMPTY_PAGE)
    assert response.status == 401
    response.dispose()


def test_should_return_error_with_correct_credentials_and_mismatching_hostname(
    playwright: Playwright, server: Server
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    hostname = urlparse(server.PREFIX).hostname
    assert hostname
    origin = server.PREFIX.replace(hostname, "mismatching-hostname")
    request = playwright.request.new_context(
        http_credentials={"username": "user", "password": "pass", "origin": origin}
    )
    response = request.get(server.EMPTY_PAGE)
    assert response.status == 401
    response.dispose()


def test_should_return_error_with_correct_credentials_and_mismatching_port(
    playwright: Playwright, server: Server
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    origin = server.PREFIX.replace(str(server.PORT), str(server.PORT + 1))
    request = playwright.request.new_context(
        http_credentials={"username": "user", "password": "pass", "origin": origin}
    )
    response = request.get(server.EMPTY_PAGE)
    assert response.status == 401
    response.dispose()


def test_should_support_global_ignore_https_errors_option(
    playwright: Playwright, https_server: Server
) -> None:
    request = playwright.request.new_context(ignore_https_errors=True)
    response = request.get(https_server.EMPTY_PAGE)
    assert response.status == 200
    assert response.ok is True
    assert response.url == https_server.EMPTY_PAGE
    response.dispose()


def test_should_resolve_url_relative_to_global_base_url_option(
    playwright: Playwright, server: Server
) -> None:
    request = playwright.request.new_context(base_url=server.PREFIX)
    response = request.get("/empty.html")
    assert response.status == 200
    assert response.ok is True
    assert response.url == server.EMPTY_PAGE
    response.dispose()


def test_should_use_playwright_as_a_user_agent(
    playwright: Playwright, server: Server
) -> None:
    request = playwright.request.new_context()
    with server.expect_request("/empty.html") as server_req:
        request.get(server.EMPTY_PAGE)
    assert str(server_req.value.getHeader("User-Agent")).startswith("Playwright/")
    request.dispose()


def test_should_return_empty_body(playwright: Playwright, server: Server) -> None:
    request = playwright.request.new_context()
    response = request.get(server.EMPTY_PAGE)
    body = response.body()
    assert len(body) == 0
    assert response.text() == ""
    request.dispose()
    with pytest.raises(Error, match="Response has been disposed"):
        response.body()


def test_storage_state_should_round_trip_through_file(
    playwright: Playwright, tmpdir: Path
) -> None:
    expected: StorageState = {
        "cookies": [
            {
                "name": "a",
                "value": "b",
                "domain": "a.b.one.com",
                "path": "/",
                "expires": -1,
                "httpOnly": False,
                "secure": False,
                "sameSite": "Lax",
            }
        ],
        "origins": [],
    }
    request = playwright.request.new_context(storage_state=expected)
    path = tmpdir / "storage-state.json"
    actual = request.storage_state(path=path)
    assert actual == expected

    written = path.read_text("utf8")
    assert json.loads(written) == expected

    request2 = playwright.request.new_context(storage_state=path)
    state2 = request2.storage_state()
    assert state2 == expected


def test_should_throw_an_error_when_max_redirects_is_exceeded(
    playwright: Playwright, server: Server
) -> None:
    server.set_redirect("/a/redirect1", "/b/c/redirect2")
    server.set_redirect("/b/c/redirect2", "/b/c/redirect3")
    server.set_redirect("/b/c/redirect3", "/b/c/redirect4")
    server.set_redirect("/b/c/redirect4", "/simple.json")

    request = playwright.request.new_context()
    for method in ["GET", "PUT", "POST", "OPTIONS", "HEAD", "PATCH"]:
        for max_redirects in [1, 2, 3]:
            with pytest.raises(Error) as exc_info:
                request.fetch(
                    server.PREFIX + "/a/redirect1",
                    method=method,
                    max_redirects=max_redirects,
                )
            assert "Max redirect count exceeded" in str(exc_info)


def test_should_not_follow_redirects_when_max_redirects_is_set_to_0(
    playwright: Playwright, server: Server
) -> None:
    server.set_redirect("/a/redirect1", "/b/c/redirect2")
    server.set_redirect("/b/c/redirect2", "/simple.json")

    request = playwright.request.new_context()
    for method in ["GET", "PUT", "POST", "OPTIONS", "HEAD", "PATCH"]:
        response = request.fetch(
            server.PREFIX + "/a/redirect1", method=method, max_redirects=0
        )
        assert response.headers["location"] == "/b/c/redirect2"
        assert response.status == 302


def test_should_throw_an_error_when_max_redirects_is_less_than_0(
    playwright: Playwright,
    server: Server,
) -> None:
    request = playwright.request.new_context()
    for method in ["GET", "PUT", "POST", "OPTIONS", "HEAD", "PATCH"]:
        with pytest.raises(AssertionError) as exc_info:
            request.fetch(
                server.PREFIX + "/a/redirect1", method=method, max_redirects=-1
            )
        assert "'max_redirects' must be greater than or equal to '0'" in str(exc_info)


def test_should_serialize_null_values_in_json(
    playwright: Playwright, server: Server
) -> None:
    request = playwright.request.new_context()
    server.set_route("/echo", lambda req: (req.write(req.post_body), req.finish()))
    response = request.post(server.PREFIX + "/echo", data={"foo": None})
    assert response.status == 200
    assert response.text() == '{"foo": null}'
    request.dispose()
