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

"""Port of tests/page/page-click-timeout-1.spec.ts."""

import pytest

from playwright.async_api import Error, Page


async def test_CL_111_should_timeout_waiting_for_button_to_be_enabled(
    page: Page,
) -> None:
    await page.set_content(
        '<button onclick="javascript:window.__CLICKED=true;" disabled><span>Click target</span></button>'
    )
    with pytest.raises(Error) as exc_info:
        await page.click("text=Click target", timeout=3000)
    assert await page.evaluate("window.__CLICKED") is None
    assert "Page.click: Timeout 3000ms exceeded." in exc_info.value.message
    assert "element is not enabled" in exc_info.value.message
    assert "retrying click action" in exc_info.value.message


async def test_CL_112_should_timeout_waiting_for_inert_element_to_become_non_inert(
    page: Page,
) -> None:
    await page.set_content(
        '<div inert><button onclick="javascript:window.__CLICKED=true;">Click target</button></div>'
    )
    with pytest.raises(Error) as exc_info:
        await page.click("text=Click target", timeout=3000)
    assert await page.evaluate("window.__CLICKED") is None
    assert "Page.click: Timeout 3000ms exceeded." in exc_info.value.message
    assert "element is inert" in exc_info.value.message
    assert "retrying click action" in exc_info.value.message


async def test_CL_113_should_timeout_waiting_for_element_outside_of_a_modal_dialog(
    page: Page,
) -> None:
    await page.set_content(
        """
    <button onclick="javascript:window.__CLICKED=true;">Click target</button>
    <dialog id=dialog><button>Inside</button></dialog>
    <script>
      document.getElementById('dialog').showModal();
    </script>
  """
    )
    with pytest.raises(Error) as exc_info:
        await page.click("text=Click target", timeout=3000)
    assert await page.evaluate("window.__CLICKED") is None
    assert "Page.click: Timeout 3000ms exceeded." in exc_info.value.message
    assert "element is inert" in exc_info.value.message
