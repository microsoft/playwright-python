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
from typing import Optional

from playwright.async_api import Page, Route
from tests.server import Server, TestServerRequest


async def test_request_continue_should_work(page: Page, server: Server) -> None:
    await page.route("**/*", lambda route: asyncio.create_task(route.continue_()))
    await page.goto(server.EMPTY_PAGE)


async def test_request_continue_should_amend_http_headers(
    page: Page, server: Server
) -> None:
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


async def test_request_continue_should_amend_method(page: Page, server: Server) -> None:
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


async def test_request_continue_should_amend_method_on_main_request(
    page: Page, server: Server
) -> None:
    request = asyncio.create_task(server.wait_for_request("/empty.html"))
    await page.route(
        "**/*", lambda route: asyncio.create_task(route.continue_(method="POST"))
    )
    await page.goto(server.EMPTY_PAGE)
    assert (await request).method.decode() == "POST"


async def test_request_continue_should_amend_post_data(
    page: Page, server: Server
) -> None:
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
    assert server_request.post_body
    assert server_request.post_body.decode() == "doggo"


async def test_should_override_request_url(page: Page, server: Server) -> None:
    request = asyncio.create_task(server.wait_for_request("/empty.html"))
    await page.route(
        "**/foo",
        lambda route: asyncio.create_task(route.continue_(url=server.EMPTY_PAGE)),
    )

    await page.goto(server.PREFIX + "/foo")
    assert (await request).method == b"GET"


async def test_should_raise_except(page: Page, server: Server) -> None:
    exc_fut: "asyncio.Future[Optional[Exception]]" = asyncio.Future()

    async def capture_exception(route: Route) -> None:
        try:
            await route.continue_(url="file:///tmp/does-not-exist")
            exc_fut.set_result(None)
        except Exception as e:
            exc_fut.set_result(e)

    await page.route("**/*", capture_exception)
    asyncio.create_task(page.goto(server.EMPTY_PAGE))
    assert "New URL must have same protocol as overridden URL" in str(await exc_fut)


async def test_should_amend_utf8_post_data(page: Page, server: Server) -> None:
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
    assert server_request.post_body
    assert server_request.post_body.decode("utf8") == "пушкин"


async def test_should_amend_binary_post_data(page: Page, server: Server) -> None:
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


async def test_continue_should_not_change_multipart_form_data_body(
    page: Page, server: Server, browser_name: str
) -> None:
    await page.goto(server.EMPTY_PAGE)
    server.set_route(
        "/upload",
        lambda context: (
            context.write(b"done"),
            context.setHeader("Content-Type", "text/plain"),
            context.finish(),
        ),
    )

    async def send_form_data() -> TestServerRequest:
        req_task = asyncio.create_task(server.wait_for_request("/upload"))
        status = await page.evaluate(
            """async () => {
            const newFile = new File(['file content'], 'file.txt');
            const formData = new FormData();
            formData.append('file', newFile);
            const response = await fetch('/upload', {
                method: 'POST',
                credentials: 'include',
                body: formData,
            });
            return response.status;
        }"""
        )
        req = await req_task
        assert status == 200
        return req

    req_before = await send_form_data()
    await page.route("**/*", lambda route: route.continue_())
    req_after = await send_form_data()

    file_content = (
        'Content-Disposition: form-data; name="file"; filename="file.txt"\r\n'
        "Content-Type: application/octet-stream\r\n"
        "\r\n"
        "file content\r\n"
        "------"
    )
    assert req_before.post_body
    assert req_after.post_body
    assert file_content in req_before.post_body.decode()
    assert file_content in req_after.post_body.decode()
