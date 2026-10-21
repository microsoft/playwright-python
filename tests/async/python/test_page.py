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

"""Python only: tests of behaviors that no upstream test covers."""

from typing import Any, AsyncGenerator, Dict

import pytest

from playwright.async_api import (
    BrowserContext,
    Error,
    Page,
    TimeoutError,
    async_playwright,
)
from tests.server import Server


async def test_wait_for_request_should_work_with_predicate(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_request(
        lambda request: request.url == server.PREFIX + "/digits/2.png"
    ) as request_info:
        await page.evaluate(
            """() => {
                fetch('/digits/1.png')
                fetch('/digits/2.png')
                fetch('/digits/3.png')
            }"""
        )
    request = await request_info.value
    assert request.url == server.PREFIX + "/digits/2.png"


async def test_expect_response_should_reject_when_async_predicate_throws(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)

    async def predicate(response: Any) -> bool:
        raise Exception("Async oops!")

    with pytest.raises(Exception, match="Async oops!"):
        async with page.expect_response(predicate):
            await page.evaluate("() => fetch('/digits/1.png')")


async def test_expect_response_should_reject_when_sync_predicate_throws(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)

    def predicate(response: Any) -> bool:
        raise Exception("Sync oops!")

    with pytest.raises(Exception, match="Sync oops!"):
        async with page.expect_response(predicate):
            await page.evaluate("() => fetch('/digits/1.png')")


async def test_wait_for_response_should_use_context_timeout(
    page: Page, context: BrowserContext, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)

    context.set_default_timeout(1_000)
    with pytest.raises(Error) as exc_info:
        async with page.expect_response("https://playwright.dev"):
            pass
    assert exc_info.type is TimeoutError
    assert "Timeout 1000ms exceeded" in exc_info.value.message


async def test_expect_response_should_not_hang_when_predicate_throws(
    page: Page,
) -> None:
    with pytest.raises(Exception, match="Oops!"):
        async with page.expect_response("**/*"):
            raise Exception("Oops!")


@pytest.fixture
async def page_outside_test_mode(
    monkeypatch: pytest.MonkeyPatch, browser_name: str, launch_arguments: Dict
) -> AsyncGenerator[Page, None]:
    """A page from a driver that does not run in upstream's test mode.

    In test mode (PWTEST_UNDER_TEST=1, set by tests/conftest.py) the driver enables
    the debugger, so page.pause() waits even when the browser is headless.
    """
    monkeypatch.delenv("PWTEST_UNDER_TEST", raising=False)
    async with async_playwright() as playwright:
        browser = await playwright[browser_name].launch(**launch_arguments)
        yield await browser.new_page()
        await browser.close()


@pytest.mark.slow
async def test_page_pause_should_reset_default_timeouts(
    page_outside_test_mode: Page, headless: bool, server: Server
) -> None:
    if not headless:
        pytest.skip()

    page = page_outside_test_mode
    await page.goto(server.EMPTY_PAGE)
    await page.pause()
    with pytest.raises(Error, match="Timeout 30000ms exceeded."):
        await page.get_by_text("foo").click()


@pytest.mark.slow
async def test_page_pause_should_reset_custom_timeouts(
    page_outside_test_mode: Page, headless: bool, server: Server
) -> None:
    if not headless:
        pytest.skip()

    page = page_outside_test_mode
    # Navigate before the short timeouts apply: a slow machine can take over 456ms.
    await page.goto(server.EMPTY_PAGE)
    page.set_default_timeout(123)
    page.set_default_navigation_timeout(456)
    await page.pause()
    with pytest.raises(Error, match="Timeout 123ms exceeded."):
        await page.get_by_text("foo").click()

    server.set_route("/empty.html", lambda route: None)
    with pytest.raises(Error, match="Timeout 456ms exceeded."):
        await page.goto(server.EMPTY_PAGE)


async def test_page_should_ignore_deprecated_is_hidden_and_visible_timeout(
    page: Page,
) -> None:
    await page.set_content("<div>foo</div>")
    assert await page.is_hidden("div", timeout=10) is False
    assert await page.is_visible("div", timeout=10) is True
