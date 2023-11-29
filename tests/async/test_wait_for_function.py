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

from datetime import datetime

import pytest

from playwright.async_api import ConsoleMessage, Error, Page


async def test_should_timeout(page: Page) -> None:
    start_time = datetime.now()
    timeout = 42
    await page.wait_for_timeout(timeout)
    assert ((datetime.now() - start_time).microseconds * 1000) >= timeout / 2


async def test_should_accept_a_string(page: Page) -> None:
    watchdog = page.wait_for_function("window.__FOO === 1")
    await page.evaluate("window['__FOO'] = 1")
    await watchdog


async def test_should_work_when_resolved_right_before_execution_context_disposal(
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


async def test_should_poll_on_interval(page: Page) -> None:
    polling = 100
    time_delta = await page.wait_for_function(
        """() => {
            if (!window['__startTime']) {
                window['__startTime'] = Date.now();
                return false;
            }
            return Date.now() - window['__startTime'];
        }""",
        polling=polling,
    )
    assert await time_delta.json_value() >= polling


async def test_should_avoid_side_effects_after_timeout(page: Page) -> None:
    counter = 0

    async def on_console(message: ConsoleMessage) -> None:
        nonlocal counter
        counter += 1

    page.on("console", on_console)
    with pytest.raises(Error) as exc_info:
        await page.wait_for_function(
            """() => {
            window['counter'] = (window['counter'] || 0) + 1;
            console.log(window['counter']);
        }""",
            polling=1,
            timeout=1000,
        )

    saved_counter = counter
    await page.wait_for_timeout(2000)  # Give it some time to produce more logs.

    assert "Timeout 1000ms exceeded" in exc_info.value.message
    assert counter == saved_counter


async def test_should_throw_on_polling_mutation(page: Page) -> None:
    with pytest.raises(Error) as exc_info:
        await page.wait_for_function("() => true", polling="mutation")  # type: ignore
    assert "Unknown polling option: mutation" in exc_info.value.message
