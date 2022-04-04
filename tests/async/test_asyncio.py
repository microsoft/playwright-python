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
import contextlib

from playwright.async_api import async_playwright


def test_should_cancel_underlying_calls(browser_name: str):
    handler_exception = None

    async def main():
        loop = asyncio.get_running_loop()

        def handler(loop, context):
            nonlocal handler_exception
            handler_exception = context["exception"]

        async with async_playwright() as p:
            loop.set_exception_handler(handler)
            browser = await p[browser_name].launch()
            page = await browser.new_page()
            task = asyncio.create_task(page.wait_for_selector("will-never-find"))
            # make sure that the wait_for_selector message was sent to the server (driver)
            await asyncio.sleep(1)
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
            await browser.close()

    asyncio.run(main())

    assert handler_exception is None
