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

"""Port of tests/page/page-click-react.spec.ts."""

import pytest

from playwright.async_api import Error, Page
from tests.server import Server


async def test_CL_106_should_timeout_when_click_opens_alert(page: Page) -> None:
    async with page.expect_event("dialog") as dialog_info:
        await page.set_content("<div onclick='window.alert(123)'>Click me</div>")
        with pytest.raises(Error) as exc_info:
            await page.click("div", timeout=3000)
        assert "Page.click: Timeout 3000ms exceeded." in exc_info.value.message
    dialog = await dialog_info.value
    await dialog.dismiss()


async def test_CL_107_should_not_retarget_when_element_changes_on_hover(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/react.html")
    await page.evaluate(
        """() => {
    renderComponent(e('div', {}, [e(MyButton, { name: 'button1', renameOnHover: true }), e(MyButton, { name: 'button2' })]));
  }"""
    )
    await page.click("text=button1")
    assert await page.evaluate("window.button1") is True
    assert await page.evaluate("window.button2") is None


async def test_CL_108_should_not_retarget_when_element_is_recycled_on_hover(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/react.html")
    await page.evaluate(
        """() => {
    function shuffle() {
      renderComponent(e('div', {}, [e(MyButton, { name: 'button2' }), e(MyButton, { name: 'button1' })]));
    }
    renderComponent(e('div', {}, [e(MyButton, { name: 'button1', onHover: shuffle }), e(MyButton, { name: 'button2' })]));
  }"""
    )
    await page.click("text=button1")
    assert await page.evaluate("window.button1") is None
    assert await page.evaluate("window.button2") is True
