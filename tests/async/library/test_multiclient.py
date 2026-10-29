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

"""Port of tests/library/multiclient.spec.ts."""

import asyncio
import re
import time
from typing import (
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    List,
    Tuple,
)

import pytest

from playwright.async_api import (
    Browser,
    BrowserContext,
    BrowserType,
    Error,
    Locator,
    Page,
    Playwright,
    Route,
    ScreencastFrame,
    WebSocketRoute,
    expect,
)
from tests.conftest import RemoteServer
from tests.server import Server, TestServerRequest
from tests.utils import TARGET_CLOSED_ERROR_MESSAGE

from ..utils import Utils

TwoPages = Tuple[Page, Page]


@pytest.fixture
def remote_server(launch_server: Callable[..., RemoteServer]) -> RemoteServer:
    """Port of the remoteServer fixture: browserType.launchServer({ _sharedBrowser: true })."""
    return launch_server(_sharedBrowser=True)


@pytest.fixture
async def connect(
    browser_type: BrowserType,
) -> AsyncGenerator[Callable[..., Awaitable[Browser]], None]:
    browsers: List[Browser] = []

    async def _connect(ws_endpoint: str, **options: Any) -> Browser:
        browser = await browser_type.connect(ws_endpoint, **options)
        browsers.append(browser)
        return browser

    yield _connect
    for browser in browsers:
        await browser.close()


@pytest.fixture
async def two_pages(
    remote_server: RemoteServer, connect: Callable[..., Awaitable[Browser]]
) -> TwoPages:
    browser_a = await connect(remote_server.ws_endpoint)
    context_a = await browser_a.new_context()
    page_a = await context_a.new_page()

    browser_b = await connect(remote_server.ws_endpoint)
    context_b = browser_b.contexts[0]
    page_b = context_b.pages[0]

    return page_a, page_b


async def wait_for_timeout(playwright: Playwright, timeout: float) -> None:
    """Lets the event loop run for timeout milliseconds."""
    await asyncio.sleep(timeout / 1000)


async def poll(
    playwright: Playwright, predicate: Callable[[], bool], timeout: float = 5000
) -> None:
    """Port of `await expect.poll(...)`: waits until predicate() is true."""
    deadline = time.monotonic() + timeout / 1000
    while not predicate():
        assert time.monotonic() < deadline, f"Timeout {timeout}ms exceeded"
        await wait_for_timeout(playwright, 100)


async def disconnect(playwright: Playwright, page: Page) -> None:
    browser = page.context.browser
    assert browser
    await browser.close()
    # Give disconnect some time to cleanup.
    await wait_for_timeout(playwright, 1000)


async def test_MC_001_should_connect_two_clients(
    playwright: Playwright,
    connect: Callable[..., Awaitable[Browser]],
    remote_server: RemoteServer,
    server: Server,
) -> None:
    browser_a = await connect(remote_server.ws_endpoint)
    assert len(browser_a.contexts) == 0
    context_a1 = await browser_a.new_context()
    page_a1 = await context_a1.new_page()
    await page_a1.goto(server.EMPTY_PAGE)

    browser_b = await connect(remote_server.ws_endpoint)
    assert len(browser_b.contexts) == 1
    context_b1 = browser_b.contexts[0]
    assert len(context_b1.pages) == 1
    page_b1 = context_b1.pages[0]
    await expect(page_b1).to_have_url(server.EMPTY_PAGE)

    context_b2 = await browser_b.new_context(base_url=server.PREFIX)
    assert browser_b.contexts == [context_b1, context_b2]
    await poll(playwright, lambda: len(browser_a.contexts) == 2)
    context_a2 = browser_a.contexts[1]
    assert browser_a.contexts == [context_a1, context_a2]

    async with context_b2.expect_page() as page_info:
        page_a2 = await context_a2.new_page()
    page_b2 = await page_info.value
    await page_a2.goto("/frames/frame.html")
    await expect(page_b2).to_have_url("/frames/frame.html")

    # Both contexts and pages should be still operational after any client disconnects.
    await disconnect(playwright, page_a1)

    await expect(page_b1).to_have_url(server.EMPTY_PAGE)
    await expect(page_b2).to_have_url(server.PREFIX + "/frames/frame.html")


async def test_MC_002_should_fire_context_event_on_remote_new_context(
    playwright: Playwright,
    connect: Callable[..., Awaitable[Browser]],
    remote_server: RemoteServer,
) -> None:
    browser_a = await connect(remote_server.ws_endpoint)
    events: List[BrowserContext] = []
    browser_a.on("context", lambda ctx: events.append(ctx))

    browser_b = await connect(remote_server.ws_endpoint)
    context_b = await browser_b.new_context()

    await poll(playwright, lambda: len(events) == 1)
    assert browser_a.contexts == [events[0]]
    assert events[0] != context_b


async def test_MC_003_should_have_separate_default_timeouts(
    two_pages: TwoPages,
) -> None:
    page_a, page_b = two_pages
    page_a.set_default_timeout(500)
    page_b.set_default_timeout(600)

    async def click(page: Page) -> Error:
        with pytest.raises(Error) as exc_info:
            await page.click("div")
        return exc_info.value

    error_a, error_b = await asyncio.gather(
        click(page_a),
        click(page_b),
    )
    assert "Timeout 500ms exceeded" in error_a.message
    assert "Timeout 600ms exceeded" in error_b.message


async def test_MC_004_should_receive_viewport_size_changes(
    playwright: Playwright, two_pages: TwoPages
) -> None:
    page_a, page_b = two_pages

    await page_a.set_viewport_size({"width": 567, "height": 456})
    assert page_a.viewport_size == {"width": 567, "height": 456}
    await poll(
        playwright, lambda: page_b.viewport_size == {"width": 567, "height": 456}
    )

    await page_b.set_viewport_size({"width": 456, "height": 567})
    assert page_b.viewport_size == {"width": 456, "height": 567}
    await poll(
        playwright, lambda: page_a.viewport_size == {"width": 456, "height": 567}
    )


async def test_MC_007_should_unpause_clock(
    playwright: Playwright, two_pages: TwoPages
) -> None:
    page_a, page_b = two_pages
    await page_a.clock.install(time=1000)
    await page_a.clock.pause_at(2000)
    promise = asyncio.create_task(
        page_b.evaluate("() => new Promise(f => setTimeout(f, 1000))")
    )
    # Let the task send the call, as calling the function does in JavaScript.
    await asyncio.sleep(0)
    await disconnect(playwright, page_a)
    await promise


async def test_MC_008_last_emulate_media_wins(two_pages: TwoPages) -> None:
    page_a, page_b = two_pages
    await page_a.emulate_media(media="print")
    assert await page_b.evaluate("() => window.matchMedia('screen').matches") is False
    assert await page_a.evaluate("() => window.matchMedia('print').matches") is True
    await page_b.emulate_media(media="screen")
    assert await page_b.evaluate("() => window.matchMedia('screen').matches") is True
    assert await page_a.evaluate("() => window.matchMedia('print').matches") is False


def html_route(body: str) -> Callable[[TestServerRequest], None]:
    def handler(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("Content-Type", "text/html")
        request.write(body.encode())
        request.finish()

    return handler


async def test_MC_009_should_chain_routes(
    playwright: Playwright, two_pages: TwoPages, server: Server
) -> None:
    page_a, page_b = two_pages

    server.set_route("/foo", html_route("<div>server-foo</div>"))
    server.set_route("/bar", html_route("<div>server-bar</div>"))
    server.set_route("/qux", html_route("<div>server-qux</div>"))

    stall = False
    stalled: List[bool] = []

    async def handle_foo_a(route: Route) -> None:
        if stall:
            stalled.append(True)
        else:
            await route.fallback()

    await page_a.route("**/foo", handle_foo_a)

    async def handle_bar_a(route: Route) -> None:
        await route.fulfill(body="<div>intercepted-bar</div>", content_type="text/html")

    await page_a.route("**/bar", handle_bar_a)

    async def handle_foo_b(route: Route) -> None:
        await route.fulfill(
            body="<div>intercepted2-foo</div>", content_type="text/html"
        )

    await page_b.route("**/foo", handle_foo_b)

    async def handle_bar_b(route: Route) -> None:
        await route.fulfill(
            body="<div>intercepted2-bar</div>", content_type="text/html"
        )

    await page_b.route("**/bar", handle_bar_b)

    async def handle_qux_b(route: Route) -> None:
        await route.fulfill(
            body="<div>intercepted2-qux</div>", content_type="text/html"
        )

    await page_b.route("**/qux", handle_qux_b)

    await page_a.goto(server.PREFIX + "/foo")
    await expect(page_b.locator("div")).to_have_text("intercepted2-foo")

    await page_a.goto(server.PREFIX + "/bar")
    await expect(page_b.locator("div")).to_have_text("intercepted-bar")

    await page_a.goto(server.PREFIX + "/qux")
    await expect(page_b.locator("div")).to_have_text("intercepted2-qux")

    stall = True
    goto_promise = asyncio.create_task(page_b.goto(server.PREFIX + "/foo"))
    await poll(playwright, lambda: len(stalled) > 0, timeout=30000)
    browser_a = page_a.context.browser
    assert browser_a
    await browser_a.close()

    await goto_promise
    await expect(page_b.locator("div")).to_have_text("intercepted2-foo")

    await page_b.goto(server.PREFIX + "/bar")
    await expect(page_b.locator("div")).to_have_text("intercepted2-bar")


async def test_MC_010_should_chain_routes_with_changed_url(
    two_pages: TwoPages, server: Server
) -> None:
    pytest.skip("fixme")
    page_a, page_b = two_pages

    server.set_route("/foo", html_route("<div>server-foo</div>"))
    server.set_route("/baz", html_route("<div>server-baz</div>"))

    async def handle_foo_a(route: Route) -> None:
        await route.fallback(url=server.PREFIX + "/baz")

    await page_a.route("**/foo", handle_foo_a)

    async def handle_baz_b(route: Route) -> None:
        await route.fulfill(
            body="<div>intercepted2-baz</div>", content_type="text/html"
        )

    await page_b.route("**/baz", handle_baz_b)

    await page_a.goto(server.PREFIX + "/foo")
    await expect(page_b.locator("div")).to_have_text("intercepted2-baz")


async def test_MC_011_should_remove_exposed_bindings_upon_disconnect(
    playwright: Playwright, two_pages: TwoPages
) -> None:
    page_a, page_b = two_pages

    await page_a.expose_binding("pageBindingA", lambda source: "pageBindingAResult")
    await page_a.evaluate("() => { window.pageBindingACopy = window.pageBindingA; }")
    assert await page_b.evaluate("() => window.pageBindingA()") == "pageBindingAResult"
    assert await page_b.evaluate("() => !!window.pageBindingACopy") is True

    await page_a.context.expose_binding(
        "contextBindingA", lambda source: "contextBindingAResult"
    )
    assert (
        await page_b.evaluate("() => window.contextBindingA()")
        == "contextBindingAResult"
    )

    await page_b.expose_binding("pageBindingB", lambda source: "pageBindingBResult")
    assert await page_a.evaluate("() => window.pageBindingB()") == "pageBindingBResult"
    await page_b.context.expose_binding(
        "contextBindingB", lambda source: "contextBindingBResult"
    )
    assert (
        await page_a.evaluate("() => window.contextBindingB()")
        == "contextBindingBResult"
    )

    await disconnect(playwright, page_a)

    assert await page_b.evaluate("() => window.pageBindingA") is None
    assert await page_b.evaluate("() => window.contextBindingA") is None
    with pytest.raises(Error) as exc_info:
        await page_b.evaluate("() => window.pageBindingACopy()")
    assert 'binding "pageBindingA" has been removed' in exc_info.value.message

    assert await page_b.evaluate("() => window.pageBindingB()") == "pageBindingBResult"


async def test_MC_012_should_unroute_websockets(
    playwright: Playwright, two_pages: TwoPages, server: Server
) -> None:
    page_a, page_b = two_pages

    await page_a.goto(server.EMPTY_PAGE)
    await page_a.route_web_socket(re.compile(".*"), lambda ws: None)
    await page_a.route_web_socket(re.compile(".*"), lambda ws: None)
    await page_a.route_web_socket(re.compile(".*"), lambda ws: None)

    with pytest.raises(Error) as exc_info:
        await page_b.route_web_socket(re.compile(".*"), lambda ws: None)
    assert "Another client is already routing WebSockets" in exc_info.value.message

    await disconnect(playwright, page_a)

    routed: List[WebSocketRoute] = []
    await page_b.route_web_socket(re.compile(".*"), lambda ws: routed.append(ws))
    await page_b.goto(server.EMPTY_PAGE)
    await page_b.evaluate(
        "host => window.ws = new WebSocket('ws://' + host + '/ws')", server.HOST
    )
    await poll(playwright, lambda: len(routed) > 0, timeout=30000)


async def test_MC_013_should_remove_init_scripts_upon_disconnect(
    playwright: Playwright, two_pages: TwoPages, server: Server
) -> None:
    page_a, page_b = two_pages

    await page_a.add_init_script("window.pageValueA = 'pageValueA'")
    await page_a.context.add_init_script("window.contextValueA = 'contextValueA'")
    await page_b.goto(server.EMPTY_PAGE)
    assert await page_b.evaluate("() => window.pageValueA") == "pageValueA"
    assert await page_b.evaluate("() => window.contextValueA") == "contextValueA"

    await page_b.add_init_script("window.pageValueB = 'pageValueB'")
    await page_b.context.add_init_script("window.contextValueB = 'contextValueB'")
    await page_a.goto(server.EMPTY_PAGE)
    assert await page_a.evaluate("() => window.pageValueB") == "pageValueB"
    assert await page_a.evaluate("() => window.contextValueB") == "contextValueB"

    await disconnect(playwright, page_b)

    await page_a.goto(server.EMPTY_PAGE)
    assert await page_a.evaluate("() => window.pageValueB") is None
    assert await page_a.evaluate("() => window.contextValueB") is None
    assert await page_a.evaluate("() => window.pageValueA") == "pageValueA"
    assert await page_a.evaluate("() => window.contextValueA") == "contextValueA"


async def test_MC_014_should_remove_locator_handlers_upon_disconnect(
    playwright: Playwright, two_pages: TwoPages, server: Server
) -> None:
    page_a, page_b = two_pages

    await page_a.goto(server.PREFIX + "/input/handle-locator.html")

    count = 0

    async def handler(locator: Locator) -> None:
        nonlocal count
        count += 1
        await page_a.locator("#close").click()

    await page_a.add_locator_handler(
        page_a.get_by_text("This interstitial covers the button"), handler
    )

    await page_a.locator("#aside").hover()
    await page_a.evaluate(
        """() => {
        window.clicked = 0;
        window.setupAnnoyingInterstitial('mouseover', 1);
    }"""
    )
    await page_a.locator("#target").click()
    assert count == 1
    assert await page_b.evaluate("window.clicked") == 1
    await expect(page_b.locator("#interstitial")).not_to_be_visible()

    await page_a.locator("#aside").hover()
    await page_a.evaluate(
        """() => {
        window.clicked = 0;
        window.setupAnnoyingInterstitial('mouseover', 1);
    }"""
    )

    await disconnect(playwright, page_a)

    with pytest.raises(Error) as exc_info:
        await page_b.locator("#target").click(timeout=3000)
    assert "Timeout 3000ms exceeded" in exc_info.value.message
    assert "intercepts pointer events" in exc_info.value.message
    assert "locator handler" not in exc_info.value.message


async def test_MC_015_should_launch_persistent(
    browser_type: BrowserType, launch_server: Callable[..., RemoteServer]
) -> None:
    browser_server = launch_server(_userDataDir="", _sharedBrowser=True)
    browser = await browser_type.connect(browser_server.ws_endpoint)
    assert len(browser.contexts) == 1
    await browser.close()
    browser_server.kill()


async def test_MC_016_should_avoid_side_effects_upon_disconnect(
    playwright: Playwright, two_pages: TwoPages, server: Server
) -> None:
    page_a, page_b = two_pages

    counter = 0

    def on_console(_: Any) -> None:
        nonlocal counter
        counter += 1

    page_b.on("console", on_console)

    async def wait_for_function() -> Error:
        with pytest.raises(Error) as exc_info:
            await page_a.wait_for_function(
                """() => {
                window['counter'] = (window['counter'] || 0) + 1;
                console.log(window['counter']);
            }""",
                polling=1,
                timeout=10000,
            )
        return exc_info.value

    promise = asyncio.create_task(wait_for_function())
    # Let the task send the call, as calling the function does in JavaScript.
    await asyncio.sleep(0)

    await disconnect(playwright, page_a)
    error = await promise
    saved_counter = counter

    await page_b.wait_for_timeout(2000)  # Give it some time to produce more logs.

    assert TARGET_CLOSED_ERROR_MESSAGE in error.message
    assert counter == saved_counter


async def test_MC_017_screencast_should_deliver_cached_last_frame_to_a_new_client(
    playwright: Playwright, two_pages: TwoPages, server: Server, utils: Utils
) -> None:
    page_a, page_b = two_pages
    await page_a.goto(server.EMPTY_PAGE)
    await page_a.evaluate("() => document.body.style.backgroundColor = 'red'")

    frames_a: List[bytes] = []
    await page_a.screencast.start(
        on_frame=lambda frame: frames_a.append(frame["data"]),
        size={"width": 320, "height": 240},
    )
    # Port of ensureSomeFrames() in tests/config/utils.ts.
    await utils.rafraf(page_a, 100)
    await page_a.screenshot()
    assert len(frames_a) > 0
    last_frame_a = frames_a[-1]

    frames_b: List[bytes] = []

    def on_frame_b(frame: ScreencastFrame) -> None:
        frames_b.append(frame["data"])

    await page_b.screencast.start(on_frame=on_frame_b)
    # Second client should receive the cached last frame without waiting for a browser repaint.
    await poll(playwright, lambda: len(frames_b) > 0, timeout=5000)
    assert frames_b[0] == last_frame_a

    await page_a.screencast.stop()
    await page_b.screencast.stop()


async def test_MC_018_should_stop_tracing_upon_disconnect(
    playwright: Playwright, two_pages: TwoPages
) -> None:
    page_a, page_b = two_pages

    await page_a.context.tracing.start()
    with pytest.raises(Error) as exc_info:
        await page_b.context.tracing.start()
    assert "Tracing has been already started" in exc_info.value.message

    await disconnect(playwright, page_a)

    await page_b.context.tracing.start()


@pytest.mark.slow
async def test_MC_020_should_run_locator_handlers_after_reconnecting_with_a_pending_callback(
    playwright: Playwright,
    connect: Callable[..., Awaitable[Browser]],
    remote_server: RemoteServer,
    server: Server,
) -> None:
    browser = await connect(remote_server.ws_endpoint)
    page = await browser.new_page()
    await page.goto(server.PREFIX + "/input/handle-locator.html")

    called = 0

    async def handler() -> None:
        nonlocal called
        called += 1
        await asyncio.Future()

    await page.add_locator_handler(
        page.get_by_text("This interstitial covers the button"), handler
    )
    await page.evaluate(
        """() => {
        window.setupAnnoyingInterstitial('none', 1);
    }"""
    )
    with pytest.raises(Error) as exc_info:
        await page.locator("#target").click(timeout=1000)
    assert "Timeout 1000ms exceeded" in exc_info.value.message
    assert called == 1

    await disconnect(playwright, page)

    reconnected_browser = await connect(remote_server.ws_endpoint)
    reconnected_page = reconnected_browser.contexts[0].pages[0]

    async def reconnected_handler() -> None:
        await reconnected_page.locator("#close").click()

    await reconnected_page.add_locator_handler(
        reconnected_page.get_by_text("This interstitial covers the button"),
        reconnected_handler,
    )
    await reconnected_page.locator("#target").click(timeout=3000)
    assert await reconnected_page.evaluate("window.clicked") == 1
