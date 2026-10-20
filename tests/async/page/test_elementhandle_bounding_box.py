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

"""Port of tests/page/elementhandle-bounding-box.spec.ts."""

import math
from typing import Dict

from playwright.async_api import FloatRect, Page
from tests.server import Server


def js_round(value: float) -> int:
    """Like JavaScript Math.round: rounds .5 up."""
    return math.floor(value + 0.5)


async def test_EH_001_should_work(page: Page, server: Server) -> None:
    await page.set_viewport_size({"width": 500, "height": 500})
    await page.goto(server.PREFIX + "/grid.html")
    element_handle = await page.query_selector(".box:nth-of-type(13)")
    assert element_handle
    box = await element_handle.bounding_box()
    assert box == {"x": 100, "y": 50, "width": 50, "height": 50}


async def test_EH_002_should_handle_nested_frames(page: Page, server: Server) -> None:
    await page.set_viewport_size({"width": 616, "height": 500})
    await page.goto(server.PREFIX + "/frames/nested-frames.html")
    nested_frame = page.frame_locator('[name="2frames"]').frame_locator("[name=dos]")
    element_handle = await nested_frame.locator("div").element_handle()
    box = await element_handle.bounding_box()
    assert box == {"x": 24, "y": 224, "width": 268, "height": 18}


async def test_EH_003_should_get_frame_box(page: Page) -> None:
    await page.set_viewport_size({"width": 250, "height": 250})
    await page.set_content(
        """<style>
  body {
      display: flex;
      height: 500px;
      margin: 0px;
  }
  body iframe {
      flex-shrink: 1;
      border: 0;
      background-color: green;
  }
  </style>
  <iframe></iframe>
  """
    )
    element_handle = await page.query_selector("iframe")
    assert element_handle
    box = await element_handle.bounding_box()
    assert box == {"x": 0, "y": 0, "width": 300, "height": 500}


async def test_EH_004_should_handle_scroll_offset_and_click(page: Page) -> None:
    await page.set_content(
        """
    <style>* { margin: 0; padding: 0; }</style>
    <div style="width:8000px; height:8000px;">
      <div id=target style="width:20px; height:20px; margin-left:230px; margin-top:340px;"
        onclick="window.__clicked = true">
      </div>
    </div>
  """
    )
    element_handle = await page.query_selector("#target")
    assert element_handle
    box1 = await element_handle.bounding_box()
    await page.evaluate("() => window.scrollBy(200, 300)")
    box2 = await element_handle.bounding_box()
    assert box1 == {"x": 230, "y": 340, "width": 20, "height": 20}
    assert box2 == {"x": 30, "y": 40, "width": 20, "height": 20}
    assert box2
    await page.mouse.click(box2["x"] + 10, box2["y"] + 10)
    assert await page.evaluate("() => window['__clicked']") is True


async def test_EH_005_should_return_null_for_invisible_elements(page: Page) -> None:
    await page.set_content('<div style="display:none">hi</div>')
    element = await page.query_selector("div")
    assert element
    assert await element.bounding_box() is None


async def test_EH_006_should_get_bounding_box_of_element_inside_a_cross_origin_iframe(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        f"""
    <div style="height:120px"></div>
    <iframe style="border:0;margin-left:30px;width:300px;height:200px" src="{server.CROSS_PROCESS_PREFIX}/input/button.html"></iframe>
  """
    )
    frame = page.frames[1]
    button = await frame.wait_for_selector("button")
    assert button
    iframe = await page.query_selector("iframe")
    assert iframe
    iframe_box = await iframe.bounding_box()
    assert iframe_box
    inner = await button.evaluate(
        "b => { const r = b.getBoundingClientRect(); return { x: r.left, y: r.top }; }"
    )
    box = await button.bounding_box()
    assert box
    assert js_round(box["x"]) == js_round(iframe_box["x"] + inner["x"])
    assert js_round(box["y"]) == js_round(iframe_box["y"] + inner["y"])


async def test_EH_007_should_force_a_layout(page: Page) -> None:
    await page.set_viewport_size({"width": 500, "height": 500})
    await page.set_content('<div style="width: 100px; height: 100px">hello</div>')
    element_handle = await page.query_selector("div")
    assert element_handle
    await page.evaluate("element => element.style.height = '200px'", element_handle)
    box = await element_handle.bounding_box()
    assert box == {"x": 8, "y": 8, "width": 100, "height": 200}


async def test_EH_008_should_work_with_svg_nodes(page: Page) -> None:
    await page.set_content(
        """
      <svg xmlns="http://www.w3.org/2000/svg" width="500" height="500">
        <rect id="theRect" x="30" y="50" width="200" height="300"></rect>
      </svg>
    """
    )
    element = await page.query_selector("#therect")
    assert element
    pw_bounding_box = await element.bounding_box()
    web_bounding_box = await page.evaluate(
        """e => {
    const rect = e.getBoundingClientRect();
    return { x: rect.x, y: rect.y, width: rect.width, height: rect.height };
  }""",
        element,
    )
    assert pw_bounding_box == web_bounding_box


async def test_EH_009_should_work_when_inline_box_child_is_outside_of_viewport(
    page: Page,
) -> None:
    await page.set_content(
        """
      <style>
      i {
        position: absolute;
        top: -1000px;
      }
      body {
        margin: 0;
        font-size: 12px;
      }
      </style>
      <span><i>woof</i><b>doggo</b></span>
    """
    )
    handle = await page.query_selector("span")
    assert handle
    box = await handle.bounding_box()
    assert box
    web_bounding_box = await handle.evaluate(
        """e => {
    const rect = e.getBoundingClientRect();
    return { x: rect.x, y: rect.y, width: rect.width, height: rect.height };
  }"""
    )

    def round_box(box: FloatRect) -> Dict[str, int]:
        return {
            "x": js_round(box["x"] * 100),
            "y": js_round(box["y"] * 100),
            "width": js_round(box["width"] * 100),
            "height": js_round(box["height"] * 100),
        }

    assert round_box(box) == round_box(web_bounding_box)
