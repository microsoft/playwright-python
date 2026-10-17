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

"""Port of tests/page/locator-misc-2.spec.ts."""

import asyncio
from typing import Callable

import pytest

from playwright.async_api import Error, Page, expect
from tests.server import Server


async def test_LO_140_should_press_smoke(page: Page) -> None:
    await page.set_content("<input type='text' />")
    await page.locator("input").press("h")
    assert await page.eval_on_selector("input", "input => input.value") == "h"


async def test_LO_141_should_scroll_into_view(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/offscreenbuttons.html")
    for i in range(11):
        button = page.locator(f"#btn{i}")
        before = await button.evaluate(
            """button => {
      return button.getBoundingClientRect().right - window.innerWidth;
    }"""
        )
        assert before == 10 * i
        await button.scroll_into_view_if_needed()
        after = await button.evaluate(
            """button => {
      return button.getBoundingClientRect().right - window.innerWidth;
    }"""
        )
        assert (after <= 0) is True
        await page.evaluate("() => window.scrollTo(0, 0)")


async def test_LO_142_should_scroll_zero_sized_element_into_view(page: Page) -> None:
    await page.set_content(
        """
    <style>
      html,body { margin: 0; padding: 0; }
      ::-webkit-scrollbar { display: none; }
      * { scrollbar-width: none; }
    </style>
    <div style="height: 2000px; text-align: center; border: 10px solid blue;">
      <h1>SCROLL DOWN</h1>
    </div>
    <div id=lazyload style="font-size:75px; background-color: green;"></div>
    <script>
      const lazyLoadElement = document.querySelector('#lazyload');
      const observer = new IntersectionObserver((entries) => {
        if (entries.some(entry => entry.isIntersecting)) {
          lazyLoadElement.textContent = 'LAZY LOADED CONTENT';
          lazyLoadElement.style.height = '20px';
          observer.disconnect();
        }
      });
      observer.observe(lazyLoadElement);
    </script>
  """
    )
    assert await page.locator("#lazyload").bounding_box() == {
        "x": 0,
        "y": 2020,
        "width": 1280,
        "height": 0,
    }
    await page.locator("#lazyload").scroll_into_view_if_needed()
    await expect(page.locator("#lazyload")).to_have_text("LAZY LOADED CONTENT")
    assert await page.locator("#lazyload").bounding_box() == {
        "x": 0,
        "y": 720,
        "width": 1280,
        "height": 20,
    }


async def test_LO_143_should_select_textarea(
    page: Page, server: Server, browser_name: str
) -> None:
    await page.goto(server.PREFIX + "/input/textarea.html")
    textarea = page.locator("textarea")
    await textarea.evaluate("textarea => textarea.value = 'some value'")
    await textarea.select_text()
    assert await page.evaluate("() => window.getSelection().toString()") == "some value"


async def test_LO_144_should_type(page: Page) -> None:
    await page.set_content("<input type='text' />")
    await page.locator("input").type("hello")
    assert await page.eval_on_selector("input", "input => input.value") == "hello"


async def test_LO_145_should_press_sequentially(page: Page) -> None:
    await page.set_content("<input type='text' />")
    await page.locator("input").press_sequentially("hello")
    assert await page.eval_on_selector("input", "input => input.value") == "hello"


async def test_LO_146_should_take_screenshot(
    page: Page,
    server: Server,
    browser_name: str,
    headless: bool,
    assert_to_be_golden: Callable[[bytes, str], None],
) -> None:
    if browser_name == "firefox" and not headless:
        pytest.skip("headed firefox")
    await page.set_viewport_size({"width": 500, "height": 500})
    await page.goto(server.PREFIX + "/grid.html")
    await page.evaluate("() => window.scrollBy(50, 100)")
    element = page.locator(".box:nth-of-type(3)")
    screenshot = await element.screenshot()
    assert_to_be_golden(screenshot, "screenshot-element-bounding-box.png")


async def test_LO_147_should_return_bounding_box(page: Page, server: Server) -> None:
    await page.set_viewport_size({"width": 500, "height": 500})
    await page.goto(server.PREFIX + "/grid.html")
    element = page.locator(".box:nth-of-type(13)")
    box = await element.bounding_box()
    assert box == {"x": 100, "y": 50, "width": 50, "height": 50}


async def test_LO_148_should_wait_for(page: Page) -> None:
    await page.set_content("<div></div>")
    locator = page.locator("span")

    async def wait_for() -> None:
        await locator.wait_for()

    async def add_span() -> None:
        await page.eval_on_selector(
            "div", "div => div.innerHTML = '<span>target</span>'"
        )

    await asyncio.gather(wait_for(), add_span())
    await expect(locator).to_have_text("target")


async def test_LO_149_should_wait_for_hidden(page: Page) -> None:
    await page.set_content("<div><span>target</span></div>")
    locator = page.locator("span")

    async def wait_for_hidden() -> None:
        await locator.wait_for(state="hidden")

    async def remove_span() -> None:
        await page.eval_on_selector("div", "div => div.innerHTML = ''")

    await asyncio.gather(wait_for_hidden(), remove_span())


async def test_LO_150_should_combine_visible_with_other_selectors(page: Page) -> None:
    await page.set_content(
        """<div>
  <div class="item" style="display: none">Hidden data0</div>
  <div class="item">visible data1</div>
  <div class="item" style="display: none">Hidden data1</div>
  <div class="item">visible data2</div>
  <div class="item" style="display: none">Hidden data1</div>
  <div class="item">visible data3</div>
  </div>"""
    )
    locator = page.locator(".item >> visible=true").nth(1)
    await expect(locator).to_have_text("visible data2")
    await expect(page.locator(".item >> visible=true >> text=data3")).to_have_text(
        "visible data3"
    )


async def test_LO_151_should_support_filter_visible(page: Page) -> None:
    await page.set_content(
        """<div>
    <div class="item" style="display: none">Hidden data0</div>
    <div class="item">visible data1</div>
    <div class="item" style="display: none">Hidden data1</div>
    <div class="item">visible data2</div>
    <div class="item" style="display: none">Hidden data2</div>
    <div class="item">visible data3</div>
    </div>
  """
    )
    locator = page.locator(".item").filter(visible=True).nth(1)
    await expect(locator).to_have_text("visible data2")
    await expect(
        page.locator(".item").filter(visible=True).get_by_text("data3")
    ).to_have_text("visible data3")
    await expect(
        page.locator(".item").filter(visible=False).get_by_text("data1")
    ).to_have_text("Hidden data1")


async def test_LO_152_should_support_visible(page: Page) -> None:
    await page.set_content(
        """<div>
    <div class="item" style="display: none">Hidden data0</div>
    <div class="item">visible data1</div>
    <div class="item" style="display: none">Hidden data1</div>
    <div class="item">visible data2</div>
    <div class="item" style="display: none">Hidden data2</div>
    <div class="item">visible data3</div>
    </div>
  """
    )
    locator = page.locator(".item").visible.nth(1)
    await expect(locator).to_have_text("visible data2")
    await expect(page.locator(".item").visible.get_by_text("data3")).to_have_text(
        "visible data3"
    )
    await expect(page.locator(".item").visible).to_have_count(3)


async def test_LO_153_locator_count_should_work_with_deleted_map_in_main_world(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/11254
    await page.evaluate("Map = 1")
    await page.locator("#searchResultTableDiv .x-grid3-row").count()
    await expect(page.locator("#searchResultTableDiv .x-grid3-row")).to_have_count(0)


async def test_LO_154_locator_locator_and_frame_locator_locator_should_accept_locator(
    page: Page,
) -> None:
    await page.set_content(
        """
    <div><input value=outer></div>
    <iframe srcdoc="<div><input value=inner></div>"></iframe>
  """
    )

    input_locator = page.locator("input")
    assert await input_locator.input_value() == "outer"
    assert await page.locator("div").locator(input_locator).input_value() == "outer"
    assert (
        await page.frame_locator("iframe").locator(input_locator).input_value()
        == "inner"
    )
    assert (
        await page.frame_locator("iframe")
        .locator("div")
        .locator(input_locator)
        .input_value()
        == "inner"
    )

    div_locator = page.locator("div")
    assert await div_locator.locator("input").input_value() == "outer"
    assert (
        await page.frame_locator("iframe")
        .locator(div_locator)
        .locator("input")
        .input_value()
        == "inner"
    )


async def test_LO_155_should_fill_programmatically_enabled_textarea(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/36307
    await page.set_content(
        """
    <button>Enable</button>
    <form>
      <textarea id="text" disabled></textarea>
    </form>
    <script>
      document.querySelector('button').addEventListener('click', () => {
        document.querySelector('#text').disabled = false;
      });
    </script>
  """
    )
    await page.locator("button").click()
    await page.locator("#text").fill("Hello")
    await expect(page.locator("#text")).to_have_value("Hello")


async def test_LO_156_press_should_throw_on_unknown_keys(
    page: Page, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/36697
    await page.set_content("<input type='text' value='hello' />")
    locator = page.get_by_role("textbox")
    with pytest.raises(Error, match='Unknown key: "NotARealKey"'):
        await locator.press("NotARealKey")
    with pytest.raises(Error, match='Unknown key: "ё"'):
        await locator.press("ё")
    with pytest.raises(Error, match='Unknown key: "😊"'):
        await locator.press("😊")
