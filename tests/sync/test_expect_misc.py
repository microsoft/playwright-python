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

from playwright.sync_api import Page, expect
from tests.server import Server


def test_to_be_in_viewport_should_work(page: Page) -> None:
    page.set_content(
        """
      <div id=big style="height: 10000px;"></div>
      <div id=small>foo</div>
    """
    )
    expect(page.locator("#big")).to_be_in_viewport()
    expect(page.locator("#small")).not_to_be_in_viewport()
    page.locator("#small").scroll_into_view_if_needed()
    expect(page.locator("#small")).to_be_in_viewport()
    expect(page.locator("#small")).to_be_in_viewport(ratio=1)


def test_to_be_in_viewport_should_respect_ratio_option(
    page: Page, server: Server
) -> None:
    page.set_content(
        """
      <style>body, div, html { padding: 0; margin: 0; }</style>
      <div id=big style="height: 400vh;"></div>
    """
    )
    expect(page.locator("div")).to_be_in_viewport()
    expect(page.locator("div")).to_be_in_viewport(ratio=0.1)
    expect(page.locator("div")).to_be_in_viewport(ratio=0.2)

    expect(page.locator("div")).to_be_in_viewport(ratio=0.25)
    # In this test, element's ratio is 0.25.
    expect(page.locator("div")).not_to_be_in_viewport(ratio=0.26)

    expect(page.locator("div")).not_to_be_in_viewport(ratio=0.3)
    expect(page.locator("div")).not_to_be_in_viewport(ratio=0.7)
    expect(page.locator("div")).not_to_be_in_viewport(ratio=0.8)


def test_to_be_in_viewport_should_have_good_stack(page: Page, server: Server) -> None:
    with pytest.raises(AssertionError) as exc_info:
        expect(page.locator("body")).not_to_be_in_viewport(timeout=100)
    assert 'unexpected value "viewport ratio' in str(exc_info.value)


def test_to_be_in_viewport_should_report_intersection_even_if_fully_covered_by_other_element(
    page: Page, server: Server
) -> None:
    page.set_content(
        """
      <h1>hello</h1>
      <div style="position: relative; height: 10000px; top: -5000px;></div>
    """
    )
    expect(page.locator("h1")).to_be_in_viewport()
