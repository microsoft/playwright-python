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

"""Port of tests/page/page-network-sizes.spec.ts."""

import gzip
import math
import re
from email.utils import formatdate
from pathlib import Path

import pytest

from playwright.async_api import Error, Page
from tests.server import Server, TestServerRequest


def end(server_request: TestServerRequest, body: bytes) -> None:
    """Like res.end(body) in Node.js, which also sends these headers.

    Without Content-Length, twisted sends the body in chunks, and the chunk headers
    count in the response body size.
    """
    server_request.setHeader("Content-Length", str(len(body)))
    server_request.setHeader("Date", formatdate(usegmt=True))
    server_request.setHeader("Connection", "keep-alive")
    server_request.setHeader("Keep-Alive", "timeout=5")
    server_request.write(body)
    server_request.finish()


async def test_NE_058_should_set_body_size_and_headers_size(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_event("request") as request_info:
        await page.evaluate(
            "() => fetch('./get', { method: 'POST', body: '12345' }).then(r => r.text())"
        )
    request = await request_info.value
    sizes = await request.sizes()
    assert sizes["requestBodySize"] == 5
    assert sizes["requestHeadersSize"] >= 250


async def test_NE_059_should_set_body_size_to_0_if_there_was_no_body(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_event("request") as request_info:
        await page.evaluate("() => fetch('./get').then(r => r.text())")
    request = await request_info.value
    sizes = await request.sizes()
    assert sizes["requestBodySize"] == 0
    assert sizes["requestHeadersSize"] >= 190


async def test_NE_060_should_set_body_size_headers_size_and_transfer_size(
    page: Page, server: Server
) -> None:
    def handle(server_request: TestServerRequest) -> None:
        # In Firefox, |fetch| will be hanging until it receives |Content-Type| header
        # from server.
        server_request.setHeader("Content-Type", "text/plain; charset=utf-8")
        end(server_request, b"abc134")

    server.set_route("/get", handle)
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_event("response") as response_info:
        with server.expect_request("/get"):
            await page.evaluate("async () => fetch('./get').then(r => r.text())")
    response = await response_info.value
    sizes = await response.request.sizes()
    assert sizes["responseBodySize"] == 6
    assert sizes["responseHeadersSize"] >= 100


async def test_NE_061_should_set_body_size_to_0_when_there_was_no_response_body(
    page: Page, server: Server
) -> None:
    response = await page.goto(server.EMPTY_PAGE)
    assert response
    sizes = await response.request.sizes()
    assert sizes["responseBodySize"] == 0
    assert sizes["responseHeadersSize"] >= 150


async def test_NE_062_should_have_the_correct_response_body_size(
    page: Page, server: Server, assetdir: Path
) -> None:
    response = await page.goto(server.PREFIX + "/simplezip.json")
    assert response
    sizes = await response.request.sizes()
    assert sizes["responseBodySize"] == (assetdir / "simplezip.json").stat().st_size


async def test_NE_063_should_have_the_correct_response_body_size_for_chunked_request(
    page: Page, server: Server, assetdir: Path, browser_name: str, platform: str
) -> None:
    if browser_name == "firefox":
        pytest.skip("fixme")
    if browser_name == "webkit" and platform != "darwin":
        pytest.skip("fixme")
    content = (assetdir / "simplezip.json").read_bytes()
    AMOUNT_OF_CHUNKS = 10
    CHUNK_SIZE = math.ceil(len(content) / AMOUNT_OF_CHUNKS)

    def handle(server_request: TestServerRequest) -> None:
        server_request.setResponseCode(200)
        server_request.setHeader("Content-Type", "text/html; charset=utf-8")
        server_request.setHeader("Transfer-Encoding", "chunked")
        # Twisted sends each write as its own chunk.
        for start in range(0, len(content), CHUNK_SIZE):
            stop = min(start + CHUNK_SIZE, len(content))
            server_request.write(content[start:stop])
        server_request.finish()

    server.set_route("/chunked-simplezip.json", handle)
    response = await page.goto(server.PREFIX + "/chunked-simplezip.json")
    assert response
    sizes = await response.request.sizes()
    # The actual file size is 5100 bytes. The extra 75 bytes are coming from the chunked encoding headers and end bytes.
    if browser_name == "webkit":
        # WebKit on macOS reports 5173 with the legacy CFNetwork loader (builds <= 2346) and the
        # correct 5175 with NWLoader. TODO: expect 5175 once the NWLoader-based build ships.
        assert sizes["responseBodySize"] in [5173, 5175]
    else:
        assert sizes["responseBodySize"] == 5175


async def test_NE_064_should_have_the_correct_response_body_size_with_gzip_compression(
    page: Page,
    server: Server,
    assetdir: Path,
) -> None:
    server.enable_gzip("/simplezip.json")
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_event("response") as response_info:
        await page.evaluate("() => fetch('./simplezip.json').then(r => r.text())")
    response = await response_info.value
    sizes = await response.request.sizes()

    # Compress the file as the test server does.
    compressed = gzip.compress((assetdir / "simplezip.json").read_bytes())

    assert sizes["responseBodySize"] == len(compressed)


async def test_NE_065_should_handle_redirects(page: Page, server: Server) -> None:
    server.set_redirect("/foo", "/bar")
    server.set_route("/bar", lambda server_request: end(server_request, b"bar"))
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_event("response") as response_info:
        await page.evaluate(
            """async () => fetch('/foo', {
                method: 'POST',
                body: '12345',
            }).then(r => r.text())"""
        )
    response = await response_info.value
    assert (await response.request.sizes())["requestBodySize"] == 5
    new_request = response.request.redirected_to
    assert new_request
    assert (await new_request.sizes())["responseBodySize"] == 3


async def test_NE_066_should_throw_for_failed_requests(
    page: Page, server: Server
) -> None:
    def handle(server_request: TestServerRequest) -> None:
        server_request.setHeader("Content-Type", "text/css")
        assert server_request.transport
        server_request.transport.loseConnection()

    server.set_route("/one-style.css", handle)
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_event("requestfailed") as request_info:
        await page.goto(server.PREFIX + "/one-style.html")
    request = await request_info.value
    with pytest.raises(Error) as exc_info:
        await request.sizes()
    assert "Unable to fetch sizes for failed request" in exc_info.value.message


@pytest.mark.parametrize("status_code", [200, 401, 404, 500])
async def test_NE_067_should_work_with_status_code(
    page: Page, server: Server, status_code: int
) -> None:
    def handle(server_request: TestServerRequest) -> None:
        server_request.setResponseCode(status_code)
        server_request.setHeader("Content-Type", "text/plain; charset=utf-8")
        server_request.setHeader("Content-Length", "3")
        server_request.write(b"bar")
        server_request.finish()

    server.set_route("/foo", handle)
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_event("response") as response_info:
        await page.evaluate(
            """async () => fetch('/foo', {
                method: 'POST',
                body: '12345',
            }).then(r => r.text())"""
        )
    response = await response_info.value
    assert response.status == status_code
    sizes = await response.request.sizes()
    assert sizes["requestBodySize"] == 5
    assert sizes["responseBodySize"] == 3


async def test_NE_068_should_have_correct_response_body_size_for_404_with_content(
    page: Page, server: Server, browser_name: str
) -> None:
    if browser_name == "chromium":
        pytest.skip("fixme")

    def handle_image(server_request: TestServerRequest) -> None:
        server_request.setResponseCode(404)
        end(server_request, b"<p>this should have a non-negative size</p>")

    def handle_page(server_request: TestServerRequest) -> None:
        end(
            server_request,
            b"""
    <!DOCTYPE html>
    <html>
      <head><title>Page with Broken Image</title></head>
      <body>
        <img src="/broken-image.png" />
      </body>
    </html>
    """,
        )

    server.set_route("/broken-image.png", handle_image)
    server.set_route("/page-with-404-image.html", handle_page)

    async with page.expect_request(re.compile(r"broken-image\.png$")) as request_info:
        await page.goto(server.PREFIX + "/page-with-404-image.html")
    req = await request_info.value

    response_body_size = (await req.sizes())["responseBodySize"]
    assert response_body_size >= 0


async def test_NE_069_should_return_sizes_without_hanging(
    page: Page, server: Server, browser_name: str
) -> None:
    if browser_name == "chromium":
        pytest.skip("fixme")

    def handle(server_request: TestServerRequest) -> None:
        end(
            server_request,
            b"""
    <!DOCTYPE html>
    <html>
      <head><title>t</title></head>
      <body>
        <script>
          fetch("./404");
        </script>
      </body>
    </html>
    """,
        )

    server.set_route("/has-abandoned-fetch", handle)

    async with page.expect_request(re.compile(r"404$")) as request_info:
        await page.goto(server.PREFIX + "/has-abandoned-fetch")
    req = await request_info.value

    await req.sizes()
