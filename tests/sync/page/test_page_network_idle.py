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

"""Port of tests/page/page-network-idle.spec.ts."""

import json
import time
from typing import Any, Callable, List, Optional

from playwright.sync_api import Frame, Page, Response, Route
from tests.server import ExpectResponse, Server, TestServerRequest, reactor


def respond_not_found(request: TestServerRequest) -> None:
    """Answers a request that a route handler holds: `res.statusCode = 404; res.end(...)`."""

    def respond() -> None:
        request.setResponseCode(404)
        request.write(b"File not found")
        request.finish()

    reactor.callFromThread(respond)


def wait_for_server_request(
    page: Page, request_info: ExpectResponse[TestServerRequest]
) -> TestServerRequest:
    """Waits until the test server gets the request of server.expect_request()."""
    while True:
        try:
            return request_info.value
        except ValueError:
            page.wait_for_timeout(10)


def network_idle_test(
    frame: Frame,
    server: Server,
    action: Callable[[], Optional[Response]],
    sync_gather: Callable[..., List[Any]],
    is_set_content: bool = False,
) -> None:
    page = frame.page
    # Track when the action gets completed.
    action_finished = False

    def run_action() -> Optional[Response]:
        nonlocal action_finished
        response = action()
        action_finished = True
        return response

    def rest() -> float:
        # Hold on to a bunch of requests without answering.
        server.set_route("/fetch-request-a.js", lambda request: None)
        server.set_route("/fetch-request-b.js", lambda request: None)
        with (
            server.expect_request(
                "/fetch-request-b.js"
            ) as second_fetch_resource_requested,
            page.expect_request(server.PREFIX + "/fetch-request-b.js"),
        ):
            with (
                server.expect_request(
                    "/fetch-request-a.js"
                ) as first_fetch_resource_requested,
                page.expect_request(server.PREFIX + "/fetch-request-a.js"),
            ):
                # Navigate to a page which loads immediately and then does a bunch of
                # requests via javascript's fetch method. The action starts when this
                # function first waits.
                if not is_set_content:
                    # Wait for the frame's 'load' event.
                    with frame.expect_navigation(wait_until="load"):
                        pass
                assert action_finished is False

            # Wait for the initial resource to be requested.
            response_a = wait_for_server_request(page, first_fetch_resource_requested)
            assert action_finished is False

            # Trigger the second request.
            page.evaluate("() => window['fetchSecond']()")
            # Finish the first request.
            respond_not_found(response_a)

        # Wait for the second round to be requested.
        response_b = wait_for_server_request(page, second_fetch_resource_requested)
        assert action_finished is False

        # Finishing the second response should trigger networkidle.
        start = time.monotonic()
        respond_not_found(response_b)
        return start

    start, response = sync_gather(rest, run_action)
    timer_triggered = time.monotonic() - start >= 0.5
    assert timer_triggered is True
    if not is_set_content:
        assert response
        assert response.ok is True


def test_NE_070_should_navigate_to_empty_page_with_networkidle(
    page: Page, server: Server
) -> None:
    response = page.goto(server.EMPTY_PAGE, wait_until="networkidle")
    assert response
    assert response.status == 200


def test_NE_071_should_wait_for_networkidle_to_succeed_navigation(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    network_idle_test(
        page.main_frame,
        server,
        lambda: page.goto(
            server.PREFIX + "/networkidle.html", wait_until="networkidle"
        ),
        sync_gather,
    )


def test_NE_072_should_wait_for_networkidle_to_succeed_navigation_with_request_from_previous_navigation(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    page.goto(server.EMPTY_PAGE)
    server.set_route("/foo.js", lambda request: None)
    page.set_content("<script>fetch('foo.js');</script>")
    network_idle_test(
        page.main_frame,
        server,
        lambda: page.goto(
            server.PREFIX + "/networkidle.html", wait_until="networkidle"
        ),
        sync_gather,
    )


def test_NE_073_should_wait_for_networkidle_in_wait_for_navigation(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    def action() -> Optional[Response]:
        with page.expect_navigation(wait_until="networkidle") as response_info:
            page.goto(server.PREFIX + "/networkidle.html")
        return response_info.value

    network_idle_test(page.main_frame, server, action, sync_gather)


def test_NE_074_should_wait_for_networkidle_in_set_content(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    page.goto(server.EMPTY_PAGE)

    def action() -> None:
        page.set_content(
            "<script src='networkidle.js'></script>", wait_until="networkidle"
        )

    network_idle_test(page.main_frame, server, action, sync_gather, True)


def test_NE_075_should_wait_for_networkidle_in_set_content_with_request_from_previous_navigation(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    page.goto(server.EMPTY_PAGE)
    server.set_route("/foo.js", lambda request: None)
    page.set_content("<script>fetch('foo.js');</script>")

    def action() -> None:
        page.set_content(
            "<script src='networkidle.js'></script>", wait_until="networkidle"
        )

    network_idle_test(page.main_frame, server, action, sync_gather, True)


def test_NE_076_should_wait_for_networkidle_when_navigating_iframe(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    page.goto(server.PREFIX + "/frames/one-frame.html")
    frame = page.main_frame.child_frames[0]
    network_idle_test(
        frame,
        server,
        lambda: frame.goto(
            server.PREFIX + "/networkidle.html", wait_until="networkidle"
        ),
        sync_gather,
    )


def test_NE_077_should_wait_for_networkidle_in_set_content_from_the_child_frame(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    page.goto(server.EMPTY_PAGE)

    def action() -> None:
        page.set_content(
            "<iframe src='networkidle.html'></iframe>", wait_until="networkidle"
        )

    network_idle_test(page.main_frame, server, action, sync_gather, True)


def test_NE_078_should_wait_for_networkidle_from_the_child_frame(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    network_idle_test(
        page.main_frame,
        server,
        lambda: page.goto(
            server.PREFIX + "/networkidle-frame.html", wait_until="networkidle"
        ),
        sync_gather,
    )


def test_NE_079_should_wait_for_networkidle_from_the_popup(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content(
        """
    <button id=box1 onclick="window.open('./popup/popup.html')">Button1</button>
    <button id=box2 onclick="window.open('./popup/popup.html')">Button2</button>
    <button id=box3 onclick="window.open('./popup/popup.html')">Button3</button>
    <button id=box4 onclick="window.open('./popup/popup.html')">Button4</button>
    <button id=box5 onclick="window.open('./popup/popup.html')">Button5</button>
  """
    )
    for i in range(1, 6):
        with page.expect_popup() as popup_info:
            page.click("#box" + str(i))
        popup = popup_info.value
        popup.wait_for_load_state("networkidle")


def test_NE_080_should_wait_for_networkidle_when_iframe_attaches_and_detaches(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    server.set_route("/empty.html", lambda request: None)
    done = False

    def set_content() -> None:
        nonlocal done
        page.set_content(
            f"""
    <body>
      <script>
        const iframe = document.createElement('iframe');
        iframe.src = {json.dumps(server.EMPTY_PAGE)};
        document.body.appendChild(iframe);
      </script>
    </body>
  """,
            wait_until="networkidle",
        )
        done = True

    def rest() -> None:
        page.wait_for_timeout(600)
        assert done is False
        page.evaluate(
            """() => {
    document.querySelector('iframe').remove();
  }"""
        )

    sync_gather(set_content, rest)
    assert done is True


def test_NE_081_should_work_after_repeated_navigations_in_the_same_page(
    page: Page, server: Server
) -> None:
    request_count = 0

    def handle_empty(route: Route) -> None:
        route.fulfill(
            content_type="text/html",
            body="""
        <script>
          fetch('http://localhost:8000/sample').then(res => console.log(res.json()))
        </script>""",
        )

    page.route("**/empty.html", handle_empty)

    def handle_sample(route: Route) -> None:
        nonlocal request_count
        request_count += 1
        route.fulfill(
            content_type="application/json",
            body=json.dumps({"content": "sample"}),
        )

    page.route("**/sample", handle_sample)

    page.goto(server.EMPTY_PAGE, wait_until="networkidle")
    assert request_count == 1
    page.goto(server.EMPTY_PAGE, wait_until="networkidle")
    assert request_count == 2


def handle_sse(request: TestServerRequest) -> None:
    request.setResponseCode(200)
    request.setHeader("Content-Type", "text/event-stream")
    request.setHeader("Connection", "keep-alive")
    request.setHeader("Cache-Control", "no-cache")
    request.write(b"data: hello\n\n")


def test_NE_082_should_not_wait_for_an_open_event_source_connection(
    page: Page, server: Server
) -> None:
    server.set_route("/sse", handle_sse)

    def handle_page(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("Content-Type", "text/html")
        request.write(b"<script>new EventSource('/sse');</script>")
        request.finish()

    server.set_route("/sse-page.html", handle_page)

    response = page.goto(server.PREFIX + "/sse-page.html", wait_until="networkidle")
    assert response
    assert response.status == 200


def test_NE_083_should_not_wait_for_an_open_event_source_connection_in_set_content(
    page: Page, server: Server
) -> None:
    server.set_route("/sse", handle_sse)

    page.goto(server.EMPTY_PAGE)
    page.set_content(
        """<script>
    window.__sseOpened = new Promise(resolve => {
      const es = new EventSource('/sse');
      es.onmessage = () => resolve();
    });
  </script>""",
        wait_until="networkidle",
    )
    page.evaluate("() => window['__sseOpened']")
