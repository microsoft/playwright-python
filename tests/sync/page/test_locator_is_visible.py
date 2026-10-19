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

"""Port of tests/page/locator-is-visible.spec.ts."""

import json

import pytest

from playwright.sync_api import Error, Page, expect
from tests.server import Server


def test_LO_115_is_visible_and_is_hidden_should_work(page: Page) -> None:
    page.set_content("<div>Hi</div><span></span>")

    div = page.locator("div")
    assert div.is_visible() is True
    assert div.is_hidden() is False
    assert page.is_visible("div") is True
    assert page.is_hidden("div") is False

    span = page.locator("span")
    assert span.is_visible() is False
    assert span.is_hidden() is True
    assert page.is_visible("span") is False
    assert page.is_hidden("span") is True

    assert page.is_visible("no-such-element") is False
    assert page.is_hidden("no-such-element") is True


def test_LO_116_is_visible_should_be_true_for_opacity_0(page: Page) -> None:
    page.set_content('<div style="opacity:0">Hi</div>')
    expect(page.locator("div")).to_be_visible()


def test_LO_117_is_visible_should_be_true_for_element_outside_view(
    page: Page,
) -> None:
    page.set_content('<div style="position: absolute; left: -1000px">Hi</div>')
    expect(page.locator("div")).to_be_visible()


def test_LO_118_is_visible_and_is_hidden_should_work_with_details(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/10674
    page.set_content(
        """<details>
    <summary>click to open</summary>
      <ul>
        <li>hidden item 1</li>
        <li>hidden item 2</li>
        <li>hidden item 3</li>
      </ul
  </details>"""
    )

    expect(page.locator("ul")).to_be_hidden()


def test_LO_119_is_visible_and_is_hidden_should_work_with_nested_details(
    page: Page,
) -> None:
    page.set_content(
        """<details>
    <summary>outer</summary>
    <details open>
      <summary>inner</summary>
      <button>hidden button</button>
    </details>
  </details>"""
    )

    expect(page.locator("summary", has_text="outer")).to_be_visible()
    expect(page.locator("summary", has_text="inner")).to_be_hidden()
    expect(page.locator("button")).to_be_hidden()
    expect(page.get_by_role("button")).to_have_count(0)


def test_LO_120_is_visible_and_is_hidden_should_work_with_unslotted_content(
    page: Page,
) -> None:
    page.set_content(
        """
    <div id=unslotted><span>hidden 1</span><div><span>hidden 2</span></div></div>
    <div id=slotted><span>visible</span></div>
    <script>
      unslotted.attachShadow({ mode: 'open' }).innerHTML = 'nothing to see here';
      slotted.attachShadow({ mode: 'open' }).innerHTML = '<slot></slot>';
    </script>
  """
    )

    expect(page.locator("span", has_text="hidden 1")).to_be_hidden()
    expect(page.locator("span", has_text="hidden 2")).to_be_hidden()
    expect(page.locator("span", has_text="visible")).to_be_visible()


def test_LO_121_is_visible_and_is_hidden_should_work_with_list_box_options(
    page: Page,
) -> None:
    page.set_content(
        """
    <select multiple>
      <option>visible 1</option>
      <optgroup label="group"><option>visible 2</option></optgroup>
      <option hidden>hidden 1</option>
      <optgroup label="hidden group" style="display:none"><option>hidden 2</option></optgroup>
    </select>
    <select size=3><option>visible 3</option></select>
    <select multiple style="display:none"><option>hidden 3</option></select>
  """
    )

    for name in ["visible 1", "visible 2", "visible 3"]:
        expect(page.get_by_role("option", name=name, exact=True)).to_be_visible()
    for text in ["hidden 1", "hidden 2", "hidden 3"]:
        expect(page.locator("option", has_text=text)).to_be_hidden()


def test_LO_122_is_visible_inside_a_button(page: Page) -> None:
    page.set_content("<button><span></span>a button</button>")
    span = page.locator("span")
    assert span.is_visible() is False
    assert span.is_hidden() is True
    assert page.is_visible("span") is False
    assert page.is_hidden("span") is True
    expect(span).not_to_be_visible()
    expect(span).to_be_hidden()
    span.wait_for(state="hidden")
    page.locator("button").wait_for(state="visible")


def test_LO_123_is_visible_inside_a_role_button(page: Page) -> None:
    page.set_content("<div role=button><span></span>a button</div>")
    span = page.locator("span")
    assert span.is_visible() is False
    assert span.is_hidden() is True
    assert page.is_visible("span") is False
    assert page.is_hidden("span") is True
    expect(span).not_to_be_visible()
    expect(span).to_be_hidden()
    span.wait_for(state="hidden")
    page.locator("[role=button]").wait_for(state="visible")


def test_LO_124_is_visible_during_navigation_should_not_throw(
    page: Page, server: Server
) -> None:
    for _ in range(20):
        try:
            page.set_content(
                f"""
      <script>
        setTimeout(() => {{
          window.location.href = {json.dumps(server.EMPTY_PAGE)};
        }}, Math.random(50));
      </script>
    """
            )
        except Error:
            pass  # Avoid page.set_content throwing because of scheduled navigation.
        assert page.locator("div").is_visible() is False


def test_LO_125_is_visible_with_invalid_selector_should_throw(
    page: Page,
) -> None:
    with pytest.raises(Error) as exc_info:
        page.locator("hey=what").is_visible()
    assert (
        'Unknown engine "hey" while parsing selector hey=what' in exc_info.value.message
    )
