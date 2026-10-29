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

"""Port of tests/library/chromium/connect-over-cdp.spec.ts."""

import asyncio
import json
import os
import signal
import urllib.request
from contextlib import suppress
from pathlib import Path
from typing import Any, Dict, Generator, List

import pytest

from playwright.async_api import (
    Browser,
    BrowserType,
    Error,
    Page,
    Playwright,
    async_playwright,
    expect,
)
from tests.helpers.proxy_server import ProxyServer
from tests.helpers.remote_server import RemoteServer
from tests.server import Server, TestServerRequest, WebSocketProtocol, find_free_port

pytestmark = pytest.mark.only_browser("chromium")


@pytest.fixture
def port() -> int:
    """Port of `9339 + testInfo.workerIndex`: a free port for --remote-debugging-port."""
    return find_free_port()


@pytest.fixture
def proxy_server() -> Generator[ProxyServer, None, None]:
    proxy = ProxyServer()
    yield proxy
    proxy.stop()


async def launch(
    browser_type: BrowserType, launch_arguments: Dict, port: int, *args: str
) -> Browser:
    return await browser_type.launch(
        **launch_arguments, args=[f"--remote-debugging-port={port}", *args]
    )


def http_get(url: str) -> str:
    """Port of the http.get() calls: the body of a GET request."""
    with urllib.request.urlopen(url) as response:
        return response.read().decode()


async def start_playwright_with_env(
    monkeypatch: pytest.MonkeyPatch, env: Dict[str, str]
) -> Playwright:
    """Starts a new Playwright whose driver has env in its environment.

    Upstream sets process.env in the test process, which runs the Playwright server.
    The Python driver is another process, and it reads its environment when it starts.
    """
    with monkeypatch.context() as patch:
        for name, value in env.items():
            patch.setenv(name, value)
        return await async_playwright().start()


async def test_CD_001_should_connect_to_an_existing_cdp_session(
    browser_type: BrowserType, launch_arguments: Dict, port: int
) -> None:
    browser_server = await launch(browser_type, launch_arguments, port)
    try:
        cdp_browser = await browser_type.connect_over_cdp(
            endpoint_url=f"http://127.0.0.1:{port}/",
        )
        contexts = cdp_browser.contexts
        assert len(contexts) == 1
        await cdp_browser.close()
    finally:
        await browser_server.close()


async def test_CD_002_should_connect_when_an_existing_page_has_no_renderer(
    browser_type: BrowserType, launch_arguments: Dict, port: int, server: Server
) -> None:
    browser_server = await launch(browser_type, launch_arguments, port)
    try:
        # Prepare a page without a renderer, e.g. one discarded by the Memory Saver.
        cdp_browser1 = await browser_type.connect_over_cdp(
            endpoint_url=f"http://127.0.0.1:{port}/",
        )
        context1 = cdp_browser1.contexts[0]
        healthy_page1 = await context1.new_page()
        await healthy_page1.goto(server.PREFIX + "/title.html")
        crashed_page1 = await context1.new_page()
        await crashed_page1.goto(server.EMPTY_PAGE)
        async with crashed_page1.expect_event("crash"):
            crash_task = asyncio.create_task(crashed_page1.goto("chrome://crash"))
        with suppress(Error):
            await crash_task
        await cdp_browser1.close()

        # Connecting again should not hang on the page without a renderer,
        # and should not report it at all.
        cdp_browser2 = await browser_type.connect_over_cdp(
            endpoint_url=f"http://127.0.0.1:{port}/",
        )
        pages = cdp_browser2.contexts[0].pages
        assert [page.url for page in pages] == [server.PREFIX + "/title.html"]
        assert await pages[0].title() == "Woof-Woof"
        await cdp_browser2.close()
    finally:
        await browser_server.close()


async def test_CD_003_should_connect_when_the_opener_of_an_existing_page_has_no_renderer(
    browser_type: BrowserType, launch_arguments: Dict, port: int, server: Server
) -> None:
    # The popup should be in a different process to survive the crash of the opener.
    browser_server = await launch(
        browser_type, launch_arguments, port, "--site-per-process"
    )
    try:
        cdp_browser1 = await browser_type.connect_over_cdp(
            endpoint_url=f"http://127.0.0.1:{port}/",
        )
        crashed_page1 = await cdp_browser1.contexts[0].new_page()
        await crashed_page1.goto(server.EMPTY_PAGE)
        async with crashed_page1.expect_popup() as popup_info:
            await crashed_page1.evaluate(
                "url => { window.open(url); }",
                server.CROSS_PROCESS_PREFIX + "/title.html",
            )
        popup1 = await popup_info.value
        await popup1.wait_for_load_state()
        async with crashed_page1.expect_event("crash"):
            crash_task = asyncio.create_task(crashed_page1.goto("chrome://crash"))
        with suppress(Error):
            await crash_task
        await cdp_browser1.close()

        # Connecting again should not report the opener, and should not wait for it.
        cdp_browser2 = await browser_type.connect_over_cdp(
            endpoint_url=f"http://127.0.0.1:{port}/",
        )
        pages = cdp_browser2.contexts[0].pages
        assert [page.url for page in pages] == [
            server.CROSS_PROCESS_PREFIX + "/title.html"
        ]
        assert await pages[0].title() == "Woof-Woof"
        assert await pages[0].opener() is None
        await cdp_browser2.close()
    finally:
        await browser_server.close()


async def test_CD_004_should_connect_when_an_existing_page_has_been_discarded(
    browser_type: BrowserType,
    launch_arguments: Dict,
    port: int,
    create_user_data_dir: Any,
    server: Server,
) -> None:
    user_data_dir: Path = create_user_data_dir()
    # chrome://discards is an internal debug page that is only available with this pref.
    (user_data_dir / "Local State").write_text(
        json.dumps({"internal_only_uis_enabled": True})
    )
    context = await browser_type.launch_persistent_context(
        user_data_dir,
        **{
            **launch_arguments,
            "headless": False,
            # Emulating the viewport of a discarded tab crashes the browser in
            # WebContentsImpl::SetDeviceEmulationSize, because it has no view.
            "no_viewport": True,
            "args": [
                f"--remote-debugging-port={port}",
                # Chrome refuses to discard tabs with DevTools attached, and we attach to all of them.
                "--enable-features=AllowDevtoolsConnectedDiscard",
            ],
        },
    )
    try:
        victim_url = server.PREFIX + "/title.html"
        victim = await context.new_page()
        await victim.goto(victim_url)
        discards = await context.new_page()
        await discards.goto("chrome://discards/")
        # Discarding replaces the tab's WebContents, but the url in the table survives.
        row = discards.get_by_role("row", name=victim_url)
        await row.get_by_text("Urgent Discard").click()
        await expect(row).to_contain_text("discarded")
        # The renderer process is shut down asynchronously after the discard.
        await discards.wait_for_timeout(3000)
        # Upstream attaches the discards rows and /json/list to the report here.

        # Connecting should not hang on the discarded page, and the page should not be reported.
        cdp_browser = await browser_type.connect_over_cdp(
            endpoint_url=f"http://127.0.0.1:{port}/",
        )
        pages = cdp_browser.contexts[0].pages
        assert sorted(page.url for page in pages) == sorted(
            ["about:blank", discards.url]
        )
        await cdp_browser.close()
    finally:
        await context.close()


async def test_CD_006_should_reject_pending_cdp_session_calls_when_the_browser_is_killed(
    browser_type: BrowserType, browser_name: str, launch_arguments: Dict, port: int
) -> None:
    # browserType.launchServer() is not in the Python API: RemoteServer runs it in
    # the driver's Node.js.
    browser_server = RemoteServer(
        browser_name,
        {**launch_arguments, "args": [f"--remote-debugging-port={port}"]},
    )
    try:
        cdp_browser = await browser_type.connect_over_cdp(
            endpoint_url=f"http://127.0.0.1:{port}/",
        )
        context = cdp_browser.contexts[0]
        page = await context.new_page()
        session = await context.new_cdp_session(page)
        send_task = asyncio.create_task(
            session.send(
                "Runtime.evaluate",
                {"expression": "new Promise(() => {})", "awaitPromise": True},
            )
        )
        await asyncio.sleep(0)
        # Port of browserServer.kill(): kills the browser process.
        os.kill(
            int(browser_server.out("pid")),
            getattr(signal, "SIGKILL", signal.SIGTERM),
        )
        with pytest.raises(Error) as exc_info:
            await send_task
        assert "Target page, context or browser has been closed" in (
            exc_info.value.message
        )
    finally:
        browser_server.close()


async def test_CD_007_should_write_traces_to_provided_artifacts_dir_on_connect_over_cdp(
    browser_type: BrowserType, launch_arguments: Dict, port: int, tmp_path: Path
) -> None:
    browser_server = await launch(browser_type, launch_arguments, port)
    artifacts_dir = tmp_path / "custom-artifacts"
    try:
        cdp_browser = await browser_type.connect_over_cdp(
            endpoint_url=f"http://127.0.0.1:{port}/",
            artifacts_dir=artifacts_dir,
        )
        # Upstream also checks toImpl(cdpBrowser).options.artifactsDir and tracesDir,
        # which are server internals. The files below show the same.

        context = cdp_browser.contexts[0]
        await context.tracing.start(name="cdp-trace", snapshots=True, screenshots=True)
        page = await context.new_page()
        await page.set_content("<button>Hello</button>")
        await context.tracing.stop_chunk()

        assert (artifacts_dir / "cdp-trace.trace").exists()
        assert (artifacts_dir / "cdp-trace.network").exists()
        assert (artifacts_dir / "resources").exists()

        disconnected: "asyncio.Future[Browser]" = (
            asyncio.get_running_loop().create_future()
        )
        cdp_browser.once(
            "disconnected", lambda browser: disconnected.set_result(browser)
        )
        await asyncio.gather(disconnected, browser_server.close())

        assert artifacts_dir.exists()
    finally:
        with suppress(Error):
            await browser_server.close()


async def test_CD_008_should_connect_over_cdp_and_manage_downloads_in_default_context(
    browser_type: BrowserType,
    launch_arguments: Dict,
    port: int,
    server: Server,
    tmp_path: Path,
) -> None:
    def handle(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "application/octet-stream")
        request.setHeader("Content-Disposition", "attachment; filename=file.txt")
        request.write(b"Hello world")
        request.finish()

    server.set_route("/downloadWithFilename", handle)

    browser_server = await launch(browser_type, launch_arguments, port)

    try:
        browser = await browser_type.connect_over_cdp(
            endpoint_url=f"http://127.0.0.1:{port}/",
        )
        page = await browser.contexts[0].new_page()
        await page.set_content(
            f'<a href="{server.PREFIX}/downloadWithFilename">download</a>'
        )

        async with page.expect_download() as download_info:
            await page.click("a")
        download = await download_info.value
        assert download.page is page
        assert download.url == f"{server.PREFIX}/downloadWithFilename"
        assert download.suggested_filename == "file.txt"

        user_path = tmp_path / "download.txt"
        await download.save_as(user_path)
        assert user_path.exists()
        assert user_path.read_text() == "Hello world"
    finally:
        await browser_server.close()


async def test_CD_009_should_connect_to_an_existing_cdp_session_twice(
    browser_type: BrowserType, launch_arguments: Dict, port: int, server: Server
) -> None:
    browser_server = await launch(browser_type, launch_arguments, port)
    try:
        cdp_browser1 = await browser_type.connect_over_cdp(
            endpoint_url=f"http://127.0.0.1:{port}/",
        )
        cdp_browser2 = await browser_type.connect_over_cdp(
            endpoint_url=f"http://127.0.0.1:{port}/",
        )
        contexts1 = cdp_browser1.contexts
        assert len(contexts1) == 1
        [context1] = contexts1
        page1 = await context1.new_page()
        await page1.goto(server.EMPTY_PAGE)

        contexts2 = cdp_browser2.contexts
        assert len(contexts2) == 1
        [context2] = contexts2
        page2 = await context2.new_page()
        await page2.goto(server.EMPTY_PAGE)

        assert len(context1.pages) == 2
        assert len(context2.pages) == 2

        await page1.evaluate("() => alert('dialog race')")
        assert await context2.pages[0].title() == ""

        await cdp_browser1.close()
        await cdp_browser2.close()
    finally:
        await browser_server.close()


async def test_CD_010_should_connect_to_existing_page_with_iframe_and_navigate(
    browser_type: BrowserType, launch_arguments: Dict, port: int, server: Server
) -> None:
    browser_server = await launch(browser_type, launch_arguments, port)
    try:
        context1 = await browser_server.new_context()
        page = await context1.new_page()
        await page.goto(server.PREFIX + "/frames/one-frame.html")
        cdp_browser = await browser_type.connect_over_cdp(f"http://127.0.0.1:{port}/")
        contexts = cdp_browser.contexts
        assert len(contexts) == 1
        await contexts[0].pages[0].goto(server.EMPTY_PAGE)
        await cdp_browser.close()
    finally:
        await browser_server.close()


async def test_CD_011_should_connect_to_existing_service_workers(
    browser_type: BrowserType, launch_arguments: Dict, port: int, server: Server
) -> None:
    browser_server = await launch(browser_type, launch_arguments, port)
    try:
        cdp_browser1 = await browser_type.connect_over_cdp(
            endpoint_url=f"http://127.0.0.1:{port}",
        )
        context = cdp_browser1.contexts[0]
        page = await cdp_browser1.contexts[0].new_page()
        async with context.expect_event("serviceworker") as worker_info:
            await page.goto(server.PREFIX + "/serviceworkers/empty/sw.html")
        worker = await worker_info.value
        assert (
            await worker.evaluate("() => self.toString()")
            == "[object ServiceWorkerGlobalScope]"
        )
        await cdp_browser1.close()

        cdp_browser2 = await browser_type.connect_over_cdp(
            endpoint_url=f"http://127.0.0.1:{port}",
        )
        context2 = cdp_browser2.contexts[0]
        assert len(context2.service_workers) == 1
        await cdp_browser2.close()
    finally:
        await browser_server.close()


async def test_CD_012_should_connect_over_a_ws_endpoint(
    browser_type: BrowserType, launch_arguments: Dict, port: int, server: Server
) -> None:
    browser_server = await launch(browser_type, launch_arguments, port)
    try:
        json_text = http_get(f"http://127.0.0.1:{port}/json/version/")
        cdp_browser = await browser_type.connect_over_cdp(
            endpoint_url=json.loads(json_text)["webSocketDebuggerUrl"],
        )
        contexts = cdp_browser.contexts
        assert len(contexts) == 1
        await cdp_browser.close()

        # Upstream also connects with the deprecated wsEndpoint option, which is
        # JavaScript-only: Python passes the same URL as the endpoint URL.
        cdp_browser2 = await browser_type.connect_over_cdp(
            json.loads(json_text)["webSocketDebuggerUrl"],
        )
        contexts2 = cdp_browser2.contexts
        assert len(contexts2) == 1
        await cdp_browser2.close()
    finally:
        await browser_server.close()


async def test_CD_013_should_send_extra_headers_with_connect_request(
    browser_type: BrowserType, server: Server
) -> None:
    with server.expect_request("/ws") as request_info:
        with suppress(Error):
            await browser_type.connect_over_cdp(
                endpoint_url=f"ws://localhost:{server.PORT}/ws",
                headers={
                    "User-Agent": "Playwright",
                    "foo": "bar",
                },
                timeout=100,
            )
    request = request_info.value
    assert request.getHeader("user-agent") == "Playwright"
    assert request.getHeader("foo") == "bar"

    with server.expect_request("/json/version/") as request_info:
        with suppress(Error):
            await browser_type.connect_over_cdp(
                endpoint_url=f"http://localhost:{server.PORT}",
                headers={
                    "User-Agent": "Playwright",
                    "foo": "bar",
                },
                timeout=100,
            )
    request = request_info.value
    assert request.getHeader("user-agent") == "Playwright"
    assert request.getHeader("foo") == "bar"


async def test_CD_014_should_keep_url_parameters_when_adding_json_version(
    browser_type: BrowserType, server: Server
) -> None:
    with server.expect_request("/browser/json/version/?foo=bar") as request_info:
        with suppress(Error):
            await browser_type.connect_over_cdp(
                f"http://localhost:{server.PORT}/browser/?foo=bar"
            )
    assert request_info.value


async def test_CD_015_should_append_json_version_with_a_slash_if_there_isnt_one(
    browser_type: BrowserType, server: Server
) -> None:
    with server.expect_request("/browser/json/version/?foo=bar") as request_info:
        with suppress(Error):
            await browser_type.connect_over_cdp(
                f"http://localhost:{server.PORT}/browser?foo=bar"
            )
    assert request_info.value


async def test_CD_016_should_send_default_user_agent_header_with_connect_request(
    browser_type: BrowserType, playwright: Playwright, server: Server
) -> None:
    # Port of getUserAgent(): the driver sends the same User-Agent with global fetch.
    request_context = await playwright.request.new_context()
    with server.expect_request("/empty.html") as user_agent_request:
        await request_context.get(server.EMPTY_PAGE)
    await request_context.dispose()
    user_agent = user_agent_request.value.getHeader("user-agent")
    assert user_agent

    with server.expect_request("/ws") as request_info:
        with suppress(Error):
            await browser_type.connect_over_cdp(
                endpoint_url=f"ws://localhost:{server.PORT}/ws",
                headers={
                    "foo": "bar",
                },
                timeout=100,
            )
    request = request_info.value
    assert request.getHeader("user-agent") == user_agent
    assert request.getHeader("foo") == "bar"


async def test_CD_017_should_report_all_pages_in_an_existing_browser(
    browser_type: BrowserType, launch_arguments: Dict, port: int
) -> None:
    browser_server = await launch(browser_type, launch_arguments, port)
    try:
        cdp_browser = await browser_type.connect_over_cdp(
            endpoint_url=f"http://127.0.0.1:{port}/",
        )
        contexts = cdp_browser.contexts
        assert len(contexts) == 1
        for _ in range(3):
            await contexts[0].new_page()
        await cdp_browser.close()

        cdp_browser2 = await browser_type.connect_over_cdp(
            endpoint_url=f"http://127.0.0.1:{port}/",
        )
        assert len(cdp_browser2.contexts[0].pages) == 3

        await cdp_browser2.close()
    finally:
        await browser_server.close()


async def test_CD_018_should_connect_via_https(
    browser_type: BrowserType,
    launch_arguments: Dict,
    port: int,
    https_server: Server,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    browser_server = await launch(browser_type, launch_arguments, port)
    json_text = http_get(f"http://127.0.0.1:{port}/json/version/")

    def handle(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.write(json_text.encode())
        request.finish()

    https_server.set_route("/json/version/", handle)
    # https://stackoverflow.com/a/21961005/552185
    # NODE_NO_WARNINGS is suppressCertificateWarning().
    playwright = await start_playwright_with_env(
        monkeypatch, {"NODE_TLS_REJECT_UNAUTHORIZED": "0", "NODE_NO_WARNINGS": "1"}
    )
    try:
        cdp_browser = await playwright.chromium.connect_over_cdp(
            f"https://localhost:{https_server.PORT}/"
        )
        contexts = cdp_browser.contexts
        assert len(contexts) == 1
        for _ in range(3):
            await contexts[0].new_page()
        await cdp_browser.close()
    finally:
        await playwright.stop()
        await browser_server.close()


async def test_CD_019_should_return_valid_browser_from_context_browser(
    browser_type: BrowserType, launch_arguments: Dict, port: int
) -> None:
    browser_server = await launch(browser_type, launch_arguments, port)
    try:
        cdp_browser = await browser_type.connect_over_cdp(
            endpoint_url=f"http://127.0.0.1:{port}/",
        )
        contexts = cdp_browser.contexts
        assert len(contexts) == 1
        assert contexts[0].browser is cdp_browser

        context2 = await cdp_browser.new_context()
        assert context2.browser is cdp_browser

        await cdp_browser.close()
    finally:
        await browser_server.close()


async def test_CD_020_should_report_an_expected_error_when_the_endpoint_url_returns_a_non_expected_status_code(
    browser_type: BrowserType, server: Server
) -> None:
    def handle(request: TestServerRequest) -> None:
        request.setResponseCode(404)
        request.write(json.dumps({"webSocketDebuggerUrl": "dont-use-me"}).encode())
        request.finish()

    server.set_route("/json/version/", handle)
    with pytest.raises(Error) as exc_info:
        await browser_type.connect_over_cdp(
            endpoint_url=server.PREFIX,
        )
    assert (
        f"BrowserType.connect_over_cdp: Unexpected status 404 when connecting to {server.PREFIX}/json/version/"
        in exc_info.value.message
    )


async def test_CD_021_should_report_an_expected_error_when_the_endpoint_url_json_web_socket_debugger_url_is_undefined(
    browser_type: BrowserType, server: Server
) -> None:
    def handle(request: TestServerRequest) -> None:
        # JSON.stringify() leaves out an undefined property.
        request.write(json.dumps({}).encode())
        request.finish()

    server.set_route("/json/version/", handle)
    with pytest.raises(Error) as exc_info:
        await browser_type.connect_over_cdp(
            endpoint_url=server.PREFIX,
        )
    assert "BrowserType.connect_over_cdp: Invalid URL" in exc_info.value.message


async def test_CD_022_should_connect_to_an_existing_cdp_session_when_passed_as_a_first_argument(
    browser_type: BrowserType, launch_arguments: Dict, port: int
) -> None:
    browser_server = await launch(browser_type, launch_arguments, port)
    try:
        cdp_browser = await browser_type.connect_over_cdp(f"http://127.0.0.1:{port}/")
        contexts = cdp_browser.contexts
        assert len(contexts) == 1
        await cdp_browser.close()
    finally:
        await browser_server.close()


async def test_CD_023_should_use_proxy_with_connect_over_cdp(
    browser_type: BrowserType, launch_arguments: Dict, port: int, server: Server
) -> None:
    def handle(request: TestServerRequest) -> None:
        request.write(b"<html><title>Served by the proxy</title></html>")
        request.finish()

    server.set_route("/target.html", handle)
    browser_server = await launch(browser_type, launch_arguments, port)
    try:
        cdp_browser = await browser_type.connect_over_cdp(f"http://127.0.0.1:{port}/")
        context = await cdp_browser.new_context(
            proxy={"server": f"localhost:{server.PORT}"}
        )
        page = await context.new_page()
        await page.goto("http://non-existent.test/target.html")
        assert await page.title() == "Served by the proxy"
        await cdp_browser.close()
    finally:
        await browser_server.close()


async def test_CD_024_should_use_env_proxy_with_connect_over_cdp_discovery_request(
    server: Server, proxy_server: ProxyServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    proxy_server.forward_to(server.PORT)

    playwright = await start_playwright_with_env(
        monkeypatch, {"HTTP_PROXY": proxy_server.URL}
    )
    try:
        with pytest.raises(Error) as exc_info:
            await playwright.chromium.connect_over_cdp(server.PREFIX)
        assert (
            f"Unexpected status 404 when connecting to {server.PREFIX}/json/version/"
            in exc_info.value.message
        )
        assert proxy_server.request_urls == [f"{server.PREFIX}/json/version/"]
    finally:
        await playwright.stop()


async def test_CD_025_should_send_target_host_header_when_using_env_http_proxy_with_connect_over_cdp(
    server: Server, proxy_server: ProxyServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    proxy_server.forward_to(server.PORT)

    playwright = await start_playwright_with_env(
        monkeypatch, {"HTTP_PROXY": proxy_server.URL}
    )
    try:
        with pytest.raises(Error) as exc_info:
            await playwright.chromium.connect_over_cdp(server.PREFIX)
        assert (
            f"Unexpected status 404 when connecting to {server.PREFIX}/json/version/"
            in exc_info.value.message
        )
        assert proxy_server.request_hosts == [server.HOST]
    finally:
        await playwright.stop()


async def test_CD_026_should_be_able_to_connect_via_localhost(
    browser_type: BrowserType, launch_arguments: Dict, port: int
) -> None:
    browser_server = await launch(browser_type, launch_arguments, port)
    try:
        cdp_browser = await browser_type.connect_over_cdp(f"http://localhost:{port}")
        contexts = cdp_browser.contexts
        assert len(contexts) == 1
        await cdp_browser.close()
    finally:
        await browser_server.close()


async def test_CD_027_emulate_media_should_not_be_affected_by_second_connect_over_cdp_with_no_defaults(
    browser_type: BrowserType, launch_arguments: Dict, port: int
) -> None:
    browser_server = await launch(browser_type, launch_arguments, port)
    try:

        async def is_print(page: Page) -> bool:
            return await page.evaluate("() => matchMedia('print').matches")

        browser1 = await browser_type.connect_over_cdp(f"http://localhost:{port}")
        context1 = await browser1.new_context()
        page1 = await context1.new_page()
        await page1.emulate_media(media="print")
        assert await is_print(page1) is True
        browser2 = await browser_type.connect_over_cdp(
            f"http://localhost:{port}", no_defaults=True
        )
        assert await is_print(page1) is True
        await asyncio.gather(browser1.close(), browser2.close())
    finally:
        await browser_server.close()


async def test_CD_028_should_allow_tracing_over_cdp_session(
    browser_type: BrowserType, launch_arguments: Dict, port: int, tmp_path: Path
) -> None:
    browser_server = await launch(browser_type, launch_arguments, port)
    try:
        cdp_browser = await browser_type.connect_over_cdp(
            endpoint_url=f"http://127.0.0.1:{port}/",
        )
        [context] = cdp_browser.contexts
        await context.tracing.start(screenshots=True, snapshots=True)
        page = await context.new_page()
        await page.evaluate("() => 2 + 2")
        trace_zip = tmp_path / "trace.zip"
        await context.tracing.stop(path=trace_zip)
        await cdp_browser.close()
        assert trace_zip.exists()
    finally:
        await browser_server.close()


async def test_CD_029_set_input_files_should_preserve_last_modified_timestamp(
    browser_type: BrowserType, launch_arguments: Dict, port: int, assetdir: Path
) -> None:
    browser_server = await launch(browser_type, launch_arguments, port)
    try:
        cdp_browser = await browser_type.connect_over_cdp(
            endpoint_url=f"http://127.0.0.1:{port}/",
        )
        [context] = cdp_browser.contexts
        page = await context.new_page()
        await page.set_content("<input type=file multiple=true/>")
        input = page.locator("input")
        files = ["file-to-upload.txt", "file-to-upload-2.txt"]
        await input.set_input_files([assetdir / f for f in files])
        assert await input.evaluate("e => [...e.files].map(f => f.name)") == files
        timestamps: List[float] = await input.evaluate(
            "e => [...e.files].map(f => f.lastModified)"
        )
        expected_timestamps = [
            round(os.stat(assetdir / file).st_mtime_ns / 1_000_000) for file in files
        ]
        # On Linux browser sometimes reduces the timestamp by 1ms: 1696272058110.0715  -> 1696272058109 or even
        # rounds it to seconds in WebKit: 1696272058110 -> 1696272058000.
        for i in range(len(timestamps)):
            assert (
                abs(timestamps[i] - expected_timestamps[i]) <= 1000
            ), f"expected: {expected_timestamps}; actual: {timestamps}"
        await cdp_browser.close()
    finally:
        await browser_server.close()


async def test_CD_031_should_print_custom_ws_close_error(
    browser_type: BrowserType, server: Server
) -> None:
    def handle_ws(ws: WebSocketProtocol) -> None:
        ws.events.on(
            "message",
            lambda payload, is_binary: ws.sendClose(code=4123, reason="Oh my!"),
        )

    server.once_web_socket_connection(handle_ws)
    with pytest.raises(Error) as exc_info:
        await browser_type.connect_over_cdp(f"ws://localhost:{server.PORT}/ws")
    assert "Browser logs:\n\nOh my!\n" in exc_info.value.message


async def test_CD_033_should_get_title_and_url_of_existing_page(
    browser_type: BrowserType, launch_arguments: Dict, port: int, server: Server
) -> None:
    browser_server = await launch(browser_type, launch_arguments, port)
    browsers: List[Browser] = []
    try:
        cdp_browser = await browser_type.connect_over_cdp(
            endpoint_url=f"http://127.0.0.1:{port}/",
        )
        browsers.append(cdp_browser)
        [context] = cdp_browser.contexts
        page = await context.new_page()
        await page.goto(server.EMPTY_PAGE)
        await page.evaluate("() => document.title = 'my title'")

        cdp_browser = await browser_type.connect_over_cdp(
            endpoint_url=f"http://127.0.0.1:{port}/",
        )
        browsers.append(cdp_browser)

        [context] = cdp_browser.contexts
        [page] = context.pages
        assert page.url == server.EMPTY_PAGE
        assert await page.title() == "my title"
    finally:
        for browser in browsers:
            await browser.close()
        await browser_server.close()


async def test_CD_034_should_skip_default_overrides_with_no_defaults(
    browser_type: BrowserType, launch_arguments: Dict, port: int, server: Server
) -> None:
    browser_server = await launch(browser_type, launch_arguments, port)
    try:
        browser = await browser_type.connect_over_cdp(
            endpoint_url=f"http://127.0.0.1:{port}/",
            no_defaults=True,
        )
        default_context = browser.contexts[0]
        page = await default_context.new_page()

        # Browser.setDownloadBehavior was not sent, so no Playwright download event fires.
        def handle(request: TestServerRequest) -> None:
            request.setHeader("Content-Type", "application/octet-stream")
            request.setHeader("Content-Disposition", "attachment; filename=file.txt")
            request.write(b"Hello world")
            request.finish()

        server.set_route("/download", handle)
        await page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
        saw_download = False

        def on_download(download: Any) -> None:
            nonlocal saw_download
            saw_download = True

        page.on("download", on_download)
        await page.click("a")
        await page.wait_for_timeout(500)
        assert saw_download is False

        await browser.close()
    finally:
        await browser_server.close()


async def test_CD_035_no_defaults_should_not_affect_new_contexts(
    browser_type: BrowserType, launch_arguments: Dict, port: int
) -> None:
    browser_server = await launch(browser_type, launch_arguments, port)
    try:
        browser = await browser_type.connect_over_cdp(
            endpoint_url=f"http://127.0.0.1:{port}/",
            no_defaults=True,
        )

        # New contexts should still get normal Playwright defaults.
        new_context = await browser.new_context()
        page = await new_context.new_page()
        has_focus = await page.evaluate("() => document.hasFocus()")
        assert has_focus is True

        await new_context.close()
        await browser.close()
    finally:
        await browser_server.close()


async def test_CD_053_should_connect_when_another_client_inspects_a_terminated_shared_worker(
    browser_type: BrowserType, server: Server, launch_arguments: Dict, port: int
) -> None:
    pytest.skip("fixme")
    browser = await launch(browser_type, launch_arguments, port)
    try:
        # Another client inspects the shared worker.
        page = await browser.new_page()
        inspector = await browser.new_browser_cdp_session()
        worker_created: asyncio.Future[str] = asyncio.get_running_loop().create_future()

        def on_target_created(event: Dict[str, Any]) -> None:
            if event["targetInfo"]["type"] == "shared_worker":
                worker_created.set_result(event["targetInfo"]["targetId"])

        inspector.on("Target.targetCreated", on_target_created)
        await inspector.send("Target.setDiscoverTargets", {"discover": True})
        await page.goto(server.PREFIX + "/shared-worker/shared-worker.html")
        assert await page.evaluate("window.sharedWorkerResponsePromise") == "echo:hello"
        worker_target_id = await worker_created
        await inspector.send(
            "Target.attachToTarget", {"targetId": worker_target_id, "flatten": True}
        )

        # The last client of the shared worker goes away, so the worker is terminated.
        # The inspector stays attached, so the worker target lingers without a browser context.
        await page.close()
        # Python: poll the CDP target list instead of expect.poll.
        deadline = asyncio.get_running_loop().time() + 5
        while True:
            targets = await inspector.send("Target.getTargets")
            if not any(
                info["targetId"] == worker_target_id for info in targets["targetInfos"]
            ):
                break
            assert asyncio.get_running_loop().time() < deadline
            await asyncio.sleep(0.1)

        # A new client auto-attaches to the lingering worker target.
        cdp_browser = await browser_type.connect_over_cdp(f"http://127.0.0.1:{port}/")
        page2 = await cdp_browser.contexts[0].new_page()
        assert await page2.evaluate("1 + 1") == 2
        await cdp_browser.close()
    finally:
        await browser.close()
