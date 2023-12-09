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

from typing import Callable

from playwright.async_api import Page
from tests.server import Server
from tests.utils import must


async def test_should_screenshot_with_mask(
    page: Page, server: Server, assert_to_be_golden: Callable[[bytes, str], None]
) -> None:
    await page.set_viewport_size(
        {
            "width": 500,
            "height": 500,
        }
    )
    await page.goto(server.PREFIX + "/grid.html")
    assert_to_be_golden(
        await page.screenshot(mask=[page.locator("div").nth(5)]),
        "mask-should-work-with-page.png",
    )
    assert_to_be_golden(
        await page.locator("body").screenshot(mask=[page.locator("div").nth(5)]),
        "mask-should-work-with-locator.png",
    )
    assert_to_be_golden(
        await must(await page.query_selector("body")).screenshot(
            mask=[page.locator("div").nth(5)]
        ),
        "mask-should-work-with-element-handle.png",
    )
