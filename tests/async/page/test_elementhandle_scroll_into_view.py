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

"""Port of tests/page/elementhandle-scroll-into-view.spec.ts."""

import asyncio

import pytest

from playwright.async_api import Error, Page
from tests.server import Server


async def test_EH_093_should_work_smoke(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/offscreenbuttons.html")
    for i in range(11):
        button = await page.query_selector(f"#btn{i}")
        assert button
        before = await button.evaluate(
            "button => button.getBoundingClientRect().right - window.innerWidth"
        )
        assert before == 10 * i
        await button.scroll_into_view_if_needed()
        after = await button.evaluate(
            "button => button.getBoundingClientRect().right - window.innerWidth"
        )
        assert (after <= 0) is True
        await page.evaluate("() => window.scrollTo(0, 0)")


async def test_EH_094_should_throw_for_detached_element(page: Page) -> None:
    await page.set_content("<div>Hello</div>")
    div = await page.query_selector("div")
    assert div
    await div.evaluate("div => div.remove()")
    with pytest.raises(Error) as exc_info:
        await div.scroll_into_view_if_needed()
    assert "Element is not attached to the DOM" in exc_info.value.message


async def _test_waiting(page: Page, after: str) -> None:
    div = await page.query_selector("div")
    assert div
    done = False

    async def scroll() -> None:
        nonlocal done
        await div.scroll_into_view_if_needed()
        done = True

    async def change() -> None:
        await page.wait_for_timeout(1000)
        assert done is False
        await div.evaluate(after)

    await asyncio.gather(scroll(), change())
    assert done is True


async def test_EH_095_should_wait_for_display_none_to_become_visible(
    page: Page,
) -> None:
    await page.set_content('<div style="display:none">Hello</div>')
    await _test_waiting(page, "div => div.style.display = 'block'")


async def test_EH_096_should_scroll_display_contents_into_view(
    page: Page, browser_name: str, browser_major_version: int
) -> None:
    if browser_name == "chromium" and browser_major_version < 105:
        pytest.skip(
            "Needs https://chromium-review.googlesource.com/c/chromium/src/+/3758670"
        )

    await page.set_content(
        """
    <style>
      html, body { margin: 0; padding: 0; width: 100%; height: 100%; }
      ::-webkit-scrollbar { display: none; }
      * { scrollbar-width: none; }
    </style>
    <div id=container style="width:200px;height:200px;overflow:scroll;border:1px solid black;">
      <div style="margin-top:500px;background:red;">
        <div style="height:50px;width:100px;background:cyan;">
          <div id=target style="display:contents">Hello</div>
        </div>
      <div>
    </div>
  """
    )
    div = await page.query_selector("#target")
    assert div
    await div.scroll_into_view_if_needed()
    scroll_top = await page.eval_on_selector("#container", "e => e.scrollTop")
    assert abs(scroll_top - 350) < 1


async def test_EH_097_should_work_for_visibility_hidden_element(page: Page) -> None:
    await page.set_content('<div style="visibility:hidden">Hello</div>')
    div = await page.query_selector("div")
    assert div
    await div.scroll_into_view_if_needed()


async def test_EH_098_should_work_for_zero_sized_element(page: Page) -> None:
    await page.set_content('<div style="height:0">Hello</div>')
    div = await page.query_selector("div")
    assert div
    await div.scroll_into_view_if_needed()


async def test_EH_099_should_wait_for_nested_display_none_to_become_visible(
    page: Page,
) -> None:
    await page.set_content('<span style="display:none"><div>Hello</div></span>')
    await _test_waiting(page, "div => div.parentElement.style.display = 'block'")


async def test_EH_100_should_wait_for_element_to_stop_moving(page: Page) -> None:
    await page.set_content(
        """
    <style>
      @keyframes move {
        from { margin-left: 0; }
        to { margin-left: 200px; }
      }
      div.animated {
        animation: 2s linear 0s infinite alternate move;
      }
    </style>
    <div class=animated>moving</div>
    """
    )
    await _test_waiting(page, "div => div.classList.remove('animated')")


async def test_EH_101_should_timeout_waiting_for_visible(page: Page) -> None:
    await page.set_content('<div style="display:none">Hello</div>')
    div = await page.query_selector("div")
    assert div
    with pytest.raises(Error) as exc_info:
        await div.scroll_into_view_if_needed(timeout=3000)
    assert "element is not visible" in exc_info.value.message
    assert "retrying scroll into view action" in exc_info.value.message
