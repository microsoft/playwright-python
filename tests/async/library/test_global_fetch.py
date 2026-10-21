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

"""Port of tests/library/global-fetch.spec.ts."""

import asyncio
import base64
import json
import os
import platform
import re
import socket
import ssl
import threading
import time
from pathlib import Path
from typing import Any, Awaitable, Callable, List
from urllib.parse import urlparse

import pytest

from playwright._impl._driver import compute_driver_executable
from playwright.async_api import APIResponse, Error, Playwright
from tests.helpers.raw_http_server import RawHttpServer, write_response
from tests.helpers.raw_request_headers import raw_headers, record_raw_headers
from tests.server import Server, TestServerRequest

SECURITY_DETAILS = {
    "issuer": "playwright-test",
    "protocol": "TLSv1.3",
    "subjectName": "playwright-test",
    "validFrom": 1691708270,
    "validTo": 2007068270,
}

HTTP_METHODS = ["GET", "PUT", "POST", "OPTIONS", "HEAD", "PATCH"]


async def catch_error(awaitable: Awaitable[Any]) -> Any:
    """Port of `promise.catch(e => e)`."""
    try:
        return await awaitable
    except Error as error:
        return error


def node_arch() -> str:
    """The value of os.arch() in Node.js on this machine."""
    machine = platform.machine().lower()
    return {
        "x86_64": "x64",
        "amd64": "x64",
        "aarch64": "arm64",
        "arm64": "arm64",
        "i386": "ia32",
        "i686": "ia32",
    }.get(machine, machine)


def driver_version() -> str:
    """Port of getPlaywrightVersion(): the version of the driver package."""
    package_json = Path(compute_driver_executable()[1]).parent / "package.json"
    return json.loads(package_json.read_text())["version"]


@pytest.mark.parametrize(
    "method", ["fetch", "delete", "get", "head", "patch", "post", "put"]
)
async def test_FE_001_should_work_smoke(
    playwright: Playwright, server: Server, method: str
) -> None:
    request = await playwright.request.new_context()
    response: APIResponse = await getattr(request, method)(
        server.PREFIX + "/simple.json"
    )
    assert response.url == server.PREFIX + "/simple.json"
    assert response.status == 200
    assert response.status_text == "OK"
    assert response.ok
    assert response.headers["content-type"] == "application/json; charset=utf-8"
    assert {
        "name": "Content-Type",
        "value": "application/json; charset=utf-8",
    } in response.headers_array
    assert await response.text() == ("" if method == "head" else '{"foo": "bar"}\n')
    await request.dispose()


async def test_FE_002_should_dispose_global_request(
    playwright: Playwright, server: Server
) -> None:
    request = await playwright.request.new_context()
    response = await request.get(server.PREFIX + "/simple.json")
    assert await response.json() == {"foo": "bar"}
    await request.dispose()
    with pytest.raises(Error) as exc_info:
        await response.body()
    assert "Response has been disposed" in exc_info.value.message
    await request.dispose()


async def test_FE_003_should_support_global_user_agent_option(
    playwright: Playwright, server: Server
) -> None:
    request = await playwright.request.new_context(user_agent="My Agent")
    with server.expect_request("/empty.html") as server_request_info:
        response = await request.get(server.EMPTY_PAGE)
    assert response.ok
    assert response.url == server.EMPTY_PAGE
    assert server_request_info.value.getHeader("user-agent") == "My Agent"
    await request.dispose()


async def test_FE_004_should_support_global_timeout_option(
    playwright: Playwright, server: Server
) -> None:
    request = await playwright.request.new_context(timeout=100)
    server.set_route("/empty.html", lambda req: None)
    with pytest.raises(Error) as exc_info:
        await request.get(server.EMPTY_PAGE)
    assert "APIRequestContext.get: Timeout 100ms exceeded" in exc_info.value.message
    await request.dispose()


async def test_FE_005_should_propagate_extra_http_headers_with_redirects(
    playwright: Playwright, server: Server
) -> None:
    server.set_redirect("/a/redirect1", "/b/c/redirect2")
    server.set_redirect("/b/c/redirect2", "/simple.json")
    request = await playwright.request.new_context(
        extra_http_headers={"My-Secret": "Value"}
    )
    with server.expect_request("/a/redirect1") as req1_info:
        with server.expect_request("/b/c/redirect2") as req2_info:
            with server.expect_request("/simple.json") as req3_info:
                await request.get(f"{server.PREFIX}/a/redirect1")
    assert req1_info.value.getHeader("my-secret") == "Value"
    assert req2_info.value.getHeader("my-secret") == "Value"
    assert req3_info.value.getHeader("my-secret") == "Value"
    await request.dispose()


async def test_FE_006_should_preserve_authorization_on_same_origin_redirect_but_strip_on_cross_origin(
    playwright: Playwright, server: Server
) -> None:
    server.set_redirect("/same/redirect", "/same/dest")
    server.set_redirect("/cross/redirect", server.CROSS_PROCESS_PREFIX + "/cross/dest")
    request = await playwright.request.new_context(
        extra_http_headers={"Authorization": "Bearer secret"},
    )

    with server.expect_request("/same/dest") as same_dest_req_info:
        await request.get(f"{server.PREFIX}/same/redirect")
    assert same_dest_req_info.value.getHeader("authorization") == "Bearer secret"

    with server.expect_request("/cross/dest") as cross_dest_req_info:
        await request.get(f"{server.PREFIX}/cross/redirect")
    assert cross_dest_req_info.value.getHeader("authorization") is None

    await request.dispose()


async def test_FE_007_should_support_global_http_credentials_option(
    playwright: Playwright, server: Server
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    request1 = await playwright.request.new_context()
    response1 = await request1.get(server.EMPTY_PAGE)
    assert response1.status == 401
    await request1.dispose()

    request2 = await playwright.request.new_context(
        http_credentials={"username": "user", "password": "pass"}
    )
    response2 = await request2.get(server.EMPTY_PAGE)
    assert response2.status == 200
    await request2.dispose()


async def test_FE_008_should_return_error_with_wrong_credentials(
    playwright: Playwright, server: Server
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    request = await playwright.request.new_context(
        http_credentials={"username": "user", "password": "wrong"}
    )
    response = await request.get(server.EMPTY_PAGE)
    assert response.status == 401
    await request.dispose()


async def test_FE_009_should_work_with_correct_credentials_and_matching_origin(
    playwright: Playwright, server: Server
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    request = await playwright.request.new_context(
        http_credentials={
            "username": "user",
            "password": "pass",
            "origin": server.PREFIX,
        }
    )
    response = await request.get(server.EMPTY_PAGE)
    assert response.status == 200
    await request.dispose()


async def test_FE_010_should_work_with_correct_credentials_and_matching_origin_case_insensitive(
    playwright: Playwright, server: Server
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    request = await playwright.request.new_context(
        http_credentials={
            "username": "user",
            "password": "pass",
            "origin": server.PREFIX.upper(),
        }
    )
    response = await request.get(server.EMPTY_PAGE)
    assert response.status == 200
    await request.dispose()


async def test_FE_011_should_return_error_with_correct_credentials_and_mismatching_scheme(
    playwright: Playwright, server: Server
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    request = await playwright.request.new_context(
        http_credentials={
            "username": "user",
            "password": "pass",
            "origin": server.PREFIX.replace("http://", "https://"),
        }
    )
    response = await request.get(server.EMPTY_PAGE)
    assert response.status == 401
    await request.dispose()


async def test_FE_012_should_return_error_with_correct_credentials_and_mismatching_hostname(
    playwright: Playwright, server: Server
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    hostname = urlparse(server.PREFIX).hostname
    assert hostname
    origin = server.PREFIX.replace(hostname, "mismatching-hostname")
    request = await playwright.request.new_context(
        http_credentials={"username": "user", "password": "pass", "origin": origin}
    )
    response = await request.get(server.EMPTY_PAGE)
    assert response.status == 401
    await request.dispose()


async def test_FE_013_should_return_error_with_correct_credentials_and_mismatching_port(
    playwright: Playwright, server: Server
) -> None:
    server.set_auth("/empty.html", "user", "pass")
    origin = server.PREFIX.replace(str(server.PORT), str(server.PORT + 1))
    request = await playwright.request.new_context(
        http_credentials={"username": "user", "password": "pass", "origin": origin}
    )
    response = await request.get(server.EMPTY_PAGE)
    assert response.status == 401
    await request.dispose()


async def test_FE_014_should_support_www_authenticate_basic(
    playwright: Playwright, server: Server
) -> None:
    credentials: List[str] = []

    def handler(req: TestServerRequest) -> None:
        authorization = req.getHeader("authorization")
        if not authorization:
            req.setResponseCode(401)
            req.setHeader("WWW-Authenticate", "Basic")
            req.write(b"HTTP Error 401 Unauthorized: Access is denied")
            req.finish()
            return
        parts = authorization.split(" ")
        credentials.append(
            base64.b64decode(parts[1] if len(parts) > 1 else "").decode()
        )
        req.setResponseCode(200)
        req.setHeader("content-type", "text/plain")
        req.finish()

    server.set_route("/empty.html", handler)
    request = await playwright.request.new_context(
        http_credentials={"username": "user", "password": "pass"}
    )
    response = await request.get(server.EMPTY_PAGE)
    assert response.status == 200
    assert credentials == ["user:pass"]
    await request.dispose()


async def test_FE_015_should_support_http_credentials_send(
    playwright: Playwright, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/30534
    request = await playwright.request.new_context(
        http_credentials={
            "username": "user",
            "password": "pass",
            "origin": server.PREFIX.upper(),
            "send": "always",
        }
    )
    with server.expect_request("/empty.html") as server_request_info:
        response = await request.get(server.EMPTY_PAGE)
    assert (
        server_request_info.value.getHeader("authorization")
        == "Basic " + base64.b64encode(b"user:pass").decode()
    )
    assert response.status == 200

    with server.expect_request("/empty.html") as server_request_info:
        response = await request.get(server.CROSS_PROCESS_PREFIX + "/empty.html")
    # Not sent to another origin.
    assert server_request_info.value.getHeader("authorization") is None
    assert response.status == 200
    await request.dispose()


async def test_FE_016_should_support_multiple_http_credentials(
    playwright: Playwright, server: Server
) -> None:
    server.set_auth("/empty.html", "user1", "pass1")
    request = await playwright.request.new_context(
        http_credentials=[
            {"username": "user1", "password": "pass1", "origin": server.PREFIX},
            {
                "username": "user2",
                "password": "pass2",
                "origin": server.CROSS_PROCESS_PREFIX,
            },
        ]
    )
    response1 = await request.get(server.EMPTY_PAGE)
    assert response1.status == 200
    # Wrong credentials are picked for the other origin.
    response2 = await request.get(server.CROSS_PROCESS_PREFIX + "/empty.html")
    assert response2.status == 401
    await request.dispose()


async def test_FE_017_should_support_http_credentials_send_with_multiple_http_credentials(
    playwright: Playwright, server: Server
) -> None:
    request = await playwright.request.new_context(
        http_credentials=[
            {
                "username": "user1",
                "password": "pass1",
                "origin": server.PREFIX,
                "send": "always",
            },
            {
                "username": "user2",
                "password": "pass2",
                "origin": server.CROSS_PROCESS_PREFIX,
                "send": "unauthorized",
            },
        ]
    )
    with server.expect_request("/empty.html") as server_request_info:
        response = await request.get(server.EMPTY_PAGE)
    assert (
        server_request_info.value.getHeader("authorization")
        == "Basic " + base64.b64encode(b"user1:pass1").decode()
    )
    assert response.status == 200

    with server.expect_request("/empty.html") as server_request_info:
        response = await request.get(server.CROSS_PROCESS_PREFIX + "/empty.html")
    # This origin has send: 'unauthorized', so credentials are not sent proactively.
    assert server_request_info.value.getHeader("authorization") is None
    assert response.status == 200
    await request.dispose()


async def test_FE_018_should_support_global_ignore_https_errors_option(
    playwright: Playwright, https_server: Server
) -> None:
    request = await playwright.request.new_context(ignore_https_errors=True)
    response = await request.get(https_server.EMPTY_PAGE)
    assert response.status == 200
    await request.dispose()


async def test_FE_019_should_propagate_ignore_https_errors_on_redirects(
    playwright: Playwright, https_server: Server
) -> None:
    https_server.set_redirect("/redir", "/empty.html")
    request = await playwright.request.new_context()
    response = await request.get(
        https_server.PREFIX + "/redir", ignore_https_errors=True
    )
    assert response.status == 200
    await request.dispose()


async def test_FE_020_should_return_server_address_from_response(
    playwright: Playwright, server: Server
) -> None:
    request = await playwright.request.new_context()
    # The second request reuses the keep-alive socket and should report the address as well.
    for _ in range(2):
        response = await request.get(server.EMPTY_PAGE)
        addr = await response.server_addr()
        assert addr
        assert re.match(r"^(127\.0\.0\.1|::1)$", addr["ipAddress"])
        assert addr["port"] == server.PORT
    await request.dispose()


async def test_FE_021_should_return_security_details_from_response(
    playwright: Playwright, https_server: Server
) -> None:
    request = await playwright.request.new_context(ignore_https_errors=True)
    # The second request reuses the keep-alive socket and should report the details as well.
    for _ in range(2):
        response = await request.get(https_server.EMPTY_PAGE)
        assert await response.security_details() == SECURITY_DETAILS
    await request.dispose()


async def test_FE_022_should_return_security_details_for_a_resumed_tls_session(
    playwright: Playwright, https_server: Server
) -> None:
    expected = SECURITY_DETAILS
    request = await playwright.request.new_context(ignore_https_errors=True)
    # 'Connection: close' drops the socket, so the next request opens a new one and resumes
    # the cached TLS session. A resumed session does not carry the server certificate.
    first = await request.get(https_server.EMPTY_PAGE, headers={"connection": "close"})
    assert await first.security_details() == expected
    second = await request.get(https_server.EMPTY_PAGE)
    assert await second.security_details() == expected
    await request.dispose()


async def test_FE_023_should_return_null_security_details_for_http_response(
    playwright: Playwright, server: Server
) -> None:
    request = await playwright.request.new_context()
    response = await request.get(server.EMPTY_PAGE)
    assert await response.security_details() is None
    await request.dispose()


async def test_FE_024_should_return_security_details_for_certificate_with_multiple_cn_attributes(
    playwright: Playwright, assetdir: Path
) -> None:
    # https://github.com/microsoft/playwright/issues/41815
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(
        assetdir / "multi-value-rdn" / "cert.pem",
        assetdir / "multi-value-rdn" / "key.pem",
    )

    def handler(sock: socket.socket, head: bytes) -> None:
        write_response(
            sock,
            "200 OK",
            ["Content-Type: application/json"],
            json.dumps({"ok": True}).encode(),
        )

    server = RawHttpServer(handler, ssl_context)
    try:
        request = await playwright.request.new_context(ignore_https_errors=True)
        response = await request.get(f"https://localhost:{server.port}/")
        assert response.status == 200
        security_details = await response.security_details()
        assert security_details
        assert security_details.get("subjectName") == "localhost"
        assert security_details.get("issuer") == "localhost"
        await request.dispose()
    finally:
        server.close()


async def test_FE_025_should_resolve_url_relative_to_global_base_url_option(
    playwright: Playwright, server: Server
) -> None:
    request = await playwright.request.new_context(base_url=server.PREFIX)
    response = await request.get("/empty.html")
    assert response.url == server.EMPTY_PAGE
    await request.dispose()


async def test_FE_026_should_fallback_to_given_url_if_base_url_is_bogus(
    playwright: Playwright, server: Server
) -> None:
    request = await playwright.request.new_context(base_url="bogus")
    response = await request.get(server.PREFIX + "/empty.html")
    assert response.url == server.EMPTY_PAGE
    await request.dispose()


async def test_FE_027_should_set_playwright_as_user_agent(
    playwright: Playwright,
    server: Server,
    is_win: bool,
    is_linux: bool,
    is_mac: bool,
) -> None:
    request = await playwright.request.new_context()
    with server.expect_request("/empty.html") as server_request_info:
        await request.get(server.EMPTY_PAGE)
    user_agent = server_request_info.value.getHeader("user-agent")
    assert user_agent
    user_agent_masked = re.sub(
        r"\d+",
        "X",
        user_agent.replace(node_arch(), "<ARCH>", 1).replace(
            driver_version(), "X.X.X", 1
        ),
    )

    tokens = []
    if os.environ.get("CI"):
        tokens.append("CI/X")
    suffix = f" {' '.join(tokens)}" if tokens else ""

    # The driver names the client language and its version: python/X.X, not node/X.X.
    if is_win:
        assert (
            user_agent_masked
            == "Playwright/X.X.X (<ARCH>; windows X.X) python/X.X" + suffix
        )
    elif is_linux:
        # on ubuntu: distro is 'ubuntu' and version is 'X.X'
        # on manjaro: distro is 'Manjaro' and version is 'unknown'
        assert (
            re.sub(
                r"<ARCH>; \w+ [^)]+",
                "<ARCH>; distro version",
                user_agent_masked,
                count=1,
            )
            == "Playwright/X.X.X (<ARCH>; distro version) python/X.X" + suffix
        )
    elif is_mac:
        assert (
            user_agent_masked
            == "Playwright/X.X.X (<ARCH>; macOS X.X) python/X.X" + suffix
        )
    await request.dispose()


async def test_FE_029_should_return_empty_body(
    playwright: Playwright, server: Server
) -> None:
    request = await playwright.request.new_context()
    response = await request.get(server.EMPTY_PAGE)
    body = await response.body()
    assert len(body) == 0
    assert await response.text() == ""
    await request.dispose()


async def test_FE_030_should_abort_requests_when_context_is_disposed(
    playwright: Playwright, server: Server
) -> None:
    connection_closed = threading.Event()

    def handler(req: TestServerRequest) -> None:
        req.notifyFinish().addErrback(lambda _: connection_closed.set())

    server.set_route("/empty.html", handler)
    request = await playwright.request.new_context()

    async def dispose_on_request() -> None:
        await server.wait_for_request("/empty.html")
        await request.dispose()

    results = await asyncio.gather(
        catch_error(request.get(server.EMPTY_PAGE)),
        catch_error(request.post(server.EMPTY_PAGE)),
        catch_error(request.delete(server.EMPTY_PAGE)),
        dispose_on_request(),
    )
    for result in results[:-1]:
        assert isinstance(result, Error)
        assert "Request context disposed." in result.message
    assert connection_closed.wait(10)
    await request.dispose()


async def test_FE_031_should_abort_redirected_requests_when_context_is_disposed(
    playwright: Playwright, server: Server
) -> None:
    server.set_redirect("/redirect", "/test")
    connection_closed = threading.Event()

    def handler(req: TestServerRequest) -> None:
        req.notifyFinish().addErrback(lambda _: connection_closed.set())

    server.set_route("/test", handler)
    request = await playwright.request.new_context()

    async def dispose_on_request() -> None:
        await server.wait_for_request("/test")
        await request.dispose()

    [result, _] = await asyncio.gather(
        catch_error(request.get(server.PREFIX + "/redirect")),
        dispose_on_request(),
    )
    assert isinstance(result, Error)
    assert re.search(
        r"Request context disposed|Target page, context or browser has been closed",
        result.message,
    )
    assert connection_closed.wait(10)
    await request.dispose()


async def test_FE_032_should_remove_content_length_from_redirected_post_requests(
    playwright: Playwright, server: Server
) -> None:
    server.set_redirect("/redirect", "/empty.html")
    request = await playwright.request.new_context()
    with server.expect_request("/redirect") as req1_info:
        with server.expect_request("/empty.html") as req2_info:
            result = await request.post(
                server.PREFIX + "/redirect", data={"foo": "bar"}
            )
    assert result.status == 200
    assert req1_info.value.getHeader("content-length") == "13"
    assert req2_info.value.getHeader("content-length") is None
    await request.dispose()


SERIALIZATION = [
    ("object", {"foo": "bar"}),
    ("array", ["foo", "bar", 2021]),
    ("string", "foo"),
    ("string (falsey)", ""),
    ("bool", True),
    ("bool (false)", False),
    ("number", 2021),
    ("number (falsey)", 0),
    ("null", None),
    ("literal string undefined", "undefined"),
]


def json_stringify_params() -> List[Any]:
    params = []
    for name, value in SERIALIZATION:
        marks: List[pytest.MarkDecorator] = []
        if value is None:
            marks.append(
                pytest.mark.skip(
                    reason="data=None means no data in Python: a JSON null body "
                    "can not be passed as a value"
                )
            )
        params.append(pytest.param(value, id=name, marks=marks))
    return params


@pytest.mark.parametrize("value", json_stringify_params())
async def test_FE_033_should_json_stringify_body_when_content_type_is_application_json(
    playwright: Playwright, server: Server, value: Any
) -> None:
    # https://github.com/microsoft/playwright/issues/43388
    stringified_value = json.dumps(value, separators=(",", ":"))
    request = await playwright.request.new_context()
    for content_type in ["application/json", "Application/JSON; charset=utf-8"]:
        with server.expect_request("/empty.html") as req_info:
            await request.post(
                server.EMPTY_PAGE,
                headers={"content-type": content_type},
                data=value,
            )
        body = req_info.value.post_body
        assert (body or b"").decode() == stringified_value
    await request.dispose()


@pytest.mark.parametrize(
    "value", [pytest.param(value, id=name) for name, value in SERIALIZATION]
)
async def test_FE_034_should_not_double_stringify_body_when_content_type_is_application_json(
    playwright: Playwright, server: Server, value: Any
) -> None:
    stringified_value = json.dumps(value, separators=(",", ":"))
    request = await playwright.request.new_context()
    with server.expect_request("/empty.html") as req_info:
        await request.post(
            server.EMPTY_PAGE,
            headers={"content-type": "application/json"},
            data=stringified_value,
        )
    body = req_info.value.post_body
    assert (body or b"").decode() == stringified_value
    await request.dispose()


async def test_FE_035_should_accept_already_serialized_data_as_buffer_when_content_type_is_application_json(
    playwright: Playwright, server: Server
) -> None:
    request = await playwright.request.new_context()
    value = json.dumps(json.dumps({"foo": "bar"}))
    with server.expect_request("/empty.html") as req_info:
        await request.post(
            server.EMPTY_PAGE,
            headers={"content-type": "application/json"},
            data=value.encode("utf8"),
        )
    body = req_info.value.post_body
    assert (body or b"").decode() == value
    await request.dispose()


def respond_empty_with_encoding(
    encoding: str,
) -> Callable[[TestServerRequest], None]:
    def handler(req: TestServerRequest) -> None:
        req.setResponseCode(200)
        req.setHeader("Content-Encoding", encoding)
        req.setHeader("Content-Type", "text/plain")
        req.finish()

    return handler


async def test_FE_037_should_not_fail_on_empty_body_with_encoding(
    playwright: Playwright, server: Server
) -> None:
    request = await playwright.request.new_context()
    for method in ["head", "put"]:
        for encoding in ["br", "gzip", "deflate"]:
            server.set_route("/empty.html", respond_empty_with_encoding(encoding))
            response = await getattr(request, method)(server.EMPTY_PAGE)
            assert response.status == 200
            assert len(await response.body()) == 0
    await request.dispose()


async def test_FE_038_should_return_body_for_failing_requests(
    playwright: Playwright, server: Server
) -> None:
    def handler(req: TestServerRequest) -> None:
        req.setResponseCode(404)
        req.setHeader("Content-Length", "10")
        req.setHeader("Content-Type", "text/plain")
        req.write(b"Not found.")
        req.finish()

    request = await playwright.request.new_context()
    for method in ["head", "put", "trace"]:
        server.set_route("/empty.html", handler)
        response = await request.fetch(server.EMPTY_PAGE, method=method)
        assert response.status == 404
        # HEAD response returns empty body in node http module.
        assert await response.text() == ("" if method == "head" else "Not found.")
    await request.dispose()


async def test_FE_039_should_throw_an_error_when_max_redirects_is_exceeded(
    playwright: Playwright, server: Server
) -> None:
    server.set_redirect("/a/redirect1", "/b/c/redirect2")
    server.set_redirect("/b/c/redirect2", "/b/c/redirect3")
    server.set_redirect("/b/c/redirect3", "/b/c/redirect4")
    server.set_redirect("/b/c/redirect4", "/simple.json")

    request = await playwright.request.new_context()
    for method in HTTP_METHODS:
        for max_redirects in [1, 2, 3]:
            with pytest.raises(Error) as exc_info:
                await request.fetch(
                    f"{server.PREFIX}/a/redirect1",
                    method=method,
                    max_redirects=max_redirects,
                )
            assert "Max redirect count exceeded" in exc_info.value.message
    await request.dispose()


async def test_FE_040_should_not_follow_redirects_when_max_redirects_is_set_to_0(
    playwright: Playwright, server: Server
) -> None:
    server.set_redirect("/a/redirect1", "/b/c/redirect2")
    server.set_redirect("/b/c/redirect2", "/simple.json")

    request = await playwright.request.new_context()
    for method in HTTP_METHODS:
        response = await request.fetch(
            f"{server.PREFIX}/a/redirect1", method=method, max_redirects=0
        )
        assert response.headers["location"] == "/b/c/redirect2"
        assert response.status == 302
    await request.dispose()


async def test_FE_041_should_throw_an_error_when_max_redirects_is_less_than_0(
    playwright: Playwright, server: Server
) -> None:
    server.set_redirect("/a/redirect1", "/b/c/redirect2")
    server.set_redirect("/b/c/redirect2", "/simple.json")

    request = await playwright.request.new_context()
    for method in HTTP_METHODS:
        with pytest.raises(Error) as exc_info:
            await request.fetch(
                f"{server.PREFIX}/a/redirect1", method=method, max_redirects=-1
            )
        # The Python client names the option max_redirects.
        assert (
            "'max_redirects' must be greater than or equal to '0'"
            in exc_info.value.message
        )
    await request.dispose()


async def test_FE_042_should_not_follow_redirects_when_max_redirects_is_set_to_0_in_new_context(
    playwright: Playwright, server: Server
) -> None:
    server.set_redirect("/a/redirect1", "/b/c/redirect2")
    server.set_redirect("/b/c/redirect2", "/simple.json")

    request = await playwright.request.new_context(max_redirects=0)
    for method in HTTP_METHODS:
        response = await request.fetch(f"{server.PREFIX}/a/redirect1", method=method)
        assert response.headers["location"] == "/b/c/redirect2"
        assert response.status == 302
    await request.dispose()


async def test_FE_043_should_follow_redirects_up_to_max_redirects_limit_set_in_new_context(
    playwright: Playwright, server: Server
) -> None:
    server.set_redirect("/a/redirect1", "/b/c/redirect2")
    server.set_redirect("/b/c/redirect2", "/b/c/redirect3")
    server.set_redirect("/b/c/redirect3", "/b/c/redirect4")
    server.set_redirect("/b/c/redirect4", "/simple.json")

    for max_redirects in [1, 2, 3, 4]:
        request = await playwright.request.new_context(max_redirects=max_redirects)
        for method in HTTP_METHODS:
            if max_redirects < 4:
                with pytest.raises(Error) as exc_info:
                    await request.fetch(f"{server.PREFIX}/a/redirect1", method=method)
                assert "Max redirect count exceeded" in exc_info.value.message
            else:
                response = await request.fetch(
                    f"{server.PREFIX}/a/redirect1", method=method
                )
                assert response.status == 200
        await request.dispose()


async def test_FE_044_should_use_max_redirects_from_fetch_when_provided_overriding_new_context(
    playwright: Playwright, server: Server
) -> None:
    server.set_redirect("/a/redirect1", "/b/c/redirect2")
    server.set_redirect("/b/c/redirect2", "/b/c/redirect3")
    server.set_redirect("/b/c/redirect3", "/b/c/redirect4")
    server.set_redirect("/b/c/redirect4", "/simple.json")

    request = await playwright.request.new_context(max_redirects=1)
    for method in HTTP_METHODS:
        response = await request.fetch(
            f"{server.PREFIX}/a/redirect1", method=method, max_redirects=4
        )
        assert response.status == 200
    await request.dispose()


async def test_FE_045_should_keep_headers_capitalization(
    playwright: Playwright, server: Server, monkeypatch: pytest.MonkeyPatch
) -> None:
    record_raw_headers(monkeypatch)
    request = await playwright.request.new_context()
    with server.expect_request("/empty.html") as server_request_info:
        response = await request.get(
            server.EMPTY_PAGE,
            headers={
                "X-fOo": "vaLUE",
            },
        )
    assert response.ok
    # Port of serverRequest.rawHeaders: the names and values, as sent.
    raw = [item for header in raw_headers(server_request_info.value) for item in header]
    assert "X-fOo" in raw
    assert "vaLUE" in raw
    await request.dispose()


async def test_FE_047_should_throw_after_dispose(
    playwright: Playwright, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/27822
    request = await playwright.request.new_context()
    await request.dispose()
    with pytest.raises(Error) as exc_info:
        await request.get(server.EMPTY_PAGE)
    assert "Target page, context or browser has been closed" in exc_info.value.message


async def test_FE_048_should_retry_econnreset(
    playwright: Playwright, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/30978
    request = await playwright.request.new_context()
    request_count = 0

    def handler(req: TestServerRequest) -> None:
        nonlocal request_count
        request_count += 1
        if request_count <= 3:
            # Port of req.socket.destroy(): close the connection without a response.
            assert req.transport
            req.transport.loseConnection()
            return
        req.setResponseCode(200)
        req.setHeader("content-type", "text/plain")
        req.write(b"Hello!")
        req.finish()

    server.set_route("/test", handler)
    response = await request.fetch(server.PREFIX + "/test", max_retries=3)
    assert response.status == 200
    assert await response.text() == "Hello!"
    assert request_count == 4
    await request.dispose()


async def test_FE_049_should_expose_node_error_code_on_network_errors(
    playwright: Playwright, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/42532
    # Reset the connection so that node reports a system error instead of a plain 'socket hang up'.
    # Port of req.socket.resetAndDestroy(): abortConnection() closes with a TCP reset.
    def handler(req: TestServerRequest) -> None:
        assert req.transport
        req.transport.abortConnection()

    server.set_route("/reset", handler)
    request = await playwright.request.new_context()
    with pytest.raises(Error) as exc_info:
        await request.get(server.PREFIX + "/reset", max_retries=0)
    assert "ECONNRESET" in exc_info.value.message
    # Upstream also checks error.code, error.syscall and error.errno: Node.js error
    # fields that the JavaScript client copies to its Error. The Python Error has none.
    await request.dispose()


async def test_FE_050_should_append_node_error_code_to_the_message(
    playwright: Playwright, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/42532
    # Node reports this one as a plain 'socket hang up' that does not mention the code.
    def handler(req: TestServerRequest) -> None:
        # Port of req.socket.destroy(): close the connection without a response.
        assert req.transport
        req.transport.loseConnection()

    server.set_route("/hangup", handler)
    request = await playwright.request.new_context()
    with pytest.raises(Error) as exc_info:
        await request.get(server.PREFIX + "/hangup", max_retries=0)
    assert "socket hang up (ECONNRESET)" in exc_info.value.message
    # Upstream also checks error.code, a Node.js error field that the JavaScript
    # client copies to its Error. The Python Error has no such attribute.
    await request.dispose()


async def test_FE_051_should_not_crash_when_server_refuses_body_before_reading_it(
    playwright: Playwright,
) -> None:
    # https://github.com/microsoft/playwright/issues/42074
    # Respond without reading the body, then reset. Node emits a late write
    # EPIPE/ECONNRESET on the request socket; without a listener that becomes an
    # unhandled 'error' and kills the process.
    # The test server reads the whole body before a route runs, so this test uses a
    # server that gets the connection right after the request head.
    def handler(sock: socket.socket, head: bytes) -> None:
        time.sleep(0.05)
        write_response(
            sock,
            "413 Payload Too Large",
            ["content-type: application/json"],
            json.dumps({"error": "too large"}).encode(),
        )
        # The server closes the socket when the handler returns, with the body unread.

    server = RawHttpServer(handler)
    try:
        request = await playwright.request.new_context()
        # Large body so the client is still writing when the reset lands.
        result = await catch_error(
            request.post(
                server.PREFIX + "/refuse",
                data=b"x" * (20 * 1024 * 1024),
                headers={"content-type": "text/plain"},
                max_retries=0,
            )
        )
        if isinstance(result, Error):
            assert re.search(
                r"apiRequestContext\.post|ECONNRESET|EPIPE|ECONNABORTED|socket",
                result.message,
                re.IGNORECASE,
            )
        else:
            assert result.status == 413
            assert await result.text() == json.dumps({"error": "too large"})
        await request.dispose()
    finally:
        server.close()


async def test_FE_052_should_throw_when_fail_on_status_code_is_set_to_true_inside_api_request_context_options(
    playwright: Playwright, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/34204
    request = await playwright.request.new_context(fail_on_status_code=True)

    def handler(req: TestServerRequest) -> None:
        req.setResponseCode(404)
        req.setHeader("Content-Length", "10")
        req.setHeader("Content-Type", "text/plain")
        req.write(b"Not found.")
        req.finish()

    server.set_route("/empty.html", handler)
    with pytest.raises(Error) as exc_info:
        await request.fetch(server.EMPTY_PAGE)
    assert "404 Not Found" in exc_info.value.message
    await request.dispose()


async def test_FE_053_should_not_throw_when_fail_on_status_code_is_set_to_false_inside_api_request_context_options(
    playwright: Playwright, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/34204
    request = await playwright.request.new_context(fail_on_status_code=False)

    def handler(req: TestServerRequest) -> None:
        req.setResponseCode(404)
        req.setHeader("Content-Length", "10")
        req.setHeader("Content-Type", "text/plain")
        req.write(b"Not found.")
        req.finish()

    server.set_route("/empty.html", handler)
    response = await request.fetch(server.EMPTY_PAGE)
    assert response.status == 404
    await request.dispose()
