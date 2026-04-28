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

from playwright.async_api import Page
from tests.server import Server


async def test_page_errors_should_work(page: Page) -> None:
    await page.evaluate(
        """async () => {
            for (let i = 0; i < 301; i++)
                window.setTimeout(() => { throw new Error('error' + i); }, 0);
            await new Promise(f => window.setTimeout(f, 100));
        }"""
    )

    errors = await page.page_errors()
    messages = [e.message for e in errors]

    expected = []
    for i in range(201, 301):
        expected.append(f"error{i}")

    assert len(messages) >= 100, "should be at least 100 errors"
    message_count = len(messages) - len(expected)
    assert messages[message_count:] == expected, "should return last errors"


async def test_clear_page_errors_should_drop_buffered_errors(page: Page) -> None:
    await page.evaluate("() => setTimeout(() => { throw new Error('first'); }, 0)")
    await page.evaluate("() => new Promise(r => setTimeout(r, 50))")
    assert any(e.message == "first" for e in await page.page_errors())
    await page.clear_page_errors()
    assert not any(e.message == "first" for e in await page.page_errors())


async def test_page_errors_filter_since_navigation_drops_pre_nav_errors(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.evaluate("() => setTimeout(() => { throw new Error('before-nav'); }, 0)")
    await page.evaluate("() => new Promise(r => setTimeout(r, 50))")
    await page.goto(server.EMPTY_PAGE)
    await page.evaluate("() => setTimeout(() => { throw new Error('after-nav'); }, 0)")
    await page.evaluate("() => new Promise(r => setTimeout(r, 50))")
    after = await page.page_errors(filter="since-navigation")
    messages = [e.message for e in after]
    assert "after-nav" in messages
    assert "before-nav" not in messages
