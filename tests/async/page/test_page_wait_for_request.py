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

"""Port of tests/page/page-wait-for-request.spec.ts."""

import re
import traceback
from typing import Optional

import pytest

from playwright.async_api import Error, Page, Request, TimeoutError
from tests.server import Server


async def test_WA_121_should_work(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_request(server.PREFIX + "/digits/2.png") as request_info:
        await page.evaluate(
            """() => {
                void fetch('/digits/1.png');
                void fetch('/digits/2.png');
                void fetch('/digits/3.png');
            }"""
        )
    request = await request_info.value
    assert request.url == server.PREFIX + "/digits/2.png"


async def test_WA_122_should_work_with_predicate(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)

    def is_digit_2(request: Request) -> bool:
        return request.url == server.PREFIX + "/digits/2.png"

    async with page.expect_event("request", is_digit_2) as request_info:
        await page.evaluate(
            """() => {
                void fetch('/digits/1.png');
                void fetch('/digits/2.png');
                void fetch('/digits/3.png');
            }"""
        )
    request = await request_info.value
    assert request.url == server.PREFIX + "/digits/2.png"


async def test_WA_123_should_respect_timeout(page: Page) -> None:
    error: Optional[Error] = None
    try:
        await page.wait_for_event("request", predicate=lambda _: False, timeout=1)
    except Error as e:
        error = e
    assert isinstance(error, TimeoutError)
    assert 'Timeout 1ms exceeded while waiting for event "request"' in error.message
    # Error stack should point to the api call.
    first_frame = traceback.extract_tb(error.__traceback__)[0]
    assert first_frame.filename == __file__


async def test_WA_124_should_respect_default_timeout(page: Page) -> None:
    error: Optional[Error] = None
    page.set_default_timeout(1)
    try:
        await page.wait_for_event("request", lambda _: False)
    except Error as e:
        error = e
    assert isinstance(error, TimeoutError)


@pytest.mark.xfail(
    reason="python: expect_request logs the url without quotes and trims it to 50 "
    "characters, not 49, before the ellipsis",
    strict=True,
)
async def test_WA_125_should_log_the_url(page: Page) -> None:
    with pytest.raises(Error) as exc_info:
        async with page.expect_request(
            "long-long-long-long-long-long-long-long-long-long-long-long-long-long.css",
            timeout=1000,
        ):
            pass
    assert (
        'waiting for request "long-long-long-long-long-long-long-long-long-long…"'
        in exc_info.value.message
    )


async def test_WA_126_should_work_with_no_timeout(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_request(
        server.PREFIX + "/digits/2.png", timeout=0
    ) as request_info:
        await page.evaluate(
            """() => window.builtins.setTimeout(() => {
                void fetch('/digits/1.png');
                void fetch('/digits/2.png');
                void fetch('/digits/3.png');
            }, 50)"""
        )
    request = await request_info.value
    assert request.url == server.PREFIX + "/digits/2.png"


async def test_WA_127_should_work_with_url_match(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_request(re.compile(r"digits\/\d\.png")) as request_info:
        await page.evaluate(
            """() => {
                void fetch('/digits/1.png');
            }"""
        )
    request = await request_info.value
    assert request.url == server.PREFIX + "/digits/1.png"
