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

from playwright.async_api import Page, Route
from tests.server import Server


async def test_should_not_follow_redirects_when_max_redirects_is_set_to_0_in_route_fetch(
    server: Server, page: Page
):
    server.set_redirect("/foo", "/empty.html")

    async def handle(route: Route):
        response = await route.fetch(max_redirects=0)
        assert response.headers["location"] == "/empty.html"
        assert response.status == 302
        await route.fulfill(body="hello")

    await page.route("**/*", lambda route: handle(route))
    await page.goto(server.PREFIX + "/foo")
    assert "hello" in await page.content()


async def test_should_intercept_with_url_override(server: Server, page: Page):
    async def handle(route: Route):
        response = await route.fetch(url=server.PREFIX + "/one-style.html")
        await route.fulfill(response=response)

    await page.route("**/*.html", lambda route: handle(route))
    response = await page.goto(server.PREFIX + "/empty.html")
    assert response.status == 200
    assert "one-style.css" in (await response.body()).decode("utf-8")


async def test_should_intercept_with_post_data_override(server: Server, page: Page):
    request_promise = asyncio.create_task(server.wait_for_request("/empty.html"))

    async def handle(route: Route):
        response = await route.fetch(post_data={"foo": "bar"})
        await route.fulfill(response=response)

    await page.route("**/*.html", lambda route: handle(route))
    await page.goto(server.PREFIX + "/empty.html")
    request = await request_promise
    assert request.post_body.decode("utf-8") == '{"foo":"bar"}'
