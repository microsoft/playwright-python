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

"""Port of tests/page/page-request-gc.spec.ts."""

import pytest

from playwright.sync_api import Page


def test_RO_149_should_work(page: Page) -> None:
    page.evaluate(
        """() => {
    globalThis.objectToDestroy = { hello: 'world' };
    globalThis.weakRef = new WeakRef(globalThis.objectToDestroy);
  }"""
    )

    page.request_gc()
    assert page.evaluate("() => globalThis.weakRef.deref()") == {"hello": "world"}

    page.request_gc()
    assert page.evaluate("() => globalThis.weakRef.deref()") == {"hello": "world"}

    page.evaluate("() => globalThis.objectToDestroy = null")
    page.request_gc()
    assert page.evaluate("() => globalThis.weakRef.deref()") is None


def test_RO_150_should_collect_element_retained_by_locator_hit_target_interceptor_after_detach(
    page: Page, browser_name: str
) -> None:
    if browser_name == "firefox":
        pytest.skip(
            "fixme: Firefox hit-target interceptor does not release its element reference on detach"
        )
    if browser_name == "chromium":
        pytest.skip(
            "fixme: Chromium retains a native reference to the last hit-tested element; fix pending upstream discussion, see #41575"
        )
    page.set_content('<button id="btn">click me</button>')
    page.locator("#btn").click()
    page.evaluate(
        """() => {
    globalThis.weakRef = new WeakRef(document.getElementById('btn'));
    document.getElementById('btn').remove();
  }"""
    )
    page.request_gc()
    assert page.evaluate("() => globalThis.weakRef.deref()") is None
