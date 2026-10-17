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

"""Port of tests/page/page-wait-for-url.spec.ts."""

import re
from typing import Any, Callable, List, Optional

import pytest

from playwright.sync_api import Error, Page
from tests.server import Server, TestServerRequest, reactor


def end_response(request: TestServerRequest, body: bytes = b"") -> None:
    """Ends a response that a route handler holds: upstream's response.end()."""

    def end() -> None:
        request.write(body)
        request.finish()

    reactor.callFromThread(end)


def wait_until(page: Page, condition: Callable[[], bool]) -> None:
    """Runs the event loop until the condition holds: the sync stand-in for awaiting a promise."""
    while not condition():
        page.wait_for_timeout(10)


def test_WA_110_should_work(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    page.evaluate("url => window.location.href = url", server.PREFIX + "/grid.html")
    page.wait_for_url("**/grid.html")


@pytest.mark.xfail(
    reason="python: wait_for_url errors lack the 'Page.wait_for_url: ' prefix",
    strict=True,
)
def test_WA_111_should_respect_timeout(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    error: Optional[Error] = None

    def wait_for_url() -> None:
        nonlocal error
        try:
            page.wait_for_url("**/frame.html", timeout=2500)
        except Error as e:
            error = e

    def navigate() -> None:
        page.goto(server.EMPTY_PAGE)

    sync_gather(wait_for_url, navigate)
    assert error
    assert "Page.wait_for_url: Timeout 2500ms exceeded." in error.message


def test_WA_112_should_work_with_both_domcontentloaded_and_load(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    responses: List[TestServerRequest] = []
    server.set_route("/one-style.css", responses.append)
    load_fired = False

    def wait_for_load() -> None:
        nonlocal load_fired
        page.wait_for_url("**/one-style.html", wait_until="load")
        load_fired = True

    def wait_for_dom_content_loaded() -> None:
        page.wait_for_url("**/one-style.html", wait_until="domcontentloaded")
        # server.waitForRequest('/one-style.css')
        wait_until(page, lambda: len(responses) > 0)
        both_fired = load_fired
        assert both_fired is False
        end_response(responses[0])

    def navigate() -> None:
        page.goto(server.PREFIX + "/one-style.html")

    sync_gather(wait_for_load, wait_for_dom_content_loaded, navigate)
    assert load_fired is True


def test_WA_113_should_work_with_commit(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    server.set_route("/script.js", lambda request: None)

    def handle_empty(request: TestServerRequest) -> None:
        request.setHeader("content-type", "text/html")
        request.write(b'<title>Hello</title><script src="script.js"></script>')
        request.finish()

    server.set_route("/empty.html", handle_empty)

    def navigate() -> None:
        try:
            page.goto(server.EMPTY_PAGE)
        except Error:
            pass

    def wait_for_url() -> None:
        page.wait_for_url("**/empty.html", wait_until="commit")
        assert page.title() == "Hello"
        # The goto never ends: end it as the page fixture does after the upstream test.
        page.close()

    sync_gather(navigate, wait_for_url)


def test_WA_114_should_work_with_commit_and_about_blank(
    page: Page, server: Server
) -> None:
    page.wait_for_url("about:blank", wait_until="commit")


def test_WA_115_should_work_with_clicking_on_anchor_links(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content("<a href='#foobar'>foobar</a>")
    page.click("a")
    page.wait_for_url("**/*#foobar")


def test_WA_116_should_work_with_history_push_state(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content(
        """
    <a onclick='javascript:pushState()'>SPA</a>
    <script>
      function pushState() { history.pushState({}, '', 'wow.html') }
    </script>
  """
    )
    page.click("a")
    page.wait_for_url("**/wow.html")
    assert page.url == server.PREFIX + "/wow.html"


def test_WA_117_should_work_with_history_replace_state(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content(
        """
    <a onclick='javascript:replaceState()'>SPA</a>
    <script>
      function replaceState() { history.replaceState({}, '', '/replaced.html') }
    </script>
  """
    )
    page.click("a")
    page.wait_for_url("**/replaced.html")
    assert page.url == server.PREFIX + "/replaced.html"


def test_WA_118_should_work_with_dom_history_back_history_forward(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content(
        """
    <a id=back onclick='javascript:goBack()'>back</a>
    <a id=forward onclick='javascript:goForward()'>forward</a>
    <script>
      function goBack() { history.back(); }
      function goForward() { history.forward(); }
      history.pushState({}, '', '/first.html');
      history.pushState({}, '', '/second.html');
    </script>
  """
    )
    assert page.url == server.PREFIX + "/second.html"

    page.click("a#back")
    page.wait_for_url("**/first.html")
    assert page.url == server.PREFIX + "/first.html"

    page.click("a#forward")
    page.wait_for_url("**/second.html")
    assert page.url == server.PREFIX + "/second.html"


def test_WA_119_should_work_with_url_match_for_same_document_navigations(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    page.goto(server.EMPTY_PAGE)
    resolved = False

    def wait_for_url() -> None:
        nonlocal resolved
        page.wait_for_url(re.compile(r"third\.html"))
        resolved = True

    def navigate() -> None:
        assert resolved is False
        page.evaluate("() => { history.pushState({}, '', '/first.html'); }")
        assert resolved is False
        page.evaluate("() => { history.pushState({}, '', '/second.html'); }")
        assert resolved is False
        page.evaluate("() => { history.pushState({}, '', '/third.html'); }")

    sync_gather(wait_for_url, navigate)
    assert resolved is True


def test_WA_120_should_work_on_frame(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/frames/one-frame.html")
    frame = page.frames[1]
    frame.evaluate("url => window.location.href = url", server.PREFIX + "/grid.html")
    frame.wait_for_url("**/grid.html")
