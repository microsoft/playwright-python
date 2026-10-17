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

"""Port of tests/library/fetch-proxy.spec.ts."""

import asyncio
import base64
import concurrent.futures
import os
from typing import Awaitable, Callable, Dict, Generator, Optional
from urllib.parse import urlsplit

import pytest

from playwright.async_api import BrowserContext, BrowserType, Error, Playwright
from tests.helpers.alpn_server import AlpnRecordingServer
from tests.helpers.proxy_server import ProxyRequest, ProxyServer
from tests.helpers.socks_server import MockSocksServer
from tests.server import Server, TestServerRequest

ContextFactory = Callable[..., Awaitable[BrowserContext]]


@pytest.fixture
def proxy_server() -> Generator[ProxyServer, None, None]:
    """Port of the proxyServer fixture in tests/config/serverFixtures.ts."""
    proxy = ProxyServer()
    yield proxy
    proxy.stop()


@pytest.fixture
def socks_port() -> Generator[int, None, None]:
    """Port of the socksPort fixture in tests/config/serverFixtures.ts."""
    socks_server = MockSocksServer()
    yield socks_server.port
    socks_server.close()


async def test_PR_041_context_request_should_pick_up_proxy_credentials(
    browser_type: BrowserType,
    launch_arguments: Dict,
    server: Server,
    proxy_server: ProxyServer,
) -> None:
    proxy_server.forward_to(server.PORT, allow_connect_requests=True)
    # The proxy calls the handler on its own thread.
    auth_future: "concurrent.futures.Future[Optional[str]]" = (
        concurrent.futures.Future()
    )

    def auth_handler(request: ProxyRequest) -> bool:
        header = request.headers.get("proxy-authorization")
        # Browser can issue various unrelated requests over the proxy,
        # but we are only interested in our own request.
        if "non-existent.com:80" in proxy_server.connect_hosts:
            if not auth_future.done():
                auth_future.set_result(header)
        return bool(header)

    proxy_server.set_auth_handler(auth_handler)
    browser = await browser_type.launch(
        **launch_arguments,
        proxy={
            "server": f"localhost:{proxy_server.PORT}",
            "username": "user",
            "password": "secret",
        },
    )
    context = await browser.new_context()
    response = await context.request.get("http://non-existent.com/simple.json")
    assert "non-existent.com:80" in proxy_server.connect_hosts
    auth = await asyncio.wrap_future(auth_future)
    assert auth == "Basic " + base64.b64encode(b"user:secret").decode()
    assert await response.json() == {"foo": "bar"}
    await browser.close()


async def test_PR_042_global_request_should_pick_up_proxy_credentials(
    playwright: Playwright, server: Server, proxy_server: ProxyServer
) -> None:
    proxy_server.forward_to(server.PORT, allow_connect_requests=True)
    auth: Optional[str] = None

    def auth_handler(request: ProxyRequest) -> bool:
        nonlocal auth
        auth = request.headers.get("proxy-authorization")
        return bool(auth)

    proxy_server.set_auth_handler(auth_handler)
    request = await playwright.request.new_context(
        proxy={
            "server": f"localhost:{proxy_server.PORT}",
            "username": "user",
            "password": "secret",
        }
    )
    response = await request.get("http://non-existent.com/simple.json")
    assert "non-existent.com:80" in proxy_server.connect_hosts
    assert auth == "Basic " + base64.b64encode(b"user:secret").decode()
    assert await response.json() == {"foo": "bar"}
    await request.dispose()


async def test_PR_043_should_work_with_context_level_proxy(
    context_factory: ContextFactory, server: Server, proxy_server: ProxyServer
) -> None:
    def handle(request: TestServerRequest) -> None:
        request.write(b"<title>Served by the proxy</title>")
        request.finish()

    server.set_route("/target.html", handle)

    proxy_server.forward_to(server.PORT, allow_connect_requests=True)
    context = await context_factory(proxy={"server": f"localhost:{proxy_server.PORT}"})

    with server.expect_request("/target.html") as request_info:
        response = await context.request.get("http://non-existent.com/target.html")
    request = request_info.value
    assert response.status == 200
    assert request.uri.decode() == "/target.html"


async def test_PR_044_should_support_proxy_bypass(
    context_factory: ContextFactory, server: Server, proxy_server: ProxyServer
) -> None:
    def handle(request: TestServerRequest) -> None:
        request.write(b"Served by the proxy")
        request.finish()

    server.set_route("/target.html", handle)
    # FYI: using long and weird domain names to avoid ATT DNS hijacking
    # that resolves everything to some weird search results page.
    #
    # @see https://gist.github.com/CollinChaffin/24f6c9652efb3d6d5ef2f5502720ef00
    proxy_server.forward_to(server.PORT, allow_connect_requests=True)
    context = await context_factory(
        proxy={
            "server": f"localhost:{proxy_server.PORT}",
            "bypass": "1.non.existent.domain.for.the.test, 2.non.existent.domain.for.the.test, .another.test",
        }
    )

    res = await context.request.get(server.CROSS_PROCESS_PREFIX + "/target.html")
    assert "Served by the proxy" in await res.text()
    assert urlsplit(server.CROSS_PROCESS_PREFIX).netloc in proxy_server.connect_hosts
    proxy_server.connect_hosts = []

    res = await context.request.get(
        "http://0.non.existent.domain.for.the.test/target.html"
    )
    assert "Served by the proxy" in await res.text()
    proxy_server.connect_hosts = []

    with pytest.raises(Error) as exc_info:
        await context.request.get(
            "http://1.non.existent.domain.for.the.test/target.html"
        )
    assert exc_info.value.message
    assert proxy_server.connect_hosts == []

    with pytest.raises(Error) as exc_info:
        await context.request.get(
            "http://2.non.existent.domain.for.the.test/target.html"
        )
    assert exc_info.value.message
    assert proxy_server.connect_hosts == []

    with pytest.raises(Error) as exc_info:
        await context.request.get("http://foo.is.the.another.test/target.html")
    assert exc_info.value.message
    assert proxy_server.connect_hosts == []

    res = await context.request.get(
        "http://3.non.existent.domain.for.the.test/target.html"
    )
    assert "Served by the proxy" in await res.text()


async def test_PR_045_should_use_socks_proxy(
    playwright: Playwright, server: Server, socks_port: int
) -> None:
    if os.environ.get("INSIDE_DOCKER"):
        pytest.skip("connect ECONNREFUSED 127.0.0.1:<port>")

    request = await playwright.request.new_context(
        proxy={"server": f"socks5://localhost:{socks_port}"}
    )
    response = await request.get(server.EMPTY_PAGE)
    assert "Served by the SOCKS proxy" in await response.text()


async def test_PR_046_should_send_correct_alpn_protocol_to_https_proxy(
    playwright: Playwright, server: Server
) -> None:
    proxy = AlpnRecordingServer()

    request = await playwright.request.new_context(
        proxy={"server": f"https://localhost:{proxy.port}"},
        ignore_https_errors=True,
    )

    with pytest.raises(Error):
        await request.get(server.EMPTY_PAGE)

    assert proxy.offered_protocols
    assert "http/1.1" in proxy.offered_protocols

    proxy.close()
    await request.dispose()


async def test_PR_047_should_apply_proxy_bypass_to_redirect_targets(
    context_factory: ContextFactory, server: Server, proxy_server: ProxyServer
) -> None:
    cross_process_host = urlsplit(server.CROSS_PROCESS_PREFIX).netloc
    if cross_process_host == server.HOST:
        pytest.skip("Needs two different host names for the same server")

    proxy_server.forward_to(server.PORT, allow_connect_requests=True)
    server.set_redirect(
        "/redirect-to-cross-process", server.CROSS_PROCESS_PREFIX + "/simple.json"
    )
    server.set_redirect("/redirect-to-same-origin", server.PREFIX + "/simple.json")
    context = await context_factory(
        proxy={"server": f"localhost:{proxy_server.PORT}", "bypass": server.HOSTNAME}
    )

    # Bypassed first hop redirects to a host that must go through the proxy.
    response = await context.request.get(server.PREFIX + "/redirect-to-cross-process")
    assert response.url == server.CROSS_PROCESS_PREFIX + "/simple.json"
    assert await response.json() == {"foo": "bar"}
    assert proxy_server.connect_hosts == [cross_process_host]
    proxy_server.connect_hosts = []

    # Proxied first hop redirects to a bypassed host.
    response = await context.request.get(
        server.CROSS_PROCESS_PREFIX + "/redirect-to-same-origin"
    )
    assert response.url == server.PREFIX + "/simple.json"
    assert await response.json() == {"foo": "bar"}
    assert proxy_server.connect_hosts == [cross_process_host]
