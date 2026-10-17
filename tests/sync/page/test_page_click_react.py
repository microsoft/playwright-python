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

from playwright.sync_api import Error, Page
from tests.server import Server


def test_CL_106_should_timeout_when_click_opens_alert(page: Page) -> None:
    with page.expect_event("dialog") as dialog_info:
        page.set_content("<div onclick='window.alert(123)'>Click me</div>")
        with pytest.raises(Error) as exc_info:
            page.click("div", timeout=3000)
        assert "Page.click: Timeout 3000ms exceeded." in exc_info.value.message
    dialog = dialog_info.value
    dialog.dismiss()


def test_CL_107_should_not_retarget_when_element_changes_on_hover(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/react.html")
    page.evaluate(
        """() => {
    renderComponent(e('div', {}, [e(MyButton, { name: 'button1', renameOnHover: true }), e(MyButton, { name: 'button2' })]));
  }"""
    )
    page.click("text=button1")
    assert page.evaluate("window.button1") is True
    assert page.evaluate("window.button2") is None


def test_CL_108_should_not_retarget_when_element_is_recycled_on_hover(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/react.html")
    page.evaluate(
        """() => {
    function shuffle() {
      renderComponent(e('div', {}, [e(MyButton, { name: 'button2' }), e(MyButton, { name: 'button1' })]));
    }
    renderComponent(e('div', {}, [e(MyButton, { name: 'button1', onHover: shuffle }), e(MyButton, { name: 'button2' })]));
  }"""
    )
    page.click("text=button1")
    assert page.evaluate("window.button1") is None
    assert page.evaluate("window.button2") is True
