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

"""Port of tests/library/ignorehttpserrors.spec.ts."""

import re
from typing import Optional

import pytest

from playwright.async_api import Browser, Error, Route
from tests.server import Server, TestServerRequest

WEBSOCKET_VALUE = """endpoint => {
    let cb;
    const result = new Promise(f => cb = f);
    const ws = new WebSocket(endpoint);
    ws.addEventListener('message', data => { ws.close(); cb(data.data); });
    ws.addEventListener('error', error => cb('Error'));
    return result;
  }"""


async def test_NE_136_should_work_smoke(browser: Browser, https_server: Server) -> None:
    error: Optional[Error] = None
    context = await browser.new_context(ignore_https_errors=True)
    page = await context.new_page()
    try:
        response = await page.goto(https_server.EMPTY_PAGE)
    except Error as e:
        error = e
    assert error is None
    assert response
    assert response.ok is True
    await context.close()


async def test_NE_137_should_isolate_contexts(
    browser: Browser, https_server: Server
) -> None:
    error: Optional[Error] = None
    context = await browser.new_context(ignore_https_errors=True)
    page = await context.new_page()
    try:
        response = await page.goto(https_server.EMPTY_PAGE)
    except Error as e:
        error = e
    assert error is None
    assert response
    assert response.ok is True
    await context.close()

    error = None
    context = await browser.new_context()
    page = await context.new_page()
    try:
        await page.goto(https_server.EMPTY_PAGE)
    except Error as e:
        error = e
    assert error is not None
    await context.close()


async def test_NE_138_should_isolated_contexts_that_share_network_process(
    browser: Browser, https_server: Server, browser_name: str, is_linux: bool
) -> None:
    if browser_name == "webkit" and is_linux:
        pytest.skip("fixme: See https://bugs.webkit.org/show_bug.cgi?id=293148")
    context = await browser.new_context(ignore_https_errors=True)
    page = await context.new_page()
    response = await page.goto(https_server.EMPTY_PAGE)
    assert response
    assert response.ok is True
    # Closing the context will remove WebsiteDataStore and stop the network process
    # which will make the test pass.
    # await context.close()

    context2 = await browser.new_context()
    page2 = await context2.new_page()
    error: Optional[Error] = None
    try:
        await page2.goto(https_server.EMPTY_PAGE)
    except Error as e:
        error = e
    assert error is not None, "A TLS error expected, but the request succeeded."
    await context2.close()
    await context.close()


async def test_NE_139_should_work_with_mixed_content(
    browser: Browser, server: Server, https_server: Server
) -> None:
    def handle(request: TestServerRequest) -> None:
        request.write(f"<iframe src={server.EMPTY_PAGE}></iframe>".encode())
        request.finish()

    https_server.set_route("/mixedcontent.html", handle)
    context = await browser.new_context(ignore_https_errors=True)
    page = await context.new_page()
    await page.goto(https_server.PREFIX + "/mixedcontent.html", wait_until="load")
    assert len(page.frames) == 2
    # Make sure blocked iframe has functional execution context
    # @see https://github.com/GoogleChrome/puppeteer/issues/2709
    assert await page.frames[0].evaluate("1 + 2") == 3
    assert await page.frames[1].evaluate("2 + 3") == 5
    await context.close()


async def test_NE_140_should_work_with_web_socket(
    browser: Browser, https_server: Server
) -> None:
    https_server.send_on_web_socket_connection(b"incoming")
    context = await browser.new_context(ignore_https_errors=True)
    page = await context.new_page()
    value = await page.evaluate(
        WEBSOCKET_VALUE, re.sub(r"https", "wss", https_server.PREFIX, 1) + "/ws"
    )
    assert value == "incoming"
    await context.close()


async def test_NE_141_should_fail_with_web_socket_if_not_ignored(
    browser: Browser, https_server: Server
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    value = await page.evaluate(
        WEBSOCKET_VALUE, re.sub(r"https", "wss", https_server.PREFIX, 1) + "/ws"
    )
    assert value == "Error"
    await context.close()


async def test_NE_142_service_worker_should_intercept_document_request(
    browser: Browser, https_server: Server, browser_name: str
) -> None:
    if browser_name == "chromium":
        pytest.skip(
            "fixme: Failed to register a ServiceWorker: An SSL certificate error occurred when fetching the script."
        )
    context = await browser.new_context(ignore_https_errors=True)
    page = await context.new_page()

    async def handle_route(route: Route) -> None:
        await route.continue_()

    await context.route("**/*", handle_route)

    def handle_sw(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "application/javascript")
        request.write(
            b"""
      self.addEventListener('fetch', event => {
        event.respondWith(new Response('intercepted'));
      });
      self.addEventListener('activate', event => {
        event.waitUntil(clients.claim());
      });
    """
        )
        request.finish()

    https_server.set_route("/sw.js", handle_sw)
    await page.goto(https_server.EMPTY_PAGE)
    await page.evaluate(
        """async () => {
    const waitForControllerChange = new Promise(resolve => navigator.serviceWorker.oncontrollerchange = resolve);
    await navigator.serviceWorker.register('/sw.js');
    await waitForControllerChange;
  }"""
    )
    await page.reload()
    assert await page.text_content("body") == "intercepted"
    await context.close()
