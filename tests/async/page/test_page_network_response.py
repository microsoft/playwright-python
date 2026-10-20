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

"""Port of tests/page/page-network-response.spec.ts."""

import asyncio
import base64
import re
import threading
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import pytest

from playwright.async_api import Error, Page, Request, Route
from tests.server import Server, TestServerRequest, reactor


def expect_failure(request: pytest.FixtureRequest, reason: str) -> None:
    """Like `it.fail()`: the test must fail."""
    request.applymarker(pytest.mark.xfail(reason=f"upstream: {reason}", strict=True))


def write_raw_response(
    server_request: TestServerRequest, headers: List[Tuple[str, str]]
) -> None:
    """Writes a 200 response with no body and closes the connection.

    Like `res.writeHead(200, headers); res.end()` in Node.js, which keeps the case of
    the header names. Twisted would change it.
    """
    assert server_request.transport
    head = "HTTP/1.1 200 OK\r\n"
    for name, value in headers:
        head += f"{name}: {value}\r\n"
    head += "Connection: close\r\n\r\n"
    server_request.transport.write(head.encode())
    server_request.transport.loseConnection()


async def test_NE_030_should_work_smoke(page: Page, server: Server) -> None:
    def handle(server_request: TestServerRequest) -> None:
        server_request.setHeader("foo", "bar")
        server_request.setHeader("BaZ", "bAz")
        server_request.finish()

    server.set_route("/empty.html", handle)
    response = await page.goto(server.EMPTY_PAGE)
    assert response
    assert (await response.all_headers())["foo"] == "bar"
    assert (await response.all_headers())["baz"] == "bAz"
    assert (await response.all_headers()).get("BaZ") is None


async def test_NE_031_should_return_multiple_header_value(
    page: Page, server: Server, browser_name: str, platform: str
) -> None:
    if browser_name == "webkit" and platform == "win32":
        pytest.skip("libcurl does not support non-set-cookie multivalue headers")

    def handle(server_request: TestServerRequest) -> None:
        # Write directly to the socket, to send the header names as they are.
        conn = server_request.transport
        assert conn
        conn.write(b"HTTP/1.1 200 OK\r\n")
        conn.write(b"Name-A: v1\r\n")
        conn.write(b"Name-a: v2\r\n")
        conn.write(b"name-A: v3\r\n")
        conn.write(b"\r\n")
        conn.loseConnection()

    server.set_route("/headers", handle)
    response = await page.goto(f"{server.PREFIX}/headers")
    assert response
    assert response.status == 200
    assert response.headers["name-a"] == "v1, v2, v3"


async def test_NE_032_should_return_text(page: Page, server: Server) -> None:
    response = await page.goto(server.PREFIX + "/simple.json")
    assert response
    assert await response.text() == '{"foo": "bar"}\n'


async def test_NE_033_should_return_uncompressed_text(
    page: Page, server: Server
) -> None:
    server.enable_gzip("/simple.json")
    response = await page.goto(server.PREFIX + "/simple.json")
    assert response
    assert response.headers["content-encoding"] == "gzip"
    assert await response.text() == '{"foo": "bar"}\n'


async def test_NE_034_should_return_uncompressed_text_for_brotli_encoding(
    page: Page, server: Server
) -> None:
    text = '{"foo": "bar"}\n'
    # zlib.brotliCompressSync(Buffer.from(text)) in Node.js: Python has no brotli module.
    compressed = base64.b64decode("CweAeyJmb28iOiAiYmFyIn0KAw==")

    def handle(server_request: TestServerRequest) -> None:
        server_request.setResponseCode(200)
        server_request.setHeader("Content-Type", "application/json")
        server_request.setHeader("Content-Encoding", "br")
        server_request.write(compressed)
        server_request.finish()

    server.set_route("/brotli.json", handle)
    response = await page.goto(server.PREFIX + "/brotli.json")
    assert response
    assert response.headers["content-encoding"] == "br"
    assert await response.text() == text


async def test_NE_035_should_return_text_for_identity_encoding(
    page: Page, server: Server
) -> None:
    text = "<div>hello</div>"

    def handle(server_request: TestServerRequest) -> None:
        server_request.setResponseCode(200)
        server_request.setHeader("Content-Type", "text/html; charset=utf-8")
        server_request.setHeader("Content-Encoding", "Identity")
        server_request.write(text.encode())
        server_request.finish()

    server.set_route("/identity.html", handle)
    response = await page.goto(server.PREFIX + "/identity.html")
    assert response
    assert response.headers["content-encoding"] == "Identity"
    assert await response.text() == text


async def test_NE_036_should_throw_when_requesting_body_of_redirected_response(
    page: Page, server: Server
) -> None:
    server.set_redirect("/foo.html", "/empty.html")
    response = await page.goto(server.PREFIX + "/foo.html")
    assert response
    redirected_from = response.request.redirected_from
    assert redirected_from
    redirected = await redirected_from.response()
    assert redirected
    assert redirected.status == 302
    with pytest.raises(Error) as exc_info:
        await redirected.text()
    assert (
        "Response body is unavailable for redirect responses" in exc_info.value.message
    )


async def test_NE_037_should_wait_until_response_completes(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    # Setup server to trap request.
    server_responses: List[TestServerRequest] = []

    def handle(server_request: TestServerRequest) -> None:
        server_responses.append(server_request)
        # In Firefox, |fetch| will be hanging until it receives |Content-Type| header
        # from server.
        server_request.setHeader("Content-Type", "text/plain; charset=utf-8")
        server_request.write(b"hello ")

    server.set_route("/get", handle)
    # Setup page to trap response.
    request_finished = False

    def on_request_finished(r: Request) -> None:
        nonlocal request_finished
        request_finished = request_finished or "/get" in r.url

    page.on("requestfinished", on_request_finished)
    # send request and wait for server response
    async with page.expect_event("response") as response_info:
        with server.expect_request("/get"):
            await page.evaluate("() => fetch('./get', { method: 'GET' })")
    page_response = await response_info.value

    assert server_responses
    assert page_response
    assert page_response.status == 200
    assert request_finished is False

    def finish_response() -> None:
        server_response = server_responses[0]
        # Write part of the response, then finish the response.
        reactor.callFromThread(server_response.write, b"wor")

        def end() -> None:
            server_response.write(b"ld!")
            server_response.finish()

        reactor.callFromThread(end)

    response_text = asyncio.create_task(page_response.text())
    await asyncio.sleep(0)
    finish_response()
    assert await response_text == "hello world!"


async def test_NE_038_should_return_json(page: Page, server: Server) -> None:
    response = await page.goto(server.PREFIX + "/simple.json")
    assert response
    assert await response.json() == {"foo": "bar"}


async def test_NE_039_should_return_body(
    page: Page, server: Server, assetdir: Path
) -> None:
    response = await page.goto(server.PREFIX + "/pptr.png")
    assert response
    image_buffer = (assetdir / "pptr.png").read_bytes()
    response_buffer = await response.body()
    assert response_buffer == image_buffer


async def test_NE_040_should_return_body_with_compression(
    page: Page, server: Server, assetdir: Path
) -> None:
    server.enable_gzip("/pptr.png")
    response = await page.goto(server.PREFIX + "/pptr.png")
    assert response
    image_buffer = (assetdir / "pptr.png").read_bytes()
    response_buffer = await response.body()
    assert response_buffer == image_buffer


async def test_NE_041_should_return_non_utf8_body_even_when_content_type_says_utf8(
    page: Page, server: Server, browser_name: str, browser_major_version: int
) -> None:
    if browser_name == "webkit":
        pytest.skip("fixme: webkit encodes the response body")
    if browser_name == "chromium" and browser_major_version < 151:
        pytest.skip(
            "fixme: older chromium re-encodes the non-utf8 response body and lacks Response.bytes()"
        )

    # Binary data with bytes that are invalid UTF-8.
    byte_values = [0x80, 0x81, 0x82, 0xFF, 0xFE, 0x00, 0x01, 0x02]
    buffer = bytes(byte_values)

    def handle(server_request: TestServerRequest) -> None:
        server_request.setResponseCode(200)
        server_request.setHeader("Content-Type", "text/plain;charset=UTF-8")
        server_request.setHeader("Content-Length", str(len(buffer)))
        server_request.write(buffer)
        server_request.finish()

    server.set_route("/binary-as-text", handle)
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_response(server.PREFIX + "/binary-as-text") as response_info:
        bytes_received = await page.evaluate(
            "url => fetch(url).then(r => r.bytes())", server.PREFIX + "/binary-as-text"
        )
    response = await response_info.value
    body = await response.body()
    assert body == buffer
    assert list(bytes_received) == byte_values


async def test_NE_042_should_return_status_text(page: Page, server: Server) -> None:
    def handle(server_request: TestServerRequest) -> None:
        server_request.setResponseCode(200, b"cool!")
        server_request.finish()

    server.set_route("/cool", handle)
    response = await page.goto(server.PREFIX + "/cool")
    assert response
    assert response.status_text == "cool!"


async def test_NE_043_should_report_all_headers(
    page: Page, server: Server, browser_name: str, platform: str
) -> None:
    if browser_name == "webkit" and platform == "win32":
        pytest.skip("libcurl does not support non-set-cookie multivalue headers")

    expected_headers = {
        "header-a": ["value-a", "value-a-1", "value-a-2"],
        "header-b": ["value-b"],
    }

    def handle(server_request: TestServerRequest) -> None:
        write_raw_response(
            server_request,
            [
                (name, value)
                for name, values in expected_headers.items()
                for value in values
            ],
        )

    server.set_route("/headers", handle)

    await page.goto(server.EMPTY_PAGE)
    async with page.expect_response("**/*") as response_info:
        await page.evaluate("() => fetch('/headers')")
    response = await response_info.value
    headers = await response.headers_array()
    actual_headers: Dict[str, List[str]] = {}
    for header in headers:
        actual_headers.setdefault(header["name"], []).append(header["value"])
    for name in [
        "Keep-Alive",
        "keep-alive",
        "Connection",
        "connection",
        "Date",
        "date",
        "Transfer-Encoding",
        "transfer-encoding",
    ]:
        actual_headers.pop(name, None)
    assert actual_headers == expected_headers


async def test_NE_044_should_report_multiple_set_cookie_headers(
    page: Page, server: Server
) -> None:
    def handle(server_request: TestServerRequest) -> None:
        server_request.setResponseCode(200)
        server_request.responseHeaders.addRawHeader("Set-Cookie", "a=b")
        server_request.responseHeaders.addRawHeader("Set-Cookie", "c=d")
        server_request.write(b"\r\n")
        server_request.finish()

    server.set_route("/headers", handle)

    await page.goto(server.EMPTY_PAGE)
    async with page.expect_response("**/*") as response_info:
        await page.evaluate("() => fetch('/headers')")
    response = await response_info.value
    headers = await response.headers_array()
    cookies = [
        header["value"] for header in headers if header["name"].lower() == "set-cookie"
    ]
    assert cookies == ["a=b", "c=d"]
    assert await response.header_value("not-there") is None
    assert await response.header_value("set-cookie") == "a=b\nc=d"
    assert await response.header_values("set-cookie") == ["a=b", "c=d"]


async def test_NE_045_should_behave_the_same_way_for_headers_and_all_headers(
    page: Page, server: Server, browser_name: str, platform: str
) -> None:
    if browser_name == "webkit" and platform == "win32":
        pytest.skip("libcurl does not support non-set-cookie multivalue headers")

    def handle(server_request: TestServerRequest) -> None:
        headers: List[Tuple[str, str]] = [
            ("Set-Cookie", "a=b"),
            ("Set-Cookie", "c=d"),
            ("header-a", "a=b"),
            ("header-a", "c=d"),
            ("Name-A", "v1"),
            ("name-b", "v4"),
            ("Name-a", "v2"),
            ("name-A", "v3"),
        ]
        # Chromium does not report set-cookie headers immediately, so they are missing from .headers()
        if browser_name == "chromium":
            headers = [header for header in headers if header[0] != "Set-Cookie"]

        server_request.setResponseCode(200)
        for name, value in headers:
            server_request.responseHeaders.addRawHeader(name, value)
        server_request.write(b"\r\n")
        server_request.finish()

    server.set_route("/headers", handle)

    await page.goto(server.EMPTY_PAGE)
    async with page.expect_response("**/*") as response_info:
        await page.evaluate("() => fetch('/headers')")
    response = await response_info.value
    all_headers = await response.all_headers()
    assert response.headers == all_headers
    assert all_headers["header-a"] == "a=b, c=d"
    assert all_headers["name-a"] == "v1, v2, v3"
    assert all_headers["name-b"] == "v4"


async def test_NE_046_should_provide_a_response_with_a_file_url(
    page: Page,
    assetdir: Path,
    is_win: bool,
    browser_name: str,
    browser_channel: Optional[str],
) -> None:
    if browser_name == "firefox":
        pytest.skip("Firefox does return null for file:// URLs")
    if browser_channel == "webkit-wsl":
        pytest.skip("webkit-wsl")

    fileurl = (assetdir / "frames" / "two-frames.html").as_uri()
    response = await page.goto(fileurl)
    assert response
    if browser_name == "chromium" or (browser_name == "webkit" and is_win):
        assert response.status == 200
    else:
        assert response.status == 0
    assert response.ok is True


async def test_NE_047_should_return_set_cookie_header_after_route_fulfill(
    page: Page, server: Server, browser_name: str, request: pytest.FixtureRequest
) -> None:
    if browser_name == "webkit" or browser_name == "chromium":
        expect_failure(request, "https://github.com/microsoft/playwright/issues/11035")

    async def handle(route: Route) -> None:
        await route.fulfill(
            status=200,
            headers={"set-cookie": "a=b"},
            content_type="text/plain",
            body="",
        )

    await page.route("**/*", handle)
    response = await page.goto(server.EMPTY_PAGE)
    assert response
    headers = await response.all_headers()
    assert headers.get("set-cookie") == "a=b"


async def test_NE_048_should_return_headers_after_route_fulfill(
    page: Page, server: Server
) -> None:
    async def handle(route: Route) -> None:
        await route.fulfill(
            status=200,
            headers={"foo": "bar", "content-language": "en"},
            content_type="text/plain",
            body="done",
        )

    await page.route("**/*", handle)
    response = await page.goto(server.EMPTY_PAGE)
    assert response
    assert await response.all_headers() == {
        "foo": "bar",
        "content-type": "text/plain",
        "content-length": "4",
        "content-language": "en",
    }


async def test_NE_049_should_report_if_request_was_from_service_worker(
    page: Page, server: Server
) -> None:
    res = await page.goto(server.PREFIX + "/serviceworkers/fetch/sw.html")
    assert res
    assert res.from_service_worker is False
    await page.evaluate("() => window['activationPromise']")
    async with page.expect_response(re.compile(r"example\.txt")) as response_info:
        await page.evaluate("() => fetch('/example.txt')")
    res = await response_info.value
    assert res.from_service_worker is True


async def test_NE_050_should_return_body_for_prefetch_script(
    page: Page, server: Server, browser_name: str, browser_major_version: int
) -> None:
    if browser_name == "webkit":
        pytest.skip("No prefetch in WebKit: https://caniuse.com/link-rel-prefetch")
    if browser_name == "chromium" and browser_major_version < 138:
        pytest.skip("Requires Sec-Purpose header, shipped in Chrome 138")
    async with page.expect_response("**/prefetch.js") as response_info:
        await page.goto(server.PREFIX + "/prefetch.html")
    response = await response_info.value
    body = await response.body()
    assert body.decode() == "// Scripts will be pre-fetched"


async def test_NE_051_should_return_body_for_image_with_evicted_body(
    page: Page, server: Server, is_mac: bool, browser_name: str
) -> None:
    if is_mac and browser_name == "webkit":
        pytest.skip("fixme: WebKit on Mac evicts the body and returns empty buffer")
    image_base64 = "R0lGODlhAQABAAAAACw="  # truncated 1x1 gif, Chromium evicts its body

    def end(server_request: TestServerRequest, body: bytes) -> None:
        # Like res.end(body) in Node.js, which sets Content-Length.
        server_request.setHeader("content-length", str(len(body)))
        server_request.write(body)
        server_request.finish()

    def handle_gif(server_request: TestServerRequest) -> None:
        server_request.setHeader("content-type", "image/gif")
        end(server_request, base64.b64decode(image_base64))

    def handle_page(server_request: TestServerRequest) -> None:
        server_request.setHeader("content-type", "text/html")
        end(server_request, b'<html><body><img src="/pixel.gif"></body></html>')

    server.set_route("/pixel.gif", handle_gif)
    server.set_route("/page.html", handle_page)
    async with page.expect_response("**/pixel.gif") as response_info:
        await page.goto(server.PREFIX + "/page.html")
    response = await response_info.value
    body = await response.body()
    assert base64.b64encode(body).decode() == image_base64


async def test_NE_052_should_bypass_disk_cache_when_page_interception_is_enabled(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/frames/one-frame.html")
    await page.route("**/api*", lambda route: route.continue_())

    def cached_route(
        requests: List[TestServerRequest],
    ) -> Callable[[TestServerRequest], None]:
        def handle(server_request: TestServerRequest) -> None:
            requests.append(server_request)
            server_request.setResponseCode(200)
            server_request.setHeader("content-type", "text/plain")
            server_request.setHeader("cache-control", "public, max-age=31536000")
            server_request.write(b"Hello")
            server_request.finish()

        return handle

    main_frame_requests: List[TestServerRequest] = []
    server.set_route("/api", cached_route(main_frame_requests))
    for i in range(3):
        # Step: main frame iteration i.
        async with page.expect_response("**/api") as response_info:
            await page.evaluate(
                """async () => {
                    const response = await fetch('/api');
                    return response.status;
                }"""
            )
        response = await response_info.value
        assert response.status == 200
        assert len(main_frame_requests) == i + 1

    subframe_requests: List[TestServerRequest] = []
    server.set_route("/frame/api", cached_route(subframe_requests))
    for i in range(3):
        # Step: subframe iteration i.
        async with page.expect_response("**/frame/api") as response_info:
            frame = page.frame(url="**/frame.html")
            assert frame
            await frame.evaluate(
                """async () => {
                    const response = await fetch('/frame/api');
                    return response.status;
                }"""
            )
        response = await response_info.value
        assert response.status == 200
        assert len(subframe_requests) == i + 1


async def test_NE_053_request_existing_response_should_return_null_before_response_is_received(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    server_responses: List[TestServerRequest] = []
    server_got_request = threading.Event()

    def handle(server_request: TestServerRequest) -> None:
        server_responses.append(server_request)
        server_got_request.set()
        # Don't end the response yet

    server.set_route("/get", handle)

    async with page.expect_event("request") as request_info:
        await page.evaluate("() => { void fetch('./get', { method: 'GET' }); }")
    request = await request_info.value
    # Like server.waitForRequest('/get').
    while not server_got_request.is_set():
        await page.wait_for_timeout(10)

    # Response hasn't been received yet
    assert request.existing_response is None

    # Now send the response
    def end() -> None:
        server_response = server_responses[0]
        server_response.setHeader("Content-Type", "text/plain; charset=utf-8")
        server_response.write(b"done")
        server_response.finish()

    async with page.expect_event("response"):
        reactor.callFromThread(end)

    # After response is received, existingResponse should return the response
    existing_response = request.existing_response
    assert existing_response is not None
    assert existing_response.status == 200


async def test_NE_054_request_existing_response_should_return_the_response_after_it_is_received(
    page: Page, server: Server
) -> None:
    response = await page.goto(server.EMPTY_PAGE)
    assert response
    request = response.request
    assert request.existing_response is response


async def test_NE_055_should_return_http_version(page: Page, server: Server) -> None:
    response = await page.goto(server.EMPTY_PAGE)
    assert response
    assert await response.http_version() == "HTTP/1.1"


async def test_NE_056_response_form_data_should_parse_multipart_form_data_in_page_context(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    result = await page.evaluate(
        """async () => {
            const boundary = '----WebKitFormBoundary1234';
            const body = [
                `--${boundary}`,
                'Content-Disposition: form-data; name="field1"',
                '',
                'value1',
                `--${boundary}`,
                'Content-Disposition: form-data; name="file1"; filename="test.txt"',
                'Content-Type: text/plain',
                '',
                'hello',
                `--${boundary}--`,
            ].join('\\r\\n');
            const response = new Response(body, {
                headers: { 'Content-Type': `multipart/form-data; boundary=${boundary}` },
            });
            const fd = await response.formData();
            const file = fd.get('file1');
            return {
                field1: fd.get('field1'),
                filename: file instanceof File ? file.name : null,
                fileContent: file instanceof File ? await file.text() : null,
            };
        }"""
    )
    assert result["field1"] == "value1"
    assert result["filename"] == "test.txt"
    assert result["fileContent"] == "hello"


async def test_NE_057_should_give_a_readable_error_when_response_body_races_with_navigation(
    page: Page, server: Server, browser_name: str
) -> None:
    if browser_name == "firefox":
        pytest.skip(
            "Firefox keeps the response body available after navigating away, so it never throws"
        )
    async with page.expect_response(server.PREFIX + "/title.html") as response_info:
        await page.goto(server.PREFIX + "/title.html")
    response = await response_info.value
    # Navigate away — the browser frees the network resource from the first page load.
    # The first page must have a non-empty body, otherwise WebKit returns an empty buffer instead of throwing.
    await page.goto(server.PREFIX + "/grid.html")
    with pytest.raises(Error) as exc_info:
        await response.body()
    assert isinstance(exc_info.value, Error)
    assert "navigated away" in exc_info.value.message
