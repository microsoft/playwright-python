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

import json
from typing import Any, Dict, List
from urllib.parse import parse_qs

import pytest

from playwright.sync_api import BrowserContext, Error, FilePayload, Page
from tests.server import Server
from tests.utils import must


def test_get_should_work(context: BrowserContext, server: Server) -> None:
    response = context.request.get(server.PREFIX + "/simple.json")
    assert response.url == server.PREFIX + "/simple.json"
    assert response.status == 200
    assert response.status_text == "OK"
    assert response.ok is True
    assert response.headers["content-type"] == "application/json"
    assert {
        "name": "Content-Type",
        "value": "application/json",
    } in response.headers_array
    assert response.text() == '{"foo": "bar"}\n'


def test_fetch_should_work(context: BrowserContext, server: Server) -> None:
    response = context.request.fetch(server.PREFIX + "/simple.json")
    assert response.url == server.PREFIX + "/simple.json"
    assert response.status == 200
    assert response.status_text == "OK"
    assert response.ok is True
    assert response.headers["content-type"] == "application/json"
    assert {
        "name": "Content-Type",
        "value": "application/json",
    } in response.headers_array
    assert response.text() == '{"foo": "bar"}\n'


def test_should_throw_on_network_error(context: BrowserContext, server: Server) -> None:
    server.set_route("/test", lambda request: request.loseConnection())
    with pytest.raises(Error, match="socket hang up"):
        context.request.fetch(server.PREFIX + "/test")


def test_should_add_session_cookies_to_request(
    context: BrowserContext, server: Server
) -> None:
    context.add_cookies(
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
    with server.expect_request("/empty.html") as server_req:
        context.request.get(server.EMPTY_PAGE)
    assert server_req.value.getHeader("Cookie") == "username=John Doe"


@pytest.mark.parametrize(
    "method", ["fetch", "delete", "get", "head", "patch", "post", "put"]
)
def test_should_support_query_params(
    context: BrowserContext, server: Server, method: str
) -> None:
    expected_params = {"p1": "v1", "парам2": "знач2"}
    with server.expect_request("/empty.html") as server_req:
        getattr(context.request, method)(
            server.EMPTY_PAGE + "?p1=foo", params=expected_params
        )
    assert list(map(lambda x: x.decode(), server_req.value.args["p1".encode()])) == [
        "foo",
        "v1",
    ]
    assert server_req.value.args["парам2".encode()][0].decode() == "знач2"


@pytest.mark.parametrize(
    "method", ["fetch", "delete", "get", "head", "patch", "post", "put"]
)
def test_should_support_params_passed_as_object(
    context: BrowserContext, server: Server, method: str
) -> None:
    params = {
        "param1": "value1",
        "парам2": "знач2",
    }
    with server.expect_request("/empty.html") as server_req:
        getattr(context.request, method)(server.EMPTY_PAGE, params=params)
    assert server_req.value.args["param1".encode()][0].decode() == "value1"
    assert len(server_req.value.args["param1".encode()]) == 1
    assert server_req.value.args["парам2".encode()][0].decode() == "знач2"


@pytest.mark.parametrize(
    "method", ["fetch", "delete", "get", "head", "patch", "post", "put"]
)
def test_should_support_params_passed_as_strings(
    context: BrowserContext, server: Server, method: str
) -> None:
    params = "?param1=value1&param1=value2&парам2=знач2"
    with server.expect_request("/empty.html") as server_req:
        getattr(context.request, method)(server.EMPTY_PAGE, params=params)
    assert list(
        map(lambda x: x.decode(), server_req.value.args["param1".encode()])
    ) == ["value1", "value2"]
    assert len(server_req.value.args["param1".encode()]) == 2
    assert server_req.value.args["парам2".encode()][0].decode() == "знач2"


@pytest.mark.parametrize(
    "method", ["fetch", "delete", "get", "head", "patch", "post", "put"]
)
def test_should_support_fail_on_status_code(
    context: BrowserContext, server: Server, method: str
) -> None:
    with pytest.raises(Error, match="404 Not Found"):
        getattr(context.request, method)(
            server.PREFIX + "/this-does-clearly-not-exist.html",
            fail_on_status_code=True,
        )


@pytest.mark.parametrize(
    "method", ["fetch", "delete", "get", "head", "patch", "post", "put"]
)
def test_should_support_ignore_https_errors_option(
    context: BrowserContext, https_server: Server, method: str
) -> None:
    response = getattr(context.request, method)(
        https_server.EMPTY_PAGE, ignore_https_errors=True
    )
    assert response.ok
    assert response.status == 200


def test_should_not_add_context_cookie_if_cookie_header_passed_as_parameter(
    context: BrowserContext, server: Server
) -> None:
    context.add_cookies(
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
    with server.expect_request("/empty.html") as server_req:
        context.request.get(server.EMPTY_PAGE, headers={"Cookie": "foo=bar"})
    assert server_req.value.getHeader("Cookie") == "foo=bar"


@pytest.mark.parametrize("method", ["delete", "patch", "post", "put"])
def test_should_support_post_data(
    context: BrowserContext, method: str, server: Server
) -> None:
    def support_post_data(fetch_data: Any, request_post_data: Any) -> None:
        with server.expect_request("/simple.json") as request:
            response = getattr(context.request, method)(
                server.PREFIX + "/simple.json", data=fetch_data
            )
        assert request.value.method.decode() == method.upper()
        assert request.value.post_body == request_post_data
        assert response.status == 200
        assert response.url == server.PREFIX + "/simple.json"
        assert request.value.getHeader("Content-Length") == str(
            len(must(request.value.post_body))
        )

    support_post_data("My request", "My request".encode())
    support_post_data(b"My request", "My request".encode())
    support_post_data(["my", "request"], json.dumps(["my", "request"]).encode())
    support_post_data({"my": "request"}, json.dumps({"my": "request"}).encode())
    with pytest.raises(Error, match="Unsupported 'data' type: <class 'function'>"):
        support_post_data(lambda: None, None)


def test_should_support_application_x_www_form_urlencoded(
    context: BrowserContext, server: Server
) -> None:
    with server.expect_request("/empty.html") as server_req:
        context.request.post(
            server.PREFIX + "/empty.html",
            form={
                "firstName": "John",
                "lastName": "Doe",
                "file": "f.js",
            },
        )
    assert server_req.value.method == b"POST"
    assert (
        server_req.value.getHeader("Content-Type")
        == "application/x-www-form-urlencoded"
    )
    body = must(server_req.value.post_body).decode()
    assert server_req.value.getHeader("Content-Length") == str(len(body))
    params: Dict[bytes, List[bytes]] = parse_qs(server_req.value.post_body)
    assert params[b"firstName"] == [b"John"]
    assert params[b"lastName"] == [b"Doe"]
    assert params[b"file"] == [b"f.js"]


def test_should_support_multipart_form_data(
    context: BrowserContext, server: Server
) -> None:
    file: FilePayload = {
        "name": "f.js",
        "mimeType": "text/javascript",
        "buffer": b"var x = 10;\r\n;console.log(x);",
    }
    with server.expect_request("/empty.html") as server_req:
        context.request.post(
            server.PREFIX + "/empty.html",
            multipart={
                "firstName": "John",
                "lastName": "Doe",
                "file": file,
            },
        )
    assert server_req.value.method == b"POST"
    content_type = server_req.value.getHeader("Content-Type")
    assert content_type
    assert content_type.startswith("multipart/form-data; ")
    assert server_req.value.getHeader("Content-Length") == str(
        len(must(server_req.value.post_body))
    )
    assert server_req.value.args[b"firstName"] == [b"John"]
    assert server_req.value.args[b"lastName"] == [b"Doe"]
    assert server_req.value.args[b"file"][0] == file["buffer"]


def test_should_add_default_headers(
    context: BrowserContext, page: Page, server: Server
) -> None:
    with server.expect_request("/empty.html") as server_req:
        context.request.get(server.EMPTY_PAGE)
    assert server_req.value.getHeader("Accept") == "*/*"
    assert server_req.value.getHeader("Accept-Encoding") == "gzip,deflate,br"
    assert server_req.value.getHeader("User-Agent") == page.evaluate(
        "() => navigator.userAgent"
    )
