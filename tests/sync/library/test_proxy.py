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

"""Port of tests/library/proxy.spec.ts."""

import base64
import socket
import threading
from typing import Any, Callable, Dict, Generator, List, Optional

import pytest

from playwright.sync_api import BrowserType, Error
from tests.helpers.proxy_server import ProxyRequest, ProxyServer
from tests.helpers.socks_server import MockSocksServer, SocksForwardingServer
from tests.server import Server, TestServerRequest


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


@pytest.mark.skip_protocol_check
def test_PR_001_should_throw_for_bad_server_value(
    browser_type: BrowserType, launch_arguments: Dict
) -> None:
    # The server must be a string.
    proxy: Any = {"server": 123}
    with pytest.raises(Error) as exc_info:
        browser_type.launch(**launch_arguments, proxy=proxy)
    assert "proxy.server: expected string, got number" in exc_info.value.message


def test_PR_002_should_use_proxy_smoke(
    browser_type: BrowserType, launch_arguments: Dict, server: Server
) -> None:
    server.set_route(
        "/target.html", respond("<html><title>Served by the proxy</title></html>")
    )
    browser = browser_type.launch(**launch_arguments, proxy={"server": server.HOST})
    page = browser.new_page()
    page.goto("http://non-existent.test/target.html")
    assert page.title() == "Served by the proxy"
    browser.close()


def test_PR_003_should_use_proxy_for_second_page(
    browser_type: BrowserType, launch_arguments: Dict, server: Server
) -> None:
    server.set_route(
        "/target.html", respond("<html><title>Served by the proxy</title></html>")
    )
    browser = browser_type.launch(
        **launch_arguments, proxy={"server": f"localhost:{server.PORT}"}
    )

    page = browser.new_page()
    page.goto("http://non-existent.test/target.html")
    assert page.title() == "Served by the proxy"

    page2 = browser.new_page()
    page2.goto("http://non-existent.test/target.html")
    assert page2.title() == "Served by the proxy"

    browser.close()


def test_PR_004_should_work_with_ip_port_notion(
    browser_type: BrowserType, launch_arguments: Dict, server: Server
) -> None:
    server.set_route(
        "/target.html", respond("<html><title>Served by the proxy</title></html>")
    )
    browser = browser_type.launch(
        **launch_arguments, proxy={"server": f"127.0.0.1:{server.PORT}"}
    )
    page = browser.new_page()
    page.goto("http://non-existent.test/target.html")
    assert page.title() == "Served by the proxy"
    browser.close()


@pytest.mark.parametrize(
    "additional_bypass", [False, True], ids=["by_default", "with_other_bypasses"]
)
@pytest.mark.parametrize(
    "target",
    ["localhost", "127.0.0.1", "169.254.3.4"],
    ids=["localhost", "loopback_address", "link_local"],
)
def test_PR_005_should_proxy_local_network_requests(
    additional_bypass: bool,
    target: str,
    platform: str,
    browser_name: str,
    browser_type: BrowserType,
    launch_arguments: Dict,
    server: Server,
    proxy_server: ProxyServer,
    browser_channel: Optional[str],
) -> None:
    if (
        browser_name == "webkit"
        and platform == "darwin"
        and target in ["localhost", "127.0.0.1"]
        and additional_bypass
    ):
        pytest.skip("Mac webkit does not proxy localhost when bypass rules are set.")
    if browser_channel and browser_channel.startswith("msedge"):
        pytest.skip("times out while loading the page")

    path = f"/target-{str(additional_bypass).lower()}-{target}.html"
    server.set_route(path, respond("<html><title>Served by the proxy</title></html>"))

    url = f"http://{target}:55555{path}"
    proxy_server.forward_to(server.PORT)
    browser = browser_type.launch(
        **launch_arguments,
        proxy={
            "server": f"localhost:{proxy_server.PORT}",
            "bypass": (
                "1.non.existent.domain.for.the.test" if additional_bypass else None
            ),
        },
    )

    page = browser.new_page()
    page.goto(url)
    assert url in proxy_server.request_urls
    assert page.title() == "Served by the proxy"

    try:
        page.goto("http://1.non.existent.domain.for.the.test/foo.html")
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

    browser.close()


@pytest.mark.parametrize("host", ["localhost", "127.0.0.1"])
def test_PR_006_should_allow_bypassing_requests(
    host: str,
    browser_type: BrowserType,
    launch_arguments: Dict,
    server: Server,
    proxy_server: ProxyServer,
) -> None:
    server.set_route(
        "/proxied/target.html",
        respond("<html><title>Served by the server</title></html>"),
    )
    server.set_route(
        "/target.html", respond("<html><title>Served by the proxy</title></html>")
    )
    proxy_server.forward_to(server.PORT, remove_prefix="/proxied")

    browser = browser_type.launch(
        **launch_arguments,
        proxy={"server": f"localhost:{proxy_server.PORT}", "bypass": host},
    )
    page = browser.new_page()
    page.goto(f"http://{host}:{server.PORT}/proxied/target.html")
    assert page.title() == "Served by the server"
    browser.close()


def test_PR_007_should_authenticate(
    browser_type: BrowserType, launch_arguments: Dict, server: Server
) -> None:
    def handle_target(request: TestServerRequest) -> None:
        auth = request.getHeader("proxy-authorization")
        if not auth:
            request.setResponseCode(407, b"Proxy Authentication Required")
            request.setHeader(
                "Proxy-Authenticate", 'Basic realm="Access to internal site"'
            )
            request.finish()
        else:
            request.write(f"<html><title>{auth}</title></html>".encode())
            request.finish()

    def handle_protected(request: TestServerRequest) -> None:
        if not request.getHeader("proxy-authorization"):
            request.setResponseCode(407)
            request.setHeader(
                "Proxy-Authenticate", 'Basic realm="Access to internal site"'
            )
            request.finish()
            return
        request.setResponseCode(401)
        request.setHeader("WWW-Authenticate", 'Basic realm="site"')
        request.write((request.getHeader("authorization") or "no credentials").encode())
        request.finish()

    server.set_route("/target.html", handle_target)
    server.set_route("/protected.html", handle_protected)
    browser = browser_type.launch(
        **launch_arguments,
        proxy={"server": server.HOST, "username": "user", "password": "secret"},
    )
    page = browser.new_page()
    page.goto("http://non-existent.test/target.html")
    assert page.title() == "Basic " + base64.b64encode(b"user:secret").decode()
    # Proxy credentials must not be sent to the website's own auth challenge.
    response = page.goto("http://non-existent.com/protected.html")
    assert response
    assert response.status == 401
    assert page.locator("body").text_content() == "no credentials"
    browser.close()


def test_PR_008_should_reconnect_with_credentials_after_connect_407_closes_the_socket(
    browser_type: BrowserType,
    launch_arguments: Dict,
    https_server: Server,
    proxy_server: ProxyServer,
) -> None:
    # Some HTTP proxies send 407 and close the socket on the first CONNECT, expecting
    # the client to reconnect on a new TCP connection with Proxy-Authorization.
    https_server.set_route(
        "/target.html",
        respond("<html><title>Served by https server via proxy</title></html>"),
    )
    proxy_server.forward_to(https_server.PORT, allow_connect_requests=True)

    connect_attempts: List[bool] = []
    closed_first_connect = False

    def auth_handler(proxy_request: ProxyRequest) -> bool:
        nonlocal closed_first_connect
        # WebKit on Windows uses libcurl and sends Proxy-Authorization preemptively
        # on every CONNECT, while libsoup on Linux/macOS sends it only after a 407.
        # Force the first CONNECT to fail regardless to deterministically exercise
        # the reconnect path on all platforms.
        if proxy_request.method != "CONNECT" or not proxy_request.headers.get(
            "host", ""
        ).startswith("non-existent.test"):
            return True
        connect_attempts.append(bool(proxy_request.headers.get("proxy-authorization")))
        if not closed_first_connect:
            closed_first_connect = True
            return False
        return bool(proxy_request.headers.get("proxy-authorization"))

    proxy_server.set_auth_handler(auth_handler)

    browser = browser_type.launch(
        **launch_arguments,
        proxy={"server": proxy_server.HOST, "username": "user", "password": "secret"},
    )
    page = browser.new_page(ignore_https_errors=True)
    page.goto("https://non-existent.test/target.html")
    assert page.title() == "Served by https server via proxy"
    assert len(connect_attempts) >= 2
    assert any(connect_attempts)
    browser.close()


def test_PR_009_should_work_with_authenticate_followed_by_redirect(
    browser_type: BrowserType, launch_arguments: Dict, server: Server
) -> None:
    def has_auth(request: TestServerRequest) -> bool:
        auth = request.getHeader("proxy-authorization")
        if not auth:
            request.setResponseCode(407, b"Proxy Authentication Required")
            request.setHeader(
                "Proxy-Authenticate", 'Basic realm="Access to internal site"'
            )
            request.finish()
            return False
        return True

    def handle_page1(request: TestServerRequest) -> None:
        if not has_auth(request):
            return
        request.setResponseCode(302)
        request.setHeader("location", "/page2.html")
        request.finish()

    def handle_page2(request: TestServerRequest) -> None:
        if not has_auth(request):
            return
        request.write(b"<html><title>Served by the proxy</title></html>")
        request.finish()

    server.set_route("/page1.html", handle_page1)
    server.set_route("/page2.html", handle_page2)
    browser = browser_type.launch(
        **launch_arguments,
        proxy={"server": server.HOST, "username": "user", "password": "secret"},
    )
    page = browser.new_page()
    page.goto("http://non-existent.test/page1.html")
    assert page.title() == "Served by the proxy"
    browser.close()


def test_PR_010_should_exclude_patterns(
    browser_type: BrowserType,
    launch_arguments: Dict,
    server: Server,
    browser_channel: Optional[str],
) -> None:
    if browser_channel and browser_channel.startswith("msedge"):
        pytest.skip("times out while loading the page")

    server.set_route(
        "/target.html", respond("<html><title>Served by the proxy</title></html>")
    )
    # FYI: using long and weird domain names to avoid ATT DNS hijacking
    # that resolves everything to some weird search results page.
    #
    # @see https://gist.github.com/CollinChaffin/24f6c9652efb3d6d5ef2f5502720ef00
    browser = browser_type.launch(
        **launch_arguments,
        proxy={
            "server": server.HOST,
            "bypass": "1.non.existent.domain.for.the.test, 2.non.existent.domain.for.the.test, .another.test",
        },
    )

    page = browser.new_page()
    page.goto("http://0.non.existent.domain.for.the.test/target.html")
    assert page.title() == "Served by the proxy"
    page.close()

    page = browser.new_page()
    with pytest.raises(Error) as exc_info:
        page.goto("http://1.non.existent.domain.for.the.test/target.html")
    assert exc_info.value.message
    page.close()

    page = browser.new_page()
    with pytest.raises(Error) as exc_info:
        page.goto("http://2.non.existent.domain.for.the.test/target.html")
    assert exc_info.value.message
    page.close()

    page = browser.new_page()
    with pytest.raises(Error) as exc_info:
        page.goto("http://foo.is.the.another.test/target.html")
    assert exc_info.value.message
    page.close()

    page = browser.new_page()
    page.goto("http://3.non.existent.domain.for.the.test/target.html")
    assert page.title() == "Served by the proxy"
    page.close()

    browser.close()


@pytest.mark.parametrize("host", ["localhost", "127.0.0.1"])
def test_PR_011_should_bypass_proxy_for_is_in_bypass_list(
    host: str,
    browser_type: BrowserType,
    launch_arguments: Dict,
    server: Server,
    proxy_server: ProxyServer,
) -> None:
    proxy_server.forward_to(server.PORT, remove_prefix="/proxied")
    server.set_route(
        "/proxied/target.html",
        respond("<html><title>Served by the server</title></html>"),
    )
    server.set_route(
        "/target.html", respond("<html><title>Served by the proxy</title></html>")
    )
    browser = browser_type.launch(
        **launch_arguments,
        proxy={"server": f"localhost:{proxy_server.PORT}", "bypass": host},
    )
    page = browser.new_page()
    page.goto(f"http://{host}:{server.PORT}/proxied/target.html")
    assert page.title() == "Served by the server"
    browser.close()


def test_PR_012_should_use_socks_proxy(
    browser_type: BrowserType, launch_arguments: Dict, socks_port: int
) -> None:
    browser = browser_type.launch(
        **launch_arguments, proxy={"server": f"socks5://localhost:{socks_port}"}
    )
    page = browser.new_page()
    page.goto("http://non-existent.test")
    assert page.title() == "Served by the SOCKS proxy"
    browser.close()


def test_PR_013_should_use_socks_proxy_in_second_page(
    browser_type: BrowserType, launch_arguments: Dict, socks_port: int
) -> None:
    browser = browser_type.launch(
        **launch_arguments, proxy={"server": f"socks5://localhost:{socks_port}"}
    )

    page = browser.new_page()
    page.goto("http://non-existent.test")
    assert page.title() == "Served by the SOCKS proxy"

    page2 = browser.new_page()
    page2.goto("http://non-existent.test")
    assert page2.title() == "Served by the SOCKS proxy"

    browser.close()


def test_PR_014_does_launch_without_a_port(
    browser_type: BrowserType, launch_arguments: Dict
) -> None:
    browser = browser_type.launch(
        **launch_arguments, proxy={"server": "http://localhost"}
    )
    browser.close()


@pytest.mark.skip(reason="fixme: Non-emulated user agent is used in proxy CONNECT")
def test_PR_015_should_use_proxy_with_emulated_user_agent(
    browser_type: BrowserType, launch_arguments: Dict
) -> None:
    request_text = ""
    # This is our proxy server
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(16)

    def serve() -> None:
        nonlocal request_text
        while True:
            try:
                conn, _ = listener.accept()
            except OSError:
                return
            data = conn.recv(65536)
            if data:
                request_text = data.decode("latin-1")
            conn.close()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()

    browser = browser_type.launch(
        **launch_arguments,
        proxy={"server": f"http://127.0.0.1:{listener.getsockname()[1]}"},
    )

    page = browser.new_page(user_agent="MyUserAgent")

    # HTTPS over HTTP proxy will start with CONNECT request.
    try:
        page.goto("https://bing.com/")
    except Error:
        pass
    browser.close()
    listener.close()
    thread.join()
    # This connect request should have emulated user agent.
    assert "MyUserAgent" in request_text


def test_PR_016_should_use_socks_proxy_for_websocket_requests(
    browser_type: BrowserType, launch_arguments: Dict, server: Server
) -> None:
    socks_server = SocksForwardingServer(
        forward_port=server.PORT, allowed_target_port=1337
    )
    browser = browser_type.launch(
        **launch_arguments, proxy={"server": socks_server.proxy_server_addr}
    )
    server.send_on_web_socket_connection(b"incoming")
    server.set_route(
        "/target.html", respond("<html><title>Served by the proxy</title></html>")
    )

    page = browser.new_page()

    # Hosts get resolved by the client
    page.goto("http://fake-localhost-127-0-0-1.nip.io:1337/target.html")
    assert page.title() == "Served by the proxy"

    value = page.evaluate(
        """() => {
        let cb;
        const result = new Promise(f => cb = f);
        const ws = new WebSocket('ws://fake-localhost-127-0-0-1.nip.io:1337/ws');
        ws.addEventListener('message', data => { ws.close(); cb(data.data); });
        return result;
    }"""
    )
    assert value == "incoming"

    browser.close()
    socks_server.close()


def test_PR_017_should_use_http_proxy_for_websocket_requests(
    browser_name: str,
    browser_type: BrowserType,
    launch_arguments: Dict,
    server: Server,
    proxy_server: ProxyServer,
    is_win: bool,
    is_mac: bool,
    mac_version: int,
    browser_channel: Optional[str],
) -> None:
    if is_mac and mac_version == 13:
        pytest.skip("Times out on Mac 13")

    proxy_server.forward_to(server.PORT, allow_connect_requests=True)
    browser = browser_type.launch(
        **launch_arguments, proxy={"server": f"localhost:{proxy_server.PORT}"}
    )

    server.send_on_web_socket_connection(b"incoming")
    server.set_route(
        "/target.html", respond("<html><title>Served by the proxy</title></html>")
    )

    page = browser.new_page()

    page.goto("http://fake-localhost-127-0-0-1.nip.io:1337/target.html")
    assert page.title() == "Served by the proxy"

    value = page.evaluate(
        """() => {
        let cb;
        const result = new Promise(f => cb = f);
        const ws = new WebSocket('ws://fake-localhost-127-0-0-1.nip.io:1337/ws');
        ws.addEventListener('message', data => { ws.close(); cb(data.data); });
        return result;
    }"""
    )
    assert value == "incoming"

    # WebKit does not use CONNECT for websockets, but other browsers do.
    if browser_name == "webkit":
        assert (
            "/ws"
            if is_win and not browser_channel
            else "ws://fake-localhost-127-0-0-1.nip.io:1337/ws"
        ) in proxy_server.ws_urls
    else:
        assert "fake-localhost-127-0-0-1.nip.io:1337" in proxy_server.connect_hosts

    browser.close()
