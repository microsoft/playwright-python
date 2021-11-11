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
from typing import Callable
from urllib.parse import urlparse

import pytest

from playwright._impl._path_utils import get_file_dirname
from playwright.sync_api import Error, Page
from tests.server import Server

_dirname = get_file_dirname()
FILE_TO_UPLOAD = _dirname / ".." / "assets/file-to-upload.txt"


def test_locators_click_should_work(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/button.html")
    button = page.locator("button")
    button.click()
    assert page.evaluate("window['result']") == "Clicked"


def test_locators_click_should_work_with_node_removed(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/input/button.html")
    page.evaluate("delete window['Node']")
    button = page.locator("button")
    button.click()
    assert page.evaluate("window['result']") == "Clicked"


def test_locators_click_should_work_for_text_nodes(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/button.html")
    page.evaluate(
        """() => {
        window['double'] = false;
        const button = document.querySelector('button');
        button.addEventListener('dblclick', event => {
        window['double'] = true;
        });
    }"""
    )
    button = page.locator("button")
    button.dblclick()
    assert page.evaluate("double") is True
    assert page.evaluate("result") == "Clicked"


def test_locators_should_have_repr(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/button.html")
    button = page.locator("button")
    button.click()
    assert (
        str(button)
        == f"<Locator frame=<Frame name= url='{server.PREFIX}/input/button.html'> selector='button'>"
    )


def test_locators_get_attribute_should_work(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/dom.html")
    button = page.locator("#outer")
    assert button.get_attribute("name") == "value"
    assert button.get_attribute("foo") is None


def test_locators_input_value_should_work(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/dom.html")
    page.fill("#textarea", "input value")
    text_area = page.locator("#textarea")
    assert text_area.input_value() == "input value"


def test_locators_inner_html_should_work(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/dom.html")
    locator = page.locator("#outer")
    assert locator.inner_html() == '<div id="inner">Text,\nmore text</div>'


def test_locators_inner_text_should_work(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/dom.html")
    locator = page.locator("#inner")
    assert locator.inner_text() == "Text, more text"


def test_locators_text_content_should_work(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/dom.html")
    locator = page.locator("#inner")
    assert locator.text_content() == "Text,\nmore text"


def test_locators_is_hidden_and_is_visible_should_work(page: Page) -> None:
    page.set_content("<div>Hi</div><span></span>")

    div = page.locator("div")
    assert div.is_visible() is True
    assert div.is_hidden() is False

    span = page.locator("span")
    assert span.is_visible() is False
    assert span.is_hidden() is True


def test_locators_is_enabled_and_is_disabled_should_work(page: Page) -> None:
    page.set_content(
        """
        <button disabled>button1</button>
        <button>button2</button>
        <div>div</div>
    """
    )

    div = page.locator("div")
    assert div.is_enabled() is True
    assert div.is_disabled() is False

    button1 = page.locator(':text("button1")')
    assert button1.is_enabled() is False
    assert button1.is_disabled() is True

    button1 = page.locator(':text("button2")')
    assert button1.is_enabled() is True
    assert button1.is_disabled() is False


def test_locators_is_editable_should_work(page: Page) -> None:
    page.set_content(
        """
        <input id=input1 disabled><textarea></textarea><input id=input2>
    """
    )

    input1 = page.locator("#input1")
    assert input1.is_editable() is False

    input2 = page.locator("#input2")
    assert input2.is_editable() is True


def test_locators_is_checked_should_work(page: Page) -> None:
    page.set_content(
        """
        <input type='checkbox' checked><div>Not a checkbox</div>
    """
    )

    element = page.locator("input")
    assert element.is_checked() is True
    element.evaluate("e => e.checked = false")
    assert element.is_checked() is False


def test_locators_all_text_contents_should_work(page: Page) -> None:
    page.set_content(
        """
        <div>A</div><div>B</div><div>C</div>
    """
    )

    element = page.locator("div")
    assert element.all_text_contents() == ["A", "B", "C"]


def test_locators_all_inner_texts(page: Page) -> None:
    page.set_content(
        """
        <div>A</div><div>B</div><div>C</div>
    """
    )

    element = page.locator("div")
    assert element.all_inner_texts() == ["A", "B", "C"]


def test_locators_should_query_existing_element(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/playground.html")
    page.set_content(
        """<html><body><div class="second"><div class="inner">A</div></div></body></html>"""
    )
    html = page.locator("html")
    second = html.locator(".second")
    inner = second.locator(".inner")
    assert page.evaluate("e => e.textContent", inner.element_handle()) == "A"


def test_locators_evaluate_handle_should_work(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/dom.html")
    outer = page.locator("#outer")
    inner = outer.locator("#inner")
    check = inner.locator("#check")
    text = inner.evaluate_handle("e => e.firstChild")
    page.evaluate("1 + 1")
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


def test_locators_should_query_existing_elements(page: Page) -> None:
    page.set_content("""<html><body><div>A</div><br/><div>B</div></body></html>""")
    html = page.locator("html")
    elements = html.locator("div").element_handles()
    assert len(elements) == 2
    result = []
    for element in elements:
        result.append(page.evaluate("e => e.textContent", element))
    assert result == ["A", "B"]


def test_locators_return_empty_array_for_non_existing_elements(page: Page) -> None:
    page.set_content("""<html><body><div>A</div><br/><div>B</div></body></html>""")
    html = page.locator("html")
    elements = html.locator("abc").element_handles()
    assert len(elements) == 0
    assert elements == []


def test_locators_evaluate_all_should_work(page: Page) -> None:
    page.set_content(
        """<html><body><div class="tweet"><div class="like">100</div><div class="like">10</div></div></body></html>"""
    )
    tweet = page.locator(".tweet .like")
    content = tweet.evaluate_all("nodes => nodes.map(n => n.innerText)")
    assert content == ["100", "10"]


def test_locators_evaluate_all_should_work_with_missing_selector(page: Page) -> None:
    page.set_content("""<div class="a">not-a-child-div</div><div id="myId"></div""")
    tweet = page.locator("#myId .a")
    nodes_length = tweet.evaluate_all("nodes => nodes.length")
    assert nodes_length == 0


def test_locators_hover_should_work(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/scrollable.html")
    button = page.locator("#button-6")
    button.hover()
    assert page.evaluate("document.querySelector('button:hover').id") == "button-6"


def test_locators_fill_should_work(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/textarea.html")
    button = page.locator("input")
    button.fill("some value")
    assert page.evaluate("result") == "some value"


def test_locators_check_should_work(page: Page) -> None:
    page.set_content("<input id='checkbox' type='checkbox'></input>")
    button = page.locator("input")
    button.check()
    assert page.evaluate("checkbox.checked") is True


def test_locators_uncheck_should_work(page: Page) -> None:
    page.set_content("<input id='checkbox' type='checkbox' checked></input>")
    button = page.locator("input")
    button.uncheck()
    assert page.evaluate("checkbox.checked") is False


def test_locators_select_option_should_work(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/select.html")
    select = page.locator("select")
    select.select_option("blue")
    assert page.evaluate("result.onInput") == ["blue"]
    assert page.evaluate("result.onChange") == ["blue"]


def test_locators_focus_should_work(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/button.html")
    button = page.locator("button")
    assert button.evaluate("button => document.activeElement === button") is False
    button.focus()
    assert button.evaluate("button => document.activeElement === button") is True


def test_locators_dispatch_event_should_work(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/button.html")
    button = page.locator("button")
    button.dispatch_event("click")
    assert page.evaluate("result") == "Clicked"


def test_locators_should_upload_a_file(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/fileupload.html")
    input = page.locator("input[type=file]")

    file_path = os.path.relpath(FILE_TO_UPLOAD, os.getcwd())
    input.set_input_files(file_path)
    assert (
        page.evaluate("e => e.files[0].name", input.element_handle())
        == "file-to-upload.txt"
    )


def test_locators_should_press(page: Page) -> None:
    page.set_content("<input type='text' />")
    page.locator("input").press("h")
    page.eval_on_selector("input", "input => input.value") == "h"


def test_locators_should_scroll_into_view(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/offscreenbuttons.html")
    for i in range(11):
        button = page.locator(f"#btn{i}")
        before = button.evaluate(
            "button => button.getBoundingClientRect().right - window.innerWidth"
        )
        assert before == 10 * i
        button.scroll_into_view_if_needed()
        after = button.evaluate(
            "button => button.getBoundingClientRect().right - window.innerWidth"
        )
        assert after <= 0
        page.evaluate("window.scrollTo(0, 0)")


def test_locators_should_select_textarea(
    page: Page, server: Server, browser_name: str
) -> None:
    page.goto(server.PREFIX + "/input/textarea.html")
    textarea = page.locator("textarea")
    textarea.evaluate("textarea => textarea.value = 'some value'")
    textarea.select_text()
    if browser_name == "firefox":
        assert textarea.evaluate("el => el.selectionStart") == 0
        assert textarea.evaluate("el => el.selectionEnd") == 10
    else:
        assert page.evaluate("window.getSelection().toString()") == "some value"


def test_locators_should_type(page: Page) -> None:
    page.set_content("<input type='text' />")
    page.locator("input").type("hello")
    page.eval_on_selector("input", "input => input.value") == "hello"


def test_locators_should_screenshot(
    page: Page, server: Server, assert_to_be_golden: Callable[[bytes, str], None]
) -> None:
    page.set_viewport_size(
        {
            "width": 500,
            "height": 500,
        }
    )
    page.goto(server.PREFIX + "/grid.html")
    page.evaluate("window.scrollBy(50, 100)")
    element = page.locator(".box:nth-of-type(3)")
    assert_to_be_golden(element.screenshot(), "screenshot-element-bounding-box.png")


def test_locators_should_return_bounding_box(page: Page, server: Server) -> None:
    page.set_viewport_size(
        {
            "width": 500,
            "height": 500,
        }
    )
    page.goto(server.PREFIX + "/grid.html")
    element = page.locator(".box:nth-of-type(13)")
    box = element.bounding_box()
    assert box == {
        "x": 100,
        "y": 50,
        "width": 50,
        "height": 50,
    }


def test_locators_should_respect_first_and_last(page: Page) -> None:
    page.set_content(
        """
        <section>
            <div><p>A</p></div>
            <div><p>A</p><p>A</p></div>
            <div><p>A</p><p>A</p><p>A</p></div>
        </section>"""
    )
    assert page.locator("div >> p").count() == 6
    assert page.locator("div").locator("p").count() == 6
    assert page.locator("div").first.locator("p").count() == 1
    assert page.locator("div").last.locator("p").count() == 3


def test_locators_should_respect_nth(page: Page) -> None:
    page.set_content(
        """
    <section>
        <div><p>A</p></div>
        <div><p>A</p><p>A</p></div>
        <div><p>A</p><p>A</p><p>A</p></div>
    </section>"""
    )
    assert page.locator("div >> p").nth(0).count() == 1
    assert page.locator("div").nth(1).locator("p").count() == 2
    assert page.locator("div").nth(2).locator("p").count() == 3


def test_locators_should_throw_on_capture_without_nth(page: Page) -> None:
    page.set_content(
        """
        <section><div><p>A</p></div></section>
    """
    )
    with pytest.raises(Error, match="Can't query n-th element"):
        page.locator("*css=div >> p").nth(1).click()


def test_locators_should_throw_due_to_strictness(page: Page) -> None:
    page.set_content(
        """
        <div>A</div><div>B</div>
    """
    )
    with pytest.raises(Error, match="strict mode violation"):
        page.locator("div").is_visible()


def test_locators_should_throw_due_to_strictness_2(page: Page) -> None:
    page.set_content(
        """
        <select><option>One</option><option>Two</option></select>
    """
    )
    with pytest.raises(Error, match="strict mode violation"):
        page.locator("option").evaluate("e => {}")


def test_locators_set_checked(page: Page) -> None:
    page.set_content("`<input id='checkbox' type='checkbox'></input>`")
    locator = page.locator("input")
    locator.set_checked(True)
    assert page.evaluate("checkbox.checked")
    locator.set_checked(False)
    assert page.evaluate("checkbox.checked") is False


def route_iframe(page: Page) -> None:
    page.route(
        "**/empty.html",
        lambda route: route.fulfill(
            body='<iframe src="iframe.html"></iframe>', content_type="text/html"
        ),
    )
    page.route(
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
    page.route(
        "**/iframe-2.html",
        lambda route: route.fulfill(
            body="<html><button>Hello nested iframe</button></html>",
            content_type="text/html",
        ),
    )


def test_locators_frame_should_work_with_iframe(page: Page, server: Server) -> None:
    route_iframe(page)
    page.goto(server.EMPTY_PAGE)
    button = page.frame_locator("iframe").locator("button")
    button.wait_for()
    assert button.inner_text() == "Hello iframe"
    button.click()
    assert (
        repr(page.frame_locator("iframe"))
        == f"<FrameLocator frame=<Frame name= url='{server.PREFIX}/empty.html'> selector='iframe'>"
    )


def test_locators_frame_should_work_for_nested_iframe(
    page: Page, server: Server
) -> None:
    route_iframe(page)
    page.goto(server.EMPTY_PAGE)
    button = page.frame_locator("iframe").frame_locator("iframe").locator("button")
    button.wait_for()
    assert button.inner_text() == "Hello nested iframe"
    button.click()


def test_locators_frame_should_work_with_locator_frame_locator(
    page: Page, server: Server
) -> None:
    route_iframe(page)
    page.goto(server.EMPTY_PAGE)
    button = page.locator("body").frame_locator("iframe").locator("button")
    button.wait_for()
    assert button.inner_text() == "Hello iframe"
    button.click()


def route_ambiguous(page: Page) -> None:
    page.route(
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
    page.route(
        "**/iframe-*",
        lambda route: route.fulfill(
            body=f"<html><button>Hello from {urlparse(route.request.url).path[1:]}</button></html>",
            content_type="text/html",
        ),
    )


def test_locator_frame_locator_should_throw_on_ambiguity(
    page: Page, server: Server
) -> None:
    route_ambiguous(page)
    page.goto(server.EMPTY_PAGE)
    button = page.locator("body").frame_locator("iframe").locator("button")
    with pytest.raises(
        Error,
        match='.*strict mode violation: "body >> iframe" resolved to 3 elements.*',
    ):
        button.wait_for()


def test_locator_frame_locator_should_not_throw_on_first_last_nth(
    page: Page, server: Server
) -> None:
    route_ambiguous(page)
    page.goto(server.EMPTY_PAGE)
    button1 = page.locator("body").frame_locator("iframe").first.locator("button")
    assert button1.text_content() == "Hello from iframe-1.html"
    button2 = page.locator("body").frame_locator("iframe").nth(1).locator("button")
    assert button2.text_content() == "Hello from iframe-2.html"
    button3 = page.locator("body").frame_locator("iframe").last.locator("button")
    assert button3.text_content() == "Hello from iframe-3.html"
