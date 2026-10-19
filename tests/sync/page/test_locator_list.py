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

"""Port of tests/page/locator-list.spec.ts."""

from typing import List, Optional

from playwright.sync_api import Page


def test_LO_126_locator_all_should_work(page: Page) -> None:
    page.set_content("<div><p>A</p><p>B</p><p>C</p></div>")
    texts: List[Optional[str]] = []
    for p in page.locator("div >> p").all():
        texts.append(p.text_content())
    assert texts == ["A", "B", "C"]
