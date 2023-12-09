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

from playwright.async_api import Page, Route
from tests.server import Server


async def test_should_fetch_original_request_and_fulfill(
    page: Page, server: Server
) -> None:
    async def handle(route: Route) -> None:
        response = await page.request.fetch(route.request)
        await route.fulfill(response=response)

    await page.route("**/*", handle)
    response = await page.goto(server.PREFIX + "/title.html")
    assert response
    assert response.status == 200
    assert await page.title() == "Woof-Woof"


async def test_should_fulfill_json(page: Page, server: Server) -> None:
    async def handle(route: Route) -> None:
        await route.fulfill(status=201, headers={"foo": "bar"}, json={"bar": "baz"})

    await page.route("**/*", handle)

    response = await page.goto(server.EMPTY_PAGE)
    assert response
    assert response.status == 201
    assert response.headers["content-type"] == "application/json"
    assert await response.json() == {"bar": "baz"}


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
