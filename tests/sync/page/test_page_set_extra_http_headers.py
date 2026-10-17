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

"""Port of tests/page/page-set-extra-http-headers.spec.ts."""

import pytest

from playwright.sync_api import Error, Page
from tests.server import Server


def test_NE_114_should_work_smoke(page: Page, server: Server) -> None:
    page.set_extra_http_headers(
        {
            "foo": "bar",
        }
    )
    with server.expect_request("/empty.html") as request_info:
        page.goto(server.EMPTY_PAGE)
    request = request_info.value
    assert request.getHeader("foo") == "bar"
    assert request.getHeader("baz") is None


def test_NE_115_should_work_with_redirects(page: Page, server: Server) -> None:
    server.set_redirect("/foo.html", "/empty.html")
    page.set_extra_http_headers({"foo": "bar"})
    with server.expect_request("/empty.html") as request_info:
        page.goto(server.PREFIX + "/foo.html")
    request = request_info.value
    assert request.getHeader("foo") == "bar"


def test_NE_116_should_work_with_extra_headers_from_browser_context(
    page: Page, server: Server
) -> None:
    page.context.set_extra_http_headers(
        {
            "foo": "bar",
        }
    )
    with server.expect_request("/empty.html") as request_info:
        page.goto(server.EMPTY_PAGE)
    request = request_info.value
    assert request.getHeader("foo") == "bar"


@pytest.mark.skip_protocol_check
@pytest.mark.xfail(
    reason="python: header values are not checked on the client; the driver fails with another message",
    strict=True,
)
def test_NE_117_should_throw_for_non_string_header_values(page: Page) -> None:
    with pytest.raises(Error) as exc_info:
        page.set_extra_http_headers({"foo": 1})  # type: ignore
    assert (
        'Expected value of header "foo" to be String, but "number" is found.'
        in exc_info.value.message
    )
    with pytest.raises(Error) as exc_info:
        page.context.set_extra_http_headers({"foo": True})  # type: ignore
    assert (
        'Expected value of header "foo" to be String, but "boolean" is found.'
        in exc_info.value.message
    )


def test_NE_118_should_not_duplicate_referer_header(
    page: Page,
    server: Server,
    browser_name: str,
    browser_major_version: int,
    request: pytest.FixtureRequest,
) -> None:
    if browser_name == "chromium" and browser_major_version < 154:
        request.applymarker(
            pytest.mark.xfail(
                reason="upstream: Request has referer and Referer", strict=True
            )
        )
    page.set_extra_http_headers({"referer": server.EMPTY_PAGE})
    response = page.goto(server.EMPTY_PAGE)
    assert response
    assert response.ok is True
    assert response.request.headers["referer"] == server.EMPTY_PAGE
