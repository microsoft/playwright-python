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

"""Port of tests/page/page-focus.spec.ts."""

import pytest

from playwright.sync_api import Page, expect
from tests.server import Server, TestServerRequest


def _frame_route(server: Server) -> None:
    def handler(request: TestServerRequest) -> None:
        request.setHeader("content-type", "text/html")
        request.write(b"<input id=inner>")
        request.finish()

    server.set_route("/frame.html", handler)


def _xfail_old_firefox_focus(request: pytest.FixtureRequest, browser_name: str) -> None:
    if browser_name == "firefox":
        request.applymarker(
            pytest.mark.xfail(
                reason="driver: the bundled Firefox (r1560) predates upstream's roll to "
                "r1562 (#43446), which moves focus out of an iframe (#43280)",
                strict=True,
            )
        )


@pytest.mark.skip_browser("firefox")
def test_FO_001_should_work_smoke(page: Page) -> None:
    page.set_content("<div id=d1 tabIndex=0></div>")
    assert page.evaluate("() => document.activeElement.nodeName") == "BODY"
    page.focus("#d1")
    assert page.evaluate("() => document.activeElement.id") == "d1"


def test_FO_002_should_emit_focus_event(page: Page) -> None:
    page.set_content("<div id=d1 tabIndex=0></div>")
    focused = False

    def on_focus() -> None:
        nonlocal focused
        focused = True

    page.expose_function("focusEvent", on_focus)
    page.eval_on_selector(
        "#d1", "d1 => d1.addEventListener('focus', window['focusEvent'])"
    )
    page.focus("#d1")
    assert focused is True


def test_FO_003_should_emit_blur_event(page: Page) -> None:
    page.set_content("<div id=d1 tabIndex=0>DIV1</div><div id=d2 tabIndex=0>DIV2</div>")
    page.focus("#d1")
    focused = False
    blurred = False

    def on_focus() -> None:
        nonlocal focused
        focused = True

    def on_blur() -> None:
        nonlocal blurred
        blurred = True

    page.expose_function("focusEvent", on_focus)
    page.expose_function("blurEvent", on_blur)
    page.eval_on_selector(
        "#d1", "d1 => d1.addEventListener('blur', window['blurEvent'])"
    )
    page.eval_on_selector(
        "#d2", "d2 => d2.addEventListener('focus', window['focusEvent'])"
    )
    page.focus("#d2")
    assert focused is True
    assert blurred is True


def test_FO_004_should_traverse_focus(page: Page) -> None:
    page.set_content('<input id="i1"><input id="i2">')
    focused = False

    def on_focus() -> None:
        nonlocal focused
        focused = True

    page.expose_function("focusEvent", on_focus)
    page.eval_on_selector(
        "#i2", "i2 => i2.addEventListener('focus', window['focusEvent'])"
    )

    page.focus("#i1")
    page.keyboard.type("First")
    page.keyboard.press("Tab")
    page.keyboard.type("Last")

    assert focused is True
    assert page.eval_on_selector("#i1", "e => e.value") == "First"
    assert page.eval_on_selector("#i2", "e => e.value") == "Last"


def test_FO_005_should_traverse_focus_in_all_directions(page: Page) -> None:
    page.set_content('<input value="1"><input value="2"><input value="3">')
    page.keyboard.press("Tab")
    assert page.evaluate("() => document.activeElement.value") == "1"
    page.keyboard.press("Tab")
    assert page.evaluate("() => document.activeElement.value") == "2"
    page.keyboard.press("Tab")
    assert page.evaluate("() => document.activeElement.value") == "3"
    page.keyboard.press("Shift+Tab")
    assert page.evaluate("() => document.activeElement.value") == "2"
    page.keyboard.press("Shift+Tab")
    assert page.evaluate("() => document.activeElement.value") == "1"


def test_FO_006_should_traverse_only_form_elements(
    page: Page, browser_name: str, platform: str
) -> None:
    if platform != "darwin" or browser_name != "webkit":
        pytest.skip(
            "Chromium and WebKit both have settings for tab traversing all links, but it is only on by default in WebKit."
        )

    page.set_content(
        """
    <input id="input-1">
    <button id="button">button</button>
    <a href id="link">link</a>
    <input id="input-2">
  """
    )
    page.keyboard.press("Tab")
    assert page.evaluate("() => document.activeElement.id") == "input-1"
    page.keyboard.press("Tab")
    assert page.evaluate("() => document.activeElement.id") == "input-2"
    page.keyboard.press("Shift+Tab")
    assert page.evaluate("() => document.activeElement.id") == "input-1"
    page.keyboard.press("Alt+Tab")
    assert page.evaluate("() => document.activeElement.id") == "button"
    page.keyboard.press("Alt+Tab")
    assert page.evaluate("() => document.activeElement.id") == "link"
    page.keyboard.press("Alt+Tab")
    assert page.evaluate("() => document.activeElement.id") == "input-2"
    page.keyboard.press("Alt+Shift+Tab")
    assert page.evaluate("() => document.activeElement.id") == "link"
    page.keyboard.press("Alt+Shift+Tab")
    assert page.evaluate("() => document.activeElement.id") == "button"
    page.keyboard.press("Alt+Shift+Tab")
    assert page.evaluate("() => document.activeElement.id") == "input-1"


def test_FO_007_clicking_checkbox_should_activate_it(
    page: Page, browser_name: str
) -> None:
    if browser_name == "webkit":
        pytest.skip("Safari does not focus on click")

    page.set_content("<input type=checkbox></input>")
    page.click("input")
    node_name = page.evaluate("() => document.activeElement.nodeName")
    assert node_name == "INPUT"


def test_FO_008_tab_should_cycle_between_single_input_and_browser(
    page: Page, browser_name: str, is_headless_shell: bool
) -> None:
    if browser_name == "chromium" and not is_headless_shell:
        pytest.skip("Chromium keeps input focused.")
    if browser_name == "firefox":
        pytest.skip("fixme")
    page.set_content(
        """<label for="input1">input1</label>
    <input id="input1">
    <script>
    {
      window.focusEvents = [];
      const input = document.getElementById('input1');
      input.addEventListener('blur', () => focusEvents.push('blur'));
      input.addEventListener('focus', () => focusEvents.push('focus'));
    }
    </script>"""
    )
    assert page.evaluate("() => document.activeElement.tagName") == "BODY"
    page.keyboard.press("Tab")
    assert page.evaluate("() => document.activeElement.id") == "input1"
    assert page.evaluate("() => window.focusEvents") == ["focus"]
    page.keyboard.press("Tab")
    assert page.evaluate("() => document.activeElement.tagName") == "BODY"
    assert page.evaluate("() => window.focusEvents") == ["focus", "blur"]
    page.keyboard.press("Tab")
    assert page.evaluate("() => document.activeElement.id") == "input1"
    assert page.evaluate("() => window.focusEvents") == [
        "focus",
        "blur",
        "focus",
    ]


def test_FO_009_tab_should_cycle_between_document_elements_and_browser(
    page: Page, browser_name: str, is_headless_shell: bool
) -> None:
    if browser_name == "chromium" and not is_headless_shell:
        pytest.skip("Chromium keeps last input focused.")
    if browser_name == "firefox":
        pytest.skip("fixme")
    page.set_content(
        """
    <input id="input1">
    <input id="input2">
    <script>
      window.focusEvents = [];
      {
        const input = document.getElementById('input1');
        input.addEventListener('blur', () => focusEvents.push('blur1'));
        input.addEventListener('focus', () => focusEvents.push('focus1'));
      }
      {
        const input = document.getElementById('input2');
        input.addEventListener('blur', () => focusEvents.push('blur2'));
        input.addEventListener('focus', () => focusEvents.push('focus2'));
      }
    </script>"""
    )
    assert page.evaluate("() => document.activeElement.tagName") == "BODY"
    page.keyboard.press("Tab")
    assert page.evaluate("() => document.activeElement.id") == "input1"
    assert page.evaluate("() => window.focusEvents") == ["focus1"]
    page.keyboard.press("Tab")
    assert page.evaluate("() => document.activeElement.id") == "input2"
    assert page.evaluate("() => window.focusEvents") == [
        "focus1",
        "blur1",
        "focus2",
    ]
    page.keyboard.press("Tab")
    assert page.evaluate("() => document.activeElement.tagName") == "BODY"
    assert page.evaluate("() => window.focusEvents") == [
        "focus1",
        "blur1",
        "focus2",
        "blur2",
    ]
    page.keyboard.press("Tab")
    assert page.evaluate("() => document.activeElement.id") == "input1"
    assert page.evaluate("() => window.focusEvents") == [
        "focus1",
        "blur1",
        "focus2",
        "blur2",
        "focus1",
    ]


def test_FO_010_keeps_focus_on_element_when_attempting_to_focus_a_non_focusable_element(
    page: Page,
) -> None:
    page.set_content(
        """
      <div id="focusable" tabindex="0">focusable</div>
      <div id="non-focusable">not focusable</div>
      <script>
        window.eventLog = [];

        const focusable = document.getElementById("focusable");

        focusable.addEventListener('blur', () => window.eventLog.push('blur focusable'));
        focusable.addEventListener('focus', () => window.eventLog.push('focus focusable'));

        const nonFocusable = document.getElementById("non-focusable");
        nonFocusable.addEventListener('blur', () => window.eventLog.push('blur non-focusable'));
        nonFocusable.addEventListener('focus', () => window.eventLog.push('focus non-focusable'));
      </script>
    """
    )
    page.locator("#focusable").click()
    assert page.evaluate("() => document.activeElement?.id") == "focusable"
    page.locator("#non-focusable").focus()
    assert page.evaluate("() => document.activeElement?.id") == "focusable"
    assert page.evaluate("() => window['eventLog']") == [
        "focus focusable",
    ]


def test_FO_011_should_move_focus_from_an_iframe_to_its_parent(
    page: Page, server: Server, request: pytest.FixtureRequest, browser_name: str
) -> None:
    _xfail_old_firefox_focus(request, browser_name)
    _frame_route(server)
    page.goto(server.EMPTY_PAGE)
    page.set_content(
        f'<iframe src="{server.PREFIX}/frame.html"></iframe><input id=outer>'
    )
    page.frame_locator("iframe").locator("#inner").focus()
    assert (
        page.frame_locator("iframe")
        .locator("#inner")
        .evaluate("e => e === document.activeElement")
        is True
    )
    page.evaluate("() => document.getElementById('outer').focus()")
    expect(page.locator("#outer")).to_be_focused()
    assert (
        page.frame_locator("iframe")
        .locator("#inner")
        .evaluate("e => e === document.activeElement")
        is False
    )


def test_FO_012_should_tab_from_an_iframe_to_its_parent(
    page: Page, server: Server, request: pytest.FixtureRequest, browser_name: str
) -> None:
    _xfail_old_firefox_focus(request, browser_name)
    _frame_route(server)
    page.goto(server.EMPTY_PAGE)
    page.set_content(
        f'<iframe src="{server.PREFIX}/frame.html"></iframe><input id=outer>'
    )
    page.frame_locator("iframe").locator("#inner").click()
    assert (
        page.frame_locator("iframe")
        .locator("#inner")
        .evaluate("e => e === document.activeElement")
        is True
    )
    page.keyboard.press("Tab")
    expect(page.locator("#outer")).to_be_focused()
