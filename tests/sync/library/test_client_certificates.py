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

"""Port of tests/library/client-certificates.spec.ts."""

import concurrent.futures
import os
import re
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    List,
    Tuple,
    Union,
)
from urllib.parse import urlparse

import pytest

from playwright._impl._api_structures import ClientCertificate
from playwright.sync_api import (
    Browser,
    BrowserContext,
    BrowserType,
    Error,
    Page,
    Playwright,
    ProxySettings,
    Route,
    expect,
    sync_playwright,
)
from tests.helpers.client_certificate_server import (
    ClientCertificateServer,
    HandshakeRejectingServer,
    PeerInfo,
    RenegotiatingServer,
    Response,
)
from tests.helpers.forwarding_proxy import ConnectForwardingProxy, SocksForwardingServer
from tests.server import Server, TestServerRequest

LaunchPersistent = Callable[..., Tuple[BrowserContext, Page]]

DUMMY_FILE_NAME = __file__
VALIDATION_SUB_TESTS: List[Tuple[Dict[str, Any], str]] = [
    (
        {"client_certificates": [{"origin": "test"}]},
        "None of cert, key, passphrase or pfx is specified",
    ),
    (
        {
            "client_certificates": [
                {
                    "origin": "test",
                    "certPath": DUMMY_FILE_NAME,
                    "keyPath": DUMMY_FILE_NAME,
                    "pfxPath": DUMMY_FILE_NAME,
                    "passphrase": DUMMY_FILE_NAME,
                }
            ]
        },
        "pfx is specified together with cert, key or passphrase",
    ),
]


@pytest.fixture
def start_cc_server() -> Generator[Callable[..., str], None, None]:
    """Port of the startCCServer fixture."""
    servers: List[ClientCertificateServer] = []

    def start(
        http2: bool = False,
        enable_http1_fallback_when_using_http2: bool = False,
        use_fake_localhost: bool = False,
        reject_unauthorized: bool = False,
    ) -> str:
        server = ClientCertificateServer(
            http2=http2,
            allow_http1=enable_http1_fallback_when_using_http2,
            reject_unauthorized=reject_unauthorized,
        )
        servers.append(server)
        host = "local.playwright" if use_fake_localhost else "127.0.0.1"
        return f"https://{host}:{server.port}/"

    yield start
    for server in servers:
        server.close()


@pytest.fixture
def proxy_server() -> Generator[ConnectForwardingProxy, None, None]:
    """Port of the proxyServer fixture in tests/config/serverFixtures.ts."""
    proxy = ConnectForwardingProxy()
    yield proxy
    proxy.close()


def origin(url: str) -> str:
    """Like new URL(url).origin."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def client_certificate(
    assetdir: Path, origin: str, kind: str = "trusted"
) -> ClientCertificate:
    """The certPath and keyPath of client-certificates/client/<kind>, for origin."""
    return {
        "origin": origin,
        "certPath": assetdir / f"client-certificates/client/{kind}/cert.pem",
        "keyPath": assetdir / f"client-certificates/client/{kind}/key.pem",
    }


def test_CC_001_fetch_validate_input(playwright: Playwright) -> None:
    for context_options, expected in VALIDATION_SUB_TESTS:
        with pytest.raises(Error) as exc_info:
            playwright.request.new_context(**context_options)
        assert expected in exc_info.value.message


def test_CC_002_fetch_should_fail_with_no_client_certificates_provided(
    playwright: Playwright, start_cc_server: Callable[..., str]
) -> None:
    server_url = start_cc_server()
    request = playwright.request.new_context(ignore_https_errors=True)
    response = request.get(server_url)
    assert response.status == 401
    assert (
        "Sorry, but you need to provide a client certificate to continue."
        in response.text()
    )
    request.dispose()


def test_CC_003_fetch_should_keep_supporting_http(
    playwright: Playwright, server: Server, assetdir: Path
) -> None:
    request = playwright.request.new_context(
        ignore_https_errors=True,
        client_certificates=[client_certificate(assetdir, origin(server.PREFIX))],
    )
    response = request.get(server.PREFIX + "/one-style.html")
    assert response.url == server.PREFIX + "/one-style.html"
    assert response.status == 200
    assert "<div>hello, world!</div>" in response.text()
    request.dispose()


def test_CC_004_fetch_should_throw_with_untrusted_client_certs(
    playwright: Playwright, start_cc_server: Callable[..., str], assetdir: Path
) -> None:
    server_url = start_cc_server()
    request = playwright.request.new_context(
        ignore_https_errors=True,
        client_certificates=[
            client_certificate(assetdir, origin(server_url), "self-signed")
        ],
    )
    response = request.get(server_url)
    assert response.url == server_url
    assert response.status == 403
    assert "Sorry Bob, certificates from Bob are not welcome here." in response.text()
    request.dispose()


def test_CC_005_fetch_pass_with_trusted_client_certificates(
    playwright: Playwright, start_cc_server: Callable[..., str], assetdir: Path
) -> None:
    server_url = start_cc_server()
    request = playwright.request.new_context(
        ignore_https_errors=True,
        client_certificates=[client_certificate(assetdir, origin(server_url))],
    )
    response = request.get(server_url)
    assert response.url == server_url
    assert response.status == 200
    assert "Hello Alice, your certificate was issued by localhost!" in response.text()
    request.dispose()


def test_CC_006_fetch_should_not_leak_client_certificate_to_cross_origin_redirect_target(
    playwright: Playwright, start_cc_server: Callable[..., str], assetdir: Path
) -> None:
    target_url = start_cc_server()

    # Standalone HTTPS server (not cert-required) that 302-redirects to the cert-required server.
    def redirect(peer: PeerInfo) -> Response:
        return 302, {"Location": target_url}, b""

    redirect_server = ClientCertificateServer(request_cert=False, respond=redirect)
    # Use 'localhost' for the redirect origin so it differs from the target's '127.0.0.1' origin
    # even though both resolve to the loopback interface and share the same trusted CA.
    redirect_url = f"https://localhost:{redirect_server.port}/redir"

    request = playwright.request.new_context(
        ignore_https_errors=True,
        # Cert is scoped to the redirect *origin*, not the target — it must not follow the redirect.
        client_certificates=[client_certificate(assetdir, origin(redirect_url))],
    )
    response = request.get(redirect_url)
    assert response.url == target_url
    assert response.status == 401
    assert "you need to provide a client certificate" in response.text()
    request.dispose()
    redirect_server.close()


def test_CC_007_fetch_pass_with_trusted_client_certificates_in_pfx_format(
    playwright: Playwright, start_cc_server: Callable[..., str], assetdir: Path
) -> None:
    server_url = start_cc_server()
    request = playwright.request.new_context(
        ignore_https_errors=True,
        client_certificates=[
            {
                "origin": origin(server_url),
                "pfxPath": assetdir / "client-certificates/client/trusted/cert.pfx",
                "passphrase": "secure",
            }
        ],
    )
    response = request.get(server_url)
    assert response.url == server_url
    assert response.status == 200
    assert "Hello Alice, your certificate was issued by localhost!" in response.text()
    request.dispose()


def test_CC_008_fetch_pass_with_trusted_client_certificates_and_when_a_http_proxy_is_used(
    playwright: Playwright,
    start_cc_server: Callable[..., str],
    proxy_server: ConnectForwardingProxy,
    assetdir: Path,
) -> None:
    server_url = start_cc_server()
    proxy_server.forward_to(urlparse(server_url).port or 0)
    request = playwright.request.new_context(
        ignore_https_errors=True,
        client_certificates=[client_certificate(assetdir, origin(server_url))],
        proxy={"server": f"localhost:{proxy_server.PORT}"},
    )
    assert proxy_server.connect_hosts == []
    response = request.get(server_url)
    assert proxy_server.connect_hosts == [urlparse(server_url).netloc]
    assert response.url == server_url
    assert response.status == 200
    assert "Hello Alice, your certificate was issued by localhost!" in response.text()
    request.dispose()


def test_CC_009_fetch_pass_with_trusted_client_certificates_and_when_a_socks_proxy_is_used(
    playwright: Playwright, start_cc_server: Callable[..., str], assetdir: Path
) -> None:
    server_url = start_cc_server()
    server_port = urlparse(server_url).port or 0
    socks_server = SocksForwardingServer(
        forward_port=server_port, allowed_target_port=server_port
    )
    request = playwright.request.new_context(
        ignore_https_errors=True,
        client_certificates=[client_certificate(assetdir, origin(server_url))],
        proxy={"server": socks_server.proxy_server_addr},
    )
    assert socks_server.connect_hosts == []
    response = request.get(server_url)
    assert socks_server.connect_hosts == [urlparse(server_url).netloc]
    assert response.url == server_url
    assert response.status == 200
    assert "Hello Alice, your certificate was issued by localhost!" in response.text()
    request.dispose()
    socks_server.close()


def test_CC_010_fetch_should_throw_a_http_error_if_the_pfx_passphrase_is_incorect(
    playwright: Playwright, start_cc_server: Callable[..., str], assetdir: Path
) -> None:
    server_url = start_cc_server()
    request = playwright.request.new_context(
        ignore_https_errors=True,
        client_certificates=[
            {
                "origin": origin(server_url),
                "pfxPath": assetdir / "client-certificates/client/trusted/cert.pfx",
                "passphrase": "this-password-is-incorrect",
            }
        ],
    )
    with pytest.raises(Error) as exc_info:
        request.get(server_url)
    assert "mac verify failure" in exc_info.value.message
    request.dispose()


def test_CC_011_fetch_should_fail_with_matching_certificates_in_legacy_pfx_format(
    playwright: Playwright, start_cc_server: Callable[..., str], assetdir: Path
) -> None:
    server_url = start_cc_server()
    request = playwright.request.new_context(
        ignore_https_errors=True,
        client_certificates=[
            {
                "origin": origin(server_url),
                "pfxPath": assetdir
                / "client-certificates/client/trusted/cert-legacy.pfx",
                "passphrase": "secure",
            }
        ],
    )
    with pytest.raises(Error) as exc_info:
        request.get(server_url)
    assert "Unsupported TLS certificate" in exc_info.value.message
    request.dispose()


def test_CC_012_fetch_should_work_in_the_browser_with_request_interception(
    browser: Browser,
    playwright: Playwright,
    start_cc_server: Callable[..., str],
    assetdir: Path,
) -> None:
    server_url = start_cc_server()
    request = playwright.request.new_context(
        ignore_https_errors=True,
        client_certificates=[client_certificate(assetdir, origin(server_url))],
    )
    page = browser.new_page(ignore_https_errors=True)

    def handler(route: Route) -> None:
        response = request.fetch(route.request)
        route.fulfill(response=response)

    page.route("**/*", handler)
    page.goto(server_url)
    expect(page.get_by_test_id("message")).to_have_text(
        "Hello Alice, your certificate was issued by localhost!"
    )
    page.close()
    request.dispose()


def test_CC_013_browser_validate_input(browser: Browser) -> None:
    for context_options, expected in VALIDATION_SUB_TESTS:
        with pytest.raises(Error) as exc_info:
            browser.new_context(**context_options)
        assert expected in exc_info.value.message


def test_CC_014_browser_should_keep_supporting_http(
    browser: Browser, server: Server, assetdir: Path
) -> None:
    page = browser.new_page(
        client_certificates=[client_certificate(assetdir, origin(server.PREFIX))],
    )
    page.goto(server.PREFIX + "/one-style.html")
    expect(page.get_by_text("hello, world!")).to_be_visible()
    expect(page.locator("body")).to_have_css("background-color", "rgb(255, 192, 203)")
    page.close()


def test_CC_015_browser_should_pass_through_to_non_matching_origin_with_self_signed_cert(
    browser: Browser, assetdir: Path, https_server: Server
) -> None:
    def handle(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("Content-Type", "text/html")
        request.write(
            b'<html><body><div data-testid="message">hello</div></body></html>'
        )
        request.finish()

    https_server.set_route("/hello.html", handle)
    page = browser.new_page(
        client_certificates=[client_certificate(assetdir, "https://not-matching.com")],
    )
    page.goto(https_server.PREFIX + "/hello.html")
    expect(page.get_by_test_id("message")).to_have_text("hello")
    page.close()


def test_CC_016_browser_should_not_intercept_tls_for_origins_without_a_client_certificate(
    browser: Browser, assetdir: Path, https_server: Server
) -> None:
    # If the proxy intercepted this origin, the browser would see its self-signed cert (CN=localhost)
    # instead of the real server cert (CN=playwright-test upstream).
    page = browser.new_page(
        client_certificates=[client_certificate(assetdir, "https://not-matching.com")],
    )
    response = page.goto(https_server.EMPTY_PAGE)
    assert response
    assert response.ok is True
    security_details = response.security_details()
    assert security_details
    subject_name = security_details.get("subjectName")
    assert subject_name
    assert "playwright-test" in subject_name
    page.close()


def test_CC_017_browser_should_fail_with_no_client_certificates(
    browser: Browser,
    start_cc_server: Callable[..., str],
    assetdir: Path,
    browser_name: str,
    is_mac: bool,
) -> None:
    server_url = start_cc_server(use_fake_localhost=browser_name == "webkit" and is_mac)
    page = browser.new_page(
        ignore_https_errors=True,
        client_certificates=[client_certificate(assetdir, "https://not-matching.com")],
    )
    page.goto(server_url)
    expect(page.get_by_test_id("message")).to_have_text(
        "Sorry, but you need to provide a client certificate to continue."
    )
    page.close()


def test_CC_018_browser_should_fail_with_self_signed_client_certificates(
    browser: Browser,
    start_cc_server: Callable[..., str],
    assetdir: Path,
    browser_name: str,
    is_mac: bool,
) -> None:
    server_url = start_cc_server(use_fake_localhost=browser_name == "webkit" and is_mac)
    page = browser.new_page(
        ignore_https_errors=True,
        client_certificates=[
            client_certificate(assetdir, origin(server_url), "self-signed")
        ],
    )
    page.goto(server_url)
    expect(page.get_by_test_id("message")).to_have_text(
        "Sorry Bob, certificates from Bob are not welcome here."
    )
    page.close()


def test_CC_019_browser_should_complete_browser_tls_handshake_when_server_rejects_client_certificate_after_it(
    browser: Browser,
    start_cc_server: Callable[..., str],
    assetdir: Path,
    browser_name: str,
    is_mac: bool,
) -> None:
    server_url = start_cc_server(
        reject_unauthorized=True,
        use_fake_localhost=browser_name == "webkit" and is_mac,
    )
    page = browser.new_page(
        ignore_https_errors=True,
        client_certificates=[
            client_certificate(assetdir, origin(server_url), "self-signed")
        ],
    )
    try:
        result = page.goto(server_url)
    except Error as error:
        # The server closed the connection with FIN after the TLS handshake.
        assert re.search(
            r"net::ERR_EMPTY_RESPONSE|NS_ERROR_NET_RESET|Connection terminated unexpectedly|The network connection was lost|Failure when receiving data from the peer",
            error.message,
        )
    else:
        # The server reset the connection, which the proxy reports as a client certificate error.
        assert result
        assert result.status == 503
        expect(page.get_by_text("Playwright client-certificate error")).to_be_visible()
    page.close()


def test_CC_020_browser_should_pass_with_matching_certificates(
    browser: Browser,
    start_cc_server: Callable[..., str],
    assetdir: Path,
    browser_name: str,
    is_mac: bool,
) -> None:
    server_url = start_cc_server(use_fake_localhost=browser_name == "webkit" and is_mac)
    page = browser.new_page(
        ignore_https_errors=True,
        client_certificates=[client_certificate(assetdir, origin(server_url))],
    )
    page.goto(server_url)
    expect(page.get_by_test_id("message")).to_have_text(
        "Hello Alice, your certificate was issued by localhost!"
    )
    page.close()


def test_CC_021_browser_should_pass_with_matching_certificates_when_passing_as_content(
    browser: Browser,
    start_cc_server: Callable[..., str],
    assetdir: Path,
    browser_name: str,
    is_mac: bool,
) -> None:
    server_url = start_cc_server(use_fake_localhost=browser_name == "webkit" and is_mac)
    page = browser.new_page(
        ignore_https_errors=True,
        client_certificates=[
            {
                "origin": origin(server_url),
                "cert": (
                    assetdir / "client-certificates/client/trusted/cert.pem"
                ).read_bytes(),
                "key": (
                    assetdir / "client-certificates/client/trusted/key.pem"
                ).read_bytes(),
            }
        ],
    )
    page.goto(server_url)
    expect(page.get_by_test_id("message")).to_have_text(
        "Hello Alice, your certificate was issued by localhost!"
    )
    page.close()


def test_CC_022_browser_should_pass_with_matching_certificates_and_when_a_http_proxy_is_used(
    browser: Browser,
    start_cc_server: Callable[..., str],
    assetdir: Path,
    browser_name: str,
    proxy_server: ConnectForwardingProxy,
    is_mac: bool,
) -> None:
    server_url = start_cc_server(use_fake_localhost=browser_name == "webkit" and is_mac)
    proxy_server.forward_to(urlparse(server_url).port or 0)
    page = browser.new_page(
        ignore_https_errors=True,
        client_certificates=[client_certificate(assetdir, origin(server_url))],
        proxy={"server": f"localhost:{proxy_server.PORT}"},
    )
    assert proxy_server.connect_hosts == []
    page.goto(server_url)
    host = "localhost" if browser_name == "webkit" and is_mac else "127.0.0.1"
    assert list(dict.fromkeys(proxy_server.connect_hosts)) == [
        f"{host}:{urlparse(server_url).port}"
    ]
    expect(page.get_by_test_id("message")).to_have_text(
        "Hello Alice, your certificate was issued by localhost!"
    )
    page.close()


def test_CC_023_browser_should_pass_with_matching_certificates_and_when_a_http_proxy_is_used_from_env(
    browser_name: str,
    launch_arguments: Dict,
    start_cc_server: Callable[..., str],
    assetdir: Path,
    proxy_server: ConnectForwardingProxy,
    is_mac: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Upstream sets HTTPS_PROXY in the test process, which runs the Playwright server
    # (and skips the test where the server is another process). The Python driver is
    # another process, and it reads the environment when it starts: start one with the
    # variable set. Its browser does not get the variable, like upstream's browser, which
    # was launched before the test set it. A thread can run only one sync Playwright, so
    # the new one runs in a thread of its own.
    browser_env: Dict[str, Union[str, float, bool]] = dict(os.environ)
    monkeypatch.setenv("HTTPS_PROXY", f"http://localhost:{proxy_server.PORT}")
    server_url = start_cc_server(use_fake_localhost=browser_name == "webkit" and is_mac)
    proxy_server.forward_to(urlparse(server_url).port or 0)

    def run() -> None:
        with sync_playwright() as playwright:
            browser = playwright[browser_name].launch(
                **launch_arguments, env=browser_env
            )
            page = browser.new_page(
                ignore_https_errors=True,
                client_certificates=[client_certificate(assetdir, origin(server_url))],
            )
            assert proxy_server.connect_hosts == []
            page.goto(server_url)
            host = "localhost" if browser_name == "webkit" and is_mac else "127.0.0.1"
            assert list(dict.fromkeys(proxy_server.connect_hosts)) == [
                f"{host}:{urlparse(server_url).port}"
            ]
            expect(page.get_by_test_id("message")).to_have_text(
                "Hello Alice, your certificate was issued by localhost!"
            )
            page.close()
            browser.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        executor.submit(run).result()


def test_CC_024_browser_should_pass_with_matching_certificates_and_when_a_http_proxy_is_used_from_config_but_env_is_there(
    browser_name: str,
    launch_arguments: Dict,
    start_cc_server: Callable[..., str],
    assetdir: Path,
    proxy_server: ConnectForwardingProxy,
    is_mac: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Like CC-023: start a driver with HTTPS_PROXY set, and a browser without it.
    browser_env: Dict[str, Union[str, float, bool]] = dict(os.environ)
    monkeypatch.setenv("HTTPS_PROXY", "http://this-should-not-taken-into-account:4242")
    server_url = start_cc_server(use_fake_localhost=browser_name == "webkit" and is_mac)
    proxy_server.forward_to(urlparse(server_url).port or 0)

    def run() -> None:
        with sync_playwright() as playwright:
            browser = playwright[browser_name].launch(
                **launch_arguments, env=browser_env
            )
            page = browser.new_page(
                ignore_https_errors=True,
                client_certificates=[client_certificate(assetdir, origin(server_url))],
                proxy={"server": f"localhost:{proxy_server.PORT}"},
            )
            assert proxy_server.connect_hosts == []
            page.goto(server_url)
            host = "localhost" if browser_name == "webkit" and is_mac else "127.0.0.1"
            assert list(dict.fromkeys(proxy_server.connect_hosts)) == [
                f"{host}:{urlparse(server_url).port}"
            ]
            expect(page.get_by_test_id("message")).to_have_text(
                "Hello Alice, your certificate was issued by localhost!"
            )
            page.close()
            browser.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        executor.submit(run).result()


def test_CC_025_browser_should_respect_launch_proxy_and_proxy_bypass(
    browser_type: BrowserType,
    launch_arguments: Dict,
    start_cc_server: Callable[..., str],
    assetdir: Path,
    browser_name: str,
    proxy_server: ConnectForwardingProxy,
    is_mac: bool,
) -> None:
    server_url = start_cc_server(use_fake_localhost=browser_name == "webkit" and is_mac)
    parsed = urlparse(server_url)
    proxy_server.forward_to(parsed.port or 0)
    proxy: ProxySettings = {"server": f"localhost:{proxy_server.PORT}"}
    server_host = (
        f"{'localhost' if browser_name == 'webkit' and is_mac else '127.0.0.1'}"
        f":{parsed.port}"
    )
    client_certificates = [client_certificate(assetdir, origin(server_url))]
    browser = browser_type.launch(**launch_arguments, proxy=proxy)
    page = browser.new_page(
        ignore_https_errors=True, client_certificates=client_certificates
    )
    page.goto(server_url)
    expect(page.get_by_test_id("message")).to_have_text(
        "Hello Alice, your certificate was issued by localhost!"
    )
    # Headed Chromium also sends its own background requests through the launch proxy.
    assert server_host in proxy_server.connect_hosts
    page.close()

    proxy_server.connect_hosts = []
    page = browser.new_page(
        ignore_https_errors=True,
        client_certificates=client_certificates,
        proxy={**proxy, "bypass": parsed.hostname or ""},
    )
    page.goto(server_url)
    expect(page.get_by_test_id("message")).to_have_text(
        "Hello Alice, your certificate was issued by localhost!"
    )
    assert server_host not in proxy_server.connect_hosts
    page.close()
    browser.close()


def test_CC_026_browser_should_pass_with_matching_certificates_and_when_a_socks_proxy_is_used(
    browser: Browser,
    start_cc_server: Callable[..., str],
    assetdir: Path,
    browser_name: str,
    is_mac: bool,
) -> None:
    server_url = start_cc_server(use_fake_localhost=browser_name == "webkit" and is_mac)
    server_port = urlparse(server_url).port or 0
    socks_server = SocksForwardingServer(
        forward_port=server_port, allowed_target_port=server_port
    )
    page = browser.new_page(
        ignore_https_errors=True,
        client_certificates=[client_certificate(assetdir, origin(server_url))],
        proxy={"server": socks_server.proxy_server_addr},
    )
    assert socks_server.connect_hosts == []
    page.goto(server_url)
    host = "localhost" if browser_name == "webkit" and is_mac else "127.0.0.1"
    assert socks_server.connect_hosts == [f"{host}:{server_port}"]
    expect(page.get_by_test_id("message")).to_have_text(
        "Hello Alice, your certificate was issued by localhost!"
    )
    page.close()
    socks_server.close()


def test_CC_027_browser_should_not_hang_on_tls_errors_during_tls_1_2_handshake(
    browser: Browser, assetdir: Path, platform: str, browser_name: str
) -> None:
    for tls_version in ["TLSv1.3", "TLSv1.2"]:
        # TLS version: tls_version
        server = HandshakeRejectingServer(tls_version, host="localhost")
        host = (
            "local.playwright"
            if browser_name == "webkit" and platform == "darwin"
            else "localhost"
        )
        server_url = f"https://{host}:{server.port}/"
        page = browser.new_page(
            ignore_https_errors=True,
            client_certificates=[
                client_certificate(assetdir, origin(server_url), "self-signed")
            ],
        )
        page.goto(server_url)
        expect(
            page.get_by_text(
                "Playwright client-certificate error: Client network socket disconnected before secure TLS connection was established"
            )
        ).to_be_visible()
        page.close()
        server.close()


def test_CC_028_browser_should_pass_with_matching_certificates_in_pfx_format(
    browser: Browser,
    start_cc_server: Callable[..., str],
    assetdir: Path,
    browser_name: str,
    is_mac: bool,
) -> None:
    server_url = start_cc_server(use_fake_localhost=browser_name == "webkit" and is_mac)
    page = browser.new_page(
        ignore_https_errors=True,
        client_certificates=[
            {
                "origin": origin(server_url),
                "pfxPath": assetdir / "client-certificates/client/trusted/cert.pfx",
                "passphrase": "secure",
            }
        ],
    )
    page.goto(server_url)
    expect(page.get_by_test_id("message")).to_have_text(
        "Hello Alice, your certificate was issued by localhost!"
    )
    page.close()


def test_CC_029_browser_should_handle_tls_renegotiation_with_client_certificates(
    browser: Browser, assetdir: Path, browser_name: str, platform: str
) -> None:
    server = RenegotiatingServer(host="localhost")
    host = (
        "local.playwright"
        if browser_name == "webkit" and platform == "darwin"
        else "localhost"
    )
    server_url = f"https://{host}:{server.port}"

    context = browser.new_context(
        ignore_https_errors=True,
        client_certificates=[client_certificate(assetdir, server_url)],
    )

    page = context.new_page()

    # fetch API
    page.goto(server_url)
    response = page.evaluate(
        """async () => {
            const response = await fetch('/from-fetch-api', {
                method: 'POST',
                body: 'client-request-payload'
            });
            return await response.text();
        }"""
    )
    assert response == "\n".join(
        [
            "server received: client-request-payload",
            "0-from-server",
            "1-from-server",
            "2-from-server",
            "3-from-server",
            "server closed the connection",
        ]
    )

    # Gzip encoded CSS Stylesheet
    page.goto(server_url)
    # The <link> would throw with net::ERR_INVALID_CHUNKED_ENCODING
    page.set_content(
        """
        <button>Click me</button>
        <link rel="stylesheet" href="/style.css">
      """
    )
    expect(page.locator("button")).to_have_css(
        "background-color", "rgb(255, 0, 0)"  # red
    )

    context.close()
    server.close()


def test_CC_030_browser_should_pass_with_matching_certificates_in_pfx_format_when_passing_as_content(
    browser: Browser,
    start_cc_server: Callable[..., str],
    assetdir: Path,
    browser_name: str,
    is_mac: bool,
) -> None:
    server_url = start_cc_server(use_fake_localhost=browser_name == "webkit" and is_mac)
    page = browser.new_page(
        ignore_https_errors=True,
        client_certificates=[
            {
                "origin": origin(server_url),
                "pfx": (
                    assetdir / "client-certificates/client/trusted/cert.pfx"
                ).read_bytes(),
                "passphrase": "secure",
            }
        ],
    )
    page.goto(server_url)
    expect(page.get_by_test_id("message")).to_have_text(
        "Hello Alice, your certificate was issued by localhost!"
    )
    page.close()


def test_CC_031_browser_should_fail_with_matching_certificates_in_legacy_pfx_format(
    browser: Browser,
    start_cc_server: Callable[..., str],
    assetdir: Path,
    browser_name: str,
    is_mac: bool,
) -> None:
    server_url = start_cc_server(use_fake_localhost=browser_name == "webkit" and is_mac)
    with pytest.raises(Error) as exc_info:
        browser.new_page(
            ignore_https_errors=True,
            client_certificates=[
                {
                    "origin": origin(server_url),
                    "pfxPath": assetdir
                    / "client-certificates/client/trusted/cert-legacy.pfx",
                    "passphrase": "secure",
                }
            ],
        )
    assert "Unsupported TLS certificate" in exc_info.value.message


def test_CC_032_browser_should_throw_a_http_error_if_the_pfx_passphrase_is_incorect(
    browser: Browser,
    start_cc_server: Callable[..., str],
    assetdir: Path,
    browser_name: str,
    is_mac: bool,
) -> None:
    server_url = start_cc_server(use_fake_localhost=browser_name == "webkit" and is_mac)
    with pytest.raises(Error) as exc_info:
        browser.new_page(
            ignore_https_errors=True,
            client_certificates=[
                {
                    "origin": origin(server_url),
                    "pfxPath": assetdir / "client-certificates/client/trusted/cert.pfx",
                    "passphrase": "this-password-is-incorrect",
                }
            ],
        )
    assert (
        "Failed to load client certificate: mac verify failure"
        in exc_info.value.message
    )


def test_CC_033_browser_should_pass_with_matching_certificates_on_context_api_request_context_instance(
    browser: Browser, start_cc_server: Callable[..., str], assetdir: Path
) -> None:
    server_url = start_cc_server()
    page = browser.new_page(
        ignore_https_errors=True,
        client_certificates=[
            client_certificate(assetdir, origin(server_url)),
            client_certificate(
                assetdir, origin(server_url).replace("localhost", "127.0.0.1")
            ),
        ],
    )
    for url in [server_url, server_url.replace("localhost", "127.0.0.1")]:
        response = page.request.get(url)
        assert response.status == 200
        assert (
            "Hello Alice, your certificate was issued by localhost!" in response.text()
        )
    page.close()


def test_CC_034_browser_should_pass_with_matching_certificates_and_trailing_slash(
    browser: Browser,
    start_cc_server: Callable[..., str],
    assetdir: Path,
    browser_name: str,
    is_mac: bool,
) -> None:
    server_url = start_cc_server(use_fake_localhost=browser_name == "webkit" and is_mac)
    page = browser.new_page(
        ignore_https_errors=True,
        client_certificates=[client_certificate(assetdir, server_url)],
    )
    page.goto(server_url)
    expect(
        page.get_by_text("Hello Alice, your certificate was issued by localhost!")
    ).to_be_visible()
    page.close()


def test_CC_035_browser_should_have_ignore_https_errors_false_by_default(
    browser: Browser,
    https_server: Server,
    assetdir: Path,
    browser_name: str,
    platform: str,
) -> None:
    target_url = (
        https_server.EMPTY_PAGE.replace("localhost", "local.playwright")
        if browser_name == "webkit" and platform == "darwin"
        else https_server.EMPTY_PAGE
    )
    page = browser.new_page(
        client_certificates=[client_certificate(assetdir, origin(target_url))],
    )
    page.goto(target_url)
    expect(
        page.get_by_text("Playwright client-certificate error: self-signed certificate")
    ).to_be_visible()
    page.close()


def test_CC_036_browser_support_http2(
    browser: Browser,
    start_cc_server: Callable[..., str],
    assetdir: Path,
    browser_name: str,
    is_mac: bool,
) -> None:
    if browser_name == "webkit" and is_mac:
        pytest.skip("WebKit on macOS does not proxy localhost")
    server_url = start_cc_server(http2=True)
    page = browser.new_page(
        ignore_https_errors=True,
        client_certificates=[client_certificate(assetdir, origin(server_url))],
    )
    page.goto(server_url.replace("127.0.0.1", "local.playwright"))
    expect(page.get_by_test_id("message")).to_have_text(
        "Sorry, but you need to provide a client certificate to continue."
    )
    expect(page.get_by_test_id("alpn-protocol")).to_have_text("h2")
    expect(page.get_by_test_id("servername")).to_have_text("local.playwright")

    page.goto(server_url)
    expect(page.get_by_test_id("message")).to_have_text(
        "Hello Alice, your certificate was issued by localhost!"
    )
    expect(page.get_by_test_id("alpn-protocol")).to_have_text("h2")
    page.close()


@pytest.mark.only_browser("chromium")
def test_CC_037_browser_support_http2_if_the_browser_only_supports_http1_1(
    browser_type: BrowserType,
    launch_arguments: Dict,
    start_cc_server: Callable[..., str],
    assetdir: Path,
) -> None:
    server_url = start_cc_server(
        http2=True, enable_http1_fallback_when_using_http2=True
    )
    browser = browser_type.launch(**launch_arguments, args=["--disable-http2"])
    page = browser.new_page(
        ignore_https_errors=True,
        client_certificates=[client_certificate(assetdir, origin(server_url))],
    )
    page.goto(server_url.replace("127.0.0.1", "local.playwright"))
    expect(page.get_by_test_id("message")).to_have_text(
        "Sorry, but you need to provide a client certificate to continue."
    )
    expect(page.get_by_test_id("alpn-protocol")).to_have_text("http/1.1")

    page.goto(server_url)
    expect(page.get_by_test_id("message")).to_have_text(
        "Hello Alice, your certificate was issued by localhost!"
    )
    expect(page.get_by_test_id("alpn-protocol")).to_have_text("http/1.1")
    browser.close()


def test_CC_038_browser_should_return_target_connection_errors_when_using_http2(
    browser: Browser,
    start_cc_server: Callable[..., str],
    assetdir: Path,
    browser_name: str,
    is_mac: bool,
) -> None:
    if browser_name == "webkit" and is_mac:
        pytest.skip("WebKit on macOS does not proxy localhost")

    server_url = start_cc_server(http2=True)
    page = browser.new_page(
        client_certificates=[client_certificate(assetdir, origin(server_url))],
    )
    page.goto(server_url)
    expect(
        page.get_by_text("Playwright client-certificate error: self-signed certificate")
    ).to_be_visible()
    page.close()


def test_CC_039_browser_should_handle_rejected_certificate_in_handshake_with_http_2(
    browser: Browser, assetdir: Path, browser_name: str, platform: str
) -> None:
    def respond(peer: PeerInfo) -> Response:
        return 200, {"Content-Type": "text/html"}, b"Hello world"

    # requestCert: true; Node.js rejects unauthorized clients by default.
    server = ClientCertificateServer(
        http2=True, reject_unauthorized=True, host="localhost", respond=respond
    )
    server_url = (
        "https://"
        + (
            "local.playwright"
            if browser_name == "webkit" and platform == "darwin"
            else "localhost"
        )
        + f":{server.port}"
    )

    context = browser.new_context(
        ignore_https_errors=True,
        client_certificates=[
            client_certificate(
                assetdir,
                "https://just-there-that-the-client-certificates-proxy-server-is-getting-launched.com",
            )
        ],
    )

    page = context.new_page()

    # This was triggering an unhandled error before.
    try:
        page.goto(server_url)
    except Error:
        pass

    context.close()
    server.close()


def test_CC_040_browser_persistent_context_validate_input(
    launch_persistent: LaunchPersistent,
) -> None:
    for context_options, expected in VALIDATION_SUB_TESTS:
        with pytest.raises(Error) as exc_info:
            launch_persistent(**context_options)
        assert expected in exc_info.value.message


def test_CC_041_browser_persistent_context_should_pass_with_matching_certificates(
    launch_persistent: LaunchPersistent,
    start_cc_server: Callable[..., str],
    assetdir: Path,
    browser_name: str,
    is_mac: bool,
) -> None:
    server_url = start_cc_server(use_fake_localhost=browser_name == "webkit" and is_mac)
    _, page = launch_persistent(
        ignore_https_errors=True,
        client_certificates=[client_certificate(assetdir, origin(server_url))],
    )
    page.goto(server_url)
    expect(page.get_by_test_id("message")).to_have_text(
        "Hello Alice, your certificate was issued by localhost!"
    )
