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
from typing import Any, Awaitable, Callable, List, TypeVar

from playwright._impl._greenlets import wait_for_future
from playwright.sync_api import BrowserContext, Error, Page, Route
from tests.server import Server
from tests.utils import must

T = TypeVar("T")


def wait_for(page: Page, awaitable: "Awaitable[T]") -> T:
    """Port of `await promise`: runs the event loop until the awaitable settles."""
    future = asyncio.ensure_future(awaitable)
    wait_for_future(page._loop, page._dispatcher_fiber, future)
    return future.result()


def ignore_error(action: Callable[[], Any]) -> Callable[[], None]:
    """Port of `promise.catch(() => {})`."""

    def run() -> None:
        try:
            action()
        except Error:
            pass

    return run


def resolve(future: "asyncio.Future[T]", value: T) -> None:
    """Port of a promise's resolve(): only the first call settles the promise."""
    if not future.done():
        future.set_result(value)


def test_RO_186_context_unroute_should_not_wait_for_pending_handlers_to_complete(
    page: Page,
    context: BrowserContext,
    server: Server,
    sync_gather: Callable[..., List[Any]],
) -> None:
    second_handler_called = False

    def handler1(route: Route) -> None:
        nonlocal second_handler_called
        second_handler_called = True
        route.continue_()

    context.route(re.compile(".*"), handler1)
    route_future: "asyncio.Future[None]" = asyncio.Future()
    route_barrier: "asyncio.Future[None]" = asyncio.Future()

    def handler(route: Route) -> None:
        resolve(route_future, None)
        wait_for(page, route_barrier)
        route.fallback()

    context.route(re.compile(".*"), handler)

    def unroute() -> None:
        wait_for(page, route_future)
        context.unroute(re.compile(".*"), handler)
        route_barrier.set_result(None)

    sync_gather(lambda: page.goto(server.EMPTY_PAGE), unroute)
    assert second_handler_called is True


def test_RO_187_context_unroute_all_removes_all_handlers(
    page: Page, context: BrowserContext, server: Server
) -> None:
    context.route("**/*", lambda route: route.abort())
    context.route("**/empty.html", lambda route: route.abort())
    context.unroute_all()
    page.goto(server.EMPTY_PAGE)


def test_RO_188_context_unroute_all_should_wait_for_pending_handlers_to_complete(
    page: Page,
    context: BrowserContext,
    server: Server,
    sync_gather: Callable[..., List[Any]],
) -> None:
    second_handler_called = False

    def handler1(route: Route) -> None:
        nonlocal second_handler_called
        second_handler_called = True
        route.abort()

    context.route(re.compile(".*"), handler1)
    route_future: "asyncio.Future[None]" = asyncio.Future()
    route_barrier: "asyncio.Future[None]" = asyncio.Future()

    def handler(route: Route) -> None:
        resolve(route_future, None)
        wait_for(page, route_barrier)
        route.fallback()

    context.route(re.compile(".*"), handler)
    did_unroute = False

    def unroute() -> None:
        nonlocal did_unroute
        wait_for(page, route_future)
        context.unroute_all(behavior="wait")
        did_unroute = True

    def release() -> None:
        wait_for(page, route_future)
        wait_for(page, asyncio.sleep(0.5))
        assert did_unroute is False
        route_barrier.set_result(None)

    sync_gather(lambda: page.goto(server.EMPTY_PAGE), unroute, release)
    assert did_unroute is True
    assert second_handler_called is False


def test_RO_189_context_unroute_all_should_not_wait_for_pending_handlers_to_complete_if_behavior_is_ignore_errors(
    page: Page,
    context: BrowserContext,
    server: Server,
    sync_gather: Callable[..., List[Any]],
) -> None:
    second_handler_called = False

    def handler1(route: Route) -> None:
        nonlocal second_handler_called
        second_handler_called = True
        route.abort()

    context.route(re.compile(".*"), handler1)
    route_future: "asyncio.Future[None]" = asyncio.Future()
    route_barrier: "asyncio.Future[None]" = asyncio.Future()

    def handler(route: Route) -> None:
        resolve(route_future, None)
        wait_for(page, route_barrier)
        raise Exception("Handler error")

    context.route(re.compile(".*"), handler)
    did_unroute = False
    unroute_future: "asyncio.Future[None]" = asyncio.Future()

    def unroute() -> None:
        nonlocal did_unroute
        wait_for(page, route_future)
        context.unroute_all(behavior="ignoreErrors")
        did_unroute = True
        unroute_future.set_result(None)

    def release() -> None:
        wait_for(page, route_future)
        wait_for(page, asyncio.sleep(0.5))
        wait_for(page, unroute_future)
        assert did_unroute is True
        route_barrier.set_result(None)

    sync_gather(ignore_error(lambda: page.goto(server.EMPTY_PAGE)), unroute, release)
    # The error in the unrouted handler should be silently caught and remaining handler called.
    assert second_handler_called is False


def test_RO_190_page_close_should_not_wait_for_active_route_handlers_on_the_owning_context(
    page: Page,
    context: BrowserContext,
    server: Server,
    sync_gather: Callable[..., List[Any]],
) -> None:
    route_future: "asyncio.Future[None]" = asyncio.Future()

    def context_handler(route: Route) -> None:
        resolve(route_future, None)

    context.route(re.compile(".*"), context_handler)

    def page_handler(route: Route) -> None:
        route.fallback()

    page.route(re.compile(".*"), page_handler)

    def close() -> None:
        wait_for(page, route_future)
        page.close()

    sync_gather(ignore_error(lambda: page.goto(server.EMPTY_PAGE)), close)


def test_RO_191_context_close_should_not_wait_for_active_route_handlers_on_the_owned_pages(
    page: Page,
    context: BrowserContext,
    server: Server,
    sync_gather: Callable[..., List[Any]],
) -> None:
    route_future: "asyncio.Future[None]" = asyncio.Future()

    def handler1(route: Route) -> None:
        resolve(route_future, None)

    page.route(re.compile(".*"), handler1)

    def handler2(route: Route) -> None:
        route.fallback()

    page.route(re.compile(".*"), handler2)

    def close() -> None:
        wait_for(page, route_future)
        context.close()

    sync_gather(ignore_error(lambda: page.goto(server.EMPTY_PAGE)), close)


def test_RO_192_page_unroute_should_not_wait_for_pending_handlers_to_complete(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    second_handler_called = False

    def handler1(route: Route) -> None:
        nonlocal second_handler_called
        second_handler_called = True
        route.continue_()

    page.route(re.compile(".*"), handler1)
    route_future: "asyncio.Future[None]" = asyncio.Future()
    route_barrier: "asyncio.Future[None]" = asyncio.Future()

    def handler(route: Route) -> None:
        resolve(route_future, None)
        wait_for(page, route_barrier)
        route.fallback()

    page.route(re.compile(".*"), handler)

    def unroute() -> None:
        wait_for(page, route_future)
        page.unroute(re.compile(".*"), handler)
        route_barrier.set_result(None)

    sync_gather(lambda: page.goto(server.EMPTY_PAGE), unroute)
    assert second_handler_called is True


def test_RO_193_page_unroute_all_removes_all_routes(page: Page, server: Server) -> None:
    page.route("**/*", lambda route: route.abort())
    page.route("**/empty.html", lambda route: route.abort())
    page.unroute_all()
    response = must(page.goto(server.EMPTY_PAGE))
    assert response.ok is True


def test_RO_194_page_unroute_all_should_wait_for_pending_handlers_to_complete(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    second_handler_called = False

    def handler1(route: Route) -> None:
        nonlocal second_handler_called
        second_handler_called = True
        route.abort()

    page.route(re.compile(".*"), handler1)
    route_future: "asyncio.Future[None]" = asyncio.Future()
    route_barrier: "asyncio.Future[None]" = asyncio.Future()

    def handler(route: Route) -> None:
        resolve(route_future, None)
        wait_for(page, route_barrier)
        route.fallback()

    page.route(re.compile(".*"), handler)
    did_unroute = False

    def unroute() -> None:
        nonlocal did_unroute
        wait_for(page, route_future)
        page.unroute_all(behavior="wait")
        did_unroute = True

    def release() -> None:
        wait_for(page, route_future)
        wait_for(page, asyncio.sleep(0.5))
        assert did_unroute is False
        route_barrier.set_result(None)

    sync_gather(lambda: page.goto(server.EMPTY_PAGE), unroute, release)
    assert did_unroute is True
    assert second_handler_called is False


def test_RO_195_page_unroute_all_should_not_wait_for_pending_handlers_to_complete_if_behavior_is_ignore_errors(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    second_handler_called = False

    def handler1(route: Route) -> None:
        nonlocal second_handler_called
        second_handler_called = True
        route.abort()

    page.route(re.compile(".*"), handler1)
    route_future: "asyncio.Future[None]" = asyncio.Future()
    route_barrier: "asyncio.Future[None]" = asyncio.Future()

    def handler(route: Route) -> None:
        resolve(route_future, None)
        wait_for(page, route_barrier)
        raise Exception("Handler error")

    page.route(re.compile(".*"), handler)
    did_unroute = False
    unroute_future: "asyncio.Future[None]" = asyncio.Future()

    def unroute() -> None:
        nonlocal did_unroute
        wait_for(page, route_future)
        page.unroute_all(behavior="ignoreErrors")
        did_unroute = True
        unroute_future.set_result(None)

    def release() -> None:
        wait_for(page, route_future)
        wait_for(page, asyncio.sleep(0.5))
        wait_for(page, unroute_future)
        assert did_unroute is True
        route_barrier.set_result(None)

    sync_gather(ignore_error(lambda: page.goto(server.EMPTY_PAGE)), unroute, release)
    # The error in the unrouted handler should be silently caught.
    assert second_handler_called is False


def test_RO_196_page_close_does_not_wait_for_active_route_handlers(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    second_handler_called = False

    def handler1(route: Route) -> None:
        nonlocal second_handler_called
        second_handler_called = True

    page.route(re.compile(".*"), handler1)
    route_future: "asyncio.Future[None]" = asyncio.Future()

    def handler(route: Route) -> None:
        resolve(route_future, None)
        never: "asyncio.Future[None]" = asyncio.Future()
        wait_for(page, never)

    page.route(re.compile(".*"), handler)

    def close() -> None:
        wait_for(page, route_future)
        page.close()
        wait_for(page, asyncio.sleep(0.5))

    sync_gather(ignore_error(lambda: page.goto(server.EMPTY_PAGE)), close)
    assert second_handler_called is False


def test_RO_197_route_continue_should_not_throw_if_page_has_been_closed(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    route_future: "asyncio.Future[Route]" = asyncio.Future()

    def handler(route: Route) -> None:
        resolve(route_future, route)

    page.route(re.compile(".*"), handler)

    def close() -> None:
        route = wait_for(page, route_future)
        page.close()
        # Should not throw.
        route.continue_()

    sync_gather(ignore_error(lambda: page.goto(server.EMPTY_PAGE)), close)


def test_RO_198_route_fallback_should_not_throw_if_page_has_been_closed(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    route_future: "asyncio.Future[Route]" = asyncio.Future()

    def handler(route: Route) -> None:
        resolve(route_future, route)

    page.route(re.compile(".*"), handler)

    def close() -> None:
        route = wait_for(page, route_future)
        page.close()
        # Should not throw.
        route.fallback()

    sync_gather(ignore_error(lambda: page.goto(server.EMPTY_PAGE)), close)


def test_RO_199_route_fulfill_should_not_throw_if_page_has_been_closed(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    route_future: "asyncio.Future[Route]" = asyncio.Future()

    def handler(route: Route) -> None:
        resolve(route_future, route)

    page.route(re.compile(".*"), handler)

    def close() -> None:
        route = wait_for(page, route_future)
        page.close()
        # Should not throw.
        route.fulfill()

    sync_gather(ignore_error(lambda: page.goto(server.EMPTY_PAGE)), close)


def test_RO_200_should_not_continue_requests_in_flight_page(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    route_future: "asyncio.Future[None]" = asyncio.Future()
    page.goto(server.EMPTY_PAGE)

    def handler(route: Route) -> None:
        resolve(route_future, None)
        wait_for(page, asyncio.sleep(3))
        response = route.fetch()
        route.fulfill(response=response)

    page.route("**/*", handler)

    def unroute() -> None:
        wait_for(page, route_future)
        page.unroute_all(behavior="wait")

    sync_gather(ignore_error(lambda: page.evaluate("() => fetch('/')")), unroute)


def test_RO_201_should_not_continue_requests_in_flight_context(
    page: Page,
    context: BrowserContext,
    server: Server,
    sync_gather: Callable[..., List[Any]],
) -> None:
    route_future: "asyncio.Future[None]" = asyncio.Future()
    page.goto(server.EMPTY_PAGE)

    def handler(route: Route) -> None:
        resolve(route_future, None)
        wait_for(page, asyncio.sleep(3))
        response = route.fetch()
        route.fulfill(response=response)

    context.route("**/*", handler)

    def unroute() -> None:
        wait_for(page, route_future)
        context.unroute_all(behavior="wait")

    sync_gather(ignore_error(lambda: page.evaluate("() => fetch('/')")), unroute)
