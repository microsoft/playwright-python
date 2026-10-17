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

"""Port of tests/page/page-click-timeout-2.spec.ts."""

import pytest

from playwright.async_api import Error, Page
from tests.server import Server


async def test_CL_114_should_timeout_waiting_for_display_none_to_be_gone(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    await page.eval_on_selector("button", "b => b.style.display = 'none'")
    with pytest.raises(Error) as exc_info:
        await page.click("button", timeout=5000)
    assert "Page.click: Timeout 5000ms exceeded." in exc_info.value.message
    assert (
        "waiting for element to be visible, enabled and stable"
        in exc_info.value.message
    )
    assert "element is not visible" in exc_info.value.message
    assert "retrying click action" in exc_info.value.message


async def test_CL_115_should_timeout_waiting_for_visibility_hidden_to_be_gone(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    await page.eval_on_selector("button", "b => b.style.visibility = 'hidden'")
    with pytest.raises(Error) as exc_info:
        await page.click("button", timeout=5000)
    assert "Page.click: Timeout 5000ms exceeded." in exc_info.value.message
    assert (
        "waiting for element to be visible, enabled and stable"
        in exc_info.value.message
    )
    assert "element is not visible" in exc_info.value.message
    assert "retrying click action" in exc_info.value.message
