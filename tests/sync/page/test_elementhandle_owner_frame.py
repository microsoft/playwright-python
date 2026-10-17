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

"""Port of tests/page/elementhandle-owner-frame.spec.ts."""

from playwright.sync_api import Page
from tests.server import Server

from ..utils import Utils


def test_EH_055_should_work(page: Page, server: Server, utils: Utils) -> None:
    page.goto(server.EMPTY_PAGE)
    utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    frame = page.frames[1]
    element_handle = (frame.evaluate_handle("() => document.body")).as_element()
    assert element_handle
    assert element_handle.owner_frame() == frame


def test_EH_056_should_work_for_cross_process_iframes(
    page: Page, server: Server, utils: Utils
) -> None:
    page.goto(server.EMPTY_PAGE)
    utils.attach_frame(page, "frame1", server.CROSS_PROCESS_PREFIX + "/empty.html")
    frame = page.frames[1]
    element_handle = (frame.evaluate_handle("() => document.body")).as_element()
    assert element_handle
    assert element_handle.owner_frame() == frame


def test_EH_057_should_work_for_document(
    page: Page, server: Server, utils: Utils
) -> None:
    page.goto(server.EMPTY_PAGE)
    utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    frame = page.frames[1]
    element_handle = (frame.evaluate_handle("() => document")).as_element()
    assert element_handle
    assert element_handle.owner_frame() == frame


def test_EH_058_should_work_for_iframe_elements(
    page: Page, server: Server, utils: Utils
) -> None:
    page.goto(server.EMPTY_PAGE)
    utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    frame = page.main_frame
    element_handle = (
        frame.evaluate_handle("() => document.querySelector('#frame1')")
    ).as_element()
    assert element_handle
    assert element_handle.owner_frame() == frame


def test_EH_059_should_work_for_cross_frame_evaluations(
    page: Page, server: Server, utils: Utils
) -> None:
    page.goto(server.EMPTY_PAGE)
    utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    frame = page.main_frame
    element_handle = (
        frame.evaluate_handle(
            "() => document.querySelector('iframe').contentWindow.document.body"
        )
    ).as_element()
    assert element_handle
    assert element_handle.owner_frame() == frame.child_frames[0]


def test_EH_060_should_work_for_detached_elements(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    div_handle = (
        page.evaluate_handle(
            """() => {
    const div = document.createElement('div');
    document.body.appendChild(div);
    return div;
  }"""
        )
    ).as_element()
    assert div_handle
    assert div_handle.owner_frame() == page.main_frame
    page.evaluate(
        """() => {
    const div = document.querySelector('div');
    document.body.removeChild(div);
  }"""
    )
    assert div_handle.owner_frame() == page.main_frame


def test_EH_061_should_work_for_adopted_elements(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    with page.expect_popup() as popup_info:
        page.evaluate("url => window['__popup'] = window.open(url)", server.EMPTY_PAGE)
    popup = popup_info.value
    div_handle = (
        page.evaluate_handle(
            """() => {
    const div = document.createElement('div');
    document.body.appendChild(div);
    return div;
  }"""
        )
    ).as_element()
    assert div_handle
    assert div_handle.owner_frame() == page.main_frame
    popup.wait_for_load_state("domcontentloaded")
    page.evaluate(
        """() => {
    const div = document.querySelector('div');
    window['__popup'].document.body.appendChild(div);
  }"""
    )
    assert div_handle.owner_frame() == popup.main_frame
