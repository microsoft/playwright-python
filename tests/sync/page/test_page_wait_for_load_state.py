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

"""Port of tests/page/page-wait-for-load-state.spec.ts."""

import traceback
from typing import Any, Callable, List

import pytest

from playwright.sync_api import Error, Page, Route
from tests.server import Server, TestServerRequest, reactor


def end_response(
    request: TestServerRequest, status: int = 200, body: bytes = b""
) -> None:
    """Ends a response that a route handler holds: upstream's response.end()."""

    def end() -> None:
        request.setResponseCode(status)
        request.write(body)
        request.finish()

    reactor.callFromThread(end)


def wait_until(page: Page, condition: Callable[[], bool]) -> None:
    """Runs the event loop until the condition holds: the sync stand-in for awaiting a promise."""
    while not condition():
        page.wait_for_timeout(10)


def test_WA_077_should_pick_up_ongoing_navigation(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    responses: List[TestServerRequest] = []
    server.set_route("/one-style.css", responses.append)
    page.goto(server.PREFIX + "/one-style.html", wait_until="domcontentloaded")
    # server.waitForRequest('/one-style.css')
    wait_until(page, lambda: len(responses) > 0)

    def wait() -> None:
        page.wait_for_load_state()

    def respond() -> None:
        end_response(responses[0], 404, b"Not found")

    sync_gather(wait, respond)


@pytest.mark.xfail(
    reason="python: wait_for_load_state errors lack the 'Page.wait_for_load_state: ' prefix",
    strict=True,
)
def test_WA_078_should_respect_timeout(page: Page, server: Server) -> None:
    server.set_route("/one-style.css", lambda request: None)
    page.goto(server.PREFIX + "/one-style.html", wait_until="domcontentloaded")
    with pytest.raises(Error) as exc_info:
        page.wait_for_load_state("load", timeout=1)
    assert "Page.wait_for_load_state: Timeout 1ms exceeded." in exc_info.value.message
    assert traceback.extract_tb(exc_info.tb)[0].filename == __file__


def test_WA_079_should_resolve_immediately_if_loaded(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/one-style.html")
    page.wait_for_load_state()


def test_WA_080_should_throw_for_bad_state(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/one-style.html")
    with pytest.raises(Error) as exc_info:
        page.wait_for_load_state("bad")  # type: ignore[arg-type]
    assert (
        "state: expected one of (load|domcontentloaded|networkidle|commit)"
        in exc_info.value.message
    )


def test_WA_081_should_resolve_immediately_if_load_state_matches(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    server.set_route("/one-style.css", lambda request: None)
    page.goto(server.PREFIX + "/one-style.html", wait_until="domcontentloaded")
    page.wait_for_load_state("domcontentloaded")


def test_WA_082_should_work_with_pages_that_have_loaded_before_being_connected_to(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    with page.expect_popup() as popup_info:
        page.evaluate("() => window['_popup'] = window.open(document.location.href)")
    popup = popup_info.value
    # The url is about:blank in FF.
    # assert popup.url == server.EMPTY_PAGE
    popup.wait_for_load_state()
    assert popup.url == server.EMPTY_PAGE


def test_WA_083_should_wait_for_load_state_of_empty_url_popup(
    page: Page, browser_name: str, browser_major_version: int
) -> None:
    with page.expect_popup() as popup_info:
        ready_state = page.evaluate(
            """() => {
                const popup = window.open('');
                return popup.document.readyState;
            }"""
        )
    popup = popup_info.value
    popup.wait_for_load_state()
    is_old_firefox = browser_name == "firefox" and browser_major_version < 148
    expected = "uninitialized" if is_old_firefox else "complete"
    assert ready_state == expected
    assert popup.evaluate("() => document.readyState") == expected


def test_WA_084_should_wait_for_load_state_of_about_blank_popup(
    page: Page,
) -> None:
    with page.expect_popup() as popup_info:
        page.evaluate("() => window.open('about:blank') && 1")
    popup = popup_info.value
    popup.wait_for_load_state()
    assert popup.evaluate("() => document.readyState") == "complete"


def test_WA_085_should_wait_for_load_state_of_about_blank_popup_with_noopener(
    page: Page,
) -> None:
    with page.expect_popup() as popup_info:
        page.evaluate("() => window.open('about:blank', null, 'noopener') && 1")
    popup = popup_info.value
    popup.wait_for_load_state()
    assert popup.evaluate("() => document.readyState") == "complete"


def test_WA_086_should_wait_for_load_state_of_popup_with_network_url(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    with page.expect_popup() as popup_info:
        page.evaluate("url => window.open(url) && 1", server.EMPTY_PAGE)
    popup = popup_info.value
    popup.wait_for_load_state()
    assert popup.evaluate("() => document.readyState") == "complete"


def test_WA_087_should_wait_for_load_state_of_popup_with_network_url_and_noopener(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    with page.expect_popup() as popup_info:
        page.evaluate(
            "url => window.open(url, null, 'noopener') && 1", server.EMPTY_PAGE
        )
    popup = popup_info.value
    popup.wait_for_load_state()
    assert popup.evaluate("() => document.readyState") == "complete"


def test_WA_088_should_work_with_clicking_target_blank(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content('<a target=_blank rel="opener" href="/one-style.html">yo</a>')
    with page.expect_popup() as popup_info:
        page.click("a")
    popup = popup_info.value
    popup.wait_for_load_state()
    assert popup.evaluate("() => document.readyState") == "complete"


def test_WA_089_should_wait_for_load_state_of_new_page(page: Page) -> None:
    with page.context.expect_page() as new_page_info:
        page.context.new_page()
    new_page = new_page_info.value
    new_page.wait_for_load_state()
    assert new_page.evaluate("() => document.readyState") == "complete"


def test_WA_090_should_resolve_after_popup_load(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    page.goto(server.EMPTY_PAGE)
    # Stall the 'load' by delaying css.
    css_responses: List[TestServerRequest] = []
    server.set_route("/one-style.css", css_responses.append)
    with page.expect_popup() as popup_info:
        page.evaluate(
            "url => window['popup'] = window.open(url)",
            server.PREFIX + "/one-style.html",
        )
        # server.waitForRequest('/one-style.css')
        wait_until(page, lambda: len(css_responses) > 0)
    popup = popup_info.value
    resolved = False

    def wait_for_load_state() -> None:
        nonlocal resolved
        popup.wait_for_load_state()
        resolved = True

    def respond() -> None:
        # Round trips!
        for _ in range(5):
            page.evaluate("window")
        assert resolved is False
        end_response(css_responses[0])

    sync_gather(wait_for_load_state, respond)
    assert resolved is True
    assert popup.url == server.PREFIX + "/one-style.html"


def test_WA_091_should_work_for_frame(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    page.goto(server.PREFIX + "/frames/one-frame.html")
    frame = page.frames[1]

    routes: List[Route] = []
    page.route(server.PREFIX + "/one-style.css", lambda route: routes.append(route))
    frame.goto(server.PREFIX + "/one-style.html", wait_until="domcontentloaded")
    wait_until(page, lambda: len(routes) > 0)
    request = routes[0]
    resolved = False

    def wait_for_load_state() -> None:
        nonlocal resolved
        frame.wait_for_load_state()
        resolved = True

    def continue_request() -> None:
        # give the promise a chance to resolve, even though it shouldn't
        page.evaluate("1")
        assert resolved is False
        request.continue_()

    sync_gather(wait_for_load_state, continue_request)


def test_WA_092_should_work_with_javascript_iframe(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content('<iframe src="javascript:false"></iframe>', wait_until="commit")
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_load_state("load")
    page.wait_for_load_state("networkidle")


def test_WA_093_should_work_with_broken_data_url_iframe(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content('<iframe src="data:text/html"></iframe>', wait_until="commit")
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_load_state("load")
    page.wait_for_load_state("networkidle")


def test_WA_094_should_work_with_broken_blob_url_iframe(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content('<iframe src="blob:"></iframe>', wait_until="commit")
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_load_state("load")
    page.wait_for_load_state("networkidle")
