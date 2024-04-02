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

import pytest

from playwright.async_api import Error, Page, Playwright


async def test_should_use_data_test_id_in_strict_errors(
    page: Page, playwright: Playwright
) -> None:
    playwright.selectors.set_test_id_attribute("data-custom-id")
    try:
        await page.set_content(
            """
          <div>
            <div></div>
            <div>
              <div></div>
              <div></div>
            </div>
          </div>
          <div>
            <div class='foo bar:0' data-custom-id='One'>
            </div>
            <div class='foo bar:1' data-custom-id='Two'>
            </div>
          </div>
        """
        )
        with pytest.raises(Error) as exc_info:
            await page.locator(".foo").hover(timeout=200)
        assert "strict mode violation" in exc_info.value.message
        assert '<div class="foo bar:0' in exc_info.value.message
        assert '<div class="foo bar:1' in exc_info.value.message
        assert 'aka get_by_test_id("One")' in exc_info.value.message
        assert 'aka get_by_test_id("Two")' in exc_info.value.message
    finally:
        playwright.selectors.set_test_id_attribute("data-testid")
