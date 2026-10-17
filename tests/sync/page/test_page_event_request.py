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

"""Port of tests/page/page-event-request.spec.ts."""

from typing import Callable, Dict, List, Optional, Set

import pytest

from playwright.sync_api import Error, Page, Request, Route
from tests.server import Server, TestServerRequest

from ..utils import Utils


def first_event(page: Page, events: List[str]) -> str:
    """Like `Promise.race()` of event promises: waits until one event is in `events`."""
    for _ in range(3000):
        if events:
            break
        page.wait_for_timeout(10)
    assert events, "none of the events happened"
    return events[0]


def test_NE_091_should_fire_for_navigation_requests(page: Page, server: Server) -> None:
    requests: List[Request] = []
    page.on("request", lambda request: requests.append(request))
    page.goto(server.EMPTY_PAGE)
    assert len(requests) == 1


def test_NE_092_should_fire_for_iframes(
    page: Page, server: Server, utils: Utils
) -> None:
    requests: List[Request] = []
    page.on("request", lambda request: requests.append(request))
    page.goto(server.EMPTY_PAGE)
    utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    assert len(requests) == 2


def test_NE_093_should_fire_for_fetches(page: Page, server: Server) -> None:
    requests: List[Request] = []
    page.on("request", lambda request: requests.append(request))
    page.goto(server.EMPTY_PAGE)
    page.evaluate("() => fetch('/empty.html')")
    assert len(requests) == 2


def test_NE_094_should_fire_for_fetches_with_keepalive_true(
    page: Page, server: Server
) -> None:
    requests: List[Request] = []
    page.on("request", lambda request: requests.append(request))
    page.goto(server.EMPTY_PAGE)
    page.evaluate("() => fetch('/empty.html', { keepalive: true })")
    assert len(requests) == 2


def test_NE_095_should_report_requests_and_responses_handled_by_service_worker(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/serviceworkers/fetchdummy/sw.html")
    page.evaluate("() => window['activationPromise']")
    with page.expect_event("request") as request_info:
        sw_response = page.evaluate("() => window['fetchDummy']('foo')")
    request = request_info.value
    assert sw_response == "responseFromServiceWorker:foo"
    assert request.url == server.PREFIX + "/serviceworkers/fetchdummy/foo"
    assert request.service_worker is None
    response = request.response()
    assert response
    assert response.url == server.PREFIX + "/serviceworkers/fetchdummy/foo"
    assert response.text() == "responseFromServiceWorker:foo"
    assert response.from_service_worker is True

    with page.expect_event("requestfailed") as failed_request_info:
        try:
            page.evaluate("() => window['fetchDummy']('error')")
        except Error:
            pass
    failed_request = failed_request_info.value
    assert failed_request.url == server.PREFIX + "/serviceworkers/fetchdummy/error"
    assert failed_request.failure is not None
    assert failed_request.service_worker is None
    assert failed_request.response() is None


def test_NE_096_should_report_requests_and_responses_handled_by_service_worker_with_routing(
    page: Page, server: Server, browser_name: str
) -> None:
    intercepted_urls: List[str] = []

    def handle(route: Route) -> None:
        intercepted_urls.append(route.request.url)
        route.continue_()

    page.route("**/*", handle)
    page.goto(server.PREFIX + "/serviceworkers/fetchdummy/sw.html")
    page.evaluate("() => window['activationPromise']")
    with page.expect_event("request") as request_info:
        sw_response = page.evaluate("() => window['fetchDummy']('foo')")
    request = request_info.value
    assert sw_response == "responseFromServiceWorker:foo"
    assert request.url == server.PREFIX + "/serviceworkers/fetchdummy/foo"
    assert request.service_worker is None
    response = request.response()
    assert response
    assert response.url == server.PREFIX + "/serviceworkers/fetchdummy/foo"
    assert response.text() == "responseFromServiceWorker:foo"

    with page.expect_event("requestfailed") as failed_request_info:
        try:
            page.evaluate("() => window['fetchDummy']('error')")
        except Error:
            pass
    failed_request = failed_request_info.value
    assert failed_request.url == server.PREFIX + "/serviceworkers/fetchdummy/error"
    assert failed_request.failure is not None
    assert failed_request.service_worker is None
    assert failed_request.response() is None

    expected_urls = [server.PREFIX + "/serviceworkers/fetchdummy/sw.html"]
    if browser_name == "webkit":
        expected_urls.append(server.PREFIX + "/serviceworkers/fetchdummy/sw.js")
    assert intercepted_urls == expected_urls


def test_NE_097_should_report_navigation_requests_and_responses_handled_by_service_worker(
    page: Page, server: Server, browser_name: str
) -> None:
    page.goto(server.PREFIX + "/serviceworkers/stub/sw.html")
    page.evaluate("() => window['activationPromise']")

    reload_response = page.reload()
    assert reload_response
    assert page.evaluate("window.fromSW") is True
    assert reload_response.url == server.PREFIX + "/serviceworkers/stub/sw.html"
    page.evaluate("() => window['activationPromise']")

    if browser_name != "firefox":
        # When SW fetch throws, Firefox does not fail the navigation,
        # but rather falls back to the real network.

        with page.expect_event("requestfailed") as failed_request_info:
            page.evaluate(
                """() => {
                    window.location.href = '/serviceworkers/stub/error.html';
                }"""
            )
        failed_request = failed_request_info.value
        assert failed_request.url == server.PREFIX + "/serviceworkers/stub/error.html"
        failure = failed_request.failure
        assert failure
        assert ("net::ERR_FAILED" if browser_name == "chromium" else "uh oh") in failure
        assert failed_request.service_worker is None
        assert failed_request.response() is None


def test_NE_098_should_report_navigation_requests_and_responses_handled_by_service_worker_with_routing(
    page: Page, server: Server, browser_name: str
) -> None:
    page.route("**/*", lambda route: route.continue_())
    page.goto(server.PREFIX + "/serviceworkers/stub/sw.html")
    page.evaluate("() => window['activationPromise']")

    reload_response = page.reload()
    assert reload_response
    assert page.evaluate("window.fromSW") is True
    assert reload_response.url == server.PREFIX + "/serviceworkers/stub/sw.html"
    page.evaluate("() => window['activationPromise']")

    if browser_name != "firefox":
        # When SW fetch throws, Firefox does not fail the navigation,
        # but rather falls back to the real network.

        with page.expect_event("requestfailed") as failed_request_info:
            page.evaluate(
                """() => {
                    window.location.href = '/serviceworkers/stub/error.html';
                    // eslint-disable-next-line
                    undefined
                }"""
            )
        failed_request = failed_request_info.value
        assert failed_request.url == server.PREFIX + "/serviceworkers/stub/error.html"
        failure = failed_request.failure
        assert failure
        assert ("net::ERR_FAILED" if browser_name == "chromium" else "uh oh") in failure
        assert failed_request.service_worker is None
        assert failed_request.response() is None


def test_NE_099_should_return_response_body_when_cross_origin_opener_policy_is_set(
    page: Page, server: Server
) -> None:
    def handle(server_request: TestServerRequest) -> None:
        server_request.setHeader("Cross-Origin-Opener-Policy", "same-origin")
        # Note: without 'onload', Firefox sometimes does not fire the load event
        # over the protocol. The reason is unclear.
        server_request.write(
            b"""
      <div>Hello there!</div>
      <script>window.onload = () => console.log('onload')</script>
    """
        )
        server_request.finish()

    server.set_route("/empty.html", handle)
    response = page.goto(server.EMPTY_PAGE)
    assert response
    assert page.url == server.EMPTY_PAGE
    response.finished()
    assert response.request.failure is None
    assert "Hello there!" in response.text()


@pytest.mark.only_browser("chromium")
def test_NE_100_should_fire_requestfailed_when_intercepting_race(
    page: Page, server: Server
) -> None:
    # This test is specifically testing Chromium race.
    errors: List[str] = []
    failures: Set[Request] = set()
    alive: Set[Request] = set()

    def on_request(request: Request) -> None:
        if request in alive:
            errors.append(f"request event for an alive request {request.url}")
        if request in failures:
            errors.append(f"request event for a failed request {request.url}")
        alive.add(request)

    def on_request_failed(request: Request) -> None:
        if request in failures:
            errors.append(f"requestfailed event for a failed request {request.url}")
        if request not in alive:
            errors.append(f"requestfailed event for an unknown request {request.url}")
        alive.discard(request)
        failures.add(request)

    page.on("request", on_request)
    page.on("requestfailed", on_request_failed)

    # Stall requests to make sure we don't get requestfinished.
    page.route("**", lambda route: None)

    # Resolves on the 10th failed request.
    with page.expect_event("requestfailed", lambda _: len(failures) >= 10):
        page.set_content(
            f"""
    <iframe src="{server.EMPTY_PAGE}"></iframe>
    <iframe src="{server.EMPTY_PAGE}"></iframe>
    <iframe src="{server.EMPTY_PAGE}"></iframe>
    <iframe src="{server.EMPTY_PAGE}"></iframe>
    <iframe src="{server.EMPTY_PAGE}"></iframe>
    <iframe src="{server.EMPTY_PAGE}"></iframe>
    <iframe src="{server.EMPTY_PAGE}"></iframe>
    <iframe src="{server.EMPTY_PAGE}"></iframe>
    <iframe src="{server.EMPTY_PAGE}"></iframe>
    <iframe src="{server.EMPTY_PAGE}"></iframe>
    <script>
      function abortAll() {{
        const frames = document.querySelectorAll("iframe");
        for (const frame of frames)
          frame.src = "about:blank";
      }}
      abortAll();
    </script>
  """
        )
    assert errors == []


def test_NE_101_main_resource_xhr_should_have_type_xhr(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    with page.expect_event("request") as request_info:
        page.evaluate(
            """() => {
                const x = new XMLHttpRequest();
                x.open('GET', location.href, false);
                x.send();
            }"""
        )
    request = request_info.value
    assert request.is_navigation_request() is False
    assert request.resource_type == "xhr"


def test_NE_102_should_finish_204_request(page: Page, server: Server) -> None:
    def handle(server_request: TestServerRequest) -> None:
        server_request.setResponseCode(204)
        server_request.setHeader("Content-type", "text/plain")
        server_request.finish()

    server.set_route("/204", handle)
    page.goto(server.EMPTY_PAGE)
    events: List[str] = []
    page.on(
        "requestfailed",
        lambda r: events.append("requestfailed") if r.url.endswith("/204") else None,
    )
    page.on(
        "requestfinished",
        lambda r: events.append("requestfinished") if r.url.endswith("/204") else None,
    )
    try:
        page.evaluate("async url => { await fetch(url); }", server.PREFIX + "/204")
    except Error:
        pass
    assert first_event(page, events) == "requestfinished"


def test_NE_103_should_fail_204_navigation_request(page: Page, server: Server) -> None:
    def handle(server_request: TestServerRequest) -> None:
        server_request.setResponseCode(204)
        server_request.finish()

    server.set_route("/204", handle)
    page.goto(server.EMPTY_PAGE)
    events: List[str] = []
    page.on(
        "requestfailed",
        lambda r: events.append("requestfailed") if r.url.endswith("/204") else None,
    )
    page.on(
        "requestfinished",
        lambda r: events.append("requestfinished") if r.url.endswith("/204") else None,
    )
    page.set_content(f'<a href="{server.PREFIX}/204">link</a>')
    page.click("a", no_wait_after=True)
    assert first_event(page, events) == "requestfailed"


def test_NE_104_picture_resource_should_have_type_image(page: Page) -> None:
    with page.expect_event("request") as request_info:
        page.set_content(
            """
      <picture>
        <source>
          <img src="https://www.wikipedia.org/portal/wikipedia.org/assets/img/Wikipedia-logo-v2@2x.png">
        </source>
      </picture>
    """
        )
    request = request_info.value
    assert request.resource_type == "image"


def cors_route(
    server_requests: List[str],
) -> Callable[[TestServerRequest], None]:
    def handle(server_request: TestServerRequest) -> None:
        server_requests.append(
            f"{server_request.method.decode()} {server_request.uri.decode()}"
        )
        if server_request.method == b"OPTIONS":
            server_request.setResponseCode(204)
            server_request.setHeader("Access-Control-Allow-Origin", "*")
            server_request.setHeader(
                "Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS"
            )
            server_request.setHeader("Access-Control-Allow-Headers", "*")
            server_request.finish()
            return
        server_request.setResponseCode(200)
        server_request.setHeader("Content-type", "text/plain")
        server_request.setHeader("Access-Control-Allow-Origin", "*")
        server_request.write(b"Hello there!")
        server_request.finish()

    return handle


CORS_FETCH = """async url => {
    const response = await fetch(url, {
        method: 'POST',
        body: '',
        headers: {
            'Content-Type': 'application/json',
            'X-Custom-Header': 'test-value'
        }
    });
    return await response.text();
}"""


# Chromium: requestWillBeSentEvent.frameId is undefined for OPTIONS.
# WebKit: no requestWillBeSent event in the protocol for OPTIONS (at least on Mac).
# Firefox: OPTIONS request can be dispatched.
def test_NE_105_should_not_expose_preflight_options_request(
    page: Page, server: Server
) -> None:
    server_requests: List[str] = []
    server.set_route("/cors", cors_route(server_requests))
    client_requests: List[str] = []
    page.on(
        "request",
        lambda request: client_requests.append(f"{request.method} {request.url}"),
    )
    response: Optional[str]
    try:
        response = page.evaluate(CORS_FETCH, server.CROSS_PROCESS_PREFIX + "/cors")
    except Error:
        response = None
    assert response == "Hello there!"
    assert server_requests == [
        "OPTIONS /cors",
        "POST /cors",
    ]
    assert client_requests == [
        f"POST {server.CROSS_PROCESS_PREFIX}/cors",
    ]


def test_NE_106_should_not_expose_preflight_options_request_with_network_interception(
    page: Page, server: Server, browser_name: str
) -> None:
    server_requests: List[str] = []
    server.set_route("/cors", cors_route(server_requests))
    page.route("**/*", lambda route: route.continue_())
    client_requests: List[str] = []
    page.on(
        "request",
        lambda request: client_requests.append(f"{request.method} {request.url}"),
    )
    response: Optional[str]
    try:
        response = page.evaluate(CORS_FETCH, server.CROSS_PROCESS_PREFIX + "/cors")
    except Error:
        response = None
    assert response == "Hello there!"
    assert server_requests == [
        *([] if browser_name == "chromium" else ["OPTIONS /cors"]),
        "POST /cors",
    ]
    assert client_requests == [
        f"POST {server.CROSS_PROCESS_PREFIX}/cors",
    ]


def test_NE_107_should_return_last_requests(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/title.html")

    def handle(server_request: TestServerRequest) -> None:
        server_request.write(
            f"url:{server.PREFIX}{server_request.uri.decode()}".encode()
        )
        server_request.finish()

    for i in range(200):
        server.set_route(f"/fetch?{i}", handle)

    # #0 is the navigation request, so start with #1.
    for i in range(99):
        page.evaluate("url => fetch(url)", server.PREFIX + f"/fetch?{i}")
    first99_requests = page.requests()
    first99_requests.pop(0)
    for i in range(99, 199):
        page.evaluate("url => fetch(url)", server.PREFIX + f"/fetch?{i}")
    last100_requests = page.requests()
    all_requests = [*first99_requests, *last100_requests]

    # All 199 requests are fully functional.
    received: List[Dict[str, str]] = []
    for request in all_requests:
        response = request.response()
        assert response
        received.append({"text": response.text(), "url": request.url})
    expected: List[Dict[str, str]] = []
    for i in range(199):
        url = server.PREFIX + f"/fetch?{i}"
        expected.append({"url": url, "text": "url:" + url})
    assert received == expected
