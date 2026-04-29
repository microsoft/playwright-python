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


from playwright.sync_api import Page


def test_console_messages_should_work(page: Page) -> None:
    page.evaluate(
        """() => {
            for (let i = 0; i < 301; i++)
                console.log('message' + i);
        }"""
    )

    messages = page.console_messages()
    objects = [{"text": m.text, "type": m.type, "page": m.page} for m in messages]

    expected = []
    for i in range(201, 301):
        expected.append({"text": f"message{i}", "type": "log", "page": page})

    assert len(objects) >= 100, "should be at least 100 messages"
    message_count = len(messages) - len(expected)
    assert objects[message_count:] == expected, "should return last messages"


def test_should_have_a_timestamp(page: Page) -> None:
    with page.expect_console_message() as message_info:
        page.evaluate("() => console.log('hello')")
    assert message_info.value.timestamp > 0


def test_clear_console_messages_should_drop_buffered_messages(page: Page) -> None:
    page.evaluate("() => console.log('first')")
    assert any(m.text == "first" for m in page.console_messages())
    page.clear_console_messages()
    assert not any(m.text == "first" for m in page.console_messages())
