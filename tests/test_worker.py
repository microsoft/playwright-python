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
from playwright.worker import Worker
import pytest
from playwright import Error
from playwright.page import Page


async def test_workers_page_workers(page, server):
    await asyncio.gather(
        page.waitForEvent("worker"), page.goto(server.PREFIX + "/worker/worker.html")
    )
    worker = page.workers[0]
    assert "worker.js" in worker.url

    assert (
        await worker.evaluate('() => self["workerFunction"]()')
        == "worker function result"
    )

    await page.goto(server.EMPTY_PAGE)
    assert len(page.workers) == 0


async def test_workers_should_emit_created_and_destroyed_events(page: Page):
    worker_createdpromise = asyncio.ensure_future(page.waitForEvent("worker"))
    worker_obj = await page.evaluateHandle(
        "() => new Worker(URL.createObjectURL(new Blob(['1'], {type: 'application/javascript'})))"
    )
    worker = await worker_createdpromise
    worker_this_obj = await worker.evaluateHandle("() => this")
    worker_destroyed_promise: Future[Worker] = asyncio.Future()
    worker.once("close", lambda w: worker_destroyed_promise.set_result(w))
    await page.evaluate("workerObj => workerObj.terminate()", worker_obj)
    assert await worker_destroyed_promise == worker
    with pytest.raises(Error) as exc:
        await worker_this_obj.getProperty("self")
    assert "Most likely the worker has been closed." in exc.value.message


async def test_workers_should_report_console_logs(page):
    [message, _] = await asyncio.gather(
        page.waitForEvent("console"),
        page.evaluate(
            '() => new Worker(URL.createObjectURL(new Blob(["console.log(1)"], {type: "application/javascript"})))'
        ),
    )
    assert message.text == "1"


@pytest.mark.skip_browser("firefox")  # TODO: investigate further @pavelfeldman
async def test_workers_should_have_JSHandles_for_console_logs(page):
    log_promise = asyncio.Future()
    page.on("console", lambda m: log_promise.set_result(m))
    await page.evaluate(
        "() => new Worker(URL.createObjectURL(new Blob(['console.log(1,2,3,this)'], {type: 'application/javascript'})))"
    )
    log = await log_promise
    assert log.text == "1 2 3 JSHandle@object"
    assert len(log.args) == 4
    assert await (await log.args[3].getProperty("origin")).jsonValue() == "null"


async def test_workers_should_evaluate(page):
    worker_createdpromise = asyncio.ensure_future(page.waitForEvent("worker"))
    await page.evaluate(
        "() => new Worker(URL.createObjectURL(new Blob(['console.log(1)'], {type: 'application/javascript'})))"
    )
    worker = await worker_createdpromise
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


async def test_workers_should_clear_upon_navigation(server, page):
    await page.goto(server.EMPTY_PAGE)
    worker_createdpromise = asyncio.ensure_future(page.waitForEvent("worker"))
    await page.evaluate(
        '() => new Worker(URL.createObjectURL(new Blob(["console.log(1)"], {type: "application/javascript"})))'
    )
    worker = await worker_createdpromise
    assert len(page.workers) == 1
    destroyed = []
    worker.once("close", lambda _: destroyed.append(True))
    await page.goto(server.PREFIX + "/one-style.html")
    assert destroyed
    assert len(page.workers) == 0


async def test_workers_should_clear_upon_cross_process_navigation(server, page):
    await page.goto(server.EMPTY_PAGE)
    worker_createdpromise = asyncio.ensure_future(page.waitForEvent("worker"))
    await page.evaluate(
        "() => new Worker(URL.createObjectURL(new Blob(['console.log(1)'], {type: 'application/javascript'})))"
    )
    worker = await worker_createdpromise
    assert len(page.workers) == 1
    destroyed = []
    worker.once("close", lambda _: destroyed.append(True))
    await page.goto(server.CROSS_PROCESS_PREFIX + "/empty.html")
    assert destroyed
    assert len(page.workers) == 0


async def test_workers_should_report_network_activity(page, server):
    [worker, _] = await asyncio.gather(
        page.waitForEvent("worker"), page.goto(server.PREFIX + "/worker/worker.html"),
    )
    url = server.PREFIX + "/one-style.css"
    request_promise = asyncio.ensure_future(page.waitForRequest(url))
    response_promise = asyncio.ensure_future(page.waitForResponse(url))
    await worker.evaluate(
        "url => fetch(url).then(response => response.text()).then(console.log)", url
    )
    request = await request_promise
    response = await response_promise
    assert request.url == url
    assert response.request == request
    assert response.ok


async def test_workers_should_report_network_activity_on_worker_creation(page, server):
    # Chromium needs waitForDebugger enabled for this one.
    await page.goto(server.EMPTY_PAGE)
    url = server.PREFIX + "/one-style.css"
    request_promise = asyncio.ensure_future(page.waitForRequest(url))
    response_promise = asyncio.ensure_future(page.waitForResponse(url))
    await page.evaluate(
        """url => new Worker(URL.createObjectURL(new Blob([`
      fetch("${url}").then(response => response.text()).then(console.log);
    `], {type: 'application/javascript'})))""",
        url,
    )
    request = await request_promise
    response = await response_promise
    assert request.url == url
    assert response.request == request
    assert response.ok


async def test_workers_should_format_number_using_context_locale(browser, server):
    context = await browser.newContext(locale="ru-RU")
    page = await context.newPage()
    await page.goto(server.EMPTY_PAGE)
    [worker, _] = await asyncio.gather(
        page.waitForEvent("worker"),
        page.evaluate(
            "() => new Worker(URL.createObjectURL(new Blob(['console.log(1)'], {type: 'application/javascript'})))"
        ),
    )
    assert await worker.evaluate("() => (10000.20).toLocaleString()") == "10\u00A0000,2"
    await context.close()
