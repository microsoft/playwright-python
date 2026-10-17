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

"""Port of tests/page/page-event-popup.spec.ts."""


from typing import Any, Callable, List

from playwright.sync_api import Page
from tests.server import Server


def test_PO_001_should_work_smoke(page: Page) -> None:
    with page.expect_popup() as popup_info:
        page.evaluate("() => window['__popup'] = window.open('about:blank')")
    popup = popup_info.value
    assert page.evaluate("() => !!window.opener") is False
    assert popup.evaluate("() => !!window.opener") is True


def test_PO_002_should_work_with_window_features(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    with page.expect_popup() as popup_info:
        page.evaluate(
            "() => window['__popup'] = window.open(window.location.href, 'Title', 'toolbar=no,location=no,directories=no,status=no,menubar=no,scrollbars=yes,resizable=yes,width=780,height=200,top=0,left=0')"
        )
    popup = popup_info.value
    assert page.evaluate("() => !!window.opener") is False
    assert popup.evaluate("() => !!window.opener") is True


def test_PO_003_should_emit_for_immediately_closed_popups(page: Page) -> None:
    with page.expect_popup() as popup_info:
        page.evaluate(
            """() => {
      const win = window.open('about:blank');
      win.close();
    }"""
        )
    popup = popup_info.value
    assert popup


def test_PO_004_should_emit_for_immediately_closed_popups_2(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    with page.expect_popup() as popup_info:
        page.evaluate(
            """() => {
      const win = window.open(window.location.href);
      win.close();
    }"""
        )
    popup = popup_info.value
    assert popup


def test_PO_005_should_be_able_to_capture_alert(
    page: Page, sync_gather: Callable[..., List[Any]]
) -> None:
    def evaluate() -> None:
        page.evaluate(
            """() => {
      const win = window.open('');
      win.alert('hello');
    }"""
        )

    def capture_alert() -> None:
        with page.expect_popup() as popup_info:
            with page.context.expect_event("dialog") as dialog_info:
                pass
        popup = popup_info.value
        dialog = dialog_info.value
        assert dialog.message == "hello"
        assert dialog.page == popup
        dialog.dismiss()

    sync_gather(evaluate, capture_alert)


def test_PO_006_should_work_with_empty_url(page: Page) -> None:
    with page.expect_popup() as popup_info:
        page.evaluate("() => window['__popup'] = window.open('')")
    popup = popup_info.value
    assert page.evaluate("() => !!window.opener") is False
    assert popup.evaluate("() => !!window.opener") is True


def test_PO_007_should_work_with_noopener_and_no_url(page: Page) -> None:
    with page.expect_popup() as popup_info:
        page.evaluate(
            "() => window['__popup'] = window.open(undefined, null, 'noopener')"
        )
    popup = popup_info.value
    # Chromium reports `about:blank#blocked` here.
    assert popup.url.split("#")[0] == "about:blank"
    assert page.evaluate("() => !!window.opener") is False
    assert popup.evaluate("() => !!window.opener") is False


def test_PO_008_should_work_with_noopener_and_about_blank(page: Page) -> None:
    with page.expect_popup() as popup_info:
        page.evaluate(
            "() => window['__popup'] = window.open('about:blank', null, 'noopener')"
        )
    popup = popup_info.value
    assert page.evaluate("() => !!window.opener") is False
    assert popup.evaluate("() => !!window.opener") is False


def test_PO_009_should_work_with_noopener_and_url(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    with page.expect_popup() as popup_info:
        page.evaluate(
            "url => window['__popup'] = window.open(url, null, 'noopener')",
            server.EMPTY_PAGE,
        )
    popup = popup_info.value
    assert page.evaluate("() => !!window.opener") is False
    assert popup.evaluate("() => !!window.opener") is False


def test_PO_010_should_work_with_clicking_target_blank(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content('<a target=_blank rel="opener" href="/one-style.html">yo</a>')
    with page.expect_popup() as popup_info:
        page.click("a")
    popup = popup_info.value
    assert page.evaluate("() => !!window.opener") is False
    assert popup.evaluate("() => !!window.opener") is True
    assert popup.main_frame.page == popup


def test_PO_011_should_work_with_fake_clicking_target_blank_and_rel_noopener(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content('<a target=_blank rel=noopener href="/one-style.html">yo</a>')
    with page.expect_popup() as popup_info:
        page.eval_on_selector("a", "a => a.click()")
    popup = popup_info.value
    assert page.evaluate("() => !!window.opener") is False
    assert popup.evaluate("() => !!window.opener") is False


def test_PO_012_should_work_with_clicking_target_blank_and_rel_noopener(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content('<a target=_blank rel=noopener href="/one-style.html">yo</a>')
    with page.expect_popup() as popup_info:
        page.click("a")
    popup = popup_info.value
    assert page.evaluate("() => !!window.opener") is False
    assert popup.evaluate("() => !!window.opener") is False


def test_PO_013_should_report_popup_opened_from_iframes(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/frames/two-frames.html")
    frame = page.frames[1]
    assert frame
    with page.expect_popup() as popup_info:
        frame.evaluate("() => window.open('')")
    popup = popup_info.value
    assert popup
