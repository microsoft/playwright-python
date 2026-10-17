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

"""Port of tests/library/browsercontext-proxy.spec.ts."""

import base64
from typing import Any, Awaitable, Callable, Dict, Generator, List, Optional

import pytest

from playwright.async_api import (
    Browser,
    BrowserContext,
    BrowserType,
    Error,
    expect,
)
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


def respond(body: str) -> Callable[[TestServerRequest], None]:
    def handler(request: TestServerRequest) -> None:
        request.write(body.encode())
        request.finish()

    return handler


@pytest.fixture(autouse=True)
def before_each(server: Server) -> None:
    server.set_route(
        "/target.html", respond("<html><title>Served by the proxy</title></html>")
    )


async def test_PR_018_should_work_when_passing_the_proxy_only_on_the_context_level(
    browser_name: str,
    platform: str,
    browser_type: BrowserType,
    launch_arguments: Dict,
    server: Server,
    proxy_server: ProxyServer,
) -> None:
    proxy_server.forward_to(server.PORT)
    browser: Optional[Browser] = None
    try:
        browser = await browser_type.launch(**launch_arguments, proxy=None)
        context = await browser.new_context(proxy={"server": proxy_server.HOST})

        page = await context.new_page()
        await page.goto("http://non-existent.test/target.html")
        assert "http://non-existent.test/target.html" in proxy_server.request_urls
        assert await page.title() == "Served by the proxy"
    finally:
        assert browser
        await browser.close()


@pytest.mark.parametrize("launch_proxy", ["per-context", "http://per-context"])
async def test_PR_019_should_ignore_legacy_launch_proxy(
    launch_proxy: str,
    browser_type: BrowserType,
    launch_arguments: Dict,
    server: Server,
    proxy_server: ProxyServer,
) -> None:
    proxy_server.forward_to(server.PORT, allow_connect_requests=True)
    browser = await browser_type.launch(
        **launch_arguments, proxy={"server": launch_proxy}
    )
    try:
        context = await browser.new_context(proxy={"server": proxy_server.HOST})
        page = await context.new_page()
        await page.goto("http://non-existent.test/target.html")
        assert await page.title() == "Served by the proxy"
        response = await context.request.get("http://non-existent.test/target.html")
        assert "Served by the proxy" in await response.text()
        assert "non-existent.test:80" in proxy_server.connect_hosts

        direct_context = await browser.new_context()
        direct_page = await direct_context.new_page()
        await direct_page.goto(server.PREFIX + "/target.html")
        assert await direct_page.title() == "Served by the proxy"
        direct_response = await direct_context.request.get(
            server.PREFIX + "/target.html"
        )
        assert direct_response.ok is True
    finally:
        await browser.close()


@pytest.mark.skip_protocol_check
async def test_PR_020_should_throw_for_bad_server_value(
    context_factory: ContextFactory,
) -> None:
    # The server must be a string.
    proxy: Any = {"server": 123}
    with pytest.raises(Error) as exc_info:
        await context_factory(proxy=proxy)
    assert "proxy.server: expected string, got number" in exc_info.value.message


async def test_PR_021_should_use_proxy(
    context_factory: ContextFactory, server: Server, proxy_server: ProxyServer
) -> None:
    proxy_server.forward_to(server.PORT)
    context = await context_factory(proxy={"server": proxy_server.HOST})
    page = await context.new_page()
    await page.goto("http://non-existent.test/target.html")
    assert "http://non-existent.test/target.html" in proxy_server.request_urls
    assert await page.title() == "Served by the proxy"
    await context.close()


async def test_PR_022_should_send_secure_cookies_to_subdomain_localhost(
    context_factory: ContextFactory,
    browser_name: str,
    server: Server,
    is_win: bool,
    proxy_server: ProxyServer,
    browser_channel: Optional[str],
) -> None:
    proxy_server.forward_to(server.PORT)
    context = await context_factory(proxy={"server": proxy_server.HOST})

    def handle_set_cookie(request: TestServerRequest) -> None:
        request.responseHeaders.setRawHeaders(
            "Set-Cookie", ["non-secure=1; HttpOnly", "secure=1; HttpOnly; Secure"]
        )
        request.finish()

    def handle_read_cookie(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "text/html")
        cookie = "; ".join(
            sorted(c.strip() for c in (request.getHeader("cookie") or "").split(";"))
        )
        request.write(f"<div>Cookie: {cookie}</div>".encode())
        request.finish()

    server.set_route("/set-cookie.html", handle_set_cookie)
    server.set_route("/read-cookie.html", handle_read_cookie)

    page = await context.new_page()

    await page.goto("http://subdomain.localhost/set-cookie.html")

    cookies = await context.cookies("http://subdomain.localhost")
    expected: List[Dict[str, str]] = [
        {"name": "non-secure", "domain": "subdomain.localhost"}
    ]
    if not (
        browser_name == "webkit" and (not is_win or browser_channel == "webkit-wsl")
    ):
        expected.append({"name": "secure", "domain": "subdomain.localhost"})
    assert [
        {"name": cookie.get("name"), "domain": cookie.get("domain")}
        for cookie in cookies
    ] == expected

    await page.goto("http://subdomain.localhost/read-cookie.html")
    await expect(page.locator("div")).to_have_text(
        "Cookie: non-secure=1"
        if browser_name == "webkit"
        else "Cookie: non-secure=1; secure=1"
    )

    await context.close()


async def test_PR_023_should_set_cookie_for_top_level_domain(
    context_factory: ContextFactory,
    server: Server,
    proxy_server: ProxyServer,
    browser_name: str,
    is_linux: bool,
    browser_channel: Optional[str],
) -> None:
    if browser_name == "webkit" and (is_linux or browser_channel == "webkit-wsl"):
        pytest.skip("fixme: webkit on linux")

    proxy_server.forward_to(server.PORT, allow_connect_requests=True)
    context = await context_factory(proxy={"server": proxy_server.HOST})

    def handle(request: TestServerRequest) -> None:
        request.setHeader("Set-Cookie", "name=val; Domain=codes; Path=/;")
        request.finish()

    server.set_route("/empty.html", handle)

    await context.request.get("http://codes/empty.html")
    [cookie] = await context.cookies()
    assert cookie
    assert cookie.get("name") == "name"
    assert cookie.get("value") == "val"
    await context.close()


@pytest.mark.parametrize(
    "additional_bypass", [False, True], ids=["by_default", "with_other_bypasses"]
)
@pytest.mark.parametrize(
    "target",
    ["localhost", "127.0.0.1", "169.254.3.4"],
    ids=["localhost", "loopback_address", "link_local"],
)
async def test_PR_024_should_proxy_local_network_requests(
    additional_bypass: bool,
    target: str,
    platform: str,
    browser_name: str,
    context_factory: ContextFactory,
    server: Server,
    proxy_server: ProxyServer,
) -> None:
    if (
        browser_name == "webkit"
        and platform == "darwin"
        and target in ["localhost", "127.0.0.1"]
        and additional_bypass
    ):
        pytest.skip("Mac webkit does not proxy localhost when bypass rules are set")

    path = f"/target-{str(additional_bypass).lower()}-{target}.html"
    server.set_route(path, respond("<html><title>Served by the proxy</title></html>"))

    url = f"http://{target}:55555{path}"
    proxy_server.forward_to(server.PORT)
    context = await context_factory(
        proxy={
            "server": proxy_server.HOST,
            "bypass": (
                "1.non.existent.domain.for.the.test" if additional_bypass else None
            ),
        }
    )

    page = await context.new_page()
    await page.goto(url)
    assert url in proxy_server.request_urls
    assert await page.title() == "Served by the proxy"

    try:
        await page.goto("http://1.non.existent.domain.for.the.test/foo.html")
    except Error:
        pass
    if additional_bypass:
        assert (
            "http://1.non.existent.domain.for.the.test/foo.html"
            not in proxy_server.request_urls
        )
    else:
        assert (
            "http://1.non.existent.domain.for.the.test/foo.html"
            in proxy_server.request_urls
        )

    await context.close()


async def test_PR_025_should_use_ipv6_proxy(
    request: pytest.FixtureRequest,
    context_factory: ContextFactory,
    server: Server,
    proxy_server: ProxyServer,
    browser_name: str,
    browser_channel: Optional[str],
) -> None:
    if browser_name == "firefox":
        request.applymarker(
            pytest.mark.xfail(
                reason="upstream: page.goto: NS_ERROR_UNKNOWN_HOST", strict=True
            )
        )
    if browser_channel == "webkit-wsl":
        request.applymarker(
            pytest.mark.xfail(
                reason="upstream: WebKit on WSL does not support IPv6: https://github.com/microsoft/WSL/issues/10803",
                strict=True,
            )
        )
    proxy_server.forward_to(server.PORT)
    context = await context_factory(
        proxy={"server": f"[0:0:0:0:0:0:0:1]:{proxy_server.PORT}"}
    )
    page = await context.new_page()
    await page.goto("http://non-existent.test/target.html")
    assert "http://non-existent.test/target.html" in proxy_server.request_urls
    assert await page.title() == "Served by the proxy"
    await context.close()


async def test_PR_026_should_use_proxy_twice(
    context_factory: ContextFactory, server: Server, proxy_server: ProxyServer
) -> None:
    proxy_server.forward_to(server.PORT)
    context = await context_factory(proxy={"server": proxy_server.HOST})
    page = await context.new_page()
    await page.goto("http://non-existent.test/target.html")
    assert "http://non-existent.test/target.html" in proxy_server.request_urls
    await page.goto("http://non-existent-2.test/target.html")
    assert "http://non-existent-2.test/target.html" in proxy_server.request_urls
    assert await page.title() == "Served by the proxy"
    await context.close()


async def test_PR_027_should_use_proxy_for_second_page(
    context_factory: ContextFactory, server: Server, proxy_server: ProxyServer
) -> None:
    proxy_server.forward_to(server.PORT)
    context = await context_factory(proxy={"server": proxy_server.HOST})

    page = await context.new_page()
    await page.goto("http://non-existent.test/target.html")
    assert "http://non-existent.test/target.html" in proxy_server.request_urls
    assert await page.title() == "Served by the proxy"

    page2 = await context.new_page()
    proxy_server.request_urls = []
    await page2.goto("http://non-existent.test/target.html")
    assert "http://non-existent.test/target.html" in proxy_server.request_urls
    assert await page2.title() == "Served by the proxy"

    await context.close()


async def test_PR_028_should_use_proxy_for_https_urls(
    context_factory: ContextFactory, https_server: Server, proxy_server: ProxyServer
) -> None:
    https_server.set_route(
        "/target.html",
        respond("<html><title>Served by https server via proxy</title></html>"),
    )
    proxy_server.forward_to(https_server.PORT, allow_connect_requests=True)
    context = await context_factory(
        ignore_https_errors=True, proxy={"server": proxy_server.HOST}
    )
    page = await context.new_page()
    await page.goto("https://non-existent.test/target.html")
    assert "non-existent.test:443" in proxy_server.connect_hosts
    assert await page.title() == "Served by https server via proxy"
    await context.close()


async def test_PR_029_should_work_with_ip_port_notion(
    context_factory: ContextFactory, server: Server, proxy_server: ProxyServer
) -> None:
    proxy_server.forward_to(server.PORT)
    context = await context_factory(proxy={"server": f"127.0.0.1:{proxy_server.PORT}"})
    page = await context.new_page()
    await page.goto("http://non-existent.test/target.html")
    assert "http://non-existent.test/target.html" in proxy_server.request_urls
    assert await page.title() == "Served by the proxy"
    await context.close()


async def test_PR_030_should_throw_for_socks5_authentication(
    context_factory: ContextFactory,
) -> None:
    with pytest.raises(Error) as exc_info:
        await context_factory(
            proxy={
                "server": "socks5://localhost:1234",
                "username": "user",
                "password": "secret",
            }
        )
    assert (
        "Browser does not support socks5 proxy authentication" in exc_info.value.message
    )


async def test_PR_031_should_throw_for_socks4_authentication(
    context_factory: ContextFactory,
) -> None:
    with pytest.raises(Error) as exc_info:
        await context_factory(
            proxy={
                "server": "socks4://localhost:1234",
                "username": "user",
                "password": "secret",
            }
        )
    assert (
        "Socks4 proxy protocol does not support authentication"
        in exc_info.value.message
    )


async def test_PR_032_should_authenticate(
    context_factory: ContextFactory, server: Server, proxy_server: ProxyServer
) -> None:
    proxy_server.forward_to(server.PORT)
    auth: Optional[str] = None

    def auth_handler(request: ProxyRequest) -> bool:
        nonlocal auth
        auth = request.headers.get("proxy-authorization")
        return bool(auth)

    proxy_server.set_auth_handler(auth_handler)
    context = await context_factory(
        proxy={"server": proxy_server.HOST, "username": "user", "password": "secret"}
    )
    page = await context.new_page()
    await page.goto("http://non-existent.test/target.html")
    assert "http://non-existent.test/target.html" in proxy_server.request_urls
    assert auth == "Basic " + base64.b64encode(b"user:secret").decode()
    assert await page.title() == "Served by the proxy"
    await context.close()


async def test_PR_033_should_authenticate_with_empty_password(
    context_factory: ContextFactory, server: Server, proxy_server: ProxyServer
) -> None:
    proxy_server.forward_to(server.PORT)
    auth: Optional[str] = None

    def auth_handler(request: ProxyRequest) -> bool:
        nonlocal auth
        auth = request.headers.get("proxy-authorization")
        return bool(auth)

    proxy_server.set_auth_handler(auth_handler)
    context = await context_factory(
        proxy={"server": proxy_server.HOST, "username": "user", "password": ""}
    )
    page = await context.new_page()
    await page.goto("http://non-existent.test/target.html")
    assert auth == "Basic " + base64.b64encode(b"user:").decode()
    assert await page.title() == "Served by the proxy"
    await context.close()


async def test_PR_034_should_isolate_proxy_credentials_between_contexts(
    context_factory: ContextFactory,
    server: Server,
    browser_name: str,
    proxy_server: ProxyServer,
) -> None:
    proxy_server.forward_to(server.PORT)
    auth: Optional[str] = None

    def auth_handler(request: ProxyRequest) -> bool:
        nonlocal auth
        auth = request.headers.get("proxy-authorization")
        return bool(auth)

    proxy_server.set_auth_handler(auth_handler)

    context = await context_factory(
        proxy={
            "server": proxy_server.HOST,
            "username": "user1",
            "password": "secret1",
        }
    )
    page = await context.new_page()
    await page.goto("http://non-existent.test/target.html")
    assert auth == "Basic " + base64.b64encode(b"user1:secret1").decode()
    assert await page.title() == "Served by the proxy"
    await context.close()

    auth = None

    context = await context_factory(
        proxy={
            "server": proxy_server.HOST,
            "username": "user2",
            "password": "secret2",
        }
    )
    page = await context.new_page()
    await page.goto("http://non-existent.test/target.html")
    assert await page.title() == "Served by the proxy"
    assert auth == "Basic " + base64.b64encode(b"user2:secret2").decode()
    await context.close()


async def test_PR_035_should_exclude_patterns(
    context_factory: ContextFactory, server: Server, proxy_server: ProxyServer
) -> None:
    proxy_server.forward_to(server.PORT)
    # FYI: using long and weird domain names to avoid ATT DNS hijacking
    # that resolves everything to some weird search results page.
    #
    # @see https://gist.github.com/CollinChaffin/24f6c9652efb3d6d5ef2f5502720ef00
    context = await context_factory(
        proxy={
            "server": proxy_server.HOST,
            "bypass": "1.non.existent.domain.for.the.test, 2.non.existent.domain.for.the.test, .another.test",
        }
    )

    def non_favicon_urls() -> List[str]:
        return [u for u in proxy_server.request_urls if "favicon" not in u]

    proxy_server.request_urls = []
    page = await context.new_page()
    await page.goto("http://0.non.existent.domain.for.the.test/target.html")
    assert (
        "http://0.non.existent.domain.for.the.test/target.html"
        in proxy_server.request_urls
    )
    assert await page.title() == "Served by the proxy"
    await page.close()

    proxy_server.request_urls = []
    page = await context.new_page()
    with pytest.raises(Error) as exc_info:
        await page.goto("http://1.non.existent.domain.for.the.test/target.html")
    assert non_favicon_urls() == []
    assert exc_info.value.message
    await page.close()

    proxy_server.request_urls = []
    page = await context.new_page()
    with pytest.raises(Error) as exc_info:
        await page.goto("http://2.non.existent.domain.for.the.test/target.html")
    assert non_favicon_urls() == []
    assert exc_info.value.message
    await page.close()

    proxy_server.request_urls = []
    page = await context.new_page()
    with pytest.raises(Error) as exc_info:
        await page.goto("http://foo.is.the.another.test/target.html")
    assert non_favicon_urls() == []
    assert exc_info.value.message
    await page.close()

    proxy_server.request_urls = []
    page = await context.new_page()
    await page.goto("http://3.non.existent.domain.for.the.test/target.html")
    assert "http://3.non.existent.domain.for.the.test/target.html" in non_favicon_urls()
    assert await page.title() == "Served by the proxy"
    await page.close()

    await context.close()


async def test_PR_036_should_use_socks_proxy(
    context_factory: ContextFactory, socks_port: int
) -> None:
    context = await context_factory(
        proxy={"server": f"socks5://localhost:{socks_port}"}
    )
    page = await context.new_page()
    await page.goto("http://non-existent.test")
    assert await page.title() == "Served by the SOCKS proxy"
    await context.close()


async def test_PR_037_should_use_socks_proxy_in_second_page(
    context_factory: ContextFactory, socks_port: int
) -> None:
    context = await context_factory(
        proxy={"server": f"socks5://localhost:{socks_port}"}
    )

    page = await context.new_page()
    await page.goto("http://non-existent.test")
    assert await page.title() == "Served by the SOCKS proxy"

    page2 = await context.new_page()
    await page2.goto("http://non-existent.test")
    assert await page2.title() == "Served by the SOCKS proxy"

    await context.close()


async def test_PR_038_does_launch_without_a_port(
    context_factory: ContextFactory,
) -> None:
    context = await context_factory(proxy={"server": "http://localhost"})
    await context.close()


async def test_PR_039_should_isolate_proxy_credentials_between_contexts_on_navigation(
    context_factory: ContextFactory, server: Server
) -> None:
    def handle(request: TestServerRequest) -> None:
        auth_header = request.getHeader("proxy-authorization")

        if not auth_header:
            request.setResponseCode(407)
            request.setHeader("Proxy-Authenticate", 'Basic realm="proxy"')
            request.write(b"Proxy authorization required")
            request.finish()
            return

        username = base64.b64decode(auth_header.split(" ")[1]).decode().split(":")[0]
        request.setResponseCode(200)
        request.setHeader("Content-Type", "text/html")
        request.write(f"Hello <div data-testid=user>{username}</div>!\n".encode())
        request.finish()

    server.set_route("/target.html", handle)

    context1 = await context_factory(
        proxy={"server": server.PREFIX, "username": "user1", "password": "secret1"}
    )
    page1 = await context1.new_page()
    await page1.goto("http://non-existent.test/target.html")
    await expect(page1.get_by_test_id("user")).to_have_text("user1")

    context2 = await context_factory(
        proxy={"server": server.PREFIX, "username": "user2", "password": "secret2"}
    )
    page2 = await context2.new_page()
    await page2.goto("http://non-existent.test/target.html")
    await expect(page2.get_by_test_id("user")).to_have_text("user2")

    await page1.goto("http://non-existent.test/target.html")
    await expect(page1.get_by_test_id("user")).to_have_text("user1")
