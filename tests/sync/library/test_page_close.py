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
from typing import Any, Awaitable, Callable, List, Optional, TypeVar

import pytest

from playwright._impl._greenlets import wait_for_future
from playwright.sync_api import Error, Page, Route, expect
from tests.server import Server, TestServerRequest
from tests.utils import TARGET_CLOSED_ERROR_MESSAGE

T = TypeVar("T")


def error_of(action: Callable[[], Any]) -> Any:
    """Like `promise.catch(e => e)`: returns the result or the error."""
    try:
        return action()
    except Exception as e:
        return e


def wait_for(page: Page, awaitable: "Awaitable[T]") -> T:
    """Port of `await promise`: runs the event loop until the awaitable settles."""
    future = asyncio.ensure_future(awaitable)
    wait_for_future(page._loop, page._dispatcher_fiber, future)
    return future.result()


def settle(future: "asyncio.Future[None]", action: Callable[[], Any]) -> None:
    """Runs the action and settles the future with its outcome, like a promise."""
    try:
        action()
        future.set_result(None)
    except Exception as e:
        future.set_exception(e)


def test_PA_039_should_close_page_with_active_dialog(
    page: Page, sync_gather: Callable[..., List[Any]]
) -> None:
    page.evaluate('"trigger builtins.setTimeout"')
    page.set_content(
        '<button onclick="builtins.setTimeout(() => alert(1))">alert</button>'
    )

    def wait_for_dialog_and_close() -> None:
        with page.expect_event("dialog"):
            pass
        page.close()

    sync_gather(
        lambda: error_of(lambda: page.click("button")), wait_for_dialog_and_close
    )


def test_PA_040_expect_should_not_print_timed_out_error_message_when_page_closes(
    page: Page, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_content("<div id=node>Text content</div>")
    error, _ = sync_gather(
        lambda: error_of(
            lambda: expect(page.locator("div")).to_have_text("hey", timeout=100000)
        ),
        page.close,
    )
    assert isinstance(error, AssertionError)
    assert "Locator expected to have text 'hey'" in str(error)
    assert "Timed out" not in str(error)


def test_PA_041_add_locator_handler_should_throw_when_page_closes(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/input/handle-locator.html")

    def handler() -> None:
        page.close(reason="custom reason")

    page.add_locator_handler(
        page.get_by_text("This interstitial covers the button"), handler
    )

    page.locator("#aside").hover()
    page.evaluate(
        """() => {
    window.clicked = 0;
    window.setupAnnoyingInterstitial('mouseover', 1);
  }"""
    )
    with pytest.raises(Error) as exc_info:
        page.locator("#target").click()
    assert "custom reason" in exc_info.value.message


def test_PA_042_should_reject_all_promises_when_page_is_closed(
    page: Page, sync_gather: Callable[..., List[Any]]
) -> None:
    error, _ = sync_gather(
        lambda: error_of(lambda: page.evaluate("() => new Promise(r => {})")),
        page.close,
    )
    assert isinstance(error, Error)
    assert TARGET_CLOSED_ERROR_MESSAGE in error.message


def test_PA_043_should_set_the_page_close_state(page: Page) -> None:
    assert page.is_closed() is False
    page.close()
    assert page.is_closed() is True


def test_PA_044_should_pass_page_to_close_event(page: Page) -> None:
    with page.expect_event("close") as close_info:
        page.close()
    assert close_info.value == page


def test_PA_045_should_terminate_network_waiters(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    def wait_for_request() -> Any:
        try:
            with page.expect_request(server.EMPTY_PAGE):
                pass
        except Error as e:
            return e

    def wait_for_response() -> Any:
        try:
            with page.expect_response(server.EMPTY_PAGE):
                pass
        except Error as e:
            return e

    results = sync_gather(wait_for_request, wait_for_response, page.close)
    for i in range(2):
        error = results[i]
        assert isinstance(error, Error)
        message = error.message
        assert TARGET_CLOSED_ERROR_MESSAGE in message
        assert "Timeout" not in message


def test_PA_046_should_be_callable_twice(
    page: Page, sync_gather: Callable[..., List[Any]]
) -> None:
    sync_gather(lambda: page.close(), lambda: page.close())
    page.close()


def test_PA_047_should_return_null_if_parent_page_has_been_closed(
    page: Page,
) -> None:
    with page.expect_popup() as popup_info:
        page.evaluate("() => window.open('about:blank')")
    popup = popup_info.value
    page.close()
    opener = popup.opener()
    assert opener is None


def test_PA_048_should_fail_with_error_upon_disconnect(page: Page) -> None:
    with pytest.raises(Error) as exc_info:
        with page.expect_event("download"):
            page.close()
    assert TARGET_CLOSED_ERROR_MESSAGE in exc_info.value.message


def test_PA_049_page_close_should_work_with_window_close(page: Page) -> None:
    with page.expect_event("close"):
        page.close()


def test_PA_050_should_not_throw_unhandled_promise_rejection_when_page_closes(
    page: Page,
    browser_name: str,
    is_win: bool,
    sync_gather: Callable[..., List[Any]],
) -> None:
    if browser_name == "firefox" and is_win:
        pytest.skip("fixme: makes the next test to always timeout")

    sync_gather(
        lambda: error_of(page.close), lambda: error_of(lambda: page.mouse.click(1, 2))
    )


def test_PA_051_interrupt_request_response_and_request_all_headers_on_page_close(
    page: Page,
    server: Server,
    browser_name: str,
    sync_gather: Callable[..., List[Any]],
) -> None:
    def handle(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "text/css")

    server.set_route("/one-style.css", handle)
    with page.expect_request("**/one-style.css") as request_info:
        page.goto(server.PREFIX + "/one-style.html", wait_until="domcontentloaded")
    req = request_info.value
    response, headers, _ = sync_gather(
        lambda: error_of(req.response), lambda: error_of(req.all_headers), page.close
    )
    assert isinstance(response, Error)
    assert TARGET_CLOSED_ERROR_MESSAGE in response.message
    # All headers are the same as "provisional" headers in Firefox.
    if browser_name == "firefox":
        assert headers["user-agent"]
    else:
        assert isinstance(headers, Error)
        assert TARGET_CLOSED_ERROR_MESSAGE in headers.message


def test_PA_052_should_not_treat_navigations_as_new_popups(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content('<a target=_blank rel=noopener href="/one-style.html">yo</a>')
    with page.expect_popup() as popup_info:
        page.click("a")
    popup = popup_info.value
    bad_second_popup = False

    def on_popup(_: Page) -> None:
        nonlocal bad_second_popup
        bad_second_popup = True

    page.on("popup", on_popup)
    popup.goto(server.CROSS_PROCESS_PREFIX + "/empty.html")
    page.close()
    assert bad_second_popup is False


# run=False: the hang does not end at the test timeout.
@pytest.mark.xfail(
    reason="python: a sync expose_binding/expose_function callback runs on the dispatcher greenlet, so a sync API call in it (page.close()) never returns and the test hangs",
    run=False,
    strict=True,
)
def test_PA_053_should_not_result_in_unhandled_rejection(page: Page) -> None:
    def foo() -> None:
        page.close()

    with page.expect_event("close"):
        page.expose_function("foo", foo)
        page.evaluate(
            """() => {
    window.builtins.setTimeout(() => window.foo(), 0);
    return undefined;
  }"""
        )
    # Make a round-trip to be sure we did not throw immediately after closing.
    with pytest.raises(Error):
        page.evaluate("1 + 1")


def test_PA_054_should_reject_response_finished_if_page_closes(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    page.goto(server.EMPTY_PAGE)

    def handle(request: TestServerRequest) -> None:
        # In Firefox, |fetch| will be hanging until it receives |Content-Type| header
        # from server.
        request.setHeader("Content-Type", "text/plain; charset=utf-8")
        request.write(b"hello ")

    server.set_route("/get", handle)
    # send request and wait for server response
    with page.expect_event("response") as response_info:
        page.evaluate("() => fetch('./get', { method: 'GET' })")
    page_response = response_info.value

    error, _ = sync_gather(lambda: error_of(page_response.finished), page.close)
    assert isinstance(error, Error)
    assert "closed" in error.message


def test_PA_055_should_not_throw_when_continuing_while_page_is_closing(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    done: "asyncio.Future[None]" = page._loop.create_future()

    def handle(route: Route) -> None:
        settle(done, lambda: sync_gather(route.continue_, page.close))

    page.route("**/*", handle)
    error_of(lambda: page.goto(server.EMPTY_PAGE))
    wait_for(page, done)


def test_PA_056_should_not_throw_when_continuing_after_page_is_closed(
    page: Page, server: Server
) -> None:
    done: "asyncio.Future[None]" = page._loop.create_future()

    def handle(route: Route) -> None:
        page.close()
        settle(done, route.continue_)

    page.route("**/*", handle)
    error: Optional[Exception] = error_of(lambda: page.goto(server.EMPTY_PAGE))
    wait_for(page, done)
    assert isinstance(error, Error)
