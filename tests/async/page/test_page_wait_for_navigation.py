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

"""Port of tests/page/page-wait-for-navigation.spec.ts."""

import asyncio
import re
from typing import List, Optional
from urllib.parse import parse_qs, urlparse

import pytest

from playwright.async_api import Error, Frame, Page
from tests.server import Server, TestServerRequest, reactor
from tests.utils import expected_ssl_error


def end_response(request: TestServerRequest, body: bytes = b"") -> None:
    """Ends a response that a route handler holds: upstream's response.end()."""

    def end() -> None:
        request.write(body)
        request.finish()

    reactor.callFromThread(end)


async def test_WA_095_should_work(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_navigation() as response_info:
        await page.evaluate(
            "url => window.location.href = url", server.PREFIX + "/grid.html"
        )
    response = await response_info.value
    assert response
    assert response.ok is True
    assert "grid.html" in response.url


@pytest.mark.xfail(
    reason="python: expect_navigation errors lack the 'Page.expect_navigation: ' prefix "
    "and log until 'load' instead of until \"load\"",
    strict=True,
)
async def test_WA_096_should_respect_timeout(page: Page, server: Server) -> None:
    error: Optional[Error] = None

    async def wait_for_navigation() -> None:
        nonlocal error
        try:
            async with page.expect_navigation(url="**/frame.html", timeout=5000):
                pass
        except Error as e:
            error = e

    async def navigate() -> None:
        await page.goto(server.EMPTY_PAGE)

    await asyncio.gather(wait_for_navigation(), navigate())
    assert error
    assert "Page.expect_navigation: Timeout 5000ms exceeded." in error.message
    assert 'waiting for navigation to "**/frame.html" until "load"' in error.message
    assert f'navigated to "{server.EMPTY_PAGE}"' in error.message


async def test_WA_097_should_work_with_both_domcontentloaded_and_load(
    page: Page, server: Server
) -> None:
    responses: List[TestServerRequest] = []
    server.set_route("/one-style.css", responses.append)

    async def navigate() -> None:
        await page.goto(server.PREFIX + "/one-style.html")

    async def wait_for_navigations() -> None:
        async with page.expect_navigation(
            wait_until="domcontentloaded"
        ) as dom_content_loaded_info:
            async with page.expect_navigation(wait_until="load") as load_info:
                await server.wait_for_request("/one-style.css")
                await dom_content_loaded_info.value
                both_fired = load_info.is_done() and dom_content_loaded_info.is_done()
                assert both_fired is False
                end_response(responses[0])

    await asyncio.gather(wait_for_navigations(), navigate())


async def test_WA_098_should_work_with_commit(page: Page, server: Server) -> None:
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

    async def wait_for_navigation() -> None:
        async with page.expect_navigation(wait_until="commit"):
            pass
        assert await page.title() == "Hello"
        # The goto never ends: end it as the page fixture does after the upstream test.
        await page.close()

    await asyncio.gather(navigate(), wait_for_navigation())


async def test_WA_099_should_work_with_clicking_on_anchor_links(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<a href='#foobar'>foobar</a>")
    async with page.expect_navigation() as response_info:
        await page.click("a")
    assert await response_info.value is None
    assert page.url == server.EMPTY_PAGE + "#foobar"


async def test_WA_100_should_work_with_clicking_on_links_which_do_not_commit_navigation(
    page: Page,
    server: Server,
    https_server: Server,
    browser_name: str,
    platform: str,
    browser_channel: Optional[str],
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(f"<a href='{https_server.EMPTY_PAGE}'>foobar</a>")
    with pytest.raises(Error) as exc_info:
        async with page.expect_navigation():
            await page.click("a")
    assert re.search(
        expected_ssl_error(browser_name, platform, browser_channel),
        exc_info.value.message,
    )


async def test_WA_101_should_work_with_history_push_state(
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
    async with page.expect_navigation() as response_info:
        await page.click("a")
    assert await response_info.value is None
    assert page.url == server.PREFIX + "/wow.html"


async def test_WA_102_should_work_with_history_replace_state(
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
    async with page.expect_navigation() as response_info:
        await page.click("a")
    assert await response_info.value is None
    assert page.url == server.PREFIX + "/replaced.html"


async def test_WA_103_should_work_with_dom_history_back_history_forward(
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
    async with page.expect_navigation() as back_response_info:
        await page.click("a#back")
    assert await back_response_info.value is None
    assert page.url == server.PREFIX + "/first.html"
    async with page.expect_navigation() as forward_response_info:
        await page.click("a#forward")
    assert await forward_response_info.value is None
    assert page.url == server.PREFIX + "/second.html"


async def test_WA_104_should_work_when_subframe_issues_window_stop(
    browser_name: str, page: Page, server: Server
) -> None:
    if browser_name == "webkit":
        pytest.skip("fixme: WebKit issues load event in some cases, but not always")

    server.set_route("/frames/style.css", lambda request: None)
    done = False

    async def navigate() -> None:
        nonlocal done
        try:
            await page.goto(server.PREFIX + "/frames/one-frame.html")
            done = True
        except Error:
            pass

    async def stop() -> None:
        frame: Frame = await page.wait_for_event("frameattached")
        await page.wait_for_event("framenavigated", lambda f: f == frame)
        await frame.evaluate("() => window.stop()")
        assert done is True

    await asyncio.gather(navigate(), stop())


async def test_WA_105_should_work_with_url_match(page: Page, server: Server) -> None:
    async with page.expect_navigation(
        url=re.compile(r"one-style\.html")
    ) as response1_info:
        async with page.expect_navigation(
            url=re.compile(r"\/frame.html")
        ) as response2_info:
            async with page.expect_navigation(
                url=lambda url: parse_qs(urlparse(url).query).get("foo") == ["bar"]
            ) as response3_info:
                assert not response1_info.is_done()
                assert not response2_info.is_done()
                assert not response3_info.is_done()
                await page.goto(server.EMPTY_PAGE)
                assert not response1_info.is_done()
                assert not response2_info.is_done()
                assert not response3_info.is_done()
                await page.goto(server.PREFIX + "/frame.html")
                assert not response1_info.is_done()
                response2 = await response2_info.value
                assert response2 is not None
                assert not response3_info.is_done()
                await page.goto(server.PREFIX + "/one-style.html")
                response1 = await response1_info.value
                assert response1 is not None
                assert response2 is not None
                assert not response3_info.is_done()
                await page.goto(server.PREFIX + "/frame.html?foo=bar")
                response3 = await response3_info.value
                assert response1 is not None
                assert response2 is not None
                assert response3 is not None
                await page.goto(server.PREFIX + "/empty.html")
                assert response1.url == server.PREFIX + "/one-style.html"
                assert response2.url == server.PREFIX + "/frame.html"
                assert response3.url == server.PREFIX + "/frame.html?foo=bar"


async def test_WA_106_should_work_with_url_match_for_same_document_navigations(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_navigation(url=re.compile(r"third\.html")) as wait_info:
        assert not wait_info.is_done()
        await page.evaluate("() => { history.pushState({}, '', '/first.html'); }")
        assert not wait_info.is_done()
        await page.evaluate("() => { history.pushState({}, '', '/second.html'); }")
        assert not wait_info.is_done()
        await page.evaluate("() => { history.pushState({}, '', '/third.html'); }")
        await wait_info.value
        assert wait_info.is_done()


async def test_WA_107_should_work_for_cross_process_navigations(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    url = server.CROSS_PROCESS_PREFIX + "/empty.html"

    async def wait_for_navigation() -> None:
        async with page.expect_navigation(
            wait_until="domcontentloaded"
        ) as response_info:
            pass
        response = await response_info.value
        assert response
        assert response.url == url
        assert page.url == url
        assert await page.evaluate("document.location.href") == url

    async def navigate() -> None:
        await page.goto(url)

    await asyncio.gather(wait_for_navigation(), navigate())


async def test_WA_108_should_work_on_frame(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/frames/one-frame.html")
    frame = page.frames[1]
    async with frame.expect_navigation() as response_info:
        await frame.evaluate(
            "url => window.location.href = url", server.PREFIX + "/grid.html"
        )
    response = await response_info.value
    assert response
    assert response.ok is True
    assert "grid.html" in response.url
    assert response.frame == frame
    assert "/frames/one-frame.html" in page.url


@pytest.mark.xfail(
    reason="python: after the commit, expect_navigation waits for the load state with a "
    "new waiter, so the error loses the 'waiting for navigation until \"load\"' log",
    strict=True,
)
async def test_WA_109_should_fail_when_frame_detaches(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/frames/one-frame.html")
    frame = page.frames[1]
    server.set_route("/empty.html", lambda request: None)
    server.set_route("/one-style.css", lambda request: None)
    error: Optional[Error] = None

    async def wait_for_navigation() -> None:
        nonlocal error
        try:
            async with frame.expect_navigation():
                pass
        except Error as e:
            error = e

    async def navigate() -> None:
        await page.eval_on_selector(
            "iframe",
            "frame => { frame.contentWindow.location.href = '/one-style.html'; }",
        )

    async def remove_frame() -> None:
        # Make sure policy checks pass and navigation actually begins before removing the frame to avoid other errors
        await server.wait_for_request("/one-style.css")
        await page.eval_on_selector(
            "iframe", "frame => window.builtins.setTimeout(() => frame.remove(), 0)"
        )

    await asyncio.gather(wait_for_navigation(), navigate(), remove_frame())
    assert error
    assert 'waiting for navigation until "load"' in error.message
    assert "frame was detached" in error.message
