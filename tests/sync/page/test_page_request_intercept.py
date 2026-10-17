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

"""Port of tests/page/page-request-intercept.spec.ts."""

import json
import os
import time
from pathlib import Path
from typing import Any, Callable, List, Optional, Tuple

import pytest

from playwright.sync_api import Error, Page, Request, Route
from tests.server import Server, TestServerRequest


def wait_for_list(page: Page, values: List[Any]) -> None:
    """Waits until a route handler adds to values.

    Port of awaiting the promise that upstream's route handler resolves.
    """
    deadline = time.monotonic() + 10
    while not values:
        assert time.monotonic() < deadline, "the route handler did not run"
        page.wait_for_timeout(20)


def test_RO_134_should_fulfill_intercepted_response(page: Page, server: Server) -> None:
    def handler(route: Route) -> None:
        response = page.request.fetch(route.request)
        route.fulfill(
            response=response,
            status=201,
            headers={"foo": "bar"},
            content_type="text/plain",
            body="Yo, page!",
        )

    page.route("**/*", handler)
    response = page.goto(server.PREFIX + "/empty.html")
    assert response
    assert response.status == 201
    assert response.headers["foo"] == "bar"
    assert response.headers["content-type"] == "text/plain"
    assert page.evaluate("() => document.body.textContent") == "Yo, page!"


def test_RO_135_should_fulfill_response_with_empty_body(
    page: Page, server: Server, browser_name: str, browser_major_version: int
) -> None:
    if browser_name == "chromium" and browser_major_version <= 91:
        pytest.skip("Fails in Electron that uses old Chromium")

    def handler(route: Route) -> None:
        response = page.request.fetch(route.request)
        route.fulfill(
            response=response,
            headers={"content-length": "0"},
            status=201,
            body="",
        )

    page.route("**/*", handler)
    response = page.goto(server.PREFIX + "/title.html")
    assert response
    assert response.status == 201
    assert response.text() == ""


def test_RO_136_should_override_with_defaults_when_intercepted_response_not_provided(
    page: Page, server: Server, browser_name: str
) -> None:
    def handle_empty(request: TestServerRequest) -> None:
        request.setHeader("foo", "bar")
        request.write(b"my content")
        request.finish()

    server.set_route("/empty.html", handle_empty)

    def handler(route: Route) -> None:
        page.request.fetch(route.request)
        route.fulfill(status=201)

    page.route("**/*", handler)
    response = page.goto(server.EMPTY_PAGE)
    assert response
    assert response.status == 201
    assert response.text() == ""
    if browser_name == "webkit":
        assert response.headers == {"content-type": "text/plain"}
    else:
        assert response.headers == {}


def test_RO_137_should_fulfill_with_any_response(page: Page, server: Server) -> None:
    def handle_sample(request: TestServerRequest) -> None:
        request.setHeader("foo", "bar")
        request.write(b"Woo-hoo")
        request.finish()

    server.set_route("/sample", handle_sample)
    sample_response = page.request.get(f"{server.PREFIX}/sample")

    page.route(
        "**/*",
        lambda route: route.fulfill(
            response=sample_response,
            status=201,
            content_type="text/plain",
        ),
    )
    response = page.goto(server.EMPTY_PAGE)
    assert response
    assert response.status == 201
    assert response.text() == "Woo-hoo"
    assert response.headers["foo"] == "bar"


def test_RO_138_should_support_fulfill_after_intercept(
    page: Page, server: Server, assetdir: Path
) -> None:
    def handler(route: Route) -> None:
        response = page.request.fetch(route.request)
        route.fulfill(response=response)

    page.route("**", handler)
    with server.expect_request("/title.html") as request_info:
        response = page.goto(server.PREFIX + "/title.html")
    request = request_info.value
    assert request.uri.decode() == "/title.html"
    original = (assetdir / "title.html").read_text(encoding="utf-8")
    assert response
    assert response.text() == original


def test_RO_139_should_give_access_to_the_intercepted_response(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    page.goto(server.EMPTY_PAGE)

    routes: List[Route] = []
    page.route("**/title.html", lambda route: routes.append(route))

    def evaluate() -> None:
        page.evaluate("url => fetch(url)", server.PREFIX + "/title.html")

    def check_and_fulfill() -> None:
        wait_for_list(page, routes)
        route = routes[0]
        response = page.request.fetch(route.request)

        assert response.status == 200
        assert response.status_text == "OK"
        assert response.ok
        assert response.url.endswith("/title.html") is True
        assert response.headers["content-type"] == "text/html; charset=utf-8"
        assert [
            header
            for header in response.headers_array
            if header["name"].lower() == "content-type"
        ] == [{"name": "Content-Type", "value": "text/html; charset=utf-8"}]

        route.fulfill(response=response)

    sync_gather(evaluate, check_and_fulfill)


def test_RO_140_should_give_access_to_the_intercepted_response_body(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    page.goto(server.EMPTY_PAGE)

    routes: List[Route] = []
    page.route("**/simple.json", lambda route: routes.append(route))

    def evaluate() -> None:
        try:
            page.evaluate("url => fetch(url)", server.PREFIX + "/simple.json")
        except Error:
            pass

    def check_and_fulfill() -> None:
        wait_for_list(page, routes)
        route = routes[0]
        response = page.request.fetch(route.request)

        assert response.text() == '{"foo": "bar"}\n'

        route.fulfill(response=response)

    sync_gather(evaluate, check_and_fulfill)


def test_RO_141_should_intercept_multipart_form_data_request_body(
    page: Page, server: Server, assetdir: Path, browser_name: str
) -> None:
    # https://github.com/microsoft/playwright/issues/14624
    if browser_name != "firefox":
        pytest.skip("fixme")
    page.goto(server.PREFIX + "/input/fileupload.html")
    file_path = os.path.relpath(assetdir / "file-to-upload.txt")
    page.locator("input[type=file]").set_input_files(file_path)
    requests: List[Request] = []
    page.route("**/upload", lambda route: requests.append(route.request))
    page.click("input[type=submit]", no_wait_after=True)
    wait_for_list(page, requests)
    request = requests[0]
    assert request.method == "POST"
    assert Path(file_path).read_text(encoding="utf-8") in (request.post_data or "")


def test_RO_142_should_fulfill_intercepted_response_using_alias(
    page: Page, server: Server
) -> None:
    def handler(route: Route) -> None:
        response = route.fetch()
        route.fulfill(response=response)

    page.route("**/*", handler)
    response = page.goto(server.PREFIX + "/empty.html")
    assert response
    assert response.status == 200
    assert "text/html" in response.headers["content-type"]


def test_RO_143_should_support_timeout_option_in_route_fetch(
    page: Page, server: Server
) -> None:
    def handle_slow(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("content-length", "4096")
        request.setHeader("content-type", "text/html")
        request.write(b"")

    server.set_route("/slow", handle_slow)

    fetch_errors: List[Optional[Error]] = []

    def handler(route: Route) -> None:
        try:
            route.fetch(timeout=1000)
            fetch_errors.append(None)
        except Error as e:
            fetch_errors.append(e)

    page.route("**/*", handler)
    with pytest.raises(Error) as exc_info:
        page.goto(server.PREFIX + "/slow", timeout=2000)
    assert "Timeout 2000ms exceeded" in exc_info.value.message
    wait_for_list(page, fetch_errors)
    fetch_error = fetch_errors[0]
    assert fetch_error
    assert "Route.fetch: Timeout 1000ms exceeded" in fetch_error.message


def test_RO_144_should_not_follow_redirects_when_max_redirects_is_set_to_0_in_route_fetch(
    page: Page, server: Server
) -> None:
    server.set_redirect("/foo", "/empty.html")
    fetched: List[Tuple[Optional[str], int]] = []

    def handler(route: Route) -> None:
        response = route.fetch(max_redirects=0)
        fetched.append((response.headers.get("location"), response.status))
        route.fulfill(body="hello")

    page.route("**/*", handler)
    page.goto(server.PREFIX + "/foo")
    assert "hello" in page.content()
    assert fetched == [("/empty.html", 302)]


def test_RO_145_should_intercept_with_url_override(page: Page, server: Server) -> None:
    def handler(route: Route) -> None:
        response = route.fetch(url=server.PREFIX + "/one-style.html")
        route.fulfill(response=response)

    page.route("**/*.html", handler)
    response = page.goto(server.PREFIX + "/empty.html")
    assert response
    assert response.status == 200
    assert "one-style.css" in (response.body()).decode()


def test_RO_146_should_intercept_with_post_data_override(
    page: Page, server: Server
) -> None:
    def handler(route: Route) -> None:
        response = route.fetch(post_data={"foo": "bar"})
        route.fulfill(response=response)

    page.route("**/*.html", handler)
    with server.expect_request("/empty.html") as request_info:
        page.goto(server.PREFIX + "/empty.html")
    request = request_info.value
    assert request.post_body
    assert request.post_body.decode() == json.dumps({"foo": "bar"})


def test_RO_147_request_post_data_is_not_null_when_fetching_form_data_with_a_blob(
    page: Page, server: Server, browser_name: str
) -> None:
    # https://github.com/microsoft/playwright/issues/24077
    if browser_name == "webkit":
        pytest.skip("fixme: The body is empty in WebKit when intercepting")
    page.goto(server.EMPTY_PAGE)
    page.set_content(
        """
<script>
  function doStuff() {
    const formData = new FormData();
    formData.append('file', new Blob(["hello"], { type: "text/plain" }));
    fetch('/upload', {
      method: 'POST',
      body: formData
    });
  }
</script>
<body>
<button onclick="doStuff()" data-testid="click-me">Click me!</button>
</body>"""
    )
    methods: List[str] = []
    post_datas: List[Optional[str]] = []

    def handler(route: Route, request: Request) -> None:
        methods.append(request.method)
        post_datas.append(request.post_data)
        route.fulfill(status=200, body="ok")

    page.route(server.PREFIX + "/upload", handler)
    page.get_by_test_id("click-me").click()
    wait_for_list(page, post_datas)
    assert methods == ["POST"]
    post_data = post_datas[0]
    assert post_data
    assert 'Content-Disposition: form-data; name="file"; filename="blob"' in post_data
    assert "\r\nhello\r\n" in post_data


def test_RO_148_should_abort_favicon_requests_if_interception_is_enabled(
    page: Page, server: Server
) -> None:
    request_count = 0

    def handle_favicon(request: TestServerRequest) -> None:
        nonlocal request_count
        request_count += 1
        request.setHeader("content-type", "text/plain")
        request.write(b"my content")
        request.finish()

    server.set_route("/favicon.ico", handle_favicon)
    # Intercept all requests.
    page.route("**/*", lambda route: route.fulfill(status=200, body="Hello, world!"))
    page.goto(server.EMPTY_PAGE)
    response = page.evaluate(
        "() => fetch('/favicon.ico').then(r => r.text()).catch(e => 'load failed')"
    )
    assert response == "load failed"
    # Browsers can send favicon requests in the background.
    page.wait_for_timeout(1000)
    assert request_count == 0
