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

import asyncio
import traceback
from typing import List

import pytest

from playwright.async_api import Error, Page, Route
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


async def test_WA_077_should_pick_up_ongoing_navigation(
    page: Page, server: Server
) -> None:
    responses: List[TestServerRequest] = []
    server.set_route("/one-style.css", responses.append)
    await asyncio.gather(
        server.wait_for_request("/one-style.css"),
        page.goto(server.PREFIX + "/one-style.html", wait_until="domcontentloaded"),
    )

    async def wait() -> None:
        await page.wait_for_load_state()

    async def respond() -> None:
        end_response(responses[0], 404, b"Not found")

    await asyncio.gather(wait(), respond())


@pytest.mark.xfail(
    reason="python: wait_for_load_state errors lack the 'Page.wait_for_load_state: ' prefix",
    strict=True,
)
async def test_WA_078_should_respect_timeout(page: Page, server: Server) -> None:
    server.set_route("/one-style.css", lambda request: None)
    await page.goto(server.PREFIX + "/one-style.html", wait_until="domcontentloaded")
    with pytest.raises(Error) as exc_info:
        await page.wait_for_load_state("load", timeout=1)
    assert "Page.wait_for_load_state: Timeout 1ms exceeded." in exc_info.value.message
    assert traceback.extract_tb(exc_info.tb)[0].filename == __file__


async def test_WA_079_should_resolve_immediately_if_loaded(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/one-style.html")
    await page.wait_for_load_state()


async def test_WA_080_should_throw_for_bad_state(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/one-style.html")
    with pytest.raises(Error) as exc_info:
        await page.wait_for_load_state("bad")  # type: ignore[arg-type]
    assert (
        "state: expected one of (load|domcontentloaded|networkidle|commit)"
        in exc_info.value.message
    )


async def test_WA_081_should_resolve_immediately_if_load_state_matches(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    server.set_route("/one-style.css", lambda request: None)
    await page.goto(server.PREFIX + "/one-style.html", wait_until="domcontentloaded")
    await page.wait_for_load_state("domcontentloaded")


async def test_WA_082_should_work_with_pages_that_have_loaded_before_being_connected_to(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_popup() as popup_info:
        await page.evaluate(
            "() => window['_popup'] = window.open(document.location.href)"
        )
    popup = await popup_info.value
    # The url is about:blank in FF.
    # assert popup.url == server.EMPTY_PAGE
    await popup.wait_for_load_state()
    assert popup.url == server.EMPTY_PAGE


async def test_WA_083_should_wait_for_load_state_of_empty_url_popup(
    page: Page, browser_name: str, browser_major_version: int
) -> None:
    async with page.expect_popup() as popup_info:
        ready_state = await page.evaluate(
            """() => {
                const popup = window.open('');
                return popup.document.readyState;
            }"""
        )
    popup = await popup_info.value
    await popup.wait_for_load_state()
    is_old_firefox = browser_name == "firefox" and browser_major_version < 148
    expected = "uninitialized" if is_old_firefox else "complete"
    assert ready_state == expected
    assert await popup.evaluate("() => document.readyState") == expected


async def test_WA_084_should_wait_for_load_state_of_about_blank_popup(
    page: Page,
) -> None:
    async with page.expect_popup() as popup_info:
        await page.evaluate("() => window.open('about:blank') && 1")
    popup = await popup_info.value
    await popup.wait_for_load_state()
    assert await popup.evaluate("() => document.readyState") == "complete"


async def test_WA_085_should_wait_for_load_state_of_about_blank_popup_with_noopener(
    page: Page,
) -> None:
    async with page.expect_popup() as popup_info:
        await page.evaluate("() => window.open('about:blank', null, 'noopener') && 1")
    popup = await popup_info.value
    await popup.wait_for_load_state()
    assert await popup.evaluate("() => document.readyState") == "complete"


async def test_WA_086_should_wait_for_load_state_of_popup_with_network_url(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_popup() as popup_info:
        await page.evaluate("url => window.open(url) && 1", server.EMPTY_PAGE)
    popup = await popup_info.value
    await popup.wait_for_load_state()
    assert await popup.evaluate("() => document.readyState") == "complete"


async def test_WA_087_should_wait_for_load_state_of_popup_with_network_url_and_noopener(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_popup() as popup_info:
        await page.evaluate(
            "url => window.open(url, null, 'noopener') && 1", server.EMPTY_PAGE
        )
    popup = await popup_info.value
    await popup.wait_for_load_state()
    assert await popup.evaluate("() => document.readyState") == "complete"


async def test_WA_088_should_work_with_clicking_target_blank(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        '<a target=_blank rel="opener" href="/one-style.html">yo</a>'
    )
    async with page.expect_popup() as popup_info:
        await page.click("a")
    popup = await popup_info.value
    await popup.wait_for_load_state()
    assert await popup.evaluate("() => document.readyState") == "complete"


async def test_WA_089_should_wait_for_load_state_of_new_page(page: Page) -> None:
    async with page.context.expect_page() as new_page_info:
        await page.context.new_page()
    new_page = await new_page_info.value
    await new_page.wait_for_load_state()
    assert await new_page.evaluate("() => document.readyState") == "complete"


async def test_WA_090_should_resolve_after_popup_load(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    # Stall the 'load' by delaying css.
    css_responses: List[TestServerRequest] = []
    server.set_route("/one-style.css", css_responses.append)
    async with page.expect_popup() as popup_info:
        await asyncio.gather(
            server.wait_for_request("/one-style.css"),
            page.evaluate(
                "url => window['popup'] = window.open(url)",
                server.PREFIX + "/one-style.html",
            ),
        )
    popup = await popup_info.value
    resolved = False

    async def wait_for_load_state() -> None:
        nonlocal resolved
        await popup.wait_for_load_state()
        resolved = True

    async def respond() -> None:
        # Round trips!
        for _ in range(5):
            await page.evaluate("window")
        assert resolved is False
        end_response(css_responses[0])

    await asyncio.gather(wait_for_load_state(), respond())
    assert resolved is True
    assert popup.url == server.PREFIX + "/one-style.html"


async def test_WA_091_should_work_for_frame(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/frames/one-frame.html")
    frame = page.frames[1]

    route_future: "asyncio.Future[Route]" = asyncio.get_running_loop().create_future()
    await page.route(
        server.PREFIX + "/one-style.css", lambda route: route_future.set_result(route)
    )
    await frame.goto(server.PREFIX + "/one-style.html", wait_until="domcontentloaded")
    request = await route_future
    resolved = False

    async def wait_for_load_state() -> None:
        nonlocal resolved
        await frame.wait_for_load_state()
        resolved = True

    async def continue_request() -> None:
        # give the promise a chance to resolve, even though it shouldn't
        await page.evaluate("1")
        assert resolved is False
        await request.continue_()

    await asyncio.gather(wait_for_load_state(), continue_request())


async def test_WA_092_should_work_with_javascript_iframe(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        '<iframe src="javascript:false"></iframe>', wait_until="commit"
    )
    await page.wait_for_load_state("domcontentloaded")
    await page.wait_for_load_state("load")
    await page.wait_for_load_state("networkidle")


async def test_WA_093_should_work_with_broken_data_url_iframe(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        '<iframe src="data:text/html"></iframe>', wait_until="commit"
    )
    await page.wait_for_load_state("domcontentloaded")
    await page.wait_for_load_state("load")
    await page.wait_for_load_state("networkidle")


async def test_WA_094_should_work_with_broken_blob_url_iframe(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content('<iframe src="blob:"></iframe>', wait_until="commit")
    await page.wait_for_load_state("domcontentloaded")
    await page.wait_for_load_state("load")
    await page.wait_for_load_state("networkidle")
