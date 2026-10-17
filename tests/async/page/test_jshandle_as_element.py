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

"""Port of tests/page/jshandle-as-element.spec.ts."""

from playwright.async_api import Page


async def test_JH_001_should_work_smoke(page: Page) -> None:
    a_handle = await page.evaluate_handle("() => document.body")
    element = a_handle.as_element()
    assert element


async def test_JH_002_should_return_null_for_non_elements(page: Page) -> None:
    a_handle = await page.evaluate_handle("() => 2")
    element = a_handle.as_element()
    assert not element


async def test_JH_003_should_return_element_handle_for_text_nodes(page: Page) -> None:
    await page.set_content("<div>ee!</div>")
    a_handle = await page.evaluate_handle(
        "() => document.querySelector('div').firstChild"
    )
    element = a_handle.as_element()
    assert element
    assert await page.evaluate("e => e.nodeType === Node.TEXT_NODE", element)


async def test_JH_004_should_work_with_nullified_node(page: Page) -> None:
    await page.set_content("<section>test</section>")
    await page.evaluate("delete Node")
    handle = await page.evaluate_handle("() => document.querySelector('section')")
    element = handle.as_element()
    assert element is not None
