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

"""Port of tests/library/browsercontext-locale.spec.ts."""

import asyncio

import pytest

from playwright.async_api import Browser, BrowserContext
from tests.server import Server


async def test_LC_001_should_affect_accept_language_header_smoke(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context(locale="fr-CH")
    page = await context.new_page()
    with server.expect_request("/empty.html") as request_info:
        await page.goto(server.EMPTY_PAGE)
    request = request_info.value
    accept_language = request.getHeader("accept-language")
    assert accept_language
    assert accept_language[0:5] == "fr-CH"
    await context.close()


async def test_LC_002_should_affect_navigator_language(browser: Browser) -> None:
    context = await browser.new_context(locale="fr-FR")
    page = await context.new_page()
    assert await page.evaluate("() => navigator.language") == "fr-FR"
    await context.close()


async def test_LC_003_should_format_number(browser: Browser, server: Server) -> None:
    context = await browser.new_context(locale="en-US")
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    assert await page.evaluate("() => (1000000.50).toLocaleString()") == "1,000,000.5"
    await context.close()

    context = await browser.new_context(locale="fr-FR")
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    assert (
        await page.evaluate("() => (1000000.50).toLocaleString().replace(/\\s/g, ' ')")
        == "1 000 000,5"
    )
    await context.close()


async def test_LC_004_should_format_date(
    browser: Browser, server: Server, browser_name: str
) -> None:
    context = await browser.new_context(
        locale="en-US", timezone_id="America/Los_Angeles"
    )
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    formatted = "Sat Nov 19 2016 10:12:34 GMT-0800 (Pacific Standard Time)"
    assert await page.evaluate("() => new Date(1479579154987).toString()") == formatted
    await context.close()

    context = await browser.new_context(locale="de-DE", timezone_id="Europe/Berlin")
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    formatted = "Sat Nov 19 2016 19:12:34 GMT+0100 (Mitteleuropäische Normalzeit)"
    assert await page.evaluate("() => new Date(1479579154987).toString()") == formatted
    await context.close()


async def test_LC_005_should_format_number_in_popups(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context(locale="fr-FR")
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)

    async with page.expect_popup() as popup_info:
        await page.evaluate(
            "url => window.open(url)", server.PREFIX + "/formatted-number.html"
        )
    popup = await popup_info.value
    await popup.wait_for_load_state("domcontentloaded")
    result = await popup.evaluate('window["result"]')
    assert result == "1 000 000,5"
    await context.close()


async def test_LC_006_should_affect_navigator_language_in_popups(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context(locale="fr-FR")
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_popup() as popup_info:
        await page.evaluate(
            "url => window.open(url)", server.PREFIX + "/formatted-number.html"
        )
    popup = await popup_info.value
    await popup.wait_for_load_state("domcontentloaded")
    result = await popup.evaluate("window.initialNavigatorLanguage")
    assert result == "fr-FR"
    await context.close()


async def test_LC_007_should_work_for_multiple_pages_sharing_same_process(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context(locale="ru-RU")
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_popup() as popup_info:
        await page.evaluate("url => { window.open(url); }", server.EMPTY_PAGE)
    popup = await popup_info.value
    async with popup.expect_popup() as popup_info:
        await popup.evaluate("url => { window.open(url); }", server.EMPTY_PAGE)
    popup = await popup_info.value
    await context.close()


async def test_LC_008_should_be_isolated_between_contexts(
    browser: Browser, server: Server
) -> None:
    context1 = await browser.new_context(locale="en-US")
    # By default firefox limits number of child web processes to 8.
    await asyncio.gather(*[context1.new_page() for _ in range(8)])

    context2 = await browser.new_context(locale="ru-RU")
    page2 = await context2.new_page()

    locale_number = "() => (1000000.50).toLocaleString()"
    numbers = await asyncio.gather(
        *[page.evaluate(locale_number) for page in context1.pages]
    )

    for value in numbers:
        assert value == "1,000,000.5"
    assert await page2.evaluate(locale_number) == "1\u00a0000\u00a0000,5"

    await asyncio.gather(context1.close(), context2.close())


async def get_context_locale(context: BrowserContext) -> str:
    page = await context.new_page()
    return await page.evaluate(
        "() => (new Intl.NumberFormat()).resolvedOptions().locale"
    )


async def test_LC_009_should_not_change_default_locale_in_another_context(
    browser: Browser,
) -> None:
    context = await browser.new_context()
    default_locale = await get_context_locale(context)
    await context.close()

    locale_override = "de-DE" if default_locale == "es-MX" else "es-MX"
    context = await browser.new_context(locale=locale_override)
    assert await get_context_locale(context) == locale_override
    await context.close()

    context = await browser.new_context()
    assert await get_context_locale(context) == default_locale
    await context.close()


async def test_LC_010_should_propagate_locale_to_workers(
    browser: Browser, browser_name: str, server: Server
) -> None:
    context = await browser.new_context(locale="ru-RU")
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_console_message(
        lambda e: e.text.startswith("locale:")
    ) as msg_info:
        await page.evaluate(
            """() => new Worker(URL.createObjectURL(new Blob(['console.log("locale:" + Intl.NumberFormat().resolvedOptions().locale)'], { type: 'application/javascript' })))"""
        )
    msg = await msg_info.value
    if browser_name == "webkit":
        # Webkit on Ubuntu is "ru-RU", and on other platforms is "ru"
        assert "locale:ru" in msg.text
    else:
        assert msg.text == "locale:ru-RU"
    await context.close()


async def test_LC_011_should_affect_intl_date_time_format_resolved_options_locale(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context(locale="en-GB")
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    assert (
        await page.evaluate(
            "() => (new Intl.DateTimeFormat()).resolvedOptions().locale"
        )
        == "en-GB"
    )
    await context.close()


async def test_LC_012_should_send_user_accept_language_header(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context(locale="en-GB")
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)

    with server.expect_request("/empty.html") as req_info:
        await page.evaluate(
            """async url => {
      await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          'Accept-Language': 'de'
        },
      });
    }""",
            server.EMPTY_PAGE,
        )
    req = req_info.value
    assert req.getHeader("accept-language") == "de"

    with server.expect_request("/empty.html") as req_info:
        await page.evaluate(
            """async url => {
      await fetch(url, {
        headers: {
          'Content-Type': 'application/json'
        },
      });
    }""",
            server.EMPTY_PAGE,
        )
    req = req_info.value
    assert "en-GB" in (req.getHeader("accept-language") or "")
    await context.close()


async def test_LC_013_should_send_accept_language_header_on_web_socket_handshake(
    browser: Browser, server: Server, browser_name: str, browser_major_version: int
) -> None:
    if browser_name == "chromium" and browser_major_version < 151:
        pytest.skip(
            "fixme: Chromium before 151 sends the browser Accept-Language instead of the emulated locale on WebSocket handshake"
        )

    context = await browser.new_context(locale="en-GB")
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    req_promise = asyncio.create_task(server.wait_for_request("/ws"))
    await page.evaluate(
        "port => { new WebSocket(`ws://localhost:${port}/ws`); }", server.PORT
    )
    req = await req_promise
    assert "en-GB" in (req.getHeader("accept-language") or "")
    await context.close()


async def test_LC_014_should_send_accept_language_header_on_web_socket_handshake_from_a_worker(
    browser: Browser, server: Server, browser_name: str, browser_major_version: int
) -> None:
    if browser_name == "chromium" and browser_major_version < 151:
        pytest.skip(
            "fixme: Chromium before 151 sends the browser Accept-Language instead of the emulated locale on WebSocket handshake"
        )

    context = await browser.new_context(locale="en-GB")
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    req_promise = asyncio.create_task(server.wait_for_request("/ws"))
    await page.evaluate(
        """port => {
    const code = `new WebSocket(${JSON.stringify(`ws://localhost:${port}/ws`)});`;
    new Worker(URL.createObjectURL(new Blob([code], { type: 'text/javascript' })));
  }""",
        server.PORT,
    )
    req = await req_promise
    assert "en-GB" in (req.getHeader("accept-language") or "")
    await context.close()
