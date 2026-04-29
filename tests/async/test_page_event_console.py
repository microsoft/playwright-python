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


async def test_console_messages_should_work(page: Page) -> None:
    await page.evaluate(
        """() => {
            for (let i = 0; i < 301; i++)
                console.log('message' + i);
        }"""
    )

    messages = await page.console_messages()
    objects = [{"text": m.text, "type": m.type, "page": m.page} for m in messages]

    expected = []
    for i in range(201, 301):
        expected.append({"text": f"message{i}", "type": "log", "page": page})

    assert len(objects) >= 100, "should be at least 100 messages"
    message_count = len(messages) - len(expected)
    assert objects[message_count:] == expected, "should return last messages"


async def test_should_have_a_timestamp(page: Page) -> None:
    async with page.expect_console_message() as message_info:
        await page.evaluate("() => console.log('hello')")
    message = await message_info.value
    assert message.timestamp > 0


async def test_clear_console_messages_should_drop_buffered_messages(page: Page) -> None:
    await page.evaluate("() => console.log('first')")
    assert any(m.text == "first" for m in await page.console_messages())
    await page.clear_console_messages()
    assert not any(m.text == "first" for m in await page.console_messages())
    await page.evaluate("() => console.log('second')")
    assert any(m.text == "second" for m in await page.console_messages())


async def test_console_messages_filter_since_navigation_drops_pre_nav_messages(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.evaluate("() => console.log('before-nav')")
    await page.goto(server.EMPTY_PAGE)
    await page.evaluate("() => console.log('after-nav')")
    after = await page.console_messages(filter="since-navigation")
    texts = [m.text for m in after]
    assert "after-nav" in texts
    assert "before-nav" not in texts
