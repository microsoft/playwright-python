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

from playwright.async_api import Page, expect
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
async def test_FO_001_should_work_smoke(page: Page) -> None:
    await page.set_content("<div id=d1 tabIndex=0></div>")
    assert await page.evaluate("() => document.activeElement.nodeName") == "BODY"
    await page.focus("#d1")
    assert await page.evaluate("() => document.activeElement.id") == "d1"


async def test_FO_002_should_emit_focus_event(page: Page) -> None:
    await page.set_content("<div id=d1 tabIndex=0></div>")
    focused = False

    def on_focus() -> None:
        nonlocal focused
        focused = True

    await page.expose_function("focusEvent", on_focus)
    await page.eval_on_selector(
        "#d1", "d1 => d1.addEventListener('focus', window['focusEvent'])"
    )
    await page.focus("#d1")
    assert focused is True


async def test_FO_003_should_emit_blur_event(page: Page) -> None:
    await page.set_content(
        "<div id=d1 tabIndex=0>DIV1</div><div id=d2 tabIndex=0>DIV2</div>"
    )
    await page.focus("#d1")
    focused = False
    blurred = False

    def on_focus() -> None:
        nonlocal focused
        focused = True

    def on_blur() -> None:
        nonlocal blurred
        blurred = True

    await page.expose_function("focusEvent", on_focus)
    await page.expose_function("blurEvent", on_blur)
    await page.eval_on_selector(
        "#d1", "d1 => d1.addEventListener('blur', window['blurEvent'])"
    )
    await page.eval_on_selector(
        "#d2", "d2 => d2.addEventListener('focus', window['focusEvent'])"
    )
    await page.focus("#d2")
    assert focused is True
    assert blurred is True


async def test_FO_004_should_traverse_focus(page: Page) -> None:
    await page.set_content('<input id="i1"><input id="i2">')
    focused = False

    def on_focus() -> None:
        nonlocal focused
        focused = True

    await page.expose_function("focusEvent", on_focus)
    await page.eval_on_selector(
        "#i2", "i2 => i2.addEventListener('focus', window['focusEvent'])"
    )

    await page.focus("#i1")
    await page.keyboard.type("First")
    await page.keyboard.press("Tab")
    await page.keyboard.type("Last")

    assert focused is True
    assert await page.eval_on_selector("#i1", "e => e.value") == "First"
    assert await page.eval_on_selector("#i2", "e => e.value") == "Last"


async def test_FO_005_should_traverse_focus_in_all_directions(page: Page) -> None:
    await page.set_content('<input value="1"><input value="2"><input value="3">')
    await page.keyboard.press("Tab")
    assert await page.evaluate("() => document.activeElement.value") == "1"
    await page.keyboard.press("Tab")
    assert await page.evaluate("() => document.activeElement.value") == "2"
    await page.keyboard.press("Tab")
    assert await page.evaluate("() => document.activeElement.value") == "3"
    await page.keyboard.press("Shift+Tab")
    assert await page.evaluate("() => document.activeElement.value") == "2"
    await page.keyboard.press("Shift+Tab")
    assert await page.evaluate("() => document.activeElement.value") == "1"


async def test_FO_006_should_traverse_only_form_elements(
    page: Page, browser_name: str, platform: str
) -> None:
    if platform != "darwin" or browser_name != "webkit":
        pytest.skip(
            "Chromium and WebKit both have settings for tab traversing all links, but it is only on by default in WebKit."
        )

    await page.set_content(
        """
    <input id="input-1">
    <button id="button">button</button>
    <a href id="link">link</a>
    <input id="input-2">
  """
    )
    await page.keyboard.press("Tab")
    assert await page.evaluate("() => document.activeElement.id") == "input-1"
    await page.keyboard.press("Tab")
    assert await page.evaluate("() => document.activeElement.id") == "input-2"
    await page.keyboard.press("Shift+Tab")
    assert await page.evaluate("() => document.activeElement.id") == "input-1"
    await page.keyboard.press("Alt+Tab")
    assert await page.evaluate("() => document.activeElement.id") == "button"
    await page.keyboard.press("Alt+Tab")
    assert await page.evaluate("() => document.activeElement.id") == "link"
    await page.keyboard.press("Alt+Tab")
    assert await page.evaluate("() => document.activeElement.id") == "input-2"
    await page.keyboard.press("Alt+Shift+Tab")
    assert await page.evaluate("() => document.activeElement.id") == "link"
    await page.keyboard.press("Alt+Shift+Tab")
    assert await page.evaluate("() => document.activeElement.id") == "button"
    await page.keyboard.press("Alt+Shift+Tab")
    assert await page.evaluate("() => document.activeElement.id") == "input-1"


async def test_FO_007_clicking_checkbox_should_activate_it(
    page: Page, browser_name: str
) -> None:
    if browser_name == "webkit":
        pytest.skip("Safari does not focus on click")

    await page.set_content("<input type=checkbox></input>")
    await page.click("input")
    node_name = await page.evaluate("() => document.activeElement.nodeName")
    assert node_name == "INPUT"


async def test_FO_008_tab_should_cycle_between_single_input_and_browser(
    page: Page, browser_name: str, is_headless_shell: bool
) -> None:
    if browser_name == "chromium" and not is_headless_shell:
        pytest.skip("Chromium keeps input focused.")
    if browser_name == "firefox":
        pytest.skip("fixme")
    await page.set_content(
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
    assert await page.evaluate("() => document.activeElement.tagName") == "BODY"
    await page.keyboard.press("Tab")
    assert await page.evaluate("() => document.activeElement.id") == "input1"
    assert await page.evaluate("() => window.focusEvents") == ["focus"]
    await page.keyboard.press("Tab")
    assert await page.evaluate("() => document.activeElement.tagName") == "BODY"
    assert await page.evaluate("() => window.focusEvents") == ["focus", "blur"]
    await page.keyboard.press("Tab")
    assert await page.evaluate("() => document.activeElement.id") == "input1"
    assert await page.evaluate("() => window.focusEvents") == [
        "focus",
        "blur",
        "focus",
    ]


async def test_FO_009_tab_should_cycle_between_document_elements_and_browser(
    page: Page, browser_name: str, is_headless_shell: bool
) -> None:
    if browser_name == "chromium" and not is_headless_shell:
        pytest.skip("Chromium keeps last input focused.")
    if browser_name == "firefox":
        pytest.skip("fixme")
    await page.set_content(
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
    assert await page.evaluate("() => document.activeElement.tagName") == "BODY"
    await page.keyboard.press("Tab")
    assert await page.evaluate("() => document.activeElement.id") == "input1"
    assert await page.evaluate("() => window.focusEvents") == ["focus1"]
    await page.keyboard.press("Tab")
    assert await page.evaluate("() => document.activeElement.id") == "input2"
    assert await page.evaluate("() => window.focusEvents") == [
        "focus1",
        "blur1",
        "focus2",
    ]
    await page.keyboard.press("Tab")
    assert await page.evaluate("() => document.activeElement.tagName") == "BODY"
    assert await page.evaluate("() => window.focusEvents") == [
        "focus1",
        "blur1",
        "focus2",
        "blur2",
    ]
    await page.keyboard.press("Tab")
    assert await page.evaluate("() => document.activeElement.id") == "input1"
    assert await page.evaluate("() => window.focusEvents") == [
        "focus1",
        "blur1",
        "focus2",
        "blur2",
        "focus1",
    ]


async def test_FO_010_keeps_focus_on_element_when_attempting_to_focus_a_non_focusable_element(
    page: Page,
) -> None:
    await page.set_content(
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
    await page.locator("#focusable").click()
    assert await page.evaluate("() => document.activeElement?.id") == "focusable"
    await page.locator("#non-focusable").focus()
    assert await page.evaluate("() => document.activeElement?.id") == "focusable"
    assert await page.evaluate("() => window['eventLog']") == [
        "focus focusable",
    ]


async def test_FO_011_should_move_focus_from_an_iframe_to_its_parent(
    page: Page, server: Server, request: pytest.FixtureRequest, browser_name: str
) -> None:
    _xfail_old_firefox_focus(request, browser_name)
    _frame_route(server)
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        f'<iframe src="{server.PREFIX}/frame.html"></iframe><input id=outer>'
    )
    await page.frame_locator("iframe").locator("#inner").focus()
    assert (
        await page.frame_locator("iframe")
        .locator("#inner")
        .evaluate("e => e === document.activeElement")
        is True
    )
    await page.evaluate("() => document.getElementById('outer').focus()")
    await expect(page.locator("#outer")).to_be_focused()
    assert (
        await page.frame_locator("iframe")
        .locator("#inner")
        .evaluate("e => e === document.activeElement")
        is False
    )


async def test_FO_012_should_tab_from_an_iframe_to_its_parent(
    page: Page, server: Server, request: pytest.FixtureRequest, browser_name: str
) -> None:
    _xfail_old_firefox_focus(request, browser_name)
    _frame_route(server)
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        f'<iframe src="{server.PREFIX}/frame.html"></iframe><input id=outer>'
    )
    await page.frame_locator("iframe").locator("#inner").click()
    assert (
        await page.frame_locator("iframe")
        .locator("#inner")
        .evaluate("e => e === document.activeElement")
        is True
    )
    await page.keyboard.press("Tab")
    await expect(page.locator("#outer")).to_be_focused()
