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

import pytest

from playwright.async_api import Error, Page
from tests.server import Server, TestServerRequest


async def test_should_reject_response_finished_if_page_closes(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)

    def handle_get(request: TestServerRequest) -> None:
        # In Firefox, |fetch| will be hanging until it receives |Content-Type| header
        # from server.
        request.setHeader("Content-Type", "text/plain; charset=utf-8")
        request.write(b"hello ")

    server.set_route("/get", handle_get)
    # send request and wait for server response
    [page_response, _] = await asyncio.gather(
        page.wait_for_event("response"),
        page.evaluate("() => fetch('./get', { method: 'GET' })"),
    )

    finish_coroutine = page_response.finished()
    await page.close()
    with pytest.raises(Error) as exc_info:
        await finish_coroutine
    error = exc_info.value
    assert "closed" in error.message


async def test_should_reject_response_finished_if_context_closes(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)

    def handle_get(request: TestServerRequest) -> None:
        # In Firefox, |fetch| will be hanging until it receives |Content-Type| header
        # from server.
        request.setHeader("Content-Type", "text/plain; charset=utf-8")
        request.write(b"hello ")

    server.set_route("/get", handle_get)
    # send request and wait for server response
    [page_response, _] = await asyncio.gather(
        page.wait_for_event("response"),
        page.evaluate("() => fetch('./get', { method: 'GET' })"),
    )

    finish_coroutine = page_response.finished()
    await page.context.close()
    with pytest.raises(Error) as exc_info:
        await finish_coroutine
    error = exc_info.value
    assert "closed" in error.message

async def test_response_finished_should_not_leave_page_close_waiter(
    page: Page, server: Server
) -> None:
    def response_finished_waiters() -> list[asyncio.Task]:
        return [
            task
            for task in asyncio.all_tasks()
            if not task.done()
            and getattr(task.get_coro(), "__qualname__", "")
            == "Response.finished.<locals>.on_finished"
        ]

    baseline = set(response_finished_waiters())
    leaked_waiters = []
    try:
        response = await page.goto(server.EMPTY_PAGE)
        assert response
        await response.finished()
        await asyncio.sleep(0)

        leaked_waiters = [
            task for task in response_finished_waiters() if task not in baseline
        ]
        assert not leaked_waiters, "Response.finished() leaked page-close waiter tasks"
    finally:
        await page.close()
        if leaked_waiters:
            await asyncio.gather(*leaked_waiters, return_exceptions=True)

async def test_should_return_http_version(page: Page, server: Server) -> None:
    response = await page.goto(server.EMPTY_PAGE)
    assert response
    http_version = await response.http_version()
    assert http_version in ("HTTP/1.0", "HTTP/1.1", "HTTP/2.0")
