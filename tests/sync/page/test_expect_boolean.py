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

"""Port of tests/page/expect-boolean.spec.ts."""

from typing import Any, Callable, List

import pytest

from playwright.sync_api import Page, expect
from tests.server import Server, TestServerRequest

# Python's assertion messages have their own format: upstream's
# "expect(locator).toBeChecked() failed\n\nLocator: ...\nExpected: checked\n
# Received: unchecked\nTimeout: 1000ms" is "Locator expected to be checked\n
# Actual value: unchecked" followed by the call log, whose first line holds the
# timeout. The call log comes from the driver, with locators in Python syntax.


def test_EX_001_to_be_checked_default(page: Page) -> None:
    page.set_content("<input type=checkbox checked></input>")
    locator = page.locator("input")
    expect(locator).to_be_checked()


def test_EX_002_to_be_checked_with_checked_true(page: Page) -> None:
    page.set_content("<input type=checkbox checked></input>")
    locator = page.locator("input")
    expect(locator).to_be_checked(checked=True)


def test_EX_004_to_be_checked_with_indeterminate_true(page: Page) -> None:
    page.set_content("<input type=checkbox></input>")
    page.locator("input").evaluate("e => e.indeterminate = true")
    locator = page.locator("input")
    expect(locator).to_be_checked(indeterminate=True)


def test_EX_005_to_be_checked_with_indeterminate_true_and_checked(
    page: Page,
) -> None:
    page.set_content("<input type=checkbox></input>")
    page.locator("input").evaluate("e => e.indeterminate = true")
    locator = page.locator("input")
    with pytest.raises(AssertionError) as exc_info:
        expect(locator).to_be_checked(indeterminate=True, checked=False)
    assert "Can't assert indeterminate and checked at the same time" in str(
        exc_info.value
    )


def test_EX_006_to_be_checked_fail(page: Page) -> None:
    page.set_content("<input type=checkbox></input>")
    locator = page.locator("input")
    with pytest.raises(AssertionError) as exc_info:
        expect(locator).to_be_checked(timeout=1000)
    message = str(exc_info.value)
    assert "Locator expected to be checked\nActual value: unchecked" in message
    assert '- Expect "to_be_checked" locator("input") with timeout 1000ms' in message


def test_EX_007_to_be_checked_with_not(page: Page) -> None:
    page.set_content("<input type=checkbox></input>")
    locator = page.locator("input")
    expect(locator).not_to_be_checked()


def test_EX_008_to_be_checked_with_not_and_checked_false(page: Page) -> None:
    page.set_content("<input type=checkbox></input>")
    locator = page.locator("input")
    expect(locator).to_be_checked(checked=False)


def test_EX_009_to_be_checked_fail_with_not(page: Page) -> None:
    page.set_content("<input type=checkbox checked></input>")
    locator = page.locator("input")
    with pytest.raises(AssertionError) as exc_info:
        expect(locator).not_to_be_checked(timeout=1000)
    message = str(exc_info.value)
    assert "Locator expected not to be checked\nActual value: checked" in message
    assert (
        '- Expect "not_to_be_checked" locator("input") with timeout 1000ms' in message
    )
    assert 'locator resolved to <input checked type="checkbox"/>' in message


def test_EX_010_to_be_checked_fail_with_checked_false(page: Page) -> None:
    page.set_content("<input type=checkbox checked></input>")
    locator = page.locator("input")
    with pytest.raises(AssertionError) as exc_info:
        expect(locator).to_be_checked(checked=False, timeout=1000)
    message = str(exc_info.value)
    assert "Locator expected to be unchecked\nActual value: checked" in message
    assert '- Expect "to_be_checked" locator("input") with timeout 1000ms' in message
    assert 'locator resolved to <input checked type="checkbox"/>' in message


def test_EX_011_to_be_checked_fail_with_indeterminate_true(page: Page) -> None:
    page.set_content("<input type=checkbox></input>")
    locator = page.locator("input")
    with pytest.raises(AssertionError) as exc_info:
        expect(locator).to_be_checked(indeterminate=True, timeout=1000)
    message = str(exc_info.value)
    assert "Locator expected to be indeterminate\nActual value: unchecked" in message
    assert '- Expect "to_be_checked" locator("input") with timeout 1000ms' in message


def test_EX_012_to_be_checked_fail_missing(page: Page) -> None:
    page.set_content("<div>no inputs here</div>")
    locator2 = page.locator("input2")
    with pytest.raises(AssertionError) as exc_info:
        expect(locator2).not_to_be_checked(timeout=1000)
    message = str(exc_info.value)
    assert (
        "Locator expected not to be checked\n"
        "Actual value: None\n"
        "Error: element(s) not found"
    ) in message
    assert (
        "Call log:\n"
        '  - Expect "not_to_be_checked" locator("input2") with timeout 1000ms\n'
        '  - waiting for locator("input2")\n'
    ) in message


def test_EX_013_to_be_checked_with_role(page: Page) -> None:
    for role in [
        "checkbox",
        "menuitemcheckbox",
        "option",
        "radio",
        "switch",
        "menuitemradio",
        "treeitem",
    ]:
        page.set_content(f"<div role={role} aria-checked=true>I am checked</div>")
        locator = page.locator("div")
        expect(locator).to_be_checked()


def test_EX_014_to_be_checked_friendly_log(page: Page) -> None:
    page.set_content("<input type=checkbox></input>")
    with pytest.raises(AssertionError) as exc_info1:
        expect(page.locator("input")).to_be_checked(timeout=1000)
    assert 'unexpected value "unchecked"' in str(exc_info1.value)

    page.set_content("<input type=checkbox checked></input>")
    with pytest.raises(AssertionError) as exc_info2:
        expect(page.locator("input")).to_be_checked(checked=False, timeout=1000)
    assert 'unexpected value "checked"' in str(exc_info2.value)


def test_EX_015_to_be_checked_with_impossible_timeout(page: Page) -> None:
    page.set_content("<input type=checkbox checked></input>")
    expect(page.locator("input")).to_be_checked(timeout=1)


def test_EX_016_to_be_checked_with_impossible_timeout_not(page: Page) -> None:
    page.set_content("<input type=checkbox></input>")
    expect(page.locator("input")).not_to_be_checked(timeout=1)


def test_EX_017_to_be_editable_default(page: Page) -> None:
    page.set_content("<input></input>")
    locator = page.locator("input")
    expect(locator).to_be_editable()


def test_EX_018_to_be_editable_with_not(page: Page) -> None:
    page.set_content("<input readonly></input>")
    locator = page.locator("input")
    expect(locator).not_to_be_editable()


def test_EX_019_to_be_editable_with_editable_true(page: Page) -> None:
    page.set_content("<input></input>")
    locator = page.locator("input")
    expect(locator).to_be_editable(editable=True)


def test_EX_020_to_be_editable_with_editable_false(page: Page) -> None:
    page.set_content("<input readonly></input>")
    locator = page.locator("input")
    expect(locator).to_be_editable(editable=False)


def test_EX_021_to_be_editable_with_not_and_editable_false(page: Page) -> None:
    page.set_content("<input></input>")
    locator = page.locator("input")
    expect(locator).not_to_be_editable(editable=False)


def test_EX_022_to_be_editable_throws(page: Page) -> None:
    page.set_content("<button>")
    locator = page.locator("button")
    with pytest.raises(AssertionError) as exc_info:
        expect(locator).to_be_editable()
    assert (
        "Element is not an <input>, <textarea>, <select> or [contenteditable] and does not have a role allowing [aria-readonly]"
        in str(exc_info.value)
    )


def test_EX_023_to_be_enabled_default(page: Page) -> None:
    page.set_content("<button>Text</button>")
    locator = page.locator("button")
    expect(locator).to_be_enabled()


def test_EX_024_to_be_enabled_with_enabled_true(page: Page) -> None:
    page.set_content("<button>Text</button>")
    locator = page.locator("button")
    expect(locator).to_be_enabled(enabled=True)


def test_EX_025_to_be_enabled_with_enabled_false(page: Page) -> None:
    page.set_content("<button disabled>Text</button>")
    locator = page.locator("button")
    expect(locator).to_be_enabled(enabled=False)


def test_EX_026_to_be_enabled_failed(page: Page) -> None:
    page.set_content("<button disabled>Text</button>")
    locator = page.locator("button")
    with pytest.raises(AssertionError) as exc_info:
        expect(locator).to_be_enabled(timeout=1000)
    assert "locator resolved to <button disabled>Text</button>" in str(exc_info.value)


def test_EX_027_to_be_enabled_eventually(
    page: Page, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_content("<button disabled>Text</button>")
    locator = page.locator("button")

    def remove_disabled() -> None:
        page.wait_for_timeout(500)
        locator.evaluate("e => e.removeAttribute('disabled')")

    def check() -> None:
        expect(locator).to_be_enabled()

    sync_gather(check, remove_disabled)


def test_EX_028_to_be_enabled_eventually_with_not(
    page: Page, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_content("<button>Text</button>")
    locator = page.locator("button")

    def set_disabled() -> None:
        page.wait_for_timeout(500)
        locator.evaluate("e => e.setAttribute('disabled', '')")

    def check() -> None:
        expect(locator).not_to_be_enabled()

    sync_gather(check, set_disabled)


def test_EX_029_to_be_enabled_with_not_and_enabled_false(page: Page) -> None:
    page.set_content("<button>Text</button>")
    locator = page.locator("button")
    expect(locator).not_to_be_enabled(enabled=False)


def test_EX_030_to_be_enabled_to_be_disabled(page: Page) -> None:
    page.set_content("<button disabled>Text</button>")
    locator = page.locator("button")
    expect(locator).to_be_disabled()


def test_EX_031_to_be_empty_input(page: Page) -> None:
    page.set_content("<input></input>")
    locator = page.locator("input")
    expect(locator).to_be_empty()


def test_EX_032_not_to_be_empty(page: Page) -> None:
    page.set_content("<input value=text></input>")
    locator = page.locator("input")
    expect(locator).not_to_be_empty()


def test_EX_033_to_be_empty_div(page: Page) -> None:
    page.set_content('<div style="width: 50; height: 50px"></div>')
    locator = page.locator("div")
    expect(locator).to_be_empty()


def test_EX_034_to_be_disabled_with_value(page: Page) -> None:
    page.set_content('<button disabled="yes">Text</button>')
    locator = page.locator("button")
    expect(locator).to_be_disabled()


def test_EX_035_to_be_checked_with_value(page: Page) -> None:
    page.set_content('<input type=checkbox checked="yes"></input>')
    locator = page.locator("input")
    expect(locator).to_be_checked()


def test_EX_036_to_be_hidden_with_value(page: Page) -> None:
    page.set_content('<input type=checkbox hidden="of course"></input>')
    locator = page.locator("input")
    expect(locator).to_be_hidden()


def test_EX_037_not_to_be_disabled_div(page: Page) -> None:
    page.set_content('<div disabled="yes"></div>')
    locator = page.locator("div")
    expect(locator).not_to_be_disabled()


def test_EX_038_to_be_visible_default(page: Page) -> None:
    page.set_content("<input></input>")
    locator = page.locator("input")
    expect(locator).to_be_visible()


def test_EX_039_to_be_visible_with_not(page: Page) -> None:
    page.set_content('<button style="display: none">hello</button>')
    locator = page.locator("button")
    expect(locator).not_to_be_visible()


def test_EX_040_to_be_visible_with_visible_true(page: Page) -> None:
    page.set_content("<button>hello</button>")
    locator = page.locator("button")
    expect(locator).to_be_visible(visible=True)


def test_EX_041_to_be_visible_with_visible_false(page: Page) -> None:
    page.set_content("<button hidden>hello</button>")
    locator = page.locator("button")
    expect(locator).to_be_visible(visible=False)


def test_EX_042_to_be_visible_with_not_and_visible_false(page: Page) -> None:
    page.set_content("<button>hello</button>")
    locator = page.locator("button")
    expect(locator).not_to_be_visible(visible=False)


def test_EX_043_to_be_visible_eventually(
    page: Page, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_content("<div></div>")
    locator = page.locator("span")

    def add_span() -> None:
        page.eval_on_selector("div", "div => div.innerHTML = '<span>Hello</span>'")

    def check() -> None:
        expect(locator).to_be_visible()

    sync_gather(check, add_span)


def test_EX_044_to_be_visible_eventually_with_not(
    page: Page, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_content("<div><span>Hello</span></div>")
    locator = page.locator("span")

    def clear_span() -> None:
        page.eval_on_selector("span", "span => span.textContent = ''")

    def check() -> None:
        expect(locator).not_to_be_visible()

    sync_gather(check, clear_span)


def test_EX_045_to_be_visible_fail(page: Page) -> None:
    page.set_content('<button style="display: none"></button>')
    locator = page.locator("button")
    with pytest.raises(AssertionError) as exc_info:
        expect(locator).to_be_visible(timeout=1000)
    assert "locator resolved to <button></button>" in str(exc_info.value)


def test_EX_046_to_be_visible_fail_with_not(page: Page) -> None:
    page.set_content("<input></input>")
    locator = page.locator("input")
    with pytest.raises(AssertionError) as exc_info:
        expect(locator).not_to_be_visible(timeout=1000)
    assert "locator resolved to <input/>" in str(exc_info.value)


def test_EX_047_to_be_visible_with_impossible_timeout(page: Page) -> None:
    page.set_content("<div id=node>Text content</div>")
    expect(page.locator("#node")).to_be_visible(timeout=1)


def test_EX_048_to_be_visible_with_impossible_timeout_not(page: Page) -> None:
    page.set_content("<div id=node>Text content</div>")
    expect(page.locator("no-such-thing")).not_to_be_visible(timeout=1)


def test_EX_049_to_be_visible_with_frame_locator(
    page: Page, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_content("<div></div>")
    locator = page.frame_locator("iframe").locator("input")
    done = False

    def check() -> None:
        nonlocal done
        expect(locator).to_be_visible()
        done = True

    def add_frame() -> None:
        page.wait_for_timeout(1000)
        assert done is False
        page.set_content('<iframe srcdoc="<input>"></iframe>')

    sync_gather(check, add_frame)
    assert done is True


def test_EX_050_to_be_visible_with_frame_locator_2(
    page: Page, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_content("<iframe></iframe>")
    locator = page.frame_locator("iframe").locator("input")
    done = False

    def check() -> None:
        nonlocal done
        expect(locator).to_be_visible()
        done = True

    def add_frame() -> None:
        page.wait_for_timeout(1000)
        assert done is False
        page.set_content('<iframe srcdoc="<input>"></iframe>')

    sync_gather(check, add_frame)
    assert done is True


def test_EX_051_to_be_visible_over_navigation(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    page.goto(server.EMPTY_PAGE)
    done = False

    def check() -> None:
        nonlocal done
        expect(page.locator("input")).to_be_visible()
        done = True

    def navigate() -> None:
        page.wait_for_timeout(1000)
        assert done is False
        page.goto(server.PREFIX + "/input/checkbox.html")

    sync_gather(check, navigate)
    assert done is True


def test_EX_052_to_be_hidden_default(page: Page) -> None:
    page.set_content('<button style="display: none"></button>')
    locator = page.locator("button")
    expect(locator).to_be_hidden()


def test_EX_053_to_be_hidden_when_nothing_matches(page: Page) -> None:
    page.set_content("<div></div>")
    locator = page.locator("button")
    expect(locator).to_be_hidden()


def test_EX_054_to_be_hidden_with_not(page: Page) -> None:
    page.set_content("<input></input>")
    locator = page.locator("input")
    expect(locator).not_to_be_hidden()


def test_EX_055_to_be_hidden_eventually_with_not(
    page: Page, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_content("<div></div>")
    locator = page.locator("span")

    def add_span() -> None:
        page.eval_on_selector("div", "div => div.innerHTML = '<span>Hello</span>'")

    def check() -> None:
        expect(locator).not_to_be_hidden()

    sync_gather(check, add_span)


def test_EX_056_to_be_hidden_eventually(
    page: Page, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_content("<div><span>Hello</span></div>")
    locator = page.locator("span")

    def clear_span() -> None:
        page.eval_on_selector("span", "span => span.textContent = ''")

    def check() -> None:
        expect(locator).to_be_hidden()

    sync_gather(check, clear_span)


def test_EX_057_to_be_hidden_fail(page: Page) -> None:
    page.set_content("<input></input>")
    locator = page.locator("input")
    with pytest.raises(AssertionError) as exc_info:
        expect(locator).to_be_hidden(timeout=3000)
    assert "locator resolved to <input/>" in str(exc_info.value)


def test_EX_058_to_be_hidden_fail_with_not(page: Page) -> None:
    page.set_content('<button style="display: none"></button>')
    locator = page.locator("button")
    with pytest.raises(AssertionError) as exc_info:
        expect(locator).not_to_be_hidden(timeout=3000)
    assert "locator resolved to <button></button>" in str(exc_info.value)


def test_EX_059_to_be_hidden_fail_with_not_when_nothing_matching(
    page: Page,
) -> None:
    page.set_content("<div></div>")
    locator = page.locator("button")
    with pytest.raises(AssertionError) as exc_info:
        expect(locator).not_to_be_hidden(timeout=1000)
    message = str(exc_info.value)
    assert (
        "Locator expected not to be hidden\n"
        "Actual value: None\n"
        "Error: element(s) not found"
    ) in message
    assert (
        "Call log:\n"
        '  - Expect "not_to_be_hidden" locator("button") with timeout 1000ms\n'
    ) in message


def test_EX_060_to_be_hidden_with_impossible_timeout_not(page: Page) -> None:
    page.set_content("<div id=node>Text content</div>")
    expect(page.locator("#node")).not_to_be_hidden(timeout=1)


def test_EX_061_to_be_hidden_with_impossible_timeout(page: Page) -> None:
    page.set_content("<div id=node>Text content</div>")
    expect(page.locator("no-such-thing")).to_be_hidden(timeout=1)


def test_EX_062_to_be_focused(page: Page) -> None:
    page.set_content("<input></input>")
    locator = page.locator("input")
    locator.focus()
    expect(locator).to_be_focused()


def test_EX_063_to_be_focused_with_shadow_elements(page: Page) -> None:
    page.set_content(
        """
    <div id="app">
    </div>
    <script>
      const root = document.querySelector('div');
      const shadowRoot = root.attachShadow({ mode: 'open' });
      const input = document.createElement('input');
      input.id = "my-input"
      shadowRoot.appendChild(input);
    </script>
  """
    )

    page.locator("input").focus()
    assert (
        page.evaluate("() => document.activeElement.shadowRoot.activeElement.id")
        == "my-input"
    )
    expect(page.locator("#app")).to_be_focused()
    expect(page.locator("input")).to_be_focused()


def test_EX_064_should_print_unknown_engine_error(page: Page) -> None:
    with pytest.raises(AssertionError) as exc_info:
        expect(page.locator('row="row"')).to_be_visible()
    assert 'Unknown engine "row" while parsing selector row="row"' in str(
        exc_info.value
    )


def test_EX_065_should_print_selector_syntax_error(page: Page) -> None:
    with pytest.raises(AssertionError) as exc_info:
        expect(page.locator("row]")).to_be_visible()
    assert 'Unexpected token "]" while parsing css selector "row]"' in str(
        exc_info.value
    )


def test_EX_066_to_be_ok(page: Page, server: Server) -> None:
    res = page.request.get(server.EMPTY_PAGE)
    expect(res).to_be_ok()


def test_EX_067_not_to_be_ok(page: Page, server: Server) -> None:
    res = page.request.get(f"{server.PREFIX}/unknown")
    expect(res).not_to_be_ok()


@pytest.fixture
def content_type_routes(server: Server) -> None:
    """The beforeEach of 'toBeOK should print response with text content type when fails'."""

    def text_content_type(request: TestServerRequest) -> None:
        request.setResponseCode(404)
        request.setHeader("Content-type", "text/plain")
        request.write(b"Text error")
        request.finish()

    def no_content_type(request: TestServerRequest) -> None:
        request.setResponseCode(404)
        request.write(b"No content type error")
        request.finish()

    def binary_content_type(request: TestServerRequest) -> None:
        request.setResponseCode(404)
        request.setHeader("Content-type", "image/bmp")
        request.write(b"Image content type error")
        request.finish()

    server.set_route("/text-content-type", text_content_type)
    server.set_route("/no-content-type", no_content_type)
    server.set_route("/binary-content-type", binary_content_type)


@pytest.mark.usefixtures("content_type_routes")
def test_EX_070_to_be_ok_should_print_response_with_text_content_type_when_fails_text_content_type(
    page: Page, server: Server
) -> None:
    res = page.request.get(f"{server.PREFIX}/text-content-type")
    with pytest.raises(AssertionError) as exc_info:
        expect(res).to_be_ok()
    message = str(exc_info.value)
    assert "Response status expected to be within [200..299] range, was '404'" in (
        message
    )
    assert f"→ GET {server.PREFIX}/text-content-type" in message
    assert "← 404 Not Found" in message
    assert "Response Text:\nText error" in message


@pytest.mark.usefixtures("content_type_routes")
def test_EX_071_to_be_ok_should_print_response_with_text_content_type_when_fails_no_content_type(
    page: Page, server: Server
) -> None:
    res = page.request.get(f"{server.PREFIX}/no-content-type")
    with pytest.raises(AssertionError) as exc_info:
        expect(res).to_be_ok()
    message = str(exc_info.value)
    assert f"→ GET {server.PREFIX}/no-content-type" in message
    assert "← 404 Not Found" in message
    assert "No content type error" not in message


@pytest.mark.usefixtures("content_type_routes")
def test_EX_072_to_be_ok_should_print_response_with_text_content_type_when_fails_image_content_type(
    page: Page, server: Server
) -> None:
    res = page.request.get(f"{server.PREFIX}/image-content-type")
    with pytest.raises(AssertionError) as exc_info:
        expect(res).to_be_ok()
    message = str(exc_info.value)
    assert f"→ GET {server.PREFIX}/image-content-type" in message
    assert "← 404 Not Found" in message
    assert "Image content type error" not in message


def test_EX_073_to_be_attached_default(page: Page) -> None:
    page.set_content("<input></input>")
    locator = page.locator("input")
    expect(locator).to_be_attached()


def test_EX_074_to_be_attached_with_hidden_element(page: Page) -> None:
    page.set_content('<button style="display:none">hello</button>')
    locator = page.locator("button")
    expect(locator).to_be_attached()


def test_EX_075_to_be_attached_with_not(page: Page) -> None:
    page.set_content("<button>hello</button>")
    locator = page.locator("input")
    expect(locator).not_to_be_attached()


def test_EX_076_to_be_attached_with_attached_true(page: Page) -> None:
    page.set_content("<button>hello</button>")
    locator = page.locator("button")
    expect(locator).to_be_attached(attached=True)


def test_EX_077_to_be_attached_with_attached_false(page: Page) -> None:
    page.set_content("<button>hello</button>")
    locator = page.locator("input")
    expect(locator).to_be_attached(attached=False)


def test_EX_078_to_be_attached_with_not_and_attached_false(page: Page) -> None:
    page.set_content("<button>hello</button>")
    locator = page.locator("button")
    expect(locator).not_to_be_attached(attached=False)


def test_EX_079_to_be_attached_eventually(
    page: Page, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_content("<div></div>")
    locator = page.locator("span")

    def add_span() -> None:
        page.eval_on_selector("div", "div => div.innerHTML = '<span>Hello</span>'")

    def check() -> None:
        expect(locator).to_be_attached()

    sync_gather(check, add_span)


def test_EX_080_to_be_attached_eventually_with_not(
    page: Page, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_content("<div><span>Hello</span></div>")
    locator = page.locator("span")

    def clear_div() -> None:
        page.eval_on_selector("div", "div => div.textContent = ''")

    def check() -> None:
        expect(locator).not_to_be_attached()

    sync_gather(check, clear_div)


def test_EX_081_to_be_attached_fail(page: Page) -> None:
    page.set_content("<button>Hello</button>")
    locator = page.locator("input")
    with pytest.raises(AssertionError) as exc_info:
        expect(locator).to_be_attached(timeout=1000)
    assert "locator resolved to" not in str(exc_info.value)


def test_EX_082_to_be_attached_fail_with_not(page: Page) -> None:
    page.set_content("<input></input>")
    locator = page.locator("input")
    with pytest.raises(AssertionError) as exc_info:
        expect(locator).not_to_be_attached(timeout=3000)
    assert "locator resolved to <input/>" in str(exc_info.value)


def test_EX_083_to_be_attached_with_impossible_timeout(page: Page) -> None:
    page.set_content("<div id=node>Text content</div>")
    expect(page.locator("#node")).to_be_attached(timeout=1)


def test_EX_084_to_be_attached_with_impossible_timeout_not(page: Page) -> None:
    page.set_content("<div id=node>Text content</div>")
    expect(page.locator("no-such-thing")).not_to_be_attached(timeout=1)


def test_EX_085_to_be_attached_with_frame_locator(
    page: Page, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_content("<div></div>")
    locator = page.frame_locator("iframe").locator("input")
    done = False

    def check() -> None:
        nonlocal done
        expect(locator).to_be_attached()
        done = True

    def add_frame() -> None:
        page.wait_for_timeout(1000)
        assert done is False
        page.set_content('<iframe srcdoc="<input>"></iframe>')

    sync_gather(check, add_frame)
    assert done is True


def test_EX_086_to_be_attached_over_navigation(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    page.goto(server.EMPTY_PAGE)
    done = False

    def check() -> None:
        nonlocal done
        expect(page.locator("input")).to_be_attached()
        done = True

    def navigate() -> None:
        page.wait_for_timeout(1000)
        assert done is False
        page.goto(server.PREFIX + "/input/checkbox.html")

    sync_gather(check, navigate)
    assert done is True
