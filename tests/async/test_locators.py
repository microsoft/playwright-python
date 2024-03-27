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

import os
import re
import traceback
from typing import Callable
from urllib.parse import urlparse

import pytest

from playwright._impl._path_utils import get_file_dirname
from playwright.async_api import Error, Page, expect
from tests.server import Server

_dirname = get_file_dirname()
FILE_TO_UPLOAD = _dirname / ".." / "assets/file-to-upload.txt"


async def test_locators_click_should_work(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    button = page.locator("button")
    await button.click()
    assert await page.evaluate("window['result']") == "Clicked"


async def test_locators_click_should_work_with_node_removed(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    await page.evaluate("delete window['Node']")
    button = page.locator("button")
    await button.click()
    assert await page.evaluate("window['result']") == "Clicked"


async def test_locators_click_should_work_for_text_nodes(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    await page.evaluate(
        """() => {
        window['double'] = false;
        const button = document.querySelector('button');
        button.addEventListener('dblclick', event => {
        window['double'] = true;
        });
    }"""
    )
    button = page.locator("button")
    await button.dblclick()
    assert await page.evaluate("double") is True
    assert await page.evaluate("result") == "Clicked"


async def test_locators_should_have_repr(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    button = page.locator("button")
    await button.click()
    assert (
        str(button)
        == f"<Locator frame=<Frame name= url='{server.PREFIX}/input/button.html'> selector='button'>"
    )


async def test_locators_get_attribute_should_work(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/dom.html")
    button = page.locator("#outer")
    assert await button.get_attribute("name") == "value"
    assert await button.get_attribute("foo") is None


async def test_locators_input_value_should_work(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/dom.html")
    await page.fill("#textarea", "input value")
    text_area = page.locator("#textarea")
    assert await text_area.input_value() == "input value"


async def test_locators_inner_html_should_work(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/dom.html")
    locator = page.locator("#outer")
    assert await locator.inner_html() == '<div id="inner">Text,\nmore text</div>'


async def test_locators_inner_text_should_work(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/dom.html")
    locator = page.locator("#inner")
    assert await locator.inner_text() == "Text, more text"


async def test_locators_text_content_should_work(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/dom.html")
    locator = page.locator("#inner")
    assert await locator.text_content() == "Text,\nmore text"


async def test_locators_is_hidden_and_is_visible_should_work(page: Page) -> None:
    await page.set_content("<div>Hi</div><span></span>")

    div = page.locator("div")
    assert await div.is_visible() is True
    assert await div.is_hidden() is False

    span = page.locator("span")
    assert await span.is_visible() is False
    assert await span.is_hidden() is True


async def test_locators_is_enabled_and_is_disabled_should_work(page: Page) -> None:
    await page.set_content(
        """
        <button disabled>button1</button>
        <button>button2</button>
        <div>div</div>
    """
    )

    div = page.locator("div")
    assert await div.is_enabled() is True
    assert await div.is_disabled() is False

    button1 = page.locator(':text("button1")')
    assert await button1.is_enabled() is False
    assert await button1.is_disabled() is True

    button1 = page.locator(':text("button2")')
    assert await button1.is_enabled() is True
    assert await button1.is_disabled() is False


async def test_locators_is_editable_should_work(page: Page) -> None:
    await page.set_content(
        """
        <input id=input1 disabled><textarea></textarea><input id=input2>
    """
    )

    input1 = page.locator("#input1")
    assert await input1.is_editable() is False

    input2 = page.locator("#input2")
    assert await input2.is_editable() is True


async def test_locators_is_checked_should_work(page: Page) -> None:
    await page.set_content(
        """
        <input type='checkbox' checked><div>Not a checkbox</div>
    """
    )

    element = page.locator("input")
    assert await element.is_checked() is True
    await element.evaluate("e => e.checked = false")
    assert await element.is_checked() is False


async def test_locators_all_text_contents_should_work(page: Page) -> None:
    await page.set_content(
        """
        <div>A</div><div>B</div><div>C</div>
    """
    )

    element = page.locator("div")
    assert await element.all_text_contents() == ["A", "B", "C"]


async def test_locators_all_inner_texts(page: Page) -> None:
    await page.set_content(
        """
        <div>A</div><div>B</div><div>C</div>
    """
    )

    element = page.locator("div")
    assert await element.all_inner_texts() == ["A", "B", "C"]


async def test_locators_should_query_existing_element(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/playground.html")
    await page.set_content(
        """<html><body><div class="second"><div class="inner">A</div></div></body></html>"""
    )
    html = page.locator("html")
    second = html.locator(".second")
    inner = second.locator(".inner")
    assert (
        await page.evaluate("e => e.textContent", await inner.element_handle()) == "A"
    )


async def test_locators_evaluate_handle_should_work(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/dom.html")
    outer = page.locator("#outer")
    inner = outer.locator("#inner")
    check = inner.locator("#check")
    text = await inner.evaluate_handle("e => e.firstChild")
    await page.evaluate("1 + 1")
    assert (
        str(outer)
        == f"<Locator frame=<Frame name= url='{server.PREFIX}/dom.html'> selector='#outer'>"
    )
    assert (
        str(inner)
        == f"<Locator frame=<Frame name= url='{server.PREFIX}/dom.html'> selector='#outer >> #inner'>"
    )
    assert str(text) == "JSHandle@#text=Text,↵more text"
    assert (
        str(check)
        == f"<Locator frame=<Frame name= url='{server.PREFIX}/dom.html'> selector='#outer >> #inner >> #check'>"
    )


async def test_locators_should_query_existing_elements(page: Page) -> None:
    await page.set_content(
        """<html><body><div>A</div><br/><div>B</div></body></html>"""
    )
    html = page.locator("html")
    elements = await html.locator("div").element_handles()
    assert len(elements) == 2
    result = []
    for element in elements:
        result.append(await page.evaluate("e => e.textContent", element))
    assert result == ["A", "B"]


async def test_locators_return_empty_array_for_non_existing_elements(
    page: Page,
) -> None:
    await page.set_content(
        """<html><body><div>A</div><br/><div>B</div></body></html>"""
    )
    html = page.locator("html")
    elements = await html.locator("abc").element_handles()
    assert len(elements) == 0
    assert elements == []


async def test_locators_evaluate_all_should_work(page: Page) -> None:
    await page.set_content(
        """<html><body><div class="tweet"><div class="like">100</div><div class="like">10</div></div></body></html>"""
    )
    tweet = page.locator(".tweet .like")
    content = await tweet.evaluate_all("nodes => nodes.map(n => n.innerText)")
    assert content == ["100", "10"]


async def test_locators_evaluate_all_should_work_with_missing_selector(
    page: Page,
) -> None:
    await page.set_content(
        """<div class="a">not-a-child-div</div><div id="myId"></div"""
    )
    tweet = page.locator("#myId .a")
    nodes_length = await tweet.evaluate_all("nodes => nodes.length")
    assert nodes_length == 0


async def test_locators_hover_should_work(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/scrollable.html")
    button = page.locator("#button-6")
    await button.hover()
    assert (
        await page.evaluate("document.querySelector('button:hover').id") == "button-6"
    )


async def test_locators_fill_should_work(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/textarea.html")
    button = page.locator("input")
    await button.fill("some value")
    assert await page.evaluate("result") == "some value"


async def test_locators_clear_should_work(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/textarea.html")
    button = page.locator("input")
    await button.fill("some value")
    assert await page.evaluate("result") == "some value"
    await button.clear()
    assert await page.evaluate("result") == ""


async def test_locators_check_should_work(page: Page) -> None:
    await page.set_content("<input id='checkbox' type='checkbox'></input>")
    button = page.locator("input")
    await button.check()
    assert await page.evaluate("checkbox.checked") is True


async def test_locators_uncheck_should_work(page: Page) -> None:
    await page.set_content("<input id='checkbox' type='checkbox' checked></input>")
    button = page.locator("input")
    await button.uncheck()
    assert await page.evaluate("checkbox.checked") is False


async def test_locators_select_option_should_work(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    select = page.locator("select")
    await select.select_option("blue")
    assert await page.evaluate("result.onInput") == ["blue"]
    assert await page.evaluate("result.onChange") == ["blue"]


async def test_locators_focus_should_work(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    button = page.locator("button")
    assert await button.evaluate("button => document.activeElement === button") is False
    await button.focus()
    assert await button.evaluate("button => document.activeElement === button") is True


async def test_locators_dispatch_event_should_work(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    button = page.locator("button")
    await button.dispatch_event("click")
    assert await page.evaluate("result") == "Clicked"


async def test_locators_should_upload_a_file(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/fileupload.html")
    input = page.locator("input[type=file]")

    file_path = os.path.relpath(FILE_TO_UPLOAD, os.getcwd())
    await input.set_input_files(file_path)
    assert (
        await page.evaluate("e => e.files[0].name", await input.element_handle())
        == "file-to-upload.txt"
    )


async def test_locators_should_press(page: Page) -> None:
    await page.set_content("<input type='text' />")
    await page.locator("input").press("h")
    assert await page.eval_on_selector("input", "input => input.value") == "h"


async def test_locators_should_scroll_into_view(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/offscreenbuttons.html")
    for i in range(11):
        button = page.locator(f"#btn{i}")
        before = await button.evaluate(
            "button => button.getBoundingClientRect().right - window.innerWidth"
        )
        assert before == 10 * i
        await button.scroll_into_view_if_needed()
        after = await button.evaluate(
            "button => button.getBoundingClientRect().right - window.innerWidth"
        )
        assert after <= 0
        await page.evaluate("window.scrollTo(0, 0)")


async def test_locators_should_select_textarea(
    page: Page, server: Server, browser_name: str
) -> None:
    await page.goto(server.PREFIX + "/input/textarea.html")
    textarea = page.locator("textarea")
    await textarea.evaluate("textarea => textarea.value = 'some value'")
    await textarea.select_text()
    if browser_name == "firefox" or browser_name == "webkit":
        assert await textarea.evaluate("el => el.selectionStart") == 0
        assert await textarea.evaluate("el => el.selectionEnd") == 10
    else:
        assert await page.evaluate("window.getSelection().toString()") == "some value"


async def test_locators_should_type(page: Page) -> None:
    await page.set_content("<input type='text' />")
    await page.locator("input").type("hello")
    assert await page.eval_on_selector("input", "input => input.value") == "hello"


async def test_locators_should_press_sequentially(page: Page) -> None:
    await page.set_content("<input type='text' />")
    await page.locator("input").press_sequentially("hello")
    assert await page.eval_on_selector("input", "input => input.value") == "hello"


async def test_locators_should_screenshot(
    page: Page, server: Server, assert_to_be_golden: Callable[[bytes, str], None]
) -> None:
    await page.set_viewport_size(
        {
            "width": 500,
            "height": 500,
        }
    )
    await page.goto(server.PREFIX + "/grid.html")
    await page.evaluate("window.scrollBy(50, 100)")
    element = page.locator(".box:nth-of-type(3)")
    assert_to_be_golden(
        await element.screenshot(), "screenshot-element-bounding-box.png"
    )


async def test_locators_should_return_bounding_box(page: Page, server: Server) -> None:
    await page.set_viewport_size(
        {
            "width": 500,
            "height": 500,
        }
    )
    await page.goto(server.PREFIX + "/grid.html")
    element = page.locator(".box:nth-of-type(13)")
    box = await element.bounding_box()
    assert box == {
        "x": 100,
        "y": 50,
        "width": 50,
        "height": 50,
    }


async def test_locators_should_respect_first_and_last(page: Page) -> None:
    await page.set_content(
        """
        <section>
            <div><p>A</p></div>
            <div><p>A</p><p>A</p></div>
            <div><p>A</p><p>A</p><p>A</p></div>
        </section>"""
    )
    assert await page.locator("div >> p").count() == 6
    assert await page.locator("div").locator("p").count() == 6
    assert await page.locator("div").first.locator("p").count() == 1
    assert await page.locator("div").last.locator("p").count() == 3


async def test_locators_should_respect_nth(page: Page) -> None:
    await page.set_content(
        """
    <section>
        <div><p>A</p></div>
        <div><p>A</p><p>A</p></div>
        <div><p>A</p><p>A</p><p>A</p></div>
    </section>"""
    )
    assert await page.locator("div >> p").nth(0).count() == 1
    assert await page.locator("div").nth(1).locator("p").count() == 2
    assert await page.locator("div").nth(2).locator("p").count() == 3


async def test_locators_should_throw_on_capture_without_nth(page: Page) -> None:
    await page.set_content(
        """
        <section><div><p>A</p></div></section>
    """
    )
    with pytest.raises(Error, match="Can't query n-th element"):
        await page.locator("*css=div >> p").nth(1).click()


async def test_locators_should_throw_due_to_strictness(page: Page) -> None:
    await page.set_content(
        """
        <div>A</div><div>B</div>
    """
    )
    with pytest.raises(Error, match="strict mode violation"):
        await page.locator("div").is_visible()


async def test_locators_should_throw_due_to_strictness_2(page: Page) -> None:
    await page.set_content(
        """
        <select><option>One</option><option>Two</option></select>
    """
    )
    with pytest.raises(Error, match="strict mode violation"):
        await page.locator("option").evaluate("e => {}")


async def test_locators_set_checked(page: Page) -> None:
    await page.set_content("`<input id='checkbox' type='checkbox'></input>`")
    locator = page.locator("input")
    await locator.set_checked(True)
    assert await page.evaluate("checkbox.checked")
    await locator.set_checked(False)
    assert await page.evaluate("checkbox.checked") is False


async def test_locators_wait_for(page: Page) -> None:
    await page.set_content("<div></div>")
    locator = page.locator("div")
    task = locator.wait_for()
    await page.eval_on_selector("div", "div => div.innerHTML = '<span>target</span>'")
    await task
    assert await locator.text_content() == "target"


async def test_should_wait_for_hidden(page: Page) -> None:
    await page.set_content("<div><span>target</span></div>")
    locator = page.locator("span")
    task = locator.wait_for(state="hidden")
    await page.eval_on_selector("div", "div => div.innerHTML = ''")
    await task


async def test_should_combine_visible_with_other_selectors(page: Page) -> None:
    await page.set_content(
        """<div>
        <div class="item" style="display: none">Hidden data0</div>
        <div class="item">visible data1</div>
        <div class="item" style="display: none">Hidden data1</div>
        <div class="item">visible data2</div>
        <div class="item" style="display: none">Hidden data1</div>
        <div class="item">visible data3</div>
        </div>
    """
    )
    locator = page.locator(".item >> visible=true").nth(1)
    await expect(locator).to_have_text("visible data2")
    await expect(page.locator(".item >> visible=true >> text=data3")).to_have_text(
        "visible data3"
    )


async def test_locator_count_should_work_with_deleted_map_in_main_world(
    page: Page,
) -> None:
    await page.evaluate("Map = 1")
    await page.locator("#searchResultTableDiv .x-grid3-row").count()
    await expect(page.locator("#searchResultTableDiv .x-grid3-row")).to_have_count(0)


async def test_locator_locator_and_framelocator_locator_should_accept_locator(
    page: Page,
) -> None:
    await page.set_content(
        """
        <div><input value=outer></div>
        <iframe srcdoc="<div><input value=inner></div>"></iframe>
    """
    )

    input_locator = page.locator("input")
    assert await input_locator.input_value() == "outer"
    assert await page.locator("div").locator(input_locator).input_value() == "outer"
    assert (
        await page.frame_locator("iframe").locator(input_locator).input_value()
        == "inner"
    )
    assert (
        await page.frame_locator("iframe")
        .locator("div")
        .locator(input_locator)
        .input_value()
        == "inner"
    )

    div_locator = page.locator("div")
    assert await div_locator.locator("input").input_value() == "outer"
    assert (
        await page.frame_locator("iframe")
        .locator(div_locator)
        .locator("input")
        .input_value()
        == "inner"
    )


async def route_iframe(page: Page) -> None:
    await page.route(
        "**/empty.html",
        lambda route: route.fulfill(
            body='<iframe src="iframe.html" name="frame1">></iframe>',
            content_type="text/html",
        ),
    )
    await page.route(
        "**/iframe.html",
        lambda route: route.fulfill(
            body="""<html>
          <div>
            <button>Hello iframe</button>
            <iframe src="iframe-2.html"></iframe>
          </div>
          <span>1</span>
          <span>2</span>
        </html>""",
            content_type="text/html",
        ),
    )
    await page.route(
        "**/iframe-2.html",
        lambda route: route.fulfill(
            body="<html><button>Hello nested iframe</button></html>",
            content_type="text/html",
        ),
    )


async def test_locators_frame_should_work_with_iframe(
    page: Page, server: Server
) -> None:
    await route_iframe(page)
    await page.goto(server.EMPTY_PAGE)
    button = page.frame_locator("iframe").locator("button")
    await button.wait_for()
    assert await button.inner_text() == "Hello iframe"
    await button.click()


async def test_locators_frame_should_work_for_nested_iframe(
    page: Page, server: Server
) -> None:
    await route_iframe(page)
    await page.goto(server.EMPTY_PAGE)
    button = page.frame_locator("iframe").frame_locator("iframe").locator("button")
    await button.wait_for()
    assert await button.inner_text() == "Hello nested iframe"
    await button.click()


async def test_locators_frame_should_work_with_locator_frame_locator(
    page: Page, server: Server
) -> None:
    await route_iframe(page)
    await page.goto(server.EMPTY_PAGE)
    button = page.locator("body").frame_locator("iframe").locator("button")
    await button.wait_for()
    assert await button.inner_text() == "Hello iframe"
    await button.click()


async def test_locator_content_frame_should_work(page: Page, server: Server) -> None:
    await route_iframe(page)
    await page.goto(server.EMPTY_PAGE)
    locator = page.locator("iframe")
    frame_locator = locator.content_frame
    button = frame_locator.locator("button")
    assert await button.inner_text() == "Hello iframe"
    await expect(button).to_have_text("Hello iframe")
    await button.click()


async def test_frame_locator_owner_should_work(page: Page, server: Server) -> None:
    await route_iframe(page)
    await page.goto(server.EMPTY_PAGE)
    frame_locator = page.frame_locator("iframe")
    locator = frame_locator.owner
    await expect(locator).to_be_visible()
    assert await locator.get_attribute("name") == "frame1"


async def route_ambiguous(page: Page) -> None:
    await page.route(
        "**/empty.html",
        lambda route: route.fulfill(
            body="""
        <iframe src="iframe-1.html"></iframe>
        <iframe src="iframe-2.html"></iframe>
        <iframe src="iframe-3.html"></iframe>
    """,
            content_type="text/html",
        ),
    )
    await page.route(
        "**/iframe-*",
        lambda route: route.fulfill(
            body=f"<html><button>Hello from {urlparse(route.request.url).path[1:]}</button></html>",
            content_type="text/html",
        ),
    )


async def test_locator_frame_locator_should_throw_on_ambiguity(
    page: Page, server: Server
) -> None:
    await route_ambiguous(page)
    await page.goto(server.EMPTY_PAGE)
    button = page.locator("body").frame_locator("iframe").locator("button")
    with pytest.raises(
        Error,
        match=r'.*strict mode violation: locator\("body"\)\.locator\("iframe"\) resolved to 3 elements.*',
    ):
        await button.wait_for()


async def test_locator_frame_locator_should_not_throw_on_first_last_nth(
    page: Page, server: Server
) -> None:
    await route_ambiguous(page)
    await page.goto(server.EMPTY_PAGE)
    button1 = page.locator("body").frame_locator("iframe").first.locator("button")
    assert await button1.text_content() == "Hello from iframe-1.html"
    button2 = page.locator("body").frame_locator("iframe").nth(1).locator("button")
    assert await button2.text_content() == "Hello from iframe-2.html"
    button3 = page.locator("body").frame_locator("iframe").last.locator("button")
    assert await button3.text_content() == "Hello from iframe-3.html"


async def test_drag_to(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/drag-n-drop.html")
    await page.locator("#source").drag_to(page.locator("#target"))
    assert (
        await page.eval_on_selector(
            "#target", "target => target.contains(document.querySelector('#source'))"
        )
        is True
    )


async def test_drag_to_with_position(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        """
      <div style="width:100px;height:100px;background:red;" id="red">
      </div>
      <div style="width:100px;height:100px;background:blue;" id="blue">
      </div>
    """
    )
    events_handle = await page.evaluate_handle(
        """
        () => {
        const events = [];
        document.getElementById('red').addEventListener('mousedown', event => {
            events.push({
            type: 'mousedown',
            x: event.offsetX,
            y: event.offsetY,
            });
        });
        document.getElementById('blue').addEventListener('mouseup', event => {
            events.push({
            type: 'mouseup',
            x: event.offsetX,
            y: event.offsetY,
            });
        });
        return events;
        }
    """
    )
    await page.locator("#red").drag_to(
        page.locator("#blue"),
        source_position={"x": 34, "y": 7},
        target_position={"x": 10, "y": 20},
    )
    assert await events_handle.json_value() == [
        {"type": "mousedown", "x": 34, "y": 7},
        {"type": "mouseup", "x": 10, "y": 20},
    ]


async def test_locator_query_should_filter_by_text(page: Page, server: Server) -> None:
    await page.set_content("<div>Foobar</div><div>Bar</div>")
    await expect(page.locator("div", has_text="Foo")).to_have_text("Foobar")


async def test_locator_query_should_filter_by_text_2(
    page: Page, server: Server
) -> None:
    await page.set_content("<div>foo <span>hello world</span> bar</div>")
    await expect(page.locator("div", has_text="hello world")).to_have_text(
        "foo hello world bar"
    )


async def test_locator_query_should_filter_by_regex(page: Page, server: Server) -> None:
    await page.set_content("<div>Foobar</div><div>Bar</div>")
    await expect(page.locator("div", has_text=re.compile(r"Foo.*"))).to_have_text(
        "Foobar"
    )


async def test_locator_query_should_filter_by_text_with_quotes(
    page: Page, server: Server
) -> None:
    await page.set_content('<div>Hello "world"</div><div>Hello world</div>')
    await expect(page.locator("div", has_text='Hello "world"')).to_have_text(
        'Hello "world"'
    )


async def test_locator_query_should_filter_by_regex_with_quotes(
    page: Page, server: Server
) -> None:
    await page.set_content('<div>Hello "world"</div><div>Hello world</div>')
    await expect(
        page.locator("div", has_text=re.compile('Hello "world"'))
    ).to_have_text('Hello "world"')


async def test_locator_query_should_filter_by_regex_and_regexp_flags(
    page: Page, server: Server
) -> None:
    await page.set_content('<div>Hello "world"</div><div>Hello world</div>')
    await expect(
        page.locator("div", has_text=re.compile('hElLo "world', re.IGNORECASE))
    ).to_have_text('Hello "world"')


async def test_locator_should_return_page(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/frames/two-frames.html")
    outer = page.locator("#outer")
    assert outer.page == page

    inner = outer.locator("#inner")
    assert inner.page == page

    in_frame = page.frames[1].locator("div")
    assert in_frame.page == page


async def test_locator_should_support_has_locator(page: Page, server: Server) -> None:
    await page.set_content("<div><span>hello</span></div><div><span>world</span></div>")
    await expect(page.locator("div", has=page.locator("text=world"))).to_have_count(1)
    assert (
        await page.locator("div", has=page.locator("text=world")).evaluate(
            "e => e.outerHTML"
        )
        == "<div><span>world</span></div>"
    )
    await expect(page.locator("div", has=page.locator('text="hello"'))).to_have_count(1)
    assert (
        await page.locator("div", has=page.locator('text="hello"')).evaluate(
            "e => e.outerHTML"
        )
        == "<div><span>hello</span></div>"
    )
    await expect(page.locator("div", has=page.locator("xpath=./span"))).to_have_count(2)
    await expect(page.locator("div", has=page.locator("span"))).to_have_count(2)
    await expect(
        page.locator("div", has=page.locator("span", has_text="wor"))
    ).to_have_count(1)
    assert (
        await page.locator("div", has=page.locator("span", has_text="wor")).evaluate(
            "e => e.outerHTML"
        )
        == "<div><span>world</span></div>"
    )
    await expect(
        page.locator(
            "div",
            has=page.locator("span"),
            has_text="wor",
        )
    ).to_have_count(1)


async def test_locator_should_enforce_same_frame_for_has_locator(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/frames/two-frames.html")
    child = page.frames[1]
    with pytest.raises(Error) as exc_info:
        page.locator("div", has=child.locator("span"))
    assert (
        'Inner "has" locator must belong to the same frame.' in exc_info.value.message
    )


async def test_locator_should_support_locator_or(page: Page, server: Server) -> None:
    await page.set_content("<div>hello</div><span>world</span>")
    await expect(page.locator("div").or_(page.locator("span"))).to_have_count(2)
    await expect(page.locator("div").or_(page.locator("span"))).to_have_text(
        ["hello", "world"]
    )
    await expect(
        page.locator("span").or_(page.locator("article")).or_(page.locator("div"))
    ).to_have_text(["hello", "world"])
    await expect(page.locator("article").or_(page.locator("someting"))).to_have_count(0)
    await expect(page.locator("article").or_(page.locator("div"))).to_have_text("hello")
    await expect(page.locator("article").or_(page.locator("span"))).to_have_text(
        "world"
    )
    await expect(page.locator("div").or_(page.locator("article"))).to_have_text("hello")
    await expect(page.locator("span").or_(page.locator("article"))).to_have_text(
        "world"
    )


async def test_locator_should_support_locator_locator_with_and_or(page: Page) -> None:
    await page.set_content(
        """
        <div>one <span>two</span> <button>three</button> </div>
        <span>four</span>
        <button>five</button>
        """
    )

    await expect(page.locator("div").locator(page.locator("button"))).to_have_text(
        ["three"]
    )
    await expect(
        page.locator("div").locator(page.locator("button").or_(page.locator("span")))
    ).to_have_text(["two", "three"])
    await expect(page.locator("button").or_(page.locator("span"))).to_have_text(
        ["two", "three", "four", "five"]
    )

    await expect(
        page.locator("div").locator(
            page.locator("button").and_(page.get_by_role("button"))
        )
    ).to_have_text(["three"])
    await expect(page.locator("button").and_(page.get_by_role("button"))).to_have_text(
        ["three", "five"]
    )


async def test_locator_highlight_should_work(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/grid.html")
    await page.locator(".box").nth(3).highlight()
    assert await page.locator("x-pw-glass").is_visible()


async def test_should_support_locator_that(page: Page) -> None:
    await page.set_content(
        "<section><div><span>hello</span></div><div><span>world</span></div></section>"
    )

    await expect(page.locator("div").filter(has_text="hello")).to_have_count(1)
    await expect(
        page.locator("div", has_text="hello").filter(has_text="hello")
    ).to_have_count(1)
    await expect(
        page.locator("div", has_text="hello").filter(has_text="world")
    ).to_have_count(0)
    await expect(
        page.locator("section", has_text="hello").filter(has_text="world")
    ).to_have_count(1)
    await expect(
        page.locator("div").filter(has_text="hello").locator("span")
    ).to_have_count(1)
    await expect(
        page.locator("div").filter(has=page.locator("span", has_text="world"))
    ).to_have_count(1)
    await expect(page.locator("div").filter(has=page.locator("span"))).to_have_count(2)
    await expect(
        page.locator("div").filter(
            has=page.locator("span"),
            has_text="world",
        )
    ).to_have_count(1)


async def test_should_filter_by_case_insensitive_regex_in_a_child(page: Page) -> None:
    await page.set_content('<div class="test"><h5>Title Text</h5></div>')
    await expect(
        page.locator("div", has_text=re.compile(r"^title text$", re.I))
    ).to_have_text("Title Text")


async def test_should_filter_by_case_insensitive_regex_in_multiple_children(
    page: Page,
) -> None:
    await page.set_content(
        '<div class="test"><h5>Title</h5> <h2><i>Text</i></h2></div>'
    )
    await expect(
        page.locator("div", has_text=re.compile(r"^title text$", re.I))
    ).to_have_class("test")


async def test_should_filter_by_regex_with_special_symbols(page: Page) -> None:
    await page.set_content(
        '<div class="test"><h5>First/"and"</h5><h2><i>Second\\</i></h2></div>'
    )
    await expect(
        page.locator("div", has_text=re.compile(r'^first\/".*"second\\$', re.S | re.I))
    ).to_have_class("test")


async def test_should_support_locator_filter(page: Page) -> None:
    await page.set_content(
        "<section><div><span>hello</span></div><div><span>world</span></div></section>"
    )

    await expect(page.locator("div").filter(has_text="hello")).to_have_count(1)
    await expect(
        page.locator("div", has_text="hello").filter(has_text="hello")
    ).to_have_count(1)
    await expect(
        page.locator("div", has_text="hello").filter(has_text="world")
    ).to_have_count(0)
    await expect(
        page.locator("section", has_text="hello").filter(has_text="world")
    ).to_have_count(1)
    await expect(
        page.locator("div").filter(has_text="hello").locator("span")
    ).to_have_count(1)
    await expect(
        page.locator("div").filter(has=page.locator("span", has_text="world"))
    ).to_have_count(1)
    await expect(page.locator("div").filter(has=page.locator("span"))).to_have_count(2)
    await expect(
        page.locator("div").filter(
            has=page.locator("span"),
            has_text="world",
        )
    ).to_have_count(1)
    await expect(
        page.locator("div").filter(has_not=page.locator("span", has_text="world"))
    ).to_have_count(1)
    await expect(
        page.locator("div").filter(has_not=page.locator("section"))
    ).to_have_count(2)
    await expect(
        page.locator("div").filter(has_not=page.locator("span"))
    ).to_have_count(0)

    await expect(page.locator("div").filter(has_not_text="hello")).to_have_count(1)
    await expect(page.locator("div").filter(has_not_text="foo")).to_have_count(2)


async def test_locators_should_support_locator_and(page: Page, server: Server) -> None:
    await page.set_content(
        """
        <div data-testid=foo>hello</div><div data-testid=bar>world</div>
        <span data-testid=foo>hello2</span><span data-testid=bar>world2</span>
    """
    )
    await expect(page.locator("div").and_(page.locator("div"))).to_have_count(2)
    await expect(page.locator("div").and_(page.get_by_test_id("foo"))).to_have_text(
        ["hello"]
    )
    await expect(page.locator("div").and_(page.get_by_test_id("bar"))).to_have_text(
        ["world"]
    )
    await expect(page.get_by_test_id("foo").and_(page.locator("div"))).to_have_text(
        ["hello"]
    )
    await expect(page.get_by_test_id("bar").and_(page.locator("span"))).to_have_text(
        ["world2"]
    )
    await expect(
        page.locator("span").and_(page.get_by_test_id(re.compile("bar|foo")))
    ).to_have_count(2)


async def test_locators_has_does_not_encode_unicode(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    locators = [
        page.locator("button", has_text="Драматург"),
        page.locator("button", has_text=re.compile("Драматург")),
        page.locator("button", has=page.locator("text=Драматург")),
    ]
    for locator in locators:
        with pytest.raises(Error) as exc_info:
            await locator.click(timeout=1_000)
        assert "Драматург" in exc_info.value.message


async def test_locators_should_focus_and_blur_a_button(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    button = page.locator("button")
    assert not await button.evaluate("button => document.activeElement === button")

    focused = False
    blurred = False

    async def focus_event() -> None:
        nonlocal focused
        focused = True

    async def blur_event() -> None:
        nonlocal blurred
        blurred = True

    await page.expose_function("focusEvent", focus_event)
    await page.expose_function("blurEvent", blur_event)
    await button.evaluate(
        """button => {
        button.addEventListener('focus', window['focusEvent']);
        button.addEventListener('blur', window['blurEvent']);
    }"""
    )

    await button.focus()
    assert focused
    assert not blurred
    assert await button.evaluate("button => document.activeElement === button")

    await button.blur()
    assert focused
    assert blurred
    assert not await button.evaluate("button => document.activeElement === button")


async def test_locator_all_should_work(page: Page) -> None:
    await page.set_content("<div><p>A</p><p>B</p><p>C</p></div>")
    texts = []
    for p in await page.locator("p").all():
        texts.append(await p.text_content())
    assert texts == ["A", "B", "C"]


async def test_locator_click_timeout_error_should_contain_call_log(page: Page) -> None:
    with pytest.raises(Error) as exc_info:
        await page.get_by_role("button", name="Hello Python").click(timeout=42)
    formatted_exception = "".join(
        traceback.format_exception(type(exc_info.value), value=exc_info.value, tb=None)
    )
    assert "Locator.click: Timeout 42ms exceeded." in formatted_exception
    assert (
        'waiting for get_by_role("button", name="Hello Python")' in formatted_exception
    )
    assert (
        "During handling of the above exception, another exception occurred"
        not in formatted_exception
    )
