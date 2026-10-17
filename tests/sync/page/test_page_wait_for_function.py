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

"""Port of tests/page/page-wait-for-function.spec.ts."""

import re
import time
from typing import Any, Callable, List, Optional

import pytest

from playwright.sync_api import ConsoleMessage, Error, Page, TimeoutError
from tests.server import Server

from ..utils import Utils


def test_WA_001_should_timeout(page: Page) -> None:
    start_time = time.monotonic()
    timeout = 42
    page.wait_for_timeout(timeout)
    assert (time.monotonic() - start_time) * 1000 >= timeout / 2


def test_WA_002_should_accept_a_string(
    page: Page, sync_gather: Callable[..., List[Any]]
) -> None:
    def watchdog() -> None:
        page.wait_for_function("window.__FOO === 1")

    def set_foo() -> None:
        page.evaluate("() => window['__FOO'] = 1")

    sync_gather(watchdog, set_foo)


def test_WA_003_should_work_when_resolved_right_before_execution_context_disposal(
    page: Page,
) -> None:
    page.add_init_script("window['__RELOADED'] = true")
    page.wait_for_function(
        """() => {
            if (!window['__RELOADED'])
                window.location.reload();
            return true;
        }"""
    )


def test_WA_004_should_poll_on_interval(page: Page, server: Server) -> None:
    polling = 100
    time_delta = page.wait_for_function(
        """() => {
            if (!window['__startTime']) {
                window['__startTime'] = window.builtins.Date.now();
                return false;
            }
            return window.builtins.Date.now() - window['__startTime'];
        }""",
        arg={},
        polling=polling,
    )
    assert time_delta.json_value() >= polling


def test_WA_005_should_avoid_side_effects_after_timeout(page: Page) -> None:
    counter = 0

    def on_console(message: ConsoleMessage) -> None:
        nonlocal counter
        counter += 1

    page.on("console", on_console)

    with pytest.raises(Error) as exc_info:
        page.wait_for_function(
            """() => {
                window['counter'] = (window['counter'] || 0) + 1;
                console.log(window['counter']);
            }""",
            arg={},
            polling=1,
            timeout=1000,
        )

    saved_counter = counter
    page.wait_for_timeout(2000)  # Give it some time to produce more logs.

    assert "Page.wait_for_function: Timeout 1000ms exceeded" in exc_info.value.message
    assert counter == saved_counter


def test_WA_006_should_throw_on_polling_mutation(page: Page) -> None:
    with pytest.raises(Error) as exc_info:
        page.wait_for_function(
            "() => true", arg={}, polling="mutation"  # type: ignore[arg-type]
        )
    assert "Unknown polling option: mutation" in exc_info.value.message


def test_WA_007_should_poll_on_raf(
    page: Page, sync_gather: Callable[..., List[Any]]
) -> None:
    def watchdog() -> None:
        page.wait_for_function("() => window['__FOO'] === 'hit'", arg={}, polling="raf")

    def hit() -> None:
        page.evaluate("() => window['__FOO'] = 'hit'")

    sync_gather(watchdog, hit)


def test_WA_008_should_fail_with_predicate_throwing_on_first_call(
    page: Page,
) -> None:
    with pytest.raises(Error) as exc_info:
        page.wait_for_function("() => { throw new Error('oh my'); }")
    assert "oh my" in exc_info.value.message


def test_WA_009_should_fail_with_predicate_throwing_sometimes(
    page: Page,
) -> None:
    with pytest.raises(Error) as exc_info:
        page.wait_for_function(
            """() => {
                window['counter'] = (window['counter'] || 0) + 1;
                if (window['counter'] === 3)
                    throw new Error('Bad counter!');
                return window['counter'] === 5 ? 'result' : false;
            }"""
        )
    assert "Bad counter!" in exc_info.value.message


def test_WA_010_should_fail_with_reference_error_on_wrong_page(
    page: Page,
) -> None:
    with pytest.raises(Error) as exc_info:
        page.wait_for_function("() => globalVar === 123")
    assert "globalVar" in exc_info.value.message


def test_WA_011_should_work_with_strict_csp_policy(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    server.set_csp("/empty.html", "script-src " + server.PREFIX)
    page.goto(server.EMPTY_PAGE)
    error: Optional[Error] = None

    def wait() -> None:
        nonlocal error
        try:
            page.wait_for_function(
                "() => window['__FOO'] === 'hit'", arg={}, polling="raf"
            )
        except Error as e:
            error = e

    def hit() -> None:
        page.wait_for_timeout(1000)
        page.evaluate("() => window['__FOO'] = 'hit'")

    sync_gather(wait, hit)
    assert error is None


def test_WA_012_should_throw_on_bad_polling_value(page: Page) -> None:
    error: Optional[Error] = None
    try:
        page.wait_for_function(
            "() => !!document.body", arg={}, polling="unknown"  # type: ignore[arg-type]
        )
    except Error as e:
        error = e
    assert error
    assert "polling" in error.message


def test_WA_013_should_throw_negative_polling_interval(page: Page) -> None:
    error: Optional[Error] = None
    try:
        page.wait_for_function("() => !!document.body", arg={}, polling=-10)
    except Error as e:
        error = e
    assert error
    assert "Cannot poll with non-positive interval" in error.message


def test_WA_014_should_return_the_success_value_as_a_js_handle(
    page: Page,
) -> None:
    assert (page.wait_for_function("() => 5")).json_value() == 5


def test_WA_015_should_return_the_window_as_a_success_value(
    page: Page,
) -> None:
    assert page.wait_for_function("() => window")


def test_WA_016_should_accept_element_handle_arguments(
    page: Page, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_content("<div></div>")
    div = page.query_selector("div")
    resolved = False

    def wait_for_function() -> None:
        nonlocal resolved
        page.wait_for_function("element => !element.parentElement", arg=div)
        resolved = True

    def remove() -> None:
        assert resolved is False
        page.evaluate("element => element.remove()", div)

    sync_gather(wait_for_function, remove)


def test_WA_017_should_respect_timeout(page: Page) -> None:
    error: Optional[Error] = None
    try:
        page.wait_for_function("false", arg={}, timeout=10)
    except Error as e:
        error = e
    assert error
    assert "Page.wait_for_function: Timeout 10ms exceeded" in error.message
    assert isinstance(error, TimeoutError)


def test_WA_018_should_respect_default_timeout(page: Page) -> None:
    page.set_default_timeout(1)
    error: Optional[Error] = None
    try:
        page.wait_for_function("false")
    except Error as e:
        error = e
    assert isinstance(error, TimeoutError)
    assert "Page.wait_for_function: Timeout 1ms exceeded" in error.message


def test_WA_019_should_disable_timeout_when_its_set_to_0(
    page: Page, sync_gather: Callable[..., List[Any]]
) -> None:
    def watchdog() -> None:
        page.wait_for_function(
            """() => {
                window['__counter'] = (window['__counter'] || 0) + 1;
                return window['__injected'];
            }""",
            arg={},
            timeout=0,
            polling=10,
        )

    def inject() -> None:
        page.wait_for_function("() => window['__counter'] > 10")
        page.evaluate("() => window['__injected'] = true")

    sync_gather(watchdog, inject)


def test_WA_020_should_survive_cross_process_navigation(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    foo_found = False

    def wait_for_function() -> None:
        nonlocal foo_found
        page.wait_for_function("window.__FOO === 1")
        foo_found = True

    def navigate() -> None:
        page.goto(server.EMPTY_PAGE)
        assert foo_found is False
        page.reload()
        assert foo_found is False
        page.goto(server.CROSS_PROCESS_PREFIX + "/grid.html")
        assert foo_found is False
        page.evaluate("() => window['__FOO'] = 1")

    sync_gather(wait_for_function, navigate)
    assert foo_found is True


def test_WA_021_should_survive_navigations(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    def watchdog() -> None:
        page.wait_for_function("() => window['__done']")

    def navigate() -> None:
        page.goto(server.EMPTY_PAGE)
        page.goto(server.PREFIX + "/consolelog.html")
        page.evaluate("() => window['__done'] = true")

    sync_gather(watchdog, navigate)


def test_WA_022_should_work_with_multiline_body(page: Page) -> None:
    result = page.wait_for_function(
        """
    (() => true)()
  """
    )
    assert result.json_value() is True


def test_WA_023_should_wait_for_predicate_with_arguments(page: Page) -> None:
    page.wait_for_function(
        "({ arg1, arg2 }) => arg1 + arg2 === 3", arg={"arg1": 1, "arg2": 2}
    )


def test_WA_024_should_not_be_called_after_finishing_successfully(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)

    messages: List[str] = []

    def on_console(msg: ConsoleMessage) -> None:
        if msg.text.startswith("waitForFunction"):
            messages.append(msg.text)

    page.on("console", on_console)

    page.wait_for_function(
        """() => {
            console.log('waitForFunction1');
            return true;
        }"""
    )
    page.reload()
    page.wait_for_function(
        """() => {
            console.log('waitForFunction2');
            return true;
        }"""
    )
    page.reload()
    page.wait_for_function(
        """() => {
            console.log('waitForFunction3');
            return true;
        }"""
    )

    assert "|".join(messages) == "waitForFunction1|waitForFunction2|waitForFunction3"


def test_WA_025_should_not_be_called_after_finishing_unsuccessfully(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)

    messages: List[str] = []

    def on_console(msg: ConsoleMessage) -> None:
        if msg.text.startswith("waitForFunction"):
            messages.append(msg.text)

    page.on("console", on_console)

    with pytest.raises(Error):
        page.wait_for_function(
            """() => {
                console.log('waitForFunction1');
                throw new Error('waitForFunction1');
            }"""
        )
    page.reload()
    with pytest.raises(Error):
        page.wait_for_function(
            """() => {
                console.log('waitForFunction2');
                throw new Error('waitForFunction2');
            }"""
        )
    page.reload()
    with pytest.raises(Error):
        page.wait_for_function(
            """() => {
                console.log('waitForFunction3');
                throw new Error('waitForFunction3');
            }"""
        )

    assert "|".join(messages) == "waitForFunction1|waitForFunction2|waitForFunction3"


def test_WA_026_should_throw_when_frame_is_detached(
    page: Page, server: Server, utils: Utils, sync_gather: Callable[..., List[Any]]
) -> None:
    utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    frame = page.frames[1]
    error: Optional[Error] = None

    def wait_for_function() -> None:
        nonlocal error
        try:
            frame.wait_for_function("() => false")
        except Error as e:
            error = e

    def detach() -> None:
        utils.detach_frame(page, "frame1")

    sync_gather(wait_for_function, detach)
    assert error
    assert re.search(
        r"Frame.wait_for_function: (Frame was detached|Execution context was destroyed)",
        error.message,
    )
