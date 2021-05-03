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

from playwright.async_api import Error, TimeoutError


async def give_it_a_chance_to_click(page):
    for _ in range(5):
        await page.evaluate(
            "() => new Promise(f => requestAnimationFrame(() => requestAnimationFrame(f)))"
        )


async def test_click_the_button(page, server):
    await page.goto(server.PREFIX + "/input/button.html")
    await page.click("button")
    assert await page.evaluate("result") == "Clicked"


async def test_click_svg(page, server):
    await page.set_content(
        """
        <svg height="100" width="100">
            <circle onclick="javascript:window.__CLICKED=42" cx="50" cy="50" r="40" stroke="black" stroke-width="3" fill="red" />
        </svg>
        """
    )
    await page.click("circle")
    assert await page.evaluate("window.__CLICKED") == 42


async def test_click_the_button_if_window_node_is_removed(page, server):
    await page.goto(server.PREFIX + "/input/button.html")
    await page.evaluate("() => delete window.Node")
    await page.click("button")
    assert await page.evaluate("() => result") == "Clicked"


async def test_click_on_a_span_with_an_inline_element_inside(page, server):
    await page.set_content(
        """
        <style>
        span::before {
            content: 'q'
        }
        </style>
        <span onclick='javascript:window.CLICKED=42'></span>
        """
    )
    await page.click("span")
    assert await page.evaluate("window.CLICKED") == 42


async def test_click_not_throw_when_page_closes(browser, server):
    context = await browser.new_context()
    page = await context.new_page()
    try:
        await asyncio.gather(
            page.close(),
            page.mouse.click(1, 2),
        )
    except Error:
        pass
    await context.close()


async def test_click_the_button_after_navigation(page, server):
    await page.goto(server.PREFIX + "/input/button.html")
    await page.click("button")
    await page.goto(server.PREFIX + "/input/button.html")
    await page.click("button")
    assert await page.evaluate("() => result") == "Clicked"


async def test_click_the_button_after_a_cross_origin_navigation_(page, server):
    await page.goto(server.PREFIX + "/input/button.html")
    await page.click("button")
    await page.goto(server.CROSS_PROCESS_PREFIX + "/input/button.html")
    await page.click("button")
    assert await page.evaluate("() => result") == "Clicked"


async def test_click_with_disabled_javascript(browser, server):
    context = await browser.new_context(java_script_enabled=False)
    page = await context.new_page()
    await page.goto(server.PREFIX + "/wrappedlink.html")
    async with page.expect_navigation():
        await page.click("a")
    assert page.url == server.PREFIX + "/wrappedlink.html#clicked"
    await context.close()


async def test_click_when_one_of_inline_box_children_is_outside_of_viewport(
    page, server
):
    await page.set_content(
        """
        <style>
        i {
            position: absolute
            top: -1000px
        }
        </style>
        <span onclick='javascript:window.CLICKED = 42;'><i>woof</i><b>doggo</b></span>
        """
    )
    await page.click("span")
    assert await page.evaluate("() => window.CLICKED") == 42


async def test_select_the_text_by_triple_clicking(page, server):
    await page.goto(server.PREFIX + "/input/textarea.html")
    text = "This is the text that we are going to try to select. Let's see how it goes."
    await page.fill("textarea", text)
    await page.click("textarea", click_count=3)
    assert (
        await page.evaluate(
            """() => {
                textarea = document.querySelector('textarea')
                return textarea.value.substring(textarea.selectionStart, textarea.selectionEnd)
            }"""
        )
        == text
    )


async def test_click_offscreen_buttons(page, server):
    await page.goto(server.PREFIX + "/offscreenbuttons.html")
    messages = []
    page.on("console", lambda msg: messages.append(msg.text))
    for i in range(11):
        # We might've scrolled to click a button - reset to (0, 0).
        await page.evaluate("window.scrollTo(0, 0)")
        await page.click(f"#btn{i}")
    assert messages == [
        "button #0 clicked",
        "button #1 clicked",
        "button #2 clicked",
        "button #3 clicked",
        "button #4 clicked",
        "button #5 clicked",
        "button #6 clicked",
        "button #7 clicked",
        "button #8 clicked",
        "button #9 clicked",
        "button #10 clicked",
    ]


async def test_waitFor_visible_when_already_visible(page, server):
    await page.goto(server.PREFIX + "/input/button.html")
    await page.click("button")
    assert await page.evaluate("result") == "Clicked"


async def test_wait_with_force(page, server):
    error = None
    await page.goto(server.PREFIX + "/input/button.html")
    await page.eval_on_selector("button", "b => b.style.display = 'none'")
    try:
        await page.click("button", force=True)
    except Error as e:
        error = e
    assert "Element is not visible" in error.message
    assert await page.evaluate("result") == "Was not clicked"


async def test_wait_for_display_none_to_be_gone(page, server):
    done = list()
    await page.goto(server.PREFIX + "/input/button.html")
    await page.eval_on_selector("button", "b => b.style.display = 'none'")

    async def click():
        await page.click("button", timeout=0)
        done.append(True)

    clicked = asyncio.create_task(click())
    await give_it_a_chance_to_click(page)
    assert await page.evaluate("result") == "Was not clicked"
    assert done == []
    await page.eval_on_selector("button", "b => b.style.display = 'block'")
    await clicked
    assert done == [True]
    assert await page.evaluate("result") == "Clicked"


async def test_wait_for_visibility_hidden_to_be_gone(page, server):
    done = list()
    await page.goto(server.PREFIX + "/input/button.html")
    await page.eval_on_selector("button", "b => b.style.visibility = 'hidden'")

    async def click():
        await page.click("button", timeout=0)
        done.append(True)

    clicked = asyncio.create_task(click())
    await give_it_a_chance_to_click(page)
    assert await page.evaluate("result") == "Was not clicked"
    assert done == []
    await page.eval_on_selector("button", "b => b.style.visibility = 'visible'")
    await clicked
    assert done == [True]
    assert await page.evaluate("result") == "Clicked"


async def test_timeout_waiting_for_display_none_to_be_gone(page, server):
    await page.goto(server.PREFIX + "/input/button.html")
    await page.eval_on_selector("button", "b => b.style.display = 'none'")
    try:
        await page.click("button", timeout=5000)
    except Error as e:
        error = e
    assert "Timeout 5000ms exceeded" in error.message
    assert "waiting for element to be visible, enabled and stable" in error.message
    assert "element is not visible - waiting" in error.message


async def test_timeout_waiting_for_visbility_hidden_to_be_gone(page, server):
    await page.goto(server.PREFIX + "/input/button.html")
    await page.eval_on_selector("button", "b => b.style.visibility = 'hidden'")
    try:
        await page.click("button", timeout=5000)
    except Error as e:
        error = e
    assert "Timeout 5000ms exceeded" in error.message
    assert "waiting for element to be visible, enabled and stable" in error.message
    assert "element is not visible - waiting" in error.message


async def test_waitFor_visible_when_parent_is_hidden(page, server):
    done = list()
    await page.goto(server.PREFIX + "/input/button.html")
    await page.eval_on_selector("button", "b => b.parentElement.style.display = 'none'")

    async def click():
        await page.click("button", timeout=0)
        done.append(True)

    clicked = asyncio.create_task(click())
    await give_it_a_chance_to_click(page)
    assert done == []
    await page.eval_on_selector(
        "button", "b => b.parentElement.style.display = 'block'"
    )
    await clicked
    assert done == [True]
    assert await page.evaluate("result") == "Clicked"


async def test_click_wrapped_links(page, server):
    await page.goto(server.PREFIX + "/wrappedlink.html")
    await page.click("a")
    assert await page.evaluate("window.__clicked")


async def test_click_on_checkbox_input_and_toggle(page, server):
    await page.goto(server.PREFIX + "/input/checkbox.html")
    assert await page.evaluate("() => result.check") is None
    await page.click("input#agree")
    assert await page.evaluate("result.check")
    assert await page.evaluate("result.events") == [
        "mouseover",
        "mouseenter",
        "mousemove",
        "mousedown",
        "mouseup",
        "click",
        "input",
        "change",
    ]
    await page.click("input#agree")
    assert await page.evaluate("result.check") is False


async def test_click_on_checkbox_label_and_toggle(page, server):
    await page.goto(server.PREFIX + "/input/checkbox.html")
    assert await page.evaluate("result.check") is None
    await page.click('label[for="agree"]')
    assert await page.evaluate("result.check")
    assert await page.evaluate("result.events") == [
        "click",
        "input",
        "change",
    ]
    await page.click('label[for="agree"]')
    assert await page.evaluate("result.check") is False


async def test_not_hang_with_touch_enabled_viewports(playwright, server, browser):
    iphone_6 = playwright.devices["iPhone 6"]
    context = await browser.new_context(
        viewport=iphone_6["viewport"], has_touch=iphone_6["has_touch"]
    )
    page = await context.new_page()
    await page.mouse.down()
    await page.mouse.move(100, 10)
    await page.mouse.up()
    await context.close()


async def test_scroll_and_click_the_button(page, server):
    await page.goto(server.PREFIX + "/input/scrollable.html")
    await page.click("#button-5")
    assert (
        await page.evaluate("document.querySelector('#button-5').textContent")
        == "clicked"
    )
    await page.click("#button-80")
    assert (
        await page.evaluate("document.querySelector('#button-80').textContent")
        == "clicked"
    )


async def test_double_click_the_button(page, server):
    await page.goto(server.PREFIX + "/input/button.html")
    await page.evaluate(
        """() => {
            window.double = false;
            button = document.querySelector('button');
            button.addEventListener('dblclick', event => window.double = true);
        }"""
    )

    await page.dblclick("button")
    assert await page.evaluate("double")
    assert await page.evaluate("result") == "Clicked"


async def test_click_a_partially_obscured_button(page, server):
    await page.goto(server.PREFIX + "/input/button.html")
    await page.evaluate(
        """() => {
            button = document.querySelector('button');
            button.textContent = 'Some really long text that will go offscreen';
            button.style.position = 'absolute';
            button.style.left = '368px';
        }"""
    )

    await page.click("button")
    assert await page.evaluate("() => window.result") == "Clicked"


async def test_click_a_rotated_button(page, server):
    await page.goto(server.PREFIX + "/input/rotatedButton.html")
    await page.click("button")
    assert await page.evaluate("result") == "Clicked"


async def test_fire_contextmenu_event_on_right_click(page, server):
    await page.goto(server.PREFIX + "/input/scrollable.html")
    await page.click("#button-8", button="right")
    assert (
        await page.evaluate("document.querySelector('#button-8').textContent")
        == "context menu"
    )


async def test_click_links_which_cause_navigation(page, server):
    await page.set_content(f'<a href="{server.EMPTY_PAGE}">empty.html</a>')
    # This await should not hang.
    await page.click("a")


async def test_click_the_button_inside_an_iframe(page, server, utils):
    await page.goto(server.EMPTY_PAGE)
    await page.set_content('<div style="width:100px;height:100px">spacer</div>')
    await utils.attach_frame(page, "button-test", server.PREFIX + "/input/button.html")
    frame = page.frames[1]
    button = await frame.query_selector("button")
    await button.click()
    assert await frame.evaluate("window.result") == "Clicked"


async def test_click_the_button_with_device_scale_factor_set(browser, server, utils):
    context = await browser.new_context(
        viewport={"width": 400, "height": 400}, device_scale_factor=5
    )
    page = await context.new_page()
    assert await page.evaluate("window.devicePixelRatio") == 5
    await page.set_content('<div style="width:100px;height:100px">spacer</div>')
    await utils.attach_frame(page, "button-test", server.PREFIX + "/input/button.html")
    frame = page.frames[1]
    button = await frame.query_selector("button")
    await button.click()
    assert await frame.evaluate("window.result") == "Clicked"
    await context.close()


async def test_click_the_button_with_px_border_with_offset(page, server, is_webkit):
    await page.goto(server.PREFIX + "/input/button.html")
    await page.eval_on_selector("button", "button => button.style.borderWidth = '8px'")
    await page.click("button", position={"x": 20, "y": 10})
    assert await page.evaluate("result") == "Clicked"
    # Safari reports border-relative offsetX/offsetY.
    assert await page.evaluate("offsetX") == 20 + 8 if is_webkit else 20
    assert await page.evaluate("offsetY") == 10 + 8 if is_webkit else 10


async def test_click_the_button_with_em_border_with_offset(page, server, is_webkit):
    await page.goto(server.PREFIX + "/input/button.html")
    await page.eval_on_selector("button", "button => button.style.borderWidth = '2em'")
    await page.eval_on_selector("button", "button => button.style.fontSize = '12px'")
    await page.click("button", position={"x": 20, "y": 10})
    assert await page.evaluate("result") == "Clicked"
    # Safari reports border-relative offsetX/offsetY.
    assert await page.evaluate("offsetX") == 12 * 2 + 20 if is_webkit else 20
    assert await page.evaluate("offsetY") == 12 * 2 + 10 if is_webkit else 10


async def test_click_a_very_large_button_with_offset(page, server, is_webkit):
    await page.goto(server.PREFIX + "/input/button.html")
    await page.eval_on_selector("button", "button => button.style.borderWidth = '8px'")
    await page.eval_on_selector(
        "button", "button => button.style.height = button.style.width = '2000px'"
    )
    await page.click("button", position={"x": 1900, "y": 1910})
    assert await page.evaluate("() => window.result") == "Clicked"
    # Safari reports border-relative offsetX/offsetY.
    assert await page.evaluate("() => offsetX") == 1900 + 8 if is_webkit else 1900
    assert await page.evaluate("() => offsetY") == 1910 + 8 if is_webkit else 1910


async def test_click_a_button_in_scrolling_container_with_offset(
    page, server, is_webkit
):
    await page.goto(server.PREFIX + "/input/button.html")
    await page.eval_on_selector(
        "button",
        """button => {
            container = document.createElement('div');
            container.style.overflow = 'auto';
            container.style.width = '200px';
            container.style.height = '200px';
            button.parentElement.insertBefore(container, button);
            container.appendChild(button);
            button.style.height = '2000px';
            button.style.width = '2000px';
            button.style.borderWidth = '8px';
        }""",
    )

    await page.click("button", position={"x": 1900, "y": 1910})
    assert await page.evaluate("window.result") == "Clicked"
    # Safari reports border-relative offsetX/offsetY.
    assert await page.evaluate("offsetX") == 1900 + 8 if is_webkit else 1900
    assert await page.evaluate("offsetY") == 1910 + 8 if is_webkit else 1910


@pytest.mark.skip_browser("firefox")
async def test_click_the_button_with_offset_with_page_scale(
    browser, server, is_chromium, is_webkit
):
    context = await browser.new_context(
        viewport={"width": 400, "height": 400}, is_mobile=True
    )
    page = await context.new_page()
    await page.goto(server.PREFIX + "/input/button.html")
    await page.eval_on_selector(
        "button",
        """button => {
      button.style.borderWidth = '8px'
      document.body.style.margin = '0'
    }""",
    )

    await page.click("button", position={"x": 20, "y": 10})
    assert await page.evaluate("result") == "Clicked"
    expected = {"x": 28, "y": 18}
    if is_webkit:
        # WebKit rounds up during css -> dip -> css conversion.
        expected = {"x": 29, "y": 19}
    elif is_chromium:
        # Chromium rounds down during css -> dip -> css conversion.
        expected = {"x": 27, "y": 18}
    assert await page.evaluate("pageX") == expected["x"]
    assert await page.evaluate("pageY") == expected["y"]
    await context.close()


async def test_wait_for_stable_position(page, server):
    await page.goto(server.PREFIX + "/input/button.html")
    await page.eval_on_selector(
        "button",
        """button => {
            button.style.transition = 'margin 500ms linear 0s';
            button.style.marginLeft = '200px';
            button.style.borderWidth = '0';
            button.style.width = '200px';
            button.style.height = '20px';
            // Set display to "block" - otherwise Firefox layouts with non-even
            // values on Linux.
            button.style.display = 'block';
            document.body.style.margin = '0';
        }""",
    )

    await page.click("button")
    assert await page.evaluate("window.result") == "Clicked"
    assert await page.evaluate("pageX") == 300
    assert await page.evaluate("pageY") == 10


async def test_timeout_waiting_for_stable_position(page, server):
    await page.goto(server.PREFIX + "/input/button.html")
    button = await page.query_selector("button")
    await button.evaluate(
        """button => {
            button.style.transition = 'margin 5s linear 0s'
            button.style.marginLeft = '200px'
        }"""
    )

    with pytest.raises(Error) as exc_info:
        await button.click(timeout=3000)
    error = exc_info.value
    assert "Timeout 3000ms exceeded." in error.message
    assert "waiting for element to be visible, enabled and stable" in error.message
    assert "element is not stable - waiting" in error.message


async def test_wait_for_becoming_hit_target(page, server):
    await page.goto(server.PREFIX + "/input/button.html")
    await page.eval_on_selector(
        "button",
        """button => {
            button.style.borderWidth = '0';
            button.style.width = '200px';
            button.style.height = '20px';
            document.body.style.margin = '0';
            document.body.style.position = 'relative';
            flyOver = document.createElement('div');
            flyOver.className = 'flyover';
            flyOver.style.position = 'absolute';
            flyOver.style.width = '400px';
            flyOver.style.height = '20px';
            flyOver.style.left = '-200px';
            flyOver.style.top = '0';
            flyOver.style.background = 'red';
            document.body.appendChild(flyOver);
        }""",
    )

    clicked = [False]

    async def click():
        await page.click("button")
        clicked.append(True)

    click_promise = asyncio.create_task(click())
    assert clicked == [False]

    await page.eval_on_selector(".flyover", "flyOver => flyOver.style.left = '0'")
    await give_it_a_chance_to_click(page)
    assert clicked == [False]

    await page.eval_on_selector(".flyover", "flyOver => flyOver.style.left = '200px'")
    await click_promise
    assert clicked == [False, True]
    assert await page.evaluate("() => window.result") == "Clicked"


async def test_timeout_waiting_for_hit_target(page, server):
    await page.goto(server.PREFIX + "/input/button.html")
    button = await page.query_selector("button")
    await page.evaluate(
        """() => {
      document.body.style.position = 'relative'
      blocker = document.createElement('div')
      blocker.id = 'blocker';
      blocker.style.position = 'absolute'
      blocker.style.width = '400px'
      blocker.style.height = '20px'
      blocker.style.left = '0'
      blocker.style.top = '0'
      document.body.appendChild(blocker)
      }"""
    )
    error = None
    try:
        await button.click(timeout=5000)
    except TimeoutError as e:
        error = e
    assert "Timeout 5000ms exceeded." in error.message
    assert '<div id="blocker"></div> intercepts pointer events' in error.message
    assert "retrying click action" in error.message


async def test_fail_when_obscured_and_not_waiting_for_hit_target(page, server):
    await page.goto(server.PREFIX + "/input/button.html")
    button = await page.query_selector("button")
    await page.evaluate(
        """() => {
            document.body.style.position = 'relative'
            blocker = document.createElement('div')
            blocker.style.position = 'absolute'
            blocker.style.width = '400px'
            blocker.style.height = '20px'
            blocker.style.left = '0'
            blocker.style.top = '0'
            document.body.appendChild(blocker)
        }"""
    )

    await button.click(force=True)
    assert await page.evaluate("window.result") == "Was not clicked"


async def test_wait_for_button_to_be_enabled(page, server):
    await page.set_content(
        '<button onclick="javascript:window.__CLICKED=true;" disabled><span>Click target</span></button>'
    )
    done = list()

    async def click():
        await page.click("text=Click target")
        done.append(True)

    click_promise = asyncio.create_task(click())
    await give_it_a_chance_to_click(page)
    assert await page.evaluate("() => window.__CLICKED") is None
    assert done == []
    await page.evaluate("document.querySelector('button').removeAttribute('disabled')")
    await click_promise
    assert await page.evaluate("window.__CLICKED")


async def test_timeout_waiting_for_button_to_be_enabled(page, server):
    await page.set_content(
        '<button onclick="javascript:window.__CLICKED=true;" disabled><span>Click target</span></button>'
    )
    error = None
    try:
        await page.click("text=Click target", timeout=3000)
    except TimeoutError as e:
        error = e
    assert await page.evaluate("window.__CLICKED") is None
    assert "Timeout 3000ms exceeded" in error.message
    assert "element is not enabled - waiting" in error.message


async def test_wait_for_input_to_be_enabled(page, server):
    await page.set_content(
        '<input onclick="javascript:window.__CLICKED=true;" disabled>'
    )
    done = []

    async def click():
        await page.click("input")
        done.append(True)

    click_promise = asyncio.create_task(click())
    await give_it_a_chance_to_click(page)
    assert await page.evaluate("window.__CLICKED") is None
    assert done == []
    await page.evaluate("document.querySelector('input').removeAttribute('disabled')")
    await click_promise
    assert await page.evaluate("window.__CLICKED")


async def test_wait_for_select_to_be_enabled(page, server):
    await page.set_content(
        '<select onclick="javascript:window.__CLICKED=true;" disabled><option selected>Hello</option></select>'
    )
    done = []

    async def click():
        await page.click("select")
        done.append(True)

    click_promise = asyncio.create_task(click())
    await give_it_a_chance_to_click(page)
    assert await page.evaluate("window.__CLICKED") is None
    assert done == []
    await page.evaluate("document.querySelector('select').removeAttribute('disabled')")
    await click_promise
    assert await page.evaluate("window.__CLICKED")


async def test_click_disabled_div(page, server):
    await page.set_content(
        '<div onclick="javascript:window.__CLICKED=true;" disabled>Click target</div>'
    )
    await page.click("text=Click target")
    assert await page.evaluate("window.__CLICKED")


async def test_climb_dom_for_inner_label_with_pointer_events_none(page, server):
    await page.set_content(
        '<button onclick="javascript:window.__CLICKED=true;"><label style="pointer-events:none">Click target</label></button>'
    )
    await page.click("text=Click target")
    assert await page.evaluate("window.__CLICKED")


async def test_climb_up_to_role_button(page, server):
    await page.set_content(
        '<div role=button onclick="javascript:window.__CLICKED=true;"><div style="pointer-events:none"><span><div>Click target</div></span></div>'
    )
    await page.click("text=Click target")
    assert await page.evaluate("window.__CLICKED")


async def test_wait_for_BUTTON_to_be_clickable_when_it_has_pointer_events_none(
    page, server
):
    await page.set_content(
        '<button onclick="javascript:window.__CLICKED=true;" style="pointer-events:none"><span>Click target</span></button>'
    )
    done = []

    async def click():
        await page.click("text=Click target")
        done.append(True)

    click_promise = asyncio.create_task(click())
    await give_it_a_chance_to_click(page)
    assert await page.evaluate("window.__CLICKED") is None
    assert done == []
    await page.evaluate(
        "document.querySelector('button').style.removeProperty('pointer-events')"
    )
    await click_promise
    assert await page.evaluate("window.__CLICKED")


async def test_wait_for_LABEL_to_be_clickable_when_it_has_pointer_events_none(
    page, server
):
    await page.set_content(
        '<label onclick="javascript:window.__CLICKED=true;" style="pointer-events:none"><span>Click target</span></label>'
    )
    click_promise = asyncio.create_task(page.click("text=Click target"))
    #  Do a few roundtrips to the page.
    for _ in range(5):
        assert await page.evaluate("window.__CLICKED") is None
    #  remove 'pointer-events: none' css from button.
    await page.evaluate(
        "document.querySelector('label').style.removeProperty('pointer-events')"
    )
    await click_promise
    assert await page.evaluate("window.__CLICKED")


async def test_update_modifiers_correctly(page, server):
    await page.goto(server.PREFIX + "/input/button.html")
    await page.click("button", modifiers=["Shift"])
    assert await page.evaluate("shiftKey")
    await page.click("button", modifiers=[])
    assert await page.evaluate("shiftKey") is False

    await page.keyboard.down("Shift")
    await page.click("button", modifiers=[])
    assert await page.evaluate("shiftKey") is False
    await page.click("button")
    assert await page.evaluate("shiftKey")
    await page.keyboard.up("Shift")
    await page.click("button")
    assert await page.evaluate("shiftKey") is False


async def test_click_an_offscreen_element_when_scroll_behavior_is_smooth(page):
    await page.set_content(
        """
        <div style="border: 1px solid black; height: 500px; overflow: auto; width: 500px; scroll-behavior: smooth">
            <button style="margin-top: 2000px" onClick="window.clicked = true">hi</button>
        </div>
        """
    )
    await page.click("button")
    assert await page.evaluate("window.clicked")


async def test_report_nice_error_when_element_is_detached_and_force_clicked(
    page, server
):
    await page.goto(server.PREFIX + "/input/animating-button.html")
    await page.evaluate("addButton()")
    handle = await page.query_selector("button")
    await page.evaluate("stopButton(true)")
    error = None
    try:
        await handle.click(force=True)
    except Error as e:
        error = e
    assert await page.evaluate("window.clicked") is None
    assert "Element is not attached to the DOM" in error.message


async def test_fail_when_element_detaches_after_animation(page, server):
    await page.goto(server.PREFIX + "/input/animating-button.html")
    await page.evaluate("addButton()")
    handle = await page.query_selector("button")
    promise = asyncio.create_task(handle.click())
    await asyncio.sleep(0)  # execute scheduled tasks, but don't await them
    await page.evaluate("stopButton(true)")
    with pytest.raises(Error) as exc_info:
        await promise
    assert await page.evaluate("window.clicked") is None
    assert "Element is not attached to the DOM" in exc_info.value.message


async def test_retry_when_element_detaches_after_animation(page, server):
    await page.goto(server.PREFIX + "/input/animating-button.html")
    await page.evaluate("addButton()")
    clicked = []

    async def click():
        await page.click("button")
        clicked.append(True)

    promise = asyncio.create_task(click())
    await asyncio.sleep(0)  # execute scheduled tasks, but don't await them
    assert clicked == []
    assert await page.evaluate("window.clicked") is None
    await page.evaluate("stopButton(true)")
    await page.evaluate("addButton()")
    assert clicked == []
    assert await page.evaluate("window.clicked") is None
    await page.evaluate("stopButton(true)")
    await page.evaluate("addButton()")
    assert clicked == []
    assert await page.evaluate("window.clicked") is None
    await page.evaluate("stopButton(false)")
    await promise
    assert clicked == [True]
    assert await page.evaluate("window.clicked")


async def test_retry_when_element_is_animating_from_outside_the_viewport(page, server):
    await page.set_content(
        """<style>
        @keyframes move {
            from { left: -300px; }
            to { left: 0; }
        }
        button {
            position: absolute
            left: -300px
            top: 0
            bottom: 0
            width: 200px
        }
        button.animated {
            animation: 1s linear 1s move forwards
        }
        </style>
        <div style="position: relative; width: 300px; height: 300px;">
            <button onclick="window.clicked=true"></button>
        </div>
        """
    )
    handle = await page.query_selector("button")
    promise = asyncio.create_task(handle.click())
    await asyncio.sleep(0)  # execute scheduled tasks, but don't await them
    await handle.evaluate("button => button.className = 'animated'")
    await promise
    assert await page.evaluate("window.clicked")


async def test_fail_when_element_is_animating_from_outside_the_viewport_with_force(
    page, server
):
    await page.set_content(
        """<style>
        @keyframes move {
            from { left: -300px; }
            to { left: 0; }
        }
        button {
            position: absolute;
            left: -300px;
            top: 0;
            bottom: 0
            width: 200px;
        }
        button.animated {
            animation: 1s linear 1s move forwards;
        }
        </style>
        <div style="position: relative; width: 300px; height: 300px;">
            <button onclick="window.clicked=true"></button>
        </div>
        """
    )
    handle = await page.query_selector("button")
    promise = asyncio.create_task(handle.click(force=True))
    await asyncio.sleep(0)  # execute scheduled tasks, but don't await them
    await handle.evaluate("button => button.className = 'animated'")
    error = None
    try:
        await promise
    except Error as e:
        error = e
    assert await page.evaluate("window.clicked") is None
    assert "Element is outside of the viewport" in error.message


async def test_not_retarget_when_element_changes_on_hover(page, server):
    await page.goto(server.PREFIX + "/react.html")
    await page.evaluate(
        """() => {
          renderComponent(e('div', {}, [e(MyButton, { name: 'button1', renameOnHover: true }), e(MyButton, { name: 'button2' })] ));
        }"""
    )
    await page.click("text=button1")
    assert await page.evaluate("window.button1")
    assert await page.evaluate("window.button2") is None


async def test_not_retarget_when_element_is_recycled_on_hover(page, server):
    await page.goto(server.PREFIX + "/react.html")
    await page.evaluate(
        """() => {
            function shuffle() {
                renderComponent(e('div', {}, [e(MyButton, { name: 'button2' }), e(MyButton, { name: 'button1' })] ));
            }
            renderComponent(e('div', {}, [e(MyButton, { name: 'button1', onHover: shuffle }), e(MyButton, { name: 'button2' })] ));
        }"""
    )

    await page.click("text=button1")
    assert await page.evaluate("window.button1") is None
    assert await page.evaluate("window.button2")


async def test_click_the_button_when_window_inner_width_is_corrupted(page, server):
    await page.goto(server.PREFIX + "/input/button.html")
    await page.evaluate("window.innerWidth = 0")
    await page.click("button")
    assert await page.evaluate("result") == "Clicked"


async def test_timeout_when_click_opens_alert(page, server):
    await page.set_content('<div onclick="window.alert(123)">Click me</div>')
    async with page.expect_event("dialog") as dialog_info:
        with pytest.raises(Error) as exc_info:
            await page.click("div", timeout=3000)
        assert "Timeout 3000ms exceeded" in exc_info.value.message
    dialog = await dialog_info.value
    await dialog.dismiss()


async def test_check_the_box(page):
    await page.set_content('<input id="checkbox" type="checkbox"></input>')
    await page.check("input")
    assert await page.evaluate("checkbox.checked")


async def test_not_check_the_checked_box(page):
    await page.set_content('<input id="checkbox" type="checkbox" checked></input>')
    await page.check("input")
    assert await page.evaluate("checkbox.checked")


async def test_uncheck_the_box(page):
    await page.set_content('<input id="checkbox" type="checkbox" checked></input>')
    await page.uncheck("input")
    assert await page.evaluate("checkbox.checked") is False


async def test_not_uncheck_the_unchecked_box(page):
    await page.set_content('<input id="checkbox" type="checkbox"></input>')
    await page.uncheck("input")
    assert await page.evaluate("checkbox.checked") is False


async def test_check_the_box_by_label(page):
    await page.set_content(
        '<label for="checkbox"><input id="checkbox" type="checkbox"></input></label>'
    )
    await page.check("label")
    assert await page.evaluate("checkbox.checked")


async def test_check_the_box_outside_label(page):
    await page.set_content(
        '<label for="checkbox">Text</label><div><input id="checkbox" type="checkbox"></input></div>'
    )
    await page.check("label")
    assert await page.evaluate("checkbox.checked")


async def test_check_the_box_inside_label_without_id(page):
    await page.set_content(
        '<label>Text<span><input id="checkbox" type="checkbox"></input></span></label>'
    )
    await page.check("label")
    assert await page.evaluate("checkbox.checked")


async def test_check_radio(page):
    await page.set_content(
        """
        <input type='radio'>one</input>
        <input id='two' type='radio'>two</input>
        <input type='radio'>three</input>"""
    )
    await page.check("#two")
    assert await page.evaluate("two.checked")


async def test_check_the_box_by_aria_role(page):
    await page.set_content(
        """<div role='checkbox' id='checkbox'>CHECKBOX</div>
        <script>
            checkbox.addEventListener('click', () => checkbox.setAttribute('aria-checked', 'true'))
        </script>"""
    )
    await page.check("div")
    assert await page.evaluate("checkbox.getAttribute ('aria-checked')")
