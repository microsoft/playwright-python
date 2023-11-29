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

from typing import Dict

import pytest
from flaky import flaky

from playwright.async_api import Browser, Page
from tests.server import Server


async def test_should_work(page: Page, server: Server) -> None:
    async with page.expect_event("requestfinished") as request_info:
        await page.goto(server.EMPTY_PAGE)
    request = await request_info.value
    timing = request.timing
    verify_connections_timing_consistency(timing)
    assert timing["requestStart"] >= timing["connectEnd"]
    assert timing["responseStart"] >= timing["requestStart"]
    assert timing["responseEnd"] >= timing["responseStart"]
    assert timing["responseEnd"] < 10000


@flaky
async def test_should_work_for_subresource(
    page: Page, server: Server, is_win: bool, is_mac: bool, is_webkit: bool
) -> None:
    if is_webkit and (is_mac or is_win):
        pytest.skip()
    requests = []
    page.on("requestfinished", lambda request: requests.append(request))
    await page.goto(server.PREFIX + "/one-style.html")
    assert len(requests) >= 2
    timing = requests[1].timing
    verify_connections_timing_consistency(timing)
    assert timing["requestStart"] >= 0
    assert timing["responseStart"] > timing["requestStart"]
    assert timing["responseEnd"] >= timing["responseStart"]
    assert timing["responseEnd"] < 10000


@flaky  # Upstream flaky
async def test_should_work_for_ssl(browser: Browser, https_server: Server) -> None:
    page = await browser.new_page(ignore_https_errors=True)
    async with page.expect_event("requestfinished") as request_info:
        await page.goto(https_server.EMPTY_PAGE)
    request = await request_info.value
    timing = request.timing
    verify_connections_timing_consistency(timing)
    assert timing["requestStart"] >= timing["connectEnd"]
    assert timing["responseStart"] >= timing["requestStart"]
    assert timing["responseEnd"] >= timing["responseStart"]
    assert timing["responseEnd"] < 10000
    await page.close()


@pytest.mark.skip_browser("webkit")  # In WebKit, redirects don"t carry the timing info
async def test_should_work_for_redirect(page: Page, server: Server) -> None:
    server.set_redirect("/foo.html", "/empty.html")
    responses = []
    page.on("response", lambda response: responses.append(response))
    await page.goto(server.PREFIX + "/foo.html")
    for r in responses:
        await r.finished()

    assert len(responses) == 2
    assert responses[0].url == server.PREFIX + "/foo.html"
    assert responses[1].url == server.PREFIX + "/empty.html"

    timing1 = responses[0].request.timing
    verify_connections_timing_consistency(timing1)
    assert timing1["requestStart"] >= timing1["connectEnd"]
    assert timing1["responseStart"] > timing1["requestStart"]
    assert timing1["responseEnd"] >= timing1["responseStart"]
    assert timing1["responseEnd"] < 10000

    timing2 = responses[1].request.timing
    verify_connections_timing_consistency(timing2)
    assert timing2["requestStart"] >= 0
    assert timing2["responseStart"] > timing2["requestStart"]
    assert timing2["responseEnd"] >= timing2["responseStart"]
    assert timing2["responseEnd"] < 10000


def verify_timing_value(value: float, previous: float) -> None:
    assert value == -1 or value > 0 and value >= previous


def verify_connections_timing_consistency(timing: Dict) -> None:
    verify_timing_value(timing["domainLookupStart"], -1)
    verify_timing_value(timing["domainLookupEnd"], timing["domainLookupStart"])
    verify_timing_value(timing["connectStart"], timing["domainLookupEnd"])
    verify_timing_value(timing["secureConnectionStart"], timing["connectStart"])
    verify_timing_value(timing["connectEnd"], timing["secureConnectionStart"])
