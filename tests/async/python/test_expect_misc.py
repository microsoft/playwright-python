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

from playwright.async_api import Page, expect


async def test_to_have_css_should_support_pseudo_element(page: Page) -> None:
    await page.set_content(
        """
      <style>
        #node::before {
          color: rgb(255, 0, 0);
          content: "Text content";
        }
      </style>
      <div id=node></div>
    """
    )
    locator = page.locator("#node")
    await expect(locator).to_have_css("color", "rgb(255, 0, 0)", pseudo="before")
    with pytest.raises(AssertionError):
        await expect(locator).not_to_have_css(
            "color", "rgb(255, 0, 0)", pseudo="before", timeout=100
        )
