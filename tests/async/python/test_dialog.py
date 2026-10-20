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

from playwright.async_api import Browser


async def test_dismiss_should_swallow_target_closed_error(browser: Browser) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    async with page.expect_event("dialog") as dialog_info:
        await page.evaluate("() => setTimeout(() => alert('hello'), 0)", None)
    dialog = await dialog_info.value
    await page.close()
    # Dialog.dismiss should be a no-op once the target is closed.
    await dialog.dismiss()
    await context.close()
