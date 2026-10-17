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

"""Port of tests/page/page-click.spec.ts."""

import asyncio
from typing import Any, Callable, List

import pytest

from playwright.async_api import Error, Page, expect
from tests.server import Server, TestServerRequest

from ..utils import Utils


async def give_it_a_chance_to_click(utils: Utils, page: Page) -> None:
    await utils.rafraf(page, 5)


async def poll_until_equal(
    page: Page, actual: Callable[[], Any], expected: Any, timeout: float = 5000
) -> None:
    """Port of `await expect.poll(actual).toEqual(expected)`."""
    deadline = asyncio.get_running_loop().time() + timeout / 1000
    while actual() != expected and asyncio.get_running_loop().time() < deadline:
        await page.wait_for_timeout(100)
    assert actual() == expected


async def test_CL_001_should_click_the_button_smoke(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    await page.click("button")
    assert await page.evaluate("result") == "Clicked"


async def test_CL_002_should_click_button_inside_frameset(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/frames/frameset.html")
    frame_element = await page.query_selector("frame")
    assert frame_element
    await frame_element.evaluate("frame => frame.src = '/input/button.html'")
    frame = await frame_element.content_frame()
    assert frame
    await frame.click("button")
    assert await frame.evaluate("result") == "Clicked"


async def test_CL_003_should_issue_clicks_in_parallel_in_page_and_popup(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/counter.html")
    async with page.expect_popup() as popup_info:
        await page.evaluate("() => window.open('/counter.html')")
    popup = await popup_info.value
    click_promises = []
    for i in range(21):
        if i % 3 == 0:
            click_promises.append(popup.locator("button").click())
        else:
            click_promises.append(page.locator("button").click())
    await asyncio.gather(*click_promises)
    assert await page.evaluate("() => window['count']") == 14
    assert await popup.evaluate("() => window['count']") == 7


async def test_CL_004_should_click_svg(page: Page) -> None:
    await page.set_content(
        """
    <svg height="100" width="100">
      <circle onclick="window.__CLICKED=42" cx="50" cy="50" r="40" stroke="black" stroke-width="3" fill="red" />
    </svg>
  """
    )
    await page.click("circle")
    assert await page.evaluate("__CLICKED") == 42


async def test_CL_005_should_click_the_button_if_window_node_is_removed(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    await page.evaluate("() => delete window.Node")
    await page.click("button")
    assert await page.evaluate("result") == "Clicked"


# @see https://github.com/GoogleChrome/puppeteer/issues/4281
async def test_CL_006_should_click_on_a_span_with_an_inline_element_inside(
    page: Page,
) -> None:
    await page.set_content(
        """
    <style>
    span::before {
      content: 'q';
    }
    </style>
    <span onclick='window.CLICKED=42'></span>
  """
    )
    await page.click("span")
    assert await page.evaluate("CLICKED") == 42


async def test_CL_007_should_click_the_aligned_1x1_div(page: Page) -> None:
    await page.set_content(
        '<div style="width: 1px; height: 1px;" onclick="window.__clicked = true"></div>'
    )
    await page.click("div")
    assert await page.evaluate("window.__clicked") is True


async def test_CL_008_should_click_the_half_aligned_1x1_div(page: Page) -> None:
    await page.set_content(
        '<div style="margin-left: 20.5px; margin-top: 11.5px; width: 1px; height: 1px;" onclick="window.__clicked = true"></div>'
    )
    await page.click("div")
    assert await page.evaluate("window.__clicked") is True


async def test_CL_009_should_click_the_unaligned_1x1_div_v1(page: Page) -> None:
    await page.set_content(
        '<div style="margin-left: 20.23px; margin-top: 11.65px; width: 1px; height: 1px;" onclick="window.__clicked = true"></div>'
    )
    await page.click("div")
    assert await page.evaluate("window.__clicked") is True


async def test_CL_010_should_click_the_unaligned_1x1_div_v2(page: Page) -> None:
    await page.set_content(
        '<div style="margin-left: 20.68px; margin-top: 11.13px; width: 1px; height: 1px;" onclick="window.__clicked = true"></div>'
    )
    await page.click("div")
    assert await page.evaluate("window.__clicked") is True


async def test_CL_011_should_click_the_unaligned_1x1_div_v3(page: Page) -> None:
    await page.set_content(
        '<div style="margin-left: 20.68px; margin-top: 11.52px; width: 1px; height: 1px;" onclick="window.__clicked = true"></div>'
    )
    await page.click("div")
    assert await page.evaluate("window.__clicked") is True


async def test_CL_012_should_click_the_unaligned_1x1_div_v4(page: Page) -> None:
    await page.set_content(
        '<div style="margin-left: 20.15px; margin-top: 11.24px; width: 1px; height: 1px;" onclick="window.__clicked = true"></div>'
    )
    await page.click("div")
    assert await page.evaluate("window.__clicked") is True


async def test_CL_013_should_click_the_button_after_navigation(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    await page.click("button")
    await page.goto(server.PREFIX + "/input/button.html")
    await page.click("button")
    assert await page.evaluate("result") == "Clicked"


async def test_CL_014_should_click_the_button_after_a_cross_origin_navigation(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    await page.click("button")
    await page.goto(server.CROSS_PROCESS_PREFIX + "/input/button.html")
    await page.click("button")
    assert await page.evaluate("result") == "Clicked"


async def test_CL_015_should_click_when_one_of_inline_box_children_is_outside_of_viewport(
    page: Page,
) -> None:
    await page.set_content(
        """
    <style>
    i {
      position: absolute;
      top: -1000px;
    }
    </style>
    <span onclick='window.CLICKED = 42;'><i>woof</i><b>doggo</b></span>
  """
    )
    await page.click("span")
    assert await page.evaluate("CLICKED") == 42


async def test_CL_016_should_select_the_text_by_triple_clicking(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/textarea.html")
    text = "This is the text that we are going to try to select. Let's see how it goes."
    await page.fill("textarea", text)
    await page.click("textarea", click_count=3)
    assert (
        await page.evaluate(
            """() => {
    const textarea = document.querySelector('textarea');
    return textarea.value.substring(textarea.selectionStart, textarea.selectionEnd);
  }"""
        )
        == text
    )


async def test_CL_017_should_click_offscreen_buttons(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/offscreenbuttons.html")
    messages: List[str] = []
    page.on("console", lambda msg: messages.append(msg.text))
    for i in range(11):
        # We might've scrolled to click a button - reset to (0, 0).
        await page.evaluate("() => window.scrollTo(0, 0)")
        await page.click(f"#btn{i}")
    assert messages == [
        "button #0 clicked",
        "button #1 clicked",
        "button #2 clicked",
        "button #3 clicked",
        "button #4 clicked",
        "button #5 clicked",
        "button #6 clicked",
        "button #7 clicked",
        "button #8 clicked",
        "button #9 clicked",
        "button #10 clicked",
    ]


async def test_CL_018_should_wait_for_visible_when_already_visible(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    await page.click("button")
    assert await page.evaluate("result") == "Clicked"


async def test_CL_019_should_not_wait_with_force(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    await page.eval_on_selector("button", "b => b.style.display = 'none'")
    with pytest.raises(Error) as exc_info:
        await page.click("button", force=True)
    assert "Element is not visible" in exc_info.value.message
    assert await page.evaluate("result") == "Was not clicked"


async def test_CL_020_should_wait_for_display_none_to_be_gone(
    page: Page, server: Server, utils: Utils
) -> None:
    done = False
    await page.goto(server.PREFIX + "/input/button.html")
    await page.eval_on_selector("button", "b => b.style.display = 'none'")

    async def click() -> None:
        nonlocal done
        await page.click("button", timeout=0)
        done = True

    clicked = asyncio.create_task(click())
    await give_it_a_chance_to_click(utils, page)
    assert await page.evaluate("result") == "Was not clicked"
    assert done is False
    await page.eval_on_selector("button", "b => b.style.display = 'block'")
    await clicked
    assert done is True
    assert await page.evaluate("result") == "Clicked"


async def test_CL_021_should_wait_for_visibility_hidden_to_be_gone(
    page: Page, server: Server, utils: Utils
) -> None:
    done = False
    await page.goto(server.PREFIX + "/input/button.html")
    await page.eval_on_selector("button", "b => b.style.visibility = 'hidden'")

    async def click() -> None:
        nonlocal done
        await page.click("button", timeout=0)
        done = True

    clicked = asyncio.create_task(click())
    await give_it_a_chance_to_click(utils, page)
    assert await page.evaluate("result") == "Was not clicked"
    assert done is False
    await page.eval_on_selector("button", "b => b.style.visibility = 'visible'")
    await clicked
    assert done is True
    assert await page.evaluate("result") == "Clicked"


async def test_CL_022_should_wait_for_visible_when_parent_is_hidden(
    page: Page, server: Server, utils: Utils
) -> None:
    done = False
    await page.goto(server.PREFIX + "/input/button.html")
    await page.eval_on_selector("button", "b => b.parentElement.style.display = 'none'")

    async def click() -> None:
        nonlocal done
        await page.click("button", timeout=0)
        done = True

    clicked = asyncio.create_task(click())
    await give_it_a_chance_to_click(utils, page)
    assert done is False
    await page.eval_on_selector(
        "button", "b => b.parentElement.style.display = 'block'"
    )
    await clicked
    assert done is True
    assert await page.evaluate("result") == "Clicked"


async def test_CL_023_should_click_wrapped_links(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/wrappedlink.html")
    await page.click("a")
    assert await page.evaluate("__clicked") is True


async def test_CL_024_should_click_on_checkbox_input_and_toggle(
    page: Page, server: Server, headless: bool
) -> None:
    await page.goto(server.PREFIX + "/input/checkbox.html")
    assert await page.evaluate("() => window['result'].check") is None
    await page.click("input#agree")
    assert await page.evaluate("() => window['result'].check") is True
    events: List[str] = await page.evaluate("() => window['result'].events")
    if not headless:
        events = [e for e in events if e != "mouseout" and e != "mouseleave"]
    assert events == [
        "mouseover",
        "mouseenter",
        "mousemove",
        "mousedown",
        "mouseup",
        "click",
        "input",
        "change",
    ]
    await page.click("input#agree")
    assert await page.evaluate("() => window['result'].check") is False


async def test_CL_025_should_click_on_checkbox_label_and_toggle(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/checkbox.html")
    assert await page.evaluate("() => window['result'].check") is None
    await page.click('label[for="agree"]')
    assert await page.evaluate("() => window['result'].check") is True
    assert await page.evaluate("() => window['result'].events") == [
        "click",
        "input",
        "change",
    ]
    await page.click('label[for="agree"]')
    assert await page.evaluate("() => window['result'].check") is False


async def test_CL_026_should_scroll_and_click_the_button(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/scrollable.html")
    await page.click("#button-5")
    assert (
        await page.evaluate("() => document.querySelector('#button-5').textContent")
        == "clicked"
    )
    await page.click("#button-80")
    assert (
        await page.evaluate("() => document.querySelector('#button-80').textContent")
        == "clicked"
    )


async def test_CL_027_should_scroll_and_click_the_button_with_smooth_scroll_behavior(
    page: Page, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/12370
    await page.goto(server.PREFIX + "/input/scrollable.html")
    await page.add_style_tag(content="html { scroll-behavior: smooth; }")
    for _ in range(5):
        await page.click("#button-80")
        assert (
            await page.evaluate(
                "() => document.querySelector('#button-80').textContent"
            )
            == "clicked"
        )
        await page.click("#button-20")
        assert (
            await page.evaluate(
                "() => document.querySelector('#button-20').textContent"
            )
            == "clicked"
        )


async def test_CL_028_should_double_click_the_button(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    await page.evaluate(
        """() => {
    window['double'] = false;
    const button = document.querySelector('button');
    button.addEventListener('dblclick', event => {
      window['double'] = true;
    });
  }"""
    )
    await page.dblclick("button")
    assert await page.evaluate("double") is True
    assert await page.evaluate("result") == "Clicked"


async def test_CL_029_should_click_a_partially_obscured_button(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    await page.evaluate(
        """() => {
    const button = document.querySelector('button');
    button.textContent = 'Some really long text that will go offscreen';
    button.style.position = 'absolute';
    button.style.left = '368px';
  }"""
    )
    await page.click("button")
    assert await page.evaluate("() => window['result']") == "Clicked"


async def test_CL_030_should_click_a_rotated_button(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/rotatedButton.html")
    await page.click("button")
    assert await page.evaluate("result") == "Clicked"


async def test_CL_031_should_fire_contextmenu_event_on_right_click(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/scrollable.html")
    await page.click("#button-8", button="right")
    assert (
        await page.evaluate("() => document.querySelector('#button-8').textContent")
        == "context menu"
    )


async def test_CL_032_should_click_links_which_cause_navigation(
    page: Page, server: Server
) -> None:
    # @see https://github.com/GoogleChrome/puppeteer/issues/206
    await page.set_content(f'<a href="{server.EMPTY_PAGE}">empty.html</a>')
    # This await should not hang.
    await page.click("a")


async def test_CL_033_should_not_wait_for_navigation_after_clicking_a_link_answered_with_204(
    page: Page, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/43279
    def handle(request: TestServerRequest) -> None:
        request.setResponseCode(204)
        request.finish()

    server.set_route("/204", handle)
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(f'<a href="{server.PREFIX}/204">link</a>')
    await page.click("a", timeout=5000)
    assert page.url == server.EMPTY_PAGE


async def test_CL_034_should_click_the_button_inside_an_iframe(
    page: Page, server: Server, utils: Utils
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content('<div style="width:100px;height:100px">spacer</div>')
    await utils.attach_frame(page, "button-test", server.PREFIX + "/input/button.html")
    frame = page.frames[1]
    button = await frame.query_selector("button")
    assert button
    await button.click()
    assert await frame.evaluate("() => window['result']") == "Clicked"


async def test_CL_035_should_click_the_button_with_fixed_position_inside_an_iframe(
    page: Page, server: Server, utils: Utils, browser_name: str
) -> None:
    if browser_name == "chromium":
        pytest.skip("fixme: chromium")

    # @see https://github.com/GoogleChrome/puppeteer/issues/4110
    # @see https://bugs.chromium.org/p/chromium/issues/detail?id=986390
    # @see https://chromium-review.googlesource.com/c/chromium/src/+/1742784
    await page.goto(server.EMPTY_PAGE)
    await page.set_viewport_size({"width": 500, "height": 500})
    await page.set_content('<div style="width:100px;height:2000px">spacer</div>')
    await utils.attach_frame(
        page, "button-test", server.CROSS_PROCESS_PREFIX + "/input/button.html"
    )
    frame = page.frames[1]
    await frame.eval_on_selector(
        "button", "button => button.style.setProperty('position', 'fixed')"
    )
    await frame.click("button")
    assert await frame.evaluate("() => window['result']") == "Clicked"


async def test_CL_036_should_click_the_button_behind_sticky_header(page: Page) -> None:
    await page.set_viewport_size({"width": 500, "height": 240})
    await page.set_content(
        """
    <style>
    * {
      padding: 0;
      margin: 0;
    }
    li {
      height: 80px;
      border: 1px solid black;
    }
    ol {
      padding-top: 160px;
    }
    div.fixed {
      position: fixed;
      z-index: 1001;
      width: 100%;
      background: red;
      height: 160px;
    }
    </style>

    <div class=fixed></div>

    <ol>
    <li>hi1</li><li>hi2</li><li>hi3</li><li>hi4</li><li>hi5</li><li>hi6</li><li>hi7</li><li>hi8</li>
    <li id=target onclick="window.__clicked = true">hi9</li>
    <li>hi10</li><li>hi11</li><li>hi12</li><li>hi13</li><li id=li14>hi14</li>
    </ol>
  """
    )
    await page.eval_on_selector("#li14", "e => e.scrollIntoView()")
    await page.click("#target")
    assert await page.evaluate("() => window['__clicked']") is True


async def test_CL_037_should_click_the_button_behind_position_absolute_header(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/36339
    await page.set_viewport_size({"width": 500, "height": 240})
    await page.set_content(
        """
    <style>
    * {
      padding: 0;
      margin: 0;
    }
    li {
      height: 80px;
      border: 1px solid black;
    }
    ol {
      height: 100vh;
      overflow: scroll;
      padding-top: 160px;
    }
    body {
      position: relative;
    }
    div.fixed {
      position: absolute;
      top: 0;
      z-index: 1001;
      width: 100%;
      background: red;
      height: 160px;
    }
    </style>

    <ol>
    <li>hi1</li><li>hi2</li><li>hi3</li><li>hi4</li><li>hi5</li><li>hi6</li><li>hi7</li><li>hi8</li>
    <li id=target onclick="window.__clicked = true">hi9</li>
    <li>hi10</li><li>hi11</li><li>hi12</li><li>hi13</li><li id=li14>hi14</li>
    </ol>

    <div class=fixed>Overlay</div>
  """
    )
    await page.eval_on_selector(
        "ol",
        """e => {
    const target = document.querySelector('#target');
    e.scrollTo({ top: target.offsetTop, behavior: 'instant' });
  }""",
    )
    await page.click("#target")
    assert await page.evaluate("() => window['__clicked']") is True


async def test_CL_038_should_click_the_button_with_px_border_with_offset(
    page: Page, server: Server, is_frozen_webkit: bool
) -> None:
    if is_frozen_webkit:
        pytest.skip("needs recent webkit")
    await page.goto(server.PREFIX + "/input/button.html")
    await page.eval_on_selector("button", "button => button.style.borderWidth = '8px'")
    await page.click("button", position={"x": 20, "y": 10})
    assert await page.evaluate("result") == "Clicked"
    # Safari reports border-relative offsetX/offsetY.
    assert await page.evaluate("offsetX") == 20
    assert await page.evaluate("offsetY") == 10


async def test_CL_039_should_click_the_button_with_em_border_with_offset(
    page: Page, server: Server, is_frozen_webkit: bool
) -> None:
    if is_frozen_webkit:
        pytest.skip("needs recent webkit")
    await page.goto(server.PREFIX + "/input/button.html")
    await page.eval_on_selector("button", "button => button.style.borderWidth = '2em'")
    await page.eval_on_selector("button", "button => button.style.fontSize = '12px'")
    await page.click("button", position={"x": 20, "y": 10})
    assert await page.evaluate("result") == "Clicked"
    # Safari reports border-relative offsetX/offsetY.
    assert await page.evaluate("offsetX") == 20
    assert await page.evaluate("offsetY") == 10


async def test_CL_040_should_click_a_very_large_button_with_offset(
    page: Page, server: Server, is_frozen_webkit: bool
) -> None:
    if is_frozen_webkit:
        pytest.skip("needs recent webkit")
    await page.goto(server.PREFIX + "/input/button.html")
    await page.eval_on_selector("button", "button => button.style.borderWidth = '8px'")
    await page.eval_on_selector(
        "button", "button => button.style.height = button.style.width = '2000px'"
    )
    await page.click("button", position={"x": 1900, "y": 1910})
    assert await page.evaluate("() => window['result']") == "Clicked"
    # Safari reports border-relative offsetX/offsetY.
    assert await page.evaluate("offsetX") == 1900
    assert await page.evaluate("offsetY") == 1910


async def test_CL_041_should_click_a_button_in_scrolling_container_with_offset(
    page: Page, server: Server, is_frozen_webkit: bool
) -> None:
    if is_frozen_webkit:
        pytest.skip("needs recent webkit")
    await page.goto(server.PREFIX + "/input/button.html")
    await page.eval_on_selector(
        "button",
        """button => {
    const container = document.createElement('div');
    container.style.overflow = 'auto';
    container.style.width = '200px';
    container.style.height = '200px';
    button.parentElement.insertBefore(container, button);
    container.appendChild(button);
    button.style.height = '2000px';
    button.style.width = '2000px';
    button.style.borderWidth = '8px';
  }""",
    )
    await page.click("button", position={"x": 1900, "y": 1910})
    assert await page.evaluate("() => window['result']") == "Clicked"
    # Safari reports border-relative offsetX/offsetY.
    assert await page.evaluate("offsetX") == 1900
    assert await page.evaluate("offsetY") == 1910


async def test_CL_042_should_wait_for_stable_position(
    page: Page, server: Server, utils: Utils
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    await page.eval_on_selector(
        "button",
        """button => {
    button.style.transition = 'margin 500ms linear 0s';
    button.style.marginLeft = '200px';
    button.style.borderWidth = '0';
    button.style.width = '200px';
    button.style.height = '20px';
    // Set display to "block" - otherwise Firefox layouts with non-even
    // values on Linux.
    button.style.display = 'block';
    document.body.style.margin = '0';
  }""",
    )
    # rafraf for Firefox to kick in the animation.
    await utils.rafraf(page)
    await page.click("button")
    assert await page.evaluate("() => window['result']") == "Clicked"
    assert await page.evaluate("pageX") == 300
    assert await page.evaluate("pageY") == 10


ADD_FLYOVER = """button => {
    button.style.borderWidth = '0';
    button.style.width = '200px';
    button.style.height = '20px';
    document.body.style.margin = '0';
    document.body.style.position = 'relative';
    const flyOver = document.createElement('div');
    flyOver.className = 'flyover';
    flyOver.style.position = 'absolute';
    flyOver.style.width = '400px';
    flyOver.style.height = '20px';
    flyOver.style.left = '-200px';
    flyOver.style.top = '0';
    flyOver.style.background = 'red';
    document.body.appendChild(flyOver);
  }"""


async def test_CL_043_should_wait_for_becoming_hit_target(
    page: Page, server: Server, utils: Utils
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    await page.eval_on_selector("button", ADD_FLYOVER)
    clicked = False

    async def click() -> None:
        nonlocal clicked
        await page.click("button")
        clicked = True

    click_promise = asyncio.create_task(click())
    assert clicked is False

    await page.eval_on_selector(".flyover", "flyOver => flyOver.style.left = '0'")
    await give_it_a_chance_to_click(utils, page)
    assert clicked is False

    await page.eval_on_selector(".flyover", "flyOver => flyOver.style.left = '200px'")
    await click_promise
    assert clicked is True
    assert await page.evaluate("() => window['result']") == "Clicked"


async def test_CL_044_should_wait_for_becoming_hit_target_with_trial_run(
    page: Page, server: Server, utils: Utils
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    await page.eval_on_selector("button", ADD_FLYOVER)
    clicked = False

    async def click() -> None:
        nonlocal clicked
        await page.click("button", trial=True)
        clicked = True

    click_promise = asyncio.create_task(click())
    assert clicked is False

    await page.eval_on_selector(".flyover", "flyOver => flyOver.style.left = '0'")
    await give_it_a_chance_to_click(utils, page)
    assert clicked is False

    await page.eval_on_selector(".flyover", "flyOver => flyOver.style.left = '200px'")
    await click_promise
    assert clicked is True

    # Should not actually click.
    assert await page.evaluate("() => window['result']") == "Was not clicked"


async def test_CL_045_trial_run_should_work_with_short_timeout(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    await page.eval_on_selector("button", "button => button.disabled = true")
    with pytest.raises(Error) as exc_info:
        await page.click("button", trial=True, timeout=2000)
    assert "click action (trial run)" in exc_info.value.message
    assert await page.evaluate("() => window['result']") == "Was not clicked"


async def test_CL_046_trial_run_should_not_click(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    await page.click("button", trial=True)
    assert await page.evaluate("() => window['result']") == "Was not clicked"


async def test_CL_047_trial_run_should_not_double_click(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    await page.evaluate(
        """() => {
    window['double'] = false;
    const button = document.querySelector('button');
    button.addEventListener('dblclick', event => {
      window['double'] = true;
    });
  }"""
    )
    await page.dblclick("button", trial=True)
    assert await page.evaluate("double") is False
    assert await page.evaluate("result") == "Was not clicked"


async def test_CL_048_should_fail_when_obscured_and_not_waiting_for_hit_target(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    button = await page.query_selector("button")
    assert button
    await page.evaluate(
        """() => {
    document.body.style.position = 'relative';
    const blocker = document.createElement('div');
    blocker.style.position = 'absolute';
    blocker.style.width = '400px';
    blocker.style.height = '20px';
    blocker.style.left = '0';
    blocker.style.top = '0';
    document.body.appendChild(blocker);
  }"""
    )
    await button.click(force=True)
    assert await page.evaluate("() => window['result']") == "Was not clicked"


async def test_CL_049_should_wait_for_button_to_be_enabled(
    page: Page, utils: Utils
) -> None:
    await page.set_content(
        '<button onclick="window.__CLICKED=true;" disabled><span>Click target</span></button>'
    )
    done = False

    async def click() -> None:
        nonlocal done
        await page.click("text=Click target")
        done = True

    click_promise = asyncio.create_task(click())
    await give_it_a_chance_to_click(utils, page)
    assert await page.evaluate("window.__CLICKED") is None
    assert done is False
    await page.evaluate(
        "() => document.querySelector('button').removeAttribute('disabled')"
    )
    await click_promise
    assert await page.evaluate("__CLICKED") is True


async def test_CL_050_should_wait_for_element_to_become_non_inert(
    page: Page, utils: Utils
) -> None:
    await page.set_content(
        '<div inert id=container><button onclick="window.__CLICKED=true;"><span>Click target</span></button></div>'
    )
    done = False

    async def click() -> None:
        nonlocal done
        await page.click("text=Click target")
        done = True

    click_promise = asyncio.create_task(click())
    await give_it_a_chance_to_click(utils, page)
    assert await page.evaluate("window.__CLICKED") is None
    assert done is False
    await page.evaluate(
        "() => document.getElementById('container').removeAttribute('inert')"
    )
    await click_promise
    assert await page.evaluate("__CLICKED") is True


async def test_CL_051_should_wait_for_modal_dialog_to_close(
    page: Page, utils: Utils
) -> None:
    await page.set_content(
        """
    <button onclick="window.__CLICKED=true;">Click target</button>
    <dialog id=dialog><button onclick="window.__DIALOG_CLICKED=true;">Inside</button></dialog>
    <script>
      document.getElementById('dialog').showModal();
    </script>
  """
    )
    await page.click("text=Inside")
    assert await page.evaluate("__DIALOG_CLICKED") is True

    done = False

    async def click() -> None:
        nonlocal done
        await page.click("text=Click target")
        done = True

    click_promise = asyncio.create_task(click())
    await give_it_a_chance_to_click(utils, page)
    assert await page.evaluate("window.__CLICKED") is None
    assert done is False
    await page.evaluate("() => document.getElementById('dialog').close()")
    await click_promise
    assert await page.evaluate("__CLICKED") is True


async def test_CL_052_should_wait_for_input_to_be_enabled(
    page: Page, utils: Utils
) -> None:
    await page.set_content('<input onclick="window.__CLICKED=true;" disabled>')
    done = False

    async def click() -> None:
        nonlocal done
        await page.click("input")
        done = True

    click_promise = asyncio.create_task(click())
    await give_it_a_chance_to_click(utils, page)
    assert await page.evaluate("window.__CLICKED") is None
    assert done is False
    await page.evaluate(
        "() => document.querySelector('input').removeAttribute('disabled')"
    )
    await click_promise
    assert await page.evaluate("__CLICKED") is True


async def test_CL_053_should_wait_for_select_to_be_enabled(
    page: Page, utils: Utils
) -> None:
    await page.set_content(
        """
    <select disabled><option selected>Hello</option></select>
    <script>
      document.querySelector('select').addEventListener('mousedown', event => {
        window.__CLICKED=true;
        event.preventDefault();
      });
    </script>
  """
    )
    done = False

    async def click() -> None:
        nonlocal done
        await page.click("select")
        done = True

    click_promise = asyncio.create_task(click())
    await give_it_a_chance_to_click(utils, page)
    assert await page.evaluate("window.__CLICKED") is None
    assert done is False
    await page.evaluate(
        "() => document.querySelector('select').removeAttribute('disabled')"
    )
    await click_promise
    assert await page.evaluate("__CLICKED") is True


async def test_CL_054_should_click_disabled_div(page: Page) -> None:
    await page.set_content(
        '<div onclick="window.__CLICKED=true" disabled>Click target</div>'
    )
    await page.click("text=Click target")
    assert await page.evaluate("__CLICKED") is True


async def test_CL_055_should_wait_for_button_to_be_clickable_when_it_has_pointer_events_none(
    page: Page, utils: Utils
) -> None:
    await page.set_content(
        '<button onclick="window.__CLICKED=true" style="pointer-events:none"><span>Click target</span></button>'
    )
    done = False

    async def click() -> None:
        nonlocal done
        await page.click("text=Click target")
        done = True

    click_promise = asyncio.create_task(click())
    await give_it_a_chance_to_click(utils, page)
    assert await page.evaluate("window.__CLICKED") is None
    assert done is False
    await page.evaluate(
        "() => document.querySelector('button').style.removeProperty('pointer-events')"
    )
    await click_promise
    assert await page.evaluate("__CLICKED") is True


async def test_CL_056_should_wait_for_label_to_be_clickable_when_it_has_pointer_events_none(
    page: Page,
) -> None:
    await page.set_content(
        '<label onclick="window.__CLICKED=true" style="pointer-events:none"><span>Click target</span></label>'
    )
    click_promise = asyncio.create_task(page.click("text=Click target"))
    # Do a few roundtrips to the page.
    for _ in range(5):
        assert await page.evaluate("window.__CLICKED") is None
    # remove `pointer-events: none` css from button.
    await page.evaluate(
        "() => document.querySelector('label').style.removeProperty('pointer-events')"
    )
    await click_promise
    assert await page.evaluate("__CLICKED") is True


async def test_CL_057_should_update_modifiers_correctly(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    await page.click("button", modifiers=["Shift"])
    assert await page.evaluate("shiftKey") is True
    await page.click("button", modifiers=[])
    assert await page.evaluate("shiftKey") is False

    await page.keyboard.down("Shift")
    await page.click("button", modifiers=[])
    assert await page.evaluate("shiftKey") is False
    await page.click("button")
    assert await page.evaluate("shiftKey") is True
    await page.keyboard.up("Shift")
    await page.click("button")
    assert await page.evaluate("shiftKey") is False


async def test_CL_058_should_click_an_offscreen_element_when_scroll_behavior_is_smooth(
    page: Page,
) -> None:
    await page.set_content(
        """
    <div style="border: 1px solid black; height: 500px; overflow: auto; width: 500px; scroll-behavior: smooth">
    <button style="margin-top: 2000px" onClick="window.clicked = true">hi</button>
    </div>
  """
    )
    await page.click("button")
    assert await page.evaluate("window.clicked") is True


async def test_CL_059_should_report_nice_error_when_element_is_detached_and_force_clicked(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/animating-button.html")
    await page.evaluate("addButton()")
    handle = await page.query_selector("button")
    assert handle
    await page.evaluate("stopButton(true)")
    with pytest.raises(Error) as exc_info:
        await handle.click(force=True)
    assert await page.evaluate("window.clicked") is None
    assert "Element is not attached to the DOM" in exc_info.value.message


async def test_CL_060_should_fail_when_element_detaches_after_animation(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/animating-button.html")
    await page.evaluate("addButton()")
    handle = await page.query_selector("button")
    assert handle
    promise = asyncio.create_task(handle.click())
    await page.evaluate("stopButton(true)")
    with pytest.raises(Error) as exc_info:
        await promise
    assert await page.evaluate("window.clicked") is None
    assert "Element is not attached to the DOM" in exc_info.value.message


async def test_CL_061_should_retry_when_element_detaches_after_animation(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/animating-button.html")
    await page.evaluate("addButton()")
    clicked = False

    async def click() -> None:
        nonlocal clicked
        await page.click("button")
        clicked = True

    promise = asyncio.create_task(click())
    assert clicked is False
    assert await page.evaluate("window.clicked") is None
    await page.evaluate("stopButton(true)")
    await page.evaluate("addButton()")
    assert clicked is False
    assert await page.evaluate("window.clicked") is None
    await page.evaluate("stopButton(true)")
    await page.evaluate("addButton()")
    assert clicked is False
    assert await page.evaluate("window.clicked") is None
    await page.evaluate("stopButton(false)")
    await promise
    assert clicked is True
    assert await page.evaluate("clicked") is True


ANIMATING_FROM_OUTSIDE = """<style>
    @keyframes move {
      from { left: -300px; }
      to { left: 0; }
    }
    button {
      position: absolute;
      left: -300px;
      top: 0;
      bottom: 0;
      width: 200px;
    }
    button.animated {
      animation: 1s linear 1s move forwards;
    }
    </style>
    <div style="position: relative; width: 300px; height: 300px;">
      <button onclick="window.clicked=true"></button>
    </div>
  """


async def test_CL_062_should_retry_when_element_is_animating_from_outside_the_viewport(
    page: Page,
) -> None:
    await page.set_content(ANIMATING_FROM_OUTSIDE)
    handle = await page.query_selector("button")
    assert handle
    promise = asyncio.create_task(handle.click())
    await handle.evaluate("button => button.className = 'animated'")
    await promise
    assert await page.evaluate("clicked") is True


async def test_CL_063_should_fail_when_element_is_animating_from_outside_the_viewport_with_force(
    page: Page,
) -> None:
    await page.set_content(ANIMATING_FROM_OUTSIDE)
    handle = await page.query_selector("button")
    assert handle
    promise = asyncio.create_task(handle.click(force=True))
    await handle.evaluate("button => button.className = 'animated'")
    with pytest.raises(Error) as exc_info:
        await promise
    assert await page.evaluate("window.clicked") is None
    assert "Element is outside of the viewport" in exc_info.value.message


async def test_CL_064_should_dispatch_microtasks_in_order(page: Page) -> None:
    await page.set_content(
        """
    <button id=button>Click me</button>
    <script>
      let mutationCount = 0;
      const observer = new MutationObserver((mutationsList, observer) => {
        for(let mutation of mutationsList)
          ++mutationCount;
      });
      observer.observe(document.body, { attributes: true, childList: true, subtree: true });
      button.addEventListener('mousedown', () => {
        mutationCount = 0;
        document.body.appendChild(document.createElement('div'));
      });
      button.addEventListener('mouseup', () => {
        window['result'] = mutationCount;
      });
    </script>
  """
    )
    await page.click("button")
    assert await page.evaluate("() => window['result']") == 1


async def test_CL_065_should_click_the_button_when_window_inner_width_is_corrupted(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    await page.evaluate(
        "() => Object.defineProperty(window, 'innerWidth', { value: 0 })"
    )
    await page.click("button")
    assert await page.evaluate("result") == "Clicked"


async def test_CL_066_should_click_zero_sized_input_by_label(page: Page) -> None:
    await page.set_content(
        """
    <label>
      Click me
      <input onclick="window.__clicked=true" style="width:0;height:0;padding:0;margin:0;border:0;">
    </label>
  """
    )
    await page.click("text=Click me")
    assert await page.evaluate("window.__clicked") is True


async def test_CL_070_should_climb_dom_for_inner_label_with_pointer_events_none(
    page: Page,
) -> None:
    await page.set_content(
        '<button onclick="window.__CLICKED=true;"><label style="pointer-events:none">Click target</label></button>'
    )
    await page.click("text=Click target")
    assert await page.evaluate("__CLICKED") is True


async def test_CL_071_should_climb_up_to_role_button(page: Page) -> None:
    await page.set_content(
        '<div role=button onclick="window.__CLICKED=true;"><div style="pointer-events:none"><span><div>Click target</div></span></div>'
    )
    await page.click("text=Click target")
    assert await page.evaluate("__CLICKED") is True


async def test_CL_072_should_climb_up_to_a_anchor(page: Page) -> None:
    # For Firefox its not allowed to return anything: https://bugzilla.mozilla.org/show_bug.cgi?id=1392046
    # Note the intermediate div - it is necessary, otherwise <a><non-clickable/></a> is not recognized as a clickable link.
    await page.set_content(
        '<a href="#" onclick="window.__CLICKED=true" id="outer"><div id="intermediate"><div id="inner" style="pointer-events: none">Inner</div></div></a>'
    )
    await page.click("#inner")
    assert await page.evaluate("__CLICKED") is True


async def test_CL_073_should_climb_up_to_a_role_link(page: Page) -> None:
    await page.set_content(
        '<div role=link onclick="window.__CLICKED=true" id="outer"><div id="inner" style="pointer-events: none">Inner</div></div>'
    )
    await page.click("#inner")
    assert await page.evaluate("__CLICKED") is True


async def test_CL_074_should_click_in_an_iframe_with_border(page: Page) -> None:
    await page.set_content(
        """
    <style>
      body, html, iframe { margin: 0; padding: 0; border: none; box-sizing: border-box; }
      iframe { border: 4px solid black; background: gray; margin-left: 33px; margin-top: 24px; width: 400px; height: 400px; }
    </style>
    <iframe srcdoc="
      <style>
        body, html { margin: 0; padding: 0; }
        div { margin-left: 10px; margin-top: 20px; width: 2px; height: 2px; }
      </style>
      <div>Target</div>
      <script>
        document.querySelector('div').addEventListener('click', () => window.top._clicked = true);
      </script>
    "></iframe>
  """
    )
    locator = page.frame_locator("iframe").locator("div")
    await locator.click()
    assert await page.evaluate("window._clicked") is True


async def test_CL_075_should_click_in_an_iframe_with_border_2(page: Page) -> None:
    await page.set_content(
        """
    <style>
      body, html, iframe { margin: 0; padding: 0; border: none; }
      iframe { border: 4px solid black; background: gray; margin-left: 33px; margin-top: 24px; width: 400px; height: 400px; }
    </style>
    <iframe srcdoc="
      <style>
        body, html { margin: 0; padding: 0; }
        div { margin-left: 10px; margin-top: 20px; width: 2px; height: 2px; }
      </style>
      <div>Target</div>
      <script>
        document.querySelector('div').addEventListener('click', () => window.top._clicked = true);
      </script>
    "></iframe>
  """
    )
    locator = page.frame_locator("iframe").locator("div")
    await locator.click()
    assert await page.evaluate("window._clicked") is True


async def test_CL_076_should_not_retain_removed_iframe_after_clicking_inside_it(
    page: Page,
) -> None:
    await page.set_content('<iframe srcdoc="<button>Click</button>"></iframe>')
    button = page.frame_locator("iframe").get_by_role("button")
    await button.wait_for()
    await page.evaluate(
        """() => {
    window.iframeRef = new WeakRef(document.querySelector('iframe'));
  }"""
    )
    await button.click()
    await page.evaluate("() => document.querySelector('iframe').remove()")
    # Move the mouse away to release Chromium's own last-hovered-node retention.
    await page.mouse.move(500, 500)
    await page.request_gc()
    retained = await page.evaluate("() => Boolean(window.iframeRef.deref())")
    assert retained is False


async def test_CL_077_should_click_in_a_transformed_iframe(page: Page) -> None:
    await page.set_content(
        """
    <style>
      body, html, iframe { margin: 0; padding: 0; border: none; }
      iframe {
        border: 4px solid black;
        background: gray;
        margin-left: 33px;
        margin-top: 24px;
        width: 400px;
        height: 400px;
        transform: translate(100px, 100px) scale(1.2) rotate3d(1, 1, 1, 25deg);
      }
    </style>
    <iframe srcdoc="
      <style>
        body, html { margin: 0; padding: 0; }
        div { margin-left: 10px; margin-top: 20px; width: 2px; height: 2px; }
      </style>
      <div>Target</div>
      <script>
        document.querySelector('div').addEventListener('click', () => window.top._clicked = true);
      </script>
    "></iframe>
  """
    )
    locator = page.frame_locator("iframe").locator("div")
    await locator.click()
    assert await page.evaluate("window._clicked") is True


async def test_CL_078_should_click_a_button_that_is_overlaid_by_a_permission_popup(
    page: Page, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/23280
    await page.set_viewport_size({"width": 500, "height": 500})
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        """
    <style>body, html { padding: 0; margin: 0; }</style>
    <script type='text/javascript'>
      window.addEventListener('DOMContentLoaded', () => {
        // Viewport filled with buttons.
        for (let i = 0; i < 100; ++i) {
          const button = document.createElement('button');
          button.textContent = i;
          button.style.setProperty('width', '50px');
          button.style.setProperty('height', '50px');
          document.body.append(button);
        }
      }, false);
    </script>
  """
    )
    # Issue a geolocation request. This should show a browser popup.
    # NOTE: this is a bit racy since we can't wait for the geolocation
    # popup to be shown.
    await page.evaluate(
        """() => {
    navigator.geolocation.getCurrentPosition(position => { });
  }"""
    )
    # If popup blocks the click, then some of the `page.click` calls below will hang.
    for i in range(30):
        await page.click(f"text={i}")


async def test_CL_079_should_click_in_a_transformed_iframe_with_force(
    page: Page,
) -> None:
    await page.set_content(
        """
    <style>
      body, html, iframe { margin: 0; padding: 0; border: none; }
      iframe { background: gray; margin-left: 33px; margin-top: 24px; width: 400px; height: 400px; transform: translate(-40px, -40px) scale(0.8); }
    </style>
    <iframe srcdoc="
      <style>
        body, html { margin: 0; padding: 0; }
        div { margin-left: 10px; margin-top: 20px; width: 2px; height: 2px; }
      </style>
      <div>Target</div>
      <script>
        document.querySelector('div').addEventListener('click', () => window.top._clicked = true);
      </script>
    "></iframe>
  """
    )
    locator = page.frame_locator("iframe").locator("div")
    await locator.click(force=True)
    assert await page.evaluate("window._clicked") is True


async def test_CL_080_should_click_in_a_nested_transformed_iframe(page: Page) -> None:
    await page.set_content(
        """
    <style>
      body, html, iframe { margin: 0; padding: 0; box-sizing: border-box; }
      iframe { border: 1px solid black; background: gray; margin-left: 33px; margin-top: 24px; width: 400px; height: 400px; transform: scale(0.8); }
    </style>
    <iframe srcdoc="
      <style>
        body, html, iframe { margin: 0; padding: 0; box-sizing: border-box; }
        iframe { border: 3px solid black; background: gray; margin-left: 18px; margin-top: 14px; width: 200px; height: 200px; transform: scale(0.7); }
      </style>
      <iframe srcdoc='
        <style>
          div { margin-left: 10px; margin-top: 20px; width: 2px; height: 2px; }
        </style>
        <div>Target</div>
      '></iframe>
    "></iframe>
  """
    )
    locator = page.frame_locator("iframe").frame_locator("iframe").locator("div")
    await locator.evaluate(
        """div => {
    div.addEventListener('click', () => window.top['_clicked'] = true);
  }"""
    )
    await locator.click()
    assert await page.evaluate("window._clicked") is True


async def test_CL_081_ensure_events_are_dispatched_in_the_individual_tasks(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/19685
    await page.set_content(
        """
    <div id="outer" style="background: #d4d4d4; width: 60px; height: 60px;">
      <div id="inner" style="background: #adadad; width: 46px; height: 46px;"></div>
    </div>
  """
    )

    await page.evaluate(
        """() => {
    function onClick(name) {
      console.log(`click ${name}`);

      window.builtins.setTimeout(function() {
        console.log(`timeout ${name}`);
      }, 0);

      void Promise.resolve().then(function() {
        console.log(`promise ${name}`);
      });
    }

    document.getElementById('inner').addEventListener('click', () => onClick('inner'));
    document.getElementById('outer').addEventListener('click', () => onClick('outer'));
  }"""
    )

    # Capture console messages
    messages: List[str] = []
    page.on("console", lambda msg: messages.append(msg.text))

    # Click on the inner div element
    await page.locator("#inner").click()

    await poll_until_equal(
        page,
        lambda: messages,
        [
            "click inner",
            "promise inner",
            "click outer",
            "promise outer",
            "timeout inner",
            "timeout outer",
        ],
    )


async def test_CL_082_should_click_if_opened_select_covers_the_button(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/23618
    await page.set_content(
        """
    <div>
      <select>
        <option>very long text #1</option>
        <option>very long text #2</option>
        <option>very long text #3</option>
        <option>very long text #4</option>
        <option>very long text #5</option>
        <option>very long text #6</option>
      </select>
    </div>
    <div>
      <button onclick="window.__CLICKED=42">clickme</button>
    </div>
  """
    )
    await page.click("select")
    await page.click("button")
    assert await page.evaluate("window.__CLICKED") == 42


async def test_CL_083_should_fire_contextmenu_event_on_right_click_in_correct_order(
    page: Page, server: Server, browser_name: str, is_win: bool
) -> None:
    # https://github.com/microsoft/playwright/issues/26515
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        """
    <button id="target">Click me</button>
  """
    )
    await page.evaluate(
        """() => {
    const logEvent = e => console.log(e.type);
    document.addEventListener('mousedown', logEvent);
    document.addEventListener('mouseup', logEvent);
    document.addEventListener('contextmenu', logEvent);
  }"""
    )
    entries: List[str] = []
    page.on("console", lambda message: entries.append(message.text))
    await page.get_by_role("button", name="Click me").click(button="right")
    if browser_name == "chromium" and is_win:
        await poll_until_equal(
            page, lambda: entries, ["mousedown", "mouseup", "contextmenu"]
        )
    else:
        await poll_until_equal(
            page, lambda: entries, ["mousedown", "contextmenu", "mouseup"]
        )


async def test_CL_084_should_click_after_a_right_click(page: Page) -> None:
    # https://github.com/microsoft/playwright/issues/39246
    await page.set_content(
        """
    <button>Click me</button>
    <script>
      const button = document.querySelector('button');
      button.addEventListener('click', () => button.textContent = 'Clicked!');
    </script>
  """
    )
    await page.get_by_role("button").click(button="right")
    await page.get_by_role("button").click()
    await expect(page.get_by_role("button")).to_have_text("Clicked!")


async def test_CL_085_should_set_pointer_event_pressure_on_pointerdown(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/35844
    await page.set_content(
        """
    <button id="target">Click me</button>
    <script>
      window['pressures'] = [];
      document.addEventListener('pointerdown', e => window['pressures'].push(['pointerdown', e.pressure]));
      document.addEventListener('pointerup', e => window['pressures'].push(['pointerup', e.pressure]));
    </script>
  """
    )
    await page.click("button")
    pressures = await page.evaluate("() => window['pressures']")
    # expect.arrayContaining
    for expected in [["pointerdown", 0.5], ["pointerup", 0]]:
        assert expected in pressures


async def test_CL_086_should_set_pointer_event_pressure_on_pointermove(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/35844
    await page.set_content(
        """
    <body style="margin: 0; padding: 0;">
      <div id="target" style="width: 500px; height: 500px; background-color: red;"></div>
      <script>
        window['pressures'] = [];
        document.addEventListener('pointermove', e => window['pressures'].push([e.pressure, e.clientX, e.clientY]));
      </script>
    </body>
  """
    )
    await page.click("div#target")
    await page.mouse.move(10, 10)
    await page.mouse.down()
    await page.mouse.move(250, 250)
    await page.mouse.up()
    await page.mouse.move(50, 50)
    pressures = await page.evaluate("() => window['pressures']")
    # expect.arrayContaining
    for expected in [[0, 250, 250], [0, 10, 10], [0.5, 250, 250], [0, 50, 50]]:
        assert expected in pressures


async def test_CL_087_should_click_into_shadow_root_with_slotted_div(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/37768
    await page.set_content(
        """
    <my-button>
      <template shadowrootmode="open">
        <button><slot></slot></button>
      </template>
      <div>Foo</div>
    </my-button>
  """
    )

    await page.get_by_role("button", name="Foo").click()


async def test_CL_088_should_click_shadow_root_button(page: Page) -> None:
    # https://github.com/microsoft/playwright/issues/37768
    await page.set_content(
        """
    <my-button>
      <template shadowrootmode="open">
        <button><slot></slot></button>
      </template>
      <div>Foo</div>
    </my-button>
  """
    )

    await page.locator("my-button").click()


async def test_CL_089_should_click_with_tweened_mouse_movement(
    page: Page, browser_name: str, headless: bool
) -> None:
    if not headless:
        pytest.skip("System cursor tends to interfere with this test")

    await page.set_content(
        """
    <body style="margin: 0; padding: 0; height: 500px; width: 500px;">
      <div style="position: relative; top: 280px; left: 150px; width: 100px; height: 40px">Click me</div>
    </body>
  """
    )

    # The test becomes flaky on WebKit without next line.
    if browser_name == "webkit":
        await page.evaluate("() => new Promise(requestAnimationFrame)")
    await page.mouse.move(100, 100)
    await page.evaluate(
        """() => {
    window['result'] = [];
    document.addEventListener('mousemove', event => {
      window['result'].push([event.clientX, event.clientY]);
    });
  }"""
    )
    # Centerpoint at 150 + 100/2, 280 + 40/2 = 200, 300
    await page.locator("div").click(steps=5)
    assert await page.evaluate("result") == [
        [120, 140],
        [140, 180],
        [160, 220],
        [180, 260],
        [200, 300],
    ]
