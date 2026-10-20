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

from typing import Any, Dict

import pytest

from playwright.sync_api import Browser, Error, Page
from tests.server import Server
from tests.sync.utils import Utils


def test_bounding_box(page: Page, server: Server) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.goto(server.PREFIX + "/grid.html")
    element_handle = page.query_selector(".box:nth-of-type(13)")
    assert element_handle
    box = element_handle.bounding_box()
    assert box == {"x": 100, "y": 50, "width": 50, "height": 50}


def test_bounding_box_handle_nested_frames(page: Page, server: Server) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.goto(server.PREFIX + "/frames/nested-frames.html")
    nested_frame = page.frame(name="dos")
    assert nested_frame
    element_handle = nested_frame.query_selector("div")
    assert element_handle
    box = element_handle.bounding_box()
    assert box == {"x": 24, "y": 224, "width": 268, "height": 18}


def test_bounding_box_return_null_for_invisible_elements(page: Page) -> None:
    page.set_content('<div style="display:none">hi</div>')
    element = page.query_selector("div")
    assert element
    assert element.bounding_box() is None


def test_bounding_box_force_a_layout(page: Page) -> None:
    page.set_viewport_size({"width": 500, "height": 500})
    page.set_content('<div style="width: 100px; height: 100px">hello</div>')
    element_handle = page.query_selector("div")
    assert element_handle
    page.evaluate('element => element.style.height = "200px"', element_handle)
    box = element_handle.bounding_box()
    assert box == {"x": 8, "y": 8, "width": 100, "height": 200}


def test_bounding_box_with_SVG_nodes(page: Page) -> None:
    page.set_content(
        """<svg xmlns="http://www.w3.org/2000/svg" width="500" height="500">
             <rect id="theRect" x="30" y="50" width="200" height="300"></rect>
           </svg>"""
    )
    element = page.query_selector("#therect")
    assert element
    pw_bounding_box = element.bounding_box()
    web_bounding_box = page.evaluate(
        """e => {
            rect = e.getBoundingClientRect()
            return {x: rect.x, y: rect.y, width: rect.width, height: rect.height}
        }""",
        element,
    )
    assert pw_bounding_box == web_bounding_box


@pytest.mark.skip_browser("firefox")
def test_bounding_box_with_page_scale(browser: Browser, server: Server) -> None:
    context = browser.new_context(
        viewport={"width": 400, "height": 400}, is_mobile=True
    )
    page = context.new_page()
    page.goto(server.PREFIX + "/input/button.html")
    button = page.query_selector("button")
    assert button
    button.evaluate(
        """button => {
            document.body.style.margin = '0'
            button.style.borderWidth = '0'
            button.style.width = '200px'
            button.style.height = '20px'
            button.style.marginLeft = '17px'
            button.style.marginTop = '23px'
        }"""
    )

    box = button.bounding_box()
    assert box
    assert round(box["x"] * 100) == 17 * 100
    assert round(box["y"] * 100) == 23 * 100
    assert round(box["width"] * 100) == 200 * 100
    assert round(box["height"] * 100) == 20 * 100
    context.close()


def test_bounding_box_when_inline_box_child_is_outside_of_viewport(page: Page) -> None:
    page.set_content(
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
    handle = page.query_selector("span")
    assert handle
    box = handle.bounding_box()
    assert handle
    web_bounding_box = handle.evaluate(
        """e => {
        rect = e.getBoundingClientRect();
        return {x: rect.x, y: rect.y, width: rect.width, height: rect.height};
    }"""
    )

    def roundbox(b: Any) -> Dict:
        return {
            "x": round(b["x"] * 100),
            "y": round(b["y"] * 100),
            "width": round(b["width"] * 100),
            "height": round(b["height"] * 100),
        }

    assert roundbox(box) == roundbox(web_bounding_box)


def test_content_frame(page: Page, server: Server, utils: Utils) -> None:
    page.goto(server.EMPTY_PAGE)
    utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    element_handle = page.query_selector("#frame1")
    assert element_handle
    frame = element_handle.content_frame()
    assert frame == page.frames[1]


def test_content_frame_for_non_iframes(
    page: Page, server: Server, utils: Utils
) -> None:
    page.goto(server.EMPTY_PAGE)
    utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    frame = page.frames[1]
    element_handle = frame.evaluate_handle("document.body").as_element()
    assert element_handle
    assert element_handle.content_frame() is None


def test_content_frame_for_document_element(
    page: Page, server: Server, utils: Utils
) -> None:
    page.goto(server.EMPTY_PAGE)
    utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    frame = page.frames[1]
    element_handle = frame.evaluate_handle("document.documentElement").as_element()
    assert element_handle
    assert element_handle.content_frame() is None


def test_owner_frame(page: Page, server: Server, utils: Utils) -> None:
    page.goto(server.EMPTY_PAGE)
    utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    frame = page.frames[1]
    element_handle = frame.evaluate_handle("document.body").as_element()
    assert element_handle
    assert element_handle.owner_frame() == frame


def test_owner_frame_for_cross_process_iframes(
    page: Page, server: Server, utils: Utils
) -> None:
    page.goto(server.EMPTY_PAGE)
    utils.attach_frame(page, "frame1", server.CROSS_PROCESS_PREFIX + "/empty.html")
    frame = page.frames[1]
    element_handle = frame.evaluate_handle("document.body").as_element()
    assert element_handle
    assert element_handle.owner_frame() == frame


def test_owner_frame_for_document(page: Page, server: Server, utils: Utils) -> None:
    page.goto(server.EMPTY_PAGE)
    utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    frame = page.frames[1]
    element_handle = frame.evaluate_handle("document").as_element()
    assert element_handle
    assert element_handle.owner_frame() == frame


def test_owner_frame_for_iframe_elements(
    page: Page, server: Server, utils: Utils
) -> None:
    page.goto(server.EMPTY_PAGE)
    utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    frame = page.main_frame
    element_handle = frame.evaluate_handle(
        'document.querySelector("#frame1")'
    ).as_element()
    assert element_handle
    assert element_handle.owner_frame() == frame


def test_owner_frame_for_cross_frame_evaluations(
    page: Page, server: Server, utils: Utils
) -> None:
    page.goto(server.EMPTY_PAGE)
    utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    frame = page.main_frame
    element_handle = frame.evaluate_handle(
        'document.querySelector("#frame1").contentWindow.document.body'
    ).as_element()
    assert element_handle
    assert element_handle.owner_frame() == frame.child_frames[0]


def test_owner_frame_for_detached_elements(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    div_handle = page.evaluate_handle(
        """() => {
            div = document.createElement('div');
            document.body.appendChild(div);
            return div;
        }"""
    ).as_element()
    assert div_handle

    assert div_handle.owner_frame() == page.main_frame
    page.evaluate(
        """() => {
            div = document.querySelector('div')
            document.body.removeChild(div)
        }"""
    )
    assert div_handle.owner_frame() == page.main_frame


def test_click(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/button.html")
    button = page.query_selector("button")
    assert button
    button.click()
    assert page.evaluate("result") == "Clicked"


def test_click_with_node_removed(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/button.html")
    page.evaluate('delete window["Node"]')
    button = page.query_selector("button")
    assert button
    button.click()
    assert page.evaluate("result") == "Clicked"


def test_click_for_shadow_dom_v1(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/shadow.html")
    button_handle = page.evaluate_handle("button").as_element()
    assert button_handle
    button_handle.click()
    assert page.evaluate("clicked")


def test_click_for_TextNodes(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/button.html")
    buttonTextNode = page.evaluate_handle(
        'document.querySelector("button").firstChild'
    ).as_element()
    assert buttonTextNode
    buttonTextNode.click()
    assert page.evaluate("result") == "Clicked"


def test_click_throw_for_detached_nodes(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/button.html")
    button = page.query_selector("button")
    assert button
    page.evaluate("button => button.remove()", button)
    with pytest.raises(Error) as exc_info:
        button.click()
    assert "Element is not attached to the DOM" in exc_info.value.message


def test_click_throw_for_hidden_nodes_with_force(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/button.html")
    button = page.query_selector("button")
    assert button
    page.evaluate('button => button.style.display = "none"', button)
    with pytest.raises(Error) as exc_info:
        button.click(force=True)
    assert "Element is not visible" in exc_info.value.message


def test_click_throw_for_recursively_hidden_nodes_with_force(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/input/button.html")
    button = page.query_selector("button")
    assert button
    page.evaluate('button => button.parentElement.style.display = "none"', button)
    with pytest.raises(Error) as exc_info:
        button.click(force=True)
    assert "Element is not visible" in exc_info.value.message


def test_click_throw_for__br__elements_with_force(page: Page) -> None:
    page.set_content("hello<br>goodbye")
    br = page.query_selector("br")
    assert br
    with pytest.raises(Error) as exc_info:
        br.click(force=True)
    assert "Element is outside of the viewport" in exc_info.value.message


def test_double_click_the_button(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/button.html")
    page.evaluate(
        """() => {
            window.double = false;
            button = document.querySelector('button');
            button.addEventListener('dblclick', event => {
            window.double = true;
            });
        }"""
    )
    button = page.query_selector("button")
    assert button
    button.dblclick()
    assert page.evaluate("double")
    assert page.evaluate("result") == "Clicked"


def test_hover(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/scrollable.html")
    button = page.query_selector("#button-6")
    assert button
    button.hover()
    assert page.evaluate('document.querySelector("button:hover").id') == "button-6"


def test_hover_when_node_is_removed(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/scrollable.html")
    page.evaluate('delete window["Node"]')
    button = page.query_selector("#button-6")
    assert button
    button.hover()
    assert page.evaluate('document.querySelector("button:hover").id') == "button-6"


def test_scroll(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/offscreenbuttons.html")
    for i in range(11):
        button = page.query_selector(f"#btn{i}")
        assert button
        before = button.evaluate(
            """button => {
                return button.getBoundingClientRect().right - window.innerWidth
            }"""
        )

        assert before == 10 * i
        button.scroll_into_view_if_needed()
        after = button.evaluate(
            """button => {
                return button.getBoundingClientRect().right - window.innerWidth
            }"""
        )

        assert after <= 0
        page.evaluate("() => window.scrollTo(0, 0)")


def test_scroll_should_throw_for_detached_element(page: Page) -> None:
    page.set_content("<div>Hello</div>")
    div = page.query_selector("div")
    assert div
    div.evaluate("div => div.remove()")
    with pytest.raises(Error) as exc_info:
        div.scroll_into_view_if_needed()
    assert "Element is not attached to the DOM" in exc_info.value.message


def test_should_timeout_waiting_for_visible(page: Page) -> None:
    page.set_content('<div style="display:none">Hello</div>')
    div = page.query_selector("div")
    assert div
    with pytest.raises(Error) as exc_info:
        div.scroll_into_view_if_needed(timeout=3000)
    assert "element is not visible" in exc_info.value.message
    assert "retrying scroll into view action" in exc_info.value.message


def test_fill_input(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/textarea.html")
    handle = page.query_selector("input")
    assert handle
    handle.fill("some value")
    assert page.evaluate("result") == "some value"


def test_fill_input_when_Node_is_removed(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/textarea.html")
    page.evaluate('delete window["Node"]')
    handle = page.query_selector("input")
    assert handle
    handle.fill("some value")
    assert page.evaluate("result") == "some value"


def test_select_textarea(
    page: Page, server: Server, is_firefox: bool, is_webkit: bool
) -> None:
    page.goto(server.PREFIX + "/input/textarea.html")
    textarea = page.query_selector("textarea")
    assert textarea
    textarea.evaluate('textarea => textarea.value = "some value"')
    textarea.select_text()
    if is_firefox or is_webkit:
        assert textarea.evaluate("el => el.selectionStart") == 0
        assert textarea.evaluate("el => el.selectionEnd") == 10
    else:
        assert page.evaluate("() => window.getSelection().toString()") == "some value"


def test_select_input(
    page: Page, server: Server, is_firefox: bool, is_webkit: bool
) -> None:
    page.goto(server.PREFIX + "/input/textarea.html")
    input = page.query_selector("input")
    assert input
    input.evaluate('input => input.value = "some value"')
    input.select_text()
    if is_firefox or is_webkit:
        assert input.evaluate("el => el.selectionStart") == 0
        assert input.evaluate("el => el.selectionEnd") == 10
    else:
        assert page.evaluate("() => window.getSelection().toString()") == "some value"


def test_select_text_select_plain_div(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/textarea.html")
    div = page.query_selector("div.plain")
    assert div
    div.select_text()
    assert page.evaluate("() => window.getSelection().toString()") == "Plain div"


def test_select_text_timeout_waiting_for_invisible_element(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/input/textarea.html")
    textarea = page.query_selector("textarea")
    assert textarea
    textarea.evaluate('e => e.style.display = "none"')
    with pytest.raises(Error) as exc_info:
        textarea.select_text(timeout=3000)
    assert "element is not visible" in exc_info.value.message


def test_a_nice_preview(page: Page, server: Server) -> None:
    page.goto(f"{server.PREFIX}/dom.html")
    outer = page.query_selector("#outer")
    inner = page.query_selector("#inner")
    assert inner
    check = page.query_selector("#check")
    text = inner.evaluate_handle("e => e.firstChild")
    page.evaluate("1")  # Give them a chance to calculate the preview.
    assert str(outer) == 'JSHandle@<div id="outer" name="value">…</div>'
    assert str(inner) == 'JSHandle@<div id="inner">Text,↵more text</div>'
    assert str(text) == "JSHandle@#text=Text,↵more text"
    assert (
        str(check) == 'JSHandle@<input checked id="check" foo="bar"" type="checkbox"/>'
    )


def test_get_attribute(page: Page, server: Server) -> None:
    page.goto(f"{server.PREFIX}/dom.html")
    handle = page.query_selector("#outer")
    assert handle
    assert handle.get_attribute("name") == "value"
    assert page.get_attribute("#outer", "name") == "value"


def test_inner_html(page: Page, server: Server) -> None:
    page.goto(f"{server.PREFIX}/dom.html")
    handle = page.query_selector("#outer")
    assert handle
    assert handle.inner_html() == '<div id="inner">Text,\nmore text</div>'
    assert page.inner_html("#outer") == '<div id="inner">Text,\nmore text</div>'


def test_inner_text(page: Page, server: Server) -> None:
    page.goto(f"{server.PREFIX}/dom.html")
    handle = page.query_selector("#inner")
    assert handle
    assert handle.inner_text() == "Text, more text"
    assert page.inner_text("#inner") == "Text, more text"


def test_inner_text_should_throw(page: Page) -> None:
    page.set_content("<svg>text</svg>")
    with pytest.raises(Error) as exc_info1:
        page.inner_text("svg")
    assert " Node is not an HTMLElement" in exc_info1.value.message

    handle = page.query_selector("svg")
    assert handle
    with pytest.raises(Error) as exc_info2:
        handle.inner_text()
    assert " Node is not an HTMLElement" in exc_info2.value.message


def test_text_content(page: Page, server: Server) -> None:
    page.goto(f"{server.PREFIX}/dom.html")
    handle = page.query_selector("#inner")
    assert handle
    assert handle.text_content() == "Text,\nmore text"
    assert page.text_content("#inner") == "Text,\nmore text"


def test_check_the_box(page: Page) -> None:
    page.set_content('<input id="checkbox" type="checkbox"></input>')
    input = page.query_selector("input")
    assert input
    input.check()
    assert page.evaluate("checkbox.checked")


def test_uncheck_the_box(page: Page) -> None:
    page.set_content('<input id="checkbox" type="checkbox" checked></input>')
    input = page.query_selector("input")
    assert input
    input.uncheck()
    assert page.evaluate("checkbox.checked") is False


def test_select_single_option(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/select.html")
    select = page.query_selector("select")
    assert select
    select.select_option(value="blue")
    assert page.evaluate("result.onInput") == ["blue"]
    assert page.evaluate("result.onChange") == ["blue"]


def test_focus_a_button(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/button.html")
    button = page.query_selector("button")
    assert button
    assert button.evaluate("button => document.activeElement === button") is False
    button.focus()
    assert button.evaluate("button => document.activeElement === button")


def test_is_visible_and_is_hidden_should_work(page: Page) -> None:
    page.set_content("<div>Hi</div><span></span>")
    div = page.query_selector("div")
    assert div
    assert div.is_visible()
    assert div.is_hidden() is False
    assert page.is_visible("div")
    assert page.is_hidden("div") is False
    span = page.query_selector("span")
    assert span
    assert span.is_visible() is False
    assert span.is_hidden()
    assert page.is_visible("span") is False
    assert page.is_hidden("span")


def test_is_enabled_and_is_disabled_should_work(page: Page) -> None:
    page.set_content(
        """
        <button disabled>button1</button>
        <button>button2</button>
        <div>div</div>
    """
    )
    div = page.query_selector("div")
    assert div
    assert div.is_enabled()
    assert div.is_disabled() is False
    assert page.is_enabled("div")
    assert page.is_disabled("div") is False
    button1 = page.query_selector(":text('button1')")
    assert button1
    assert button1.is_enabled() is False
    assert button1.is_disabled()
    assert page.is_enabled(":text('button1')") is False
    assert page.is_disabled(":text('button1')")
    button2 = page.query_selector(":text('button2')")
    assert button2
    assert button2.is_enabled()
    assert button2.is_disabled() is False
    assert page.is_enabled(":text('button2')")
    assert page.is_disabled(":text('button2')") is False


def test_is_editable_should_work(page: Page) -> None:
    page.set_content("<input id=input1 disabled><textarea></textarea><input id=input2>")
    page.eval_on_selector("textarea", "t => t.readOnly = true")
    input1 = page.query_selector("#input1")
    assert input1
    assert input1.is_editable() is False
    assert page.is_editable("#input1") is False
    input2 = page.query_selector("#input2")
    assert input2
    assert input2.is_editable()
    assert page.is_editable("#input2")
    textarea = page.query_selector("textarea")
    assert textarea
    assert textarea.is_editable() is False
    assert page.is_editable("textarea") is False


def test_is_checked_should_work(page: Page) -> None:
    page.set_content('<input type="checkbox" checked><div>Not a checkbox</div>')
    handle = page.query_selector("input")
    assert handle
    assert handle.is_checked()
    assert page.is_checked("input")
    handle.evaluate("input => input.checked = false")
    assert handle.is_checked() is False
    assert page.is_checked("input") is False
    with pytest.raises(Error) as exc_info:
        page.is_checked("div")
    assert "Not a checkbox or radio button" in exc_info.value.message


def test_input_value(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/textarea.html")
    element = page.query_selector("input")
    assert element
    element.fill("my-text-content")
    assert element.input_value() == "my-text-content"

    element.fill("")
    assert element.input_value() == ""


def test_set_checked(page: Page) -> None:
    page.set_content("`<input id='checkbox' type='checkbox'></input>`")
    input = page.query_selector("input")
    assert input
    input.set_checked(True)
    assert page.evaluate("checkbox.checked")
    input.set_checked(False)
    assert page.evaluate("checkbox.checked") is False


def test_should_allow_disposing_twice(page: Page) -> None:
    page.set_content("<section>39</section>")
    element = page.query_selector("section")
    assert element
    element.dispose()
    element.dispose()
