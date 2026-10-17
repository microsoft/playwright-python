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

import asyncio
import re
from typing import List, Optional

import pytest

from playwright.async_api import Error, Page
from tests.server import Server, TestServerRequest, reactor


def end_response(request: TestServerRequest, body: bytes = b"") -> None:
    """Ends a response that a route handler holds: upstream's response.end()."""

    def end() -> None:
        request.write(body)
        request.finish()

    reactor.callFromThread(end)


async def test_WA_110_should_work(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.evaluate(
        "url => window.location.href = url", server.PREFIX + "/grid.html"
    )
    await page.wait_for_url("**/grid.html")


@pytest.mark.xfail(
    reason="python: wait_for_url errors lack the 'Page.wait_for_url: ' prefix",
    strict=True,
)
async def test_WA_111_should_respect_timeout(page: Page, server: Server) -> None:
    error: Optional[Error] = None

    async def wait_for_url() -> None:
        nonlocal error
        try:
            await page.wait_for_url("**/frame.html", timeout=2500)
        except Error as e:
            error = e

    async def navigate() -> None:
        await page.goto(server.EMPTY_PAGE)

    await asyncio.gather(wait_for_url(), navigate())
    assert error
    assert "Page.wait_for_url: Timeout 2500ms exceeded." in error.message


async def test_WA_112_should_work_with_both_domcontentloaded_and_load(
    page: Page, server: Server
) -> None:
    responses: List[TestServerRequest] = []
    server.set_route("/one-style.css", responses.append)
    load_fired = False

    async def wait_for_load() -> None:
        nonlocal load_fired
        await page.wait_for_url("**/one-style.html", wait_until="load")
        load_fired = True

    async def wait_for_dom_content_loaded() -> None:
        await asyncio.gather(
            server.wait_for_request("/one-style.css"),
            page.wait_for_url("**/one-style.html", wait_until="domcontentloaded"),
        )
        both_fired = load_fired
        assert both_fired is False
        end_response(responses[0])

    async def navigate() -> None:
        await page.goto(server.PREFIX + "/one-style.html")

    await asyncio.gather(wait_for_load(), wait_for_dom_content_loaded(), navigate())
    assert load_fired is True


async def test_WA_113_should_work_with_commit(page: Page, server: Server) -> None:
    server.set_route("/script.js", lambda request: None)

    def handle_empty(request: TestServerRequest) -> None:
        request.setHeader("content-type", "text/html")
        request.write(b'<title>Hello</title><script src="script.js"></script>')
        request.finish()

    server.set_route("/empty.html", handle_empty)

    async def navigate() -> None:
        try:
            await page.goto(server.EMPTY_PAGE)
        except Error:
            pass

    async def wait_for_url() -> None:
        await page.wait_for_url("**/empty.html", wait_until="commit")
        assert await page.title() == "Hello"
        # The goto never ends: end it as the page fixture does after the upstream test.
        await page.close()

    await asyncio.gather(navigate(), wait_for_url())


async def test_WA_114_should_work_with_commit_and_about_blank(
    page: Page, server: Server
) -> None:
    await page.wait_for_url("about:blank", wait_until="commit")


async def test_WA_115_should_work_with_clicking_on_anchor_links(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<a href='#foobar'>foobar</a>")
    await page.click("a")
    await page.wait_for_url("**/*#foobar")


async def test_WA_116_should_work_with_history_push_state(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        """
    <a onclick='javascript:pushState()'>SPA</a>
    <script>
      function pushState() { history.pushState({}, '', 'wow.html') }
    </script>
  """
    )
    await page.click("a")
    await page.wait_for_url("**/wow.html")
    assert page.url == server.PREFIX + "/wow.html"


async def test_WA_117_should_work_with_history_replace_state(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        """
    <a onclick='javascript:replaceState()'>SPA</a>
    <script>
      function replaceState() { history.replaceState({}, '', '/replaced.html') }
    </script>
  """
    )
    await page.click("a")
    await page.wait_for_url("**/replaced.html")
    assert page.url == server.PREFIX + "/replaced.html"


async def test_WA_118_should_work_with_dom_history_back_history_forward(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
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

    await page.click("a#back")
    await page.wait_for_url("**/first.html")
    assert page.url == server.PREFIX + "/first.html"

    await page.click("a#forward")
    await page.wait_for_url("**/second.html")
    assert page.url == server.PREFIX + "/second.html"


async def test_WA_119_should_work_with_url_match_for_same_document_navigations(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    resolved = False

    async def wait_for_url() -> None:
        nonlocal resolved
        await page.wait_for_url(re.compile(r"third\.html"))
        resolved = True

    async def navigate() -> None:
        assert resolved is False
        await page.evaluate("() => { history.pushState({}, '', '/first.html'); }")
        assert resolved is False
        await page.evaluate("() => { history.pushState({}, '', '/second.html'); }")
        assert resolved is False
        await page.evaluate("() => { history.pushState({}, '', '/third.html'); }")

    await asyncio.gather(wait_for_url(), navigate())
    assert resolved is True


async def test_WA_120_should_work_on_frame(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/frames/one-frame.html")
    frame = page.frames[1]
    await frame.evaluate(
        "url => window.location.href = url", server.PREFIX + "/grid.html"
    )
    await frame.wait_for_url("**/grid.html")
