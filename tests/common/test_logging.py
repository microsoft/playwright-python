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

import logging
from unittest import TestCase

import pytest

from playwright.async_api import Error, async_playwright
from playwright.sync_api import sync_playwright


def test_logging_sync(browser_name, launch_arguments):
    class LoggingTestCase(TestCase):
        def test_logging(self):
            with self.assertLogs("playwright", level=logging.DEBUG) as logger:
                with sync_playwright() as playwright:
                    browser = getattr(playwright, browser_name).launch(
                        **launch_arguments
                    )
                    page = browser.new_page()
                    page.goto("https://example.com")
                    with pytest.raises(Error):
                        page.wait_for_selector("will never find", timeout=100)
                    page.close()
                    browser.close()
            self.assertEqual(
                logger.output,
                [
                    "DEBUG:playwright:=> browser_type.launch started",
                    "DEBUG:playwright:<= browser_type.launch succeeded",
                    "DEBUG:playwright:=> browser.new_page started",
                    "DEBUG:playwright:<= browser.new_page succeeded",
                    "DEBUG:playwright:=> page.goto started",
                    "DEBUG:playwright:<= page.goto succeeded",
                    "DEBUG:playwright:=> page.wait_for_selector started",
                    "DEBUG:playwright:<= page.wait_for_selector failed",
                    "DEBUG:playwright:=> page.close started",
                    "DEBUG:playwright:<= page.close succeeded",
                    "DEBUG:playwright:=> browser.close started",
                    "DEBUG:playwright:<= browser.close succeeded",
                ],
            )

    test_case = LoggingTestCase()
    test_case.test_logging()


@pytest.mark.asyncio
async def test_logging_async(browser_name, launch_arguments):
    class AsyncLoggingTestCase(TestCase):
        async def test_logging(self):
            with self.assertLogs("playwright", level=logging.DEBUG) as logger:
                async with async_playwright() as playwright:
                    browser = await getattr(playwright, browser_name).launch(
                        **launch_arguments
                    )
                    page = await browser.new_page()
                    await page.goto("https://example.com")
                    with pytest.raises(Error):
                        await page.wait_for_selector("will never find", timeout=100)
                    await page.close()
                    await browser.close()
            self.assertEqual(
                logger.output,
                [
                    "DEBUG:playwright:=> browser_type.launch started",
                    "DEBUG:playwright:<= browser_type.launch succeeded",
                    "DEBUG:playwright:=> browser.new_page started",
                    "DEBUG:playwright:<= browser.new_page succeeded",
                    "DEBUG:playwright:=> page.goto started",
                    "DEBUG:playwright:<= page.goto succeeded",
                    "DEBUG:playwright:=> page.wait_for_selector started",
                    "DEBUG:playwright:<= page.wait_for_selector failed",
                    "DEBUG:playwright:=> page.close started",
                    "DEBUG:playwright:<= page.close succeeded",
                    "DEBUG:playwright:=> browser.close started",
                    "DEBUG:playwright:<= browser.close succeeded",
                ],
            )

    test_case = AsyncLoggingTestCase()
    await test_case.test_logging()
