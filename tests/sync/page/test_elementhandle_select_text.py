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

"""Port of tests/page/elementhandle-select-text.spec.ts."""

from typing import Any, Callable, List

import pytest

from playwright.sync_api import Error, Page
from tests.server import Server


def test_EH_102_should_select_textarea(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/textarea.html")
    textarea = page.query_selector("textarea")
    assert textarea
    textarea.evaluate("textarea => textarea.value = 'some value'")
    textarea.select_text()
    assert page.evaluate("() => window.getSelection().toString()") == "some value"


def test_EH_103_should_select_input(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/textarea.html")
    input = page.query_selector("input")
    assert input
    input.evaluate("input => input.value = 'some value'")
    input.select_text()
    assert page.evaluate("() => window.getSelection().toString()") == "some value"


def test_EH_104_should_select_plain_div(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/textarea.html")
    div = page.query_selector("div.plain")
    assert div
    div.select_text()
    assert page.evaluate("() => window.getSelection().toString()") == "Plain div"


def test_EH_105_should_timeout_waiting_for_invisible_element(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/input/textarea.html")
    textarea = page.query_selector("textarea")
    assert textarea
    textarea.evaluate("e => e.style.display = 'none'")
    with pytest.raises(Error) as exc_info:
        textarea.select_text(timeout=3000)
    assert "element is not visible" in exc_info.value.message


def test_EH_106_should_wait_for_visible(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    page.goto(server.PREFIX + "/input/textarea.html")
    textarea = page.query_selector("textarea")
    assert textarea
    textarea.evaluate("textarea => textarea.value = 'some value'")
    textarea.evaluate("e => e.style.display = 'none'")
    done = False

    def select_text() -> None:
        nonlocal done
        textarea.select_text(timeout=3000)
        done = True

    def show() -> None:
        page.wait_for_timeout(1000)
        assert done is False
        textarea.evaluate("e => e.style.display = 'block'")

    sync_gather(select_text, show)
