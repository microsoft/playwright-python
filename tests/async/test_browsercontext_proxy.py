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
from typing import AsyncGenerator, Awaitable, Callable

import pytest
from flaky import flaky

from playwright.async_api import Browser, BrowserContext
from tests.server import Server, TestServerRequest


@pytest.fixture(scope="session")
async def browser(
    browser_factory: "Callable[..., asyncio.Future[Browser]]",
) -> AsyncGenerator[Browser, None]:
    browser = await browser_factory(proxy={"server": "dummy"})
    yield browser
    await browser.close()


async def test_should_use_proxy(
    context_factory: "Callable[..., asyncio.Future[BrowserContext]]", server: Server
) -> None:
    server.set_route(
        "/target.html",
        lambda r: (
            r.write(b"<html><title>Served by the proxy</title></html>"),
            r.finish(),
        ),
    )
    context = await context_factory(proxy={"server": f"localhost:{server.PORT}"})
    page = await context.new_page()
    await page.goto("http://non-existent.com/target.html")
    assert await page.title() == "Served by the proxy"


async def test_proxy_should_allow_none_for_optional_settings(
    context_factory: "Callable[..., asyncio.Future[BrowserContext]]", server: Server
) -> None:
    server.set_route(
        "/target.html",
        lambda r: (
            r.write(b"<html><title>Served by the proxy</title></html>"),
            r.finish(),
        ),
    )
    context = await context_factory(
        proxy={
            "server": f"localhost:{server.PORT}",
            "username": None,
            "password": None,
            "bypass": None,
        }
    )
    page = await context.new_page()
    await page.goto("http://non-existent.com/target.html")
    assert await page.title() == "Served by the proxy"


async def test_should_use_proxy_for_second_page(
    context_factory: "Callable[..., Awaitable[BrowserContext]]", server: Server
) -> None:
    server.set_route(
        "/target.html",
        lambda r: (
            r.write(b"<html><title>Served by the proxy</title></html>"),
            r.finish(),
        ),
    )
    context = await context_factory(proxy={"server": f"localhost:{server.PORT}"})

    page1 = await context.new_page()
    await page1.goto("http://non-existent.com/target.html")
    assert await page1.title() == "Served by the proxy"

    page2 = await context.new_page()
    await page2.goto("http://non-existent.com/target.html")
    assert await page2.title() == "Served by the proxy"


async def test_should_work_with_ip_port_notion(
    context_factory: "Callable[..., Awaitable[BrowserContext]]", server: Server
) -> None:
    server.set_route(
        "/target.html",
        lambda r: (
            r.write(b"<html><title>Served by the proxy</title></html>"),
            r.finish(),
        ),
    )
    context = await context_factory(proxy={"server": f"127.0.0.1:{server.PORT}"})
    page = await context.new_page()
    await page.goto("http://non-existent.com/target.html")
    assert await page.title() == "Served by the proxy"


@flaky  # Upstream flaky
async def test_should_authenticate(
    context_factory: "Callable[..., Awaitable[BrowserContext]]", server: Server
) -> None:
    def handler(req: TestServerRequest) -> None:
        auth = req.getHeader("proxy-authorization")
        if not auth:
            req.setHeader(
                b"Proxy-Authenticate", b'Basic realm="Access to internal site"'
            )
            req.setResponseCode(407)
        else:
            req.write(f"<html><title>{auth}</title></html>".encode("utf-8"))
        req.finish()

    server.set_route("/target.html", handler)

    context = await context_factory(
        proxy={
            "server": f"localhost:{server.PORT}",
            "username": "user",
            "password": "secret",
        }
    )
    page = await context.new_page()
    await page.goto("http://non-existent.com/target.html")
    assert await page.title() == "Basic " + base64.b64encode(b"user:secret").decode(
        "utf-8"
    )


@flaky  # Upstream flaky
async def test_should_authenticate_with_empty_password(
    context_factory: "Callable[..., Awaitable[BrowserContext]]", server: Server
) -> None:
    def handler(req: TestServerRequest) -> None:
        auth = req.getHeader("proxy-authorization")
        if not auth:
            req.setHeader(
                b"Proxy-Authenticate", b'Basic realm="Access to internal site"'
            )
            req.setResponseCode(407)
        else:
            req.write(f"<html><title>{auth}</title></html>".encode("utf-8"))
        req.finish()

    server.set_route("/target.html", handler)

    context = await context_factory(
        proxy={"server": f"localhost:{server.PORT}", "username": "user", "password": ""}
    )
    page = await context.new_page()
    await page.goto("http://non-existent.com/target.html")
    assert await page.title() == "Basic " + base64.b64encode(b"user:").decode("utf-8")
