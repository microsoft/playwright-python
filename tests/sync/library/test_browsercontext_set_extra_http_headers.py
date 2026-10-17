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

"""Port of tests/library/browsercontext-set-extra-http-headers.spec.ts."""

import pytest

from playwright.sync_api import Browser, Error
from tests.server import Server


def test_NE_119_should_override_extra_headers_from_browser_context(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context(
        extra_http_headers={"fOo": "bAr", "baR": "foO"},
    )
    page = context.new_page()
    page.set_extra_http_headers({"Foo": "Bar"})
    with server.expect_request("/empty.html") as request_info:
        page.goto(server.EMPTY_PAGE)
    request = request_info.value
    context.close()
    assert request.getHeader("foo") == "Bar"
    assert request.getHeader("bar") == "foO"


@pytest.mark.xfail(
    reason="python: a None header value is dropped instead of rejected",
    strict=True,
)
def test_NE_120_should_throw_for_non_string_header_values(
    browser: Browser,
) -> None:
    with pytest.raises(Error) as exc_info:
        browser.new_context(extra_http_headers={"foo": None})  # type: ignore
    assert (
        'Expected value of header "foo" to be String, but "object" is found.'
        in exc_info.value.message
    )
