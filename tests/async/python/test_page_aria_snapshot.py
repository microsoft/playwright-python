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


from playwright.async_api import Page, expect


async def test_normalize_should_return_python_locator_code(page: Page) -> None:
    await page.set_content('<button id="submit">Submit</button>')
    assert 'button "Submit" [ref=e2]' in await page.aria_snapshot(mode="ai")
    normalized = await page.get_by_ref("e2").normalize()
    assert str(normalized) == 'get_by_role("button", name="Submit")'
    await expect(normalized).to_have_text("Submit")
    # Locators that were not normalized keep the default representation.
    assert str(page.get_by_ref("e2")) == repr(page.get_by_ref("e2"))
