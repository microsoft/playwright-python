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


async def test_should_fetch_original_request_and_fulfill(page: Page, server: Server):
    async def handle(route: Route):
        response = await page.request.fetch(route.request)
        await route.fulfill(response=response)

    await page.route("**/*", handle)
    response = await page.goto(server.PREFIX + "/title.html")
    assert response.status == 200
    assert await page.title() == "Woof-Woof"
