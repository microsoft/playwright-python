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

import pytest

from playwright.sync_api import Error, Page
from tests.server import Server


def test_input_value(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/textarea.html")

    page.fill("input", "my-text-content")
    assert page.input_value("input") == "my-text-content"

    page.fill("input", "")
    assert page.input_value("input") == ""


def test_drag_and_drop_helper_method(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/drag-n-drop.html")
    page.drag_and_drop("#source", "#target")
    assert (
        page.eval_on_selector(
            "#target", "target => target.contains(document.querySelector('#source'))"
        )
        is True
    )


def test_should_check_box_using_set_checked(page: Page) -> None:
    page.set_content("`<input id='checkbox' type='checkbox'></input>`")
    page.set_checked("input", True)
    assert page.evaluate("checkbox.checked") is True
    page.set_checked("input", False)
    assert page.evaluate("checkbox.checked") is False


def test_should_set_bodysize_and_headersize(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    with page.expect_request("*/**") as request_info:
        page.evaluate(
            "() => fetch('./get', { method: 'POST', body: '12345'}).then(r => r.text())"
        )
    request = request_info.value
    sizes = request.sizes()
    assert sizes["requestBodySize"] == 5
    assert sizes["requestHeadersSize"] >= 300


def test_should_set_bodysize_to_0(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    with page.expect_request("*/**") as request_info:
        page.evaluate("() => fetch('./get').then(r => r.text())")

    request = request_info.value
    sizes = request.sizes()
    assert sizes["requestBodySize"] == 0
    assert sizes["requestHeadersSize"] >= 200


def test_sync_stacks_should_work(page: Page, server: Server) -> None:
    page.route("**/empty.html", lambda route: route.abort())
    with pytest.raises(Error) as exc_info:
        page.goto(server.EMPTY_PAGE)
    assert exc_info.value.stack
    assert __file__ in exc_info.value.stack


def test_emitted_for_domcontentloaded_and_load(page: Page, server: Server) -> None:
    with page.expect_event("domcontentloaded") as dom_info:
        with page.expect_event("load") as load_info:
            page.goto(server.EMPTY_PAGE)
    assert isinstance(dom_info.value, Page)
    assert isinstance(load_info.value, Page)


def test_page_pause_should_reset_default_timeouts(
    page: Page, headless: bool, server: Server
) -> None:
    if not headless:
        pytest.skip()

    page.goto(server.EMPTY_PAGE)
    page.pause()
    with pytest.raises(Error, match="Timeout 30000ms exceeded."):
        page.get_by_text("foo").click()


def test_page_pause_should_reset_custom_timeouts(
    page: Page, headless: bool, server: Server
) -> None:
    if not headless:
        pytest.skip()

    page.set_default_timeout(123)
    page.set_default_navigation_timeout(456)
    page.goto(server.EMPTY_PAGE)
    page.pause()
    with pytest.raises(Error, match="Timeout 123ms exceeded."):
        page.get_by_text("foo").click()

    server.set_route("/empty.html", lambda route: None)
    with pytest.raises(Error, match="Timeout 456ms exceeded."):
        page.goto(server.EMPTY_PAGE)
