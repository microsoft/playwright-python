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

import threading
from pathlib import Path
from typing import Generator, cast

import pytest
from twisted.internet import reactor as _twisted_reactor
from twisted.internet import ssl
from twisted.internet.selectreactor import SelectReactor
from twisted.web import resource, server

from playwright.async_api import Browser, BrowserType, Playwright, Request, expect

reactor = cast(SelectReactor, _twisted_reactor)


class Simple(resource.Resource):
    isLeaf = True

    def render_GET(self, request: Request) -> bytes:
        return b"<html>Hello, world!</html>"


@pytest.fixture(scope="session", autouse=True)
def _client_certificate_server(assetdir: Path) -> Generator[None, None, None]:
    server.Site(Simple())

    certAuthCert = ssl.Certificate.loadPEM(
        (assetdir / "client-certificates/server/server_cert.pem").read_text()
    )
    serverCert = ssl.PrivateCertificate.loadPEM(
        (assetdir / "client-certificates/server/server_key.pem").read_text()
        + (assetdir / "client-certificates/server/server_cert.pem").read_text()
    )

    contextFactory = serverCert.options(certAuthCert)
    site = server.Site(Simple())

    def _run() -> None:
        reactor.listenSSL(8000, site, contextFactory)

    thread = threading.Thread(target=_run)
    thread.start()
    yield
    thread.join()


async def test_should_work_with_new_context(browser: Browser, assetdir: Path) -> None:
    context = await browser.new_context(
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
    page = await context.new_page()
    await page.goto("https://localhost:8000")
    await expect(page.get_by_text("alert certificate required")).to_be_visible()
    await page.goto("https://127.0.0.1:8000")
    await expect(page.get_by_text("Hello, world!")).to_be_visible()

    with pytest.raises(Exception, match="alert certificate required"):
        await page.context.request.get("https://localhost:8000")
    response = await page.context.request.get("https://127.0.0.1:8000")
    assert "Hello, world!" in await response.text()
    await context.close()


async def test_should_work_with_new_persistent_context(
    browser_type: BrowserType, assetdir: Path
) -> None:
    context = await browser_type.launch_persistent_context(
        "",
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
    page = await context.new_page()
    await page.goto("https://localhost:8000")
    await expect(page.get_by_text("alert certificate required")).to_be_visible()
    await page.goto("https://127.0.0.1:8000")
    await expect(page.get_by_text("Hello, world!")).to_be_visible()
    await context.close()


async def test_should_work_with_global_api_request_context(
    playwright: Playwright, assetdir: Path
) -> None:
    request = await playwright.request.new_context(
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
    with pytest.raises(Exception, match="alert certificate required"):
        await request.get("https://localhost:8000")
    response = await request.get("https://127.0.0.1:8000")
    assert "Hello, world!" in await response.text()
    await request.dispose()
