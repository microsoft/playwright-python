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

"""Port of tests/library/beforeunload.spec.ts."""

from typing import Callable, Dict

from playwright.sync_api import BrowserContext, BrowserType, Dialog, Page, expect
from tests.server import Server


def test_BU_001_should_close_browser_with_beforeunload_page(
    server: Server, browser_type: BrowserType, launch_arguments: Dict
) -> None:
    browser = browser_type.launch(**launch_arguments)
    page = browser.new_page()
    page.goto(server.PREFIX + "/beforeunload.html")
    # We have to interact with a page so that 'beforeunload' handlers
    # fire.
    page.click("body")
    browser.close()


def test_BU_002_should_close_browsercontext_with_beforeunload_page(
    server: Server, page: Page, context: BrowserContext
) -> None:
    page.goto(server.PREFIX + "/beforeunload.html")
    # We have to interact with a page so that 'beforeunload' handlers
    # fire.
    page.click("body")
    context.close()


def test_BU_003_should_be_able_to_navigate_away_from_page_with_beforeunload(
    server: Server, page: Page, context: BrowserContext
) -> None:
    page.goto(server.PREFIX + "/beforeunload.html")
    # We have to interact with a page so that 'beforeunload' handlers
    # fire.
    page.click("body")
    page.goto(server.EMPTY_PAGE)


def test_BU_004_should_close_page_with_beforeunload_listener(
    context: BrowserContext, server: Server
) -> None:
    new_page = context.new_page()
    new_page.goto(server.PREFIX + "/beforeunload.html")
    # We have to interact with a page so that 'beforeunload' handlers
    # fire.
    new_page.click("body")
    new_page.close()


def test_BU_005_should_run_beforeunload_if_asked_for_smoke(
    context: BrowserContext, server: Server, browser_name: str
) -> None:
    new_page = context.new_page()
    new_page.goto(server.PREFIX + "/beforeunload.html")
    # We have to interact with a page so that 'beforeunload' handlers
    # fire.
    new_page.click("body")
    with new_page.expect_event("dialog") as dialog_info:
        new_page.close(run_before_unload=True)
    dialog = dialog_info.value
    assert dialog.type == "beforeunload"
    assert dialog.default_value == ""
    if browser_name == "chromium":
        assert dialog.message == ""
    elif browser_name == "webkit":
        assert dialog.message == "Leave?"
    else:
        assert (
            "This page is asking you to confirm that you want to leave"
            in dialog.message
        )
    with new_page.expect_event("close"):
        dialog.accept()


def test_BU_006_should_access_page_after_beforeunload(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/beforeunload.html")
    # We have to interact with a page so that 'beforeunload' handlers
    # fire.
    page.click("body")
    with page.expect_event("dialog") as dialog_info:
        page.close(run_before_unload=True)
    dialog = dialog_info.value
    dialog.dismiss()
    page.evaluate("() => document.title")


def test_BU_007_should_not_stall_on_evaluate_when_dismissing_beforeunload(
    page: Page, server: Server, sync_gather: Callable
) -> None:
    page.goto(server.PREFIX + "/beforeunload.html")
    # We have to interact with a page so that 'beforeunload' handlers fire.
    page.click("body")

    def dismiss_dialog() -> None:
        dialog = page.wait_for_event("dialog")
        dialog.dismiss()

    sync_gather(
        dismiss_dialog,
        lambda: page.evaluate(
            """() => {
                window.location.reload();
            }"""
        ),
    )


def test_BU_008_should_not_stall_on_click_when_dismissing_beforeunload(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content(f'<a href="{server.PREFIX}/frames/one-frame.html">click me</a>')

    page.evaluate(
        """() => {
            window.onbeforeunload = () => false;
        }"""
    )

    def on_dialog(dialog: Dialog) -> None:
        dialog.dismiss()

    page.on("dialog", on_dialog)

    page.get_by_role("link").click(no_wait_after=True)
    page.evaluate(
        """() => {
            window.onbeforeunload = null;
        }"""
    )

    # This line should not timeout.
    page.get_by_role("link").click(timeout=5000)
    expect(page).to_have_url(server.PREFIX + "/frames/one-frame.html")


def test_BU_009_should_support_dismissing_the_dialog_multiple_times(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/beforeunload.html")

    # We have to interact with a page so that 'beforeunload' handlers
    # fire (in Firefox).
    page.click("body")

    with page.expect_event("dialog") as dialog_info:
        page.close(run_before_unload=True)
    dialog = dialog_info.value

    dialog.dismiss()

    with page.expect_event("dialog") as dialog_info2:
        page.close(run_before_unload=True)
    dialog2 = dialog_info2.value

    dialog2.dismiss()


def test_BU_010_should_support_closing_the_page_after_a_previous_dismiss(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/beforeunload.html")

    # We have to interact with a page so that 'beforeunload' handlers
    # fire (in Firefox).
    page.click("body")

    with page.expect_event("dialog") as dialog_info:
        page.close(run_before_unload=True)
    dialog = dialog_info.value

    dialog.dismiss()

    page.close()
    assert page.is_closed() is True


def test_BU_011_should_support_closing_the_page_via_a_subsequent_onbeforeunload_dialog(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/beforeunload.html")

    # We have to interact with a page so that 'beforeunload' handlers
    # fire (in Firefox).
    page.click("body")

    with page.expect_event("dialog") as dialog_info:
        page.close(run_before_unload=True)
    dialog = dialog_info.value

    with page.expect_event("close"):
        dialog.accept()
    assert page.is_closed() is True


def test_BU_012_does_not_get_stalled_by_before_unload(
    page: Page, server: Server
) -> None:
    # Upstream's server.HELLO_WORLD.
    page.goto(server.PREFIX + "/hello-world")

    page.evaluate(
        """() => {
            window.addEventListener('beforeunload', event => {
                event.preventDefault();
            });
        }"""
    )

    def on_dialog(dialog: Dialog) -> None:
        dialog.dismiss()

    page.on("dialog", on_dialog)

    # We have to interact with a page so that 'beforeunload' handlers
    # fire.
    page.click("body")

    page.route("**/api", lambda route: route.fulfill(status=200, body="ok"))
    page.evaluate("async () => fetch(new URL('/api', window.location.href))")

    page.close(run_before_unload=True)

    page.evaluate("async () => fetch(new URL('/api', window.location.href))")
