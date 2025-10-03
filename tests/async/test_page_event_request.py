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

from playwright._impl._network import Request, Route
from playwright._impl._page import Page
from tests.server import Server


async def test_should_return_last_requests(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/title.html")
    for i in range(200):

        def _handle_route(route: Route) -> None:
            asyncio.ensure_future(
                route.fulfill(
                    status=200,
                    body=f"url:{route.request.url}",
                )
            )

        await page.route(f"**/fetch?{i}", _handle_route)

    # #0 is the navigation request, so start with #1.
    for i in range(1, 100):
        await page.evaluate("url => fetch(url)", server.PREFIX + f"/fetch?{i}")
    first_100_requests_with_goto = await page.requests()
    first_100_requests = first_100_requests_with_goto[1:]

    for i in range(100, 200):
        await page.evaluate("url => fetch(url)", server.PREFIX + f"/fetch?{i}")
    last_100_requests = await page.requests()

    all_requests = first_100_requests + last_100_requests

    async def gather_response(request: Request) -> dict:
        response = await request.response()
        assert response
        return {"text": await response.text(), "url": request.url}

    # All 199 requests are fully functional.
    received = await asyncio.gather(
        *[gather_response(request) for request in all_requests]
    )

    expected = []
    for i in range(1, 200):
        url = server.PREFIX + f"/fetch?{i}"
        expected.append({"url": url, "text": f"url:{url}"})
    assert received == expected
