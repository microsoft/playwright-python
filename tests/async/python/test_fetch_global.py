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

"""Python only: tests of behaviors that no upstream test covers."""

import asyncio
import sys

import pytest

from playwright.async_api import Error, Playwright
from tests.server import Server


async def test_should_dispose_with_custom_error_message(
    playwright: Playwright, server: Server
) -> None:
    request = await playwright.request.new_context()
    await request.dispose(reason="My reason")
    with pytest.raises(Error, match="My reason"):
        await request.get(server.EMPTY_PAGE)


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


async def test_should_json_stringify_string_body_when_content_type_is_application_json(
    playwright: Playwright, server: Server
) -> None:
    request = await playwright.request.new_context()
    [req, _] = await asyncio.gather(
        server.wait_for_request("/empty.html"),
        request.post(
            server.EMPTY_PAGE,
            headers={"content-type": "application/json"},
            data="foo",
        ),
    )
    assert req.post_body == b'"foo"'
    # https://github.com/microsoft/playwright/issues/43329
    # NaN is not valid JSON, even though json.loads() accepts it.
    [req, _] = await asyncio.gather(
        server.wait_for_request("/empty.html"),
        request.post(
            server.EMPTY_PAGE,
            headers={"content-type": "application/json"},
            data="NaN",
        ),
    )
    assert req.post_body == b'"NaN"'
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


@pytest.mark.parametrize("value", [float("inf"), float("-inf"), float("nan")])
async def test_should_reject_non_finite_floats_in_request_data(
    playwright: Playwright, server: Server, value: float
) -> None:
    request = await playwright.request.new_context()
    with pytest.raises(Error, match="Out of range float values are not JSON"):
        await request.post(server.EMPTY_PAGE, data={"value": value})
    await request.dispose()


async def test_should_reject_empty_data_with_form(
    playwright: Playwright, server: Server
) -> None:
    request = await playwright.request.new_context()
    with pytest.raises(
        Error,
        match="Only one of 'data', 'form' or 'multipart' can be specified",
    ):
        await request.post(
            server.EMPTY_PAGE,
            data="",
            form={"name": "value"},
        )
    await request.dispose()
