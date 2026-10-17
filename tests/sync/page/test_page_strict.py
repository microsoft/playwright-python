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

"""Port of tests/page/page-strict.spec.ts."""

import pytest

from playwright.sync_api import Error, Page, expect


def test_SM_001_should_fail_page_text_content_in_strict_mode(page: Page) -> None:
    page.set_content("<span>span1</span><div><span>target</span></div>")
    with pytest.raises(Error) as exc_info:
        page.text_content("span", strict=True)
    assert "strict mode violation" in exc_info.value.message
    assert '1) <span>span1</span> aka get_by_text("span1")' in exc_info.value.message
    assert '2) <span>target</span> aka get_by_text("target")' in exc_info.value.message


def test_SM_002_should_fail_page_get_attribute_in_strict_mode(page: Page) -> None:
    page.set_content("<span>span1</span><div><span>target</span></div>")
    with pytest.raises(Error) as exc_info:
        page.get_attribute("span", "id", strict=True)
    assert "strict mode violation" in exc_info.value.message


def test_SM_003_should_fail_page_fill_in_strict_mode(page: Page) -> None:
    page.set_content("<input></input><div><input></input></div>")
    with pytest.raises(Error) as exc_info:
        page.fill("input", "text", strict=True)
    assert "strict mode violation" in exc_info.value.message
    assert '1) <input/> aka get_by_role("textbox").first' in exc_info.value.message
    assert (
        '2) <input/> aka locator("div").get_by_role("textbox")'
        in exc_info.value.message
    )


def test_SM_004_should_fail_page_in_strict_mode(page: Page) -> None:
    page.set_content("<span>span1</span><div><span>target</span></div>")
    with pytest.raises(Error) as exc_info:
        page.query_selector("span", strict=True)
    assert "strict mode violation" in exc_info.value.message


def test_SM_005_should_fail_page_wait_for_selector_in_strict_mode(
    page: Page,
) -> None:
    page.set_content("<span>span1</span><div><span>target</span></div>")
    with pytest.raises(Error) as exc_info:
        page.wait_for_selector("span", strict=True)
    assert "strict mode violation" in exc_info.value.message


def test_SM_006_should_fail_page_dispatch_event_in_strict_mode(
    page: Page,
) -> None:
    page.set_content("<span></span><div><span></span></div>")
    with pytest.raises(Error) as exc_info:
        page.dispatch_event("span", "click", {}, strict=True)
    assert "strict mode violation" in exc_info.value.message
    assert '1) <span></span> aka locator("span").first' in exc_info.value.message
    assert '2) <span></span> aka locator("div span")' in exc_info.value.message


def test_SM_007_should_properly_format_nth_child_in_strict_mode_message(
    page: Page,
) -> None:
    page.set_content(
        """
  <div>
    <div>
    </div>
    <div>
      <div>
      </div>
      <div>
      </div>
    </div>
  </div>
  <div>
    <div class='foo'>
    </div>
    <div class='foo'>
    </div>
  </div>
  """
    )
    with pytest.raises(Error) as exc_info:
        page.locator(".foo").hover()
    assert "strict mode violation" in exc_info.value.message
    # Second div has body > div:nth-child(2) > div:nth-child(2) selector which would be ambiguous
    # if '>' were ' '.
    assert "body > div:nth-child(2) > div:nth-child(2)" in exc_info.value.message


def test_SM_008_should_escape_class_names(page: Page) -> None:
    page.set_content(
        """
  <div>
    <div></div>
    <div>
      <div></div>
      <div></div>
    </div>
  </div>
  <div>
    <div class='foo bar:0'>
    </div>
    <div class='foo bar:1'>
    </div>
  </div>
  """
    )
    with pytest.raises(Error) as exc_info:
        page.locator(".foo").hover()
    assert "strict mode violation" in exc_info.value.message
    assert '<div class="foo bar:0' in exc_info.value.message
    assert '<div class="foo bar:1' in exc_info.value.message


def test_SM_009_should_escape_tag_names(page: Page) -> None:
    page.set_content(
        """
    <q:template> </q:template>
    <span>special test description</span>
    <q:template hidden="" aria-hidden="true">
      <span>special test description</span>
    </q:template>
  """
    )
    # Python assertions raise AssertionError, not Error.
    with pytest.raises(AssertionError) as exc_info:
        expect(page.get_by_text("special test description")).to_be_visible()
    message = str(exc_info.value)
    assert "strict mode violation" in message
    assert 'get_by_text("special test description").first' in message
    assert (
        'locator("q\\\\:template").filter(has_text="special test description")'
        in message
    )


def test_SM_010_should_keep_the_engine_name_for_a_text_selector_in_strict_mode(
    page: Page,
) -> None:
    page.set_content("<div>..loading</div><div>..loading</div>")
    with pytest.raises(Error) as exc_info:
        page.locator("text=..loading").hover()
    assert "strict mode violation" in exc_info.value.message
    assert 'locator("text=..loading")' in exc_info.value.message
