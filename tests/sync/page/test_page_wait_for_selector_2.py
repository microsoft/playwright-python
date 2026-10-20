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

"""Port of tests/page/page-wait-for-selector-2.spec.ts."""

import traceback
from typing import Any, Callable, List, Optional

import pytest

from playwright.sync_api import ElementHandle, Error, Page, TimeoutError, expect
from tests.server import Server

from ..utils import Utils

ADD_ELEMENT = "tag => document.body.appendChild(document.createElement(tag))"


def test_WA_044_should_survive_cross_process_navigation(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    box_found = False

    def wait_for_selector() -> None:
        nonlocal box_found
        page.wait_for_selector(".box")
        box_found = True

    def navigate() -> None:
        page.goto(server.EMPTY_PAGE)
        assert box_found is False
        page.reload()
        assert box_found is False
        page.goto(server.CROSS_PROCESS_PREFIX + "/grid.html")

    sync_gather(wait_for_selector, navigate)
    assert box_found is True


def test_WA_045_should_wait_for_visible(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    div_found = False

    def wait_for_selector() -> None:
        nonlocal div_found
        page.wait_for_selector("div")
        div_found = True

    def show() -> None:
        page.set_content("<div style='display: none; visibility: hidden;'>1</div>")
        assert div_found is False
        page.evaluate(
            "() => document.querySelector('div').style.removeProperty('display')"
        )
        assert div_found is False
        page.evaluate(
            "() => document.querySelector('div').style.removeProperty('visibility')"
        )

    sync_gather(wait_for_selector, show)
    assert div_found is True


def test_WA_046_should_not_consider_visible_when_zero_sized(
    page: Page, server: Server
) -> None:
    page.set_content("<div style='width: 0; height: 0;'>1</div>")
    with pytest.raises(Error) as exc_info:
        page.wait_for_selector("div", timeout=1000)
    assert "Page.wait_for_selector: Timeout 1000ms exceeded" in exc_info.value.message
    page.evaluate("() => document.querySelector('div').style.width = '10px'")
    with pytest.raises(Error) as exc_info:
        page.wait_for_selector("div", timeout=1000)
    assert "Page.wait_for_selector: Timeout 1000ms exceeded" in exc_info.value.message
    page.evaluate("() => document.querySelector('div').style.height = '10px'")
    assert page.wait_for_selector("div", timeout=1000)


def test_WA_047_should_wait_for_visible_recursively(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    div_visible = False

    def wait_for_selector() -> None:
        nonlocal div_visible
        page.wait_for_selector("div#inner")
        div_visible = True

    def show() -> None:
        page.set_content(
            "<div style='display: none; visibility: hidden;'><div id=\"inner\">hi</div></div>"
        )
        assert div_visible is False
        page.evaluate(
            "() => document.querySelector('div').style.removeProperty('display')"
        )
        assert div_visible is False
        page.evaluate(
            "() => document.querySelector('div').style.removeProperty('visibility')"
        )

    sync_gather(wait_for_selector, show)
    assert div_visible is True


def test_WA_048_should_consider_outside_of_viewport_visible(
    page: Page,
) -> None:
    page.set_content(
        """
    <style>
      .cover {
        position: fixed;
        left: 0;
        top: 0;
        width: 100px;
        height: 100px;
        background-color: red;
        transform: translateX(-200px);
      }
    </style>
    <div class="cover">cover</div>
  """
    )

    cover = page.locator(".cover")
    cover.wait_for(state="visible")
    expect(cover).to_be_visible()


def test_WA_049_hidden_should_wait_for_hidden(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    div_hidden = False
    page.set_content("<div style='display: block;'>content</div>")

    def wait_for_selector() -> None:
        nonlocal div_hidden
        page.wait_for_selector("div", state="hidden")
        div_hidden = True

    def hide() -> None:
        page.wait_for_selector("div")  # do a round trip
        assert div_hidden is False
        page.evaluate(
            "() => document.querySelector('div').style.setProperty('visibility', 'hidden')"
        )

    sync_gather(wait_for_selector, hide)
    assert div_hidden is True


def test_WA_050_hidden_should_wait_for_display_none(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    div_hidden = False
    page.set_content("<div style='display: block;'>content</div>")

    def wait_for_selector() -> None:
        nonlocal div_hidden
        page.wait_for_selector("div", state="hidden")
        div_hidden = True

    def hide() -> None:
        page.wait_for_selector("div")  # do a round trip
        assert div_hidden is False
        page.evaluate(
            "() => document.querySelector('div').style.setProperty('display', 'none')"
        )

    sync_gather(wait_for_selector, hide)
    assert div_hidden is True


def test_WA_051_hidden_should_wait_for_removal(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_content("<div>content</div>")
    div_removed = False

    def wait_for_selector() -> None:
        nonlocal div_removed
        page.wait_for_selector("div", state="hidden")
        div_removed = True

    def remove() -> None:
        page.wait_for_selector("div")  # do a round trip
        assert div_removed is False
        page.evaluate("() => document.querySelector('div').remove()")

    sync_gather(wait_for_selector, remove)
    assert div_removed is True


def test_WA_052_should_return_null_if_waiting_to_hide_non_existing_element(
    page: Page, server: Server
) -> None:
    handle = page.wait_for_selector("non-existing", state="hidden")
    assert handle is None


def test_WA_053_should_respect_timeout(page: Page) -> None:
    error: Optional[Error] = None
    try:
        page.wait_for_selector("div", timeout=3000, state="attached")
    except Error as e:
        error = e
    assert error
    assert "Page.wait_for_selector: Timeout 3000ms exceeded" in error.message
    assert 'waiting for locator("div")' in error.message
    assert isinstance(error, TimeoutError)


def test_WA_054_should_have_an_error_message_specifically_for_awaiting_an_element_to_be_hidden(
    page: Page, server: Server
) -> None:
    page.set_content("<div>content</div>")
    error: Optional[Error] = None
    try:
        page.wait_for_selector("div", state="hidden", timeout=1000)
    except Error as e:
        error = e
    assert error
    assert "Page.wait_for_selector: Timeout 1000ms exceeded" in error.message
    assert 'waiting for locator("div") to be hidden' in error.message


def test_WA_055_should_respond_to_node_attribute_mutation(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    div_found = False

    def wait_for_selector() -> None:
        nonlocal div_found
        page.wait_for_selector(".zombo", state="attached")
        div_found = True

    def mutate() -> None:
        page.set_content("<div class='notZombo'></div>")
        assert div_found is False
        page.evaluate("() => document.querySelector('div').className = 'zombo'")

    sync_gather(wait_for_selector, mutate)
    assert div_found is True


def test_WA_056_should_return_the_element_handle(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    handle, _ = sync_gather(
        lambda: page.wait_for_selector(".zombo"),
        lambda: page.set_content("<div class='zombo'>anything</div>"),
    )
    assert page.evaluate("x => x.textContent", handle) == "anything"


def test_WA_057_should_have_correct_stack_trace_for_timeout(
    page: Page, server: Server
) -> None:
    with pytest.raises(Error) as exc_info:
        page.wait_for_selector(".zombo", timeout=10)
    # The traceback leads to the call in this file.
    assert any(
        frame.filename == __file__ for frame in traceback.extract_tb(exc_info.tb)
    )


def test_WA_058_should_throw_for_unknown_state_option(
    page: Page, server: Server
) -> None:
    page.set_content("<section>test</section>")
    with pytest.raises(Error) as exc_info:
        page.wait_for_selector("section", state="foo")  # type: ignore[arg-type]
    assert (
        "state: expected one of (attached|detached|visible|hidden)"
        in exc_info.value.message
    )


def test_WA_060_should_throw_for_true_state_option(page: Page, server: Server) -> None:
    page.set_content("<section>test</section>")
    with pytest.raises(Error) as exc_info:
        page.wait_for_selector("section", state=True)  # type: ignore[arg-type]
    assert (
        "state: expected one of (attached|detached|visible|hidden)"
        in exc_info.value.message
    )


def test_WA_061_should_throw_for_false_state_option(page: Page, server: Server) -> None:
    page.set_content("<section>test</section>")
    with pytest.raises(Error) as exc_info:
        page.wait_for_selector("section", state=False)  # type: ignore[arg-type]
    assert (
        "state: expected one of (attached|detached|visible|hidden)"
        in exc_info.value.message
    )


def test_WA_062_should_support_selector_syntax(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    page.goto(server.EMPTY_PAGE)
    frame = page.main_frame
    e_handle: Optional[ElementHandle] = None

    def watchdog() -> None:
        nonlocal e_handle
        e_handle = frame.wait_for_selector("css=div >> css=span", state="attached")

    def add_elements() -> None:
        frame.evaluate(ADD_ELEMENT, "br")
        frame.evaluate(ADD_ELEMENT, "div")
        frame.evaluate(
            "() => document.querySelector('div').appendChild(document.createElement('span'))"
        )

    sync_gather(watchdog, add_elements)
    assert e_handle
    tag_name = (e_handle.get_property("tagName")).json_value()
    assert tag_name == "SPAN"


def test_WA_063_should_wait_for_detached_if_already_detached(
    page: Page, server: Server
) -> None:
    page.set_content('<section id="testAttribute">43543</section>')
    assert page.wait_for_selector("css=div", state="detached") is None


def test_WA_064_should_wait_for_detached(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_content('<section id="testAttribute"><div>43543</div></section>')
    done = False

    def wait_for() -> None:
        nonlocal done
        page.wait_for_selector("css=div", state="detached")
        done = True

    def remove() -> None:
        assert done is False
        page.wait_for_selector("css=section")
        assert done is False
        page.eval_on_selector("div", "div => div.remove()")

    sync_gather(wait_for, remove)
    assert done is True


def test_WA_065_should_support_some_fancy_xpath(page: Page, server: Server) -> None:
    page.set_content("<p>red herring</p><p>hello  world  </p>")
    wait_for_xpath = page.wait_for_selector('//p[normalize-space(.)="hello world"]')
    assert page.evaluate("x => x.textContent", wait_for_xpath) == "hello  world  "


def test_WA_066_should_respect_timeout_xpath(page: Page) -> None:
    error: Optional[Error] = None
    try:
        page.wait_for_selector("//div", state="attached", timeout=3000)
    except Error as e:
        error = e
    assert error
    assert "Page.wait_for_selector: Timeout 3000ms exceeded" in error.message
    assert 'waiting for locator("//div")' in error.message
    assert isinstance(error, TimeoutError)


def test_WA_067_should_run_in_specified_frame_xpath(
    page: Page, server: Server, utils: Utils, sync_gather: Callable[..., List[Any]]
) -> None:
    utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    utils.attach_frame(page, "frame2", server.EMPTY_PAGE)
    frame1 = page.frames[1]
    frame2 = page.frames[2]
    e_handle: Optional[ElementHandle] = None

    def wait_for_xpath() -> None:
        nonlocal e_handle
        e_handle = frame2.wait_for_selector("//div", state="attached")

    def add_elements() -> None:
        frame1.evaluate(ADD_ELEMENT, "div")
        frame2.evaluate(ADD_ELEMENT, "div")

    sync_gather(wait_for_xpath, add_elements)
    assert e_handle
    assert e_handle.owner_frame() == frame2


def test_WA_068_should_throw_when_frame_is_detached_xpath(
    page: Page, server: Server, utils: Utils, sync_gather: Callable[..., List[Any]]
) -> None:
    utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    frame = page.frames[1]
    wait_error: Optional[Error] = None

    def wait_for_xpath() -> None:
        nonlocal wait_error
        try:
            frame.wait_for_selector('//*[@class="box"]')
        except Error as e:
            wait_error = e

    def detach() -> None:
        utils.detach_frame(page, "frame1")

    sync_gather(wait_for_xpath, detach)
    assert wait_error
    assert "Frame.wait_for_selector: Frame was detached" in wait_error.message


def test_WA_069_should_return_the_element_handle_xpath(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    handle, _ = sync_gather(
        lambda: page.wait_for_selector('//*[@class="zombo"]'),
        lambda: page.set_content("<div class='zombo'>anything</div>"),
    )
    assert page.evaluate("x => x.textContent", handle) == "anything"


def test_WA_070_should_allow_you_to_select_an_element_with_single_slash_xpath(
    page: Page, server: Server
) -> None:
    page.set_content("<div>some text</div>")
    wait_for_xpath = page.wait_for_selector("//html/body/div")
    assert page.evaluate("x => x.textContent", wait_for_xpath) == "some text"


def test_WA_071_should_correctly_handle_hidden_shadow_host(
    page: Page, server: Server
) -> None:
    page.set_content(
        """
    <x-host hidden></x-host>
    <script>
      const host = document.querySelector('x-host');
      const root = host.attachShadow({ mode: 'open' });
      const style = document.createElement('style');
      style.textContent = ':host([hidden]) { display: none; }';
      root.appendChild(style);
      const child = document.createElement('div');
      child.textContent = 'Find me';
      root.appendChild(child);
    </script>
  """
    )
    assert page.text_content("div") == "Find me"
    page.wait_for_selector("div", state="hidden")


def test_WA_074_should_fail_if_element_handle_was_detached_while_waiting(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_content("<button>hello</button>")
    button = page.query_selector("button")
    assert button
    error: Optional[Error] = None

    def wait_for_selector() -> None:
        nonlocal error
        try:
            button.wait_for_selector("something")
        except Error as e:
            error = e

    def detach() -> None:
        page.wait_for_timeout(100)
        page.evaluate("() => document.body.innerText = ''")

    sync_gather(wait_for_selector, detach)
    assert error
    assert "Element is not attached to the DOM" in error.message


def test_WA_075_should_succeed_if_element_handle_was_detached_while_waiting_for_hidden(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_content("<button>hello</button>")
    button = page.query_selector("button")
    assert button

    def wait_for_selector() -> None:
        button.wait_for_selector("something", state="hidden")

    def detach() -> None:
        page.wait_for_timeout(1000)
        page.evaluate("() => document.body.innerText = ''")

    sync_gather(wait_for_selector, detach)


def test_WA_076_should_succeed_if_element_handle_was_detached_while_waiting_for_detached(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_content("<button>hello</button>")
    button = page.query_selector("button")
    assert button

    def wait_for_selector() -> None:
        button.wait_for_selector("something", state="detached")

    def detach() -> None:
        page.wait_for_timeout(1000)
        page.evaluate("() => document.body.innerText = ''")

    sync_gather(wait_for_selector, detach)
