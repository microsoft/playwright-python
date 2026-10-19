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

import asyncio
from typing import Dict

from playwright.async_api import BrowserContext, BrowserType, Dialog, Page, expect
from tests.server import Server


async def test_BU_001_should_close_browser_with_beforeunload_page(
    server: Server, browser_type: BrowserType, launch_arguments: Dict
) -> None:
    browser = await browser_type.launch(**launch_arguments)
    page = await browser.new_page()
    await page.goto(server.PREFIX + "/beforeunload.html")
    # We have to interact with a page so that 'beforeunload' handlers
    # fire.
    await page.click("body")
    await browser.close()


async def test_BU_002_should_close_browsercontext_with_beforeunload_page(
    server: Server, page: Page, context: BrowserContext
) -> None:
    await page.goto(server.PREFIX + "/beforeunload.html")
    # We have to interact with a page so that 'beforeunload' handlers
    # fire.
    await page.click("body")
    await context.close()


async def test_BU_003_should_be_able_to_navigate_away_from_page_with_beforeunload(
    server: Server, page: Page, context: BrowserContext
) -> None:
    await page.goto(server.PREFIX + "/beforeunload.html")
    # We have to interact with a page so that 'beforeunload' handlers
    # fire.
    await page.click("body")
    await page.goto(server.EMPTY_PAGE)


async def test_BU_004_should_close_page_with_beforeunload_listener(
    context: BrowserContext, server: Server
) -> None:
    new_page = await context.new_page()
    await new_page.goto(server.PREFIX + "/beforeunload.html")
    # We have to interact with a page so that 'beforeunload' handlers
    # fire.
    await new_page.click("body")
    await new_page.close()


async def test_BU_005_should_run_beforeunload_if_asked_for_smoke(
    context: BrowserContext, server: Server, browser_name: str
) -> None:
    new_page = await context.new_page()
    await new_page.goto(server.PREFIX + "/beforeunload.html")
    # We have to interact with a page so that 'beforeunload' handlers
    # fire.
    await new_page.click("body")
    async with new_page.expect_event("dialog") as dialog_info:
        await new_page.close(run_before_unload=True)
    dialog = await dialog_info.value
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
    async with new_page.expect_event("close"):
        await dialog.accept()


async def test_BU_006_should_access_page_after_beforeunload(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/beforeunload.html")
    # We have to interact with a page so that 'beforeunload' handlers
    # fire.
    await page.click("body")
    async with page.expect_event("dialog") as dialog_info:
        await page.close(run_before_unload=True)
    dialog = await dialog_info.value
    await dialog.dismiss()
    await page.evaluate("() => document.title")


async def test_BU_007_should_not_stall_on_evaluate_when_dismissing_beforeunload(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/beforeunload.html")
    # We have to interact with a page so that 'beforeunload' handlers fire.
    await page.click("body")

    async def dismiss_dialog() -> None:
        dialog = await page.wait_for_event("dialog")
        await dialog.dismiss()

    await asyncio.gather(
        dismiss_dialog(),
        page.evaluate(
            """() => {
                window.location.reload();
            }"""
        ),
    )


async def test_BU_008_should_not_stall_on_click_when_dismissing_beforeunload(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        f'<a href="{server.PREFIX}/frames/one-frame.html">click me</a>'
    )

    await page.evaluate(
        """() => {
            window.onbeforeunload = () => false;
        }"""
    )

    async def on_dialog(dialog: Dialog) -> None:
        await dialog.dismiss()

    page.on("dialog", on_dialog)

    await page.get_by_role("link").click(no_wait_after=True)
    await page.evaluate(
        """() => {
            window.onbeforeunload = null;
        }"""
    )

    # This line should not timeout.
    await page.get_by_role("link").click(timeout=5000)
    await expect(page).to_have_url(server.PREFIX + "/frames/one-frame.html")


async def test_BU_009_should_support_dismissing_the_dialog_multiple_times(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/beforeunload.html")

    # We have to interact with a page so that 'beforeunload' handlers
    # fire (in Firefox).
    await page.click("body")

    async with page.expect_event("dialog") as dialog_info:
        await page.close(run_before_unload=True)
    dialog = await dialog_info.value

    await dialog.dismiss()

    async with page.expect_event("dialog") as dialog_info2:
        await page.close(run_before_unload=True)
    dialog2 = await dialog_info2.value

    await dialog2.dismiss()


async def test_BU_010_should_support_closing_the_page_after_a_previous_dismiss(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/beforeunload.html")

    # We have to interact with a page so that 'beforeunload' handlers
    # fire (in Firefox).
    await page.click("body")

    async with page.expect_event("dialog") as dialog_info:
        await page.close(run_before_unload=True)
    dialog = await dialog_info.value

    await dialog.dismiss()

    await page.close()
    assert page.is_closed() is True


async def test_BU_011_should_support_closing_the_page_via_a_subsequent_onbeforeunload_dialog(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/beforeunload.html")

    # We have to interact with a page so that 'beforeunload' handlers
    # fire (in Firefox).
    await page.click("body")

    async with page.expect_event("dialog") as dialog_info:
        await page.close(run_before_unload=True)
    dialog = await dialog_info.value

    async with page.expect_event("close"):
        await dialog.accept()
    assert page.is_closed() is True


async def test_BU_012_does_not_get_stalled_by_before_unload(
    page: Page, server: Server
) -> None:
    # Upstream's server.HELLO_WORLD.
    await page.goto(server.PREFIX + "/hello-world")

    await page.evaluate(
        """() => {
            window.addEventListener('beforeunload', event => {
                event.preventDefault();
            });
        }"""
    )

    async def on_dialog(dialog: Dialog) -> None:
        await dialog.dismiss()

    page.on("dialog", on_dialog)

    # We have to interact with a page so that 'beforeunload' handlers
    # fire.
    await page.click("body")

    await page.route("**/api", lambda route: route.fulfill(status=200, body="ok"))
    await page.evaluate("async () => fetch(new URL('/api', window.location.href))")

    await page.close(run_before_unload=True)

    await page.evaluate("async () => fetch(new URL('/api', window.location.href))")
