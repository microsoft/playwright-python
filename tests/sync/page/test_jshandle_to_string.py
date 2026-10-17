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

"""Port of tests/page/jshandle-to-string.spec.ts."""

import time

import pytest

from playwright.sync_api import JSHandle, Page


def poll_preview(page: Page, handle: JSHandle, expected: str) -> None:
    """Port of expect.poll(() => handle.toString()).toBe(expected)."""
    deadline = time.monotonic() + 5
    while str(handle) != expected and time.monotonic() < deadline:
        page.wait_for_timeout(100)
    assert str(handle) == expected


def test_JH_018_should_work_for_primitives(page: Page) -> None:
    number_handle = page.evaluate_handle("() => 2")
    assert str(number_handle) == "2"
    string_handle = page.evaluate_handle("() => 'a'")
    assert str(string_handle) == "a"


def test_JH_019_should_work_for_complicated_objects(
    page: Page, browser_name: str
) -> None:
    a_handle = page.evaluate_handle("() => window")
    if browser_name != "firefox":
        assert str(a_handle) == "Window"
    else:
        assert str(a_handle) == "JSHandle@object"


def test_JH_020_should_beautifully_render_sparse_arrays(
    page: Page, browser_name: str
) -> None:
    with page.expect_console_message() as msg_info:
        page.evaluate_handle(
            """() => {
            const a = [];
            a[1] = 1;
            a[10] = 2;
            a[100] = 3;
            console.log(a);
          }"""
        )
    msg = msg_info.value
    if browser_name == "firefox":
        assert msg.text == "Array"
    else:
        assert msg.text == "[empty, 1, empty x 8, 2, empty x 89, 3]"


def test_JH_021_should_work_for_promises(page: Page) -> None:
    # wrap the promise in an object, otherwise we will await.
    wrapper_handle = page.evaluate_handle("() => ({ b: Promise.resolve(123) })")
    b_handle = wrapper_handle.get_property("b")
    assert str(b_handle) == "Promise"


def test_JH_022_should_work_with_different_subtypes_smoke(
    page: Page, browser_name: str
) -> None:
    # Python invokes an expression that evaluates to a function, so return the
    # function from an arrow function to get a handle to it.
    assert "function" in str(page.evaluate_handle("() => (function(){})"))
    assert str(page.evaluate_handle("12")) == "12"
    assert str(page.evaluate_handle("true")) == "true"
    assert str(page.evaluate_handle("undefined")) == "undefined"
    assert str(page.evaluate_handle('"foo"')) == "foo"
    assert str(page.evaluate_handle("Symbol()")) == "Symbol()"
    assert "Map" in str(page.evaluate_handle("new Map()"))
    assert "Set" in str(page.evaluate_handle("new Set()"))
    assert "Array" in str(page.evaluate_handle("[]"))
    assert str(page.evaluate_handle("null")) == "null"
    body_handle = page.evaluate_handle("document.body")
    poll_preview(page, body_handle, "JSHandle@<body></body>")
    assert str(page.evaluate_handle("new WeakMap()")) == "WeakMap"
    assert str(page.evaluate_handle("new WeakSet()")) == "WeakSet"
    assert "Error" in str(page.evaluate_handle("new Error()"))
    assert str(page.evaluate_handle("new Proxy({}, {})")) == (
        "Proxy(Object)" if browser_name == "chromium" else "Proxy"
    )


@pytest.mark.skip_browser("firefox")
def test_JH_023_should_work_with_previewable_subtypes(page: Page) -> None:
    assert str(page.evaluate_handle("/foo/")) == "/foo/"
    assert "GMT" in str(page.evaluate_handle("new Date(0)"))
    assert "Int32Array" in str(page.evaluate_handle("new Int32Array()"))
