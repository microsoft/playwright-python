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

from pathlib import Path

import pytest
from twisted.web import http

from playwright.sync_api import BrowserContext, Page, Route
from tests.server import Server


def test_should_fulfill_intercepted_response(
    page: Page, context: BrowserContext, server: Server
) -> None:
    def handle(route: Route) -> None:
        response = page.request.fetch(route.request)
        route.fulfill(
            response=response,
            status=201,
            headers={"foo": "bar"},
            content_type="text/plain",
            body="Yo, page!",
        )

    context.route("**/*", handle)
    response = page.goto(server.PREFIX + "/empty.html")
    assert response
    assert response.status == 201
    assert response.headers["foo"] == "bar"
    assert response.headers["content-type"] == "text/plain"
    assert page.evaluate("() => document.body.textContent") == "Yo, page!"


def test_should_fulfill_response_with_empty_body(
    page: Page, context: BrowserContext, server: Server
) -> None:
    def handle(route: Route) -> None:
        response = page.request.fetch(route.request)
        route.fulfill(
            response=response, status=201, body="", headers={"content-length": "0"}
        )

    context.route("**/*", handle)
    response = page.goto(server.PREFIX + "/title.html")
    assert response
    assert response.status == 201
    assert response.text() == ""


def test_should_override_with_defaults_when_intercepted_response_not_provided(
    page: Page, context: BrowserContext, server: Server, browser_name: str
) -> None:
    def server_handler(request: http.Request) -> None:
        request.setHeader("foo", "bar")
        request.write("my content".encode())
        request.finish()

    server.set_route("/empty.html", server_handler)

    def handle(route: Route) -> None:
        page.request.fetch(route.request)
        route.fulfill(status=201)

    context.route("**/*", handle)
    response = page.goto(server.EMPTY_PAGE)
    assert response
    assert response.status == 201
    assert response.text() == ""
    if browser_name == "webkit":
        assert response.headers == {"content-type": "text/plain"}
    else:
        assert response.headers == {}


def test_should_fulfill_with_any_response(
    page: Page, context: BrowserContext, server: Server
) -> None:
    def server_handler(request: http.Request) -> None:
        request.setHeader("foo", "bar")
        request.write("Woo-hoo".encode())
        request.finish()

    server.set_route("/sample", server_handler)
    sample_response = page.request.get(server.PREFIX + "/sample")
    context.route(
        "**/*",
        lambda route: route.fulfill(
            response=sample_response, status=201, content_type="text/plain"
        ),
    )
    response = page.goto(server.EMPTY_PAGE)
    assert response
    assert response.status == 201
    assert response.text() == "Woo-hoo"
    assert response.headers["foo"] == "bar"


def test_should_support_fulfill_after_intercept(
    page: Page, context: BrowserContext, server: Server, assetdir: Path
) -> None:
    def handle_route(route: Route) -> None:
        response = page.request.fetch(route.request)
        route.fulfill(response=response)

    context.route("**", handle_route)
    with server.expect_request("/title.html") as request_info:
        response = page.goto(server.PREFIX + "/title.html")
    assert response
    request = request_info.value
    assert request.uri.decode() == "/title.html"
    original = (assetdir / "title.html").read_text()
    assert response.text() == original


def test_should_show_exception_after_fulfill(page: Page, server: Server) -> None:
    def _handle(route: Route) -> None:
        route.continue_()
        raise Exception("Exception text!?")

    page.route("*/**", _handle)
    page.goto(server.EMPTY_PAGE)
    # Any next API call should throw because handler did throw during previous goto()
    with pytest.raises(Exception, match="Exception text!?"):
        page.goto(server.EMPTY_PAGE)
