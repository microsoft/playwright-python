# Copyright (c) Microsoft Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License")
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
from asyncio.futures import Future

import pytest
from flaky import flaky

from playwright.async_api import Error, Page, Worker


async def test_workers_page_workers(page: Page, server):
    async with page.expect_worker() as worker_info:
        await page.goto(server.PREFIX + "/worker/worker.html")
    worker = await worker_info.value
    assert "worker.js" in worker.url
    assert repr(worker) == f"<Worker url={worker.url!r}>"

    assert (
        await worker.evaluate('() => self["workerFunction"]()')
        == "worker function result"
    )

    await page.goto(server.EMPTY_PAGE)
    assert len(page.workers) == 0


async def test_workers_should_emit_created_and_destroyed_events(page: Page):
    worker_obj = None
    async with page.expect_event("worker") as event_info:
        worker_obj = await page.evaluate_handle(
            "() => new Worker(URL.createObjectURL(new Blob(['1'], {type: 'application/javascript'})))"
        )
    worker = await event_info.value
    worker_this_obj = await worker.evaluate_handle("() => this")
    worker_destroyed_promise: Future[Worker] = asyncio.Future()
    worker.once("close", lambda w: worker_destroyed_promise.set_result(w))
    await page.evaluate("workerObj => workerObj.terminate()", worker_obj)
    assert await worker_destroyed_promise == worker
    with pytest.raises(Error) as exc:
        await worker_this_obj.get_property("self")
    assert "Most likely the worker has been closed." in exc.value.message


async def test_workers_should_report_console_logs(page):
    async with page.expect_console_message() as message_info:
        await page.evaluate(
            '() => new Worker(URL.createObjectURL(new Blob(["console.log(1)"], {type: "application/javascript"})))'
        )
    message = await message_info.value
    assert message.text == "1"


async def test_workers_should_have_JSHandles_for_console_logs(page):
    log_promise = asyncio.Future()
    page.on("console", lambda m: log_promise.set_result(m))
    await page.evaluate(
        "() => new Worker(URL.createObjectURL(new Blob(['console.log(1,2,3,this)'], {type: 'application/javascript'})))"
    )
    log = await log_promise
    assert log.text == "1 2 3 JSHandle@object"
    assert len(log.args) == 4
    assert await (await log.args[3].get_property("origin")).json_value() == "null"


async def test_workers_should_evaluate(page):
    async with page.expect_event("worker") as event_info:
        await page.evaluate(
            "() => new Worker(URL.createObjectURL(new Blob(['console.log(1)'], {type: 'application/javascript'})))"
        )
    worker = await event_info.value
    assert await worker.evaluate("1+1") == 2


async def test_workers_should_report_errors(page):
    error_promise = asyncio.Future()
    page.on("pageerror", lambda e: error_promise.set_result(e))
    await page.evaluate(
        """() => new Worker(URL.createObjectURL(new Blob([`
      setTimeout(() => {
        // Do a console.log just to check that we do not confuse it with an error.
        console.log('hey');
        throw new Error('this is my error');
      })
    `], {type: 'application/javascript'})))"""
    )
    error_log = await error_promise
    assert "this is my error" in error_log.message


@flaky  # Upstream flaky
async def test_workers_should_clear_upon_navigation(server, page):
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_event("worker") as event_info:
        await page.evaluate(
            '() => new Worker(URL.createObjectURL(new Blob(["console.log(1)"], {type: "application/javascript"})))'
        )
    worker = await event_info.value
    assert len(page.workers) == 1
    destroyed = []
    worker.once("close", lambda _: destroyed.append(True))
    await page.goto(server.PREFIX + "/one-style.html")
    assert destroyed == [True]
    assert len(page.workers) == 0


@flaky  # Upstream flaky
async def test_workers_should_clear_upon_cross_process_navigation(server, page):
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_event("worker") as event_info:
        await page.evaluate(
            "() => new Worker(URL.createObjectURL(new Blob(['console.log(1)'], {type: 'application/javascript'})))"
        )
    worker = await event_info.value
    assert len(page.workers) == 1
    destroyed = []
    worker.once("close", lambda _: destroyed.append(True))
    await page.goto(server.CROSS_PROCESS_PREFIX + "/empty.html")
    assert destroyed == [True]
    assert len(page.workers) == 0


async def test_workers_should_report_network_activity(page, server):
    async with page.expect_worker() as worker_info:
        await page.goto(server.PREFIX + "/worker/worker.html"),
    worker = await worker_info.value
    url = server.PREFIX + "/one-style.css"
    async with page.expect_request(url) as request_info, page.expect_response(
        url
    ) as response_info:
        await worker.evaluate(
            "url => fetch(url).then(response => response.text()).then(console.log)", url
        )
    request = await request_info.value
    response = await response_info.value
    assert request.url == url
    assert response.request == request
    assert response.ok


async def test_workers_should_report_network_activity_on_worker_creation(page, server):
    # Chromium needs waitForDebugger enabled for this one.
    await page.goto(server.EMPTY_PAGE)
    url = server.PREFIX + "/one-style.css"
    async with page.expect_request(url) as request_info, page.expect_response(
        url
    ) as response_info:
        await page.evaluate(
            """url => new Worker(URL.createObjectURL(new Blob([`
        fetch("${url}").then(response => response.text()).then(console.log);
        `], {type: 'application/javascript'})))""",
            url,
        )
    request = await request_info.value
    response = await response_info.value
    assert request.url == url
    assert response.request == request
    assert response.ok


async def test_workers_should_format_number_using_context_locale(browser, server):
    context = await browser.new_context(locale="ru-RU")
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_worker() as worker_info:
        await page.evaluate(
            "() => new Worker(URL.createObjectURL(new Blob(['console.log(1)'], {type: 'application/javascript'})))"
        )
    worker = await worker_info.value
    assert await worker.evaluate("() => (10000.20).toLocaleString()") == "10\u00A0000,2"
    await context.close()
