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
from playwright.async_api import Browser
from tests.server import Server


async def test_should_allow_service_workers_by_default(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(server.PREFIX + "/serviceworkers/fetchdummy/sw.html")
    await page.evaluate("() => window.activationPromise")
    await context.close()


async def test_block_blocks_service_worker_registration(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context(service_workers="block")
    page = await context.new_page()
    async with page.expect_console_message(
        lambda m: "Service Worker registration blocked by Playwright" == m.text
    ):
        await page.goto(server.PREFIX + "/serviceworkers/fetchdummy/sw.html")
    await context.close()
