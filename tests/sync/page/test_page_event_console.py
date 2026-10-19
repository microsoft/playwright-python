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

"""Port of tests/page/page-event-console.spec.ts."""


import re
import time
from typing import Any, Callable, List, Optional

import pytest

from playwright.sync_api import ConsoleMessage, Page
from tests.server import Server


def poll_until_equal(
    page: Page, actual: Callable[[], Any], expected: Any, timeout: float = 5000
) -> None:
    """Port of `await expect.poll(actual).toEqual(expected)`."""
    deadline = time.monotonic() + timeout / 1000
    while actual() != expected and time.monotonic() < deadline:
        page.wait_for_timeout(100)
    assert actual() == expected


def test_CM_001_should_work_smoke(page: Page, browser_name: str) -> None:
    messages: List[ConsoleMessage] = []
    page.once("console", lambda m: messages.append(m))
    with page.expect_event("console"):
        page.evaluate("() => console.log('hello', 5, { foo: 'bar' })")
    message = messages[0]
    if browser_name != "firefox":
        assert message.text == "hello 5 {foo: bar}"
    else:
        assert message.text == "hello 5 JSHandle@object"
    assert message.type == "log"
    assert message.args[0].json_value() == "hello"
    assert message.args[1].json_value() == 5
    assert message.args[2].json_value() == {"foo": "bar"}


def test_CM_002_should_emit_same_log_twice(page: Page) -> None:
    messages: List[str] = []
    page.on("console", lambda m: messages.append(m.text))
    page.evaluate(
        """() => {
    for (let i = 0; i < 2; ++i)
      console.log('hello');
  }"""
    )
    assert messages == ["hello", "hello"]


def test_CM_003_should_use_text_for_inspection(page: Page) -> None:
    text: Optional[str] = None

    def inspect(value: ConsoleMessage) -> None:
        nonlocal text
        text = str(value)

    page.on("console", inspect)
    page.evaluate("() => console.log('Hello world')")
    assert text == "Hello world"


def test_CM_004_should_work_for_different_console_api_calls(page: Page) -> None:
    messages: List[ConsoleMessage] = []
    page.on("console", lambda msg: messages.append(msg))
    # All console events will be reported before `page.evaluate` is finished.
    page.evaluate(
        """() => {
    // A pair of time/timeEnd generates only one Console API call.
    console.time('calling console.time');
    console.timeEnd('calling console.time');
    console.trace('calling console.trace');
    console.dir('calling console.dir');
    console.warn('calling console.warn');
    console.error('calling console.error');
    console.info('calling console.info');
    console.debug('calling console.debug');
    console.log(Promise.resolve('should not wait until resolved!'));
  }"""
    )

    # WebKit uses console.debug() to report binding calls, make sure they don't get reported.
    def foobar(_: Any, value: Any) -> Any:
        return page.evaluate("value => console.log(value)", value)

    page.expose_binding("foobar", foobar)
    page.evaluate("() => window['foobar']('Using bindings')")

    assert [msg.type for msg in messages] == [
        "timeEnd",
        "trace",
        "dir",
        "warning",
        "error",
        "info",
        "debug",
        "log",
        "log",
    ]
    assert "calling console.time" in messages[0].text
    assert [msg.text for msg in messages[1:]] == [
        "calling console.trace",
        "calling console.dir",
        "calling console.warn",
        "calling console.error",
        "calling console.info",
        "calling console.debug",
        "Promise",
        "Using bindings",
    ]


def test_CM_005_should_format_the_message_correctly_with_time_time_log_time_end(
    page: Page, browser_name: str
) -> None:
    if browser_name == "firefox":
        pytest.skip("fixme: https://github.com/microsoft/playwright/issues/10580")
    messages: List[ConsoleMessage] = []
    page.on("console", lambda msg: messages.append(msg))
    page.evaluate(
        """async () => {
    console.time('foo time');
    await new Promise(x => window.builtins.setTimeout(x, 100));
    console.timeLog('foo time');
    await new Promise(x => window.builtins.setTimeout(x, 100));
    console.timeEnd('foo time');
  }"""
    )
    assert len(messages) == 2
    if browser_name == "webkit":
        assert messages[0].type == "timeEnd"
    elif browser_name == "chromium":
        assert messages[0].type == "log"
    elif browser_name == "firefox":
        assert messages[0].type == "timeLog"
    assert messages[1].type == "timeEnd"

    # WebKit has no space before the unit: https://bugs.webkit.org/show_bug.cgi?id=233556
    # Firefox/Bidi has no fractional part.
    assert re.search(r"foo time: \d+(.\d+)? ?ms", messages[0].text)
    assert re.search(r"foo time: \d+(.\d+)? ?ms", messages[1].text)


def test_CM_006_should_not_fail_for_window_object(
    page: Page, browser_name: str
) -> None:
    messages: List[ConsoleMessage] = []
    page.once("console", lambda msg: messages.append(msg))
    with page.expect_event("console"):
        page.evaluate("() => console.error(window)")
    message = messages[0]
    if browser_name != "firefox":
        assert message.text == "Window"
    else:
        assert message.text == "JSHandle@object"


def test_CM_007_should_not_fail_for_object_that_can_t_be_coerced_to_a_primitive(
    page: Page, browser_name: str
) -> None:
    messages: List[ConsoleMessage] = []
    page.once("console", lambda msg: messages.append(msg))
    with page.expect_event("console"):
        page.evaluate(
            "() => console.log({ toString() { return {}; }, valueOf() { return {}; } })"
        )
    message = messages[0]
    if browser_name != "firefox":
        assert re.search(
            r"\{toString: (Function)?, valueOf: (Function)?\}", message.text
        )
    else:
        assert message.text == "JSHandle@object"


def test_CM_008_should_trigger_correct_log(
    page: Page, server: Server, browser_name: str, is_win: bool
) -> None:
    if browser_name == "webkit" and is_win:
        pytest.skip("Upstream issue https://bugs.webkit.org/show_bug.cgi?id=229515")
    page.goto("about:blank")
    with page.expect_event("console") as message_info:
        page.evaluate("async url => fetch(url).catch(e => {})", server.EMPTY_PAGE)
    message = message_info.value
    assert re.search(r"Access-Control-Allow-Origin|CORS", message.text)
    assert message.type == "error"


def test_CM_009_should_have_location_for_console_api_calls(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    with page.expect_event(
        "console", lambda m: m.text.startswith("here:")
    ) as message_info:
        page.goto(server.PREFIX + "/consolelog.html")
    message = message_info.value
    assert message.type == "log"
    # Engines have different column notion.
    location = message.location
    assert {
        "url": location["url"],
        "line": location["line"],
        "lineNumber": location["lineNumber"],
    } == {
        "url": server.PREFIX + "/consolelog.html",
        "line": 7,
        "lineNumber": 7,
    }


def test_CM_010_should_not_throw_when_there_are_console_messages_in_detached_iframes(
    page: Page, server: Server
) -> None:
    # @see https://github.com/GoogleChrome/puppeteer/issues/3865
    page.goto(server.EMPTY_PAGE)
    with page.expect_popup() as popup_info:
        page.evaluate(
            """async () => {
      // 1. Create a popup that Playwright is not connected to.
      const win = window.open('');
      window['_popup'] = win;
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
        )
    popup = popup_info.value
    # 4. Connect to the popup and make sure it doesn't throw.
    assert popup.evaluate("1 + 1") == 2


def test_CM_011_should_use_object_previews_for_arrays_and_objects(
    page: Page, browser_name: str
) -> None:
    text: Optional[str] = None

    def on_console(message: ConsoleMessage) -> None:
        nonlocal text
        text = message.text

    page.on("console", on_console)
    page.evaluate("() => console.log([1, 2, 3], { a: 1 }, window)")

    if browser_name != "firefox":
        assert text == "[1, 2, 3] {a: 1} Window"
    else:
        assert text == "Array JSHandle@object JSHandle@object"


def test_CM_012_should_use_object_previews_for_errors(
    page: Page, browser_name: str
) -> None:
    text: Optional[str] = None

    def on_console(message: ConsoleMessage) -> None:
        nonlocal text
        text = message.text

    page.on("console", on_console)
    page.evaluate("() => console.log(new Error('Exception'))")
    assert text is not None
    if browser_name == "firefox":
        assert text == "Error"
    elif browser_name == "chromium":
        assert ".evaluate" in text
    elif browser_name == "webkit":
        assert text == "Error: Exception"


def test_CM_013_do_not_update_console_count_on_unhandled_rejections(
    page: Page,
) -> None:
    messages: List[str] = []

    def console_event_listener(m: ConsoleMessage) -> None:
        messages.append(m.text)

    page.on("console", console_event_listener)

    page.evaluate(
        """() => {
    const fail = async () => Promise.reject(new Error('error'));
    console.log('begin');
    void fail();
    void fail();
    fail().catch(() => {
      console.log('end');
    });
  }"""
    )

    poll_until_equal(page, lambda: messages, ["begin", "end"])


def test_CM_014_should_have_timestamp(page: Page) -> None:
    # Generous slack to absorb host wall-clock resolution (e.g. ~15.6ms on Windows)
    # vs sub-millisecond browser timestamps.
    before = time.time() * 1000 - 100
    with page.expect_event("console") as message_info:
        page.evaluate("() => console.log('timestamp test')")
    message = message_info.value
    after = time.time() * 1000 + 100
    assert message.timestamp >= before
    assert message.timestamp <= after


def test_CM_015_should_have_increasing_timestamps(page: Page) -> None:
    messages: List[ConsoleMessage] = []
    page.on("console", lambda msg: messages.append(msg))
    page.evaluate(
        """() => {
    console.log('first');
    console.log('second');
    console.log('third');
  }"""
    )
    assert len(messages) == 3
    for i in range(1, len(messages)):
        assert messages[i].timestamp >= messages[i - 1].timestamp


def test_CM_016_should_have_timestamp_in_console_messages(page: Page) -> None:
    # Generous slack to absorb host wall-clock resolution (e.g. ~15.6ms on Windows)
    # vs sub-millisecond browser timestamps.
    before = time.time() * 1000 - 100
    page.evaluate("() => console.log('stored message')")
    after = time.time() * 1000 + 100
    messages = page.console_messages()
    assert len(messages) >= 1
    last = messages[-1]
    assert last.text == "stored message"
    assert last.timestamp >= before
    assert last.timestamp <= after


def test_CM_017_console_messages_should_work(page: Page) -> None:
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
        expected.append({"text": "message" + str(i), "type": "log", "page": page})

    assert len(objects) >= 100, "should be at least 100 messages"
    start = len(objects) - len(expected)
    assert objects[start:] == expected, "should return last messages"


def test_CM_018_clear_console_messages_should_work(page: Page) -> None:
    page.evaluate(
        """() => {
    console.log('message1');
    console.log('message2');
  }"""
    )

    messages = page.console_messages()
    assert "message1" in [m.text for m in messages]
    assert "message2" in [m.text for m in messages]

    page.clear_console_messages()

    messages = page.console_messages()
    assert messages == []

    page.evaluate("() => console.log('message3')")
    messages = page.console_messages()
    assert len(messages) == 1
    assert messages[0].text == "message3"


def test_CM_019_console_messages_since_navigation_filter_should_work(
    page: Page, server: Server
) -> None:
    page.evaluate("() => console.log('before navigation')")
    page.goto(server.EMPTY_PAGE)
    page.evaluate("() => console.log('after navigation')")

    all_messages = page.console_messages(filter="all")
    assert "before navigation" in [m.text for m in all_messages]
    assert "after navigation" in [m.text for m in all_messages]

    # since-navigation is the default
    since_nav = page.console_messages()
    assert "before navigation" not in [m.text for m in since_nav]
    assert "after navigation" in [m.text for m in since_nav]


def test_CM_020_page_errors_since_navigation_filter_should_work(
    page: Page, server: Server
) -> None:
    server.set_content(
        "/page1", "<script>throw new Error('page1 error');</script>", "text/html"
    )
    server.set_content(
        "/page2", "<script>throw new Error('page2 error');</script>", "text/html"
    )

    page.goto(server.PREFIX + "/page1")
    page.goto(server.PREFIX + "/page2")

    all_errors = page.page_errors(filter="all")
    assert "page1 error" in [e.message for e in all_errors]
    assert "page2 error" in [e.message for e in all_errors]

    # since-navigation is the default
    since_nav = page.page_errors()
    assert "page1 error" not in [e.message for e in since_nav]
    assert "page2 error" in [e.message for e in since_nav]
