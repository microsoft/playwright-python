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

import sys
import threading
from pathlib import Path
from typing import Dict, Generator, Optional, cast

import OpenSSL.crypto
import OpenSSL.SSL
import pytest
from twisted.internet import reactor as _twisted_reactor
from twisted.internet import ssl
from twisted.internet.selectreactor import SelectReactor
from twisted.web import resource, server
from twisted.web.http import Request

from playwright.sync_api import Browser, BrowserType, Playwright, expect

reactor = cast(SelectReactor, _twisted_reactor)


@pytest.fixture(scope="function", autouse=True)
def _skip_webkit_darwin(browser_name: str) -> None:
    if browser_name == "webkit" and sys.platform == "darwin":
        pytest.skip("WebKit does not proxy localhost on macOS")


class HttpsResource(resource.Resource):
    serverCertificate: ssl.PrivateCertificate
    isLeaf = True

    def _verify_cert_chain(self, cert: Optional[OpenSSL.crypto.X509]) -> bool:
        if not cert:
            return False
        store = OpenSSL.crypto.X509Store()
        store.add_cert(self.serverCertificate.original)
        store_ctx = OpenSSL.crypto.X509StoreContext(store, cert)
        try:
            store_ctx.verify_certificate()
            return True
        except OpenSSL.crypto.X509StoreContextError:
            return False

    def render_GET(self, request: Request) -> bytes:
        tls_socket: OpenSSL.SSL.Connection = request.transport.getHandle()  # type: ignore
        cert = tls_socket.get_peer_certificate()
        parts = []

        if self._verify_cert_chain(cert):
            request.setResponseCode(200)
            parts.append(
                {
                    "key": "message",
                    "value": f"Hello {cert.get_subject().CN}, your certificate was issued by {cert.get_issuer().CN}!",  # type: ignore
                }
            )
        elif cert and cert.get_subject():
            request.setResponseCode(403)
            parts.append(
                {
                    "key": "message",
                    "value": f"Sorry {cert.get_subject().CN}, certificates from {cert.get_issuer().CN} are not welcome here.",
                }
            )
        else:
            request.setResponseCode(401)
            parts.append(
                {
                    "key": "message",
                    "value": "Sorry, but you need to provide a client certificate to continue.",
                }
            )
        return b"".join(
            [
                f'<div data-testid="{part["key"]}">{part["value"]}</div>'.encode()
                for part in parts
            ]
        )


@pytest.fixture(scope="session", autouse=True)
def _client_certificate_server(assetdir: Path) -> Generator[None, None, None]:
    certAuthCert = ssl.Certificate.loadPEM(
        (assetdir / "client-certificates/server/server_cert.pem").read_text()
    )
    serverCert = ssl.PrivateCertificate.loadPEM(
        (assetdir / "client-certificates/server/server_key.pem").read_text()
        + (assetdir / "client-certificates/server/server_cert.pem").read_text()
    )

    contextFactory = serverCert.options(certAuthCert)
    contextFactory.requireCertificate = False
    resource = HttpsResource()
    resource.serverCertificate = serverCert
    site = server.Site(resource)

    def _run() -> None:
        reactor.listenSSL(8000, site, contextFactory)

    thread = threading.Thread(target=_run)
    thread.start()
    yield
    thread.join()


def test_should_throw_with_untrusted_client_certs(
    playwright: Playwright, assetdir: Path
) -> None:
    serverURL = "https://localhost:8000/"
    request = playwright.request.new_context(
        # TODO: Remove this once we can pass a custom CA.
        ignore_https_errors=True,
        client_certificates=[
            {
                "origin": serverURL,
                "certPath": assetdir
                / "client-certificates/client/self-signed/cert.pem",
                "keyPath": assetdir / "client-certificates/client/self-signed/key.pem",
            }
        ],
    )
    with pytest.raises(Exception, match="alert unknown ca"):
        request.get(serverURL)
    request.dispose()


def test_should_work_with_new_context(browser: Browser, assetdir: Path) -> None:
    context = browser.new_context(
        # TODO: Remove this once we can pass a custom CA.
        ignore_https_errors=True,
        client_certificates=[
            {
                "origin": "https://127.0.0.1:8000",
                "certPath": assetdir / "client-certificates/client/trusted/cert.pem",
                "keyPath": assetdir / "client-certificates/client/trusted/key.pem",
            }
        ],
    )
    page = context.new_page()
    page.goto("https://localhost:8000")
    expect(page.get_by_test_id("message")).to_have_text(
        "Sorry, but you need to provide a client certificate to continue."
    )
    page.goto("https://127.0.0.1:8000")
    expect(page.get_by_test_id("message")).to_have_text(
        "Hello Alice, your certificate was issued by localhost!"
    )

    response = page.context.request.get("https://localhost:8000")
    assert (
        "Sorry, but you need to provide a client certificate to continue."
        in response.text()
    )
    response = page.context.request.get("https://127.0.0.1:8000")
    assert "Hello Alice, your certificate was issued by localhost!" in response.text()
    context.close()


def test_should_work_with_new_context_passing_as_content(
    browser: Browser, assetdir: Path
) -> None:
    context = browser.new_context(
        # TODO: Remove this once we can pass a custom CA.
        ignore_https_errors=True,
        client_certificates=[
            {
                "origin": "https://127.0.0.1:8000",
                "cert": (
                    assetdir / "client-certificates/client/trusted/cert.pem"
                ).read_bytes(),
                "key": (
                    assetdir / "client-certificates/client/trusted/key.pem"
                ).read_bytes(),
            }
        ],
    )
    page = context.new_page()
    page.goto("https://localhost:8000")
    expect(page.get_by_test_id("message")).to_have_text(
        "Sorry, but you need to provide a client certificate to continue."
    )
    page.goto("https://127.0.0.1:8000")
    expect(page.get_by_test_id("message")).to_have_text(
        "Hello Alice, your certificate was issued by localhost!"
    )

    response = page.context.request.get("https://localhost:8000")
    assert (
        "Sorry, but you need to provide a client certificate to continue."
        in response.text()
    )
    response = page.context.request.get("https://127.0.0.1:8000")
    assert "Hello Alice, your certificate was issued by localhost!" in response.text()
    context.close()


def test_should_work_with_new_persistent_context(
    browser_type: BrowserType, assetdir: Path, launch_arguments: Dict
) -> None:
    context = browser_type.launch_persistent_context(
        "",
        **launch_arguments,
        # TODO: Remove this once we can pass a custom CA.
        ignore_https_errors=True,
        client_certificates=[
            {
                "origin": "https://127.0.0.1:8000",
                "certPath": assetdir / "client-certificates/client/trusted/cert.pem",
                "keyPath": assetdir / "client-certificates/client/trusted/key.pem",
            }
        ],
    )
    page = context.new_page()
    page.goto("https://localhost:8000")
    expect(page.get_by_test_id("message")).to_have_text(
        "Sorry, but you need to provide a client certificate to continue."
    )
    page.goto("https://127.0.0.1:8000")
    expect(page.get_by_test_id("message")).to_have_text(
        "Hello Alice, your certificate was issued by localhost!"
    )
    context.close()


def test_should_work_with_global_api_request_context(
    playwright: Playwright, assetdir: Path
) -> None:
    request = playwright.request.new_context(
        # TODO: Remove this once we can pass a custom CA.
        ignore_https_errors=True,
        client_certificates=[
            {
                "origin": "https://127.0.0.1:8000",
                "certPath": assetdir / "client-certificates/client/trusted/cert.pem",
                "keyPath": assetdir / "client-certificates/client/trusted/key.pem",
            }
        ],
    )
    response = request.get("https://localhost:8000")
    assert (
        "Sorry, but you need to provide a client certificate to continue."
        in response.text()
    )
    response = request.get("https://127.0.0.1:8000")
    assert "Hello Alice, your certificate was issued by localhost!" in response.text()
    request.dispose()
