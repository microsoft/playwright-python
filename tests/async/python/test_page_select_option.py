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

import pytest

from playwright.async_api import Page, TimeoutError
from tests.server import Server


async def test_select_option_should_select_single_option_by_empty_label(
    page: Page, server: Server
) -> None:
    await page.set_content(
        """
        <select>
            <option value="indigo">Indigo</option>
            <option value="violet"></option>
        </select>
    """
    )
    assert await page.locator("select").input_value() == "indigo"
    await page.select_option("select", label="")
    assert await page.locator("select").input_value() == "violet"


async def test_select_option_should_select_single_option_by_index_0(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    await page.select_option("select", index=0)
    assert await page.evaluate("result.onInput") == ["black"]


async def test_select_option_should_select_option_with_empty_value(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        """
        <select>
            <option value="first">First</option>
            <option value="">Second</option>
        </select>
    """
    )
    assert await page.locator("select").input_value() == "first"
    await page.select_option("select", value="")
    assert await page.locator("select").input_value() == ""


async def test_select_option_should_return_on_no_matched_values(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    with pytest.raises(TimeoutError) as exc_info:
        await page.select_option("select", ["42", "abc"], timeout=1000)
    assert "Timeout 1000" in exc_info.value.message
