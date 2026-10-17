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

import asyncio
from typing import List, Optional

import pytest

from playwright.async_api import Error, Page, Response
from tests.server import Server, TestServerRequest, reactor
from tests.utils import must

from ..utils import Utils


def end(request: TestServerRequest, body: str) -> None:
    """Ends a held response from the test thread, like res.end(body)."""

    def finish() -> None:
        request.write(body.encode())
        request.finish()

    reactor.callFromThread(finish)


async def test_FR_020_should_navigate_subframes_smoke(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/frames/one-frame.html")
    assert "/frames/one-frame.html" in page.frames[0].url
    assert "/frames/frame.html" in page.frames[1].url

    response = must(await page.frames[1].goto(server.EMPTY_PAGE))
    assert response.ok is True
    assert response.frame == page.frames[1]


async def test_FR_021_should_reject_when_frame_detaches(
    page: Page, server: Server, browser_name: str
) -> None:
    await page.goto(server.PREFIX + "/frames/one-frame.html")

    server.set_route("/one-style.css", lambda request: None)

    async def navigate() -> Error:
        with pytest.raises(Error) as exc_info:
            await page.frames[1].goto(server.PREFIX + "/one-style.html")
        return exc_info.value

    navigation_task = asyncio.create_task(navigate())
    await server.wait_for_request("/one-style.css")

    await page.eval_on_selector("iframe", "frame => frame.remove()")
    error = await navigation_task
    if browser_name == "chromium":
        assert (
            "net::ERR_ABORTED" in error.message
            or "frame was detached" in error.message.lower()
        )
    else:
        assert "frame was detached" in error.message.lower()


async def test_FR_022_should_continue_after_client_redirect(
    page: Page, server: Server, browser_name: str
) -> None:
    if browser_name == "firefox":
        pytest.skip("fixme: script.js is requested before navigationCommitted arrives")

    server.set_route("/frames/script.js", lambda request: None)
    url = server.PREFIX + "/frames/child-redirect.html"
    with pytest.raises(Error) as exc_info:
        await page.goto(url, timeout=5000, wait_until="networkidle")
    assert "Page.goto: Timeout 5000ms exceeded." in exc_info.value.message
    assert (
        f'navigating to "{url}", waiting until "networkidle"' in exc_info.value.message
    )


async def test_FR_023_should_return_matching_responses(
    page: Page, server: Server, utils: Utils
) -> None:
    await page.goto(server.EMPTY_PAGE)
    # Attach three frames.
    frames = [
        await utils.attach_frame(page, "frame1", server.EMPTY_PAGE),
        await utils.attach_frame(page, "frame2", server.EMPTY_PAGE),
        await utils.attach_frame(page, "frame3", server.EMPTY_PAGE),
    ]
    server_responses: List[TestServerRequest] = []
    server.set_route("/0.html", server_responses.append)
    server.set_route("/1.html", server_responses.append)
    server.set_route("/2.html", server_responses.append)
    navigations: List["asyncio.Task[Optional[Response]]"] = []
    for i in range(3):
        navigations.append(
            asyncio.create_task(frames[i].goto(server.PREFIX + "/" + str(i) + ".html"))
        )
        await server.wait_for_request("/" + str(i) + ".html")
    # Respond from server out-of-order.
    server_response_texts = ["AAA", "BBB", "CCC"]
    for i in [1, 2, 0]:
        end(server_responses[i], server_response_texts[i])
        response = must(await navigations[i])
        assert response.frame == frames[i]
        assert await response.text() == server_response_texts[i]
