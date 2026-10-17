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

import asyncio
import re
import time
from typing import List, Optional

import pytest

from playwright.async_api import ConsoleMessage, Error, Page, TimeoutError
from tests.server import Server

from ..utils import Utils


async def test_WA_001_should_timeout(page: Page) -> None:
    start_time = time.monotonic()
    timeout = 42
    await page.wait_for_timeout(timeout)
    assert (time.monotonic() - start_time) * 1000 >= timeout / 2


async def test_WA_002_should_accept_a_string(page: Page) -> None:
    async def watchdog() -> None:
        await page.wait_for_function("window.__FOO === 1")

    async def set_foo() -> None:
        await page.evaluate("() => window['__FOO'] = 1")

    await asyncio.gather(watchdog(), set_foo())


async def test_WA_003_should_work_when_resolved_right_before_execution_context_disposal(
    page: Page,
) -> None:
    await page.add_init_script("window['__RELOADED'] = true")
    await page.wait_for_function(
        """() => {
            if (!window['__RELOADED'])
                window.location.reload();
            return true;
        }"""
    )


async def test_WA_004_should_poll_on_interval(page: Page, server: Server) -> None:
    polling = 100
    time_delta = await page.wait_for_function(
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
    assert await time_delta.json_value() >= polling


async def test_WA_005_should_avoid_side_effects_after_timeout(page: Page) -> None:
    counter = 0

    def on_console(message: ConsoleMessage) -> None:
        nonlocal counter
        counter += 1

    page.on("console", on_console)

    with pytest.raises(Error) as exc_info:
        await page.wait_for_function(
            """() => {
                window['counter'] = (window['counter'] || 0) + 1;
                console.log(window['counter']);
            }""",
            arg={},
            polling=1,
            timeout=1000,
        )

    saved_counter = counter
    await page.wait_for_timeout(2000)  # Give it some time to produce more logs.

    assert "Page.wait_for_function: Timeout 1000ms exceeded" in exc_info.value.message
    assert counter == saved_counter


async def test_WA_006_should_throw_on_polling_mutation(page: Page) -> None:
    with pytest.raises(Error) as exc_info:
        await page.wait_for_function(
            "() => true", arg={}, polling="mutation"  # type: ignore[arg-type]
        )
    assert "Unknown polling option: mutation" in exc_info.value.message


async def test_WA_007_should_poll_on_raf(page: Page) -> None:
    async def watchdog() -> None:
        await page.wait_for_function(
            "() => window['__FOO'] === 'hit'", arg={}, polling="raf"
        )

    async def hit() -> None:
        await page.evaluate("() => window['__FOO'] = 'hit'")

    await asyncio.gather(watchdog(), hit())


async def test_WA_008_should_fail_with_predicate_throwing_on_first_call(
    page: Page,
) -> None:
    with pytest.raises(Error) as exc_info:
        await page.wait_for_function("() => { throw new Error('oh my'); }")
    assert "oh my" in exc_info.value.message


async def test_WA_009_should_fail_with_predicate_throwing_sometimes(
    page: Page,
) -> None:
    with pytest.raises(Error) as exc_info:
        await page.wait_for_function(
            """() => {
                window['counter'] = (window['counter'] || 0) + 1;
                if (window['counter'] === 3)
                    throw new Error('Bad counter!');
                return window['counter'] === 5 ? 'result' : false;
            }"""
        )
    assert "Bad counter!" in exc_info.value.message


async def test_WA_010_should_fail_with_reference_error_on_wrong_page(
    page: Page,
) -> None:
    with pytest.raises(Error) as exc_info:
        await page.wait_for_function("() => globalVar === 123")
    assert "globalVar" in exc_info.value.message


async def test_WA_011_should_work_with_strict_csp_policy(
    page: Page, server: Server
) -> None:
    server.set_csp("/empty.html", "script-src " + server.PREFIX)
    await page.goto(server.EMPTY_PAGE)
    error: Optional[Error] = None

    async def wait() -> None:
        nonlocal error
        try:
            await page.wait_for_function(
                "() => window['__FOO'] === 'hit'", arg={}, polling="raf"
            )
        except Error as e:
            error = e

    async def hit() -> None:
        await page.wait_for_timeout(1000)
        await page.evaluate("() => window['__FOO'] = 'hit'")

    await asyncio.gather(wait(), hit())
    assert error is None


async def test_WA_012_should_throw_on_bad_polling_value(page: Page) -> None:
    error: Optional[Error] = None
    try:
        await page.wait_for_function(
            "() => !!document.body", arg={}, polling="unknown"  # type: ignore[arg-type]
        )
    except Error as e:
        error = e
    assert error
    assert "polling" in error.message


async def test_WA_013_should_throw_negative_polling_interval(page: Page) -> None:
    error: Optional[Error] = None
    try:
        await page.wait_for_function("() => !!document.body", arg={}, polling=-10)
    except Error as e:
        error = e
    assert error
    assert "Cannot poll with non-positive interval" in error.message


async def test_WA_014_should_return_the_success_value_as_a_js_handle(
    page: Page,
) -> None:
    assert await (await page.wait_for_function("() => 5")).json_value() == 5


async def test_WA_015_should_return_the_window_as_a_success_value(
    page: Page,
) -> None:
    assert await page.wait_for_function("() => window")


async def test_WA_016_should_accept_element_handle_arguments(page: Page) -> None:
    await page.set_content("<div></div>")
    div = await page.query_selector("div")
    resolved = False

    async def wait_for_function() -> None:
        nonlocal resolved
        await page.wait_for_function("element => !element.parentElement", arg=div)
        resolved = True

    async def remove() -> None:
        assert resolved is False
        await page.evaluate("element => element.remove()", div)

    await asyncio.gather(wait_for_function(), remove())


async def test_WA_017_should_respect_timeout(page: Page) -> None:
    error: Optional[Error] = None
    try:
        await page.wait_for_function("false", arg={}, timeout=10)
    except Error as e:
        error = e
    assert error
    assert "Page.wait_for_function: Timeout 10ms exceeded" in error.message
    assert isinstance(error, TimeoutError)


async def test_WA_018_should_respect_default_timeout(page: Page) -> None:
    page.set_default_timeout(1)
    error: Optional[Error] = None
    try:
        await page.wait_for_function("false")
    except Error as e:
        error = e
    assert isinstance(error, TimeoutError)
    assert "Page.wait_for_function: Timeout 1ms exceeded" in error.message


async def test_WA_019_should_disable_timeout_when_its_set_to_0(page: Page) -> None:
    async def watchdog() -> None:
        await page.wait_for_function(
            """() => {
                window['__counter'] = (window['__counter'] || 0) + 1;
                return window['__injected'];
            }""",
            arg={},
            timeout=0,
            polling=10,
        )

    async def inject() -> None:
        await page.wait_for_function("() => window['__counter'] > 10")
        await page.evaluate("() => window['__injected'] = true")

    await asyncio.gather(watchdog(), inject())


async def test_WA_020_should_survive_cross_process_navigation(
    page: Page, server: Server
) -> None:
    foo_found = False

    async def wait_for_function() -> None:
        nonlocal foo_found
        await page.wait_for_function("window.__FOO === 1")
        foo_found = True

    async def navigate() -> None:
        await page.goto(server.EMPTY_PAGE)
        assert foo_found is False
        await page.reload()
        assert foo_found is False
        await page.goto(server.CROSS_PROCESS_PREFIX + "/grid.html")
        assert foo_found is False
        await page.evaluate("() => window['__FOO'] = 1")

    await asyncio.gather(wait_for_function(), navigate())
    assert foo_found is True


async def test_WA_021_should_survive_navigations(page: Page, server: Server) -> None:
    async def watchdog() -> None:
        await page.wait_for_function("() => window['__done']")

    async def navigate() -> None:
        await page.goto(server.EMPTY_PAGE)
        await page.goto(server.PREFIX + "/consolelog.html")
        await page.evaluate("() => window['__done'] = true")

    await asyncio.gather(watchdog(), navigate())


async def test_WA_022_should_work_with_multiline_body(page: Page) -> None:
    result = await page.wait_for_function(
        """
    (() => true)()
  """
    )
    assert await result.json_value() is True


async def test_WA_023_should_wait_for_predicate_with_arguments(page: Page) -> None:
    await page.wait_for_function(
        "({ arg1, arg2 }) => arg1 + arg2 === 3", arg={"arg1": 1, "arg2": 2}
    )


async def test_WA_024_should_not_be_called_after_finishing_successfully(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)

    messages: List[str] = []

    def on_console(msg: ConsoleMessage) -> None:
        if msg.text.startswith("waitForFunction"):
            messages.append(msg.text)

    page.on("console", on_console)

    await page.wait_for_function(
        """() => {
            console.log('waitForFunction1');
            return true;
        }"""
    )
    await page.reload()
    await page.wait_for_function(
        """() => {
            console.log('waitForFunction2');
            return true;
        }"""
    )
    await page.reload()
    await page.wait_for_function(
        """() => {
            console.log('waitForFunction3');
            return true;
        }"""
    )

    assert "|".join(messages) == "waitForFunction1|waitForFunction2|waitForFunction3"


async def test_WA_025_should_not_be_called_after_finishing_unsuccessfully(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)

    messages: List[str] = []

    def on_console(msg: ConsoleMessage) -> None:
        if msg.text.startswith("waitForFunction"):
            messages.append(msg.text)

    page.on("console", on_console)

    with pytest.raises(Error):
        await page.wait_for_function(
            """() => {
                console.log('waitForFunction1');
                throw new Error('waitForFunction1');
            }"""
        )
    await page.reload()
    with pytest.raises(Error):
        await page.wait_for_function(
            """() => {
                console.log('waitForFunction2');
                throw new Error('waitForFunction2');
            }"""
        )
    await page.reload()
    with pytest.raises(Error):
        await page.wait_for_function(
            """() => {
                console.log('waitForFunction3');
                throw new Error('waitForFunction3');
            }"""
        )

    assert "|".join(messages) == "waitForFunction1|waitForFunction2|waitForFunction3"


async def test_WA_026_should_throw_when_frame_is_detached(
    page: Page, server: Server, utils: Utils
) -> None:
    await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    frame = page.frames[1]
    error: Optional[Error] = None

    async def wait_for_function() -> None:
        nonlocal error
        try:
            await frame.wait_for_function("() => false")
        except Error as e:
            error = e

    async def detach() -> None:
        await utils.detach_frame(page, "frame1")

    await asyncio.gather(wait_for_function(), detach())
    assert error
    assert re.search(
        r"Frame.wait_for_function: (Frame was detached|Execution context was destroyed)",
        error.message,
    )
