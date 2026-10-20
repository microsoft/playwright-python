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

"""Python only: tests of behaviors that no upstream test covers."""


from playwright.sync_api import Page, expect


def test_get_by_text(page: Page) -> None:
    page.set_content("<div><div>yo</div><div>ya</div><div>\nye  </div></div>")

    expect(page.get_by_text("yo")).to_have_count(1)
    expect(page.main_frame.get_by_text("yo")).to_have_count(1)
    expect(page.locator("div").get_by_text("yo")).to_have_count(1)

    assert ">\nye  </div>" in page.get_by_text("ye").evaluate("e => e.outerHTML")
    assert ">\nye  </div>" in page.get_by_text(r"ye").evaluate("e => e.outerHTML")

    page.set_content("<div> ye </div><div>ye</div>")
    assert "> ye </div>" in page.get_by_text("ye", exact=True).first.evaluate(
        "e => e.outerHTML"
    )

    page.set_content("<div>Hello world</div><div>Hello</div>")
    assert (
        page.get_by_text("Hello", exact=True).evaluate("e => e.outerHTML")
        == "<div>Hello</div>"
    )
