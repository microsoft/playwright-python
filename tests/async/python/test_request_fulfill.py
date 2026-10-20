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

from typing import Any

import pytest

from playwright.async_api import Page, Route
from tests.server import Server


@pytest.mark.parametrize("value", [[], {}])
async def test_should_fulfill_empty_json_with_json_content_type(
    page: Page, server: Server, value: Any
) -> None:
    async def handle(route: Route) -> None:
        await route.fulfill(json=value)

    await page.route("**/*", handle)

    response = await page.goto(server.EMPTY_PAGE)
    assert response
    assert response.headers["content-type"] == "application/json"
    assert await response.json() == value


async def test_should_fulfill_json_overriding_existing_response(
    page: Page, server: Server
) -> None:
    server.set_route(
        "/tags",
        lambda request: (
            request.setHeader("foo", "bar"),
            request.write('{"tags": ["a", "b"]}'.encode()),
            request.finish(),
        ),
    )

    original = {}

    async def handle(route: Route) -> None:
        response = await route.fetch()
        json = await response.json()
        original["tags"] = json["tags"]
        json["tags"] = ["c"]
        await route.fulfill(response=response, json=json)

    await page.route("**/*", handle)

    response = await page.goto(server.PREFIX + "/tags")
    assert response
    assert response.status == 200
    assert response.headers["content-type"] == "application/json"
    assert response.headers["foo"] == "bar"
    assert original["tags"] == ["a", "b"]
    assert await response.json() == {"tags": ["c"]}
