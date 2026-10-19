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

"""Port of tests/page/page-wait-for-selector-1.spec.ts."""

import asyncio
from typing import Optional

import pytest

from playwright.async_api import ElementHandle, Error, Frame, Page
from tests.server import Server

from ..utils import Utils

ADD_ELEMENT = "tag => document.body.appendChild(document.createElement(tag))"


async def give_it_time_to_log(frame: Frame, utils: Utils) -> None:
    await utils.rafraf(frame, 2)


async def test_WA_029_should_immediately_resolve_promise_if_node_exists(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    frame = page.main_frame
    await frame.wait_for_selector("*")
    await frame.evaluate(ADD_ELEMENT, "div")
    await frame.wait_for_selector("div", state="attached")


async def test_WA_030_element_handle_wait_for_selector_should_immediately_resolve_if_node_exists(
    page: Page,
) -> None:
    await page.set_content("<span>extra</span><div><span>target</span></div>")
    div = await page.query_selector("div")
    assert div
    span = await div.wait_for_selector("span", state="attached")
    assert span
    assert await span.evaluate("e => e.textContent") == "target"


async def test_WA_031_element_handle_wait_for_selector_should_wait(
    page: Page,
) -> None:
    await page.set_content("<div></div>")
    div = await page.query_selector("div")
    assert div
    span: Optional[ElementHandle] = None

    async def wait_for_selector() -> None:
        nonlocal span
        span = await div.wait_for_selector("span", state="attached")

    async def add_span() -> None:
        await div.evaluate("div => div.innerHTML = '<span>target</span>'")

    await asyncio.gather(wait_for_selector(), add_span())
    assert span
    assert await span.evaluate("e => e.textContent") == "target"


async def test_WA_032_element_handle_wait_for_selector_should_timeout(
    page: Page,
) -> None:
    await page.set_content("<div></div>")
    div = await page.query_selector("div")
    assert div
    with pytest.raises(Error) as exc_info:
        await div.wait_for_selector("span", timeout=100)
    assert "Timeout 100ms exceeded." in exc_info.value.message


async def test_WA_033_element_handle_wait_for_selector_should_throw_on_navigation(
    page: Page, server: Server
) -> None:
    await page.set_content("<div></div>")
    div = await page.query_selector("div")
    assert div
    error: Optional[Error] = None

    async def wait_for_selector() -> None:
        nonlocal error
        try:
            await div.wait_for_selector("span")
        except Error as e:
            error = e

    async def navigate() -> None:
        # Give it some time before navigating.
        for _ in range(10):
            await page.evaluate("() => 1")
        await page.goto(server.EMPTY_PAGE)

    await asyncio.gather(wait_for_selector(), navigate())
    assert error
    assert 'waiting for locator("span") to be visible' in error.message


async def test_WA_034_should_work_with_removed_mutation_observer(page: Page) -> None:
    await page.evaluate("() => delete window.MutationObserver")
    handle, _ = await asyncio.gather(
        page.wait_for_selector(".zombo"),
        page.set_content("<div class='zombo'>anything</div>"),
    )
    assert await page.evaluate("x => x.textContent", handle) == "anything"


async def test_WA_035_should_resolve_promise_when_node_is_added(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    frame = page.main_frame
    e_handle: Optional[ElementHandle] = None

    async def watchdog() -> None:
        nonlocal e_handle
        e_handle = await frame.wait_for_selector("div", state="attached")

    async def add_elements() -> None:
        await frame.evaluate(ADD_ELEMENT, "br")
        await frame.evaluate(ADD_ELEMENT, "div")

    await asyncio.gather(watchdog(), add_elements())
    assert e_handle
    tag_name = await (await e_handle.get_property("tagName")).json_value()
    assert tag_name == "DIV"


async def test_WA_036_should_report_logs_while_waiting_for_visible(
    page: Page, server: Server, utils: Utils
) -> None:
    await page.goto(server.EMPTY_PAGE)
    frame = page.main_frame
    error: Optional[Error] = None

    async def watchdog() -> None:
        nonlocal error
        try:
            await frame.wait_for_selector("div", timeout=5000)
        except Error as e:
            error = e

    async def change_divs() -> None:
        await frame.evaluate(
            """() => {
                const div = document.createElement('div');
                div.className = 'foo bar';
                div.id = 'mydiv';
                div.setAttribute('style', 'display: none');
                div.setAttribute('foo', '123456789012345678901234567890123456789012345678901234567890');
                div.textContent = 'abcdefghijklmnopqrstuvwyxzabcdefghijklmnopqrstuvwyxzabcdefghijklmnopqrstuvwyxz';
                document.body.appendChild(div);
            }"""
        )
        await give_it_time_to_log(frame, utils)

        await frame.evaluate("() => document.querySelector('div').remove()")
        await give_it_time_to_log(frame, utils)

        await frame.evaluate(
            """() => {
                const div = document.createElement('div');
                div.className = 'another';
                div.style.display = 'none';
                document.body.appendChild(div);
            }"""
        )
        await give_it_time_to_log(frame, utils)

    await asyncio.gather(watchdog(), change_divs())
    assert error
    assert "Frame.wait_for_selector: Timeout 5000ms exceeded." in error.message
    assert 'waiting for locator("div") to be visible' in error.message
    assert (
        'locator resolved to hidden <div id="mydiv" class="foo bar" foo="123456789012345678901234567890123456789012345678901234567890">abcdefghijklmnopqrstuvwyxzabcdefghijklmnopqrstuvw…</div>'
        in error.message
    )
    assert 'locator resolved to hidden <div class="another"></div>' in error.message


async def test_WA_037_should_report_logs_while_waiting_for_hidden(
    page: Page, server: Server, utils: Utils
) -> None:
    await page.goto(server.EMPTY_PAGE)
    frame = page.main_frame
    await frame.evaluate(
        """() => {
            const div = document.createElement('div');
            div.className = 'foo bar';
            div.id = 'mydiv';
            div.textContent = 'hello';
            document.body.appendChild(div);
        }"""
    )
    error: Optional[Error] = None

    async def watchdog() -> None:
        nonlocal error
        try:
            await frame.wait_for_selector("div", state="hidden", timeout=5000)
        except Error as e:
            error = e

    async def change_divs() -> None:
        await give_it_time_to_log(frame, utils)

        await frame.evaluate(
            """() => {
                document.querySelector('div').remove();
                const div = document.createElement('div');
                div.className = 'another';
                div.textContent = 'hello';
                document.body.appendChild(div);
            }"""
        )
        await give_it_time_to_log(frame, utils)

    await asyncio.gather(watchdog(), change_divs())
    assert error
    assert "Frame.wait_for_selector: Timeout 5000ms exceeded." in error.message
    assert 'waiting for locator("div") to be hidden' in error.message
    assert (
        'locator resolved to visible <div id="mydiv" class="foo bar">hello</div>'
        in error.message
    )
    assert (
        'locator resolved to visible <div class="another">hello</div>' in error.message
    )


async def test_WA_038_should_report_logs_when_the_selector_resolves_to_multiple_elements(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        """
    <button style="display: none; position: absolute; top: 0px; left: 0px; width: 100%;">Reset</button>
    <button>Reset</button>
  """
    )
    with pytest.raises(Error) as exc_info:
        await page.click("text=Reset", timeout=1000)
    assert (
        "locator resolved to 2 elements. Proceeding with the first one: <button>Reset</button>"
        in str(exc_info.value)
    )


async def test_WA_039_should_resolve_promise_when_node_is_added_in_shadow_dom(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    handle: Optional[ElementHandle] = None

    async def watchdog() -> None:
        nonlocal handle
        handle = await page.wait_for_selector("span")

    async def add_span() -> None:
        await page.evaluate(
            """() => {
                const div = document.createElement('div');
                div.attachShadow({ mode: 'open' });
                document.body.appendChild(div);
            }"""
        )
        await page.wait_for_timeout(100)
        await page.evaluate(
            """() => {
                const span = document.createElement('span');
                span.textContent = 'Hello from shadow';
                document.querySelector('div').shadowRoot.appendChild(span);
            }"""
        )

    await asyncio.gather(watchdog(), add_span())
    assert handle
    assert await handle.evaluate("e => e.textContent") == "Hello from shadow"


async def test_WA_040_should_work_when_node_is_added_through_inner_html(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)

    async def watchdog() -> None:
        await page.wait_for_selector("h3 div", state="attached")

    async def add_elements() -> None:
        await page.evaluate(ADD_ELEMENT, "span")
        await page.evaluate(
            "() => document.querySelector('span').innerHTML = '<h3><div></div></h3>'"
        )

    await asyncio.gather(watchdog(), add_elements())


async def test_WA_041_page_wait_for_selector_is_shortcut_for_main_frame(
    page: Page, server: Server, utils: Utils
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    other_frame = page.frames[1]
    e_handle: Optional[ElementHandle] = None

    async def watchdog() -> None:
        nonlocal e_handle
        e_handle = await page.wait_for_selector("div", state="attached")

    async def add_elements() -> None:
        await other_frame.evaluate(ADD_ELEMENT, "div")
        await page.evaluate(ADD_ELEMENT, "div")

    await asyncio.gather(watchdog(), add_elements())
    assert e_handle
    assert await e_handle.owner_frame() == page.main_frame


async def test_WA_042_should_run_in_specified_frame(
    page: Page, server: Server, utils: Utils
) -> None:
    await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    await utils.attach_frame(page, "frame2", server.EMPTY_PAGE)
    frame1 = page.frames[1]
    frame2 = page.frames[2]
    e_handle: Optional[ElementHandle] = None

    async def wait_for_selector() -> None:
        nonlocal e_handle
        e_handle = await frame2.wait_for_selector("div", state="attached")

    async def add_elements() -> None:
        await frame1.evaluate(ADD_ELEMENT, "div")
        await frame2.evaluate(ADD_ELEMENT, "div")

    await asyncio.gather(wait_for_selector(), add_elements())
    assert e_handle
    assert await e_handle.owner_frame() == frame2


async def test_WA_043_should_throw_when_frame_is_detached(
    page: Page, server: Server, utils: Utils
) -> None:
    await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    frame = page.frames[1]
    wait_error: Optional[Error] = None

    async def wait_for_selector() -> None:
        nonlocal wait_error
        try:
            await frame.wait_for_selector(".box")
        except Error as e:
            wait_error = e

    async def detach() -> None:
        await utils.detach_frame(page, "frame1")

    await asyncio.gather(wait_for_selector(), detach())
    assert wait_error
    assert "Frame.wait_for_selector: Frame was detached" in wait_error.message
