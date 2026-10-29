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

from typing import Any, Callable, List

import pytest

from playwright.sync_api import Error, Page
from tests.server import Server


def test_EH_093_should_work_smoke(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/offscreenbuttons.html")
    for i in range(11):
        button = page.query_selector(f"#btn{i}")
        assert button
        before = button.evaluate(
            "button => button.getBoundingClientRect().right - window.innerWidth"
        )
        assert before == 10 * i
        button.scroll_into_view_if_needed()
        after = button.evaluate(
            "button => button.getBoundingClientRect().right - window.innerWidth"
        )
        assert (after <= 0) is True
        page.evaluate("() => window.scrollTo(0, 0)")


def test_EH_094_should_throw_for_detached_element(page: Page) -> None:
    page.set_content("<div>Hello</div>")
    div = page.query_selector("div")
    assert div
    div.evaluate("div => div.remove()")
    with pytest.raises(Error) as exc_info:
        div.scroll_into_view_if_needed()
    assert "Element is not attached to the DOM" in exc_info.value.message


def _test_waiting(
    page: Page, after: str, sync_gather: Callable[..., List[Any]]
) -> None:
    div = page.query_selector("div")
    assert div
    done = False

    def scroll() -> None:
        nonlocal done
        div.scroll_into_view_if_needed()
        done = True

    def change() -> None:
        page.wait_for_timeout(1000)
        assert done is False
        div.evaluate(after)

    sync_gather(scroll, change)
    assert done is True


def test_EH_095_should_wait_for_display_none_to_become_visible(
    page: Page, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_content('<div style="display:none">Hello</div>')
    _test_waiting(page, "div => div.style.display = 'block'", sync_gather)


def test_EH_096_should_scroll_display_contents_into_view(
    page: Page, browser_name: str, browser_major_version: int
) -> None:
    if browser_name == "chromium" and browser_major_version < 105:
        pytest.skip(
            "Needs https://chromium-review.googlesource.com/c/chromium/src/+/3758670"
        )

    page.set_content(
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
    div = page.query_selector("#target")
    assert div
    div.scroll_into_view_if_needed()
    scroll_top = page.eval_on_selector("#container", "e => e.scrollTop")
    assert abs(scroll_top - 350) < 1


def test_EH_124_should_scroll_nested_display_contents_into_view(
    page: Page, browser_name: str, browser_major_version: int
) -> None:
    page.set_content(
        """
    <style>
      html, body { margin: 0; padding: 0; width: 100%; height: 100%; }
      ::-webkit-scrollbar { display: none; }
      * { scrollbar-width: none; }
    </style>
    <div id=container style="width:200px;height:200px;overflow:scroll;border:1px solid black;">
      <div style="margin-top:500px;background:red;">
        <div id=outer style="display:contents"><div style="display:contents"><div id=target style="height:50px;width:100px;background:cyan;">Hello</div></div><div style="height:2000px;"></div><div>Sibling</div></div>
      </div>
    </div>
    """
    )
    div = page.query_selector("#outer")
    assert div
    div.scroll_into_view_if_needed()
    # The first box in the flattened subtree of #outer is #target, two levels down,
    # not the tall sibling. No whitespace text nodes inside #outer: in Firefox they
    # get boxes of their own, which would hide a fallback that only looks one level down.
    target_is_visible = page.eval_on_selector(
        "#target",
        """target => {
            const container = document.getElementById('container').getBoundingClientRect();
            const rect = target.getBoundingClientRect();
            return rect.top >= container.top && rect.bottom <= container.bottom;
        }""",
    )
    assert target_is_visible is True


def test_EH_097_should_work_for_visibility_hidden_element(page: Page) -> None:
    page.set_content('<div style="visibility:hidden">Hello</div>')
    div = page.query_selector("div")
    assert div
    div.scroll_into_view_if_needed()


def test_EH_098_should_work_for_zero_sized_element(page: Page) -> None:
    page.set_content('<div style="height:0">Hello</div>')
    div = page.query_selector("div")
    assert div
    div.scroll_into_view_if_needed()


def test_EH_099_should_wait_for_nested_display_none_to_become_visible(
    page: Page, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_content('<span style="display:none"><div>Hello</div></span>')
    _test_waiting(page, "div => div.parentElement.style.display = 'block'", sync_gather)


def test_EH_100_should_wait_for_element_to_stop_moving(
    page: Page, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_content(
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
    _test_waiting(page, "div => div.classList.remove('animated')", sync_gather)


def test_EH_101_should_timeout_waiting_for_visible(page: Page) -> None:
    page.set_content('<div style="display:none">Hello</div>')
    div = page.query_selector("div")
    assert div
    with pytest.raises(Error) as exc_info:
        div.scroll_into_view_if_needed(timeout=3000)
    assert "element is not visible" in exc_info.value.message
    assert "retrying scroll into view action" in exc_info.value.message
