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

import asyncio
import base64
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pytest

from playwright.async_api import APIResponse, Error, Playwright, StorageState
from tests.server import Server, TestServerRequest


@pytest.mark.parametrize(
    "method", ["fetch", "delete", "get", "head", "patch", "post", "put"]
)
async def test_should_work(playwright: Playwright, method: str, server: Server) -> None:
    request = await playwright.request.new_context()
    response: APIResponse = await getattr(request, method)(
        server.PREFIX + "/simple.json"
    )
    assert response.status == 200
    assert response.status_text == "OK"
    assert response.ok is True
    assert response.url == server.PREFIX + "/simple.json"
    assert response.headers["content-type"] == "application/json"
    assert {
        "name": "Content-Type",
        "value": "application/json",
    } in response.headers_array
    assert await response.text() == ("" if method == "head" else '{"foo": "bar"}\n')


async def test_should_dispose_global_request(
    playwright: Playwright, server: Server
) -> None:
    request = await playwright.request.new_context()
    response = await request.get(server.PREFIX + "/simple.json")
    assert await response.json() == {"foo": "bar"}
    await response.dispose()
    with pytest.raises(Error, match="Response has been disposed"):
        await response.body()


async def test_should_dispose_with_custom_error_message(
    playwright: Playwright, server: Server
) -> None:
    request = await playwright.request.new_context()
    await request.dispose(reason="My reason")
    with pytest.raises(Error, match="My reason"):
        await request.get(server.EMPTY_PAGE)


async def test_should_support_global_user_agent_option(
    playwright: Playwright, server: Server
) -> None:
    api_request_context = await playwright.request.new_context(user_agent="My Agent")
    response = await api_request_context.get(server.PREFIX + "/empty.html")
    [request, _] = await asyncio.gather(
        server.wait_for_request("/empty.html"),
        api_request_context.get(server.EMPTY_PAGE),
    )
    assert response.ok is True
    assert response.url == server.EMPTY_PAGE
    assert request.getHeader("user-agent") == "My Agent"


async def test_should_support_global_timeout_option(
    playwright: Playwright, server: Server
) -> None:
    request = await playwright.request.new_context(timeout=100)
    server.set_route("/empty.html", lambda req: None)
    with pytest.raises(Error, match="Request timed out after 100ms"):
        await request.get(server.EMPTY_PAGE)


async def test_should_propagate_extra_http_headers_with_redirects(
    playwright: Playwright, server: Server
) -> None:
    server.set_redirect("/a/redirect1", "/b/c/redirect2")
    server.set_redirect("/b/c/redirect2", "/simple.json")
    request = await playwright.request.new_context(
        extra_http_headers={"My-Secret": "Value"}
    )
    [req1, req2, req3, _] = await asyncio.gather(
        server.wait_for_request("/a/redirect1"),
        server.wait_for_request("/b/c/redirect2"),
        server.wait_for_request("/simple.json"),
        request.get(f"{server.PREFIX}/a/redirect1"),
    )
    assert req1.getHeader("my-secret") == "Value"
    assert req2.getHeader("my-secret") == "Value"
    assert req3.getHeader("my-secret") == "Value"


async def test_should_support_global_http_credentials_option(
    playwright: Playwright, server: Server
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    request1 = await playwright.request.new_context()
    response1 = await request1.get(server.EMPTY_PAGE)
    assert response1.status == 401
    await response1.dispose()

    request2 = await playwright.request.new_context(
        http_credentials={"username": "user", "password": "pass"}
    )
    response2 = await request2.get(server.EMPTY_PAGE)
    assert response2.status == 200
    assert response2.ok is True
    await response2.dispose()


async def test_should_return_error_with_wrong_credentials(
    playwright: Playwright, server: Server
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    request = await playwright.request.new_context(
        http_credentials={"username": "user", "password": "wrong"}
    )
    response = await request.get(server.EMPTY_PAGE)
    assert response.status == 401
    assert response.ok is False


async def test_should_work_with_correct_credentials_and_matching_origin(
    playwright: Playwright, server: Server
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    request = await playwright.request.new_context(
        http_credentials={
            "username": "user",
            "password": "pass",
            "origin": server.PREFIX,
        }
    )
    response = await request.get(server.EMPTY_PAGE)
    assert response.status == 200
    await response.dispose()


async def test_should_work_with_correct_credentials_and_matching_origin_case_insensitive(
    playwright: Playwright, server: Server
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    request = await playwright.request.new_context(
        http_credentials={
            "username": "user",
            "password": "pass",
            "origin": server.PREFIX.upper(),
        }
    )
    response = await request.get(server.EMPTY_PAGE)
    assert response.status == 200
    await response.dispose()


async def test_should_return_error_with_correct_credentials_and_mismatching_scheme(
    playwright: Playwright, server: Server
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    request = await playwright.request.new_context(
        http_credentials={
            "username": "user",
            "password": "pass",
            "origin": server.PREFIX.replace("http://", "https://"),
        }
    )
    response = await request.get(server.EMPTY_PAGE)
    assert response.status == 401
    await response.dispose()


async def test_should_return_error_with_correct_credentials_and_mismatching_hostname(
    playwright: Playwright, server: Server
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    hostname = urlparse(server.PREFIX).hostname
    assert hostname
    origin = server.PREFIX.replace(hostname, "mismatching-hostname")
    request = await playwright.request.new_context(
        http_credentials={"username": "user", "password": "pass", "origin": origin}
    )
    response = await request.get(server.EMPTY_PAGE)
    assert response.status == 401
    await response.dispose()


async def test_should_return_error_with_correct_credentials_and_mismatching_port(
    playwright: Playwright, server: Server
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    origin = server.PREFIX.replace(str(server.PORT), str(server.PORT + 1))
    request = await playwright.request.new_context(
        http_credentials={"username": "user", "password": "pass", "origin": origin}
    )
    response = await request.get(server.EMPTY_PAGE)
    assert response.status == 401
    await response.dispose()


async def test_support_http_credentials_send_immediately(
    playwright: Playwright, server: Server
) -> None:
    request = await playwright.request.new_context(
        http_credentials={
            "username": "user",
            "password": "pass",
            "origin": server.PREFIX.upper(),
            "send": "always",
        }
    )
    server_request, response = await asyncio.gather(
        server.wait_for_request("/empty.html"), request.get(server.EMPTY_PAGE)
    )
    assert (
        server_request.getHeader("authorization")
        == "Basic " + base64.b64encode(b"user:pass").decode()
    )
    assert response.status == 200

    server_request, response = await asyncio.gather(
        server.wait_for_request("/empty.html"),
        request.get(server.CROSS_PROCESS_PREFIX + "/empty.html"),
    )
    # Not sent to another origin.
    assert server_request.getHeader("authorization") is None
    assert response.status == 200


async def test_should_support_global_ignore_https_errors_option(
    playwright: Playwright, https_server: Server
) -> None:
    request = await playwright.request.new_context(ignore_https_errors=True)
    response = await request.get(https_server.EMPTY_PAGE)
    assert response.status == 200
    assert response.ok is True
    assert response.url == https_server.EMPTY_PAGE
    await response.dispose()


async def test_should_resolve_url_relative_to_global_base_url_option(
    playwright: Playwright, server: Server
) -> None:
    request = await playwright.request.new_context(base_url=server.PREFIX)
    response = await request.get("/empty.html")
    assert response.status == 200
    assert response.ok is True
    assert response.url == server.EMPTY_PAGE
    await response.dispose()


async def test_should_use_playwright_as_a_user_agent(
    playwright: Playwright, server: Server
) -> None:
    request = await playwright.request.new_context()
    [server_req, _] = await asyncio.gather(
        server.wait_for_request("/empty.html"),
        request.get(server.EMPTY_PAGE),
    )
    assert str(server_req.getHeader("User-Agent")).startswith("Playwright/")
    await request.dispose()


async def test_should_return_empty_body(playwright: Playwright, server: Server) -> None:
    request = await playwright.request.new_context()
    response = await request.get(server.EMPTY_PAGE)
    body = await response.body()
    assert len(body) == 0
    assert await response.text() == ""
    await request.dispose()
    with pytest.raises(Error, match="Response has been disposed"):
        await response.body()


async def test_storage_state_should_round_trip_through_file(
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
    request = await playwright.request.new_context(storage_state=expected)
    path = tmpdir / "storage-state.json"
    actual = await request.storage_state(path=path)
    assert actual == expected

    written = path.read_text("utf8")
    assert json.loads(written) == expected

    request2 = await playwright.request.new_context(storage_state=path)
    state2 = await request2.storage_state()
    assert state2 == expected


serialization_data = [
    [{"foo": "bar"}],
    [["foo", "bar", 2021]],
    ["foo"],
    [True],
    [2021],
]


@pytest.mark.parametrize("serialization", serialization_data)
async def test_should_json_stringify_body_when_content_type_is_application_json(
    playwright: Playwright, server: Server, serialization: Any
) -> None:
    request = await playwright.request.new_context()
    [req, _] = await asyncio.gather(
        server.wait_for_request("/empty.html"),
        request.post(
            server.EMPTY_PAGE,
            headers={"content-type": "application/json"},
            data=serialization,
        ),
    )
    body = req.post_body
    assert body
    assert body.decode() == json.dumps(serialization)
    await request.dispose()


@pytest.mark.parametrize("serialization", serialization_data)
async def test_should_not_double_stringify_body_when_content_type_is_application_json(
    playwright: Playwright, server: Server, serialization: Any
) -> None:
    request = await playwright.request.new_context()
    stringified_value = json.dumps(serialization)
    [req, _] = await asyncio.gather(
        server.wait_for_request("/empty.html"),
        request.post(
            server.EMPTY_PAGE,
            headers={"content-type": "application/json"},
            data=stringified_value,
        ),
    )

    body = req.post_body
    assert body
    assert body.decode() == stringified_value
    await request.dispose()


async def test_should_accept_already_serialized_data_as_bytes_when_content_type_is_application_json(
    playwright: Playwright, server: Server
) -> None:
    request = await playwright.request.new_context()
    stringified_value = json.dumps({"foo": "bar"}).encode()
    [req, _] = await asyncio.gather(
        server.wait_for_request("/empty.html"),
        request.post(
            server.EMPTY_PAGE,
            headers={"content-type": "application/json"},
            data=stringified_value,
        ),
    )
    body = req.post_body
    assert body == stringified_value
    await request.dispose()


async def test_should_contain_default_user_agent(
    playwright: Playwright, server: Server
) -> None:
    request = await playwright.request.new_context()
    [server_request, _] = await asyncio.gather(
        server.wait_for_request("/empty.html"),
        request.get(server.EMPTY_PAGE),
    )
    user_agent = server_request.getHeader("user-agent")
    assert user_agent
    assert "python" in user_agent
    assert f"{sys.version_info.major}.{sys.version_info.minor}" in user_agent


async def test_should_throw_an_error_when_max_redirects_is_exceeded(
    playwright: Playwright, server: Server
) -> None:
    server.set_redirect("/a/redirect1", "/b/c/redirect2")
    server.set_redirect("/b/c/redirect2", "/b/c/redirect3")
    server.set_redirect("/b/c/redirect3", "/b/c/redirect4")
    server.set_redirect("/b/c/redirect4", "/simple.json")

    request = await playwright.request.new_context()
    for method in ["GET", "PUT", "POST", "OPTIONS", "HEAD", "PATCH"]:
        for max_redirects in [1, 2, 3]:
            with pytest.raises(Error) as exc_info:
                await request.fetch(
                    server.PREFIX + "/a/redirect1",
                    method=method,
                    max_redirects=max_redirects,
                )
            assert "Max redirect count exceeded" in str(exc_info)


async def test_should_not_follow_redirects_when_max_redirects_is_set_to_0(
    playwright: Playwright, server: Server
) -> None:
    server.set_redirect("/a/redirect1", "/b/c/redirect2")
    server.set_redirect("/b/c/redirect2", "/simple.json")

    request = await playwright.request.new_context()
    for method in ["GET", "PUT", "POST", "OPTIONS", "HEAD", "PATCH"]:
        response = await request.fetch(
            server.PREFIX + "/a/redirect1", method=method, max_redirects=0
        )
        assert response.headers["location"] == "/b/c/redirect2"
        assert response.status == 302


async def test_should_throw_an_error_when_max_redirects_is_less_than_0(
    playwright: Playwright,
    server: Server,
) -> None:
    request = await playwright.request.new_context()
    for method in ["GET", "PUT", "POST", "OPTIONS", "HEAD", "PATCH"]:
        with pytest.raises(AssertionError) as exc_info:
            await request.fetch(
                server.PREFIX + "/a/redirect1", method=method, max_redirects=-1
            )
        assert "'max_redirects' must be greater than or equal to '0'" in str(exc_info)


async def test_should_serialize_request_data(
    playwright: Playwright, server: Server
) -> None:
    request = await playwright.request.new_context()
    server.set_route("/echo", lambda req: (req.write(req.post_body), req.finish()))
    for data, expected in [
        ({"foo": None}, '{"foo": null}'),
        ([], "[]"),
        ({}, "{}"),
        ("", ""),
    ]:
        response = await request.post(server.PREFIX + "/echo", data=data)
        assert response.status == 200
        assert await response.text() == expected
    await request.dispose()


async def test_should_retry_ECONNRESET(playwright: Playwright, server: Server) -> None:
    request_count = 0

    def _handle_request(req: TestServerRequest) -> None:
        nonlocal request_count
        request_count += 1
        if request_count <= 3:
            assert req.transport
            req.transport.abortConnection()
            return
        req.setHeader("content-type", "text/plain")
        req.write(b"Hello!")
        req.finish()

    server.set_route("/test", _handle_request)
    request = await playwright.request.new_context()
    response = await request.fetch(server.PREFIX + "/test", max_retries=3)
    assert response.status == 200
    assert await response.text() == "Hello!"
    assert request_count == 4
    await request.dispose()
