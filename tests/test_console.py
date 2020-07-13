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

import asyncio
import pytest

from playwright.console_message import ConsoleMessage
from typing import List

from playwright.page import Page


async def test_console_should_work(page: Page, server):
    messages: List[ConsoleMessage] = []
    page.once("console", lambda m: messages.append(m))
    await asyncio.gather(
        page.evaluate('() => console.log("hello", 5, {foo: "bar"})'),
        page.waitForEvent("console"),
    )
    assert len(messages) == 1
    message = messages[0]
    assert message.text == "hello 5 JSHandle@object"
    assert str(message) == "hello 5 JSHandle@object"
    assert message.type == "log"
    assert await message.args[0].jsonValue() == "hello"
    assert await message.args[1].jsonValue() == 5
    assert await message.args[2].jsonValue() == {"foo": "bar"}


async def test_console_should_emit_same_log_twice(page, server):
    messages = []
    page.on("console", lambda m: messages.append(m.text))
    await page.evaluate('() => { for (let i = 0; i < 2; ++i ) console.log("hello"); } ')
    assert messages == ["hello", "hello"]


async def test_console_should_use_text_for__str__(page):
    messages = []
    page.on("console", lambda m: messages.append(m))
    await page.evaluate('() => console.log("Hello world")')
    assert len(messages) == 1
    assert str(messages[0]) == "Hello world"


async def test_console_should_work_for_different_console_api_calls(page, server):
    messages = []
    page.on("console", lambda m: messages.append(m))
    # All console events will be reported before 'page.evaluate' is finished.
    await page.evaluate(
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
        "JSHandle@promise",
    ]


async def test_console_should_not_fail_for_window_object(page, server):
    messages = []
    page.once("console", lambda m: messages.append(m))
    await asyncio.gather(
        page.evaluate("() => console.error(window)"), page.waitForEvent("console")
    )
    assert len(messages) == 1
    assert messages[0].text == "JSHandle@object"


async def test_console_should_trigger_correct_Log(page, server):
    await page.goto("about:blank")
    message = (
        await asyncio.gather(
            page.waitForEvent("console"),
            page.evaluate("async url => fetch(url).catch(e => {})", server.EMPTY_PAGE),
        )
    )[0]
    assert "Access-Control-Allow-Origin" in message.text
    assert message.type == "error"


async def test_console_should_have_location_for_console_api_calls(page, server):
    await page.goto(server.EMPTY_PAGE)
    message = (
        await asyncio.gather(
            page.waitForEvent("console"), page.goto(server.PREFIX + "/consolelog.html"),
        )
    )[0]
    assert message.text == "yellow"
    assert message.type == "log"
    location = message.location
    # Engines have different column notion.
    del location["columnNumber"]
    assert location == {"url": server.PREFIX + "/consolelog.html", "lineNumber": 7}


@pytest.mark.skip_browser("firefox")  # a fix just landed upstream, will roll later
async def test_console_should_not_throw_when_there_are_console_messages_in_detached_iframes(
    page, server
):
    await page.goto(server.EMPTY_PAGE)
    popup = (
        await asyncio.gather(
            page.waitForEvent("popup"),
            page.evaluate(
                """async() => {
        // 1. Create a popup that Playwright is not connected to.
        const win = window.open('');
        window._popup = win;
        if (window.document.readyState !== 'complete')
          await new Promise(f => window.addEventListener('load', f));
        // 2. In this popup, create an iframe that console.logs a message.
        win.document.body.innerHTML = `<iframe src='/consolelog.html'></iframe>`;
        const frame = win.document.querySelector('iframe');
        if (!frame.contentDocument || frame.contentDocument.readyState !== 'complete')
          await new Promise(f => frame.addEventListener('load', f));
        // 3. After that, remove the iframe.
        frame.remove();
      }"""
            ),
        )
    )[0]
    # 4. Connect to the popup and make sure it doesn't throw.
    assert await popup.evaluate("1 + 1") == 2
