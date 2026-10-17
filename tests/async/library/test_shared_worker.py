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

"""Port of tests/library/shared-worker.spec.ts."""

from playwright.async_api import BrowserContext
from tests.server import Server


async def test_WO_026_should_survive_shared_worker_restart(
    context: BrowserContext, server: Server
) -> None:
    page1 = await context.new_page()
    await page1.goto(server.PREFIX + "/shared-worker/shared-worker.html")
    assert await page1.evaluate("window.sharedWorkerResponsePromise") == "echo:hello"
    await page1.close()

    page2 = await context.new_page()
    await page2.goto(server.PREFIX + "/shared-worker/shared-worker.html")
    assert await page2.evaluate("window.sharedWorkerResponsePromise") == "echo:hello"
    await page2.close()
