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

"""Port of tests/page/retarget.spec.ts."""

import asyncio
from pathlib import Path

from playwright.async_api import Page, expect
from tests.server import Server

from ..utils import Utils


async def give_it_a_chance_to_resolve(page: Page, utils: Utils) -> None:
    await utils.rafraf(page, 5)


async def test_RE_001_element_state_checks_should_work_as_expected_for_label_with_zero_sized_input(
    page: Page, server: Server
) -> None:
    await page.set_content(
        """
    <label>
      Click me
      <input disabled style="width:0;height:0;padding:0;margin:0;border:0;">
    </label>
  """
    )
    # Visible checks the label.
    assert await page.is_visible("text=Click me") is True
    assert await page.is_hidden("text=Click me") is False

    # Enabled checks the input.
    assert await page.is_enabled("text=Click me") is False
    assert await page.is_disabled("text=Click me") is True


async def test_RE_002_should_wait_for_enclosing_disabled_button(
    page: Page, utils: Utils
) -> None:
    await page.set_content("<button><span>Target</span></button>")
    span = await page.query_selector("text=Target")
    assert span
    done = False

    async def wait() -> None:
        nonlocal done
        await span.wait_for_element_state("disabled")
        done = True

    async def check_and_disable() -> None:
        await give_it_a_chance_to_resolve(page, utils)
        assert done is False
        await span.evaluate("span => span.parentElement.disabled = true")

    await asyncio.gather(wait(), check_and_disable())


async def test_RE_003_should_wait_for_enclosing_button_with_a_disabled_fieldset(
    page: Page, utils: Utils
) -> None:
    await page.set_content(
        "<fieldset disabled=true><button><span>Target</span></button></div>"
    )
    span = await page.query_selector("text=Target")
    assert span
    done = False

    async def wait() -> None:
        nonlocal done
        await span.wait_for_element_state("enabled")
        done = True

    async def check_and_enable() -> None:
        await give_it_a_chance_to_resolve(page, utils)
        assert done is False
        await span.evaluate("span => span.parentElement.parentElement.disabled = false")

    await asyncio.gather(wait(), check_and_enable())


async def test_RE_004_should_wait_for_enclosing_enabled_button(
    page: Page, server: Server, utils: Utils
) -> None:
    await page.set_content("<button disabled><span>Target</span></button>")
    span = await page.query_selector("text=Target")
    assert span
    done = False

    async def wait() -> None:
        nonlocal done
        await span.wait_for_element_state("enabled")
        done = True

    async def check_and_enable() -> None:
        await give_it_a_chance_to_resolve(page, utils)
        assert done is False
        await span.evaluate("span => span.parentElement.disabled = false")

    await asyncio.gather(wait(), check_and_enable())


async def test_RE_005_should_check_the_box_outside_shadow_dom_label(
    page: Page,
) -> None:
    await page.set_content("<div></div>")
    await page.eval_on_selector(
        "div",
        """div => {
          const root = div.attachShadow({ mode: 'open' });
          const label = document.createElement('label');
          label.setAttribute('for', 'target');
          label.textContent = 'Click me';
          root.appendChild(label);
          const input = document.createElement('input');
          input.setAttribute('type', 'checkbox');
          input.setAttribute('id', 'target');
          root.appendChild(input);
        }""",
    )
    await page.check("label")
    assert await page.eval_on_selector("input", "input => input.checked") is True


async def test_RE_006_set_input_files_should_work_with_label(
    page: Page, assetdir: Path
) -> None:
    await page.set_content(
        "<label for=target>Choose a file</label><input id=target type=file>"
    )
    await page.set_input_files("text=Choose a file", assetdir / "file-to-upload.txt")
    assert await page.eval_on_selector("input", "input => input.files.length") == 1
    assert (
        await page.eval_on_selector("input", "input => input.files?.[0].name")
        == "file-to-upload.txt"
    )


def options_to_attributes(
    disabled: bool = False, hidden: bool = False, readonly: bool = False
) -> str:
    return f" {'disabled' if disabled else ''} {'hidden' if hidden else ''} {'readonly' if readonly else ''} "


def dom_in_label(
    dom: str, disabled: bool = False, hidden: bool = False, readonly: bool = False
) -> str:
    return (
        f"<label {options_to_attributes(disabled, hidden, readonly)}>Text {dom}</label>"
    )


def dom_label_for(
    dom: str, disabled: bool = False, hidden: bool = False, readonly: bool = False
) -> str:
    return f'<label {options_to_attributes(disabled, hidden, readonly)} for="target"><h1>Text</h1></label>{dom}'


def dom_standalone(dom: str) -> str:
    return dom


def dom_in_button(
    dom: str, disabled: bool = False, hidden: bool = False, readonly: bool = False
) -> str:
    return f"<button {options_to_attributes(disabled, hidden, readonly)}>Button {dom}</button>"


def dom_in_link(
    dom: str, disabled: bool = False, hidden: bool = False, readonly: bool = False
) -> str:
    return f"<button {options_to_attributes(disabled, hidden, readonly)}>Button {dom}</button>"


async def test_RE_007_enabled_disabled_retargeting(page: Page) -> None:
    cases = [
        (dom_in_label("<input id=target>"), True, "label"),
        (dom_label_for("<input id=target>"), True, "label"),
        (dom_standalone("<input id=target>"), True, "input"),
        (dom_in_button("<input id=target>"), True, "input"),
        (dom_in_link("<input id=target>"), True, "input"),
        (dom_in_button("<input id=target>", disabled=True), True, "input"),
        (
            dom_in_label("<li role=menuitem id=target aria-disabled=false></li>"),
            True,
            "li",
        ),
        (dom_in_label("<input id=target disabled>"), False, "label"),
        (dom_label_for("<input id=target disabled>"), False, "label"),
        (dom_standalone("<input id=target disabled>"), False, "input"),
        (dom_in_button("<input id=target disabled>"), False, "input"),
        (dom_in_link("<input id=target disabled>"), False, "input"),
        (dom_in_button("<input id=target disabled>", disabled=True), False, "input"),
        (
            dom_in_label("<li role=menuitem id=target aria-disabled=true></li>"),
            False,
            "li",
        ),
        (
            dom_in_label(
                "<select><option disabled>Other employees</option><option>Alex</option></select>"
            ),
            False,
            "option >> nth=0",
        ),
        (
            dom_in_label(
                '<select><optgroup disabled label="Other employees"><option>Alex</option></optgroup></select>'
            ),
            False,
            "optgroup",
        ),
    ]
    for dom, enabled, locator in cases:
        # Step: '"{locator}" in "{dom}" should be enabled={enabled}'.
        await page.set_content(dom)
        target = page.locator(locator)
        handle = await page.query_selector(locator)
        assert handle
        assert await target.is_enabled() is enabled, dom
        assert await target.is_disabled() is (not enabled), dom
        if enabled:
            await expect(target).to_be_enabled()
            await expect(target).not_to_be_disabled()
            await handle.wait_for_element_state("enabled")
        else:
            await expect(target).not_to_be_enabled()
            await expect(target).to_be_disabled()
            await handle.wait_for_element_state("disabled")


async def test_RE_008_visible_hidden_retargeting(page: Page) -> None:
    cases = [
        (dom_in_label("<span id=target>content</span>"), True, "label"),
        (dom_in_label("<span id=target hidden>content</span>"), True, "label"),
        (dom_label_for("<span id=target>content</span>"), True, "label"),
        (dom_label_for("<span id=target hidden>content</span>"), True, "label"),
        (dom_standalone("<span id=target>content</span>"), True, "span"),
        (dom_in_button("<span id=target>content</span>"), True, "span"),
        (dom_in_link("<span id=target>content</span>"), True, "span"),
        (dom_in_label("<span id=target>content</span>", hidden=True), False, "label"),
        (
            dom_label_for("<span id=target>content</span>", hidden=True),
            False,
            "label",
        ),
        (dom_standalone("<span id=target hidden>content</span>"), False, "span"),
        (dom_in_button("<span id=target hidden>content</span>"), False, "span"),
        (dom_in_button("<span id=target>content</span>", hidden=True), False, "span"),
        (dom_in_link("<span id=target hidden>content</span>"), False, "span"),
        (dom_in_link("<span id=target>content</span>", hidden=True), False, "span"),
    ]
    for dom, visible, locator in cases:
        # Step: '"{locator}" in "{dom}" should be visible={visible}'.
        await page.set_content(dom)
        target = page.locator(locator)
        handle = await page.query_selector(locator)
        assert handle
        assert await target.is_visible() is visible, dom
        assert await target.is_hidden() is (not visible), dom
        if visible:
            await expect(target).to_be_visible()
            await expect(target).not_to_be_hidden()
            await handle.wait_for_element_state("visible")
        else:
            await expect(target).not_to_be_visible()
            await expect(target).to_be_hidden()
            await handle.wait_for_element_state("hidden")


async def test_RE_009_editable_retargeting(page: Page) -> None:
    cases = [
        (dom_in_label("<input id=target>"), True, "label"),
        (dom_label_for("<input id=target>"), True, "label"),
        (dom_standalone("<input id=target>"), True, "input"),
        (dom_in_button("<input id=target>"), True, "input"),
        (dom_in_link("<input id=target>"), True, "input"),
        (dom_in_button("<input id=target>", readonly=True), True, "input"),
        (dom_in_label("<input id=target readonly>"), False, "label"),
        (dom_label_for("<input id=target readonly>"), False, "label"),
        (dom_standalone("<input id=target readonly>"), False, "input"),
        (dom_in_button("<input id=target readonly>"), False, "input"),
        (dom_in_link("<input id=target readonly>"), False, "input"),
        (dom_in_button("<input id=target readonly>", readonly=True), False, "input"),
    ]
    for dom, editable, locator in cases:
        # Step: '"{locator}" in "{dom}" should be editable={editable}'.
        await page.set_content(dom)
        target = page.locator(locator)
        handle = await page.query_selector(locator)
        assert handle
        assert await target.is_editable() is editable, dom
        if editable:
            await expect(target).to_be_editable()
            await handle.wait_for_element_state("editable")
        else:
            await expect(target).not_to_be_editable()


async def test_RE_010_input_value_retargeting(page: Page) -> None:
    cases = [
        (dom_in_label("<input id=target>"), "label"),
        (dom_label_for("<input id=target>"), "label"),
        (dom_standalone("<input id=target>"), "input"),
        (dom_in_button("<input id=target>"), "input"),
        (dom_in_link("<input id=target>"), "input"),
        (dom_in_button("<input id=target>"), "input"),
    ]
    for dom, locator in cases:
        # Step: '"{locator}" in "{dom}" input value'.
        await page.set_content(dom)
        target = page.locator(locator)
        handle = await page.query_selector(locator)
        assert handle

        assert await target.input_value() == "", dom
        assert await handle.input_value() == "", dom
        await expect(target).to_have_value("")

        await target.fill("foo")
        assert await target.input_value() == "foo", dom
        assert await handle.input_value() == "foo", dom
        await expect(target).to_have_value("foo")

        await page.eval_on_selector("#target", "input => input.value = 'bar'")
        assert await target.input_value() == "bar", dom
        assert await handle.input_value() == "bar", dom
        await expect(target).to_have_value("bar")

        await target.select_text()
        assert (
            await page.evaluate("() => window.getSelection().toString()") == "bar"
        ), dom


async def test_RE_011_selection_retargeting(page: Page) -> None:
    cases = [
        (dom_standalone("<div contenteditable id=target>content</div>"), "div"),
        (dom_in_button("<div contenteditable id=target>content</div>"), "div"),
        (dom_in_link("<div contenteditable id=target>content</div>"), "div"),
        (dom_in_button("<div contenteditable id=target>content</div>"), "div"),
    ]
    for dom, locator in cases:
        # Step: '"{locator}" in "{dom}" text selection'.
        await page.set_content(dom)
        target = page.locator(locator)
        handle = await page.query_selector(locator)
        assert handle

        assert await target.is_editable() is True, dom
        assert await handle.is_editable() is True, dom
        await expect(page.locator("#target")).to_have_text("content")

        await target.fill("foo")
        await expect(page.locator("#target")).to_have_text("foo")

        await target.select_text()
        assert (
            await page.evaluate("() => window.getSelection().toString()") == "foo"
        ), dom


async def test_RE_012_select_options_retargeting(page: Page) -> None:
    select = "<select id=target multiple><option value=dog selected>Dog</option><option value=cat>Cat</option></select>"
    cases = [
        (dom_in_label(select), "label"),
        (dom_label_for(select), "label"),
        (dom_standalone(select), "select"),
        (dom_in_button(select), "select"),
        (dom_in_link(select), "select"),
        (dom_in_button(select), "select"),
    ]
    for dom, locator in cases:
        # Step: '"{locator}" in "{dom}" select option'.
        await page.set_content(dom)
        target = page.locator(locator)
        handle = await page.query_selector(locator)
        assert handle

        assert await target.input_value() == "dog", dom
        assert await handle.input_value() == "dog", dom
        await expect(target).to_have_value("dog")
        await expect(target).to_have_values(["dog"])

        await target.select_option("cat")
        assert await target.input_value() == "cat", dom
        assert await handle.input_value() == "cat", dom
        await expect(target).to_have_value("cat")
        await expect(target).to_have_values(["cat"])


async def test_RE_013_direct_actions_retargeting(page: Page) -> None:
    cases = [
        (dom_in_label("<div>content</div><input id=target value=oh>"), "div"),
        (dom_label_for("<div>content</div><input id=target value=oh>"), "div"),
        (dom_standalone("<div>content</div>"), "div"),
        (dom_in_button("<div>content</div>"), "div"),
        (dom_in_link("<div>content</div>"), "div"),
        (dom_in_button("<div>content</div>"), "div"),
    ]
    for dom, locator in cases:
        # Step: '"{locator}" in "{dom}" direct actions'.
        await page.set_content(dom)
        target = page.locator(locator)

        assert await target.inner_text() == "content", dom
        assert await target.text_content() == "content", dom
        await expect(target).to_have_text("content")
        await expect(target).to_contain_text("content")
        await expect(target).not_to_be_focused()
        await expect(target).to_have_count(1)

        await page.eval_on_selector("div", "div => div.foo = 'bar'")
        await expect(target).to_have_js_property("foo", "bar")

        await page.eval_on_selector("div", "div => div.classList.add('cls')")
        await expect(target).to_have_class("cls")

        await page.eval_on_selector("div", "div => div.id = 'myid'")
        await expect(target).to_have_id("myid")
        await expect(target).to_have_attribute("id", "myid")
        assert await target.get_attribute("id") == "myid", dom


async def test_RE_014_check_retargeting(page: Page) -> None:
    cases = [
        (dom_in_label("<input type=checkbox id=target>"), "label"),
        (dom_label_for("<input type=checkbox id=target>"), "label"),
        (dom_standalone("<input type=checkbox id=target>"), "input"),
        (dom_in_button("<input type=checkbox id=target>"), "input"),
        (dom_in_link("<input type=checkbox id=target>"), "input"),
        (dom_in_button("<input type=checkbox id=target>"), "input"),
    ]
    for dom, locator in cases:
        # Step: '"{locator}" in "{dom}" check'.
        await page.set_content(dom)
        target = page.locator(locator)
        assert await target.is_checked() is False, dom
        await expect(target).not_to_be_checked()
        await expect(target).to_be_checked(checked=False)

        await page.eval_on_selector("input", "input => input.checked = true")
        assert await target.is_checked() is True, dom
        await expect(target).to_be_checked()
        await expect(target).to_be_checked(checked=True)

        await target.uncheck()
        assert await page.eval_on_selector("input", "input => input.checked") is False

        await target.check()
        assert await page.eval_on_selector("input", "input => input.checked") is True

        await target.set_checked(False)
        assert await page.eval_on_selector("input", "input => input.checked") is False


async def test_RE_015_should_not_retarget_anchor_into_parent_label(
    page: Page,
) -> None:
    await page.set_content(
        """
    <label disabled>Text<a href='#' onclick='window.__clicked=1'>Target</a></label>
  """
    )
    await page.locator("a").click()
    assert await page.evaluate("window.__clicked") == 1

    await page.set_content(
        """
    <input type="radio" id="input-id" checked disabled />
    <label for="input-id">Text<a href='#' onclick='window.__clicked=2'>Target</a></label>
  """
    )
    await page.locator("a").click()
    assert await page.evaluate("window.__clicked") == 2
