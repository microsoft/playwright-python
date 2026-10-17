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

"""Port of tests/page/frame-goto.spec.ts."""

from typing import Any, Callable, Dict, List

import pytest

from playwright.sync_api import Error, Page, Response
from tests.server import Server, TestServerRequest, reactor
from tests.utils import must

from ..utils import Utils


def end(request: TestServerRequest, body: str) -> None:
    """Ends a held response from the test thread, like res.end(body)."""

    def finish() -> None:
        request.write(body.encode())
        request.finish()

    reactor.callFromThread(finish)


def wait_until(page: Page, predicate: Callable[[], bool]) -> None:
    """Lets the event loop run until the predicate holds. The sync port of awaiting
    a server-side event, such as server.waitForRequest()."""
    while not predicate():
        page.wait_for_timeout(10)


def test_FR_020_should_navigate_subframes_smoke(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/frames/one-frame.html")
    assert "/frames/one-frame.html" in page.frames[0].url
    assert "/frames/frame.html" in page.frames[1].url

    response = must(page.frames[1].goto(server.EMPTY_PAGE))
    assert response.ok is True
    assert response.frame == page.frames[1]


def test_FR_021_should_reject_when_frame_detaches(
    page: Page,
    server: Server,
    browser_name: str,
    sync_gather: Callable[..., List[Any]],
) -> None:
    page.goto(server.PREFIX + "/frames/one-frame.html")

    css_requests: List[TestServerRequest] = []
    server.set_route("/one-style.css", css_requests.append)

    def navigate() -> Error:
        with pytest.raises(Error) as exc_info:
            page.frames[1].goto(server.PREFIX + "/one-style.html")
        return exc_info.value

    def detach() -> None:
        wait_until(page, lambda: len(css_requests) > 0)
        page.eval_on_selector("iframe", "frame => frame.remove()")

    [error, _] = sync_gather(navigate, detach)
    if browser_name == "chromium":
        assert (
            "net::ERR_ABORTED" in error.message
            or "frame was detached" in error.message.lower()
        )
    else:
        assert "frame was detached" in error.message.lower()


def test_FR_022_should_continue_after_client_redirect(
    page: Page, server: Server, browser_name: str
) -> None:
    if browser_name == "firefox":
        pytest.skip("fixme: script.js is requested before navigationCommitted arrives")

    server.set_route("/frames/script.js", lambda request: None)
    url = server.PREFIX + "/frames/child-redirect.html"
    with pytest.raises(Error) as exc_info:
        page.goto(url, timeout=5000, wait_until="networkidle")
    assert "Page.goto: Timeout 5000ms exceeded." in exc_info.value.message
    assert (
        f'navigating to "{url}", waiting until "networkidle"' in exc_info.value.message
    )


def test_FR_023_should_return_matching_responses(
    page: Page, server: Server, utils: Utils, sync_gather: Callable[..., List[Any]]
) -> None:
    page.goto(server.EMPTY_PAGE)
    # Attach three frames.
    frames = [
        utils.attach_frame(page, "frame1", server.EMPTY_PAGE),
        utils.attach_frame(page, "frame2", server.EMPTY_PAGE),
        utils.attach_frame(page, "frame3", server.EMPTY_PAGE),
    ]
    server_responses: List[TestServerRequest] = []
    server.set_route("/0.html", server_responses.append)
    server.set_route("/1.html", server_responses.append)
    server.set_route("/2.html", server_responses.append)
    navigations: Dict[int, Response] = {}

    def navigate(i: int) -> Callable[[], None]:
        def action() -> None:
            # Start each navigation after the server got the previous one.
            wait_until(page, lambda: len(server_responses) == i)
            navigations[i] = must(
                frames[i].goto(server.PREFIX + "/" + str(i) + ".html")
            )

        return action

    def respond() -> None:
        wait_until(page, lambda: len(server_responses) == 3)
        # Respond from server out-of-order.
        server_response_texts = ["AAA", "BBB", "CCC"]
        for i in [1, 2, 0]:
            end(server_responses[i], server_response_texts[i])
            while i not in navigations:
                page.wait_for_timeout(10)
            response = navigations[i]
            assert response.frame == frames[i]
            assert response.text() == server_response_texts[i]

    sync_gather(navigate(0), navigate(1), navigate(2), respond)
