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

from playwright._impl._browser import Browser
from playwright._impl._errors import Error
from playwright._impl._selectors import Selectors
from playwright.async_api import Page


async def test_should_work_with_internal_and(page: Page) -> None:
    await page.set_content(
        """
        <div class=foo>hello</div><div class=bar>world</div>
        <span class=foo>hello2</span><span class=bar>world2</span>
    """
    )
    assert (
        await page.eval_on_selector_all(
            'div >> internal:and="span"', "els => els.map(e => e.textContent)"
        )
    ) == []
    assert (
        await page.eval_on_selector_all(
            'div >> internal:and=".foo"', "els => els.map(e => e.textContent)"
        )
    ) == ["hello"]
    assert (
        await page.eval_on_selector_all(
            'div >> internal:and=".bar"', "els => els.map(e => e.textContent)"
        )
    ) == ["world"]
    assert (
        await page.eval_on_selector_all(
            'span >> internal:and="span"', "els => els.map(e => e.textContent)"
        )
    ) == ["hello2", "world2"]
    assert (
        await page.eval_on_selector_all(
            '.foo >> internal:and="div"', "els => els.map(e => e.textContent)"
        )
    ) == ["hello"]
    assert (
        await page.eval_on_selector_all(
            '.bar >> internal:and="span"', "els => els.map(e => e.textContent)"
        )
    ) == ["world2"]


async def test_should_throw_already_registered_error_when_registering(
    selectors: Selectors,
    browser: Browser,
) -> None:
    create_tag_selector = """
    () => ({
        query(root, selector) {
            return root.querySelector(selector);
        },
        queryAll(root, selector) {
            return Array.from(root.querySelectorAll(selector));
        }
    })
    """
    name = f"alreadyRegistered-{browser.browser_type.name}"
    await selectors.register(name, create_tag_selector)
    with pytest.raises(
        Error,
        match=f'Selectors.register: "{name}" selector engine has been already registered',
    ):
        await selectors.register(name, create_tag_selector)
