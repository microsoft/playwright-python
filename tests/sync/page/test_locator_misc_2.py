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

from typing import Any, Callable, List

import pytest

from playwright.sync_api import Error, Page, expect
from tests.server import Server


def test_LO_140_should_press_smoke(page: Page) -> None:
    page.set_content("<input type='text' />")
    page.locator("input").press("h")
    assert page.eval_on_selector("input", "input => input.value") == "h"


def test_LO_141_should_scroll_into_view(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/offscreenbuttons.html")
    for i in range(11):
        button = page.locator(f"#btn{i}")
        before = button.evaluate(
            """button => {
      return button.getBoundingClientRect().right - window.innerWidth;
    }"""
        )
        assert before == 10 * i
        button.scroll_into_view_if_needed()
        after = button.evaluate(
            """button => {
      return button.getBoundingClientRect().right - window.innerWidth;
    }"""
        )
        assert (after <= 0) is True
        page.evaluate("() => window.scrollTo(0, 0)")


def test_LO_142_should_scroll_zero_sized_element_into_view(page: Page) -> None:
    page.set_content(
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
    assert page.locator("#lazyload").bounding_box() == {
        "x": 0,
        "y": 2020,
        "width": 1280,
        "height": 0,
    }
    page.locator("#lazyload").scroll_into_view_if_needed()
    expect(page.locator("#lazyload")).to_have_text("LAZY LOADED CONTENT")
    assert page.locator("#lazyload").bounding_box() == {
        "x": 0,
        "y": 720,
        "width": 1280,
        "height": 20,
    }


def test_LO_143_should_select_textarea(
    page: Page, server: Server, browser_name: str
) -> None:
    page.goto(server.PREFIX + "/input/textarea.html")
    textarea = page.locator("textarea")
    textarea.evaluate("textarea => textarea.value = 'some value'")
    textarea.select_text()
    assert page.evaluate("() => window.getSelection().toString()") == "some value"


def test_LO_144_should_type(page: Page) -> None:
    page.set_content("<input type='text' />")
    page.locator("input").type("hello")
    assert page.eval_on_selector("input", "input => input.value") == "hello"


def test_LO_145_should_press_sequentially(page: Page) -> None:
    page.set_content("<input type='text' />")
    page.locator("input").press_sequentially("hello")
    assert page.eval_on_selector("input", "input => input.value") == "hello"


def test_LO_146_should_take_screenshot(
    page: Page,
    server: Server,
    browser_name: str,
    headless: bool,
    assert_to_be_golden: Callable[[bytes, str], None],
) -> None:
    if browser_name == "firefox" and not headless:
        pytest.skip("headed firefox")
    page.set_viewport_size({"width": 500, "height": 500})
    page.goto(server.PREFIX + "/grid.html")
    page.evaluate("() => window.scrollBy(50, 100)")
    element = page.locator(".box:nth-of-type(3)")
    screenshot = element.screenshot()
    assert_to_be_golden(screenshot, "screenshot-element-bounding-box.png")


def test_LO_147_should_return_bounding_box(page: Page, server: Server) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.goto(server.PREFIX + "/grid.html")
    element = page.locator(".box:nth-of-type(13)")
    box = element.bounding_box()
    assert box == {"x": 100, "y": 50, "width": 50, "height": 50}


def test_LO_148_should_wait_for(
    page: Page, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_content("<div></div>")
    locator = page.locator("span")

    def wait_for() -> None:
        locator.wait_for()

    def add_span() -> None:
        page.eval_on_selector("div", "div => div.innerHTML = '<span>target</span>'")

    sync_gather(wait_for, add_span)
    expect(locator).to_have_text("target")


def test_LO_149_should_wait_for_hidden(
    page: Page, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_content("<div><span>target</span></div>")
    locator = page.locator("span")

    def wait_for_hidden() -> None:
        locator.wait_for(state="hidden")

    def remove_span() -> None:
        page.eval_on_selector("div", "div => div.innerHTML = ''")

    sync_gather(wait_for_hidden, remove_span)


def test_LO_150_should_combine_visible_with_other_selectors(page: Page) -> None:
    page.set_content(
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
    expect(locator).to_have_text("visible data2")
    expect(page.locator(".item >> visible=true >> text=data3")).to_have_text(
        "visible data3"
    )


def test_LO_151_should_support_filter_visible(page: Page) -> None:
    page.set_content(
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
    expect(locator).to_have_text("visible data2")
    expect(
        page.locator(".item").filter(visible=True).get_by_text("data3")
    ).to_have_text("visible data3")
    expect(
        page.locator(".item").filter(visible=False).get_by_text("data1")
    ).to_have_text("Hidden data1")


def test_LO_152_should_support_visible(page: Page) -> None:
    page.set_content(
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
    expect(locator).to_have_text("visible data2")
    expect(page.locator(".item").visible.get_by_text("data3")).to_have_text(
        "visible data3"
    )
    expect(page.locator(".item").visible).to_have_count(3)


def test_LO_153_locator_count_should_work_with_deleted_map_in_main_world(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/11254
    page.evaluate("Map = 1")
    page.locator("#searchResultTableDiv .x-grid3-row").count()
    expect(page.locator("#searchResultTableDiv .x-grid3-row")).to_have_count(0)


def test_LO_154_locator_locator_and_frame_locator_locator_should_accept_locator(
    page: Page,
) -> None:
    page.set_content(
        """
    <div><input value=outer></div>
    <iframe srcdoc="<div><input value=inner></div>"></iframe>
  """
    )

    input_locator = page.locator("input")
    assert input_locator.input_value() == "outer"
    assert page.locator("div").locator(input_locator).input_value() == "outer"
    assert page.frame_locator("iframe").locator(input_locator).input_value() == "inner"
    assert (
        page.frame_locator("iframe").locator("div").locator(input_locator).input_value()
        == "inner"
    )

    div_locator = page.locator("div")
    assert div_locator.locator("input").input_value() == "outer"
    assert (
        page.frame_locator("iframe").locator(div_locator).locator("input").input_value()
        == "inner"
    )


def test_LO_155_should_fill_programmatically_enabled_textarea(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/36307
    page.set_content(
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
    page.locator("button").click()
    page.locator("#text").fill("Hello")
    expect(page.locator("#text")).to_have_value("Hello")


def test_LO_156_press_should_throw_on_unknown_keys(page: Page, server: Server) -> None:
    # https://github.com/microsoft/playwright/issues/36697
    page.set_content("<input type='text' value='hello' />")
    locator = page.get_by_role("textbox")
    with pytest.raises(Error, match='Unknown key: "NotARealKey"'):
        locator.press("NotARealKey")
    with pytest.raises(Error, match='Unknown key: "ё"'):
        locator.press("ё")
    with pytest.raises(Error, match='Unknown key: "😊"'):
        locator.press("😊")
