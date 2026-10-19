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

import asyncio
import traceback
from typing import Optional

import pytest

from playwright.async_api import ElementHandle, Error, Page, TimeoutError, expect
from tests.server import Server

from ..utils import Utils

ADD_ELEMENT = "tag => document.body.appendChild(document.createElement(tag))"


async def test_WA_044_should_survive_cross_process_navigation(
    page: Page, server: Server
) -> None:
    box_found = False

    async def wait_for_selector() -> None:
        nonlocal box_found
        await page.wait_for_selector(".box")
        box_found = True

    async def navigate() -> None:
        await page.goto(server.EMPTY_PAGE)
        assert box_found is False
        await page.reload()
        assert box_found is False
        await page.goto(server.CROSS_PROCESS_PREFIX + "/grid.html")

    await asyncio.gather(wait_for_selector(), navigate())
    assert box_found is True


async def test_WA_045_should_wait_for_visible(page: Page, server: Server) -> None:
    div_found = False

    async def wait_for_selector() -> None:
        nonlocal div_found
        await page.wait_for_selector("div")
        div_found = True

    async def show() -> None:
        await page.set_content(
            "<div style='display: none; visibility: hidden;'>1</div>"
        )
        assert div_found is False
        await page.evaluate(
            "() => document.querySelector('div').style.removeProperty('display')"
        )
        assert div_found is False
        await page.evaluate(
            "() => document.querySelector('div').style.removeProperty('visibility')"
        )

    await asyncio.gather(wait_for_selector(), show())
    assert div_found is True


async def test_WA_046_should_not_consider_visible_when_zero_sized(
    page: Page, server: Server
) -> None:
    await page.set_content("<div style='width: 0; height: 0;'>1</div>")
    with pytest.raises(Error) as exc_info:
        await page.wait_for_selector("div", timeout=1000)
    assert "Page.wait_for_selector: Timeout 1000ms exceeded" in exc_info.value.message
    await page.evaluate("() => document.querySelector('div').style.width = '10px'")
    with pytest.raises(Error) as exc_info:
        await page.wait_for_selector("div", timeout=1000)
    assert "Page.wait_for_selector: Timeout 1000ms exceeded" in exc_info.value.message
    await page.evaluate("() => document.querySelector('div').style.height = '10px'")
    assert await page.wait_for_selector("div", timeout=1000)


async def test_WA_047_should_wait_for_visible_recursively(
    page: Page, server: Server
) -> None:
    div_visible = False

    async def wait_for_selector() -> None:
        nonlocal div_visible
        await page.wait_for_selector("div#inner")
        div_visible = True

    async def show() -> None:
        await page.set_content(
            "<div style='display: none; visibility: hidden;'><div id=\"inner\">hi</div></div>"
        )
        assert div_visible is False
        await page.evaluate(
            "() => document.querySelector('div').style.removeProperty('display')"
        )
        assert div_visible is False
        await page.evaluate(
            "() => document.querySelector('div').style.removeProperty('visibility')"
        )

    await asyncio.gather(wait_for_selector(), show())
    assert div_visible is True


async def test_WA_048_should_consider_outside_of_viewport_visible(
    page: Page,
) -> None:
    await page.set_content(
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
    await cover.wait_for(state="visible")
    await expect(cover).to_be_visible()


async def test_WA_049_hidden_should_wait_for_hidden(page: Page, server: Server) -> None:
    div_hidden = False
    await page.set_content("<div style='display: block;'>content</div>")

    async def wait_for_selector() -> None:
        nonlocal div_hidden
        await page.wait_for_selector("div", state="hidden")
        div_hidden = True

    async def hide() -> None:
        await page.wait_for_selector("div")  # do a round trip
        assert div_hidden is False
        await page.evaluate(
            "() => document.querySelector('div').style.setProperty('visibility', 'hidden')"
        )

    await asyncio.gather(wait_for_selector(), hide())
    assert div_hidden is True


async def test_WA_050_hidden_should_wait_for_display_none(
    page: Page, server: Server
) -> None:
    div_hidden = False
    await page.set_content("<div style='display: block;'>content</div>")

    async def wait_for_selector() -> None:
        nonlocal div_hidden
        await page.wait_for_selector("div", state="hidden")
        div_hidden = True

    async def hide() -> None:
        await page.wait_for_selector("div")  # do a round trip
        assert div_hidden is False
        await page.evaluate(
            "() => document.querySelector('div').style.setProperty('display', 'none')"
        )

    await asyncio.gather(wait_for_selector(), hide())
    assert div_hidden is True


async def test_WA_051_hidden_should_wait_for_removal(
    page: Page, server: Server
) -> None:
    await page.set_content("<div>content</div>")
    div_removed = False

    async def wait_for_selector() -> None:
        nonlocal div_removed
        await page.wait_for_selector("div", state="hidden")
        div_removed = True

    async def remove() -> None:
        await page.wait_for_selector("div")  # do a round trip
        assert div_removed is False
        await page.evaluate("() => document.querySelector('div').remove()")

    await asyncio.gather(wait_for_selector(), remove())
    assert div_removed is True


async def test_WA_052_should_return_null_if_waiting_to_hide_non_existing_element(
    page: Page, server: Server
) -> None:
    handle = await page.wait_for_selector("non-existing", state="hidden")
    assert handle is None


async def test_WA_053_should_respect_timeout(page: Page) -> None:
    error: Optional[Error] = None
    try:
        await page.wait_for_selector("div", timeout=3000, state="attached")
    except Error as e:
        error = e
    assert error
    assert "Page.wait_for_selector: Timeout 3000ms exceeded" in error.message
    assert 'waiting for locator("div")' in error.message
    assert isinstance(error, TimeoutError)


async def test_WA_054_should_have_an_error_message_specifically_for_awaiting_an_element_to_be_hidden(
    page: Page, server: Server
) -> None:
    await page.set_content("<div>content</div>")
    error: Optional[Error] = None
    try:
        await page.wait_for_selector("div", state="hidden", timeout=1000)
    except Error as e:
        error = e
    assert error
    assert "Page.wait_for_selector: Timeout 1000ms exceeded" in error.message
    assert 'waiting for locator("div") to be hidden' in error.message


async def test_WA_055_should_respond_to_node_attribute_mutation(
    page: Page, server: Server
) -> None:
    div_found = False

    async def wait_for_selector() -> None:
        nonlocal div_found
        await page.wait_for_selector(".zombo", state="attached")
        div_found = True

    async def mutate() -> None:
        await page.set_content("<div class='notZombo'></div>")
        assert div_found is False
        await page.evaluate("() => document.querySelector('div').className = 'zombo'")

    await asyncio.gather(wait_for_selector(), mutate())
    assert div_found is True


async def test_WA_056_should_return_the_element_handle(
    page: Page, server: Server
) -> None:
    handle, _ = await asyncio.gather(
        page.wait_for_selector(".zombo"),
        page.set_content("<div class='zombo'>anything</div>"),
    )
    assert await page.evaluate("x => x.textContent", handle) == "anything"


async def test_WA_057_should_have_correct_stack_trace_for_timeout(
    page: Page, server: Server
) -> None:
    with pytest.raises(Error) as exc_info:
        await page.wait_for_selector(".zombo", timeout=10)
    # The traceback leads to the call in this file.
    assert any(
        frame.filename == __file__ for frame in traceback.extract_tb(exc_info.tb)
    )


async def test_WA_058_should_throw_for_unknown_state_option(
    page: Page, server: Server
) -> None:
    await page.set_content("<section>test</section>")
    with pytest.raises(Error) as exc_info:
        await page.wait_for_selector("section", state="foo")  # type: ignore[arg-type]
    assert (
        "state: expected one of (attached|detached|visible|hidden)"
        in exc_info.value.message
    )


async def test_WA_060_should_throw_for_true_state_option(
    page: Page, server: Server
) -> None:
    await page.set_content("<section>test</section>")
    with pytest.raises(Error) as exc_info:
        await page.wait_for_selector("section", state=True)  # type: ignore[arg-type]
    assert (
        "state: expected one of (attached|detached|visible|hidden)"
        in exc_info.value.message
    )


async def test_WA_061_should_throw_for_false_state_option(
    page: Page, server: Server
) -> None:
    await page.set_content("<section>test</section>")
    with pytest.raises(Error) as exc_info:
        await page.wait_for_selector("section", state=False)  # type: ignore[arg-type]
    assert (
        "state: expected one of (attached|detached|visible|hidden)"
        in exc_info.value.message
    )


async def test_WA_062_should_support_selector_syntax(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    frame = page.main_frame
    e_handle: Optional[ElementHandle] = None

    async def watchdog() -> None:
        nonlocal e_handle
        e_handle = await frame.wait_for_selector(
            "css=div >> css=span", state="attached"
        )

    async def add_elements() -> None:
        await frame.evaluate(ADD_ELEMENT, "br")
        await frame.evaluate(ADD_ELEMENT, "div")
        await frame.evaluate(
            "() => document.querySelector('div').appendChild(document.createElement('span'))"
        )

    await asyncio.gather(watchdog(), add_elements())
    assert e_handle
    tag_name = await (await e_handle.get_property("tagName")).json_value()
    assert tag_name == "SPAN"


async def test_WA_063_should_wait_for_detached_if_already_detached(
    page: Page, server: Server
) -> None:
    await page.set_content('<section id="testAttribute">43543</section>')
    assert await page.wait_for_selector("css=div", state="detached") is None


async def test_WA_064_should_wait_for_detached(page: Page, server: Server) -> None:
    await page.set_content('<section id="testAttribute"><div>43543</div></section>')
    done = False

    async def wait_for() -> None:
        nonlocal done
        await page.wait_for_selector("css=div", state="detached")
        done = True

    async def remove() -> None:
        assert done is False
        await page.wait_for_selector("css=section")
        assert done is False
        await page.eval_on_selector("div", "div => div.remove()")

    await asyncio.gather(wait_for(), remove())
    assert done is True


async def test_WA_065_should_support_some_fancy_xpath(
    page: Page, server: Server
) -> None:
    await page.set_content("<p>red herring</p><p>hello  world  </p>")
    wait_for_xpath = await page.wait_for_selector(
        '//p[normalize-space(.)="hello world"]'
    )
    assert await page.evaluate("x => x.textContent", wait_for_xpath) == "hello  world  "


async def test_WA_066_should_respect_timeout_xpath(page: Page) -> None:
    error: Optional[Error] = None
    try:
        await page.wait_for_selector("//div", state="attached", timeout=3000)
    except Error as e:
        error = e
    assert error
    assert "Page.wait_for_selector: Timeout 3000ms exceeded" in error.message
    assert 'waiting for locator("//div")' in error.message
    assert isinstance(error, TimeoutError)


async def test_WA_067_should_run_in_specified_frame_xpath(
    page: Page, server: Server, utils: Utils
) -> None:
    await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    await utils.attach_frame(page, "frame2", server.EMPTY_PAGE)
    frame1 = page.frames[1]
    frame2 = page.frames[2]
    e_handle: Optional[ElementHandle] = None

    async def wait_for_xpath() -> None:
        nonlocal e_handle
        e_handle = await frame2.wait_for_selector("//div", state="attached")

    async def add_elements() -> None:
        await frame1.evaluate(ADD_ELEMENT, "div")
        await frame2.evaluate(ADD_ELEMENT, "div")

    await asyncio.gather(wait_for_xpath(), add_elements())
    assert e_handle
    assert await e_handle.owner_frame() == frame2


async def test_WA_068_should_throw_when_frame_is_detached_xpath(
    page: Page, server: Server, utils: Utils
) -> None:
    await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    frame = page.frames[1]
    wait_error: Optional[Error] = None

    async def wait_for_xpath() -> None:
        nonlocal wait_error
        try:
            await frame.wait_for_selector('//*[@class="box"]')
        except Error as e:
            wait_error = e

    async def detach() -> None:
        await utils.detach_frame(page, "frame1")

    await asyncio.gather(wait_for_xpath(), detach())
    assert wait_error
    assert "Frame.wait_for_selector: Frame was detached" in wait_error.message


async def test_WA_069_should_return_the_element_handle_xpath(
    page: Page, server: Server
) -> None:
    handle, _ = await asyncio.gather(
        page.wait_for_selector('//*[@class="zombo"]'),
        page.set_content("<div class='zombo'>anything</div>"),
    )
    assert await page.evaluate("x => x.textContent", handle) == "anything"


async def test_WA_070_should_allow_you_to_select_an_element_with_single_slash_xpath(
    page: Page, server: Server
) -> None:
    await page.set_content("<div>some text</div>")
    wait_for_xpath = await page.wait_for_selector("//html/body/div")
    assert await page.evaluate("x => x.textContent", wait_for_xpath) == "some text"


async def test_WA_071_should_correctly_handle_hidden_shadow_host(
    page: Page, server: Server
) -> None:
    await page.set_content(
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
    assert await page.text_content("div") == "Find me"
    await page.wait_for_selector("div", state="hidden")


async def test_WA_074_should_fail_if_element_handle_was_detached_while_waiting(
    page: Page, server: Server
) -> None:
    await page.set_content("<button>hello</button>")
    button = await page.query_selector("button")
    assert button
    error: Optional[Error] = None

    async def wait_for_selector() -> None:
        nonlocal error
        try:
            await button.wait_for_selector("something")
        except Error as e:
            error = e

    async def detach() -> None:
        await page.wait_for_timeout(100)
        await page.evaluate("() => document.body.innerText = ''")

    await asyncio.gather(wait_for_selector(), detach())
    assert error
    assert "Element is not attached to the DOM" in error.message


async def test_WA_075_should_succeed_if_element_handle_was_detached_while_waiting_for_hidden(
    page: Page, server: Server
) -> None:
    await page.set_content("<button>hello</button>")
    button = await page.query_selector("button")
    assert button

    async def wait_for_selector() -> None:
        await button.wait_for_selector("something", state="hidden")

    async def detach() -> None:
        await page.wait_for_timeout(1000)
        await page.evaluate("() => document.body.innerText = ''")

    await asyncio.gather(wait_for_selector(), detach())


async def test_WA_076_should_succeed_if_element_handle_was_detached_while_waiting_for_detached(
    page: Page, server: Server
) -> None:
    await page.set_content("<button>hello</button>")
    button = await page.query_selector("button")
    assert button

    async def wait_for_selector() -> None:
        await button.wait_for_selector("something", state="detached")

    async def detach() -> None:
        await page.wait_for_timeout(1000)
        await page.evaluate("() => document.body.innerText = ''")

    await asyncio.gather(wait_for_selector(), detach())
