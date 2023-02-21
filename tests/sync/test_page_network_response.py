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

import pytest
from twisted.web import http

from playwright.sync_api import Error, Page
from tests.server import Server


def test_should_reject_response_finished_if_page_closes(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)

    def handle_get(request: http.Request) -> None:
        # In Firefox, |fetch| will be hanging until it receives |Content-Type| header
        # from server.
        request.setHeader("Content-Type", "text/plain; charset=utf-8")
        request.write(b"hello ")

    server.set_route("/get", handle_get)
    # send request and wait for server response
    with page.expect_response("**/*") as response_info:
        page.evaluate("() => fetch('./get', { method: 'GET' })")
    page_response = response_info.value
    page.close()
    with pytest.raises(Error) as exc_info:
        page_response.finished()
    error = exc_info.value
    assert "closed" in error.message


def test_should_reject_response_finished_if_context_closes(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)

    def handle_get(request: http.Request) -> None:
        # In Firefox, |fetch| will be hanging until it receives |Content-Type| header
        # from server.
        request.setHeader("Content-Type", "text/plain; charset=utf-8")
        request.write(b"hello ")

    server.set_route("/get", handle_get)
    # send request and wait for server response
    with page.expect_response("**/*") as response_info:
        page.evaluate("() => fetch('./get', { method: 'GET' })")
    page_response = response_info.value

    page.context.close()
    with pytest.raises(Error) as exc_info:
        page_response.finished()
    error = exc_info.value
    assert "closed" in error.message
