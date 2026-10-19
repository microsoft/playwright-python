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

"""Port of tests/page/page-wait-for-response.spec.ts."""

import re
import traceback
from typing import Optional

import pytest

from playwright.async_api import Error, Page, Response, TimeoutError
from tests.server import Server


async def test_WA_129_should_work(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_response(server.PREFIX + "/digits/2.png") as response_info:
        await page.evaluate(
            """() => {
                void fetch('/digits/1.png');
                void fetch('/digits/2.png');
                void fetch('/digits/3.png');
            }"""
        )
    response = await response_info.value
    assert response.url == server.PREFIX + "/digits/2.png"


async def test_WA_130_should_respect_timeout(page: Page) -> None:
    error: Optional[Error] = None
    try:
        await page.wait_for_event("response", predicate=lambda _: False, timeout=1)
    except Error as e:
        error = e
    assert isinstance(error, TimeoutError)


async def test_WA_131_should_respect_default_timeout(page: Page) -> None:
    error: Optional[Error] = None
    page.set_default_timeout(1)
    try:
        async with page.expect_response(lambda _: False):
            pass
    except Error as e:
        error = e
    assert isinstance(error, TimeoutError)
    # Error stack should point to the api call.
    first_frame = traceback.extract_tb(error.__traceback__)[0]
    assert first_frame.filename == __file__


async def test_WA_132_should_log_the_url(page: Page) -> None:
    with pytest.raises(Error) as exc_info1:
        async with page.expect_response("foo.css", timeout=1000):
            pass
    assert 'waiting for response "foo.css"' in exc_info1.value.message
    with pytest.raises(Error) as exc_info2:
        async with page.expect_response(
            re.compile(r"foo.css", re.IGNORECASE), timeout=1000
        ):
            pass
    assert "waiting for response /foo.css/i" in exc_info2.value.message


async def test_WA_133_should_work_with_predicate(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)

    def is_digit_2(response: Response) -> bool:
        return response.url == server.PREFIX + "/digits/2.png"

    async with page.expect_event("response", is_digit_2) as response_info:
        await page.evaluate(
            """() => {
                void fetch('/digits/1.png');
                void fetch('/digits/2.png');
                void fetch('/digits/3.png');
            }"""
        )
    response = await response_info.value
    assert response.url == server.PREFIX + "/digits/2.png"


async def test_WA_134_should_work_with_async_predicate(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)

    async def has_file_contents(response: Response) -> bool:
        text = await response.text()
        return "contents of the file" in text

    async def has_bar(response: Response) -> bool:
        text = await response.text()
        return "bar" in text

    async with page.expect_event(
        "response", has_file_contents  # type: ignore[arg-type]
    ) as response1_info:
        async with page.expect_response(has_bar) as response2_info:
            await page.evaluate(
                """() => {
                    void fetch('/simple.json').then(r => r.json());
                    void fetch('/file-to-upload.txt').then(r => r.text());
                }"""
            )
    response1 = await response1_info.value
    response2 = await response2_info.value
    assert response1.url == server.PREFIX + "/file-to-upload.txt"
    assert response2.url == server.PREFIX + "/simple.json"


async def test_WA_135_sync_predicate_should_be_only_called_once(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    counter = 0

    def is_digit_1(response: Response) -> bool:
        nonlocal counter
        counter += 1
        return response.url == server.PREFIX + "/digits/1.png"

    async with page.expect_event("response", is_digit_1) as response_info:
        await page.evaluate(
            """async () => {
                await fetch('/digits/1.png');
                await fetch('/digits/2.png');
                await fetch('/digits/3.png');
            }"""
        )
    response = await response_info.value
    assert response.url == server.PREFIX + "/digits/1.png"
    assert counter == 1


async def test_WA_136_should_work_with_no_timeout(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_response(
        server.PREFIX + "/digits/2.png", timeout=0
    ) as response_info:
        await page.evaluate(
            """() => window.builtins.setTimeout(() => {
                void fetch('/digits/1.png');
                void fetch('/digits/2.png');
                void fetch('/digits/3.png');
            }, 50)"""
        )
    response = await response_info.value
    assert response.url == server.PREFIX + "/digits/2.png"
