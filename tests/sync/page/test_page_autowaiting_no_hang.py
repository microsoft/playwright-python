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

"""Port of tests/page/page-autowaiting-no-hang.spec.ts."""

import threading
from typing import Any, Callable, List
from urllib.parse import urlparse

from playwright.sync_api import Error, Page, expect
from tests.server import Server, TestServerRequest, reactor


def ignore_errors(action: Callable[[], Any]) -> None:
    """Like `promise.catch(() => {})`."""
    try:
        action()
    except Error:
        pass


class StalledRoute:
    """Port of the `/stall.html` routes of this file.

    Holds each request until release() is called, then passes it to `action`.
    Like the upstream handler, which awaits a promise, a request that arrives after
    the release (for example a retry by the browser) gets the action at once.
    """

    def __init__(
        self,
        server: Server,
        path: str,
        action: Callable[[TestServerRequest], None],
    ) -> None:
        # Set when the first request arrives, like `stallPromise`.
        self._stalled = threading.Event()
        self._action = action
        self._released = False
        self._held: List[TestServerRequest] = []
        server.set_route(path, self._handle)

    def _handle(self, request: TestServerRequest) -> None:
        # Runs on the server thread.
        self._stalled.set()
        if self._released:
            self._action(request)
        else:
            self._held.append(request)

    def wait(self, page: Page) -> None:
        """Like `await stallPromise`. Polls, so that the sync API keeps dispatching."""
        while not self._stalled.is_set():
            page.wait_for_timeout(10)

    def release(self) -> None:
        def run() -> None:
            self._released = True
            for request in self._held:
                self._action(request)

        reactor.callFromThread(run)


def destroy(request: TestServerRequest) -> None:
    """Like `req.socket.destroy()`."""
    assert request.transport
    request.transport.abortConnection()


def respond_hello_world(request: TestServerRequest) -> None:
    request.setResponseCode(200)
    request.setHeader("Content-Type", "text/html")
    request.write(b"hello world")
    try:
        request.finish()
    except RuntimeError:
        # The browser has dropped the request. Like res.end() in Node.js, do nothing.
        pass


def test_AW_013_clicking_on_links_which_do_not_commit_navigation(
    page: Page, server: Server, https_server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content(f"<a href='{https_server.EMPTY_PAGE}'>foobar</a>")
    page.click("a")


def test_AW_014_calling_window_stop_async(page: Page, server: Server) -> None:
    server.set_route("/empty.html", lambda request: None)
    page.evaluate(
        """url => {
    window.location.href = url;
    setTimeout(() => window.stop(), 100);
  }""",
        server.EMPTY_PAGE,
    )


def test_AW_015_calling_window_stop_sync(page: Page, server: Server) -> None:
    page.evaluate(
        """url => {
    window.location.href = url;
    window.stop();
  }""",
        server.EMPTY_PAGE,
    )


def test_AW_016_assigning_location_to_about_blank(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    page.evaluate('window.location.href = "about:blank";')


def test_AW_017_assigning_location_to_about_blank_after_non_about_blank(
    page: Page, server: Server
) -> None:
    server.set_route("/empty.html", lambda request: None)
    page.evaluate(
        f"""
      window.location.href = "{server.EMPTY_PAGE}";
      window.location.href = "about:blank";"""
    )


def test_AW_018_calling_window_open_and_window_close(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    page.evaluate(
        """() => {
    const popup = window.open(window.location.href);
    popup.close();
  }"""
    )


def test_AW_019_opening_a_popup(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    with page.expect_event("popup"):
        page.evaluate("() => window.open(window.location.href) && 1")


def test_AW_020_clicking_in_the_middle_of_navigation_that_aborts(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    stall = StalledRoute(server, "/stall.html", destroy)

    page.goto(server.PREFIX + "/one-style.html")

    def navigate() -> None:
        ignore_errors(lambda: page.goto(server.PREFIX + "/stall.html"))

    def click() -> None:
        stall.wait(page)
        page.click("body")

    def abort_later() -> None:
        stall.wait(page)
        page.wait_for_timeout(1000)
        stall.release()

    sync_gather(navigate, click, abort_later)


def test_AW_021_clicking_in_the_middle_of_navigation_that_commits(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    stall = StalledRoute(server, "/stall.html", respond_hello_world)

    page.goto(server.PREFIX + "/one-style.html")

    def navigate() -> None:
        ignore_errors(lambda: page.goto(server.PREFIX + "/stall.html"))

    def click() -> None:
        stall.wait(page)
        page.click("body")

    def commit_later() -> None:
        stall.wait(page)
        page.wait_for_timeout(1000)
        stall.release()

    sync_gather(navigate, click, commit_later)
    expect(page.locator("body")).to_contain_text("hello world")


def test_AW_022_clicking_a_link_intercepted_by_the_navigation_api_same_document(
    page: Page, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/41125
    def handler(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("Content-Type", "text/html")
        request.write(
            b"""
      <a id="go" href="/other">go</a>
      <p id="status">initial</p>
      <script>
        navigation.addEventListener('navigate', event => {
          if (!event.canIntercept)
            return;
          event.intercept({
            handler: async () => {
              const dest = new URL(event.destination.url).pathname;
              document.getElementById('status').textContent = 'intercepted:' + dest;
            },
          });
        });
      </script>
    """
        )
        request.finish()

    server.set_route("/intercept.html", handler)

    page.goto(server.PREFIX + "/intercept.html")
    expect(page.locator("#status")).to_have_text("initial")

    # Should not hang waiting for the same-document navigation to commit.
    page.locator("#go").click()

    expect(page.locator("#status")).to_have_text("intercepted:/other")
    assert urlparse(page.url).path == "/other"


def test_AW_023_go_back_in_the_middle_of_navigation_that_commits(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    stall = StalledRoute(server, "/stall.html", respond_hello_world)

    page.goto(server.PREFIX + "/one-style.html")

    def navigate() -> None:
        ignore_errors(lambda: page.goto(server.PREFIX + "/stall.html"))

    def go_back() -> None:
        stall.wait(page)
        ignore_errors(page.go_back)

    def commit_later() -> None:
        stall.wait(page)
        page.wait_for_timeout(1000)
        stall.release()

    sync_gather(navigate, go_back, commit_later)
