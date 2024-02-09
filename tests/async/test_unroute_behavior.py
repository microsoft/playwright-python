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
import re

from playwright.async_api import BrowserContext, Error, Page, Route
from tests.server import Server
from tests.utils import must


async def test_context_unroute_should_not_wait_for_pending_handlers_to_complete(
    page: Page, context: BrowserContext, server: Server
) -> None:
    second_handler_called = False

    async def _handler1(route: Route) -> None:
        nonlocal second_handler_called
        second_handler_called = True
        await route.continue_()

    await context.route(
        re.compile(".*"),
        _handler1,
    )
    route_future: "asyncio.Future[Route]" = asyncio.Future()
    route_barrier_future: "asyncio.Future[None]" = asyncio.Future()

    async def _handler2(route: Route) -> None:
        route_future.set_result(route)
        await route_barrier_future
        await route.fallback()

    await context.route(
        re.compile(".*"),
        _handler2,
    )
    navigation_task = asyncio.create_task(page.goto(server.EMPTY_PAGE))
    await route_future
    await context.unroute(
        re.compile(".*"),
        _handler2,
    )
    route_barrier_future.set_result(None)
    await navigation_task
    assert second_handler_called


async def test_context_unroute_all_removes_all_handlers(
    page: Page, context: BrowserContext, server: Server
) -> None:
    await context.route(
        "**/*",
        lambda route: route.abort(),
    )
    await context.route(
        "**/empty.html",
        lambda route: route.abort(),
    )
    await context.unroute_all()
    await page.goto(server.EMPTY_PAGE)


async def test_context_unroute_all_should_not_wait_for_pending_handlers_to_complete(
    page: Page, context: BrowserContext, server: Server
) -> None:
    second_handler_called = False

    async def _handler1(route: Route) -> None:
        nonlocal second_handler_called
        second_handler_called = True
        await route.abort()

    await context.route(
        re.compile(".*"),
        _handler1,
    )
    route_future: "asyncio.Future[Route]" = asyncio.Future()
    route_barrier_future: "asyncio.Future[None]" = asyncio.Future()

    async def _handler2(route: Route) -> None:
        route_future.set_result(route)
        await route_barrier_future
        await route.fallback()

    await context.route(
        re.compile(".*"),
        _handler2,
    )
    navigation_task = asyncio.create_task(page.goto(server.EMPTY_PAGE))
    await route_future
    did_unroute = False

    async def _unroute_promise() -> None:
        nonlocal did_unroute
        await context.unroute_all(behavior="wait")
        did_unroute = True

    unroute_task = asyncio.create_task(_unroute_promise())
    await asyncio.sleep(0.5)
    assert did_unroute is False
    route_barrier_future.set_result(None)
    await unroute_task
    assert did_unroute
    await navigation_task
    assert second_handler_called is False


async def test_context_unroute_all_should_not_wait_for_pending_handlers_to_complete_if_behavior_is_ignore_errors(
    page: Page, context: BrowserContext, server: Server
) -> None:
    second_handler_called = False

    async def _handler1(route: Route) -> None:
        nonlocal second_handler_called
        second_handler_called = True
        await route.abort()

    await context.route(
        re.compile(".*"),
        _handler1,
    )
    route_future: "asyncio.Future[Route]" = asyncio.Future()
    route_barrier_future: "asyncio.Future[None]" = asyncio.Future()

    async def _handler2(route: Route) -> None:
        route_future.set_result(route)
        await route_barrier_future
        raise Exception("Handler error")

    await context.route(
        re.compile(".*"),
        _handler2,
    )
    navigation_task = asyncio.create_task(page.goto(server.EMPTY_PAGE))
    await route_future
    did_unroute = False

    async def _unroute_promise() -> None:
        await context.unroute_all(behavior="ignoreErrors")
        nonlocal did_unroute
        did_unroute = True

    unroute_task = asyncio.create_task(_unroute_promise())
    await asyncio.sleep(0.5)
    await unroute_task
    assert did_unroute
    route_barrier_future.set_result(None)
    try:
        await navigation_task
    except Error:
        pass
    # The error in the unrouted handler should be silently caught and remaining handler called.
    assert not second_handler_called


async def test_page_close_should_not_wait_for_active_route_handlers_on_the_owning_context(
    page: Page, context: BrowserContext, server: Server
) -> None:
    route_future: "asyncio.Future[Route]" = asyncio.Future()
    await context.route(
        re.compile(".*"),
        lambda route: route_future.set_result(route),
    )
    await page.route(
        re.compile(".*"),
        lambda route: route.fallback(),
    )

    async def _goto_ignore_exceptions() -> None:
        try:
            await page.goto(server.EMPTY_PAGE)
        except Error:
            pass

    asyncio.create_task(_goto_ignore_exceptions())
    await route_future
    await page.close()


async def test_context_close_should_not_wait_for_active_route_handlers_on_the_owned_pages(
    page: Page, context: BrowserContext, server: Server
) -> None:
    route_future: "asyncio.Future[Route]" = asyncio.Future()
    await page.route(
        re.compile(".*"),
        lambda route: route_future.set_result(route),
    )
    await page.route(re.compile(".*"), lambda route: route.fallback())

    async def _goto_ignore_exceptions() -> None:
        try:
            await page.goto(server.EMPTY_PAGE)
        except Error:
            pass

    asyncio.create_task(_goto_ignore_exceptions())
    await route_future
    await context.close()


async def test_page_unroute_should_not_wait_for_pending_handlers_to_complete(
    page: Page, server: Server
) -> None:
    second_handler_called = False

    async def _handler1(route: Route) -> None:
        nonlocal second_handler_called
        second_handler_called = True
        await route.continue_()

    await page.route(
        re.compile(".*"),
        _handler1,
    )
    route_future: "asyncio.Future[Route]" = asyncio.Future()
    route_barrier_future: "asyncio.Future[None]" = asyncio.Future()

    async def _handler2(route: Route) -> None:
        route_future.set_result(route)
        await route_barrier_future
        await route.fallback()

    await page.route(
        re.compile(".*"),
        _handler2,
    )
    navigation_task = asyncio.create_task(page.goto(server.EMPTY_PAGE))
    await route_future
    await page.unroute(
        re.compile(".*"),
        _handler2,
    )
    route_barrier_future.set_result(None)
    await navigation_task
    assert second_handler_called


async def test_page_unroute_all_removes_all_routes(page: Page, server: Server) -> None:
    await page.route(
        "**/*",
        lambda route: route.abort(),
    )
    await page.route(
        "**/empty.html",
        lambda route: route.abort(),
    )
    await page.unroute_all()
    response = must(await page.goto(server.EMPTY_PAGE))
    assert response.ok


async def test_page_unroute_should_wait_for_pending_handlers_to_complete(
    page: Page, server: Server
) -> None:
    second_handler_called = False

    async def _handler1(route: Route) -> None:
        nonlocal second_handler_called
        second_handler_called = True
        await route.abort()

    await page.route(
        "**/*",
        _handler1,
    )
    route_future: "asyncio.Future[Route]" = asyncio.Future()
    route_barrier_future: "asyncio.Future[None]" = asyncio.Future()

    async def _handler2(route: Route) -> None:
        route_future.set_result(route)
        await route_barrier_future
        await route.fallback()

    await page.route(
        "**/*",
        _handler2,
    )
    navigation_task = asyncio.create_task(page.goto(server.EMPTY_PAGE))
    await route_future
    did_unroute = False

    async def _unroute_promise() -> None:
        await page.unroute_all(behavior="wait")
        nonlocal did_unroute
        did_unroute = True

    unroute_task = asyncio.create_task(_unroute_promise())
    await asyncio.sleep(0.5)
    assert did_unroute is False
    route_barrier_future.set_result(None)
    await unroute_task
    assert did_unroute
    await navigation_task
    assert second_handler_called is False


async def test_page_unroute_all_should_not_wait_for_pending_handlers_to_complete_if_behavior_is_ignore_errors(
    page: Page, server: Server
) -> None:
    second_handler_called = False

    async def _handler1(route: Route) -> None:
        nonlocal second_handler_called
        second_handler_called = True
        await route.abort()

    await page.route(re.compile(".*"), _handler1)
    route_future: "asyncio.Future[Route]" = asyncio.Future()
    route_barrier_future: "asyncio.Future[None]" = asyncio.Future()

    async def _handler2(route: Route) -> None:
        route_future.set_result(route)
        await route_barrier_future
        raise Exception("Handler error")

    await page.route(re.compile(".*"), _handler2)
    navigation_task = asyncio.create_task(page.goto(server.EMPTY_PAGE))
    await route_future
    did_unroute = False

    async def _unroute_promise() -> None:
        await page.unroute_all(behavior="ignoreErrors")
        nonlocal did_unroute
        did_unroute = True

    unroute_task = asyncio.create_task(_unroute_promise())
    await asyncio.sleep(0.5)
    await unroute_task
    assert did_unroute
    route_barrier_future.set_result(None)
    try:
        await navigation_task
    except Error:
        pass
    # The error in the unrouted handler should be silently caught.
    assert not second_handler_called


async def test_page_close_does_not_wait_for_active_route_handlers(
    page: Page, server: Server
) -> None:
    stalling_future: "asyncio.Future[None]" = asyncio.Future()
    second_handler_called = False

    def _handler1(route: Route) -> None:
        nonlocal second_handler_called
        second_handler_called = True

    await page.route(
        "**/*",
        _handler1,
    )
    route_future: "asyncio.Future[Route]" = asyncio.Future()

    async def _handler2(route: Route) -> None:
        route_future.set_result(route)
        await stalling_future

    await page.route(
        "**/*",
        _handler2,
    )

    async def _goto_ignore_exceptions() -> None:
        try:
            await page.goto(server.EMPTY_PAGE)
        except Error:
            pass

    asyncio.create_task(_goto_ignore_exceptions())
    await route_future
    await page.close()
    await asyncio.sleep(0.5)
    assert not second_handler_called
    stalling_future.cancel()


async def test_route_continue_should_not_throw_if_page_has_been_closed(
    page: Page, server: Server
) -> None:
    route_future: "asyncio.Future[Route]" = asyncio.Future()
    await page.route(
        re.compile(".*"),
        lambda route: route_future.set_result(route),
    )

    async def _goto_ignore_exceptions() -> None:
        try:
            await page.goto(server.EMPTY_PAGE)
        except Error:
            pass

    asyncio.create_task(_goto_ignore_exceptions())
    route = await route_future
    await page.close()
    # Should not throw.
    await route.continue_()


async def test_route_fallback_should_not_throw_if_page_has_been_closed(
    page: Page, server: Server
) -> None:
    route_future: "asyncio.Future[Route]" = asyncio.Future()
    await page.route(
        re.compile(".*"),
        lambda route: route_future.set_result(route),
    )

    async def _goto_ignore_exceptions() -> None:
        try:
            await page.goto(server.EMPTY_PAGE)
        except Error:
            pass

    asyncio.create_task(_goto_ignore_exceptions())
    route = await route_future
    await page.close()
    # Should not throw.
    await route.fallback()


async def test_route_fulfill_should_not_throw_if_page_has_been_closed(
    page: Page, server: Server
) -> None:
    route_future: "asyncio.Future[Route]" = asyncio.Future()
    await page.route(
        "**/*",
        lambda route: route_future.set_result(route),
    )

    async def _goto_ignore_exceptions() -> None:
        try:
            await page.goto(server.EMPTY_PAGE)
        except Error:
            pass

    asyncio.create_task(_goto_ignore_exceptions())
    route = await route_future
    await page.close()
    # Should not throw.
    await route.fulfill()
