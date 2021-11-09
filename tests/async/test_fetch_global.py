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
import json
from pathlib import Path

import pytest

from playwright.async_api import APIResponse, Error, Playwright
from tests.server import Server


@pytest.mark.parametrize(
    "method", ["fetch", "delete", "get", "head", "patch", "post", "put"]
)
async def test_should_work(playwright: Playwright, method: str, server: Server):
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


async def test_should_dispose_global_request(playwright: Playwright, server: Server):
    request = await playwright.request.new_context()
    response = await request.get(server.PREFIX + "/simple.json")
    assert await response.json() == {"foo": "bar"}
    await response.dispose()
    with pytest.raises(Error, match="Response has been disposed"):
        await response.body()


async def test_should_support_global_user_agent_option(
    playwright: Playwright, server: Server
):
    request = await playwright.request.new_context(user_agent="My Agent")
    response = await request.get(server.PREFIX + "/empty.html")
    [request, _] = await asyncio.gather(
        server.wait_for_request("/empty.html"),
        request.get(server.EMPTY_PAGE),
    )
    assert response.ok is True
    assert response.url == server.EMPTY_PAGE
    assert request.getHeader("user-agent") == "My Agent"


async def test_should_support_global_timeout_option(
    playwright: Playwright, server: Server
):
    request = await playwright.request.new_context(timeout=1)
    server.set_route("/empty.html", lambda req: None)
    with pytest.raises(Error, match="Request timed out after 1ms"):
        await request.get(server.EMPTY_PAGE)


async def test_should_propagate_extra_http_headers_with_redirects(
    playwright: Playwright, server: Server
):
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
):
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
):
    server.set_auth("/empty.html", "user", "pass")
    request = await playwright.request.new_context(
        http_credentials={"username": "user", "password": "wrong"}
    )
    response = await request.get(server.EMPTY_PAGE)
    assert response.status == 401
    assert response.ok is False


async def test_should_support_global_ignore_https_errors_option(
    playwright: Playwright, https_server: Server
):
    request = await playwright.request.new_context(ignore_https_errors=True)
    response = await request.get(https_server.EMPTY_PAGE)
    assert response.status == 200
    assert response.ok is True
    assert response.url == https_server.EMPTY_PAGE
    await response.dispose()


async def test_should_resolve_url_relative_to_global_base_url_option(
    playwright: Playwright, server: Server
):
    request = await playwright.request.new_context(base_url=server.PREFIX)
    response = await request.get("/empty.html")
    assert response.status == 200
    assert response.ok is True
    assert response.url == server.EMPTY_PAGE
    await response.dispose()


async def test_should_use_playwright_as_a_user_agent(
    playwright: Playwright, server: Server
):
    request = await playwright.request.new_context()
    [server_req, _] = await asyncio.gather(
        server.wait_for_request("/empty.html"),
        request.get(server.EMPTY_PAGE),
    )
    assert str(server_req.getHeader("User-Agent")).startswith("Playwright/")
    await request.dispose()


async def test_should_return_empty_body(playwright: Playwright, server: Server):
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
):
    expected = {
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
