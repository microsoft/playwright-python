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

"""Port of tests/library/browsercontext-timezone-id.spec.ts."""

from typing import Optional

from playwright.async_api import Browser, BrowserContext, Error
from tests.server import Server


async def test_TZ_001_should_work_smoke(browser: Browser, browser_name: str) -> None:
    # Note: timezone names are rendered differently between browsers and platforms,
    # so we only check the GMT offset.
    func = "() => new Date(1479579154987).toString()"
    context = await browser.new_context(locale="en-US", timezone_id="America/Jamaica")
    page = await context.new_page()
    assert "Sat Nov 19 2016 13:12:34 GMT-0500" in await page.evaluate(func)
    await context.close()

    context = await browser.new_context(locale="en-US", timezone_id="Pacific/Honolulu")
    page = await context.new_page()
    assert "Sat Nov 19 2016 08:12:34 GMT-1000" in await page.evaluate(func)
    await context.close()

    context = await browser.new_context(
        locale="en-US",
        timezone_id=(
            "America/Argentina/Buenos_Aires"
            if browser_name == "firefox"
            else "America/Buenos_Aires"
        ),
    )
    page = await context.new_page()
    assert "Sat Nov 19 2016 15:12:34 GMT-0300" in await page.evaluate(func)
    await context.close()

    context = await browser.new_context(locale="en-US", timezone_id="Europe/Berlin")
    page = await context.new_page()
    assert "Sat Nov 19 2016 19:12:34 GMT+0100" in await page.evaluate(func)
    await context.close()


async def test_TZ_002_should_throw_for_invalid_timezone_i_ds_when_creating_pages(
    browser: Browser,
) -> None:
    for timezone_id in ["Foo/Bar", "Baz/Qux"]:
        error: Optional[Error] = None
        context: Optional[BrowserContext] = None
        try:
            context = await browser.new_context(timezone_id=timezone_id)
            await context.new_page()
        except Error as e:
            error = e
        assert error
        assert f"Invalid timezone ID: {timezone_id}" in error.message
        if context:
            await context.close()


async def test_TZ_003_should_work_for_multiple_pages_sharing_same_process(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context(timezone_id="Europe/Moscow")
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_popup() as popup_info:
        await page.evaluate("url => { window.open(url); }", server.EMPTY_PAGE)
    popup = await popup_info.value
    async with popup.expect_popup() as popup_info:
        await popup.evaluate("url => { window.open(url); }", server.EMPTY_PAGE)
    popup = await popup_info.value
    await context.close()


async def get_context_timezone(context: BrowserContext) -> str:
    page = await context.new_page()
    return await page.evaluate("() => Intl.DateTimeFormat().resolvedOptions().timeZone")


async def test_TZ_004_should_not_change_default_timezone_in_another_context(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()
    default_timezone = await get_context_timezone(context)
    await context.close()

    timezone_override = (
        "America/Los_Angeles"
        if default_timezone == "Europe/Moscow"
        else "Europe/Moscow"
    )
    context = await browser.new_context(timezone_id=timezone_override)
    assert await get_context_timezone(context) == timezone_override
    await context.close()

    context = await browser.new_context()
    assert await get_context_timezone(context) == default_timezone
    await context.close()


async def test_TZ_005_should_affect_intl_date_time_format_resolved_options_time_zone(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context(timezone_id="America/Jamaica")
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    assert (
        await page.evaluate(
            "() => (new Intl.DateTimeFormat()).resolvedOptions().timeZone"
        )
        == "America/Jamaica"
    )
    await context.close()


async def test_TZ_006_should_propagate_timezone_to_workers(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context(timezone_id="America/Jamaica")
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_console_message() as msg_info:
        await page.evaluate(
            "() => new Worker(URL.createObjectURL(new Blob(['console.log(Intl.DateTimeFormat().resolvedOptions().timeZone)'], { type: 'application/javascript' })))"
        )
    msg = await msg_info.value
    assert msg.text == "America/Jamaica"
    await context.close()
