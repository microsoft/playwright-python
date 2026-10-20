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

"""Port of tests/page/locator-wait-for-function.spec.ts."""

from typing import Any, Awaitable, Callable

import pytest

from playwright.async_api import Error, Page


async def test_LO_183_should_wait_for_an_attribute_to_appear(page: Page) -> None:
    await page.set_content("<button id=toggle>Menu</button>")
    await page.evaluate(
        "() => window.builtins.setTimeout(() => document.querySelector('#toggle').setAttribute('aria-expanded', 'true'), 1000)"
    )
    await page.locator("#toggle").wait_for_function(
        "element => element.hasAttribute('aria-expanded')"
    )


async def test_LO_184_should_return_immediately_when_already_truthy(
    page: Page,
) -> None:
    await page.set_content("<div id=target>yes</div>")
    locator = page.locator("#target")
    # Typed as returning a value, so that the result can be checked.
    wait_for_function: Callable[..., Awaitable[Any]] = locator.wait_for_function
    assert await wait_for_function("element => element.textContent === 'yes'") is None


async def test_LO_185_should_accept_element_handle_arguments(page: Page) -> None:
    await page.set_content("<div id=a></div><div id=b>value</div>")
    handle = await page.query_selector("#b")
    await page.locator("#a").wait_for_function(
        "(element, other) => other.textContent === 'value'", arg=handle
    )


async def test_LO_186_should_accept_string_expression(page: Page) -> None:
    await page.set_content("<div id=target>yes</div>")
    await page.locator("#target").wait_for_function(
        "element => element.textContent === 'yes'"
    )


async def test_LO_187_should_resolve_a_promise_returned_by_the_predicate(
    page: Page,
) -> None:
    await page.set_content("<div id=target>yes</div>")
    await page.locator("#target").wait_for_function(
        "async element => element.textContent === 'yes'"
    )


async def test_LO_188_should_wait_for_element_to_appear_and_survive_rerender(
    page: Page,
) -> None:
    await page.set_content("<span>nothing here</span>")
    await page.evaluate(
        """() => {
    let count = 0;
    let prev = null;
    const tick = () => {
      ++count;
      const next = document.createElement('div');
      next.id = 'target';
      next.textContent = String(count);
      if (prev)
        prev.remove();
      document.body.appendChild(next);
      prev = next;
      if (count < 3)
        window.builtins.setTimeout(tick, 500);
    };
    window.builtins.setTimeout(tick, 500);
  }"""
    )
    await page.locator("#target").wait_for_function(
        "element => element.textContent === '3'"
    )


async def test_LO_189_should_throw_when_predicate_throws(page: Page) -> None:
    await page.set_content("<div id=target>no</div>")
    with pytest.raises(Error) as exc_info:
        await page.locator("#target").wait_for_function(
            """() => {
    throw new Error('oh my');
  }"""
        )
    assert "oh my" in exc_info.value.message


async def test_LO_190_should_throw_on_strict_mode_violation(page: Page) -> None:
    await page.set_content("<div class=x>1</div><div class=x>2</div>")
    with pytest.raises(Error) as exc_info:
        await page.locator("div.x").wait_for_function("() => true")
    assert "strict mode violation" in exc_info.value.message
