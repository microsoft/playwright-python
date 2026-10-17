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

"""Port of tests/page/page-event-popup.spec.ts."""


import asyncio

from playwright.async_api import Page
from tests.server import Server


async def test_PO_001_should_work_smoke(page: Page) -> None:
    async with page.expect_popup() as popup_info:
        await page.evaluate("() => window['__popup'] = window.open('about:blank')")
    popup = await popup_info.value
    assert await page.evaluate("() => !!window.opener") is False
    assert await popup.evaluate("() => !!window.opener") is True


async def test_PO_002_should_work_with_window_features(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_popup() as popup_info:
        await page.evaluate(
            "() => window['__popup'] = window.open(window.location.href, 'Title', 'toolbar=no,location=no,directories=no,status=no,menubar=no,scrollbars=yes,resizable=yes,width=780,height=200,top=0,left=0')"
        )
    popup = await popup_info.value
    assert await page.evaluate("() => !!window.opener") is False
    assert await popup.evaluate("() => !!window.opener") is True


async def test_PO_003_should_emit_for_immediately_closed_popups(page: Page) -> None:
    async with page.expect_popup() as popup_info:
        await page.evaluate(
            """() => {
      const win = window.open('about:blank');
      win.close();
    }"""
        )
    popup = await popup_info.value
    assert popup


async def test_PO_004_should_emit_for_immediately_closed_popups_2(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_popup() as popup_info:
        await page.evaluate(
            """() => {
      const win = window.open(window.location.href);
      win.close();
    }"""
        )
    popup = await popup_info.value
    assert popup


async def test_PO_005_should_be_able_to_capture_alert(page: Page) -> None:
    async with page.expect_popup() as popup_info:
        async with page.context.expect_event("dialog") as dialog_info:
            evaluate_task = asyncio.create_task(
                page.evaluate(
                    """() => {
      const win = window.open('');
      win.alert('hello');
    }"""
                )
            )
    popup = await popup_info.value
    dialog = await dialog_info.value
    assert dialog.message == "hello"
    assert dialog.page == popup
    await dialog.dismiss()
    await evaluate_task


async def test_PO_006_should_work_with_empty_url(page: Page) -> None:
    async with page.expect_popup() as popup_info:
        await page.evaluate("() => window['__popup'] = window.open('')")
    popup = await popup_info.value
    assert await page.evaluate("() => !!window.opener") is False
    assert await popup.evaluate("() => !!window.opener") is True


async def test_PO_007_should_work_with_noopener_and_no_url(page: Page) -> None:
    async with page.expect_popup() as popup_info:
        await page.evaluate(
            "() => window['__popup'] = window.open(undefined, null, 'noopener')"
        )
    popup = await popup_info.value
    # Chromium reports `about:blank#blocked` here.
    assert popup.url.split("#")[0] == "about:blank"
    assert await page.evaluate("() => !!window.opener") is False
    assert await popup.evaluate("() => !!window.opener") is False


async def test_PO_008_should_work_with_noopener_and_about_blank(page: Page) -> None:
    async with page.expect_popup() as popup_info:
        await page.evaluate(
            "() => window['__popup'] = window.open('about:blank', null, 'noopener')"
        )
    popup = await popup_info.value
    assert await page.evaluate("() => !!window.opener") is False
    assert await popup.evaluate("() => !!window.opener") is False


async def test_PO_009_should_work_with_noopener_and_url(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_popup() as popup_info:
        await page.evaluate(
            "url => window['__popup'] = window.open(url, null, 'noopener')",
            server.EMPTY_PAGE,
        )
    popup = await popup_info.value
    assert await page.evaluate("() => !!window.opener") is False
    assert await popup.evaluate("() => !!window.opener") is False


async def test_PO_010_should_work_with_clicking_target_blank(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        '<a target=_blank rel="opener" href="/one-style.html">yo</a>'
    )
    async with page.expect_popup() as popup_info:
        await page.click("a")
    popup = await popup_info.value
    assert await page.evaluate("() => !!window.opener") is False
    assert await popup.evaluate("() => !!window.opener") is True
    assert popup.main_frame.page == popup


async def test_PO_011_should_work_with_fake_clicking_target_blank_and_rel_noopener(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        '<a target=_blank rel=noopener href="/one-style.html">yo</a>'
    )
    async with page.expect_popup() as popup_info:
        await page.eval_on_selector("a", "a => a.click()")
    popup = await popup_info.value
    assert await page.evaluate("() => !!window.opener") is False
    assert await popup.evaluate("() => !!window.opener") is False


async def test_PO_012_should_work_with_clicking_target_blank_and_rel_noopener(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        '<a target=_blank rel=noopener href="/one-style.html">yo</a>'
    )
    async with page.expect_popup() as popup_info:
        await page.click("a")
    popup = await popup_info.value
    assert await page.evaluate("() => !!window.opener") is False
    assert await popup.evaluate("() => !!window.opener") is False


async def test_PO_013_should_report_popup_opened_from_iframes(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/frames/two-frames.html")
    frame = page.frames[1]
    assert frame
    async with page.expect_popup() as popup_info:
        await frame.evaluate("() => window.open('')")
    popup = await popup_info.value
    assert popup
