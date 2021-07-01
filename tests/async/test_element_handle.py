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

import asyncio

import pytest

from playwright.async_api import Error, Page
from tests.server import Server


async def test_bounding_box(page, server):
    await page.set_viewport_size({"width": 500, "height": 500})
    await page.goto(server.PREFIX + "/grid.html")
    element_handle = await page.query_selector(".box:nth-of-type(13)")
    box = await element_handle.bounding_box()
    assert box == {"x": 100, "y": 50, "width": 50, "height": 50}


async def test_bounding_box_handle_nested_frames(page, server):
    await page.set_viewport_size({"width": 500, "height": 500})
    await page.goto(server.PREFIX + "/frames/nested-frames.html")
    nested_frame = page.frame(name="dos")
    element_handle = await nested_frame.query_selector("div")
    box = await element_handle.bounding_box()
    assert box == {"x": 24, "y": 224, "width": 268, "height": 18}


async def test_bounding_box_return_null_for_invisible_elements(page, server):
    await page.set_content('<div style="display:none">hi</div>')
    element = await page.query_selector("div")
    assert await element.bounding_box() is None


async def test_bounding_box_force_a_layout(page, server):
    await page.set_viewport_size({"width": 500, "height": 500})
    await page.set_content('<div style="width: 100px; height: 100px">hello</div>')
    element_handle = await page.query_selector("div")
    await page.evaluate('element => element.style.height = "200px"', element_handle)
    box = await element_handle.bounding_box()
    assert box == {"x": 8, "y": 8, "width": 100, "height": 200}


async def test_bounding_box_with_SVG_nodes(page, server):
    await page.set_content(
        """<svg xmlns="http://www.w3.org/2000/svg" width="500" height="500">
             <rect id="theRect" x="30" y="50" width="200" height="300"></rect>
           </svg>"""
    )
    element = await page.query_selector("#therect")
    pw_bounding_box = await element.bounding_box()
    web_bounding_box = await page.evaluate(
        """e => {
            rect = e.getBoundingClientRect()
            return {x: rect.x, y: rect.y, width: rect.width, height: rect.height}
        }""",
        element,
    )
    assert pw_bounding_box == web_bounding_box


async def test_bounding_box_with_page_scale(browser, server):
    context = await browser.new_context(
        viewport={"width": 400, "height": 400, "is_mobile": True}
    )
    page = await context.new_page()
    await page.goto(server.PREFIX + "/input/button.html")
    button = await page.query_selector("button")
    await button.evaluate(
        """button => {
            document.body.style.margin = '0'
            button.style.borderWidth = '0'
            button.style.width = '200px'
            button.style.height = '20px'
            button.style.marginLeft = '17px'
            button.style.marginTop = '23px'
        }"""
    )

    box = await button.bounding_box()
    assert round(box["x"] * 100) == 17 * 100
    assert round(box["y"] * 100) == 23 * 100
    assert round(box["width"] * 100) == 200 * 100
    assert round(box["height"] * 100) == 20 * 100
    await context.close()


async def test_bounding_box_when_inline_box_child_is_outside_of_viewport(page, server):
    await page.set_content(
        """
            <style>
            i {
            position: absolute
            top: -1000px
            }
            body {
            margin: 0
            font-size: 12px
            }
            </style>
            <span><i>woof</i><b>doggo</b></span>
        """
    )
    handle = await page.query_selector("span")
    box = await handle.bounding_box()
    web_bounding_box = await handle.evaluate(
        """e => {
        rect = e.getBoundingClientRect();
        return {x: rect.x, y: rect.y, width: rect.width, height: rect.height};
    }"""
    )

    def roundbox(b):
        return {
            "x": round(b["x"] * 100),
            "y": round(b["y"] * 100),
            "width": round(b["width"] * 100),
            "height": round(b["height"] * 100),
        }

    assert roundbox(box) == roundbox(web_bounding_box)


async def test_content_frame(page, server, utils):
    await page.goto(server.EMPTY_PAGE)
    await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    element_handle = await page.query_selector("#frame1")
    frame = await element_handle.content_frame()
    assert frame == page.frames[1]


async def test_content_frame_for_non_iframes(page, server, utils):
    await page.goto(server.EMPTY_PAGE)
    await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    frame = page.frames[1]
    element_handle = await frame.evaluate_handle("document.body")
    assert await element_handle.content_frame() is None


async def test_content_frame_for_document_element(page, server, utils):
    await page.goto(server.EMPTY_PAGE)
    await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    frame = page.frames[1]
    element_handle = await frame.evaluate_handle("document.documentElement")
    assert await element_handle.content_frame() is None


async def test_owner_frame(page, server, utils):
    await page.goto(server.EMPTY_PAGE)
    await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    frame = page.frames[1]
    element_handle = await frame.evaluate_handle("document.body")
    assert await element_handle.owner_frame() == frame


async def test_owner_frame_for_cross_process_iframes(page, server, utils):
    await page.goto(server.EMPTY_PAGE)
    await utils.attach_frame(
        page, "frame1", server.CROSS_PROCESS_PREFIX + "/empty.html"
    )
    frame = page.frames[1]
    element_handle = await frame.evaluate_handle("document.body")
    assert await element_handle.owner_frame() == frame


async def test_owner_frame_for_document(page, server, utils):
    await page.goto(server.EMPTY_PAGE)
    await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    frame = page.frames[1]
    element_handle = await frame.evaluate_handle("document")
    assert await element_handle.owner_frame() == frame


async def test_owner_frame_for_iframe_elements(page, server, utils):
    await page.goto(server.EMPTY_PAGE)
    await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    frame = page.main_frame
    element_handle = await frame.evaluate_handle('document.querySelector("#frame1")')
    assert await element_handle.owner_frame() == frame


async def test_owner_frame_for_cross_frame_evaluations(page, server, utils):
    await page.goto(server.EMPTY_PAGE)
    await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    frame = page.main_frame
    element_handle = await frame.evaluate_handle(
        'document.querySelector("#frame1").contentWindow.document.body'
    )
    assert await element_handle.owner_frame() == frame.child_frames[0]


async def test_owner_frame_for_detached_elements(page, server):
    await page.goto(server.EMPTY_PAGE)
    div_handle = await page.evaluate_handle(
        """() => {
            div = document.createElement('div');
            document.body.appendChild(div);
            return div;
        }"""
    )

    assert await div_handle.owner_frame() == page.main_frame
    await page.evaluate(
        """() => {
            div = document.querySelector('div')
            document.body.removeChild(div)
        }"""
    )
    assert await div_handle.owner_frame() == page.main_frame


async def test_owner_frame_for_adopted_elements(page, server):
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_popup() as popup_info:
        await page.evaluate(
            "url => window.__popup = window.open(url)", server.EMPTY_PAGE
        )
    popup = await popup_info.value
    div_handle = await page.evaluate_handle(
        """() => {
            div = document.createElement('div');
            document.body.appendChild(div);
            return div;
        }"""
    )
    assert await div_handle.owner_frame() == page.main_frame
    await popup.wait_for_load_state("domcontentloaded")
    await page.evaluate(
        """() => {
            div = document.querySelector('div');
            window.__popup.document.body.appendChild(div);
        }"""
    )
    assert await div_handle.owner_frame() == popup.main_frame


async def test_click(page, server):
    await page.goto(server.PREFIX + "/input/button.html")
    button = await page.query_selector("button")
    await button.click()
    assert await page.evaluate("result") == "Clicked"


async def test_click_with_node_removed(page, server):
    await page.goto(server.PREFIX + "/input/button.html")
    await page.evaluate('delete window["Node"]')
    button = await page.query_selector("button")
    await button.click()
    assert await page.evaluate("result") == "Clicked"


async def test_click_for_shadow_dom_v1(page, server):
    await page.goto(server.PREFIX + "/shadow.html")
    button_handle = await page.evaluate_handle("button")
    await button_handle.click()
    assert await page.evaluate("clicked")


async def test_click_for_TextNodes(page, server):
    await page.goto(server.PREFIX + "/input/button.html")
    buttonTextNode = await page.evaluate_handle(
        'document.querySelector("button").firstChild'
    )
    await buttonTextNode.click()
    assert await page.evaluate("result") == "Clicked"


async def test_click_throw_for_detached_nodes(page, server):
    await page.goto(server.PREFIX + "/input/button.html")
    button = await page.query_selector("button")
    await page.evaluate("button => button.remove()", button)
    with pytest.raises(Error) as exc_info:
        await button.click()
    assert "Element is not attached to the DOM" in exc_info.value.message


async def test_click_throw_for_hidden_nodes_with_force(page, server):
    await page.goto(server.PREFIX + "/input/button.html")
    button = await page.query_selector("button")
    await page.evaluate('button => button.style.display = "none"', button)
    with pytest.raises(Error) as exc_info:
        await button.click(force=True)
    assert "Element is not visible" in exc_info.value.message


async def test_click_throw_for_recursively_hidden_nodes_with_force(page, server):
    await page.goto(server.PREFIX + "/input/button.html")
    button = await page.query_selector("button")
    await page.evaluate('button => button.parentElement.style.display = "none"', button)
    with pytest.raises(Error) as exc_info:
        await button.click(force=True)
    assert "Element is not visible" in exc_info.value.message


async def test_click_throw_for__br__elements_with_force(page, server):
    await page.set_content("hello<br>goodbye")
    br = await page.query_selector("br")
    with pytest.raises(Error) as exc_info:
        await br.click(force=True)
    assert "Element is outside of the viewport" in exc_info.value.message


async def test_double_click_the_button(page, server):
    await page.goto(server.PREFIX + "/input/button.html")
    await page.evaluate(
        """() => {
            window.double = false;
            button = document.querySelector('button');
            button.addEventListener('dblclick', event => {
            window.double = true;
            });
        }"""
    )
    button = await page.query_selector("button")
    await button.dblclick()
    assert await page.evaluate("double")
    assert await page.evaluate("result") == "Clicked"


async def test_hover(page, server):
    await page.goto(server.PREFIX + "/input/scrollable.html")
    button = await page.query_selector("#button-6")
    await button.hover()
    assert (
        await page.evaluate('document.querySelector("button:hover").id') == "button-6"
    )


async def test_hover_when_node_is_removed(page, server):
    await page.goto(server.PREFIX + "/input/scrollable.html")
    await page.evaluate('delete window["Node"]')
    button = await page.query_selector("#button-6")
    await button.hover()
    assert (
        await page.evaluate('document.querySelector("button:hover").id') == "button-6"
    )


async def test_scroll(page, server):
    await page.goto(server.PREFIX + "/offscreenbuttons.html")
    for i in range(11):
        button = await page.query_selector(f"#btn{i}")
        before = await button.evaluate(
            """button => {
                return button.getBoundingClientRect().right - window.innerWidth
            }"""
        )

        assert before == 10 * i
        await button.scroll_into_view_if_needed()
        after = await button.evaluate(
            """button => {
                return button.getBoundingClientRect().right - window.innerWidth
            }"""
        )

        assert after <= 0
        await page.evaluate("() => window.scrollTo(0, 0)")


async def test_scroll_should_throw_for_detached_element(page, server):
    await page.set_content("<div>Hello</div>")
    div = await page.query_selector("div")
    await div.evaluate("div => div.remove()")
    with pytest.raises(Error) as exc_info:
        await div.scroll_into_view_if_needed()
    assert "Element is not attached to the DOM" in exc_info.value.message


async def waiting_helper(page, after):
    div = await page.query_selector("div")
    done = list()

    async def scroll():
        done.append(False)
        await div.scroll_into_view_if_needed()
        done.append(True)

    promise = asyncio.create_task(scroll())
    await asyncio.sleep(0)  # execute scheduled tasks, but don't await them
    await page.evaluate("() => new Promise(f => setTimeout(f, 1000))")
    assert done == [False]
    await div.evaluate(after)
    await promise
    assert done == [False, True]


async def test_should_wait_for_display_none_to_become_visible(page):
    await page.set_content('<div style="display:none">Hello</div>')
    await waiting_helper(page, 'div => div.style.display = "block"')


async def test_should_wait_for_display_contents_to_become_visible(page):
    await page.set_content('<div style="display:contents">Hello</div>')
    await waiting_helper(page, 'div => div.style.display = "block"')


async def test_should_wait_for_visibility_hidden_to_become_visible(page):
    await page.set_content('<div style="visibility:hidden">Hello</div>')
    await waiting_helper(page, 'div => div.style.visibility = "visible"')


async def test_should_wait_for_zero_sized_element_to_become_visible(page):
    await page.set_content('<div style="height:0">Hello</div>')
    await waiting_helper(page, 'div => div.style.height = "100px"')


async def test_should_wait_for_nested_display_none_to_become_visible(page):
    await page.set_content('<span style="display:none"><div>Hello</div></span>')
    await waiting_helper(page, 'div => div.parentElement.style.display = "block"')


async def test_should_timeout_waiting_for_visible(page):
    await page.set_content('<div style="display:none">Hello</div>')
    div = await page.query_selector("div")
    with pytest.raises(Error) as exc_info:
        await div.scroll_into_view_if_needed(timeout=3000)
    assert "element is not visible" in exc_info.value.message


async def test_fill_input(page, server):
    await page.goto(server.PREFIX + "/input/textarea.html")
    handle = await page.query_selector("input")
    await handle.fill("some value")
    assert await page.evaluate("result") == "some value"


async def test_fill_input_when_Node_is_removed(page, server):
    await page.goto(server.PREFIX + "/input/textarea.html")
    await page.evaluate('delete window["Node"]')
    handle = await page.query_selector("input")
    await handle.fill("some value")
    assert await page.evaluate("result") == "some value"


async def test_select_textarea(page, server, is_firefox):
    await page.goto(server.PREFIX + "/input/textarea.html")
    textarea = await page.query_selector("textarea")
    await textarea.evaluate('textarea => textarea.value = "some value"')
    await textarea.select_text()
    if is_firefox:
        assert await textarea.evaluate("el => el.selectionStart") == 0
        assert await textarea.evaluate("el => el.selectionEnd") == 10
    else:
        assert (
            await page.evaluate("() => window.getSelection().toString()")
            == "some value"
        )


async def test_select_input(page, server, is_firefox):
    await page.goto(server.PREFIX + "/input/textarea.html")
    input = await page.query_selector("input")
    await input.evaluate('input => input.value = "some value"')
    await input.select_text()
    if is_firefox:
        assert await input.evaluate("el => el.selectionStart") == 0
        assert await input.evaluate("el => el.selectionEnd") == 10
    else:
        assert (
            await page.evaluate("() => window.getSelection().toString()")
            == "some value"
        )


async def test_select_text_select_plain_div(page, server):
    await page.goto(server.PREFIX + "/input/textarea.html")
    div = await page.query_selector("div.plain")
    await div.select_text()
    assert await page.evaluate("() => window.getSelection().toString()") == "Plain div"


async def test_select_text_timeout_waiting_for_invisible_element(page, server):
    await page.goto(server.PREFIX + "/input/textarea.html")
    textarea = await page.query_selector("textarea")
    await textarea.evaluate('e => e.style.display = "none"')
    with pytest.raises(Error) as exc_info:
        await textarea.select_text(timeout=3000)
    assert "element is not visible" in exc_info.value.message


async def test_select_text_wait_for_visible(page, server):
    await page.goto(server.PREFIX + "/input/textarea.html")
    textarea = await page.query_selector("textarea")
    await textarea.evaluate('textarea => textarea.value = "some value"')
    await textarea.evaluate('e => e.style.display = "none"')
    done = list()

    async def select_text():
        done.append(False)
        await textarea.select_text(timeout=3000)
        done.append(True)

    promise = asyncio.create_task(select_text())
    await asyncio.sleep(0)  # execute scheduled tasks, but don't await them
    await page.evaluate("() => new Promise(f => setTimeout(f, 1000))")
    await textarea.evaluate('e => e.style.display = "block"')
    await promise
    assert done == [False, True]


async def test_a_nice_preview(page, server):
    await page.goto(f"{server.PREFIX}/dom.html")
    outer = await page.query_selector("#outer")
    inner = await page.query_selector("#inner")
    check = await page.query_selector("#check")
    text = await inner.evaluate_handle("e => e.firstChild")
    await page.evaluate("1")  # Give them a chance to calculate the preview.
    assert str(outer) == 'JSHandle@<div id="outer" name="value">…</div>'
    assert str(inner) == 'JSHandle@<div id="inner">Text,↵more text</div>'
    assert str(text) == "JSHandle@#text=Text,↵more text"
    assert (
        str(check) == 'JSHandle@<input checked id="check" foo="bar"" type="checkbox"/>'
    )


async def test_get_attribute(page, server):
    await page.goto(f"{server.PREFIX}/dom.html")
    handle = await page.query_selector("#outer")
    assert await handle.get_attribute("name") == "value"
    assert await page.get_attribute("#outer", "name") == "value"


async def test_inner_html(page, server):
    await page.goto(f"{server.PREFIX}/dom.html")
    handle = await page.query_selector("#outer")
    assert await handle.inner_html() == '<div id="inner">Text,\nmore text</div>'
    assert await page.inner_html("#outer") == '<div id="inner">Text,\nmore text</div>'


async def test_inner_text(page, server):
    await page.goto(f"{server.PREFIX}/dom.html")
    handle = await page.query_selector("#inner")
    assert await handle.inner_text() == "Text, more text"
    assert await page.inner_text("#inner") == "Text, more text"


async def test_inner_text_should_throw(page, server):
    await page.set_content("<svg>text</svg>")
    with pytest.raises(Error) as exc_info1:
        await page.inner_text("svg")
    assert "Not an HTMLElement" in exc_info1.value.message

    handle = await page.query_selector("svg")
    with pytest.raises(Error) as exc_info2:
        await handle.inner_text()
    assert "Not an HTMLElement" in exc_info2.value.message


async def test_text_content(page, server):
    await page.goto(f"{server.PREFIX}/dom.html")
    handle = await page.query_selector("#inner")
    assert await handle.text_content() == "Text,\nmore text"
    assert await page.text_content("#inner") == "Text,\nmore text"


async def test_check_the_box(page):
    await page.set_content('<input id="checkbox" type="checkbox"></input>')
    input = await page.query_selector("input")
    await input.check()
    assert await page.evaluate("checkbox.checked")


async def test_uncheck_the_box(page):
    await page.set_content('<input id="checkbox" type="checkbox" checked></input>')
    input = await page.query_selector("input")
    await input.uncheck()
    assert await page.evaluate("checkbox.checked") is False


async def test_select_single_option(page, server):
    await page.goto(server.PREFIX + "/input/select.html")
    select = await page.query_selector("select")
    await select.select_option(value="blue")
    assert await page.evaluate("result.onInput") == ["blue"]
    assert await page.evaluate("result.onChange") == ["blue"]


async def test_focus_a_button(page, server):
    await page.goto(server.PREFIX + "/input/button.html")
    button = await page.query_selector("button")
    assert await button.evaluate("button => document.activeElement === button") is False
    await button.focus()
    assert await button.evaluate("button => document.activeElement === button")


async def test_is_visible_and_is_hidden_should_work(page):
    await page.set_content("<div>Hi</div><span></span>")
    div = await page.query_selector("div")
    assert await div.is_visible()
    assert await div.is_hidden() is False
    assert await page.is_visible("div")
    assert await page.is_hidden("div") is False
    span = await page.query_selector("span")
    assert await span.is_visible() is False
    assert await span.is_hidden()
    assert await page.is_visible("span") is False
    assert await page.is_hidden("span")


async def test_is_enabled_and_is_disabled_should_work(page):
    await page.set_content(
        """
        <button disabled>button1</button>
        <button>button2</button>
        <div>div</div>
    """
    )
    div = await page.query_selector("div")
    assert await div.is_enabled()
    assert await div.is_disabled() is False
    assert await page.is_enabled("div")
    assert await page.is_disabled("div") is False
    button1 = await page.query_selector(":text('button1')")
    assert await button1.is_enabled() is False
    assert await button1.is_disabled()
    assert await page.is_enabled(":text('button1')") is False
    assert await page.is_disabled(":text('button1')")
    button2 = await page.query_selector(":text('button2')")
    assert await button2.is_enabled()
    assert await button2.is_disabled() is False
    assert await page.is_enabled(":text('button2')")
    assert await page.is_disabled(":text('button2')") is False


async def test_is_editable_should_work(page):
    await page.set_content(
        "<input id=input1 disabled><textarea></textarea><input id=input2>"
    )
    await page.eval_on_selector("textarea", "t => t.readOnly = true")
    input1 = await page.query_selector("#input1")
    assert await input1.is_editable() is False
    assert await page.is_editable("#input1") is False
    input2 = await page.query_selector("#input2")
    assert await input2.is_editable()
    assert await page.is_editable("#input2")
    textarea = await page.query_selector("textarea")
    assert await textarea.is_editable() is False
    assert await page.is_editable("textarea") is False


async def test_is_checked_should_work(page):
    await page.set_content('<input type="checkbox" checked><div>Not a checkbox</div>')
    handle = await page.query_selector("input")
    assert await handle.is_checked()
    assert await page.is_checked("input")
    await handle.evaluate("input => input.checked = false")
    assert await handle.is_checked() is False
    assert await page.is_checked("input") is False
    with pytest.raises(Error) as exc_info:
        await page.is_checked("div")
    assert "Not a checkbox or radio button" in exc_info.value.message


async def test_input_value(page: Page, server: Server):
    await page.goto(server.PREFIX + "/input/textarea.html")
    element = await page.query_selector("input")
    await element.fill("my-text-content")
    assert await element.input_value() == "my-text-content"

    await element.fill("")
    assert await element.input_value() == ""
