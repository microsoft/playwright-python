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

"""Port of tests/page/selectors-role.spec.ts."""

import re
from typing import Awaitable, Callable, Dict

import pytest

from playwright.async_api import Error, Page, async_playwright, expect
from tests.server import Server

OUTERS = "els => els.map(e => e.outerHTML)"


async def _run_with_driver_env(
    browser_name: str,
    launch_arguments: Dict,
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    body: Callable[[Page], Awaitable[None]],
) -> None:
    """Runs body with a page of a new driver that has the variable name set.

    Upstream sets the variable in the process of its in-process server. The driver
    of the session is already running, so start a new one with the variable.
    """
    monkeypatch.setenv(name, "1")
    async with async_playwright() as playwright:
        browser = await playwright[browser_name].launch(**launch_arguments)
        try:
            await body(await browser.new_page())
        finally:
            await browser.close()


async def test_SE_050_should_detect_roles(page: Page) -> None:
    await page.set_content(
        """
    <button>Hello</button>
    <select multiple="" size="2"></select>
    <select></select>
    <h3>Heading</h3>
    <details><summary>Hello</summary></details>
    <div role="dialog">I am a dialog</div>
  """
    )
    assert await page.locator("role=button").evaluate_all(OUTERS) == [
        "<button>Hello</button>",
    ]
    assert await page.locator("role=listbox").evaluate_all(OUTERS) == [
        '<select multiple="" size="2"></select>',
    ]
    assert await page.locator("role=combobox").evaluate_all(OUTERS) == [
        "<select></select>",
    ]
    assert await page.locator("role=heading").evaluate_all(OUTERS) == [
        "<h3>Heading</h3>",
    ]
    assert await page.locator("role=group").evaluate_all(OUTERS) == [
        "<details><summary>Hello</summary></details>",
    ]
    assert await page.locator("role=dialog").evaluate_all(OUTERS) == [
        '<div role="dialog">I am a dialog</div>',
    ]
    assert await page.locator("role=menuitem").evaluate_all(OUTERS) == []
    assert await page.get_by_role("menuitem").evaluate_all(OUTERS) == []


async def test_SE_051_should_support_selected(page: Page) -> None:
    await page.set_content(
        """
    <select>
      <option>Hi</option>
      <option selected>Hello</option>
    </select>
    <div>
      <div role="option" aria-selected="true">Hi</div>
      <div role="option" aria-selected="false">Hello</div>
    </div>
  """
    )
    assert await page.locator("role=option[selected]").evaluate_all(OUTERS) == [
        '<option selected="">Hello</option>',
        '<div role="option" aria-selected="true">Hi</div>',
    ]

    assert await page.locator("role=option[selected=true]").evaluate_all(OUTERS) == [
        '<option selected="">Hello</option>',
        '<div role="option" aria-selected="true">Hi</div>',
    ]
    assert await page.get_by_role("option", selected=True).evaluate_all(OUTERS) == [
        '<option selected="">Hello</option>',
        '<div role="option" aria-selected="true">Hi</div>',
    ]

    assert await page.locator("role=option[selected=false]").evaluate_all(OUTERS) == [
        "<option>Hi</option>",
        '<div role="option" aria-selected="false">Hello</div>',
    ]
    assert await page.get_by_role("option", selected=False).evaluate_all(OUTERS) == [
        "<option>Hi</option>",
        '<div role="option" aria-selected="false">Hello</div>',
    ]


async def test_SE_052_should_support_checked(page: Page) -> None:
    await page.set_content(
        """
    <input type=checkbox>
    <input type=checkbox checked>
    <input type=checkbox indeterminate>
    <div role=checkbox aria-checked="true">Hi</div>
    <div role=checkbox aria-checked="false">Hello</div>
    <div role=checkbox>Unknown</div>
  """
    )
    await page.eval_on_selector(
        "[indeterminate]", "input => input.indeterminate = true"
    )

    assert await page.locator("role=checkbox[checked]").evaluate_all(OUTERS) == [
        '<input type="checkbox" checked="">',
        '<div role="checkbox" aria-checked="true">Hi</div>',
    ]
    assert await page.locator("role=checkbox[checked=true]").evaluate_all(OUTERS) == [
        '<input type="checkbox" checked="">',
        '<div role="checkbox" aria-checked="true">Hi</div>',
    ]
    assert await page.get_by_role("checkbox", checked=True).evaluate_all(OUTERS) == [
        '<input type="checkbox" checked="">',
        '<div role="checkbox" aria-checked="true">Hi</div>',
    ]

    assert await page.locator("role=checkbox[checked=false]").evaluate_all(OUTERS) == [
        '<input type="checkbox">',
        '<div role="checkbox" aria-checked="false">Hello</div>',
        '<div role="checkbox">Unknown</div>',
    ]
    assert await page.get_by_role("checkbox", checked=False).evaluate_all(OUTERS) == [
        '<input type="checkbox">',
        '<div role="checkbox" aria-checked="false">Hello</div>',
        '<div role="checkbox">Unknown</div>',
    ]

    assert await page.locator('role=checkbox[checked="mixed"]').evaluate_all(
        OUTERS
    ) == [
        '<input type="checkbox" indeterminate="">',
    ]
    assert await page.locator("role=checkbox").evaluate_all(OUTERS) == [
        '<input type="checkbox">',
        '<input type="checkbox" checked="">',
        '<input type="checkbox" indeterminate="">',
        '<div role="checkbox" aria-checked="true">Hi</div>',
        '<div role="checkbox" aria-checked="false">Hello</div>',
        '<div role="checkbox">Unknown</div>',
    ]


async def test_SE_053_should_support_pressed(page: Page) -> None:
    await page.set_content(
        """
    <button>Hi</button>
    <button aria-pressed="true">Hello</button>
    <button aria-pressed="false">Bye</button>
    <button aria-pressed="mixed">Mixed</button>
  """
    )
    assert await page.locator("role=button[pressed]").evaluate_all(OUTERS) == [
        '<button aria-pressed="true">Hello</button>',
    ]
    assert await page.locator("role=button[pressed=true]").evaluate_all(OUTERS) == [
        '<button aria-pressed="true">Hello</button>',
    ]
    assert await page.get_by_role("button", pressed=True).evaluate_all(OUTERS) == [
        '<button aria-pressed="true">Hello</button>',
    ]
    assert await page.locator("role=button[pressed=false]").evaluate_all(OUTERS) == [
        "<button>Hi</button>",
        '<button aria-pressed="false">Bye</button>',
    ]
    assert await page.get_by_role("button", pressed=False).evaluate_all(OUTERS) == [
        "<button>Hi</button>",
        '<button aria-pressed="false">Bye</button>',
    ]
    assert await page.locator('role=button[pressed="mixed"]').evaluate_all(OUTERS) == [
        '<button aria-pressed="mixed">Mixed</button>',
    ]
    assert await page.locator("role=button").evaluate_all(OUTERS) == [
        "<button>Hi</button>",
        '<button aria-pressed="true">Hello</button>',
        '<button aria-pressed="false">Bye</button>',
        '<button aria-pressed="mixed">Mixed</button>',
    ]


async def test_SE_054_should_support_expanded(page: Page) -> None:
    await page.set_content(
        """
    <div role="treeitem">Hi</div>
    <div role="treeitem" aria-expanded="true">Hello</div>
    <div role="treeitem" aria-expanded="false">Bye</div>
  """
    )

    assert await page.locator("role=treeitem").evaluate_all(OUTERS) == [
        '<div role="treeitem">Hi</div>',
        '<div role="treeitem" aria-expanded="true">Hello</div>',
        '<div role="treeitem" aria-expanded="false">Bye</div>',
    ]
    assert await page.get_by_role("treeitem").evaluate_all(OUTERS) == [
        '<div role="treeitem">Hi</div>',
        '<div role="treeitem" aria-expanded="true">Hello</div>',
        '<div role="treeitem" aria-expanded="false">Bye</div>',
    ]

    assert await page.locator("role=treeitem[expanded]").evaluate_all(OUTERS) == [
        '<div role="treeitem" aria-expanded="true">Hello</div>',
    ]
    assert await page.locator("role=treeitem[expanded=true]").evaluate_all(OUTERS) == [
        '<div role="treeitem" aria-expanded="true">Hello</div>',
    ]
    assert await page.get_by_role("treeitem", expanded=True).evaluate_all(OUTERS) == [
        '<div role="treeitem" aria-expanded="true">Hello</div>',
    ]

    assert await page.locator("role=treeitem[expanded=false]").evaluate_all(OUTERS) == [
        '<div role="treeitem" aria-expanded="false">Bye</div>',
    ]
    assert await page.get_by_role("treeitem", expanded=False).evaluate_all(OUTERS) == [
        '<div role="treeitem" aria-expanded="false">Bye</div>',
    ]

    # Workaround for expanded="none".
    assert await page.locator("[role=treeitem]:not([aria-expanded])").evaluate_all(
        OUTERS
    ) == [
        '<div role="treeitem">Hi</div>',
    ]


async def test_SE_055_should_support_disabled(page: Page) -> None:
    await page.set_content(
        """
    <button>Hi</button>
    <button disabled>Bye</button>
    <button aria-disabled="true">Hello</button>
    <button aria-disabled="false">Oh</button>
    <fieldset disabled>
      <button>Yay</button>
    </fieldset>
    <select>
      <optgroup disabled>
        <option>one</option>
      </optgroup>
      <optgroup>
        <option>two</option>
      </optgroup>
      <option disabled>three</option>
    </select>
  """
    )
    assert await page.locator("role=button[disabled]").evaluate_all(OUTERS) == [
        '<button disabled="">Bye</button>',
        '<button aria-disabled="true">Hello</button>',
        "<button>Yay</button>",
    ]
    assert await page.locator("role=button[disabled=true]").evaluate_all(OUTERS) == [
        '<button disabled="">Bye</button>',
        '<button aria-disabled="true">Hello</button>',
        "<button>Yay</button>",
    ]
    assert await page.get_by_role("button", disabled=True).evaluate_all(OUTERS) == [
        '<button disabled="">Bye</button>',
        '<button aria-disabled="true">Hello</button>',
        "<button>Yay</button>",
    ]
    assert await page.locator("role=button[disabled=false]").evaluate_all(OUTERS) == [
        "<button>Hi</button>",
        '<button aria-disabled="false">Oh</button>',
    ]
    assert await page.get_by_role("button", disabled=False).evaluate_all(OUTERS) == [
        "<button>Hi</button>",
        '<button aria-disabled="false">Oh</button>',
    ]
    assert await page.get_by_role("option", disabled=True).evaluate_all(OUTERS) == [
        "<option>one</option>",
        '<option disabled="">three</option>',
    ]
    assert await page.get_by_role("option", disabled=False).evaluate_all(OUTERS) == [
        "<option>two</option>",
    ]
    assert await page.get_by_role("option").evaluate_all(OUTERS) == [
        "<option>one</option>",
        "<option>two</option>",
        '<option disabled="">three</option>',
    ]


async def test_SE_056_should_inherit_disabled_from_the_ancestor(page: Page) -> None:
    await page.set_content(
        """
    <span aria-disabled="true">
      <button>Click me!</button>
    </span>
  """
    )
    await expect(page.locator("button")).to_be_disabled()

    await page.set_content(
        """
    <span aria-disabled="true">
      <h1>Heading</h1>
    </span>
  """
    )
    await expect(page.locator("h1")).not_to_be_disabled()


async def test_SE_057_should_support_disabled_fieldset(page: Page) -> None:
    await page.set_content(
        """
    <fieldset disabled>
      <input></input>
      <button data-testid="inside-fieldset-element">x</button>
      <legend>
        <button data-testid="inside-legend-element">legend</button>
      </legend>
    </fieldset>

    <fieldset disabled>
      <legend>
        <div>
          <button data-testid="nested-inside-legend-element">x</button>
        </div>
      </legend>
    </fieldset>

    <fieldset disabled>
      <div></div>
      <legend>
        <button data-testid="first-legend-element">x</button>
      </legend>
      <legend>
        <button data-testid="second-legend-element">x</button>
      </legend>
    </fieldset>

    <fieldset disabled>
      <fieldset>
        <button data-testid="deep-button">x</button>
      </fieldset>
    </fieldset>
  """
    )

    await expect(page.get_by_test_id("inside-legend-element")).to_be_enabled()
    await expect(page.get_by_test_id("nested-inside-legend-element")).to_be_enabled()
    await expect(page.get_by_test_id("first-legend-element")).to_be_enabled()
    await expect(page.get_by_test_id("second-legend-element")).to_be_disabled()
    await expect(page.get_by_test_id("deep-button")).to_be_disabled()


async def test_SE_058_should_support_level(page: Page) -> None:
    await page.set_content(
        """
    <h1>Hello</h1>
    <h3>Hi</h3>
    <div role="heading" aria-level="5">Bye</div>
  """
    )
    assert await page.locator("role=heading[level=1]").evaluate_all(OUTERS) == [
        "<h1>Hello</h1>",
    ]
    assert await page.get_by_role("heading", level=1).evaluate_all(OUTERS) == [
        "<h1>Hello</h1>",
    ]
    assert await page.locator("role=heading[level=3]").evaluate_all(OUTERS) == [
        "<h3>Hi</h3>",
    ]
    assert await page.get_by_role("heading", level=3).evaluate_all(OUTERS) == [
        "<h3>Hi</h3>",
    ]
    assert await page.locator("role=heading[level=5]").evaluate_all(OUTERS) == [
        '<div role="heading" aria-level="5">Bye</div>',
    ]


async def test_SE_059_should_filter_hidden_unless_explicitly_asked_for(
    page: Page,
) -> None:
    await page.set_content(
        """
    <button>Hi</button>
    <button hidden>Hello</button>
    <button aria-hidden="true">Yay</button>
    <button aria-hidden="false">Nay</button>
    <button style="visibility:hidden">Bye</button>
    <div style="visibility:hidden">
      <button>Oh</button>
    </div>
    <div style="visibility:hidden">
      <button style="visibility:visible">Still here</button>
    </div>
    <button style="display:none">Never</button>
    <div id=host1></div>
    <div id=host2 style="display:none"></div>

    <input name="one">
    <details>
      <summary>Open form</summary>
      <label>
         Label
         <input name="two">
      </label>
    </details>

    <select>
      <option style="visibility:hidden">One</option>
      <option style="display:none">Two</option>
      <option>Three</option>
    </select>

    <script>
      function addButton(host, text) {
        const root = host.attachShadow({ mode: 'open' });
        const button = document.createElement('button');
        button.textContent = text;
        root.appendChild(button);
      }
      addButton(document.getElementById('host1'), 'Shadow1');
      addButton(document.getElementById('host2'), 'Shadow2');
    </script>
  """
    )
    assert await page.locator("role=button").evaluate_all(OUTERS) == [
        "<button>Hi</button>",
        '<button aria-hidden="false">Nay</button>',
        '<button style="visibility:visible">Still here</button>',
        "<button>Shadow1</button>",
    ]
    assert await page.locator("role=button[include-hidden]").evaluate_all(OUTERS) == [
        "<button>Hi</button>",
        '<button hidden="">Hello</button>',
        '<button aria-hidden="true">Yay</button>',
        '<button aria-hidden="false">Nay</button>',
        '<button style="visibility:hidden">Bye</button>',
        "<button>Oh</button>",
        '<button style="visibility:visible">Still here</button>',
        '<button style="display:none">Never</button>',
        "<button>Shadow1</button>",
        "<button>Shadow2</button>",
    ]
    assert await page.locator("role=button[include-hidden=true]").evaluate_all(
        OUTERS
    ) == [
        "<button>Hi</button>",
        '<button hidden="">Hello</button>',
        '<button aria-hidden="true">Yay</button>',
        '<button aria-hidden="false">Nay</button>',
        '<button style="visibility:hidden">Bye</button>',
        "<button>Oh</button>",
        '<button style="visibility:visible">Still here</button>',
        '<button style="display:none">Never</button>',
        "<button>Shadow1</button>",
        "<button>Shadow2</button>",
    ]
    assert await page.locator("role=button[include-hidden=false]").evaluate_all(
        OUTERS
    ) == [
        "<button>Hi</button>",
        '<button aria-hidden="false">Nay</button>',
        '<button style="visibility:visible">Still here</button>',
        "<button>Shadow1</button>",
    ]
    assert await page.locator("role=textbox").evaluate_all(OUTERS) == [
        '<input name="one">',
    ]
    assert await page.locator("role=option").evaluate_all(OUTERS) == [
        '<option style="visibility:hidden">One</option>',
        "<option>Three</option>",
    ]


async def test_SE_060_should_support_name(
    page: Page, browser_name: str, browser_major_version: int
) -> None:
    await page.set_content(
        """
    <div role="button" aria-label=" Hello "></div>
    <div role="button" aria-label="Hallo"></div>
    <div role="button" aria-label="Hello" aria-hidden="true"></div>
    <div role="button" aria-label="123" aria-hidden="true"></div>
    <div role="button" aria-label='foo"bar' aria-hidden="true"></div>

    <span id="title">Chosen name</span>
    <div role="group" aria-labelledby="title"></div>
  """
    )
    group = page.get_by_role("group")
    await expect(group).to_have_accessible_name("Chosen name")
    assert await page.locator('role=button[name="Hello"]').evaluate_all(OUTERS) == [
        '<div role="button" aria-label=" Hello "></div>',
    ]
    assert await page.locator('role=button[name=" \n Hello "]').evaluate_all(
        OUTERS
    ) == [
        '<div role="button" aria-label=" Hello "></div>',
    ]
    assert await page.get_by_role("button", name="Hello").evaluate_all(OUTERS) == [
        '<div role="button" aria-label=" Hello "></div>',
    ]

    assert await page.locator('role=button[name*="all"]').evaluate_all(OUTERS) == [
        '<div role="button" aria-label="Hallo"></div>',
    ]

    assert await page.locator("role=button[name=/^H[ae]llo$/]").evaluate_all(
        OUTERS
    ) == [
        '<div role="button" aria-label=" Hello "></div>',
        '<div role="button" aria-label="Hallo"></div>',
    ]
    assert await page.get_by_role(
        "button", name=re.compile(r"^H[ae]llo$")
    ).evaluate_all(OUTERS) == [
        '<div role="button" aria-label=" Hello "></div>',
        '<div role="button" aria-label="Hallo"></div>',
    ]

    assert await page.locator("role=button[name=/h.*o/i]").evaluate_all(OUTERS) == [
        '<div role="button" aria-label=" Hello "></div>',
        '<div role="button" aria-label="Hallo"></div>',
    ]
    assert await page.get_by_role(
        "button", name=re.compile(r"h.*o", re.IGNORECASE)
    ).evaluate_all(OUTERS) == [
        '<div role="button" aria-label=" Hello "></div>',
        '<div role="button" aria-label="Hallo"></div>',
    ]

    assert await page.locator('role=button[name="Hello"][include-hidden]').evaluate_all(
        OUTERS
    ) == [
        '<div role="button" aria-label=" Hello "></div>',
        '<div role="button" aria-label="Hello" aria-hidden="true"></div>',
    ]
    assert await page.get_by_role(
        "button", name="Hello", include_hidden=True
    ).evaluate_all(OUTERS) == [
        '<div role="button" aria-label=" Hello "></div>',
        '<div role="button" aria-label="Hello" aria-hidden="true"></div>',
    ]
    assert await page.get_by_role(
        "button", name="hello", include_hidden=True
    ).evaluate_all(OUTERS) == [
        '<div role="button" aria-label=" Hello "></div>',
        '<div role="button" aria-label="Hello" aria-hidden="true"></div>',
    ]

    assert await page.locator("role=button[name=Hello]").evaluate_all(OUTERS) == [
        '<div role="button" aria-label=" Hello "></div>',
    ]
    assert await page.locator("role=button[name=123][include-hidden]").evaluate_all(
        OUTERS
    ) == [
        '<div role="button" aria-label="123" aria-hidden="true"></div>',
    ]
    assert await page.get_by_role(
        "button", name="123", include_hidden=True
    ).evaluate_all(OUTERS) == [
        '<div role="button" aria-label="123" aria-hidden="true"></div>',
    ]

    # Old electron/android do not have this API.
    is_missing_aria_labelled_by_elements = (
        browser_name == "chromium" and browser_major_version < 135
    )
    if not is_missing_aria_labelled_by_elements:
        await group.evaluate(
            """element => {
                element.ariaLabelledByElements = [document.querySelector('#title')];
            }"""
        )
        assert await page.get_by_role(
            "group", name="Chosen name", exact=True
        ).evaluate_all(OUTERS) == [
            '<div role="group" aria-labelledby=""></div>',
        ]


async def test_SE_061_should_support_option_name_with_html_whitespace(
    page: Page,
) -> None:
    await page.set_content(
        """
    <select>
      <option value="html">&nbsp;HTML</option>
    </select>
  """
    )
    await expect(page.get_by_role("option", name="HTML")).to_have_count(1)


async def test_SE_062_errors(page: Page) -> None:
    with pytest.raises(Error) as e0:
        await page.query_selector("role=[bar]")
    assert "Role must not be empty" in e0.value.message

    with pytest.raises(Error) as e1:
        await page.query_selector("role=foo[sElected]")
    assert (
        'Unknown attribute "sElected", must be one of "checked", "description", "disabled", "expanded", "include-hidden", "level", "name", "pressed", "selected"'
        in e1.value.message
    )

    with pytest.raises(Error) as e2:
        await page.query_selector("role=foo[bar . qux=true]")
    assert 'Unknown attribute "bar.qux"' in e2.value.message

    with pytest.raises(Error) as e3:
        await page.query_selector('role=heading[level="bar"]')
    assert '"level" attribute must be compared to a number' in e3.value.message

    with pytest.raises(Error) as e4:
        await page.query_selector('role=checkbox[checked="bar"]')
    assert '"checked" must be one of true, false, "mixed"' in e4.value.message

    with pytest.raises(Error) as e5:
        await page.query_selector("role=checkbox[checked~=true]")
    assert (
        "cannot use ~= in attribute with non-string matching value" in e5.value.message
    )

    with pytest.raises(Error) as e6:
        await page.query_selector("role=button[level=3]")
    assert (
        '"level" attribute is only supported for roles: "heading", "listitem", "row", "treeitem"'
        in e6.value.message
    )

    with pytest.raises(Error) as e7:
        await page.query_selector("role=button[name]")
    assert '"name" attribute must have a value' in e7.value.message

    with pytest.raises(Error) as e8:
        await page.query_selector('role=treeitem[expanded="none"]')
    assert '"expanded" must be one of true, false' in e8.value.message


async def test_SE_063_hidden_with_shadow_dom_slots(page: Page) -> None:
    await page.set_content(
        """
    <div make-hidden>
      <button>hidden1</button>
    </div>
    <div make-hidden>
      <span><button>hidden2</button></v>
    </div>
    <div>
      <button>visible1</button>
    </div>
    <div>
      <span><button>visible2</button></span>
    </div>
    <script>
      for (const div of document.querySelectorAll('div')) {
        const hidden = div.hasAttribute('make-hidden');
        div.attachShadow({ mode: 'open' }).innerHTML = hidden ? 'nothing to see here' : '<slot></slot>';
      }
    </script>
  """
    )
    assert await page.locator("role=button").evaluate_all(OUTERS) == [
        "<button>visible1</button>",
        "<button>visible2</button>",
    ]
    assert await page.locator("role=button[include-hidden]").evaluate_all(OUTERS) == [
        "<button>hidden1</button>",
        "<button>hidden2</button>",
        "<button>visible1</button>",
        "<button>visible2</button>",
    ]


async def test_SE_064_should_support_output_accessible_name(page: Page) -> None:
    await page.set_content("<label>Output1<output>output</output></label>")
    await expect(page.get_by_role("status", name="Output1")).to_be_visible()


async def test_SE_065_should_not_match_scope_by_default(page: Page) -> None:
    await page.set_content(
        """
    <ul>
      <li aria-label="Parent list">
        Parent list
        <ul>
          <li>child 1</li>
          <li>child 2</li>
        </ul>
      </li>
    </ul>
  """
    )
    children = page.get_by_role("listitem", name="Parent list").get_by_role("listitem")
    await expect(children).to_have_count(2)
    await expect(children).to_have_text(["child 1", "child 2"])


async def test_SE_066_should_not_match_inert_elements_unless_explicitly_asked_for(
    page: Page,
) -> None:
    await page.set_content(
        """
    <button>Hi</button>
    <button inert>Hello</button>
    <div inert id=container>
      <button>Yay</button>
      <div><button>Nay</button></div>
    </div>
    <button><span inert>Save</span></button>
    <div id=host></div>
    <div inert id=inert-host></div>
    <script>
      function addButton(host, text) {
        const root = host.attachShadow({ mode: 'open' });
        const button = document.createElement('button');
        button.textContent = text;
        root.appendChild(button);
      }
      addButton(document.getElementById('host'), 'Shadow1');
      addButton(document.getElementById('inert-host'), 'Shadow2');
    </script>
  """
    )
    assert await page.get_by_role("button").evaluate_all(OUTERS) == [
        "<button>Hi</button>",
        '<button><span inert="">Save</span></button>',
        "<button>Shadow1</button>",
    ]
    assert await page.get_by_role("button", include_hidden=True).evaluate_all(
        OUTERS
    ) == [
        "<button>Hi</button>",
        '<button inert="">Hello</button>',
        "<button>Yay</button>",
        "<button>Nay</button>",
        '<button><span inert="">Save</span></button>',
        "<button>Shadow1</button>",
        "<button>Shadow2</button>",
    ]
    await expect(page.get_by_role("button", name="Yay")).to_have_count(0)
    await expect(
        page.get_by_role("button", name="Yay", include_hidden=True)
    ).to_have_count(1)

    # Inert content does not contribute to the accessible name.
    await expect(page.get_by_role("button", name="Save")).to_have_count(0)
    await expect(
        page.get_by_role("button", name="Save", include_hidden=True)
    ).to_have_count(1)

    await page.locator("#container").evaluate("e => e.removeAttribute('inert')")
    assert await page.get_by_role("button").evaluate_all(OUTERS) == [
        "<button>Hi</button>",
        "<button>Yay</button>",
        "<button>Nay</button>",
        '<button><span inert="">Save</span></button>',
        "<button>Shadow1</button>",
    ]


async def test_SE_067_should_not_match_elements_outside_of_a_modal_dialog(
    page: Page,
) -> None:
    await page.set_content(
        """
    <button>Outside</button>
    <dialog id=dialog>
      <button>Inside</button>
      <div inert><button>Inert inside</button></div>
    </dialog>
    <dialog id=non-modal><button>Non-modal</button></dialog>
    <script>
      document.getElementById('dialog').showModal();
      document.getElementById('non-modal').show();
    </script>
  """
    )
    assert await page.get_by_role("button").evaluate_all(OUTERS) == [
        "<button>Inside</button>",
    ]
    assert await page.get_by_role("button", include_hidden=True).evaluate_all(
        OUTERS
    ) == [
        "<button>Outside</button>",
        "<button>Inside</button>",
        "<button>Inert inside</button>",
        "<button>Non-modal</button>",
    ]
    await expect(page.get_by_role("dialog")).to_have_count(1)
    await expect(page.get_by_role("button", name="Outside")).to_have_count(0)

    await page.locator("#dialog").evaluate("e => e.close()")
    assert await page.get_by_role("button").evaluate_all(OUTERS) == [
        "<button>Outside</button>",
        "<button>Non-modal</button>",
    ]


async def test_SE_068_should_match_the_topmost_modal_dialog(page: Page) -> None:
    await page.set_content(
        """
    <button>Outside</button>
    <dialog id=outer>
      <button>Outer</button>
      <dialog id=inner><button>Inner</button></dialog>
    </dialog>
    <div inert>
      <dialog id=escaping><button>Escaping</button></dialog>
    </div>
    <script>
      document.getElementById('outer').showModal();
      document.getElementById('inner').showModal();
    </script>
  """
    )
    assert await page.get_by_role("button").evaluate_all(OUTERS) == [
        "<button>Inner</button>",
    ]

    await page.locator("#inner").evaluate("e => e.close()")
    assert await page.get_by_role("button").evaluate_all(OUTERS) == [
        "<button>Outer</button>",
    ]

    # Modal dialog inside an inert subtree is not inert.
    await page.locator("#outer").evaluate("e => e.close()")
    await page.locator("#escaping").evaluate("e => e.showModal()")
    assert await page.get_by_role("button").evaluate_all(OUTERS) == [
        "<button>Escaping</button>",
    ]


async def test_SE_069_should_respect_playwright_skip_inert_check(
    server: Server,
    browser_name: str,
    launch_arguments: Dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def body(page: Page) -> None:
        # Navigation creates a fresh injected script that reads the env variable.
        await page.goto(server.EMPTY_PAGE)
        await page.set_content(
            """
      <button>Outside</button>
      <div inert><button>Inert</button></div>
      <dialog id=dialog><button>Inside</button></dialog>
      <script>
        document.getElementById('dialog').showModal();
      </script>
    """
        )
        assert await page.get_by_role("button").evaluate_all(OUTERS) == [
            "<button>Outside</button>",
            "<button>Inert</button>",
            "<button>Inside</button>",
        ]

    await _run_with_driver_env(
        browser_name, launch_arguments, monkeypatch, "PLAYWRIGHT_SKIP_INERT_CHECK", body
    )


async def test_SE_070_should_respect_playwright_skip_dialog_check(
    server: Server,
    browser_name: str,
    launch_arguments: Dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def body(page: Page) -> None:
        # Navigation creates a fresh injected script that reads the env variable.
        await page.goto(server.EMPTY_PAGE)
        await page.set_content(
            """
      <button>Outside</button>
      <div inert><button>Inert</button></div>
      <dialog id=dialog><button>Inside</button></dialog>
      <script>
        document.getElementById('dialog').showModal();
      </script>
    """
        )
        assert await page.get_by_role("button").evaluate_all(OUTERS) == [
            "<button>Outside</button>",
            "<button>Inside</button>",
        ]

    await _run_with_driver_env(
        browser_name,
        launch_arguments,
        monkeypatch,
        "PLAYWRIGHT_SKIP_DIALOG_CHECK",
        body,
    )
