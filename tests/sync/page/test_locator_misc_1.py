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

"""Port of tests/page/locator-misc-1.spec.ts."""

from pathlib import Path

import pytest

from playwright.sync_api import Error, Page
from tests.server import Server
from tests.utils import relative_path


def test_LO_127_should_hover_smoke(page: Page, server: Server, headless: bool) -> None:
    if not headless:
        pytest.skip("headed messes up with hover")

    page.goto(server.PREFIX + "/input/scrollable.html")
    button = page.locator("#button-6")
    button.hover()
    assert (
        page.evaluate("() => document.querySelector('button:hover').id") == "button-6"
    )


def test_LO_128_should_hover_when_node_is_removed(
    page: Page, server: Server, headless: bool
) -> None:
    if not headless:
        pytest.skip("headed messes up with hover")

    page.goto(server.PREFIX + "/input/scrollable.html")
    page.evaluate("() => delete window['Node']")
    button = page.locator("#button-6")
    button.hover()
    assert (
        page.evaluate("() => document.querySelector('button:hover').id") == "button-6"
    )


def test_LO_129_should_fill_input(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/textarea.html")
    handle = page.locator("input")
    handle.fill("some value")
    assert page.evaluate("() => window['result']") == "some value"


def test_LO_130_should_fill_input_when_node_is_removed(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/input/textarea.html")
    page.evaluate("() => delete window['Node']")
    handle = page.locator("input")
    handle.fill("some value")
    assert page.evaluate("() => window['result']") == "some value"


def test_LO_131_should_clear_input(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/textarea.html")
    handle = page.locator("input")
    handle.fill("some value")
    assert page.evaluate("() => window['result']") == "some value"
    handle.clear()
    assert page.evaluate("() => window['result']") == ""


def test_LO_132_should_check_the_box(page: Page) -> None:
    page.set_content("<input id='checkbox' type='checkbox'></input>")
    input = page.locator("input")
    input.check()
    assert page.evaluate("checkbox.checked") is True


def test_LO_133_should_check_the_box_using_set_checked(page: Page) -> None:
    page.set_content("<input id='checkbox' type='checkbox'></input>")
    input = page.locator("input")
    input.set_checked(True)
    assert page.evaluate("checkbox.checked") is True
    input.set_checked(False)
    assert page.evaluate("checkbox.checked") is False


def test_LO_134_should_uncheck_the_box(page: Page) -> None:
    page.set_content("<input id='checkbox' type='checkbox' checked></input>")
    input = page.locator("input")
    input.uncheck()
    assert page.evaluate("checkbox.checked") is False


def test_LO_135_should_select_single_option(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/select.html")
    select = page.locator("select")
    select.select_option("blue")
    assert page.evaluate("() => window['result'].onInput") == ["blue"]
    assert page.evaluate("() => window['result'].onChange") == ["blue"]


def test_LO_136_should_focus_and_blur_a_button(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/button.html")
    button = page.locator("button")
    assert button.evaluate("button => document.activeElement === button") is False

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
    button.evaluate(
        """button => {
    button.addEventListener('focus', window['focusEvent']);
    button.addEventListener('blur', window['blurEvent']);
  }"""
    )

    button.focus()
    assert focused is True
    assert blurred is False
    assert button.evaluate("button => document.activeElement === button") is True

    button.blur()
    assert focused is True
    assert blurred is True
    assert button.evaluate("button => document.activeElement === button") is False


def test_LO_137_focus_should_respect_strictness(page: Page, server: Server) -> None:
    page.set_content("<div>A</div><div>B</div>")
    with pytest.raises(Error) as exc_info:
        page.locator("div").focus()
    assert "strict mode violation" in exc_info.value.message


def test_LO_138_should_dispatch_click_event_via_element_handles(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/input/button.html")
    button = page.locator("button")
    button.dispatch_event("click")
    assert page.evaluate("() => window['result']") == "Clicked"


def test_LO_139_should_upload_the_file(
    page: Page, server: Server, assetdir: Path
) -> None:
    page.goto(server.PREFIX + "/input/fileupload.html")
    file_path = relative_path(assetdir / "file-to-upload.txt")
    input = page.locator("input[type=file]")
    input.set_input_files(file_path)
    assert (
        page.evaluate("e => e.files[0].name", input.element_handle())
        == "file-to-upload.txt"
    )
