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

"""Port of tests/library/browsertype-connect.spec.ts."""

import asyncio
import json
import os
import re
import signal
import threading
import time
import zipfile
from contextlib import suppress
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional
from urllib.parse import urlparse

import pytest

from playwright._impl._driver import compute_driver_executable
from playwright._impl._greenlets import wait_for_future
from playwright._impl._sync_base import EventContextManager
from playwright._impl._sync_base import mapping as api_mapping
from playwright.sync_api import (
    Browser,
    BrowserType,
    Error,
    Page,
    Playwright,
    Route,
    sync_playwright,
)
from tests.helpers.fixed_response_server import FixedResponseServer
from tests.helpers.remote_server import (
    KIND_LAUNCH_SERVER,
    KIND_RUN_SERVER,
    RemoteServerStarter,
    RunServer,
    redirect_port_forwarding_for_test,
)
from tests.helpers.websocket_client import WebSocketClient, forward_web_socket
from tests.server import Server, TestServerRequest, WebSocketProtocol, reactor
from tests.utils import TARGET_CLOSED_ERROR_MESSAGE

from ..utils import Utils

KINDS = [KIND_LAUNCH_SERVER, KIND_RUN_SERVER]


def connect_browser(
    browser_type: BrowserType,
    launch_arguments: Dict,
    ws_endpoint: str,
    redirect_port_for_test: Optional[int] = None,
    launch_options: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    **options: Any,
) -> Browser:
    """Port of the connect fixture: passes the launch options for run-server along."""
    with redirect_port_forwarding_for_test(browser_type, redirect_port_for_test):
        return browser_type.connect(
            ws_endpoint,
            headers={
                "x-playwright-launch-options": json.dumps(
                    {**launch_arguments, **(launch_options or {})}
                ),
                **(headers or {}),
            },
            **options,
        )


@pytest.fixture
def connect(
    browser_type: BrowserType, launch_arguments: Dict
) -> Generator[Callable[..., Browser], None, None]:
    browsers: List[Browser] = []

    def _connect(ws_endpoint: str, **options: Any) -> Browser:
        browser = connect_browser(
            browser_type, launch_arguments, ws_endpoint, **options
        )
        browsers.append(browser)
        return browser

    yield _connect
    for browser in browsers:
        browser.close()


@pytest.fixture
def start_remote_server(
    browser_name: str, launch_arguments: Dict
) -> Generator[RemoteServerStarter, None, None]:
    starter = RemoteServerStarter(browser_name, launch_arguments)
    yield starter
    starter.close()


@pytest.fixture
def dummy_server_port() -> Generator[int, None, None]:
    # Only listen on IPv4 to check that we don't try to connect to it via IPv6.
    server = FixedResponseServer(
        "127.0.0.1", "<html><body>from-dummy-server</body></html>"
    )
    yield server.port
    server.close()


@pytest.fixture
def ipv6_server_port() -> Generator[int, None, None]:
    if os.environ.get("INSIDE_DOCKER"):
        pytest.skip("docker does not support IPv6 by default")
    server = FixedResponseServer("::1", "<html><body>from-ipv6-server</body></html>")
    yield server.port
    server.close()


@pytest.fixture
def server_web_sockets() -> List[WebSocketProtocol]:
    """Collects the test server WebSockets."""
    return []


@pytest.fixture
def worker_index() -> int:
    """Port of testInfo.workerIndex."""
    return int(os.environ.get("PYTEST_XDIST_WORKER", "gw0")[2:])


def run_with_new_playwright(body: Callable[[Playwright], None]) -> None:
    """Runs body with a new Playwright, whose driver starts with the current environment.

    The driver of the session started before the test changed the environment. The
    sync API can not start a second Playwright on the thread of the first one, so
    body runs on a new thread.
    """
    errors: List[BaseException] = []

    def run() -> None:
        try:
            with sync_playwright() as playwright:
                body(playwright)
        except BaseException as error:
            errors.append(error)

    thread = threading.Thread(target=run)
    thread.start()
    thread.join()
    if errors:
        raise errors[0]


def expect_disconnected(browser: Browser) -> EventContextManager[Browser]:
    """Waits for the "disconnected" event, like page.expect_event().

    Browser has no expect_event().
    """
    future: "asyncio.Future[Browser]" = browser._loop.create_future()

    def on_disconnected(disconnected: Browser) -> None:
        if not future.done():
            future.set_result(disconnected)

    browser.once("disconnected", on_disconnected)
    return EventContextManager(browser, future)


def wait_for_timeout(playwright: Playwright, timeout: float) -> None:
    """Lets the event loop run for timeout milliseconds.

    The sync API runs the event loop only while a call waits, so time.sleep() would
    not deliver the events.
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
    """Port of `await expect.poll(...)`: waits until predicate() is true."""
    deadline = time.monotonic() + timeout / 1000
    while not predicate():
        assert time.monotonic() < deadline, f"Timeout {timeout}ms exceeded"
        wait_for_timeout(playwright, 100)


def ensure_some_frames(page: Page, utils: Utils) -> None:
    """Port of ensureSomeFrames() in tests/config/utils.ts."""
    utils.rafraf(page, 100)
    page.screenshot()


def download_route(request: TestServerRequest) -> None:
    request.setHeader("Content-Type", "application/octet-stream")
    request.setHeader("Content-Disposition", "attachment")
    request.write(b"Hello world")
    request.finish()


def read_trace(path: Path) -> Dict[str, bytes]:
    """Port of the resources of parseTraceRaw() in tests/config/utils.ts."""
    with zipfile.ZipFile(path) as zip_file:
        return {name: zip_file.read(name) for name in zip_file.namelist()}


def trace_actions(resources: Dict[str, bytes]) -> List[str]:
    """The actions of parseTraceRaw(), as "Class.method".

    Upstream renders the titles from the protocol metainfo, which the Python client
    does not have: "Set content" is the title of Frame.setContent.
    """
    actions: List[Any] = []
    for name, content in resources.items():
        if not name.endswith(".trace"):
            continue
        for line in content.decode().splitlines():
            if line:
                event = json.loads(line)
                if event["type"] == "before":
                    actions.append(event)
    actions.sort(key=lambda action: action["startTime"])
    return [f"{action['class']}.{action['method']}" for action in actions]


@pytest.mark.parametrize("kind", KINDS)
def test_BT_034_should_connect_over_wss(
    kind: str,
    browser_name: str,
    launch_arguments: Dict,
    start_remote_server: RemoteServerStarter,
    https_server: Server,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    remote_server = start_remote_server(kind)

    # https://stackoverflow.com/a/21961005/552185
    monkeypatch.setenv("NODE_TLS_REJECT_UNAUTHORIZED", "0")
    # suppressCertificateWarning()
    monkeypatch.setenv("NODE_NO_WARNINGS", "1")

    https_server.once_web_socket_connection(
        lambda ws: forward_web_socket(ws, remote_server.ws_endpoint)
    )

    def body(playwright: Playwright) -> None:
        browser = connect_browser(
            playwright[browser_name],
            launch_arguments,
            f"wss://localhost:{https_server.PORT}/ws",
        )
        assert browser.version
        browser.close()

    # The driver reads NODE_TLS_REJECT_UNAUTHORIZED when it starts.
    run_with_new_playwright(body)


@pytest.mark.parametrize("kind", KINDS)
def test_BT_035_should_print_http_error(
    kind: str, connect: Callable[..., Browser], server: Server
) -> None:
    # Port of the /ws-401 upgrade handler of the upstream test server.
    def handle_ws_401(request: TestServerRequest) -> None:
        request.setResponseCode(401)
        request.setHeader("Content-Length", str(len(b"Unauthorized body")))
        request.write(b"Unauthorized body")
        request.finish()

    server.set_route("/ws-401", handle_ws_401)
    with pytest.raises(Error) as exc_info:
        connect(f"ws://localhost:{server.PORT}/ws-401")
    assert "401" in exc_info.value.message
    assert "Unauthorized body" in exc_info.value.message


@pytest.mark.parametrize("kind", KINDS)
def test_BT_036_should_print_ws_error(
    kind: str, connect: Callable[..., Browser], server: Server
) -> None:
    with pytest.raises(Error) as exc_info:
        connect("ws://does-not-exist.problem-domain:10987?secret=MYSECRET")
    assert (
        "<ws connecting> ws://does-not-exist.problem-domain:10987/"
        in exc_info.value.message
    )
    assert "<ws error>" in exc_info.value.message
    assert "getaddrinfo" in exc_info.value.message
    assert "secret=MYSECRET" not in exc_info.value.message


@pytest.mark.parametrize("kind", KINDS)
def test_BT_037_should_print_custom_ws_close_error(
    kind: str, connect: Callable[..., Browser], server: Server
) -> None:
    def handle_ws(ws: WebSocketProtocol) -> None:
        ws.events.on(
            "message",
            lambda payload, is_binary: ws.sendClose(code=4123, reason="Oh my!"),
        )

    server.once_web_socket_connection(handle_ws)
    with pytest.raises(Error) as exc_info:
        connect(f"ws://localhost:{server.PORT}/ws")
    assert "BrowserType.connect: Oh my!" in exc_info.value.message


@pytest.mark.parametrize("kind", KINDS)
def test_BT_038_should_be_able_to_reconnect_to_a_browser(
    kind: str,
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
    server: Server,
) -> None:
    remote_server = start_remote_server(kind)
    browser = connect(remote_server.ws_endpoint)
    browser_context = browser.new_context()
    assert len(browser_context.pages) == 0
    page = browser_context.new_page()
    assert page.evaluate("11 * 11") == 121
    page.goto(server.EMPTY_PAGE)
    browser.close()

    browser = connect(remote_server.ws_endpoint)
    browser_context = browser.new_context()
    page = browser_context.new_page()
    page.goto(server.EMPTY_PAGE)
    browser.close()


@pytest.mark.parametrize("kind", KINDS)
def test_BT_039_should_not_crash_on_malformed_json_frame(
    kind: str,
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
) -> None:
    remote_server = start_remote_server(kind)
    ws = WebSocketClient(remote_server.ws_endpoint)
    assert ws.opened.wait(30), f"{remote_server.ws_endpoint}: {ws.close_reason}"
    ws.send("]")
    assert ws.closed.wait(30)
    # Server should still be alive and accept new connections.
    browser = connect(remote_server.ws_endpoint)
    page = browser.new_page()
    assert page.evaluate("1 + 2") == 3
    browser.close()


@pytest.mark.parametrize("kind", KINDS)
def test_BT_040_should_be_able_to_visit_ipv6(
    kind: str,
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
    ipv6_server_port: int,
    browser_channel: Optional[str],
    request: pytest.FixtureRequest,
) -> None:
    if os.environ.get("INSIDE_DOCKER"):
        request.applymarker(
            pytest.mark.xfail(
                reason="docker does not support IPv6 by default", strict=True
            )
        )
    if browser_channel == "webkit-wsl":
        request.applymarker(
            pytest.mark.xfail(
                reason="WebKit on WSL does not support IPv6: https://github.com/microsoft/WSL/issues/10803",
                strict=True,
            )
        )
    remote_server = start_remote_server(kind)
    browser = connect(remote_server.ws_endpoint)
    page = browser.new_page()
    ipv6_url = "http://[::1]:" + str(ipv6_server_port)
    page.goto(ipv6_url)
    assert "from-ipv6-server" in page.content()
    browser.close()


@pytest.mark.parametrize("kind", KINDS)
def test_BT_041_should_ignore_page_pause_when_headed(
    kind: str,
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
    browser_channel: Optional[str],
) -> None:
    if browser_channel == "chromium-headless-shell":
        pytest.skip("shell is never headed")

    remote_server = start_remote_server(kind, launch_options={"headless": False})
    browser = connect(remote_server.ws_endpoint, launch_options={"headless": False})
    browser_context = browser.new_context()
    page = browser_context.new_page()
    page.pause()
    browser.close()


@pytest.mark.parametrize("kind", KINDS)
def test_BT_042_should_be_able_to_visit_ipv6_through_localhost(
    kind: str,
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
    ipv6_server_port: int,
    browser_channel: Optional[str],
    request: pytest.FixtureRequest,
) -> None:
    if os.environ.get("INSIDE_DOCKER"):
        request.applymarker(
            pytest.mark.xfail(
                reason="docker does not support IPv6 by default", strict=True
            )
        )
    if browser_channel == "webkit-wsl":
        pytest.skip(
            "WebKit on WSL does not support IPv6: https://github.com/microsoft/WSL/issues/10803"
        )
    remote_server = start_remote_server(kind)
    browser = connect(remote_server.ws_endpoint)
    page = browser.new_page()
    ipv6_url = "http://localhost:" + str(ipv6_server_port)
    page.goto(ipv6_url)
    assert "from-ipv6-server" in page.content()
    browser.close()


@pytest.mark.parametrize("kind", KINDS)
def test_BT_043_should_be_able_to_connect_two_browsers_at_the_same_time(
    kind: str,
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
) -> None:
    remote_server = start_remote_server(kind)

    browser1 = connect(remote_server.ws_endpoint)
    assert len(browser1.contexts) == 0
    browser1.new_context()
    assert len(browser1.contexts) == 1

    browser2 = connect(remote_server.ws_endpoint)
    assert len(browser2.contexts) == 0
    browser2.new_context()
    assert len(browser2.contexts) == 1
    assert len(browser1.contexts) == 1

    browser1.close()
    assert len(browser2.contexts) == 1
    page2 = browser2.new_page()
    # original browser should still work
    assert page2.evaluate("() => 7 * 6") == 42

    browser2.close()


@pytest.mark.parametrize("kind", KINDS)
def test_BT_044_should_timeout_in_socket_while_connecting(
    kind: str, connect: Callable[..., Browser], server: Server
) -> None:
    # Port of the /ws-slow upgrade handler of the upstream test server.
    def handle_ws_slow(request: TestServerRequest) -> None:
        def upgrade() -> None:
            with suppress(Exception):
                getattr(server, "_ws_resource").render(request)

        reactor.callLater(2, upgrade)

    server.set_route("/ws-slow", handle_ws_slow)
    with pytest.raises(Error) as exc_info:
        connect(f"ws://localhost:{server.PORT}/ws-slow", timeout=1000)
    assert "BrowserType.connect: Timeout 1000ms exceeded" in exc_info.value.message


@pytest.mark.parametrize("kind", KINDS)
def test_BT_045_should_timeout_in_connect_while_connecting(
    kind: str,
    connect: Callable[..., Browser],
    server: Server,
    server_web_sockets: List[WebSocketProtocol],
) -> None:
    server.once_web_socket_connection(server_web_sockets.append)
    with pytest.raises(Error) as exc_info:
        connect(f"ws://localhost:{server.PORT}/ws", timeout=100)
    assert "BrowserType.connect: Timeout 100ms exceeded" in exc_info.value.message


@pytest.mark.parametrize("kind", KINDS)
def test_BT_046_should_send_extra_headers_with_connect_request(
    kind: str,
    playwright: Playwright,
    connect: Callable[..., Browser],
    server: Server,
) -> None:
    request_future = server.wait_for_web_socket_connection_request()
    with suppress(Error):
        connect(
            f"ws://localhost:{server.PORT}/ws",
            headers={
                "User-Agent": "Playwright",
                "foo": "bar",
            },
            timeout=100,
        )
    wait_for_future(playwright._loop, playwright._dispatcher_fiber, request_future)
    request = request_future.result()
    assert request.headers["user-agent"] == "Playwright"
    assert request.headers["foo"] == "bar"


@pytest.mark.parametrize("kind", KINDS)
def test_BT_047_should_send_extra_headers_with_connect_request_in_object_form(
    kind: str,
    playwright: Playwright,
    browser_type: BrowserType,
    server: Server,
    server_web_sockets: List[WebSocketProtocol],
    sync_gather: Callable,
) -> None:
    server.once_web_socket_connection(server_web_sockets.append)

    def connect() -> None:
        # Python's counterpart of the object form: every argument by name.
        with suppress(Error):
            browser_type.connect(
                endpoint=f"ws://localhost:{server.PORT}/ws",
                headers={
                    "User-Agent": "Playwright",
                    "foo": "bar",
                },
                timeout=3000,
            )

    def check_request() -> None:
        poll(playwright, lambda: len(server_web_sockets) > 0)
        request = server_web_sockets[0].http_headers
        assert request["user-agent"] == "Playwright"
        assert request["foo"] == "bar"

    sync_gather(connect, check_request)


@pytest.mark.parametrize("kind", KINDS)
def test_BT_048_should_send_default_user_agent_and_x_playwright_browser_headers_with_connect_request(
    kind: str,
    playwright: Playwright,
    connect: Callable[..., Browser],
    browser_name: str,
    server: Server,
    is_frozen_webkit: bool,
    server_web_sockets: List[WebSocketProtocol],
) -> None:
    if is_frozen_webkit:
        pytest.skip()

    # Port of getUserAgent(): the driver sends the same User-Agent with global fetch.
    request_context = playwright.request.new_context()
    with server.expect_request("/empty.html") as user_agent_request:
        request_context.get(server.EMPTY_PAGE)
    request_context.dispose()
    user_agent = user_agent_request.value.getHeader("user-agent")

    server.once_web_socket_connection(server_web_sockets.append)
    with suppress(Error):
        connect(
            f"ws://localhost:{server.PORT}/ws",
            headers={
                "foo": "bar",
            },
            timeout=100,
        )
    request = server_web_sockets[0].http_headers
    assert request["user-agent"] == user_agent
    assert request["x-playwright-browser"] == browser_name
    assert request["foo"] == "bar"


@pytest.mark.parametrize("kind", KINDS)
def test_BT_049_should_support_slowmo_option(
    kind: str,
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
) -> None:
    remote_server = start_remote_server(kind)

    browser1 = connect(remote_server.ws_endpoint, slow_mo=200)
    start = time.monotonic()
    browser1.new_context()
    browser1.close()
    assert (time.monotonic() - start) * 1000 > 199


@pytest.mark.parametrize("kind", KINDS)
def test_BT_050_disconnected_event_should_be_emitted_when_browser_is_closed_or_server_is_closed(
    kind: str,
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
) -> None:
    remote_server = start_remote_server(kind)

    browser1 = connect(remote_server.ws_endpoint)
    browser1.new_page()

    browser2 = connect(remote_server.ws_endpoint)
    browser2.new_page()

    disconnected1: List[bool] = []
    disconnected2: List[bool] = []
    browser1.on("disconnected", lambda _: disconnected1.append(True))
    browser2.on("disconnected", lambda _: disconnected2.append(True))

    with expect_disconnected(browser1):
        browser1.close()
    assert len(disconnected1) == 1
    assert len(disconnected2) == 0

    with expect_disconnected(browser2):
        remote_server.close()
    assert len(disconnected1) == 1
    assert len(disconnected2) == 1


@pytest.mark.parametrize("kind", KINDS)
def test_BT_051_disconnected_event_should_have_browser_as_argument(
    kind: str,
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
) -> None:
    remote_server = start_remote_server(kind)
    browser = connect(remote_server.ws_endpoint)
    with expect_disconnected(browser) as event_info:
        browser.close()
    disconnected = event_info.value
    assert disconnected is browser


@pytest.mark.parametrize("kind", KINDS)
def test_BT_053_should_set_the_browser_connected_state(
    kind: str,
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
) -> None:
    remote_server = start_remote_server(kind)
    remote = connect(remote_server.ws_endpoint)
    assert remote.is_connected() is True
    remote.close()
    assert remote.is_connected() is False


@pytest.mark.parametrize("kind", KINDS)
def test_BT_054_should_throw_when_used_after_is_connected_returns_false(
    kind: str,
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
) -> None:
    remote_server = start_remote_server(kind)
    browser = connect(remote_server.ws_endpoint)
    page = browser.new_page()
    with expect_disconnected(browser):
        remote_server.close()
    assert browser.is_connected() is False
    with pytest.raises(Error) as exc_info:
        page.evaluate("1 + 1")
    assert "closed" in exc_info.value.message


@pytest.mark.parametrize("kind", KINDS)
def test_BT_055_should_throw_when_calling_wait_for_navigation_after_disconnect(
    kind: str,
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
) -> None:
    remote_server = start_remote_server(kind)
    browser = connect(remote_server.ws_endpoint)
    page = browser.new_page()
    with expect_disconnected(browser):
        remote_server.close()
    assert browser.is_connected() is False
    with pytest.raises(Error) as exc_info:
        with page.expect_navigation():
            pass
    assert TARGET_CLOSED_ERROR_MESSAGE in exc_info.value.message


@pytest.mark.parametrize("kind", KINDS)
def test_BT_056_should_reject_navigation_when_browser_closes(
    kind: str,
    playwright: Playwright,
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
    server: Server,
    sync_gather: Callable,
) -> None:
    remote_server = start_remote_server(kind)
    # The handler never answers, as upstream's; it records the request for waitForRequest.
    requested: List[bool] = []
    server.set_route("/one-style.css", lambda request: requested.append(True))
    browser = connect(remote_server.ws_endpoint)
    page = browser.new_page()

    def navigate() -> Error:
        with pytest.raises(Error) as exc_info:
            page.goto(server.PREFIX + "/one-style.html", timeout=60000)
        return exc_info.value

    def close() -> None:
        poll(playwright, lambda: len(requested) > 0, timeout=30000)
        browser.close()

    error, _ = sync_gather(navigate, close)
    assert "has been closed" in error.message


@pytest.mark.parametrize("kind", KINDS)
def test_BT_057_should_reject_wait_for_selector_when_browser_closes(
    kind: str,
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
    server: Server,
    sync_gather: Callable,
) -> None:
    remote_server = start_remote_server(kind)
    server.set_route("/empty.html", lambda request: None)
    browser = connect(remote_server.ws_endpoint)
    page = browser.new_page()

    def wait_for_selector() -> Error:
        with pytest.raises(Error) as exc_info:
            page.wait_for_selector("div", state="attached", timeout=60000)
        return exc_info.value

    def close() -> None:
        # Make sure the previous wait_for_selector has time to make it to the browser before we disconnect.
        page.wait_for_selector("body", state="attached")

        browser.close()

    error, _ = sync_gather(wait_for_selector, close)
    assert "has been closed" in error.message


@pytest.mark.parametrize("kind", KINDS)
def test_BT_058_should_emit_close_events_on_pages_and_contexts(
    kind: str,
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
) -> None:
    remote_server = start_remote_server(kind)
    browser = connect(remote_server.ws_endpoint)
    context = browser.new_context()
    page = context.new_page()
    page_closed: List[bool] = []
    page.on("close", lambda _: page_closed.append(True))
    with context.expect_event("close"):
        remote_server.close()
    assert page_closed


@pytest.mark.parametrize("kind", KINDS)
def test_BT_059_should_terminate_network_waiters(
    kind: str,
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
    server: Server,
    sync_gather: Callable,
) -> None:
    remote_server = start_remote_server(kind)
    browser = connect(remote_server.ws_endpoint)
    new_page = browser.new_page()

    def wait_for_request() -> Error:
        with pytest.raises(Error) as exc_info:
            with new_page.expect_request(server.EMPTY_PAGE):
                pass
        return exc_info.value

    def wait_for_response() -> Error:
        with pytest.raises(Error) as exc_info:
            with new_page.expect_response(server.EMPTY_PAGE):
                pass
        return exc_info.value

    def close() -> None:
        remote_server.close()

    results = sync_gather(
        wait_for_request,
        wait_for_response,
        close,
    )
    for i in range(2):
        error = results[i]
        assert error
        message = error.message
        assert TARGET_CLOSED_ERROR_MESSAGE in message
        assert "Timeout" not in message


@pytest.mark.parametrize("kind", KINDS)
def test_BT_060_should_reject_wait_for_event_before_browser_close_finishes(
    kind: str,
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
    server: Server,
    sync_gather: Callable,
) -> None:
    remote_server = start_remote_server(kind)
    browser = connect(remote_server.ws_endpoint)
    new_page = browser.new_page()
    rejected: List[bool] = []

    def wait_for_download() -> None:
        with pytest.raises(Error):
            new_page.wait_for_event("download")
        rejected.append(True)

    def close() -> None:
        browser.close()
        assert rejected == [True]

    sync_gather(wait_for_download, close)


@pytest.mark.parametrize("kind", KINDS)
def test_BT_061_should_reject_wait_for_event_before_browser_on_disconnect_fires(
    kind: str,
    playwright: Playwright,
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
    server: Server,
    sync_gather: Callable,
) -> None:
    remote_server = start_remote_server(kind)
    browser = connect(remote_server.ws_endpoint)
    new_page = browser.new_page()
    log: List[str] = []

    def wait_for_download() -> None:
        with pytest.raises(Error):
            new_page.wait_for_event("download")
        log.append("rejected")

    def close() -> None:
        browser.on("disconnected", lambda _: log.append("disconnected"))
        remote_server.close()

    sync_gather(wait_for_download, close)
    poll(playwright, lambda: log == ["rejected", "disconnected"])


@pytest.mark.parametrize("kind", KINDS)
def test_BT_062_should_respect_selectors(
    kind: str,
    playwright: Playwright,
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
    utils: Utils,
) -> None:
    remote_server = start_remote_server(kind)

    mycss1 = "mycss1-" + kind
    mycss2 = "mycss2-" + kind
    mycss3 = "mycss3-" + kind

    mycss = """({
        query(root, selector) {
            return root.querySelector(selector);
        },
        queryAll(root, selector) {
            return Array.from(root.querySelectorAll(selector));
        }
    })"""
    # Register one engine before connecting.
    # The registration outlives the test: utils tolerates the earlier run of another browser.
    utils.register_selector_engine(playwright.selectors, mycss1, mycss)

    browser1 = connect(remote_server.ws_endpoint)
    context1 = browser1.new_context()

    # Register another engine after creating context.
    utils.register_selector_engine(playwright.selectors, mycss2, mycss)

    page1 = context1.new_page()
    page1.set_content("<div>hello</div>")
    assert page1.inner_html("css=div") == "hello"
    assert page1.inner_html(f"{mycss1}=div") == "hello"
    assert page1.inner_html(f"{mycss2}=div") == "hello"

    browser2 = connect(remote_server.ws_endpoint)

    # Register third engine after second connect.
    utils.register_selector_engine(playwright.selectors, mycss3, mycss)

    page2 = browser2.new_page()
    page2.set_content("<div>hello</div>")
    assert page2.inner_html("css=div") == "hello"
    assert page2.inner_html(f"{mycss1}=div") == "hello"
    assert page2.inner_html(f"{mycss2}=div") == "hello"
    assert page2.inner_html(f"{mycss3}=div") == "hello"

    browser1.close()


@pytest.mark.parametrize("kind", KINDS)
def test_BT_063_should_not_throw_on_close_after_disconnect(
    kind: str,
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
) -> None:
    remote_server = start_remote_server(kind)
    browser = connect(remote_server.ws_endpoint)
    browser.new_page()
    with expect_disconnected(browser):
        remote_server.close()
    browser.close()


@pytest.mark.parametrize("kind", KINDS)
def test_BT_064_should_save_as_videos_from_remote_browser(
    kind: str,
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
    tmp_path: Path,
    utils: Utils,
) -> None:
    remote_server = start_remote_server(kind)
    browser = connect(remote_server.ws_endpoint)
    videos_path = tmp_path
    context = browser.new_context(
        record_video_dir=videos_path,
        record_video_size={"width": 320, "height": 240},
    )
    page = context.new_page()
    page.evaluate("() => document.body.style.backgroundColor = 'red'")
    ensure_some_frames(page, utils)
    context.close()

    # recordVideo.dir might be unaccessible in server mode, so /tmp/artifacts should be used.
    assert os.listdir(videos_path) == []

    saved_as_path = tmp_path / "my-video.webm"
    assert page.video
    page.video.save_as(saved_as_path)
    assert saved_as_path.exists()


@pytest.mark.parametrize("kind", KINDS)
def test_BT_065_should_save_videos_to_artifacts_dir(
    kind: str,
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
    tmp_path: Path,
    utils: Utils,
) -> None:
    artifacts_dir = tmp_path / "artifacts"
    remote_server = start_remote_server(kind, artifacts_dir=artifacts_dir)
    browser = connect(remote_server.ws_endpoint)
    local_dir = tmp_path / "random-dir"
    context = browser.new_context(
        record_video_dir=local_dir,
        record_video_size={"width": 320, "height": 240},
    )
    page = context.new_page()
    page.evaluate("() => document.body.style.backgroundColor = 'red'")
    ensure_some_frames(page, utils)
    context.close()

    saved_as_path = tmp_path / "my-video.webm"
    assert page.video
    page.video.save_as(saved_as_path)
    assert saved_as_path.exists()
    assert not local_dir.exists()

    browser.close()


@pytest.mark.parametrize("kind", KINDS)
def test_BT_066_should_name_video_file_after_page_guid_when_connecting_to_remote_browser_with_artifacts_dir(
    kind: str,
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
    tmp_path: Path,
    utils: Utils,
) -> None:
    artifacts_dir = tmp_path / "artifacts"
    remote_server = start_remote_server(kind, artifacts_dir=artifacts_dir)
    browser = connect(remote_server.ws_endpoint)
    # Upstream passes recordVideo without a dir. Python records only with
    # record_video_dir; a remote browser puts the video into its artifactsDir anyway.
    context = browser.new_context(
        record_video_dir=tmp_path / "random-dir",
        record_video_size={"width": 320, "height": 240},
    )
    page = context.new_page()
    page.evaluate("() => document.body.style.backgroundColor = 'red'")
    ensure_some_frames(page, utils)
    context.close()

    guid = getattr(page, "_impl_obj")._guid
    assert (artifacts_dir / (guid + ".webm")).exists()

    browser.close()


@pytest.mark.parametrize("kind", KINDS)
def test_BT_067_should_be_able_to_connect_20_times_to_a_single_server_without_warnings(
    kind: str,
    browser_name: str,
    launch_arguments: Dict,
    start_remote_server: RemoteServerStarter,
    platform: str,
    capfd: pytest.CaptureFixture[str],
) -> None:
    if platform != "linux":
        pytest.skip("Testing non-platform specific code")

    remote_server = start_remote_server(kind)

    def body(playwright: Playwright) -> None:
        browsers: List[Browser] = []
        for i in range(20):
            browsers.append(
                connect_browser(
                    playwright[browser_name],
                    launch_arguments,
                    remote_server.ws_endpoint,
                )
            )
        for browser in browsers:
            browser.close()

    # Upstream listens to process 'warning' events. Here the client's Node.js code runs
    # in the driver, which prints warnings to stderr: the test starts its own driver,
    # so that capfd captures its stderr.
    capfd.readouterr()
    run_with_new_playwright(body)
    warning = capfd.readouterr().err
    assert "Warning" not in warning


@pytest.mark.parametrize("kind", KINDS)
def test_BT_068_should_save_download(
    kind: str,
    server: Server,
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
    tmp_path: Path,
) -> None:
    server.set_route("/download", download_route)

    remote_server = start_remote_server(kind)
    browser = connect(remote_server.ws_endpoint)
    page = browser.new_page()
    page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    with page.expect_download() as download_info:
        page.click("a")
    download = download_info.value
    nested_path = tmp_path / "these" / "are" / "directories" / "download.txt"
    download.save_as(nested_path)
    assert nested_path.exists()
    assert nested_path.read_text() == "Hello world"
    with pytest.raises(Error) as exc_info:
        download.path()
    assert (
        "Path is not available when connecting remotely. Use save_as() to save a local copy."
        in exc_info.value.message
    )
    browser.close()


@pytest.mark.parametrize("kind", KINDS)
def test_BT_069_should_error_when_saving_download_after_deletion(
    kind: str,
    server: Server,
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
    tmp_path: Path,
) -> None:
    server.set_route("/download", download_route)

    remote_server = start_remote_server(kind)
    browser = connect(remote_server.ws_endpoint)
    page = browser.new_page()
    page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    with page.expect_download() as download_info:
        page.click("a")
    download = download_info.value
    user_path = tmp_path / "download.txt"
    download.delete()
    with pytest.raises(Error) as exc_info:
        download.save_as(user_path)
    assert "Target page, context or browser has been closed" in exc_info.value.message
    browser.close()


@pytest.mark.parametrize("kind", KINDS)
def test_BT_070_should_properly_disconnect_when_connection_closes_from_the_client_side(
    kind: str,
    playwright: Playwright,
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
    server: Server,
    sync_gather: Callable,
) -> None:
    server.set_route("/one-style.css", lambda request: None)
    remote_server = start_remote_server(kind)
    browser = connect(remote_server.ws_endpoint)
    page = browser.new_page()

    def navigate() -> Error:
        with pytest.raises(Error) as exc_info:
            page.goto(server.PREFIX + "/one-style.html", timeout=60000)
        return exc_info.value

    def wait_for_navigation() -> Error:
        with pytest.raises(Error) as exc_info:
            with page.expect_navigation():
                pass
        return exc_info.value

    def close() -> None:
        # This closes the websocket: Browser.close() of a connected browser closes the
        # connection on the client side, as upstream's browser._connection.close().
        with expect_disconnected(browser):
            browser.close()
        assert browser.is_connected() is False

    navigation_error, wait_for_navigation_error, _ = sync_gather(
        navigate, wait_for_navigation, close
    )

    assert TARGET_CLOSED_ERROR_MESSAGE in navigation_error.message
    assert TARGET_CLOSED_ERROR_MESSAGE in wait_for_navigation_error.message
    with pytest.raises(Error) as exc_info:
        page.goto(server.EMPTY_PAGE)
    assert "has been closed" in exc_info.value.message
    assert TARGET_CLOSED_ERROR_MESSAGE in wait_for_navigation().message


@pytest.mark.parametrize("kind", KINDS)
def test_BT_071_should_be_able_to_connect_when_the_ws_endpoint_is_passed_as_an_option(
    kind: str,
    browser_type: BrowserType,
    launch_arguments: Dict,
    start_remote_server: RemoteServerStarter,
) -> None:
    remote_server = start_remote_server(kind)
    browser = browser_type.connect(
        endpoint=remote_server.ws_endpoint,
        headers={
            "x-playwright-launch-options": json.dumps(launch_arguments),
        },
    )
    page = browser.new_page()
    assert page.evaluate("1 + 2") == 3
    browser.close()


@pytest.mark.parametrize("kind", KINDS)
def test_BT_072_should_save_har(
    kind: str,
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
    server: Server,
    tmp_path: Path,
) -> None:
    remote_server = start_remote_server(kind)
    browser = connect(remote_server.ws_endpoint)
    har_path = tmp_path / "test.har"
    context = browser.new_context(record_har_path=har_path)
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)
    context.close()
    browser.close()

    log = json.loads(har_path.read_text())["log"]
    assert len(log["entries"]) == 1
    entry = log["entries"][0]
    assert entry["pageref"] == log["pages"][0]["id"]
    assert entry["request"]["url"] == server.EMPTY_PAGE


@pytest.mark.parametrize("kind", KINDS)
def test_BT_073_should_filter_launch_options(
    kind: str,
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
    server: Server,
    tmp_path: Path,
) -> None:
    # Upstream also sets the internal _playwright._defaultTracesDir to traces_dir;
    # the Python client has no such default.
    traces_dir = tmp_path / "traces"
    remote_server = start_remote_server(kind)
    browser = connect(remote_server.ws_endpoint)
    page = browser.new_page()
    page.goto(server.EMPTY_PAGE)
    browser.close()
    assert traces_dir.exists() is False


@pytest.mark.parametrize("kind", KINDS)
def test_BT_074_should_record_trace_with_sources(
    kind: str,
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
    server: Server,
    tmp_path: Path,
) -> None:
    remote_server = start_remote_server(kind)
    browser = connect(remote_server.ws_endpoint)
    context = browser.new_context()
    page = context.new_page()

    context.tracing.start(sources=True)
    page.goto(server.EMPTY_PAGE)
    page.set_content("<button>Click</button>")
    page.click('"Click"')
    context.tracing.stop(path=tmp_path / "trace1.zip")

    context.close()
    browser.close()

    resources = read_trace(tmp_path / "trace1.zip")
    source_names = [name for name in resources if name.startswith("src/")]
    assert len(source_names) == 1
    source_file = resources[source_names[0]]
    this_file = Path(__file__).read_bytes()
    assert source_file == this_file


@pytest.mark.parametrize("kind", KINDS)
def test_BT_075_should_fulfill_with_global_fetch_result(
    kind: str,
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
    playwright: Playwright,
    server: Server,
) -> None:
    remote_server = start_remote_server(kind)
    browser = connect(remote_server.ws_endpoint)
    context = browser.new_context()
    page = context.new_page()

    def handle(route: Route) -> None:
        request = playwright.request.new_context()
        response = request.get(server.PREFIX + "/simple.json")
        route.fulfill(response=response)

    page.route("**/*", handle)
    response = page.goto(server.EMPTY_PAGE)
    assert response
    assert response.status == 200
    assert response.json() == {"foo": "bar"}


@pytest.mark.slow
@pytest.mark.parametrize("kind", KINDS)
def test_BT_076_should_upload_large_file(
    kind: str,
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
    server: Server,
    tmp_path: Path,
) -> None:
    remote_server = start_remote_server(kind)
    browser = connect(remote_server.ws_endpoint)
    context = browser.new_context()
    page = context.new_page()

    page.goto(server.PREFIX + "/input/fileupload.html")
    upload_file = tmp_path / "200MB.zip"
    data = b"A" * (4 * 1024)
    with upload_file.open("wb") as stream:
        for i in range(50 * 1024):
            stream.write(data)
    input = page.locator('input[type="file"]')
    events = input.evaluate_handle(
        """e => {
        const events = [];
        e.addEventListener('input', () => events.push('input'));
        e.addEventListener('change', () => events.push('change'));
        return events;
    }"""
    )
    input.set_input_files(upload_file)
    assert input.evaluate("e => e.files[0].name") == "200MB.zip"
    assert events.evaluate("e => e") == ["input", "change"]

    def handle_upload(request: TestServerRequest) -> None:
        request.finish()

    server.set_route("/upload", handle_upload)
    with server.expect_request("/upload") as request_info:
        page.click("input[type=submit]")
    file1 = request_info.value
    assert file1.post_body
    match = re.search(
        rb'^Content-Disposition: form-data; name="file1"; filename="(?P<filename>[^"]*)"',
        file1.post_body,
        re.MULTILINE,
    )
    assert match
    assert match.group("filename") == b"200MB.zip"
    assert len(file1.args[b"file1"][0]) == 200 * 1024 * 1024
    upload_file.unlink()


@pytest.mark.slow
@pytest.mark.parametrize("kind", KINDS)
def test_BT_077_should_upload_a_folder(
    kind: str,
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
    server: Server,
    tmp_path: Path,
) -> None:
    remote_server = start_remote_server(kind)
    browser = connect(remote_server.ws_endpoint)
    context = browser.new_context()
    page = context.new_page()

    page.goto(server.PREFIX + "/input/folderupload.html")
    input = page.query_selector("input")
    assert input
    folder_name = "folder-upload-test"
    dir = tmp_path / folder_name
    dir.mkdir(parents=True)
    (dir / "file1.txt").write_text("file1 content")
    (dir / "file2").write_text("file2 content")
    (dir / "sub-dir").mkdir()
    (dir / "sub-dir" / "really.txt").write_text("sub-dir file content")
    input.set_input_files(dir)

    webkit_relative_paths = page.evaluate(
        "e => [...e.files].map(f => f.webkitRelativePath)", input
    )
    assert set(webkit_relative_paths) == {
        f"{folder_name}/file1.txt",
        f"{folder_name}/file2",
        f"{folder_name}/sub-dir/really.txt",
    }

    for i, webkit_relative_path in enumerate(webkit_relative_paths):
        content = input.evaluate(
            """(e, i) => {
            const reader = new FileReader();
            const promise = new Promise(fulfill => reader.onload = fulfill);
            reader.readAsText(e.files[i]);
            return promise.then(() => reader.result);
        }""",
            i,
        )
        assert content == (dir / ".." / webkit_relative_path).read_text()


@pytest.mark.parametrize("kind", KINDS)
def test_BT_078_set_input_files_should_preserve_last_modified_timestamp(
    kind: str,
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
    assetdir: Path,
) -> None:
    remote_server = start_remote_server(kind)
    browser = connect(remote_server.ws_endpoint)
    context = browser.new_context()
    page = context.new_page()

    page.set_content("<input type=file multiple=true/>")
    input = page.locator("input")
    files = ["file-to-upload.txt", "file-to-upload-2.txt"]
    input.set_input_files([assetdir / file for file in files])
    assert input.evaluate("e => [...e.files].map(f => f.name)") == files
    timestamps = input.evaluate("e => [...e.files].map(f => f.lastModified)")
    expected_timestamps = [
        round(os.stat(assetdir / file).st_mtime * 1000) for file in files
    ]
    # On Linux browser sometimes reduces the timestamp by 1ms: 1696272058110.0715  -> 1696272058109 or even
    # rounds it to seconds in WebKit: 1696272058110 -> 1696272058000.
    for i in range(len(timestamps)):
        assert (
            abs(timestamps[i] - expected_timestamps[i]) <= 1000
        ), f"expected: {expected_timestamps}; actual: {timestamps}"


@pytest.mark.parametrize("kind", KINDS)
def test_BT_079_should_connect_over_http(
    kind: str,
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
) -> None:
    remote_server = start_remote_server(kind)

    url = urlparse(remote_server.ws_endpoint)
    browser = connect(f"http://localhost:{url.port}")
    assert browser.version
    browser.close()


def skip_socks_proxy(kind: str) -> None:
    """Port of the test.skip() of the 'socks proxy' describe."""
    if kind == KIND_LAUNCH_SERVER:
        pytest.skip("not supported yet")


def foo_route(
    body: str, reached_original_target: List[bool]
) -> Callable[[TestServerRequest], None]:
    def handler(request: TestServerRequest) -> None:
        reached_original_target.append(True)
        request.write(body.encode())
        request.finish()

    return handler


@pytest.mark.parametrize("kind", KINDS)
def test_BT_080_socks_proxy_should_forward_non_forwarded_requests(
    kind: str,
    server: Server,
    start_remote_server: RemoteServerStarter,
    connect: Callable[..., Browser],
) -> None:
    skip_socks_proxy(kind)
    reached_original_target: List[bool] = []
    server.set_route(
        "/foo.html",
        foo_route("<html><body>original-target</body></html>", reached_original_target),
    )
    remote_server = start_remote_server(kind)
    browser = connect(remote_server.ws_endpoint, expose_network="*")
    page = browser.new_page()
    page.goto(server.PREFIX + "/foo.html")
    assert "original-target" in page.content()
    assert reached_original_target == [True]


@pytest.mark.parametrize("kind", KINDS)
def test_BT_081_socks_proxy_should_proxy_localhost_requests_smoke(
    kind: str,
    start_remote_server: RemoteServerStarter,
    server: Server,
    browser_name: str,
    connect: Callable[..., Browser],
    platform: str,
    dummy_server_port: int,
    worker_index: int,
) -> None:
    skip_socks_proxy(kind)
    if browser_name == "webkit" and platform == "darwin":
        pytest.skip("no localhost proxying")

    reached_original_target: List[bool] = []
    server.set_route(
        "/foo.html", foo_route("<html><body></body></html>", reached_original_target)
    )
    example_port = 20_000 + worker_index * 3
    remote_server = start_remote_server(kind)
    browser = connect(
        remote_server.ws_endpoint,
        expose_network="*",
        redirect_port_for_test=dummy_server_port,
    )
    page = browser.new_page()

    page.set_content("empty")
    page.goto(f"http://127.0.0.1:{example_port}/foo.html")
    assert "from-dummy-server" in page.content()
    assert reached_original_target == []

    page.set_content("empty")
    page.goto(f"http://localhost:{example_port}/foo.html")
    assert "from-dummy-server" in page.content()
    assert reached_original_target == []

    with pytest.raises(Error):
        page.goto(f"http://[::1]:{example_port}/foo.html")
    assert reached_original_target == []


@pytest.mark.parametrize("kind", KINDS)
def test_BT_082_socks_proxy_should_proxy_ipv6_localhost_requests_smoke(
    kind: str,
    start_remote_server: RemoteServerStarter,
    server: Server,
    browser_name: str,
    connect: Callable[..., Browser],
    platform: str,
    ipv6_server_port: int,
    worker_index: int,
) -> None:
    skip_socks_proxy(kind)
    if browser_name == "webkit" and platform == "darwin":
        pytest.skip("no localhost proxying")

    reached_original_target: List[bool] = []
    server.set_route(
        "/foo.html", foo_route("<html><body></body></html>", reached_original_target)
    )
    example_port = 20_000 + worker_index * 3
    remote_server = start_remote_server(kind)
    browser = connect(
        remote_server.ws_endpoint,
        expose_network="*",
        redirect_port_for_test=ipv6_server_port,
    )
    page = browser.new_page()

    page.set_content("empty")
    page.goto(f"http://[::1]:{example_port}/foo.html")
    assert "from-ipv6-server" in page.content()
    assert reached_original_target == []

    page.set_content("empty")
    page.goto(f"http://localhost:{example_port}/foo.html")
    assert "from-ipv6-server" in page.content()
    assert reached_original_target == []

    with pytest.raises(Error):
        page.goto(f"http://127.0.0.1:{example_port}/foo.html")
    assert reached_original_target == []


@pytest.mark.parametrize("kind", KINDS)
def test_BT_083_socks_proxy_should_proxy_requests_from_fetch_api(
    kind: str,
    start_remote_server: RemoteServerStarter,
    server: Server,
    browser_name: str,
    connect: Callable[..., Browser],
    platform: str,
    dummy_server_port: int,
    worker_index: int,
) -> None:
    skip_socks_proxy(kind)
    if browser_name == "webkit" and platform == "darwin":
        pytest.skip("no localhost proxying")

    reached_original_target: List[bool] = []
    server.set_route(
        "/foo.html", foo_route("<html><body></body></html>", reached_original_target)
    )
    example_port = 20_000 + worker_index * 3
    remote_server = start_remote_server(kind)
    browser = connect(
        remote_server.ws_endpoint,
        expose_network="*",
        redirect_port_for_test=dummy_server_port,
    )
    page = browser.new_page()

    response = page.request.get(f"http://localhost:{example_port}/foo.html")
    assert response.status == 200
    assert "from-dummy-server" in response.text()
    assert reached_original_target == []

    response = page.request.get(f"http://127.0.0.1:{example_port}/foo.html")
    assert response.status == 200
    assert "from-dummy-server" in response.text()
    assert reached_original_target == []

    with pytest.raises(Error):
        page.request.get(f"http://[::1]:{example_port}/foo.html")
    assert reached_original_target == []


@pytest.mark.parametrize("kind", KINDS)
def test_BT_084_socks_proxy_should_proxy_requests_from_fetch_api_over_ipv6(
    kind: str,
    start_remote_server: RemoteServerStarter,
    server: Server,
    browser_name: str,
    connect: Callable[..., Browser],
    platform: str,
    ipv6_server_port: int,
    worker_index: int,
) -> None:
    skip_socks_proxy(kind)
    if browser_name == "webkit" and platform == "darwin":
        pytest.skip("no localhost proxying")

    reached_original_target: List[bool] = []
    server.set_route(
        "/foo.html", foo_route("<html><body></body></html>", reached_original_target)
    )
    example_port = 20_000 + worker_index * 3
    remote_server = start_remote_server(kind)
    browser = connect(
        remote_server.ws_endpoint,
        expose_network="*",
        redirect_port_for_test=ipv6_server_port,
    )
    page = browser.new_page()

    response = page.request.get(f"http://localhost:{example_port}/foo.html")
    assert response.status == 200
    assert "from-ipv6-server" in response.text()
    assert reached_original_target == []

    response = page.request.get(f"http://[::1]:{example_port}/foo.html")
    assert response.status == 200
    assert "from-ipv6-server" in response.text()
    assert reached_original_target == []

    with pytest.raises(Error):
        page.request.get(f"http://127.0.0.1:{example_port}/foo.html")
    assert reached_original_target == []


@pytest.mark.parametrize("kind", KINDS)
def test_BT_085_socks_proxy_should_proxy_local_playwright_requests(
    kind: str,
    connect: Callable[..., Browser],
    server: Server,
    dummy_server_port: int,
    start_remote_server: RemoteServerStarter,
    worker_index: int,
) -> None:
    skip_socks_proxy(kind)
    reached_original_target: List[bool] = []
    server.set_route(
        "/foo.html", foo_route("<html><body></body></html>", reached_original_target)
    )
    example_port = 20_000 + worker_index * 3
    remote_server = start_remote_server(kind)
    browser = connect(
        remote_server.ws_endpoint,
        expose_network="*",
        redirect_port_for_test=dummy_server_port,
    )
    page = browser.new_page()
    page.goto(f"http://local.playwright:{example_port}/foo.html")
    assert "from-dummy-server" in page.content()
    assert reached_original_target == []


@pytest.mark.parametrize("kind", KINDS)
def test_BT_086_socks_proxy_should_lead_to_the_error_page_for_forwarded_requests_when_the_connection_is_refused(
    kind: str,
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
    browser_name: str,
    worker_index: int,
) -> None:
    skip_socks_proxy(kind)
    example_port = 20_000 + worker_index * 3
    remote_server = start_remote_server(kind)
    browser = connect(remote_server.ws_endpoint, expose_network="*")
    page = browser.new_page()
    with pytest.raises(Error) as exc_info:
        page.goto(f"http://127.0.0.1:{example_port}")
    message = exc_info.value.message
    if browser_name == "chromium":
        assert "net::ERR_SOCKS_CONNECTION_FAILED at http://127.0.0.1:20" in message
    elif browser_name == "webkit":
        assert message
    elif browser_name == "firefox":
        assert (
            "NS_ERROR_NET_RESET" in message or "NS_ERROR_CONNECTION_REFUSED" in message
        )


@pytest.mark.parametrize("kind", KINDS)
def test_BT_087_socks_proxy_should_proxy_based_on_the_pattern(
    kind: str,
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
    server: Server,
    browser_name: str,
    platform: str,
    dummy_server_port: int,
    worker_index: int,
) -> None:
    skip_socks_proxy(kind)
    if browser_name == "webkit" and platform == "darwin":
        pytest.skip("no localhost proxying")

    reached_original_target: List[bool] = []
    server.set_route(
        "/foo.html",
        foo_route(
            "<html><body>from-original-server</body></html>", reached_original_target
        ),
    )
    example_port = 20_000 + worker_index * 3
    remote_server = start_remote_server(kind)
    browser = connect(
        remote_server.ws_endpoint,
        expose_network="localhost",
        redirect_port_for_test=dummy_server_port,
    )
    page = browser.new_page()

    # localhost should be proxied.
    page.goto(f"http://localhost:{example_port}/foo.html")
    assert "from-dummy-server" in page.content()
    assert reached_original_target == []

    # 127.0.0.1 should be served directly.
    page.goto(f"http://127.0.0.1:{server.PORT}/foo.html")
    assert "from-original-server" in page.content()
    assert reached_original_target == [True]

    # Random domain should be served directly and fail.
    with pytest.raises(Error):
        page.goto("http://does-not-exist-bad-domain.oh-no-should-not-work")


@pytest.mark.parametrize("kind", KINDS)
def test_BT_088_socks_proxy_should_check_proxy_pattern_on_the_client(
    kind: str,
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
    server: Server,
    dummy_server_port: int,
) -> None:
    skip_socks_proxy(kind)
    reached_original_target: List[bool] = []
    server.set_route(
        "/foo.html",
        foo_route(
            "<html><body>from-original-server</body></html>", reached_original_target
        ),
    )
    remote_server = start_remote_server(kind)
    browser = connect(
        remote_server.ws_endpoint,
        expose_network="127.0.0.1",
        headers={
            "x-playwright-proxy": "*",
        },
        redirect_port_for_test=dummy_server_port,
    )
    page = browser.new_page()

    # local.playwright should fail on the client side.
    with pytest.raises(Error):
        page.goto(f"http://local.playwright:{server.PORT}/foo.html")
    assert reached_original_target == []


def test_BT_089_launch_server_only_should_work_with_cluster(
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
) -> None:
    remote_server = start_remote_server(KIND_LAUNCH_SERVER, in_cluster=True)
    browser = connect(remote_server.ws_endpoint)
    page = browser.new_page()
    assert page.evaluate("1 + 2") == 3


def test_BT_090_launch_server_only_should_properly_disconnect_when_connection_closes_from_the_server_side(
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
    server: Server,
    platform: str,
    sync_gather: Callable,
) -> None:
    if platform == "win32":
        pytest.skip("Cannot send signals")

    server.set_route("/one-style.css", lambda request: None)
    remote_server = start_remote_server(KIND_LAUNCH_SERVER, disconnect_on_sighup=True)
    browser = connect(remote_server.ws_endpoint)
    page = browser.new_page()

    def navigate() -> Error:
        with pytest.raises(Error) as exc_info:
            page.goto(server.PREFIX + "/one-style.html", timeout=60000)
        return exc_info.value

    def wait_for_navigation() -> Error:
        with pytest.raises(Error) as exc_info:
            with page.expect_navigation():
                pass
        return exc_info.value

    def close() -> None:
        with expect_disconnected(browser):
            # This closes the websocket server.
            os.kill(remote_server.child_pid, getattr(signal, "SIGHUP"))
        assert browser.is_connected() is False

    navigation_error, wait_for_navigation_error, _ = sync_gather(
        navigate, wait_for_navigation, close
    )

    assert "has been closed" in navigation_error.message
    assert TARGET_CLOSED_ERROR_MESSAGE in wait_for_navigation_error.message
    with pytest.raises(Error) as exc_info:
        page.goto(server.EMPTY_PAGE)
    assert "has been closed" in exc_info.value.message
    assert TARGET_CLOSED_ERROR_MESSAGE in wait_for_navigation().message


@pytest.mark.slow
def test_BT_091_launch_server_only_should_be_able_to_reconnect_to_a_browser_12_times_without_warnings(
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
    server: Server,
) -> None:
    remote_server = start_remote_server(KIND_LAUNCH_SERVER, exit_on_warning=True)
    for i in range(12):
        browser = connect(remote_server.ws_endpoint)
        browser_context = browser.new_context()
        assert len(browser_context.pages) == 0
        page = browser_context.new_page()
        assert page.evaluate("11 * 11") == 121
        page.goto(server.EMPTY_PAGE)
        browser.close()


def test_BT_092_launch_server_only_cannot_launch_another_browser(
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
) -> None:
    remote_server = start_remote_server(KIND_LAUNCH_SERVER)
    browser = connect(remote_server.ws_endpoint)
    # The remote BrowserType, as upstream's browser._parent.
    remote_browser_type: BrowserType = api_mapping.from_impl(
        getattr(browser, "_impl_obj")._parent
    )
    with pytest.raises(Error) as exc_info:
        remote_browser_type.launch(timeout=0)
    assert "Launching more browsers is not allowed." in exc_info.value.message


def client_version() -> str:
    """Port of getPlaywrightVersion(true): the driver is the client of the server."""
    package_json = Path(compute_driver_executable()[1]).parent / "package.json"
    version = json.loads(package_json.read_text())["version"]
    return ".".join(version.split(".")[:2])


def test_BT_093_should_refuse_connecting_when_versions_do_not_match(
    connect: Callable[..., Browser],
) -> None:
    server = RunServer(mode="default", env={"PW_VERSION_OVERRIDE": "1.2.3"})
    with pytest.raises(Error) as exc_info:
        connect(server.ws_endpoint)
    server.close()
    assert "Playwright version mismatch" in exc_info.value.message
    assert "server version: v1.2" in exc_info.value.message
    assert "client version: v" + client_version() in exc_info.value.message


def test_BT_094_should_filter_local_paths_from_unsafe_launch_options(
    connect: Callable[..., Browser],
    start_remote_server: RemoteServerStarter,
    server: Server,
    tmp_path: Path,
) -> None:
    server.set_route("/download", download_route)
    artifacts_dir = tmp_path / "artifacts"
    downloads_path = tmp_path / "downloads"
    artifacts_dir.write_text("not a directory")
    downloads_path.write_text("not a directory")
    remote_server = start_remote_server(
        KIND_RUN_SERVER, unsafe=True, env={"PWTEST_UNDER_TEST": None}
    )
    browser = connect(
        remote_server.ws_endpoint,
        launch_options={
            "artifactsDir": str(artifacts_dir),
            "downloadsPath": str(downloads_path),
        },
    )
    context = browser.new_context()
    context.tracing.start(snapshots=True)
    page = context.new_page()
    page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    with page.expect_download() as download_info:
        page.click("a")
    download = download_info.value
    assert download.failure() is None
    trace_path = tmp_path / "trace.zip"
    context.tracing.stop(path=trace_path)
    context.close()
    browser.close()

    actions = trace_actions(read_trace(trace_path))
    assert "Frame.setContent" in actions


def test_BT_095_should_timeout_after_redirect_when_connecting_over_http(
    playwright: Playwright,
    connect: Callable[..., Browser],
    server: Server,
) -> None:
    server.set_redirect("/connect/json", "/connect/slow")
    aborted: List[bool] = []

    def handle_slow(request: TestServerRequest) -> None:
        request.notifyFinish().addErrback(lambda _: aborted.append(True))

    server.set_route("/connect/slow", handle_slow)
    with pytest.raises(Error) as exc_info:
        connect(
            f"{server.PREFIX}/connect", timeout=2000, headers={"Connection": "Close"}
        )
    assert "Timeout 2000ms exceeded." in exc_info.value.message
    poll(playwright, lambda: aborted == [True])
