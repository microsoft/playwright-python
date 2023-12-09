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

from typing import Optional

import pytest

from playwright.sync_api import Dialog, Page

from ..server import Server, TestServerRequest


def test_console_event_should_work(page: Page) -> None:
    with page.context.expect_console_message() as console_info:
        page.evaluate("() => console.log('hello')")
    message = console_info.value
    assert message.text == "hello"
    assert message.page == page


def test_console_event_should_work_in_popup(page: Page) -> None:
    with page.context.expect_console_message() as console_info:
        with page.expect_popup() as popup_info:
            page.evaluate(
                """() => {
                const win = window.open('');
                win.console.log('hello');
                }"""
            )
    message = console_info.value
    popup = popup_info.value
    assert message.text == "hello"
    assert message.page == popup


# console message from javascript: url is not reported at all
@pytest.mark.skip_browser("firefox")
def test_console_event_should_work_in_popup_2(page: Page, browser_name: str) -> None:
    with page.context.expect_console_message(
        lambda msg: msg.type == "log"
    ) as console_info:
        with page.context.expect_page() as page_info:
            page.evaluate(
                """async () => {
                const win = window.open('javascript:console.log("hello")');
                await new Promise(f => setTimeout(f, 0));
                win.close();
            }"""
            )
    message = console_info.value
    popup = page_info.value
    assert message.text == "hello"
    assert message.page == popup


# console message from javascript: url is not reported at all
@pytest.mark.skip_browser("firefox")
def test_console_event_should_work_in_immediately_closed_popup(
    page: Page, browser_name: str
) -> None:
    with page.context.expect_console_message(
        lambda msg: msg.type == "log"
    ) as console_info:
        with page.context.expect_page() as page_info:
            page.evaluate(
                """() => {
                const win = window.open('');
                win.console.log('hello');
                win.close();
            }"""
            )
    message = console_info.value
    popup = page_info.value
    assert message.text == "hello"
    assert message.page == popup


def test_dialog_event_should_work1(page: Page) -> None:
    dialog1: Optional[Dialog] = None

    def handle_page_dialog(dialog: Dialog) -> None:
        nonlocal dialog1
        dialog1 = dialog
        dialog.accept("hello")

    page.on("dialog", handle_page_dialog)

    dialog2: Optional[Dialog] = None

    def handle_context_dialog(dialog: Dialog) -> None:
        nonlocal dialog2
        dialog2 = dialog

    page.context.on("dialog", handle_context_dialog)

    assert page.evaluate("() => prompt('hey?')") == "hello"
    assert dialog1
    assert dialog1 == dialog2
    assert dialog1.message == "hey?"
    assert dialog1.page == page


def test_dialog_event_should_work_in_popup1(page: Page) -> None:
    dialog: Optional[Dialog] = None

    def handle_dialog(d: Dialog) -> None:
        nonlocal dialog
        dialog = d
        dialog.accept("hello")

    page.context.on("dialog", handle_dialog)

    with page.expect_popup() as popup_info:
        assert page.evaluate("() => window.open('').prompt('hey?')") == "hello"
    popup = popup_info.value
    assert dialog
    assert dialog.message == "hey?"
    assert dialog.page == popup


# console message from javascript: url is not reported at all
@pytest.mark.skip_browser("firefox")
def test_dialog_event_should_work_in_popup_2(page: Page, browser_name: str) -> None:
    def handle_dialog(dialog: Dialog) -> None:
        assert dialog.message == "hey?"
        assert dialog.page is None
        dialog.accept("hello")

    page.context.on("dialog", handle_dialog)

    assert page.evaluate("() => window.open('javascript:prompt(\"hey?\")')")


# console message from javascript: url is not reported at all
@pytest.mark.skip_browser("firefox")
def test_dialog_event_should_work_in_immdiately_closed_popup(page: Page) -> None:
    popup = None

    def handle_popup(p: Page) -> None:
        nonlocal popup
        popup = p

    page.on("popup", handle_popup)

    with page.context.expect_console_message() as console_info:
        page.evaluate(
            """() => {
                const win = window.open();
                win.console.log('hello');
                win.close();
            }"""
        )
    message = console_info.value

    assert message.text == "hello"
    assert message.page == popup


def test_dialog_event_should_work_with_inline_script_tag(
    page: Page, server: Server
) -> None:
    def handle_route(request: TestServerRequest) -> None:
        request.setHeader("content-type", "text/html")
        request.write(b"""<script>window.result = prompt('hey?')</script>""")
        request.finish()

    server.set_route("/popup.html", handle_route)
    page.goto(server.EMPTY_PAGE)
    page.set_content("<a href='popup.html' target=_blank>Click me</a>")

    def handle_dialog(dialog: Dialog) -> None:
        assert dialog.message == "hey?"
        assert dialog.page == popup
        dialog.accept("hello")

    page.context.on("dialog", handle_dialog)

    with page.expect_popup() as popup_info:
        page.click("a")
    popup = popup_info.value
    assert popup.evaluate("window.result") == "hello"


def test_console_event_should_work_with_context_manager(page: Page) -> None:
    with page.context.expect_console_message() as cm_info:
        page.evaluate("() => console.log('hello')")
    message = cm_info.value
    assert message.text == "hello"
    assert message.page == page
