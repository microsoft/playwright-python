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

from typing import List

import pytest

from playwright.sync_api import ConsoleMessage, Page
from tests.server import Server


def test_console_should_work(page: Page, browser_name: str) -> None:
    messages: List[ConsoleMessage] = []
    page.once("console", lambda m: messages.append(m))
    with page.expect_console_message():
        page.evaluate('() => console.log("hello", 5, {foo: "bar"})')
    assert len(messages) == 1
    message = messages[0]
    if browser_name != "firefox":
        assert message.text == "hello 5 {foo: bar}"
        assert str(message) == "hello 5 {foo: bar}"
    else:
        assert message.text == "hello 5 JSHandle@object"
        assert str(message) == "hello 5 JSHandle@object"
    assert message.type == "log"
    assert message.args[0].json_value() == "hello"
    assert message.args[1].json_value() == 5
    assert message.args[2].json_value() == {"foo": "bar"}


def test_console_should_emit_same_log_twice(page: Page) -> None:
    messages = []
    page.on("console", lambda m: messages.append(m.text))
    page.evaluate('() => { for (let i = 0; i < 2; ++i ) console.log("hello"); } ')
    assert messages == ["hello", "hello"]


def test_console_should_use_text_for__str__(page: Page) -> None:
    messages = []
    page.on("console", lambda m: messages.append(m))
    page.evaluate('() => console.log("Hello world")')
    assert len(messages) == 1
    assert str(messages[0]) == "Hello world"


def test_console_should_work_for_different_console_api_calls(page: Page) -> None:
    messages = []
    page.on("console", lambda m: messages.append(m))
    # All console events will be reported before 'page.evaluate' is finished.
    page.evaluate(
        """() => {
      // A pair of time/timeEnd generates only one Console API call.
      console.time('calling console.time');
      console.timeEnd('calling console.time');
      console.trace('calling console.trace');
      console.dir('calling console.dir');
      console.warn('calling console.warn');
      console.error('calling console.error');
      console.log(Promise.resolve('should not wait until resolved!'));
    }"""
    )
    assert list(map(lambda msg: msg.type, messages)) == [
        "timeEnd",
        "trace",
        "dir",
        "warning",
        "error",
        "log",
    ]

    assert "calling console.time" in messages[0].text
    assert list(map(lambda msg: msg.text, messages[1:])) == [
        "calling console.trace",
        "calling console.dir",
        "calling console.warn",
        "calling console.error",
        "Promise",
    ]


def test_console_should_not_fail_for_window_object(
    page: Page, browser_name: str
) -> None:
    messages = []
    page.once("console", lambda m: messages.append(m))
    with page.expect_console_message():
        page.evaluate("() => console.error(window)")
    assert len(messages) == 1
    if browser_name != "firefox":
        assert messages[0].text == "Window"
    else:
        assert messages[0].text == "JSHandle@object"


# Upstream issue https://bugs.webkit.org/show_bug.cgi?id=229515
@pytest.mark.skip_browser("webkit")
def test_console_should_trigger_correct_Log(page: Page, server: Server) -> None:
    page.goto("about:blank")
    with page.expect_console_message() as message:
        page.evaluate("url => fetch(url).catch(e => {})", server.EMPTY_PAGE)
    assert "Access-Control-Allow-Origin" in message.value.text
    assert message.value.type == "error"


def test_console_should_have_location_for_console_api_calls(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    with page.expect_console_message() as message_info:
        page.goto(server.PREFIX + "/consolelog.html")
    message = message_info.value
    assert message.text == "yellow"
    assert message.type == "log"
    location = message.location
    # Engines have different column notion.
    assert location["url"] == server.PREFIX + "/consolelog.html"
    assert location["lineNumber"] == 7


def test_console_should_not_throw_when_there_are_console_messages_in_detached_iframes(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    with page.expect_popup() as popup:
        page.evaluate(
            """async() => {
                // 1. Create a popup that Playwright is not connected to.
                const win = window.open('');
                window._popup = win;
                if (window.document.readyState !== 'complete')
                new Promise(f => window.addEventListener('load', f));
                // 2. In this popup, create an iframe that console.logs a message.
                win.document.body.innerHTML = `<iframe src='/consolelog.html'></iframe>`;
                const frame = win.document.querySelector('iframe');
                if (!frame.contentDocument || frame.contentDocument.readyState !== 'complete')
                new Promise(f => frame.addEventListener('load', f));
                // 3. After that, remove the iframe.
                frame.remove();
            }"""
        )
    # 4. Connect to the popup and make sure it doesn't throw.
    assert popup.value.evaluate("1 + 1") == 2
