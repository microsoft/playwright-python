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

import re
import time
from typing import Any, Callable, Generator, List, Tuple

import pytest

from playwright._impl._greenlets import wait_for_future
from playwright.sync_api import (
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
def connect(
    browser_type: BrowserType,
) -> Generator[Callable[..., Browser], None, None]:
    browsers: List[Browser] = []

    def _connect(ws_endpoint: str, **options: Any) -> Browser:
        browser = browser_type.connect(ws_endpoint, **options)
        browsers.append(browser)
        return browser

    yield _connect
    for browser in browsers:
        browser.close()


@pytest.fixture
def two_pages(remote_server: RemoteServer, connect: Callable[..., Browser]) -> TwoPages:
    browser_a = connect(remote_server.ws_endpoint)
    context_a = browser_a.new_context()
    page_a = context_a.new_page()

    browser_b = connect(remote_server.ws_endpoint)
    context_b = browser_b.contexts[0]
    page_b = context_b.pages[0]

    return page_a, page_b


def wait_for_timeout(playwright: Playwright, timeout: float) -> None:
    """Lets the event loop run for timeout milliseconds.

    The sync API runs the event loop only while a call waits, so time.sleep() would
    not deliver the events of the other client.
    """
    loop = playwright._loop
    future = loop.create_future()

    def resolve() -> None:
        if not future.done():
            future.set_result(None)

    loop.call_later(timeout / 1000, resolve)
    wait_for_future(loop, playwright._dispatcher_fiber, future)


def poll(
    playwright: Playwright, predicate: Callable[[], bool], timeout: float = 5000
) -> None:
    """Port of `expect.poll(...)`: waits until predicate() is true."""
    deadline = time.monotonic() + timeout / 1000
    while not predicate():
        assert time.monotonic() < deadline, f"Timeout {timeout}ms exceeded"
        wait_for_timeout(playwright, 100)


def disconnect(playwright: Playwright, page: Page) -> None:
    browser = page.context.browser
    assert browser
    browser.close()
    # Give disconnect some time to cleanup.
    wait_for_timeout(playwright, 1000)


def test_MC_001_should_connect_two_clients(
    playwright: Playwright,
    connect: Callable[..., Browser],
    remote_server: RemoteServer,
    server: Server,
) -> None:
    browser_a = connect(remote_server.ws_endpoint)
    assert len(browser_a.contexts) == 0
    context_a1 = browser_a.new_context()
    page_a1 = context_a1.new_page()
    page_a1.goto(server.EMPTY_PAGE)

    browser_b = connect(remote_server.ws_endpoint)
    assert len(browser_b.contexts) == 1
    context_b1 = browser_b.contexts[0]
    assert len(context_b1.pages) == 1
    page_b1 = context_b1.pages[0]
    expect(page_b1).to_have_url(server.EMPTY_PAGE)

    context_b2 = browser_b.new_context(base_url=server.PREFIX)
    assert browser_b.contexts == [context_b1, context_b2]
    poll(playwright, lambda: len(browser_a.contexts) == 2)
    context_a2 = browser_a.contexts[1]
    assert browser_a.contexts == [context_a1, context_a2]

    with context_b2.expect_page() as page_info:
        page_a2 = context_a2.new_page()
    page_b2 = page_info.value
    page_a2.goto("/frames/frame.html")
    expect(page_b2).to_have_url("/frames/frame.html")

    # Both contexts and pages should be still operational after any client disconnects.
    disconnect(playwright, page_a1)

    expect(page_b1).to_have_url(server.EMPTY_PAGE)
    expect(page_b2).to_have_url(server.PREFIX + "/frames/frame.html")


def test_MC_002_should_fire_context_event_on_remote_new_context(
    playwright: Playwright,
    connect: Callable[..., Browser],
    remote_server: RemoteServer,
) -> None:
    browser_a = connect(remote_server.ws_endpoint)
    events: List[BrowserContext] = []
    browser_a.on("context", lambda ctx: events.append(ctx))

    browser_b = connect(remote_server.ws_endpoint)
    context_b = browser_b.new_context()

    poll(playwright, lambda: len(events) == 1)
    assert browser_a.contexts == [events[0]]
    assert events[0] != context_b


def test_MC_003_should_have_separate_default_timeouts(
    two_pages: TwoPages, sync_gather: Callable
) -> None:
    page_a, page_b = two_pages
    page_a.set_default_timeout(500)
    page_b.set_default_timeout(600)

    def click(page: Page) -> Error:
        with pytest.raises(Error) as exc_info:
            page.click("div")
        return exc_info.value

    error_a, error_b = sync_gather(
        lambda: click(page_a),
        lambda: click(page_b),
    )
    assert "Timeout 500ms exceeded" in error_a.message
    assert "Timeout 600ms exceeded" in error_b.message


def test_MC_004_should_receive_viewport_size_changes(
    playwright: Playwright, two_pages: TwoPages
) -> None:
    page_a, page_b = two_pages

    page_a.set_viewport_size({"width": 567, "height": 456})
    assert page_a.viewport_size == {"width": 567, "height": 456}
    poll(playwright, lambda: page_b.viewport_size == {"width": 567, "height": 456})

    page_b.set_viewport_size({"width": 456, "height": 567})
    assert page_b.viewport_size == {"width": 456, "height": 567}
    poll(playwright, lambda: page_a.viewport_size == {"width": 456, "height": 567})


def test_MC_007_should_unpause_clock(
    playwright: Playwright, two_pages: TwoPages, sync_gather: Callable
) -> None:
    page_a, page_b = two_pages
    page_a.clock.install(time=1000)
    page_a.clock.pause_at(2000)
    sync_gather(
        lambda: page_b.evaluate("() => new Promise(f => setTimeout(f, 1000))"),
        lambda: disconnect(playwright, page_a),
    )


def test_MC_008_last_emulate_media_wins(two_pages: TwoPages) -> None:
    page_a, page_b = two_pages
    page_a.emulate_media(media="print")
    assert page_b.evaluate("() => window.matchMedia('screen').matches") is False
    assert page_a.evaluate("() => window.matchMedia('print').matches") is True
    page_b.emulate_media(media="screen")
    assert page_b.evaluate("() => window.matchMedia('screen').matches") is True
    assert page_a.evaluate("() => window.matchMedia('print').matches") is False


def html_route(body: str) -> Callable[[TestServerRequest], None]:
    def handler(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("Content-Type", "text/html")
        request.write(body.encode())
        request.finish()

    return handler


def test_MC_009_should_chain_routes(
    playwright: Playwright, two_pages: TwoPages, server: Server, sync_gather: Callable
) -> None:
    page_a, page_b = two_pages

    server.set_route("/foo", html_route("<div>server-foo</div>"))
    server.set_route("/bar", html_route("<div>server-bar</div>"))
    server.set_route("/qux", html_route("<div>server-qux</div>"))

    stall = False
    stalled: List[bool] = []

    def handle_foo_a(route: Route) -> None:
        if stall:
            stalled.append(True)
        else:
            route.fallback()

    page_a.route("**/foo", handle_foo_a)

    def handle_bar_a(route: Route) -> None:
        route.fulfill(body="<div>intercepted-bar</div>", content_type="text/html")

    page_a.route("**/bar", handle_bar_a)

    def handle_foo_b(route: Route) -> None:
        route.fulfill(body="<div>intercepted2-foo</div>", content_type="text/html")

    page_b.route("**/foo", handle_foo_b)

    def handle_bar_b(route: Route) -> None:
        route.fulfill(body="<div>intercepted2-bar</div>", content_type="text/html")

    page_b.route("**/bar", handle_bar_b)

    def handle_qux_b(route: Route) -> None:
        route.fulfill(body="<div>intercepted2-qux</div>", content_type="text/html")

    page_b.route("**/qux", handle_qux_b)

    page_a.goto(server.PREFIX + "/foo")
    expect(page_b.locator("div")).to_have_text("intercepted2-foo")

    page_a.goto(server.PREFIX + "/bar")
    expect(page_b.locator("div")).to_have_text("intercepted-bar")

    page_a.goto(server.PREFIX + "/qux")
    expect(page_b.locator("div")).to_have_text("intercepted2-qux")

    stall = True

    def close_browser_a() -> None:
        poll(playwright, lambda: len(stalled) > 0, timeout=30000)
        browser_a = page_a.context.browser
        assert browser_a
        browser_a.close()

    sync_gather(
        lambda: page_b.goto(server.PREFIX + "/foo"),
        close_browser_a,
    )
    expect(page_b.locator("div")).to_have_text("intercepted2-foo")

    page_b.goto(server.PREFIX + "/bar")
    expect(page_b.locator("div")).to_have_text("intercepted2-bar")


def test_MC_010_should_chain_routes_with_changed_url(
    two_pages: TwoPages, server: Server
) -> None:
    pytest.skip("fixme")
    page_a, page_b = two_pages

    server.set_route("/foo", html_route("<div>server-foo</div>"))
    server.set_route("/baz", html_route("<div>server-baz</div>"))

    def handle_foo_a(route: Route) -> None:
        route.fallback(url=server.PREFIX + "/baz")

    page_a.route("**/foo", handle_foo_a)

    def handle_baz_b(route: Route) -> None:
        route.fulfill(body="<div>intercepted2-baz</div>", content_type="text/html")

    page_b.route("**/baz", handle_baz_b)

    page_a.goto(server.PREFIX + "/foo")
    expect(page_b.locator("div")).to_have_text("intercepted2-baz")


def test_MC_011_should_remove_exposed_bindings_upon_disconnect(
    playwright: Playwright, two_pages: TwoPages
) -> None:
    page_a, page_b = two_pages

    page_a.expose_binding("pageBindingA", lambda source: "pageBindingAResult")
    page_a.evaluate("() => { window.pageBindingACopy = window.pageBindingA; }")
    assert page_b.evaluate("() => window.pageBindingA()") == "pageBindingAResult"
    assert page_b.evaluate("() => !!window.pageBindingACopy") is True

    page_a.context.expose_binding(
        "contextBindingA", lambda source: "contextBindingAResult"
    )
    assert page_b.evaluate("() => window.contextBindingA()") == "contextBindingAResult"

    page_b.expose_binding("pageBindingB", lambda source: "pageBindingBResult")
    assert page_a.evaluate("() => window.pageBindingB()") == "pageBindingBResult"
    page_b.context.expose_binding(
        "contextBindingB", lambda source: "contextBindingBResult"
    )
    assert page_a.evaluate("() => window.contextBindingB()") == "contextBindingBResult"

    disconnect(playwright, page_a)

    assert page_b.evaluate("() => window.pageBindingA") is None
    assert page_b.evaluate("() => window.contextBindingA") is None
    with pytest.raises(Error) as exc_info:
        page_b.evaluate("() => window.pageBindingACopy()")
    assert 'binding "pageBindingA" has been removed' in exc_info.value.message

    assert page_b.evaluate("() => window.pageBindingB()") == "pageBindingBResult"


def test_MC_012_should_unroute_websockets(
    playwright: Playwright, two_pages: TwoPages, server: Server
) -> None:
    page_a, page_b = two_pages

    page_a.goto(server.EMPTY_PAGE)
    page_a.route_web_socket(re.compile(".*"), lambda ws: None)
    page_a.route_web_socket(re.compile(".*"), lambda ws: None)
    page_a.route_web_socket(re.compile(".*"), lambda ws: None)

    with pytest.raises(Error) as exc_info:
        page_b.route_web_socket(re.compile(".*"), lambda ws: None)
    assert "Another client is already routing WebSockets" in exc_info.value.message

    disconnect(playwright, page_a)

    routed: List[WebSocketRoute] = []
    page_b.route_web_socket(re.compile(".*"), lambda ws: routed.append(ws))
    page_b.goto(server.EMPTY_PAGE)
    page_b.evaluate(
        "host => window.ws = new WebSocket('ws://' + host + '/ws')", server.HOST
    )
    poll(playwright, lambda: len(routed) > 0, timeout=30000)


def test_MC_013_should_remove_init_scripts_upon_disconnect(
    playwright: Playwright, two_pages: TwoPages, server: Server
) -> None:
    page_a, page_b = two_pages

    page_a.add_init_script("window.pageValueA = 'pageValueA'")
    page_a.context.add_init_script("window.contextValueA = 'contextValueA'")
    page_b.goto(server.EMPTY_PAGE)
    assert page_b.evaluate("() => window.pageValueA") == "pageValueA"
    assert page_b.evaluate("() => window.contextValueA") == "contextValueA"

    page_b.add_init_script("window.pageValueB = 'pageValueB'")
    page_b.context.add_init_script("window.contextValueB = 'contextValueB'")
    page_a.goto(server.EMPTY_PAGE)
    assert page_a.evaluate("() => window.pageValueB") == "pageValueB"
    assert page_a.evaluate("() => window.contextValueB") == "contextValueB"

    disconnect(playwright, page_b)

    page_a.goto(server.EMPTY_PAGE)
    assert page_a.evaluate("() => window.pageValueB") is None
    assert page_a.evaluate("() => window.contextValueB") is None
    assert page_a.evaluate("() => window.pageValueA") == "pageValueA"
    assert page_a.evaluate("() => window.contextValueA") == "contextValueA"


def test_MC_014_should_remove_locator_handlers_upon_disconnect(
    playwright: Playwright, two_pages: TwoPages, server: Server
) -> None:
    page_a, page_b = two_pages

    page_a.goto(server.PREFIX + "/input/handle-locator.html")

    count = 0

    def handler(locator: Locator) -> None:
        nonlocal count
        count += 1
        page_a.locator("#close").click()

    page_a.add_locator_handler(
        page_a.get_by_text("This interstitial covers the button"), handler
    )

    page_a.locator("#aside").hover()
    page_a.evaluate(
        """() => {
        window.clicked = 0;
        window.setupAnnoyingInterstitial('mouseover', 1);
    }"""
    )
    page_a.locator("#target").click()
    assert count == 1
    assert page_b.evaluate("window.clicked") == 1
    expect(page_b.locator("#interstitial")).not_to_be_visible()

    page_a.locator("#aside").hover()
    page_a.evaluate(
        """() => {
        window.clicked = 0;
        window.setupAnnoyingInterstitial('mouseover', 1);
    }"""
    )

    disconnect(playwright, page_a)

    with pytest.raises(Error) as exc_info:
        page_b.locator("#target").click(timeout=3000)
    assert "Timeout 3000ms exceeded" in exc_info.value.message
    assert "intercepts pointer events" in exc_info.value.message
    assert "locator handler" not in exc_info.value.message


def test_MC_015_should_launch_persistent(
    browser_type: BrowserType, launch_server: Callable[..., RemoteServer]
) -> None:
    browser_server = launch_server(_userDataDir="", _sharedBrowser=True)
    browser = browser_type.connect(browser_server.ws_endpoint)
    assert len(browser.contexts) == 1
    browser.close()
    browser_server.kill()


def test_MC_016_should_avoid_side_effects_upon_disconnect(
    playwright: Playwright, two_pages: TwoPages, server: Server, sync_gather: Callable
) -> None:
    page_a, page_b = two_pages

    counter = 0

    def on_console(_: Any) -> None:
        nonlocal counter
        counter += 1

    page_b.on("console", on_console)

    def wait_for_function() -> Error:
        with pytest.raises(Error) as exc_info:
            page_a.wait_for_function(
                """() => {
                window['counter'] = (window['counter'] || 0) + 1;
                console.log(window['counter']);
            }""",
                polling=1,
                timeout=10000,
            )
        return exc_info.value

    error, _ = sync_gather(
        wait_for_function,
        lambda: disconnect(playwright, page_a),
    )
    saved_counter = counter

    page_b.wait_for_timeout(2000)  # Give it some time to produce more logs.

    assert TARGET_CLOSED_ERROR_MESSAGE in error.message
    assert counter == saved_counter


def test_MC_017_screencast_should_deliver_cached_last_frame_to_a_new_client(
    playwright: Playwright, two_pages: TwoPages, server: Server, utils: Utils
) -> None:
    page_a, page_b = two_pages
    page_a.goto(server.EMPTY_PAGE)
    page_a.evaluate("() => document.body.style.backgroundColor = 'red'")

    frames_a: List[bytes] = []
    page_a.screencast.start(
        on_frame=lambda frame: frames_a.append(frame["data"]),
        size={"width": 320, "height": 240},
    )
    # Port of ensureSomeFrames() in tests/config/utils.ts.
    utils.rafraf(page_a, 100)
    page_a.screenshot()
    assert len(frames_a) > 0
    last_frame_a = frames_a[-1]

    frames_b: List[bytes] = []

    def on_frame_b(frame: ScreencastFrame) -> None:
        frames_b.append(frame["data"])

    page_b.screencast.start(on_frame=on_frame_b)
    # Second client should receive the cached last frame without waiting for a browser repaint.
    poll(playwright, lambda: len(frames_b) > 0, timeout=5000)
    assert frames_b[0] == last_frame_a

    page_a.screencast.stop()
    page_b.screencast.stop()


def test_MC_018_should_stop_tracing_upon_disconnect(
    playwright: Playwright, two_pages: TwoPages
) -> None:
    page_a, page_b = two_pages

    page_a.context.tracing.start()
    with pytest.raises(Error) as exc_info:
        page_b.context.tracing.start()
    assert "Tracing has been already started" in exc_info.value.message

    disconnect(playwright, page_a)

    page_b.context.tracing.start()
