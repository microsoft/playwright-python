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

"""Port of tests/page/page-goto.spec.ts."""

import contextlib
import warnings
from pathlib import Path
from typing import Any, Callable, List, Optional, Set, cast

import pytest

from playwright.sync_api import (
    Error,
    Frame,
    Page,
    Request,
    Response,
    Route,
    TimeoutError,
    expect,
)
from tests.server import Server, TestServerRequest, reactor
from tests.utils import expected_ssl_error, must


def respond_later(
    request: TestServerRequest,
    delay: float,
    body: bytes,
    content_type: str,
    on_finish: Optional[Callable[[], None]] = None,
) -> None:
    """Sends a response after a delay, like an async upstream route handler."""

    def finish() -> None:
        # Like res.end() in Node.js, do nothing when the browser has closed the
        # connection.
        if not request._disconnected:
            request.setResponseCode(200)
            request.setHeader("content-type", content_type)
            request.write(body)
            request.finish()
        if on_finish:
            on_finish()

    reactor.callLater(delay, finish)


def wait_until(page: Page, predicate: Callable[[], bool]) -> None:
    """Lets the event loop run until the predicate holds. The sync port of awaiting
    a server-side event, such as server.waitForRequest()."""
    while not predicate():
        page.wait_for_timeout(10)


def end(request: TestServerRequest, body: bytes) -> None:
    """Ends a held response from the test thread, like res.end(body)."""

    def finish() -> None:
        request.write(body)
        request.finish()

    reactor.callFromThread(finish)


def test_NA_001_should_work_smoke(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    assert page.url == server.EMPTY_PAGE


def test_NA_002_should_work_with_file_url(
    page: Page, assetdir: Path, browser_channel: Optional[str]
) -> None:
    if browser_channel == "webkit-wsl":
        pytest.skip("separate filesystem on wsl")

    fileurl = (assetdir / "empty.html").as_uri()
    page.goto(fileurl)
    assert page.url.lower() == fileurl.lower()
    assert len(page.frames) == 1


def test_NA_003_should_navigate_from_file_url_to_about_blank(
    page: Page, assetdir: Path, browser_channel: Optional[str]
) -> None:
    if browser_channel == "webkit-wsl":
        pytest.skip("separate filesystem on wsl")

    page.goto((assetdir / "empty.html").as_uri())
    page.goto("about:blank")


def test_NA_004_should_work_with_file_url_with_subframes(
    page: Page, assetdir: Path, browser_channel: Optional[str]
) -> None:
    if browser_channel == "webkit-wsl":
        pytest.skip("separate filesystem on wsl")

    fileurl = (assetdir / "frames" / "two-frames.html").as_uri()
    page.goto(fileurl)
    assert page.url.lower() == fileurl.lower()
    assert len(page.frames) == 3


def test_NA_005_should_use_http_for_no_protocol(page: Page, server: Server) -> None:
    protocol_length = len("http://")
    page.goto(server.EMPTY_PAGE[protocol_length:])
    assert page.url == server.EMPTY_PAGE


def test_NA_006_should_work_cross_process(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    assert page.url == server.EMPTY_PAGE

    url = server.CROSS_PROCESS_PREFIX + "/empty.html"
    request_frames: List[Frame] = []

    def on_request(r: Request) -> None:
        if r.url == url:
            request_frames.append(r.frame)

    page.on("request", on_request)
    response = must(page.goto(url))
    assert page.url == url
    assert response.frame == page.main_frame
    assert request_frames[-1] == page.main_frame
    assert response.url == url


def test_NA_007_should_work_with_cross_process_that_fails_before_committing(
    page: Page, server: Server
) -> None:
    server.set_route(
        "/empty.html", lambda request: must(request.transport).abortConnection()
    )
    response1 = must(page.goto(server.CROSS_PROCESS_PREFIX + "/title.html"))
    response1.finished()
    with pytest.raises(Error):
        page.goto(server.EMPTY_PAGE)


def serve_coop_page(request: TestServerRequest) -> None:
    request.setHeader("Cross-Origin-Opener-Policy", "same-origin")
    # Note: without 'onload', Firefox sometimes does not fire the load event
    # over the protocol. The reason is unclear.
    request.write(
        b"""
      <div>Hello there!</div>
      <script>window.onload = () => console.log('onload')</script>
    """
    )
    request.finish()


def track_network_events(page: Page, events: List[str], requests: Set[Request]) -> None:
    def on_event(name: str, request: Request) -> None:
        events.append(name)
        requests.add(request)

    page.on("request", lambda r: on_event("request", r))
    page.on("requestfailed", lambda r: on_event("requestfailed", r))
    page.on("requestfinished", lambda r: on_event("requestfinished", r))
    page.on("response", lambda r: on_event("response", r.request))


def test_NA_008_should_work_with_cross_origin_opener_policy(
    page: Page, server: Server
) -> None:
    server.set_route("/empty.html", serve_coop_page)
    requests: Set[Request] = set()
    events: List[str] = []
    track_network_events(page, events, requests)
    response = must(page.goto(server.EMPTY_PAGE))
    assert page.url == server.EMPTY_PAGE
    response.finished()
    assert events == ["request", "response", "requestfinished"]
    assert len(requests) == 1
    assert response.request.failure is None


@pytest.mark.parametrize("cross_origin_embedder_policy", [None, "require-corp"])
def test_NA_009_should_work_with_cross_origin_opener_policy_and_state(
    page: Page, server: Server, cross_origin_embedder_policy: Optional[str]
) -> None:
    def handle(request: TestServerRequest) -> None:
        request.setHeader("Cross-Origin-Opener-Policy", "same-origin")
        if cross_origin_embedder_policy:
            request.setHeader(
                "Cross-Origin-Embedder-Policy", cross_origin_embedder_policy
            )
        request.write(
            b"""
        <!doctype html>
        <h1>hello</h1>
        <script type="module">history.replaceState({ key: 1 }, '', location.href);</script>
      """
        )
        request.finish()

    server.set_route("/empty.html", handle)
    response = must(page.goto(server.EMPTY_PAGE))
    assert response.status == 200
    assert page.url == server.EMPTY_PAGE
    assert page.evaluate("() => history.state") == {"key": 1}
    expect(page.locator("h1")).to_have_text("hello")


def test_NA_010_should_work_with_cross_origin_opener_policy_and_interception(
    page: Page, server: Server
) -> None:
    server.set_route("/empty.html", serve_coop_page)
    requests: Set[Request] = set()
    events: List[str] = []
    track_network_events(page, events, requests)

    def handle_route(route: Route) -> None:
        page.wait_for_timeout(100)
        route.continue_()

    page.route("**/*", handle_route)
    response = must(page.goto(server.EMPTY_PAGE))
    assert page.url == server.EMPTY_PAGE
    response.finished()
    assert events == ["request", "response", "requestfinished"]
    assert len(requests) == 1
    assert response.request.failure is None


def test_NA_011_should_work_with_cross_origin_opener_policy_after_redirect(
    page: Page, server: Server
) -> None:
    server.set_redirect("/redirect", "/empty.html")
    server.set_route("/empty.html", serve_coop_page)
    requests: Set[Request] = set()
    events: List[str] = []
    track_network_events(page, events, requests)
    response = must(page.goto(server.PREFIX + "/redirect"))
    assert page.url == server.EMPTY_PAGE
    response.finished()
    assert events == [
        "request",
        "response",
        "requestfinished",
        "request",
        "response",
        "requestfinished",
    ]
    assert len(requests) == 2
    assert response.request.failure is None
    first_request = response.request.redirected_from
    assert first_request
    assert first_request.url == server.PREFIX + "/redirect"


def test_NA_012_should_capture_iframe_navigation_request(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    assert page.url == server.EMPTY_PAGE

    request_frames: List[Frame] = []

    def on_request(r: Request) -> None:
        if r.url == server.PREFIX + "/frames/frame.html":
            request_frames.append(r.frame)

    page.on("request", on_request)
    response = must(page.goto(server.PREFIX + "/frames/one-frame.html"))
    assert page.url == server.PREFIX + "/frames/one-frame.html"
    assert response.frame == page.main_frame
    assert response.url == server.PREFIX + "/frames/one-frame.html"

    assert len(page.frames) == 2
    assert request_frames[-1] == page.frames[1]


def test_NA_013_should_capture_cross_process_iframe_navigation_request(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    assert page.url == server.EMPTY_PAGE

    request_frames: List[Frame] = []

    def on_request(r: Request) -> None:
        if r.url == server.CROSS_PROCESS_PREFIX + "/frames/frame.html":
            request_frames.append(r.frame)

    page.on("request", on_request)
    response = must(page.goto(server.CROSS_PROCESS_PREFIX + "/frames/one-frame.html"))
    assert page.url == server.CROSS_PROCESS_PREFIX + "/frames/one-frame.html"
    assert response.frame == page.main_frame
    assert response.url == server.CROSS_PROCESS_PREFIX + "/frames/one-frame.html"

    assert len(page.frames) == 2
    assert request_frames[-1] == page.frames[1]


def test_NA_014_should_work_with_anchor_navigation(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    assert page.url == server.EMPTY_PAGE
    page.goto(server.EMPTY_PAGE + "#foo")
    assert page.url == server.EMPTY_PAGE + "#foo"
    page.goto(server.EMPTY_PAGE + "#bar")
    assert page.url == server.EMPTY_PAGE + "#bar"


def test_NA_015_should_work_with_redirects(page: Page, server: Server) -> None:
    server.set_redirect("/redirect/1.html", "/redirect/2.html")
    server.set_redirect("/redirect/2.html", "/empty.html")
    response = must(page.goto(server.PREFIX + "/redirect/1.html"))
    assert response.status == 200
    assert page.url == server.EMPTY_PAGE


def test_NA_016_should_navigate_to_about_blank(page: Page, server: Server) -> None:
    response = page.goto("about:blank")
    assert response is None


def test_NA_017_should_return_response_when_page_changes_its_url_after_load(
    page: Page, server: Server
) -> None:
    response = must(page.goto(server.PREFIX + "/historyapi.html"))
    assert response.status == 200


def respond_204(request: TestServerRequest) -> None:
    request.setResponseCode(204)
    request.finish()


def test_NA_018_should_work_with_subframes_return_204(
    page: Page, server: Server
) -> None:
    server.set_route("/frames/frame.html", respond_204)
    page.goto(server.PREFIX + "/frames/one-frame.html")


def test_NA_019_should_work_with_subframes_return_204_with_domcontentloaded(
    page: Page, server: Server
) -> None:
    server.set_route("/frames/frame.html", respond_204)
    page.goto(server.PREFIX + "/frames/one-frame.html", wait_until="domcontentloaded")


def test_NA_020_should_fail_when_server_returns_204(
    page: Page, server: Server, browser_name: str, is_linux: bool
) -> None:
    if browser_name == "webkit" and is_linux:
        pytest.skip(
            "fixme: Regressed in https://github.com/microsoft/playwright-browsers/pull/1297"
        )
    # WebKit just loads an empty page.
    server.set_route("/empty.html", respond_204)
    with pytest.raises(Error) as exc_info:
        page.goto(server.EMPTY_PAGE)
    if browser_name == "chromium":
        assert "net::ERR_ABORTED" in exc_info.value.message
    elif browser_name == "webkit":
        assert "Aborted: 204 No Content" in exc_info.value.message
    else:
        assert "NS_BINDING_ABORTED" in exc_info.value.message


def test_NA_021_should_navigate_to_empty_page_with_domcontentloaded(
    page: Page, server: Server
) -> None:
    response = must(page.goto(server.EMPTY_PAGE, wait_until="domcontentloaded"))
    assert response.status == 200


def test_NA_022_should_work_when_page_calls_history_api_in_beforeunload(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    page.evaluate(
        """() => {
        window.addEventListener('beforeunload', () => history.replaceState(null, 'initial', window.location.href), false);
    }"""
    )
    response = must(page.goto(server.PREFIX + "/grid.html"))
    assert response.status == 200


def test_NA_023_should_fail_when_navigating_to_bad_url(
    page: Page, browser_name: str
) -> None:
    with pytest.raises(Error) as exc_info:
        page.goto("asdfasdf")
    if browser_name == "chromium" or browser_name == "webkit":
        assert "Cannot navigate to invalid URL" in exc_info.value.message
    else:
        assert "Invalid url" in exc_info.value.message


def test_NA_024_should_fail_when_navigating_to_bad_ssl(
    page: Page,
    https_server: Server,
    browser_name: str,
    platform: str,
    browser_channel: Optional[str],
) -> None:
    # Make sure that network events do not emit 'undefined'.
    # @see https://crbug.com/750469
    def check(request: Request) -> None:
        assert request

    page.on("request", check)
    page.on("requestfinished", check)
    page.on("requestfailed", check)
    with pytest.raises(Error) as exc_info:
        page.goto(https_server.EMPTY_PAGE)
    assert expected_ssl_error(browser_name, platform, browser_channel).search(
        exc_info.value.message
    )


def test_NA_025_should_fail_when_navigating_to_bad_ssl_after_redirects(
    page: Page,
    server: Server,
    https_server: Server,
    browser_name: str,
    platform: str,
    browser_channel: Optional[str],
) -> None:
    server.set_redirect("/redirect/1.html", "/redirect/2.html")
    server.set_redirect("/redirect/2.html", "/empty.html")
    with pytest.raises(Error) as exc_info:
        page.goto(https_server.PREFIX + "/redirect/1.html")
    assert expected_ssl_error(browser_name, platform, browser_channel).search(
        exc_info.value.message
    )


def test_NA_026_should_not_crash_when_navigating_to_bad_ssl_after_a_cross_origin_navigation(
    page: Page, server: Server, https_server: Server
) -> None:
    page.goto(server.CROSS_PROCESS_PREFIX + "/empty.html")
    with contextlib.suppress(Error):
        page.goto(https_server.EMPTY_PAGE)


@pytest.mark.skip_protocol_check
def test_NA_028_should_throw_if_networkidle2_is_passed_as_an_option(
    page: Page, server: Server
) -> None:
    with pytest.raises(Error) as exc_info:
        # networkidle2 is not allowed.
        page.goto(server.EMPTY_PAGE, wait_until=cast(Any, "networkidle2"))
    assert (
        "wait_until: expected one of (load|domcontentloaded|networkidle|commit)"
        in exc_info.value.message
    )


def test_NA_029_should_fail_when_main_resources_failed_to_load(
    page: Page, browser_name: str, is_win: bool, browser_channel: Optional[str]
) -> None:
    if browser_channel == "webkit-wsl":
        pytest.skip(
            "Networking mode mirrored ends up stalling connections rather than terminating them, see https://github.com/microsoft/WSL/issues/10855."
        )
    with pytest.raises(Error) as exc_info:
        page.goto("http://localhost:44123/non-existing-url")
    if browser_name == "chromium":
        assert "net::ERR_CONNECTION_REFUSED" in exc_info.value.message
    elif browser_name == "webkit" and is_win and browser_channel != "webkit-wsl":
        assert "Could not connect to server" in exc_info.value.message
    elif browser_name == "webkit":
        assert "Could not connect" in exc_info.value.message
    else:
        assert "NS_ERROR_CONNECTION_REFUSED" in exc_info.value.message


def test_NA_030_should_fail_when_exceeding_maximum_navigation_timeout(
    page: Page, server: Server
) -> None:
    # Hang for request to the empty.html
    server.set_route("/empty.html", lambda request: None)
    with pytest.raises(Error) as exc_info:
        page.goto(server.PREFIX + "/empty.html", timeout=1)
    assert "Page.goto: Timeout 1ms exceeded." in exc_info.value.message
    assert server.PREFIX + "/empty.html" in exc_info.value.message
    assert isinstance(exc_info.value, TimeoutError)


def test_NA_031_should_fail_when_exceeding_default_maximum_navigation_timeout(
    page: Page, server: Server
) -> None:
    # Hang for request to the empty.html
    server.set_route("/empty.html", lambda request: None)
    page.context.set_default_navigation_timeout(2)
    page.set_default_navigation_timeout(1)
    with pytest.raises(Error) as exc_info:
        page.goto(server.PREFIX + "/empty.html")
    assert "Page.goto: Timeout 1ms exceeded." in exc_info.value.message
    assert server.PREFIX + "/empty.html" in exc_info.value.message
    assert isinstance(exc_info.value, TimeoutError)


def test_NA_032_should_fail_when_exceeding_browser_context_navigation_timeout(
    page: Page, server: Server
) -> None:
    # Hang for request to the empty.html
    server.set_route("/empty.html", lambda request: None)
    page.context.set_default_navigation_timeout(2)
    with pytest.raises(Error) as exc_info:
        page.goto(server.PREFIX + "/empty.html")
    assert "Page.goto: Timeout 2ms exceeded." in exc_info.value.message
    assert server.PREFIX + "/empty.html" in exc_info.value.message
    assert isinstance(exc_info.value, TimeoutError)


def test_NA_033_should_fail_when_exceeding_default_maximum_timeout(
    page: Page, server: Server
) -> None:
    # Hang for request to the empty.html
    server.set_route("/empty.html", lambda request: None)
    # Upstream first undoes the default navigation timeout that its harness sets;
    # the Python harness sets none.
    page.context.set_default_timeout(2)
    page.set_default_timeout(1)
    with pytest.raises(Error) as exc_info:
        page.goto(server.PREFIX + "/empty.html")
    assert "Page.goto: Timeout 1ms exceeded." in exc_info.value.message
    assert server.PREFIX + "/empty.html" in exc_info.value.message
    assert isinstance(exc_info.value, TimeoutError)


def test_NA_034_should_fail_when_exceeding_browser_context_timeout(
    page: Page, server: Server
) -> None:
    # Hang for request to the empty.html
    server.set_route("/empty.html", lambda request: None)
    # Upstream first undoes the default navigation timeout that its harness sets;
    # the Python harness sets none.
    page.context.set_default_timeout(2)
    with pytest.raises(Error) as exc_info:
        page.goto(server.PREFIX + "/empty.html")
    assert "Page.goto: Timeout 2ms exceeded." in exc_info.value.message
    assert server.PREFIX + "/empty.html" in exc_info.value.message
    assert isinstance(exc_info.value, TimeoutError)


def test_NA_035_should_prioritize_default_navigation_timeout_over_default_timeout(
    page: Page, server: Server
) -> None:
    # Hang for request to the empty.html
    server.set_route("/empty.html", lambda request: None)
    page.set_default_timeout(0)
    page.set_default_navigation_timeout(1)
    with pytest.raises(Error) as exc_info:
        page.goto(server.PREFIX + "/empty.html")
    assert "Page.goto: Timeout 1ms exceeded." in exc_info.value.message
    assert server.PREFIX + "/empty.html" in exc_info.value.message
    assert isinstance(exc_info.value, TimeoutError)


def test_NA_036_should_disable_timeout_when_its_set_to_0(
    page: Page, server: Server
) -> None:
    loaded: List[bool] = []
    page.once("load", lambda _: loaded.append(True))
    page.goto(server.PREFIX + "/grid.html", timeout=0, wait_until="load")
    assert loaded == [True]


def test_NA_037_should_fail_when_replaced_by_another_navigation(
    page: Page,
    server: Server,
    browser_name: str,
    sync_gather: Callable[..., List[Any]],
) -> None:
    # Hang request to empty.html.
    empty_requests: List[TestServerRequest] = []
    server.set_route("/empty.html", empty_requests.append)

    def navigate() -> Error:
        with pytest.raises(Error) as exc_info:
            page.goto(server.PREFIX + "/empty.html")
        return exc_info.value

    def navigate_again() -> None:
        wait_until(page, lambda: len(empty_requests) > 0)
        page.goto(server.PREFIX + "/one-style.html")

    [error, _] = sync_gather(navigate, navigate_again)
    if browser_name == "chromium":
        assert "net::ERR_ABORTED" in error.message
    elif browser_name == "webkit":
        assert (
            f'Page.goto: Navigation to "{server.PREFIX}/empty.html" is interrupted by another navigation to "{server.PREFIX}/one-style.html"'
            in error.message
        )
    elif browser_name == "firefox":
        # Firefox might yield either NS_BINDING_ABORTED or 'navigation interrupted by another one'
        assert (
            f'Page.goto: Navigation to "{server.PREFIX}/empty.html" is interrupted by another navigation to "{server.PREFIX}/one-style.html"'
            in error.message
            or "NS_BINDING_ABORTED" in error.message
        )


def set_url_bar_routes(server: Server, redirect_delay: int, events: List[str]) -> None:
    """Routes of the url bar navigation tests: /a redirects to /c from JavaScript,
    and /b and /c respond after 2 seconds."""
    server.set_route(
        "/a",
        lambda request: respond_later(
            request,
            0,
            f"""
        <body>
          <script>
            setTimeout(() => {{
              window.location.pathname = '/c';
            }}, {redirect_delay});
          </script>
        </body>
      """.encode(),
            "text/html",
        ),
    )

    def slow_route(name: str) -> Any:
        def handle(request: TestServerRequest) -> None:
            events.append(f"started {name}")
            respond_later(
                request,
                2,
                name.upper().encode() * 3,
                "text/html",
                lambda: events.append(f"finished {name}"),
            )

        return handle

    server.set_route("/b", slow_route("b"))
    server.set_route("/c", slow_route("c"))


def test_NA_038_js_redirect_overrides_url_bar_navigation(
    page: Page, server: Server, browser_name: str
) -> None:
    events: List[str] = []
    set_url_bar_routes(server, 1000, events)
    page.goto(server.PREFIX + "/a")
    error: Optional[Error] = None
    try:
        page.goto(server.PREFIX + "/b")
    except Error as e:
        error = e
    expect_events = (
        ["started b", "finished b"]
        if browser_name == "chromium"
        else ["started b", "started c", "finished b", "finished c"]
    )
    # Port of expect(() => ...).toPass().
    for _ in range(100):
        if events == expect_events:
            break
        page.wait_for_timeout(100)
    assert events == expect_events
    if browser_name == "chromium":
        # Chromium prioritizes the url bar navigation over the js redirect.
        assert error is None
        expect(page).to_have_url(server.PREFIX + "/b")
    elif browser_name == "webkit":
        assert error
        assert (
            f'Page.goto: Navigation to "{server.PREFIX}/b" is interrupted by another navigation to "{server.PREFIX}/c"'
            in error.message
        )
        expect(page).to_have_url(server.PREFIX + "/c")
    elif browser_name == "firefox":
        assert error
        assert "NS_BINDING_ABORTED" in error.message
        expect(page).to_have_url(server.PREFIX + "/c")


def test_NA_039_should_succeed_on_url_bar_navigation_when_there_is_pending_navigation(
    page: Page, server: Server
) -> None:
    events: List[str] = []
    set_url_bar_routes(server, 10, events)
    page.goto(server.PREFIX + "/a")
    page.wait_for_timeout(1000)
    error: Optional[Error] = None
    try:
        page.goto(server.PREFIX + "/b")
    except Error as e:
        error = e
    expect_events = ["started c", "started b", "finished c", "finished b"]
    # Port of expect(() => ...).toPass({ timeout: 5000 }).
    for _ in range(50):
        if events == expect_events:
            break
        page.wait_for_timeout(100)
    assert events == expect_events
    assert error is None
    assert page.url == server.PREFIX + "/b"


def test_NA_040_should_work_when_navigating_to_valid_url(
    page: Page, server: Server
) -> None:
    response = must(page.goto(server.EMPTY_PAGE))
    assert response.ok is True


def test_NA_041_should_work_when_navigating_to_data_url(
    page: Page, server: Server
) -> None:
    response = page.goto("data:text/html,hello")
    assert response is None


def test_NA_042_should_work_when_navigating_to_404(page: Page, server: Server) -> None:
    response = must(page.goto(server.PREFIX + "/not-found"))
    assert response.ok is False
    assert response.status == 404


def test_NA_043_should_return_last_response_in_redirect_chain(
    page: Page, server: Server
) -> None:
    server.set_redirect("/redirect/1.html", "/redirect/2.html")
    server.set_redirect("/redirect/2.html", "/redirect/3.html")
    server.set_redirect("/redirect/3.html", server.EMPTY_PAGE)
    response = must(page.goto(server.PREFIX + "/redirect/1.html"))
    assert response.ok is True
    assert response.url == server.EMPTY_PAGE


def test_NA_044_should_not_leak_listeners_during_navigation(
    page: Page, server: Server
) -> None:
    # Python's counterpart of Node.js process warnings is the warnings module.
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        for _ in range(20):
            page.goto(server.EMPTY_PAGE)
    assert caught == []


def test_NA_045_should_not_leak_listeners_during_bad_navigation(
    page: Page, server: Server
) -> None:
    # Python's counterpart of Node.js process warnings is the warnings module.
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        for _ in range(20):
            # swallow navigation error
            with contextlib.suppress(Error):
                page.goto("asdf")
    assert caught == []


def test_NA_046_should_not_leak_listeners_during_20_wait_for_navigation(
    page: Page, server: Server
) -> None:
    # Python's counterpart of Node.js process warnings is the warnings module.
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with contextlib.ExitStack() as stack:
            for _ in range(20):
                stack.enter_context(page.expect_navigation())
            page.goto(server.EMPTY_PAGE)
    assert caught == []


def test_NA_047_should_navigate_to_data_url_and_not_fire_data_url_requests(
    page: Page, server: Server
) -> None:
    requests: List[Request] = []
    page.on("request", lambda request: requests.append(request))
    data_url = "data:text/html,<div>yo</div>"
    response = page.goto(data_url)
    assert response is None
    assert len(requests) == 0


def test_NA_048_should_navigate_to_url_with_hash_and_fire_requests_without_hash(
    page: Page, server: Server
) -> None:
    requests: List[Request] = []
    page.on("request", lambda request: requests.append(request))
    response = must(page.goto(server.EMPTY_PAGE + "#hash"))
    assert response.status == 200
    assert response.url == server.EMPTY_PAGE
    assert len(requests) == 1
    assert requests[0].url == server.EMPTY_PAGE


def test_NA_049_should_work_with_self_requesting_page(
    page: Page, server: Server
) -> None:
    response = must(page.goto(server.PREFIX + "/self-request.html"))
    assert response.status == 200
    assert "self-request.html" in response.url


def test_NA_050_should_fail_when_navigating_and_show_the_url_at_the_error_message(
    page: Page, server: Server, https_server: Server
) -> None:
    url = https_server.PREFIX + "/redirect/1.html"
    with pytest.raises(Error) as exc_info:
        page.goto(url)
    assert url in exc_info.value.message


def test_NA_051_should_be_able_to_navigate_to_a_page_controlled_by_service_worker(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/serviceworkers/fetch/sw.html")
    page.evaluate("() => window['activationPromise']")
    page.goto(server.PREFIX + "/serviceworkers/fetch/sw.html")


def test_NA_052_should_send_referer(page: Page, server: Server) -> None:
    with server.expect_request("/grid.html") as request1_info:
        with server.expect_request("/digits/1.png") as request2_info:
            page.goto(server.PREFIX + "/grid.html", referer="http://google.com/")
    request1 = request1_info.value
    request2 = request2_info.value
    assert request1.getHeader("referer") == "http://google.com/"
    # Make sure subresources do not inherit referer.
    assert request2.getHeader("referer") == server.PREFIX + "/grid.html"
    assert page.url == server.PREFIX + "/grid.html"


def test_NA_053_should_send_referer_of_cross_origin_url(
    page: Page, server: Server
) -> None:
    with server.expect_request("/grid.html") as request1_info:
        with server.expect_request("/digits/1.png") as request2_info:
            page.goto(
                server.PREFIX + "/grid.html", referer="https://microsoft.com/xbox/"
            )
    request1 = request1_info.value
    request2 = request2_info.value
    assert request1.getHeader("referer") == "https://microsoft.com/xbox/"
    # Make sure subresources do not inherit referer.
    assert request2.getHeader("referer") == server.PREFIX + "/grid.html"
    assert page.url == server.PREFIX + "/grid.html"


def test_NA_054_should_reject_referer_option_when_set_extra_http_headers_provides_referer(
    page: Page, server: Server
) -> None:
    page.set_extra_http_headers({"referer": "http://microsoft.com/"})
    with pytest.raises(Error) as exc_info:
        page.goto(server.PREFIX + "/grid.html", referer="http://google.com/")
    assert (
        '"referer" is already specified as extra HTTP header' in exc_info.value.message
    )
    assert server.PREFIX + "/grid.html" in exc_info.value.message


def test_NA_055_should_override_referrer_policy(
    page: Page, server: Server, assetdir: Path
) -> None:
    def handle(request: TestServerRequest) -> None:
        request.setHeader("Referrer-Policy", "no-referrer")
        request.serve_file(assetdir / "grid.html")

    server.set_route("/grid.html", handle)
    with server.expect_request("/grid.html") as request1_info:
        with server.expect_request("/digits/1.png") as request2_info:
            page.goto(server.PREFIX + "/grid.html", referer="http://microsoft.com/")
    request1 = request1_info.value
    request2 = request2_info.value
    assert request1.getHeader("referer") == "http://microsoft.com/"
    # Make sure subresources do not inherit referer.
    assert request2.getHeader("referer") is None
    assert page.url == server.PREFIX + "/grid.html"


def test_NA_056_should_fail_when_canceled_by_another_navigation(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    requests: List[TestServerRequest] = []
    server.set_route("/one-style.html", requests.append)

    def navigate() -> Error:
        with pytest.raises(Error) as exc_info:
            page.goto(server.PREFIX + "/one-style.html")
        return exc_info.value

    def navigate_again() -> None:
        wait_until(page, lambda: len(requests) > 0)
        page.goto(server.PREFIX + "/empty.html")

    [error, _] = sync_gather(navigate, navigate_again)
    assert error.message


def test_NA_057_should_work_with_lazy_loading_iframes(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/frames/lazy-frame.html")
    assert len(page.frames) == 2


def test_NA_058_should_report_raw_buffer_for_main_resource(
    page: Page,
    server: Server,
    browser_name: str,
    platform: str,
    browser_channel: Optional[str],
    request: pytest.FixtureRequest,
) -> None:
    if browser_name == "chromium":
        request.applymarker(
            pytest.mark.xfail(
                reason="upstream it.fail: Chromium sends main resource as text",
                strict=True,
            )
        )
    if (
        browser_name == "webkit"
        and platform == "win32"
        and browser_channel != "webkit-wsl"
    ):
        request.applymarker(
            pytest.mark.xfail(reason="upstream it.fail: Same here", strict=True)
        )

    def handle(server_request: TestServerRequest) -> None:
        server_request.setResponseCode(200)
        server_request.write("Ü (lowercase ü)".encode("utf-8"))
        server_request.finish()

    server.set_route("/empty.html", handle)
    response = must(page.goto(server.PREFIX + "/empty.html"))
    body = response.body()
    assert body.decode() == "Ü (lowercase ü)"


def test_NA_059_should_not_throw_unhandled_rejections_on_invalid_url(
    page: Page, server: Server
) -> None:
    with pytest.raises(Error) as exc_info:
        page.goto("https://www.youtube Panel Title.com/")
    assert "Panel Title" in str(exc_info.value)


def test_NA_060_should_not_crash_when_rtc_peer_connection_is_used(
    page: Page, server: Server
) -> None:
    def handle(request: TestServerRequest) -> None:
        request.write(
            b"""
      <!DOCTYPE html>
      <html>
        <body>
          <script>
            window.RTCPeerConnection && new window.RTCPeerConnection({
              iceServers: []
            });
          </script>
        </body>
      </html>
"""
        )
        request.finish()

    server.set_route("/rtc.html", handle)
    page.goto(server.PREFIX + "/rtc.html")
    page.evaluate(
        """() => {
        // RTCPeerConnection is not present on WebKit Linux
        window.RTCPeerConnection && new window.RTCPeerConnection({
          iceServers: []
        });
    }"""
    )


def test_NA_061_should_properly_wait_for_load(page: Page, server: Server) -> None:
    server.set_route(
        "/slow.js",
        lambda request: respond_later(
            request,
            0.1,
            b"window.results.push('slow module');export const foo = 'slow';",
            "application/javascript",
        ),
    )
    page.goto(server.PREFIX + "/load-event/load-event.html")
    results = page.evaluate("window.results")
    assert results == [
        "script tag after after module",
        "slow module",
        "module",
        "DOMContentLoaded",
        "load",
    ]


def test_NA_062_should_not_resolve_goto_upon_window_stop(
    page: Page,
    server: Server,
    browser_name: str,
    sync_gather: Callable[..., List[Any]],
) -> None:
    if browser_name == "firefox":
        pytest.skip("fixme: load/domcontentloaded events are flaky")

    responses: List[TestServerRequest] = []

    def handle(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("Content-Type", "text/javascript")
        responses.append(request)

    server.set_route("/module.js", handle)
    done: List[bool] = []

    def navigate() -> None:
        with contextlib.suppress(Error):
            page.goto(server.PREFIX + "/window-stop.html")
            done.append(True)

    def check() -> None:
        wait_until(page, lambda: len(responses) > 0)
        assert done == []
        page.wait_for_timeout(1000)  # give it some time to erroneously resolve
        end(responses[0], b"")
        page.wait_for_timeout(1000)  # give it more time to erroneously resolve
        assert done == []
        # The test ends with the navigation still pending; closing the page ends it.
        page.close()

    sync_gather(navigate, check)


def test_NA_063_should_return_from_goto_if_new_navigation_is_started(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    server.set_route("/slow.js", lambda request: None)
    finished: List[bool] = []

    def navigate() -> Optional[Response]:
        response = page.goto(server.PREFIX + "/load-event/load-event.html")
        finished.append(True)
        return response

    def navigate_again() -> None:
        page.wait_for_timeout(500)
        assert finished == []
        page.goto(server.EMPTY_PAGE)

    [navigation, _] = sync_gather(navigate, navigate_again)
    assert must(navigation).status == 200


def test_NA_064_should_return_when_navigation_is_committed_if_commit_is_specified(
    page: Page, server: Server
) -> None:
    server.set_route("/script.js", lambda request: None)

    def handle(request: TestServerRequest) -> None:
        request.setHeader("content-type", "text/html")
        request.write(b'<title>Hello</title><script src="script.js"></script>')
        request.finish()

    server.set_route("/empty.html", handle)
    response = must(page.goto(server.EMPTY_PAGE, wait_until="commit"))
    assert response.status == 200
    assert page.title() == "Hello"


def test_NA_065_should_wait_for_load_when_iframe_attaches_and_detaches(
    page: Page, server: Server
) -> None:
    def handle_empty(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("content-type", "text/html")
        request.write(
            b"""
      <body>
        <script>
          const iframe = document.createElement('iframe');
          iframe.src = './iframe.html';
          document.body.appendChild(iframe);
          setTimeout(() => iframe.remove(), 1000);
        </script>
      </body>
    """
        )
        request.finish()

    server.set_route("/empty.html", handle_empty)

    def handle_iframe(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("content-type", "text/html")
        request.write(
            b"""
      <link rel="stylesheet" href="./style2.css">
    """
        )
        request.finish()

    server.set_route("/iframe.html", handle_iframe)

    # Stall the css so that 'load' does not fire.
    server.set_route("/style2.css", lambda request: None)

    # Make sure that iframe is gone.
    with page.expect_event("framedetached"):
        page.goto(server.EMPTY_PAGE, wait_until="load")
    assert page.query_selector("iframe") is None


def test_NA_066_should_return_url_with_basic_auth_info(
    page: Page, server: Server
) -> None:
    url = f"http://admin:admin@localhost:{server.PORT}/empty.html"
    page.goto(url)
    assert page.url == url
