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

"""Python only: tests of behaviors that no upstream test covers."""


from playwright.async_api import Page
from tests.server import Server


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
            body: 'foo=bar&baz=123&empty='
        })"""
        )
    request = await request_info.value
    assert request
    assert request.post_data_json == {"foo": "bar", "baz": "123", "empty": ""}
