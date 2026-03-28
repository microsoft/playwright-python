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

from playwright.async_api import Page
from tests.server import Server, TestServerRequest


async def test_response_body_should_return_correct_utf8_bytes_for_sse_stream(
    page: Page, server: Server
) -> None:
    """
    Test that response.body() returns correct UTF-8 bytes for SSE streaming responses.
    
    Regression test for: https://github.com/microsoft/playwright-python/issues/3023
    
    The issue: response.body() was returning double-encoded UTF-8 bytes (mojibake)
    for SSE streams, caused by CDP Network.getResponseBody returning a string
    instead of bytes.
    """
    
    # Test data with UTF-8 characters (Chinese + emoji)
    test_messages = [
        "你好，这是第一条消息",  # Chinese: "Hello, this is the first message"
        "测试中文：😀🎉",        # Chinese + emoji
    ]
    
    # Build SSE response body
    sse_body = ""
    for msg in test_messages:
        sse_body += f"data: {msg}\n\n"
    
    expected_bytes = sse_body.encode("utf-8")
    
    # Set up SSE endpoint
    def handle_sse(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "text/event-stream; charset=utf-8")
        request.setHeader("Cache-Control", "no-cache")
        request.write(sse_body.encode("utf-8"))
        request.finish()
    
    server.set_route("/sse", handle_sse)
    
    # Collect response body via page.on("response")
    response_body_bytes = None
    
    async def on_response(response):
        nonlocal response_body_bytes
        if "/sse" in response.url:
            response_body_bytes = await response.body()
    
    page.on("response", on_response)
    
    # Trigger the SSE request
    await page.goto(server.PREFIX + "/sse")
    
    # Wait for response to be captured
    await page.wait_for_timeout(500)
    
    # Assertion 1: response.body() should return correct UTF-8 bytes
    assert response_body_bytes is not None, "SSE response was not captured"
    
    # Assertion 2: Bytes should NOT be double-encoded (mojibake check)
    # Mojibake pattern: UTF-8 -> Latin-1 decode -> UTF-8 encode
    # For "你好" (correct: \xe4\xbd\xa0), mojibake would be \xc3\xa4\xc2\xbd\xc2\xa0
    assert response_body_bytes == expected_bytes, (
        f"Response body has incorrect encoding.\n"
        f"Expected: {expected_bytes!r}\n"
        f"Got: {response_body_bytes!r}\n"
        f"This indicates double-encoding (mojibake)."
    )
    
    # Assertion 3: Decoded text should match original messages
    decoded_text = response_body_bytes.decode("utf-8")
    for msg in test_messages:
        assert msg in decoded_text, f"Expected message '{msg}' not found in response"


async def test_response_body_utf8_vs_route_fetch_consistency(
    page: Page, server: Server
) -> None:
    """
    Verify that response.body() and route.fetch() return consistent UTF-8 bytes.
    
    Regression test for: https://github.com/microsoft/playwright-python/issues/3023
    
    Before fix: route.fetch() returned correct bytes, but response.body() returned mojibake.
    After fix: both should return identical bytes.
    """
    
    # Test data with UTF-8 characters
    test_content = "测试内容：Hello 世界! 🌍"
    
    def handle_endpoint(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "text/plain; charset=utf-8")
        request.write(test_content.encode("utf-8"))
        request.finish()
    
    server.set_route("/test", handle_endpoint)
    
    # Method 1: Capture via route.fetch()
    route_fetch_bytes = None
    
    async def handle_route(route):
        nonlocal route_fetch_bytes
        response = await route.fetch()
        route_fetch_bytes = await response.body()
        await route.fulfill(response=response)
    
    await page.route("**/test", handle_route)
    
    # Method 2: Capture via page.on("response")
    response_body_bytes = None
    
    async def on_response(response):
        nonlocal response_body_bytes
        if "/test" in response.url:
            response_body_bytes = await response.body()
    
    page.on("response", on_response)
    
    # Trigger the request
    await page.goto(server.PREFIX + "/test")
    
    # Wait for both captures
    await page.wait_for_timeout(500)
    
    # Assertion 1: Both methods should capture the response
    assert route_fetch_bytes is not None, "route.fetch() did not capture response"
    assert response_body_bytes is not None, "response.body() did not capture response"
    
    # Assertion 2: Both should return identical bytes
    assert route_fetch_bytes == response_body_bytes, (
        f"Inconsistent encoding detected!\n"
        f"route.fetch(): {route_fetch_bytes!r}\n"
        f"response.body(): {response_body_bytes!r}\n"
        f"These should be identical."
    )
    
    # Assertion 3: Content should decode correctly
    decoded = response_body_bytes.decode("utf-8")
    assert test_content in decoded, f"Expected content not found in response"
