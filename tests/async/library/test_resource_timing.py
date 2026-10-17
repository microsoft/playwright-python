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

"""Port of tests/library/resource-timing.spec.ts."""

from typing import Awaitable, Callable, List

import pytest

from playwright.async_api import (
    Browser,
    BrowserContext,
    Request,
    ResourceTiming,
    Response,
)
from tests.server import Server, TestServerRequest


def verify_timing_value(value: float, previous: float) -> None:
    assert value == -1 or value > 0 and value >= previous


def verify_connection_timing_consistency(timing: ResourceTiming) -> None:
    verify_timing_value(timing["domainLookupStart"], -1)
    verify_timing_value(timing["domainLookupEnd"], timing["domainLookupStart"])
    verify_timing_value(timing["connectStart"], timing["domainLookupEnd"])
    verify_timing_value(timing["secureConnectionStart"], timing["connectStart"])
    verify_timing_value(timing["connectEnd"], timing["secureConnectionStart"])


async def test_NE_131_should_work_smoke(
    context_factory: Callable[..., Awaitable[BrowserContext]], server: Server
) -> None:
    context = await context_factory()
    page = await context.new_page()
    async with page.expect_event("requestfinished") as request_info:
        await page.goto(server.EMPTY_PAGE)
    request = await request_info.value
    timing = request.timing
    verify_connection_timing_consistency(timing)
    assert timing["requestStart"] >= timing["connectEnd"]
    assert timing["responseStart"] >= timing["requestStart"]
    assert timing["responseEnd"] >= timing["responseStart"]
    assert timing["responseEnd"] < 10000
    await context.close()


async def test_NE_132_should_work_for_subresource(
    context_factory: Callable[..., Awaitable[BrowserContext]],
    server: Server,
    browser_name: str,
    platform: str,
) -> None:
    if browser_name == "webkit" and platform == "win32":
        pytest.skip("fixme: responseStart is wrong due upstream webkit/libcurl bug")
    context = await context_factory()
    page = await context.new_page()
    requests: List[Request] = []
    page.on("requestfinished", lambda request: requests.append(request))
    await page.goto(server.PREFIX + "/one-style.html")
    assert len(requests) == 2
    timing = requests[1].timing
    verify_connection_timing_consistency(timing)
    assert timing["requestStart"] >= 0
    assert timing["responseStart"] > timing["requestStart"]
    assert timing["responseEnd"] >= timing["responseStart"]
    assert timing["responseEnd"] < 10000
    await context.close()


async def test_NE_133_should_work_for_ssl(
    browser: Browser, https_server: Server
) -> None:
    page = await browser.new_page(ignore_https_errors=True)
    async with page.expect_event("requestfinished") as request_info:
        await page.goto(https_server.EMPTY_PAGE)
    request = await request_info.value
    timing = request.timing
    verify_connection_timing_consistency(timing)
    assert timing["requestStart"] >= timing["connectEnd"]
    assert timing["responseStart"] > timing["requestStart"]
    assert timing["responseEnd"] >= timing["responseStart"]
    assert timing["responseEnd"] < 10000
    await page.close()


async def test_NE_134_should_work_for_redirect(
    context_factory: Callable[..., Awaitable[BrowserContext]],
    browser_name: str,
    server: Server,
) -> None:
    if browser_name == "webkit":
        pytest.skip("fixme: In WebKit, redirects don't carry the timing info")

    context = await context_factory()
    page = await context.new_page()
    server.set_redirect("/foo.html", "/empty.html")
    responses: List[Response] = []
    page.on("response", lambda response: responses.append(response))
    await page.goto(server.PREFIX + "/foo.html")
    for response in responses:
        await response.finished()

    assert len(responses) == 2
    assert responses[0].url == server.PREFIX + "/foo.html"
    assert responses[1].url == server.PREFIX + "/empty.html"

    timing1 = responses[0].request.timing
    verify_connection_timing_consistency(timing1)
    assert timing1["requestStart"] >= timing1["connectEnd"]
    assert timing1["responseStart"] > timing1["requestStart"]
    assert timing1["responseEnd"] >= timing1["responseStart"]
    assert timing1["responseEnd"] < 10000

    timing2 = responses[1].request.timing
    verify_connection_timing_consistency(timing2)
    assert timing2["requestStart"] >= 0
    assert timing2["responseStart"] > timing2["requestStart"]
    assert timing2["responseEnd"] >= timing2["responseStart"]
    assert timing2["responseEnd"] < 10000

    await context.close()


async def test_NE_135_should_work_when_serving_from_memory_cache(
    context_factory: Callable[..., Awaitable[BrowserContext]],
    server: Server,
    browser_name: str,
) -> None:
    if browser_name == "firefox":
        pytest.skip("fixme: Response event is not fired in Firefox")

    def handle(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("Content-Type", "text/css")
        request.setHeader("Cache-Control", "public, max-age=10031518")
        request.write(b"body { background: red }")
        request.finish()

    server.set_route("/one-style.css", handle)

    context = await context_factory()
    page = await context.new_page()
    await page.goto(server.PREFIX + "/one-style.html")
    async with page.expect_response("**/one-style.css") as response_info:
        await page.reload()
    response = await response_info.value
    await response.finished()

    timing = response.request.timing
    verify_connection_timing_consistency(timing)

    assert timing["responseStart"] == timing["responseEnd"]
    assert timing["responseEnd"] < 1000
    await context.close()
