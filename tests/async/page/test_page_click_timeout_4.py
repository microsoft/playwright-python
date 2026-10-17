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

"""Port of tests/page/page-click-timeout-4.spec.ts."""

import pytest

from playwright.async_api import Error, Page
from tests.server import Server

from ..utils import Utils


async def test_CL_120_should_timeout_waiting_for_stable_position(
    page: Page, server: Server, utils: Utils
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    button = await page.query_selector("button")
    assert button
    await button.evaluate(
        """button => {
    button.style.transition = 'margin 5s linear 0s';
    button.style.marginLeft = '200px';
  }"""
    )
    # rafraf for Firefox to kick in the animation.
    await utils.rafraf(page)
    with pytest.raises(Error) as exc_info:
        await button.click(timeout=3000)
    assert "ElementHandle.click: Timeout 3000ms exceeded." in exc_info.value.message
    assert (
        "waiting for element to be visible, enabled and stable"
        in exc_info.value.message
    )
    assert "element is not stable" in exc_info.value.message
    assert "retrying click action" in exc_info.value.message


async def test_CL_122_should_fail_to_click_the_button_behind_a_large_header_after_scrolling_around(
    page: Page,
) -> None:
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
      background: rgba(255, 0, 0, 0.2);
      height: 2000px;
    }
    </style>

    <div class=fixed></div>

    <ol>
    <li>hi1</li><li>hi2</li><li>hi3</li><li>hi4</li><li>hi5</li><li>hi6</li><li>hi7</li><li>hi8</li>
    <li id=target onclick="window.__clicked = true">hi9</li>
    <li>hi10</li><li>hi11</li><li>hi12</li><li>hi13</li><li id=li14>hi14</li>
    </ol>

    <script>
      window.scrollTops = [];
      window.addEventListener('scroll', () => {
        window.scrollTops.push(window.scrollY);
      });
    </script>
  """
    )
    await page.eval_on_selector("#li14", "e => e.scrollIntoView()")
    with pytest.raises(Error) as exc_info:
        await page.click("#target", timeout=3500)
    assert (
        '<div class="fixed"></div> intercepts pointer events' in exc_info.value.message
    )
    assert await page.evaluate("() => window['__clicked']") is None
    scroll_tops = await page.evaluate("() => window['scrollTops']")
    distinct = set(scroll_tops)
    assert len(distinct) > 2  # At least three different scroll positions.
