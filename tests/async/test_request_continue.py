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


async def test_request_continue_should_work(page, server):
    await page.route("**/*", lambda route: asyncio.create_task(route.continue_()))
    await page.goto(server.EMPTY_PAGE)


async def test_request_continue_should_amend_http_headers(page, server):
    await page.route(
        "**/*",
        lambda route: asyncio.create_task(
            route.continue_(headers={**route.request.headers, "FOO": "bar"})
        ),
    )

    await page.goto(server.EMPTY_PAGE)
    [request, _] = await asyncio.gather(
        server.wait_for_request("/sleep.zzz"),
        page.evaluate('() => fetch("/sleep.zzz")'),
    )
    assert request.getHeader("foo") == "bar"


async def test_request_continue_should_amend_method(page, server):
    server_request = asyncio.create_task(server.wait_for_request("/sleep.zzz"))
    await page.goto(server.EMPTY_PAGE)
    await page.route(
        "**/*", lambda route: asyncio.create_task(route.continue_(method="POST"))
    )
    [request, _] = await asyncio.gather(
        server.wait_for_request("/sleep.zzz"),
        page.evaluate('() => fetch("/sleep.zzz")'),
    )
    assert request.method.decode() == "POST"
    assert (await server_request).method.decode() == "POST"


async def test_request_continue_should_amend_method_on_main_request(page, server):
    request = asyncio.create_task(server.wait_for_request("/empty.html"))
    await page.route(
        "**/*", lambda route: asyncio.create_task(route.continue_(method="POST"))
    )
    await page.goto(server.EMPTY_PAGE)
    assert (await request).method.decode() == "POST"


async def test_request_continue_should_amend_post_data(page, server):
    await page.goto(server.EMPTY_PAGE)
    await page.route(
        "**/*",
        lambda route: asyncio.create_task(route.continue_(post_data=b"doggo")),
    )

    [server_request, _] = await asyncio.gather(
        server.wait_for_request("/sleep.zzz"),
        page.evaluate(
            """
            () => fetch('/sleep.zzz', { method: 'POST', body: 'birdy' })
            """
        ),
    )
    assert server_request.post_body.decode() == "doggo"


async def test_should_override_request_url(page, server):
    request = asyncio.create_task(server.wait_for_request("/empty.html"))
    await page.route(
        "**/foo",
        lambda route: asyncio.create_task(route.continue_(url=server.EMPTY_PAGE)),
    )

    await page.goto(server.PREFIX + "/foo")
    assert (await request).method == b"GET"


async def test_should_amend_utf8_post_data(page, server):
    await page.goto(server.EMPTY_PAGE)
    await page.route(
        "**/*",
        lambda route: asyncio.create_task(route.continue_(post_data="пушкин")),
    )

    [server_request, result] = await asyncio.gather(
        server.wait_for_request("/sleep.zzz"),
        page.evaluate("fetch('/sleep.zzz', { method: 'POST', body: 'birdy' })"),
    )
    assert server_request.method == b"POST"
    assert server_request.post_body.decode("utf8") == "пушкин"


async def test_should_amend_binary_post_data(page, server):
    await page.goto(server.EMPTY_PAGE)
    await page.route(
        "**/*",
        lambda route: asyncio.create_task(
            route.continue_(post_data=b"\x00\x01\x02\x03\x04")
        ),
    )

    [server_request, result] = await asyncio.gather(
        server.wait_for_request("/sleep.zzz"),
        page.evaluate("fetch('/sleep.zzz', { method: 'POST', body: 'birdy' })"),
    )
    assert server_request.method == b"POST"
    assert server_request.post_body == b"\x00\x01\x02\x03\x04"
