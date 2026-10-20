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

"""Python only: tests of behaviors that no upstream test covers."""


from playwright.async_api import Page
from tests.server import Server


async def test_workers_page_workers(page: Page, server: Server) -> None:
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


async def test_worker_should_report_console_event(page: Page) -> None:
    async with page.expect_worker() as worker_info:
        await page.evaluate(
            "() => { window.worker = new Worker(URL.createObjectURL(new Blob(['42'], { type: 'application/javascript' }))); }"
        )
    worker = await worker_info.value

    async with worker.expect_event("console") as message1_info:
        async with page.expect_console_message() as message2_info:
            async with page.context.expect_console_message() as message3_info:
                await worker.evaluate("() => { console.log('hello from worker'); }")

    message1 = await message1_info.value
    message2 = await message2_info.value
    message3 = await message3_info.value

    assert message1.text == "hello from worker"
    assert message1 is message2
    assert message1 is message3
    assert message1.worker is worker
