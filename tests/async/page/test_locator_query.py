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

"""Port of tests/page/locator-query.spec.ts."""

import re
from typing import Any, Dict

import pytest

from playwright.async_api import Error, Page, Playwright, expect
from tests.server import Server

from ..utils import Utils


async def test_LO_157_should_respect_first_and_last_smoke(page: Page) -> None:
    await page.set_content(
        """
  <section>
    <div><p>A</p></div>
    <div><p>A</p><p>A</p></div>
    <div><p>A</p><p>A</p><p>A</p></div>
  </section>"""
    )
    assert await page.locator("div >> p").count() == 6
    assert await page.locator("div").locator("p").count() == 6
    assert await page.locator("div").first.locator("p").count() == 1
    assert await page.locator("div").last.locator("p").count() == 3


async def test_LO_158_should_respect_nth(page: Page) -> None:
    await page.set_content(
        """
  <section>
    <div><p>A</p></div>
    <div><p>A</p><p>A</p></div>
    <div><p>A</p><p>A</p><p>A</p></div>
  </section>"""
    )
    assert await page.locator("div >> p").nth(0).count() == 1
    assert await page.locator("div").nth(1).locator("p").count() == 2
    assert await page.locator("div").nth(2).locator("p").count() == 3


async def test_LO_159_should_throw_on_capture_w_nth(page: Page) -> None:
    await page.set_content("<section><div><p>A</p></div></section>")
    with pytest.raises(Error) as exc_info:
        await page.locator("*css=div >> p").nth(1).click()
    assert "Can't query n-th element" in exc_info.value.message


async def test_LO_160_should_throw_on_due_to_strictness(page: Page) -> None:
    await page.set_content("<div>A</div><div>B</div>")
    with pytest.raises(Error) as exc_info:
        await page.locator("div").is_visible()
    assert "strict mode violation" in exc_info.value.message


async def test_LO_161_should_throw_on_due_to_strictness_2(page: Page) -> None:
    await page.set_content("<select><option>One</option><option>Two</option></select>")
    with pytest.raises(Error) as exc_info:
        await page.locator("option").evaluate("e => {}")
    assert "strict mode violation" in exc_info.value.message


async def test_LO_162_should_filter_by_text(page: Page) -> None:
    await page.set_content("<div>Foobar</div><div>Bar</div>")
    await expect(page.locator("div", has_text="Foo")).to_have_text("Foobar")


async def test_LO_163_should_filter_by_text_2(page: Page) -> None:
    await page.set_content("<div>foo <span>hello world</span> bar</div>")
    await expect(page.locator("div", has_text="hello world")).to_have_text(
        "foo hello world bar"
    )


async def test_LO_164_should_filter_by_regex(page: Page) -> None:
    await page.set_content("<div>Foobar</div><div>Bar</div>")
    await expect(page.locator("div", has_text=re.compile(r"Foo.*"))).to_have_text(
        "Foobar"
    )


async def test_LO_165_should_filter_by_text_with_quotes(page: Page) -> None:
    await page.set_content('<div>Hello "world"</div><div>Hello world</div>')
    await expect(page.locator("div", has_text='Hello "world"')).to_have_text(
        'Hello "world"'
    )


async def test_LO_166_should_filter_by_regex_with_quotes(page: Page) -> None:
    await page.set_content('<div>Hello "world"</div><div>Hello world</div>')
    await expect(
        page.locator("div", has_text=re.compile(r'Hello "world"'))
    ).to_have_text('Hello "world"')


async def test_LO_167_should_filter_by_regex_with_a_single_quote(page: Page) -> None:
    await page.set_content("<button>let's let's<span>hello</span></button>")
    for pattern in [
        r"let's",
        r"let\'s",
        r"'s",
        r"\'s",
        r"let['abc]s",
    ]:
        regex = re.compile(pattern, re.IGNORECASE)
        await expect(
            page.locator("button", has_text=regex).locator("span")
        ).to_have_text("hello")
        await expect(
            page.get_by_role("button", name=regex).locator("span")
        ).to_have_text("hello")
    regex = re.compile(r"let\\'s", re.IGNORECASE)
    await expect(page.locator("button", has_text=regex)).not_to_be_visible()
    await expect(page.get_by_role("button", name=regex)).not_to_be_visible()
    for pattern in [
        r"let's let\'s",
        r"let\'s let's",
    ]:
        regex = re.compile(pattern, re.IGNORECASE)
        await expect(
            page.locator("button", has_text=regex).locator("span")
        ).to_have_text("hello")
        await expect(
            page.get_by_role("button", name=regex).locator("span")
        ).to_have_text("hello")

    await page.set_content("<button>let\\'s let\\'s<span>hello</span></button>")
    regex = re.compile(r"let\'s", re.IGNORECASE)
    await expect(page.locator("button", has_text=regex)).not_to_be_visible()
    await expect(page.get_by_role("button", name=regex)).not_to_be_visible()
    for pattern in [
        r"let\\'s",
        r"let\\\'s",
        r"let\\'s let\\\'s",
        r"let\\\'s let\\'s",
    ]:
        regex = re.compile(pattern, re.IGNORECASE)
        await expect(
            page.locator("button", has_text=regex).locator("span")
        ).to_have_text("hello")
        await expect(
            page.get_by_role("button", name=regex).locator("span")
        ).to_have_text("hello")

    await page.set_content("<button>let's hello</button>")
    # Python patterns have no "u" flag: re.UNICODE is the closest one.
    regex = re.compile(r"let's", re.IGNORECASE | re.UNICODE)
    await expect(page.locator("button", has_text=regex)).to_have_text("let's hello")
    await expect(page.get_by_role("button", name=regex)).to_have_text("let's hello")


async def test_LO_168_should_filter_by_regex_and_regexp_flags(page: Page) -> None:
    await page.set_content('<div>Hello "world"</div><div>Hello world</div>')
    await expect(
        page.locator("div", has_text=re.compile(r'hElLo "world"', re.IGNORECASE))
    ).to_have_text('Hello "world"')


async def test_LO_169_should_filter_by_case_insensitive_regex_in_a_child(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/15348
    await page.set_content('<div class="test"><h5>Title Text</h5></div>')
    await expect(
        page.locator("div", has_text=re.compile(r"^title text$", re.IGNORECASE))
    ).to_have_text("Title Text")


async def test_LO_170_should_filter_by_case_insensitive_regex_in_multiple_children(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/15348
    await page.set_content(
        '<div class="test"><h5>Title</h5> <h2><i>Text</i></h2></div>'
    )
    await expect(
        page.locator("div", has_text=re.compile(r"^title text$", re.IGNORECASE))
    ).to_have_class("test")


async def test_LO_171_should_filter_by_regex_with_special_symbols(page: Page) -> None:
    # https://github.com/microsoft/playwright/issues/15348
    await page.set_content(
        '<div class="test"><h5>First/"and"</h5><h2><i>Second\\</i></h2></div>'
    )
    await expect(
        page.locator(
            "div",
            has_text=re.compile(r'^first\/".*"second\\$', re.DOTALL | re.IGNORECASE),
        )
    ).to_have_class("test")


async def test_LO_172_should_support_has_locator(page: Page) -> None:
    await page.set_content("<div><span>hello</span></div><div><span>world</span></div>")
    await expect(page.locator("div", has=page.locator("text=world"))).to_have_count(1)
    assert (
        await page.locator("div", has=page.locator("text=world")).evaluate(
            "e => e.outerHTML"
        )
        == "<div><span>world</span></div>"
    )
    await expect(page.locator("div", has=page.locator('text="hello"'))).to_have_count(1)
    assert (
        await page.locator("div", has=page.locator('text="hello"')).evaluate(
            "e => e.outerHTML"
        )
        == "<div><span>hello</span></div>"
    )
    await expect(page.locator("div", has=page.locator("xpath=./span"))).to_have_count(2)
    await expect(page.locator("div", has=page.locator("span"))).to_have_count(2)
    await expect(
        page.locator("div", has=page.locator("span", has_text="wor"))
    ).to_have_count(1)
    assert (
        await page.locator("div", has=page.locator("span", has_text="wor")).evaluate(
            "e => e.outerHTML"
        )
        == "<div><span>world</span></div>"
    )
    await expect(
        page.locator("div", has=page.locator("span"), has_text="wor")
    ).to_have_count(1)


async def test_LO_173_should_support_locator_filter(page: Page) -> None:
    await page.set_content(
        "<section><div><span>hello</span></div><div><span>world</span></div></section>"
    )
    await expect(page.locator("div").filter(has_text="hello")).to_have_count(1)
    await expect(
        page.locator("div", has_text="hello").filter(has_text="hello")
    ).to_have_count(1)
    await expect(
        page.locator("div", has_text="hello").filter(has_text="world")
    ).to_have_count(0)
    await expect(
        page.locator("section", has_text="hello").filter(has_text="world")
    ).to_have_count(1)
    await expect(
        page.locator("div").filter(has_text="hello").locator("span")
    ).to_have_count(1)
    await expect(
        page.locator("div").filter(has=page.locator("span", has_text="world"))
    ).to_have_count(1)
    await expect(page.locator("div").filter(has=page.locator("span"))).to_have_count(2)
    await expect(
        page.locator("div").filter(has=page.locator("span"), has_text="world")
    ).to_have_count(1)
    await expect(
        page.locator("div").filter(has_not=page.locator("span", has_text="world"))
    ).to_have_count(1)
    await expect(
        page.locator("div").filter(has_not=page.locator("section"))
    ).to_have_count(2)
    await expect(
        page.locator("div").filter(has_not=page.locator("span"))
    ).to_have_count(0)
    await expect(page.locator("div").filter(has_not_text="hello")).to_have_count(1)
    await expect(page.locator("div").filter(has_not_text="foo")).to_have_count(2)


async def test_LO_174_should_support_locator_and(page: Page) -> None:
    await page.set_content(
        """
    <div data-testid=foo>hello</div><div data-testid=bar>world</div>
    <span data-testid=foo>hello2</span><span data-testid=bar>world2</span>
  """
    )
    await expect(page.locator("div").and_(page.locator("div"))).to_have_count(2)
    await expect(page.locator("div").and_(page.get_by_test_id("foo"))).to_have_text(
        ["hello"]
    )
    await expect(page.locator("div").and_(page.get_by_test_id("bar"))).to_have_text(
        ["world"]
    )
    await expect(page.get_by_test_id("foo").and_(page.locator("div"))).to_have_text(
        ["hello"]
    )
    await expect(page.get_by_test_id("bar").and_(page.locator("span"))).to_have_text(
        ["world2"]
    )
    await expect(
        page.locator("span").and_(page.get_by_test_id(re.compile(r"bar|foo")))
    ).to_have_count(2)


async def test_LO_175_should_support_locator_or(page: Page) -> None:
    await page.set_content("<div>hello</div><span>world</span>")
    await expect(page.locator("div").or_(page.locator("span"))).to_have_count(2)
    await expect(page.locator("div").or_(page.locator("span"))).to_have_text(
        ["hello", "world"]
    )
    await expect(
        page.locator("span").or_(page.locator("article")).or_(page.locator("div"))
    ).to_have_text(["hello", "world"])
    await expect(page.locator("article").or_(page.locator("something"))).to_have_count(
        0
    )
    await expect(page.locator("article").or_(page.locator("div"))).to_have_text("hello")
    await expect(page.locator("article").or_(page.locator("span"))).to_have_text(
        "world"
    )
    await expect(page.locator("div").or_(page.locator("article"))).to_have_text("hello")
    await expect(page.locator("span").or_(page.locator("article"))).to_have_text(
        "world"
    )


async def test_LO_176_should_support_locator_locator_with_and_or(page: Page) -> None:
    await page.set_content(
        """
    <div>one <span>two</span> <button>three</button> </div>
    <span>four</span>
    <button>five</button>
  """
    )

    await expect(page.locator("div").locator(page.locator("button"))).to_have_text(
        ["three"]
    )
    await expect(
        page.locator("div").locator(page.locator("button").or_(page.locator("span")))
    ).to_have_text(["two", "three"])
    await expect(page.locator("button").or_(page.locator("span"))).to_have_text(
        ["two", "three", "four", "five"]
    )

    await expect(
        page.locator("div").locator(
            page.locator("button").and_(page.get_by_role("button"))
        )
    ).to_have_text(["three"])
    await expect(page.locator("button").and_(page.get_by_role("button"))).to_have_text(
        ["three", "five"]
    )


async def test_LO_177_should_support_locator_within(page: Page) -> None:
    await page.set_content(
        """
    <table>
      <tr><td>a1</td><td>a2</td><td>a3</td></tr>
      <tr><td>b1</td><td>b2</td><td>b3</td></tr>
      <tr><td>c1</td><td>c2</td><td>c3</td></tr>
    </table>
    <span>outside</span>
  """
    )

    await expect(page.get_by_role("cell").within(page.get_by_role("row"))).to_have_text(
        ["a1", "a2", "a3", "b1", "b2", "b3", "c1", "c2", "c3"]
    )
    await expect(
        page.get_by_role("cell").nth(1).within(page.get_by_role("row"))
    ).to_have_text(["a2", "b2", "c2"])
    await expect(
        page.get_by_role("cell").last.within(page.get_by_role("row"))
    ).to_have_text(["a3", "b3", "c3"])
    await expect(
        page.get_by_role("cell").nth(1).within(page.get_by_role("row").nth(2))
    ).to_have_text(["c2"])
    await expect(page.locator("span").within(page.get_by_role("row"))).to_have_count(0)
    await expect(
        page.get_by_role("cell").nth(1).within(page.get_by_role("row")).nth(1)
    ).to_have_text("b2")


async def test_LO_178_should_allow_some_but_not_all_nested_frame_locators(
    page: Page,
) -> None:
    await page.set_content(
        '<iframe srcdoc="<span id=target>world</span>"></iframe><span>hello</span>'
    )
    await expect(
        page.frame_locator("iframe")
        .locator("span")
        .or_(page.frame_locator("iframe").locator("article"))
    ).to_have_text("world")
    await expect(
        page.frame_locator("iframe")
        .locator("article")
        .or_(page.frame_locator("iframe").locator("span"))
    ).to_have_text("world")
    await expect(
        page.frame_locator("iframe")
        .locator("span")
        .and_(page.frame_locator("iframe").locator("#target"))
    ).to_have_text("world")
    with pytest.raises(AssertionError) as exc_info1:
        await expect(
            page.frame_locator("iframe")
            .locator("div")
            .or_(page.frame_locator("#iframe").locator("span"))
        ).to_have_text("world")
    assert (
        """Frame locators are not allowed inside composite locators, while querying "locator("iframe").content_frame.locator("div").or_(locator("#iframe").content_frame.locator("span"))"""
        in str(exc_info1.value)
    )
    with pytest.raises(AssertionError) as exc_info2:
        await expect(
            page.frame_locator("iframe")
            .locator("div")
            .and_(page.frame_locator("#iframe").locator("span"))
        ).to_have_text("world")
    assert (
        """Frame locators are not allowed inside composite locators, while querying "locator("iframe").content_frame.locator("div").and_(locator("#iframe").content_frame.locator("span"))"""
        in str(exc_info2.value)
    )


async def test_LO_179_should_keep_the_capture_when_removing_a_common_frame_prefix(
    page: Page,
) -> None:
    await page.set_content(
        '<iframe id=f srcdoc="<section id=target><span>hi</span></section>"></iframe>'
    )
    inner = page.frame_locator("#f").locator("*css=section >> span")
    await expect(
        page.frame_locator("#f").locator("body").locator(inner)
    ).to_have_attribute("id", "target")

    capture_frame = page.locator("*css=#f").content_frame.locator("span")
    with pytest.raises(Error) as exc_info:
        await page.frame_locator("#f").locator("body").locator(capture_frame).count()
    assert (
        "Can not capture the selector before diving into the frame"
        in exc_info.value.message
    )


async def test_LO_180_should_enforce_same_frame_for_has_left_of_right_of_above_below_near(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/frames/two-frames.html")
    child = page.frames[1]
    for option in ["has"]:
        options: Dict[str, Any] = {option: child.locator("span")}
        with pytest.raises(Error) as exc_info:
            page.locator("div", **options)
        assert (
            f'Inner "{option}" locator must belong to the same frame.'
            in exc_info.value.message
        )


async def test_LO_181_alias_methods_coverage(page: Page) -> None:
    await page.set_content("<div><button>Submit</button></div>")
    await expect(page.locator("button")).to_have_count(1)
    await expect(page.locator("div").locator("button")).to_have_count(1)
    await expect(page.locator("div").get_by_role("button")).to_have_count(1)
    await expect(page.main_frame.locator("button")).to_have_count(1)


async def test_LO_182_count_should_not_throw_during_navigation(
    playwright: Playwright, page: Page, server: Server, utils: Utils
) -> None:
    create_dummy_selector = """({
    query(root, selector) {
      window.location.href = './frames/one-frame.html';
      return document.querySelector(selector);
    },
    queryAll(root, selector) {
      window.location.href = './frames/one-frame.html';
      return Array.from(document.querySelectorAll(selector));
    }
  })"""
    await utils.register_selector_engine(
        playwright.selectors, "locatorCountHelper", create_dummy_selector
    )
    await page.goto(server.PREFIX + "/frames/one-frame.html")
    await page.frames[1].set_content("<div>A</div>")
    assert (
        await page.frame_locator("locatorCountHelper=iframe")
        .locator("locatorCountHelper=div")
        .count()
        == 0
    )
