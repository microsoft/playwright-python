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

"""Port of tests/library/page-close.spec.ts."""


import asyncio
from typing import Any, Awaitable, List, Optional

import pytest

from playwright.async_api import Error, Page, Route, expect
from tests.server import Server, TestServerRequest
from tests.utils import TARGET_CLOSED_ERROR_MESSAGE


async def error_of(awaitable: Awaitable[Any]) -> Any:
    """Like `promise.catch(e => e)`: returns the result or the error."""
    try:
        return await awaitable
    except Exception as e:
        return e


async def test_PA_039_should_close_page_with_active_dialog(page: Page) -> None:
    await page.evaluate('"trigger builtins.setTimeout"')
    await page.set_content(
        '<button onclick="builtins.setTimeout(() => alert(1))">alert</button>'
    )
    async with page.expect_event("dialog"):
        click_task = asyncio.create_task(error_of(page.click("button")))
    await page.close()
    await click_task


async def test_PA_040_expect_should_not_print_timed_out_error_message_when_page_closes(
    page: Page,
) -> None:
    await page.set_content("<div id=node>Text content</div>")
    error, _ = await asyncio.gather(
        error_of(expect(page.locator("div")).to_have_text("hey", timeout=100000)),
        page.close(),
    )
    assert isinstance(error, AssertionError)
    assert "Locator expected to have text 'hey'" in str(error)
    assert "Timed out" not in str(error)


async def test_PA_041_add_locator_handler_should_throw_when_page_closes(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/handle-locator.html")

    async def handler() -> None:
        await page.close(reason="custom reason")

    await page.add_locator_handler(
        page.get_by_text("This interstitial covers the button"), handler
    )

    await page.locator("#aside").hover()
    await page.evaluate(
        """() => {
    window.clicked = 0;
    window.setupAnnoyingInterstitial('mouseover', 1);
  }"""
    )
    with pytest.raises(Error) as exc_info:
        await page.locator("#target").click()
    assert "custom reason" in exc_info.value.message


async def test_PA_042_should_reject_all_promises_when_page_is_closed(
    page: Page, server: Server
) -> None:
    server.set_route("/hang", lambda request: None)
    request_promise = asyncio.create_task(server.wait_for_request("/hang"))
    await page.set_content(
        f'<iframe src="{server.PREFIX}/hang"></iframe>', wait_until="domcontentloaded"
    )
    await request_promise
    frame_error_promise = asyncio.create_task(
        error_of(page.frames[1].evaluate("() => new Promise(() => {})"))
    )
    error, _ = await asyncio.gather(
        error_of(page.evaluate("() => new Promise(r => {})")),
        page.close(),
    )
    assert isinstance(error, Error)
    assert TARGET_CLOSED_ERROR_MESSAGE in error.message
    assert TARGET_CLOSED_ERROR_MESSAGE in (await frame_error_promise).message


async def test_PA_043_should_set_the_page_close_state(page: Page) -> None:
    assert page.is_closed() is False
    await page.close()
    assert page.is_closed() is True


async def test_PA_044_should_pass_page_to_close_event(page: Page) -> None:
    async with page.expect_event("close") as close_info:
        await page.close()
    assert await close_info.value == page


async def test_PA_045_should_terminate_network_waiters(
    page: Page, server: Server
) -> None:
    async def wait_for_request() -> Any:
        try:
            async with page.expect_request(server.EMPTY_PAGE):
                pass
        except Error as e:
            return e

    async def wait_for_response() -> Any:
        try:
            async with page.expect_response(server.EMPTY_PAGE):
                pass
        except Error as e:
            return e

    results = await asyncio.gather(
        wait_for_request(), wait_for_response(), page.close()
    )
    for i in range(2):
        error = results[i]
        assert isinstance(error, Error)
        message = error.message
        assert TARGET_CLOSED_ERROR_MESSAGE in message
        assert "Timeout" not in message


async def test_PA_046_should_be_callable_twice(page: Page) -> None:
    await asyncio.gather(page.close(), page.close())
    await page.close()


async def test_PA_047_should_return_null_if_parent_page_has_been_closed(
    page: Page,
) -> None:
    async with page.expect_popup() as popup_info:
        await page.evaluate("() => window.open('about:blank')")
    popup = await popup_info.value
    await page.close()
    opener = await popup.opener()
    assert opener is None


async def test_PA_048_should_fail_with_error_upon_disconnect(page: Page) -> None:
    with pytest.raises(Error) as exc_info:
        async with page.expect_event("download"):
            await page.close()
    assert TARGET_CLOSED_ERROR_MESSAGE in exc_info.value.message


async def test_PA_049_page_close_should_work_with_window_close(page: Page) -> None:
    async with page.expect_event("close"):
        await page.close()


async def test_PA_050_should_not_throw_unhandled_promise_rejection_when_page_closes(
    page: Page, browser_name: str, is_win: bool
) -> None:
    if browser_name == "firefox" and is_win:
        pytest.skip("fixme: makes the next test to always timeout")

    await asyncio.gather(page.close(), page.mouse.click(1, 2), return_exceptions=True)


async def test_PA_051_interrupt_request_response_and_request_all_headers_on_page_close(
    page: Page, server: Server, browser_name: str
) -> None:
    def handle(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "text/css")

    server.set_route("/one-style.css", handle)
    async with page.expect_request("**/one-style.css") as request_info:
        await page.goto(
            server.PREFIX + "/one-style.html", wait_until="domcontentloaded"
        )
    req = await request_info.value
    response, headers, _ = await asyncio.gather(
        error_of(req.response()), error_of(req.all_headers()), page.close()
    )
    assert isinstance(response, Error)
    assert TARGET_CLOSED_ERROR_MESSAGE in response.message
    # All headers are the same as "provisional" headers in Firefox.
    if browser_name == "firefox":
        assert headers["user-agent"]
    else:
        assert isinstance(headers, Error)
        assert TARGET_CLOSED_ERROR_MESSAGE in headers.message


async def test_PA_052_should_not_treat_navigations_as_new_popups(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        '<a target=_blank rel=noopener href="/one-style.html">yo</a>'
    )
    async with page.expect_popup() as popup_info:
        await page.click("a")
    popup = await popup_info.value
    bad_second_popup = False

    def on_popup(_: Page) -> None:
        nonlocal bad_second_popup
        bad_second_popup = True

    page.on("popup", on_popup)
    await popup.goto(server.CROSS_PROCESS_PREFIX + "/empty.html")
    await page.close()
    assert bad_second_popup is False


async def test_PA_053_should_not_result_in_unhandled_rejection(page: Page) -> None:
    async def foo() -> None:
        await page.close()

    async with page.expect_event("close"):
        await page.expose_function("foo", foo)
        await page.evaluate(
            """() => {
    window.builtins.setTimeout(() => window.foo(), 0);
    return undefined;
  }"""
        )
    # Make a round-trip to be sure we did not throw immediately after closing.
    with pytest.raises(Error):
        await page.evaluate("1 + 1")


async def test_PA_054_should_reject_response_finished_if_page_closes(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)

    def handle(request: TestServerRequest) -> None:
        # In Firefox, |fetch| will be hanging until it receives |Content-Type| header
        # from server.
        request.setHeader("Content-Type", "text/plain; charset=utf-8")
        request.write(b"hello ")

    server.set_route("/get", handle)
    # send request and wait for server response
    async with page.expect_event("response") as response_info:
        await page.evaluate("() => fetch('./get', { method: 'GET' })")
    page_response = await response_info.value

    error, _ = await asyncio.gather(error_of(page_response.finished()), page.close())
    assert isinstance(error, Error)
    assert "closed" in error.message


async def test_PA_055_should_not_throw_when_continuing_while_page_is_closing(
    page: Page, server: Server
) -> None:
    done: List["asyncio.Future[Any]"] = []

    async def handle(route: Route) -> None:
        done.append(asyncio.gather(route.continue_(), page.close()))

    await page.route("**/*", handle)
    await error_of(page.goto(server.EMPTY_PAGE))
    await done[0]


async def test_PA_056_should_not_throw_when_continuing_after_page_is_closed(
    page: Page, server: Server
) -> None:
    done: "asyncio.Future[Any]" = asyncio.get_running_loop().create_future()

    async def handle(route: Route) -> None:
        await page.close()
        done.set_result(asyncio.ensure_future(route.continue_()))

    await page.route("**/*", handle)
    error: Optional[Exception] = await error_of(page.goto(server.EMPTY_PAGE))
    await (await done)
    assert isinstance(error, Error)
