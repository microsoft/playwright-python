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

"""Port of tests/page/elementhandle-convenience.spec.ts."""

import pytest

from playwright.async_api import ElementHandle, Error, Page
from tests.server import Server


async def test_EH_024_should_have_a_nice_preview(page: Page, server: Server) -> None:
    await page.goto(f"{server.PREFIX}/dom.html")
    outer = await page.query_selector("#outer")
    inner = await page.query_selector("#inner")
    check = await page.query_selector("#check")
    assert inner
    text = await inner.evaluate_handle("e => e.firstChild")
    await page.evaluate("() => 1")  # Give them a chance to calculate the preview.
    assert str(outer) == 'JSHandle@<div id="outer" name="value">…</div>'
    assert str(inner) == 'JSHandle@<div id="inner">Text,↵more text</div>'
    assert str(text) == "JSHandle@#text=Text,↵more text"
    assert (
        str(check) == 'JSHandle@<input checked id="check" foo="bar"" type="checkbox"/>'
    )


async def test_EH_025_should_have_a_nice_preview_for_non_ascii_attributes_children(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(f'<div title="{"😛" * 100}">{"😛" * 100}')
    handle = await page.query_selector("div")
    assert handle
    expected = f'JSHandle@<div title="{"😛" * 100}">{"😛" * 49}…</div>'
    # Like expect.poll(): the preview is updated by an event from the driver.
    for _ in range(50):
        if str(handle) == expected:
            break
        await page.wait_for_timeout(100)
    assert str(handle) == expected


async def test_EH_026_get_attribute_should_work(page: Page, server: Server) -> None:
    await page.goto(f"{server.PREFIX}/dom.html")
    handle = await page.query_selector("#outer")
    assert handle
    assert await handle.get_attribute("name") == "value"
    assert await handle.get_attribute("foo") is None
    assert await page.get_attribute("#outer", "name") == "value"
    assert await page.get_attribute("#outer", "foo") is None


async def test_EH_027_input_value_should_work(page: Page, server: Server) -> None:
    await page.goto(f"{server.PREFIX}/dom.html")

    await page.select_option("#select", "foo")
    assert await page.input_value("#select") == "foo"

    await page.fill("#textarea", "text value")
    assert await page.input_value("#textarea") == "text value"

    await page.fill("#input", "input value")
    assert await page.input_value("#input") == "input value"
    handle = await page.query_selector("#input")
    assert handle
    assert await handle.input_value() == "input value"

    with pytest.raises(Error) as exc_info:
        await page.input_value("#inner")
    assert (
        "Node is not an <input>, <textarea> or <select> element"
        in exc_info.value.message
    )
    handle2 = await page.query_selector("#inner")
    assert handle2
    with pytest.raises(Error) as exc_info:
        await handle2.input_value()
    assert (
        "Node is not an <input>, <textarea> or <select> element"
        in exc_info.value.message
    )


async def test_EH_028_inner_html_should_work(page: Page, server: Server) -> None:
    await page.goto(f"{server.PREFIX}/dom.html")
    handle = await page.query_selector("#outer")
    assert handle
    assert await handle.inner_html() == '<div id="inner">Text,\nmore text</div>'
    assert await page.inner_html("#outer") == '<div id="inner">Text,\nmore text</div>'


async def test_EH_029_inner_text_should_work(page: Page, server: Server) -> None:
    await page.goto(f"{server.PREFIX}/dom.html")
    handle = await page.query_selector("#inner")
    assert handle
    assert await handle.inner_text() == "Text, more text"
    assert await page.inner_text("#inner") == "Text, more text"


async def test_EH_030_inner_text_should_throw(page: Page) -> None:
    await page.set_content("<svg>text</svg>")
    with pytest.raises(Error) as exc_info1:
        await page.inner_text("svg")
    assert "Node is not an HTMLElement" in exc_info1.value.message
    handle = await page.query_selector("svg")
    assert handle
    with pytest.raises(Error) as exc_info2:
        await handle.inner_text()
    assert "Node is not an HTMLElement" in exc_info2.value.message


async def test_EH_031_text_content_should_work(page: Page, server: Server) -> None:
    await page.goto(f"{server.PREFIX}/dom.html")
    handle = await page.query_selector("#inner")
    assert handle
    assert await handle.text_content() == "Text,\nmore text"
    assert await page.text_content("#inner") == "Text,\nmore text"


async def test_EH_032_text_content_should_work_on_shadow_root(page: Page) -> None:
    await page.set_content(
        """
    <div></div>
    <script>
      document.querySelector('div').attachShadow({ mode: 'open' }).innerHTML = '<div>hello</div>';
    </script>
  """
    )
    div = await page.query_selector("div")
    assert div
    root = (await div.evaluate_handle("div => div.shadowRoot")).as_element()
    assert root
    assert await root.text_content() == "hello"
    # We do not match ShadowRoot as ":scope".
    assert await root.query_selector_all(":scope div") == []


async def test_EH_033_is_visible_and_is_hidden_should_work(page: Page) -> None:
    await page.set_content("<div>Hi</div><span></span>")

    div = await page.query_selector("div")
    assert div
    assert await div.is_visible() is True
    assert await div.is_hidden() is False
    assert await page.is_visible("div") is True
    assert await page.is_hidden("div") is False

    span = await page.query_selector("span")
    assert span
    assert await span.is_visible() is False
    assert await span.is_hidden() is True
    assert await page.is_visible("span") is False
    assert await page.is_hidden("span") is True

    assert await page.is_visible("no-such-element") is False
    assert await page.is_hidden("no-such-element") is True


async def test_EH_034_is_visible_should_not_throw_when_the_dom_element_is_not_connected(
    page: Page,
) -> None:
    await page.set_content('<div id="root"></div>')
    await page.evaluate(
        """() => {
    function insert() {
      document.getElementById('root').innerHTML = '<div id="problem">Problem</div>';
      window.requestAnimationFrame(remove);
    }
    function remove() {
      const node = document.getElementById('problem');
      node?.parentNode?.removeChild(node);
      window.requestAnimationFrame(insert);
    }
    window.requestAnimationFrame(insert);
  }"""
    )

    for _ in range(10):
        await page.is_visible("#problem")


async def test_EH_035_is_enabled_and_is_disabled_should_work(page: Page) -> None:
    await page.set_content(
        """
    <button disabled>button1</button>
    <button>button2</button>
    <div>div</div>
  """
    )
    div = await page.query_selector("div")
    assert div
    assert await div.is_enabled() is True
    assert await div.is_disabled() is False
    assert await page.is_enabled("div") is True
    assert await page.is_disabled("div") is False
    button1 = await page.query_selector(':text("button1")')
    assert button1
    assert await button1.is_enabled() is False
    assert await button1.is_disabled() is True
    assert await page.is_enabled(':text("button1")') is False
    assert await page.is_disabled(':text("button1")') is True
    button2 = await page.query_selector(':text("button2")')
    assert button2
    assert await button2.is_enabled() is True
    assert await button2.is_disabled() is False
    assert await page.is_enabled(':text("button2")') is True
    assert await page.is_disabled(':text("button2")') is False


async def test_EH_036_is_enabled_and_is_disabled_should_work_with_select_option_optgroup_correctly(
    page: Page,
) -> None:
    await page.set_content(
        """
    <select name="select">
      <option id="enabled1" value="1">Enabled</option>
      <option id="disabled1" value="2" disabled>Disabled</option>
      <optgroup label="Foo1">
        <option value="mercedes">Mercedes</option>
      </optgroup>
      <optgroup label="Foo2" disabled>
        <option value="mercedes">Mercedes</option>
      </optgroup>
    </select>
  """
    )

    async def query(selector: str) -> ElementHandle:
        handle = await page.query_selector(selector)
        assert handle
        return handle

    assert await (await query("#enabled1")).is_enabled() is True
    assert await (await query("#enabled1")).is_disabled() is False
    assert await (await query("#disabled1")).is_enabled() is False
    assert await (await query("#disabled1")).is_disabled() is True
    assert await (await query("optgroup >> nth=0")).is_enabled() is True
    assert await (await query("optgroup >> nth=0")).is_disabled() is False
    assert await (await query("optgroup >> nth=1")).is_enabled() is False
    assert await (await query("optgroup >> nth=1")).is_disabled() is True


async def test_EH_037_is_editable_should_work(page: Page) -> None:
    await page.set_content(
        "<input id=input1 disabled><textarea></textarea><input id=input2>"
    )
    await page.eval_on_selector("textarea", "t => t.readOnly = true")
    input1 = await page.query_selector("#input1")
    assert input1
    assert await input1.is_editable() is False
    assert await page.is_editable("#input1") is False
    input2 = await page.query_selector("#input2")
    assert input2
    assert await input2.is_editable() is True
    assert await page.is_editable("#input2") is True
    textarea = await page.query_selector("textarea")
    assert textarea
    assert await textarea.is_editable() is False
    assert await page.is_editable("textarea") is False


async def test_EH_038_is_checked_should_work(page: Page) -> None:
    await page.set_content("<input type='checkbox' checked><div>Not a checkbox</div>")
    handle = await page.query_selector("input")
    assert handle
    assert await handle.is_checked() is True
    assert await page.is_checked("input") is True
    await handle.evaluate("input => input.checked = false")
    assert await handle.is_checked() is False
    assert await page.is_checked("input") is False
    with pytest.raises(Error) as exc_info:
        await page.is_checked("div")
    assert "Not a checkbox or radio button" in exc_info.value.message
