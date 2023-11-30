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

from playwright.sync_api import Error, Page, Route
from tests.server import Server, TestServerRequest


def test_should_support_timeout_option_in_route_fetch(
    server: Server, page: Page
) -> None:
    def _handle(request: TestServerRequest) -> None:
        request.responseHeaders.addRawHeader("Content-Length", "4096")
        request.responseHeaders.addRawHeader("Content-Type", "text/html")
        request.write(b"")

    server.set_route(
        "/slow",
        _handle,
    )

    def handle(route: Route) -> None:
        with pytest.raises(Error) as error:
            route.fetch(timeout=1000)
        assert "Request timed out after 1000ms" in error.value.message

    page.route("**/*", lambda route: handle(route))
    with pytest.raises(Error) as error:
        page.goto(server.PREFIX + "/slow", timeout=2000)
    assert "Timeout 2000ms exceeded" in error.value.message


def test_should_intercept_with_url_override(server: Server, page: Page) -> None:
    def handle(route: Route) -> None:
        response = route.fetch(url=server.PREFIX + "/one-style.html")
        route.fulfill(response=response)

    page.route("**/*.html", lambda route: handle(route))
    response = page.goto(server.PREFIX + "/empty.html")
    assert response
    assert response.status == 200
    assert "one-style.css" in response.body().decode("utf-8")
