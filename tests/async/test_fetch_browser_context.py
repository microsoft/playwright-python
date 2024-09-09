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

import asyncio
import base64
import json
from typing import Any, Callable, cast
from urllib.parse import parse_qs

import pytest

from playwright.async_api import Browser, BrowserContext, Error, FilePayload, Page
from tests.server import Server, TestServerRequest
from tests.utils import must


async def test_get_should_work(context: BrowserContext, server: Server) -> None:
    response = await context.request.get(server.PREFIX + "/simple.json")
    assert response.url == server.PREFIX + "/simple.json"
    assert response.status == 200
    assert response.status_text == "OK"
    assert response.ok is True
    assert response.headers["content-type"] == "application/json"
    assert {
        "name": "Content-Type",
        "value": "application/json",
    } in response.headers_array
    assert await response.text() == '{"foo": "bar"}\n'


async def test_fetch_should_work(context: BrowserContext, server: Server) -> None:
    response = await context.request.fetch(server.PREFIX + "/simple.json")
    assert response.url == server.PREFIX + "/simple.json"
    assert response.status == 200
    assert response.status_text == "OK"
    assert response.ok is True
    assert response.headers["content-type"] == "application/json"
    assert {
        "name": "Content-Type",
        "value": "application/json",
    } in response.headers_array
    assert await response.text() == '{"foo": "bar"}\n'


async def test_should_throw_on_network_error(
    context: BrowserContext, server: Server
) -> None:
    server.set_route("/test", lambda request: request.loseConnection())
    with pytest.raises(Error, match="socket hang up"):
        await context.request.fetch(server.PREFIX + "/test")


async def test_should_add_session_cookies_to_request(
    context: BrowserContext, server: Server
) -> None:
    await context.add_cookies(
        [
            {
                "name": "username",
                "value": "John Doe",
                "url": server.EMPTY_PAGE,
                "expires": -1,
                "httpOnly": False,
                "secure": False,
                "sameSite": "Lax",
            }
        ]
    )
    [server_req, response] = await asyncio.gather(
        server.wait_for_request("/empty.html"),
        context.request.get(server.EMPTY_PAGE),
    )
    assert server_req.getHeader("Cookie") == "username=John Doe"


@pytest.mark.parametrize(
    "method", ["fetch", "delete", "get", "head", "patch", "post", "put"]
)
async def test_should_support_query_params(
    context: BrowserContext, server: Server, method: str
) -> None:
    expected_params = {"p1": "v1", "парам2": "знач2"}
    [server_req, _] = await asyncio.gather(
        server.wait_for_request("/empty.html"),
        getattr(context.request, method)(
            server.EMPTY_PAGE + "?p1=foo", params=expected_params
        ),
    )
    assert list(map(lambda x: x.decode(), server_req.args["p1".encode()])) == [
        "foo",
        "v1",
    ]
    assert server_req.args["парам2".encode()][0].decode() == "знач2"


@pytest.mark.parametrize(
    "method", ["fetch", "delete", "get", "head", "patch", "post", "put"]
)
async def test_should_support_params_passed_as_object(
    context: BrowserContext, server: Server, method: str
) -> None:
    params = {
        "param1": "value1",
        "парам2": "знач2",
    }
    [server_req, _] = await asyncio.gather(
        server.wait_for_request("/empty.html"),
        getattr(context.request, method)(server.EMPTY_PAGE, params=params),
    )
    assert server_req.args["param1".encode()][0].decode() == "value1"
    assert len(server_req.args["param1".encode()]) == 1
    assert server_req.args["парам2".encode()][0].decode() == "знач2"


@pytest.mark.parametrize(
    "method", ["fetch", "delete", "get", "head", "patch", "post", "put"]
)
async def test_should_support_params_passed_as_strings(
    context: BrowserContext, server: Server, method: str
) -> None:
    params = "?param1=value1&param1=value2&парам2=знач2"
    [server_req, _] = await asyncio.gather(
        server.wait_for_request("/empty.html"),
        getattr(context.request, method)(server.EMPTY_PAGE, params=params),
    )
    assert list(map(lambda x: x.decode(), server_req.args["param1".encode()])) == [
        "value1",
        "value2",
    ]
    assert len(server_req.args["param1".encode()]) == 2
    assert server_req.args["парам2".encode()][0].decode() == "знач2"


@pytest.mark.parametrize(
    "method", ["fetch", "delete", "get", "head", "patch", "post", "put"]
)
async def test_should_support_fail_on_status_code(
    context: BrowserContext, server: Server, method: str
) -> None:
    with pytest.raises(Error, match="404 Not Found"):
        await getattr(context.request, method)(
            server.PREFIX + "/this-does-clearly-not-exist.html",
            fail_on_status_code=True,
        )


@pytest.mark.parametrize(
    "method", ["fetch", "delete", "get", "head", "patch", "post", "put"]
)
async def test_should_support_ignore_https_errors_option(
    context: BrowserContext, https_server: Server, method: str
) -> None:
    response = await getattr(context.request, method)(
        https_server.EMPTY_PAGE, ignore_https_errors=True
    )
    assert response.ok
    assert response.status == 200


async def test_should_not_add_context_cookie_if_cookie_header_passed_as_parameter(
    context: BrowserContext, server: Server
) -> None:
    await context.add_cookies(
        [
            {
                "name": "username",
                "value": "John Doe",
                "url": server.EMPTY_PAGE,
                "expires": -1,
                "httpOnly": False,
                "secure": False,
                "sameSite": "Lax",
            }
        ]
    )
    [server_req, _] = await asyncio.gather(
        server.wait_for_request("/empty.html"),
        context.request.get(server.EMPTY_PAGE, headers={"Cookie": "foo=bar"}),
    )
    assert server_req.getHeader("Cookie") == "foo=bar"


async def test_should_support_http_credentials_send_immediately_for_browser_context(
    context_factory: "Callable[..., asyncio.Future[BrowserContext]]", server: Server
) -> None:
    context = await context_factory(
        http_credentials={
            "username": "user",
            "password": "pass",
            "origin": server.PREFIX.upper(),
            "send": "always",
        }
    )
    # First request
    server_request, response = await asyncio.gather(
        server.wait_for_request("/empty.html"), context.request.get(server.EMPTY_PAGE)
    )
    expected_auth = "Basic " + base64.b64encode(b"user:pass").decode()
    assert server_request.getHeader("authorization") == expected_auth
    assert response.status == 200

    # Second request
    server_request, response = await asyncio.gather(
        server.wait_for_request("/empty.html"),
        context.request.get(server.CROSS_PROCESS_PREFIX + "/empty.html"),
    )
    # Not sent to another origin.
    assert server_request.getHeader("authorization") is None
    assert response.status == 200


async def test_support_http_credentials_send_immediately_for_browser_new_page(
    server: Server, browser: Browser
) -> None:
    page = await browser.new_page(
        http_credentials={
            "username": "user",
            "password": "pass",
            "origin": server.PREFIX.upper(),
            "send": "always",
        }
    )
    server_request, response = await asyncio.gather(
        server.wait_for_request("/empty.html"), page.request.get(server.EMPTY_PAGE)
    )
    assert (
        server_request.getHeader("authorization")
        == "Basic " + base64.b64encode(b"user:pass").decode()
    )
    assert response.status == 200

    server_request, response = await asyncio.gather(
        server.wait_for_request("/empty.html"),
        page.request.get(server.CROSS_PROCESS_PREFIX + "/empty.html"),
    )
    # Not sent to another origin.
    assert server_request.getHeader("authorization") is None
    assert response.status == 200

    await page.close()


@pytest.mark.parametrize("method", ["delete", "patch", "post", "put"])
async def test_should_support_post_data(
    context: BrowserContext, method: str, server: Server
) -> None:
    async def support_post_data(fetch_data: Any, request_post_data: Any) -> None:
        [request, response] = await asyncio.gather(
            server.wait_for_request("/simple.json"),
            getattr(context.request, method)(
                server.PREFIX + "/simple.json", data=fetch_data
            ),
        )
        assert request.method.decode() == method.upper()
        assert request.post_body == request_post_data
        assert response.status == 200
        assert response.url == server.PREFIX + "/simple.json"
        assert request.getHeader("Content-Length") == str(len(must(request.post_body)))

    await support_post_data("My request", "My request".encode())
    await support_post_data(b"My request", "My request".encode())
    await support_post_data(["my", "request"], json.dumps(["my", "request"]).encode())
    await support_post_data({"my": "request"}, json.dumps({"my": "request"}).encode())
    with pytest.raises(Error, match="Unsupported 'data' type: <class 'function'>"):
        await support_post_data(lambda: None, None)


async def test_should_support_application_x_www_form_urlencoded(
    context: BrowserContext, server: Server
) -> None:
    [request, response] = await asyncio.gather(
        server.wait_for_request("/empty.html"),
        context.request.post(
            server.PREFIX + "/empty.html",
            form={
                "firstName": "John",
                "lastName": "Doe",
                "file": "f.js",
            },
        ),
    )
    assert request.method == b"POST"
    assert request.getHeader("Content-Type") == "application/x-www-form-urlencoded"
    assert request.post_body
    body = request.post_body.decode()
    assert request.getHeader("Content-Length") == str(len(body))
    params = parse_qs(request.post_body)
    assert params[b"firstName"] == [b"John"]
    assert params[b"lastName"] == [b"Doe"]
    assert params[b"file"] == [b"f.js"]


async def test_should_support_multipart_form_data(
    context: BrowserContext, server: Server
) -> None:
    file: FilePayload = {
        "name": "f.js",
        "mimeType": "text/javascript",
        "buffer": b"var x = 10;\r\n;console.log(x);",
    }
    [request, _] = await asyncio.gather(
        server.wait_for_request("/empty.html"),
        context.request.post(
            server.PREFIX + "/empty.html",
            multipart={
                "firstName": "John",
                "lastName": "Doe",
                "file": file,
            },
        ),
    )
    assert request.method == b"POST"
    assert cast(str, request.getHeader("Content-Type")).startswith(
        "multipart/form-data; "
    )
    assert must(request.getHeader("Content-Length")) == str(
        len(must(request.post_body))
    )
    assert request.args[b"firstName"] == [b"John"]
    assert request.args[b"lastName"] == [b"Doe"]
    assert request.args[b"file"][0] == file["buffer"]


async def test_should_add_default_headers(
    context: BrowserContext, page: Page, server: Server
) -> None:
    [request, response] = await asyncio.gather(
        server.wait_for_request("/empty.html"),
        context.request.get(server.EMPTY_PAGE),
    )
    assert request.getHeader("Accept") == "*/*"
    assert request.getHeader("Accept-Encoding") == "gzip,deflate,br"
    assert request.getHeader("User-Agent") == await page.evaluate(
        "() => navigator.userAgent"
    )


async def test_should_work_after_context_dispose(
    context: BrowserContext, server: Server
) -> None:
    await context.close(reason="Test ended.")
    with pytest.raises(Error, match="Test ended."):
        await context.request.get(server.EMPTY_PAGE)


async def test_should_retry_ECONNRESET(context: BrowserContext, server: Server) -> None:
    request_count = 0

    def _handle_request(req: TestServerRequest) -> None:
        nonlocal request_count
        request_count += 1
        if request_count <= 3:
            assert req.transport
            req.transport.abortConnection()
            return
        req.setHeader("content-type", "text/plain")
        req.write(b"Hello!")
        req.finish()

    server.set_route("/test", _handle_request)
    response = await context.request.fetch(server.PREFIX + "/test", max_retries=3)
    assert response.status == 200
    assert await response.text() == "Hello!"
    assert request_count == 4
