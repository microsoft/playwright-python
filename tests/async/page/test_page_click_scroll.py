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

"""Port of tests/page/page-click-scroll.spec.ts."""

import pytest

from playwright.async_api import Error, Page
from tests.server import Server


async def test_CL_094_should_not_hit_scroll_bar(page: Page) -> None:
    await page.set_content(
        """
    <style>
      .categories { width: 180px; display: flex; overflow-x: scroll; }
      button { flex: none; height: 28px; }
    </style>
    <div class="categories">
      <button>One</button>
      <button>Two</button>
      <button>Three</button>
      <button>Story</button>
      <button>More</button>
      <button>Items</button>
      <button>Here</button>
    </div>
    """
    )
    await page.click("text=Story", timeout=2000)


async def test_CL_095_should_scroll_into_view_display_contents(
    page: Page, browser_name: str, browser_major_version: int
) -> None:
    if browser_name == "chromium" and browser_major_version < 105:
        pytest.skip(
            "Needs https://chromium-review.googlesource.com/c/chromium/src/+/3758670"
        )

    await page.set_content(
        """
    <div style="background:red;height:2000px">filler</div>
    <div>
      Example text, and button here:
      <button style="display: contents" onclick="window._clicked=true;">click me</button>
    </div>
  """
    )
    await page.click("text=click me", timeout=5000)
    assert await page.evaluate("window._clicked") is True


async def test_CL_096_should_scroll_into_view_display_contents_with_a_child(
    page: Page, browser_name: str, browser_major_version: int
) -> None:
    if browser_name == "chromium" and browser_major_version < 105:
        pytest.skip(
            "Needs https://chromium-review.googlesource.com/c/chromium/src/+/3758670"
        )

    await page.set_content(
        """
    <div style="background:red;height:2000px">filler</div>
    Example text, and button here:
    <button style="display: contents" onclick="window._clicked=true;"><div>click me</div></button>
  """
    )
    await page.click("text=click me", timeout=5000)
    assert await page.evaluate("window._clicked") is True


async def test_CL_097_should_scroll_into_view_display_contents_with_position(
    page: Page, browser_name: str
) -> None:
    if browser_name == "chromium":
        pytest.skip("fixme: DOM.getBoxModel does not work for display:contents")

    await page.set_content(
        """
    <div style="background:red;height:2000px">filler</div>
    <div>
      Example text, and button here:
      <button style="display: contents" onclick="window._clicked=true;">click me</button>
    </div>
  """
    )
    await page.click("text=click me", position={"x": 5, "y": 5}, timeout=5000)
    assert await page.evaluate("window._clicked") is True


async def test_CL_098_should_not_crash_when_force_clicking_hidden_input(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/18183
    await page.set_content("<input type=hidden>")
    with pytest.raises(Error) as exc_info:
        await page.locator("input").click(force=True, timeout=2000)
    assert "Element is not visible" in exc_info.value.message


async def test_CL_099_should_scroll_into_view_span_element(page: Page) -> None:
    # https://github.com/microsoft/playwright/issues/20165
    await page.set_content(
        """
    <div id=big style="height: 10000px;"></div>
    <span id=small>foo</span>
  """
    )
    await page.locator("#small").scroll_into_view_if_needed()
    assert await page.evaluate("() => window.scrollY") > 9000


async def test_CL_100_should_scroll_into_view_element_in_iframe(
    page: Page, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/27196
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        f"""
    <div id=big style="height: 10000px;"></div>
    <iframe src='{server.CROSS_PROCESS_PREFIX}/input/button.html'></iframe>
  """
    )
    await page.frame_locator("iframe").get_by_role("button").click(timeout=5000)


async def test_CL_101_should_not_scroll_the_page_when_scroll_is_none(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/41421
    await page.set_content(
        """
    <div style="height: 2000px;"></div>
    <button onclick="window._clicked=true">click me</button>
  """
    )
    with pytest.raises(Error) as exc_info:
        await page.locator("button").click(scroll="none", timeout=2000)
    assert "element is outside of the viewport" in exc_info.value.message
    assert not await page.evaluate("window._clicked")
    assert await page.evaluate("() => window.scrollY") == 0


async def test_CL_102_should_click_in_viewport_element_when_scroll_is_none(
    page: Page,
) -> None:
    await page.set_content(
        """
    <button onclick="window._clicked=true">click me</button>
    <div style="height: 2000px;"></div>
  """
    )
    await page.locator("button").click(scroll="none", timeout=2000)
    assert await page.evaluate("window._clicked") is True
    assert await page.evaluate("() => window.scrollY") == 0


async def test_CL_103_should_not_scroll_nested_container_when_scroll_is_none(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/41421
    await page.set_content(
        """
    <div style="height: 100px; width: 100px; overflow-y: scroll;">
      <div style="height: 50px;">A</div>
      <div style="height: 50px;">B</div>
      <button style="height: 50px; width: 100px;" onclick="window._clicked=true">C</button>
    </div>
  """
    )
    button = page.locator("button")
    # The button is scrolled out of the nested overflow container.
    with pytest.raises(Error) as exc_info:
        await button.click(scroll="none", timeout=2000)
    assert exc_info.value
    assert not await page.evaluate("window._clicked")
    # Default behavior scrolls the nested container into view and succeeds.
    await button.click(timeout=2000)
    assert await page.evaluate("window._clicked") is True


async def test_CL_104_should_not_scroll_on_hover_when_scroll_is_none(
    page: Page,
) -> None:
    await page.set_content(
        """
    <div style="height: 2000px;"></div>
    <div onmouseover="window._hovered=true" style="width: 50px; height: 50px;">hover me</div>
  """
    )
    with pytest.raises(Error) as exc_info:
        await page.locator("div >> text=hover me").hover(scroll="none", timeout=2000)
    assert "element is outside of the viewport" in exc_info.value.message
    assert not await page.evaluate("window._hovered")
    assert await page.evaluate("() => window.scrollY") == 0


async def test_CL_105_should_scroll_instantly_on_retry_when_scroll_behavior_is_smooth(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/42625
    # The fixed header covers everything but the bottom strip of the viewport.
    # The first attempt centers the button under the header, so the click is
    # retried with a different scroll alignment using the native scrollIntoView().
    await page.set_content(
        """
    <style>
      html { scroll-behavior: smooth; }
      body { margin: 0; }
      .spacer { height: 2000px; }
      #header { position: fixed; top: 0; left: 0; right: 0; bottom: 50px; background: rgba(0, 0, 0, 0.1); }
      button { height: 30px; }
    </style>
    <div id="header"></div>
    <div class="spacer"></div>
    <button onclick="window.clicked = true">Target</button>
    <div class="spacer"></div>
    <script>
      window.scrolls = [];
      addEventListener('scroll', () => window.scrolls.push(window.scrollY));
    </script>
  """
    )
    await page.click("button")
    assert await page.evaluate("window.clicked") is True
    # Every scroll performed by Playwright should be a single instant jump,
    # and never a smooth animation that fires a scroll event per frame.
    scrolls = await page.evaluate("() => window['scrolls']")
    assert len(scrolls) <= 2
