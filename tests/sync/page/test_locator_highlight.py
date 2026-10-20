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

"""Port of tests/page/locator-highlight.spec.ts."""

from typing import Dict, Optional

from playwright.sync_api import FloatRect, Page, expect


def round_box(box: Optional[FloatRect]) -> Dict[str, int]:
    """Port of roundBox() in tests/config/utils.ts."""
    assert box
    return {
        "x": round(box["x"]),
        "y": round(box["y"]),
        "width": round(box["width"]),
        "height": round(box["height"]),
    }


def test_LO_114_should_highlight_locator(page: Page) -> None:
    page.set_content("<input type='text' />")
    page.locator("input").highlight()
    # The highlight overlay always renders the locator in JavaScript syntax.
    expect(page.locator("x-pw-tooltip")).to_have_text("locator('input')")
    expect(page.locator("x-pw-highlight")).to_be_visible()
    box1 = round_box(page.locator("input").bounding_box())
    box2 = round_box(page.locator("x-pw-highlight").bounding_box())
    assert box1 == box2
