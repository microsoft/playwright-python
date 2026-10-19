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

"""Port of tests/library/chromium/extensions.spec.ts."""

import asyncio
import re
import time
from pathlib import Path
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, List, Optional

import pytest

from playwright.async_api import BrowserContext, BrowserType, CDPSession, Page, Worker
from tests.server import Server, TestServerRequest

pytestmark = pytest.mark.only_browser("chromium")

LaunchPersistentContext = Callable[..., Awaitable[BrowserContext]]


@pytest.fixture(autouse=True)
def skip_unsupported(
    browser_name: str, is_headless_shell: bool, browser_channel: Optional[str]
) -> None:
    if browser_name != "chromium":
        return
    if is_headless_shell:
        pytest.skip("Headless Shell has no support for extensions")
    # describe('MV3')
    if browser_channel and browser_channel.startswith("chrome"):
        pytest.skip(
            "--load-extension is not supported in Chrome anymore. https://groups.google.com/a/chromium.org/g/chromium-extensions/c/1-g8EFx2BBY/m/S0ET5wPjCAAJ"
        )


@pytest.fixture
async def launch_persistent_context(
    browser_type: BrowserType, launch_arguments: Dict
) -> AsyncGenerator[LaunchPersistentContext, None]:
    contexts: List[BrowserContext] = []

    async def launch(extension_path: Path, **options: Any) -> BrowserContext:
        context = await browser_type.launch_persistent_context(
            "",
            **{
                **launch_arguments,
                **options,
                "args": [
                    f"--disable-extensions-except={extension_path}",
                    f"--load-extension={extension_path}",
                ],
            },
        )
        contexts.append(context)
        return context

    yield launch
    for context in contexts:
        await context.close()


async def poll(
    actual: Callable[[], Awaitable[Any]], expected: Any, timeout: float = 10000
) -> None:
    """Port of `await expect.poll(actual).toBe(expected)`."""
    deadline = time.monotonic() + timeout / 1000
    value = await actual()
    while value != expected and time.monotonic() < deadline:
        await asyncio.sleep(0.1)
        value = await actual()
    assert value == expected


async def get_service_worker(context: BrowserContext) -> Worker:
    service_workers = context.service_workers
    if service_workers:
        return service_workers[0]
    return await context.wait_for_event("serviceworker")


class CdpEventWaiter:
    """Port of waitForCdpEvent(): the first non-None predicate result of the event."""

    def __init__(
        self, cdp: CDPSession, event: str, predicate: Callable[[Dict], Any]
    ) -> None:
        self._cdp = cdp
        self._event = event
        self._predicate = predicate
        self._result: Any = None
        cdp.on(event, self._handler)

    def _handler(self, params: Dict) -> None:
        result = self._predicate(params)
        if result is not None and self._result is None:
            self._cdp.remove_listener(self._event, self._handler)
            self._result = result

    async def wait(self, page: Page) -> Any:
        # The events come while the page waits.
        while self._result is None:
            await page.wait_for_timeout(50)
        return self._result


def first_version(params: Dict) -> Any:
    versions = params["versions"]
    return versions[0] if versions else None


async def test_CR_036_mv3_should_support_service_worker_stop_and_restart_lifecycle(
    launch_persistent_context: LaunchPersistentContext, assetdir: Path
) -> None:
    extension_path = assetdir / "extension-mv3-sw-lifecycle"
    context = await launch_persistent_context(extension_path)

    sw1 = await get_service_worker(context)
    start_time1 = await sw1.evaluate("() => globalThis.startTime")

    # stopWorker keeps the same CDP target alive, matching Chrome's natural idle suspension behavior.
    page = await context.new_page()
    cdp = await context.new_cdp_session(page)

    version_waiter = CdpEventWaiter(
        cdp,
        "ServiceWorker.workerVersionUpdated",
        lambda params: (first_version(params) or {}).get("versionId"),
    )
    scope_waiter = CdpEventWaiter(
        cdp,
        "ServiceWorker.workerRegistrationUpdated",
        lambda params: (
            params["registrations"][0].get("scopeURL")
            if params["registrations"]
            else None
        ),
    )
    await cdp.send("ServiceWorker.enable")
    version_id = await version_waiter.wait(page)
    scope_url = await scope_waiter.wait(page)

    stopped_waiter = CdpEventWaiter(
        cdp,
        "ServiceWorker.workerVersionUpdated",
        lambda params: (
            True
            if (first_version(params) or {}).get("runningStatus") == "stopped"
            else None
        ),
    )
    await cdp.send("ServiceWorker.stopWorker", {"versionId": version_id})
    await stopped_waiter.wait(page)

    running_waiter = CdpEventWaiter(
        cdp,
        "ServiceWorker.workerVersionUpdated",
        lambda params: (
            True
            if (first_version(params) or {}).get("runningStatus") == "running"
            else None
        ),
    )
    await cdp.send("ServiceWorker.startWorker", {"scopeURL": scope_url})
    await running_waiter.wait(page)

    start_time2 = await sw1.evaluate("() => globalThis.startTime")
    assert start_time2 > start_time1
    # same object, no new event
    assert context.service_workers == [sw1]
    assert context.service_workers[0] is sw1

    await context.close()


async def test_CR_037_mv3_should_give_access_to_the_service_worker(
    launch_persistent_context: LaunchPersistentContext, assetdir: Path
) -> None:
    extension_path = assetdir / "extension-mv3-simple"
    context = await launch_persistent_context(extension_path)
    service_worker = await get_service_worker(context)
    assert service_worker
    assert service_worker in context.service_workers
    await poll(lambda: service_worker.evaluate("() => globalThis.MAGIC"), 42)
    await context.close()
    assert len(context.background_pages) == 0


async def test_CR_038_mv3_should_give_access_to_the_service_worker_when_recording_video(
    launch_persistent_context: LaunchPersistentContext,
    assetdir: Path,
    tmp_path: Path,
) -> None:
    extension_path = assetdir / "extension-mv3-simple"
    context = await launch_persistent_context(extension_path, record_video_dir=tmp_path)
    service_worker = await get_service_worker(context)
    assert service_worker
    assert service_worker in context.service_workers
    await poll(lambda: service_worker.evaluate("() => globalThis.MAGIC"), 42)
    await context.close()


async def test_CR_039_mv3_should_support_request_response_events_in_the_service_worker(
    launch_persistent_context: LaunchPersistentContext,
    assetdir: Path,
    server: Server,
    browser_major_version: int,
) -> None:
    if browser_major_version < 143:
        pytest.skip("needs workerScriptLoaded event")

    def handle(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("Content-Type", "text/html")
        request.setHeader("x-response-foobar", "BarFoo")
        request.write(b"<span>hello world!</span>")
        request.finish()

    server.set_route("/empty.html", handle)
    extension_path = assetdir / "extension-mv3-simple"
    context = await launch_persistent_context(extension_path)
    service_worker = await get_service_worker(context)
    assert re.search(r"chrome-extension\:\/\/.*", service_worker.url)
    async with context.expect_event("request") as request_info:
        async with context.expect_event("response") as response_info:
            await service_worker.evaluate(
                """url => fetch(url, {
              method: 'POST',
              body: 'foobar',
              headers: { 'X-FOOBAR': 'KEKBAR' }
            })""",
                server.EMPTY_PAGE,
            )
    request = await request_info.value
    response = await response_info.value
    assert request.url == server.EMPTY_PAGE
    assert request.method == "POST"
    assert (await request.all_headers())["x-foobar"] == "KEKBAR"
    assert request.post_data == "foobar"

    assert response.status == 200
    assert response.url == server.EMPTY_PAGE
    assert response.request is request
    assert await response.text() == "<span>hello world!</span>"
    assert (await response.all_headers())["x-response-foobar"] == "BarFoo"

    await context.close()


async def test_CR_040_mv3_should_report_console_messages_from_content_script(
    launch_persistent_context: LaunchPersistentContext,
    assetdir: Path,
    server: Server,
) -> None:
    extension_path = assetdir / "extension-mv3-with-logging"
    context = await launch_persistent_context(extension_path)
    page = await context.new_page()
    async with page.expect_console_message(
        lambda e: "Test console log from a third-party execution context" in e.text
    ) as message_info:
        await page.goto(server.EMPTY_PAGE)
    message = await message_info.value
    assert "Test console log from a third-party execution context" in message.text
    await context.close()


async def test_CR_041_mv3_should_use_custom_user_agent_in_service_worker_fetch_requests(
    launch_persistent_context: LaunchPersistentContext,
    assetdir: Path,
    server: Server,
) -> None:
    def handle(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("Content-Type", "text/plain")
        request.write((request.getHeader("user-agent") or "").encode())
        request.finish()

    server.set_route("/ua-echo", handle)
    extension_path = assetdir / "extension-mv3-simple"
    context = await launch_persistent_context(
        extension_path, user_agent="MyTestAgent/1.0"
    )
    sw = await get_service_worker(context)
    user_agent = await sw.evaluate(
        """async url => {
          const response = await fetch(url);
          return response.text();
        }""",
        server.PREFIX + "/ua-echo",
    )
    assert user_agent == "MyTestAgent/1.0"
    await context.close()
