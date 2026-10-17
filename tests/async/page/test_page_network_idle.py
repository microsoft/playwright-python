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

import asyncio
import json
import time
from typing import Any, Callable, Coroutine, Optional

from playwright.async_api import Frame, Page, Response, Route
from tests.server import Server, TestServerRequest, reactor


def respond_not_found(request: TestServerRequest) -> None:
    """Answers a request that a route handler holds: `res.statusCode = 404; res.end(...)`."""

    def respond() -> None:
        request.setResponseCode(404)
        request.write(b"File not found")
        request.finish()

    reactor.callFromThread(respond)


async def network_idle_test(
    frame: Frame,
    server: Server,
    action: Callable[[], Coroutine[Any, Any, Optional[Response]]],
    is_set_content: bool = False,
) -> None:
    page = frame.page

    async def wait_for_request(suffix: str) -> TestServerRequest:
        server_request, _ = await asyncio.gather(
            server.wait_for_request(suffix),
            page.wait_for_event(
                "request", lambda request: request.url == server.PREFIX + suffix
            ),
        )
        return server_request

    # Hold on to a bunch of requests without answering.
    server.set_route("/fetch-request-a.js", lambda request: None)
    first_fetch_resource_requested = asyncio.create_task(
        wait_for_request("/fetch-request-a.js")
    )
    server.set_route("/fetch-request-b.js", lambda request: None)
    second_fetch_resource_requested = asyncio.create_task(
        wait_for_request("/fetch-request-b.js")
    )

    # Navigate to a page which loads immediately and then does a bunch of
    # requests via javascript's fetch method.
    if is_set_content:
        action_task = asyncio.create_task(action())
    else:
        # Wait for the frame's 'load' event.
        async with frame.expect_navigation(wait_until="load"):
            action_task = asyncio.create_task(action())
    # Track when the action gets completed.
    assert action_task.done() is False

    # Wait for the initial resource to be requested.
    response_a = await first_fetch_resource_requested
    assert action_task.done() is False

    # Trigger the second request.
    await page.evaluate("() => window['fetchSecond']()")
    # Finish the first request.
    respond_not_found(response_a)

    # Wait for the second round to be requested.
    response_b = await second_fetch_resource_requested
    assert action_task.done() is False

    # Finishing the second response should trigger networkidle.
    start = time.monotonic()
    respond_not_found(response_b)

    response = await action_task
    timer_triggered = time.monotonic() - start >= 0.5
    assert timer_triggered is True
    if not is_set_content:
        assert response
        assert response.ok is True


async def test_NE_070_should_navigate_to_empty_page_with_networkidle(
    page: Page, server: Server
) -> None:
    response = await page.goto(server.EMPTY_PAGE, wait_until="networkidle")
    assert response
    assert response.status == 200


async def test_NE_071_should_wait_for_networkidle_to_succeed_navigation(
    page: Page, server: Server
) -> None:
    await network_idle_test(
        page.main_frame,
        server,
        lambda: page.goto(
            server.PREFIX + "/networkidle.html", wait_until="networkidle"
        ),
    )


async def test_NE_072_should_wait_for_networkidle_to_succeed_navigation_with_request_from_previous_navigation(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    server.set_route("/foo.js", lambda request: None)
    await page.set_content("<script>fetch('foo.js');</script>")
    await network_idle_test(
        page.main_frame,
        server,
        lambda: page.goto(
            server.PREFIX + "/networkidle.html", wait_until="networkidle"
        ),
    )


async def test_NE_073_should_wait_for_networkidle_in_wait_for_navigation(
    page: Page, server: Server
) -> None:
    async def action() -> Optional[Response]:
        async with page.expect_navigation(wait_until="networkidle") as response_info:
            goto_task = asyncio.create_task(
                page.goto(server.PREFIX + "/networkidle.html")
            )
        response = await response_info.value
        await goto_task
        return response

    await network_idle_test(page.main_frame, server, action)


async def test_NE_074_should_wait_for_networkidle_in_set_content(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)

    async def action() -> None:
        await page.set_content(
            "<script src='networkidle.js'></script>", wait_until="networkidle"
        )

    await network_idle_test(page.main_frame, server, action, True)


async def test_NE_075_should_wait_for_networkidle_in_set_content_with_request_from_previous_navigation(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    server.set_route("/foo.js", lambda request: None)
    await page.set_content("<script>fetch('foo.js');</script>")

    async def action() -> None:
        await page.set_content(
            "<script src='networkidle.js'></script>", wait_until="networkidle"
        )

    await network_idle_test(page.main_frame, server, action, True)


async def test_NE_076_should_wait_for_networkidle_when_navigating_iframe(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/frames/one-frame.html")
    frame = page.main_frame.child_frames[0]
    await network_idle_test(
        frame,
        server,
        lambda: frame.goto(
            server.PREFIX + "/networkidle.html", wait_until="networkidle"
        ),
    )


async def test_NE_077_should_wait_for_networkidle_in_set_content_from_the_child_frame(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)

    async def action() -> None:
        await page.set_content(
            "<iframe src='networkidle.html'></iframe>", wait_until="networkidle"
        )

    await network_idle_test(page.main_frame, server, action, True)


async def test_NE_078_should_wait_for_networkidle_from_the_child_frame(
    page: Page, server: Server
) -> None:
    await network_idle_test(
        page.main_frame,
        server,
        lambda: page.goto(
            server.PREFIX + "/networkidle-frame.html", wait_until="networkidle"
        ),
    )


async def test_NE_079_should_wait_for_networkidle_from_the_popup(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        """
    <button id=box1 onclick="window.open('./popup/popup.html')">Button1</button>
    <button id=box2 onclick="window.open('./popup/popup.html')">Button2</button>
    <button id=box3 onclick="window.open('./popup/popup.html')">Button3</button>
    <button id=box4 onclick="window.open('./popup/popup.html')">Button4</button>
    <button id=box5 onclick="window.open('./popup/popup.html')">Button5</button>
  """
    )
    for i in range(1, 6):
        async with page.expect_popup() as popup_info:
            await page.click("#box" + str(i))
        popup = await popup_info.value
        await popup.wait_for_load_state("networkidle")


async def test_NE_080_should_wait_for_networkidle_when_iframe_attaches_and_detaches(
    page: Page, server: Server
) -> None:
    server.set_route("/empty.html", lambda request: None)
    done = False

    async def set_content() -> None:
        nonlocal done
        await page.set_content(
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

    promise = asyncio.create_task(set_content())
    await page.wait_for_timeout(600)
    assert done is False
    await page.evaluate(
        """() => {
    document.querySelector('iframe').remove();
  }"""
    )
    await promise
    assert done is True


async def test_NE_081_should_work_after_repeated_navigations_in_the_same_page(
    page: Page, server: Server
) -> None:
    request_count = 0

    async def handle_empty(route: Route) -> None:
        await route.fulfill(
            content_type="text/html",
            body="""
        <script>
          fetch('http://localhost:8000/sample').then(res => console.log(res.json()))
        </script>""",
        )

    await page.route("**/empty.html", handle_empty)

    async def handle_sample(route: Route) -> None:
        nonlocal request_count
        request_count += 1
        await route.fulfill(
            content_type="application/json",
            body=json.dumps({"content": "sample"}),
        )

    await page.route("**/sample", handle_sample)

    await page.goto(server.EMPTY_PAGE, wait_until="networkidle")
    assert request_count == 1
    await page.goto(server.EMPTY_PAGE, wait_until="networkidle")
    assert request_count == 2


def handle_sse(request: TestServerRequest) -> None:
    request.setResponseCode(200)
    request.setHeader("Content-Type", "text/event-stream")
    request.setHeader("Connection", "keep-alive")
    request.setHeader("Cache-Control", "no-cache")
    request.write(b"data: hello\n\n")


async def test_NE_082_should_not_wait_for_an_open_event_source_connection(
    page: Page, server: Server
) -> None:
    server.set_route("/sse", handle_sse)

    def handle_page(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("Content-Type", "text/html")
        request.write(b"<script>new EventSource('/sse');</script>")
        request.finish()

    server.set_route("/sse-page.html", handle_page)

    response = await page.goto(
        server.PREFIX + "/sse-page.html", wait_until="networkidle"
    )
    assert response
    assert response.status == 200


async def test_NE_083_should_not_wait_for_an_open_event_source_connection_in_set_content(
    page: Page, server: Server
) -> None:
    server.set_route("/sse", handle_sse)

    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        """<script>
    window.__sseOpened = new Promise(resolve => {
      const es = new EventSource('/sse');
      es.onmessage = () => resolve();
    });
  </script>""",
        wait_until="networkidle",
    )
    await page.evaluate("() => window['__sseOpened']")
