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

import asyncio
import json
import time
from pathlib import Path
from typing import Any, List, Optional, Tuple

import pytest

from playwright.async_api import Error, Page, Request, Route
from tests.server import Server, TestServerRequest
from tests.utils import relative_path


async def wait_for_list(page: Page, values: List[Any]) -> None:
    """Waits until a route handler adds to values.

    Port of awaiting the promise that upstream's route handler resolves.
    """
    deadline = time.monotonic() + 10
    while not values:
        assert time.monotonic() < deadline, "the route handler did not run"
        await page.wait_for_timeout(20)


async def test_RO_134_should_fulfill_intercepted_response(
    page: Page, server: Server
) -> None:
    async def handler(route: Route) -> None:
        response = await page.request.fetch(route.request)
        await route.fulfill(
            response=response,
            status=201,
            headers={"foo": "bar"},
            content_type="text/plain",
            body="Yo, page!",
        )

    await page.route("**/*", handler)
    response = await page.goto(server.PREFIX + "/empty.html")
    assert response
    assert response.status == 201
    assert response.headers["foo"] == "bar"
    assert response.headers["content-type"] == "text/plain"
    assert await page.evaluate("() => document.body.textContent") == "Yo, page!"


async def test_RO_135_should_fulfill_response_with_empty_body(
    page: Page, server: Server, browser_name: str, browser_major_version: int
) -> None:
    if browser_name == "chromium" and browser_major_version <= 91:
        pytest.skip("Fails in Electron that uses old Chromium")

    async def handler(route: Route) -> None:
        response = await page.request.fetch(route.request)
        await route.fulfill(
            response=response,
            headers={"content-length": "0"},
            status=201,
            body="",
        )

    await page.route("**/*", handler)
    response = await page.goto(server.PREFIX + "/title.html")
    assert response
    assert response.status == 201
    assert await response.text() == ""


async def test_RO_136_should_override_with_defaults_when_intercepted_response_not_provided(
    page: Page, server: Server, browser_name: str
) -> None:
    def handle_empty(request: TestServerRequest) -> None:
        request.setHeader("foo", "bar")
        request.write(b"my content")
        request.finish()

    server.set_route("/empty.html", handle_empty)

    async def handler(route: Route) -> None:
        await page.request.fetch(route.request)
        await route.fulfill(status=201)

    await page.route("**/*", handler)
    response = await page.goto(server.EMPTY_PAGE)
    assert response
    assert response.status == 201
    assert await response.text() == ""
    if browser_name == "webkit":
        assert response.headers == {"content-type": "text/plain"}
    else:
        assert response.headers == {}


async def test_RO_137_should_fulfill_with_any_response(
    page: Page, server: Server
) -> None:
    def handle_sample(request: TestServerRequest) -> None:
        request.setHeader("foo", "bar")
        request.write(b"Woo-hoo")
        request.finish()

    server.set_route("/sample", handle_sample)
    sample_response = await page.request.get(f"{server.PREFIX}/sample")

    await page.route(
        "**/*",
        lambda route: route.fulfill(
            response=sample_response,
            status=201,
            content_type="text/plain",
        ),
    )
    response = await page.goto(server.EMPTY_PAGE)
    assert response
    assert response.status == 201
    assert await response.text() == "Woo-hoo"
    assert response.headers["foo"] == "bar"


async def test_RO_138_should_support_fulfill_after_intercept(
    page: Page, server: Server, assetdir: Path
) -> None:
    async def handler(route: Route) -> None:
        response = await page.request.fetch(route.request)
        await route.fulfill(response=response)

    await page.route("**", handler)
    with server.expect_request("/title.html") as request_info:
        response = await page.goto(server.PREFIX + "/title.html")
    request = request_info.value
    assert request.uri.decode() == "/title.html"
    original = (assetdir / "title.html").read_text(encoding="utf-8")
    assert response
    assert await response.text() == original


async def test_RO_139_should_give_access_to_the_intercepted_response(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)

    routes: List[Route] = []
    await page.route("**/title.html", lambda route: routes.append(route))

    async def evaluate() -> None:
        await page.evaluate("url => fetch(url)", server.PREFIX + "/title.html")

    async def check_and_fulfill() -> None:
        await wait_for_list(page, routes)
        route = routes[0]
        response = await page.request.fetch(route.request)

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

        await route.fulfill(response=response)

    await asyncio.gather(evaluate(), check_and_fulfill())


async def test_RO_140_should_give_access_to_the_intercepted_response_body(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)

    routes: List[Route] = []
    await page.route("**/simple.json", lambda route: routes.append(route))

    async def evaluate() -> None:
        try:
            await page.evaluate("url => fetch(url)", server.PREFIX + "/simple.json")
        except Error:
            pass

    async def check_and_fulfill() -> None:
        await wait_for_list(page, routes)
        route = routes[0]
        response = await page.request.fetch(route.request)

        assert await response.text() == '{"foo": "bar"}\n'

        await route.fulfill(response=response)

    await asyncio.gather(evaluate(), check_and_fulfill())


async def test_RO_141_should_intercept_multipart_form_data_request_body(
    page: Page, server: Server, assetdir: Path, browser_name: str
) -> None:
    # https://github.com/microsoft/playwright/issues/14624
    if browser_name != "firefox":
        pytest.skip("fixme")
    await page.goto(server.PREFIX + "/input/fileupload.html")
    file_path = relative_path(assetdir / "file-to-upload.txt")
    await page.locator("input[type=file]").set_input_files(file_path)
    requests: List[Request] = []
    await page.route("**/upload", lambda route: requests.append(route.request))
    await page.click("input[type=submit]", no_wait_after=True)
    await wait_for_list(page, requests)
    request = requests[0]
    assert request.method == "POST"
    assert Path(file_path).read_text(encoding="utf-8") in (request.post_data or "")


async def test_RO_142_should_fulfill_intercepted_response_using_alias(
    page: Page, server: Server
) -> None:
    async def handler(route: Route) -> None:
        response = await route.fetch()
        await route.fulfill(response=response)

    await page.route("**/*", handler)
    response = await page.goto(server.PREFIX + "/empty.html")
    assert response
    assert response.status == 200
    assert "text/html" in response.headers["content-type"]


async def test_RO_143_should_support_timeout_option_in_route_fetch(
    page: Page, server: Server
) -> None:
    def handle_slow(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("content-length", "4096")
        request.setHeader("content-type", "text/html")
        request.write(b"")

    server.set_route("/slow", handle_slow)

    fetch_errors: List[Optional[Error]] = []

    async def handler(route: Route) -> None:
        try:
            await route.fetch(timeout=1000)
            fetch_errors.append(None)
        except Error as e:
            fetch_errors.append(e)

    await page.route("**/*", handler)
    with pytest.raises(Error) as exc_info:
        await page.goto(server.PREFIX + "/slow", timeout=2000)
    assert "Timeout 2000ms exceeded" in exc_info.value.message
    await wait_for_list(page, fetch_errors)
    fetch_error = fetch_errors[0]
    assert fetch_error
    assert "Route.fetch: Timeout 1000ms exceeded" in fetch_error.message


async def test_RO_144_should_not_follow_redirects_when_max_redirects_is_set_to_0_in_route_fetch(
    page: Page, server: Server
) -> None:
    server.set_redirect("/foo", "/empty.html")
    fetched: List[Tuple[Optional[str], int]] = []

    async def handler(route: Route) -> None:
        response = await route.fetch(max_redirects=0)
        fetched.append((response.headers.get("location"), response.status))
        await route.fulfill(body="hello")

    await page.route("**/*", handler)
    await page.goto(server.PREFIX + "/foo")
    assert "hello" in await page.content()
    assert fetched == [("/empty.html", 302)]


async def test_RO_145_should_intercept_with_url_override(
    page: Page, server: Server
) -> None:
    async def handler(route: Route) -> None:
        response = await route.fetch(url=server.PREFIX + "/one-style.html")
        await route.fulfill(response=response)

    await page.route("**/*.html", handler)
    response = await page.goto(server.PREFIX + "/empty.html")
    assert response
    assert response.status == 200
    assert "one-style.css" in (await response.body()).decode()


async def test_RO_146_should_intercept_with_post_data_override(
    page: Page, server: Server
) -> None:
    async def handler(route: Route) -> None:
        response = await route.fetch(post_data={"foo": "bar"})
        await route.fulfill(response=response)

    await page.route("**/*.html", handler)
    with server.expect_request("/empty.html") as request_info:
        await page.goto(server.PREFIX + "/empty.html")
    request = request_info.value
    assert request.post_body
    assert request.post_body.decode() == json.dumps(
        {"foo": "bar"}, separators=(",", ":")
    )


async def test_RO_147_request_post_data_is_not_null_when_fetching_form_data_with_a_blob(
    page: Page, server: Server, browser_name: str
) -> None:
    # https://github.com/microsoft/playwright/issues/24077
    if browser_name == "webkit":
        pytest.skip("fixme: The body is empty in WebKit when intercepting")
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
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

    async def handler(route: Route, request: Request) -> None:
        methods.append(request.method)
        post_datas.append(request.post_data)
        await route.fulfill(status=200, body="ok")

    await page.route(server.PREFIX + "/upload", handler)
    await page.get_by_test_id("click-me").click()
    await wait_for_list(page, post_datas)
    assert methods == ["POST"]
    post_data = post_datas[0]
    assert post_data
    assert 'Content-Disposition: form-data; name="file"; filename="blob"' in post_data
    assert "\r\nhello\r\n" in post_data


async def test_RO_148_should_abort_favicon_requests_if_interception_is_enabled(
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
    await page.route(
        "**/*", lambda route: route.fulfill(status=200, body="Hello, world!")
    )
    await page.goto(server.EMPTY_PAGE)
    response = await page.evaluate(
        "() => fetch('/favicon.ico').then(r => r.text()).catch(e => 'load failed')"
    )
    assert response == "load failed"
    # Browsers can send favicon requests in the background.
    await page.wait_for_timeout(1000)
    assert request_count == 0
