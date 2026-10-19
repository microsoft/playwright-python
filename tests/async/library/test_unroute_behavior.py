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

"""Port of tests/library/unroute-behavior.spec.ts."""

import asyncio
import re
from typing import Any, Awaitable, TypeVar

from playwright.async_api import BrowserContext, Error, Page, Route
from tests.server import Server
from tests.utils import must

T = TypeVar("T")


async def ignore_error(awaitable: Awaitable[Any]) -> None:
    """Port of `promise.catch(() => {})`."""
    try:
        await awaitable
    except Error:
        pass


def resolve(future: "asyncio.Future[T]", value: T) -> None:
    """Port of a promise's resolve(): only the first call settles the promise."""
    if not future.done():
        future.set_result(value)


async def test_RO_186_context_unroute_should_not_wait_for_pending_handlers_to_complete(
    page: Page, context: BrowserContext, server: Server
) -> None:
    second_handler_called = False

    async def handler1(route: Route) -> None:
        nonlocal second_handler_called
        second_handler_called = True
        await route.continue_()

    await context.route(re.compile(".*"), handler1)
    route_future: "asyncio.Future[None]" = asyncio.Future()
    route_barrier: "asyncio.Future[None]" = asyncio.Future()

    async def handler(route: Route) -> None:
        resolve(route_future, None)
        await route_barrier
        await route.fallback()

    await context.route(re.compile(".*"), handler)
    navigation_task = asyncio.create_task(page.goto(server.EMPTY_PAGE))
    await route_future
    await context.unroute(re.compile(".*"), handler)
    route_barrier.set_result(None)
    await navigation_task
    assert second_handler_called is True


async def test_RO_187_context_unroute_all_removes_all_handlers(
    page: Page, context: BrowserContext, server: Server
) -> None:
    await context.route("**/*", lambda route: route.abort())
    await context.route("**/empty.html", lambda route: route.abort())
    await context.unroute_all()
    await page.goto(server.EMPTY_PAGE)


async def test_RO_188_context_unroute_all_should_wait_for_pending_handlers_to_complete(
    page: Page, context: BrowserContext, server: Server
) -> None:
    second_handler_called = False

    async def handler1(route: Route) -> None:
        nonlocal second_handler_called
        second_handler_called = True
        await route.abort()

    await context.route(re.compile(".*"), handler1)
    route_future: "asyncio.Future[None]" = asyncio.Future()
    route_barrier: "asyncio.Future[None]" = asyncio.Future()

    async def handler(route: Route) -> None:
        resolve(route_future, None)
        await route_barrier
        await route.fallback()

    await context.route(re.compile(".*"), handler)
    navigation_task = asyncio.create_task(page.goto(server.EMPTY_PAGE))
    await route_future
    did_unroute = False

    async def unroute() -> None:
        nonlocal did_unroute
        await context.unroute_all(behavior="wait")
        did_unroute = True

    unroute_task = asyncio.create_task(unroute())
    await asyncio.sleep(0.5)
    assert did_unroute is False
    route_barrier.set_result(None)
    await unroute_task
    assert did_unroute is True
    await navigation_task
    assert second_handler_called is False


async def test_RO_189_context_unroute_all_should_not_wait_for_pending_handlers_to_complete_if_behavior_is_ignore_errors(
    page: Page, context: BrowserContext, server: Server
) -> None:
    second_handler_called = False

    async def handler1(route: Route) -> None:
        nonlocal second_handler_called
        second_handler_called = True
        await route.abort()

    await context.route(re.compile(".*"), handler1)
    route_future: "asyncio.Future[None]" = asyncio.Future()
    route_barrier: "asyncio.Future[None]" = asyncio.Future()

    async def handler(route: Route) -> None:
        resolve(route_future, None)
        await route_barrier
        raise Exception("Handler error")

    await context.route(re.compile(".*"), handler)
    navigation_task = asyncio.create_task(ignore_error(page.goto(server.EMPTY_PAGE)))
    await route_future
    did_unroute = False

    async def unroute() -> None:
        nonlocal did_unroute
        await context.unroute_all(behavior="ignoreErrors")
        did_unroute = True

    unroute_task = asyncio.create_task(unroute())
    await asyncio.sleep(0.5)
    await unroute_task
    assert did_unroute is True
    route_barrier.set_result(None)
    await navigation_task
    # The error in the unrouted handler should be silently caught and remaining handler called.
    assert second_handler_called is False


async def test_RO_190_page_close_should_not_wait_for_active_route_handlers_on_the_owning_context(
    page: Page, context: BrowserContext, server: Server
) -> None:
    route_future: "asyncio.Future[None]" = asyncio.Future()

    async def context_handler(route: Route) -> None:
        resolve(route_future, None)

    await context.route(re.compile(".*"), context_handler)

    async def page_handler(route: Route) -> None:
        await route.fallback()

    await page.route(re.compile(".*"), page_handler)
    asyncio.create_task(ignore_error(page.goto(server.EMPTY_PAGE)))
    await route_future
    await page.close()


async def test_RO_191_context_close_should_not_wait_for_active_route_handlers_on_the_owned_pages(
    page: Page, context: BrowserContext, server: Server
) -> None:
    route_future: "asyncio.Future[None]" = asyncio.Future()

    async def handler1(route: Route) -> None:
        resolve(route_future, None)

    await page.route(re.compile(".*"), handler1)

    async def handler2(route: Route) -> None:
        await route.fallback()

    await page.route(re.compile(".*"), handler2)
    asyncio.create_task(ignore_error(page.goto(server.EMPTY_PAGE)))
    await route_future
    await context.close()


async def test_RO_192_page_unroute_should_not_wait_for_pending_handlers_to_complete(
    page: Page, server: Server
) -> None:
    second_handler_called = False

    async def handler1(route: Route) -> None:
        nonlocal second_handler_called
        second_handler_called = True
        await route.continue_()

    await page.route(re.compile(".*"), handler1)
    route_future: "asyncio.Future[None]" = asyncio.Future()
    route_barrier: "asyncio.Future[None]" = asyncio.Future()

    async def handler(route: Route) -> None:
        resolve(route_future, None)
        await route_barrier
        await route.fallback()

    await page.route(re.compile(".*"), handler)
    navigation_task = asyncio.create_task(page.goto(server.EMPTY_PAGE))
    await route_future
    await page.unroute(re.compile(".*"), handler)
    route_barrier.set_result(None)
    await navigation_task
    assert second_handler_called is True


async def test_RO_193_page_unroute_all_removes_all_routes(
    page: Page, server: Server
) -> None:
    await page.route("**/*", lambda route: route.abort())
    await page.route("**/empty.html", lambda route: route.abort())
    await page.unroute_all()
    response = must(await page.goto(server.EMPTY_PAGE))
    assert response.ok is True


async def test_RO_194_page_unroute_all_should_wait_for_pending_handlers_to_complete(
    page: Page, server: Server
) -> None:
    second_handler_called = False

    async def handler1(route: Route) -> None:
        nonlocal second_handler_called
        second_handler_called = True
        await route.abort()

    await page.route(re.compile(".*"), handler1)
    route_future: "asyncio.Future[None]" = asyncio.Future()
    route_barrier: "asyncio.Future[None]" = asyncio.Future()

    async def handler(route: Route) -> None:
        resolve(route_future, None)
        await route_barrier
        await route.fallback()

    await page.route(re.compile(".*"), handler)
    navigation_task = asyncio.create_task(page.goto(server.EMPTY_PAGE))
    await route_future
    did_unroute = False

    async def unroute() -> None:
        nonlocal did_unroute
        await page.unroute_all(behavior="wait")
        did_unroute = True

    unroute_task = asyncio.create_task(unroute())
    await asyncio.sleep(0.5)
    assert did_unroute is False
    route_barrier.set_result(None)
    await unroute_task
    assert did_unroute is True
    await navigation_task
    assert second_handler_called is False


async def test_RO_195_page_unroute_all_should_not_wait_for_pending_handlers_to_complete_if_behavior_is_ignore_errors(
    page: Page, server: Server
) -> None:
    second_handler_called = False

    async def handler1(route: Route) -> None:
        nonlocal second_handler_called
        second_handler_called = True
        await route.abort()

    await page.route(re.compile(".*"), handler1)
    route_future: "asyncio.Future[None]" = asyncio.Future()
    route_barrier: "asyncio.Future[None]" = asyncio.Future()

    async def handler(route: Route) -> None:
        resolve(route_future, None)
        await route_barrier
        raise Exception("Handler error")

    await page.route(re.compile(".*"), handler)
    navigation_task = asyncio.create_task(ignore_error(page.goto(server.EMPTY_PAGE)))
    await route_future
    did_unroute = False

    async def unroute() -> None:
        nonlocal did_unroute
        await page.unroute_all(behavior="ignoreErrors")
        did_unroute = True

    unroute_task = asyncio.create_task(unroute())
    await asyncio.sleep(0.5)
    await unroute_task
    assert did_unroute is True
    route_barrier.set_result(None)
    await navigation_task
    # The error in the unrouted handler should be silently caught.
    assert second_handler_called is False


async def test_RO_196_page_close_does_not_wait_for_active_route_handlers(
    page: Page, server: Server
) -> None:
    second_handler_called = False

    def handler1(route: Route) -> None:
        nonlocal second_handler_called
        second_handler_called = True

    await page.route(re.compile(".*"), handler1)
    route_future: "asyncio.Future[None]" = asyncio.Future()

    async def handler(route: Route) -> None:
        resolve(route_future, None)
        await asyncio.Future()

    await page.route(re.compile(".*"), handler)
    asyncio.create_task(ignore_error(page.goto(server.EMPTY_PAGE)))
    await route_future
    await page.close()
    await asyncio.sleep(0.5)
    assert second_handler_called is False


async def test_RO_197_route_continue_should_not_throw_if_page_has_been_closed(
    page: Page, server: Server
) -> None:
    route_future: "asyncio.Future[Route]" = asyncio.Future()

    async def handler(route: Route) -> None:
        resolve(route_future, route)

    await page.route(re.compile(".*"), handler)
    asyncio.create_task(ignore_error(page.goto(server.EMPTY_PAGE)))
    route = await route_future
    await page.close()
    # Should not throw.
    await route.continue_()


async def test_RO_198_route_fallback_should_not_throw_if_page_has_been_closed(
    page: Page, server: Server
) -> None:
    route_future: "asyncio.Future[Route]" = asyncio.Future()

    async def handler(route: Route) -> None:
        resolve(route_future, route)

    await page.route(re.compile(".*"), handler)
    asyncio.create_task(ignore_error(page.goto(server.EMPTY_PAGE)))
    route = await route_future
    await page.close()
    # Should not throw.
    await route.fallback()


async def test_RO_199_route_fulfill_should_not_throw_if_page_has_been_closed(
    page: Page, server: Server
) -> None:
    route_future: "asyncio.Future[Route]" = asyncio.Future()

    async def handler(route: Route) -> None:
        resolve(route_future, route)

    await page.route(re.compile(".*"), handler)
    asyncio.create_task(ignore_error(page.goto(server.EMPTY_PAGE)))
    route = await route_future
    await page.close()
    # Should not throw.
    await route.fulfill()


async def test_RO_200_should_not_continue_requests_in_flight_page(
    page: Page, server: Server
) -> None:
    route_future: "asyncio.Future[None]" = asyncio.Future()
    await page.goto(server.EMPTY_PAGE)

    async def handler(route: Route) -> None:
        resolve(route_future, None)
        await asyncio.sleep(3)
        response = await route.fetch()
        await route.fulfill(response=response)

    await page.route("**/*", handler)
    asyncio.create_task(ignore_error(page.evaluate("() => fetch('/')")))
    await route_future
    await page.unroute_all(behavior="wait")


async def test_RO_201_should_not_continue_requests_in_flight_context(
    page: Page, context: BrowserContext, server: Server
) -> None:
    route_future: "asyncio.Future[None]" = asyncio.Future()
    await page.goto(server.EMPTY_PAGE)

    async def handler(route: Route) -> None:
        resolve(route_future, None)
        await asyncio.sleep(3)
        response = await route.fetch()
        await route.fulfill(response=response)

    await context.route("**/*", handler)
    asyncio.create_task(ignore_error(page.evaluate("() => fetch('/')")))
    await route_future
    await context.unroute_all(behavior="wait")
