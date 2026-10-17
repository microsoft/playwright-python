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

"""Port of tests/library/browsercontext-events.spec.ts."""

import time
from typing import Any, Callable, List

import pytest

from playwright.sync_api import BrowserContext, Page
from tests.server import Server, TestServerRequest
from tests.utils import must


def poll_until_equal(
    actual: Callable[[], Any], expected: Any, timeout: float = 5000
) -> None:
    """Port of `await expect.poll(actual).toBe(expected)`."""
    deadline = time.monotonic() + timeout / 1000
    value = actual()
    while value != expected and time.monotonic() < deadline:
        time.sleep(0.1)
        value = actual()
    assert value == expected


def test_BC_032_console_event_should_work_smoke(page: Page) -> None:
    with page.context.expect_event("console") as message_info:
        page.evaluate("() => console.log('hello')")
    message = message_info.value

    assert message.text == "hello"
    assert message.page == page


def test_BC_033_console_event_should_work_with_element_handles(
    page: Page,
) -> None:
    page.set_content("<body>hello</body>")
    with page.context.expect_event("console") as message_info:
        page.evaluate("() => console.log(document.body)")
    message = message_info.value
    body = message.args[0]
    assert body.evaluate("x => x.nodeName") == "BODY"
    must(body.as_element()).click()


def test_BC_034_console_event_should_work_in_popup(page: Page) -> None:
    with page.context.expect_event("console") as message_info:
        with page.expect_popup() as popup_info:
            page.evaluate(
                """() => {
                  const win = window.open('');
                  win.console.log('hello');
                }"""
            )
    message = message_info.value
    popup = popup_info.value

    assert message.text == "hello"
    assert message.page == popup


def test_BC_035_console_event_should_work_in_popup_2(
    page: Page, browser_name: str
) -> None:
    if browser_name == "firefox":
        pytest.skip(
            "fixme: console message from javascript: url is not reported at all"
        )

    with page.context.expect_event(
        "console", lambda msg: msg.type == "log"
    ) as message_info:
        with page.context.expect_event("page") as popup_info:
            page.evaluate(
                """async () => {
                  const win = window.open('javascript:console.log("hello")');
                  await new Promise(f => window.builtins.setTimeout(f, 0));
                  win.close();
                }"""
            )
    message = message_info.value
    popup = popup_info.value

    assert message.text == "hello"
    assert message.page == popup


def test_BC_036_console_event_should_work_in_immediately_closed_popup(
    page: Page, browser_name: str
) -> None:
    if browser_name == "firefox":
        pytest.skip("fixme: console message is not reported at all")

    with page.context.expect_event("console") as message_info:
        with page.expect_popup() as popup_info:
            page.evaluate(
                """async () => {
                  const win = window.open();
                  win.console.log('hello');
                  win.close();
                }"""
            )
    message = message_info.value
    popup = popup_info.value

    assert message.text == "hello"
    assert message.page == popup


def test_BC_037_dialog_event_should_work_smoke(
    page: Page, sync_gather: Callable[..., List[Any]]
) -> None:
    def run_prompt() -> Any:
        return page.evaluate("() => prompt('hey?')")

    def handle_dialog() -> None:
        with page.context.expect_event("dialog") as dialog1_info:
            with page.expect_event("dialog") as dialog2_info:
                pass
        dialog1 = dialog1_info.value
        dialog2 = dialog2_info.value

        assert dialog1 == dialog2
        assert dialog1.message == "hey?"
        assert dialog1.page == page
        dialog1.accept("hello")

    # Listen first: the driver dismisses a dialog that nobody listens for yet.
    [_, result] = sync_gather(handle_dialog, run_prompt)
    assert result == "hello"


def test_BC_038_dialogclosed_event_should_work(
    page: Page, sync_gather: Callable[..., List[Any]]
) -> None:
    def run_prompt() -> Any:
        return page.evaluate("() => prompt('hey?')")

    def handle_dialog() -> None:
        dialog = page.context.wait_for_event("dialog")
        with page.context.expect_event("dialogclosed") as closed1_info:
            with page.expect_event("dialogclosed") as closed2_info:
                dialog.accept("hello")
        assert closed1_info.value == dialog
        assert closed2_info.value == dialog

    # Listen first: the driver dismisses a dialog that nobody listens for yet.
    [_, result] = sync_gather(handle_dialog, run_prompt)
    assert result == "hello"


def test_BC_039_dialog_event_should_work_in_popup(
    page: Page, sync_gather: Callable[..., List[Any]]
) -> None:
    def run_prompt() -> Any:
        return page.evaluate(
            """() => {
              const win = window.open('');
              return win.prompt('hey?');
            }"""
        )

    def handle_dialog() -> None:
        with page.context.expect_event("dialog") as dialog_info:
            with page.expect_popup() as popup_info:
                pass
        dialog = dialog_info.value
        popup = popup_info.value

        assert dialog.message == "hey?"
        assert dialog.page == popup
        dialog.accept("hello")

    # Listen first: the driver dismisses a dialog that nobody listens for yet.
    [_, result] = sync_gather(handle_dialog, run_prompt)
    assert result == "hello"


def test_BC_040_dialog_event_should_work_in_popup_2(
    page: Page, browser_name: str, sync_gather: Callable[..., List[Any]]
) -> None:
    if browser_name == "firefox":
        pytest.skip("fixme: dialog from javascript: url is not reported at all")

    def open_popup() -> None:
        page.evaluate(
            """async () => {
              window.open('javascript:prompt("hey?")');
            }"""
        )

    def handle_dialog() -> None:
        dialog = page.context.wait_for_event("dialog")

        assert dialog.message == "hey?"
        assert dialog.page is None
        dialog.accept("hello")

    sync_gather(open_popup, handle_dialog)


def test_BC_041_dialog_event_should_work_in_immediately_closed_popup(
    page: Page, sync_gather: Callable[..., List[Any]]
) -> None:
    def run_prompt() -> Any:
        return page.evaluate(
            """async () => {
              const win = window.open();
              const result = win.prompt('hey?');
              win.close();
              return result;
            }"""
        )

    def handle_dialog() -> None:
        with page.context.expect_event("dialog") as dialog_info:
            with page.expect_popup() as popup_info:
                pass
        dialog = dialog_info.value
        popup = popup_info.value

        assert dialog.message == "hey?"
        assert dialog.page == popup
        dialog.accept("hello")

    # Listen first: the driver dismisses a dialog that nobody listens for yet.
    [_, result] = sync_gather(handle_dialog, run_prompt)
    assert result == "hello"


def test_BC_042_dialog_event_should_work_with_inline_script_tag(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    def handler(request: TestServerRequest) -> None:
        request.setHeader("content-type", "text/html")
        request.write(b"<script>window.result = prompt('hey?')</script>")
        request.finish()

    server.set_route("/popup.html", handler)

    page.goto(server.EMPTY_PAGE)
    page.set_content("<a href='popup.html' target=_blank>Click me</a>")

    def click() -> None:
        page.click("a")

    def handle_dialog() -> Page:
        with page.context.expect_event("dialog") as dialog_info:
            with page.context.expect_event("page") as popup_info:
                pass
        dialog = dialog_info.value
        popup = popup_info.value

        assert dialog.message == "hey?"
        assert dialog.page == popup
        dialog.accept("hello")
        return popup

    # Listen first: the driver dismisses a dialog that nobody listens for yet.
    [popup, _] = sync_gather(handle_dialog, click)
    poll_until_equal(lambda: popup.evaluate("window.result"), "hello")


def test_BC_043_weberror_event_should_work(page: Page) -> None:
    with page.context.expect_event("weberror") as web_error_info:
        page.set_content('<script>throw new Error("boom")</script>')
    web_error = web_error_info.value
    assert web_error.page == page
    assert "boom" in must(web_error.error.stack)


def test_BC_044_weberror_event_should_include_location(
    page: Page, server: Server
) -> None:
    def handle_error_js(request: TestServerRequest) -> None:
        request.setHeader("content-type", "application/javascript")
        request.write(
            b"""
      function foo() {
        throw new Error('boom');
      }
      foo();
    """
        )
        request.finish()

    server.set_route("/error.js", handle_error_js)

    def handle_error_html(request: TestServerRequest) -> None:
        request.setHeader("content-type", "text/html")
        request.write(b'<script src="/error.js"></script>')
        request.finish()

    server.set_route("/error.html", handle_error_html)

    with page.context.expect_event("weberror") as web_error_info:
        page.goto(server.PREFIX + "/error.html")
    web_error = web_error_info.value

    location = web_error.location
    assert location["url"] == f"{server.PREFIX}/error.js"
    assert location["line"] == 2
    # column is not consistent across browsers
    assert location["column"] > 0


def test_BC_045_pageload_event_should_work_smoke(page: Page, server: Server) -> None:
    with page.context.expect_event("pageload") as event_page_info:
        page.goto(server.EMPTY_PAGE)
    event_page = event_page_info.value
    assert event_page == page


def test_BC_046_framenavigated_event_should_work_smoke(
    page: Page, server: Server
) -> None:
    with page.context.expect_event("framenavigated") as frame_info:
        page.goto(server.EMPTY_PAGE)
    frame = frame_info.value
    assert frame == page.main_frame
    assert frame.url == server.EMPTY_PAGE


def test_BC_047_pageclose_event_should_work_smoke(
    context: BrowserContext,
) -> None:
    page = context.new_page()
    with context.expect_event("pageclose") as closed_info:
        page.close()
    closed = closed_info.value
    assert closed == page


def test_BC_048_frameattached_event_should_work_smoke(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    with page.context.expect_event("frameattached") as frame_info:
        page.evaluate(
            """() => {
              const iframe = document.createElement('iframe');
              iframe.src = 'about:blank';
              document.body.appendChild(iframe);
            }"""
        )
    frame = frame_info.value
    assert frame.parent_frame == page.main_frame


def test_BC_049_framedetached_event_should_work_smoke(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    page.evaluate(
        """() => {
          const iframe = document.createElement('iframe');
          iframe.id = 'x';
          iframe.src = 'about:blank';
          document.body.appendChild(iframe);
        }"""
    )
    page.wait_for_selector("iframe")
    with page.context.expect_event("framedetached") as frame_info:
        page.evaluate("() => document.getElementById('x').remove()")
    frame = frame_info.value
    assert frame.parent_frame == page.main_frame


def test_BC_050_download_event_should_work_smoke(page: Page, server: Server) -> None:
    def handler(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "application/octet-stream")
        request.setHeader("Content-Disposition", "attachment; filename=file.txt")
        request.write(b"Hello world")
        request.finish()

    server.set_route("/download", handler)
    page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    with page.context.expect_event("download") as download_info:
        page.click("a")
    download = download_info.value
    assert download.suggested_filename == "file.txt"
    assert download.page == page
