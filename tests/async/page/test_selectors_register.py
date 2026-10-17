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

"""Port of tests/page/selectors-register.spec.ts."""

from playwright.async_api import Page, Selectors

from ..utils import Utils

# The engines are registered on the session's playwright.selectors, so a test that
# runs again in the same session finds its engine already registered: register them
# through utils.register_selector_engine, which ignores that error.


async def test_SE_154_text_content_should_be_atomic(
    selectors: Selectors, page: Page, utils: Utils
) -> None:
    create_dummy_selector = """({
      query(root, selector) {
        const result = root.querySelector(selector);
        if (result)
          void Promise.resolve().then(() => result.textContent = 'modified');
        return result;
      },
      queryAll(root, selector) {
        const result = Array.from(root.querySelectorAll(selector));
        for (const e of result)
          void Promise.resolve().then(() => e.textContent = 'modified');
        return result;
      }
    })"""
    await utils.register_selector_engine(
        selectors, "textContent", create_dummy_selector
    )
    await page.goto("data:text/html,<div>Hello</div>")
    tc = await page.text_content("textContent=div")
    assert tc == "Hello"
    assert (
        await page.evaluate("() => document.querySelector('div').textContent")
        == "modified"
    )


async def test_SE_155_inner_text_should_be_atomic(
    selectors: Selectors, page: Page, utils: Utils
) -> None:
    create_dummy_selector = """({
      query(root, selector) {
        const result = root.querySelector(selector);
        if (result)
          void Promise.resolve().then(() => result.textContent = 'modified');
        return result;
      },
      queryAll(root, selector) {
        const result = Array.from(root.querySelectorAll(selector));
        for (const e of result)
          void Promise.resolve().then(() => e.textContent = 'modified');
        return result;
      }
    })"""
    await utils.register_selector_engine(selectors, "innerText", create_dummy_selector)
    await page.goto("data:text/html,<div>Hello</div>")
    tc = await page.inner_text("innerText=div")
    assert tc == "Hello"
    assert (
        await page.evaluate("() => document.querySelector('div').innerText")
        == "modified"
    )


async def test_SE_156_inner_html_should_be_atomic(
    selectors: Selectors, page: Page, utils: Utils
) -> None:
    create_dummy_selector = """({
      query(root, selector) {
        const result = root.querySelector(selector);
        if (result)
          void Promise.resolve().then(() => result.textContent = 'modified');
        return result;
      },
      queryAll(root, selector) {
        const result = Array.from(root.querySelectorAll(selector));
        for (const e of result)
          void Promise.resolve().then(() => e.textContent = 'modified');
        return result;
      }
    })"""
    await utils.register_selector_engine(selectors, "innerHTML", create_dummy_selector)
    await page.goto("data:text/html,<div>Hello<span>world</span></div>")
    tc = await page.inner_html("innerHTML=div")
    assert tc == "Hello<span>world</span>"
    assert (
        await page.evaluate("() => document.querySelector('div').innerHTML")
        == "modified"
    )


async def test_SE_157_get_attribute_should_be_atomic(
    selectors: Selectors, page: Page, utils: Utils
) -> None:
    create_dummy_selector = """({
      query(root, selector) {
        const result = root.querySelector(selector);
        if (result)
          void Promise.resolve().then(() => result.setAttribute('foo', 'modified'));
        return result;
      },
      queryAll(root, selector) {
        const result = Array.from(root.querySelectorAll(selector));
        for (const e of result)
          void Promise.resolve().then(() => e.setAttribute('foo', 'modified'));
        return result;
      }
    })"""
    await utils.register_selector_engine(
        selectors, "getAttribute", create_dummy_selector
    )
    await page.goto("data:text/html,<div foo=hello></div>")
    tc = await page.get_attribute("getAttribute=div", "foo")
    assert tc == "hello"
    assert (
        await page.evaluate("() => document.querySelector('div').getAttribute('foo')")
        == "modified"
    )


async def test_SE_158_is_visible_should_be_atomic(
    selectors: Selectors, page: Page, utils: Utils
) -> None:
    create_dummy_selector = """({
      query(root, selector) {
        const result = root.querySelector(selector);
        if (result)
          void Promise.resolve().then(() => result.style.display = 'none');
        return result;
      },
      queryAll(root, selector) {
        const result = Array.from(root.querySelectorAll(selector));
        for (const e of result)
          void Promise.resolve().then(() => e.style.display = 'none');
        return result;
      }
    })"""
    await utils.register_selector_engine(selectors, "isVisible", create_dummy_selector)
    await page.goto("data:text/html,<div>Hello</div>")
    result = await page.is_visible("isVisible=div")
    assert result is True
    assert (
        await page.evaluate("() => document.querySelector('div').style.display")
        == "none"
    )


async def test_SE_159_should_take_java_style_string(
    selectors: Selectors, page: Page, utils: Utils
) -> None:
    create_dummy_selector = """{
      query(root, selector) {
        return root.querySelector(selector);
      },
      queryAll(root, selector) {
        return root.querySelectorAll(selector);
      }
    }"""
    await utils.register_selector_engine(
        selectors, "objectLiteral", create_dummy_selector
    )
    await page.goto("data:text/html,<div>Hello</div>")
    await page.text_content("objectLiteral=div")
