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

# The upstream file has this notice:
#
# Copyright (c) 2014-present Matt Zabriskie
# Modifications copyright (c) Microsoft Corporation.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""Port of tests/library/browsercontext-fetch-algorithms.spec.ts."""

import gzip
import zlib

import pytest

from playwright.async_api import BrowserContext
from tests.server import Server, TestServerRequest

RESPONSE_BODY = "str"

ZIPPED = {
    "gzip": gzip.compress(RESPONSE_BODY.encode()),
    "deflate": zlib.compress(RESPONSE_BODY.encode()),
    # zlib.brotliCompressSync('str') in Node.js: Python has no brotli encoder.
    "br": bytes.fromhex("0b018073747203"),
}

ENCODINGS = list(ZIPPED.keys())


@pytest.mark.parametrize("encoding", ENCODINGS)
async def test_FE_180_algorithms_decompression_should_support_decompression(
    context: BrowserContext, server: Server, encoding: str
) -> None:
    def handler(request: TestServerRequest) -> None:
        request.setHeader("Content-Encoding", encoding)
        # Node.js sets Content-Length when res.end() gets the whole body.
        request.setHeader("Content-Length", str(len(ZIPPED[encoding])))
        request.write(ZIPPED[encoding])
        request.finish()

    server.set_route("/compressed", handler)

    response = await context.request.get(server.PREFIX + "/compressed")
    assert await response.text() == RESPONSE_BODY


@pytest.mark.parametrize("encoding", ENCODINGS)
async def test_FE_181_algorithms_decompression_should_not_fail_if_response_content_length_header_is_missing(
    context: BrowserContext, server: Server, encoding: str
) -> None:
    def handler(request: TestServerRequest) -> None:
        request.setHeader("Content-Encoding", encoding)
        # Without Content-Length, the response is chunked, as in Node.js.
        request.write(ZIPPED[encoding])
        request.finish()

    server.set_route("/compressed", handler)

    response = await context.request.get(server.PREFIX + "/compressed")
    assert await response.text() == RESPONSE_BODY


@pytest.mark.parametrize("encoding", ENCODINGS)
async def test_FE_182_algorithms_decompression_should_not_fail_with_chunked_responses_without_content_length_header(
    context: BrowserContext, server: Server, encoding: str
) -> None:
    def handler(request: TestServerRequest) -> None:
        request.setHeader("Content-Encoding", encoding)
        request.setHeader("Transfer-Encoding", "chunked")
        request.write(ZIPPED[encoding])
        request.finish()

    server.set_route("/compressed", handler)

    response = await context.request.get(server.PREFIX + "/compressed")
    assert await response.text() == RESPONSE_BODY


@pytest.mark.parametrize("encoding", ENCODINGS)
async def test_FE_183_algorithms_decompression_should_not_fail_with_an_empty_response_without_content_length_header_z_buf_error(
    context: BrowserContext, server: Server, encoding: str
) -> None:
    def handler(request: TestServerRequest) -> None:
        request.setHeader("Content-Encoding", encoding)
        request.finish()

    server.set_route("/compressed", handler)

    response = await context.request.get(server.PREFIX + "/compressed")
    assert await response.text() == ""


@pytest.mark.parametrize("encoding", ENCODINGS)
async def test_FE_184_algorithms_decompression_should_not_fail_with_an_empty_response_with_content_length_header_z_buf_error(
    context: BrowserContext, server: Server, encoding: str
) -> None:
    def handler(request: TestServerRequest) -> None:
        request.setHeader("Content-Encoding", encoding)
        # Node.js sends Content-Length: 0 for res.end() without a body.
        request.setHeader("Content-Length", "0")
        request.finish()

    server.set_route("/compressed", handler)

    await context.request.get(server.PREFIX + "/compressed")
