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

"""Port of tests/page/workers.spec.ts."""

import asyncio
import inspect
import json
import time
from pathlib import Path
from typing import Any, Callable, List, Optional

import pytest

from playwright.async_api import Error, Page, Worker
from tests.server import Server, TestServerRequest
from tests.utils import TARGET_CLOSED_ERROR_MESSAGE

from ..utils import Utils


async def expect_poll(
    page: Page, actual: Callable[[], Any], expected: Any, timeout: float = 5000
) -> None:
    """Port of `await expect.poll(actual).toEqual(expected)`."""
    deadline = time.monotonic() + timeout / 1000
    while True:
        value = actual()
        if inspect.isawaitable(value):
            value = await value
        if value == expected or time.monotonic() > deadline:
            break
        await page.wait_for_timeout(100)
    assert value == expected


async def test_WO_001_page_workers_smoke(
    page: Page, server: Server, browser_name: str, browser_major_version: int
) -> None:
    if browser_name == "chromium" and browser_major_version < 143:
        pytest.skip("needs workerScriptLoaded event")

    async with page.expect_worker():
        await page.goto(server.PREFIX + "/worker/worker.html")
    worker = page.workers[0]
    assert "worker.js" in worker.url

    assert (
        await worker.evaluate("() => self['workerFunction']()")
        == "worker function result"
    )

    await page.goto(server.EMPTY_PAGE)
    assert len(page.workers) == 0


async def test_WO_002_should_emit_created_and_destroyed_events(page: Page) -> None:
    async with page.expect_worker() as worker_info:
        worker_obj = await page.evaluate_handle(
            "() => new Worker(URL.createObjectURL(new Blob(['1'], { type: 'application/javascript' })))"
        )
    worker = await worker_info.value
    worker_this_obj = await worker.evaluate_handle("this")
    worker_destroyed: "asyncio.Future[Worker]" = asyncio.Future()
    worker.once("close", lambda w: worker_destroyed.set_result(w))
    await page.evaluate("workerObj => workerObj.terminate()", worker_obj)
    assert await worker_destroyed is worker
    with pytest.raises(Error) as exc_info:
        await worker_this_obj.get_property("self")
    assert "JSHandle.get_property" in exc_info.value.message
    assert TARGET_CLOSED_ERROR_MESSAGE in exc_info.value.message


async def test_WO_003_should_reject_in_flight_evaluate_and_emit_close_when_page_closes(
    page: Page, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/43204
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_worker() as worker_info:
        await page.evaluate(
            "() => new Worker(URL.createObjectURL(new Blob(['1'], { type: 'application/javascript' })))"
        )
    worker = await worker_info.value
    closed: "asyncio.Future[Worker]" = asyncio.Future()
    worker.once("close", lambda w: closed.set_result(w))
    eval_task = asyncio.create_task(worker.evaluate("() => new Promise(() => {})"))
    await page.close()
    with pytest.raises(Error) as exc_info:
        await eval_task
    assert "Worker.evaluate" in exc_info.value.message
    assert await closed is worker


async def test_WO_004_should_report_console_logs(page: Page) -> None:
    async with page.expect_console_message() as message_info:
        await page.evaluate(
            "() => new Worker(URL.createObjectURL(new Blob(['console.log(1)'], { type: 'application/javascript' })))"
        )
    message = await message_info.value
    assert message.text == "1"
    # Firefox's juggler had an issue that reported worker blob urls as frame urls.
    assert "blob" not in page.url


async def test_WO_005_should_have_timestamp_on_worker_console_messages(
    page: Page, browser_channel: Optional[str]
) -> None:
    if browser_channel == "webkit-wsl":
        pytest.skip("there is a time difference between WSL VM and host machine")

    # Account for the rounding of fractional timestamps.
    before = time.time() * 1000 - 1
    async with page.expect_console_message() as message_info:
        await page.evaluate(
            """() => new Worker(URL.createObjectURL(new Blob(['console.log("ts")'], { type: 'application/javascript' })))"""
        )
    message = await message_info.value
    # Account for the rounding of fractional timestamps.
    after = time.time() * 1000 + 1
    assert message.text == "ts"
    assert message.timestamp >= before
    assert message.timestamp <= after


async def test_WO_006_should_not_report_console_logs_from_workers_twice(
    page: Page,
) -> None:
    messages: List[str] = []
    page.on("console", lambda msg: messages.append(msg.text))
    async with page.expect_console_message(lambda msg: msg.text == "1"):
        async with page.expect_console_message(lambda msg: msg.text == "2"):
            await page.evaluate(
                "() => new Worker(URL.createObjectURL(new Blob(['console.log(1); console.log(2);'], { type: 'application/javascript' })))"
            )
    assert messages == ["1", "2"]
    # Firefox's juggler had an issue that reported worker blob urls as frame urls.
    assert "blob" not in page.url


async def test_WO_007_should_have_js_handles_for_console_logs(
    page: Page, browser_name: str
) -> None:
    async with page.expect_console_message() as log_info:
        await page.evaluate(
            "() => new Worker(URL.createObjectURL(new Blob(['console.log(1,2,3,this)'], { type: 'application/javascript' })))"
        )
    log = await log_info.value
    if browser_name != "firefox":
        assert log.text == "1 2 3 DedicatedWorkerGlobalScope"
    else:
        assert log.text == "1 2 3 JSHandle@object"
    assert len(log.args) == 4
    assert await (await log.args[3].get_property("origin")).json_value() == "null"


async def test_WO_008_should_evaluate(
    page: Page, browser_name: str, browser_major_version: int
) -> None:
    if browser_name == "chromium" and browser_major_version < 143:
        pytest.skip("needs workerScriptLoaded event")

    async with page.expect_worker() as worker_info:
        await page.evaluate(
            "() => new Worker(URL.createObjectURL(new Blob(['console.log(1)'], { type: 'application/javascript' })))"
        )
    worker = await worker_info.value
    assert await worker.evaluate("1+1") == 2


async def test_WO_009_should_report_console_event_on_the_worker(
    page: Page, browser_name: str, browser_major_version: int
) -> None:
    if browser_name == "chromium" and browser_major_version < 143:
        pytest.skip("needs workerScriptLoaded event")

    async with page.expect_worker() as worker_info:
        await page.evaluate(
            """() => {
                window.worker = new Worker(URL.createObjectURL(new Blob(['42'], { type: 'application/javascript' })));
            }"""
        )
    worker = await worker_info.value
    async with worker.expect_event("console") as message1_info:
        async with page.expect_console_message() as message2_info:
            async with page.context.expect_console_message() as message3_info:
                await worker.evaluate(
                    """() => {
                        console.log('hello from worker');
                    }"""
                )
    message1 = await message1_info.value
    message2 = await message2_info.value
    message3 = await message3_info.value
    assert message1.text == "hello from worker"
    assert message1 is message2
    assert message1 is message3


async def test_WO_010_should_report_console_event_on_the_worker_when_not_listening_on_page_or_context(
    page: Page, browser_name: str, browser_major_version: int
) -> None:
    if browser_name == "chromium" and browser_major_version < 143:
        pytest.skip("needs workerScriptLoaded event")

    async with page.expect_worker() as worker_info:
        await page.evaluate(
            """() => {
                window.worker = new Worker(URL.createObjectURL(new Blob(['42'], { type: 'application/javascript' })));
            }"""
        )
    worker = await worker_info.value
    async with worker.expect_event("console") as message_info:
        await worker.evaluate(
            """() => {
                console.log('hello from worker');
            }"""
        )
    message = await message_info.value
    assert message.text == "hello from worker"


async def test_WO_011_should_report_errors(page: Page) -> None:
    async with page.expect_event("pageerror") as error_info:
        await page.evaluate(
            """() => new Worker(URL.createObjectURL(new Blob([`
                setTimeout(() => {
                  // Do a console.log just to check that we do not confuse it with an error.
                  console.log('hey');
                  throw new Error('this is my error');
                })
            `], { type: 'application/javascript' })))"""
        )
    error_log = await error_info.value
    assert "this is my error" in error_log.message


async def test_WO_012_should_clear_upon_navigation(server: Server, page: Page) -> None:
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_worker() as worker_info:
        await page.evaluate(
            "() => new Worker(URL.createObjectURL(new Blob(['console.log(1)'], { type: 'application/javascript' })))"
        )
    worker = await worker_info.value
    assert len(page.workers) == 1
    destroyed = False

    def on_close(_: Worker) -> None:
        nonlocal destroyed
        destroyed = True

    worker.once("close", on_close)
    await page.goto(server.PREFIX + "/one-style.html")
    assert destroyed is True
    assert len(page.workers) == 0


async def test_WO_013_should_clear_upon_cross_process_navigation(
    server: Server, page: Page
) -> None:
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_worker() as worker_info:
        await page.evaluate(
            "() => new Worker(URL.createObjectURL(new Blob(['console.log(1)'], { type: 'application/javascript' })))"
        )
    worker = await worker_info.value
    assert len(page.workers) == 1
    destroyed = False

    def on_close(_: Worker) -> None:
        nonlocal destroyed
        destroyed = True

    worker.once("close", on_close)
    await page.goto(server.CROSS_PROCESS_PREFIX + "/empty.html")
    assert destroyed is True
    assert len(page.workers) == 0


async def test_WO_014_should_attribute_network_activity_for_worker_inside_iframe_to_the_iframe(
    page: Page,
    server: Server,
    browser_name: str,
    browser_major_version: int,
    utils: Utils,
) -> None:
    if browser_name == "chromium" and browser_major_version < 149:
        pytest.skip("needs TargetInfo.parentFrameId for workers")

    await page.goto(server.PREFIX + "/empty.html")
    async with page.expect_worker() as worker_info:
        frame = await utils.attach_frame(
            page, "frame1", server.PREFIX + "/worker/worker.html"
        )
    worker = await worker_info.value
    url = server.PREFIX + "/one-style.css"
    async with page.expect_request(url) as request_info:
        await worker.evaluate(
            "url => fetch(url).then(response => response.text()).then(console.log)",
            url,
        )
    request = await request_info.value
    assert request.url == url
    assert request.frame == frame


async def test_WO_015_should_report_network_activity(
    page: Page,
    server: Server,
    browser_name: str,
    browser_major_version: int,
    assetdir: Path,
) -> None:
    if browser_name == "chromium" and browser_major_version < 143:
        pytest.skip("needs workerScriptLoaded event")

    async with page.expect_worker() as worker_info:
        await page.goto(server.PREFIX + "/worker/worker.html")
    worker = await worker_info.value
    url = server.PREFIX + "/one-style.css"
    async with page.expect_request(url) as request_info:
        async with page.expect_response(url) as response_info:
            await worker.evaluate(
                "url => fetch(url).then(response => response.text()).then(console.log)",
                url,
            )
    request = await request_info.value
    response = await response_info.value
    assert request.url == url
    assert response.request is request
    assert response.ok is True
    assert await response.text() == (assetdir / "one-style.css").read_text()


async def test_WO_016_should_report_network_activity_on_worker_creation(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    url = server.PREFIX + "/one-style.css"
    async with page.expect_request(url) as request_info:
        async with page.expect_response(url) as response_info:
            await page.evaluate(
                """url => new Worker(URL.createObjectURL(new Blob([`
                    fetch("${url}").then(response => response.text()).then(console.log);
                `], { type: 'application/javascript' })))""",
                url,
            )
    request = await request_info.value
    response = await response_info.value
    assert request.url == url
    assert response.request is request
    assert response.ok is True


async def test_WO_017_should_report_worker_script_as_network_request(
    page: Page, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/33107
    # https://github.com/microsoft/playwright/issues/35678
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_event(
        "request", lambda r: "worker.js" in r.url
    ) as request1_info:
        async with page.expect_event(
            "requestfinished", lambda r: "worker.js" in r.url
        ) as request2_info:
            await page.evaluate("() => window.w = new Worker('/worker/worker.js')")
    request1 = await request1_info.value
    request2 = await request2_info.value
    assert request1.url == server.PREFIX + "/worker/worker.js"
    assert request1 is request2
    response = await request1.response()
    assert response
    text = await response.text()
    assert "console.log('hello from the worker');" in text


async def test_WO_018_should_report_worker_script_as_network_request_after_redirect(
    page: Page, server: Server, browser_name: str
) -> None:
    # https://github.com/microsoft/playwright/issues/35678
    if browser_name == "chromium":
        pytest.skip(
            "fixme: Chromium does not report the redirect because it is not plumbed to the worker target"
        )

    await page.goto(server.EMPTY_PAGE)
    server.set_redirect("/worker.js", "/worker2.js")

    def handle_worker2(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "text/javascript")
        request.write(b"console.log('hello from the worker');")
        request.finish()

    server.set_route("/worker2.js", handle_worker2)
    async with page.expect_event(
        "request", lambda r: "worker.js" in r.url
    ) as request_info:
        async with page.expect_console_message(
            lambda msg: "hello from the worker" in msg.text
        ):
            await page.evaluate("() => window.w = new Worker('/worker.js')")
    request = await request_info.value
    assert request.url == server.PREFIX + "/worker.js"
    redirect = request.redirected_to
    assert redirect
    assert redirect.url == server.PREFIX + "/worker2.js"
    response = await redirect.response()
    assert response
    text = await response.text()
    assert "console.log('hello from the worker');" in text


async def test_WO_019_should_dispatch_console_messages_when_page_has_workers(
    page: Page, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/15550
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_worker():
        await page.evaluate(
            "() => new Worker(URL.createObjectURL(new Blob(['const x = 1;'], { type: 'application/javascript' })))"
        )
    async with page.expect_console_message() as message_info:
        await page.evaluate("() => console.log('foo')")
    message = await message_info.value
    assert message.text == "foo"


async def test_WO_020_should_report_and_intercept_network_from_nested_worker(
    page: Page, server: Server, browser_name: str, browser_major_version: int
) -> None:
    if browser_name == "webkit":
        pytest.skip("fixme: https://github.com/microsoft/playwright/issues/27376")
    if browser_name == "chromium" and browser_major_version < 143:
        pytest.skip("needs workerScriptLoaded event")

    json_body = {"foo": "not bar"}
    await page.route("**/simple.json", lambda route: route.fulfill(json=json_body))

    await page.goto(server.EMPTY_PAGE)
    url = server.PREFIX + "/simple.json"
    workers: List[Worker] = []
    messages: List[str] = []

    page.on("worker", lambda worker: workers.append(worker))
    page.on("console", lambda msg: messages.append(msg.text))

    await page.evaluate(
        """url => new Worker(URL.createObjectURL(new Blob([`
            fetch("${url}").then(response => response.text()).then(t => console.log(t.trim()));
        `], { type: 'application/javascript' })))""",
        url,
    )
    await expect_poll(page, lambda: len(workers), 1)

    await workers[0].evaluate(
        """url => new Worker(URL.createObjectURL(new Blob([`
            fetch("${url}").then(response => response.text()).then(t => console.log(t.trim()));
        `], { type: 'application/javascript' })))""",
        url,
    )

    await expect_poll(page, lambda: len(workers), 2)

    # route.fulfill(json=) serializes with json.dumps() where upstream uses JSON.stringify().
    await expect_poll(page, lambda: messages, [json.dumps(json_body)] * 2)


async def test_WO_021_should_support_extra_http_headers(
    page: Page, server: Server, browser_name: str, browser_major_version: int
) -> None:
    # https://github.com/microsoft/playwright/issues/31747
    if browser_name == "chromium" and browser_major_version < 143:
        pytest.skip("needs workerScriptLoaded event")

    await page.set_extra_http_headers({"foo": "bar"})
    async with page.expect_worker() as worker_info:
        with server.expect_request("/worker/worker.js") as request1_info:
            await page.goto(server.PREFIX + "/worker/worker.html")
    worker = await worker_info.value
    with server.expect_request("/one-style.css") as request2_info:
        await worker.evaluate("url => fetch(url)", server.PREFIX + "/one-style.css")
    assert request1_info.value.getHeader("foo") == "bar"
    assert request2_info.value.getHeader("foo") == "bar"


async def test_WO_022_should_support_offline(
    page: Page, server: Server, browser_name: str
) -> None:
    if browser_name == "webkit":
        pytest.skip("fixme: flaky on all platforms")
    if browser_name == "firefox":
        pytest.skip("fixme: does not plumb setOffline into WorkerNavigator::OnLine")

    async with page.expect_worker() as worker_info:
        async with page.expect_console_message(
            lambda msg: "hello from the worker" in msg.text
        ):
            await page.goto(server.PREFIX + "/worker/worker.html")
    worker = await worker_info.value
    await page.context.set_offline(True)
    await expect_poll(page, lambda: worker.evaluate("() => navigator.onLine"), False)
    assert (
        await worker.evaluate("() => fetch('/one-style.css').catch(e => 'error')")
        == "error"
    )
    await page.context.set_offline(False)
    await expect_poll(page, lambda: worker.evaluate("() => navigator.onLine"), True)


async def test_WO_023_should_resolve_worker_script_all_headers_in_main_frame(
    page: Page, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/39948
    async with page.expect_event(
        "requestfinished",
        lambda request: request.url == server.PREFIX + "/worker/worker.js",
    ) as request_info:
        await page.goto(server.PREFIX + "/worker/worker.html")
    request = await request_info.value
    response = await request.response()
    assert response
    request_headers = await request.all_headers()
    assert request_headers["host"]
    response_headers = await response.all_headers()
    assert response_headers["content-type"]


async def test_WO_024_should_resolve_worker_script_all_headers_in_iframe(
    page: Page,
    server: Server,
    browser_name: str,
    browser_major_version: int,
    utils: Utils,
) -> None:
    # https://github.com/microsoft/playwright/issues/39948
    if browser_name == "chromium" and browser_major_version < 151:
        pytest.skip("needs proper Network.requestWillBeSentExtraInfo")

    async with page.expect_event(
        "requestfinished",
        lambda request: request.url == server.PREFIX + "/worker/worker.js",
    ) as request_info:
        await utils.attach_frame(page, "frame1", server.PREFIX + "/worker/worker.html")
    request = await request_info.value
    response = await request.response()
    assert response
    request_headers = await request.all_headers()
    assert request_headers["host"]
    response_headers = await response.all_headers()
    assert response_headers["content-type"]


async def test_WO_025_should_resolve_worker_script_all_headers_in_nested_worker_inside_iframe(
    page: Page, server: Server, browser_name: str, utils: Utils
) -> None:
    # https://github.com/microsoft/playwright/issues/39948
    if browser_name == "webkit":
        pytest.skip("fixme: cannot evaluate in nested worker")
    if browser_name == "firefox":
        pytest.skip("fixme: nested worker script request is not reported at all")

    url = server.PREFIX + "/worker/worker.js"
    async with page.expect_worker() as worker_info:
        async with page.expect_event(
            "requestfinished", lambda request: request.url == url
        ):
            await utils.attach_frame(
                page, "frame1", server.PREFIX + "/worker/worker.html"
            )
    worker = await worker_info.value

    async with page.expect_event(
        "requestfinished", lambda request: request.url == url
    ) as request_info:
        await worker.evaluate(
            """url => {
                self.w = new Worker(url);
            }""",
            url,
        )

    request = await request_info.value
    response = await request.response()
    assert response
    headers = await response.all_headers()
    assert headers["content-type"]
