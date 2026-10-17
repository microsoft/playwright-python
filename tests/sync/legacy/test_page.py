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

import threading
from typing import Callable, Dict, List

import pytest

from playwright.sync_api import Error, Page, sync_playwright
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


def run_outside_test_mode(
    monkeypatch: pytest.MonkeyPatch,
    browser_name: str,
    launch_arguments: Dict,
    body: Callable[[Page], None],
) -> None:
    """Runs body with a page from a driver that does not run in upstream's test mode.

    In test mode (PWTEST_UNDER_TEST=1, set by tests/conftest.py) the driver enables
    the debugger, so page.pause() waits even when the browser is headless. A second
    sync Playwright must run on its own thread.
    """
    monkeypatch.delenv("PWTEST_UNDER_TEST", raising=False)
    errors: List[BaseException] = []

    def run() -> None:
        try:
            with sync_playwright() as playwright:
                browser = playwright[browser_name].launch(**launch_arguments)
                try:
                    body(browser.new_page())
                finally:
                    browser.close()
        except BaseException as error:
            errors.append(error)

    thread = threading.Thread(target=run)
    thread.start()
    thread.join()
    if errors:
        raise errors[0]


def test_page_pause_should_reset_default_timeouts(
    monkeypatch: pytest.MonkeyPatch,
    browser_name: str,
    launch_arguments: Dict,
    headless: bool,
    server: Server,
) -> None:
    if not headless:
        pytest.skip()

    def body(page: Page) -> None:
        page.goto(server.EMPTY_PAGE)
        page.pause()
        with pytest.raises(Error, match="Timeout 30000ms exceeded."):
            page.get_by_text("foo").click()

    run_outside_test_mode(monkeypatch, browser_name, launch_arguments, body)


def test_page_pause_should_reset_custom_timeouts(
    monkeypatch: pytest.MonkeyPatch,
    browser_name: str,
    launch_arguments: Dict,
    headless: bool,
    server: Server,
) -> None:
    if not headless:
        pytest.skip()

    def body(page: Page) -> None:
        page.set_default_timeout(123)
        page.set_default_navigation_timeout(456)
        page.goto(server.EMPTY_PAGE)
        page.pause()
        with pytest.raises(Error, match="Timeout 123ms exceeded."):
            page.get_by_text("foo").click()

        server.set_route("/empty.html", lambda route: None)
        with pytest.raises(Error, match="Timeout 456ms exceeded."):
            page.goto(server.EMPTY_PAGE)

    run_outside_test_mode(monkeypatch, browser_name, launch_arguments, body)


def test_page_should_ignore_deprecated_is_hidden_and_visible_timeout(
    page: Page,
) -> None:
    page.set_content("<div>foo</div>")
    assert page.is_hidden("div", timeout=10) is False
    assert page.is_visible("div", timeout=10) is True


def test_content_should_include_shadow_roots(page: Page) -> None:
    html = '<!DOCTYPE html><html lang="en"><head></head><body><div id="host"><template shadowrootmode="open"><div id="nested"><template shadowrootmode="open"><span>nested</span></template><slot></slot></div></template><span>light</span></div><div id="closed"></div></body></html>'
    # Closed shadow roots are not accessible from script and are never serialized.
    page.set_content(
        html.replace(
            '<div id="closed">',
            '<div id="closed"><template shadowrootmode="closed"><span>closed</span></template>',
        )
    )
    assert (
        page.content()
        == '<!DOCTYPE html><html lang="en"><head></head><body><div id="host"><span>light</span></div><div id="closed"></div></body></html>'
    )
    assert page.content(include_shadow=True) == html
    assert page.main_frame.content(include_shadow=True) == html
