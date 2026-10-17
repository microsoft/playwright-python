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

"""Port of tests/library/browsercontext-service-worker-policy.spec.ts."""

from typing import Any, Callable, List

import pytest

from playwright.async_api import BrowserContext, Error, Page, expect
from tests.server import Server, TestServerRequest

WORKER_RESPONSES = {
    "literal": "new Response('<h1>offline</h1>', { headers: { 'Content-Type': 'text/html' } })",
    "cache-only": "caches.match('/offline.html')",
    "network-fallback": "fetch(event.request).catch(() => caches.match('/offline.html'))",
    "preload-fallback": """(async () => {
    try {
      return await event.preloadResponse || await fetch(event.request);
    } catch {
      return caches.match('/offline.html');
    }
  })()""",
}


async def test_WO_027_should_allow_service_workers_by_default(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/serviceworkers/empty/sw.html")
    # The registration serializes to {}, which is truthy in JavaScript only.
    assert await page.evaluate("() => window['registrationPromise']") is not None


@pytest.mark.parametrize("mode", list(WORKER_RESPONSES))
async def test_WO_028_should_allow_service_worker_navigation_while_offline(
    context: BrowserContext,
    page: Page,
    server: Server,
    browser_name: str,
    is_frozen_webkit: bool,
    mode: str,
) -> None:
    # https://github.com/microsoft/playwright/issues/42775
    if is_frozen_webkit:
        pytest.skip("Requires offline emulation in the network process.")
    if browser_name == "firefox" and mode in ("network-fallback", "preload-fallback"):
        pytest.skip(
            "fixme: Firefox does not apply offline emulation to service worker requests."
        )

    network_requests = 0

    def handle_target(request: TestServerRequest) -> None:
        nonlocal network_requests
        network_requests += 1
        request.setHeader("Cache-Control", "no-store")
        request.write(b"online")
        request.finish()

    server.set_route("/target.html", handle_target)

    def handle_offline(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "text/html")
        request.write(b"<h1>offline</h1>")
        request.finish()

    server.set_route("/offline.html", handle_offline)

    preload = (
        "await self.registration.navigationPreload.enable();"
        if mode == "preload-fallback"
        else ""
    )
    worker_response = WORKER_RESPONSES[mode]

    def handle_sw(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "application/javascript")
        request.write(
            f"""
        self.addEventListener('install', event => event.waitUntil((async () => {{
          const cache = await caches.open('offline');
          await cache.add('/offline.html');
          await self.skipWaiting();
        }})()));
        self.addEventListener('activate', event => event.waitUntil((async () => {{
          {preload}
          await self.clients.claim();
        }})()));
        self.addEventListener('fetch', event => {{
          if (event.request.mode === 'navigate')
            event.respondWith({worker_response});
        }});
      """.encode()
        )
        request.finish()

    server.set_route("/sw.js", handle_sw)

    await page.goto(server.EMPTY_PAGE)
    await page.evaluate(
        """async () => {
            await navigator.serviceWorker.register('/sw.js');
            await navigator.serviceWorker.ready;
        }"""
    )
    await page.wait_for_function("() => !!navigator.serviceWorker.controller")
    await context.set_offline(True)

    response = await page.goto(server.PREFIX + "/target.html")
    assert response
    assert response.status == 200
    assert response.from_service_worker is True
    await expect(page.locator("h1")).to_have_text("offline")
    assert await page.evaluate("() => navigator.onLine") is False
    assert network_requests == 0

    new_page = await context.new_page()
    new_response = await new_page.goto(server.PREFIX + "/target.html")
    assert new_response
    assert new_response.status == 200
    assert new_response.from_service_worker is True
    await expect(new_page.locator("h1")).to_have_text("offline")
    assert await new_page.evaluate("() => navigator.onLine") is False
    assert network_requests == 0

    await context.set_offline(False)
    assert (
        await page.evaluate(
            "() => fetch('/target.html').then(response => response.text())"
        )
        == "online"
    )
    assert network_requests == 1


async def test_WO_029_block_blocks_service_worker_registration(
    context_factory: Callable[..., Any], server: Server
) -> None:
    context = await context_factory(service_workers="block")
    page = await context.new_page()
    async with page.expect_console_message(
        lambda evt: evt.text == "Service Worker registration blocked by Playwright"
    ):
        await page.goto(server.PREFIX + "/serviceworkers/empty/sw.html")


async def test_WO_030_block_should_not_throw_error_on_about_blank(
    context_factory: Callable[..., Any],
) -> None:
    # https://github.com/microsoft/playwright/issues/32292
    context = await context_factory(service_workers="block")
    page = await context.new_page()
    errors: List[Error] = []
    page.on("pageerror", lambda error: errors.append(error))
    await page.goto("about:blank")
    assert errors == []


async def test_WO_031_block_should_not_throw_error_in_opaque_sandboxed_iframe(
    context_factory: Callable[..., Any], server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/43113
    context = await context_factory(service_workers="block")
    page = await context.new_page()
    errors: List[Error] = []
    page.on("pageerror", lambda error: errors.append(error))
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        '<iframe sandbox="allow-scripts" srcdoc="<p>Preview</p>"></iframe>'
    )
    await expect(page.frame_locator("iframe").locator("p")).to_have_text("Preview")
    assert errors == []
