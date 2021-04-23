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

from playwright.async_api import Error


def test_should_wait_for_visible(page):
    page.set_content('<div id=div style="display:none">content</div>')
    div = page.query_selector("div")
    page.evaluate('setTimeout(() => div.style.display = "block", 500)')
    assert div.is_visible() is False
    div.wait_for_element_state("visible")
    assert div.is_visible()


def test_should_wait_for_already_visible(page):
    page.set_content("<div>content</div>")
    div = page.query_selector("div")
    div.wait_for_element_state("visible")


def test_should_timeout_waiting_for_visible(page):
    page.set_content('<div style="display:none">content</div>')
    div = page.query_selector("div")
    with pytest.raises(Error) as exc_info:
        div.wait_for_element_state("visible", timeout=1000)
    assert "Timeout 1000ms exceeded" in exc_info.value.message


def test_should_throw_waiting_for_visible_when_detached(page):
    page.set_content('<div id=div style="display:none">content</div>')
    div = page.query_selector("div")
    page.evaluate("setTimeout(() => div.remove(), 500)")
    with pytest.raises(Error) as exc_info:
        div.wait_for_element_state("visible")
    assert "Element is not attached to the DOM" in exc_info.value.message


def test_should_wait_for_hidden(page):
    page.set_content("<div id=div>content</div>")
    div = page.query_selector("div")
    page.evaluate('setTimeout(() => div.style.display = "none", 500)')
    assert div.is_hidden() is False
    div.wait_for_element_state("hidden")
    assert div.is_hidden()


def test_should_wait_for_already_hidden(page):
    page.set_content("<div></div>")
    div = page.query_selector("div")
    div.wait_for_element_state("hidden")


def test_should_wait_for_hidden_when_detached(page):
    page.set_content("<div id=div>content</div>")
    div = page.query_selector("div")
    page.evaluate("setTimeout(() => div.remove(), 500)")
    div.wait_for_element_state("hidden")
    assert div.is_hidden()


def test_should_wait_for_enabled_button(page, server):
    page.set_content("<button id=button disabled><span>Target</span></button>")
    span = page.query_selector("text=Target")
    assert span.is_enabled() is False
    page.evaluate("setTimeout(() => button.disabled = false, 500)")
    span.wait_for_element_state("enabled")
    assert span.is_enabled()


def test_should_throw_waiting_for_enabled_when_detached(page):
    page.set_content("<button id=button disabled>Target</button>")
    button = page.query_selector("button")
    page.evaluate("setTimeout(() => button.remove(), 500)")
    with pytest.raises(Error) as exc_info:
        button.wait_for_element_state("enabled")
    assert "Element is not attached to the DOM" in exc_info.value.message


def test_should_wait_for_disabled_button(page):
    page.set_content("<button id=button><span>Target</span></button>")
    span = page.query_selector("text=Target")
    assert span.is_disabled() is False
    page.evaluate("setTimeout(() => button.disabled = true, 500)")
    span.wait_for_element_state("disabled")
    assert span.is_disabled()


def test_should_wait_for_editable_input(page, server):
    page.set_content("<input id=input readonly>")
    input = page.query_selector("input")
    page.evaluate("setTimeout(() => input.readOnly = false, 500)")
    assert input.is_editable() is False
    input.wait_for_element_state("editable")
    assert input.is_editable()
