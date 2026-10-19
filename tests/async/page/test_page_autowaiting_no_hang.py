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

import asyncio
from typing import Any, Awaitable, Callable, List
from urllib.parse import urlparse

from playwright.async_api import Error, Page, expect
from tests.server import Server, TestServerRequest, reactor


async def ignore_errors(action: Awaitable[Any]) -> None:
    """Like `promise.catch(() => {})`."""
    try:
        await action
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
        self._loop = asyncio.get_running_loop()
        # Resolves when the first request arrives, like `stallPromise`.
        self.stalled: "asyncio.Future[None]" = self._loop.create_future()
        self._action = action
        self._released = False
        self._held: List[TestServerRequest] = []
        server.set_route(path, self._handle)

    def _handle(self, request: TestServerRequest) -> None:
        # Runs on the server thread.
        self._loop.call_soon_threadsafe(self._notify_stalled)
        if self._released:
            self._action(request)
        else:
            self._held.append(request)

    def _notify_stalled(self) -> None:
        if not self.stalled.done():
            self.stalled.set_result(None)

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


async def test_AW_013_clicking_on_links_which_do_not_commit_navigation(
    page: Page, server: Server, https_server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(f"<a href='{https_server.EMPTY_PAGE}'>foobar</a>")
    await page.click("a")


async def test_AW_014_calling_window_stop_async(page: Page, server: Server) -> None:
    server.set_route("/empty.html", lambda request: None)
    await page.evaluate(
        """url => {
    window.location.href = url;
    setTimeout(() => window.stop(), 100);
  }""",
        server.EMPTY_PAGE,
    )


async def test_AW_015_calling_window_stop_sync(page: Page, server: Server) -> None:
    await page.evaluate(
        """url => {
    window.location.href = url;
    window.stop();
  }""",
        server.EMPTY_PAGE,
    )


async def test_AW_016_assigning_location_to_about_blank(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.evaluate('window.location.href = "about:blank";')


async def test_AW_017_assigning_location_to_about_blank_after_non_about_blank(
    page: Page, server: Server
) -> None:
    server.set_route("/empty.html", lambda request: None)
    await page.evaluate(
        f"""
      window.location.href = "{server.EMPTY_PAGE}";
      window.location.href = "about:blank";"""
    )


async def test_AW_018_calling_window_open_and_window_close(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.evaluate(
        """() => {
    const popup = window.open(window.location.href);
    popup.close();
  }"""
    )


async def test_AW_019_opening_a_popup(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_event("popup"):
        await page.evaluate("() => window.open(window.location.href) && 1")


async def test_AW_020_clicking_in_the_middle_of_navigation_that_aborts(
    page: Page, server: Server
) -> None:
    stall = StalledRoute(server, "/stall.html", destroy)

    await page.goto(server.PREFIX + "/one-style.html")
    asyncio.create_task(ignore_errors(page.goto(server.PREFIX + "/stall.html")))
    await stall.stalled

    click_task = asyncio.create_task(page.click("body"))
    await page.wait_for_timeout(1000)
    stall.release()

    await click_task


async def test_AW_021_clicking_in_the_middle_of_navigation_that_commits(
    page: Page, server: Server
) -> None:
    stall = StalledRoute(server, "/stall.html", respond_hello_world)

    await page.goto(server.PREFIX + "/one-style.html")
    asyncio.create_task(ignore_errors(page.goto(server.PREFIX + "/stall.html")))
    await stall.stalled

    click_task = asyncio.create_task(page.click("body"))
    await page.wait_for_timeout(1000)
    stall.release()

    await click_task
    await expect(page.locator("body")).to_contain_text("hello world")


async def test_AW_022_clicking_a_link_intercepted_by_the_navigation_api_same_document(
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

    await page.goto(server.PREFIX + "/intercept.html")
    await expect(page.locator("#status")).to_have_text("initial")

    # Should not hang waiting for the same-document navigation to commit.
    await page.locator("#go").click()

    await expect(page.locator("#status")).to_have_text("intercepted:/other")
    assert urlparse(page.url).path == "/other"


async def test_AW_023_go_back_in_the_middle_of_navigation_that_commits(
    page: Page, server: Server
) -> None:
    stall = StalledRoute(server, "/stall.html", respond_hello_world)

    await page.goto(server.PREFIX + "/one-style.html")
    asyncio.create_task(ignore_errors(page.goto(server.PREFIX + "/stall.html")))
    await stall.stalled

    go_back_task = asyncio.create_task(ignore_errors(page.go_back()))
    await page.wait_for_timeout(1000)
    stall.release()

    await go_back_task
