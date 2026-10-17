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

"""Port of tests/library/browsercontext-strict.spec.ts."""

from typing import Awaitable, Callable

import pytest

from playwright.async_api import BrowserContext, Error, Page


@pytest.fixture
async def strict_page(
    context_factory: Callable[..., Awaitable[BrowserContext]],
) -> Page:
    """The page of the "strict context mode" describe: a context with strictSelectors."""
    context = await context_factory(strict_selectors=True)
    return await context.new_page()


async def test_SM_011_should_not_fail_page_text_content_in_non_strict_mode(
    page: Page,
) -> None:
    await page.set_content("<span>span1</span><div><span>target</span></div>")
    assert await page.text_content("span", strict=False) == "span1"


async def test_SM_012_strict_context_mode_should_fail_page_text_content_in_strict_mode(
    strict_page: Page,
) -> None:
    page = strict_page
    await page.set_content("<span>span1</span><div><span>target</span></div>")
    with pytest.raises(Error) as exc_info:
        await page.text_content("span")
    assert "strict mode violation" in exc_info.value.message


async def test_SM_013_strict_context_mode_should_fail_page_click_in_strict_mode(
    strict_page: Page,
) -> None:
    page = strict_page
    await page.set_content("<button>button1</button><button>target</button>")
    with pytest.raises(Error) as exc_info:
        await page.click("button")
    assert "strict mode violation" in exc_info.value.message


async def test_SM_014_strict_context_mode_should_opt_out_of_strict_mode(
    strict_page: Page,
) -> None:
    page = strict_page
    await page.set_content("<span>span1</span><div><span>target</span></div>")
    assert await page.text_content("span", strict=False) == "span1"
