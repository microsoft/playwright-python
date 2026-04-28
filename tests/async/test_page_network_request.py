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

import asyncio

import pytest

from playwright.async_api import Error, Page, Request
from tests.server import Server


async def test_should_not_allow_to_access_frame_on_popup_main_request(
    page: Page, server: Server
) -> None:
    await page.set_content(f'<a target=_blank href="{server.EMPTY_PAGE}">click me</a>')
    request_promise = asyncio.ensure_future(page.context.wait_for_event("request"))
    popup_promise = asyncio.ensure_future(page.context.wait_for_event("page"))
    clicked = asyncio.ensure_future(page.get_by_text("click me").click())
    request: Request = await request_promise

    assert request.is_navigation_request()

    with pytest.raises(Error) as exc_info:
        request.frame
    assert (
        "Frame for this navigation request is not available" in exc_info.value.message
    )

    response = await request.response()
    assert response
    await response.finished()
    await popup_promise
    await clicked


async def test_should_parse_the_data_if_content_type_is_application_x_www_form_urlencoded_charset_UTF_8(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_event("request") as request_info:
        await page.evaluate(
            """() => fetch('./post', {
            method: 'POST',
            headers: {
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            },
            body: 'foo=bar&baz=123'
        })"""
        )
    request = await request_info.value
    assert request
    assert request.post_data_json == {"foo": "bar", "baz": "123"}


async def test_existing_response_should_return_response_after_it_is_received(
    page: Page, server: Server
) -> None:
    async with page.expect_event("requestfinished") as request_finished_info:
        await page.goto(server.EMPTY_PAGE)
    request = await request_finished_info.value
    assert request.existing_response is not None
    assert request.existing_response.status == 200


async def test_existing_response_should_return_none_before_response_arrives(
    page: Page, server: Server
) -> None:
    captured = []
    page.on("request", lambda req: captured.append(req.existing_response))
    await page.goto(server.EMPTY_PAGE)
    assert captured
    # When the "request" event fires, the response has not been received yet.
    assert captured[0] is None
