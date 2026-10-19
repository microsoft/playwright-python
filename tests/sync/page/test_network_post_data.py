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

"""Port of tests/page/network-post-data.spec.ts."""

import json

import pytest

from playwright.sync_api import Error, Page
from tests.server import Server


def expect_failure(request: pytest.FixtureRequest, reason: str) -> None:
    """Like `it.fail()`: the test must fail."""
    request.applymarker(pytest.mark.xfail(reason=f"upstream: {reason}", strict=True))


def test_NE_108_should_return_correct_post_data_buffer_for_utf_8_body(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    value = "baẞ"
    with page.expect_request("**") as request_info:
        page.evaluate(
            """({ url, value }) => {
                const request = new Request(url, {
                    method: 'POST',
                    body: JSON.stringify(value),
                });
                request.headers.set('content-type', 'application/json;charset=UTF-8');
                return fetch(request);
            }""",
            {"url": server.PREFIX + "/title.html", "value": value},
        )
    request = request_info.value
    assert request.post_data_buffer == json.dumps(value, ensure_ascii=False).encode(
        "utf-8"
    )
    assert request.post_data_json == value


def test_NE_109_should_return_post_data_w_o_content_type_smoke(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    with page.expect_request("**") as request_info:
        page.evaluate(
            """({ url }) => {
                const request = new Request(url, {
                    method: 'POST',
                    body: JSON.stringify({ value: 42 }),
                });
                request.headers.set('content-type', '');
                return fetch(request);
            }""",
            {"url": server.PREFIX + "/title.html"},
        )
    request = request_info.value
    assert request.post_data_json == {"value": 42}


def test_NE_110_should_throw_on_invalid_json_in_post_data(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    with page.expect_request("**") as request_info:
        page.evaluate(
            """({ url }) => {
                const request = new Request(url, {
                    method: 'POST',
                    body: '<not a json>',
                });
                return fetch(request);
            }""",
            {"url": server.PREFIX + "/title.html"},
        )
    request = request_info.value
    with pytest.raises(Error) as exc_info:
        request.post_data_json
    assert (
        "POST data is not a valid JSON object: <not a json>" in exc_info.value.message
    )


def test_NE_111_should_return_post_data_for_put_requests(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    with page.expect_request("**") as request_info:
        page.evaluate(
            """({ url }) => {
                const request = new Request(url, {
                    method: 'PUT',
                    body: JSON.stringify({ value: 42 }),
                });
                return fetch(request);
            }""",
            {"url": server.PREFIX + "/title.html"},
        )
    request = request_info.value
    assert request.post_data_json == {"value": 42}


def test_NE_112_should_get_post_data_for_file_blob(
    page: Page, server: Server, browser_name: str, request: pytest.FixtureRequest
) -> None:
    if browser_name == "webkit" or browser_name == "chromium":
        expect_failure(request, "expected to fail on chromium and webkit")
    page.goto(server.EMPTY_PAGE)
    with page.expect_request("**/*") as request_info:
        page.evaluate(
            """() => {
                const file = new File(['file-contents'], 'filename.txt');

                void fetch('/data', {
                    method: 'POST',
                    headers: {
                        'content-type': 'application/octet-stream'
                    },
                    body: file
                });
            }"""
        )
    assert (request_info.value).post_data == "file-contents"


def test_NE_113_should_get_post_data_for_navigator_send_beacon_api_calls(
    page: Page, server: Server, browser_name: str, request: pytest.FixtureRequest
) -> None:
    if browser_name == "chromium":
        expect_failure(request, "postData is empty")
    if browser_name == "webkit":
        expect_failure(request, "postData is empty")
    page.goto(server.EMPTY_PAGE)
    with page.expect_request("**/*") as request_info:
        page.evaluate(
            "() => navigator.sendBeacon(window.location.origin + '/api/foo', new Blob([JSON.stringify({ foo: 'bar' })]))"
        )
    beacon_request = request_info.value
    assert beacon_request.method == "POST"
    assert beacon_request.url == server.PREFIX + "/api/foo"
    assert beacon_request.post_data_json == {"foo": "bar"}
