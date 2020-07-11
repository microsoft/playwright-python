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
from playwright.helper import Error


async def test_bounding_box(page, server):
    await page.setViewportSize(width=500, height=500)
    await page.goto(server.PREFIX + "/grid.html")
    element_handle = await page.querySelector(".box:nth-of-type(13)")
    box = await element_handle.boundingBox()
    assert box == {"x": 100, "y": 50, "width": 50, "height": 50}


async def test_bounding_box_handle_nested_frames(page, server):
    await page.setViewportSize(width=500, height=500)
    await page.goto(server.PREFIX + "/frames/nested-frames.html")
    nested_frame = page.frame(name="dos")
    element_handle = await nested_frame.querySelector("div")
    box = await element_handle.boundingBox()
    assert box == {"x": 24, "y": 224, "width": 268, "height": 18}


async def test_bounding_box_return_null_for_invisible_elements(page, server):
    await page.setContent('<div style="display:none">hi</div>')
    element = await page.querySelector("div")
    assert await element.boundingBox() is None


async def test_bounding_box_force_a_layout(page, server):
    await page.setViewportSize(width=500, height=500)
    await page.setContent('<div style="width: 100px; height: 100px">hello</div>')
    element_handle = await page.querySelector("div")
    await page.evaluate('element => element.style.height = "200px"', element_handle)
    box = await element_handle.boundingBox()
    assert box == {"x": 8, "y": 8, "width": 100, "height": 200}


async def test_bounding_box_with_SVG_nodes(page, server):
    await page.setContent(
        """<svg xmlns="http://www.w3.org/2000/svg" width="500" height="500">
             <rect id="theRect" x="30" y="50" width="200" height="300"></rect>
           </svg>"""
    )
    element = await page.querySelector("#therect")
    pwBounding_box = await element.boundingBox()
    web_bounding_box = await page.evaluate(
        """e => {
            rect = e.getBoundingClientRect()
            return {x: rect.x, y: rect.y, width: rect.width, height: rect.height}
        }""",
        element,
    )
    assert pwBounding_box == web_bounding_box


async def test_bounding_box_with_page_scale(browser, server):
    context = await browser.newContext(
        viewport={"width": 400, "height": 400, "isMobile": True}
    )
    page = await context.newPage()
    await page.goto(server.PREFIX + "/input/button.html")
    button = await page.querySelector("button")
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

    box = await button.boundingBox()
    assert round(box["x"] * 100) == 17 * 100
    assert round(box["y"] * 100) == 23 * 100
    assert round(box["width"] * 100) == 200 * 100
    assert round(box["height"] * 100) == 20 * 100
    await context.close()


async def test_bounding_box_when_inline_box_child_is_outside_of_viewport(page, server):
    await page.setContent(
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
    handle = await page.querySelector("span")
    box = await handle.boundingBox()
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
    element_handle = await page.querySelector("#frame1")
    frame = await element_handle.contentFrame()
    assert frame == page.frames[1]


async def test_content_frame_for_non_iframes(page, server, utils):
    await page.goto(server.EMPTY_PAGE)
    await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    frame = page.frames[1]
    element_handle = await frame.evaluateHandle("document.body")
    assert await element_handle.contentFrame() is None


async def test_content_frame_for_document_element(page, server, utils):
    await page.goto(server.EMPTY_PAGE)
    await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    frame = page.frames[1]
    element_handle = await frame.evaluateHandle("document.documentElement")
    assert await element_handle.contentFrame() is None


async def test_owner_frame(page, server, utils):
    await page.goto(server.EMPTY_PAGE)
    await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    frame = page.frames[1]
    element_handle = await frame.evaluateHandle("document.body")
    assert await element_handle.ownerFrame() == frame


async def test_owner_frame_for_cross_process_iframes(page, server, utils):
    await page.goto(server.EMPTY_PAGE)
    await utils.attach_frame(
        page, "frame1", server.CROSS_PROCESS_PREFIX + "/empty.html"
    )
    frame = page.frames[1]
    element_handle = await frame.evaluateHandle("document.body")
    assert await element_handle.ownerFrame() == frame


async def test_owner_frame_for_document(page, server, utils):
    await page.goto(server.EMPTY_PAGE)
    await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    frame = page.frames[1]
    element_handle = await frame.evaluateHandle("document")
    assert await element_handle.ownerFrame() == frame


async def test_owner_frame_for_iframe_elements(page, server, utils):
    await page.goto(server.EMPTY_PAGE)
    await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    frame = page.mainFrame
    element_handle = await frame.evaluateHandle('document.querySelector("#frame1")')
    assert await element_handle.ownerFrame() == frame


async def test_owner_frame_for_cross_frame_evaluations(page, server, utils):
    await page.goto(server.EMPTY_PAGE)
    await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    frame = page.mainFrame
    element_handle = await frame.evaluateHandle(
        'document.querySelector("#frame1").contentWindow.document.body'
    )
    assert await element_handle.ownerFrame() == frame.childFrames[0]


async def test_owner_frame_for_detached_elements(page, server):
    await page.goto(server.EMPTY_PAGE)
    div_handle = await page.evaluateHandle(
        """() => {
            div = document.createElement('div');
            document.body.appendChild(div);
            return div;
        }"""
    )

    assert await div_handle.ownerFrame() == page.mainFrame
    await page.evaluate(
        """() => {
            div = document.querySelector('div')
            document.body.removeChild(div)
        }"""
    )
    assert await div_handle.ownerFrame() == page.mainFrame


async def test_owner_frame_for_adopted_elements(page, server):
    await page.goto(server.EMPTY_PAGE)
    [popup, _] = await asyncio.gather(
        page.waitForEvent("popup"),
        page.evaluate("url => window.__popup = window.open(url)", server.EMPTY_PAGE),
    )
    div_handle = await page.evaluateHandle(
        """() => {
            div = document.createElement('div');
            document.body.appendChild(div);
            return div;
        }"""
    )
    assert await div_handle.ownerFrame() == page.mainFrame
    await popup.waitForLoadState("domcontentloaded")
    await page.evaluate(
        """() => {
            div = document.querySelector('div');
            window.__popup.document.body.appendChild(div);
        }"""
    )
    assert await div_handle.ownerFrame() == popup.mainFrame


async def test_click(page, server):
    await page.goto(server.PREFIX + "/input/button.html")
    button = await page.querySelector("button")
    await button.click()
    assert await page.evaluate("result") == "Clicked"


async def test_click_with_node_removed(page, server):
    await page.goto(server.PREFIX + "/input/button.html")
    await page.evaluate('delete window["Node"]')
    button = await page.querySelector("button")
    await button.click()
    assert await page.evaluate("result") == "Clicked"


async def test_click_for_shadow_dom_v1(page, server):
    await page.goto(server.PREFIX + "/shadow.html")
    button_handle = await page.evaluateHandle("button")
    await button_handle.click()
    assert await page.evaluate("clicked")


async def test_click_for_TextNodes(page, server):
    await page.goto(server.PREFIX + "/input/button.html")
    buttonTextNode = await page.evaluateHandle(
        'document.querySelector("button").firstChild'
    )
    await buttonTextNode.click()
    assert await page.evaluate("result") == "Clicked"


async def test_click_throw_for_detached_nodes(page, server):
    await page.goto(server.PREFIX + "/input/button.html")
    button = await page.querySelector("button")
    await page.evaluate("button => button.remove()", button)
    error = None
    try:
        await button.click()
    except Error as e:
        error = e
    assert "Element is not attached to the DOM" in error.message


async def test_click_throw_for_hidden_nodes_with_force(page, server):
    await page.goto(server.PREFIX + "/input/button.html")
    button = await page.querySelector("button")
    await page.evaluate('button => button.style.display = "none"', button)
    try:
        await button.click(force=True)
    except Error as e:
        error = e
    assert "Element is not visible" in error.message


async def test_click_throw_for_recursively_hidden_nodes_with_force(page, server):
    await page.goto(server.PREFIX + "/input/button.html")
    button = await page.querySelector("button")
    await page.evaluate('button => button.parentElement.style.display = "none"', button)
    try:
        await button.click(force=True)
    except Error as e:
        error = e
    assert "Element is not visible" in error.message


async def test_click_throw_for__br__elements_with_force(page, server):
    await page.setContent("hello<br>goodbye")
    br = await page.querySelector("br")
    try:
        await br.click(force=True)
    except Error as e:
        error = e
    assert "Element is outside of the viewport" in error.message


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
    button = await page.querySelector("button")
    await button.dblclick()
    assert await page.evaluate("double")
    assert await page.evaluate("result") == "Clicked"


async def test_hover(page, server):
    await page.goto(server.PREFIX + "/input/scrollable.html")
    button = await page.querySelector("#button-6")
    await button.hover()
    assert (
        await page.evaluate('document.querySelector("button:hover").id') == "button-6"
    )


async def test_hover_when_node_is_removed(page, server):
    await page.goto(server.PREFIX + "/input/scrollable.html")
    await page.evaluate('delete window["Node"]')
    button = await page.querySelector("#button-6")
    await button.hover()
    assert (
        await page.evaluate('document.querySelector("button:hover").id') == "button-6"
    )


async def test_scroll(page, server):
    await page.goto(server.PREFIX + "/offscreenbuttons.html")
    for i in range(11):
        button = await page.querySelector(f"#btn{i}")
        before = await button.evaluate(
            """button => {
                return button.getBoundingClientRect().right - window.innerWidth
            }"""
        )

        assert before == 10 * i
        await button.scrollIntoViewIfNeeded()
        after = await button.evaluate(
            """button => {
                return button.getBoundingClientRect().right - window.innerWidth
            }"""
        )

        assert after <= 0
        await page.evaluate("() => window.scrollTo(0, 0)")


async def test_scroll_should_throw_for_detached_element(page, server):
    await page.setContent("<div>Hello</div>")
    div = await page.querySelector("div")
    await div.evaluate("div => div.remove()")
    try:
        await div.scrollIntoViewIfNeeded()
    except Error as e:
        error = e
    assert "Element is not attached to the DOM" in error.message


async def waiting_helper(page, after):
    div = await page.querySelector("div")
    done = list()

    async def scroll():
        done.append(False)
        await div.scrollIntoViewIfNeeded()
        done.append(True)

    promise = asyncio.ensure_future(scroll())
    await page.evaluate("() => new Promise(f => setTimeout(f, 1000))")
    assert done == [False]
    await div.evaluate(after)
    await promise
    assert done == [False, True]


async def test_should_wait_for_display_none_to_become_visible(page):
    await page.setContent('<div style="display:none">Hello</div>')
    await waiting_helper(page, 'div => div.style.display = "block"')


async def test_should_wait_for_display_contents_to_become_visible(page):
    await page.setContent('<div style="display:contents">Hello</div>')
    await waiting_helper(page, 'div => div.style.display = "block"')


async def test_should_wait_for_visibility_hidden_to_become_visible(page):
    await page.setContent('<div style="visibility:hidden">Hello</div>')
    await waiting_helper(page, 'div => div.style.visibility = "visible"')


async def test_should_wait_for_zero_sized_element_to_become_visible(page):
    await page.setContent('<div style="height:0">Hello</div>')
    await waiting_helper(page, 'div => div.style.height = "100px"')


async def test_should_wait_for_nested_display_none_to_become_visible(page):
    await page.setContent('<span style="display:none"><div>Hello</div></span>')
    await waiting_helper(page, 'div => div.parentElement.style.display = "block"')


async def test_should_timeout_waiting_for_visible(page):
    await page.setContent('<div style="display:none">Hello</div>')
    div = await page.querySelector("div")
    try:
        error = await div.scrollIntoViewIfNeeded(timeout=3000)
    except Error as e:
        error = e
    assert "element is not visible" in error.message


async def test_fill_input(page, server):
    await page.goto(server.PREFIX + "/input/textarea.html")
    handle = await page.querySelector("input")
    await handle.fill("some value")
    assert await page.evaluate("result") == "some value"


async def test_fill_input_when_Node_is_removed(page, server):
    await page.goto(server.PREFIX + "/input/textarea.html")
    await page.evaluate('delete window["Node"]')
    handle = await page.querySelector("input")
    await handle.fill("some value")
    assert await page.evaluate("result") == "some value"


async def test_select_textarea(page, server, is_firefox):
    await page.goto(server.PREFIX + "/input/textarea.html")
    textarea = await page.querySelector("textarea")
    await textarea.evaluate('textarea => textarea.value = "some value"')
    await textarea.selectText()
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
    input = await page.querySelector("input")
    await input.evaluate('input => input.value = "some value"')
    await input.selectText()
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
    div = await page.querySelector("div.plain")
    await div.selectText()
    assert await page.evaluate("() => window.getSelection().toString()") == "Plain div"


async def test_select_text_timeout_waiting_for_invisible_element(page, server):
    await page.goto(server.PREFIX + "/input/textarea.html")
    textarea = await page.querySelector("textarea")
    await textarea.evaluate('e => e.style.display = "none"')
    try:
        await textarea.selectText(timeout=3000)
    except Error as e:
        error = e
    assert "element is not visible" in error.message


async def test_select_text_wait_for_visible(page, server):
    await page.goto(server.PREFIX + "/input/textarea.html")
    textarea = await page.querySelector("textarea")
    await textarea.evaluate('textarea => textarea.value = "some value"')
    await textarea.evaluate('e => e.style.display = "none"')
    done = list()

    async def select_text():
        done.append(False)
        await textarea.selectText(timeout=3000)
        done.append(True)

    promise = asyncio.ensure_future(select_text())
    await page.evaluate("() => new Promise(f => setTimeout(f, 1000))")
    await textarea.evaluate('e => e.style.display = "block"')
    await promise
    assert done == [False, True]


async def test_a_nice_preview(page, server):
    await page.goto(f"{server.PREFIX}/dom.html")
    outer = await page.querySelector("#outer")
    inner = await page.querySelector("#inner")
    check = await page.querySelector("#check")
    text = await inner.evaluateHandle("e => e.firstChild")
    await page.evaluate("1")  # Give them a chance to calculate the preview.
    assert str(outer) == 'JSHandle@<div id="outer" name="value">…</div>'
    assert str(inner) == 'JSHandle@<div id="inner">Text,↵more text</div>'
    assert str(text) == "JSHandle@#text=Text,↵more text"
    assert (
        str(check) == 'JSHandle@<input checked id="check" foo="bar"" type="checkbox"/>'
    )


async def test_get_attribute(page, server):
    await page.goto(f"{server.PREFIX}/dom.html")
    handle = await page.querySelector("#outer")
    assert await handle.getAttribute("name") == "value"
    assert await page.getAttribute("#outer", "name") == "value"


async def test_inner_html(page, server):
    await page.goto(f"{server.PREFIX}/dom.html")
    handle = await page.querySelector("#outer")
    assert await handle.innerHTML() == '<div id="inner">Text,\nmore text</div>'
    assert await page.innerHTML("#outer") == '<div id="inner">Text,\nmore text</div>'


async def test_inner_text(page, server):
    await page.goto(f"{server.PREFIX}/dom.html")
    handle = await page.querySelector("#inner")
    assert await handle.innerText() == "Text, more text"
    assert await page.innerText("#inner") == "Text, more text"


async def test_inner_text_should_throw(page, server):
    await page.setContent("<svg>text</svg>")
    error1 = None
    try:
        await page.innerText("svg")
    except Error as e:
        error1 = e
    assert "Not an HTMLElement" in error1.message
    handle = await page.querySelector("svg")
    error2 = None
    try:
        await handle.innerText()
    except Error as e:
        error2 = e
    assert "Not an HTMLElement" in error2.message


async def test_text_content(page, server):
    await page.goto(f"{server.PREFIX}/dom.html")
    handle = await page.querySelector("#inner")
    assert await handle.textContent() == "Text,\nmore text"
    assert await page.textContent("#inner") == "Text,\nmore text"


async def test_check_the_box(page):
    await page.setContent('<input id="checkbox" type="checkbox"></input>')
    input = await page.querySelector("input")
    await input.check()
    assert await page.evaluate("checkbox.checked")


async def test_uncheck_the_box(page):
    await page.setContent('<input id="checkbox" type="checkbox" checked></input>')
    input = await page.querySelector("input")
    await input.uncheck()
    assert await page.evaluate("checkbox.checked") is False


async def test_select_single_option(page, server):
    await page.goto(server.PREFIX + "/input/select.html")
    select = await page.querySelector("select")
    await select.selectOption("blue")
    assert await page.evaluate("result.onInput") == ["blue"]
    assert await page.evaluate("result.onChange") == ["blue"]


async def test_focus_a_button(page, server):
    await page.goto(server.PREFIX + "/input/button.html")
    button = await page.querySelector("button")
    assert await button.evaluate("button => document.activeElement === button") is False
    await button.focus()
    assert await button.evaluate("button => document.activeElement === button")
